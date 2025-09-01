import argparse
import logging
from pathlib import Path
import inspect
import importlib
import pkgutil

from nexus import plugins
from nexus.plugins.base_plugin import BasePlugin
from nexus.core.execution_context import ExecutionContext
from nexus.core.plugin_executor import PluginExecutor
from nexus.core.config_manager import ConfigManager

# The project root is 4 levels up from this file (src/nexus/core/plugin_helper.py)
project_root = Path(__file__).resolve().parent.parent.parent.parent

logger = logging.getLogger(__name__)

def find_plugin_class(plugin_name: str) -> type[BasePlugin] | None:
    """
    Scans the 'plugins' directory to find a plugin class by its name.
    Args:
        plugin_name: The string name of the plugin class to find.
    Returns:
        The plugin class type if found, otherwise None.
    """
    for importer, modname, ispkg in pkgutil.walk_packages(path=plugins.__path__,
                                                          prefix=plugins.__name__+'.',
                                                          onerror=lambda x: None):
        module = importlib.import_module(modname)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name == plugin_name and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                logger.debug(f"Found plugin class '{plugin_name}' in module '{modname}'")
                return obj
    logger.error(f"Plugin class '{plugin_name}' not found.")
    return None

def run_single_plugin_by_name(plugin_name: str, case_name: str):
    """
    Finds a plugin by name and executes it using the new context and executor.
    This is now a thin wrapper.
    """
    try:
        # Initialize ConfigManager just to resolve the case path
        config_manager = ConfigManager(project_root=str(project_root))
        cases_root = config_manager.get_cases_root_path()
        case_arg_path = Path(case_name)
        case_path = cases_root / case_arg_path if not case_arg_path.is_absolute() else case_arg_path

        plugin_class = find_plugin_class(plugin_name)
        if plugin_class is None:
            raise ValueError(f"Plugin '{plugin_name}' could not be found.")

        # All setup logic is now in ExecutionContext.
        context = ExecutionContext(project_root=str(project_root), case_path=str(case_path))
        
        # All execution logic is now in PluginExecutor.
        executor = PluginExecutor(context=context)
        executor.execute(plugin_class)

    except Exception as e:
        logger.error(f"An error occurred while running plugin '{plugin_name}': {e}", exc_info=True)
        raise

def run_plugin_standalone(plugin_class: type[BasePlugin]):
    """
    A generic helper function to run a plugin standalone using argparse.
    This is a thin wrapper around the core execution logic.
    """
    parser = argparse.ArgumentParser(description=f"Standalone runner for {plugin_class.__name__}")
    parser.add_argument("--case", required=True, help="Name of the case directory under 'cases/' or an absolute path.")
    args = parser.parse_args()

    try:
        # We still need to resolve the case path before creating the context
        config_manager = ConfigManager(project_root=str(project_root))
        cases_root = config_manager.get_cases_root_path()
        case_arg_path = Path(args.case)
        case_path = cases_root / case_arg_path if not case_arg_path.is_absolute() else case_arg_path

        # All setup logic is now in ExecutionContext.
        context = ExecutionContext(project_root=str(project_root), case_path=str(case_path))
        
        # All execution logic is now in PluginExecutor.
        executor = PluginExecutor(context=context)
        executor.execute(plugin_class)

    except Exception as e:
        logger.error(f"An error occurred while running plugin '{plugin_class.__name__}': {e}", exc_info=True)
        raise
