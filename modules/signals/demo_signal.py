
import pandas as pd
from modules.base_plugin import BasePlugin
from utils.logger import get_logger

logger = get_logger(__name__)

class DemoSignal(BasePlugin):
    def __init__(self, config):
        self.config = config

    def run(self, data_hub):
        """Generates sample signal data and adds it to the data_hub."""
        logger.info(f"Running DemoSignal with config: {self.config}")
        
        # Generate some sample data
        num_rows = self.config.get('num_rows', 10)
        start_value = self.config.get('start_value', 0)
        
        data = {
            'time': pd.to_datetime(pd.date_range(start='2023-01-01', periods=num_rows, freq='h')),
            'value': [start_value + i * 10 + (i % 3) * 5 for i in range(num_rows)]
        }
        df = pd.DataFrame(data)
        
        logger.info(f"Generated {num_rows} rows of sample data.")
        
        # Put the generated DataFrame into data_hub['data']
        data_hub['data'] = df

        # This plugin doesn't produce specific results to be stored in data_hub['results']
        # but it populates the main data payload.
        return data_hub
