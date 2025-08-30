import argparse
import logging
import json
from pathlib import Path
import sys
import inspect
import yaml
import importlib
import pkgutil

from nexus import modules
from nexus.core.config_manager import ConfigManager
from nexus.core.data_hub import DataHub
from nexus.modules.base_plugin import BasePlugin

# The project root is 4 levels up from this file (src/nexus/core/plugin_helper.py)
project_root = Path(__file__).resolve().parent.parent.parent.parent

logger = logging.getLogger(__name__)

def find_plugin_class(plugin_name: str) -> type[BasePlugin] | None:
    """
    Scans the 'modules' directory to find a plugin class by its name.
    Args:
        plugin_name: The string name of the plugin class to find.
    Returns:
        The plugin class type if found, otherwise None.
    """
    for importer, modname, ispkg in pkgutil.walk_packages(path=modules.__path__,
                                                          prefix=modules.__name__+'.',
                                                          onerror=lambda x: None):
        module = importlib.import_module(modname)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name == plugin_name and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                logger.info(f"Found plugin class '{plugin_name}' in module '{modname}'")
                return obj
    logger.error(f"Plugin class '{plugin_name}' not found.")
    return None

def execute_plugin(plugin_class: type[BasePlugin], case_name: str):
    """
    Core logic to execute a single plugin within a given case context.
    This function is designed to be called by different CLI wrappers.
    Args:
        plugin_class: The plugin class to run.
        case_name: The name of the case directory.
    Raises:
        FileNotFoundError: If case path or configs are not found.
        ValueError: If the plugin is not found in the case config.
    """
    # Initialize ConfigManager to resolve cases_root
    # project_root is already defined at the top of this file
    config_manager = ConfigManager(project_root=str(project_root))
    cases_root = config_manager.get_cases_root_path()
    case_arg_path = Path(case_name)
    if case_arg_path.is_absolute():
        case_path = case_arg_path
    else:
        case_path = cases_root / case_arg_path

    if not case_path.is_dir():
        raise FileNotFoundError(f"Case path not found or is not a directory: {case_path}")

    # --- Load Configuration ---
    case_yaml_path = case_path / "case.yaml"
    if not case_yaml_path.exists():
        raise FileNotFoundError(f"Case config file not found: {case_yaml_path}")

    with open(case_yaml_path, 'r', encoding='utf-8') as f:
        case_config = yaml.safe_load(f)

    plugin_specific_config = None
    for step in case_config.get("pipeline", []):
        if step.get("plugin") == plugin_class.__name__:
            plugin_specific_config = step
            logger.info(f"Found config for {plugin_class.__name__} in case.yaml")
            break
    
    if plugin_specific_config is None:
        raise ValueError(f"Plugin '{plugin_class.__name__}' not found in the pipeline of '{case_yaml_path}'")

    # --- Initialize DataHub ---
    data_sources = case_config.get("data_sources", {})
    data_hub = DataHub(case_path=case_path, data_sources=data_sources)

    # --- Instantiate and Run the Plugin ---
    logger.info(f"--- Running {plugin_class.__name__} for case: {case_path.name} ---")
    plugin_instance = plugin_class(config=plugin_specific_config)
    plugin_instance.run(data_hub)

    logger.info(f"--- Finished Run for {plugin_class.__name__} ---")
    print("\n====== Final DataHub State ======")
    print(json.dumps(data_hub.summary(), indent=2, ensure_ascii=False))
    print("=============================")


def run_single_plugin_by_name(plugin_name: str, case_name: str):
    """
    Finds a plugin by name and executes it. Called by the main run.py CLI.
    """
    plugin_class = find_plugin_class(plugin_name)
    if plugin_class:
        try:
            execute_plugin(plugin_class, case_name)
        except (FileNotFoundError, ValueError) as e:
            logger.error(e)
            sys.exit(1)
        except Exception as e:
            logger.error(f"An unexpected error occurred while running plugin '{plugin_name}': {e}", exc_info=True)
            sys.exit(1)

def run_plugin_standalone(plugin_class: type[BasePlugin]):
    """
    A generic helper function to run a plugin standalone using argparse.
    This is a thin wrapper around execute_plugin.
    """
    parser = argparse.ArgumentParser(description=f"Standalone runner for {plugin_class.__name__}")
    parser.add_argument("--case", required=True, help="Name of the case directory under 'cases/'")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    try:
        execute_plugin(plugin_class, args.case)
    except (FileNotFoundError, ValueError) as e:
        logger.error(e)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)