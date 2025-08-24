
import numpy as np
import pandas as pd
from modules.base_plugin import BasePlugin

class KalmanFilter(BasePlugin):
    """
    A plugin that applies a Kalman filter to predict the next position of a vehicle.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize Kalman Filter parameters
        # We'll use a constant velocity model
        # State: [x, y, vx, vy]
        # Measurement: [x, y]

        self.dt = self.config.get('dt', 0.02)  # Time step

        # State transition matrix
        self.F = np.array([  [1, 0, self.dt, 0],
                             [0, 1, 0, self.dt],
                             [0, 0, 1, 0],
                             [0, 0, 0, 1]  ])

        # Measurement matrix
        self.H = np.array([  [1, 0, 0, 0],
                             [0, 1, 0, 0]  ])

        # Process noise covariance
        self.Q = np.eye(4) * self.config.get('process_noise', 0.1)

        # Measurement noise covariance
        self.R = np.eye(2) * self.config.get('measurement_noise', 0.5)

        # Initial state covariance
        self.P = np.eye(4) * 1000

        # Initial state
        self.x = np.zeros((4, 1))

    def run(self, context: dict) -> dict:
        super().run(context)

        df = self.data
        if df.empty:
            self.logger.warning("Input data is empty, skipping Kalman filter.")
            return context

        predictions = []
        
        # Initialize state with the first measurement
        self.x[0] = df.iloc[0]['x_actual']
        self.x[1] = df.iloc[0]['y_actual']
        # Initial velocity can be roughly estimated or set to zero
        self.x[2] = 0 
        self.x[3] = 0

        for i, row in df.iterrows():
            # Predict
            self.x = self.F @ self.x
            self.P = self.F @ self.P @ self.F.T + self.Q

            # Store prediction
            predicted_position = self.x[:2].flatten()
            predictions.append(predicted_position)

            # Update
            z = np.array([[row['x_actual']], [row['y_actual']]])
            y = z - self.H @ self.x
            S = self.H @ self.P @ self.H.T + self.R
            K = self.P @ self.H.T @ np.linalg.inv(S)
            self.x = self.x + K @ y
            self.P = (np.eye(4) - K @ self.H) @ self.P

        # Add predictions to the dataframe
        pred_df = pd.DataFrame(predictions, columns=['predicted_x', 'predicted_y'])
        result_df = pd.concat([df, pred_df], axis=1)

        self.logger.info(f"Kalman filter applied. {len(result_df)} records processed.")

        context['data'] = result_df
        return context
