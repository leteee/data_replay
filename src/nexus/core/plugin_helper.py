import argparse
import logging
from pathlib import Path
import inspect
import importlib
import pkgutil

from nexus import plugins
# from nexus.plugins.base_plugin import BasePlugin  # <-- Commented out
from nexus.core.execution_context import NexusContext, PluginContext  # <-- Import correct context classes
from nexus.core.plugin_executor import PluginExecutor
from nexus.core.config_manager import ConfigManager
from nexus.core.plugin_spec import PluginSpec  # <-- Import PluginSpec
from nexus.core.plugin_decorator import PLUGIN_REGISTRY  # <-- Import PLUGIN_REGISTRY
from nexus.core.data_hub import DataHub # <-- Import DataHub
import json # <-- Import json for config loading

# The project root is 4 levels up from this file (src/nexus/core/plugin_helper.py)
project_root = Path(__file__).resolve().parent.parent.parent.parent

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
    Finds a plugin by name and executes it using the new context and executor.
    This is now a thin wrapper.
    """
    try:
        # --- Setup similar to run_pipeline in run.py ---
        # 1. Resolve paths
        case_arg_path = Path(case_name)
        if case_arg_path.is_absolute():
            case_path = case_arg_path
        else:
            # ConfigManager is used here just to get the cases_root path
            temp_config_manager = ConfigManager(project_root=str(project_root), cli_args={})
            cases_root = temp_config_manager.get_cases_root_path()
            case_path = cases_root / case_arg_path

        if not case_path.is_dir():
            logger.error(f"Case path not found or is not a directory: {case_path}")
            return

        logger.info(f"====== Running Plugin '{plugin_name}' for Case: {case_path.name} ======")

        # 2. Initialize Core Services (similar to run_pipeline)
        from nexus.core.config_manager import load_yaml # Import the function
        case_config = load_yaml(case_path / "case.yaml")
        global_config = load_yaml(project_root / "config" / "global.yaml")
        from nexus.core.config_manager import deep_merge # Import here to avoid circular import issues if any
        run_config = deep_merge(global_config, case_config)

        # Create a logger for this context (In a full app, this might be more sophisticated)
        import logging
        context_logger = logging.getLogger(__name__) 

        data_hub = DataHub(case_path=case_path, data_sources=run_config.get("data_sources", {}), logger=context_logger)

        # 3. Create Global NexusContext (similar to run_pipeline)
        nexus_context = NexusContext(
            project_root=project_root,
            cases_root=case_path.parent, # Assuming cases_root is parent of case_path
            case_path=case_path,
            data_hub=data_hub,
            logger=context_logger,
            run_config=run_config
        )
        
        # 4. Discover plugins to populate PLUGIN_REGISTRY
        from nexus.core.plugin_discovery import discover_plugins
        discover_plugins(context_logger)
        
        # 5. Find the plugin spec
        plugin_spec = find_plugin_spec(plugin_name)  # <-- Changed to find_plugin_spec
        if plugin_spec is None:
            raise ValueError(f"Plugin '{plugin_name}' could not be found.")

        # 6. Get plugin configuration (similar to PipelineRunner)
        plugin_module = inspect.getmodule(plugin_spec.func)
        if plugin_module is None:
            raise TypeError(f"Could not determine module for plugin '{plugin_name}'")
        plugin_module_path = plugin_module.__file__
        if plugin_module_path is None:
             raise TypeError(f"Could not determine module path for plugin '{plugin_name}'")

        config_manager = ConfigManager(str(project_root)) # Create a ConfigManager instance
        # Get case config override for this specific plugin instance
        # This is tricky in standalone mode. We'll assume the plugin config is directly under 'config' in case.yaml
        # or use an empty dict. A more robust solution would involve parsing the pipeline steps.
        # For now, let's try to find it.
        plugin_params = {}
        pipeline_steps = run_config.get("pipeline", [])
        for step in pipeline_steps:
            if step.get("plugin") == plugin_name:
                plugin_params = step.get("config", {})
                break
        
        final_config = config_manager.get_plugin_config(
            plugin_module_path=plugin_module_path,
            case_config_override=plugin_params if plugin_params is not None else {} # <-- Ensure it's a dict
        )
        
        # 7. Add plugin's default data sources to DataHub (similar to PipelineRunner)
        from nexus.core.config_manager import load_yaml # Import here
        plugin_default_config = load_yaml(Path(plugin_module_path).with_suffix('.yaml'))
        nexus_context.data_hub.add_data_sources(plugin_default_config.get("data_sources", {}))

        # 8. Create the specific context for this plugin instance (similar to PipelineRunner)
        plugin_context = PluginContext(
            data_hub=nexus_context.data_hub,
            logger=nexus_context.logger,
            project_root=nexus_context.project_root,
            case_path=nexus_context.case_path,
            config=final_config
        )
        
        # 9. Execute the plugin using PluginExecutor (similar to PipelineRunner)
        executor = PluginExecutor(plugin_spec, plugin_context) # Pass both spec and context
        executor.execute() # Execute the plugin

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
