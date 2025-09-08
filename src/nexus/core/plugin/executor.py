import inspect
from logging import Logger
from pathlib import Path
from typing import Any
from pydantic import BaseModel

from ..data.hub import DataHub
from ..context import PluginContext
from .spec import PluginSpec
from .resolvers import get_resolver_chain, ResolutionError


class PluginExecutor:
    """
    Executes a plugin with a fully hydrated context.

    This simplified executor adheres to the principle that all dependencies
    are pre-resolved and passed via the `PluginContext`, primarily within
    the `config` object. It standardizes the plugin signature and returns
    the plugin's output for further processing by the PipelineRunner.
    """

    def __init__(self, plugin_spec: PluginSpec, context: PluginContext):
        self._spec = plugin_spec
        self._context = context
        self._func = plugin_spec.func

    def execute(self) -> Any:
        """
        Executes the plugin function with the prepared context and returns its result.

        It inspects the plugin's signature to provide the expected arguments,
        supporting the standard `(config, logger)` signature.
        """
        self._context.logger.info(f"Executing plugin: '{self._spec.name}'")

        # 1. Prepare arguments based on standard signatures
        args_to_inject = self._prepare_arguments()

        # 2. Execute the plugin function
        try:
            return_value = self._func(**args_to_inject)
            self._context.logger.info(f"Plugin '{self._spec.name}' executed successfully.")
            return return_value
        except Exception as e:
            self._context.logger.error(
                f"Error executing plugin '{self._spec.name}': {e}",
                exc_info=True
            )
            raise

    def _prepare_arguments(self) -> dict[str, Any]:
        """
        Prepares the arguments for the plugin function based on its signature.
        """
        args_to_inject = {}
        signature = inspect.signature(self._func)
        params = signature.parameters

        # A simple injection mechanism for a standardized signature
        if "config" in params:
            args_to_inject["config"] = self._context.config
        if "logger" in params:
            args_to_inject["logger"] = self._context.logger
        if "context" in params:
            args_to_inject["context"] = self._context
        
        # You can add more standard injectable parameters here if needed,
        # e.g., data_hub, project_root, etc.

        if len(args_to_inject) != len(params):
            self._context.logger.warning(
                f"Plugin '{self._spec.name}' has a non-standard signature: {signature}. "
                f"Consider using the standard `(config, logger)` signature."
            )

        return args_to_inject