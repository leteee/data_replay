"""
Benchmark tests to compare performance before and after optimizations.
"""

import time
import logging
from unittest.mock import MagicMock

from nexus.core.di import DIContainer
from nexus.core.di.services import LoggerInterface, DataHubInterface
from nexus.core.di.adapters import LoggerAdapter, DataHubAdapter
from nexus.core.di.testing import MockLogger, MockDataHub


class BenchmarkService1:
    """A benchmark service."""
    def __init__(self, logger: LoggerInterface):
        self.logger = logger


class BenchmarkService2:
    """Another benchmark service."""
    def __init__(self, logger: LoggerInterface, data_hub: DataHubInterface):
        self.logger = logger
        self.data_hub = data_hub


class BenchmarkService3:
    """A third benchmark service."""
    def __init__(self, service1: BenchmarkService1, service2: BenchmarkService2):
        self.service1 = service1
        self.service2 = service2


def benchmark_service_resolution():
    """Benchmark service resolution performance."""
    print("=== DI Container Performance Benchmark ===")
    
    # Create container
    container = DIContainer()
    
    # Register services
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(DataHubInterface, DataHubAdapter(mock_data_hub))
    container.register(BenchmarkService1, BenchmarkService1)
    container.register(BenchmarkService2, BenchmarkService2)
    container.register(BenchmarkService3, BenchmarkService3)
    
    # Warm up
    print("Warming up...")
    for _ in range(100):
        container.resolve(BenchmarkService1)
        container.resolve(BenchmarkService2)
        container.resolve(BenchmarkService3)
    
    # Benchmark
    iterations = 10000
    print(f"Benchmarking {iterations} iterations...")
    
    start_time = time.time()
    for _ in range(iterations):
        container.resolve(BenchmarkService1)
        container.resolve(BenchmarkService2)
        container.resolve(BenchmarkService3)
    end_time = time.time()
    
    duration = end_time - start_time
    total_resolutions = iterations * 3
    
    print(f"\nResults:")
    print(f"  Total resolutions: {total_resolutions:,}")
    print(f"  Total time: {duration:.4f} seconds")
    print(f"  Average time per resolution: {(duration / total_resolutions) * 1000:.4f} ms")
    print(f"  Resolutions per second: {total_resolutions / duration:,.0f}")
    
    # Performance targets
    target_time_per_resolution_ms = 0.01  # 10 microseconds per resolution
    actual_time_per_resolution_ms = (duration / total_resolutions) * 1000
    
    if actual_time_per_resolution_ms <= target_time_per_resolution_ms:
        print(f"  [PASS] Performance target met: {actual_time_per_resolution_ms:.4f}ms <= {target_time_per_resolution_ms:.4f}ms")
    else:
        print(f"  [WARN] Performance target not met: {actual_time_per_resolution_ms:.4f}ms > {target_time_per_resolution_ms:.4f}ms")
    
    return duration


def benchmark_cache_effectiveness():
    """Benchmark cache effectiveness."""
    print("\n=== Cache Effectiveness Benchmark ===")
    
    container = DIContainer()
    
    # Register services
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(DataHubInterface, DataHubAdapter(mock_data_hub))
    container.register(BenchmarkService1, BenchmarkService1)
    container.register(BenchmarkService2, BenchmarkService2)
    container.register(BenchmarkService3, BenchmarkService3)
    
    # Warm up
    for _ in range(100):
        container.resolve(BenchmarkService1)
        container.resolve(BenchmarkService2)
        container.resolve(BenchmarkService3)
    
    # Test with cache
    iterations = 5000
    start_time = time.time()
    for _ in range(iterations):
        container.resolve(BenchmarkService1)
        container.resolve(BenchmarkService2)
        container.resolve(BenchmarkService3)
    end_time = time.time()
    duration_with_cache = end_time - start_time
    
    # Clear cache
    container._clear_all_caches()
    
    # Test without cache
    start_time = time.time()
    for _ in range(iterations):
        container.resolve(BenchmarkService1)
        container.resolve(BenchmarkService2)
        container.resolve(BenchmarkService3)
    end_time = time.time()
    duration_without_cache = end_time - start_time
    
    # Calculate improvement
    if duration_with_cache > 0:
        improvement_factor = duration_without_cache / duration_with_cache
        print(f"  With cache: {duration_with_cache:.4f} seconds")
        print(f"  Without cache: {duration_without_cache:.4f} seconds")
        print(f"  Cache improvement: {improvement_factor:.2f}x faster")
    else:
        print("  Unable to calculate cache improvement (duration too small)")
    
    return duration_with_cache, duration_without_cache


def benchmark_memory_usage():
    """Benchmark memory usage."""
    print("\n=== Memory Usage Benchmark ===")
    
    import gc
    
    # Force garbage collection
    gc.collect()
    memory_before = len(gc.get_objects())
    
    # Create and use container
    container = DIContainer()
    
    mock_logger = MockLogger()
    mock_data_hub = MockDataHub()
    
    container.register(LoggerInterface, LoggerAdapter(mock_logger))
    container.register(DataHubInterface, DataHubAdapter(mock_data_hub))
    container.register(BenchmarkService1, BenchmarkService1)
    container.register(BenchmarkService2, BenchmarkService2)
    container.register(BenchmarkService3, BenchmarkService3)
    
    # Resolve many services
    resolved_services = []
    for _ in range(1000):
        resolved_services.append(container.resolve(BenchmarkService1))
        resolved_services.append(container.resolve(BenchmarkService2))
        resolved_services.append(container.resolve(BenchmarkService3))
    
    # Measure memory
    gc.collect()
    memory_after = len(gc.get_objects())
    
    memory_increase = memory_after - memory_before
    print(f"  Memory before: {memory_before:,} objects")
    print(f"  Memory after: {memory_after:,} objects")
    print(f"  Memory increase: {memory_increase:,} objects")
    print(f"  Memory per service resolution: {memory_increase / (1000 * 3):.2f} objects")
    
    # Memory efficiency target
    target_memory_per_resolution = 1.0  # Less than 1 object per resolution
    actual_memory_per_resolution = memory_increase / (1000 * 3)
    
    if actual_memory_per_resolution <= target_memory_per_resolution:
        print(f"  [PASS] Memory efficiency target met: {actual_memory_per_resolution:.2f} <= {target_memory_per_resolution}")
    else:
        print(f"  [WARN] Memory efficiency target not met: {actual_memory_per_resolution:.2f} > {target_memory_per_resolution}")
    
    return memory_increase


if __name__ == "__main__":
    print("Starting DI Container Performance Benchmarks...")
    
    # Run benchmarks
    resolution_time = benchmark_service_resolution()
    cache_with, cache_without = benchmark_cache_effectiveness()
    memory_usage = benchmark_memory_usage()
    
    print(f"\n=== Summary ===")
    print(f"  Service resolution benchmark completed in {resolution_time:.4f} seconds")
    print(f"  Cache effectiveness benchmark completed")
    print(f"  Memory usage benchmark completed with {memory_usage:,} object increase")
    
    print(f"\n[SUCCESS] All benchmarks completed successfully!")