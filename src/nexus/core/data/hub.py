'''
This module defines the DataHub, the central component for data management.
'''

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from logging import Logger

from pydantic import BaseModel

from .handlers import handler_registry, initialize_handler_discovery
from ..exceptions import NexusError
from ..exception_handler import handle_exception

logger = logging.getLogger(__name__)


class DataSource(BaseModel):
    """Represents a registered data source that can be loaded or saved."""
    path: Path
    handler_config: Dict[str, Any]

    class Config:
        arbitrary_types_allowed = True


class DataHub:
    """
    Manages the state of data in the pipeline.
    """

    def __init__(self, case_path: Path, logger: Logger = None, context=None):
        self._case_path = case_path
        self._data: Dict[str, Any] = {}
        self._registry: Dict[str, DataSource] = {}
        self.logger = logger if logger else logging.getLogger(__name__)
        
        # Initialize handler discovery with context
        initialize_handler_discovery(context)

    def add_data_sources(self, new_sources: dict):
        """Merges new data source definitions into the DataHub's registry."""
        for name, source_info in new_sources.items():
            if "path" not in source_info:
                continue

            path = Path(source_info["path"])
            if not path.is_absolute():
                path = self._case_path / path

            # Handle handler_args from PipelineRunner
            handler_conf = source_info.get("handler_args", {})
            if isinstance(handler_conf, str):
                handler_conf = {"name": handler_conf}
            
            # Set default for must_exist if not provided
            handler_conf.setdefault("must_exist", True)

            self._registry[name] = DataSource(
                path=path,
                handler_config=handler_conf
            )
            self.logger.debug(f"Added/Updated data source: '{name}' -> {path}")

    def _get_handler_instance(self, source: DataSource):
        """Instantiates a handler based on the source configuration."""
        handler_name = source.handler_config.get("name")
        self.logger.debug(f"Getting handler for path: {source.path}, handler_name: {handler_name}, handler_config: {source.handler_config}")
        # handler_params are not passed to get_handler, they are used for handler initialization
        return handler_registry(source.path, handler_name=handler_name)

    def register(self, name: str, data: Any):
        """
        Registers a data object with the Hub and persists it if a path is registered.
        """
        self._data[name] = data
        logger.debug(f"Data '{name}' registered in memory.")

        if name in self._registry:
            source = self._registry[name]
            path = source.path
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                handler = self._get_handler_instance(source)
                handler.save(data, path)
                logger.info(f"Data '{name}' automatically persisted to: {path}")
            except Exception as e:
                logger.error(f"Failed to persist data '{name}' to {path}: {e}")

    def get(self, name: str) -> Any:
        """
        Retrieves data from the Hub, lazy-loading if necessary.
        """
        if name in self._data:
            logger.debug(f"Getting data '{name}' from memory.")
            return self._data[name]
        
        if name in self._registry:
            source = self._registry[name]
            path = source.path
            must_exist = source.handler_config.get("must_exist", True)

            logger.info(f"Lazy loading data '{name}' from: {path}...")
            
            try:
                handler = self._get_handler_instance(source)
                # For directory handlers, we don't check must_exist before calling load
                # because the handler itself will create the directory if needed
                if must_exist and not path.exists() and not getattr(handler, 'handles_directories', False):
                    raise FileNotFoundError(f"Required file for data source '{name}' not found at: {path}")

                data = handler.load(path)
                self._data[name] = data
                return data
            except Exception as e:
                return self._handle_data_error(e, "load", name, path, must_exist)
                
        raise KeyError(f"Data '{name}' not found in DataHub.")
        
    def save(self, data: Any, path: Path, handler_args: dict | None = None):
        """
        Saves data to a specified path using the appropriate handler.

        Args:
            data: The data object to save.
            path: The destination path (absolute).
            handler_args: Optional arguments for the handler, including its name.
        """
        handler_args = handler_args or {}
        handler_name = handler_args.get("name")

        self.logger.debug(f"Attempting to save data to {path} using handler '{handler_name or 'auto'}'.")
        
        try:
            handler = handler_registry(path, handler_name=handler_name)
            path.parent.mkdir(parents=True, exist_ok=True)
            # We might need to pass specific save options from handler_args to the save method
            # For now, we assume the handler's save method has a simple signature.
            handler.save(data, path)
            self.logger.info(f"Data successfully saved to: {path}")
        except Exception as e:
            return self._handle_data_error(e, "save", None, path, None, handler_name)
            
    def _handle_data_error(self, e: Exception, operation: str, name: str = None, 
                          path: Path = None, must_exist: bool = None, 
                          handler_name: str = None) -> None:
        """
        Handle data operation errors consistently.
        
        Args:
            e: The exception that occurred
            operation: The operation that failed ("load" or "save")
            name: The data source name (for load operations)
            path: The path being accessed
            must_exist: The must_exist flag (for load operations)
            handler_name: The handler name (for save operations)
        """
        error_context = {
            "operation": operation,
            "path": str(path) if path else "Unknown"
        }
        
        if name:
            error_context["data_source_name"] = name
        if must_exist is not None:
            error_context["must_exist"] = must_exist
        if handler_name:
            error_context["handler_name"] = handler_name
            
        exc = NexusError(
            f"Failed to {operation} data{' ' + name if name else ''} at {path}: {e}",
            context=error_context,
            cause=e
        )
        handle_exception(exc, error_context)
        raise exc

    def __contains__(self, name: str) -> bool:
        return name in self._data or name in self._registry

    def summary(self) -> dict:
        return {
            "in_memory_data": list(self._data.keys()),
            "registered_files": {
                name: {
                    "path": str(source.path),
                    "handler": source.handler_config
                } for name, source in self._registry.items()
            }
        }
