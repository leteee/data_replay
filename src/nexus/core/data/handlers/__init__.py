from pathlib import Path
from typing import Type, Optional
import logging

from .base import DataHandler
from .decorator import HANDLER_REGISTRY
from .discovery import discover_handlers

_handlers_discovered = False
logger = logging.getLogger(__name__)

def get_handler(path: Path, handler_name: Optional[str] = None) -> DataHandler:
    """
    Gets an instantiated handler for a given path or handler name.

    This function uses the new decorator-based registry.
    Discovery of handlers is performed automatically on the first call.

    Args:
        path (Path): The file path to get a handler for (used for extension-based lookup).
        handler_name (str, optional): The specific name of the handler to use.
                                      This takes precedence over the path's extension.

    Returns:
        DataHandler: An instantiated data handler.
    
    Raises:
        ValueError: If a suitable handler cannot be found.
    """
    global _handlers_discovered
    if not _handlers_discovered:
        # This check ensures that discovery only runs once per process.
        discover_handlers(logger)
        _handlers_discovered = True

    handler_cls: Optional[Type[DataHandler]] = None
    lookup_key = ""

    # Look up by specific name first, as it has precedence.
    if handler_name:
        lookup_key = handler_name
        handler_cls = HANDLER_REGISTRY.get(handler_name)
    # Otherwise, look up by file extension.
    else:
        lookup_key = path.suffix.lower()
        if not lookup_key:
            raise ValueError(f"Cannot determine handler for path with no file extension: {path}")
        handler_cls = HANDLER_REGISTRY.get(lookup_key)

    if not handler_cls:
        raise ValueError(f"No handler found for lookup key: '{lookup_key}' (from path: {path})")

    return handler_cls()


# To maintain a consistent interface for the rest of the codebase (e.g., DataHub),
# we can provide a simple wrapper object that exposes the get_handler function.
class _RegistryWrapper:
    """A simple object that mimics the old registry's get_handler method."""
    def get_handler(self, path: Path, handler_name: Optional[str] = None) -> DataHandler:
        return get_handler(path, handler_name)

# The global instance that the rest of the application will use.
handler_registry = _RegistryWrapper()