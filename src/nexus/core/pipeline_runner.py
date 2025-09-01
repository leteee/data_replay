import logging
import json
from typing import Dict, Any

from .execution_context import ExecutionContext
from .plugin_executor import PluginExecutor
from .plugin_helper import find_plugin_class
from ..plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

class PipelineRunner:
    """
    Orchestrates the execution of a series of plugins as defined in a case configuration.
    """
    def __init__(self, project_root: str, case_path: str, cli_args: Dict[str, Any] = None):
        self.project_root = project_root
        self.case_path = case_path
        self.cli_args = cli_args or {}

        # The new ExecutionContext handles all the setup.
        self.context = ExecutionContext(project_root=self.project_root, case_path=self.case_path)

    def run(self):
        """Runs the entire pipeline from start to finish."""
        logger.info(f"Starting pipeline for case: {self.context.case_path.name}")

        pipeline_steps = self.context.case_config.get('pipeline', [])
        if not pipeline_steps:
            logger.warning("Pipeline is empty. Nothing to run.")
            return self.context.data_hub

        # The PluginExecutor handles the details of running a single plugin.
        executor = PluginExecutor(context=self.context)

        for plugin_entry in pipeline_steps:
            plugin_name = plugin_entry.get('plugin') or list(plugin_entry.keys())[0]
            plugin_class = find_plugin_class(plugin_name)

            if plugin_class:
                executor.execute(plugin_class)
            else:
                logger.error(f"Plugin '{plugin_name}' not found, skipping...")
                # Decide if we should raise an error and stop, or just continue
                # For now, we'll raise an error to be safe.
                raise ValueError(f"Plugin '{plugin_name}' defined in pipeline not found.")

        logger.info(f"Pipeline for case '{self.context.case_path.name}' finished successfully.")
        return self.context.data_hub