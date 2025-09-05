from pathlib import Path
from typing import Any
import shutil

from .base import DataHandler
from .decorator import handler

@handler(name="file", extensions=[])
class FileHandler(DataHandler):
    """
    A handler that returns a file handle (file-like object) for direct streaming or processing.
    It does not load the entire file content into memory.
    """
    file_extension = None # This handler is generic and should be specified by name

    def load(self, path: Path) -> Any:
        """Returns a file handle to the specified path in read-binary mode."""
        return open(path, 'rb')

    def save(self, data: Any, path: Path):
        """
        Saves data to the given path. Expects 'data' to be a file-like object or bytes.
        Note: This handler is primarily for loading file handles. Saving might require
        specific handling based on the type of 'data' provided.
        """
        if isinstance(data, (bytes, bytearray)):
            with open(path, 'wb') as f:
                f.write(data)
        elif hasattr(data, 'read'): # Assume it's a file-like object
            with open(path, 'wb') as f_out:
                shutil.copyfileobj(data, f_out)
        else:
            raise TypeError("FileHandler save method expects bytes or a file-like object.")
