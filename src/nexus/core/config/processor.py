"""
Shared configuration processing logic for plugins.
This module ensures consistent configuration handling between PipelineRunner and plugin helper.
"""

import logging
import inspect
from copy import deepcopy
from pathlib import Path
from .manager import ConfigManager, load_yaml

logger = logging.getLogger(__name__)

def process_plugin_configuration(plugin_class, plugin_config_entry, case_config, case_path, project_root=None):
    """
    Process plugin configuration in a consistent way for both pipeline execution and single plugin execution.
    
    Args:
        plugin_class: The plugin class to be instantiated
        plugin_config_entry: The configuration entry for this plugin from the case.yaml file
        case_config: The complete case configuration
        case_path: Path to the case directory
        project_root: Path to the project root (optional)
        
    Returns:
        dict: The final configuration dictionary for the plugin
    """
    # Extract the config section from the plugin config entry
    plugin_config_section = plugin_config_entry.get('config', {})
    
    # Ensure plugin_config_section is a dictionary
    if plugin_config_section is None:
        plugin_config_section = {}
    
    # Add case_path to the config section
    plugin_config_section['case_path'] = str(case_path)
    
    # If we have a project root and plugin class, use ConfigManager for full configuration processing
    if project_root and plugin_class:
        try:
            # Get the plugin's file path using inspect for robustness
            plugin_file_path = inspect.getfile(plugin_class)

            # Use ConfigManager to process the full configuration
            config_manager = ConfigManager(project_root=str(project_root))
            final_config = config_manager.get_plugin_config(
                plugin_module_path=str(plugin_file_path),
                case_config_override=plugin_config_section
            )
            
            # Add case_path to the final config
            final_config['case_path'] = str(case_path)
            
            return final_config
        except Exception as e:
            logger.warning(f"Could not use ConfigManager for plugin config processing: {e}")
            # Fall back to simple config processing
            pass
    
    # Simple config processing as fallback
    return plugin_config_section

def extract_plugin_config_entry(case_config, plugin_class):
    """
    Extract the configuration entry for a specific plugin from the case configuration.
    
    Args:
        case_config: The complete case configuration
        plugin_class: The plugin class to find configuration for
        
    Returns:
        dict: The configuration entry for the plugin, or None if not found
    """
    # Construct the full path of the plugin class for comparison
    full_plugin_class_path = f"{plugin_class.__module__}.{plugin_class.__name__}"
    
    for step in case_config.get("pipeline", []):
        # Compare with either the simple name or the full path from the config
        plugin_identifier_in_config = step.get("plugin")
        if plugin_identifier_in_config == plugin_class.__name__ or \
           plugin_identifier_in_config == full_plugin_class_path:
            logger.info(f"Found config for {plugin_class.__name__} (or {full_plugin_class_path}) in case.yaml")
            return step
    
    return None