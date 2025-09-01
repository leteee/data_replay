import logging
import json
from pathlib import Path
import inspect
import yaml

from .execution_context import ExecutionContext
from .plugin_config_processor import process_plugin_configuration, extract_plugin_config_entry
from ..plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

class PluginExecutor:
    """
    Handles the execution of a single plugin within a given ExecutionContext.
    """
    def __init__(self, context: ExecutionContext):
        self.context = context

    def execute(self, plugin_class: type[BasePlugin]):
        """
        Prepares the configuration for and runs a single plugin instance.
        """
        logger.info(f"--- Running {plugin_class.__name__} for case: {self.context.case_path.name} ---")

        # 1. Extract the specific config entry for this plugin from the case config
        plugin_config_entry = extract_plugin_config_entry(self.context.case_config, plugin_class)
        if plugin_config_entry is None:
            raise ValueError(f"Plugin '{plugin_class.__name__}' not found in the pipeline of '{self.context.case_path / 'case.yaml'}'")

        # 2. Process the configuration (merge, substitute variables)
        # First, get the plugin's default config to find its default data sources
        plugin_default_yaml_path = Path(inspect.getfile(plugin_class)).with_suffix('.yaml')
        with open(plugin_default_yaml_path, 'r', encoding='utf-8') as f:
            plugin_default_config = yaml.safe_load(f)

        # Merge the plugin's default data sources into the DataHub
        plugin_data_sources = plugin_default_config.get('data_sources', {})
        self.context.data_hub.add_data_sources(plugin_data_sources)

        final_plugin_config = process_plugin_configuration(
            plugin_class=plugin_class,
            plugin_config_entry=plugin_config_entry,
            case_config=self.context.case_config,
            case_path=self.context.case_path,
            project_root=self.context.project_root
        )

        # 3. Instantiate and run the plugin
        try:
            plugin_instance = plugin_class(config=final_plugin_config)
            plugin_instance.run(self.context.data_hub)
            logger.info(f"--- Finished Run for {plugin_class.__name__} ---")
            logger.debug(f"\n====== Final DataHub State after {plugin_class.__name__} ======")
            logger.debug(json.dumps(self.context.data_hub.summary(), indent=2, ensure_ascii=False))
            logger.debug("==========================================================")
        except Exception as e:
            logger.error(f"An error occurred while executing plugin '{plugin_class.__name__}': {e}", exc_info=True)
            raise