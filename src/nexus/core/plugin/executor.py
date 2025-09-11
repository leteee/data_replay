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
    Executes a plugin with a fully prepared context.

    This executor supports the new PluginContext-based signature where plugins
    receive a single context object containing all necessary dependencies.
    """

    def __init__(self, plugin_spec: PluginSpec, context: PluginContext):
        self._spec = plugin_spec
        self._context = context
        self._func = plugin_spec.func

    def execute(self) -> Any:
        """
        Executes the plugin function with the prepared context and returns its result.

        It inspects the plugin's signature to determine whether to pass individual
        arguments or the new PluginContext object.
        """
        self._context.logger.info(f"Executing plugin: '{self._spec.name}'")

        # 1. Prepare arguments based on the function signature
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
        
        Supports both the new PluginContext signature and the legacy signature
        for backward compatibility.
        """
        args_to_inject = {}
        signature = inspect.signature(self._func)
        params = signature.parameters

        # Check if the plugin uses the new PluginContext signature
        if len(params) == 1 and "context" in params:
            # New signature: def plugin_function(context: PluginContext)
            args_to_inject["context"] = self._context
        else:
            # Legacy signature support: def plugin_function(config, logger)
            if "config" in params:
                args_to_inject["config"] = self._context.config
            if "logger" in params:
                args_to_inject["logger"] = self._context.logger
            if "context" in params:
                args_to_inject["context"] = self._context
            
            # Warn if using legacy signature
            if len(params) > 0:
                self._context.logger.warning(
                    f"Plugin '{self._spec.name}' uses legacy signature: {signature}. "
                    f"Consider updating to the new PluginContext signature: (context: PluginContext)"
                )

        return args_to_inject