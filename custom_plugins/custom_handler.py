"""
Custom handler for demonstration purposes.
"""
import pandas as pd
from pathlib import Path
from typing import Any

from nexus.core.data.handlers.base import DataHandler
from nexus.core.data.handlers.decorator import handler


@handler(name="custom", extensions=[".custom"])
class CustomHandler(DataHandler):
    """Handles reading and writing custom data format."""
    produced_type = pd.DataFrame
    
    def load(self, path: Path) -> pd.DataFrame:
        """Load custom format data."""
        # For demonstration, we'll just create a simple DataFrame
        return pd.DataFrame({'id': [1, 2, 3], 'value': [10, 20, 30]})
    
    def save(self, data: Any, path: Path):
        """Save data in custom format."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"Data for .custom must be a DataFrame, not {type(data).__name__}")
        
        # For demonstration, we'll just save a simple representation
        with open(path, 'w') as f:
            f.write("Custom Data Format\n")
            f.write(data.to_string())