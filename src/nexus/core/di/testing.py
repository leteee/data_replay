"""
Testing utilities for the dependency injection system.
"""

from typing import Any, Dict, Type, Callable, Optional
from unittest.mock import Mock, MagicMock

from .container import DIContainer, ServiceLifeCycle
from .services import LoggerInterface, DataHubInterface
from .adapters import LoggerAdapter, DataHubAdapter


class TestDIContainer(DIContainer):
    """
    A specialized DI container for testing purposes.
    
    This container provides additional features useful for testing:
    - Easy mocking of services
    - Service verification capabilities
    - Test-specific lifecycle management
    """

    def __init__(self):
        super().__init__()
        self._mocked_services: Dict[str, Any] = {}
        self._service_verification: Dict[str, bool] = {}

    def mock_service(self, service_type: Type, mock_instance: Any = None) -> Any:
        """
        Register a mock service with the container.
        
        Args:
            service_type: The type (interface) of the service to mock
            mock_instance: An optional mock instance. If not provided, a MagicMock will be created.
            
        Returns:
            The mock instance that was registered
        """
        if mock_instance is None:
            mock_instance = MagicMock()
            
        service_key = self._get_service_key(service_type)
        self._mocked_services[service_key] = mock_instance
        self._registrations[service_key] = {
            "type": service_type,
            "implementation": mock_instance,
            "lifecycle": ServiceLifeCycle.SINGLETON,
            "factory": None
        }
        
        self._logger.debug(f"Mocked service: {service_key}")
        return mock_instance

    def verify_service_used(self, service_type: Type) -> bool:
        """
        Verify if a service was used during testing.
        
        Args:
            service_type: The type (interface) of the service to verify
            
        Returns:
            True if the service was used, False otherwise
        """
        service_key = self._get_service_key(service_type)
        return service_key in self._services

    def reset_mocks(self) -> None:
        """Reset all mock call counts and states."""
        for mock in self._mocked_services.values():
            if hasattr(mock, 'reset_mock'):
                mock.reset_mock()

    def clear_test_services(self) -> None:
        """Clear all test-specific services and mocks."""
        self._mocked_services.clear()
        self._service_verification.clear()
        self.clear()

    def get_mock(self, service_type: Type) -> Any:
        """
        Get the mock instance for a service type.
        
        Args:
            service_type: The type (interface) of the service
            
        Returns:
            The mock instance for the service
        """
        service_key = self._get_service_key(service_type)
        return self._mocked_services.get(service_key)


def create_test_container() -> TestDIContainer:
    """
    Create a test container with common test services.
    
    Returns:
        A configured TestDIContainer instance
    """
    container = TestDIContainer()
    return container


def create_test_container_with_mocks(**mocks) -> TestDIContainer:
    """
    Create a test container with specified mock services.
    
    Args:
        **mocks: Keyword arguments where keys are service types and values are mock instances
        
    Returns:
        A configured TestDIContainer instance with the specified mocks
    """
    container = TestDIContainer()
    
    for service_type, mock_instance in mocks.items():
        container.mock_service(service_type, mock_instance)
        
    return container


def create_test_container_with_common_mocks() -> TestDIContainer:
    """
    Create a test container with common mock services.
    
    Returns:
        A configured TestDIContainer instance with common mocks
    """
    container = TestDIContainer()
    
    # Add common mocks
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    container.mock_service(LoggerInterface, mock_logger)
    container.mock_service(DataHubInterface, mock_data_hub)
    
    return container


class MockLogger:
    """A simple mock logger for testing."""
    
    def __init__(self):
        self.messages = []
        self.debug_calls = []
        self.info_calls = []
        self.warning_calls = []
        self.error_calls = []
        self.critical_calls = []

    def debug(self, msg: str, *args, **kwargs) -> None:
        self.debug_calls.append((msg, args, kwargs))
        self.messages.append(('DEBUG', msg, args, kwargs))

    def info(self, msg: str, *args, **kwargs) -> None:
        self.info_calls.append((msg, args, kwargs))
        self.messages.append(('INFO', msg, args, kwargs))

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.warning_calls.append((msg, args, kwargs))
        self.messages.append(('WARNING', msg, args, kwargs))

    def error(self, msg: str, *args, **kwargs) -> None:
        self.error_calls.append((msg, args, kwargs))
        self.messages.append(('ERROR', msg, args, kwargs))

    def critical(self, msg: str, *args, **kwargs) -> None:
        self.critical_calls.append((msg, args, kwargs))
        self.messages.append(('CRITICAL', msg, args, kwargs))

    def reset(self) -> None:
        """Reset all logged messages."""
        self.messages.clear()
        self.debug_calls.clear()
        self.info_calls.clear()
        self.warning_calls.clear()
        self.error_calls.clear()
        self.critical_calls.clear()

    def assert_logged(self, level: str, message: str) -> bool:
        """Assert that a message was logged at the specified level."""
        for logged_level, logged_msg, _, _ in self.messages:
            if logged_level == level and message in logged_msg:
                return True
        return False

    def get_messages_by_level(self, level: str) -> list:
        """Get all messages logged at the specified level."""
        return [msg for logged_level, msg, _, _ in self.messages if logged_level == level]


class MockDataHub:
    """A mock data hub for testing."""
    
    def __init__(self):
        self._data = {}
        self._saved_data = {}
        self._loaded_data = {}

    def add_data_sources(self, new_sources: dict) -> None:
        """Mock method for adding data sources."""
        pass

    def register(self, name: str, data: Any) -> None:
        """Register data with the hub."""
        self._data[name] = data

    def get(self, name: str) -> Any:
        """Get data from the hub."""
        self._loaded_data[name] = self._data.get(name)
        return self._data.get(name)

    def get_path(self, name: str) -> Optional[str]:
        """Get the path for a data source."""
        return f"/mock/path/{name}"

    def save(self, data: Any, path: str, handler_args: dict | None = None) -> None:
        """Save data to a path."""
        self._saved_data[path] = data

    def __contains__(self, name: str) -> bool:
        return name in self._data

    def reset(self) -> None:
        """Reset the mock data hub."""
        self._data.clear()
        self._saved_data.clear()
        self._loaded_data.clear()

    def get_saved_data(self, path: str) -> Any:
        """Get data that was saved to a path."""
        return self._saved_data.get(path)

    def get_loaded_data_names(self) -> list:
        """Get names of data that was loaded."""
        return list(self._loaded_data.keys())