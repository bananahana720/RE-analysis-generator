"""Foundation layer for Phoenix Real Estate system.

This layer provides core infrastructure components including:
- Configuration management (ConfigProvider, Environment, Secrets)
- Database operations (PropertyRepository)
- Logging utilities (get_logger)
"""

from phoenix_real_estate.foundation.interfaces import (
    ConfigProvider,
    PropertyRepository,
    Logger,
)
from phoenix_real_estate.foundation.config.provider import ConfigProviderImpl
from phoenix_real_estate.foundation.config import (
    EnvironmentConfigProvider,
    Environment,
    EnvironmentFactory,
    get_config,
    reset_config_cache,
    SecretManager,
    get_secret,
    get_required_secret,
)
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
    # Enhanced Configuration
    "EnvironmentConfigProvider",
    "Environment",
    "EnvironmentFactory",
    "get_config",
    "reset_config_cache",
    # Secret Management
    "SecretManager",
    "get_secret",
    "get_required_secret",
]
