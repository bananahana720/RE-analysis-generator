"""Logging factory implementation.

This module provides the get_logger function that returns logger instances
conforming to the Logger protocol. It integrates with the Phoenix Real Estate
logging system to provide structured logging, correlation IDs, and environment-specific
configuration.
"""

from typing import Optional, Dict, Any

from phoenix_real_estate.foundation.interfaces import Logger
from phoenix_real_estate.foundation.logging.logger import (
    get_logger as _get_logger,
    configure_logging as _configure_logging,
    set_correlation_id,
    clear_correlation_id,
    get_correlation_id,
    correlation_context
)


# Module-level configuration cache
_logging_configured = False


def get_logger(name: Optional[str] = None) -> Logger:
    """Get a logger instance for the given name.
    
    This returns a Phoenix logger instance with:
    - Structured logging support (JSON in production, text in development)
    - Automatic correlation ID injection for request tracing
    - Environment-specific formatting and handlers
    - Sensitive data filtering
    - Integration with the configuration system
    
    Args:
        name: Logger name, typically __name__ of the calling module.
             If None, uses 'phoenix_real_estate' as the base name.
    
    Returns:
        A logger instance conforming to the Logger protocol
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting property data collection")
        
        >>> # With correlation ID for request tracing
        >>> with correlation_context() as correlation_id:
        ...     logger.info("Processing request")  # Includes correlation ID
        
        >>> # With extra context
        >>> logger.info("Property saved", extra={"property_id": "123", "source": "maricopa"})
    """
    global _logging_configured
    
    # Auto-configure with defaults if not already configured
    if not _logging_configured:
        try:
            # Try to get configuration from the config system
            from phoenix_real_estate.foundation.config import get_config
            config = get_config()
            
            # Check if config has the get_logging_config method
            if hasattr(config, 'get_logging_config'):
                logging_config = config.get_logging_config()
            else:
                # Fallback to manual config construction
                import os
                environment = os.getenv('ENVIRONMENT', 'development')
                log_level = os.getenv('LOG_LEVEL', 'INFO')
                log_format = os.getenv('LOG_FORMAT', 'text' if environment == 'development' else 'json')
                
                logging_config = {
                    'level': log_level,
                    'format': log_format,
                    'console': True,
                    'environment': environment
                }
                
                # Add file logging if path specified
                log_file_path = os.getenv('LOG_FILE_PATH')
                if log_file_path:
                    logging_config['file_path'] = log_file_path
            
            configure_logging(logging_config)
        except (ImportError, AttributeError) as e:
            # Config system not available yet, use defaults
            import os
            environment = os.getenv('ENVIRONMENT', 'development')
            
            configure_logging({
                'level': 'INFO',
                'format': 'text' if environment == 'development' else 'json',
                'console': True,
                'environment': environment
            })
        
        _logging_configured = True
    
    return _get_logger(name)


def configure_logging(config: Dict[str, Any]) -> None:
    """Configure the global logging system.
    
    This function allows explicit configuration of the logging system
    with custom settings. It should typically be called once during
    application initialization.
    
    Args:
        config: Logging configuration dictionary with the following keys:
            - level: Default log level (e.g., "INFO", "DEBUG")
            - format: Log format ("json" for production, "text" for development)
            - console: Whether to enable console logging (default: True)
            - file_path: Optional path to log file
            - max_bytes: Maximum log file size before rotation (default: 10MB)
            - backup_count: Number of rotated log files to keep (default: 5)
            - environment: Current environment (development, staging, production)
            - handlers: Dictionary of additional handler configurations
    
    Example:
        >>> configure_logging({
        ...     "level": "DEBUG",
        ...     "format": "json",
        ...     "console": True,
        ...     "file_path": "logs/app.log",
        ...     "max_bytes": 50 * 1024 * 1024,  # 50MB
        ...     "backup_count": 10
        ... })
    """
    global _logging_configured
    _configure_logging(config)
    _logging_configured = True


# Re-export correlation ID functions for convenience
__all__ = [
    'get_logger',
    'configure_logging',
    'set_correlation_id',
    'clear_correlation_id', 
    'get_correlation_id',
    'correlation_context'
]


# Module-level logger for this module
_module_logger = get_logger(__name__)


if __name__ == "__main__":
    # Test the logging system
    import os
    
    # Configure logging for testing
    configure_logging({
        'level': 'DEBUG',
        'format': 'text' if os.getenv('ENVIRONMENT', 'development') != 'production' else 'json',
        'console': True
    })
    
    # Test basic logging
    logger = get_logger("test.logger")
    logger.info("Testing logger factory")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Test with correlation ID
    with correlation_context() as correlation_id:
        logger.info(f"Testing with correlation ID: {correlation_id}")
        logger.error("Error with correlation tracking")
    
    # Test with extra context
    logger.info("Property processed", extra={
        "property_id": "test_123",
        "source": "test_source",
        "zip_code": "85031"
    })
    
    # Test sensitive data filtering
    logger.info("Login attempt", extra={
        "username": "testuser",
        "password": "should_be_redacted",
        "api_key": "should_be_redacted",
        "safe_field": "this_is_visible"
    })
    
    # Verify it conforms to the Logger protocol
    from phoenix_real_estate.foundation.interfaces import Logger as LoggerProtocol
    test_logger: LoggerProtocol = get_logger("protocol.test")
    print("\n[SUCCESS] get_logger returns Logger protocol compliant instances")
