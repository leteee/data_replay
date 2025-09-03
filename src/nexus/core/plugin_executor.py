
import inspect
from logging import Logger
from pathlib import Path
from typing import Any, Callable
from pydantic import BaseModel, ValidationError  # Import Pydantic classes

from .data_hub import DataHub
from .execution_context import PluginContext
from .plugin_spec import PluginSpec


class PluginExecutor:
    """
    Executes a plugin by automatically resolving its dependencies
    through type-hinted dependency injection.
    """

    def __init__(self, plugin_spec: PluginSpec, context: PluginContext):
        self._spec = plugin_spec
        self._context = context
        self._func = plugin_spec.func

    def execute(self) -> None:
        """
        Inspects the plugin function's signature, injects dependencies,
        runs the plugin, and handles the return value.
        """
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
        self._context.logger.info(f"Executing plugin: '{self._spec.name}'")
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
                # Use the 'register' method instead of 'add_data'
                self._context.data_hub.register(self._spec.output_key, return_value)
                self._context.logger.debug(
                    f"Plugin '{self._spec.name}' stored its output in DataHub "
                    f"with key: '{self._spec.output_key}'"
                )

    def _resolve_dependencies(self) -> dict[str, Any]:
        """
        Inspects the function signature and resolves dependencies based on
        type hints and parameter names.
        """
        args_to_inject = {}
        signature = inspect.signature(self._func)

        for param in signature.parameters.values():
            # Handle cases with no type hint
            if param.annotation is inspect.Parameter.empty:
                raise TypeError(
                    f"Plugin '{self._spec.name}' has parameter '{param.name}' "
                    "with no type hint. Dependency injection requires full type hinting."
                )

            # Primary dependency types from PluginContext
            if param.annotation is Logger:
                args_to_inject[param.name] = self._context.logger
                continue
            if param.annotation is DataHub:
                args_to_inject[param.name] = self._context.data_hub
                continue
            if param.annotation is Path:
                # By convention, a lone Path hint resolves to the case_path
                args_to_inject[param.name] = self._context.case_path
                continue
            
            # Check if the parameter is a Pydantic config model
            if inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
                try:
                    # Pass the entire plugin config (which is a dict) to the Pydantic model
                    args_to_inject[param.name] = param.annotation(**self._context.config)
                    continue
                except ValidationError as e:
                    raise ValueError(
                        f"Configuration validation failed for plugin '{self._spec.name}' "
                        f"parameter '{param.name}' (type {param.annotation.__name__}): {e}"
                    )

            # Check if the parameter name matches a key in the plugin's config
            if isinstance(self._context.config, dict) and param.name in self._context.config:
                # TODO: Add type validation against the hint
                args_to_inject[param.name] = self._context.config[param.name]
                continue
            
            # If it's not a core service or a config key, assume it's a DataHub key
            # This is the "Implicit I/O Contract" part of the design
            try:
                data = self._context.data_hub.get(param.name)
                # TODO: Add type validation against the hint (e.g., is it really a pd.DataFrame?)
                args_to_inject[param.name] = data
                continue
            except KeyError:
                raise ValueError(
                    f"Could not resolve parameter '{param.name}'. It was not found as a "
                    "core service, a config key, or a key in the DataHub."
                )

        return args_to_inject
