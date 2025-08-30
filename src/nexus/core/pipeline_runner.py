import importlib
import importlib.util
import logging
from pathlib import Path
import yaml

from .config_manager import ConfigManager
from .logger import setup_logging
from .data_hub import DataHub

class PipelineRunner:
    """
    The main orchestrator for running data replay pipelines.
    It reads a case configuration, discovers and loads plugins, and executes
    the pipeline steps sequentially.
    """
    def __init__(self, project_root: str, case_path: str, cli_args: dict = None):
        self.project_root = Path(project_root).resolve()
        self.case_path = Path(case_path).resolve()

        setup_logging(case_name=self.case_path.name)
        self.logger = logging.getLogger(__name__)

        self.case_config = load_yaml(self.case_path / "case.yaml")
        
        data_sources = self.case_config.get("data_sources", {})
        self.data_hub = DataHub(case_path=self.case_path, data_sources=data_sources)
        
        self.config_manager = ConfigManager(project_root=str(self.project_root), cli_args=cli_args)
        self.plugin_map = self._find_plugins()
        self.logger.info(f"Found {len(self.plugin_map)} available plugins.")

    def _find_plugins(self) -> dict:
        plugin_map = {}
        modules_root = self.project_root / "src" / "nexus" / "modules"
        for py_file in modules_root.rglob("*.py"):
            if py_file.name.startswith(("__", "base_")):
                continue
            
            class_name = py_file.stem.replace("_", " ").title().replace(" ", "")
            module_path = ".".join(py_file.relative_to(self.project_root).with_suffix('').parts)
            plugin_map[class_name] = {"file_path": str(py_file), "module_path": module_path}
        return plugin_map

    def _load_plugin_class(self, plugin_identifier: str):
        if "." in plugin_identifier:
            module_path, class_name = plugin_identifier.rsplit('.', 1)
            module = importlib.import_module(module_path)
            file_path = str(self.project_root / Path(module_path.replace('.', '/')) / f"{class_name.lower()}.py")
            return getattr(module, class_name), file_path
        else:
            if plugin_identifier not in self.plugin_map:
                raise ValueError(f"Plugin not found in 'modules': {plugin_identifier}")
            
            plugin_info = self.plugin_map[plugin_identifier]
            file_path = plugin_info["file_path"]
            
            spec = importlib.util.spec_from_file_location(plugin_info["module_path"], file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, plugin_identifier), file_path

    def run(self):
        """
        Executes the entire pipeline as defined in the case configuration.
        """
        pipeline_steps = self.case_config.get("pipeline", [])
        self.logger.info(f"Starting pipeline execution with {len(pipeline_steps)} steps.")

        for i, step_config in enumerate(pipeline_steps):
            plugin_identifier = step_config["plugin"]
            self.logger.info(f"\n--- Step {i+1}/{len(pipeline_steps)}: Executing Plugin [{plugin_identifier}] ---")

            PluginClass, plugin_file_path = self._load_plugin_class(plugin_identifier)

            # Merge the plugin-specific config from the pipeline step into the final config
            # This allows overriding default plugin configs per step
            case_override_config = step_config.get("config", {})
            case_override_config['case_path'] = str(self.case_path)

            final_config = self.config_manager.get_plugin_config(
                plugin_module_path=plugin_file_path,
                case_config_override=case_override_config
            )

            # Add inputs and outputs from the step config to the final_config
            # so the plugin can access them
            if 'inputs' in step_config:
                final_config['inputs'] = step_config['inputs']
            if 'outputs' in step_config:
                final_config['outputs'] = step_config['outputs']

            # Instantiate and run the plugin, passing the DataHub
            plugin_instance = PluginClass(config=final_config)
            plugin_instance.run(self.data_hub)

        self.logger.info("\n--- Pipeline execution finished ---")
        return self.data_hub

def load_yaml(file_path):
    path = Path(file_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f) or {}
