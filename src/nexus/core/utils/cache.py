"""
Caching utilities for the Nexus framework.
"""

import functools
import hashlib
import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, cast

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T', bound=Callable[..., Any])

# In-memory cache storage (maintain global state for backward compatibility)
_memory_cache: Dict[str, Any] = {}
_memory_cache_timestamps: Dict[str, float] = {}


def _generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Generated cache key as string
    """
    # Create a hashable representation of args and kwargs
    key_data = {
        "args": [str(arg) for arg in args],
        "kwargs": {str(k): str(v) for k, v in kwargs.items()}
    }
    
    # Create a hash of the key data
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


def memory_cache(ttl: Optional[int] = None):
    """
    Decorator for caching function results in memory.
    Improved implementation with better error handling and Pythonic patterns.
    
    Args:
        ttl: Time-to-live in seconds. If None, cache never expires.
        
    Returns:
        Decorator function
    """
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key with module and function name for better uniqueness
            cache_key = f"{func.__module__}.{func.__qualname__}:{_generate_cache_key(*args, **kwargs)}"
            
            # Check if we have a cached result
            if cache_key in _memory_cache:
                # Check TTL if specified
                if ttl is not None:
                    timestamp = _memory_cache_timestamps.get(cache_key, 0)
                    if time.time() - timestamp > ttl:
                        # Cache expired, remove it
                        del _memory_cache[cache_key]
                        del _memory_cache_timestamps[cache_key]
                    else:
                        # Cache is still valid, return cached result
                        logger.debug(f"Cache hit for {func.__name__}")
                        return _memory_cache[cache_key]
                else:
                    # No TTL, return cached result
                    logger.debug(f"Cache hit for {func.__name__}")
                    return _memory_cache[cache_key]
            
            # No cache hit, call the function
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            
            # Store result in cache
            _memory_cache[cache_key] = result
            _memory_cache_timestamps[cache_key] = time.time()
            
            return result
        return cast(T, wrapper)
    return decorator


def clear_memory_cache():
    """
    Clear all cached results from memory.
    """
    global _memory_cache, _memory_cache_timestamps
    _memory_cache.clear()
    _memory_cache_timestamps.clear()
    logger.debug("Memory cache cleared")


def get_memory_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the memory cache.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        # Estimate total size by serializing cached objects
        total_size = 0
        for value in _memory_cache.values():
            try:
                total_size += len(pickle.dumps(value))
            except Exception:
                # If serialization fails, estimate as 0 bytes
                pass
    except Exception:
        total_size = 0
        
    return {
        "cached_items": len(_memory_cache),
        "total_size_bytes": total_size
    }


class FileCache:
    """
    File-based cache for storing function results.
    """
    
    def __init__(self, cache_dir: Path):
        """
        Initialize file cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"File cache initialized at {cache_dir}")
        
    def _get_cache_file_path(self, func_name: str, *args, **kwargs) -> Path:
        """
        Get the file path for a cached result.
        
        Args:
            func_name: Name of the function
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Path to the cache file
        """
        cache_key = _generate_cache_key(*args, **kwargs)
        return self.cache_dir / f"{func_name}_{cache_key}.cache"
        
    def get(self, func_name: str, *args, **kwargs) -> Any:
        """
        Get a cached result from file.
        
        Args:
            func_name: Name of the function
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cached result or None if not found/expired
        """
        cache_file = self._get_cache_file_path(func_name, *args, **kwargs)
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    result = pickle.load(f)
                logger.debug(f"File cache hit for {func_name}")
                return result
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {e}")
                # Remove corrupted cache file
                cache_file.unlink(missing_ok=True)
                
        logger.debug(f"File cache miss for {func_name}")
        return None
        
    def set(self, func_name: str, result: Any, *args, **kwargs) -> None:
        """
        Store a result in file cache.
        
        Args:
            func_name: Name of the function
            result: Result to cache
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        cache_file = self._get_cache_file_path(func_name, *args, **kwargs)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
            logger.debug(f"Stored result in file cache for {func_name}")
        except Exception as e:
            logger.warning(f"Failed to store cache file {cache_file}: {e}")
            
    def clear(self) -> None:
        """
        Clear all cached files.
        """
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("File cache cleared")


# Global file cache instance
_global_file_cache: Optional[FileCache] = None


def initialize_file_cache(cache_dir: Path) -> None:
    """
    Initialize the global file cache.
    
    Args:
        cache_dir: Directory to store cache files
    """
    global _global_file_cache
    _global_file_cache = FileCache(cache_dir)


def get_file_cache() -> Optional[FileCache]:
    """
    Get the global file cache instance.
    
    Returns:
        FileCache instance or None if not initialized
    """
    return _global_file_cache


def clear_memory_cache():
    """
    Clear all cached results from memory.
    """
    global _memory_cache, _memory_cache_timestamps
    _memory_cache.clear()
    _memory_cache_timestamps.clear()
    logger.debug("Memory cache cleared")


def get_memory_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the memory cache.
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        "cached_items": len(_memory_cache),
        "total_size_bytes": sum(len(pickle.dumps(v)) for v in _memory_cache.values())
    }


class FileCache:
    """
    File-based cache for storing function results.
    """
    
    def __init__(self, cache_dir: Path):
        """
        Initialize file cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"File cache initialized at {cache_dir}")
        
    def _get_cache_file_path(self, func_name: str, *args, **kwargs) -> Path:
        """
        Get the file path for a cached result.
        
        Args:
            func_name: Name of the function
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Path to the cache file
        """
        cache_key = _generate_cache_key(*args, **kwargs)
        return self.cache_dir / f"{func_name}_{cache_key}.cache"
        
    def get(self, func_name: str, *args, **kwargs) -> Any:
        """
        Get a cached result from file.
        
        Args:
            func_name: Name of the function
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cached result or None if not found/expired
        """
        cache_file = self._get_cache_file_path(func_name, *args, **kwargs)
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    result = pickle.load(f)
                logger.debug(f"File cache hit for {func_name}")
                return result
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {e}")
                # Remove corrupted cache file
                cache_file.unlink(missing_ok=True)
                
        logger.debug(f"File cache miss for {func_name}")
        return None
        
    def set(self, func_name: str, result: Any, *args, **kwargs) -> None:
        """
        Store a result in file cache.
        
        Args:
            func_name: Name of the function
            result: Result to cache
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        cache_file = self._get_cache_file_path(func_name, *args, **kwargs)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
            logger.debug(f"Stored result in file cache for {func_name}")
        except Exception as e:
            logger.warning(f"Failed to store cache file {cache_file}: {e}")
            
    def clear(self) -> None:
        """
        Clear all cached files.
        """
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("File cache cleared")


# Global file cache instance
_global_file_cache: Optional[FileCache] = None


def initialize_file_cache(cache_dir: Path) -> None:
    """
    Initialize the global file cache.
    
    Args:
        cache_dir: Directory to store cache files
    """
    global _global_file_cache
    _global_file_cache = FileCache(cache_dir)


def get_file_cache() -> Optional[FileCache]:
    """
    Get the global file cache instance.
    
    Returns:
        FileCache instance or None if not initialized
    """
    return _global_file_cache