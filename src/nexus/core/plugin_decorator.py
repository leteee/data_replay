
from typing import Callable, Any
from .plugin_spec import PluginSpec

# This will act as a central registry for all discovered plugins
PLUGIN_REGISTRY: dict[str, PluginSpec] = {}

def plugin(name: str, output_key: str | None = None) -> Callable:
    """
    A decorator to register a function as a Nexus plugin.

    Args:
        name: The unique name of the plugin. This will be used to
              refer to the plugin in case configurations.
        output_key: The key under which the plugin's return value will be
                    stored in the DataHub. If None, the return value is ignored.
    """
    def decorator(func: Callable) -> Callable:
        spec = PluginSpec(
            name=name,
            func=func,
            output_key=output_key,
            # We will populate the config_model later during discovery
            config_model=None, 
        )
        if name in PLUGIN_REGISTRY:
            raise ValueError(f"Plugin with name '{name}' already exists.")
        PLUGIN_REGISTRY[name] = spec
        
        # Return the original function, as the decorator is just for registration
        return func
    return decorator
