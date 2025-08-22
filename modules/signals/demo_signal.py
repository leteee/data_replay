
import pandas as pd
from modules.base_plugin import BasePlugin

class DemoSignal(BasePlugin):
    def __init__(self, config):
        super().__init__(config) # Call parent constructor to set self.config

    def run(self, context):
        # Store context and logger for property access
        super().run(context) 

        self.logger.info(f"Running DemoSignal with config: {self.config}")
        
        # Generate some sample data
        num_rows = self.config.get('num_rows', 10)
        start_value = self.config.get('start_value', 0)
        
        data = {
            'time': pd.to_datetime(pd.date_range(start='2023-01-01', periods=num_rows, freq='h')),
            'value': [start_value + i * 10 + (i % 3) * 5 for i in range(num_rows)]
        }
        df = pd.DataFrame(data)
        
        self.logger.info(f"Generated {num_rows} rows of sample data.")
        
        # Put the generated DataFrame into context['data']
        context['data'] = df

        # This plugin doesn't produce specific results to be stored in context['results']
        # but it populates the main data payload.
        return context
