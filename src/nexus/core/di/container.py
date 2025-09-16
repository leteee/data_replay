"""
Dependency Injection Container for the Nexus framework.
"""

from typing import Any, Dict, Type, Callable, Optional, get_type_hints
from abc import ABC, abstractmethod
import logging
import inspect
import weakref
from functools import lru_cache

from .exceptions import DIException


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not found in the container."""
    pass


class ServiceLifeCycle:
    """Enumeration of service lifecycle types."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class DIContainer:
    """
    A simple dependency injection container for managing framework services.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._registrations: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)
        
        # Performance optimization: Cache service keys
        self._service_key_cache: Dict[Type, str] = {}
        self._service_name_cache: Dict[Type, str] = {}
        
        # Performance optimization: Cache constructor signatures
        self._constructor_signature_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

    def register(
        self,
        service_type: Type,
        implementation: Any = None,
        lifecycle: str = ServiceLifeCycle.SINGLETON,
        factory: Optional[Callable] = None
    ) -> None:
        """
        Register a service with the container.

        Args:
            service_type: The type (interface) of the service
            implementation: The concrete implementation of the service
            lifecycle: The lifecycle of the service (SINGLETON, TRANSIENT, SCOPED)
            factory: An optional factory function to create the service
        """
        try:
            service_key = self._get_service_key(service_type)
            
            self._registrations[service_key] = {
                "type": service_type,
                "implementation": implementation,
                "lifecycle": lifecycle,
                "factory": factory
            }
            
            # Clear cache when registering new services
            self._clear_caches_for_service(service_type)
            
            self._logger.debug(f"Registered service: {service_key} with lifecycle {lifecycle}")
        except Exception as e:
            raise DIException(
                message=f"Failed to register service {service_type}",
                context={
                    "service_type": self._get_service_name(service_type),
                    "implementation": str(implementation) if implementation else "None",
                    "lifecycle": lifecycle
                },
                cause=e
            )

    def register_core_services(self, context) -> None:
        """
        Register all core framework services from the given context.
        
        This is a convenience method that registers all standard framework services
        in one call, simplifying the setup process.
        
        Args:
            context: The NexusContext containing the core services to register
        """
        try:
            # Register logger service
            if hasattr(context, 'logger') and context.logger:
                from .services import LoggerInterface
                from .adapters import LoggerAdapter
                self.register(LoggerInterface, LoggerAdapter(context.logger))
                self._logger.debug("Registered core logger service")
                
            # Register data hub service
            if hasattr(context, 'data_hub') and context.data_hub:
                from .services import DataHubInterface
                from .adapters import DataHubAdapter
                self.register(DataHubInterface, DataHubAdapter(context.data_hub))
                self._logger.debug("Registered core data hub service")
                
            # Additional core services can be registered here as needed
            # For example:
            # if hasattr(context, 'config_manager') and context.config_manager:
            #     from .services import ConfigManagerInterface
            #     from .adapters import ConfigManagerAdapter
            #     self.register(ConfigManagerInterface, ConfigManagerAdapter(context.config_manager))
            #     self._logger.debug("Registered core config manager service")
                
        except DIException:
            # Re-raise service registration exceptions
            raise
        except Exception as e:
            self._logger.warning(f"Failed to register some core services: {e}")
            # Re-raise to enforce proper error handling
            raise

    def resolve(self, service_type: Type) -> Any:
        """
        Resolve a service from the container.

        Args:
            service_type: The type (interface) of the service to resolve

        Returns:
            The resolved service instance

        Raises:
            ServiceNotFoundError: If the service is not registered
        """
        try:
            service_key = self._get_service_key(service_type)
            
            if service_key not in self._registrations:
                raise ServiceNotFoundError(f"Service {service_key} not found in container")
                
            registration = self._registrations[service_key]
            
            # Check if we already have a singleton instance
            if registration["lifecycle"] == ServiceLifeCycle.SINGLETON and service_key in self._services:
                return self._services[service_key]
                
            # Create the service instance
            instance = self._create_instance(registration)
            
            # Store singleton instances
            if registration["lifecycle"] == ServiceLifeCycle.SINGLETON:
                self._services[service_key] = instance
                
            return instance
        except ServiceNotFoundError:
            # Re-raise service not found errors as ServiceResolutionException
            service_name = self._get_service_name(service_type)
            raise DIException(
                service_type=service_name,
                message=f"Service {service_name} not found in container",
                context={
                    "service_type": str(service_type),
                    "service_key": self._get_service_key(service_type) if 'service_type' in locals() else "unknown"
                }
            )
        except DIException:
            # Re-raise service resolution exceptions
            raise
        except Exception as e:
            service_name = self._get_service_name(service_type)
            raise DIException(
                service_type=service_name,
                message=f"Failed to resolve service {service_name}",
                context={
                    "service_type": str(service_type),
                    "service_key": self._get_service_key(service_type) if 'service_type' in locals() else "unknown"
                },
                cause=e
            )

    def _get_service_key(self, service_type: Type) -> str:
        """Generate a unique key for a service type with caching."""
        if service_type in self._service_key_cache:
            return self._service_key_cache[service_type]
        
        key = f"{service_type.__module__}.{service_type.__name__}"
        self._service_key_cache[service_type] = key
        return key

    def _get_service_name(self, service_type: Type) -> str:
        """Get a human-readable name for a service type with caching."""
        if service_type in self._service_name_cache:
            return self._service_name_cache[service_type]
        
        name = f"{service_type.__module__}.{service_type.__name__}"
        self._service_name_cache[service_type] = name
        return name

    def _clear_caches_for_service(self, service_type: Type) -> None:
        """Clear caches when a service is registered or modified."""
        self._service_key_cache.pop(service_type, None)
        self._service_name_cache.pop(service_type, None)

    def _clear_all_caches(self) -> None:
        """Clear all caches."""
        self._service_key_cache.clear()
        self._service_name_cache.clear()
        self._constructor_signature_cache.clear()

    def _get_constructor_signature_cached(self, cls: Type):
        """Get constructor signature with caching."""
        if cls in self._constructor_signature_cache:
            return self._constructor_signature_cache[cls]
        
        sig = inspect.signature(cls.__init__)
        self._constructor_signature_cache[cls] = sig
        return sig

    def _create_instance(self, registration: Dict[str, Any]) -> Any:
        """Create an instance of a service based on its registration."""
        try:
            if registration["factory"]:
                return registration["factory"](self)
            elif registration["implementation"]:
                impl = registration["implementation"]
                # If it's a class, instantiate it with dependency injection
                if isinstance(impl, type):
                    return self._inject_dependencies(impl)
                # If it's already an instance, return it
                return impl
            else:
                raise ServiceNotFoundError("No implementation or factory provided for service")
        except Exception as e:
            service_type = registration.get("type", "Unknown")
            service_name = self._get_service_name(service_type) if service_type != "Unknown" else "Unknown"
            raise DIException(
                service_type=service_name,
                message=f"Failed to create instance of service {service_name}",
                context={
                    "service_type": str(service_type),
                    "has_factory": registration["factory"] is not None if "factory" in registration else False,
                    "has_implementation": registration["implementation"] is not None if "implementation" in registration else False
                },
                cause=e
            )

    def _inject_dependencies(self, cls: Type) -> Any:
        """Inject dependencies into a class constructor with performance optimizations."""
        try:
            # Get the constructor signature with caching
            sig = self._get_constructor_signature_cached(cls)
            params = dict(sig.parameters)
            params.pop('self', None)  # Remove 'self' parameter
            
            # Resolve dependencies for each parameter
            dependencies = {}
            for param_name, param in params.items():
                if param.annotation != inspect.Parameter.empty:
                    # Try to resolve the dependency by its type annotation
                    try:
                        dependencies[param_name] = self.resolve(param.annotation)
                    except ServiceNotFoundError:
                        # If dependency not found, use default value if available
                        if param.default != inspect.Parameter.empty:
                            dependencies[param_name] = param.default
                        else:
                            raise
                else:
                    # No annotation, use default value if available
                    if param.default != inspect.Parameter.empty:
                        dependencies[param_name] = param.default
                    else:
                        raise ServiceNotFoundError(f"Cannot resolve dependency for parameter {param_name} in {cls.__name__}")
            
            # Create instance with resolved dependencies
            return cls(**dependencies)
        except ServiceNotFoundError:
            # Re-raise service not found errors
            raise
        except Exception as e:
            class_name = cls.__name__ if hasattr(cls, '__name__') else str(cls)
            raise DIException(
                target_type=class_name,
                message=f"Failed to inject dependencies for {class_name}",
                context={
                    "target_class": class_name,
                },
                cause=e
            )

    def clear(self) -> None:
        """Clear all singleton instances from the container."""
        self._services.clear()
        self._clear_all_caches()
        self._logger.debug("Cleared all singleton instances and caches from container")


# Global container instance
container = DIContainer()