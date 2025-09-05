"""
Directory handler for managing directory-based data sources.
"""

from pathlib import Path
from typing import Any
import logging

from .base import DataHandler
from .decorator import handler

logger = logging.getLogger(__name__)

@handler(name="dir", extensions=[])
class DirectoryHandler(DataHandler):
    """
    Handler for directory-based data sources.
    Simply returns the absolute path to the directory.
    """
    handles_directories = True
    
    def load(self, path: Path) -> Path:
        """
        Ensure the directory exists and return its absolute path.
        
        Args:
            path: Path to the directory
            
        Returns:
            Absolute Path object to the directory
        """
        # For a directory data source, 'loading' means ensuring it exists.
        # This is typically used for output directories.
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists (load): {path}")
        return path.absolute()
    
    def save(self, data: Any, path: Path) -> None:
        """
        Create directory if it doesn't exist.
        
        Args:
            data: Data to save (ignored for directory handler)
            path: Path to the directory
        """
        # For directory handler, we just ensure the directory exists
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists (save): {path}")