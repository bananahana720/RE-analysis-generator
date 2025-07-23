"""Tests for the logging framework."""

import json
import logging
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from phoenix_real_estate.foundation.logging import (
    get_logger,
    configure_logging,
    set_correlation_id,
    clear_correlation_id,
    get_correlation_id,
    correlation_context,
)
from phoenix_real_estate.foundation.logging.formatters import (
    JSONFormatter,
    TextFormatter,
    get_formatter,
)
from phoenix_real_estate.foundation.logging.handlers import (
    ConsoleHandler,
    FileHandler,
    TimedFileHandler,
    create_console_handler,
    create_file_handler,
    create_handler_from_config,
)
from phoenix_real_estate.foundation.logging.logger import PhoenixLogger, LoggerManager


class TestFormatters:
    """Test logging formatters."""

    def test_json_formatter_basic(self):
        """Test JSON formatter basic functionality."""
        formatter = JSONFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format the record
        output = formatter.format(record)

        # Parse JSON output
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert "location" in data
        assert data["location"]["file"] == "test.py"
        assert data["location"]["line"] == 10

    def test_json_formatter_with_correlation_id(self):
        """Test JSON formatter with correlation ID."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add correlation ID to record
        record.correlation_id = "test-correlation-123"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["correlation_id"] == "test-correlation-123"

    def test_json_formatter_with_extra_fields(self):
        """Test JSON formatter with extra fields."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields
        record.property_id = "prop_123"
        record.source = "maricopa"
        record.zip_code = "85031"

        output = formatter.format(record)
        data = json.loads(output)

        assert "extra" in data
        assert data["extra"]["property_id"] == "prop_123"
        assert data["extra"]["source"] == "maricopa"
        assert data["extra"]["zip_code"] == "85031"

    def test_json_formatter_sensitive_data_filtering(self):
        """Test that sensitive data is filtered out."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add sensitive fields
        record.password = "secret123"
        record.api_key = "key123"
        record.mongodb_uri = "mongodb://user:pass@host"
        record.safe_field = "visible_data"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["extra"]["password"] == "[REDACTED]"
        assert data["extra"]["api_key"] == "[REDACTED]"
        assert data["extra"]["mongodb_uri"] == "[REDACTED]"
        assert data["extra"]["safe_field"] == "visible_data"

    def test_json_formatter_with_exception(self):
        """Test JSON formatter with exception information."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test error"
        assert isinstance(data["exception"]["traceback"], list)

    def test_text_formatter_basic(self):
        """Test text formatter basic functionality."""
        formatter = TextFormatter(use_colors=False)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "[INFO]" in output
        assert "[test.logger]" in output
        assert "Test message" in output

    def test_text_formatter_with_colors(self):
        """Test text formatter with ANSI colors."""
        formatter = TextFormatter(use_colors=True)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Check for ANSI color codes
        assert "\033[31m" in output  # Red color for ERROR
        assert "\033[0m" in output  # Reset code

    def test_text_formatter_with_location(self):
        """Test text formatter with file location."""
        formatter = TextFormatter(use_colors=False, include_location=True)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "(test.py:10)" in output

    def test_get_formatter_json(self):
        """Test get_formatter with JSON type."""
        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)

    def test_get_formatter_text(self):
        """Test get_formatter with text type."""
        formatter = get_formatter("text", use_colors=False)
        assert isinstance(formatter, TextFormatter)

    def test_get_formatter_invalid_type(self):
        """Test get_formatter with invalid type."""
        with pytest.raises(ValueError, match="Unknown format type"):
            get_formatter("invalid")


class TestHandlers:
    """Test logging handlers."""

    def test_console_handler_development(self):
        """Test console handler in development environment."""
        handler = ConsoleHandler(environment="development")

        assert isinstance(handler.formatter, TextFormatter)
        assert handler.environment == "development"

    def test_console_handler_production(self):
        """Test console handler in production environment."""
        handler = ConsoleHandler(environment="production")

        assert isinstance(handler.formatter, JSONFormatter)
        assert handler.environment == "production"

    def test_console_handler_custom_format(self):
        """Test console handler with custom format type."""
        handler = ConsoleHandler(environment="development", format_type="json")

        assert isinstance(handler.formatter, JSONFormatter)

    def test_file_handler_creation(self):
        """Test file handler creation with directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "logs" / "app.log"

            handler = FileHandler(
                filename=log_path, maxBytes=1024, backupCount=3, environment="development"
            )

            # Check that directory was created
            assert log_path.parent.exists()

            # Check handler properties
            assert handler.maxBytes == 1024
            assert handler.backupCount == 3
            assert isinstance(handler.formatter, TextFormatter)

    def test_file_handler_rotation(self):
        """Test file handler rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "test.log"

            # Create handler with small max size
            handler = FileHandler(
                filename=log_path,
                maxBytes=100,  # Very small for testing
                backupCount=2,
                delay=False,  # Open file immediately
            )

            # Write enough data to trigger rotation
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="X" * 50,  # Long message
                args=(),
                exc_info=None,
            )

            # Emit multiple records to trigger rotation
            for _ in range(5):
                handler.emit(record)

            handler.close()

            # Check that rotation occurred
            assert log_path.exists()
            assert (Path(temp_dir) / "test.log.1").exists()

    def test_timed_file_handler(self):
        """Test time-based rotating file handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "timed.log"

            handler = TimedFileHandler(
                filename=log_path,
                when="S",  # Rotate every second (for testing)
                interval=1,
                backupCount=2,
                environment="production",
            )

            # Check configuration
            assert handler.when == "S"
            assert handler.interval == 1
            assert isinstance(handler.formatter, JSONFormatter)

            handler.close()

    def test_create_console_handler(self):
        """Test create_console_handler factory function."""
        handler = create_console_handler(level=logging.DEBUG, environment="staging")

        assert handler.level == logging.DEBUG
        assert handler.environment == "staging"

    def test_create_file_handler_size_based(self):
        """Test create_file_handler with size-based rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "app.log"

            handler = create_file_handler(
                filename=log_path,
                level="WARNING",
                max_bytes=5 * 1024 * 1024,
                backup_count=10,
                rotation_type="size",
            )

            assert handler.level == logging.WARNING
            assert handler.maxBytes == 5 * 1024 * 1024
            assert handler.backupCount == 10

            handler.close()

    def test_create_file_handler_time_based(self):
        """Test create_file_handler with time-based rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "app.log"

            handler = create_file_handler(
                filename=log_path,
                level=logging.INFO,
                rotation_type="time",
                when="midnight",
                backup_count=30,
            )

            assert isinstance(handler, TimedFileHandler)
            assert handler.when == "midnight"
            assert handler.backupCount == 30

            handler.close()

    def test_create_handler_from_config_console(self):
        """Test create_handler_from_config with console type."""
        config = {"type": "console", "level": "DEBUG", "environment": "development"}

        handler = create_handler_from_config(config)

        assert isinstance(handler, ConsoleHandler)
        assert handler.level == logging.DEBUG

    def test_create_handler_from_config_file(self):
        """Test create_handler_from_config with file type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "type": "file",
                "filename": str(Path(temp_dir) / "test.log"),
                "level": "INFO",
                "max_bytes": 1024 * 1024,
            }

            handler = create_handler_from_config(config)

            assert isinstance(handler, FileHandler)
            assert handler.level == logging.INFO

            handler.close()

    def test_create_handler_from_config_invalid(self):
        """Test create_handler_from_config with invalid type."""
        config = {"type": "invalid"}

        with pytest.raises(ValueError, match="Unknown handler type"):
            create_handler_from_config(config)


class TestPhoenixLogger:
    """Test Phoenix logger implementation."""

    def test_phoenix_logger_basic(self):
        """Test basic Phoenix logger functionality."""
        logger = PhoenixLogger("test.logger", level=logging.DEBUG)

        assert logger.name == "test.logger"
        assert logger.level == logging.DEBUG
        assert logger.include_correlation_id is True

    def test_phoenix_logger_with_correlation_id(self):
        """Test Phoenix logger with correlation ID."""
        logger = PhoenixLogger("test.logger")

        # Set correlation ID in context
        set_correlation_id("test-123")

        # Create a handler to capture output
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Mock the handler's emit to capture the record
        records = []
        original_emit = handler.emit

        def capture_emit(record):
            records.append(record)
            original_emit(record)

        handler.emit = capture_emit

        # Log a message
        logger.info("Test message")

        # Check that correlation ID was added
        assert len(records) == 1
        assert hasattr(records[0], "correlation_id")
        assert records[0].correlation_id == "test-123"

        # Clean up
        clear_correlation_id()
        logger.removeHandler(handler)

    def test_phoenix_logger_log_with_context(self):
        """Test Phoenix logger log_with_context method."""
        logger = PhoenixLogger("test.logger")

        # Create handler to capture output
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Mock to capture records
        records = []
        original_emit = handler.emit
        handler.emit = lambda r: records.append(r) or original_emit(r)

        # Log with context
        logger.log_with_context(
            "INFO", "Processing property", context={"property_id": "123", "source": "maricopa"}
        )

        # Check record
        assert len(records) == 1
        assert records[0].property_id == "123"
        assert records[0].source == "maricopa"

        logger.removeHandler(handler)

    def test_phoenix_logger_without_correlation_id(self):
        """Test Phoenix logger with correlation ID disabled."""
        logger = PhoenixLogger("test.logger", include_correlation_id=False)

        # Set correlation ID
        set_correlation_id("test-456")

        # Create handler to capture
        handler = logging.StreamHandler()
        logger.addHandler(handler)

        records = []
        handler.emit = lambda r: records.append(r)

        # Log message
        logger.info("Test without correlation")

        # Check that correlation ID was NOT added
        assert len(records) == 1
        assert not hasattr(records[0], "correlation_id")

        # Clean up
        clear_correlation_id()
        logger.removeHandler(handler)


class TestLoggerManager:
    """Test logger manager functionality."""

    def test_logger_manager_configure(self):
        """Test logger manager configuration."""
        manager = LoggerManager()

        config = {"level": "DEBUG", "format": "json", "console": True}

        manager.configure(config)

        assert manager._initialized is True
        assert len(manager._handlers) > 0

    def test_logger_manager_get_logger(self):
        """Test logger manager get_logger."""
        manager = LoggerManager()

        logger1 = manager.get_logger("test.logger1")
        logger2 = manager.get_logger("test.logger1")
        logger3 = manager.get_logger("test.logger2")

        # Should return same instance for same name
        assert logger1 is logger2
        # Different instance for different name
        assert logger1 is not logger3

        # Should be Phoenix logger instances
        assert isinstance(logger1, PhoenixLogger)
        assert isinstance(logger3, PhoenixLogger)

    def test_logger_manager_correlation_id(self):
        """Test logger manager correlation ID management."""
        manager = LoggerManager()

        # Initially no correlation ID
        assert manager.get_correlation_id() is None

        # Set correlation ID
        correlation_id = manager.set_correlation_id()
        assert correlation_id is not None
        assert manager.get_correlation_id() == correlation_id

        # Set specific correlation ID
        specific_id = "custom-123"
        manager.set_correlation_id(specific_id)
        assert manager.get_correlation_id() == specific_id

        # Clear correlation ID
        manager.clear_correlation_id()
        assert manager.get_correlation_id() is None


class TestCorrelationContext:
    """Test correlation context manager."""

    def test_correlation_context_basic(self):
        """Test basic correlation context usage."""
        # Initially no correlation ID
        assert get_correlation_id() is None

        # Use context manager
        with correlation_context() as correlation_id:
            assert correlation_id is not None
            assert get_correlation_id() == correlation_id

        # After context, correlation ID is cleared
        assert get_correlation_id() is None

    def test_correlation_context_with_custom_id(self):
        """Test correlation context with custom ID."""
        custom_id = "custom-context-123"

        with correlation_context(custom_id) as correlation_id:
            assert correlation_id == custom_id
            assert get_correlation_id() == custom_id

        assert get_correlation_id() is None

    def test_correlation_context_nested(self):
        """Test nested correlation contexts."""
        with correlation_context() as outer_id:
            assert get_correlation_id() == outer_id

            with correlation_context() as inner_id:
                assert get_correlation_id() == inner_id
                assert inner_id != outer_id

            # Back to outer context
            assert get_correlation_id() == outer_id

        assert get_correlation_id() is None


class TestIntegration:
    """Integration tests for the logging system."""

    def test_full_logging_flow(self):
        """Test complete logging flow with configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            # Configure logging
            configure_logging(
                {
                    "level": "DEBUG",
                    "format": "json",
                    "console": False,  # Disable console for cleaner test
                    "file_path": str(log_file),
                    "environment": "production",
                }
            )

            # Get logger
            logger = get_logger("test.integration")

            # Log with correlation ID
            with correlation_context() as correlation_id:
                logger.info("Start processing", extra={"step": 1})
                logger.debug("Debug info", extra={"data": "test"})
                logger.warning("Warning message")
                logger.error("Error occurred", extra={"code": "ERR001"})

            # Read log file
            with open(log_file, "r") as f:
                lines = f.readlines()

            # Verify all messages were logged
            assert len(lines) == 4

            # Parse and verify JSON structure
            for line in lines:
                data = json.loads(line)
                assert "timestamp" in data
                assert "level" in data
                assert "message" in data
                assert "correlation_id" in data
                assert data["correlation_id"] == correlation_id

    def test_sensitive_data_filtering_integration(self):
        """Test that sensitive data is filtered in real logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "sensitive.log"

            configure_logging(
                {"level": "INFO", "format": "json", "console": False, "file_path": str(log_file)}
            )

            logger = get_logger("test.sensitive")

            # Log sensitive data
            logger.info(
                "User login",
                extra={
                    "username": "testuser",
                    "password": "secret123",
                    "api_key": "key-abc-123",
                    "session_id": "sess-456",  # Non-sensitive
                },
            )

            # Read and verify
            with open(log_file, "r") as f:
                data = json.loads(f.readline())

            assert data["extra"]["username"] == "testuser"  # Username is not sensitive
            assert data["extra"]["password"] == "[REDACTED]"
            assert data["extra"]["api_key"] == "[REDACTED]"
            assert data["extra"]["session_id"] == "sess-456"

    @patch("phoenix_real_estate.foundation.config.get_config")
    def test_auto_configuration_from_config_system(self, mock_get_config):
        """Test automatic configuration from config system."""
        # Mock config system
        mock_config = MagicMock()
        mock_config.get_logging_config.return_value = {
            "level": "WARNING",
            "format": "json",
            "console": True,
        }
        mock_get_config.return_value = mock_config

        # Reset module-level configuration flag
        import phoenix_real_estate.foundation.logging.factory as factory

        factory._logging_configured = False

        # Get logger (should trigger auto-configuration)
        logger = get_logger("test.auto.config")

        # Verify configuration was called
        mock_config.get_logging_config.assert_called_once()

        # Logger should work
        assert isinstance(logger, PhoenixLogger)


class TestErrorHandling:
    """Test error handling in logging system."""

    def test_json_formatter_serialization_error(self):
        """Test JSON formatter handles serialization errors."""
        formatter = JSONFormatter()

        # Create record with non-serializable object
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Add non-serializable object
        record.bad_field = object()  # Can't be JSON serialized

        # Should not raise, should handle gracefully
        output = formatter.format(record)
        data = json.loads(output)

        # Should have converted object to string
        assert "extra" in data
        assert "bad_field" in data["extra"]
        assert isinstance(data["extra"]["bad_field"], str)

    def test_file_handler_emit_error(self):
        """Test file handler handles emit errors gracefully."""
        # Create handler with invalid path
        handler = FileHandler(
            filename="/invalid/path/that/does/not/exist/test.log",
            delay=False,  # Try to open immediately
        )

        # Create a record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Should not raise exception
        handler.emit(record)  # Should fallback to stderr
