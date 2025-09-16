"""
Base classes for plugin configuration models.
"""

from pydantic import BaseModel
from typing import Any, Dict, Optional


class PluginConfig(BaseModel):
    """
    Base class for plugin configuration models.
    
    This class provides common configuration and utilities to reduce boilerplate
    code in plugin configuration models.
    """
    
    # Allow plugins to store additional metadata
    _plugin_metadata: Dict[str, Any] = {}
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the configuration model.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self._plugin_metadata[key] = value
        
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata from the configuration model.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self._plugin_metadata.get(key, default)
        
    class Config:
        # Enable arbitrary types by default to support DataFrame, Path, etc.
        arbitrary_types_allowed = True
        
        # Do not allow extra attributes to enforce strict configuration models
        extra = "forbid"