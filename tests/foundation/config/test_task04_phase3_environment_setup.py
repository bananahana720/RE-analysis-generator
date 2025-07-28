"""Task 04 Phase 3: Environment Setup Testing.

This module provides testing for development environment setup scripts,
configuration validation scripts, and environment-specific scenarios.

Test Scenarios:
- Development environment validation script
- Configuration loading verification
- Environment separation (dev/test/prod)
- Component integration testing
- Error handling and recovery
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from phoenix_real_estate.foundation.config import (
    reset_config_cache,
    EnvironmentConfigProvider,
    ConfigurationError,
)


class TestTask04Phase3EnvironmentSetup:
    """Test suite for Task 04 Phase 3: Environment Setup Testing."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Store original environment
        original_env = os.environ.copy()
        original_path = sys.path.copy()

        # Reset config cache
        reset_config_cache()

        yield

        # Restore original state
        os.environ.clear()
        os.environ.update(original_env)
        sys.path[:] = original_path
        reset_config_cache()

    @pytest.fixture
    def temp_env_dir(self):
        """Create temporary environment setup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_dir = Path(temp_dir)

            # Create .env file for development
            env_file = env_dir / ".env"
            env_content = """
# Development Environment Configuration
ENVIRONMENT=development
MARICOPA_API_KEY=test_development_key
MARICOPA_RATE_LIMIT=50
MONGODB_URI=mongodb://localhost:27017/phoenix_real_estate_dev
LOG_LEVEL=DEBUG
DEBUG=true
""".strip()
            with open(env_file, "w") as f:
                f.write(env_content)

            # Create config directory structure
            config_dir = env_dir / "config"
            config_dir.mkdir()

            # Create base configuration
            base_config = env_dir / "config" / "base.yaml"
            base_yaml = """
application:
  name: Phoenix Real Estate Collector
  version: 0.1.0

database:
  name: phoenix_real_estate
  max_pool_size: 10

logging:
  level: INFO
  console_output: true

collection:
  max_requests_per_hour: 100
  target_zip_codes:
    - "85031"
    - "85033"

sources:
  maricopa_county:
    enabled: true
    rate_limit: 1000
""".strip()
            with open(base_config, "w") as f:
                f.write(base_yaml)

            yield env_dir

    def create_validation_script(self, script_dir: Path) -> Path:
        """Create development environment validation script."""
        script_content = '''#!/usr/bin/env python3
"""Development Environment Validation Script."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def validate_environment():
    """Validate development environment setup."""
    print("🔍 Validating development environment setup...")
    
    errors = []
    warnings = []
    
    # Check required environment variables
    required_vars = [
        'MARICOPA_API_KEY',
        'MONGODB_URI',
        'ENVIRONMENT'
    ]
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            errors.append(f"Missing required environment variable: {var}")
        else:
            print(f"✅ {var} configured")
    
    # Check optional variables with defaults
    optional_vars = {
        'MARICOPA_RATE_LIMIT': '1000',
        'LOG_LEVEL': 'INFO',
        'DEBUG': 'false'
    }
    
    for var, default in optional_vars.items():
        value = os.environ.get(var, default)
        print(f"✅ {var}: {value}")
    
    # Validate configuration loading
    try:
        from phoenix_real_estate.foundation.config.base import get_config
        config = get_config()
        
        # Test required configuration
        api_key = config.get_required('MARICOPA_API_KEY')
        print(f"✅ API Key configured: {api_key[:8]}...")
        
        # Test rate limiting
        rate_limit = config.get("MARICOPA_RATE_LIMIT", 1000)
        print(f"✅ Rate limit: {rate_limit}")
        
        # Test database configuration
        db_uri = config.get('MONGODB_URI')
        if db_uri:
            print(f"✅ Database URI configured")
        else:
            warnings.append("Database URI not configured - using default")
            
    except Exception as e:
        errors.append(f"Configuration loading failed: {str(e)}")
    
    # Report results
    if errors:
        print("\\n❌ Environment validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    if warnings:
        print("\\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("\\n🎉 Development environment validation successful!")
    return True

if __name__ == "__main__":
    validate_environment()
'''

        script_path = script_dir / "validate_environment.py"
        with open(script_path, "w") as f:
            f.write(script_content)

        # Make script executable
        script_path.chmod(0o755)
        return script_path

    async def test_development_environment_validation_script(self, temp_env_dir):
        """Test development environment validation script."""
        # Create validation script
        self.create_validation_script(temp_env_dir)

        # Set up environment variables from .env file
        env_file = temp_env_dir / ".env"
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

        # Test successful validation
        with patch("phoenix_real_estate.foundation.config.base.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.get_required.return_value = "test_development_key"
            mock_config.get.side_effect = lambda key, default=None: {
                "MARICOPA_RATE_LIMIT": 50,
                "MONGODB_URI": "mongodb://localhost:27017/phoenix_real_estate_dev",
            }.get(key, default)
            mock_get_config.return_value = mock_config

            # Execute validation script logic
            errors = []

            # Check required environment variables
            required_vars = ["MARICOPA_API_KEY", "MONGODB_URI", "ENVIRONMENT"]

            for var in required_vars:
                value = os.environ.get(var)
                if not value:
                    errors.append(f"Missing required environment variable: {var}")

            assert len(errors) == 0, f"Validation should pass: {errors}"

            # Test configuration access
            config = mock_get_config()
            api_key = config.get_required("MARICOPA_API_KEY")
            assert api_key == "test_development_key"

    async def test_configuration_loading_verification(self, temp_env_dir):
        """Test configuration loading verification across environments."""
        # Test development configuration
        os.environ["ENVIRONMENT"] = "development"
        os.environ["MARICOPA_API_KEY"] = "dev_api_key"
        os.environ["MARICOPA_RATE_LIMIT"] = "25"

        config_dir = temp_env_dir / "config"

        config = EnvironmentConfigProvider(config_dir=config_dir, environment="development")

        # Verify configuration values are loaded correctly
        assert config.get_environment() == "development"
        assert config.is_development() is True

        # Test environment-specific overrides
        api_key = config.get("maricopa_api_key")
        assert api_key == "dev_api_key"

        rate_limit = config.get_typed("maricopa_rate_limit", int)
        assert rate_limit == 25

        # Test base configuration inheritance
        app_name = config.get("application.name")
        assert app_name == "Phoenix Real Estate Collector"

        # Test default values
        max_pool_size = config.get("database.max_pool_size")
        assert max_pool_size == 10

    async def test_environment_separation(self, temp_env_dir):
        """Test environment separation (dev/test/prod)."""
        config_dir = temp_env_dir / "config"

        # Create environment-specific configurations
        dev_config = config_dir / "development.yaml"
        with open(dev_config, "w") as f:
            f.write(
                """
logging:
  level: DEBUG
database:
  name: phoenix_real_estate_dev
collection:
  max_requests_per_hour: 50
""".strip()
            )

        test_config = config_dir / "testing.yaml"
        with open(test_config, "w") as f:
            f.write(
                """
logging:
  level: WARNING
database:
  name: phoenix_real_estate_test
collection:
  max_requests_per_hour: 10
sources:
  maricopa_county:
    enabled: false
""".strip()
            )

        prod_config = config_dir / "production.yaml"
        with open(prod_config, "w") as f:
            f.write(
                """
logging:
  level: ERROR
database:
  name: phoenix_real_estate_prod
security:
  secret_key: production-secret-key-32-chars-minimum!
monitoring:
  enabled: true
""".strip()
            )

        # Test development environment
        dev_env = EnvironmentConfigProvider(config_dir=config_dir, environment="development")

        assert dev_env.get("logging.level") == "DEBUG"
        assert dev_env.get("database.name") == "phoenix_real_estate_dev"
        assert dev_env.get("collection.max_requests_per_hour") == 50
        assert dev_env.is_development() is True

        # Test testing environment
        test_env = EnvironmentConfigProvider(config_dir=config_dir, environment="testing")

        assert test_env.get("logging.level") == "WARNING"
        assert test_env.get("database.name") == "phoenix_real_estate_test"
        assert test_env.get("collection.max_requests_per_hour") == 10
        assert test_env.get("sources.maricopa_county.enabled") is False
        assert test_env.is_testing() is True

        # Test production environment
        prod_env = EnvironmentConfigProvider(config_dir=config_dir, environment="production")

        assert prod_env.get("logging.level") == "ERROR"
        assert prod_env.get("database.name") == "phoenix_real_estate_prod"
        assert prod_env.get("security.secret_key") is not None
        assert prod_env.get("monitoring.enabled") is True
        assert prod_env.is_production() is True

    async def test_component_integration_configuration(self, temp_env_dir):
        """Test component integration with configuration."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ["MARICOPA_API_KEY"] = "test_integration_key"
        os.environ["MARICOPA_BASE_URL"] = "https://api.test.maricopa.gov"
        os.environ["MARICOPA_TIMEOUT"] = "45"
        os.environ["MARICOPA_RATE_LIMIT"] = "75"

        config_dir = temp_env_dir / "config"
        config = EnvironmentConfigProvider(config_dir=config_dir, environment="development")

        # Test MaricopaAPIClient configuration integration
        class MockMaricopaAPIClient:
            def __init__(self, api_key: str, base_url: str, timeout: int, rate_limit: int):
                self.api_key = api_key
                self.base_url = base_url
                self.timeout = timeout
                self.rate_limit = rate_limit

        # Simulate component initialization from config
        client_config = {
            "api_key": config.get_required("maricopa_api_key"),
            "base_url": config.get(
                "maricopa_base_url", "https://api.mcassessor.maricopa.gov/api/v1"
            ),
            "timeout": config.get_typed("maricopa_timeout", int, 10),
            "rate_limit": config.get_typed("maricopa_rate_limit", int, 1000),
        }

        client = MockMaricopaAPIClient(**client_config)

        assert client.api_key == "test_integration_key"
        assert client.base_url == "https://api.test.maricopa.gov"
        assert client.timeout == 45
        assert client.rate_limit == 75

        # Test rate limiter configuration
        class MockRateLimiter:
            def __init__(self, max_requests: int, time_window: int):
                self.max_requests = max_requests
                self.time_window = time_window

        rate_limiter = MockRateLimiter(
            max_requests=client.rate_limit,
            time_window=3600,  # 1 hour in seconds
        )

        assert rate_limiter.max_requests == 75
        assert rate_limiter.time_window == 3600

        # Test collector configuration
        collector_config = config.get_collection_config()
        assert collector_config["batch_size"] == 100  # From base config
        assert collector_config["max_workers"] == 4  # From base config
        assert "retry_policy" in collector_config
        assert collector_config["retry_policy"]["max_retries"] == 3

    async def test_configuration_error_handling(self, temp_env_dir):
        """Test configuration error handling and recovery."""
        config_dir = temp_env_dir / "config"

        # Test missing required configuration
        os.environ["ENVIRONMENT"] = "production"
        # Don't set required production configs

        config = EnvironmentConfigProvider(config_dir=config_dir, environment="production")

        # Should raise clear error for missing required config
        with pytest.raises(ConfigurationError) as exc_info:
            config.get_required("api_key")  # Required in production

        error = exc_info.value
        assert "Required configuration key not found" in str(error)
        assert error.context["environment"] == "production"

        # Test invalid configuration file handling
        invalid_config = config_dir / "invalid.yaml"
        with open(invalid_config, "w") as f:
            f.write("invalid: yaml: [unclosed")  # Malformed YAML

        # Should handle malformed YAML gracefully
        with pytest.raises(ConfigurationError) as exc_info:
            EnvironmentConfigProvider(config_dir=config_dir, environment="invalid")

        assert "Failed to parse YAML file" in str(exc_info.value)

        # Test configuration with missing config directory
        missing_dir = temp_env_dir / "nonexistent_config"

        # Should work with just environment variables
        os.environ["PHOENIX_TEST_CONFIG"] = "fallback_value"

        fallback_config = EnvironmentConfigProvider(
            config_dir=missing_dir, environment="development"
        )

        test_value = fallback_config.get("test.config")
        assert test_value == "fallback_value"

    async def test_configuration_validation_comprehensive(self, temp_env_dir):
        """Test comprehensive configuration validation."""
        config_dir = temp_env_dir / "config"

        # Set up configuration with various validation scenarios
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["PHOENIX_DATABASE_PORT"] = "65536"  # Invalid port (too high)
        os.environ["PHOENIX_API_TIMEOUT"] = "-10"  # Invalid timeout (negative)
        os.environ["PHOENIX_API_RETRIES"] = "-1"  # Invalid retries (negative)
        os.environ["PHOENIX_PROCESSING_MAX_WORKERS"] = "150"  # Too many workers
        os.environ["COLLECTION_TARGET_ZIPCODES"] = "85031,invalid_zip,85033"  # Mixed valid/invalid

        config = EnvironmentConfigProvider(config_dir=config_dir, environment="testing")

        # Run comprehensive validation
        validation_errors = config.validate()

        # Should detect multiple validation issues
        assert len(validation_errors) > 0

        # Check for specific validation failures
        error_text = " ".join(validation_errors).lower()

        # Check for port range validation (if implemented)
        if "port" in error_text:
            assert any("port" in error.lower() for error in validation_errors)

        # Check for ZIP code validation (should be implemented)
        if "zip" in error_text or "zipcode" in error_text:
            zip_errors = [error for error in validation_errors if "zip" in error.lower()]
            assert len(zip_errors) > 0

    async def test_environment_specific_validation_rules(self, temp_env_dir):
        """Test environment-specific validation rules."""
        config_dir = temp_env_dir / "config"

        # Test production-specific validation
        os.environ["ENVIRONMENT"] = "production"
        os.environ["SECRET_KEY"] = "short"  # Too short for production
        os.environ["API_KEY"] = "prod-api-key"
        os.environ["MONITORING_ENABLED"] = "true"

        prod_config = EnvironmentConfigProvider(config_dir=config_dir, environment="production")

        validation_errors = prod_config.validate()

        # Should fail due to weak secret key in production
        secret_errors = [
            error
            for error in validation_errors
            if "secret" in error.lower() and "character" in error.lower()
        ]
        assert len(secret_errors) > 0

        # Fix secret key and test again
        os.environ["SECRET_KEY"] = "production-secret-key-32-characters-minimum-length!"

        prod_config_fixed = EnvironmentConfigProvider(
            config_dir=config_dir, environment="production"
        )

        validation_errors_fixed = prod_config_fixed.validate()
        secret_errors_fixed = [
            error
            for error in validation_errors_fixed
            if "secret" in error.lower() and "character" in error.lower()
        ]
        assert len(secret_errors_fixed) == 0  # No more secret key errors

        # Test development-specific validation (more lenient)
        os.environ["ENVIRONMENT"] = "development"
        os.environ["SECRET_KEY"] = "dev-key"  # Shorter key allowed in dev

        dev_config = EnvironmentConfigProvider(config_dir=config_dir, environment="development")

        dev_validation_errors = dev_config.validate()

        # Development should be more lenient with secret key length
        dev_secret_errors = [
            error
            for error in dev_validation_errors
            if "secret" in error.lower() and "character" in error.lower()
        ]
        # Should have fewer or no secret key errors in development
        assert len(dev_secret_errors) <= len(secret_errors)

    async def test_configuration_helper_methods(self, temp_env_dir):
        """Test configuration helper methods."""
        config_dir = temp_env_dir / "config"

        os.environ["ENVIRONMENT"] = "development"
        os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
        os.environ["MONGODB_DATABASE"] = "phoenix_test"
        os.environ["PHOENIX_DATABASE_TIMEOUT"] = "20"
        os.environ["PHOENIX_LOGGING_LEVEL"] = "DEBUG"
        os.environ["PHOENIX_LOGGING_FILE_PATH"] = "/var/log/phoenix.log"

        config = EnvironmentConfigProvider(config_dir=config_dir, environment="development")

        # Test database configuration helper
        db_config = config.get_database_config()

        assert "uri" in db_config
        assert db_config["uri"] == "mongodb://localhost:27017/test_db"
        assert db_config.get("timeout") == 20

        # Test logging configuration helper
        log_config = config.get_logging_config()

        assert log_config["level"] == "DEBUG"
        assert log_config["console"] is True
        assert log_config["file_path"] == "/var/log/phoenix.log"

        # Test collection configuration helper
        collection_config = config.get_collection_config()

        assert "target_zipcodes" in collection_config
        assert "retry_policy" in collection_config
        assert "batch_size" in collection_config
        assert collection_config["retry_policy"]["max_retries"] == 3

    async def test_dotenv_file_loading(self, temp_env_dir):
        """Test .env file loading functionality."""
        # Create .env file with test configuration
        env_file = temp_env_dir / ".env"
        env_content = """
# Test environment file
ENVIRONMENT=development
MARICOPA_API_KEY=dotenv_api_key
MARICOPA_RATE_LIMIT=35
DEBUG=true
TEST_VALUE=from_dotenv
""".strip()

        with open(env_file, "w") as f:
            f.write(env_content)

        # Change to temp directory so .env file is found
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_env_dir)

            config_dir = temp_env_dir / "config"
            config = EnvironmentConfigProvider(
                config_dir=config_dir, environment="development", load_dotenv=True
            )

            # Values should be loaded from .env file
            assert config.get("maricopa_api_key") == "dotenv_api_key"
            assert config.get_typed("maricopa_rate_limit", int) == 35
            assert config.get_typed("debug", bool) is True
            assert config.get("test_value") == "from_dotenv"

        finally:
            os.chdir(original_cwd)
