import yaml
from pathlib import Path
from copy import deepcopy
import logging # Added import

logger = logging.getLogger(__name__) # Added logger

# --- Helper Functions (retained from original) ---

def load_yaml(file_path):
    """Loads a YAML file safely."""
    path = Path(file_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def deep_merge(dict1, dict2):
    """Recursively merges two dictionaries."""
    result = deepcopy(dict1)
    for k, v in dict2.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

def merge_data_sources(plugin_defaults, global_config, case_config):
    """Merge data sources from different configuration layers."""
    # Start with plugin defaults
    merged_sources = deepcopy(plugin_defaults.get('data_sources', {}))
    
    # Merge global data sources
    global_sources = global_config.get('data_sources', {})
    for name, source_config in global_sources.items():
        merged_sources[name] = deepcopy(source_config)
    
    # Merge case-specific data sources (highest priority)
    case_sources = case_config.get('data_sources', {})
    for name, source_config in case_sources.items():
        merged_sources[name] = deepcopy(source_config)
    
    return merged_sources

# --- Main Class (rewritten) ---

class ConfigManager:
    """
    Manages the 4-layer hierarchical configuration system.
    The manager is initialized once per run and provides methods to get
    the final, merged configuration for each plugin instance.
    """
    def __init__(self, project_root: str, cli_args: dict = None):
        """
        Initializes the ConfigManager.
        Args:
            project_root (str): The absolute path to the project's root directory.
            cli_args (dict, optional): Config overrides from the command line. Defaults to None.
        """
        self.project_root = Path(project_root)
        self.cli_args = cli_args if cli_args else {}
        
        # Load the global config once during initialization
        global_config_path = self.project_root / "config" / "global.yaml"
        self.global_config = load_yaml(global_config_path)
        logger.debug(f"Loaded global config from: {global_config_path}")

    def load_case_config(self, case_path: str) -> dict:
        """Loads the case.yaml file from a given case path."""
        case_yaml_path = Path(case_path) / "case.yaml"
        logger.debug(f"Loading case config from: {case_yaml_path}")
        return load_yaml(case_yaml_path)

    def get_cases_root_path(self) -> Path:
        """
        Resolves the absolute path to the root directory where cases are stored.
        It reads the 'cases_root' from the global config.
        - If 'cases_root' is an absolute path, it's used directly.
        - If it's a relative path, it's resolved relative to the project root.
        - If not set, it defaults to 'cases' directory in the project root.
        """
        cases_root_str = self.global_config.get("cases_root", "cases")
        cases_root_path = Path(cases_root_str)
        if cases_root_path.is_absolute():
            return cases_root_path
        else:
            return (self.project_root / cases_root_path).resolve()

    def get_plugin_config(self, plugin_module_path: str, case_config_override: dict) -> dict:
        """
        Calculates the final, merged configuration for a specific plugin instance.
        
        Priority Order (from lowest to highest):
        1. Plugin Default Config
        2. Global Config
        3. Case Specific Config
        4. Command Line Overrides

        Args:
            plugin_module_path (str): The path to the plugin's .py file.
            case_config_override (dict): The configuration for this plugin from the case.yaml file.

        Returns:
            dict: The final, merged configuration dictionary for the plugin.
        """
        logger.debug(f"get_plugin_config: plugin_module_path={plugin_module_path}")
        # 1. Load Plugin Default Config (Lowest Priority)
        plugin_default_path = Path(plugin_module_path).with_suffix('.yaml')
        logger.debug(f"get_plugin_config: plugin_default_path={plugin_default_path}")
        plugin_default_config = load_yaml(plugin_default_path)
        logger.debug(f"get_plugin_config: plugin_default_config={plugin_default_config}")

        # 2. Start merging from lowest to highest priority
        # Start with the plugin's own defaults
        final_config = deepcopy(plugin_default_config)
        
        # Handle data sources separately with proper merging logic
        merged_data_sources = merge_data_sources(
            plugin_default_config,
            self.global_config,
            case_config_override
        )
        
        # Merge global config on top (excluding data_sources which we handled separately)
        global_config_without_sources = {k: v for k, v in self.global_config.items() if k != 'data_sources'}
        final_config = deep_merge(final_config, global_config_without_sources)
        logger.debug(f"get_plugin_config: after global merge, final_config={final_config}")
        
        # Merge the case-specific settings for this plugin instance (excluding data_sources)
        case_config_without_sources = {k: v for k, v in case_config_override.items() if k != 'data_sources'}
        final_config = deep_merge(final_config, case_config_without_sources)
        logger.debug(f"get_plugin_config: after case override merge, final_config={final_config}")
        logger.debug(f"get_plugin_config: case_config_override={case_config_override}")
        
        # Add merged data sources to final config
        final_config['data_sources'] = merged_data_sources
        
        # Merge command-line arguments on top (Highest Priority)
        # Note: This assumes cli_args are in a nested dict format that matches other configs.
        # A more complex CLI parser might be needed for dot-notation overrides.
        final_config = deep_merge(final_config, self.cli_args)
        logger.debug(f"get_plugin_config: after cli merge, final_config={final_config}")

        return final_config