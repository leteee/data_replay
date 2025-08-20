import sys
from pathlib import Path
import importlib
from utils.config_manager import ConfigManager
from utils.logger import setup_logger
from modules.datahub import DataHub

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class PipelineRunner:
    def __init__(self, case_cfg_path="cases/case1/case.yaml"):
        self.cfg = ConfigManager(case_cfg=case_cfg_path)
        self.case_name = Path(case_cfg_path).parent.name
        self.logger = setup_logger(self.cfg, case_dir=f"{self.case_name}_demo")
        self.hub = DataHub()
        self.plugins = []

    def load_plugins(self):
        plugin_list = self.cfg.get("plugins", [])
        for plugin_info in plugin_list:
            path = plugin_info.get("path")
            enabled = plugin_info.get("enabled", True)
            cfg = plugin_info.get("cfg", {})
            if not enabled:
                self.logger.info(f"[PipelineRunner] Plugin {path} is disabled, skip")
                continue
            try:
                mod_path, cls_name = path.rsplit(".", 1)
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                instance = cls()
                self.plugins.append({"instance": instance, "cfg": cfg, "name": cls_name})
                self.logger.info(f"[PipelineRunner] Loaded plugin {path}")
            except Exception as e:
                self.logger.error(f"[PipelineRunner] Failed to load plugin {path}: {e}")

    def run_all(self):
        for plugin in self.plugins:
            inst = plugin["instance"]
            cfg = plugin["cfg"]
            self.logger.info(f"[PipelineRunner] Running plugin {plugin['name']}")
            if hasattr(inst, "load"):
                inst.load(cfg.get("file", None), cfg, self.logger)
                self.hub.add_signal(plugin['name'], inst)
            elif hasattr(inst, "run"):
                inst.run(self.hub, cfg, self.logger)

    def run_plugin(self, plugin_name):
        for plugin in self.plugins:
            if plugin["name"] == plugin_name:
                inst = plugin["instance"]
                cfg = plugin["cfg"]
                self.logger.info(f"[PipelineRunner] Running plugin {plugin_name} independently")
                if hasattr(inst, "load"):
                    inst.load(cfg.get("file", None), cfg, self.logger)
                    self.hub.add_signal(plugin_name, inst)
                elif hasattr(inst, "run"):
                    inst.run(self.hub, cfg, self.logger)
                return
        self.logger.warning(f"[PipelineRunner] Plugin {plugin_name} not found")
