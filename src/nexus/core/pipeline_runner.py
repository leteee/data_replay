import logging
import json
import inspect
from typing import Dict, Any
from pathlib import Path

from .config_manager import ConfigManager, load_yaml
from .execution_context import NexusContext, PluginContext
from .plugin_executor import PluginExecutor
from .plugin_decorator import PLUGIN_REGISTRY
from .plugin_discovery import discover_plugins

logger = logging.getLogger(__name__)


class PipelineRunner:
    def __init__(self, context: NexusContext):
        self._context = context
        self._logger = context.logger
        self._config_manager = ConfigManager(str(context.project_root))
        # Discover and register plugins upon initialization
        discover_plugins(self._logger)

    def run(self) -> None:
        self._logger.info("Pipeline run starting.")
        pipeline_steps = self._context.run_config.get("pipeline", [])

        if not pipeline_steps:
            self._logger.warning("Pipeline is empty. Nothing to run.")
            return

        for step_config in pipeline_steps:
            plugin_name = step_config.get("plugin")
            if not plugin_name:
                self._logger.error("Pipeline step is missing 'plugin' key. Skipping.")
                continue

            if plugin_name not in PLUGIN_REGISTRY:
                self._logger.error(f"Plugin '{plugin_name}' not found in registry. Skipping.")
                continue

            plugin_spec = PLUGIN_REGISTRY[plugin_name]
            plugin_params = step_config.get("params", {})

            # Get the fully merged configuration for the plugin
            plugin_module = inspect.getmodule(plugin_spec.func)
            if plugin_module is None:
                raise TypeError(f"Could not determine module for plugin '{plugin_name}'")
            plugin_module_path = plugin_module.__file__
            if plugin_module_path is None:
                 raise TypeError(f"Could not determine module path for plugin '{plugin_name}'")

            final_config = self._config_manager.get_plugin_config(
                plugin_module_path=plugin_module_path,
                case_config_override=plugin_params
            )

            # Add plugin's default data sources to DataHub
            plugin_default_config = load_yaml(Path(plugin_module_path).with_suffix('.yaml'))
            self._context.data_hub.add_data_sources(plugin_default_config.get("data_sources", {}))

            # Create the specific context for this plugin instance
            plugin_context = PluginContext(
                data_hub=self._context.data_hub,
                logger=self._context.logger,
                project_root=self._context.project_root,
                case_path=self._context.case_path,
                config=final_config
            )

            try:
                executor = PluginExecutor(plugin_spec, plugin_context)
                executor.execute()
            except Exception as e:
                self._logger.critical(
                    f"A critical error occurred in plugin '{plugin_name}'. Halting pipeline."
                )
                # Re-raise the exception to stop the pipeline
                raise

        self._logger.info("Pipeline run finished successfully.")
