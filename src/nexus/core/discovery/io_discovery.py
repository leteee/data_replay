"""
Pythonic implementation for discovering IO declarations in plugins.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, get_type_hints, get_args, get_origin, Annotated, Union
import pandas as pd
from functools import lru_cache

from ..plugin.decorator import PLUGIN_REGISTRY
from ..plugin.typing import DataSource, DataSink


@lru_cache(maxsize=128)
def _get_type_hints_cached(config_model: type) -> dict:
    """
    Cached version of get_type_hints to avoid repeated parsing.

    Args:
        config_model: The plugin configuration model class

    Returns:
        Type hints dictionary
    """
    return get_type_hints(config_model, include_extras=True)


def discover_io_declarations(logger: logging.Logger, pipeline_steps: List[Dict[str, Any]], case_config: dict) -> Tuple[Dict[str, Any], Dict[str, Dict[str, DataSource]], Dict[str, Dict[str, DataSink]]]:
    """
    Pre-scans active plugins to discover DataSource and DataSink declarations.

    Returns:
        A tuple containing:
        - A dictionary of discovered data sources for the ConfigManager.
        - A dictionary mapping plugin names to their DataSource fields.
        - A dictionary mapping plugin names to their DataSink fields.
    """
    base_data_sources = {}
    plugin_sources = {}
    plugin_sinks = {}

    # Get io_mapping from case_config
    io_mapping = case_config.get("io_mapping", {})
    logger.debug(f"io_mapping: {io_mapping}")

    for step_config in pipeline_steps:
        plugin_name = step_config.get("plugin")
        if not plugin_name or plugin_name not in PLUGIN_REGISTRY or not step_config.get("enable", True):
            continue

        plugin_spec = PLUGIN_REGISTRY[plugin_name]
        if not plugin_spec.config_model:
            continue

        plugin_sources[plugin_name] = {}
        plugin_sinks[plugin_name] = {}

        try:
            # Use cached get_type_hints to correctly resolve forward references (e.g., from __future__ import annotations)
            type_hints = _get_type_hints_cached(plugin_spec.config_model)
        except (NameError, TypeError) as e:
            logger.error(f"Could not resolve type hints for {plugin_name}'s config: {e}")
            continue

        for field_name, field_type in type_hints.items():
            # Handle Union types (like Optional[Annotated[...]])
            field_args = get_args(field_type)
            # If it's a Union, we need to check the first argument (the Annotated type)
            if field_args and get_origin(field_type) is Union:
                # Check if the first argument is Annotated
                if get_origin(field_args[0]) is Annotated:
                    field_metadata = get_args(field_args[0])[1:]  # Skip the actual type, get metadata
                    # Get the actual type for type checking
                    actual_type = get_args(field_args[0])[0]
                else:
                    continue
            # Handle direct Annotated types
            elif get_origin(field_type) is Annotated:
                field_metadata = get_args(field_type)[1:]  # Skip the actual type, get metadata
                # Get the actual type for type checking
                actual_type = get_args(field_type)[0]
            else:
                continue

            for item in field_metadata:
                if isinstance(item, DataSource):
                    # For ConfigManager (name -> path/handler mapping)
                    # Note: We need a unique name. For now, let's use the name attribute.
                    name = item.name
                    logger.debug(f"Found DataSource with name: {name}")
                    if name in base_data_sources:
                        logger.warning(f"Data source name '{name}' is declared by multiple plugins.")
                    
                    # Get path and handler from io_mapping
                    source_config = io_mapping.get(name, {})
                    logger.debug(f"Source config for '{name}': {source_config}")
                    path = source_config.get("path", "")
                    handler = source_config.get("handler", "")
                    logger.debug(f"Path for '{name}': {path}")
                    logger.debug(f"Handler for '{name}': {handler}")
                    
                    # Build handler_args
                    handler_args = item.handler_args.copy() if item.handler_args else {}
                    if handler:
                        handler_args["name"] = handler
                    
                    base_data_sources[name] = {
                        "path": path,
                        "handler_args": handler_args,
                        "expected_type": actual_type  # Store expected type for pre-flight check
                    }
                    logger.debug(f"Added to base_data_sources: {name} -> {base_data_sources[name]}")
                    # For runner (plugin -> field -> DataSource mapping)
                    plugin_sources[plugin_name][field_name] = item

                elif isinstance(item, DataSink):
                    plugin_sinks[plugin_name][field_name] = item

    if base_data_sources:
        logger.info(f"Discovered {len(base_data_sources)} data sources from plugin configs.")
    return base_data_sources, plugin_sources, plugin_sinks