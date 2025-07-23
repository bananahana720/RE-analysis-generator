"""
Test suite for environment factory pattern - TDD approach.

Tests the environment detection, configuration creation, and validation
for the Phoenix Real Estate Data Collector application.
"""

import os
import threading

import pytest

from phoenix_real_estate.foundation.config.environment import (
    Environment,
    EnvironmentFactory,
    get_config,
    reset_config_cache,
    ConfigurationValidator,
    InvalidEnvironmentError,
    ConfigurationError,
)


class TestEnvironmentEnum:
    """Test the Environment enumeration."""

    def test_environment_values(self):
        """Test that Environment enum has expected values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.PRODUCTION.value == "production"

    def test_environment_string_conversion(self):
        """Test string representation of environments."""
        assert str(Environment.DEVELOPMENT) == "Environment.DEVELOPMENT"
        assert Environment.DEVELOPMENT.name == "DEVELOPMENT"

    def test_from_string_valid(self):
        """Test creating Environment from valid string values."""
        assert Environment.from_string("development") == Environment.DEVELOPMENT
        assert Environment.from_string("testing") == Environment.TESTING
        assert Environment.from_string("production") == Environment.PRODUCTION

        # Test case insensitive
        assert Environment.from_string("DEVELOPMENT") == Environment.DEVELOPMENT
        assert Environment.from_string("Testing") == Environment.TESTING

    def test_from_string_invalid(self):
        """Test creating Environment from invalid string raises error."""
        with pytest.raises(InvalidEnvironmentError) as exc:
            Environment.from_string("invalid")
        assert "Invalid environment: invalid" in str(exc.value)

    def test_all_environments(self):
        """Test getting all environment values."""
        envs = Environment.all()
        assert len(envs) == 3
        assert Environment.DEVELOPMENT in envs
        assert Environment.TESTING in envs
        assert Environment.PRODUCTION in envs


class TestEnvironmentFactory:
    """Test the EnvironmentFactory class."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables."""
        # Clear any existing ENVIRONMENT variable
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        return monkeypatch

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory structure."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create base .env file
        base_env = tmp_path / ".env"
        base_env.write_text("BASE_VAR=base_value\n")

        # Create environment-specific files
        (tmp_path / ".env.development").write_text("DEV_VAR=dev_value\n")
        (tmp_path / ".env.testing").write_text("TEST_VAR=test_value\n")
        (tmp_path / ".env.production").write_text("PROD_VAR=prod_value\n")

        # Create .env.local
        (tmp_path / ".env.local").write_text("LOCAL_VAR=local_value\n")

        return tmp_path

    def test_create_config_auto_detection_default(self, mock_env):
        """Test create_config defaults to development when ENVIRONMENT not set."""
        factory = EnvironmentFactory()
        config = factory.create_config()
        assert config.environment == Environment.DEVELOPMENT

    def test_create_config_auto_detection_from_env(self, mock_env):
        """Test create_config auto-detects from ENVIRONMENT variable."""
        mock_env.setenv("ENVIRONMENT", "production")
        factory = EnvironmentFactory()
        config = factory.create_config()
        assert config.environment == Environment.PRODUCTION

    def test_create_config_explicit_environment(self):
        """Test create_config with explicit environment parameter."""
        factory = EnvironmentFactory()
        config = factory.create_config(Environment.TESTING)
        assert config.environment == Environment.TESTING

    def test_create_development_config(self, temp_config_dir):
        """Test creating development configuration."""
        factory = EnvironmentFactory(root_dir=temp_config_dir)
        config = factory.create_development_config()

        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is True
        assert config.testing is False
        # Should load from .env, .env.local, and .env.development

    def test_create_testing_config(self, temp_config_dir):
        """Test creating testing configuration."""
        factory = EnvironmentFactory(root_dir=temp_config_dir)
        config = factory.create_testing_config()

        assert config.environment == Environment.TESTING
        assert config.debug is True
        assert config.testing is True
        # Should load from .env and .env.testing (not .env.local)

    def test_create_production_config(self, temp_config_dir):
        """Test creating production configuration."""
        factory = EnvironmentFactory(root_dir=temp_config_dir)
        config = factory.create_production_config()

        assert config.environment == Environment.PRODUCTION
        assert config.debug is False
        assert config.testing is False
        # Should load from .env and .env.production (not .env.local)

    def test_environment_file_loading_order(self, temp_config_dir, monkeypatch):
        """Test proper loading order of environment files."""
        # Create overlapping variables to test precedence
        (temp_config_dir / ".env").write_text("VAR=base\nONLY_BASE=yes\n")
        (temp_config_dir / ".env.local").write_text("VAR=local\nONLY_LOCAL=yes\n")
        (temp_config_dir / ".env.development").write_text("VAR=dev\nONLY_DEV=yes\n")

        monkeypatch.setenv("ENVIRONMENT", "development")
        factory = EnvironmentFactory(root_dir=temp_config_dir)
        config = factory.create_config()

        # Later files should override earlier ones
        assert os.environ.get("VAR") == "dev"
        assert os.environ.get("ONLY_BASE") == "yes"
        assert os.environ.get("ONLY_LOCAL") == "yes"
        assert os.environ.get("ONLY_DEV") == "yes"

    def test_missing_env_file_handling(self, tmp_path):
        """Test handling of missing environment files."""
        # Create empty directory with no .env files
        factory = EnvironmentFactory(root_dir=tmp_path)

        # Should not raise error, just use defaults
        config = factory.create_development_config()
        assert config.environment == Environment.DEVELOPMENT

    def test_configuration_validation_on_creation(self, temp_config_dir):
        """Test that configuration is validated when created."""
        # Create invalid config that should fail validation
        (temp_config_dir / ".env.development").write_text("MONGODB_URI=\n")  # Empty required field

        factory = EnvironmentFactory(root_dir=temp_config_dir)

        with pytest.raises(ConfigurationError) as exc:
            factory.create_development_config()
        assert "MONGODB_URI cannot be empty" in str(exc.value)

    def test_invalid_environment_error(self):
        """Test error handling for invalid environment."""
        factory = EnvironmentFactory()

        with pytest.raises(InvalidEnvironmentError):
            factory.create_config("invalid_env")


class TestGlobalConfigManagement:
    """Test global configuration management functions."""

    def setup_method(self):
        """Reset config cache before each test."""
        reset_config_cache()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config_cache()

    def test_get_config_returns_singleton(self, monkeypatch):
        """Test that get_config returns the same instance."""
        # Set minimal required env vars for testing
        monkeypatch.setenv("MONGODB_URI", "mongodb://test")
        monkeypatch.setenv("DATABASE_NAME", "test_db")

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
        assert id(config1) == id(config2)

    def test_get_config_with_different_environments(self, monkeypatch):
        """Test get_config with different environment settings."""
        # Set minimal required env vars
        monkeypatch.setenv("MONGODB_URI", "mongodb://test")
        monkeypatch.setenv("DATABASE_NAME", "test_db")

        # First call with development
        monkeypatch.setenv("ENVIRONMENT", "development")
        dev_config = get_config()
        assert dev_config.environment == Environment.DEVELOPMENT

        # Change environment but should still get cached version
        monkeypatch.setenv("ENVIRONMENT", "production")
        still_dev_config = get_config()
        assert still_dev_config.environment == Environment.DEVELOPMENT
        assert still_dev_config is dev_config

    def test_reset_config_cache(self, monkeypatch):
        """Test that reset_config_cache clears the singleton."""
        # Set minimal required env vars
        monkeypatch.setenv("MONGODB_URI", "mongodb://test")
        monkeypatch.setenv("DATABASE_NAME", "test_db")

        # Get initial config
        monkeypatch.setenv("ENVIRONMENT", "development")
        config1 = get_config()

        # Reset cache
        reset_config_cache()

        # Change environment and get new config
        monkeypatch.setenv("ENVIRONMENT", "production")
        config2 = get_config()

        assert config1 is not config2
        assert config1.environment == Environment.DEVELOPMENT
        assert config2.environment == Environment.PRODUCTION

    def test_thread_safety(self, monkeypatch):
        """Test thread safety of get_config."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("MONGODB_URI", "mongodb://test")
        monkeypatch.setenv("DATABASE_NAME", "test_db")
        reset_config_cache()

        configs = []
        errors = []

        def get_config_in_thread():
            try:
                config = get_config()
                configs.append(config)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_config_in_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0
        assert len(configs) == 10

        # All configs should be the same instance
        first_config = configs[0]
        for config in configs[1:]:
            assert config is first_config

    def test_get_config_with_explicit_environment(self, monkeypatch):
        """Test get_config with explicit environment parameter."""
        # Set minimal required env vars
        monkeypatch.setenv("MONGODB_URI", "mongodb://test")
        monkeypatch.setenv("DATABASE_NAME", "test_db")

        config = get_config(Environment.TESTING)
        assert config.environment == Environment.TESTING

        # Subsequent calls without parameter should return cached version
        config2 = get_config()
        assert config2.environment == Environment.TESTING


class TestConfigurationValidator:
    """Test the ConfigurationValidator class."""

    @pytest.fixture(autouse=True)
    def clean_environment(self, monkeypatch):
        """Clean environment before each test."""
        # Remove any PORT-related variables
        for key in list(os.environ.keys()):
            if "PORT" in key and key != "CLAUDE_CODE_SSE_PORT":
                monkeypatch.delenv(key, raising=False)

    @pytest.fixture
    def temp_env_files(self, tmp_path):
        """Create temporary environment files for testing."""
        # Valid development config
        (tmp_path / ".env.development").write_text("""
MONGODB_URI=mongodb://localhost:27017/dev
DATABASE_NAME=phoenix_dev
API_KEY=dev_key_123
        """)

        # Invalid testing config (missing required field)
        (tmp_path / ".env.testing").write_text("""
MONGODB_URI=mongodb://localhost:27017/test
DATABASE_NAME=
        """)

        # Valid production config
        (tmp_path / ".env.production").write_text("""
MONGODB_URI=mongodb+srv://prod-cluster/prod
DATABASE_NAME=phoenix_prod
API_KEY=prod_key_456
        """)

        return tmp_path

    def test_validate_all_environments_success(self, tmp_path):
        """Test validating all environments when all are valid."""
        # Create valid configs for all environments
        (tmp_path / ".env.development").write_text("""
MONGODB_URI=mongodb://localhost:27017/dev
DATABASE_NAME=phoenix_dev
API_KEY=dev_key_123
        """)

        (tmp_path / ".env.testing").write_text("""
MONGODB_URI=mongodb://localhost:27017/test
DATABASE_NAME=phoenix_test
API_KEY=test_key_123
        """)

        (tmp_path / ".env.production").write_text("""
MONGODB_URI=mongodb+srv://prod-cluster/prod
DATABASE_NAME=phoenix_prod
API_KEY=prod_key_456
        """)

        validator = ConfigurationValidator(root_dir=tmp_path)

        # Should not raise any errors
        validator.validate_all_environments()

    def test_validate_all_environments_with_errors(self, temp_env_files):
        """Test validating all environments with some invalid."""
        validator = ConfigurationValidator(root_dir=temp_env_files)

        # Add another invalid config
        (temp_env_files / ".env.production").write_text("MONGODB_URI=\n")

        with pytest.raises(ConfigurationError) as exc:
            validator.validate_all_environments()

        error_msg = str(exc.value)
        assert "Configuration errors found" in error_msg
        assert "testing:" in error_msg
        assert "production:" in error_msg
        assert "development:" not in error_msg  # This one is valid

    def test_validate_specific_environment_success(self, temp_env_files):
        """Test validating a specific valid environment."""
        validator = ConfigurationValidator(root_dir=temp_env_files)

        # Should not raise error
        validator.validate_environment(Environment.DEVELOPMENT)

    def test_validate_specific_environment_failure(self, temp_env_files):
        """Test validating a specific invalid environment."""
        validator = ConfigurationValidator(root_dir=temp_env_files)

        with pytest.raises(ConfigurationError) as exc:
            validator.validate_environment(Environment.TESTING)

        assert "DATABASE_NAME cannot be empty" in str(exc.value)

    def test_comprehensive_error_reporting(self, tmp_path):
        """Test that validator reports all errors comprehensively."""
        # Create config with multiple errors
        (tmp_path / ".env.development").write_text("""
MONGODB_URI=
DATABASE_NAME=
API_KEY=short
PORT=not_a_number
        """)

        validator = ConfigurationValidator(root_dir=tmp_path)

        with pytest.raises(ConfigurationError) as exc:
            validator.validate_environment(Environment.DEVELOPMENT)

        error_msg = str(exc.value)
        assert "MONGODB_URI cannot be empty" in error_msg
        assert "DATABASE_NAME cannot be empty" in error_msg
        assert "API_KEY must be at least" in error_msg
        assert "PORT must be a valid integer" in error_msg

    def test_missing_config_file_handling(self, tmp_path):
        """Test handling of missing configuration files."""
        validator = ConfigurationValidator(root_dir=tmp_path)

        # Should handle gracefully and report as error
        with pytest.raises(ConfigurationError) as exc:
            validator.validate_environment(Environment.PRODUCTION)

        assert "Configuration file not found" in str(exc.value)

    def test_validate_with_custom_validators(self, temp_env_files):
        """Test validation with custom validation rules."""

        # Add custom validator that checks for specific prefix
        def validate_api_key_prefix(config):
            if not config.api_key.startswith("pk_"):
                raise ConfigurationError("API_KEY must start with 'pk_'")

        validator = ConfigurationValidator(
            root_dir=temp_env_files, custom_validators=[validate_api_key_prefix]
        )

        with pytest.raises(ConfigurationError) as exc:
            validator.validate_environment(Environment.DEVELOPMENT)

        assert "API_KEY must start with 'pk_'" in str(exc.value)


class TestIntegration:
    """Integration tests for the complete configuration system."""

    @pytest.fixture(autouse=True)
    def clean_environment(self, monkeypatch):
        """Clean environment before each test."""
        # Remove any PORT-related variables
        for key in list(os.environ.keys()):
            if "PORT" in key and key != "CLAUDE_CODE_SSE_PORT":
                monkeypatch.delenv(key, raising=False)

    def test_full_configuration_lifecycle(self, tmp_path, monkeypatch):
        """Test complete configuration lifecycle from env files to validated config."""
        # Setup environment files
        (tmp_path / ".env").write_text("""
MONGODB_URI=mongodb://localhost:27017/base
DATABASE_NAME=phoenix_base
API_KEY=base_key_123456
        """)

        (tmp_path / ".env.development").write_text("""
DEBUG=true
DATABASE_NAME=phoenix_dev
        """)

        # Set environment
        monkeypatch.setenv("ENVIRONMENT", "development")

        # Create factory and get config
        factory = EnvironmentFactory(root_dir=tmp_path)
        config = factory.create_config()

        # Verify configuration
        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is True
        assert config.database_name == "phoenix_dev"  # Overridden
        assert config.mongodb_uri == "mongodb://localhost:27017/base"  # From base

        # Validate configuration
        validator = ConfigurationValidator(root_dir=tmp_path)
        validator.validate_environment(Environment.DEVELOPMENT)  # Should not raise

    def test_environment_isolation(self, tmp_path):
        """Test that different environments are properly isolated."""
        # Create different configs for each environment
        for env in ["development", "testing", "production"]:
            (tmp_path / f".env.{env}").write_text(f"""
MONGODB_URI=mongodb://localhost:27017/{env}
DATABASE_NAME=phoenix_{env}
API_KEY={env}_key_123456
SPECIAL_{env.upper()}_VAR=yes
            """)

        factory = EnvironmentFactory(root_dir=tmp_path)

        # Load each environment and verify isolation
        dev_config = factory.create_development_config()
        test_config = factory.create_testing_config()
        prod_config = factory.create_production_config()

        # Each should have its own values
        assert dev_config.database_name == "phoenix_development"
        assert test_config.database_name == "phoenix_testing"
        assert prod_config.database_name == "phoenix_production"

        # Environment-specific vars should only exist in their environment
        assert hasattr(dev_config, "special_development_var")
        assert not hasattr(dev_config, "special_testing_var")
        assert not hasattr(dev_config, "special_production_var")
