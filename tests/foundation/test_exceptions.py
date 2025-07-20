"""Unit tests for the exception hierarchy in the Phoenix Real Estate Data Collection System.

This module tests all custom exceptions from src/phoenix_real_estate/foundation/utils/exceptions.py,
including exception hierarchy behavior, context preservation, exception chaining, and string
representations.
"""

import pytest

from phoenix_real_estate.foundation.utils.exceptions import (
    PhoenixREError,
    ConfigurationError,
    DatabaseError,
)


class TestPhoenixREError:
    """Test cases for the base PhoenixREError exception."""
    
    @pytest.mark.unit
    def test_basic_initialization(self):
        """Test basic exception initialization with message only."""
        error = PhoenixREError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.context == {}
        assert error.original_error is None
    
    @pytest.mark.unit
    def test_initialization_with_context(self):
        """Test exception initialization with context information."""
        context = {"operation": "test", "user_id": 123}
        error = PhoenixREError("Test error", context=context)
        assert error.message == "Test error"
        assert error.context == context
        assert str(error) == "Test error (context: operation=test, user_id=123)"
    
    @pytest.mark.unit
    def test_initialization_with_original_error(self):
        """Test exception initialization with original error."""
        original = ValueError("Original error")
        error = PhoenixREError("Wrapped error", original_error=original)
        assert error.message == "Wrapped error"
        assert error.original_error is original
    
    @pytest.mark.unit
    def test_string_representation_without_context(self):
        """Test string representation when no context is provided."""
        error = PhoenixREError("Simple error")
        assert str(error) == "Simple error"
    
    @pytest.mark.unit
    def test_string_representation_with_context(self):
        """Test string representation with context information."""
        context = {"file": "test.py", "line": 42}
        error = PhoenixREError("File error", context=context)
        assert str(error) == "File error (context: file=test.py, line=42)"
    
    @pytest.mark.unit
    def test_context_order_in_string_representation(self):
        """Test that context items maintain consistent order in string representation."""
        # Python 3.7+ guarantees dict order preservation
        context = {"a": 1, "b": 2, "c": 3}
        error = PhoenixREError("Test", context=context)
        assert str(error) == "Test (context: a=1, b=2, c=3)"
    
    @pytest.mark.unit
    def test_exception_chaining(self):
        """Test proper exception chaining with 'from' clause."""
        try:
            try:
                int("not a number")
            except ValueError as e:
                raise PhoenixREError("Conversion failed", original_error=e) from e
        except PhoenixREError as pe:
            assert pe.__cause__ is not None
            assert isinstance(pe.__cause__, ValueError)
            assert pe.original_error is pe.__cause__


class TestConfigurationError:
    """Test cases for ConfigurationError exception."""
    
    @pytest.mark.unit
    def test_inheritance(self):
        """Test that ConfigurationError inherits from PhoenixREError."""
        error = ConfigurationError("Config error")
        assert isinstance(error, PhoenixREError)
        assert isinstance(error, ConfigurationError)
    
    @pytest.mark.unit
    def test_typical_usage(self):
        """Test typical usage patterns for configuration errors."""
        error = ConfigurationError(
            "Missing API key",
            context={"key": "PHOENIX_API_KEY", "source": "environment"}
        )
        assert error.message == "Missing API key"
        assert error.context["key"] == "PHOENIX_API_KEY"
        assert str(error) == "Missing API key (context: key=PHOENIX_API_KEY, source=environment)"
    
    @pytest.mark.unit
    def test_config_file_error(self):
        """Test configuration file error scenario."""
        error = ConfigurationError(
            "Invalid configuration file",
            context={"file": "config.yaml", "error": "YAML syntax error", "line": 15}
        )
        expected = "Invalid configuration file (context: file=config.yaml, error=YAML syntax error, line=15)"
        assert str(error) == expected


class TestDatabaseError:
    """Test cases for DatabaseError exception."""
    
    @pytest.mark.unit
    def test_inheritance(self):
        """Test that DatabaseError inherits from PhoenixREError."""
        error = DatabaseError("DB error")
        assert isinstance(error, PhoenixREError)
        assert isinstance(error, DatabaseError)
    
    @pytest.mark.unit
    def test_connection_error(self):
        """Test database connection error scenario."""
        error = DatabaseError(
            "Failed to connect to MongoDB",
            context={"host": "localhost", "port": 27017, "timeout": 30}
        )
        assert error.context["host"] == "localhost"
        assert error.context["port"] == 27017
    
    @pytest.mark.unit
    def test_query_error_with_details(self):
        """Test database query error with detailed context."""
        error = DatabaseError(
            "Query execution failed",
            context={
                "collection": "properties",
                "operation": "find",
                "filter": {"city": "Phoenix"},
                "error_code": 11000
            }
        )
        assert error.context["collection"] == "properties"
        assert error.context["error_code"] == 11000

