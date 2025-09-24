from typing import Callable, Dict, List, Type

from .base import DataHandler

# Global registry for all discovered handlers
HANDLER_REGISTRY: Dict[str, Type[DataHandler]] = {}

def handler(name: str, extensions: List[str]) -> Callable:
    """
    A decorator to register a DataHandler class.

    Args:
        name (str): The primary unique name for the handler (e.g., 'csv').
        extensions (List[str]): A list of file extensions the handler is responsible for (e.g., ['.csv']).
    """
    def decorator(cls: Type[DataHandler]) -> Type[DataHandler]:
        if not issubclass(cls, DataHandler):
            raise TypeError("The decorated class must be a subclass of DataHandler.")

        # Register by primary name
        if name in HANDLER_REGISTRY:
            raise ValueError(f"Handler name '{name}' is already registered.")
        HANDLER_REGISTRY[name] = cls

        # Register by file extensions
        for ext in extensions:
            if ext in HANDLER_REGISTRY:
                raise ValueError(f"Handler for extension '{ext}' is already registered.")
            HANDLER_REGISTRY[ext] = cls
        
        return cls
    return decorator
