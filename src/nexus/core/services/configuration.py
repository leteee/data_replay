"""
Service for handling configuration-related operations.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from ..config.manager import ConfigManager, load_yaml
from ..plugin.decorator import PLUGIN_REGISTRY
from ..utils.cache import memory_cache, get_file_cache
from ..utils.cache import memory_cache


class ConfigurationService:
    """
    Service for handling configuration-related operations.
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        
    @memory_cache(ttl=60)  # Cache for 1 minute
    def load_case_config(self, case_path: Path) -> dict:
        """
        Load the case configuration from the case directory.
        
        Args:
            case_path: Path to the case directory
            
        Returns:
            The loaded case configuration
        """
        raw_case_config = load_yaml(case_path / "case.yaml")
        self.logger.debug(f"case_config: {raw_case_config}")
        return raw_case_config
        
    def filter_pipeline_steps(self, pipeline_steps: List[Dict[str, Any]], 
                            plugin_name: str = None) -> List[Dict[str, Any]]:
        """
        Filter pipeline steps based on plugin name if specified.
        
        Args:
            pipeline_steps: List of pipeline steps
            plugin_name: Optional plugin name to filter by
            
        Returns:
            Filtered list of pipeline steps
        """
        if plugin_name:
            pipeline_steps = [step for step in pipeline_steps if step.get("plugin") == plugin_name]
            
        return pipeline_steps
        
    def create_config_manager(self, project_root: Path, case_path: Path, 
                            discovered_sources: Dict, cli_args: Dict) -> ConfigManager:
        """
        Create a ConfigManager instance.
        
        Args:
            project_root: Path to the project root
            case_path: Path to the case directory
            discovered_sources: Discovered data sources
            cli_args: Command line arguments
            
        Returns:
            ConfigManager instance
        """
        return ConfigManager.from_sources(
            project_root=project_root,
            case_path=case_path,
            plugin_registry=PLUGIN_REGISTRY,
            discovered_data_sources=discovered_sources,
            cli_args=cli_args
        )