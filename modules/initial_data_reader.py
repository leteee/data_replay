
import pandas as pd
from modules.base_plugin import BasePlugin

class InitialDataReader(BasePlugin):
    """
    A specialized plugin to load the very first dataset into the pipeline context.
    """

    def run(self, context: dict) -> dict:
        super().run(context)

        file_path = self.config.get('path')
        if not file_path:
            raise ValueError("Configuration for InitialDataReaderPlugin must contain a 'path' key.")

        # The path from config might be relative to the project root, 
        # so we construct the full path from the case_path's parent (the project root).
        full_path = self.case_path.parent.parent / file_path

        self.logger.info(f"Loading initial data from: {full_path}")
        
        # Use the helper from BasePlugin to load the data
        df = self.load_dataframe(str(full_path))
        
        self.logger.info(f"Successfully loaded {len(df)} records.")

        context['data'] = df
        return context
