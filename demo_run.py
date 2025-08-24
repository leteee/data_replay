import argparse
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

    case_path = Path('cases') / args.case
    print(f"[DEBUG] Current Working Directory: {Path.cwd()}")
    print(f"[DEBUG] Resolved Case Path: {case_path.resolve()}")
    if not case_path.is_dir():
        print(f"Error: Case path not found or is not a directory: {case_path}")
        return

    print(f"====== Running Case: {case_path.name} ======")
    
    # TODO: Parse CLI args for config overrides
    cli_overrides = {}

    # Initialize and run the pipeline
    try:
        runner = PipelineRunner(case_path=str(case_path), cli_args=cli_overrides)
        final_data_hub = runner.run()

        print("\n====== Final Data Hub Results ======")
        # Pretty print the results dictionary
        import json
        print(json.dumps(final_data_hub.get("results", {}), indent=2))
        print("=====================================")

    except Exception as e:
        print(f"\nAn error occurred during pipeline execution: {e}")
        # In a real application, you'd use a logger and possibly print a traceback
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()