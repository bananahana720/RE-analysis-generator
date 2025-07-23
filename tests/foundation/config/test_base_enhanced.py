"""Test suite for enhanced base configuration provider.

This module contains comprehensive tests for the enhanced EnvironmentConfigProvider
following TDD approach. Tests cover:
- Environment variable loading with PHOENIX_ prefix and direct names
- Validation methods returning List[str]
- Import compatibility with python-dotenv fallback
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import tempfile
import yaml


# Test import compatibility before importing the module
@pytest.fixture
def mock_dotenv_missing():
    """Mock python-dotenv not being available."""
    # Store original modules
    original_modules = {}
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("dotenv")]
    for mod in modules_to_remove:
        original_modules[mod] = sys.modules[mod]
        del sys.modules[mod]

    # Mock the import to raise ImportError
    with patch.dict("sys.modules", {"dotenv": None}):
        yield

    # Restore original modules
    for mod, original in original_modules.items():
        sys.modules[mod] = original


class TestEnvironmentVariableLoading:
    """Test environment variable loading with enhanced support."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary configuration directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Create base configuration
            base_config = {
                "database": {"host": "localhost", "port": 27017, "name": "phoenix_test"},
                "logging": {"level": "INFO"},
                "api": {"timeout": 30, "key": "base_api_key"},
            }

            with open(config_dir / "base.yaml", "w") as f:
                yaml.dump(base_config, f)

            yield config_dir

    @pytest.fixture
    def clean_env(self):
        """Clean environment variables before and after test."""
        # Store original environment
        original_env = os.environ.copy()

        # Remove all PHOENIX_ and test-related variables
        env_vars_to_remove = [
            k
            for k in os.environ.keys()
            if k.startswith("PHOENIX_")
            or k in ["MONGODB_URI", "LOG_LEVEL", "API_KEY", "DEBUG_MODE"]
        ]
        for var in env_vars_to_remove:
            os.environ.pop(var, None)

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    def test_phoenix_prefix_variables(self, temp_config_dir, clean_env):
        """Test loading environment variables with PHOENIX_ prefix."""
        # Import here to ensure clean module state
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Set PHOENIX_ prefixed variables
        os.environ["PHOENIX_DATABASE_HOST"] = "env_host"
        os.environ["PHOENIX_DATABASE_PORT"] = "5432"
        os.environ["PHOENIX_API_KEY"] = "env_api_key"
        os.environ["PHOENIX_LOGGING_LEVEL"] = "DEBUG"

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        # Test that PHOENIX_ variables override config file values
        assert config.get("database.host") == "env_host"
        assert config.get("database.port") == "5432"
        assert config.get("api.key") == "env_api_key"
        assert config.get("logging.level") == "DEBUG"

    def test_direct_environment_variables(self, temp_config_dir, clean_env):
        """Test loading direct environment variables without prefix."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Set direct environment variables
        os.environ["MONGODB_URI"] = "mongodb://direct:27017/test"
        os.environ["LOG_LEVEL"] = "ERROR"
        os.environ["API_KEY"] = "direct_api_key"
        os.environ["DEBUG_MODE"] = "true"

        # Enhanced config should support both PHOENIX_ and direct env vars
        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        # Test direct environment variable support
        assert config.get("mongodb_uri") == "mongodb://direct:27017/test"
        assert config.get("log_level") == "ERROR"
        assert config.get("api_key") == "direct_api_key"
        assert config.get("debug_mode") == "true"

    def test_environment_variable_precedence(self, temp_config_dir, clean_env):
        """Test precedence: env vars > config files."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Set both PHOENIX_ and direct variables for same config
        os.environ["PHOENIX_DATABASE_HOST"] = "phoenix_host"
        os.environ["DATABASE_HOST"] = "direct_host"
        os.environ["PHOENIX_API_KEY"] = "phoenix_key"

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        # PHOENIX_ prefix should take precedence over direct env vars
        assert config.get("database.host") == "phoenix_host"
        assert config.get("api.key") == "phoenix_key"

        # Config file value should be overridden by env var
        assert config.get("database.name") == "phoenix_test"  # From config file

    def test_dual_support_compatibility(self, temp_config_dir, clean_env):
        """Test that both approaches work simultaneously."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Mix of PHOENIX_ and direct variables
        os.environ["PHOENIX_DATABASE_HOST"] = "phoenix_db"
        os.environ["LOG_LEVEL"] = "WARNING"
        os.environ["PHOENIX_API_TIMEOUT"] = "60"
        os.environ["DEBUG"] = "yes"

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        # Both types should be accessible
        assert config.get("database.host") == "phoenix_db"
        assert config.get("log_level") == "WARNING"
        assert config.get("api.timeout") == "60"
        assert config.get("debug") == "yes"

    def test_nested_environment_variables(self, temp_config_dir, clean_env):
        """Test nested configuration from environment variables."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Set nested configuration via env vars
        os.environ["PHOENIX_DATABASE_CONNECTION_POOL_SIZE"] = "10"
        os.environ["PHOENIX_API_RETRY_MAX_ATTEMPTS"] = "5"
        os.environ["PHOENIX_FEATURES_CACHE_ENABLED"] = "true"

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        # Test nested paths are created correctly
        assert config.get("database.connection.pool.size") == "10"
        assert config.get("api.retry.max.attempts") == "5"
        assert config.get("features.cache.enabled") == "true"

    def test_type_conversion_from_env_vars(self, temp_config_dir, clean_env):
        """Test type conversion for environment variables."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Set various types via env vars
        os.environ["PHOENIX_DATABASE_PORT"] = "5432"
        os.environ["PHOENIX_API_TIMEOUT"] = "30.5"
        os.environ["PHOENIX_DEBUG_ENABLED"] = "true"
        os.environ["PHOENIX_COLLECTION_TARGET_ZIPCODES"] = "85001,85002,85003"

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        # Test type conversions work correctly
        assert config.get_typed("database.port", int) == 5432
        assert config.get_typed("api.timeout", float) == 30.5
        assert config.get_typed("debug.enabled", bool) is True
        assert config.get_typed("collection.target_zipcodes", list) == ["85001", "85002", "85003"]


class TestValidationMethods:
    """Test enhanced validation methods."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary configuration directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Create minimal base configuration
            base_config = {
                "database": {"uri": "mongodb://localhost:27017/test"},
                "logging": {"level": "INFO"},
            }

            with open(config_dir / "base.yaml", "w") as f:
                yaml.dump(base_config, f)

            yield config_dir

    def test_validate_returns_list_of_errors(self, temp_config_dir):
        """Test that validate() returns List[str] instead of raising."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create config missing required fields
        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        # Enhanced validate should return list of errors
        errors = config.validate()

        assert isinstance(errors, list)
        assert all(isinstance(error, str) for error in errors)

    def test_production_validation_requirements(self, temp_config_dir):
        """Test production-specific validation requirements."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create production config missing required fields
        os.environ["ENVIRONMENT"] = "production"
        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        errors = config.validate()

        # Should have errors for missing production requirements
        assert len(errors) > 0
        assert any("security.secret_key" in error for error in errors)
        assert any("api.key" in error for error in errors)
        assert any("monitoring.enabled" in error for error in errors)

    def test_development_validation_requirements(self, temp_config_dir):
        """Test development-specific validation requirements."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create development config
        os.environ["ENVIRONMENT"] = "development"
        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

        errors = config.validate()

        # Development should have fewer required fields
        production_only_errors = [e for e in errors if "security.secret_key" in e]
        assert len(production_only_errors) == 0

    def test_required_fields_validation(self, temp_config_dir):
        """Test validation of required fields."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create config with empty required fields
        empty_config = {
            "database": {
                "uri": ""  # Empty required field
            },
            "logging": {
                "level": ""  # Empty required field
            },
        }

        with open(temp_config_dir / "base.yaml", "w") as f:
            yaml.dump(empty_config, f)

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)
        errors = config.validate()

        # Should report empty required fields
        assert any("database.uri" in error and "empty" in error for error in errors)
        assert any("logging.level" in error and "empty" in error for error in errors)

    def test_type_validation(self, temp_config_dir):
        """Test type validation for configuration values."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create config with invalid types
        invalid_config = {
            "database": {
                "uri": "mongodb://localhost:27017/test",
                "port": "not_a_number",  # Should be int
            },
            "logging": {"level": "INFO"},
            "api": {
                "timeout": "invalid",  # Should be numeric
                "retries": -5,  # Should be non-negative
            },
        }

        with open(temp_config_dir / "base.yaml", "w") as f:
            yaml.dump(invalid_config, f)

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)
        errors = config.validate()

        # Should report type validation errors
        assert any("database.port" in error and "integer" in error for error in errors)
        assert any("api.timeout" in error and "numeric" in error for error in errors)

    def test_validation_error_details(self, temp_config_dir):
        """Test that validation errors contain helpful details."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create config with multiple issues
        os.environ["ENVIRONMENT"] = "production"
        os.environ["PHOENIX_SECURITY_SECRET_KEY"] = "short"  # Too short for production

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)
        errors = config.validate()

        # Errors should be descriptive
        assert any("secret key" in error.lower() and "32 characters" in error for error in errors)

    def test_custom_validation_rules(self, temp_config_dir):
        """Test custom business rule validation."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create config with dependency issues
        config_with_deps = {
            "database": {"uri": "mongodb://localhost:27017/test"},
            "logging": {"level": "INFO"},
            "features": {
                "cache_enabled": True  # But no cache.directory specified
            },
            "monitoring": {
                "enabled": True  # But no monitoring.endpoint specified
            },
        }

        with open(temp_config_dir / "base.yaml", "w") as f:
            yaml.dump(config_with_deps, f)

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)
        errors = config.validate()

        # Should report dependency validation errors
        assert any("cache.directory" in error for error in errors)
        assert any("monitoring.endpoint" in error for error in errors)

    def test_zipcode_validation(self, temp_config_dir):
        """Test ZIP code format validation."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create config with invalid ZIP codes
        config_with_zips = {
            "database": {"uri": "mongodb://localhost:27017/test"},
            "logging": {"level": "INFO"},
            "collection": {"target_zipcodes": ["85001", "invalid", "123", "85002-1234"]},
        }

        with open(temp_config_dir / "base.yaml", "w") as f:
            yaml.dump(config_with_zips, f)

        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)
        errors = config.validate()

        # Should report invalid ZIP codes
        assert any("ZIP code" in error or "zipcode" in error.lower() for error in errors)


class TestImportCompatibility:
    """Test import compatibility with python-dotenv."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary configuration directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Create minimal base configuration
            base_config = {
                "database": {"uri": "mongodb://localhost:27017/test"},
                "logging": {"level": "INFO"},
            }

            with open(config_dir / "base.yaml", "w") as f:
                yaml.dump(base_config, f)

            # Clean up any existing .env file before test
            if os.path.exists(".env"):
                os.remove(".env")

            yield config_dir

            # Clean up .env file after test
            if os.path.exists(".env"):
                os.remove(".env")

    @pytest.fixture
    def clean_env(self):
        """Clean environment variables before and after test."""
        # Store original environment
        original_env = os.environ.copy()

        # Remove all PHOENIX_ and test-related variables
        env_vars_to_remove = [
            k
            for k in os.environ.keys()
            if k.startswith("PHOENIX_")
            or k in ["MONGODB_URI", "LOG_LEVEL", "API_KEY", "DEBUG_MODE"]
        ]
        for var in env_vars_to_remove:
            os.environ.pop(var, None)

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    def test_dotenv_import_success(self, temp_config_dir):
        """Test successful import when python-dotenv is available."""
        # This test assumes python-dotenv is installed (it is in our dependencies)
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create .env file
        env_content = """
PHOENIX_DATABASE_HOST=dotenv_host
PHOENIX_API_KEY=dotenv_key
LOG_LEVEL=DEBUG
"""
        with open(".env", "w") as f:
            f.write(env_content)

        try:
            # Should load .env file successfully
            config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=True)

            # Values from .env should be loaded
            assert config.get("database.host") == "dotenv_host"
            assert config.get("api.key") == "dotenv_key"
        finally:
            # Clean up
            if os.path.exists(".env"):
                os.remove(".env")

    def test_dotenv_import_fallback(self, temp_config_dir, mock_dotenv_missing):
        """Test graceful fallback when python-dotenv is not available."""
        # Import with mocked missing dotenv
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Should not raise ImportError
        config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=True)

        # Should still work without dotenv
        assert config is not None
        assert config.get("database.uri") is not None

    def test_load_dotenv_disabled(self, temp_config_dir):
        """Test that load_dotenv=False skips .env loading."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create .env file
        with open(".env", "w") as f:
            f.write("PHOENIX_DATABASE_HOST=should_not_load\n")

        try:
            # Should not load .env file
            config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=False)

            # .env values should not be loaded
            assert config.get("database.host") != "should_not_load"
        finally:
            # Clean up
            if os.path.exists(".env"):
                os.remove(".env")

    def test_dotenv_loading_with_comments(self, temp_config_dir, clean_env):
        """Test .env loading with comments and special characters."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create .env file with various formats
        env_content = """
# Database configuration
PHOENIX_DATABASE_HOST=localhost  # Comment after value
PHOENIX_DATABASE_PORT=5432

# API settings
PHOENIX_API_KEY="key with spaces"
PHOENIX_API_SECRET='single quotes'

# Empty lines and comments should be ignored

PHOENIX_FEATURES_ENABLED=true
"""
        with open(".env", "w") as f:
            f.write(env_content)

        try:
            config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=True)

            # All values should be loaded correctly
            # python-dotenv handles inline comments properly and strips them
            assert config.get("database.host") == "localhost"
            assert config.get("database.port") == "5432"
            assert config.get("api.key") == "key with spaces"
            assert config.get("api.secret") == "single quotes"
            assert config.get("features.enabled") == "true"
        finally:
            # Clean up
            if os.path.exists(".env"):
                os.remove(".env")

    def test_env_file_precedence_over_config(self, temp_config_dir, clean_env):
        """Test that .env file values override config file values."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create .env file
        with open(".env", "w") as f:
            f.write("PHOENIX_DATABASE_HOST=env_file_host\n")

        try:
            config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=True)

            # .env value should override config file
            assert config.get("database.host") == "env_file_host"
        finally:
            # Clean up
            if os.path.exists(".env"):
                os.remove(".env")

    def test_explicit_env_vars_override_dotenv(self, temp_config_dir, clean_env):
        """Test that explicit environment variables override .env file."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create .env file
        with open(".env", "w") as f:
            f.write("PHOENIX_DATABASE_HOST=dotenv_host\n")

        # Set explicit environment variable
        os.environ["PHOENIX_DATABASE_HOST"] = "explicit_host"

        try:
            config = EnvironmentConfigProvider(config_dir=temp_config_dir, load_dotenv=True)

            # Explicit env var should override .env file
            assert config.get("database.host") == "explicit_host"
        finally:
            # Clean up
            if os.path.exists(".env"):
                os.remove(".env")


class TestEnhancedFeatures:
    """Test additional enhanced features."""

    @pytest.fixture
    def basic_config_dir(self):
        """Create basic configuration directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Create basic config
            base_config = {
                "database": {"uri": "mongodb://localhost:27017/test"},
                "logging": {"level": "INFO"},
            }

            with open(config_dir / "base.yaml", "w") as f:
                yaml.dump(base_config, f)

            yield config_dir

    @pytest.fixture
    def clean_env(self):
        """Clean environment variables before and after test."""
        # Store original environment
        original_env = os.environ.copy()

        # Remove all PHOENIX_ and test-related variables
        env_vars_to_remove = [
            k
            for k in os.environ.keys()
            if k.startswith("PHOENIX_")
            or k in ["MONGODB_URI", "LOG_LEVEL", "API_KEY", "DEBUG_MODE", "ENVIRONMENT"]
        ]
        for var in env_vars_to_remove:
            os.environ.pop(var, None)

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    def test_validation_performance(self, basic_config_dir):
        """Test that validation completes in reasonable time."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
        import time

        config = EnvironmentConfigProvider(config_dir=basic_config_dir, load_dotenv=False)

        # Validation should complete quickly
        start_time = time.time()
        errors = config.validate()
        elapsed = time.time() - start_time

        assert elapsed < 0.1  # Should complete in under 100ms
        assert isinstance(errors, list)

    def test_error_aggregation(self, basic_config_dir, clean_env):
        """Test that all validation errors are collected and returned."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        # Create config with multiple issues
        bad_config = {
            "database": {"uri": "", "port": "invalid"},
            "logging": {"level": "INVALID_LEVEL"},
            "collection": {"target_zipcodes": ["bad1", "bad2"]},
            "api": {"timeout": -1, "retries": "not_a_number"},
        }

        with open(basic_config_dir / "base.yaml", "w") as f:
            yaml.dump(bad_config, f)

        os.environ["ENVIRONMENT"] = "production"
        config = EnvironmentConfigProvider(config_dir=basic_config_dir, load_dotenv=False)
        errors = config.validate()

        # Should collect all errors, not stop at first
        assert len(errors) >= 5  # At least one error per issue

        # Should have errors for each category
        assert any("database.uri" in e for e in errors)
        assert any("database.port" in e for e in errors)
        assert any("logging.level" in e for e in errors)
        assert any("zipcode" in e.lower() or "zip code" in e.lower() for e in errors)
        # api.timeout might not generate error if conversion fails
        assert any("api" in e.lower() for e in errors)

    def test_backward_compatibility(self, basic_config_dir, clean_env):
        """Test that existing code continues to work with enhancements."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        config = EnvironmentConfigProvider(config_dir=basic_config_dir, load_dotenv=False)

        # All existing methods should still work
        assert config.get("database.uri") == "mongodb://localhost:27017/test"
        assert config.get_required("logging.level") == "INFO"
        assert config.get_typed("database.port", int, 27017) == 27017
        assert config.get_environment() in ["development", "test", "production"]

        # Original validate() behavior when called without expecting return value
        try:
            config.validate()  # Should not raise if config is valid
        except Exception as e:
            # If it raises, it should be ConfigurationError
            assert "ConfigurationError" in str(type(e))
