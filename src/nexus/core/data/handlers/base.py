'''
This module defines the base interface for data handlers.
'''

import abc
from pathlib import Path
from typing import Any, Type

class DataHandler(abc.ABC):
    """
    Abstract base class for data handlers.
    Defines the interface for loading and saving data.
    """
    file_extension: str | None = None
    handles_directories: bool = False
    produced_type: Type | None = None

    @abc.abstractmethod
    def load(self, path: Path) -> Any:
        """Loads data from the given path."""
        pass

    @abc.abstractmethod
    def save(self, data: Any, path: Path):
        """Saves data to the given path, overwriting if it exists."""
        pass
