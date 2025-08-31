'''
This module defines the DataHub, the central component for data management.
'''

import logging
from pathlib import Path
from typing import Any, Dict

from .handlers import handler_registry

logger = logging.getLogger(__name__)

class DataHub:
    """
    Manages the state of data in the pipeline.
    - Caches data in memory (lazy loading).
    - Tracks persisted data files.
    - Uses a handler system for loading and saving different file formats.
    """

    def __init__(self, case_path: Path, data_sources: Dict[str, Any] = None):
        """
        Initializes the DataHub.
        Args:
            case_path: The root path of the current case.
            data_sources: A dictionary defining the data items and their file paths.
        """
        self._case_path = case_path
        self._data: Dict[str, Any] = {}  # In-memory cache: {name: data}
        self._registry: Dict[str, Dict[str, Any]] = {}  # Maps data name to its info {path, handler}

        if data_sources:
            for name, source_info in data_sources.items():
                if "path" in source_info:
                    path = Path(source_info["path"])
                    if not path.is_absolute():
                        # Resolve relative paths from the case directory
                        path = self._case_path / path
                    
                    self._registry[name] = {
                        "path": path,
                        "handler": source_info.get("handler") # Can be None
                    }
        
        logger.info(f"DataHub initialized for case {case_path.name} with {len(self._registry)} registered sources.")

    def register(self, name: str, data: Any):
        """
        Registers a data object with the Hub and persists it if a path is registered.
        Args:
            name: The unique name of the data.
            data: The data to register (DataFrame, dict, list, etc.).
        """
        self._data[name] = data
        logger.debug(f"Data '{name}' registered in memory.")

        # Auto-persist if a path is defined in the registry
        if name in self._registry:
            source_info = self._registry[name]
            path = source_info["path"]
            handler_name = source_info.get("handler")

            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                handler = handler_registry.get_handler(path, handler_name=handler_name)
                handler.save(data, path)
                logger.info(f"Data '{name}' automatically persisted to: {path}")
            except Exception as e:
                logger.error(f"Failed to persist data '{name}' to {path}: {e}")

    def get(self, name: str) -> Any:
        """
        Retrieves data from the Hub.
        If data is not in memory, it's lazy-loaded from the registered file path.
        Args:
            name: The name of the data to retrieve.
        Returns:
            The requested data (DataFrame, dict, list, etc.).
        Raises:
            KeyError: If the data is not found in memory or in the registry.
        """
        if name in self._data:
            logger.debug(f"Getting data '{name}' from memory.")
            return self._data[name]
        
        if name in self._registry:
            source_info = self._registry[name]
            path = source_info["path"]
            handler_name = source_info.get("handler")

            logger.info(f"Lazy loading data '{name}' from: {path}...")
            
            # For directories, we don't require them to exist beforehand
            # For files, they must exist
            if not path.exists() and not self._is_directory_handler(handler_name):
                raise FileNotFoundError(f"File for data source '{name}' not found at: {path}")

            try:
                handler = handler_registry.get_handler(path, handler_name=handler_name)
                data = handler.load(path)
                self._data[name] = data  # Cache in memory after loading
                return data
            except Exception as e:
                logger.error(f"Failed to load data '{name}' from {path}: {e}")
                raise
            
        raise KeyError(f"Data '{name}' not found in DataHub.")

    def _is_directory_handler(self, handler_name: str) -> bool:
        """
        Check if the handler is a directory handler.
        
        Args:
            handler_name: Name of the handler
            
        Returns:
            True if it's a directory handler, False otherwise
        """
        return handler_name and ('DirectoryHandler' in handler_name or 'directory' in handler_name.lower())

    def get_path(self, name: str) -> Path | None:
        """
        Gets the registered file path for a data source.
        Args:
            name: The name of the data source.
        Returns:
            The Path object if it exists, otherwise None.
        """
        if name in self._registry:
            return self._registry[name]["path"]
        return None

    def __contains__(self, name: str) -> bool:
        """Allows using the `in` keyword to check if data exists."""
        return name in self._data or name in self._registry

    def summary(self) -> dict:
        """
        Returns a summary of the DataHub's current state.
        """
        return {
            "in_memory_data": list(self._data.keys()),
            "registered_files": {
                name: {
                    "path": str(info["path"]),
                    "handler": info.get("handler", "default (by extension)")
                } for name, info in self._registry.items()
            }
        }
