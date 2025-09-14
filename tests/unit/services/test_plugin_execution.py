"""
Unit tests for the plugin execution service.
"""

import tempfile
import pandas as pd
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from nexus.core.services.plugin_execution import PluginExecutionService
from nexus.core.context import PluginContext
from nexus.core.plugin.spec import PluginSpec


def test_plugin_execution_service_initialization():
    """Test PluginExecutionService initialization."""
    # Test with default logger
    service = PluginExecutionService()
    assert service.logger is not None
    
    # Test with custom logger
    import logging
    custom_logger = logging.getLogger("test")
    service_with_logger = PluginExecutionService(logger=custom_logger)
    assert service_with_logger.logger == custom_logger


def test_execute_plugin():
    """Test executing a plugin."""
    # Create a mock plugin function
    def mock_plugin_function(context: PluginContext) -> pd.DataFrame:
        # Return a simple DataFrame
        return pd.DataFrame({"result": [1, 2, 3]})
    
    # Create mock plugin spec
    plugin_spec = MagicMock()
    plugin_spec.func = mock_plugin_function
    plugin_spec.name = "Mock Plugin"
    
    # Create mock context
    mock_context = MagicMock(spec=PluginContext)
    
    # Create mock data hub
    mock_data_hub = MagicMock()
    
    # Test plugin execution
    service = PluginExecutionService()
    result = service.execute_plugin(
        plugin_name="Mock Plugin",
        plugin_spec=plugin_spec,
        config_object=None,
        data_hub=mock_data_hub,
        case_path=Path("/test/case"),
        project_root=Path("/test"),
        resolved_output_path=None
    )
    
    # Verify result
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert list(result.columns) == ["result"]


def test_execute_plugin_with_exception():
    """Test executing a plugin that raises an exception."""
    # Create a mock plugin function that raises an exception
    def failing_plugin_function(context: PluginContext):
        raise RuntimeError("Plugin execution failed")
    
    # Create mock plugin spec
    plugin_spec = MagicMock()
    plugin_spec.func = failing_plugin_function
    plugin_spec.name = "Failing Plugin"
    
    # Create mock data hub
    mock_data_hub = MagicMock()
    
    # Test plugin execution with exception handling
    service = PluginExecutionService()
    
    # Expect the wrapped exception, not the original one
    with pytest.raises(RuntimeError, match="A critical error occurred in plugin 'Failing Plugin'"):
        service.execute_plugin(
            plugin_name="Failing Plugin",
            plugin_spec=plugin_spec,
            config_object=None,
            data_hub=mock_data_hub,
            case_path=Path("/test/case"),
            project_root=Path("/test"),
            resolved_output_path=None
        )


def test_handle_plugin_output_no_sinks():
    """Test handling plugin output with no sinks."""
    service = PluginExecutionService()
    
    # Test with no sinks
    service.handle_plugin_output(
        plugin_name="Test Plugin",
        return_value=pd.DataFrame({"test": [1, 2, 3]}),
        sinks_for_plugin={},
        raw_case_config={"io_mapping": {}},
        case_path=Path("/test/case"),
        data_hub=MagicMock()
    )
    
    # Should not raise any exceptions


def test_handle_plugin_output_with_sinks():
    """Test handling plugin output with sinks."""
    service = PluginExecutionService()
    
    # Create mock data hub
    mock_data_hub = MagicMock()
    
    # Test with sinks
    service.handle_plugin_output(
        plugin_name="Test Plugin",
        return_value=pd.DataFrame({"test": [1, 2, 3]}),
        sinks_for_plugin={
            "output_field": MagicMock(name="test_sink")
        },
        raw_case_config={
            "io_mapping": {
                "test_sink": {
                    "path": "output/result.parquet",
                    "handler_args": {"name": "parquet"}
                }
            }
        },
        case_path=Path("/test/case"),
        data_hub=mock_data_hub
    )
    
    # Should call data_hub.save
    mock_data_hub.save.assert_called_once()


def test_handle_plugin_output_save_exception():
    """Test handling plugin output when save raises an exception."""
    service = PluginExecutionService()
    
    # Create mock data hub that raises an exception
    mock_data_hub = MagicMock()
    mock_data_hub.save.side_effect = RuntimeError("Save failed")
    
    # Create mock sink
    mock_sink = MagicMock()
    mock_sink.name = "test_sink"
    mock_sink.handler_args = {"name": "parquet"}
    
    # Test with sinks - should raise NexusError wrapping the original exception
    with pytest.raises(Exception) as exc_info:
        service.handle_plugin_output(
            plugin_name="Test Plugin",
            return_value=pd.DataFrame({"test": [1, 2, 3]}),
            sinks_for_plugin={
                "output_field": mock_sink
            },
            raw_case_config={
                "io_mapping": {
                    "test_sink": {
                        "path": "output/result.parquet",
                        "handler_args": {"name": "parquet"}
                    }
                }
            },
            case_path=Path("/test/case"),
            data_hub=mock_data_hub
        )
    
    # Verify it's a NexusError wrapping the original exception
    assert "Save failed" in str(exc_info.value)


def test_handle_plugin_output_none_return_value():
    """Test handling plugin output with None return value."""
    service = PluginExecutionService()
    
    # Create mock data hub
    mock_data_hub = MagicMock()
    
    # Test with None return value
    service.handle_plugin_output(
        plugin_name="Test Plugin",
        return_value=None,
        sinks_for_plugin={
            "output_field": MagicMock(name="test_sink")
        },
        raw_case_config={
            "io_mapping": {
                "test_sink": {
                    "path": "output/result.parquet",
                    "handler_args": {"name": "parquet"}
                }
            }
        },
        case_path=Path("/test/case"),
        data_hub=mock_data_hub
    )
    
    # Should not call data_hub.save for None return value
    mock_data_hub.save.assert_not_called()