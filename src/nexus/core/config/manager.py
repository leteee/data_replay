import yaml
from pathlib import Path
from copy import deepcopy
import logging
from pydantic import BaseModel

from ..plugin.spec import PluginSpec
from ..plugin.decorator import PLUGIN_REGISTRY
from ..plugin.typing import DataSource

logger = logging.getLogger(__name__)


def load_yaml(file_path):
    """Loads a YAML file safely."""
    path = Path(file_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def deep_merge(dict1, dict2):
    """Recursively merges two dictionaries, with dict2 values overwriting dict1."""
    result = deepcopy(dict1)
    for k, v in dict2.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class ConfigManager:
    """
    A stateless calculator for merging hierarchical configurations for a pipeline run.
    """

    def __init__(self, *, global_config: dict, case_config: dict,
                 plugin_registry: dict[str, PluginSpec], discovered_data_sources: dict,
                 case_path: Path, project_root: Path, cli_args: dict = None):
        self.global_config = global_config
        self.case_config = case_config
        self.cli_args = cli_args or {}
        self.discovered_data_sources = discovered_data_sources
        self.case_path = case_path
        self.project_root = project_root

        self.plugin_defaults_map = {}
        for name, spec in plugin_registry.items():
            if spec.config_model and issubclass(spec.config_model, BaseModel):
                # Get the raw dict representation (this will include DataSource objects)
                model_dict = {}
                # Filter out DataSource fields as they should not be in the config dict
                for field_name, field in spec.config_model.model_fields.items():
                    # Check if any of the metadata is a DataSource
                    has_data_source = any(isinstance(item, DataSource) for item in field.metadata)
                    if not has_data_source:
                        # For non-DataSource fields, we can get their default values
                        if field.default is not ...:
                            model_dict[field_name] = field.default
                # Now exclude unset fields to get only defaults
                self.plugin_defaults_map[name] = model_dict
            else:
                self.plugin_defaults_map[name] = {}
        logger.debug(f"Extracted default configs for {len(self.plugin_defaults_map)} plugins.")

        self._merged_data_sources = self._merge_all_data_sources()
        logger.debug("Final merged data sources calculated and resolved.")

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
        """
        final_sources = deepcopy(self.discovered_data_sources)

        for conf in self.plugin_defaults_map.values():
            final_sources = deep_merge(final_sources, conf.get('data_sources', {}))

        final_sources = deep_merge(final_sources, self.global_config.get('data_sources', {}))
        final_sources = deep_merge(final_sources, self.case_config.get('data_sources', {}))

        return self._resolve_paths_in_data_sources(final_sources)

    def get_data_sources(self) -> dict:
        """Returns the final, fully merged and resolved data_sources dictionary."""
        return self._merged_data_sources

    def get_plugin_config(self, *, plugin_name: str, case_plugin_config: dict) -> dict:
        """
        Calculates the final, merged configuration dictionary for a single plugin instance.
        The responsibility of instantiating the Pydantic model is now with the PipelineRunner.
        """
        plugin_default = self.plugin_defaults_map.get(plugin_name, {})
        final_config = deepcopy(plugin_default)

        final_config = deep_merge(final_config, self.global_config)
        final_config = deep_merge(final_config, case_plugin_config)
        final_config = deep_merge(final_config, self.cli_args)
        
        if 'data_sources' in final_config:
            del final_config['data_sources']
            
        return final_config
