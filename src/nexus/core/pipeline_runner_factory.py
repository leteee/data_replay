"""
Factory for creating PipelineRunner instances.
"""

from .pipeline_runner import PipelineRunner
from .context import NexusContext
from .utils.cache import initialize_file_cache
from pathlib import Path
import os


class PipelineRunnerFactory:
    """Factory for creating PipelineRunner instances."""
    
    @staticmethod
    def create(context: NexusContext) -> PipelineRunner:
        """
        Create a PipelineRunner instance.
        
        Args:
            context: The NexusContext for the pipeline run
            
        Returns:
            A configured PipelineRunner instance
        """
        # Initialize file cache
        cache_dir = context.project_root / ".cache"
        initialize_file_cache(cache_dir)
        
        # Create and return the PipelineRunner using the context
        return PipelineRunner(context)