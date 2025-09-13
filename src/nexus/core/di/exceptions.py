"""
Custom exceptions for the dependency injection system.
"""

from typing import Any, Dict, Optional
from ..exceptions import BaseFrameworkException


class DIException(BaseFrameworkException):
    """Base exception for dependency injection related errors."""
    pass


class ServiceResolutionException(DIException):
    """Raised when a service cannot be resolved from the container."""
    
    def __init__(
        self, 
        service_type: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.service_type = service_type
        super().__init__(message, context, cause)


class ServiceRegistrationException(DIException):
    """Raised when a service cannot be registered in the container."""
    
    def __init__(
        self, 
        service_type: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.service_type = service_type
        super().__init__(message, context, cause)


class DependencyInjectionException(DIException):
    """Raised when dependency injection fails during service creation."""
    
    def __init__(
        self, 
        target_type: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.target_type = target_type
        super().__init__(message, context, cause)