import pandas as pd
from abc import ABC, abstractmethod
import logging
from pathlib import Path
from core.data_hub import DataHub

class BasePlugin(ABC):
    """
    The universal abstract base class for all plugins.
    It defines the common interface for plugins and provides helper methods
    to access configuration and logging.
    """
    def __init__(self, config: dict):
        """
        The configuration for the plugin is passed during initialization.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def case_path(self) -> Path:
        """
        Convenience property to access the root path of the current case.
        """
        path_str = self.config.get('case_path')
        if not path_str:
            self.logger.warning(f"case_path not found in config for {self.__class__.__name__}. Returning current working directory.")
            return Path.cwd()
        return Path(path_str)

    @abstractmethod
    def run(self, data_hub: DataHub):
        """
        This is the core processing logic that every plugin must implement.
        It receives the DataHub instance, which it can use to get and register data.

        Args:
            data_hub: The central DataHub instance for the pipeline run.
        """
        self.logger.info(f"Executing plugin: {self.__class__.__name__}...")
        pass
