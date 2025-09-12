"""
This module contains the PipelineRunner, the core engine for orchestrating plugin execution.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, get_type_hints, get_args, get_origin, Annotated, Union, Type
import pandas as pd

from .config.manager import ConfigManager, load_yaml
from .context import NexusContext, PluginContext
from .data.hub import DataHub
from .data.handlers.base import DataHandler
from .data.handlers import handler_registry
from .plugin.executor import PluginExecutor
from .plugin.decorator import PLUGIN_REGISTRY
from .plugin.discovery import discover_plugins
from .plugin.typing import DataSource, DataSink
from .exceptions import (
    PluginExecutionException,
    PluginConfigurationException,
    DataException,
    DataSourceException
)
from .exception_handler import handle_exception

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Orchestrates a pipeline run by discovering I/O, loading data, executing plugins,
    and handling their output.
    """

    def __init__(self, context: NexusContext):
        self._context = context
        self._logger = context.logger
        plugin_modules = self._context.run_config.get("plugin_modules", [])
        if not plugin_modules:
            self._logger.warning("No 'plugin_modules' defined in config. No plugins will be loaded.")
        # Pass additional parameters to plugin discovery
        from .plugin.discovery import discover_plugins
        discover_plugins(
            plugin_modules, 
            self._logger, 
            self._context.project_root,
            self._context.run_config.get("plugin_paths", [])
        )

    def _preflight_type_check(self, data_source_name: str, source_config: dict, handler: DataHandler) -> bool:
        """
        Performs a pre-flight type check to ensure the data type produced by a Handler
        matches the type expected by the plugin.
        
        Args:
            data_source_name: Name of the data source
            source_config: Configuration for the data source including expected_type
            handler: The data handler instance
            
        Returns:
            True if type check passes, False otherwise
        """
        expected_type = source_config.get("expected_type")
        if expected_type is None:
            self._logger.debug(f"No expected type for data source '{data_source_name}', skipping type check.")
            return True
            
        # Get the handler's produced type
        produced_type = getattr(handler, 'produced_type', None)
        if produced_type is None:
            self._logger.warning(f"Handler '{handler.__class__.__name__}' does not declare a produced_type. Skipping type check for '{data_source_name}'.")
            return True
            
        # Perform type compatibility check
        # For now, we'll do a simple check. In the future, this could be more sophisticated.
        if expected_type == produced_type:
            self._logger.debug(f"Type check passed for '{data_source_name}': {expected_type}")
            return True
        elif expected_type == pd.DataFrame and produced_type == pd.DataFrame:
            self._logger.debug(f"Type check passed for '{data_source_name}': DataFrame")
            return True
        else:
            self._logger.warning(f"Type mismatch for '{data_source_name}': expected {expected_type}, got {produced_type}")
            return False

    def _discover_io_declarations(self, pipeline_steps: List[Dict[str, Any]], case_config: dict) -> Tuple[Dict[str, Any], Dict[str, Dict[str, DataSource]], Dict[str, Dict[str, DataSink]]]:
        """
        Pre-scans active plugins to discover DataSource and DataSink declarations.

        Returns:
            A tuple containing:
            - A dictionary of discovered data sources for the ConfigManager.
            - A dictionary mapping plugin names to their DataSource fields.
            - A dictionary mapping plugin names to their DataSink fields.
        """
        base_data_sources = {}
        plugin_sources = {}
        plugin_sinks = {}

        # Get io_mapping from case_config
        io_mapping = case_config.get("io_mapping", {})
        self._logger.debug(f"io_mapping: {io_mapping}")

        for step_config in pipeline_steps:
            plugin_name = step_config.get("plugin")
            if not plugin_name or plugin_name not in PLUGIN_REGISTRY or not step_config.get("enable", True):
                continue

            plugin_spec = PLUGIN_REGISTRY[plugin_name]
            if not plugin_spec.config_model:
                continue

            plugin_sources[plugin_name] = {}
            plugin_sinks[plugin_name] = {}

            try:
                # Use get_type_hints to correctly resolve forward references (e.g., from __future__ import annotations)
                type_hints = get_type_hints(plugin_spec.config_model, include_extras=True)
            except (NameError, TypeError) as e:
                self._logger.error(f"Could not resolve type hints for {plugin_name}'s config: {e}")
                continue

            for field_name, field_type in type_hints.items():
                # Handle Union types (like Optional[Annotated[...]])
                field_args = get_args(field_type)
                # If it's a Union, we need to check the first argument (the Annotated type)
                if field_args and get_origin(field_type) is Union:
                    # Check if the first argument is Annotated
                    if get_origin(field_args[0]) is Annotated:
                        field_metadata = get_args(field_args[0])[1:]  # Skip the actual type, get metadata
                        # Get the actual type for type checking
                        actual_type = get_args(field_args[0])[0]
                    else:
                        continue
                # Handle direct Annotated types
                elif get_origin(field_type) is Annotated:
                    field_metadata = get_args(field_type)[1:]  # Skip the actual type, get metadata
                    # Get the actual type for type checking
                    actual_type = get_args(field_type)[0]
                else:
                    continue

                for item in field_metadata:
                    if isinstance(item, DataSource):
                        # For ConfigManager (name -> path/handler mapping)
                        # Note: We need a unique name. For now, let's use the name attribute.
                        name = item.name
                        self._logger.debug(f"Found DataSource with name: {name}")
                        if name in base_data_sources:
                            self._logger.warning(f"Data source name '{name}' is declared by multiple plugins.")
                        
                        # Get path and handler from io_mapping
                        source_config = io_mapping.get(name, {})
                        self._logger.debug(f"Source config for '{name}': {source_config}")
                        path = source_config.get("path", "")
                        handler = source_config.get("handler", "")
                        self._logger.debug(f"Path for '{name}': {path}")
                        self._logger.debug(f"Handler for '{name}': {handler}")
                        
                        # Build handler_args
                        handler_args = item.handler_args.copy() if item.handler_args else {}
                        if handler:
                            handler_args["name"] = handler
                        
                        base_data_sources[name] = {
                            "path": path,
                            "handler_args": handler_args,
                            "expected_type": actual_type  # Store expected type for pre-flight check
                        }
                        self._logger.debug(f"Added to base_data_sources: {name} -> {base_data_sources[name]}")
                        # For runner (plugin -> field -> DataSource mapping)
                        plugin_sources[plugin_name][field_name] = item

                    elif isinstance(item, DataSink):
                        plugin_sinks[plugin_name][field_name] = item

        if base_data_sources:
            self._logger.info(f"Discovered {len(base_data_sources)} data sources from plugin configs.")
        return base_data_sources, plugin_sources, plugin_sinks

    def run(self, plugin_name: str | None = None) -> None:
        if plugin_name:
            self._logger.info(f"Single plugin run starting for '{plugin_name}' in case: {self._context.case_path.name}")
        else:
            self._logger.info(f"Pipeline run starting for case: {self._context.case_path.name}")

        # --- 1. Configuration Setup Phase ---
        global_config_path = self._context.project_root / "config" / "global.yaml"
        global_config = load_yaml(global_config_path)
        case_config = load_yaml(self._context.case_path / "case.yaml")
        self._logger.debug(f"case_config: {case_config}")
        
        pipeline_steps = case_config.get("pipeline", [])
        if plugin_name:
            pipeline_steps = [step for step in pipeline_steps if step.get("plugin") == plugin_name]
            if not pipeline_steps:
                self._logger.error(f"Plugin '{plugin_name}' not found in the case configuration.")
                return

        if not pipeline_steps:
            self._logger.warning("Pipeline is empty. Nothing to run.")
            return

        # --- 1a. Dependency Discovery Phase ---
        discovered_sources, plugin_sources, plugin_sinks = self._discover_io_declarations(pipeline_steps, case_config)

        # --- 1b. Config Merging ---
        config_manager = ConfigManager(
            global_config=global_config, case_config=case_config,
            plugin_registry=PLUGIN_REGISTRY, discovered_data_sources=discovered_sources,
            case_path=self._context.case_path, project_root=self._context.project_root,
            cli_args=self._context.run_config.get('cli_args', {})
        )

        # --- 1c. Data Loading & Pre-flight Type Checking ---
        final_data_sources = config_manager.get_data_sources()
        self._context.data_hub.add_data_sources(final_data_sources)
        self._logger.info(f"DataHub initialized with {len(final_data_sources)} merged data sources.")
        
        # Perform pre-flight type checks
        for name, source_config in final_data_sources.items():
            try:
                handler = handler_registry.get_handler(Path(source_config["path"]), source_config["handler_args"].get("name"))
                self._preflight_type_check(name, source_config, handler)
            except Exception as e:
                self._logger.warning(f"Could not perform pre-flight type check for '{name}': {e}")

        # --- 2. Execution Phase ---
        for step_config in pipeline_steps:
            p_name = step_config.get("plugin")
            if not p_name or p_name not in PLUGIN_REGISTRY or not step_config.get("enable", True):
                continue

            self._logger.debug(f"Preparing plugin: {p_name}")
            plugin_spec = PLUGIN_REGISTRY[p_name]
            case_plugin_params = step_config.get("params", {})

            if not plugin_spec.config_model:
                self._logger.debug(f"Plugin {p_name} has no config model. Executing directly.")
                # Execute plugin with no config
                plugin_context = PluginContext(data_hub=self._context.data_hub, logger=self._context.logger, project_root=self._context.project_root, case_path=self._context.case_path, config=None)
                executor = PluginExecutor(plugin_spec, plugin_context)
                executor.execute() # No return value to handle
                continue

            # --- 2a. Get Raw Config & Hydrate ---
            config_dict = config_manager.get_plugin_config(
                plugin_name=p_name, case_plugin_config=case_plugin_params
            )

            hydrated_dict = config_dict.copy()
            sources_for_plugin = plugin_sources.get(p_name, {})
            for field_name, source_marker in sources_for_plugin.items():
                # The name used here must match the one used in discovery
                name = source_marker.name
                self._logger.debug(f"Hydrating field '{field_name}' with data source '{name}'.")
                hydrated_dict[field_name] = self._context.data_hub.get(name)

            # --- 2b. Validate and Instantiate Pydantic Model ---
            try:
                config_object = plugin_spec.config_model(**hydrated_dict)
                self._logger.debug(f"Successfully created config object for {p_name}")
            except Exception as e:
                error_context = {
                    "plugin_name": p_name,
                    "config_model": plugin_spec.config_model.__name__ if plugin_spec.config_model else "None"
                }
                exc = PluginConfigurationException(
                    f"Configuration validation failed for plugin '{p_name}': {e}",
                    context=error_context,
                    cause=e
                )
                handle_exception(exc, error_context)
                raise exc

            # --- 2c. Resolve Output Path ---
            resolved_output_path = None
            sinks_for_plugin = plugin_sinks.get(p_name, {})
            if sinks_for_plugin:
                if len(sinks_for_plugin) > 1:
                    self._logger.warning(f"Plugin '{p_name}' has multiple DataSinks defined. Only one is supported for path injection. Using the first one found.")
                
                # Get the first (and only) sink
                _sink_field, sink_marker = list(sinks_for_plugin.items())[0]

                # Resolve the path
                io_mapping = case_config.get("io_mapping", {})
                sink_config = io_mapping.get(sink_marker.name, {})
                output_path_str = sink_config.get("path", "")
                if output_path_str:
                    resolved_output_path = self._context.case_path / output_path_str
                else:
                    self._logger.warning(f"DataSink '{sink_marker.name}' for plugin '{p_name}' has no path defined in io_mapping.")

            # --- 2d. Execute Plugin ---
            plugin_context = PluginContext(
                data_hub=self._context.data_hub, logger=self._context.logger,
                project_root=self._context.project_root, case_path=self._context.case_path,
                config=config_object,
                output_path=resolved_output_path  # Pass the resolved path
            )

            try:
                executor = PluginExecutor(plugin_spec, plugin_context)
                return_value = executor.execute()
            except Exception as e:
                error_context = {
                    "plugin_name": p_name,
                    "plugin_spec": plugin_spec.name if plugin_spec else "Unknown"
                }
                exc = PluginExecutionException(
                    f"A critical error occurred in plugin '{p_name}'. Halting pipeline.",
                    context=error_context,
                    cause=e
                )
                handle_exception(exc, error_context)
                raise exc

            # --- 2e. Handle Output ---
            if not sinks_for_plugin:
                if return_value is not None:
                    self._logger.debug(f"Plugin '{p_name}' returned a value but has no DataSink declared.")
                continue

            if len(sinks_for_plugin) > 1:
                self._logger.warning(f"Plugin '{p_name}' has multiple DataSinks defined. Only one is supported per plugin. Using the first one found.")

            # Get the first (and only) sink
            sink_field, sink_marker = list(sinks_for_plugin.items())[0]

            if return_value is None:
                # This is now expected for plugins that write directly to disk
                self._logger.debug(f"Plugin '{p_name}' has a DataSink for field '{sink_field}' but returned None.")
                continue

            self._logger.info(f"Plugin '{p_name}' produced output. Writing to sink: {sink_marker.name}")
            try:
                # We need to resolve the path relative to the case directory
                # Get the io_mapping from case_config
                io_mapping = case_config.get("io_mapping", {})
                sink_config = io_mapping.get(sink_marker.name, {})
                output_path_str = sink_config.get("path", "")
                output_path = self._context.case_path / output_path_str
                handler_args = sink_config.get("handler_args", sink_marker.handler_args)
                self._context.data_hub.save(
                    data=return_value,
                    path=output_path,
                    handler_args=handler_args
                )
                self._logger.debug(f"Successfully wrote output to {output_path}")
            except Exception as e:
                error_context = {
                    "plugin_name": p_name,
                    "sink_name": sink_marker.name if sink_marker else "Unknown",
                    "output_path": str(output_path) if 'output_path' in locals() else "Unknown"
                }
                exc = DataSinkException(
                    f"Failed to write output for plugin '{p_name}' to {sink_marker.name if sink_marker else 'Unknown'}: {e}",
                    context=error_context,
                    cause=e
                )
                handle_exception(exc, error_context)
                raise exc

        self._logger.info("Pipeline run finished successfully.")