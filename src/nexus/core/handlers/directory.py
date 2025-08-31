"""
Directory handler for managing directory-based data sources.
"""

from pathlib import Path
from typing import Any
import logging

from .base import DataHandler

logger = logging.getLogger(__name__)

class DirectoryHandler(DataHandler):
    """
    Handler for directory-based data sources.
    Simply returns the absolute path to the directory.
    """
    
    file_extension = ".dir"  # Directory handler uses .dir extension
    
    def load(self, path: Path) -> Path:
        """
        Return the absolute path to the directory.
        
        Args:
            path: Path to the directory
            
        Returns:
            Absolute Path object to the directory
        """
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        logger.info(f"Returning directory path: {path}")
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
        logger.info(f"Ensured directory exists: {path}")