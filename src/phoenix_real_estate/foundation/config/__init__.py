"""Configuration management module."""

from phoenix_real_estate.foundation.config.base import (
    ConfigProvider,
    EnvironmentConfigProvider,
)
from phoenix_real_estate.foundation.config.environment import (
    Environment,
    BaseConfig,
    EnvironmentFactory,
    ConfigurationValidator,
    InvalidEnvironmentError,
    ConfigurationError,
    get_config,
    reset_config_cache,
)
from phoenix_real_estate.foundation.config.secrets import (
    SecretManager,
    SecretNotFoundError,
    SecretValidationError,
    get_secret_manager,
    get_secret,
    get_required_secret,
)

__all__ = [
    # Base configuration
    "ConfigProvider",
    "EnvironmentConfigProvider",
    # Environment management
    "Environment",
    "BaseConfig",
    "EnvironmentFactory",
    "ConfigurationValidator",
    "InvalidEnvironmentError",
    "ConfigurationError",
    "get_config",
    "reset_config_cache",
    # Secret management
    "SecretManager",
    "SecretNotFoundError",
    "SecretValidationError",
    "get_secret_manager",
    "get_secret",
    "get_required_secret",
]
