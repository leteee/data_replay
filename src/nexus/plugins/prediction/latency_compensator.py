import numpy as np
import pandas as pd
from ..base_plugin import BasePlugin
from ...core.data_hub import DataHub

class LatencyCompensator(BasePlugin):
    """
    A plugin that compensates for a fixed latency in measurement data by
    predicting the state forward in time using an Extended Kalman Filter (EKF)
    with a Constant Turn Rate and Velocity (CTRV) model.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.latency_s = self.config.get('latency_to_compensate_s', 0.2)
        
        # EKF parameters for CTRV model
        # State vector: [x, y, v, yaw, yaw_rate]
        self.x = np.zeros((5, 1))
        self.P = np.eye(5) * 500 # Initial state covariance
        
        # Measurement matrix H: We now measure x, y, v, and yaw
        self.H = np.array([
            [1, 0, 0, 0, 0],  # x
            [0, 1, 0, 0, 0],  # y
            [0, 0, 1, 0, 0],  # v
            [0, 0, 0, 1, 0]   # yaw
        ])
        
        # Measurement noise R
        self.R = np.diag([
            self.config.get('measurement_noise_pos', 0.5)**2,
            self.config.get('measurement_noise_pos', 0.5)**2,
            self.config.get('measurement_noise_vel', 0.8)**2,
            self.config.get('measurement_noise_yaw', 0.5)**2
        ])

        # Process noise Q
        self.Q = np.diag([self.config.get('process_noise_std_pos', 0.5)**2,
                          self.config.get('process_noise_std_pos', 0.5)**2,
                          self.config.get('process_noise_std_vel', 0.8)**2,
                          self.config.get('process_noise_std_yaw', 0.5)**2,
                          self.config.get('process_noise_std_yaw_rate', 0.3)**2])

    def _predict_step(self, x, P, dt):
        """Performs the EKF prediction step using the CTRV model."""
        v = x[2, 0]
        yaw = x[3, 0]
        yaw_rate = x[4, 0]

        # State transition
        if abs(yaw_rate) > 1e-4:
            px_new = x[0, 0] + (v / yaw_rate) * (np.sin(yaw + yaw_rate * dt) - np.sin(yaw))
            py_new = x[1, 0] + (v / yaw_rate) * (-np.cos(yaw + yaw_rate * dt) + np.cos(yaw))
        else: # Straight line
            px_new = x[0, 0] + v * dt * np.cos(yaw)
            py_new = x[1, 0] + v * dt * np.sin(yaw)
        
        v_new = v
        yaw_new = yaw + yaw_rate * dt
        yaw_rate_new = yaw_rate

        x_pred = np.array([[px_new], [py_new], [v_new], [yaw_new], [yaw_rate_new]])

        # Jacobian of the state transition function (F_j)
        F_j = np.eye(5)
        if abs(yaw_rate) > 1e-4:
            F_j[0, 2] = (1 / yaw_rate) * (np.sin(yaw + yaw_rate * dt) - np.sin(yaw))
            F_j[0, 3] = (v / yaw_rate) * (np.cos(yaw + yaw_rate * dt) - np.cos(yaw))
            F_j[0, 4] = (v / yaw_rate**2) * (-dt * yaw_rate * np.cos(yaw + yaw_rate * dt) + np.sin(yaw + yaw_rate * dt) - np.sin(yaw))
            F_j[1, 2] = (1 / yaw_rate) * (-np.cos(yaw + yaw_rate * dt) + np.cos(yaw))
            F_j[1, 3] = (v / yaw_rate) * (np.sin(yaw + yaw_rate * dt) - np.sin(yaw))
            F_j[1, 4] = (v / yaw_rate**2) * (-dt * yaw_rate * np.sin(yaw + yaw_rate * dt) - np.cos(yaw + yaw_rate * dt) + np.cos(yaw))
            F_j[3, 4] = dt
        else:
            F_j[0, 2] = dt * np.cos(yaw)
            F_j[0, 3] = -v * dt * np.sin(yaw)
            F_j[1, 2] = dt * np.sin(yaw)
            F_j[1, 3] = v * dt * np.cos(yaw)

        P_pred = F_j @ P @ F_j.T + self.Q
        return x_pred, P_pred

    def run(self, data_hub: DataHub):
        super().run(data_hub)
        input_name = self.config.get("inputs", [None])[0]
        latent_df = data_hub.get(input_name)
        latent_df['timestamp'] = pd.to_datetime(latent_df['timestamp'], unit='s')

        # Initialize state
        self.x[0] = latent_df.iloc[0]['x']
        self.x[1] = latent_df.iloc[0]['y']
        self.x[2] = latent_df.iloc[0]['vehicle_speed']
        self.x[3] = latent_df.iloc[0]['yaw']
        self.x[4] = 0 # Initial yaw rate

        predictions = []
        for i in range(len(latent_df)):
            dt = (latent_df.iloc[i]['timestamp'] - latent_df.iloc[i-1]['timestamp']).total_seconds() if i > 0 else (1.0 / 30.0)
            
            # EKF Predict
            self.x, self.P = self._predict_step(self.x, self.P, dt)

            # EKF Update with all available measurements
            z = np.array([
                [latent_df.iloc[i]['x']],
                [latent_df.iloc[i]['y']],
                [latent_df.iloc[i]['vehicle_speed']],
                [latent_df.iloc[i]['yaw']]
            ])
            y = z - self.H @ self.x
            S = self.H @ self.P @ self.H.T + self.R
            K = self.P @ self.H.T @ np.linalg.inv(S)
            self.x = self.x + K @ y
            self.P = (np.eye(5) - K @ self.H) @ self.P

            # Predict forward by latency to get the compensated state
            compensated_state, _ = self._predict_step(self.x, self.P, self.latency_s)
            # Store the first 4 state variables: x, y, speed, yaw
            predictions.append(compensated_state[:4].flatten())

        pred_df = pd.DataFrame(predictions, columns=['predicted_x', 'predicted_y', 'predicted_speed', 'predicted_yaw_rad'])
        pred_df['timestamp'] = latent_df['timestamp']

        output_name = self.config.get("outputs", [None])[0]
        data_hub.register(output_name, pred_df)
        self.logger.info(f"Successfully registered EKF predictions as '{output_name}'.")