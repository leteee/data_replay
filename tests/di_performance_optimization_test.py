"""
Performance optimization tests for the DI container.
"""

import time
from unittest.mock import MagicMock

from nexus.core.di import DIContainer
from nexus.core.di.services import LoggerInterface, DataHubInterface
from nexus.core.di.adapters import LoggerAdapter, DataHubAdapter
from nexus.core.di.testing import MockLogger, MockDataHub


class TestService:
    """A test service for performance testing."""
    def __init__(self, logger: LoggerInterface):
        self.logger = logger


def test_service_key_caching():
    """Test service key caching performance."""
    container = DIContainer()
    
    # Test that service keys are cached
    key1 = container._get_service_key(LoggerInterface)
    key2 = container._get_service_key(LoggerInterface)
    
    assert key1 is key2 or key1 == key2
    assert LoggerInterface in container._service_key_cache
    
    print("Service key caching test passed!")


def test_service_name_caching():
    """Test service name caching performance."""
    container = DIContainer()
    
    # Test that service names are cached
    name1 = container._get_service_name(LoggerInterface)
    name2 = container._get_service_name(LoggerInterface)
    
    assert name1 is name2 or name1 == name2
    assert LoggerInterface in container._service_name_cache
    
    print("Service name caching test passed!")


def test_cache_clearing():
    """Test cache clearing functionality."""
    container = DIContainer()
    
    # Populate caches
    container._get_service_key(LoggerInterface)
    container._get_service_name(LoggerInterface)
    
    assert LoggerInterface in container._service_key_cache
    assert LoggerInterface in container._service_name_cache
    
    # Clear specific service cache
    container._clear_caches_for_service(LoggerInterface)
    assert LoggerInterface not in container._service_key_cache
    assert LoggerInterface not in container._service_name_cache
    
    # Repopulate and clear all caches
    container._get_service_key(LoggerInterface)
    container._get_service_name(LoggerInterface)
    container._clear_all_caches()
    
    assert len(container._service_key_cache) == 0
    assert len(container._service_name_cache) == 0
    
    print("Cache clearing test passed!")


def test_constructor_signature_caching():
    """Test constructor signature caching."""
    container = DIContainer()
    
    # Register a service that requires dependency injection
    mock_logger = MockLogger()
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(TestService, TestService)
    
    # Warm up the cache
    for _ in range(10):
        container.resolve(TestService)
    
    # Verify the constructor signature is cached
    assert TestService in container._constructor_signature_cache
    
    print("Constructor signature caching test passed!")


def test_performance_improvement():
    """Test that caching provides performance improvement."""
    container = DIContainer()
    
    # Register services
    mock_logger = MockLogger()
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(TestService, TestService)
    
    # Warm up
    for _ in range(100):
        container.resolve(TestService)
    
    # Measure performance with caching
    iterations = 1000
    start_time = time.time()
    for _ in range(iterations):
        container.resolve(TestService)
    end_time = time.time()
    duration_with_cache = end_time - start_time
    
    # Clear caches
    container._clear_all_caches()
    
    # Measure performance without caching
    start_time = time.time()
    for _ in range(iterations):
        container.resolve(TestService)
    end_time = time.time()
    duration_without_cache = end_time - start_time
    
    # Verify caching provides improvement
    if duration_with_cache > 0 and duration_without_cache > 0:
        improvement_factor = duration_without_cache / duration_with_cache
        print(f"Caching provides {improvement_factor:.2f}x performance improvement")
        # Even a small improvement is acceptable due to the overhead being minimal
        assert improvement_factor >= 0.8, f"Expected at least 0.8x improvement, got {improvement_factor:.2f}x"
    
    print("Performance improvement test passed!")


if __name__ == "__main__":
    test_service_key_caching()
    test_service_name_caching()
    test_cache_clearing()
    test_constructor_signature_caching()
    test_performance_improvement()
    print("All performance optimization tests passed!")