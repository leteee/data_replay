"""
Unit tests for the IO discovery service.
"""

import tempfile
import yaml
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Annotated, Optional

from nexus.core.services.io_discovery import IODiscoveryService
from nexus.core.plugin.typing import DataSource, DataSink
from nexus.core.plugin.spec import PluginSpec


def test_io_discovery_service_initialization():
    """Test IODiscoveryService initialization."""
    # Test with default logger
    service = IODiscoveryService()
    assert service.logger is not None
    
    # Test with custom logger
    import logging
    custom_logger = logging.getLogger("test")
    service_with_logger = IODiscoveryService(logger=custom_logger)
    assert service_with_logger.logger == custom_logger


def test_discover_io_declarations_empty_pipeline():
    """Test discovering IO declarations with empty pipeline."""
    service = IODiscoveryService()
    
    case_config = {"io_mapping": {}}
    pipeline_steps = []
    
    base_sources, plugin_sources, plugin_sinks = service.discover_io_declarations(
        pipeline_steps, case_config
    )
    
    # Should return empty dictionaries
    assert base_sources == {}
    assert plugin_sources == {}
    assert plugin_sinks == {}


def test_discover_io_declarations_with_data_source():
    """Test discovering IO declarations with DataSource."""
    # Create a mock plugin spec with DataSource
    class TestPluginConfig:
        # Mock Pydantic model with DataSource annotation
        measurements: Annotated[pd.DataFrame, DataSource(name="test_measurements")]
    
    # Mock plugin spec
    plugin_spec = MagicMock()
    plugin_spec.config_model = TestPluginConfig
    
    # Mock PLUGIN_REGISTRY
    with patch('nexus.core.services.io_discovery.PLUGIN_REGISTRY', {"Test Plugin": plugin_spec}):
        service = IODiscoveryService()
        
        case_config = {
            "io_mapping": {
                "test_measurements": {
                    "path": "data/measurements.csv",
                    "handler": "csv"
                }
            }
        }
        
        pipeline_steps = [
            {"plugin": "Test Plugin", "enable": True}
        ]
        
        base_sources, plugin_sources, plugin_sinks = service.discover_io_declarations(
            pipeline_steps, case_config
        )
        
        # Should find the data source
        assert "test_measurements" in base_sources
        assert base_sources["test_measurements"]["path"] == "data/measurements.csv"
        assert base_sources["test_measurements"]["handler_args"]["name"] == "csv"
        
        # Should map plugin to source
        assert "Test Plugin" in plugin_sources
        assert "measurements" in plugin_sources["Test Plugin"]


def test_discover_io_declarations_with_data_sink():
    """Test discovering IO declarations with DataSink."""
    # Create a mock plugin spec with DataSink
    class TestPluginConfig:
        # Mock Pydantic model with DataSink annotation
        predicted_states: Optional[Annotated[pd.DataFrame, DataSink(name="test_predictions")]]
    
    # Mock plugin spec
    plugin_spec = MagicMock()
    plugin_spec.config_model = TestPluginConfig
    
    # Mock PLUGIN_REGISTRY
    with patch('nexus.core.services.io_discovery.PLUGIN_REGISTRY', {"Test Plugin": plugin_spec}):
        service = IODiscoveryService()
        
        case_config = {
            "io_mapping": {
                "test_predictions": {
                    "path": "output/predictions.parquet",
                    "handler": "parquet"
                }
            }
        }
        
        pipeline_steps = [
            {"plugin": "Test Plugin", "enable": True}
        ]
        
        base_sources, plugin_sources, plugin_sinks = service.discover_io_declarations(
            pipeline_steps, case_config
        )
        
        # Should find the data sink
        assert "Test Plugin" in plugin_sinks
        assert "predicted_states" in plugin_sinks["Test Plugin"]


def test_discover_io_declarations_disabled_plugin():
    """Test that disabled plugins are not processed."""
    # Create a mock plugin spec
    class TestPluginConfig:
        measurements: Annotated[pd.DataFrame, DataSource(name="test_measurements")]
    
    # Mock plugin spec
    plugin_spec = MagicMock()
    plugin_spec.config_model = TestPluginConfig
    
    # Mock PLUGIN_REGISTRY
    with patch('nexus.core.services.io_discovery.PLUGIN_REGISTRY', {"Test Plugin": plugin_spec}):
        service = IODiscoveryService()
        
        case_config = {
            "io_mapping": {
                "test_measurements": {
                    "path": "data/measurements.csv",
                    "handler": "csv"
                }
            }
        }
        
        # Pipeline step is disabled
        pipeline_steps = [
            {"plugin": "Test Plugin", "enable": False}
        ]
        
        base_sources, plugin_sources, plugin_sinks = service.discover_io_declarations(
            pipeline_steps, case_config
        )
        
        # Should not find any sources since plugin is disabled
        assert base_sources == {}
        assert plugin_sources == {}
        assert plugin_sinks == {}


def test_discover_io_declarations_multiple_plugins():
    """Test discovering IO declarations with multiple plugins."""
    # Create mock plugin specs
    class PluginAConfig:
        input_data: Annotated[pd.DataFrame, DataSource(name="shared_input")]
        output_data: Optional[Annotated[pd.DataFrame, DataSink(name="plugin_a_output")]]
    
    class PluginBConfig:
        input_data: Annotated[pd.DataFrame, DataSource(name="shared_input")]
        output_data: Optional[Annotated[pd.DataFrame, DataSink(name="plugin_b_output")]]
    
    # Mock plugin specs
    plugin_a_spec = MagicMock()
    plugin_a_spec.config_model = PluginAConfig
    
    plugin_b_spec = MagicMock()
    plugin_b_spec.config_model = PluginBConfig
    
    # Mock PLUGIN_REGISTRY
    with patch('nexus.core.services.io_discovery.PLUGIN_REGISTRY', {
        "Plugin A": plugin_a_spec,
        "Plugin B": plugin_b_spec
    }):
        service = IODiscoveryService()
        
        case_config = {
            "io_mapping": {
                "shared_input": {
                    "path": "data/input.csv",
                    "handler": "csv"
                },
                "plugin_a_output": {
                    "path": "output/a.parquet",
                    "handler": "parquet"
                },
                "plugin_b_output": {
                    "path": "output/b.parquet",
                    "handler": "parquet"
                }
            }
        }
        
        pipeline_steps = [
            {"plugin": "Plugin A", "enable": True},
            {"plugin": "Plugin B", "enable": True}
        ]
        
        base_sources, plugin_sources, plugin_sinks = service.discover_io_declarations(
            pipeline_steps, case_config
        )
        
        # Should find shared input source
        assert "shared_input" in base_sources
        assert base_sources["shared_input"]["path"] == "data/input.csv"
        
        # Should map both plugins to the same source
        assert "Plugin A" in plugin_sources
        assert "Plugin B" in plugin_sources
        assert "input_data" in plugin_sources["Plugin A"]
        assert "input_data" in plugin_sources["Plugin B"]
        
        # Should find output sinks for both plugins
        assert "Plugin A" in plugin_sinks
        assert "Plugin B" in plugin_sinks
        assert "output_data" in plugin_sinks["Plugin A"]
        assert "output_data" in plugin_sinks["Plugin B"]