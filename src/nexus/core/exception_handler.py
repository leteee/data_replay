"""
Global exception handler for the Nexus data processing framework.

This module provides a centralized exception handling mechanism that can
process framework exceptions and provide appropriate responses based on
the exception type and context.
"""

import logging
import sys
from typing import Optional, Type
from .exceptions import (
    BaseFrameworkException, 
    ConfigurationException,
    DataException,
    PluginException,
    ValidationException,
    FrameworkException
)


class GlobalExceptionHandler:
    """
    Centralized exception handler for the framework.
    
    This class provides methods to handle exceptions in a consistent manner
    and can be configured to provide different behaviors based on the 
    exception type and severity.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def handle_exception(self, exc: Exception, context: Optional[dict] = None) -> None:
        """
        Handle an exception based on its type and severity.
        
        Args:
            exc: The exception to handle
            context: Additional context information
        """
        # Add context to exception if it's a framework exception
        if isinstance(exc, BaseFrameworkException) and context:
            exc.context.update(context)
            
        # Handle based on exception type
        if isinstance(exc, ConfigurationException):
            self._handle_configuration_exception(exc)
        elif isinstance(exc, DataException):
            self._handle_data_exception(exc)
        elif isinstance(exc, PluginException):
            self._handle_plugin_exception(exc)
        elif isinstance(exc, ValidationException):
            self._handle_validation_exception(exc)
        elif isinstance(exc, FrameworkException):
            self._handle_framework_exception(exc)
        else:
            self._handle_generic_exception(exc)
            
    def _handle_configuration_exception(self, exc: ConfigurationException) -> None:
        """Handle configuration-related exceptions."""
        self.logger.error(f"Configuration error: {exc}", exc_info=True)
        
    def _handle_data_exception(self, exc: DataException) -> None:
        """Handle data-related exceptions."""
        self.logger.error(f"Data error: {exc}", exc_info=True)
        
    def _handle_plugin_exception(self, exc: PluginException) -> None:
        """Handle plugin-related exceptions."""
        self.logger.error(f"Plugin error: {exc}", exc_info=True)
        
    def _handle_validation_exception(self, exc: ValidationException) -> None:
        """Handle validation-related exceptions."""
        self.logger.error(f"Validation error: {exc}", exc_info=True)
        
    def _handle_framework_exception(self, exc: FrameworkException) -> None:
        """Handle framework-related exceptions."""
        self.logger.critical(f"Framework error: {exc}", exc_info=True)
        
    def _handle_generic_exception(self, exc: Exception) -> None:
        """Handle generic exceptions."""
        self.logger.error(f"Unexpected error: {exc}", exc_info=True)
        
    def format_exception_details(self, exc: Exception) -> dict:
        """
        Format exception details for structured logging.
        
        Args:
            exc: The exception to format
            
        Returns:
            Dictionary with structured exception information
        """
        details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
        if isinstance(exc, BaseFrameworkException):
            details["context"] = exc.context
            details["timestamp"] = exc.timestamp.isoformat()
            
        return details


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