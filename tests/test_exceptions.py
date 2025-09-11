"""
Test suite for the framework's exception handling mechanisms.
"""

import pytest
from datetime import datetime
from nexus.core.exceptions import (
    BaseFrameworkException,
    ConfigurationException,
    DataException,
    PluginException,
    ValidationException,
    FrameworkException
)
from nexus.core.exception_handler import GlobalExceptionHandler


class TestBaseFrameworkException:
    """Test cases for the BaseFrameworkException class."""
    
    def test_base_exception_creation(self):
        """Test creating a basic framework exception."""
        exc = BaseFrameworkException("Test message")
        assert str(exc) == "Test message"
        assert exc.message == "Test message"
        assert isinstance(exc.timestamp, datetime)
        assert exc.context == {}
        assert exc.cause is None
        
    def test_base_exception_with_context(self):
        """Test creating a framework exception with context."""
        context = {"key": "value", "number": 42}
        exc = BaseFrameworkException("Test message", context=context)
        assert exc.context == context
        assert "key=value" in str(exc)
        assert "number=42" in str(exc)
        
    def test_base_exception_with_cause(self):
        """Test creating a framework exception with a cause."""
        cause = ValueError("Original error")
        exc = BaseFrameworkException("Test message", cause=cause)
        assert exc.cause == cause


class TestSpecificExceptions:
    """Test cases for specific exception types."""
    
    def test_configuration_exception(self):
        """Test ConfigurationException."""
        exc = ConfigurationException("Config error")
        assert isinstance(exc, BaseFrameworkException)
        
    def test_data_exception(self):
        """Test DataException."""
        exc = DataException("Data error")
        assert isinstance(exc, BaseFrameworkException)
        
    def test_plugin_exception(self):
        """Test PluginException."""
        exc = PluginException("Plugin error")
        assert isinstance(exc, BaseFrameworkException)
        
    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException("Validation error")
        assert isinstance(exc, BaseFrameworkException)
        
    def test_framework_exception(self):
        """Test FrameworkException."""
        exc = FrameworkException("Framework error")
        assert isinstance(exc, BaseFrameworkException)


class TestGlobalExceptionHandler:
    """Test cases for the GlobalExceptionHandler."""
    
    def test_handler_creation(self):
        """Test creating a global exception handler."""
        handler = GlobalExceptionHandler()
        assert handler.logger is not None
        
    def test_handle_base_exception(self, caplog):
        """Test handling a base framework exception."""
        handler = GlobalExceptionHandler()
        exc = BaseFrameworkException("Test error")
        
        with caplog.at_level("ERROR"):
            handler.handle_exception(exc)
            
        assert "Test error" in caplog.text
        
    def test_handle_configuration_exception(self, caplog):
        """Test handling a configuration exception."""
        handler = GlobalExceptionHandler()
        exc = ConfigurationException("Config error")
        
        with caplog.at_level("ERROR"):
            handler.handle_exception(exc)
            
        assert "Config error" in caplog.text
        assert "Configuration error" in caplog.text
        
    def test_format_exception_details(self):
        """Test formatting exception details."""
        handler = GlobalExceptionHandler()
        exc = BaseFrameworkException("Test error", context={"test": "value"})
        details = handler.format_exception_details(exc)
        
        assert details["exception_type"] == "BaseFrameworkException"
        assert "Test error" in details["exception_message"]
        assert details["timestamp"] is not None
        

if __name__ == "__main__":
    pytest.main([__file__])