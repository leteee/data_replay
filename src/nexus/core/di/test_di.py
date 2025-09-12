"""
Test module for the dependency injection container.
"""

import logging
from pathlib import Path

from nexus.core.di import container, DIContainer, LoggerInterface, DataHubInterface
from nexus.core.di.adapters import LoggerAdapter


def test_basic_di_functionality():
    """Test basic dependency injection functionality."""
    # Create a new container for testing
    test_container = DIContainer()
    
    # Register a service
    logger = logging.getLogger(__name__)
    test_container.register(LoggerInterface, LoggerAdapter(logger))
    
    # Resolve the service
    resolved_logger = test_container.resolve(LoggerInterface)
    
    # Check that the resolved service is of the correct type
    assert isinstance(resolved_logger, LoggerAdapter)
    print("Basic DI functionality test passed!")


def test_singleton_lifecycle():
    """Test singleton lifecycle management."""
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
    print("Singleton lifecycle test passed!")


if __name__ == "__main__":
    test_basic_di_functionality()
    test_singleton_lifecycle()
    print("All DI tests passed!")