"""
Factory for creating PipelineRunner instances using dependency-injector library.
"""

from .pipeline_runner import PipelineRunner
from .context import NexusContext
from .di.container_new import DIContainer
from .utils.cache import initialize_file_cache
from pathlib import Path
import os


class PipelineRunnerFactory:
    """Factory for creating PipelineRunner instances."""
    
    @staticmethod
    def create(context: NexusContext) -> PipelineRunner:
        """
        Create a PipelineRunner instance with dependency injection using dependency-injector.
        
        Args:
            context: The NexusContext for the pipeline run
            
        Returns:
            A configured PipelineRunner instance
        """
        # Initialize file cache
        cache_dir = context.project_root / ".cache"
        initialize_file_cache(cache_dir)
        
        # Create the DI container
        container = DIContainer()
        
        # Configure the container with runtime values
        container.config.from_dict({
            "project_root": context.project_root,
            "case_path": context.case_path,
            "logger": context.logger,
            "run_config": context.run_config,
            "context": context,
            "global_config": {},  # Will be populated as needed
            "case_config": {},    # Will be populated as needed
            "cli_args": {},       # Will be populated as needed
            "plugin_registry": {}, # Will be populated as needed
            "discovered_data_sources": {} # Will be populated as needed
        })
        
        # Initialize the container
        container.wire(modules=["nexus.core.pipeline_runner"])
        
        # Create and return the PipelineRunner using the context
        # (We still pass context directly since that's the current design)
        return PipelineRunner(context)