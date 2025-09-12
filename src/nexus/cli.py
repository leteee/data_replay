import argparse
import logging
from pathlib import Path
import json
import shutil
import sys
from typing import Optional
import typer

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from nexus.core.pipeline_runner import PipelineRunner
from nexus.core.data.hub import DataHub
from nexus.core.context import NexusContext
from nexus.core.config.manager import ConfigManager, load_yaml
from nexus.scripts.demo_data import generate_data
from nexus.scripts.docgen import generate_plugin_documentation
from nexus.core.logger import initialize_logging
from nexus.core.plugin.decorator import PLUGIN_REGISTRY
from nexus.core.plugin.discovery import discover_plugins
from nexus.core.plugin.executor import PluginExecutor
from nexus.core.exceptions import (
    BaseFrameworkException,
    PluginExecutionException,
    PluginNotFoundException
)
from nexus.core.exception_handler import handle_exception

app = typer.Typer(help="Data Replay Framework CLI")

logger = logging.getLogger(__name__)

def version_callback(value: bool):
    if value:
        print(f"Nexus Framework Version: 0.1.0")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show the application version and exit."),
):
    """
    Main callback for the CLI. Initializes logging.
    """
    initialize_logging()

@app.command()
def pipeline(
    case: str = typer.Option(..., "--case", help="Name of the case directory under 'cases/' (e.g., 'demo')"),
    templates: Optional[str] = typer.Option(None, "--templates", help="Name of the template to use for creating the case (e.g., 'demo')"),
):
    """
    Run a full pipeline for a given case.
    If --templates is specified, create the case from a template before running.
    """
    global_config = load_yaml(project_root / "config" / "global.yaml")
    cases_root_str = global_config.get("cases_root", "cases")
    cases_root = Path(cases_root_str)
    if not cases_root.is_absolute():
        cases_root = (project_root / cases_root).resolve()

    case_arg_path = Path(case)
    case_path = case_arg_path if case_arg_path.is_absolute() else cases_root / case_arg_path

    # If templates option is specified, create the case from template
    if templates:
        template_path = project_root / "templates" / f"{templates}_case.yaml"
        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            raise typer.Exit(code=1)
        
        # Create case directory if it doesn't exist
        case_path.mkdir(parents=True, exist_ok=True)
        
        # Copy template to case directory
        destination_path = case_path / "case.yaml"
        shutil.copy2(template_path, destination_path)
        logger.info(f"Created case '{case}' from template '{templates}' at {destination_path}")

    if not case_path.is_dir():
        logger.error(f"Case path not found: {case_path}")
        raise typer.Exit(code=1)

    logger.info(f"====== Running Case: {case_path.name} ======")

    run_config = {
        "cli_args": {},
        "plugin_modules": global_config.get("plugin_modules", []),
        "plugin_paths": global_config.get("plugin_paths", []),
        "handler_paths": global_config.get("handler_paths", [])
    }

    nexus_context = NexusContext(
        project_root=project_root,
        case_path=case_path,
        data_hub=None,  # Will be set after creation
        logger=logger,
        run_config=run_config
    )
    
    data_hub = DataHub(case_path=case_path, logger=logger, context=nexus_context)
    nexus_context.data_hub = data_hub

    try:
        runner = PipelineRunner(nexus_context)
        runner.run()
        logger.info(f"====== Case '{case_path.name}' finished successfully. ======")
    except BaseFrameworkException as e:
        handle_exception(e)
        raise typer.Exit(code=1)
    except Exception as e:
        error_context = {
            "command": "pipeline",
            "case_path": str(case_path)
        }
        exc = PluginExecutionException(
            f"A critical error occurred during pipeline execution: {e}",
            context=error_context,
            cause=e
        )
        handle_exception(exc, error_context)
        raise typer.Exit(code=1)

@app.command()
def plugin(
    name: str = typer.Argument(..., help="Name of the plugin to run"),
    case: str = typer.Option(..., "--case", help="Name of the case directory under 'cases/' (e.g., 'demo')"),
):
    """
    Run a single plugin from a case definition.
    Note: User must ensure all required input data exists before running.
    """
    global_config = load_yaml(project_root / "config" / "global.yaml")
    cases_root_str = global_config.get("cases_root", "cases")
    cases_root = Path(cases_root_str)
    if not cases_root.is_absolute():
        cases_root = (project_root / cases_root).resolve()

    case_arg_path = Path(case)
    case_path = case_arg_path if case_arg_path.is_absolute() else cases_root / case_arg_path

    if not case_path.is_dir():
        logger.error(f"Case path not found: {case_path}")
        raise typer.Exit(code=1)

    logger.info(f"====== Running Plugin: {name} in Case: {case_path.name} ======")

    run_config = {
        "cli_args": {},
        "plugin_modules": global_config.get("plugin_modules", []),
        "plugin_paths": global_config.get("plugin_paths", []),
        "handler_paths": global_config.get("handler_paths", [])
    }

    nexus_context = NexusContext(
        project_root=project_root,
        case_path=case_path,
        data_hub=None,  # Will be set after creation
        logger=logger,
        run_config=run_config
    )
    
    data_hub = DataHub(case_path=case_path, logger=logger, context=nexus_context)
    nexus_context.data_hub = data_hub

    try:
        runner = PipelineRunner(nexus_context)
        runner.run(plugin_name=name)
        logger.info(f"====== Plugin '{name}' finished successfully. ======")
    except BaseFrameworkException as e:
        handle_exception(e)
        raise typer.Exit(code=1)
    except Exception as e:
        error_context = {
            "command": "plugin",
            "plugin_name": name,
            "case_path": str(case_path)
        }
        exc = PluginExecutionException(
            f"A critical error occurred during plugin execution: {e}",
            context=error_context,
            cause=e
        )
        handle_exception(exc, error_context)
        raise typer.Exit(code=1)

@app.command(name="generate-data")
def generate_data_cmd():
    """
    Generate sample data for demos.
    """
    logger.info("Generating demo data...")
    try:
        generate_data()
        logger.info("Successfully generated demo data.")
    except BaseFrameworkException as e:
        handle_exception(e)
        raise typer.Exit(code=1)
    except Exception as e:
        error_context = {
            "command": "generate-data"
        }
        exc = BaseFrameworkException(
            f"An error occurred during data generation: {e}",
            context=error_context,
            cause=e
        )
        handle_exception(exc, error_context)
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
    except BaseFrameworkException as e:
        handle_exception(e)
        raise typer.Exit(code=1)
    except Exception as e:
        error_context = {
            "command": "docs"
        }
        exc = BaseFrameworkException(
            f"An error occurred during doc generation: {e}",
            context=error_context,
            cause=e
        )
        handle_exception(exc, error_context)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()