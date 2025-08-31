'''
Handler for JSON data.
'''
import json
from pathlib import Path
from typing import Any

from .base import DataHandler

class JsonHandler(DataHandler):
    """Handles reading and writing JSON files."""
    file_extension = ".json"
    def load(self, path: Path) -> Any:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self, data: Any, path: Path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
