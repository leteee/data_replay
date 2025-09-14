import yaml
from pathlib import Path
from copy import deepcopy
import logging
import os
from typing import Any, Dict, Type

from pydantic import BaseModel

from ..plugin.spec import PluginSpec
from ..plugin.typing import DataSource
from ..utils.cache import memory_cache

logger = logging.getLogger(__name__)


def _load_yaml(file_path: Path) -> Dict:
    """Loads a YAML file safely."""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

load_yaml = _load_yaml


def _deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Recursively merges two dictionaries, with dict2 values overwriting dict1."""
    result = deepcopy(dict1)
    for k, v in dict2.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class ConfigManager:
    """
    A stateless calculator for merging hierarchical configurations for a pipeline run.
    This class is responsible for loading configurations from all sources and merging
    them according to a defined priority.
    """

    def __init__(self, *,
                 global_config: Dict,
                 case_config: Dict,
                 cli_args: Dict,
                 plugin_registry: Dict[str, PluginSpec],
                 discovered_data_sources: Dict,
                 case_path: Path,
                 project_root: Path):
        self.global_config = global_config
        self.case_config = case_config
        self.cli_args = cli_args
        self.discovered_data_sources = discovered_data_sources
        self.case_path = case_path
        self.project_root = project_root
        self.plugin_defaults_map = self._extract_plugin_defaults(plugin_registry)

        self._merged_data_sources = self._merge_all_data_sources()
        logger.debug("Final merged data sources calculated and resolved.")

    @classmethod
    def from_sources(cls, *,
                     project_root: Path,
                     case_path: Path,
                     plugin_registry: Dict[str, PluginSpec],
                     discovered_data_sources: Dict,
                     cli_args: Dict = None) -> 'ConfigManager':
        """
        Factory method to create a ConfigManager by loading from all sources.
        Priority: CLI > Case > Global > Environment > Defaults.
        """
        cli_args = cli_args or {}

        # 1. Load configurations from files and environment
        global_config_path = project_root / "config" / "global.yaml"
        case_config_path = case_path / "case.yaml"

        global_conf = _load_yaml(global_config_path)
        case_conf = _load_yaml(case_config_path)
        env_conf = cls._load_environment_config()

        # 2. Merge global, environment, and case configs
        # Env overrides global, case overrides env.
        merged_global = _deep_merge(global_conf, env_conf)
        final_case_config = _deep_merge(merged_global, case_conf)

        return cls(
            global_config=merged_global,
            case_config=final_case_config,
            cli_args=cli_args,
            plugin_registry=plugin_registry,
            discovered_data_sources=discovered_data_sources,
            case_path=case_path,
            project_root=project_root
        )

    @staticmethod
    def _load_environment_config() -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
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
                if config_key in ["plugin_enable"]:
                    env_config[config_key] = value.lower() in ["true", "1", "yes", "on"]
                elif config_key in ["plugin_modules", "plugin_paths", "handler_paths"]:
                    env_config[config_key] = [item.strip() for item in value.split(",") if item.strip()]
                else:
                    env_config[config_key] = value
        
        if env_config:
            logger.debug(f"Loaded environment configuration: {env_config}")
        return env_config

    def _extract_plugin_defaults(self, plugin_registry: Dict[str, PluginSpec]) -> Dict:
        """Extracts default values from plugin Pydantic models."""
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

    def _resolve_paths_in_data_sources(self, sources: dict) -> dict:
        """Resolves all path strings in the data_sources dictionary."""
        resolved_sources = deepcopy(sources)
        for alias, config in resolved_sources.items():
            if "path" not in config or not isinstance(config["path"], str):
                continue

            path_str = config["path"].format(project_root=self.project_root)
            path_obj = Path(path_str)
            if not path_obj.is_absolute():
                path_obj = self.case_path / path_obj
            
            config["path"] = path_obj.resolve()
        return resolved_sources

    def _merge_all_data_sources(self) -> dict:
        """

        Merges data_sources from all layers and resolves their paths.
        Priority: Case > Global > Discovered.
        """
        final_sources = deepcopy(self.discovered_data_sources)
        final_sources = _deep_merge(final_sources, self.global_config.get('data_sources', {}))
        final_sources = _deep_merge(final_sources, self.case_config.get('data_sources', {}))

        return self._resolve_paths_in_data_sources(final_sources)

    @memory_cache(ttl=60)  # Cache for 1 minute
    def get_data_sources(self) -> dict:
        """Returns the final, fully merged and resolved data_sources dictionary."""
        return self._merged_data_sources
        
    @memory_cache(ttl=60)  # Cache for 1 minute
    def get_plugin_config(self, *, plugin_name: str, case_plugin_config: dict) -> dict:
        """
        Calculates the final, merged configuration for a single plugin.
        Priority: CLI > Case Plugin Config > Global Config > Plugin Defaults.
        """
        plugin_default = self.plugin_defaults_map.get(plugin_name, {})
        
        # Start with global config, then layer plugin-specific case config on top
        final_config = deepcopy(self.global_config)
        final_config = _deep_merge(final_config, case_plugin_config)

        # Layer defaults underneath everything
        final_config = _deep_merge(plugin_default, final_config)

        # Finally, apply CLI arguments with the highest priority
        final_config = _deep_merge(final_config, self.cli_args)
        
        # Clean up keys that are not part of the plugin's config
        if 'data_sources' in final_config:
            del final_config['data_sources']
            
        return final_config
