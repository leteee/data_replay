import numpy as np
import pandas as pd
from modules.base_plugin import BasePlugin
from core.data_hub import DataHub

class KalmanFilter(BasePlugin):
    """
    A plugin that applies a Kalman filter to predict the next position of a vehicle.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize Kalman Filter parameters
        self.dt = self.config.get('dt', 0.02)
        self.F = np.array([[1, 0, self.dt, 0],
                             [0, 1, 0, self.dt],
                             [0, 0, 1, 0],
                             [0, 0, 0, 1]])
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        self.Q = np.eye(4) * self.config.get('process_noise', 0.1)
        self.R = np.eye(2) * self.config.get('measurement_noise', 0.5)
        self.P = np.eye(4) * 1000
        self.x = np.zeros((4, 1))

    def run(self, data_hub: DataHub):
        super().run(data_hub)

        # Get input data name from config
        input_name = self.config.get("inputs", [None])[0]
        if not input_name:
            self.logger.error("No input data name defined in config for KalmanFilter.")
            return

        # Get data from DataHub
        df = data_hub.get(input_name)
        if df.empty:
            self.logger.warning("Input data is empty, skipping Kalman filter.")
            return

        predictions = []
        
        self.x[0] = df.iloc[0]['x_actual']
        self.x[1] = df.iloc[0]['y_actual']
        self.x[2] = 0 
        self.x[3] = 0

        for i, row in df.iterrows():
            self.x = self.F @ self.x
            self.P = self.F @ self.P @ self.F.T + self.Q

            predicted_position = self.x[:2].flatten()
            predictions.append(predicted_position)

            z = np.array([[row['x_actual']], [row['y_actual']]])
            y = z - self.H @ self.x
            S = self.H @ self.P @ self.H.T + self.R
            K = self.P @ self.H.T @ np.linalg.inv(S)
            self.x = self.x + K @ y
            self.P = (np.eye(4) - K @ self.H) @ self.P

        pred_df = pd.DataFrame(predictions, columns=['predicted_x', 'predicted_y'])
        result_df = pd.concat([df, pred_df], axis=1)

        self.logger.info(f"Kalman filter applied. {len(result_df)} records processed.")

        # Register output data
        output_name = self.config.get("outputs", [None])[0]
        if not output_name:
            self.logger.error("No output data name defined in config for KalmanFilter.")
            return
            
        data_hub.register(output_name, result_df)
