
from dataclasses import dataclass
from typing import Callable, Any, Type
from pydantic import BaseModel

@dataclass
class PluginSpec:
    """
    A dataclass to hold all metadata for a discovered plugin.
    """
    name: str
    func: Callable
    output_key: str | None
    config_model: Type[BaseModel] | None
