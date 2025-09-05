# -*- coding: utf-8 -*-
"""
This module defines the dependency resolution logic for the PluginExecutor.

It uses a chain-of-responsibility pattern where each resolver class is
responsible for a specific type of dependency injection.
"""
import inspect
from logging import Logger
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from ..context import PluginContext
from ..data.hub import DataHub


class ResolutionError(Exception):
    """Custom exception for dependency resolution failures."""
    pass


class IParameterResolver:
    """Abstract base class for parameter resolvers."""

    def resolve(self, parameter: inspect.Parameter, context: PluginContext) -> Any:
        """
        Tries to resolve a value for the given parameter.
        If successful, returns the value.
        If not, raises a ResolutionError.
        """
        raise NotImplementedError


class ServiceResolver(IParameterResolver):
    """Resolves core services like Logger and DataHub based on type hint."""

    def resolve(self, parameter: inspect.Parameter, context: PluginContext) -> Any:
        if parameter.annotation is Logger:
            return context.logger
        if parameter.annotation is DataHub:
            return context.data_hub
        raise ResolutionError("Not a core service.")


class ConfigModelResolver(IParameterResolver):
    """Resolves Pydantic BaseModel parameters."""

    def resolve(self, parameter: inspect.Parameter, context: PluginContext) -> Any:
        # Check if the parameter expects a Pydantic model
        if not (inspect.isclass(parameter.annotation) and issubclass(parameter.annotation, BaseModel)):
            raise ResolutionError("Not a Pydantic config model.")

        # The ConfigManager now returns a pre-validated Pydantic model instance.
        # We just need to check if the object in the context is of the correct type.
        if isinstance(context.config, parameter.annotation):
            return context.config
        else:
            # This case should ideally not be reached if the framework is used correctly.
            raise ResolutionError(
                f"Type mismatch for config model. Plugin expects "
                f"'{parameter.annotation.__name__}' but context contains "
                f"a '{type(context.config).__name__}'."
            )


class PathResolver(IParameterResolver):
    """
    Resolves Path objects. This is a critical part of fixing the bug.
    
    之前的注入逻辑存在缺陷：任何Path类型的参数都会被错误地注入case_path。
    新的逻辑优化了这一点，建立了更清晰的注入优先级：
    1. 如果参数名称是 'case_path'，则注入 case_path。
    2. 如果参数名称对应DataHub中的一个数据源，则注入该数据源的路径。
    这解决了“数据源既可以是文件也可以是路径”的二义性问题。
    """

    def resolve(self, parameter: inspect.Parameter, context: PluginContext) -> Any:
        if parameter.annotation is not Path:
            raise ResolutionError("Not a Path parameter.")

        # Convention: if param is named 'case_path', inject the case path.
        if parameter.name == "case_path":
            return context.case_path

        # Check if the parameter name corresponds to a data source path in the hub
        path = context.data_hub.get_path(parameter.name)
        if path:
            return path
        
        raise ResolutionError(f"Could not resolve Path for '{parameter.name}'.")


class ConfigValueResolver(IParameterResolver):
    """Resolves simple values from the plugin's config dictionary by name."""

    def resolve(self, parameter: inspect.Parameter, context: PluginContext) -> Any:
        if isinstance(context.config, dict) and parameter.name in context.config:
            # TODO: Add type validation against the hint
            return context.config[parameter.name]
        raise ResolutionError("Not found in config by name.")


class DataHubValueResolver(IParameterResolver):
    """Resolves values from the DataHub by name."""

    def resolve(self, parameter: inspect.Parameter, context: PluginContext) -> Any:
        if parameter.name in context.data_hub:
            # TODO: Add type validation against the hint
            return context.data_hub.get(parameter.name)
        raise ResolutionError("Not found in DataHub by name.")


def get_resolver_chain() -> list[IParameterResolver]:
    """Returns the ordered list of resolvers to be used by the executor."""
    return [
        ServiceResolver(),
        ConfigModelResolver(),
        PathResolver(),
        ConfigValueResolver(),
        DataHubValueResolver(),
    ]
