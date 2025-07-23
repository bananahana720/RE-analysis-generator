"""Enhanced logger implementation for Phoenix Real Estate system.

This module provides the main logger class with support for:
- Structured logging with correlation IDs
- Environment-specific configuration
- Multiple handlers (console, file)
- Context management for request tracing
- Integration with the configuration system
"""

import contextvars
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from phoenix_real_estate.foundation.logging.handlers import (
    create_console_handler,
    create_file_handler,
    create_handler_from_config,
)
from phoenix_real_estate.foundation.interfaces import Logger as LoggerProtocol


# Context variable for correlation ID tracking across async calls
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


class PhoenixLogger(logging.Logger, LoggerProtocol):
    """Enhanced logger with correlation ID support and structured logging.

    This logger extends the standard Python logger with:
    - Automatic correlation ID injection
    - Structured logging support
    - Environment-aware configuration
    - Sensitive data filtering (handled by formatters)

    Attributes:
        correlation_id_field: Field name for correlation IDs in log records
        include_correlation_id: Whether to automatically include correlation IDs
    """

    def __init__(
        self,
        name: str,
        level: Union[int, str] = logging.NOTSET,
        correlation_id_field: str = "correlation_id",
        include_correlation_id: bool = True,
    ) -> None:
        """Initialize Phoenix logger.

        Args:
            name: Logger name
            level: Initial logging level
            correlation_id_field: Field name for correlation IDs
            include_correlation_id: Whether to auto-include correlation IDs
        """
        # Convert string level to int if needed
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.NOTSET)

        super().__init__(name, level)

        self.correlation_id_field = correlation_id_field
        self.include_correlation_id = include_correlation_id

    def _add_correlation_id(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Add correlation ID to extra fields if not present.

        Args:
            kwargs: Keyword arguments for logging call

        Returns:
            Updated kwargs with correlation ID in extra
        """
        if not self.include_correlation_id:
            return kwargs

        # Get or create extra dict
        extra = kwargs.get("extra", {})

        # Only add correlation ID if not already present
        if self.correlation_id_field not in extra:
            correlation_id = correlation_id_var.get()
            if correlation_id:
                extra[self.correlation_id_field] = correlation_id
                kwargs["extra"] = extra

        return kwargs

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message with correlation ID."""
        kwargs = self._add_correlation_id(kwargs)
        super().debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message with correlation ID."""
        kwargs = self._add_correlation_id(kwargs)
        super().info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message with correlation ID."""
        kwargs = self._add_correlation_id(kwargs)
        super().warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message with correlation ID."""
        kwargs = self._add_correlation_id(kwargs)
        super().error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message with correlation ID."""
        kwargs = self._add_correlation_id(kwargs)
        super().critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with traceback and correlation ID."""
        kwargs = self._add_correlation_id(kwargs)
        kwargs["exc_info"] = kwargs.get("exc_info", True)
        self.error(msg, *args, **kwargs)

    def log_with_context(
        self,
        level: Union[int, str],
        msg: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log a message with additional context.

        Args:
            level: Log level
            msg: Log message
            context: Additional context to include
            **kwargs: Additional logging arguments

        Example:
            >>> logger.log_with_context(
            ...     logging.INFO,
            ...     "Processing property",
            ...     context={"property_id": "123", "source": "maricopa"}
            ... )
        """
        # Convert string level to int if needed
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)

        # Merge context into extra
        if context:
            extra = kwargs.get("extra", {})
            extra.update(context)
            kwargs["extra"] = extra

        # Add correlation ID and log
        kwargs = self._add_correlation_id(kwargs)
        self.log(level, msg, **kwargs)


class LoggerManager:
    """Manager for creating and configuring loggers.

    Handles logger creation with consistent configuration based on
    the application's configuration system.

    Attributes:
        _loggers: Cache of created loggers
        _handlers: List of configured handlers
        _config: Logging configuration
    """

    def __init__(self) -> None:
        """Initialize logger manager."""
        self._loggers: Dict[str, PhoenixLogger] = {}
        self._handlers: List[logging.Handler] = []
        self._config: Dict[str, Any] = {}
        self._initialized = False

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure logging from configuration dictionary.

        Args:
            config: Logging configuration with the following structure:
                {
                    "level": "INFO",  # Default log level
                    "format": "json" or "text",  # Log format
                    "console": True,  # Enable console logging
                    "file_path": "/path/to/logs/app.log",  # File logging
                    "max_bytes": 10485760,  # 10MB
                    "backup_count": 5,
                    "handlers": {  # Additional handlers
                        "error_file": {
                            "type": "file",
                            "filename": "logs/errors.log",
                            "level": "ERROR"
                        }
                    }
                }
        """
        self._config = config

        # Set root logger level
        root_level = config.get("level", "INFO")
        if isinstance(root_level, str):
            root_level = getattr(logging, root_level.upper(), logging.INFO)
        logging.getLogger().setLevel(root_level)

        # Clear existing handlers from root logger to avoid duplicates
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            if handler in self._handlers:
                handler.close()

        # Clear our handler list
        self._handlers.clear()

        # Get environment from config or default
        environment = config.get("environment", "development")

        # Configure console handler if enabled
        if config.get("console", True):
            console_handler = create_console_handler(
                level=root_level, environment=environment, format_type=config.get("format")
            )
            self._handlers.append(console_handler)
            root_logger.addHandler(console_handler)

        # Configure file handler if path provided
        file_path = config.get("file_path")
        if file_path:
            file_handler = create_file_handler(
                filename=file_path,
                level=root_level,
                max_bytes=config.get("max_bytes", 10 * 1024 * 1024),
                backup_count=config.get("backup_count", 5),
                environment=environment,
                format_type=config.get("format"),
            )
            self._handlers.append(file_handler)
            root_logger.addHandler(file_handler)

        # Configure additional handlers
        handlers_config = config.get("handlers", {})
        for handler_name, handler_config in handlers_config.items():
            try:
                # Ensure environment is set
                if "environment" not in handler_config:
                    handler_config["environment"] = environment

                handler = create_handler_from_config(handler_config)
                self._handlers.append(handler)
                root_logger.addHandler(handler)
            except Exception as e:
                # Log configuration errors to stderr
                import sys

                print(f"Failed to configure handler '{handler_name}': {e}", file=sys.stderr)

        self._initialized = True

    def get_logger(self, name: Optional[str] = None) -> PhoenixLogger:
        """Get or create a logger instance.

        Args:
            name: Logger name (usually __name__)

        Returns:
            Configured logger instance
        """
        if name is None:
            name = "phoenix_real_estate"

        # Return cached logger if exists
        if name in self._loggers:
            return self._loggers[name]

        # Create new logger
        # Set the logger class temporarily
        old_class = logging.getLoggerClass()
        logging.setLoggerClass(PhoenixLogger)

        try:
            # Get logger instance (will be created as PhoenixLogger)
            logger = logging.getLogger(name)

            # Ensure it's our custom logger type
            if not isinstance(logger, PhoenixLogger):
                # This shouldn't happen, but just in case
                logger = PhoenixLogger(name)

            # Cache and return
            self._loggers[name] = logger  # type: ignore
            return logger  # type: ignore
        finally:
            # Restore original logger class
            logging.setLoggerClass(old_class)

    def set_correlation_id(self, correlation_id: Optional[str] = None) -> str:
        """Set correlation ID for current context.

        Args:
            correlation_id: Correlation ID to set (generates new one if None)

        Returns:
            The correlation ID that was set

        Example:
            >>> correlation_id = logger_manager.set_correlation_id()
            >>> # All subsequent logs in this context will include this ID
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        correlation_id_var.set(correlation_id)
        return correlation_id

    def clear_correlation_id(self) -> None:
        """Clear correlation ID from current context."""
        correlation_id_var.set(None)

    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID from context.

        Returns:
            Current correlation ID or None
        """
        return correlation_id_var.get()


# Global logger manager instance
_logger_manager = LoggerManager()


def configure_logging(config: Dict[str, Any]) -> None:
    """Configure global logging settings.

    Args:
        config: Logging configuration dictionary

    Example:
        >>> configure_logging({
        ...     "level": "INFO",
        ...     "format": "json",
        ...     "file_path": "logs/app.log"
        ... })
    """
    _logger_manager.configure(config)


def get_logger(name: Optional[str] = None) -> PhoenixLogger:
    """Get a logger instance.

    This is the main entry point for getting loggers in the application.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return _logger_manager.get_logger(name)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for current context.

    Args:
        correlation_id: Correlation ID to set (generates new one if None)

    Returns:
        The correlation ID that was set

    Example:
        >>> # In request handler
        >>> correlation_id = set_correlation_id()
        >>> logger.info("Handling request")  # Will include correlation ID
    """
    return _logger_manager.set_correlation_id(correlation_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    _logger_manager.clear_correlation_id()


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context.

    Returns:
        Current correlation ID or None
    """
    return _logger_manager.get_correlation_id()


# Context manager for correlation ID
class correlation_context:
    """Context manager for setting correlation ID.

    Example:
        >>> with correlation_context() as correlation_id:
        ...     logger.info("Processing started")
        ...     # All logs within this context will have the correlation ID
    """

    def __init__(self, correlation_id: Optional[str] = None) -> None:
        """Initialize context manager.

        Args:
            correlation_id: Correlation ID to use (generates new one if None)
        """
        self.correlation_id = correlation_id
        self.token: Optional[contextvars.Token[Optional[str]]] = None

    def __enter__(self) -> str:
        """Enter context and set correlation ID.

        Returns:
            The correlation ID that was set
        """
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())

        self.token = correlation_id_var.set(self.correlation_id)
        return self.correlation_id

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous correlation ID."""
        if self.token is not None:
            correlation_id_var.reset(self.token)
