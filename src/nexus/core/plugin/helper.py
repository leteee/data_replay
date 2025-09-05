import argparse
import logging
from pathlib import Path
import inspect
import importlib
import pkgutil

# from nexus import plugins
# from nexus.plugins.base_plugin import BasePlugin  # <-- Commented out
from ..context import NexusContext, PluginContext  # <-- Import correct context classes
from .executor import PluginExecutor
from ..config.manager import ConfigManager
from .spec import PluginSpec  # <-- Import PluginSpec
from .decorator import PLUGIN_REGISTRY  # <-- Import PLUGIN_REGISTRY
from ..data.hub import DataHub # <-- Import DataHub
import json # <-- Import json for config loading

# The project root is 5 levels up from this file (src/nexus/core/plugin/plugin_helper.py)
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent

logger = logging.getLogger(__name__)

def find_plugin_spec(plugin_name: str) -> PluginSpec | None:  # <-- Changed return type
    """
    Finds a plugin spec by its registered name.
    Args:
        plugin_name: The string name of the plugin as registered.
    Returns:
        The PluginSpec if found, otherwise None.
    """
    # Use the global PLUGIN_REGISTRY
    if plugin_name in PLUGIN_REGISTRY:
        logger.debug(f"Found plugin spec '{plugin_name}' in PLUGIN_REGISTRY")
        return PLUGIN_REGISTRY[plugin_name]
    logger.error(f"Plugin spec '{plugin_name}' not found in PLUGIN_REGISTRY.")
    return None

def run_single_plugin_by_name(plugin_name: str, case_name: str):
    """
    Finds a plugin by name and executes it within the context of a given case.
    This function now mirrors the setup logic of the main PipelineRunner.
    """
    logger.info(f"====== Running single plugin '{plugin_name}' for Case: {case_name} ======")
    try:
        # --- 1. Configuration Setup Phase ---
        from ..config.manager import load_yaml, ConfigManager
        global_config = load_yaml(project_root / "config" / "global.yaml")
        
        # Discover plugins to populate PLUGIN_REGISTRY
        from .discovery import discover_plugins
        plugin_modules = global_config.get("plugin_modules", [])
        discover_plugins(plugin_modules, logger)
        
        # Find the specific plugin spec *after* discovery
        plugin_spec = find_plugin_spec(plugin_name)
        if plugin_spec is None:
            raise ValueError(f"Plugin '{plugin_name}' could not be found in registry.")

        # Resolve case path
        cases_root_str = global_config.get("cases_root", "cases")
        cases_root = Path(cases_root_str)
        if not cases_root.is_absolute():
            cases_root = (project_root / cases_root).resolve()
        
        case_path = Path(case_name)
        if not case_path.is_absolute():
            case_path = cases_root / case_path

        if not case_path.is_dir():
            raise FileNotFoundError(f"Case path not found or is not a directory: {case_path}")

        # Load all necessary configuration files
        case_config = load_yaml(case_path / "case.yaml")
        
        plugin_module = inspect.getmodule(plugin_spec.func)
        if not (plugin_module and plugin_module.__file__):
            raise TypeError(f"Could not determine module file for plugin '{plugin_name}'.")
        
        plugin_default_config = load_yaml(Path(plugin_module.__file__).with_suffix('.yaml'))

        # Instantiate the centralized ConfigManager
        config_manager = ConfigManager(
            global_config=global_config,
            case_config=case_config,
            plugin_default_configs=[plugin_default_config], # Only this plugin's default
            cli_args={}
        )

        # --- 2. Context and Execution Phase ---
        from ..data.hub import DataHub
        data_hub = DataHub(case_path=case_path, logger=logger)
        data_hub.add_data_sources(config_manager.get_data_sources())

        # Find the plugin's specific params from the case file
        case_plugin_params = {}
        for step in case_config.get("pipeline", []):
            if step.get("plugin") == plugin_name:
                case_plugin_params = step.get("params", {})
                break
        
        final_plugin_config = config_manager.get_plugin_config(
            plugin_default_config=plugin_default_config,
            case_plugin_config=case_plugin_params
        )

        from ..context import PluginContext
        plugin_context = PluginContext(
            data_hub=data_hub,
            logger=logger,
            project_root=project_root,
            case_path=case_path,
            config=final_plugin_config
        )
        
        executor = PluginExecutor(plugin_spec, plugin_context)
        executor.execute()

        logger.debug("\n====== Final DataHub State ======")
        logger.debug(json.dumps(data_hub.summary(), indent=2))
        logger.debug("=====================================")

    except Exception as e:
        logger.error(f"An error occurred while running plugin '{plugin_name}': {e}", exc_info=True)
        raise


def run_plugin_standalone(plugin_class: type):  # <-- Changed parameter type
    """
    A generic helper function to run a plugin standalone using argparse.
    This is a thin wrapper around the core execution logic.
    Note: This function might be deprecated or need significant changes
    since plugins are now functions, not classes.
    """
    # Implementation would need to be significantly revised.
    # This is a placeholder.
    logger.warning("run_plugin_standalone is not fully implemented for the new plugin system.")
    pass
