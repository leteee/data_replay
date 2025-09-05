import inspect
from logging import Logger
from pathlib import Path
from typing import Any, Callable
from pydantic import BaseModel, ValidationError

from ..data.hub import DataHub
from ..context import PluginContext
from .spec import PluginSpec
from .resolvers import get_resolver_chain, ResolutionError # Import new components


class PluginExecutor:
    """
    Executes a plugin by automatically resolving its dependencies
    through type-hinted dependency injection using a chain of resolvers.
    """

    def __init__(self, plugin_spec: PluginSpec, context: PluginContext):
        self._spec = plugin_spec
        self._context = context
        self._func = plugin_spec.func
        self._resolvers = get_resolver_chain() # Instantiate the resolver chain

    def execute(self) -> None:
        """
        Inspects the plugin function's signature, injects dependencies,
        runs the plugin, and handles the return value.
        """
        self._context.logger.info(f"Executing plugin: '{self._spec.name}'")
        
        # 1. Resolve arguments for the plugin function
        try:
            resolved_args = self._resolve_dependencies()
        except Exception as e:
            self._context.logger.error(
                f"Failed to resolve dependencies for plugin '{self._spec.name}': {e}",
                exc_info=True
            )
            raise

        # 2. Execute the plugin function
        try:
            return_value = self._func(**resolved_args)
        except Exception as e:
            self._context.logger.error(
                f"Error executing plugin '{self._spec.name}': {e}",
                exc_info=True
            )
            raise

        # 3. Handle the return value
        if self._spec.output_key:
            if return_value is None:
                self._context.logger.warning(
                    f"Plugin '{self._spec.name}' was expected to return a value "
                    f"(output_key='{self._spec.output_key}') but returned None."
                )
            else:
                self._context.data_hub.register(self._spec.output_key, return_value)
                self._context.logger.debug(
                    f"Plugin '{self._spec.name}' stored its output in DataHub "
                    f"with key: '{self._spec.output_key}'"
                )

    def _validate_parameter_type(self, value: Any, parameter: inspect.Parameter, resolver_name: str):
        """
        Validates the type of a resolved value against the parameter's type hint.
        This adds a layer of robustness to the dependency injection.
        """
        type_hint = parameter.annotation
        if type_hint is inspect.Parameter.empty or type_hint is Any:
            return  # Cannot validate against no hint or Any

        from typing import get_origin
        base_type = get_origin(type_hint) or type_hint

        # We can only perform isinstance checks on actual types.
        # Special forms from `typing` like Union, Callable, etc., will be skipped.
        if not isinstance(base_type, type):
            return

        if not isinstance(value, base_type):
            raise TypeError(
                f"Type mismatch for parameter '{parameter.name}' in plugin '{self._spec.name}'. "
                f"Expected a type compatible with '{type_hint}' but received a "
                f"'{type(value).__name__}' from the '{resolver_name}'."
            )

    def _resolve_dependencies(self) -> dict[str, Any]:
        """
        Iterates through function parameters and uses the resolver chain
        to find a suitable value for each, then validates its type.
        """
        args_to_inject = {}
        signature = inspect.signature(self._func)

        for param in signature.parameters.values():
            if param.annotation is inspect.Parameter.empty:
                raise TypeError(
                    f"Plugin '{self._spec.name}' has parameter '{param.name}' "
                    "with no type hint. Dependency injection requires full type hinting."
                )

            resolved_value = None
            resolver_name = "UnknownResolver"
            for resolver in self._resolvers:
                try:
                    resolved_value = resolver.resolve(param, self._context)
                    resolver_name = resolver.__class__.__name__
                    break  # Stop at the first resolver that succeeds
                except ResolutionError:
                    continue # Try the next resolver
            
            if resolved_value is not None:
                # --- Type validation step ---
                self._validate_parameter_type(resolved_value, param, resolver_name)
                args_to_inject[param.name] = resolved_value
            else:
                # If no resolver succeeded
                raise ValueError(
                    f"Could not resolve parameter '{param.name}:{param.annotation}'. "
                    "It was not found as a core service, config model, data source path, "
                    "config value, or a key in the DataHub."
                )

        return args_to_inject