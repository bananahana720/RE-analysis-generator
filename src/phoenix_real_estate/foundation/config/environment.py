"""
Environment factory pattern for configuration management.

This module provides environment detection, configuration creation, and validation
for the Phoenix Real Estate Data Collector application.
"""

import os
import threading
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable
import logging

from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)


class InvalidEnvironmentError(Exception):
    """Raised when an invalid environment is specified."""

    pass


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""

    pass


class BaseConfig:
    """Base configuration class for environment-specific settings."""

    def __init__(self, environment: "Environment", debug: bool = False, testing: bool = False):
        """Initialize base configuration.

        Args:
            environment: The environment this configuration is for
            debug: Whether debug mode is enabled
            testing: Whether testing mode is enabled
        """
        self.environment = environment
        self.debug = debug
        self.testing = testing

        # Load configuration from environment variables
        self._load_from_environment()

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Core configuration
        self.mongodb_uri = os.getenv("MONGODB_URI", "")
        self.database_name = os.getenv("DATABASE_NAME", "")

        # API configuration
        self.api_key = os.getenv("API_KEY", "")

        # Port configuration
        port_str = os.getenv("PORT", "")
        if port_str and port_str.strip():
            self.port = port_str.strip()
        else:
            self.port = None

        # Dynamic attribute loading for environment-specific variables
        for key, value in os.environ.items():
            # Convert environment variable to attribute name
            attr_name = key.lower()

            # Skip if already set or not a valid attribute name
            if hasattr(self, attr_name) or not attr_name.replace("_", "").isalnum():
                continue

            # Set as attribute
            setattr(self, attr_name, value)

    def get_environment(self) -> str:
        """Get the current environment name.

        Returns:
            Environment name (e.g., "development", "testing", "production").
        """
        return self.environment.value

    def get(self, key: str, default=None):
        """Get a configuration value using dot notation.

        Args:
            key: Configuration key using dot notation.
            default: Default value if key is not found.

        Returns:
            Configuration value or default if not found.
        """
        # Handle direct attributes first
        if hasattr(self, key):
            return getattr(self, key)

        # Handle dot notation for nested access
        parts = key.split(".")
        obj = self

        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return default

        return obj

    def get_required(self, key: str):
        """Get a required configuration value.

        Args:
            key: Configuration key using dot notation.

        Returns:
            Configuration value.

        Raises:
            ConfigurationError: If the key is not found.
        """
        value = self.get(key)
        if value is None:
            raise ConfigurationError(f"Required configuration key not found: {key}")
        return value

    def get_typed(self, key: str, expected_type: type, default=None):
        """Get a typed configuration value.

        Args:
            key: Configuration key using dot notation.
            expected_type: Expected type for the value.
            default: Default value if key is not found.

        Returns:
            Typed configuration value or default.

        Raises:
            ConfigurationError: If value cannot be converted to expected type.
        """
        value = self.get(key, default)

        if value is None:
            return default

        # Already the correct type
        if isinstance(value, expected_type):
            return value

        # Convert string to bool
        if expected_type is bool and isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ("true", "yes", "y", "1", "on", "enabled", "enable", "active"):
                return True
            elif value_lower in (
                "false",
                "no",
                "n",
                "0",
                "off",
                "disabled",
                "disable",
                "inactive",
                "",
            ):
                return False
            else:
                raise ConfigurationError(f"Cannot convert '{value}' to boolean for key '{key}'")

        # Convert string to int
        if expected_type is int and isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                raise ConfigurationError(f"Cannot convert '{value}' to int for key '{key}'")

        # Convert string to float
        if expected_type is float and isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise ConfigurationError(f"Cannot convert '{value}' to float for key '{key}'")

        # Try direct conversion
        try:
            return expected_type(value)
        except (ValueError, TypeError) as e:
            raise ConfigurationError(
                f"Cannot convert '{value}' to {expected_type.__name__} for key '{key}'"
            ) from e


class Environment(Enum):
    """Enumeration of supported environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, value: str) -> "Environment":
        """Create Environment from string value.

        Args:
            value: String representation of environment

        Returns:
            Environment enum value

        Raises:
            InvalidEnvironmentError: If value doesn't match any environment
        """
        value_lower = value.lower()
        for env in cls:
            if env.value == value_lower:
                return env
        raise InvalidEnvironmentError(f"Invalid environment: {value}")

    @classmethod
    def all(cls) -> List["Environment"]:
        """Get all environment values.

        Returns:
            List of all Environment enum values
        """
        return list(cls)


class EnvironmentFactory:
    """Factory for creating environment-specific configurations."""

    def __init__(self, root_dir: Optional[Path] = None):
        """Initialize the factory.

        Args:
            root_dir: Root directory for finding environment files.
                     Defaults to current working directory.
        """
        self.root_dir = root_dir or Path.cwd()

    @classmethod
    def create_config(
        cls, environment: Optional[Environment] = None, config_dir: Optional[Path] = None
    ):
        """Create configuration for specified or auto-detected environment.

        Args:
            environment: Specific environment to use, or None to auto-detect
            config_dir: Directory containing configuration files (for backward compatibility)

        Returns:
            Configured EnvironmentConfigProvider instance with proper interface

        Raises:
            InvalidEnvironmentError: If environment is invalid
            ConfigurationError: If configuration validation fails
        """
        # Import EnvironmentConfigProvider locally to avoid circular imports
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        if environment is None:
            # Auto-detect from ENVIRONMENT variable
            env_str = os.environ.get("ENVIRONMENT", "development")
            environment = Environment.from_string(env_str)
        elif isinstance(environment, str):
            environment = Environment.from_string(environment)

        logger.info(f"Creating configuration for environment: {environment.value}")

        # Create EnvironmentConfigProvider with the specified config directory and environment
        return EnvironmentConfigProvider(config_dir=config_dir, environment=environment.value)

    def create_development_config(self) -> BaseConfig:
        """Create development configuration.

        Returns:
            Configured BaseConfig instance for development

        Raises:
            ConfigurationError: If configuration validation fails
        """
        self._load_environment_files(Environment.DEVELOPMENT)

        config = BaseConfig(environment=Environment.DEVELOPMENT, debug=True, testing=False)

        self._validate_config(config)
        return config

    def create_testing_config(self) -> BaseConfig:
        """Create testing configuration.

        Returns:
            Configured BaseConfig instance for testing

        Raises:
            ConfigurationError: If configuration validation fails
        """
        self._load_environment_files(Environment.TESTING)

        config = BaseConfig(environment=Environment.TESTING, debug=True, testing=True)

        self._validate_config(config)
        return config

    def create_production_config(self) -> BaseConfig:
        """Create production configuration.

        Returns:
            Configured BaseConfig instance for production

        Raises:
            ConfigurationError: If configuration validation fails
        """
        self._load_environment_files(Environment.PRODUCTION)

        config = BaseConfig(environment=Environment.PRODUCTION, debug=False, testing=False)

        self._validate_config(config)
        return config

    def _load_environment_files(self, environment: Environment) -> None:
        """Load environment files in correct order.

        Args:
            environment: Environment to load files for
        """
        # Load base .env file first
        base_env = self.root_dir / ".env"
        if base_env.exists():
            logger.debug(f"Loading base environment file: {base_env}")
            load_dotenv(base_env, override=True)

        # Load .env.local for development only
        if environment == Environment.DEVELOPMENT:
            local_env = self.root_dir / ".env.local"
            if local_env.exists():
                logger.debug(f"Loading local environment file: {local_env}")
                load_dotenv(local_env, override=True)

        # Load environment-specific file
        env_file = self.root_dir / f".env.{environment.value}"
        if env_file.exists():
            logger.debug(f"Loading environment-specific file: {env_file}")
            load_dotenv(env_file, override=True)

    def _validate_config(self, config: BaseConfig) -> None:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If validation fails
        """
        errors = []

        # Only validate required fields if they were explicitly set (not just empty)
        # This allows for missing env files while still catching empty values when provided
        if "MONGODB_URI" in os.environ and not config.mongodb_uri:
            errors.append("MONGODB_URI cannot be empty")

        if "DATABASE_NAME" in os.environ and not config.database_name:
            errors.append("DATABASE_NAME cannot be empty")

        # Check API key if present
        if hasattr(config, "api_key") and config.api_key:
            if len(config.api_key) < 6:
                errors.append("API_KEY must be at least 6 characters long")

        # Check port if present
        if hasattr(config, "port") and config.port is not None:
            try:
                # Port might be a string, so we need to check if it can be converted
                port_val = int(config.port) if isinstance(config.port, str) else config.port
                if not (1 <= port_val <= 65535):
                    errors.append("PORT must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.append("PORT must be a valid integer")

        if errors:
            raise ConfigurationError("\n".join(errors))


# Global configuration management
_config_lock = threading.Lock()
_config_instances: Dict[Environment, BaseConfig] = {}
_current_environment: Optional[Environment] = None


def get_config(environment: Optional[Environment] = None) -> BaseConfig:
    """Get or create singleton configuration instance.

    Args:
        environment: Specific environment to use, or None to auto-detect

    Returns:
        Singleton BaseConfig instance
    """
    global _current_environment

    with _config_lock:
        # If no explicit environment given and we have a current environment, use it
        # This ensures that once an environment is set, it stays until reset
        if environment is None and _current_environment is not None:
            environment = _current_environment

        # Otherwise determine environment from env var or default
        if environment is None:
            env_str = os.environ.get("ENVIRONMENT", "development")
            environment = Environment.from_string(env_str)
            _current_environment = environment

        # Check if we already have this environment cached
        if environment in _config_instances:
            return _config_instances[environment]

        # Create new config
        factory = EnvironmentFactory()
        config = factory.create_config(environment)

        # Cache it - but limit cache size to prevent memory leaks
        if len(_config_instances) >= 3:  # Keep at most 3 environments cached
            # Remove oldest entry
            oldest_env = next(iter(_config_instances))
            del _config_instances[oldest_env]

        _config_instances[environment] = config
        _current_environment = environment

        return config


def reset_config_cache() -> None:
    """Reset the configuration cache.

    This clears all cached configuration instances, forcing new instances
    to be created on next get_config() call.
    """
    global _current_environment

    with _config_lock:
        _config_instances.clear()
        _current_environment = None


class ConfigurationValidator:
    """Validator for environment configurations."""

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        custom_validators: Optional[List[Callable[[BaseConfig], None]]] = None,
    ):
        """Initialize the validator.

        Args:
            root_dir: Root directory for finding environment files
            custom_validators: List of custom validation functions
        """
        self.root_dir = root_dir or Path.cwd()
        self.custom_validators = custom_validators or []

    def validate_all_environments(self) -> None:
        """Validate configurations for all environments.

        Raises:
            ConfigurationError: If any environment has validation errors
        """
        errors = {}

        for env in Environment.all():
            try:
                self.validate_environment(env)
            except ConfigurationError as e:
                errors[env.value] = str(e)

        if errors:
            error_msg = "Configuration errors found:\n"
            for env, error in errors.items():
                error_msg += f"\n{env}:\n{error}\n"
            raise ConfigurationError(error_msg)

    def validate_environment(self, environment: Environment) -> None:
        """Validate configuration for a specific environment.

        Args:
            environment: Environment to validate

        Raises:
            ConfigurationError: If validation fails
        """
        # Check if environment file exists
        env_file = self.root_dir / f".env.{environment.value}"
        if not env_file.exists() and environment != Environment.DEVELOPMENT:
            # Development can work without explicit .env.development
            base_env = self.root_dir / ".env"
            if not base_env.exists():
                raise ConfigurationError(f"Configuration file not found for {environment.value}")

        # Try to create configuration without validation first
        factory = EnvironmentFactory(root_dir=self.root_dir)

        # Load environment files but skip built-in validation
        factory._load_environment_files(environment)
        config = BaseConfig(
            environment=environment,
            debug=environment == Environment.DEVELOPMENT,
            testing=environment == Environment.TESTING,
        )

        # Run built-in validation
        try:
            factory._validate_config(config)
        except ConfigurationError:
            # Re-raise as is
            raise
        except Exception as e:
            raise ConfigurationError(f"Failed to create config: {str(e)}")

        # Run custom validators
        for validator in self.custom_validators:
            try:
                validator(config)
            except ConfigurationError:
                # Re-raise as is
                raise
            except Exception as e:
                raise ConfigurationError(f"Custom validation failed: {str(e)}")
