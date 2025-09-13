"""
Configuration management module for the Nexus framework.
"""

from .manager import ConfigManager, load_yaml, deep_merge
from .enhanced_manager import EnhancedConfigManager, create_enhanced_config_manager
from .processor import process_plugin_configuration, extract_plugin_config_entry

__all__ = [
    "ConfigManager",
    "load_yaml",
    "deep_merge",
    "EnhancedConfigManager",
    "create_enhanced_config_manager",
    "process_plugin_configuration",
    "extract_plugin_config_entry"
]