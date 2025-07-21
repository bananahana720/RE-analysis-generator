"""Logging configuration and utilities for Phoenix Real Estate system.

This package provides structured logging with:
- JSON format for production environments
- Human-readable format for development
- Correlation ID support for request tracing
- Environment-specific configuration
- Sensitive data filtering
- Log rotation and archival

Example:
    Basic usage:
    >>> from phoenix_real_estate.foundation.logging import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Application started")
    
    With correlation tracking:
    >>> from phoenix_real_estate.foundation.logging import correlation_context
    >>> with correlation_context() as correlation_id:
    ...     logger.info("Processing request")  # Automatically includes correlation ID
    
    With extra context:
    >>> logger.info("Property saved", extra={"property_id": "123", "source": "maricopa"})
"""

from phoenix_real_estate.foundation.logging.factory import (
    get_logger,
    configure_logging,
    set_correlation_id,
    clear_correlation_id,
    get_correlation_id,
    correlation_context
)

__all__ = [
    'get_logger',
    'configure_logging',
    'set_correlation_id',
    'clear_correlation_id',
    'get_correlation_id',
    'correlation_context'
]
