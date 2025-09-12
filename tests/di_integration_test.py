"""
Integration tests for the dependency injection container.
"""

import pytest
import logging
from pathlib import Path

from nexus.core.di import container, DIContainer, LoggerInterface, DataHubInterface
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


if __name__ == "__main__":
    test_di_container_integration()
    test_singleton_lifecycle_integration()
    test_global_container_functionality()
    print("All DI integration tests passed!")