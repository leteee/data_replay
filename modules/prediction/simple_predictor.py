
import pandas as pd
from modules.base_plugin import BasePlugin
from modules.prediction.kalman_filter import KalmanFilter
import numpy as np

class SimplePredictor(BasePlugin):
    def __init__(self, config):
        super().__init__(config)
        self.kalman_filter = KalmanFilter(self.config.get('kalman_params', {}))

    def run(self, data_hub):
        super().run(data_hub)
        self.logger.info("Executing Simple Predictor Plugin.")

        # Get input data from DataHub
        input_name = self.config.get("inputs", [None])[0]
        if not input_name:
            self.logger.error("No input data name defined in config for SimplePredictor.")
            return
        
        try:
            raw_data_df = data_hub.get(input_name)
            self.logger.info(f"Successfully loaded data '{input_name}' from DataHub.")
        except KeyError:
            self.logger.error(f"Input data '{input_name}' not found in DataHub.")
            return

        # Simulate the 200ms delay and predict
        delay_s = self.config.get('simulation_delay_ms', 200) / 1000.0
        predicted_positions = []

        # The column names for x and y are hardcoded for this demo plugin.
        # A more robust plugin might make these configurable.
        for index, row in raw_data_df.iterrows():
            measurement = np.array([[row['x']], [row['y']]])
            self.kalman_filter.update(measurement)
            predicted_state = self.kalman_filter.predict(dt=delay_s)

            predicted_positions.append({
                'timestamp': row['timestamp'] + delay_s,
                'predicted_x': predicted_state[0, 0],
                'predicted_y': predicted_state[2, 0],
                'x_actual': row['x'],
                'y_actual': row['y']
            })

        predicted_df = pd.DataFrame(predicted_positions)

        # Register output data with DataHub
        output_name = self.config.get("outputs", [None])[0]
        if not output_name:
            self.logger.error("No output data name defined in config for SimplePredictor.")
            return
            
        data_hub.register(output_name, predicted_df)
        self.logger.info(f"Successfully registered data '{output_name}' in DataHub.")
