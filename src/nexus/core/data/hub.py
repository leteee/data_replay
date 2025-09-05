'''
This module defines the DataHub, the central component for data management.
'''

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from logging import Logger

from pydantic import BaseModel

from .handlers import handler_registry

logger = logging.getLogger(__name__)


class DataSource(BaseModel):
    """Represents a registered data source that can be loaded or saved."""
    path: Path
    handler: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class DataHub:
    """
    Manages the state of data in the pipeline.
    - Caches data in memory (lazy loading).
    - Tracks persisted data files.
    - Uses a handler system for loading and saving different file formats.
    """

    def __init__(self, case_path: Path, data_sources: Dict[str, Any] = None, logger: Logger = None):
        """
        Initializes the DataHub.
        Args:
            case_path: The root path of the current case.
            data_sources: A dictionary defining the data items and their file paths.
        """
        self._case_path = case_path
        self._data: Dict[str, Any] = {}  # In-memory cache: {name: data}
        self._registry: Dict[str, DataSource] = {}  # Maps data name to its DataSource info
        self.logger = logger if logger else logging.getLogger(__name__)

        if data_sources:
            for name, source_info in data_sources.items():
                if "path" in source_info:
                    path = Path(source_info["path"])
                    if not path.is_absolute():
                        # Resolve relative paths from the case directory
                        path = self._case_path / path
                    
                    self._registry[name] = DataSource(
                        path=path,
                        handler=source_info.get("handler")
                    )
        
            self.logger.info(f"DataHub initialized for case {case_path.name} with {len(self._registry)} registered sources.")

    def add_data_sources(self, new_sources: dict):
        """Merges new data source definitions into the DataHub's registry."""
        for name, source_info in new_sources.items():
            # Always add/update the source. The priority is handled by the order of calls.
            if "path" in source_info:
                path = Path(source_info["path"])
                if not path.is_absolute():
                    path = self._case_path / path
                
                # Store a DataSource object instead of a dict
                self._registry[name] = DataSource(
                    path=path,
                    handler=source_info.get("handler")
                )
                self.logger.debug(f"Added/Updated data source: '{name}' -> {path}")

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
            source = self._registry[name] # source is now a DataSource object
            path = source.path
            handler_name = source.handler

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
            source = self._registry[name] # source is now a DataSource object
            path = source.path
            handler_name = source.handler

            logger.info(f"Lazy loading data '{name}' from: {path}...")
            
            try:
                handler = handler_registry.get_handler(path, handler_name=handler_name)

                # For directories, we don't require them to exist beforehand.
                # For files, they must exist.
                if not path.exists() and not handler.handles_directories:
                    raise FileNotFoundError(f"File for data source '{name}' not found at: {path}")

                data = handler.load(path)
                self._data[name] = data  # Cache in memory after loading
                return data
            except Exception as e:
                logger.error(f"Failed to load data '{name}' from {path}: {e}")
                raise
            
        raise KeyError(f"Data '{name}' not found in DataHub.")

    def get_path(self, name: str) -> Path | None:
        """
        Gets the registered file path for a data source.
        If the data source is a directory, ensures the directory exists by calling its handler's load method.
        Args:
            name: The name of the data source.
        Returns:
            The Path object if it exists, otherwise None.
        """
        if name in self._registry:
            source = self._registry[name]
            path = source.path
            handler_name = source.handler

            # If it's a directory handler, call its load method to ensure existence
            try:
                handler = handler_registry.get_handler(path, handler_name=handler_name)
                if handler.handles_directories:
                    self.logger.debug(f"Ensuring directory exists for '{name}' at {path} via handler.load().")
                    handler.load(path) # This will create the directory if it doesn't exist
            except Exception as e:
                self.logger.error(f"Error ensuring directory existence for '{name}' at {path}: {e}")
                # Decide whether to re-raise or just log. For now, just log and proceed.
                # The plugin will likely fail later if the directory isn't there.
                pass # Allow the path to be returned even if directory creation failed.

            return path
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
                    "path": str(source.path),
                    "handler": source.handler or "default (by extension)"
                } for name, source in self._registry.items()
            }
        }
