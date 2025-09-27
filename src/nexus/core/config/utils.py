"""
Pythonic implementation for configuration-related operations.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
from functools import lru_cache

from .functional import load_yaml, create_configuration_context, get_data_sources, get_plugin_config
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


def create_config_context(project_root: Path, case_path: Path, 
                         discovered_sources: Dict, cli_args: Dict) -> Dict[str, Any]:
    """
    Create a configuration context with all necessary information.
    
    Args:
        project_root: Path to the project root
        case_path: Path to the case directory
        discovered_sources: Discovered data sources
        cli_args: Command line arguments
        
    Returns:
        Configuration context dictionary
    """
    return create_configuration_context(
        project_root=project_root,
        case_path=case_path,
        plugin_registry=PLUGIN_REGISTRY,
        discovered_data_sources=discovered_sources,
        cli_args=cli_args
    )


def get_merged_data_sources(config_context: Dict[str, Any]) -> dict:
    """
    Get the final merged data sources from configuration context.
    
    Args:
        config_context: Configuration context created by create_config_context
        
    Returns:
        Merged data sources dictionary
    """
    # Direct approach without unnecessary JSON serialization for caching
    # Simply pass parameters directly to the functional implementation
    from .functional import merge_all_data_sources
    
    return merge_all_data_sources(
        discovered_sources=config_context["discovered_data_sources"],
        global_config=config_context["global_config"],
        case_config=config_context["case_config"],
        case_path=config_context["case_path"],
        project_root=config_context["project_root"]
    )


def get_plugin_configuration(plugin_name: str, case_plugin_config: dict, 
                            config_context: Dict[str, Any]) -> dict:
    """
    Get the final plugin configuration.
    
    Args:
        plugin_name: Name of the plugin
        case_plugin_config: Case-specific plugin configuration
        config_context: Configuration context created by create_config_context
        
    Returns:
        Final plugin configuration dictionary
    """
    return get_plugin_config(
        plugin_name=plugin_name,
        case_plugin_config=case_plugin_config,
        global_config=config_context["global_config"],
        plugin_defaults_map=config_context["plugin_defaults_map"],
        plugin_registry=config_context["plugin_registry"]
    )