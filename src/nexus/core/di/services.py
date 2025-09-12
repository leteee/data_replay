"""
Service interfaces for the Nexus framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
import logging

from pydantic import BaseModel


class LoggerInterface(ABC):
    """Interface for logging services."""
    
    @abstractmethod
    def debug(self, msg: str, *args, **kwargs) -> None:
        pass
    
    @abstractmethod
    def info(self, msg: str, *args, **kwargs) -> None:
        pass
    
    @abstractmethod
    def warning(self, msg: str, *args, **kwargs) -> None:
        pass
    
    @abstractmethod
    def error(self, msg: str, *args, **kwargs) -> None:
        pass
    
    @abstractmethod
    def critical(self, msg: str, *args, **kwargs) -> None:
        pass


class DataHubInterface(ABC):
    """Interface for data management services."""
    
    @abstractmethod
    def add_data_sources(self, new_sources: dict) -> None:
        pass
    
    @abstractmethod
    def register(self, name: str, data: Any) -> None:
        pass
    
    @abstractmethod
    def get(self, name: str) -> Any:
        pass
    
    @abstractmethod
    def get_path(self, name: str) -> Optional[Path]:
        pass
    
    @abstractmethod
    def save(self, data: Any, path: Path, handler_args: dict | None = None) -> None:
        pass
    
    @abstractmethod
    def __contains__(self, name: str) -> bool:
        pass


class ConfigManagerInterface(ABC):
    """Interface for configuration management services."""
    
    @abstractmethod
    def get_data_sources(self) -> dict:
        pass
    
    @abstractmethod
    def get_plugin_config(self, *, plugin_name: str, case_plugin_config: dict) -> dict:
        pass


class PluginExecutorInterface(ABC):
    """Interface for plugin execution services."""
    
    @abstractmethod
    def execute(self) -> Any:
        pass


class PipelineRunnerInterface(ABC):
    """Interface for pipeline execution services."""
    
    @abstractmethod
    def run(self, plugin_name: str | None = None) -> None:
        pass