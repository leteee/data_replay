import argparse
import logging
from pathlib import Path
import json
import shutil
import sys

# Add the src directory to the Python path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root / "src"))

from nexus.core.pipeline_runner import PipelineRunner
from nexus.core.data_hub import DataHub
from nexus.core.execution_context import NexusContext
from nexus.core.config_manager import ConfigManager, deep_merge, load_yaml
from nexus.core.plugin_helper import run_single_plugin_by_name # <-- Uncommented import
from nexus.scripts.generation import generate_data, generate_plugin_documentation
from nexus.core.logger import get_logger, initialize_logging

logger = logging.getLogger(__name__)

def run_pipeline(args):
    """Handles the 'pipeline' command."""
    # 1. Resolve paths
    case_arg_path = Path(args.case)
    if case_arg_path.is_absolute():
        case_path = case_arg_path
    else:
        # ConfigManager is used here just to get the cases_root path
        temp_config_manager = ConfigManager(project_root=str(project_root), cli_args={})
        cases_root = temp_config_manager.get_cases_root_path()
        case_path = cases_root / case_arg_path

    logger.debug(f"Project Root: {project_root}")
    logger.debug(f"Resolved Case Path: {case_path}")

    if not case_path.is_dir():
        logger.error(f"Case path not found or is not a directory: {case_path}")
        return

    logger.info(f"====== Running Case: {case_path.name} ======")

    # 2. Initialize Core Services
    # Note: The logger is already initialized in main()
    # ConfigManager is now initialized within PipelineRunner
    case_config = load_yaml(case_path / "case.yaml")
    global_config = load_yaml(project_root / "config" / "global.yaml")
    run_config = deep_merge(global_config, case_config)

    data_hub = DataHub(case_path=case_path, data_sources=run_config.get("data_sources", {}), logger=logger)

    # 3. Create Global NexusContext
    nexus_context = NexusContext(
        project_root=project_root,
        cases_root=case_path.parent, # Assuming cases_root is parent of case_path
        case_path=case_path,
        data_hub=data_hub,
        logger=logger,
        run_config=run_config
    )

    # 4. Initialize and Run the Pipeline
    try:
        runner = PipelineRunner(nexus_context)
        runner.run()

        logger.debug("\n====== Final DataHub State ======")
        logger.debug(json.dumps(data_hub.summary(), indent=2))
        logger.debug("=====================================")

    except Exception as e:
        logger.critical(f"A critical error occurred during pipeline execution: {e}", exc_info=True)

def run_plugin(args):
    """Handles the 'plugin' command."""
    run_single_plugin_by_name(plugin_name=args.plugin_name, case_name=args.case) # <-- This should now work

def run_generate_data(args):
    """Handles the 'generate-data' command."""
    logger.info("Generating demo data...")
    try:
        generate_data()
        logger.info("Successfully generated demo data.")
    except Exception as e:
        logger.error(f"An error occurred during data generation: {e}", exc_info=True)

def run_generate_docs(args):
    """Handles the 'generate-docs' command."""
    logger.info("Generating plugin documentation...")
    try:
        generate_plugin_documentation()
        logger.info("Successfully generated plugin documentation.")
    except Exception as e:
        logger.error(f"An error occurred during doc generation: {e}", exc_info=True)

def main():
    """Main entry point for the unified CLI."""
    # Load global config to get log level
    global_config_path = project_root / "config" / "global.yaml"
    global_config = load_yaml(global_config_path)
    log_level_str = global_config.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Get log file path from config if specified
    log_file = global_config.get("log_file")

    initialize_logging()
    parser = argparse.ArgumentParser(description="Data Replay Framework CLI")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # --- Pipeline Command ---
    parser_pipeline = subparsers.add_parser('pipeline', help='Run a full pipeline for a given case.')
    parser_pipeline.add_argument(
        "--case",
        type=str,
        required=True,
        help="Name of the case directory under 'cases/' (e.g., 'demo')"
    )
    parser_pipeline.add_argument(
        "--template",
        type=str,
        required=False,
        help="Name of the case template to use from the 'templates' directory."
    )
    parser_pipeline.set_defaults(func=run_pipeline)

    # --- Plugin Command ---
    parser_plugin = subparsers.add_parser('plugin', help='Run a single plugin from a case definition.')
    parser_plugin.add_argument(
        'plugin_name',
        type=str,
        help="The name of the plugin class to run (e.g., 'InitialDataReader')."
    )
    parser_plugin.add_argument(
        "--case",
        type=str,
        required=True,
        help="Name of the case directory under 'cases/' to provide context."
    )
    parser_plugin.set_defaults(func=run_plugin)

    # --- Generate-Data Command ---
    parser_generate_data = subparsers.add_parser('generate-data', help='Generate sample data for demos.')
    parser_generate_data.set_defaults(func=run_generate_data)

    # --- Generate-Docs Command ---
    parser_generate_docs = subparsers.add_parser('generate-docs', help='Generate documentation for all available plugins.')
    parser_generate_docs.set_defaults(func=run_generate_docs)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
