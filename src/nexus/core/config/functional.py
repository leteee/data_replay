"""
Functional implementation for configuration-related operations.
This replaces the ConfigManager class with pure functions.
"""

import yaml
from pathlib import Path
from copy import deepcopy
import logging
import os
from typing import Any, Dict, Type, Optional
from functools import lru_cache

from pydantic import BaseModel
from ..plugin.spec import PluginSpec
from ..plugin.typing import DataSource
from ..plugin.decorator import PLUGIN_REGISTRY

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def _load_yaml_cached(file_path_str: str) -> Dict:
    """
    Cached loader for YAML files.
    
    Args:
        file_path_str: String representation of file path (for caching)
        
    Returns:
        Loaded YAML content
    """
    file_path = Path(file_path_str)
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_yaml(file_path: Path) -> Dict:
    """
    Load a YAML file safely.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Loaded YAML content as dictionary
    """
    return _load_yaml_cached(str(file_path))


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    Recursively merge two dictionaries, with dict2 values overwriting dict1.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (higher priority)
        
    Returns:
        Merged dictionary
    """
    result = deepcopy(dict1)
    for k, v in dict2.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_environment_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Returns:
        Dictionary with environment configuration
    """
    env_config = {}
    env_mappings = {
        "CASES_ROOT": "cases_root",
        "LOG_LEVEL": "log_level",
        "LOG_FILE": "log_file",
        "PLUGIN_ENABLE": "plugin_enable",
        "PLUGIN_MODULES": "plugin_modules",
        "PLUGIN_PATHS": "plugin_paths",
        "HANDLER_MODULES": "handler_modules",
        "HANDLER_PATHS": "handler_paths"
    }

    for env_var, config_key in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            if config_key in ["plugin_enable"]:
                env_config[config_key] = value.lower() in ["true", "1", "yes", "on"]
            elif config_key in ["plugin_modules", "plugin_paths", "handler_modules", "handler_paths"]:
                env_config[config_key] = [item.strip() for item in value.split(",") if item.strip()]
            else:
                env_config[config_key] = value
    
    if env_config:
        logger.debug(f"Loaded environment configuration: {env_config}")
    return env_config


def extract_plugin_defaults(plugin_registry: Dict[str, PluginSpec]) -> Dict:
    """
    Extract default values from plugin Pydantic models.
    
    Args:
        plugin_registry: Dictionary of plugin specifications
        
    Returns:
        Dictionary mapping plugin names to their default configurations
    """
    defaults_map = {}
    for name, spec in plugin_registry.items():
        if spec.config_model and issubclass(spec.config_model, BaseModel):
            model_dict = {}
            for field_name, field in spec.config_model.model_fields.items():
                has_data_source = any(isinstance(item, DataSource) for item in field.metadata)
                if not has_data_source and field.default is not ...:
                    model_dict[field_name] = field.default
            defaults_map[name] = model_dict
        else:
            defaults_map[name] = {}
    logger.debug(f"Extracted default configs for {len(defaults_map)} plugins.")
    return defaults_map


def resolve_paths_in_data_sources(sources: dict, case_path: Path, project_root: Path) -> dict:
    """
    Resolve all path strings in the data_sources dictionary.
    
    Args:
        sources: Data sources dictionary
        case_path: Path to the case directory
        project_root: Path to the project root
        
    Returns:
        Dictionary with resolved paths
    """
    resolved_sources = deepcopy(sources)
    for alias, config in resolved_sources.items():
        if "path" not in config or not isinstance(config["path"], str):
            continue

        path_str = config["path"].format(project_root=project_root)
        path_obj = Path(path_str)
        if not path_obj.is_absolute():
            path_obj = case_path / path_obj
        
        config["path"] = path_obj.resolve()
    return resolved_sources


def merge_all_data_sources(discovered_sources: dict, global_config: dict, 
                          case_config: dict, case_path: Path, project_root: Path) -> dict:
    """
    Merge data_sources from all layers and resolve their paths.
    Priority: Case > Global > Discovered.
    
    Args:
        discovered_sources: Discovered data sources
        global_config: Global configuration
        case_config: Case configuration
        case_path: Path to the case directory
        project_root: Path to the project root
        
    Returns:
        Merged data sources dictionary with resolved paths
    """
    final_sources = deepcopy(discovered_sources)
    final_sources = deep_merge(final_sources, global_config.get('data_sources', {}))
    final_sources = deep_merge(final_sources, case_config.get('data_sources', {}))

    return resolve_paths_in_data_sources(final_sources, case_path, project_root)


@lru_cache(maxsize=128)
def get_data_sources(discovered_sources_hash: str, global_config_hash: str, 
                    case_config_hash: str, case_path_str: str, project_root_str: str) -> dict:
    """
    Calculate and return the final, fully merged and resolved data_sources dictionary.
    This is a cached version for performance.
    
    Args:
        discovered_sources_hash: Hash of discovered sources (as string)
        global_config_hash: Hash of global config (as string)
        case_config_hash: Hash of case config (as string)
        case_path_str: String representation of case path (for hashing)
        project_root_str: String representation of project root (for hashing)
        
    Returns:
        Final merged data sources
    """
    # Reconstruct from hashes
    import json
    discovered_sources = json.loads(discovered_sources_hash)
    global_config = json.loads(global_config_hash)
    case_config = json.loads(case_config_hash)
    case_path = Path(case_path_str)
    project_root = Path(project_root_str)
    
    # Perform the actual merge
    return merge_all_data_sources(discovered_sources, global_config, case_config, case_path, project_root)


def get_plugin_config(plugin_name: str, case_plugin_config: dict, global_config: dict, 
                     plugin_defaults_map: dict, plugin_registry: Dict[str, PluginSpec]) -> dict:
    """
    Calculate the final, merged configuration for a single plugin.
    Priority: CLI > Case Plugin Config > Global Config > Plugin Defaults.
    
    Args:
        plugin_name: Name of the plugin
        case_plugin_config: Case-specific plugin configuration
        global_config: Global configuration
        plugin_defaults_map: Map of plugin defaults
        plugin_registry: Plugin registry
        
    Returns:
        Final plugin configuration as dictionary
    """
    plugin_spec = None
    # Find the plugin spec to get its config model
    for name, spec in plugin_registry.items():
        if name == plugin_name:
            plugin_spec = spec
            break
    
    # If no config model, return an empty dict
    if not plugin_spec or not plugin_spec.config_model or not issubclass(plugin_spec.config_model, BaseModel):
        return {}
    
    # Get plugin-specific defaults
    plugin_default = plugin_defaults_map.get(plugin_name, {})
    
    # Start with global config, then layer plugin-specific case config on top
    merged_config = deepcopy(global_config)
    merged_config = deep_merge(merged_config, case_plugin_config)

    # Layer defaults underneath everything
    merged_config = deep_merge(plugin_default, merged_config)

    # Finally, apply CLI arguments with the highest priority
    # Note: CLI args would be passed separately in the calling context
    
    # Create a config dict with only the fields that are defined in the plugin's config model
    plugin_config_dict = {}
    
    # Add fields from the plugin's config model
    for field_name, field_info in plugin_spec.config_model.model_fields.items():
        # Check if this field has a DataSource annotation (these are handled separately)
        has_data_source = any(isinstance(item, DataSource) for item in field_info.metadata)
        if has_data_source:
            continue  # Skip DataSource fields, they will be injected from DataHub
        
        # Get the value from the merged config, fallback to field default if not present
        if field_name in merged_config:
            plugin_config_dict[field_name] = merged_config[field_name]
        elif field_info.default is not ...:  # not Required
            plugin_config_dict[field_name] = field_info.default
    
    return plugin_config_dict


def create_configuration_context(project_root: Path, case_path: Path, plugin_registry: Dict[str, PluginSpec],
                                 discovered_data_sources: Dict, cli_args: Dict = None) -> Dict[str, Any]:
    """
    Create a configuration context with all necessary information.
    
    Args:
        project_root: Path to the project root
        case_path: Path to the case directory
        plugin_registry: Plugin registry
        discovered_data_sources: Discovered data sources
        cli_args: Command line arguments
        
    Returns:
        Dictionary with configuration context
    """
    cli_args = cli_args or {}

    # Load configurations from files and environment
    global_config_path = project_root / "config" / "global.yaml"
    case_config_path = case_path / "case.yaml"

    global_conf = load_yaml(global_config_path)
    case_conf = load_yaml(case_config_path)
    env_conf = load_environment_config()

    # Merge global, environment, and case configs
    # Env overrides global, case overrides env.
    merged_global = deep_merge(global_conf, env_conf)
    final_case_config = deep_merge(merged_global, case_conf)
    
    # Extract plugin defaults
    plugin_defaults_map = extract_plugin_defaults(plugin_registry)

    return {
        "project_root": project_root,
        "case_path": case_path,
        "global_config": merged_global,
        "case_config": final_case_config,
        "cli_args": cli_args,
        "plugin_registry": plugin_registry,
        "discovered_data_sources": discovered_data_sources,
        "plugin_defaults_map": plugin_defaults_map
    }