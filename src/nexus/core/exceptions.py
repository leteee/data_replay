"""
Framework exception hierarchy for the Nexus data processing framework.

This module defines a comprehensive set of custom exceptions that provide
structured error handling throughout the framework. Each exception includes
context information to aid in debugging and troubleshooting.
"""

from typing import Any, Dict, Optional
import traceback


class BaseFrameworkException(Exception):
    """
    Base exception class for all framework exceptions.
    
    Provides common functionality for error context and structured error reporting.
    """
    
    def __init__(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause
        self.timestamp = __import__('datetime').datetime.now()
        
    def __str__(self) -> str:
        base_msg = self.message
        if self.context:
            context_str = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            base_msg += f" (Context: {context_str})"
        return base_msg
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, context={self.context!r})"
        
    def get_full_traceback(self) -> str:
        """Get full traceback information including cause if present."""
        if self.cause:
            return f"{traceback.format_exc()}\nCaused by: {repr(self.cause)}\n{traceback.format_exception(type(self.cause), self.cause, self.cause.__traceback__)}"
        return traceback.format_exc()


# Configuration Exceptions
class ConfigurationException(BaseFrameworkException):
    """Base exception for configuration-related errors."""
    pass


class InvalidConfigurationException(ConfigurationException):
    """Raised when configuration values are invalid."""
    pass


class MissingConfigurationException(ConfigurationException):
    """Raised when required configuration is missing."""
    pass


# Data Exceptions
class DataException(BaseFrameworkException):
    """Base exception for data-related errors."""
    pass


class DataSourceException(DataException):
    """Raised when there are issues with data sources."""
    pass


class DataSinkException(DataException):
    """Raised when there are issues with data sinks."""
    pass


class DataHandlerException(DataException):
    """Raised when there are issues with data handlers."""
    pass


# Plugin Exceptions
class PluginException(BaseFrameworkException):
    """Base exception for plugin-related errors."""
    pass


class PluginNotFoundException(PluginException):
    """Raised when a requested plugin cannot be found."""
    pass


class PluginExecutionException(PluginException):
    """Raised when a plugin fails during execution."""
    pass


class PluginConfigurationException(PluginException):
    """Raised when there are issues with plugin configuration."""
    pass


# Validation Exceptions
class ValidationException(BaseFrameworkException):
    """Raised when data or configuration validation fails."""
    pass


# Framework Exceptions
class FrameworkException(BaseFrameworkException):
    """Base exception for general framework errors."""
    pass


class InitializationException(FrameworkException):
    """Raised when framework initialization fails."""
    pass


class ExecutionContextException(FrameworkException):
    """Raised when there are issues with the execution context."""
    pass