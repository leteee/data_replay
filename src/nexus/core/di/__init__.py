"""
Dependency Injection module for the Nexus framework.
"""

from .container import DIContainer, container, ServiceNotFoundError, ServiceLifeCycle
from .services import LoggerInterface, DataHubInterface, ConfigManagerInterface, PluginExecutorInterface, PipelineRunnerInterface
from .adapters import LoggerAdapter, DataHubAdapter, ConfigManagerAdapter
from .exceptions import DIException, ServiceResolutionException, ServiceRegistrationException, DependencyInjectionException

__all__ = [
    "DIContainer",
    "container",
    "ServiceNotFoundError",
    "ServiceLifeCycle",
    "LoggerInterface",
    "DataHubInterface",
    "ConfigManagerInterface",
    "PluginExecutorInterface",
    "PipelineRunnerInterface",
    "LoggerAdapter",
    "DataHubAdapter",
    "ConfigManagerAdapter",
    "DIException",
    "ServiceResolutionException",
    "ServiceRegistrationException",
    "DependencyInjectionException"
]