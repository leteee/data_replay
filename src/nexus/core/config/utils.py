"""
Pythonic implementation for configuration-related operations.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
from functools import lru_cache

from ..config.manager import ConfigManager, load_yaml
from ..plugin.decorator import PLUGIN_REGISTRY


@lru_cache(maxsize=32)
def _load_case_config_cached(case_path_str: str) -> dict:
    """
    Cached loader for case configuration.
    
    Args:
        case_path_str: String representation of the case path (for caching)
        
    Returns:
        The loaded case configuration
    """
    case_path = Path(case_path_str)
    return load_yaml(case_path / "case.yaml")


def load_case_config(case_path: Path) -> dict:
    """
    Load the case configuration from the case directory.
    
    Args:
        case_path: Path to the case directory
        
    Returns:
        The loaded case configuration
    """
    # Convert path to string for caching purposes
    return _load_case_config_cached(str(case_path))


def filter_pipeline_steps(pipeline_steps: List[Dict[str, Any]], 
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


def create_config_manager(project_root: Path, case_path: Path, 
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