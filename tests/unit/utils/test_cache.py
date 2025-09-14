"""
Unit tests for the cache utilities module.
"""

import time
import tempfile
import os
from pathlib import Path
import pytest

from nexus.core.utils.cache import (
    memory_cache,
    clear_memory_cache,
    get_memory_cache_stats,
    FileCache,
    initialize_file_cache,
    get_file_cache
)


def test_memory_cache_basic():
    """Test basic memory caching functionality."""
    call_count = 0
    
    @memory_cache()
    def expensive_function(x, y):
        nonlocal call_count
        call_count += 1
        return x + y
    
    # First call should execute the function
    result1 = expensive_function(1, 2)
    assert result1 == 3
    assert call_count == 1
    
    # Second call with same args should use cache
    result2 = expensive_function(1, 2)
    assert result2 == 3
    assert call_count == 1  # Function should not be called again
    
    # Call with different args should execute the function
    result3 = expensive_function(2, 3)
    assert result3 == 5
    assert call_count == 2


def test_memory_cache_with_ttl():
    """Test memory caching with time-to-live expiration."""
    call_count = 0
    
    @memory_cache(ttl=1)  # 1 second TTL
    def time_sensitive_function(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # First call
    result1 = time_sensitive_function(5)
    assert result1 == 10
    assert call_count == 1
    
    # Second call should use cache
    result2 = time_sensitive_function(5)
    assert result2 == 10
    assert call_count == 1
    
    # Wait for cache to expire
    time.sleep(1.1)
    
    # Third call should execute function again due to TTL expiration
    result3 = time_sensitive_function(5)
    assert result3 == 10
    assert call_count == 2


def test_clear_memory_cache():
    """Test clearing the memory cache."""
    call_count = 0
    
    @memory_cache()
    def cached_function(x):
        nonlocal call_count
        call_count += 1
        return x ** 2
    
    # Call function to populate cache
    result1 = cached_function(3)
    assert result1 == 9
    assert call_count == 1
    
    # Clear cache
    clear_memory_cache()
    
    # Call again - should execute function since cache was cleared
    result2 = cached_function(3)
    assert result2 == 9
    assert call_count == 2


def test_get_memory_cache_stats():
    """Test getting memory cache statistics."""
    clear_memory_cache()  # Ensure clean state
    
    @memory_cache()
    def dummy_function(x):
        return x
    
    # Populate cache
    dummy_function(1)
    dummy_function(2)
    
    # Get stats
    stats = get_memory_cache_stats()
    assert "cached_items" in stats
    assert "total_size_bytes" in stats
    assert stats["cached_items"] >= 2  # At least our two items


def test_file_cache_basic():
    """Test basic file caching functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        file_cache = FileCache(cache_dir)
        
        # Test setting and getting cache
        test_data = {"key": "value", "number": 42}
        file_cache.set("test_func", test_data, "arg1", kwarg="value")
        
        # Retrieve cached data
        retrieved_data = file_cache.get("test_func", "arg1", kwarg="value")
        assert retrieved_data == test_data


def test_file_cache_miss():
    """Test file cache miss returns None."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        file_cache = FileCache(cache_dir)
        
        # Try to get non-existent cache entry
        result = file_cache.get("nonexistent_func", "arg1")
        assert result is None


def test_file_cache_clear():
    """Test clearing file cache."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        file_cache = FileCache(cache_dir)
        
        # Add some cache entries
        file_cache.set("func1", "data1", "arg1")
        file_cache.set("func2", "data2", "arg2")
        
        # Verify cache has entries
        assert file_cache.get("func1", "arg1") == "data1"
        
        # Clear cache
        file_cache.clear()
        
        # Verify cache is empty
        assert file_cache.get("func1", "arg1") is None
        assert file_cache.get("func2", "arg2") is None


def test_initialize_and_get_file_cache():
    """Test initializing and getting global file cache."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "global_cache"
        
        # Initialize global file cache
        initialize_file_cache(cache_dir)
        
        # Get the global file cache
        global_cache = get_file_cache()
        assert global_cache is not None
        assert isinstance(global_cache, FileCache)
        
        # Test that it works
        global_cache.set("global_test", "global_data", "test_arg")
        retrieved = global_cache.get("global_test", "test_arg")
        assert retrieved == "global_data"