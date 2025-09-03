
import numpy as np
import pandas as pd
from logging import Logger
from typing import List

from pydantic import BaseModel, Field

from nexus.core.data_hub import DataHub
from nexus.core.plugin_decorator import plugin


class LatencyCompensatorConfig(BaseModel):
    """Configuration model for the Latency Compensator plugin."""
    latency_to_compensate_s: float = 0.2
    measurement_noise_pos: float = 0.5
    measurement_noise_vel: float = 0.8
    measurement_noise_yaw: float = 0.5
    process_noise_std_pos: float = 0.5
    process_noise_std_vel: float = 0.8
    process_noise_std_yaw: float = 0.5
    process_noise_std_yaw_rate: float = 0.3
    input_key: str = "latent_measurements"


class _EKF_CTRV:
    """Helper class to encapsulate the EKF state and logic."""
    def __init__(self, config: LatencyCompensatorConfig):
        # State vector: [x, y, v, yaw, yaw_rate]
        self.x = np.zeros((5, 1))
        self.P = np.eye(5) * 500  # Initial state covariance

        # Measurement matrix H
        self.H = np.array([
            [1, 0, 0, 0, 0], [0, 1, 0, 0, 0], 
            [0, 0, 1, 0, 0], [0, 0, 0, 1, 0]
        ])

        # Measurement noise R
        self.R = np.diag([
            config.measurement_noise_pos**2,
            config.measurement_noise_pos**2,
            config.measurement_noise_vel**2,
            config.measurement_noise_yaw**2
        ])

        # Process noise Q
        self.Q = np.diag([
            config.process_noise_std_pos**2,
            config.process_noise_std_pos**2,
            config.process_noise_std_vel**2,
            config.process_noise_std_yaw**2,
            config.process_noise_std_yaw_rate**2
        ])

    def predict_step(self, x, P, dt):
        v, yaw, yaw_rate = x[2, 0], x[3, 0], x[4, 0]
        if abs(yaw_rate) > 1e-4:
            px_new = x[0, 0] + (v / yaw_rate) * (np.sin(yaw + yaw_rate * dt) - np.sin(yaw))
            py_new = x[1, 0] + (v / yaw_rate) * (-np.cos(yaw + yaw_rate * dt) + np.cos(yaw))
        else:
            px_new = x[0, 0] + v * dt * np.cos(yaw)
            py_new = x[1, 0] + v * dt * np.sin(yaw)
        
        x_pred = np.array([[px_new], [py_new], [v], [yaw + yaw_rate * dt], [yaw_rate]])

        F_j = np.eye(5)
        if abs(yaw_rate) > 1e-4:
            F_j[0, 2] = (np.sin(yaw + yaw_rate * dt) - np.sin(yaw)) / yaw_rate
            F_j[0, 3] = (v / yaw_rate) * (np.cos(yaw + yaw_rate * dt) - np.cos(yaw))
            F_j[0, 4] = (v/yaw_rate**2)*(-dt*yaw_rate*np.cos(yaw+yaw_rate*dt) + np.sin(yaw+yaw_rate*dt) - np.sin(yaw))
            F_j[1, 2] = (-np.cos(yaw + yaw_rate * dt) + np.cos(yaw)) / yaw_rate
            F_j[1, 3] = (v / yaw_rate) * (np.sin(yaw + yaw_rate * dt) - np.sin(yaw))
            F_j[1, 4] = (v/yaw_rate**2)*(-dt*yaw_rate*np.sin(yaw+yaw_rate*dt) - np.cos(yaw+yaw_rate*dt) + np.cos(yaw))
            F_j[3, 4] = dt
        else:
            F_j[0, 2], F_j[0, 3] = dt * np.cos(yaw), -v * dt * np.sin(yaw)
            F_j[1, 2], F_j[1, 3] = dt * np.sin(yaw), v * dt * np.cos(yaw)

        P_pred = F_j @ P @ F_j.T + self.Q
        return x_pred, P_pred

    def update_step(self, x, P, z):
        y = z - self.H @ x
        S = self.H @ P @ self.H.T + self.R
        K = P @ self.H.T @ np.linalg.inv(S)
        x_new = x + K @ y
        P_new = (np.eye(5) - K @ self.H) @ P
        return x_new, P_new


@plugin(
    name="Latency Compensator",
    output_key="predicted_states"
)
def compensate_latency(
    # Dependencies from DataHub
    latent_measurements: pd.DataFrame,
    # Dependencies from Plugin Config
    config: LatencyCompensatorConfig,
    # Dependencies from Context
    logger: Logger
) -> pd.DataFrame:
    """
    Compensates for a fixed latency in measurement data by predicting the state
    forward in time using an Extended Kalman Filter (EKF) with a Constant Turn
    Rate and Velocity (CTRV) model.
    """
    ekf = _EKF_CTRV(config)
    df = latent_measurements.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

    # Initialize state
    ekf.x[0] = df.iloc[0]['x']
    ekf.x[1] = df.iloc[0]['y']
    ekf.x[2] = df.iloc[0]['vehicle_speed']
    ekf.x[3] = df.iloc[0]['yaw']
    ekf.x[4] = 0  # Initial yaw rate

    predictions = []
    for i in range(len(df)):
        dt = (df.iloc[i]['timestamp'] - df.iloc[i-1]['timestamp']).total_seconds() if i > 0 else (1.0 / 30.0)
        
        # EKF Predict
        ekf.x, ekf.P = ekf.predict_step(ekf.x, ekf.P, dt)

        # EKF Update
        z = np.array([
            [df.iloc[i]['x']], [df.iloc[i]['y']],
            [df.iloc[i]['vehicle_speed']], [df.iloc[i]['yaw']]
        ])
        ekf.x, ekf.P = ekf.update_step(ekf.x, ekf.P, z)

        # Predict forward by latency to get the compensated state
        compensated_state, _ = ekf.predict_step(ekf.x, ekf.P, config.latency_to_compensate_s)
        predictions.append(compensated_state[:4].flatten())

    pred_df = pd.DataFrame(predictions, columns=['predicted_x', 'predicted_y', 'predicted_speed', 'predicted_yaw_rad'])
    pred_df['timestamp'] = df['timestamp']
    
    logger.info(f"Successfully compensated latency for {len(pred_df)} records.")
    return pred_df
