"""Foundation layer for Phoenix Real Estate system.

This layer provides core infrastructure components including:
- Configuration management (ConfigProvider)
- Database operations (PropertyRepository)
- Logging utilities (get_logger)
"""

from phoenix_real_estate.foundation.interfaces import (
    ConfigProvider,
    PropertyRepository,
    Logger,
)
from phoenix_real_estate.foundation.config.provider import ConfigProviderImpl
from phoenix_real_estate.foundation.database.repositories import PropertyRepository as PropertyRepositoryImpl
from phoenix_real_estate.foundation.logging.factory import get_logger

__all__ = [
    # Protocols
    "ConfigProvider",
    "PropertyRepository", 
    "Logger",
    # Implementations
    "ConfigProviderImpl",
    "PropertyRepositoryImpl",
    "get_logger",
]
