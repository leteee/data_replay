"""
Nexus Framework Built-in Plugins Package

This package contains the built-in plugins for the Nexus framework.
"""

# Import submodules to make them available at package level
from .prediction import latency_compensator
from .visualization import frame_renderer, video_creator

__all__ = [
    "latency_compensator",
    "frame_renderer", 
    "video_creator"
]