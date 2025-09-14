"""
Framework exception hierarchy for the Nexus data processing framework.

This module defines a simplified, flatter exception hierarchy that favors
built-in exceptions where possible.
"""

from typing import Any, Dict, Optional


class NexusError(Exception):
    """
    Base exception class for all framework-specific errors.
    
    Provides common functionality for capturing context to aid in debugging.
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
        
    def __str__(self) -> str:
        base_msg = self.message
        if self.context:
            context_str = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            base_msg += f" (Context: {context_str})"
        return base_msg
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, context={self.context!r})"


# For configuration errors, we can use ValueError directly
ConfigurationError = ValueError

# For plugin errors, we can use RuntimeError directly
PluginError = RuntimeError
