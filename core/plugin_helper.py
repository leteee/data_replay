import argparse
import logging
import json
from pathlib import Path
import sys
import inspect
import yaml

# To import from the parent directory (core), we adjust the path
# This will be cleaner after the src-layout refactor
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.config_manager import ConfigManager
from core.data_hub import DataHub
from modules.base_plugin import BasePlugin

def run_plugin_standalone(plugin_class: type[BasePlugin]):
    """
    A generic helper function to run a plugin standalone, adhering to the project's design.

    It uses the --case argument to get the case context and reuses ConfigManager
    and DataHub to ensure behavior is consistent with a full pipeline run.

    Args:
        plugin_class: The plugin class to run (e.g., KalmanFilter).
    """
    parser = argparse.ArgumentParser(
        description=f"Standalone runner for {plugin_class.__name__}"
    )
    parser.add_argument(
        "--case",
        required=True,
        help="Name of the case directory under 'cases/' (e.g., 'demo')"
    )
    args = parser.parse_args()

    # --- 1. Initialize Environment ---
    case_path = Path('cases') / args.case
    project_root_path = Path.cwd()
    plugin_file_path = inspect.getfile(plugin_class)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = logging.getLogger(f"{plugin_class.__name__}Standalone")

    if not case_path.is_dir():
        logger.error(f"Case path not found or is not a directory: {case_path}")
        sys.exit(1)

    # --- 2. Load Configuration (reusing ConfigManager) ---
    config_manager = ConfigManager(project_root=str(project_root_path))
    case_yaml_path = case_path / "case.yaml"
    
    if not case_yaml_path.exists():
        logger.error(f"Case config file not found: {case_yaml_path}")
        sys.exit(1)

    with open(case_yaml_path, 'r', encoding='utf-8') as f:
        case_config = yaml.safe_load(f)

    # Find the plugin's specific config from the pipeline steps in case.yaml
    plugin_specific_config = {}
    for step in case_config.get("pipeline", []):
        if step.get("plugin") == plugin_class.__name__:
            plugin_specific_config = step.get("config", {})
            logger.info(f"Found specific config for {plugin_class.__name__} in case.yaml")
            break
    
    # Get the final merged config using ConfigManager
    final_config = config_manager.get_plugin_config(
        plugin_module_path=plugin_file_path,
        case_config_override=plugin_specific_config
    )

    # --- 3. Initialize DataHub ---
    # The DataHub is responsible for all data loading and management
    data_sources = case_config.get("data_sources", {})
    data_hub = DataHub(case_path=str(case_path), data_sources=data_sources)
    # The logger can be passed to the DataHub for consistent logging
    data_hub.set_logger(logger)


    # --- 4. Instantiate and Run the Plugin ---
    logger.info(f"--- Running {plugin_class.__name__} Standalone for case: {case_path.name} ---")
    logger.debug(f"Final Plugin Config: {json.dumps(final_config, indent=2)}")
    
    try:
        plugin_instance = plugin_class(config=final_config)
        plugin_instance.run(data_hub)
    except Exception as e:
        logger.error(f"An error occurred while running the plugin: {e}", exc_info=True)
        sys.exit(1)

    # --- 5. Print Results ---
    logger.info(f"--- Standalone Run Finished for {plugin_class.__name__} ---")
    print("\n====== Final DataHub State ======")
    print(json.dumps(data_hub.summary(), indent=2, ensure_ascii=False))
    print("=============================")
