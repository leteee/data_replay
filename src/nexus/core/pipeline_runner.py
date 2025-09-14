"""
This module contains the PipelineRunner, the core engine for orchestrating plugin execution.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
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
    NexusError,
    ConfigurationError,
    PluginError
)
from .exception_handler import handle_exception
from .di import container, LoggerInterface, DataHubInterface, ConfigManagerInterface, ServiceNotFoundError
from .di.container import ServiceNotFoundError
from .di.adapters import LoggerAdapter, DataHubAdapter, ConfigManagerAdapter
from .services.io_discovery import IODiscoveryService
from .services.type_checker import TypeChecker
from .services.plugin_execution import PluginExecutionService
from .services.configuration import ConfigurationService

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Orchestrates a pipeline run by discovering I/O, loading data, executing plugins,
    and handling their output.
    """

    def __init__(self, context: NexusContext):
        self._context = context
        # Use DI container for logger if available, otherwise use direct injection
        try:
            self._logger = container.resolve(LoggerInterface)
        except ServiceNotFoundError:
            # This is expected if the service is not registered
            self._logger = context.logger
        except Exception as e:
            # Log unexpected errors but continue with direct injection
            self._logger = context.logger
            self._logger.warning(f"Unexpected error resolving logger from DI container: {e}")
            
        # Try to get ConfigManager from DI container
        try:
            self._config_manager = container.resolve(ConfigManagerInterface)
        except ServiceNotFoundError:
            # This is expected if the service is not registered
            self._config_manager = None
        except Exception as e:
            # Log unexpected errors but continue with direct injection
            self._logger.warning(f"Unexpected error resolving config manager from DI container: {e}")
            self._config_manager = None
            
        # Create service instances
        self._io_discovery_service = IODiscoveryService(self._logger)
        self._type_checker = TypeChecker(self._logger)
        self._plugin_execution_service = PluginExecutionService(self._logger)
        self._configuration_service = ConfigurationService(self._logger)
            
        plugin_modules = self._context.run_config.get("plugin_modules", [])
        if not plugin_modules:
            self._logger.warning("No 'plugin_modules' defined in config. No plugins will be loaded.")
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
        return self._type_checker.preflight_type_check(data_source_name, source_config, handler)

    def _discover_io_declarations(self, pipeline_steps: List[Dict[str, Any]], case_config: dict) -> Tuple[Dict[str, Any], Dict[str, Dict[str, DataSource]], Dict[str, Dict[str, DataSink]]]:
        """
        Pre-scans active plugins to discover DataSource and DataSink declarations.

        Returns:
            A tuple containing:
            - A dictionary of discovered data sources for the ConfigManager.
            - A dictionary mapping plugin names to their DataSource fields.
            - A dictionary mapping plugin names to their DataSink fields.
        """
        return self._io_discovery_service.discover_io_declarations(pipeline_steps, case_config)

    def run(self, plugin_name: str | None = None) -> None:
        if plugin_name:
            self._logger.info(f"Single plugin run starting for '{plugin_name}' in case: {self._context.case_path.name}")
        else:
            self._logger.info(f"Pipeline run starting for case: {self._context.case_path.name}")

        # --- 1. Configuration Setup Phase ---
        # We need the raw case_config to resolve the io_mapping
        raw_case_config = self._configuration_service.load_case_config(self._context.case_path)
        
        pipeline_steps = raw_case_config.get("pipeline", [])
        pipeline_steps = self._configuration_service.filter_pipeline_steps(pipeline_steps, plugin_name)

        if not pipeline_steps:
            if plugin_name:
                self._logger.error(f"Plugin '{plugin_name}' not found in the case configuration.")
                return
            else:
                self._logger.warning("Pipeline is empty. Nothing to run.")
                return

        # --- 1a. Dependency Discovery Phase ---
        discovered_sources, plugin_sources, plugin_sinks = self._discover_io_declarations(pipeline_steps, raw_case_config)

        # --- 1b. Config Merging ---
        if self._config_manager is not None:
            # Use DI-injected config manager
            config_manager = self._config_manager
        else:
            # Create config manager directly
            config_manager = self._configuration_service.create_config_manager(
                project_root=self._context.project_root,
                case_path=self._context.case_path,
                discovered_sources=discovered_sources,
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
                exc = ConfigurationError(
                    f"Configuration validation failed for plugin '{p_name}': {e}"
                )
                # Add context to the exception manually since ValueError doesn't accept it in constructor
                if hasattr(exc, 'context'):
                    exc.context.update(error_context)
                else:
                    exc.context = error_context
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
                io_mapping = raw_case_config.get("io_mapping", {})
                sink_config = io_mapping.get(sink_marker.name, {})
                output_path_str = sink_config.get("path", "")
                if output_path_str:
                    resolved_output_path = self._context.case_path / output_path_str
                else:
                    self._logger.warning(f"DataSink '{sink_marker.name}' for plugin '{p_name}' has no path defined in io_mapping.")

            # --- 2d. Execute Plugin ---
            return_value = self._plugin_execution_service.execute_plugin(
                plugin_name=p_name,
                plugin_spec=plugin_spec,
                config_object=config_object,
                data_hub=self._context.data_hub,
                case_path=self._context.case_path,
                project_root=self._context.project_root,
                resolved_output_path=resolved_output_path
            )

            # --- 2e. Handle Output ---
            self._plugin_execution_service.handle_plugin_output(
                plugin_name=p_name,
                return_value=return_value,
                sinks_for_plugin=sinks_for_plugin,
                raw_case_config=raw_case_config,
                case_path=self._context.case_path,
                data_hub=self._context.data_hub
            )

        self._logger.info("Pipeline run finished successfully.")