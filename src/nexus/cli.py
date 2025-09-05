import argparse
import logging
from pathlib import Path
import json
import shutil
import sys
import typer

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(project_root / "src"))

from nexus.core.pipeline_runner import PipelineRunner
from nexus.core.data.hub import DataHub
from nexus.core.context import NexusContext
from nexus.core.config.manager import ConfigManager, deep_merge, load_yaml
from nexus.core.plugin.helper import run_single_plugin_by_name # <-- Uncommented import
from nexus.scripts.demo_data import generate_data
from nexus.scripts.docgen import generate_plugin_documentation
from nexus.core.logger import get_logger, initialize_logging

logger = logging.getLogger(__name__)

app = typer.Typer(help="Data Replay Framework CLI")

def version_callback(value: bool):
    if value:
        # Assuming version is stored somewhere accessible, e.g., in pyproject.toml or a __version__.py file
        # For now, let's hardcode it as an example.
        print(f"Nexus Framework Version: 0.1.0")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show the application version and exit."),
):
    """
    Main callback for the CLI. Initializes logging.
    """
    global_config_path = project_root / "config" / "global.yaml"
    global_config = load_yaml(global_config_path)
    log_level_str = global_config.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Get log file path from config if specified
    log_file = global_config.get("log_file")

    initialize_logging()


@app.command()
def pipeline(
    case: str = typer.Option(..., "--case", help="Name of the case directory under 'cases/' (e.g., 'demo')"),
    template: str = typer.Option(None, "--template", help="Name of the case template to use from the 'templates' directory."),
):
    """
    Run a full pipeline for a given case.
    """
    # 1. Resolve paths
    global_config = load_yaml(project_root / "config" / "global.yaml")
    cases_root_str = global_config.get("cases_root", "cases")
    cases_root = Path(cases_root_str)
    if not cases_root.is_absolute():
        cases_root = (project_root / cases_root).resolve()

    case_arg_path = Path(case)
    case_path = case_arg_path if case_arg_path.is_absolute() else cases_root / case_arg_path

    logger.debug(f"Project Root: {project_root}")
    logger.debug(f"Resolved Case Path: {case_path}")

    if not case_path.is_dir():
        logger.error(f"Case path not found or is not a directory: {case_path}")
        raise typer.Exit(code=1)

    logger.info(f"====== Running Case: {case_path.name} ======")

    # 2. Create a minimal initial context.
    data_hub = DataHub(case_path=case_path, logger=logger)
    
    run_config = {
        "cli_args": {},
        "plugin_modules": global_config.get("plugin_modules", [])
    }

    nexus_context = NexusContext(
        project_root=project_root,
        cases_root=cases_root,
        case_path=case_path,
        data_hub=data_hub,
        logger=logger,
        run_config=run_config
    )

    # 3. Initialize and Run the Pipeline
    try:
        runner = PipelineRunner(nexus_context)
        runner.run()

        logger.debug("====== Final DataHub State ======")
        logger.debug(json.dumps(data_hub.summary(), indent=2))
        logger.debug("=====================================")

    except Exception as e:
        logger.critical(f"A critical error occurred during pipeline execution: {e}", exc_info=True)
        raise typer.Exit(code=1)

@app.command()
def plugin(
    plugin_name: str = typer.Argument(..., help="The name of the plugin class to run (e.g., 'InitialDataReader')."),
    case: str = typer.Option(..., "--case", help="Name of the case directory under 'cases/' to provide context."),
):
    """
    Run a single plugin from a case definition.
    """
    run_single_plugin_by_name(plugin_name=plugin_name, case_name=case, project_root=project_root)

@app.command(name="generate-data")
def generate_data_cmd():
    """
    Generate sample data for demos.
    """
    logger.info("Generating demo data...")
    try:
        generate_data()  # This is the function from nexus.scripts.demo_data
        logger.info("Successfully generated demo data.")
    except Exception as e:
        logger.error(f"An error occurred during data generation: {e}", exc_info=True)
        raise typer.Exit(code=1)

@app.command()
def docs():
    """
    Generate documentation for all available plugins and handlers.
    """
    logger.info("Generating framework documentation...")
    try:
        generate_plugin_documentation()
        logger.info("Successfully generated framework documentation.")
    except Exception as e:
        logger.error(f"An error occurred during doc generation: {e}", exc_info=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
