"""
Unit tests for the data processing utilities module.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import pytest

from nexus.core.utils.data_processing import (
    DataProcessor,
    get_data_processor,
    optimize_dataframe_access,
    vectorize_operations,
    parallel_apply,
    batch_process,
    lazy_load_dataframe
)


def test_data_processor_initialization():
    """Test DataProcessor initialization."""
    # Test with default settings
    processor = DataProcessor()
    assert processor.cache_enabled is True
    # File cache is initialized lazily, so it might be None initially
    
    # Test with caching disabled
    processor_no_cache = DataProcessor(cache_enabled=False)
    assert processor_no_cache.cache_enabled is False
    assert processor_no_cache.file_cache is None


def test_get_data_processor_singleton():
    """Test that get_data_processor returns the same instance."""
    processor1 = get_data_processor()
    processor2 = get_data_processor()
    assert processor1 is processor2


def test_optimize_dataframe_access():
    """Test optimizing DataFrame column access."""
    # Create test DataFrame
    df = pd.DataFrame({
        'A': [1, 2, 3, 4, 5],
        'B': [10, 20, 30, 40, 50],
        'C': ['x', 'y', 'z', 'w', 'v']
    })
    
    # Test selecting specific columns
    result = optimize_dataframe_access(df, ['A', 'C'])
    assert list(result.columns) == ['A', 'C']
    assert len(result) == 5
    
    # Test selecting non-existent columns (should return all columns)
    result2 = optimize_dataframe_access(df, ['X', 'Y'])
    assert list(result2.columns) == ['A', 'B', 'C']  # Should return all original columns
    
    # Test selecting no columns (should return all columns)
    result3 = optimize_dataframe_access(df, [])
    assert list(result3.columns) == ['A', 'B', 'C']


def test_vectorize_operations():
    """Test applying vectorized operations to DataFrame columns."""
    # Create test DataFrame
    df = pd.DataFrame({
        'A': [1, 2, 3, 4, 5],
        'B': [10, 20, 30, 40, 50]
    })
    
    # Define operations
    operations = {
        'A': lambda x: x * 2,
        'B': lambda x: x + 5
    }
    
    # Apply operations
    result = vectorize_operations(df, operations)
    
    # Verify results
    assert list(result['A']) == [2, 4, 6, 8, 10]
    assert list(result['B']) == [15, 25, 35, 45, 55]


def test_parallel_apply():
    """Test applying function to groups of columns in parallel."""
    # Create test DataFrame
    df = pd.DataFrame({
        'A': [1, 2, 3, 4, 5],
        'B': [10, 20, 30, 40, 50],
        'C': [100, 200, 300, 400, 500],
        'D': [1000, 2000, 3000, 4000, 5000]
    })
    
    # Define a simple function to apply
    def double_columns(df_subset):
        return df_subset * 2
    
    # Define column groups
    column_groups = [['A', 'B'], ['C', 'D']]
    
    # Apply function in parallel
    result = parallel_apply(df, double_columns, column_groups, n_workers=1)  # Use 1 worker for deterministic testing
    
    # Verify results
    assert list(result['A']) == [2, 4, 6, 8, 10]
    assert list(result['B']) == [20, 40, 60, 80, 100]
    assert list(result['C']) == [200, 400, 600, 800, 1000]
    assert list(result['D']) == [2000, 4000, 6000, 8000, 10000]


def test_batch_process():
    """Test processing items in batches."""
    # Create test data
    items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # Define a simple processing function
    def square(x):
        return x ** 2
    
    # Process items in batches
    result = batch_process(items, square, batch_size=3, n_workers=2)
    
    # Verify results
    expected = [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
    assert result == expected


def test_lazy_load_dataframe_csv():
    """Test lazily loading a DataFrame from CSV."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test CSV file
        csv_path = Path(temp_dir) / "test.csv"
        test_data = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': [10, 20, 30, 40, 50],
            'C': ['x', 'y', 'z', 'w', 'v']
        })
        test_data.to_csv(csv_path, index=False)
        
        # Test loading specific columns
        result = lazy_load_dataframe(csv_path, columns=['A', 'C'])
        assert list(result.columns) == ['A', 'C']
        assert len(result) == 5


def test_lazy_load_dataframe_parquet():
    """Test lazily loading a DataFrame from Parquet."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test Parquet file
        parquet_path = Path(temp_dir) / "test.parquet"
        test_data = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': [10, 20, 30, 40, 50],
            'C': ['x', 'y', 'z', 'w', 'v']
        })
        test_data.to_parquet(parquet_path)
        
        # Test loading specific columns
        result = lazy_load_dataframe(parquet_path, columns=['A', 'B'])
        assert list(result.columns) == ['A', 'B']
        assert len(result) == 5