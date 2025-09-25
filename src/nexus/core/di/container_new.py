"""
New Dependency Injection Container using dependency-injector library
to replace the custom DI framework.
"""

from dependency_injector import containers, providers
from dependency_injector.providers import Singleton, Factory
from logging import Logger
from pathlib import Path
from typing import Dict, Any


class DIContainer(containers.DeclarativeContainer):
    """
    Dependency Injection container using dependency-injector library.
    This container manages the core services and dependencies for the Nexus framework.
    """
    
    # Configuration that will be provided at runtime
    config = providers.Configuration()
    
    # Core services will be registered at runtime
    # We'll handle this differently to avoid circular imports
    pass