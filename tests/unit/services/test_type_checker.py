"""
Unit tests for the type checker service.
"""

import pandas as pd
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from nexus.core.services.type_checker import TypeChecker
from nexus.handlers.base import DataHandler


def test_type_checker_initialization():
    """Test TypeChecker initialization."""
    # Test with default logger
    checker = TypeChecker()
    assert checker.logger is not None
    
    # Test with custom logger
    import logging
    custom_logger = logging.getLogger("test")
    checker_with_logger = TypeChecker(logger=custom_logger)
    assert checker_with_logger.logger == custom_logger


def test_preflight_type_check_success():
    """Test successful pre-flight type check."""
    checker = TypeChecker()
    
    # Create mock data source config with expected type
    source_config = {
        "expected_type": pd.DataFrame
    }
    
    # Create mock handler that produces DataFrame
    mock_handler = MagicMock(spec=DataHandler)
    mock_handler.produced_type = pd.DataFrame
    
    # Test type check
    result = checker.preflight_type_check(
        data_source_name="test_source",
        source_config=source_config,
        handler=mock_handler
    )
    
    # Should pass type check
    assert result is True


def test_preflight_type_check_no_expected_type():
    """Test pre-flight type check with no expected type."""
    checker = TypeChecker()
    
    # Create mock data source config with no expected type
    source_config = {}
    
    # Create mock handler
    mock_handler = MagicMock(spec=DataHandler)
    
    # Test type check
    result = checker.preflight_type_check(
        data_source_name="test_source",
        source_config=source_config,
        handler=mock_handler
    )
    
    # Should skip type check and return True
    assert result is True


def test_preflight_type_check_no_produced_type():
    """Test pre-flight type check with handler that has no produced type."""
    checker = TypeChecker()
    
    # Create mock data source config with expected type
    source_config = {
        "expected_type": pd.DataFrame
    }
    
    # Create mock handler with no produced type
    mock_handler = MagicMock(spec=DataHandler)
    del mock_handler.produced_type  # Remove produced_type attribute
    
    # Test type check
    result = checker.preflight_type_check(
        data_source_name="test_source",
        source_config=source_config,
        handler=mock_handler
    )
    
    # Should skip type check and return True
    assert result is True


def test_preflight_type_check_exact_match():
    """Test pre-flight type check with exact type match."""
    checker = TypeChecker()
    
    # Create mock data source config with expected type
    source_config = {
        "expected_type": pd.DataFrame
    }
    
    # Create mock handler that produces DataFrame
    mock_handler = MagicMock(spec=DataHandler)
    mock_handler.produced_type = pd.DataFrame
    
    # Test type check
    result = checker.preflight_type_check(
        data_source_name="test_source",
        source_config=source_config,
        handler=mock_handler
    )
    
    # Should pass type check
    assert result is True


def test_preflight_type_check_pandas_dataframe():
    """Test pre-flight type check with pandas DataFrame special case."""
    checker = TypeChecker()
    
    # Create mock data source config with expected type
    source_config = {
        "expected_type": pd.DataFrame
    }
    
    # Create mock handler that produces DataFrame
    mock_handler = MagicMock(spec=DataHandler)
    mock_handler.produced_type = pd.DataFrame
    
    # Test type check
    result = checker.preflight_type_check(
        data_source_name="test_source",
        source_config=source_config,
        handler=mock_handler
    )
    
    # Should pass type check
    assert result is True


def test_preflight_type_check_mismatch():
    """Test pre-flight type check with type mismatch."""
    checker = TypeChecker()
    
    # Create mock data source config with expected type
    source_config = {
        "expected_type": str  # Expecting string
    }
    
    # Create mock handler that produces DataFrame (different type)
    mock_handler = MagicMock(spec=DataHandler)
    mock_handler.produced_type = pd.DataFrame
    
    # Test type check - should fail but not raise exception
    result = checker.preflight_type_check(
        data_source_name="test_source",
        source_config=source_config,
        handler=mock_handler
    )
    
    # Should fail type check but return False (not raise exception)
    assert result is False


def test_preflight_type_check_handler_exception():
    """Test pre-flight type check when handler raises exception."""
    checker = TypeChecker()
    
    # Create mock data source config with expected type
    source_config = {
        "expected_type": pd.DataFrame
    }
    
    # Create mock handler without produced_type attribute
    mock_handler = MagicMock(spec=DataHandler)
    del mock_handler.produced_type  # Remove produced_type attribute
    
    # Test type check - should handle missing attribute gracefully
    result = checker.preflight_type_check(
        data_source_name="test_source",
        source_config=source_config,
        handler=mock_handler
    )
    
    # Should skip type check and return True
    assert result is True