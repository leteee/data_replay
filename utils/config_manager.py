import yaml
from pathlib import Path
from copy import deepcopy

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
        print(f"加载全局配置: {global_config_path}")

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
        # 1. Load Plugin Default Config (Lowest Priority)
        plugin_default_path = Path(plugin_module_path).with_suffix('.yaml')
        plugin_default_config = load_yaml(plugin_default_path)

        # 2. Start merging from lowest to highest priority
        # Start with the plugin's own defaults
        final_config = deepcopy(plugin_default_config)
        
        # Merge global config on top
        final_config = deep_merge(final_config, self.global_config)
        
        # Merge the case-specific settings for this plugin instance
        final_config = deep_merge(final_config, case_config_override)
        
        # Merge command-line arguments on top (Highest Priority)
        # Note: This assumes cli_args are in a nested dict format that matches other configs.
        # A more complex CLI parser might be needed for dot-notation overrides.
        final_config = deep_merge(final_config, self.cli_args)

        return final_config