
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from .data.hub import DataHub

@dataclass(frozen=True)
class NexusContext:
    """
    The global context for a pipeline run.
    It holds all major services and configurations.
    """
    project_root: Path
    cases_root: Path
    case_path: Path
    data_hub: DataHub
    logger: Logger
    # This will hold the merged configuration from global and case files
    run_config: dict 

@dataclass(frozen=True)
class PluginContext:
    """
    The specific context passed to a single plugin for execution.
    It provides a focused view of the overall NexusContext, tailored
    for the plugin.
    """
    # Core services from the global context
    data_hub: DataHub
    logger: Logger

    # Paths relevant to the execution
    project_root: Path
    case_path: Path

    # Plugin-specific configuration, fully resolved and validated
    config: dict | object # Can be a dict or a Pydantic model instance
