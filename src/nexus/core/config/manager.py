import yaml
from pathlib import Path
from copy import deepcopy
import logging
from pydantic import BaseModel

from ..plugin.spec import PluginSpec
from ..plugin.decorator import PLUGIN_REGISTRY # <-- Import added

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
    It is instantiated by the PipelineRunner with all necessary configuration sources.
    """

    def __init__(self, *, global_config: dict, case_config: dict,
                 plugin_registry: dict[str, PluginSpec], cli_args: dict = None):
        """
        Initializes the ConfigManager for a single run.

        Args:
            global_config: The loaded global.yaml config.
            case_config: The loaded case.yaml config for the current run.
            plugin_registry: The registry of all discovered plugins.
            cli_args: Config overrides from the command line.
        """
        self.global_config = global_config
        self.case_config = case_config
        self.cli_args = cli_args or {}

        # 1. Extract default configurations from the plugin registry
        self.plugin_defaults_map = {}
        for name, spec in plugin_registry.items():
            if spec.config_model and issubclass(spec.config_model, BaseModel):
                # Instantiate the Pydantic model to get default values
                self.plugin_defaults_map[name] = spec.config_model().dict()
            else:
                self.plugin_defaults_map[name] = {}
        logger.debug(f"Extracted default configs for {len(self.plugin_defaults_map)} plugins.")

        # 2. Immediately calculate the final merged data sources
        self._merged_data_sources = self._merge_all_data_sources()
        logger.debug("Final merged data sources calculated.")

    def _merge_all_data_sources(self) -> dict:
        """
        Merges data_sources from all layers with the correct priority.
        Priority Order (lowest to highest): Plugin Defaults -> Global -> Case
        """
        final_sources = {}

        # 1. Merge all plugin default data_sources
        for conf in self.plugin_defaults_map.values():
            final_sources = deep_merge(final_sources, conf.get('data_sources', {}))

        # 2. Merge global config on top
        final_sources = deep_merge(final_sources, self.global_config.get('data_sources', {}))

        # 3. Merge case config on top
        final_sources = deep_merge(final_sources, self.case_config.get('data_sources', {}))

        return final_sources

    def get_data_sources(self) -> dict:
        """Returns the final, fully merged data_sources dictionary."""
        return self._merged_data_sources

    def get_plugin_config(self, *, plugin_name: str, case_plugin_config: dict) -> BaseModel | dict:
        """
        Calculates the final, merged configuration for a single plugin instance.
        It also performs validation if a Pydantic model is associated with the plugin.

        Priority Order (lowest to highest):
        1. Plugin Default Config (from Pydantic model)
        2. Global Config
        3. Case Specific Config
        4. Command Line Overrides

        Args:
            plugin_name: The name of the plugin.
            case_plugin_config: The configuration for this plugin from the case.yaml file.

        Returns:
            A validated Pydantic model instance if a model is defined, otherwise a dictionary.
        """
        # 1. Start with the plugin's own defaults
        plugin_default = self.plugin_defaults_map.get(plugin_name, {})
        final_config = deepcopy(plugin_default)

        # 2. Merge global config on top
        final_config = deep_merge(final_config, self.global_config)

        # 3. Merge the case-specific settings
        final_config = deep_merge(final_config, case_plugin_config)

        # 4. Merge command-line arguments on top
        final_config = deep_merge(final_config, self.cli_args)
        
        # Clean up data_sources key
        if 'data_sources' in final_config:
            del final_config['data_sources']
            
        # 5. Validate with Pydantic model if available
        # This is a key benefit of the refactoring
        spec = PLUGIN_REGISTRY.get(plugin_name)
        if spec and spec.config_model:
            try:
                return spec.config_model(**final_config)
            except Exception as e:
                logger.error(f"Configuration validation failed for plugin '{plugin_name}': {e}")
                raise
        
        return final_config