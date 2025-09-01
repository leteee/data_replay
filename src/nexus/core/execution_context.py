import logging
from pathlib import Path

from .config_manager import ConfigManager
from .data_hub import DataHub
from .logger import add_case_log_handler

logger = logging.getLogger(__name__)

class ExecutionContext:
    """
    Holds the complete environment for a pipeline or plugin run.
    
    This class is responsible for initializing all necessary managers and
    configurations based on the project and case paths.
    """
    def __init__(self, project_root: str, case_path: str):
        self.project_root = Path(project_root).resolve()
        self.case_path = Path(case_path).resolve()

        if not self.case_path.is_dir():
            raise FileNotFoundError(f"Case path not found or is not a directory: {self.case_path}")

        # Set up case-specific logging as soon as the context is created.
        add_case_log_handler(case_name=self.case_path.name)

        logger.debug(f"Initializing ExecutionContext for case: {self.case_path.name}")

        # 1. Initialize ConfigManager and load configs
        self.config_manager = ConfigManager(project_root=str(self.project_root))
        self.global_config = self.config_manager.global_config
        self.case_config = self.config_manager.load_case_config(str(self.case_path))

        # 2. Initialize DataHub
        # Data sources are merged: case config overrides global config
        data_sources = self.global_config.get("data_sources", {})
        data_sources.update(self.case_config.get("data_sources", {}))
        self.data_hub = DataHub(case_path=self.case_path, data_sources=data_sources)

        logger.debug("ExecutionContext initialized successfully.")