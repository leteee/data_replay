"""
Adapters for existing framework classes to implement service interfaces.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .services import LoggerInterface, DataHubInterface, ConfigManagerInterface
from ..data.hub import DataHub
from ..config.manager import ConfigManager


class LoggerAdapter(LoggerInterface):
    """Adapter for Python's logging.Logger to implement LoggerInterface."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        return self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        return self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        return self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        return self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        return self._logger.critical(msg, *args, **kwargs)


class DataHubAdapter(DataHubInterface):
    """Adapter for DataHub to implement DataHubInterface."""
    
    def __init__(self, data_hub: DataHub):
        self._data_hub = data_hub
    
    def add_data_sources(self, new_sources: dict) -> None:
        return self._data_hub.add_data_sources(new_sources)
    
    def register(self, name: str, data: Any) -> None:
        return self._data_hub.register(name, data)
    
    def get(self, name: str) -> Any:
        return self._data_hub.get(name)
    
    def get_path(self, name: str) -> Optional[Path]:
        return self._data_hub.get_path(name)
    
    def save(self, data: Any, path: Path, handler_args: dict | None = None) -> None:
        return self._data_hub.save(data, path, handler_args)
    
    def __contains__(self, name: str) -> bool:
        return name in self._data_hub


class ConfigManagerAdapter(ConfigManagerInterface):
    """Adapter for ConfigManager to implement ConfigManagerInterface."""
    
    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
    
    def get_data_sources(self) -> dict:
        return self._config_manager.get_data_sources()
    
    def get_plugin_config(self, *, plugin_name: str, case_plugin_config: dict) -> dict:
        return self._config_manager.get_plugin_config(
            plugin_name=plugin_name,
            case_plugin_config=case_plugin_config
        )