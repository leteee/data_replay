"""
Pythonic functions for performing pre-flight type checks.
"""

import logging
import pandas as pd

from ..data.handlers.base import DataHandler


def preflight_type_check(logger: logging.Logger, data_source_name: str, source_config: dict, handler: DataHandler) -> bool:
    """
    Performs a pre-flight type check to ensure the data type produced by a Handler
    matches the type expected by the plugin.
    
    Args:
        logger: Logger instance
        data_source_name: Name of the data source
        source_config: Configuration for the data source including expected_type
        handler: The data handler instance
        
    Returns:
        True if type check passes, False otherwise
    """
    expected_type = source_config.get("expected_type")
    if expected_type is None:
        logger.debug(f"No expected type for data source '{data_source_name}', skipping type check.")
        return True
        
    # Get the handler's produced type
    produced_type = getattr(handler, 'produced_type', None)
    if produced_type is None:
        logger.warning(f"Handler '{handler.__class__.__name__}' does not declare a produced_type. Skipping type check for '{data_source_name}'.")
        return True
        
    # Perform type compatibility check
    # For now, we'll do a simple check. In the future, this could be more sophisticated.
    if expected_type == produced_type:
        logger.debug(f"Type check passed for '{data_source_name}': {expected_type}")
        return True
    elif expected_type == pd.DataFrame and produced_type == pd.DataFrame:
        logger.debug(f"Type check passed for '{data_source_name}': DataFrame")
        return True
    else:
        logger.warning(f"Type mismatch for '{data_source_name}': expected {expected_type}, got {produced_type}")
        return False