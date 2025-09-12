import pandas as pd
from logging import Logger
from typing import Annotated, Optional

from pydantic import BaseModel

from nexus.core.plugin.decorator import plugin
from nexus.core.plugin.typing import DataSource, DataSink
from nexus.core.context import PluginContext


class CustomAnalyzerConfig(BaseModel):
    """Configuration model for the Custom Analyzer plugin."""
    # Needed to allow DataFrame fields
    model_config = {"arbitrary_types_allowed": True}
    
    # --- Data Dependencies ---
    input_data: Annotated[
        pd.DataFrame,
        DataSource(name="input_data")
    ]
    output_data: Optional[Annotated[
        pd.DataFrame,
        DataSink(name="output_data")
    ]] = None

    # --- Algorithm Parameters ---
    multiplier: float = 2.0


@plugin(
    name="Custom Analyzer",
    default_config=CustomAnalyzerConfig
)
def analyze_data(context: PluginContext) -> pd.DataFrame:
    """
    A custom plugin that multiplies a column in the input data.
    """
    config = context.config
    logger = context.logger
    
    # The 'input_data' field in the config is a ready-to-use DataFrame.
    df = config.input_data.copy()
    
    logger.info(f"Processing {len(df)} records with multiplier {config.multiplier}")
    
    # Multiply a column (assuming it exists)
    if 'value' in df.columns:
        df['value'] = df['value'] * config.multiplier
        logger.info(f"Multiplied 'value' column by {config.multiplier}")
    else:
        logger.warning("Column 'value' not found in input data")
    
    return df