"""Logging handlers for Phoenix Real Estate system.

This module provides console and file handlers with support for log rotation,
environment-specific configuration, and proper resource management.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from phoenix_real_estate.foundation.logging.formatters import get_formatter


class ConsoleHandler(logging.StreamHandler):
    """Enhanced console handler with environment-aware formatting.
    
    Automatically selects appropriate formatter based on environment:
    - Development: Colored text formatter with readable output
    - Production: JSON formatter for structured logging
    
    Attributes:
        environment: Current environment (development, staging, production)
        use_colors: Whether to use ANSI colors in output
    """
    
    def __init__(
        self,
        stream: Optional[Any] = None,
        environment: str = "development",
        use_colors: Optional[bool] = None,
        format_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Initialize console handler.
        
        Args:
            stream: Output stream (defaults to sys.stdout)
            environment: Current environment name
            use_colors: Force color usage (auto-detected if None)
            format_type: Force formatter type (auto-selected if None)
            **kwargs: Additional arguments for parent class
        """
        # Use stdout by default for better compatibility
        if stream is None:
            stream = sys.stdout
            
        super().__init__(stream, **kwargs)
        
        self.environment = environment.lower()
        self.use_colors = use_colors
        
        # Auto-select formatter based on environment
        if format_type is None:
            if self.environment in ("production", "prod"):
                format_type = "json"
            else:
                format_type = "text"
        
        # Set appropriate formatter
        formatter = get_formatter(
            format_type=format_type,
            use_colors=use_colors,
            include_location=(self.environment in ("development", "dev", "local"))
        )
        self.setFormatter(formatter)


class FileHandler(RotatingFileHandler):
    """Enhanced file handler with automatic directory creation and rotation.
    
    Provides file-based logging with:
    - Automatic parent directory creation
    - Size-based rotation with configurable limits
    - Backup file management
    - Environment-specific formatting
    
    Attributes:
        log_dir: Directory containing log files
        environment: Current environment name
    """
    
    def __init__(
        self,
        filename: Union[str, Path],
        mode: str = 'a',
        maxBytes: int = 10 * 1024 * 1024,  # 10MB default
        backupCount: int = 5,
        encoding: Optional[str] = 'utf-8',
        delay: bool = True,
        environment: str = "development",
        format_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Initialize file handler with rotation.
        
        Args:
            filename: Path to log file
            mode: File open mode
            maxBytes: Maximum bytes before rotation (0 = no rotation)
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Delay file opening until first write
            environment: Current environment name
            format_type: Formatter type (auto-selected if None)
            **kwargs: Additional arguments for parent class
        """
        # Convert to Path and ensure parent directory exists
        log_path = Path(filename)
        self.log_dir = log_path.parent
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize parent with absolute path
        super().__init__(
            str(log_path.absolute()),
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            **kwargs
        )
        
        self.environment = environment.lower()
        
        # Auto-select formatter based on environment
        if format_type is None:
            # Use JSON for production, text for others
            format_type = "json" if self.environment in ("production", "prod") else "text"
        
        # Set formatter (no colors for file output)
        formatter = get_formatter(
            format_type=format_type,
            use_colors=False,  # Never use colors in files
            include_location=True  # Always include location in files
        )
        self.setFormatter(formatter)
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record with error handling.
        
        Args:
            record: Log record to emit
        """
        try:
            super().emit(record)
        except Exception as e:
            # If file logging fails, try to log to stderr
            try:
                fallback_handler = logging.StreamHandler(sys.stderr)
                fallback_handler.emit(record)
                # Also log the file handler error
                error_record = logging.LogRecord(
                    name="phoenix_real_estate.logging",
                    level=logging.ERROR,
                    pathname=__file__,
                    lineno=0,
                    msg=f"File handler failed: {e}",
                    args=(),
                    exc_info=None
                )
                fallback_handler.emit(error_record)
            except Exception:
                # If even stderr fails, silently continue
                pass


class TimedFileHandler(TimedRotatingFileHandler):
    """Time-based rotating file handler with automatic directory creation.
    
    Rotates log files based on time intervals:
    - 'midnight': Roll over at midnight
    - 'H': Hourly
    - 'D': Daily
    - 'W0'-'W6': Weekly (0=Monday, 6=Sunday)
    
    Attributes:
        log_dir: Directory containing log files
        environment: Current environment name
    """
    
    def __init__(
        self,
        filename: Union[str, Path],
        when: str = 'midnight',
        interval: int = 1,
        backupCount: int = 7,
        encoding: Optional[str] = 'utf-8',
        delay: bool = True,
        utc: bool = True,
        environment: str = "development",
        format_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Initialize time-based rotating file handler.
        
        Args:
            filename: Path to log file
            when: Type of time interval
            interval: Interval multiplier
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Delay file opening until first write
            utc: Use UTC time for rotation
            environment: Current environment name
            format_type: Formatter type (auto-selected if None)
            **kwargs: Additional arguments for parent class
        """
        # Convert to Path and ensure parent directory exists
        log_path = Path(filename)
        self.log_dir = log_path.parent
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize parent with absolute path
        super().__init__(
            str(log_path.absolute()),
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            **kwargs
        )
        
        self.environment = environment.lower()
        
        # Auto-select formatter
        if format_type is None:
            format_type = "json" if self.environment in ("production", "prod") else "text"
        
        # Set formatter
        formatter = get_formatter(
            format_type=format_type,
            use_colors=False,
            include_location=True
        )
        self.setFormatter(formatter)


def create_console_handler(
    level: Union[int, str] = logging.INFO,
    environment: str = "development",
    **kwargs: Any
) -> ConsoleHandler:
    """Create a configured console handler.
    
    Args:
        level: Logging level
        environment: Current environment
        **kwargs: Additional handler configuration
        
    Returns:
        Configured console handler
        
    Example:
        >>> handler = create_console_handler(level=logging.DEBUG)
        >>> logger.addHandler(handler)
    """
    handler = ConsoleHandler(environment=environment, **kwargs)
    
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    handler.setLevel(level)
    return handler


def create_file_handler(
    filename: Union[str, Path],
    level: Union[int, str] = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    environment: str = "development",
    rotation_type: str = "size",
    **kwargs: Any
) -> Union[FileHandler, TimedFileHandler]:
    """Create a configured file handler with rotation.
    
    Args:
        filename: Path to log file
        level: Logging level
        max_bytes: Max file size for size-based rotation
        backup_count: Number of backup files
        environment: Current environment
        rotation_type: Type of rotation ("size" or "time")
        **kwargs: Additional handler configuration
        
    Returns:
        Configured file handler
        
    Example:
        >>> # Size-based rotation
        >>> handler = create_file_handler(
        ...     "logs/app.log",
        ...     max_bytes=50*1024*1024,  # 50MB
        ...     backup_count=10
        ... )
        
        >>> # Time-based rotation
        >>> handler = create_file_handler(
        ...     "logs/app.log",
        ...     rotation_type="time",
        ...     when="midnight",
        ...     backup_count=30  # Keep 30 days
        ... )
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    if rotation_type == "time":
        # Extract time-specific kwargs
        when = kwargs.pop('when', 'midnight')
        interval = kwargs.pop('interval', 1)
        utc = kwargs.pop('utc', True)
        
        handler = TimedFileHandler(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backup_count,
            utc=utc,
            environment=environment,
            **kwargs
        )
    else:
        # Size-based rotation (default)
        handler = FileHandler(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            environment=environment,
            **kwargs
        )
    
    handler.setLevel(level)
    return handler


def create_handler_from_config(config: Dict[str, Any]) -> logging.Handler:
    """Create a handler from configuration dictionary.
    
    Args:
        config: Handler configuration with 'type' and handler-specific settings
        
    Returns:
        Configured handler instance
        
    Raises:
        ValueError: If handler type is not recognized
        
    Example:
        >>> config = {
        ...     "type": "console",
        ...     "level": "DEBUG",
        ...     "environment": "development"
        ... }
        >>> handler = create_handler_from_config(config)
    """
    handler_type = config.get('type', 'console').lower()
    
    # Remove type from config to pass remaining as kwargs
    handler_config = config.copy()
    handler_config.pop('type', None)
    
    if handler_type == 'console':
        return create_console_handler(**handler_config)
    elif handler_type in ('file', 'rotating_file', 'timed_file'):
        # Determine rotation type
        if handler_type == 'timed_file' or handler_config.get('when'):
            handler_config['rotation_type'] = 'time'
        else:
            handler_config['rotation_type'] = 'size'
        
        # Filename is required for file handlers
        filename = handler_config.pop('filename', None)
        if not filename:
            raise ValueError("File handlers require 'filename' configuration")
        
        return create_file_handler(filename, **handler_config)
    else:
        raise ValueError(
            f"Unknown handler type: {handler_type}. "
            f"Supported types: 'console', 'file', 'rotating_file', 'timed_file'"
        )