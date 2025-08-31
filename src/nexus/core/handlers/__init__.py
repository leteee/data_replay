from pathlib import Path
from typing import Dict, Type
import importlib
import inspect
import pkgutil

from .base import DataHandler

class HandlerRegistry:
    """
    Manages and provides access to different data handlers.
    """
    def __init__(self):
        self._handlers_by_ext: Dict[str, Type[DataHandler]] = {}
        self._handlers_by_name: Dict[str, Type[DataHandler]] = {}
        self.discover_handlers()

    def register_handler(self, handler_cls: Type[DataHandler]):
        """Registers a handler class."""
        if not handler_cls.file_extension:
            return
        
        self._handlers_by_ext[handler_cls.file_extension.lower()] = handler_cls
        self._handlers_by_name[handler_cls.__name__] = handler_cls
        
    def discover_handlers(self):
        """Dynamically discovers and registers handlers from this directory."""
        package_path = Path(__file__).parent
        
        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            if module_name == 'base':
                continue
            
            module = importlib.import_module(f".{module_name}", package=__name__)
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, DataHandler) and obj is not DataHandler:
                    self.register_handler(obj)

    def get_handler(self, path: Path, handler_name: str = None) -> DataHandler:
        """
        Gets an instantiated handler.
        If handler_name is provided, it gets the handler by its class name or full class path.
        Otherwise, it gets the handler based on the file extension of the path.
        """
        handler_cls = None
        if handler_name:
            if "." in handler_name:
                # Assume it's a full module.class_name path
                module_path, class_name = handler_name.rsplit('.', 1)
                try:
                    module = importlib.import_module(module_path)
                    handler_cls = getattr(module, class_name)
                except (ImportError, AttributeError) as e:
                    raise ValueError(f"Could not load handler '{handler_name}' as a module path: {e}")
            else:
                # Assume it's a simple class name, look up in registered handlers
                handler_cls = self._handlers_by_name.get(handler_name)
            
            if not handler_cls:
                raise ValueError(f"No handler registered with name or path: {handler_name}")
        else:
            suffix = path.suffix.lower()
            handler_cls = self._handlers_by_ext.get(suffix)
            if not handler_cls:
                raise ValueError(f"No handler registered for file type: {suffix}")
        
        return handler_cls()


# Global instance of the registry for easy access
handler_registry = HandlerRegistry()
