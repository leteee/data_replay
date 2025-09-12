"""
Defines the context objects used throughout the Nexus framework.
"""

from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from .data.hub import DataHub


@dataclass
class NexusContext:
    """
    The global context for a pipeline run.
    """
    project_root: Path
    case_path: Path
    data_hub: DataHub
    logger: Logger
    run_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginContext:
    """
    The context provided to a plugin during execution.
    """
    data_hub: DataHub
    logger: Logger
    project_root: Path
    case_path: Path
    config: BaseModel | None = None
    output_path: Optional[Path] = None