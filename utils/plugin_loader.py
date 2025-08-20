import importlib
import logging
from pathlib import Path

class PluginLoader:
    def __init__(self, plugin_dir="modules"):
        self.plugin_dir = Path(plugin_dir)
        self.logger = logging.getLogger("PluginLoader")

    def load_module(self, module_type, module_name):
        module_path = f"modules.{module_type}.{module_name}"
        try:
            mod = importlib.import_module(module_path)
            self.logger.info(f"[PluginLoader] Loaded {module_type}.{module_name}")
            return mod
        except ModuleNotFoundError:
            self.logger.error(f"[PluginLoader] Module not found: {module_path}")
            return None
        except Exception as e:
            self.logger.error(f"[PluginLoader] Failed to load {module_path}: {e}")
            return None

    def list_plugins(self, module_type):
        folder = self.plugin_dir / module_type
        if not folder.exists():
            return []
        return [f.stem for f in folder.glob("*.py") if f.stem != "__init__"]
