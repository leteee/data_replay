import subprocess
import sys
from pathlib import Path
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Project root is two levels up from this script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_SCRIPT = PROJECT_ROOT / "run.py"
DEMO_CASE = "demo"

# List of plugins from cases/demo/case.yaml
PLUGINS = [
    "InitialDataReader",
    "LatencyCompensator",
    "FrameRenderer",
    "VideoCreator"
]

def run_command(command_args, description):
    """Helper to run shell commands and log output."""
    logger.info(f"--- {description} ---")
    full_command = [sys.executable, str(RUN_SCRIPT)] + command_args
    logger.info(f"Executing: {' '.join(full_command)}")
    try:
        result = subprocess.run(full_command, check=True, capture_output=True, text=True)
        logger.info(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR:\n{result.stderr}")
        logger.info(f"--- {description} COMPLETED ---")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"--- {description} FAILED ---")
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"STDOUT:\n{e.stdout}")
        logger.error(f"STDERR:\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"--- {description} FAILED ---")
        logger.error(f"An unexpected error occurred: {e}")
        return False

def main():
    logger.info("Starting End-to-End Test Suite")

    # 1. Data Generation
    if not run_command(["generate-data"], "Generating Demo Data"):
        logger.error("Test failed at Data Generation step.")
        sys.exit(1)

    # 2. Full Pipeline Run
    if not run_command(["pipeline", "--case", DEMO_CASE], f"Running Full Pipeline for {DEMO_CASE} case"):
        logger.error("Test failed at Full Pipeline Run step.")
        sys.exit(1)

    # 3. Run all plugins individually
    for plugin_name in PLUGINS:
        if not run_command(["plugin", plugin_name, "--case", DEMO_CASE], f"Running Plugin: {plugin_name} for {DEMO_CASE} case"):
            logger.error(f"Test failed at running individual plugin: {plugin_name}.")
            sys.exit(1)

    # 4. Generate Plugin Documentation
    if not run_command(["generate-docs"], "Generating Plugin Documentation"):
        logger.error("Test failed at Plugin Documentation Generation step.")
        sys.exit(1)

    logger.info("End-to-End Test Suite COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
