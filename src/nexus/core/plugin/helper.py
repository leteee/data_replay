import argparse
import logging
from pathlib import Path
import inspect
import json

from ..context import NexusContext, PluginContext
from .executor import PluginExecutor
from .spec import PluginSpec
from .decorator import PLUGIN_REGISTRY
from ..data.hub import DataHub
from ..config.manager import ConfigManager, load_yaml
from .discovery import discover_plugins

logger = logging.getLogger(__name__)

def run_single_plugin_by_name(plugin_name: str, case_name: str, project_root: Path):
    """
    Finds a plugin by name and executes it within the context of a given case.
    This function now mirrors the setup logic of the main PipelineRunner.
    """
    logger.info(f"====== Running single plugin '{plugin_name}' for Case: {case_name} ======")
    try:
        # --- 1. Configuration Setup Phase ---
        global_config = load_yaml(project_root / "config" / "global.yaml")

        # Discover plugins to populate PLUGIN_REGISTRY
        plugin_modules = global_config.get("plugin_modules", [])
        logger.info(f"Starting plugin discovery...")
        logger.info(f"Scanning for plugins in module: {', '.join(plugin_modules)}")
        discover_plugins(plugin_modules, logger)
        logger.info(f"Plugin discovery finished. Found {len(PLUGIN_REGISTRY)} plugins.")

        if plugin_name not in PLUGIN_REGISTRY:
            raise ValueError(f"Plugin '{plugin_name}' could not be found in registry.")

        # Resolve case path
        cases_root_str = global_config.get("cases_root", "cases")
        cases_root = Path(cases_root_str)
        if not cases_root.is_absolute():
            cases_root = (project_root / cases_root).resolve()
        
        case_path = Path(case_name)
        if not case_path.is_absolute():
            case_path = cases_root / case_name

        if not case_path.is_dir():
            raise FileNotFoundError(f"Case path not found or is not a directory: {case_path}")

        case_config = load_yaml(case_path / "case.yaml")

        # Instantiate the centralized ConfigManager
        config_manager = ConfigManager(
            global_config=global_config,
            case_config=case_config,
            plugin_registry=PLUGIN_REGISTRY,
            cli_args={}
        )

        # --- 2. Context and Execution Phase ---
        data_hub = DataHub(case_path=case_path, logger=logger)
        data_hub.add_data_sources(config_manager.get_data_sources())

        # Find the plugin's specific params from the case file
        case_plugin_params = {}
        for step in case_config.get("pipeline", []):
            if step.get("plugin") == plugin_name:
                case_plugin_params = step.get("params", {})
                break
        
        final_plugin_config = config_manager.get_plugin_config(
            plugin_name=plugin_name,
            case_plugin_config=case_plugin_params
        )

        plugin_context = PluginContext(
            data_hub=data_hub,
            logger=logger,
            project_root=project_root,
            case_path=case_path,
            config=final_plugin_config
        )
        
        executor = PluginExecutor(PLUGIN_REGISTRY[plugin_name], plugin_context)
        executor.execute()

        logger.debug("\n====== Final DataHub State ======")
        logger.debug(json.dumps(data_hub.summary(), indent=2))
        logger.debug("=====================================")

    except Exception as e:
        logger.error(f"An error occurred while running plugin '{plugin_name}': {e}", exc_info=True)
        raise