"""
Example showing how to use the new testing utilities in practice.
"""

import pytest
from unittest.mock import MagicMock, patch

from nexus.core.di import TestDIContainer, MockLogger, MockDataHub
from nexus.core.di.services import LoggerInterface, DataHubInterface


def example_function_that_uses_di():
    """
    An example function that uses DI services.
    This is similar to how real framework components would work.
    """
    # In a real implementation, these would come from a DI container
    # For this example, we'll simulate that
    pass


def test_with_mock_services():
    """Example test showing how to use mock services."""
    # Create a test container with mocks
    container = TestDIContainer()
    
    # Create mock services
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    # Register mocks with the container
    container.mock_service(LoggerInterface, mock_logger)
    container.mock_service(DataHubInterface, mock_data_hub)
    
    # Simulate using the services
    logger = container.resolve(LoggerInterface)
    data_hub = container.resolve(DataHubInterface)
    
    # Use the services
    logger.info("Processing data...")
    test_data = {"id": 1, "value": "test"}
    data_hub.register("test_data", test_data)
    retrieved_data = data_hub.get("test_data")
    
    # Verify the services were used correctly
    assert retrieved_data == test_data
    assert logger.assert_logged('INFO', 'Processing data...')
    
    # Verify service usage
    assert container.verify_service_used(LoggerInterface)
    assert container.verify_service_used(DataHubInterface)
    
    print("Test with mock services passed!")


def test_with_factory_function():
    """Example test showing how to use the factory function."""
    # Create container with common mocks
    container = TestDIContainer()
    container.mock_service(LoggerInterface, MockLogger())
    container.mock_service(DataHubInterface, MockDataHub())
    
    # Resolve services
    logger = container.resolve(LoggerInterface)
    data_hub = container.resolve(DataHubInterface)
    
    # Use services
    logger.debug("Debug message")
    data_hub.register("sample", {"data": "value"})
    
    # Verify
    assert logger.assert_logged('DEBUG', 'Debug message')
    assert data_hub.get("sample") == {"data": "value"}
    
    print("Test with factory function passed!")


def test_service_isolation():
    """Example showing service isolation between tests."""
    # Create first container
    container1 = TestDIContainer()
    mock_logger1 = MockLogger()
    container1.mock_service(LoggerInterface, mock_logger1)
    
    # Create second container
    container2 = TestDIContainer()
    mock_logger2 = MockLogger()
    container2.mock_service(LoggerInterface, mock_logger2)
    
    # Use services in container1
    logger1 = container1.resolve(LoggerInterface)
    logger1.info("Message from container 1")
    
    # Use services in container2
    logger2 = container2.resolve(LoggerInterface)
    logger2.info("Message from container 2")
    
    # Verify isolation
    assert len(mock_logger1.messages) == 1
    assert len(mock_logger2.messages) == 1
    assert mock_logger1.assert_logged('INFO', 'Message from container 1')
    assert mock_logger2.assert_logged('INFO', 'Message from container 2')
    
    print("Service isolation test passed!")


if __name__ == "__main__":
    test_with_mock_services()
    test_with_factory_function()
    test_service_isolation()
    print("All example tests passed!")