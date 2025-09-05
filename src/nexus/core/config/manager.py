import yaml
from pathlib import Path
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)

# --- Helper Functions ---

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

# --- Main Class (Refactored) ---

class ConfigManager:
    """
    A stateless calculator for merging hierarchical configurations for a pipeline run.
    It is instantiated by the PipelineRunner with all necessary configuration sources.
    """
    def __init__(self, global_config: dict, case_config: dict, 
                 plugin_default_configs: list[dict], cli_args: dict = None):
        """
        Initializes the ConfigManager for a single run.

        Args:
            global_config (dict): The loaded global.yaml config.
            case_config (dict): The loaded case.yaml config for the current run.
            plugin_default_configs (list[dict]): A list of all default configs 
                                                 for plugins in the pipeline.
            cli_args (dict, optional): Config overrides from the command line.
        """
        self.global_config = global_config
        self.case_config = case_config
        self.plugin_default_configs = plugin_default_configs
        self.cli_args = cli_args or {}
        
        # Immediately calculate the final merged data sources upon initialization.
        self._merged_data_sources = self._merge_all_data_sources()
        logger.debug("Final merged data sources calculated.")

    def _merge_all_data_sources(self) -> dict:
        """
        Merges data_sources from all layers with the correct priority.
        Priority Order (lowest to highest): 
        Plugin Defaults -> Global -> Case
        """
        final_sources = {}
        
        # 1. Merge all plugin default data_sources (lowest priority)
        for conf in self.plugin_default_configs:
            final_sources = deep_merge(final_sources, conf.get('data_sources', {}))
        
        # 2. Merge global config on top
        final_sources = deep_merge(final_sources, self.global_config.get('data_sources', {}))
        
        # 3. Merge case config on top (highest priority for files)
        final_sources = deep_merge(final_sources, self.case_config.get('data_sources', {}))
        
        return final_sources

    def get_data_sources(self) -> dict:
        """Returns the final, fully merged data_sources dictionary."""
        return self._merged_data_sources

    def get_plugin_config(self, plugin_default_config: dict, case_plugin_config: dict) -> dict:
        """
        Calculates the final, merged configuration for a single plugin instance.
        
        Priority Order (lowest to highest):
        1. Plugin Default Config
        2. Global Config
        3. Case Specific Config
        4. Command Line Overrides

        Args:
            plugin_default_config (dict): The default .yaml config for the plugin.
            case_plugin_config (dict): The configuration for this plugin from the case.yaml file.

        Returns:
            dict: The final, merged configuration dictionary for the plugin's parameters.
        """
        # 1. Start with the plugin's own defaults
        final_config = deepcopy(plugin_default_config)
        
        # 2. Merge global config on top
        final_config = deep_merge(final_config, self.global_config)
        
        # 3. Merge the case-specific settings for this plugin instance
        final_config = deep_merge(final_config, case_plugin_config)
        
        # 4. Merge command-line arguments on top (Highest Priority)
        final_config = deep_merge(final_config, self.cli_args)

        # Clean up: The returned dict should only contain plugin parameters,
        # not metadata like data_sources which is handled globally.
        if 'data_sources' in final_config:
            del final_config['data_sources']
        
        return final_config
