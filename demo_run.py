import argparse
import logging
from pathlib import Path
from core.pipeline_runner import PipelineRunner

def main():
    """
    Main entry point for running the data replay pipeline.
    """
    parser = argparse.ArgumentParser(description="Data Replay Pipeline Runner")
    parser.add_argument(
        "--case",
        type=str,
        required=True,
        help="Path to the case directory (e.g., 'cases/demo')"
    )
    # In the future, we can add --set for CLI config overrides
    # parser.add_argument("--set", nargs='*', help="Set config values from CLI")

    args = parser.parse_args()

    # The PipelineRunner will set up the logging, so we can use it after initialization
    # However, for logging before that, we can do a basic setup
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    case_path = Path(args.case)
    
    # It's better to get the logger instance after basicConfig
    logger = logging.getLogger(__name__)

    logger.debug(f"Current Working Directory: {Path.cwd()}")
    logger.debug(f"Resolved Case Path: {case_path.resolve()}")

    if not case_path.is_dir():
        logger.error(f"Case path not found or is not a directory: {case_path}")
        return

    logger.info(f"====== Running Case: {case_path.name} ======")
    
    # TODO: Parse CLI args for config overrides
    cli_overrides = {}

    # Initialize and run the pipeline
    try:
        runner = PipelineRunner(case_path=str(case_path), cli_args=cli_overrides)
        final_context = runner.run()

        logger.info("\n====== Final Context Results ======")
        import json
        # Use logger to output the final results
        logger.info(json.dumps(final_context.get("results", {}), indent=2))
        logger.info("=====================================")

    except Exception as e:
        logger.error(f"\nAn error occurred during pipeline execution: {e}", exc_info=True)

if __name__ == "__main__":
    main()
