"""
Custom exceptions for the dependency injection system.
"""

from typing import Any, Dict, Optional
from ..exceptions import NexusError


class DIException(NexusError):
    """Base exception for dependency injection related errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        service_type: Optional[str] = None,
        target_type: Optional[str] = None
    ):
        super().__init__(message, context, cause)
        self.service_type = service_type
        self.target_type = target_type
