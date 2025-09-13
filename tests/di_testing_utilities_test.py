"""
Test for the new testing utilities in the DI system.
"""

import logging
from unittest.mock import MagicMock, patch

from nexus.core.di import TestDIContainer, MockLogger, MockDataHub
from nexus.core.di.services import LoggerInterface, DataHubInterface


def test_test_di_container():
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
    
    print("TestDIContainer test passed!")


def test_mock_logger():
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
    
    print("MockLogger test passed!")


def test_mock_data_hub():
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
    
    print("MockDataHub test passed!")


def test_create_test_container_with_mocks():
    """Test the create_test_container_with_mocks function."""
    # This would be implemented in testing.py
    # For now, let's just test the concept
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    # Create container with mocks
    test_container = TestDIContainer()
    test_container.mock_service(LoggerInterface, mock_logger)
    test_container.mock_service(DataHubInterface, mock_data_hub)
    
    # Verify mocks were registered
    resolved_logger = test_container.resolve(LoggerInterface)
    resolved_data_hub = test_container.resolve(DataHubInterface)
    
    assert isinstance(resolved_logger, MockLogger)
    assert isinstance(resolved_data_hub, MockDataHub)
    
    print("Create test container with mocks test passed!")


if __name__ == "__main__":
    test_test_di_container()
    test_mock_logger()
    test_mock_data_hub()
    test_create_test_container_with_mocks()
    print("All testing utilities tests passed!")