import logging
import json
import inspect
from typing import Dict, Any
from pathlib import Path

from .config.manager import ConfigManager, load_yaml
from .context import NexusContext, PluginContext
from .plugin.executor import PluginExecutor
from .plugin.decorator import PLUGIN_REGISTRY
from .plugin.discovery import discover_plugins

logger = logging.getLogger(__name__)


class PipelineRunner:
    def __init__(self, context: NexusContext):
        self._context = context
        self._logger = context.logger
        # Discover and register plugins upon initialization
        plugin_modules = self._context.run_config.get("plugin_modules", [])
        if not plugin_modules:
            self._logger.warning("No 'plugin_modules' defined in config. No plugins will be loaded.")
        discover_plugins(plugin_modules, self._logger)

    def run(self) -> None:
        self._logger.info(f"Pipeline run starting for case: {self._context.case_path.name}")

        # --- 1. Configuration Setup Phase ---
        self._logger.debug("Entering configuration setup phase.")
        
        # Load base configs
        global_config_path = self._context.project_root / "config" / "global.yaml"
        global_config = load_yaml(global_config_path)
        case_config = load_yaml(self._context.case_path / "case.yaml")
        pipeline_steps = case_config.get("pipeline", [])

        if not pipeline_steps:
            self._logger.warning("Pipeline is empty. Nothing to run.")
            return

        # Collect all default configs for unique plugins in the pipeline
        plugin_default_configs = []
        plugin_default_configs_map = {}  # Cache for use in the loop
        unique_plugin_names = {step['plugin'] for step in pipeline_steps if 'plugin' in step}

        for name in unique_plugin_names:
            if name not in PLUGIN_REGISTRY:
                self._logger.warning(f"Plugin '{name}' is defined in pipeline but not found in registry. It will be skipped.")
                continue
            
            spec = PLUGIN_REGISTRY[name]
            plugin_module = inspect.getmodule(spec.func)
            if plugin_module and plugin_module.__file__:
                module_path = Path(plugin_module.__file__)
                default_config = load_yaml(module_path.with_suffix('.yaml'))
                plugin_default_configs.append(default_config)
                plugin_default_configs_map[name] = default_config
            else:
                self._logger.warning(f"Could not determine module file for plugin '{name}'. Its default config will be ignored.")

        # Instantiate ConfigManager with all necessary configs for this run.
        # The manager will perform all merging logic internally.
        config_manager = ConfigManager(
            global_config=global_config,
            case_config=case_config,
            plugin_default_configs=plugin_default_configs,
            cli_args=self._context.run_config.get('cli_args', {}) # Pass CLI args if they exist
        )

        # Initialize DataHub with the final, merged data_sources from the single source of truth.
        final_data_sources = config_manager.get_data_sources()
        self._context.data_hub.add_data_sources(final_data_sources)
        self._logger.info(f"DataHub initialized with {len(final_data_sources)} merged data sources.")

        # --- 2. Execution Phase ---
        self._logger.debug("Entering pipeline execution phase.")
        for step_config in pipeline_steps:
            plugin_name = step_config.get("plugin")
            if not plugin_name or plugin_name not in PLUGIN_REGISTRY:
                self._logger.error(f"Pipeline step is missing a valid 'plugin' key. Skipping.")
                continue

            # Check if the plugin is enabled
            if not step_config.get("enable", True):
                self._logger.info(f"Plugin '{plugin_name}' is disabled in case config. Skipping.")
                continue

            # Get the final, merged configuration for this specific plugin instance
            case_plugin_params = step_config.get("params", {})
            plugin_default_config = plugin_default_configs_map.get(plugin_name, {})
            
            final_plugin_config = config_manager.get_plugin_config(
                plugin_default_config=plugin_default_config,
                case_plugin_config=case_plugin_params
            )

            # Create the specific context for this plugin instance
            plugin_context = PluginContext(
                data_hub=self._context.data_hub,
                logger=self._context.logger,
                project_root=self._context.project_root,
                case_path=self._context.case_path,
                config=final_plugin_config
            )

            try:
                executor = PluginExecutor(PLUGIN_REGISTRY[plugin_name], plugin_context)
                executor.execute()
            except Exception as e:
                self._logger.critical(
                    f"A critical error occurred in plugin '{plugin_name}'. Halting pipeline.",
                    exc_info=True
                )
                raise # Re-raise the exception to stop the pipeline

        self._logger.info("Pipeline run finished successfully.")