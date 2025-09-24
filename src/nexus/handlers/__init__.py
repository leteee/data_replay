"""
Nexus Framework Built-in Handlers Package

This package contains the built-in data handlers for the Nexus framework.
"""

# Import submodules to make them available at package level
from . import base
from . import csv
from . import decorator
from . import directory
from . import discovery
from . import file
from . import json
from . import parquet

__all__ = [
    "base",
    "csv",
    "decorator",
    "directory",
    "discovery",
    "file",
    "json",
    "parquet"
]