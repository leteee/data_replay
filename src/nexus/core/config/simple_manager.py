"""
Simple, Pythonic configuration management for the Nexus framework.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Simple configuration manager with support for multiple configuration sources.
    
    Configuration precedence (highest to lowest):
    1. Environment variables
    2. Case configuration file
    3. Global configuration file
    4. Default values
    """

    def __init__(self, project_root: Path, case_path: Optional[Path] = None):
        self.project_root = project_root
        self.case_path = case_path
        
        # Load configurations with proper precedence
        self._defaults = self._get_defaults()
        self._global_config = self._load_global_config()
        self._case_config = self._load_case_config() if case_path else {}
        self._env_config = self._load_environment_config()
        
        logger.debug("Configuration manager initialized")

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "cases_root": "./cases",
            "log_level": "INFO",
            "log_file": "./logs/app.log",
            "plugin_enable": True,
            "plugin_modules": [],
            "plugin_paths": [],
            "handler_paths": []
        }

    def _load_global_config(self) -> Dict[str, Any]:
        """Load global configuration from file."""
        config_path = self.project_root / "config" / "global.yaml"
        return self._load_yaml_config(config_path)

    def _load_case_config(self) -> Dict[str, Any]:
        """Load case configuration from file."""
        if not self.case_path:
            return {}
        config_path = self.case_path / "case.yaml"
        return self._load_yaml_config(config_path)

    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Simple mapping of environment variables to config keys
        mappings = {
            "CASES_ROOT": "cases_root",
            "LOG_LEVEL": "log_level",
            "LOG_FILE": "log_file",
            "PLUGIN_ENABLE": "plugin_enable",
            "PLUGIN_MODULES": "plugin_modules",
            "PLUGIN_PATHS": "plugin_paths",
            "HANDLER_PATHS": "handler_paths"
        }
        
        for env_var, config_key in mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                env_config[config_key] = self._parse_env_value(value, config_key)
                
        return env_config

    def _parse_env_value(self, value: str, config_key: str) -> Any:
        """Parse environment variable value based on expected type."""
        if config_key in ["plugin_enable"]:
            return value.lower() in ["true", "1", "yes", "on"]
        elif config_key in ["plugin_modules", "plugin_paths", "handler_paths"]:
            # Split comma-separated values into lists
            return [item.strip() for item in value.split(",") if item.strip()]
        else:
            return value

    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from a YAML file."""
        if not config_path.exists():
            return {}
            
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with proper precedence.
        
        Precedence order (highest to lowest):
        1. Environment variables
        2. Case configuration
        3. Global configuration
        4. Default values
        5. Provided default parameter
        """
        # Check environment variables first
        if key in self._env_config:
            return self._env_config[key]
            
        # Then case configuration
        if key in self._case_config:
            return self._case_config[key]
            
        # Then global configuration
        if key in self._global_config:
            return self._global_config[key]
            
        # Then defaults
        if key in self._defaults:
            return self._defaults[key]
            
        # Finally, return the provided default
        return default

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values merged with proper precedence."""
        # Start with defaults
        result = dict(self._defaults)
        
        # Merge global config
        result.update(self._global_config)
        
        # Merge case config
        result.update(self._case_config)
        
        # Merge environment config (highest precedence)
        result.update(self._env_config)
        
        return result

    def reload(self) -> None:
        """Reload configuration from all sources."""
        self._global_config = self._load_global_config()
        self._case_config = self._load_case_config() if self.case_path else {}
        self._env_config = self._load_environment_config()
        logger.debug("Configuration reloaded from all sources")


def create_config_manager(
    project_root: Path,
    case_path: Optional[Path] = None
) -> ConfigManager:
    """
    Factory function to create a configuration manager.
    
    Args:
        project_root: The project root directory
        case_path: The case directory (optional)
        
    Returns:
        A ConfigManager instance
    """
    return ConfigManager(project_root, case_path)