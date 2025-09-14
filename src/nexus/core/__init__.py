"""
Core module for the Nexus data processing framework.

This module provides the fundamental components and utilities that form
the foundation of the framework.
"""

from .exceptions import (
    NexusError,
    ConfigurationError,
    PluginError
)

from .exception_handler import (
    GlobalExceptionHandler,
    handle_exception,
    default_exception_handler
)

__all__ = [
    # Exceptions
    'NexusError',
    'ConfigurationError',
    'PluginError',
    
    # Exception Handler
    'GlobalExceptionHandler',
    'handle_exception',
    'default_exception_handler'
]
