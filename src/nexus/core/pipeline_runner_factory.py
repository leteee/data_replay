"""
Factory for creating PipelineRunner instances using dependency injection.
"""

from .pipeline_runner import PipelineRunner
from .context import NexusContext
from .di import container


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
        # Register all core services with the container
        container.register_core_services(context)
            
        # Create and return the PipelineRunner
        return PipelineRunner(context)