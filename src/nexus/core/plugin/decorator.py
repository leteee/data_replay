import functools
from typing import Callable, Type
from pydantic import BaseModel
from .spec import PluginSpec

# This will act as a central registry for all discovered plugins
PLUGIN_REGISTRY: dict[str, PluginSpec] = {}


def plugin(*, name: str, output_key: str | None = None, default_config: Type[BaseModel] | None = None):
    """
    Decorator to register a function as a plugin and define its metadata.

    Args:
        name: The unique name of the plugin.
        output_key: The key under which the plugin's output will be stored in the DataHub.
        default_config: A Pydantic model defining the plugin's configuration.
    """
    def decorator(func: Callable):
        spec = PluginSpec(
            name=name,
            func=func,
            output_key=output_key,
            config_model=default_config
        )

        if name in PLUGIN_REGISTRY:
            raise ValueError(f"Plugin with name '{name}' is already registered.")

        PLUGIN_REGISTRY[name] = spec

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # The wrapper doesn't need to do much, the framework uses the spec
            return func(*args, **kwargs)

        # Attach the spec to the function for good measure, though registry is primary
        wrapper.plugin_spec = spec
        return wrapper
    return decorator