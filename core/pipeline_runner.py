import importlib
import importlib.util
from pathlib import Path
import yaml
import pandas as pd
import logging # Import logging module

from core.config_manager import ConfigManager
from core.logger import setup_logger, get_logger # Import get_logger

class PipelineRunner:
    """
    The main orchestrator for running data replay pipelines.
    It reads a case configuration, discovers and loads plugins, and executes
    the pipeline steps sequentially, handling data persistence as configured.
    """
    def __init__(self, case_path: str, cli_args: dict = None):
        # 1. Get a basic logger immediately for early logging
        self.logger = get_logger(__name__)

        self.case_path = Path(case_path)
        self.project_root = self.case_path.parent.parent # Assumes cases/case_name structure
        self.context = {"results": {}} # Initialize the context

        # Initialize the configuration manager for this run
        self.config_manager = ConfigManager(project_root=str(self.project_root), cli_args=cli_args)

        # 2. Setup global logger based on config (now that config_manager is ready)
        setup_logger(self.config_manager.global_config.get('logging', {}), self.case_path.name)
        
        # Load the case configuration
        self.case_config = load_yaml(self.case_path / "case.yaml")

        # Discover all available plugins
        self.plugin_map = self._find_plugins()
        self.logger.info(f"发现 {len(self.plugin_map)} 个可用插件。")

    def _find_plugins(self) -> dict:
        """
        Scans the 'modules' directory to build a map of available plugins.
        The map links a simple class name to its file path and module path.
        """
        plugin_map = {}
        modules_root = self.project_root / "modules"
        for py_file in modules_root.rglob("*.py"):
            if py_file.name.startswith(("__", "base_")):
                continue
            
            # Convention: ClassName is PascalCase version of file_name.py
            class_name = py_file.stem.replace("_", " ").title().replace(" ", "")
            
            # Convention: module.path is derived from file path
            module_path = ".".join(py_file.relative_to(self.project_root).with_suffix('').parts)

            plugin_map[class_name] = {
                "file_path": str(py_file),
                "module_path": module_path
            }
        return plugin_map

    def _load_plugin_class(self, plugin_identifier: str):
        """
        Loads a plugin class using either a simple name or a full module path.
        Returns the PluginClass and its file_path.
        """
        if "." in plugin_identifier:
            # Full path provided (e.g., modules.quality.demo_check.DemoCheck)
            module_path, class_name = plugin_identifier.rsplit('.', 1)
            module = importlib.import_module(module_path)
            # We need the file path to load the default config
            # This assumes the module path directly corresponds to a file path
            file_path = str(self.project_root / Path(module_path.replace('.', '/')) / f"{class_name.lower()}.py")
            return getattr(module, class_name), file_path
        else:
            # Simple name provided (e.g., DemoCheck)
            if plugin_identifier not in self.plugin_map:
                raise ValueError(f"在 {self.project_root / 'modules'} 中找不到插件: {plugin_identifier}")
            
            plugin_info = self.plugin_map[plugin_identifier]
            file_path = plugin_info["file_path"]
            
            spec = importlib.util.spec_from_file_location(plugin_identifier, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, plugin_identifier), file_path

    def run(self):
        """
        Executes the entire pipeline as defined in the case configuration.
        """
        pipeline_steps = self.case_config.get("pipeline", [])
        self.logger.info(f"开始执行流水线，共 {len(pipeline_steps)} 个步骤。")

        for i, step_config in enumerate(pipeline_steps):
            plugin_identifier = step_config["plugin"]
            self.logger.info(f"\n--- 步骤 {i+1}/{len(pipeline_steps)}: 执行插件 [{plugin_identifier}] ---")

            # 1. Dynamically load the plugin class and get its file path
            PluginClass, plugin_file_path = self._load_plugin_class(plugin_identifier)

            # 2. Get final config for this plugin instance
            case_override_config = step_config.get("config", {})
            
            # Inject case_path into the config for the plugin
            case_override_config['case_path'] = str(self.case_path)

            final_config = self.config_manager.get_plugin_config(
                plugin_module_path=plugin_file_path,
                case_config_override=case_override_config
            )

            # 3. Inject logger into context for the plugin
            self.context['logger'] = get_logger(plugin_identifier) # Logger named after the plugin

            # 4. Instantiate and run the plugin
            plugin_instance = PluginClass(config=final_config)
            self.context = plugin_instance.run(self.context)

            # 5. Handle persistence
            if step_config.get("persist", False):
                output_path_str = step_config.get("output_path")
                if not output_path_str:
                    self.logger.error(f"插件 {plugin_identifier} 被设置为持久化，但未提供 'output_path'。")
                    continue

                output_path = Path(output_path_str)
                if not output_path.is_absolute():
                    output_path = self.case_path / output_path
                
                output_path.parent.mkdir(parents=True, exist_ok=True)

                if isinstance(self.context.get("data"), pd.DataFrame):
                    self.context["data"].to_parquet(output_path)
                    self.logger.info(f"结果已持久化到: {output_path}")
                    self.context["data"] = str(output_path)
                else:
                    self.logger.warning(f"插件 {plugin_identifier} 被设置为持久化，但其输出 context['data'] 不是DataFrame。")

        self.logger.info("\n--- 流水线执行完毕 ---")
        return self.context

def load_yaml(file_path):
    path = Path(file_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f) or {}
