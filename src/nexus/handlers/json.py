'''
Handler for JSON data.
'''
import json
from pathlib import Path
from typing import Any, Dict, List, Union

from .base import DataHandler
from .decorator import handler

@handler(name="json", extensions=[".json"])
class JsonHandler(DataHandler):
    """Handles reading and writing JSON files."""
    file_extension = ".json"
    produced_type = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
    
    def load(self, path: Path) -> Any:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self, data: Any, path: Path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
