'''
Handler for CSV data.
'''
import pandas as pd
from pathlib import Path
from typing import Any

from .base import DataHandler
from .decorator import handler

@handler(name="csv", extensions=[".csv"])
class CsvHandler(DataHandler):
    """Handles reading and writing CSV files."""
    def load(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(path)

    def save(self, data: Any, path: Path):
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"Data for .csv must be a DataFrame, not {type(data).__name__}")
        data.to_csv(path, index=False)
