import importlib
import importlib.util
import logging
from pathlib import Path
import yaml

from .config_manager import ConfigManager
from .logger import setup_logging
from .data_hub import DataHub
from .plugin_config_processor import process_plugin_configuration, extract_plugin_config_entry

class PipelineRunner:
    """
    The main orchestrator for running data replay pipelines.
    It reads a case configuration, discovers and loads plugins, and executes
    the pipeline steps sequentially.
    """
    def __init__(self, project_root: str, case_path: str, cli_args: dict = None):
        self.project_root = Path(project_root).resolve()
        self.case_path = Path(case_path).resolve()
        self.logger = logging.getLogger(__name__)
        self.cli_args = cli_args or {}

        self.case_config = load_yaml(self.case_path / "case.yaml")
        self.config_manager = ConfigManager(project_root=str(self.project_root), cli_args=self.cli_args)
        self.plugin_map = self._find_plugins()
        self.logger.debug(f"Found {len(self.plugin_map)} available plugins.")

        # --- New DataHub Initialization Logic ---
        all_data_sources = self._get_all_data_sources()
        self.data_hub = DataHub(case_path=self.case_path, data_sources=all_data_sources)
        # --- End of New Logic ---

    def _get_all_data_sources(self) -> dict:
        """
        Collects and merges data_sources from all plugins in the pipeline and the case file.
        Case-level data_sources override plugin-level ones.
        """
        merged_sources = {}

        # 1. Collect data_sources from default plugin configs
        for plugin_config_entry in self.case_config.get('pipeline', []):
            plugin_name = plugin_config_entry['plugin']
            try:
                _, plugin_file_path = self._load_plugin_class(plugin_name)
                if plugin_file_path:
                    default_config_path = Path(plugin_file_path).with_suffix('.yaml')
                    default_config = load_yaml(default_config_path)
                    plugin_sources = default_config.get('data_sources', {})
                    # Lower priority: only add if not already present
                    for name, source in plugin_sources.items():
                        if name not in merged_sources:
                            merged_sources[name] = source
            except ValueError as e:
                self.logger.warning(f"Could not load plugin '{plugin_name}' during data_source scan: {e}")

        # 2. Merge data_sources from the case file (higher priority)
        case_sources = self.case_config.get('data_sources', {})
        merged_sources.update(case_sources)
        
        self.logger.info(f"DataHub will be initialized with {len(merged_sources)} merged data sources.")
        return merged_sources

    def _find_plugins(self) -> dict:
        plugin_map = {}
        plugins_root = self.project_root / "src" / "nexus" / "plugins"
        for py_file in plugins_root.rglob("*.py"):
            if py_file.name.startswith(("__", "base_")):
                continue
            
            class_name = py_file.stem.replace("_", " ").title().replace(" ", "")
            module_path = ".".join(py_file.relative_to(self.project_root).with_suffix('').parts)
            plugin_map[class_name] = {"file_path": str(py_file), "module_path": module_path}
        return plugin_map

    def _load_plugin_class(self, plugin_identifier: str):
        """
        Loads a plugin class using a unified, standard import mechanism.
        Args:
            plugin_identifier (str): The simple class name or full module path of the plugin.
        Returns:
            A tuple of (plugin_class, plugin_file_path)
        """
        if "." in plugin_identifier:
            # Full path provided: extract class name and module path
            module_path, class_name = plugin_identifier.rsplit('.', 1)
        else:
            # Simple name provided: look up details in the plugin map
            if plugin_identifier not in self.plugin_map:
                raise ValueError(f"Plugin '{plugin_identifier}' not found in scanned modules.")
            plugin_info = self.plugin_map[plugin_identifier]
            class_name = plugin_identifier
            module_path = plugin_info["module_path"]

        try:
            # Use the standard, robust way to import the module
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            
            # Get the file path directly from the loaded module
            file_path = Path(module.__file__)
            
            return plugin_class, file_path
        except (ImportError, AttributeError, KeyError) as e:
            raise ValueError(f"Could not load plugin '{plugin_identifier}'. Module: '{module_path}', Class: '{class_name}'. Reason: {e}")

    def run(self):
        """
        Executes the entire pipeline as defined in the case configuration.
        """
        self.logger.info(f"Starting pipeline for case: {self.case_path.name}")
        
        global_plugin_enable = self.config_manager.global_config.get('plugin_enable', True)

        for plugin_config in self.case_config.get('pipeline', []):
            plugin_name = plugin_config['plugin']
            
            plugin_enabled = plugin_config.get('enable', global_plugin_enable)

            if not plugin_enabled:
                self.logger.info(f"Skipping plugin: {plugin_name} (disabled)")
                continue

            self.logger.info(f"--- Running plugin: {plugin_name} ---")
            self.logger.info(f"PipelineRunner: Processing plugin_config: {plugin_config}") # Added log
            
            try:
                plugin_class, plugin_file_path = self._load_plugin_class(plugin_name)
                self.logger.debug(f"PipelineRunner: Loaded plugin_class: {plugin_class.__name__}, plugin_file_path: {plugin_file_path}")
                
                # Use shared configuration processing logic
                final_plugin_config = process_plugin_configuration(
                    plugin_class=plugin_class,
                    plugin_config_entry=plugin_config,
                    case_config=self.case_config,
                    case_path=self.case_path,
                    project_root=self.project_root
                )

                # Inject data_hub into the final config
                final_plugin_config['data_hub'] = self.data_hub

                plugin_instance = plugin_class(
                    config=final_plugin_config
                )
                plugin_instance.run(self.data_hub)

            except Exception as e:
                self.logger.error(f"Pipeline failed at plugin '{plugin_name}'. Reason: {e}", exc_info=True)
                break

        self.logger.info("\n--- Pipeline execution finished ---")
        return self.data_hub

def load_yaml(file_path):
    path = Path(file_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f) or {}
