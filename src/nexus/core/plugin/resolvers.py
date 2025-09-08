# -*- coding: utf-8 -*-
"""
This module defines the dependency resolution logic for the PluginExecutor.

With the new architecture, where dependencies are declared in and hydrated into
the Pydantic config model, the resolution process is greatly simplified.
"""
import inspect
from logging import Logger
from typing import Any

from pydantic import BaseModel

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
        # DataHub injection is kept for potential advanced use cases or debugging.
        if parameter.annotation is DataHub:
            return context.data_hub
        raise ResolutionError("Not a core service.")


class ConfigModelResolver(IParameterResolver):
    """Resolves the main, hydrated Pydantic config model for the plugin."""

    def resolve(self, parameter: inspect.Parameter, context: PluginContext) -> Any:
        # Check if the parameter expects a Pydantic model and matches the context.
        if not (inspect.isclass(parameter.annotation) and issubclass(parameter.annotation, BaseModel)):
            raise ResolutionError("Not a Pydantic config model.")

        if isinstance(context.config, parameter.annotation):
            return context.config
        else:
            # This case should not be reached if the framework is used correctly.
            raise ResolutionError(
                f"Type mismatch for config model. Plugin expects "
                f"'{parameter.annotation.__name__}' but context contains "
                f"a '{type(context.config).__name__}'."
            )


def get_resolver_chain() -> list[IParameterResolver]:
    """Returns the ordered list of resolvers to be used by the executor."""
    return [
        ServiceResolver(),
        ConfigModelResolver(),
    ]
