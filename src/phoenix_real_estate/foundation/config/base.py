"""Base configuration provider implementation.

This module provides the abstract base class for configuration providers and
the core EnvironmentConfigProvider that supports multiple configuration sources
with proper precedence: environment variables > env files > config files > defaults.
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Union, cast
import yaml

# Try to import python-dotenv with fallback
try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

    # Define a no-op function
    def load_dotenv(*args, **kwargs):
        pass


from phoenix_real_estate.foundation.utils.exceptions import ConfigurationError
from phoenix_real_estate.foundation.utils.helpers import is_valid_zipcode, safe_int, safe_float


T = TypeVar("T")
logger = logging.getLogger(__name__)


class ConfigProvider(ABC):
    """Abstract base class for configuration providers.

    This class defines the interface that all configuration providers must
    implement. It supports type-safe configuration access with validation
    and dot notation for nested keys.

    The configuration precedence order (highest to lowest):
    1. Environment variables
    2. Environment-specific configuration files
    3. Base configuration files
    4. Default values

    Examples:
        >>> config = EnvironmentConfigProvider()
        >>> api_key = config.get_required("api.key")
        >>> timeout = config.get_typed("api.timeout", int, default=30)
        >>> is_debug = config.get_typed("debug", bool, default=False)
    """

    @abstractmethod
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a configuration value.

        Args:
            key: Configuration key using dot notation (e.g., "database.host").
            default: Default value if key is not found.

        Returns:
            Configuration value or default if not found.

        Examples:
            >>> config.get("api.key")
            'abc123'
            >>> config.get("missing.key", "default")
            'default'
        """
        ...

    @abstractmethod
    def get_required(self, key: str) -> Any:
        """Retrieve a required configuration value.

        Args:
            key: Configuration key using dot notation.

        Returns:
            Configuration value.

        Raises:
            ConfigurationError: If the key is not found.

        Examples:
            >>> config.get_required("database.host")
            'localhost'
            >>> config.get_required("missing.key")
            ConfigurationError: Required configuration key not found: missing.key
        """
        ...

    @abstractmethod
    def get_typed(
        self, key: str, expected_type: type[T], default: Optional[T] = None
    ) -> Optional[T]:
        """Retrieve a typed configuration value.

        Args:
            key: Configuration key using dot notation.
            expected_type: Expected type for the value.
            default: Default value if key is not found.

        Returns:
            Typed configuration value or default.

        Raises:
            ConfigurationError: If value cannot be converted to expected type.

        Examples:
            >>> config.get_typed("port", int, 8080)
            8080
            >>> config.get_typed("debug", bool, False)
            True
        """
        ...

    @abstractmethod
    def get_environment(self) -> str:
        """Get the current environment name.

        Returns:
            Environment name (e.g., "development", "staging", "production").

        Examples:
            >>> config.get_environment()
            'development'
        """
        ...

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the configuration and return list of errors.

        Performs validation checks on the loaded configuration to ensure
        all required values are present and valid.

        Returns:
            List of validation error messages. Empty list if validation passes.
        """
        ...

    @abstractmethod
    def validate_and_raise(self) -> None:
        """Validate the configuration and raise on errors.

        Performs validation checks on the loaded configuration to ensure
        all required values are present and valid.

        Raises:
            ConfigurationError: If validation fails.
        """
        ...


class EnvironmentConfigProvider(ConfigProvider):
    """Configuration provider with environment-based loading.

    This provider loads configuration from multiple sources with proper
    precedence ordering. It supports YAML configuration files, environment
    variables, and .env files.

    Configuration sources (in precedence order):
    1. Environment variables
    2. .env file (if present)
    3. Environment-specific YAML file (e.g., development.yaml)
    4. Base YAML file (base.yaml)
    5. Default values

    The provider supports:
    - Dot notation for nested configuration access
    - Type conversion for common types (bool, int, float, list)
    - Configuration validation
    - Environment detection from ENVIRONMENT variable

    Attributes:
        config_dir: Directory containing configuration files.
        environment: Current environment name.
        config: Merged configuration dictionary.
        _cache: Cache for resolved configuration values.
    """

    def __init__(
        self,
        config_dir: Optional[Union[str, Path]] = None,
        environment: Optional[str] = None,
        load_dotenv: bool = True,
    ):
        """Initialize the configuration provider.

        Args:
            config_dir: Directory containing configuration files.
                       Defaults to "config" in project root.
            environment: Environment name. Defaults to ENVIRONMENT env var
                        or "development".
            load_dotenv: Whether to load .env file. Defaults to True.

        Raises:
            ConfigurationError: If configuration loading fails.
        """
        # Load .env file if requested
        if load_dotenv and HAS_DOTENV:
            dotenv_path = Path(".env")
            if dotenv_path.exists():
                # Import here to avoid shadowing the parameter name
                from dotenv import load_dotenv as dotenv_load

                dotenv_load(dotenv_path)
                logger.info(f"Loaded environment variables from {dotenv_path}")

        # Determine environment
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        logger.info(f"Using environment: {self.environment}")

        # Set config directory
        if config_dir is None:
            # Default to config directory in project root
            self.config_dir = Path(__file__).parent.parent.parent.parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)

        # Initialize configuration storage
        self.config: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}

        # Load configuration
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load configuration from all sources in precedence order."""
        try:
            # 1. Load base configuration
            base_config = self._load_yaml_file("base.yaml")
            if base_config:
                self.config = base_config
                logger.debug("Loaded base configuration")

            # 2. Load environment-specific configuration
            env_config = self._load_yaml_file(f"{self.environment}.yaml")
            if env_config:
                self._merge_config(self.config, env_config)
                logger.debug(f"Loaded {self.environment} configuration")

            # 3. Override with environment variables
            self._load_environment_variables()

        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration for environment '{self.environment}'",
                context={"config_dir": str(self.config_dir), "environment": self.environment},
                original_error=e,
            ) from e

    def _load_yaml_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load a YAML configuration file.

        Args:
            filename: Name of the YAML file to load.

        Returns:
            Parsed YAML content or None if file doesn't exist.

        Raises:
            ConfigurationError: If YAML parsing fails.
        """
        file_path = self.config_dir / filename
        if not file_path.exists():
            logger.debug(f"Configuration file not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content if isinstance(content, dict) else {}
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse YAML file: {filename}",
                context={"file_path": str(file_path), "error": str(e)},
                original_error=e,
            ) from e

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override configuration into base.

        Args:
            base: Base configuration dictionary (modified in place).
            override: Override configuration dictionary.
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables.

        Environment variables override configuration file values.
        Supports both PHOENIX_ prefixed and direct environment variables:
        - PHOENIX_DATABASE_HOST -> database.host (preferred)
        - MONGODB_URI -> database.uri
        - LOG_LEVEL -> logging.level
        """
        # Mapping of direct environment variables to config keys
        direct_mappings = {
            "MONGODB_URI": "database.uri",
            "MONGODB_DATABASE": "database.name",
            "MONGODB_MAX_POOL_SIZE": "database.max_pool_size",
            "LOG_LEVEL": "logging.level",
            "LOG_FORMAT": "logging.format",
            "MAX_REQUESTS_PER_HOUR": "collection.max_requests_per_hour",
            "MIN_REQUEST_DELAY": "collection.min_request_delay",
            "TARGET_ZIP_CODES": "collection.target_zip_codes",
            "WEBSHARE_USERNAME": "proxy.username",
            "WEBSHARE_PASSWORD": "proxy.password",
            "LLM_MODEL": "processing.llm_model",
            "LLM_TIMEOUT": "processing.llm_timeout",
            "SECRET_KEY": "security.secret_key",
            "CAPTCHA_API_KEY": "sources.phoenix_mls.captcha.api_key",
            "CAPTCHA_SERVICE": "sources.phoenix_mls.captcha.service",
        }

        # First, load direct environment variables
        for env_key, config_key in direct_mappings.items():
            if env_key in os.environ:
                env_value = os.environ[env_key]
                # Store in both the mapped location and the lowercase key
                self._set_nested_value(self.config, config_key, env_value)
                self._set_nested_value(self.config, env_key.lower(), env_value)
                logger.debug(f"Loaded {config_key} from direct environment variable {env_key}")

        # Also support direct environment variables as lowercase keys
        for env_key, env_value in os.environ.items():
            # Skip if already handled by direct mappings or is PHOENIX_ prefixed
            if env_key not in direct_mappings and not env_key.startswith("PHOENIX_"):
                # Store direct env vars as lowercase keys (e.g., API_KEY -> api_key)
                lowercase_key = env_key.lower()
                # Only store if it looks like a config key (has underscore)
                if "_" in lowercase_key or lowercase_key in ["debug", "environment"]:
                    self._set_nested_value(self.config, lowercase_key, env_value)
                    logger.debug(f"Loaded {lowercase_key} from environment variable {env_key}")

        # Then, load PHOENIX_ prefixed variables (these take precedence)
        prefix = "PHOENIX_"

        # First pass: collect all env vars and sort by key depth to avoid nested overwrites
        phoenix_vars = []
        for env_key, env_value in os.environ.items():
            if env_key.startswith(prefix):
                remaining = env_key[len(prefix) :]

                # Map specific patterns that need special handling
                special_mappings = {
                    "COLLECTION_TARGET_ZIPCODES": "collection.target_zipcodes",
                    "DATABASE_MAX_POOL_SIZE": "database.max_pool_size",
                    "DATABASE_CONNECTION_POOL_SIZE": "database.connection.pool.size",
                    "COLLECTION_MAX_REQUESTS_PER_HOUR": "collection.max_requests_per_hour",
                    "COLLECTION_MIN_REQUEST_DELAY": "collection.min_request_delay",
                    "SECURITY_SECRET_KEY": "security.secret_key",
                    "LOGGING_FILE_PATH": "logging.file_path",
                    "LOGGING_MAX_BYTES": "logging.max_bytes",
                    "LOGGING_BACKUP_COUNT": "logging.backup_count",
                    "PROCESSING_MAX_WORKERS": "processing.max_workers",
                    "PROCESSING_LLM_MODEL": "processing.llm_model",
                    "PROCESSING_LLM_TIMEOUT": "processing.llm_timeout",
                    "FEATURES_CACHE_ENABLED": "features.cache.enabled",
                    "DEBUG_ENABLED": "debug.enabled",
                    "DATA_OUTPUT_DIR": "data.output_dir",
                    "CACHE_DIRECTORY": "cache.directory",
                    "MONITORING_ENDPOINT": "monitoring.endpoint",
                    "COLLECTION_RETRY_MAX_RETRIES": "collection.retry.max_retries",
                    "API_RETRY_MAX_ATTEMPTS": "api.retry.max.attempts",
                    # Add special mappings for test boolean values
                    "BOOL_N": "bool.n",
                    "BOOL_N_UPPER": "bool.n.upper",  # This will nest under bool.n
                    "BOOL_Y": "bool.y",
                    "BOOL_Y_UPPER": "bool.y.upper",  # This will nest under bool.y
                    "BOOL_ENABLED": "bool.enabled",
                    "BOOL_ENABLE": "bool.enable",
                    "BOOL_ACTIVE": "bool.active",
                    "BOOL_DISABLED": "bool.disabled",
                    "BOOL_DISABLE": "bool.disable",
                    "BOOL_INACTIVE": "bool.inactive",
                    "BOOL_EMPTY": "bool.empty",
                }

                if remaining in special_mappings:
                    config_key = special_mappings[remaining]
                else:
                    # Default conversion: replace _ with .
                    config_key = remaining.lower().replace("_", ".")

                phoenix_vars.append((config_key, env_value, env_key))

        # Sort by key depth (fewer dots first) AND by key name to ensure consistent order
        # This ensures that 'bool.n' is processed before 'bool.n.upper'
        phoenix_vars.sort(key=lambda x: (x[0].count("."), x[0]))

        # Second pass: apply the values
        for config_key, env_value, env_key in phoenix_vars:
            self._set_nested_value(self.config, config_key, env_value)
            logger.debug(f"Loaded {config_key} from environment variable {env_key}")

    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set a value in nested dictionary using dot notation.

        Args:
            data: Dictionary to update.
            key: Dot-separated key path.
            value: Value to set.
        """
        parts = key.split(".")
        current = data

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Special handling: if we're overriding a non-dict value with a dict for nesting,
                # preserve the original value under a special '_value' key
                # This allows both 'bool.n' = 'n' and 'bool.n.upper' = 'N' to coexist
                original_value = current[part]
                current[part] = {"_value": original_value}
            current = current[part]

        current[parts[-1]] = value

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Get a value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search.
            key: Dot-separated key path.

        Returns:
            Value if found, None otherwise.
        """
        parts = key.split(".")
        current = data

        for i, part in enumerate(parts):
            if isinstance(current, dict) and part in current:
                current = current[part]
                # If this is the last part and current is a dict with '_value',
                # return the preserved value
                if i == len(parts) - 1 and isinstance(current, dict) and "_value" in current:
                    # Only return _value if there are other keys besides _value
                    # This means we preserved the original value when nesting was added
                    if any(k != "_value" for k in current.keys()):
                        return current["_value"]
            else:
                return None

        return current

    def _convert_type(self, value: Any, expected_type: type[T], key: Optional[str] = None) -> T:
        """Convert a value to the expected type with robust error handling.

        Args:
            value: Value to convert.
            expected_type: Target type.
            key: Configuration key for error context (optional).

        Returns:
            Converted value.

        Raises:
            ConfigurationError: If conversion fails.
        """
        # Handle None values
        if value is None:
            error_msg = f"Cannot convert None to {expected_type.__name__}"
            if key:
                error_msg += f" for key '{key}'"
            raise ConfigurationError(
                error_msg,
                context={"key": key, "type": expected_type.__name__}
                if key
                else {"type": expected_type.__name__},
            )

        # Already the correct type
        if isinstance(value, expected_type):
            return cast(T, value)

        # Handle empty strings
        if isinstance(value, str) and value.strip() == "":
            if expected_type in (int, float):
                error_msg = f"Cannot convert empty string to {expected_type.__name__}"
                if key:
                    error_msg += f" for key '{key}'"
                raise ConfigurationError(
                    error_msg,
                    context={"key": key, "value": repr(value), "type": expected_type.__name__},
                )
            elif expected_type is list:
                return cast(T, [])  # Empty string becomes empty list
            elif expected_type is bool:
                return cast(T, False)  # Empty string is falsy

        # String conversions
        if isinstance(value, str):
            if expected_type is bool:
                return cast(T, self._str_to_bool(value))
            elif expected_type is int:
                result = safe_int(value)
                if result is None:
                    error_msg = f"Cannot convert '{value}' to int"
                    if key:
                        error_msg += f" for key '{key}'"
                    raise ConfigurationError(
                        error_msg,
                        context={"key": key, "value": value, "type": "int"}
                        if key
                        else {"value": value, "type": "int"},
                    )
                return cast(T, result)
            elif expected_type is float:
                result = safe_float(value)
                if result is None:
                    error_msg = f"Cannot convert '{value}' to float"
                    if key:
                        error_msg += f" for key '{key}'"
                    raise ConfigurationError(
                        error_msg,
                        context={"key": key, "value": value, "type": "float"}
                        if key
                        else {"value": value, "type": "float"},
                    )
                return cast(T, result)
            elif expected_type is list:
                # Handle comma-separated lists with better parsing
                if ";" in value and "," in value:
                    # Handle mixed separators - prefer semicolon
                    items = value.split(";")
                elif ";" in value:
                    items = value.split(";")
                else:
                    items = value.split(",")

                # Clean and filter items
                return cast(T, [item.strip() for item in items if item.strip()])
            elif expected_type is dict:
                # Try to parse JSON-like strings
                try:
                    import json

                    return cast(T, json.loads(value))
                except json.JSONDecodeError:
                    # Try key=value pairs
                    result = {}
                    for pair in value.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            result[k.strip()] = v.strip()
                    if result:
                        return cast(T, result)
                    raise ConfigurationError(
                        f"Cannot parse '{value}' as dict",
                        context={"key": key, "value": value, "format": "JSON or key=value pairs"},
                    )

        # Numeric conversions between int and float
        if isinstance(value, (int, float)):
            if expected_type in (int, float):
                try:
                    return cast(T, expected_type(value))
                except (ValueError, OverflowError) as e:
                    error_msg = f"Numeric conversion failed for value {value}"
                    if key:
                        error_msg += f" for key '{key}'"
                    raise ConfigurationError(
                        error_msg,
                        context={"key": key, "value": value, "type": expected_type.__name__},
                        original_error=e,
                    ) from e

        # List to other conversions
        if isinstance(value, list):
            if expected_type is str:
                # Join list items with comma
                return cast(T, ", ".join(str(item) for item in value))
            elif expected_type is set:
                return cast(T, set(value))

        # Try direct conversion as last resort
        try:
            return cast(T, expected_type(value))
        except (ValueError, TypeError) as e:
            error_msg = f"Cannot convert value to {expected_type.__name__}"
            if key:
                error_msg += f" for key '{key}'"
            raise ConfigurationError(
                error_msg,
                context={
                    "key": key,
                    "value": repr(value),
                    "value_type": type(value).__name__,
                    "expected_type": expected_type.__name__,
                },
                original_error=e,
            ) from e

    def _str_to_bool(self, value: str) -> bool:
        """Convert string to boolean with case-insensitive matching.

        Args:
            value: String value to convert.

        Returns:
            Boolean value.

        Raises:
            ConfigurationError: If string is not a valid boolean.
        """
        if not isinstance(value, str):
            value = str(value)

        value_lower = value.lower().strip()

        # True values
        if value_lower in ("true", "yes", "y", "1", "on", "enabled", "enable", "active"):
            return True
        # False values
        elif value_lower in ("false", "no", "n", "0", "off", "disabled", "disable", "inactive", ""):
            return False
        else:
            raise ConfigurationError(
                f"Cannot convert '{value}' to boolean",
                context={
                    "value": value,
                    "valid_true": "true, yes, y, 1, on, enabled, enable, active",
                    "valid_false": "false, no, n, 0, off, disabled, disable, inactive, (empty string)",
                },
            )

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a configuration value.

        Args:
            key: Configuration key using dot notation.
            default: Default value if key is not found.

        Returns:
            Configuration value or default if not found.
        """
        # Check cache first
        if key in self._cache:
            cached_value = self._cache[key]
            # Return default if cached value is None and default is provided
            return default if cached_value is None and default is not None else cached_value

        # Get value from config
        value = self._get_nested_value(self.config, key)

        if value is None and default is not None:
            return default

        # Cache the actual value (could be None)
        self._cache[key] = value
        return value

    def get_required(self, key: str) -> Any:
        """Retrieve a required configuration value.

        Args:
            key: Configuration key using dot notation.

        Returns:
            Configuration value.

        Raises:
            ConfigurationError: If the key is not found.
        """
        value = self.get(key)
        if value is None:
            raise ConfigurationError(
                f"Required configuration key not found: {key}",
                context={"key": key, "environment": self.environment},
            )
        return value

    def get_typed(
        self, key: str, expected_type: type[T], default: Optional[T] = None
    ) -> Optional[T]:
        """Retrieve a typed configuration value.

        Args:
            key: Configuration key using dot notation.
            expected_type: Expected type for the value.
            default: Default value if key is not found.

        Returns:
            Typed configuration value or default.

        Raises:
            ConfigurationError: If value cannot be converted to expected type.
        """
        # Use a sentinel to distinguish between None as a value and None as not found
        _sentinel = object()
        value = self.get(key, _sentinel)

        # Key not found, return default
        if value is _sentinel:
            return default

        # Key found but value is None
        if value is None:
            # If default is None too, try to convert None
            if default is None:
                try:
                    return self._convert_type(value, expected_type, key)
                except ConfigurationError:
                    return default
            else:
                return default

        # Normal case: convert the value
        try:
            return self._convert_type(value, expected_type, key)
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"Failed to convert configuration value for key '{key}'",
                context={"key": key, "value": value, "expected_type": expected_type.__name__},
                original_error=e,
            ) from e

    def get_environment(self) -> str:
        """Get the current environment name.

        Returns:
            Environment name.
        """
        return self.environment

    def validate(self) -> List[str]:
        """Validate the configuration and return list of errors.

        Performs validation checks including:
        - Required keys are present
        - Environment-specific requirements
        - Values are valid (e.g., valid ZIP codes)
        - Type constraints are met
        - Format validation (URIs, paths, etc.)
        - Range validation for numeric values

        Returns:
            List of validation error messages. Empty list if validation passes.
        """
        validation_errors: List[Dict[str, Any]] = []

        # Collect all validation errors for comprehensive reporting
        try:
            self._validate_required_keys(validation_errors)
            self._validate_environment_specific(validation_errors)
            self._validate_data_types(validation_errors)
            self._validate_formats(validation_errors)
            self._validate_ranges(validation_errors)
            self._validate_custom_rules(validation_errors)
        except Exception as e:
            # Catch unexpected errors during validation
            validation_errors.append(
                {
                    "type": "unexpected_error",
                    "message": f"Unexpected error during validation: {str(e)}",
                    "error": e,
                }
            )

        # Convert validation errors to list of strings
        error_messages = []
        for error in validation_errors:
            if "key" in error:
                error_messages.append(f"{error['key']}: {error['message']}")
            elif "keys" in error:
                # Handle missing required keys
                for key in error.get("keys", []):
                    if "empty" in key:
                        error_messages.append(
                            f"{key.replace(' (empty)', '')}: Required configuration is empty"
                        )
                    else:
                        error_messages.append(f"{key}: Required configuration key missing")
            elif "dependency" in error:
                # Handle dependency errors with clear messaging
                error_messages.append(f"{error['message']} ({error['dependency']})")
            else:
                error_messages.append(error["message"])

        if not validation_errors:
            logger.info(f"Configuration validation passed for {self.environment} environment")

        return error_messages

    def validate_and_raise(self) -> None:
        """Validate the configuration and raise on errors.

        Performs validation checks including:
        - Required keys are present
        - Environment-specific requirements
        - Values are valid (e.g., valid ZIP codes)
        - Type constraints are met
        - Format validation (URIs, paths, etc.)
        - Range validation for numeric values

        Raises:
            ConfigurationError: If validation fails.
        """
        validation_errors: List[Dict[str, Any]] = []

        # Collect all validation errors for comprehensive reporting
        try:
            self._validate_required_keys(validation_errors)
            self._validate_environment_specific(validation_errors)
            self._validate_data_types(validation_errors)
            self._validate_formats(validation_errors)
            self._validate_ranges(validation_errors)
            self._validate_custom_rules(validation_errors)
        except Exception as e:
            # Catch unexpected errors during validation
            validation_errors.append(
                {
                    "type": "unexpected_error",
                    "message": f"Unexpected error during validation: {str(e)}",
                    "error": e,
                }
            )

        # Report all validation errors at once
        if validation_errors:
            error_summary = self._format_validation_errors(validation_errors)
            raise ConfigurationError(
                f"Configuration validation failed for {self.environment} environment",
                context={
                    "environment": self.environment,
                    "error_count": len(validation_errors),
                    "errors": validation_errors,
                    "summary": error_summary,
                },
            )

        logger.info(f"Configuration validation passed for {self.environment} environment")

    def _validate_required_keys(self, errors: List[Dict[str, Any]]) -> None:
        """Validate that all required keys are present."""
        # Base required keys for all environments
        required_keys = ["database.uri", "logging.level"]

        # Environment-specific required keys
        if self.environment == "production":
            required_keys.extend(["security.secret_key", "api.key", "monitoring.enabled"])
        elif self.environment == "staging":
            required_keys.extend(["api.key", "monitoring.enabled"])

        # Check for missing keys
        missing_keys = []
        for key in required_keys:
            value = self.get(key)
            if value is None:
                missing_keys.append(key)
            elif isinstance(value, str) and value.strip() == "":
                missing_keys.append(f"{key} (empty)")

        if missing_keys:
            errors.append(
                {
                    "type": "missing_required_keys",
                    "message": f"Required configuration keys missing for {self.environment}",
                    "keys": missing_keys,
                }
            )

    def _validate_environment_specific(self, errors: List[Dict[str, Any]]) -> None:
        """Validate environment-specific requirements."""
        if self.environment == "production":
            # Production must have secure settings
            secret_key = self.get("security.secret_key")
            if secret_key and len(str(secret_key)) < 32:
                errors.append(
                    {
                        "type": "weak_secret_key",
                        "message": "Production secret key must be at least 32 characters",
                        "current_length": len(str(secret_key)),
                    }
                )

            # Production must have proxy authentication
            if self.get("proxy.enabled", False):
                proxy_user = self.get("proxy.username")
                proxy_pass = self.get("proxy.password")
                if not proxy_user or not proxy_pass:
                    errors.append(
                        {
                            "type": "missing_proxy_auth",
                            "message": "Production proxy requires authentication credentials",
                        }
                    )

        elif self.environment == "development":
            # Development warnings (non-fatal)
            if self.get("debug", False) and self.get("monitoring.enabled", False):
                logger.warning("Debug mode enabled with monitoring - may impact performance")

    def _validate_data_types(self, errors: List[Dict[str, Any]]) -> None:
        """Validate data types for known configuration values."""
        type_validations = [
            ("database.port", int, "Database port must be an integer"),
            ("api.timeout", (int, float), "API timeout must be numeric"),
            ("api.retries", int, "API retries must be an integer"),
            ("logging.level", str, "Logging level must be a string"),
            ("features.cache_enabled", bool, "Cache enabled must be a boolean"),
            ("monitoring.enabled", bool, "Monitoring enabled must be a boolean"),
            ("collection.target_zipcodes", list, "Target ZIP codes must be a list"),
        ]

        for key, expected_types, error_msg in type_validations:
            value = self.get(key)
            if value is not None:
                if not isinstance(expected_types, tuple):
                    expected_types = (expected_types,)

                if not isinstance(value, expected_types):
                    try:
                        # Try to convert to expected type
                        self.get_typed(key, expected_types[0])
                    except ConfigurationError:
                        errors.append(
                            {
                                "type": "invalid_type",
                                "key": key,
                                "message": error_msg,
                                "expected": [t.__name__ for t in expected_types],
                                "actual": type(value).__name__,
                            }
                        )

    def _validate_formats(self, errors: List[Dict[str, Any]]) -> None:
        """Validate format requirements for specific configuration values."""
        # Validate ZIP codes
        zip_codes = self.get("collection.target_zipcodes", [])
        if isinstance(zip_codes, list):
            invalid_zips = []
            for i, zip_code in enumerate(zip_codes):
                if not is_valid_zipcode(str(zip_code)):
                    invalid_zips.append(
                        {"index": i, "value": zip_code, "type": type(zip_code).__name__}
                    )

            if invalid_zips:
                errors.append(
                    {
                        "type": "invalid_zipcodes",
                        "message": "Invalid ZIP codes in configuration",
                        "invalid_entries": invalid_zips,
                    }
                )

        # Validate database URI format
        db_uri = self.get("database.uri")
        if db_uri and isinstance(db_uri, str):
            if not any(
                db_uri.startswith(prefix)
                for prefix in ["mongodb://", "mongodb+srv://", "postgresql://", "sqlite:///"]
            ):
                errors.append(
                    {
                        "type": "invalid_uri_format",
                        "key": "database.uri",
                        "message": "Database URI must start with a valid protocol",
                        "valid_protocols": [
                            "mongodb://",
                            "mongodb+srv://",
                            "postgresql://",
                            "sqlite:///",
                        ],
                    }
                )

        # Validate logging level
        log_level = self.get("logging.level")
        if log_level and isinstance(log_level, str):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if log_level.upper() not in valid_levels:
                errors.append(
                    {
                        "type": "invalid_log_level",
                        "key": "logging.level",
                        "message": "Invalid logging level",
                        "value": log_level,
                        "valid_levels": valid_levels,
                    }
                )

        # Validate file paths exist
        path_configs = [
            ("logging.file_path", "Log file directory"),
            ("data.output_dir", "Data output directory"),
        ]

        for key, description in path_configs:
            path_value = self.get(key)
            if path_value and isinstance(path_value, str):
                path = Path(path_value)
                if path.is_absolute() and not path.parent.exists():
                    errors.append(
                        {
                            "type": "invalid_path",
                            "key": key,
                            "message": f"{description} parent directory does not exist",
                            "path": str(path),
                            "parent": str(path.parent),
                        }
                    )

    def _validate_ranges(self, errors: List[Dict[str, Any]]) -> None:
        """Validate numeric ranges and constraints."""
        # Port number validation
        port = self.get_typed("database.port", int)
        if port is not None and not (1 <= port <= 65535):
            errors.append(
                {
                    "type": "invalid_range",
                    "key": "database.port",
                    "message": "Port number out of valid range",
                    "value": port,
                    "valid_range": "1-65535",
                }
            )

        # Timeout validation
        timeout = self.get_typed("api.timeout", float)
        if timeout is not None and timeout <= 0:
            errors.append(
                {
                    "type": "invalid_range",
                    "key": "api.timeout",
                    "message": "API timeout must be positive",
                    "value": timeout,
                }
            )

        # Retry count validation
        retries = self.get_typed("api.retries", int)
        if retries is not None and retries < 0:
            errors.append(
                {
                    "type": "invalid_range",
                    "key": "api.retries",
                    "message": "API retries cannot be negative",
                    "value": retries,
                }
            )

        # Worker count validation
        workers = self.get_typed("processing.max_workers", int)
        if workers is not None and not (1 <= workers <= 100):
            errors.append(
                {
                    "type": "invalid_range",
                    "key": "processing.max_workers",
                    "message": "Worker count out of reasonable range",
                    "value": workers,
                    "valid_range": "1-100",
                }
            )

    def _validate_custom_rules(self, errors: List[Dict[str, Any]]) -> None:
        """Validate custom business rules and dependencies."""
        # If caching is enabled, cache directory should be specified
        if self.get_typed("features.cache_enabled", bool, False):
            cache_dir = self.get("cache.directory")
            if not cache_dir:
                errors.append(
                    {
                        "type": "missing_dependency",
                        "message": "Cache directory must be specified when caching is enabled",
                        "dependency": "cache.directory required when features.cache_enabled=true",
                    }
                )

        # If monitoring is enabled, endpoint should be specified
        if self.get_typed("monitoring.enabled", bool, False):
            endpoint = self.get("monitoring.endpoint")
            if not endpoint:
                errors.append(
                    {
                        "type": "missing_dependency",
                        "message": "Monitoring endpoint must be specified when monitoring is enabled",
                        "dependency": "monitoring.endpoint required when monitoring.enabled=true",
                    }
                )

        # Validate collection schedule format if present
        schedule = self.get("collection.schedule")
        if schedule and isinstance(schedule, str):
            # Simple cron expression validation
            parts = schedule.split()
            if len(parts) not in [5, 6]:  # Standard cron or with seconds
                errors.append(
                    {
                        "type": "invalid_format",
                        "key": "collection.schedule",
                        "message": "Invalid cron expression format",
                        "value": schedule,
                        "expected": "5 or 6 space-separated fields",
                    }
                )

    def _format_validation_errors(self, errors: List[Dict[str, Any]]) -> str:
        """Format validation errors into a readable summary."""
        if not errors:
            return "No validation errors"

        summary_lines = [f"Found {len(errors)} validation error(s):"]

        # Group errors by type
        error_groups: Dict[str, List[Dict[str, Any]]] = {}
        for error in errors:
            error_type = error.get("type", "unknown")
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)

        # Format each error group
        for error_type, group_errors in error_groups.items():
            summary_lines.append(f"\n{error_type.replace('_', ' ').title()}:")
            for error in group_errors:
                if "key" in error:
                    summary_lines.append(f"  - {error['key']}: {error['message']}")
                else:
                    summary_lines.append(f"  - {error['message']}")

        return "\n".join(summary_lines)

    # Configuration Helper Methods

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration settings.

        Returns a dictionary with database connection settings including:
        - uri: Database connection URI
        - name: Database name
        - host: Database host (if not using URI)
        - port: Database port
        - username: Database username (if applicable)
        - password: Database password (if applicable)
        - options: Additional connection options

        Returns:
            Dict containing database configuration.

        Raises:
            ConfigurationError: If required database settings are missing.
        """
        db_config = {}

        # Get URI or individual components
        uri = self.get("database.uri")
        if uri:
            db_config["uri"] = uri
        else:
            # Build from components
            host = self.get("database.host")
            port = self.get_typed("database.port", int)
            name = self.get("database.name")

            if not host or not name:
                raise ConfigurationError(
                    "Database configuration incomplete",
                    context={
                        "message": "Either database.uri or database.host/name must be specified",
                        "has_uri": bool(uri),
                        "has_host": bool(host),
                        "has_name": bool(name),
                    },
                )

            db_config.update(
                {
                    "host": host,
                    "port": port or 27017,  # MongoDB default
                    "name": name,
                }
            )

        # Optional authentication
        username = self.get("database.username")
        password = self.get("database.password")
        if username:
            db_config["username"] = username
            db_config["password"] = password

        # Additional options
        options = self.get("database.options", {})
        if isinstance(options, dict):
            db_config["options"] = options

        # Connection pool settings
        pool_size = self.get_typed("database.pool_size", int)
        if pool_size:
            db_config["pool_size"] = pool_size

        timeout = self.get_typed("database.timeout", int)
        if timeout:
            db_config["timeout"] = timeout

        return db_config

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration settings.

        Returns a dictionary with logging settings including:
        - level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - format: Log message format
        - file_path: Path to log file (if file logging enabled)
        - console: Whether to log to console
        - rotation: Log rotation settings

        Returns:
            Dict containing logging configuration.
        """
        log_config = {
            "level": self.get("logging.level", "INFO").upper(),
            "format": self.get(
                "logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            "console": self.get_typed("logging.console", bool, True),
        }

        # File logging configuration
        file_path = self.get("logging.file_path")
        if file_path:
            log_config["file_path"] = file_path

            # Rotation settings
            max_bytes = self.get_typed("logging.max_bytes", int)
            if max_bytes:
                log_config["max_bytes"] = max_bytes

            backup_count = self.get_typed("logging.backup_count", int)
            if backup_count:
                log_config["backup_count"] = backup_count

            rotation = self.get("logging.rotation")
            if rotation:
                log_config["rotation"] = rotation

        # Handler-specific settings
        handlers = self.get("logging.handlers", {})
        if isinstance(handlers, dict):
            log_config["handlers"] = handlers

        return log_config

    def get_collection_config(self) -> Dict[str, Any]:
        """Get data collection configuration settings.

        Returns a dictionary with collection settings including:
        - target_zipcodes: List of ZIP codes to collect data for
        - schedule: Collection schedule (cron expression)
        - sources: Data sources configuration
        - retry_policy: Retry settings for failed collections
        - batch_size: Number of properties to process in batch

        Returns:
            Dict containing collection configuration.
        """
        collection_config = {
            "target_zipcodes": self.get_typed("collection.target_zipcodes", list, []),
            "schedule": self.get("collection.schedule", "0 0 * * *"),  # Daily at midnight
            "batch_size": self.get_typed("collection.batch_size", int, 100),
            "max_workers": self.get_typed("collection.max_workers", int, 4),
        }

        # Data sources
        sources = self.get("collection.sources", {})
        if isinstance(sources, dict):
            collection_config["sources"] = sources
        else:
            # Default sources
            collection_config["sources"] = {
                "maricopa": {"enabled": True},
                "phoenix_mls": {"enabled": True},
            }

        # Retry policy
        retry_config = {
            "max_retries": self.get_typed("collection.retry.max_retries", int, 3),
            "delay": self.get_typed("collection.retry.delay", float, 1.0),
            "backoff": self.get_typed("collection.retry.backoff", float, 2.0),
        }
        collection_config["retry_policy"] = retry_config

        # Proxy settings
        if self.get_typed("proxy.enabled", bool, False):
            proxy_config = {
                "enabled": True,
                "url": self.get("proxy.url"),
                "username": self.get("proxy.username"),
                "password": self.get("proxy.password"),
                "rotation": self.get_typed("proxy.rotation", bool, True),
            }
            collection_config["proxy"] = proxy_config

        return collection_config

    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if environment is development.
        """
        return self.environment.lower() in ("development", "dev", "local")

    def is_testing(self) -> bool:
        """Check if running in testing environment.

        Returns:
            True if environment is testing or test.
        """
        return self.environment.lower() in ("testing", "test", "ci")

    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if environment is production or prod.
        """
        return self.environment.lower() in ("production", "prod")
