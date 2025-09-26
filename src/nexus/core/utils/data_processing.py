"""
Utilities for optimized data processing in the Nexus framework.
"""

import logging
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from pathlib import Path

from .cache import memory_cache, get_file_cache

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Utility class for optimized data processing operations.
    """
    
    def __init__(self, cache_enabled: bool = True):
        """
        Initialize the data processor.
        
        Args:
            cache_enabled: Whether to enable caching for operations
        """
        self.cache_enabled = cache_enabled
        self.file_cache = get_file_cache() if cache_enabled else None
        
    def optimize_dataframe_access(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Optimize DataFrame column access by selecting only needed columns.
        
        Args:
            df: Input DataFrame
            columns: List of columns to select
            
        Returns:
            DataFrame with selected columns
        """
        if not columns:
            return df.copy()
            
        # Only select columns that exist in the DataFrame
        existing_columns = [col for col in columns if col in df.columns]
        if existing_columns:
            return df[existing_columns].copy()
        else:
            # Return empty DataFrame with same index
            return df.iloc[:0].copy()
            
    def vectorize_operations(self, df: pd.DataFrame, operations: Dict[str, Callable]) -> pd.DataFrame:
        """
        Apply vectorized operations to DataFrame columns.
        
        Args:
            df: Input DataFrame
            operations: Dictionary mapping column names to operation functions
            
        Returns:
            DataFrame with applied operations
        """
        result_df = df.copy()
        
        for column, operation in operations.items():
            if column in result_df.columns:
                try:
                    # Apply operation vectorized
                    result_df[column] = operation(result_df[column])
                except Exception as e:
                    logger.warning(f"Failed to apply operation to column {column}: {e}")
                    
        return result_df
        
    def parallel_apply(self, df: pd.DataFrame, func: Callable, 
                      column_groups: List[List[str]], 
                      n_workers: int = None) -> pd.DataFrame:
        """
        Apply function to groups of columns in parallel.
        
        Args:
            df: Input DataFrame
            func: Function to apply to each group
            column_groups: List of column groups to process
            n_workers: Number of worker processes (defaults to CPU count)
            
        Returns:
            DataFrame with applied functions
        """
        if n_workers is None:
            n_workers = min(mp.cpu_count(), len(column_groups))
            
        if n_workers <= 1 or len(column_groups) <= 1:
            # No need for parallel processing
            result_df = df.copy()
            for columns in column_groups:
                subset = df[columns]
                processed = func(subset)
                result_df[columns] = processed[columns]
            return result_df
            
        # Use ProcessPoolExecutor for CPU-bound operations
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = []
            for columns in column_groups:
                subset = df[columns]
                future = executor.submit(func, subset)
                futures.append((future, columns))
                
            result_df = df.copy()
            for future, columns in futures:
                try:
                    processed = future.result()
                    result_df[columns] = processed[columns]
                except Exception as e:
                    logger.warning(f"Failed to process columns {columns}: {e}")
                    
        return result_df
        
    def batch_process(self, items: List[Any], process_func: Callable, 
                     batch_size: int = 100, n_workers: int = None) -> List[Any]:
        """
        Process items in batches using thread pool.
        
        Args:
            items: List of items to process
            process_func: Function to process each item
            batch_size: Size of each batch
            n_workers: Number of worker threads
            
        Returns:
            List of processed items
        """
        if not items:
            return []
            
        if n_workers is None:
            n_workers = min(mp.cpu_count(), len(items))
            
        # Process in batches
        results = []
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_futures = [executor.submit(process_func, item) for item in batch]
                
                for future in batch_futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.warning(f"Failed to process item: {e}")
                        results.append(None)
                        
        return results
        
    def lazy_load_dataframe(self, path: Path, columns: List[str] = None, 
                           chunksize: int = None) -> Union[pd.DataFrame, pd.io.parsers.TextFileReader]:
        """
        Lazily load a DataFrame with optional column selection and chunking.
        
        Args:
            path: Path to the data file
            columns: Optional list of columns to load
            chunksize: Optional chunk size for iterative loading
            
        Returns:
            Loaded DataFrame or TextFileReader for chunked reading
        """
        try:
            # Use file extension to determine loader
            if path.suffix.lower() == '.csv':
                return pd.read_csv(path, usecols=columns, chunksize=chunksize)
            elif path.suffix.lower() == '.parquet':
                return pd.read_parquet(path, columns=columns)
            else:
                # Fallback to default loading
                return pd.read_csv(path, usecols=columns, chunksize=chunksize)
        except Exception as e:
            logger.error(f"Failed to lazy load DataFrame from {path}: {e}")
            raise


# Global instance
_data_processor: Optional[DataProcessor] = None


def get_data_processor() -> DataProcessor:
    """
    Get the global data processor instance.
    
    Returns:
        DataProcessor instance
    """
    global _data_processor
    if _data_processor is None:
        _data_processor = DataProcessor()
    return _data_processor


def optimize_dataframe_access(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Optimize DataFrame column access by selecting only needed columns.
    
    Args:
        df: Input DataFrame
        columns: List of columns to select
        
    Returns:
        DataFrame with selected columns
    """
    processor = get_data_processor()
    return processor.optimize_dataframe_access(df, columns)
    
    
def vectorize_operations(df: pd.DataFrame, operations: Dict[str, Callable]) -> pd.DataFrame:
    """
    Apply vectorized operations to DataFrame columns.
    
    Args:
        df: Input DataFrame
        operations: Dictionary mapping column names to operation functions
        
    Returns:
        DataFrame with applied operations
    """
    processor = get_data_processor()
    return processor.vectorize_operations(df, operations)
    
    
def parallel_apply(df: pd.DataFrame, func: Callable, 
                  column_groups: List[List[str]], 
                  n_workers: int = None) -> pd.DataFrame:
    """
    Apply function to groups of columns in parallel.
    
    Args:
        df: Input DataFrame
        func: Function to apply to each group
        column_groups: List of column groups to process
        n_workers: Number of worker processes (defaults to CPU count)
        
    Returns:
        DataFrame with applied functions
    """
    processor = get_data_processor()
    return processor.parallel_apply(df, func, column_groups, n_workers)
    
    
def batch_process(items: List[Any], process_func: Callable, 
                 batch_size: int = 100, n_workers: int = None) -> List[Any]:
    """
    Process items in batches using thread pool.
    
    Args:
        items: List of items to process
        process_func: Function to process each item
        batch_size: Size of each batch
        n_workers: Number of worker threads
        
    Returns:
        List of processed items
    """
    processor = get_data_processor()
    return processor.batch_process(items, process_func, batch_size, n_workers)
    
    
def lazy_load_dataframe(path: Path, columns: List[str] = None, 
                       chunksize: int = None) -> Union[pd.DataFrame, pd.io.parsers.TextFileReader]:
    """
    Lazily load a DataFrame with optional column selection and chunking.
    
    Args:
        path: Path to the data file
        columns: Optional list of columns to load
        chunksize: Optional chunk size for iterative loading
        
    Returns:
        Loaded DataFrame or TextFileReader for chunked reading
    """
    processor = get_data_processor()
    return processor.lazy_load_dataframe(path, columns, chunksize)