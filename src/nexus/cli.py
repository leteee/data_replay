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

logger = logging.getLogger(__name__)

app = typer.Typer(help="Data Replay Framework CLI")

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

    try:
        runner = PipelineRunner(nexus_context)
        runner.run()
        logger.info(f"====== Case '{case_path.name}' finished successfully. ======")
    except Exception as e:
        logger.critical(f"A critical error occurred during pipeline execution: {e}", exc_info=True)
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

    logger.info(f"====== Running Plugin: {name} ======")

    # Discover plugins
    plugin_modules = global_config.get("plugin_modules", [])
    discover_plugins(plugin_modules, logger)
    
    # Check if plugin exists
    if name not in PLUGIN_REGISTRY:
        logger.error(f"Plugin '{name}' not found.")
        raise typer.Exit(code=1)
    
    plugin_spec = PLUGIN_REGISTRY[name]
    
    # Create DataHub and context
    data_hub = DataHub(case_path=case_path, logger=logger)
    
    run_config = {
        "cli_args": {},
        "plugin_modules": plugin_modules
    }
    
    # Create a minimal PipelineRunner to handle configuration setup for single plugin
    nexus_context = NexusContext(
        project_root=project_root,
        cases_root=cases_root,
        case_path=case_path,
        data_hub=data_hub,
        logger=logger,
        run_config=run_config
    )
    
    # Create a PipelineRunner to handle configuration discovery and data loading
    runner = PipelineRunner(nexus_context)
    
    # Get case config
    case_config = load_yaml(case_path / "case.yaml")
    pipeline_steps = case_config.get("pipeline", [])
    
    # Find the plugin config in the pipeline
    plugin_config = {}
    for step in pipeline_steps:
        if step.get("plugin") == name:
            plugin_config = step.get("config", {})
            break
    
    try:
        # Handle plugin execution
        if not plugin_spec.config_model:
            logger.debug(f"Plugin {name} has no config model. Executing directly.")
            from nexus.core.context import PluginContext
            plugin_context = PluginContext(
                data_hub=data_hub,
                logger=logger,
                project_root=project_root,
                case_path=case_path,
                config=None
            )
            executor = PluginExecutor(plugin_spec, plugin_context)
            executor.execute()
        else:
            # For plugins with config models, we need to set up configuration like in full pipeline
            # 1. Discover IO declarations for this single plugin
            single_plugin_pipeline = [{"plugin": name, "enable": True}]
            discovered_sources, plugin_sources, plugin_sinks = runner._discover_io_declarations(single_plugin_pipeline)
            
            # 2. Config Merging for single plugin
            config_manager = ConfigManager(
                global_config=global_config, case_config=case_config,
                plugin_registry=PLUGIN_REGISTRY, discovered_data_sources=discovered_sources,
                case_path=case_path, project_root=project_root,
                cli_args=run_config.get('cli_args', {})
            )
            
            # 3. Data Loading
            final_data_sources = config_manager.get_data_sources()
            data_hub.add_data_sources(final_data_sources)
            logger.debug(f"DataHub initialized with {len(final_data_sources)} merged data sources.")
            
            # 4. Get Raw Config & Hydrate for single plugin
            config_dict = config_manager.get_plugin_config(
                plugin_name=name, case_plugin_config=plugin_config
            )
            
            hydrated_dict = config_dict.copy()
            sources_for_plugin = plugin_sources.get(name, {})
            for field_name, source_marker in sources_for_plugin.items():
                # The alias used here must match the one used in discovery
                alias = getattr(source_marker, 'alias', source_marker.path)
                logger.debug(f"Hydrating field '{field_name}' with data source '{alias}'.")
                hydrated_dict[field_name] = data_hub.get(alias)
            
            # 5. Validate and Instantiate Pydantic Model
            try:
                config_object = plugin_spec.config_model(**hydrated_dict)
                logger.debug(f"Successfully created config object for {name}")
            except Exception as e:
                logger.error(f"Configuration validation failed for plugin '{name}': {e}")
                raise
            
            # 6. Execute Plugin
            from nexus.core.context import PluginContext
            plugin_context = PluginContext(
                data_hub=data_hub,
                logger=logger,
                project_root=project_root,
                case_path=case_path,
                config=config_object
            )
            
            executor = PluginExecutor(plugin_spec, plugin_context)
            return_value = executor.execute()
            
            # 7. Handle Output (simplified)
            sinks_for_plugin = plugin_sinks.get(name, {})
            if sinks_for_plugin and return_value is not None:
                # Get the first (and only) sink
                sink_field, sink_marker = list(sinks_for_plugin.items())[0]
                logger.info(f"Plugin '{name}' produced output. Writing to sink: {sink_marker.path}")
                try:
                    # We need to resolve the path relative to the case directory
                    output_path = case_path / sink_marker.path
                    data_hub.save(
                        data=return_value,
                        path=output_path,
                        handler_args=sink_marker.handler_args
                    )
                    logger.debug(f"Successfully wrote output to {output_path}")
                except Exception as e:
                    logger.error(f"Failed to write output for plugin '{name}' to {sink_marker.path}: {e}", exc_info=True)
                    raise
                
        logger.info(f"====== Plugin '{name}' finished successfully. ======")
    except Exception as e:
        logger.critical(f"A critical error occurred during plugin execution: {e}", exc_info=True)
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