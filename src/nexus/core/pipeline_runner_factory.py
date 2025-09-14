"""
Factory for creating PipelineRunner instances using dependency injection.
"""

from .pipeline_runner import PipelineRunner
from .context import NexusContext
from .di import container
from .utils.cache import initialize_file_cache
from pathlib import Path
import os


class PipelineRunnerFactory:
    """Factory for creating PipelineRunner instances."""
    
    @staticmethod
    def create(context: NexusContext) -> PipelineRunner:
        """
        Create a PipelineRunner instance with dependency injection.
        
        Args:
            context: The NexusContext for the pipeline run
            
        Returns:
            A configured PipelineRunner instance
        """
        # Initialize file cache
        cache_dir = context.project_root / ".cache"
        initialize_file_cache(cache_dir)
        
        # Register all core services with the container
        container.register_core_services(context)
            
        # Create and return the PipelineRunner
        return PipelineRunner(context)