"""
Core module for the Nexus data processing framework.

This module provides the fundamental components and utilities that form
the foundation of the framework.
"""

from .exceptions import (
    BaseFrameworkException,
    ConfigurationException,
    InvalidConfigurationException,
    MissingConfigurationException,
    DataException,
    DataSourceException,
    DataSinkException,
    DataHandlerException,
    PluginException,
    PluginNotFoundException,
    PluginExecutionException,
    PluginConfigurationException,
    ValidationException,
    FrameworkException,
    InitializationException,
    ExecutionContextException
)

from .exception_handler import (
    GlobalExceptionHandler,
    handle_exception,
    default_exception_handler
)

__all__ = [
    # Exceptions
    'BaseFrameworkException',
    'ConfigurationException',
    'InvalidConfigurationException',
    'MissingConfigurationException',
    'DataException',
    'DataSourceException',
    'DataSinkException',
    'DataHandlerException',
    'PluginException',
    'PluginNotFoundException',
    'PluginExecutionException',
    'PluginConfigurationException',
    'ValidationException',
    'FrameworkException',
    'InitializationException',
    'ExecutionContextException',
    
    # Exception Handler
    'GlobalExceptionHandler',
    'handle_exception',
    'default_exception_handler'
]