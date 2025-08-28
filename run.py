import argparse
import logging
from pathlib import Path
import json

from core.pipeline_runner import PipelineRunner
from core.plugin_helper import run_single_plugin_by_name
from scripts.generation import generate_data, generate_plugin_documentation

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

def run_pipeline(args):
    """Handles the 'pipeline' command."""
    case_path = Path('cases') / args.case
    
    logger.debug(f"Current Working Directory: {Path.cwd()}")
    logger.debug(f"Resolved Case Path: {case_path.resolve()}")

    if not case_path.is_dir():
        logger.error(f"Case path not found or is not a directory: {case_path}")
        return

    logger.info(f"====== Running Case: {case_path.name} ======")
    
    cli_overrides = {} # TODO: Parse CLI args for config overrides

    try:
        runner = PipelineRunner(case_path=str(case_path), cli_args=cli_overrides)
        final_data_hub = runner.run()

        logger.info("\n====== Final DataHub State ======")
        logger.info(json.dumps(final_data_hub.summary(), indent=2))
        logger.info("=====================================")

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
