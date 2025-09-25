from logging import Logger
from pathlib import Path
from typing import List

def discover_handlers(logger: Logger, project_root: Path = None, additional_paths: List[str] = None) -> None:
    """
    Scans handler paths to find and import all modules,
    which triggers the @handler decorators to register themselves.
    
    This is now a compatibility wrapper that delegates to the new discovery module.
    """
    # Import and delegate to the new discovery module
    from ....handlers.discovery import discover_handlers as new_discover_handlers
    new_discover_handlers(logger, project_root, additional_paths)