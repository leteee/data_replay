"""
Global exception handler for the Nexus data processing framework.

This module provides a centralized exception handling mechanism.
"""

import logging
import sys
from typing import Optional
from .exceptions import NexusError

# Import built-in exceptions that we're using instead of custom ones
from builtins import ValueError as ConfigurationError
from builtins import RuntimeError as PluginError


class GlobalExceptionHandler:
    """
    Centralized exception handler for the framework.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def handle_exception(self, exc: Exception, context: Optional[dict] = None) -> None:
        """
        Handle an exception based on its type.
        
        Args:
            exc: The exception to handle
            context: Additional context information
        """
        if isinstance(exc, NexusError) and context:
            exc.context.update(context)

        if isinstance(exc, ConfigurationError):
            self.logger.error(f"Configuration error: {exc}", exc_info=False) # No need for full traceback on config errors
        elif isinstance(exc, PluginError):
            self.logger.error(f"Plugin error: {exc}", exc_info=True)
        elif isinstance(exc, NexusError):
            self.logger.error(f"Framework error: {exc}", exc_info=True)
        else:
            self._handle_generic_exception(exc)
            
    def _handle_generic_exception(self, exc: Exception) -> None:
        """Handle generic exceptions."""
        self.logger.error(f"Unexpected error: {exc}", exc_info=True)


# Global instance for use throughout the framework
default_exception_handler = GlobalExceptionHandler()


def handle_exception(exc: Exception, context: Optional[dict] = None) -> None:
    """
    Convenience function to handle an exception using the default handler.
    
    Args:
        exc: The exception to handle
        context: Additional context information
    """
    default_exception_handler.handle_exception(exc, context)
