"""
Integration tests for the dependency injection container.
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import MagicMock

from nexus.core.di import container, DIContainer, LoggerInterface, DataHubInterface
from nexus.core.di.exceptions import ServiceResolutionException
from nexus.core.di.testing import TestDIContainer, MockLogger, MockDataHub
from nexus.core.di.adapters import LoggerAdapter, DataHubAdapter
from nexus.core.data.hub import DataHub


def test_di_container_integration():
    """Test integration of DI container with framework services."""
    # Create a new container for testing
    test_container = DIContainer()
    
    # Register a logger service
    logger = logging.getLogger(__name__)
    test_container.register(LoggerInterface, LoggerAdapter(logger))
    
    # Register a data hub service
    data_hub = DataHub(case_path=Path("."))
    test_container.register(DataHubInterface, DataHubAdapter(data_hub))
    
    # Resolve services
    resolved_logger = test_container.resolve(LoggerInterface)
    resolved_data_hub = test_container.resolve(DataHubInterface)
    
    # Verify services are correctly resolved
    assert isinstance(resolved_logger, LoggerAdapter)
    assert isinstance(resolved_data_hub, DataHubAdapter)
    print("DI container integration test passed!")


def test_singleton_lifecycle_integration():
    """Test singleton lifecycle management in DI container."""
    # Create a new container for testing
    test_container = DIContainer()
    
    # Register a service as singleton
    logger = logging.getLogger(__name__)
    test_container.register(LoggerInterface, LoggerAdapter(logger), "singleton")
    
    # Resolve the service twice
    resolved_logger1 = test_container.resolve(LoggerInterface)
    resolved_logger2 = test_container.resolve(LoggerInterface)
    
    # Check that both resolved instances are the same
    assert resolved_logger1 is resolved_logger2
    print("Singleton lifecycle integration test passed!")


def test_global_container_functionality():
    """Test global container functionality."""
    # Clear any existing registrations
    container.clear()
    
    # Register a service with the global container
    logger = logging.getLogger(__name__)
    container.register(LoggerInterface, LoggerAdapter(logger))
    
    # Resolve the service
    resolved_logger = container.resolve(LoggerInterface)
    
    # Verify service is correctly resolved
    assert isinstance(resolved_logger, LoggerAdapter)
    
    # Clear the container
    container.clear()
    print("Global container functionality test passed!")


def test_bulk_service_registration():
    """Test the new bulk service registration feature."""
    # Create a test container
    test_container = DIContainer()
    
    # Create a mock context
    logger = logging.getLogger(__name__)
    data_hub = DataHub(case_path=Path("."))
    
    class MockContext:
        def __init__(self):
            self.logger = logger
            self.data_hub = data_hub
    
    context = MockContext()
    
    # Test bulk registration
    test_container.register_core_services(context)
    
    # Verify services were registered
    resolved_logger = test_container.resolve(LoggerInterface)
    assert isinstance(resolved_logger, LoggerAdapter)
    
    print("Bulk service registration test passed!")


def test_enhanced_error_handling():
    """Test enhanced error handling in the DI container."""
    # Create a test container
    test_container = DIContainer()
    
    # Test ServiceResolutionException
    try:
        # Try to resolve a service that is not registered
        test_container.resolve(logging.Logger)
        assert False, "Expected ServiceResolutionException was not raised"
    except ServiceResolutionException as e:
        print(f"ServiceResolutionException caught as expected: {e}")
        assert "logging.Logger" in e.service_type
    except Exception as e:
        assert False, f"Wrong exception type: {type(e)} - {e}"
    
    print("Enhanced error handling test passed!")


def test_test_di_container_functionality():
    """Test the TestDIContainer functionality."""
    # Create a test container
    test_container = TestDIContainer()
    
    # Test mock service registration
    mock_logger = MagicMock()
    test_container.mock_service(LoggerInterface, mock_logger)
    
    # Test service resolution
    resolved_logger = test_container.resolve(LoggerInterface)
    assert resolved_logger is mock_logger
    
    # Test service verification
    # First, let's use the service
    resolved_logger.info("Test message")
    
    # Verify the service was used
    assert test_container.verify_service_used(LoggerInterface)
    
    print("TestDIContainer functionality test passed!")


def test_mock_logger_functionality():
    """Test the MockLogger functionality."""
    mock_logger = MockLogger()
    
    # Test logging methods
    mock_logger.debug("Debug message")
    mock_logger.info("Info message")
    mock_logger.warning("Warning message")
    mock_logger.error("Error message")
    mock_logger.critical("Critical message")
    
    # Verify messages were logged
    assert len(mock_logger.messages) == 5
    assert mock_logger.assert_logged('DEBUG', 'Debug message')
    assert mock_logger.assert_logged('INFO', 'Info message')
    assert mock_logger.assert_logged('WARNING', 'Warning message')
    assert mock_logger.assert_logged('ERROR', 'Error message')
    assert mock_logger.assert_logged('CRITICAL', 'Critical message')
    
    # Test message retrieval by level
    debug_messages = mock_logger.get_messages_by_level('DEBUG')
    assert len(debug_messages) == 1
    assert 'Debug message' in debug_messages[0]
    
    # Test reset functionality
    mock_logger.reset()
    assert len(mock_logger.messages) == 0
    assert len(mock_logger.debug_calls) == 0
    
    print("MockLogger functionality test passed!")


def test_mock_data_hub_functionality():
    """Test the MockDataHub functionality."""
    mock_data_hub = MockDataHub()
    
    # Test data registration and retrieval
    test_data = {"key": "value"}
    mock_data_hub.register("test_data", test_data)
    
    # Test data retrieval
    retrieved_data = mock_data_hub.get("test_data")
    assert retrieved_data == test_data
    
    # Test data containment
    assert "test_data" in mock_data_hub
    assert "nonexistent_data" not in mock_data_hub
    
    # Test path retrieval
    path = mock_data_hub.get_path("test_data")
    assert path == "/mock/path/test_data"
    
    # Test data saving
    mock_data_hub.save({"saved": "data"}, "/mock/save/path")
    saved_data = mock_data_hub.get_saved_data("/mock/save/path")
    assert saved_data == {"saved": "data"}
    
    # Test loaded data tracking
    loaded_names = mock_data_hub.get_loaded_data_names()
    assert "test_data" in loaded_names
    
    # Test reset functionality
    mock_data_hub.reset()
    assert len(mock_data_hub._data) == 0
    assert len(mock_data_hub._saved_data) == 0
    assert len(mock_data_hub._loaded_data) == 0
    
    print("MockDataHub functionality test passed!")


if __name__ == "__main__":
    test_di_container_integration()
    test_singleton_lifecycle_integration()
    test_global_container_functionality()
    test_bulk_service_registration()
    test_enhanced_error_handling()
    test_test_di_container_functionality()
    test_mock_logger_functionality()
    test_mock_data_hub_functionality()
    print("All DI integration tests passed!")