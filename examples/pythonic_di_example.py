"""
Example showing how to refactor the DI container to be more Pythonic.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Type, Callable, Optional, get_type_hints
import inspect
import weakref
from functools import lru_cache
from dataclasses import dataclass, field

# Before: Complex class with lots of methods and state
class DIContainer:
    """
    Before refactoring: Complex DI container with many methods and state.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._registrations: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)
        self._service_key_cache: Dict[Type, str] = {}
        self._service_name_cache: Dict[Type, str] = {}
        self._constructor_signature_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

    def register(
        self,
        service_type: Type,
        implementation: Any = None,
        lifecycle: str = "singleton",
        factory: Optional[Callable] = None
    ) -> None:
        """Register a service with the container."""
        service_key = self._get_service_key(service_type)
        self._registrations[service_key] = {
            "type": service_type,
            "implementation": implementation,
            "lifecycle": lifecycle,
            "factory": factory
        }
        self._logger.debug(f"Registered service: {service_key}")

    def resolve(self, service_type: Type) -> Any:
        """Resolve a service from the container."""
        service_key = self._get_service_key(service_type)
        if service_key not in self._registrations:
            raise ValueError(f"Service {service_key} not found")
        return self._create_instance(self._registrations[service_key])

    def _get_service_key(self, service_type: Type) -> str:
        """Generate a service key."""
        if service_type in self._service_key_cache:
            return self._service_key_cache[service_type]
        key = f"{service_type.__module__}.{service_type.__name__}"
        self._service_key_cache[service_type] = key
        return key

    def _create_instance(self, registration: Dict[str, Any]) -> Any:
        """Create an instance."""
        if registration["factory"]:
            return registration["factory"](self)
        elif registration["implementation"]:
            impl = registration["implementation"]
            if isinstance(impl, type):
                return self._inject_dependencies(impl)
            return impl
        else:
            raise ValueError("No implementation or factory")

    def _inject_dependencies(self, cls: Type) -> Any:
        """Inject dependencies."""
        sig = inspect.signature(cls.__init__)
        params = dict(sig.parameters)
        params.pop('self', None)
        dependencies = {}
        for param_name, param in params.items():
            if param.annotation != inspect.Parameter.empty:
                try:
                    dependencies[param_name] = self.resolve(param.annotation)
                except ValueError:
                    if param.default != inspect.Parameter.empty:
                        dependencies[param_name] = param.default
                    else:
                        raise
            else:
                if param.default != inspect.Parameter.empty:
                    dependencies[param_name] = param.default
                else:
                    raise ValueError(f"Cannot resolve dependency for {param_name}")
        return cls(**dependencies)

    def clear(self) -> None:
        """Clear all services."""
        self._services.clear()
        self._service_key_cache.clear()
        self._service_name_cache.clear()
        self._constructor_signature_cache.clear()


# After: Simplified, more Pythonic approach
@dataclass
class ServiceRegistration:
    """Simple dataclass for service registration."""
    service_type: Type
    implementation: Any = None
    lifecycle: str = "singleton"
    factory: Optional[Callable] = None


class SimpleDIContainer:
    """
    After refactoring: Simplified DI container following Pythonic principles.
    """
    
    def __init__(self):
        self._registrations: Dict[str, ServiceRegistration] = {}
        self._instances: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)

    def register(
        self,
        service_type: Type,
        implementation: Any = None,
        lifecycle: str = "singleton",
        factory: Optional[Callable] = None
    ) -> None:
        """Register a service with the container."""
        service_key = self._get_service_key(service_type)
        self._registrations[service_key] = ServiceRegistration(
            service_type=service_type,
            implementation=implementation,
            lifecycle=lifecycle,
            factory=factory
        )
        self._logger.debug(f"Registered service: {service_key}")

    def resolve(self, service_type: Type) -> Any:
        """Resolve a service from the container."""
        service_key = self._get_service_key(service_type)
        
        # Check if we already have a singleton instance
        if service_key in self._instances:
            return self._instances[service_key]
            
        # Check if service is registered
        if service_key not in self._registrations:
            raise ValueError(f"Service {service_key} not found")
            
        # Create the instance
        registration = self._registrations[service_key]
        instance = self._create_instance(registration)
        
        # Store singleton instances
        if registration.lifecycle == "singleton":
            self._instances[service_key] = instance
            
        return instance

    @lru_cache(maxsize=128)
    def _get_service_key(self, service_type: Type) -> str:
        """Generate a service key with caching."""
        return f"{service_type.__module__}.{service_type.__name__}"

    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """Create an instance."""
        if registration.factory:
            return registration.factory(self)
        elif registration.implementation:
            impl = registration.implementation
            if isinstance(impl, type):
                return self._inject_dependencies(impl)
            return impl
        else:
            raise ValueError("No implementation or factory")

    def _inject_dependencies(self, cls: Type) -> Any:
        """Inject dependencies."""
        sig = inspect.signature(cls.__init__)
        params = dict(sig.parameters)
        params.pop('self', None)
        dependencies = {}
        for param_name, param in params.items():
            if param.annotation != inspect.Parameter.empty:
                try:
                    dependencies[param_name] = self.resolve(param.annotation)
                except ValueError:
                    if param.default != inspect.Parameter.empty:
                        dependencies[param_name] = param.default
                    else:
                        raise
            else:
                if param.default != inspect.Parameter.empty:
                    dependencies[param_name] = param.default
                else:
                    raise ValueError(f"Cannot resolve dependency for {param_name}")
        return cls(**dependencies)

    def clear(self) -> None:
        """Clear all services."""
        self._instances.clear()
        self._get_service_key.cache_clear()  # Clear the LRU cache


# Even more Pythonic: Functional approach
def create_simple_container() -> Dict[str, Any]:
    """
    Even more Pythonic: Simple functional approach to DI.
    """
    container = {
        "_registrations": {},
        "_instances": {},
        "_logger": logging.getLogger(__name__)
    }
    return container


def register_service(container: Dict[str, Any], service_type: Type, 
                    implementation: Any = None, lifecycle: str = "singleton",
                    factory: Optional[Callable] = None) -> None:
    """Register a service with the container."""
    service_key = f"{service_type.__module__}.{service_type.__name__}"
    container["_registrations"][service_key] = {
        "service_type": service_type,
        "implementation": implementation,
        "lifecycle": lifecycle,
        "factory": factory
    }
    container["_logger"].debug(f"Registered service: {service_key}")


def resolve_service(container: Dict[str, Any], service_type: Type) -> Any:
    """Resolve a service from the container."""
    service_key = f"{service_type.__module__}.{service_type.__name__}"
    
    # Check if we already have a singleton instance
    if service_key in container["_instances"]:
        return container["_instances"][service_key]
        
    # Check if service is registered
    if service_key not in container["_registrations"]:
        raise ValueError(f"Service {service_key} not found")
        
    # Create the instance
    registration = container["_registrations"][service_key]
    instance = _create_instance(container, registration)
    
    # Store singleton instances
    if registration["lifecycle"] == "singleton":
        container["_instances"][service_key] = instance
        
    return instance


def _create_instance(container: Dict[str, Any], registration: Dict[str, Any]) -> Any:
    """Create an instance."""
    if registration["factory"]:
        return registration["factory"](container)
    elif registration["implementation"]:
        impl = registration["implementation"]
        if isinstance(impl, type):
            return _inject_dependencies(container, impl)
        return impl
    else:
        raise ValueError("No implementation or factory")


def _inject_dependencies(container: Dict[str, Any], cls: Type) -> Any:
    """Inject dependencies."""
    sig = inspect.signature(cls.__init__)
    params = dict(sig.parameters)
    params.pop('self', None)
    dependencies = {}
    for param_name, param in params.items():
        if param.annotation != inspect.Parameter.empty:
            try:
                dependencies[param_name] = resolve_service(container, param.annotation)
            except ValueError:
                if param.default != inspect.Parameter.empty:
                    dependencies[param_name] = param.default
                else:
                    raise
        else:
            if param.default != inspect.Parameter.empty:
                dependencies[param_name] = param.default
            else:
                raise ValueError(f"Cannot resolve dependency for {param_name}")
    return cls(**dependencies)


def clear_container(container: Dict[str, Any]) -> None:
    """Clear all services."""
    container["_instances"].clear()


# Example usage
def example_usage():
    """Example showing the different approaches."""
    print("=== Pythonic DI Container Examples ===")
    
    # Class-based approach
    print("\n1. Class-based approach:")
    container1 = SimpleDIContainer()
    container1.register(logging.Logger, logging.getLogger(__name__))
    logger1 = container1.resolve(logging.Logger)
    print(f"Resolved logger: {logger1}")
    
    # Functional approach
    print("\n2. Functional approach:")
    container2 = create_simple_container()
    register_service(container2, logging.Logger, logging.getLogger(__name__))
    logger2 = resolve_service(container2, logging.Logger)
    print(f"Resolved logger: {logger2}")
    
    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    example_usage()