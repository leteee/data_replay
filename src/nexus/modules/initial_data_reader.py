from .base_plugin import BasePlugin
from ..core.data_hub import DataHub

class InitialDataReader(BasePlugin):
    """
    A specialized plugin to load the very first dataset into the pipeline
    as defined in the `data_sources` section of the case config.
    """

    def run(self, data_hub: DataHub):
        super().run(data_hub)

        # This plugin's job is to load the data specified in its "outputs"
        # The data_hub.get() method will trigger the lazy loading from the file
        # specified in the data_sources config.
        output_names = self.config.get("outputs", [])
        if not output_names:
            self.logger.warning("No outputs defined for InitialDataReader. Nothing to load.")
            return

        for data_name in output_names:
            self.logger.info(f"Triggering initial load for data source: '{data_name}'")
            # The get method will load the data and cache it in the hub.
            # We don't need to do anything with the returned dataframe here.
            data_hub.get(data_name)
