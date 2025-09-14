"""
Plugin system for the Nexus framework.
"""

from .decorator import plugin, PLUGIN_REGISTRY
from .spec import PluginSpec
from .typing import DataSource, DataSink
from .base import PluginConfig

__all__ = [
    "plugin",
    "PLUGIN_REGISTRY",
    "PluginSpec",
    "DataSource",
    "DataSink",
    "PluginConfig"
]