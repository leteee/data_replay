"""
Enhanced configuration management for the Nexus framework.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from collections import ChainMap
import logging

from pydantic import BaseModel, ValidationError, Field

logger = logging.getLogger(__name__)


class ConfigSourcePriority:
    """Enumeration of configuration source priorities."""
    DEFAULT = 0
    ENVIRONMENT = 1
    GLOBAL_FILE = 2
    CASE_FILE = 3
    COMMAND_LINE = 4


class EnhancedConfigManager:
    """
    Enhanced configuration manager with support for multiple configuration sources
    and environment variable overrides.
    """

    def __init__(
        self,
        project_root: Path,
        case_path: Optional[Path] = None,
        config_sources: Optional[List[str]] = None
    ):
        self.project_root = project_root
        self.case_path = case_path
        self.config_sources = config_sources or ["env", "global", "case", "cli"]
        
        # Load configurations from different sources
        self._configs = {}
        self._configs["defaults"] = self._get_default_config()
        self._configs["env"] = self._load_environment_config()
        self._configs["global"] = self._load_global_config()
        self._configs["case"] = self._load_case_config() if case_path else {}
        self._configs["cli"] = {}
        
        # Create a chain map for configuration resolution
        self._config_chain = ChainMap(
            self._configs["cli"],
            self._configs["case"],
            self._configs["global"],
            self._configs["env"],
            self._configs["defaults"]
        )
        
        logger.debug("Enhanced configuration manager initialized")

    def _get_default_config(self) -> Dict[str, Any]:
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

    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Map environment variables to configuration keys
        env_mappings = {
            "CASES_ROOT": "cases_root",
            "LOG_LEVEL": "log_level",
            "LOG_FILE": "log_file",
            "PLUGIN_ENABLE": "plugin_enable",
            "PLUGIN_MODULES": "plugin_modules",
            "PLUGIN_PATHS": "plugin_paths",
            "HANDLER_PATHS": "handler_paths"
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Parse the value based on expected type
                if config_key in ["plugin_enable"]:
                    env_config[config_key] = value.lower() in ["true", "1", "yes", "on"]
                elif config_key in ["plugin_modules", "plugin_paths", "handler_paths"]:
                    # Split comma-separated values into lists
                    env_config[config_key] = [item.strip() for item in value.split(",") if item.strip()]
                else:
                    env_config[config_key] = value
                    
        logger.debug(f"Loaded environment configuration: {env_config}")
        return env_config

    def _load_global_config(self) -> Dict[str, Any]:
        """Load global configuration from file."""
        global_config_path = self.project_root / "config" / "global.yaml"
        return self._load_yaml_config(global_config_path)

    def _load_case_config(self) -> Dict[str, Any]:
        """Load case configuration from file."""
        if not self.case_path:
            return {}
            
        case_config_path = self.case_path / "case.yaml"
        return self._load_yaml_config(case_config_path)

    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from a YAML file."""
        if not config_path.exists():
            logger.debug(f"Configuration file not found: {config_path}")
            return {}
            
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            logger.debug(f"Loaded configuration from {config_path}: {config}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            return {}

    def set_cli_config(self, cli_config: Dict[str, Any]) -> None:
        """Set command-line configuration."""
        self._configs["cli"] = cli_config or {}
        # Recreate chain map with updated CLI config
        self._config_chain = ChainMap(
            self._configs["cli"],
            self._configs["case"],
            self._configs["global"],
            self._configs["env"],
            self._configs["defaults"]
        )
        logger.debug("Updated CLI configuration")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config_chain.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        # Convert ChainMap to regular dict
        return dict(self._config_chain)

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """Get a nested configuration value."""
        current = self._config_chain
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def validate_config(self) -> bool:
        """Validate the current configuration."""
        try:
            # This would be where we'd validate against a schema
            # For now, we just check that required keys exist
            required_keys = ["cases_root", "log_level"]
            for key in required_keys:
                if key not in self._config_chain:
                    logger.warning(f"Required configuration key missing: {key}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def reload(self) -> None:
        """Reload configuration from all sources."""
        self._configs["env"] = self._load_environment_config()
        self._configs["global"] = self._load_global_config()
        self._configs["case"] = self._load_case_config() if self.case_path else {}
        
        # Recreate chain map
        self._config_chain = ChainMap(
            self._configs["cli"],
            self._configs["case"],
            self._configs["global"],
            self._configs["env"],
            self._configs["defaults"]
        )
        
        logger.debug("Configuration reloaded from all sources")


def create_enhanced_config_manager(
    project_root: Path,
    case_path: Optional[Path] = None,
    cli_args: Optional[Dict[str, Any]] = None
) -> EnhancedConfigManager:
    """
    Factory function to create an enhanced configuration manager.
    
    Args:
        project_root: The project root directory
        case_path: The case directory (optional)
        cli_args: Command-line arguments (optional)
        
    Returns:
        An EnhancedConfigManager instance
    """
    config_manager = EnhancedConfigManager(project_root, case_path)
    
    if cli_args:
        config_manager.set_cli_config(cli_args)
        
    return config_manager