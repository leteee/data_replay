from typing import List
from logging import Logger

from pydantic import BaseModel, Field

from nexus.core.data_hub import DataHub
from nexus.core.plugin_decorator import plugin


class InitialDataReaderConfig(BaseModel):
    """Configuration model for the Initial Data Reader plugin."""
    outputs: List[str] = Field(
        default=[],
        description="A list of data source keys to be loaded from the DataHub."
    )


@plugin(
    name="Initial Data Reader",
    # This plugin doesn't produce a new output via its return value,
    # but triggers the loading of existing data sources.
    output_key=None 
)
def read_initial_data(
    # Dependency Injection:
    data_hub: DataHub,
    logger: Logger,
    # Configuration Injection:
    outputs: List[str]
) -> None:
    """
    A specialized plugin to load the very first dataset(s) into the pipeline
    as defined in the `data_sources` section of the case config.
    Its job is to trigger the lazy loading of data sources specified in its config.
    """
    if not outputs:
        logger.warning("No outputs defined for InitialDataReader. Nothing to load.")
        return

    for data_name in outputs:
        logger.debug(f"Triggering initial load for data source: '{data_name}'")
        # The get method will load the data and cache it in the hub.
        # We don't need to do anything with the returned value here.
        data_hub.get(data_name)