"""
Factory for creating PipelineRunner instances using dependency injection.
"""

from .pipeline_runner import PipelineRunner
from .context import NexusContext
from .di import container, LoggerInterface, DataHubInterface
from .di.adapters import LoggerAdapter, DataHubAdapter


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
        # Register services with the container if not already registered
        try:
            # Register logger
            if context.logger:
                container.register(LoggerInterface, LoggerAdapter(context.logger))
                
            # Register data hub
            if context.data_hub:
                container.register(DataHubInterface, DataHubAdapter(context.data_hub))
        except Exception:
            # If registration fails, continue without DI
            pass
            
        # Create and return the PipelineRunner
        return PipelineRunner(context)