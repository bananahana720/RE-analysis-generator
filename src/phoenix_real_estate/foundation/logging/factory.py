"""Logging factory implementation.

This module provides the get_logger function that returns logger instances
conforming to the Logger protocol. For now, it returns standard Python loggers.
"""

import logging
from typing import Optional
from phoenix_real_estate.foundation.interfaces import Logger


def get_logger(name: Optional[str] = None) -> Logger:
    """Get a logger instance for the given name.
    
    This is a placeholder implementation that returns a standard Python logger.
    The full implementation will include:
    - Custom formatting for Phoenix Real Estate system
    - Log rotation and archival
    - Integration with monitoring systems
    - Structured logging support
    
    Args:
        name: Logger name, typically __name__ of the calling module.
             If None, returns the root logger.
    
    Returns:
        A logger instance conforming to the Logger protocol
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting property data collection")
    """
    # For now, return a standard Python logger with basic configuration
    logger = logging.getLogger(name)
    
    # Only configure if no handlers exist (avoid duplicate handlers)
    if not logger.handlers:
        # Create console handler with a simple format
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Set default level to INFO
        logger.setLevel(logging.INFO)
    
    return logger


# Factory function to create configured logger instances
def create_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> Logger:
    """Create a logger with custom configuration.
    
    This is a more advanced factory function for creating loggers
    with specific configurations. Currently a placeholder for future
    implementation.
    
    Args:
        name: Logger name
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
        log_file: Optional file path for file-based logging
        format_string: Optional custom format string
    
    Returns:
        A configured logger instance
        
    Raises:
        NotImplementedError: This is a placeholder for future implementation
    """
    # TODO: Implement custom logger creation with file handlers,
    # rotation, and custom formatting
    raise NotImplementedError("Custom logger creation not yet implemented")


# Module-level logger for this module
_module_logger = get_logger(__name__)


if __name__ == "__main__":
    # Test the get_logger function
    logger = get_logger("test.logger")
    logger.info("Testing logger factory")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Verify it conforms to the Logger protocol
    from phoenix_real_estate.foundation.interfaces import Logger as LoggerProtocol
    test_logger: LoggerProtocol = get_logger("protocol.test")
    print("get_logger returns Logger protocol compliant instances")
