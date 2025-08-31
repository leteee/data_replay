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
from nexus.core.config_manager import ConfigManager
from nexus.core.plugin_helper import run_single_plugin_by_name
from nexus.scripts.generation import generate_data, generate_plugin_documentation

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

from nexus.core.logger import setup_logging # Added import

def run_pipeline(args):
    """Handles the 'pipeline' command."""
    cli_overrides = {}  # TODO: Parse CLI args for config overrides

    # Set up logging for the pipeline run
    setup_logging(case_name=args.case) # Moved setup_logging here

    # Initialize ConfigManager to resolve cases_root
    config_manager = ConfigManager(project_root=str(project_root), cli_args=cli_overrides)
    cases_root = config_manager.get_cases_root_path()
    case_arg_path = Path(args.case)
    if case_arg_path.is_absolute():
        case_path = case_arg_path
    else:
        case_path = cases_root / case_arg_path

    logger.debug(f"Project Root: {project_root}")
    logger.debug(f"Cases Root: {cases_root}")
    logger.debug(f"Resolved Case Path: {case_path}")

    # Handle template copying if provided
    if args.template:
        template_name = args.template
        template_filename = f"{template_name}_case.yaml"
        template_path = project_root / "templates" / template_filename
        
        destination_path = case_path / "case.yaml"

        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return

        # Ensure the case directory exists before copying
        case_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Copying template '{template_name}' to '{destination_path}'")
        shutil.copy(template_path, destination_path)

    if not case_path.is_dir():
        logger.error(f"Case path not found or is not a directory: {case_path}")
        return

    logger.info(f"====== Running Case: {case_path.name} ======")

    try:
        # We pass the already resolved, absolute path to the runner
        runner = PipelineRunner(
            project_root=str(project_root),
            case_path=str(case_path), 
            cli_args=cli_overrides
        )
        final_data_hub = runner.run()

        logger.debug("\n====== Final DataHub State ======")
        logger.debug(json.dumps(final_data_hub.summary(), indent=2))
        logger.debug("=====================================")

    except Exception as e:
        logger.error(f"\nAn error occurred during pipeline execution: {e}", exc_info=True)

def run_plugin(args):
    """Handles the 'plugin' command."""
    run_single_plugin_by_name(plugin_name=args.plugin_name, case_name=args.case)

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
