"""
This module contains the PipelineRunner, the core engine for orchestrating plugin execution.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd

from .config.functional import load_yaml, create_configuration_context, get_data_sources, get_plugin_config
from .context import NexusContext, PluginContext
from .data.hub import DataHub
from .data.handlers.base import DataHandler
from .data.handlers import handler_registry
from .plugin.executor import PluginExecutor
from .plugin.decorator import PLUGIN_REGISTRY
from .plugin.discovery import discover_plugins
from .plugin.typing import DataSource, DataSink
from .exceptions import (
    NexusError,
    ConfigurationError,
    PluginError
)
from .exception_handler import handle_exception

from .discovery.io_discovery import discover_io_declarations
from .config.utils import (
    load_case_config, 
    filter_pipeline_steps, 
    create_config_context,
    get_merged_data_sources,
    get_plugin_configuration
)
from .services.type_checker import preflight_type_check
from .services.plugin_execution import execute_plugin, handle_plugin_output

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Orchestrates a pipeline run by discovering I/O, loading data, executing plugins,
    and handling their output.
    """

    def __init__(self, context: NexusContext):
        self._context = context
        
        # Use context logger directly
        self._logger = context.logger
        
        
        
        plugin_modules = self._context.run_config.get("plugin_modules", [])
        if not plugin_modules:
            self._logger.warning("No 'plugin_modules' defined in config. No plugins will be loaded.")
        discover_plugins(
            plugin_modules, 
            self._logger, 
            self._context.project_root,
            self._context.run_config.get("plugin_paths", ["./demo"])
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
        return preflight_type_check(self._logger, data_source_name, source_config, handler)

    def _discover_io_declarations(self, pipeline_steps: List[Dict[str, Any]], case_config: dict) -> Tuple[Dict[str, Any], Dict[str, Dict[str, DataSource]], Dict[str, Dict[str, DataSink]]]:
        """
        Pre-scans active plugins to discover DataSource and DataSink declarations.

        Returns:
            A tuple containing:
            - A dictionary of discovered data sources for the ConfigManager.
            - A dictionary mapping plugin names to their DataSource fields.
            - A dictionary mapping plugin names to their DataSink fields.
        """
        return discover_io_declarations(self._logger, pipeline_steps, case_config)

    def run(self, plugin_name: str | None = None) -> None:
        """
        Run the pipeline, either for a specific plugin or the entire pipeline.
        
        Args:
            plugin_name: Optional plugin name to run individually
        """
        if plugin_name:
            self._logger.info(f"Single plugin run starting for '{plugin_name}' in case: {self._context.case_path.name}")
        else:
            self._logger.info(f"Pipeline run starting for case: {self._context.case_path.name}")

        # Step 1: Load configuration and pipeline steps
        raw_case_config, pipeline_steps = self._setup_configuration(plugin_name)
        if not pipeline_steps:
            return

        # Step 2: Discover dependencies and prepare environment
        discovered_sources, plugin_sources, plugin_sinks = self._discover_dependencies(pipeline_steps, raw_case_config)
        config_manager = self._prepare_environment(discovered_sources)
        
        # Step 3: Execute plugins
        self._execute_pipeline(pipeline_steps, plugin_sources, plugin_sinks, config_manager, raw_case_config)
        
        # Step 4: Finalize
        self._logger.info("Pipeline run finished successfully.")

    def _setup_configuration(self, plugin_name: str | None) -> tuple[dict, list]:
        """
        Setup configuration by loading case config and filtering pipeline steps.
        
        Args:
            plugin_name: Optional plugin name to run individually
            
        Returns:
            Tuple of (raw_case_config, filtered_pipeline_steps)
        """
        # Load case configuration
        raw_case_config = load_case_config(self._context.case_path)
        
        # Get and filter pipeline steps
        pipeline_steps = raw_case_config.get("pipeline", [])
        pipeline_steps = filter_pipeline_steps(pipeline_steps, plugin_name)

        if not pipeline_steps:
            if plugin_name:
                self._logger.error(f"Plugin '{plugin_name}' not found in the case configuration.")
            else:
                self._logger.warning("Pipeline is empty. Nothing to run.")
        
        return raw_case_config, pipeline_steps

    def _discover_dependencies(self, pipeline_steps: List[Dict[str, Any]], raw_case_config: dict) -> Tuple[Dict[str, Any], Dict[str, Dict[str, DataSource]], Dict[str, Dict[str, DataSink]]]:
        """
        Discover all dependencies for plugins in the pipeline.
        
        Args:
            pipeline_steps: List of pipeline step configurations
            raw_case_config: Raw case configuration
            
        Returns:
            Tuple of (discovered_sources, plugin_sources, plugin_sinks)
        """
        return self._discover_io_declarations(pipeline_steps, raw_case_config)

    def _prepare_environment(self, discovered_sources: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare the execution environment by creating configuration context.
        
        Args:
            discovered_sources: Discovered data sources
            
        Returns:
            Configuration context dictionary
        """
        # Create configuration context
        config_context = create_config_context(
            project_root=self._context.project_root,
            case_path=self._context.case_path,
            discovered_sources=discovered_sources,
            cli_args=self._context.run_config.get('cli_args', {})
        )

        # Load data into DataHub
        final_data_sources = get_merged_data_sources(config_context)
        self._context.data_hub.add_data_sources(final_data_sources)
        self._logger.info(f"DataHub initialized with {len(final_data_sources)} merged data sources.")
        
        # Perform pre-flight type checks
        for name, source_config in final_data_sources.items():
            try:
                handler = handler_registry(Path(source_config["path"]), source_config["handler_args"].get("name"))
                self._preflight_type_check(name, source_config, handler)
            except Exception as e:
                self._logger.warning(f"Could not perform pre-flight type check for '{name}': {e}")

        return config_context

    def _execute_pipeline(self, pipeline_steps: List[Dict[str, Any]], plugin_sources: Dict[str, Dict[str, DataSource]], 
                         plugin_sinks: Dict[str, Dict[str, DataSink]], config_context: Dict[str, Any], raw_case_config: dict) -> None:
        """
        Execute all plugins in the pipeline.
        
        Args:
            pipeline_steps: List of pipeline step configurations
            plugin_sources: Mapping of plugin names to their DataSource fields
            plugin_sinks: Mapping of plugin names to their DataSink fields
            config_context: Configuration context dictionary
            raw_case_config: Raw case configuration
        """
        for step_config in pipeline_steps:
            p_name = step_config.get("plugin")
            if not p_name or p_name not in PLUGIN_REGISTRY or not step_config.get("enable", True):
                continue

            self._logger.debug(f"Preparing plugin: {p_name}")
            
            try:
                self._execute_single_plugin(p_name, step_config, plugin_sources, plugin_sinks, config_context, raw_case_config)
            except Exception as e:
                self._logger.error(f"Error executing plugin '{p_name}': {e}", exc_info=True)
                # Re-raise to halt pipeline execution
                raise

    def _execute_single_plugin(self, plugin_name: str, step_config: Dict[str, Any], 
                              plugin_sources: Dict[str, Dict[str, DataSource]], 
                              plugin_sinks: Dict[str, Dict[str, DataSink]], 
                              config_context: Dict[str, Any], raw_case_config: dict) -> None:
        """
        Execute a single plugin with its configuration.
        
        Args:
            plugin_name: Name of the plugin to execute
            step_config: Configuration for the pipeline step
            plugin_sources: Mapping of plugin names to their DataSource fields
            plugin_sinks: Mapping of plugin names to their DataSink fields
            config_context: Configuration context dictionary
            raw_case_config: Raw case configuration
        """
        plugin_spec = PLUGIN_REGISTRY[plugin_name]
        case_plugin_params = step_config.get("params", {})

        # Execute plugin with no config if it doesn't have a config model
        if not plugin_spec.config_model:
            self._logger.debug(f"Plugin {plugin_name} has no config model. Executing directly.")
            plugin_context = PluginContext(
                data_hub=self._context.data_hub, 
                logger=self._context.logger, 
                project_root=self._context.project_root, 
                case_path=self._context.case_path, 
                config=None
            )
            executor = PluginExecutor(plugin_spec, plugin_context)
            executor.execute()  # No return value to handle
            return

        # Get and hydrate plugin configuration
        config_dict = get_plugin_configuration(
            plugin_name=plugin_name,
            case_plugin_config=case_plugin_params,
            config_context=config_context
        )

        # Hydrate data sources for the plugin
        hydrated_dict = config_dict.copy()
        sources_for_plugin = plugin_sources.get(plugin_name, {})
        for field_name, source_marker in sources_for_plugin.items():
            # The name used here must match the one used in discovery
            name = source_marker.name
            self._logger.debug(f"Hydrating field '{field_name}' with data source '{name}'.")
            hydrated_dict[field_name] = self._context.data_hub.get(name)

        # Validate and instantiate the Pydantic model
        try:
            config_object = plugin_spec.config_model(**hydrated_dict)
            self._logger.debug(f"Successfully created config object for {plugin_name}")
        except Exception as e:
            error_context = {
                "plugin_name": plugin_name,
                "config_model": plugin_spec.config_model.__name__ if plugin_spec.config_model else "None"
            }
            exc = ConfigurationError(
                f"Configuration validation failed for plugin '{plugin_name}': {e}"
            )
            # Add context to the exception manually since ValueError doesn't accept it in constructor
            if hasattr(exc, 'context'):
                exc.context.update(error_context)
            else:
                exc.context = error_context
            handle_exception(exc, error_context)
            raise exc

        # Resolve output path directly (simplified approach)
        resolved_output_path = None
        sinks_for_plugin = plugin_sinks.get(plugin_name, {})
        if sinks_for_plugin:
            if len(sinks_for_plugin) > 1:
                self._logger.warning(f"Plugin '{plugin_name}' has multiple DataSinks defined. Only one is supported for path injection. Using the first one found.")
            
            # Get the first sink and resolve its path
            _sink_field, sink_marker = list(sinks_for_plugin.items())[0]
            io_mapping = raw_case_config.get("io_mapping", {})
            sink_config = io_mapping.get(sink_marker.name, {})
            output_path_str = sink_config.get("path", "")
            if output_path_str:
                resolved_output_path = self._context.case_path / output_path_str
            else:
                self._logger.warning(f"DataSink '{sink_marker.name}' for plugin '{plugin_name}' has no path defined in io_mapping.")

        # Execute the plugin directly (simplified approach)
        plugin_context = PluginContext(
            data_hub=self._context.data_hub, logger=self._logger,
            project_root=self._context.project_root, case_path=self._context.case_path,
            config=config_object,
            output_path=resolved_output_path
        )

        try:
            executor = PluginExecutor(plugin_spec, plugin_context)
            return_value = executor.execute()
        except Exception as e:
            error_context = {
                "plugin_name": plugin_name,
                "plugin_spec": plugin_spec.name if plugin_spec else "Unknown"
            }
            exc = PluginError(
                f"A critical error occurred in plugin '{plugin_name}'. Halting pipeline."
            )
            # Add context to the exception manually since RuntimeError doesn't accept it in constructor
            if hasattr(exc, 'context'):
                exc.context.update(error_context)
            else:
                exc.context = error_context
            handle_exception(exc, error_context)
            raise exc

        # Handle plugin output directly (simplified approach)
        if sinks_for_plugin:
            if len(sinks_for_plugin) > 1:
                self._logger.warning(f"Plugin '{plugin_name}' has multiple DataSinks defined. Only one is supported per plugin. Using the first one found.")

            # Get the first (and only) sink
            sink_field, sink_marker = list(sinks_for_plugin.items())[0]

            if return_value is None:
                # This is now expected for plugins that write directly to disk
                self._logger.debug(f"Plugin '{plugin_name}' has a DataSink for field '{sink_field}' but returned None.")
            else:
                self._logger.info(f"Plugin '{plugin_name}' produced output. Writing to sink: {sink_marker.name}")
                try:
                    # We need to resolve the path relative to the case directory
                    # Get the io_mapping from case_config
                    io_mapping = raw_case_config.get("io_mapping", {})
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
                        "plugin_name": plugin_name,
                        "sink_name": sink_marker.name if sink_marker else "Unknown",
                        "output_path": str(output_path) if 'output_path' in locals() else "Unknown"
                    }
                    exc = NexusError(
                        f"Failed to write output for plugin '{plugin_name}' to {sink_marker.name if sink_marker else 'Unknown'}: {e}",
                        context=error_context,
                        cause=e
                    )
                    handle_exception(exc, error_context)
                    raise exc

    def _resolve_output_path(self, plugin_name: str, plugin_sinks: Dict[str, Dict[str, DataSink]], 
                             raw_case_config: dict) -> Path | None:
        """
        Resolve the output path for a plugin based on its DataSinks.
        
        Args:
            plugin_name: Name of the plugin
            plugin_sinks: Mapping of plugin names to their DataSink fields
            raw_case_config: Raw case configuration
            
        Returns:
            Resolved output path or None
        """
        # Simple, direct approach
        sinks = plugin_sinks.get(plugin_name, {})
        if not sinks:
            return None
            
        # Warn if multiple sinks but only use first
        if len(sinks) > 1:
            self._logger.warning(f"Plugin '{plugin_name}' has multiple DataSinks. Using first one.")
        
        # Get first sink and resolve path
        _, sink = list(sinks.items())[0]
        io_mapping = raw_case_config.get("io_mapping", {})
        config = io_mapping.get(sink.name, {})
        path_str = config.get("path")
        
        if path_str:
            return self._context.case_path / path_str
        return None

    def _handle_plugin_output(self, plugin_name: str, return_value: Any,
                             plugin_sinks: Dict[str, Dict[str, DataSink]],
                             raw_case_config: dict) -> None:
        """
        Handle plugin output by delegating to functional implementation.
        
        Args:
            plugin_name: Name of the plugin
            return_value: Return value from plugin execution
            plugin_sinks: Mapping of plugin names to their DataSink fields
            raw_case_config: Raw case configuration
        """
        # Simple delegation
        sinks = plugin_sinks.get(plugin_name, {})
        handle_plugin_output(
            logger=self._logger,
            plugin_name=plugin_name,
            return_value=return_value,
            sinks_for_plugin=sinks,
            raw_case_config=raw_case_config,
            case_path=self._context.case_path,
            data_hub=self._context.data_hub
        )