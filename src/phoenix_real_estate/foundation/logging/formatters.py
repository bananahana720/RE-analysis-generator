"""Logging formatters for Phoenix Real Estate system.

This module provides JSON and text formatters for structured logging with
support for correlation IDs and environment-specific formatting.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class BaseFormatter(logging.Formatter):
    """Base formatter with common functionality for all formatters.

    Provides correlation ID support and sensitive data filtering.
    """

    # Fields that should never be logged
    SENSITIVE_FIELDS = {
        "password",
        "secret",
        "api_key",
        "token",
        "auth",
        "credential",
        "private_key",
        "mongodb_uri",
        "database_uri",
    }

    def __init__(
        self,
        correlation_id_field: str = "correlation_id",
        include_timestamp: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize base formatter.

        Args:
            correlation_id_field: Field name for correlation IDs
            include_timestamp: Whether to include timestamps
            **kwargs: Additional arguments for parent class
        """
        super().__init__(**kwargs)
        self.correlation_id_field = correlation_id_field
        self.include_timestamp = include_timestamp

    def filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out sensitive information from log data.

        Args:
            data: Dictionary of log data

        Returns:
            Filtered dictionary with sensitive data redacted
        """
        filtered = {}

        for key, value in data.items():
            # Check if key contains sensitive field names
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                # Recursively filter nested dictionaries
                filtered[key] = self.filter_sensitive_data(value)
            elif isinstance(value, list):
                # Filter lists (but don't recurse into list items for performance)
                filtered[key] = value
            else:
                filtered[key] = value

        return filtered

    def get_correlation_id(self, record: logging.LogRecord) -> Optional[str]:
        """Extract correlation ID from log record.

        Args:
            record: Log record to extract from

        Returns:
            Correlation ID or None if not present
        """
        # Check for correlation ID in extra fields
        if hasattr(record, self.correlation_id_field):
            return str(getattr(record, self.correlation_id_field))

        # Check in record's __dict__ directly
        if self.correlation_id_field in record.__dict__:
            return str(record.__dict__[self.correlation_id_field])

        return None


class JSONFormatter(BaseFormatter):
    """JSON formatter for structured logging in production.

    Outputs logs as JSON objects with all relevant metadata including:
    - Timestamp in ISO format
    - Log level
    - Logger name
    - Message
    - Correlation ID (if present)
    - Extra fields
    - Exception information (if present)

    Example output:
        {
            "timestamp": "2025-01-20T10:30:45.123Z",
            "level": "INFO",
            "logger": "phoenix_real_estate.collectors",
            "message": "Starting property collection",
            "correlation_id": "abc123",
            "extra": {"zip_code": "85031", "source": "maricopa"},
            "exception": null
        }
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add timestamp if requested
        if self.include_timestamp:
            # Use UTC timestamp in ISO format
            dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
            log_entry["timestamp"] = dt.isoformat()

        # Add correlation ID if present
        correlation_id = self.get_correlation_id(record)
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add location information
        log_entry["location"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add thread/process information
        log_entry["context"] = {
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
            "process_name": record.processName,
        }

        # Extract extra fields
        extra_fields = {}

        # Standard fields to exclude from extra
        standard_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "getMessage",
            "exc_info",
            "exc_text",
            "stack_info",
            "taskName",
        }

        # Collect extra fields
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith("_"):
                extra_fields[key] = value

        # Filter and add extra fields
        if extra_fields:
            log_entry["extra"] = self.filter_sensitive_data(extra_fields)

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Convert to JSON
        try:
            return json.dumps(log_entry, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # Fallback if JSON serialization fails
            fallback_entry = {
                "level": "ERROR",
                "logger": "phoenix_real_estate.logging",
                "message": f"Failed to serialize log entry: {e}",
                "original_message": str(record.getMessage()),
            }
            return json.dumps(fallback_entry, default=str)


class TextFormatter(BaseFormatter):
    """Human-readable text formatter for development environments.

    Provides colored output (when supported) with clear formatting for
    easy reading during development and debugging.

    Format: [timestamp] [LEVEL] [logger] [correlation_id?] message [extra?]

    Example output:
        2025-01-20 10:30:45.123 [INFO] [phoenix_real_estate.collectors] [abc123] Starting property collection {zip_code: 85031, source: maricopa}
    """

    # Color codes for different log levels (ANSI escape codes)
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(
        self, use_colors: bool = True, include_location: bool = False, **kwargs: Any
    ) -> None:
        """Initialize text formatter.

        Args:
            use_colors: Whether to use ANSI color codes
            include_location: Whether to include file/line information
            **kwargs: Additional arguments for parent class
        """
        # Set default format if not provided
        if "fmt" not in kwargs:
            kwargs["fmt"] = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"

        super().__init__(**kwargs)
        self.use_colors = use_colors
        self.include_location = include_location

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable text.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Get base formatted message
        formatted = super().format(record)

        # Build components list
        components = []

        # Add timestamp if not already in format
        if self.include_timestamp and "%(asctime)" not in (self._fmt or ""):
            dt = datetime.fromtimestamp(record.created)
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Milliseconds only
            components.append(timestamp)

        # Add colored level if using colors
        if self.use_colors and record.levelname in self.COLORS:
            level = f"{self.COLORS[record.levelname]}[{record.levelname}]{self.RESET}"
        else:
            level = f"[{record.levelname}]"

        # Extract main components from formatted string
        if "%(asctime)" in (self._fmt or ""):
            # Format includes timestamp, parse it out
            parts = formatted.split(" [", 1)
            if len(parts) == 2:
                components.append(parts[0])  # Timestamp
                remaining = "[" + parts[1]

                # Extract level and logger
                if "] [" in remaining:
                    level_part, rest = remaining.split("] [", 1)
                    components.append(level)  # Use colored level

                    if "] " in rest:
                        logger_part, message = rest.split("] ", 1)
                        components.append(f"[{logger_part}]")
                    else:
                        message = rest
                else:
                    message = remaining
            else:
                message = formatted
        else:
            components.append(level)
            components.append(f"[{record.name}]")
            message = record.getMessage()

        # Add correlation ID if present
        correlation_id = self.get_correlation_id(record)
        if correlation_id:
            components.append(f"[{correlation_id}]")

        # Add location if requested
        if self.include_location:
            location = f"({record.filename}:{record.lineno})"
            components.append(location)

        # Add message
        components.append(message)

        # Add extra fields
        extra_fields = {}
        standard_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "getMessage",
            "exc_info",
            "exc_text",
            "stack_info",
            "taskName",
            self.correlation_id_field,
        }

        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith("_"):
                extra_fields[key] = value

        if extra_fields:
            filtered_extra = self.filter_sensitive_data(extra_fields)
            extra_str = ", ".join(f"{k}: {v}" for k, v in filtered_extra.items())
            components.append(f"{{{extra_str}}}")

        # Join all components
        result = " ".join(components)

        # Add exception information if present
        if record.exc_info:
            if self.use_colors:
                exc_text = (
                    f"\n{self.COLORS['ERROR']}{self.formatException(record.exc_info)}{self.RESET}"
                )
            else:
                exc_text = f"\n{self.formatException(record.exc_info)}"
            result += exc_text

        return result


def get_formatter(
    format_type: str = "json",
    use_colors: Optional[bool] = None,
    include_location: bool = False,
    correlation_id_field: str = "correlation_id",
) -> logging.Formatter:
    """Get a configured formatter instance.

    Args:
        format_type: Type of formatter ("json" or "text")
        use_colors: Whether to use colors in text formatter (auto-detected if None)
        include_location: Whether to include file/line information
        correlation_id_field: Field name for correlation IDs

    Returns:
        Configured formatter instance

    Raises:
        ValueError: If format_type is not recognized

    Example:
        >>> # Get JSON formatter for production
        >>> formatter = get_formatter("json")

        >>> # Get colored text formatter for development
        >>> formatter = get_formatter("text", use_colors=True)
    """
    if format_type.lower() == "json":
        return JSONFormatter(correlation_id_field=correlation_id_field)
    elif format_type.lower() == "text":
        # Auto-detect color support if not specified
        if use_colors is None:
            try:
                import sys
                import os

                # Check if stdout is a TTY and supports colors
                use_colors = (
                    hasattr(sys.stdout, "isatty")
                    and sys.stdout.isatty()
                    and os.environ.get("TERM") != "dumb"
                )
            except Exception:
                use_colors = False

        return TextFormatter(
            use_colors=use_colors,
            include_location=include_location,
            correlation_id_field=correlation_id_field,
        )
    else:
        raise ValueError(f"Unknown format type: {format_type}. Supported types: 'json', 'text'")
