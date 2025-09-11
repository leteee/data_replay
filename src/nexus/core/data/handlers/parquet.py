'''
Handler for Parquet data.
'''
import pandas as pd
from pathlib import Path
from typing import Any

from .base import DataHandler
from .decorator import handler

@handler(name="parquet", extensions=[".parquet"])
class ParquetHandler(DataHandler):
    """Handles reading and writing Parquet files."""
    file_extension = ".parquet"
    produced_type = pd.DataFrame
    
    def load(self, path: Path) -> pd.DataFrame:
        return pd.read_parquet(path)

    def save(self, data: Any, path: Path):
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"Data for .parquet must be a DataFrame, not {type(data).__name__}")
        data.to_parquet(path)
