"""
This module contains the PipelineRunner, the core engine for orchestrating plugin execution.
"""

import logging
from typing import Dict, Any, List, Tuple, get_type_hints, get_args, get_origin, Annotated, Union

from .config.manager import ConfigManager, load_yaml
from .context import NexusContext, PluginContext
from .data.hub import DataHub
from .plugin.executor import PluginExecutor
from .plugin.decorator import PLUGIN_REGISTRY
from .plugin.discovery import discover_plugins
from .plugin.typing import DataSource, DataSink

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
        discover_plugins(plugin_modules, self._logger)

    def _discover_io_declarations(self, pipeline_steps: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Dict[str, DataSource]], Dict[str, Dict[str, DataSink]]]:
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
                    else:
                        continue
                # Handle direct Annotated types
                elif get_origin(field_type) is Annotated:
                    field_metadata = get_args(field_type)[1:]  # Skip the actual type, get metadata
                else:
                    continue

                for item in field_metadata:
                    if isinstance(item, DataSource):
                        # For ConfigManager (alias -> path/handler mapping)
                        # Note: We need a unique alias. For now, let's use the path as a key if no alias is defined.
                        alias = getattr(item, 'alias', item.path)
                        if alias in base_data_sources:
                            self._logger.warning(f"Data source alias '{alias}' is declared by multiple plugins.")
                        base_data_sources[alias] = {"path": item.path, "handler_args": item.handler_args}
                        # For runner (plugin -> field -> DataSource mapping)
                        plugin_sources[plugin_name][field_name] = item

                    elif isinstance(item, DataSink):
                        plugin_sinks[plugin_name][field_name] = item

        if base_data_sources:
            self._logger.info(f"Discovered {len(base_data_sources)} data sources from plugin configs.")
        return base_data_sources, plugin_sources, plugin_sinks

    def run(self) -> None:
        self._logger.info(f"Pipeline run starting for case: {self._context.case_path.name}")

        # --- 1. Configuration Setup Phase ---
        global_config_path = self._context.project_root / "config" / "global.yaml"
        global_config = load_yaml(global_config_path)
        case_config = load_yaml(self._context.case_path / "case.yaml")
        pipeline_steps = case_config.get("pipeline", [])

        if not pipeline_steps:
            self._logger.warning("Pipeline is empty. Nothing to run.")
            return

        # --- 1a. Dependency Discovery Phase ---
        discovered_sources, plugin_sources, plugin_sinks = self._discover_io_declarations(pipeline_steps)

        # --- 1b. Config Merging ---
        config_manager = ConfigManager(
            global_config=global_config, case_config=case_config,
            plugin_registry=PLUGIN_REGISTRY, discovered_data_sources=discovered_sources,
            case_path=self._context.case_path, project_root=self._context.project_root,
            cli_args=self._context.run_config.get('cli_args', {})
        )

        # --- 1c. Data Loading ---
        final_data_sources = config_manager.get_data_sources()
        self._context.data_hub.add_data_sources(final_data_sources)
        self._logger.info(f"DataHub initialized with {len(final_data_sources)} merged data sources.")

        # --- 2. Execution Phase ---
        for step_config in pipeline_steps:
            plugin_name = step_config.get("plugin")
            if not plugin_name or plugin_name not in PLUGIN_REGISTRY or not step_config.get("enable", True):
                continue

            self._logger.debug(f"Preparing plugin: {plugin_name}")
            plugin_spec = PLUGIN_REGISTRY[plugin_name]
            case_plugin_params = step_config.get("params", {})

            if not plugin_spec.config_model:
                self._logger.debug(f"Plugin {plugin_name} has no config model. Executing directly.")
                # Execute plugin with no config
                plugin_context = PluginContext(data_hub=self._context.data_hub, logger=self._context.logger, project_root=self._context.project_root, case_path=self._context.case_path, config=None)
                executor = PluginExecutor(plugin_spec, plugin_context)
                executor.execute() # No return value to handle
                continue

            # --- 2a. Get Raw Config & Hydrate ---
            config_dict = config_manager.get_plugin_config(
                plugin_name=plugin_name, case_plugin_config=case_plugin_params
            )

            hydrated_dict = config_dict.copy()
            sources_for_plugin = plugin_sources.get(plugin_name, {})
            for field_name, source_marker in sources_for_plugin.items():
                # The alias used here must match the one used in discovery
                alias = getattr(source_marker, 'alias', source_marker.path)
                self._logger.debug(f"Hydrating field '{field_name}' with data source '{alias}'.")
                hydrated_dict[field_name] = self._context.data_hub.get(alias)

            # --- 2b. Validate and Instantiate Pydantic Model ---
            try:
                config_object = plugin_spec.config_model(**hydrated_dict)
                self._logger.debug(f"Successfully created config object for {plugin_name}")
            except Exception as e:
                self._logger.error(f"Configuration validation failed for plugin '{plugin_name}': {e}")
                raise

            # --- 2c. Execute Plugin ---
            plugin_context = PluginContext(
                data_hub=self._context.data_hub, logger=self._context.logger,
                project_root=self._context.project_root, case_path=self._context.case_path,
                config=config_object
            )

            try:
                executor = PluginExecutor(plugin_spec, plugin_context)
                return_value = executor.execute()
            except Exception:
                self._logger.critical(f"A critical error occurred in plugin '{plugin_name}'. Halting pipeline.", exc_info=True)
                raise

            # --- 2d. Handle Output ---
            sinks_for_plugin = plugin_sinks.get(plugin_name, {})
            if not sinks_for_plugin:
                if return_value is not None:
                    self._logger.debug(f"Plugin '{plugin_name}' returned a value but has no DataSink declared.")
                continue

            if len(sinks_for_plugin) > 1:
                self._logger.warning(f"Plugin '{plugin_name}' has multiple DataSinks defined. Only one is supported per plugin. Using the first one found.")

            # Get the first (and only) sink
            sink_field, sink_marker = list(sinks_for_plugin.items())[0]

            if return_value is None:
                self._logger.warning(f"Plugin '{plugin_name}' has a DataSink for field '{sink_field}' but returned None.")
                continue

            self._logger.info(f"Plugin '{plugin_name}' produced output. Writing to sink: {sink_marker.path}")
            try:
                # We need to resolve the path relative to the case directory
                output_path = self._context.case_path / sink_marker.path
                self._context.data_hub.save(
                    data=return_value,
                    path=output_path,
                    handler_args=sink_marker.handler_args
                )
                self._logger.debug(f"Successfully wrote output to {output_path}")
            except Exception as e:
                self._logger.error(f"Failed to write output for plugin '{plugin_name}' to {sink_marker.path}: {e}", exc_info=True)
                raise

        self._logger.info("Pipeline run finished successfully.")
