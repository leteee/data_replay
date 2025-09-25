"""
Pythonic functions for executing plugins and handling their results.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from ..context import PluginContext
from ..data.hub import DataHub
from ..plugin.executor import PluginExecutor
from ..plugin.decorator import PLUGIN_REGISTRY
from ..plugin.typing import DataSink
from ..exceptions import (
    NexusError,
    ConfigurationError,
    PluginError
)
from ..exception_handler import handle_exception


def execute_plugin(logger: logging.Logger, plugin_name: str, plugin_spec, config_object, 
                  data_hub: DataHub, case_path: Path, project_root: Path,
                  resolved_output_path: Optional[Path] = None) -> Any:
    """
    Execute a plugin with the given configuration.
    
    Args:
        logger: Logger instance
        plugin_name: Name of the plugin to execute
        plugin_spec: Plugin specification
        config_object: Configuration object for the plugin
        data_hub: DataHub instance
        case_path: Path to the case directory
        project_root: Path to the project root
        resolved_output_path: Resolved output path for the plugin
        
    Returns:
        The return value from the plugin execution
    """
    plugin_context = PluginContext(
        data_hub=data_hub, logger=logger,
        project_root=project_root, case_path=case_path,
        config=config_object,
        output_path=resolved_output_path
    )

    try:
        executor = PluginExecutor(plugin_spec, plugin_context)
        return_value = executor.execute()
        return return_value
    except Exception as e:
        error_context = {
            "plugin_name": plugin_name,
            "plugin_spec": plugin_spec.name if plugin_spec else "Unknown"
        }
        exc = PluginError(
            f"A critical error occurred in plugin '{plugin_name}'. Halting pipeline."
        )
        # Add context to the exception manually since RuntimeError doesn't accept it in constructor
        if hasattr(exc, 'context'):
            exc.context.update(error_context)
        else:
            exc.context = error_context
        handle_exception(exc, error_context)
        raise exc


def handle_plugin_output(logger: logging.Logger, plugin_name: str, return_value: Any, 
                       sinks_for_plugin: Dict[str, DataSink], raw_case_config: dict,
                       case_path: Path, data_hub: DataHub) -> None:
    """
    Handle the output from a plugin execution.
    
    Args:
        logger: Logger instance
        plugin_name: Name of the plugin
        return_value: Return value from the plugin
        sinks_for_plugin: Data sinks for the plugin
        raw_case_config: Raw case configuration
        case_path: Path to the case directory
        data_hub: DataHub instance
    """
    if not sinks_for_plugin:
        if return_value is not None:
            logger.debug(f"Plugin '{plugin_name}' returned a value but has no DataSink declared.")
        return

    if len(sinks_for_plugin) > 1:
        logger.warning(f"Plugin '{plugin_name}' has multiple DataSinks defined. Only one is supported per plugin. Using the first one found.")

    # Get the first (and only) sink
    sink_field, sink_marker = list(sinks_for_plugin.items())[0]

    if return_value is None:
        # This is now expected for plugins that write directly to disk
        logger.debug(f"Plugin '{plugin_name}' has a DataSink for field '{sink_field}' but returned None.")
        return

    logger.info(f"Plugin '{plugin_name}' produced output. Writing to sink: {sink_marker.name}")
    try:
        # We need to resolve the path relative to the case directory
        # Get the io_mapping from case_config
        io_mapping = raw_case_config.get("io_mapping", {})
        sink_config = io_mapping.get(sink_marker.name, {})
        output_path_str = sink_config.get("path", "")
        output_path = case_path / output_path_str
        handler_args = sink_config.get("handler_args", sink_marker.handler_args)
        data_hub.save(
            data=return_value,
            path=output_path,
            handler_args=handler_args
        )
        logger.debug(f"Successfully wrote output to {output_path}")
    except Exception as e:
        error_context = {
            "plugin_name": plugin_name,
            "sink_name": sink_marker.name if sink_marker else "Unknown",
            "output_path": str(output_path) if 'output_path' in locals() else "Unknown"
        }
        exc = NexusError(
            f"Failed to write output for plugin '{plugin_name}' to {sink_marker.name if sink_marker else 'Unknown'}: {e}",
            context=error_context,
            cause=e
        )
        handle_exception(exc, error_context)
        raise exc