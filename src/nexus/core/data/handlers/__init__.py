from pathlib import Path
from typing import Type, Optional
import logging

# Import the handler registry and utilities from the new location
from ....handlers.base import DataHandler
from ....handlers.decorator import HANDLER_REGISTRY

_handlers_discovered = False
_discovery_context = None
logger = logging.getLogger(__name__)

def initialize_handler_discovery(context=None):
    """Initialize the handler discovery with context."""
    global _discovery_context
    _discovery_context = context

def get_handler(path: Path, handler_name: Optional[str] = None) -> DataHandler:
    """
    Gets an instantiated handler for a given path or handler name.

    This function uses the new decorator-based registry from nexus.handlers.
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
        project_root = _discovery_context.project_root if _discovery_context else None
        handler_modules = _discovery_context.run_config.get("handler_modules", ["nexus.handlers"]) if _discovery_context else []
        handler_paths = _discovery_context.run_config.get("handler_paths", ["./src/nexus/handlers"]) if _discovery_context else []
        # Use the discovery mechanism from nexus.handlers
        from ....handlers.discovery import discover_handlers
        discover_handlers(logger, project_root, handler_modules, handler_paths)
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
            raise ValueError(f"Cannot determine handler for lookup key with no file extension: {path}")
        handler_cls = HANDLER_REGISTRY.get(lookup_key)

    if not handler_cls:
        raise ValueError(f"No handler found for lookup key: '{lookup_key}' (from path: {path})")

    return handler_cls()

# Global instance that the rest of the application will use.
handler_registry = get_handler