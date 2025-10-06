"""Unit tests for core exceptions."""

import pytest

from core.exceptions import PluginConnectionError, PluginError, PluginValidationError


class TestPluginExceptions:
    """Test cases for plugin exception hierarchy."""

    def test_plugin_error_base(self):
        """Test base PluginError exception."""
        error = PluginError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_plugin_validation_error(self):
        """Test PluginValidationError inherits from PluginError."""
        error = PluginValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, PluginError)
        assert isinstance(error, Exception)

    def test_plugin_connection_error(self):
        """Test PluginConnectionError inherits from PluginError."""
        error = PluginConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, PluginError)
        assert isinstance(error, Exception)

    def test_exception_hierarchy(self):
        """Test exception hierarchy is correct."""
        # Test that we can catch specific exceptions
        with pytest.raises(PluginValidationError):
            raise PluginValidationError("Validation error")

        with pytest.raises(PluginConnectionError):
            raise PluginConnectionError("Connection error")

        # Test that we can catch base exception
        with pytest.raises(PluginError):
            raise PluginValidationError("Validation error")

        with pytest.raises(PluginError):
            raise PluginConnectionError("Connection error")
