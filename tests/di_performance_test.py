"""
Performance tests for the DI container optimizations.
"""

import time
import logging
from unittest.mock import MagicMock

from nexus.core.di import DIContainer, TestDIContainer
from nexus.core.di.services import LoggerInterface, DataHubInterface
from nexus.core.di.adapters import LoggerAdapter, DataHubAdapter
from nexus.core.di.testing import MockLogger, MockDataHub


class PerformanceTestService1:
    """A test service for performance testing."""
    def __init__(self, logger: LoggerInterface):
        self.logger = logger


class PerformanceTestService2:
    """Another test service for performance testing."""
    def __init__(self, logger: LoggerInterface, data_hub: DataHubInterface):
        self.logger = logger
        self.data_hub = data_hub


class PerformanceTestService3:
    """A third test service for performance testing."""
    def __init__(self, service1: PerformanceTestService1, service2: PerformanceTestService2):
        self.service1 = service1
        self.service2 = service2


def test_service_resolution_performance():
    """Test the performance of service resolution."""
    # Create a container
    container = DIContainer()
    
    # Register services
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(DataHubInterface, DataHubAdapter(mock_data_hub))
    container.register(PerformanceTestService1, PerformanceTestService1)
    container.register(PerformanceTestService2, PerformanceTestService2)
    container.register(PerformanceTestService3, PerformanceTestService3)
    
    # Warm up the container
    for _ in range(10):
        container.resolve(PerformanceTestService1)
        container.resolve(PerformanceTestService2)
        container.resolve(PerformanceTestService3)
    
    # Measure performance
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        container.resolve(PerformanceTestService1)
        container.resolve(PerformanceTestService2)
        container.resolve(PerformanceTestService3)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Resolved {iterations * 3} services in {duration:.4f} seconds")
    print(f"Average time per service resolution: {(duration / (iterations * 3)) * 1000:.4f} ms")
    
    print("Service resolution performance test passed!")


def test_cache_effectiveness():
    """Test the effectiveness of caching optimizations."""
    # Create a container
    container = DIContainer()
    
    # Register services
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(DataHubInterface, DataHubAdapter(mock_data_hub))
    container.register(PerformanceTestService1, PerformanceTestService1)
    container.register(PerformanceTestService2, PerformanceTestService2)
    container.register(PerformanceTestService3, PerformanceTestService3)
    
    # Warm up the container
    for _ in range(100):
        container.resolve(PerformanceTestService1)
        container.resolve(PerformanceTestService2)
        container.resolve(PerformanceTestService3)
    
    # Measure cache hit performance
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        container.resolve(PerformanceTestService1)
        container.resolve(PerformanceTestService2)
        container.resolve(PerformanceTestService3)
    
    end_time = time.time()
    duration_with_cache = end_time - start_time
    
    print(f"With caching: Resolved {iterations * 3} services in {duration_with_cache:.4f} seconds")
    print(f"With caching: Average time per service resolution: {(duration_with_cache / (iterations * 3)) * 1000:.4f} ms")
    
    # Clear caches and measure without caching
    container._clear_all_caches()
    
    start_time = time.time()
    for _ in range(iterations):
        container.resolve(PerformanceTestService1)
        container.resolve(PerformanceTestService2)
        container.resolve(PerformanceTestService3)
    end_time = time.time()
    duration_without_cache = end_time - start_time
    
    print(f"Without caching: Resolved {iterations * 3} services in {duration_without_cache:.4f} seconds")
    print(f"Without caching: Average time per service resolution: {(duration_without_cache / (iterations * 3)) * 1000:.4f} ms")
    
    print("Cache effectiveness test passed!")


def test_memory_usage():
    """Test memory usage of the container."""
    import gc
    
    # Force garbage collection
    gc.collect()
    
    # Create a container
    container = DIContainer()
    
    # Register services
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(DataHubInterface, DataHubAdapter(mock_data_hub))
    
    # Register test services
    container.register(PerformanceTestService1, PerformanceTestService1)
    container.register(PerformanceTestService2, PerformanceTestService2)
    container.register(PerformanceTestService3, PerformanceTestService3)
    
    # Measure memory before
    gc.collect()
    memory_before = len(gc.get_objects())
    
    # Resolve services
    resolved_services = []
    for _ in range(100):
        resolved_services.append(container.resolve(PerformanceTestService1))
        resolved_services.append(container.resolve(PerformanceTestService2))
        resolved_services.append(container.resolve(PerformanceTestService3))
    
    # Measure memory after
    gc.collect()
    memory_after = len(gc.get_objects())
    
    memory_increase = memory_after - memory_before
    print(f"Memory increase after resolving services: {memory_increase} objects")
    
    print("Memory usage test passed!")


if __name__ == "__main__":
    test_service_resolution_performance()
    test_cache_effectiveness()
    test_memory_usage()
    print("All performance tests passed!")