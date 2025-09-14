"""
Utility modules for the Nexus framework.
"""

from .cache import (
    memory_cache,
    clear_memory_cache,
    get_memory_cache_stats,
    FileCache,
    initialize_file_cache,
    get_file_cache
)

from .data_processing import (
    DataProcessor,
    get_data_processor,
    optimize_dataframe_access,
    vectorize_operations,
    parallel_apply,
    batch_process,
    lazy_load_dataframe
)

__all__ = [
    "memory_cache",
    "clear_memory_cache",
    "get_memory_cache_stats",
    "FileCache",
    "initialize_file_cache",
    "get_file_cache",
    "DataProcessor",
    "get_data_processor",
    "optimize_dataframe_access",
    "vectorize_operations",
    "parallel_apply",
    "batch_process",
    "lazy_load_dataframe"
]