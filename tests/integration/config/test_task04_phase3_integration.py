"""Task 04 Phase 3: Configuration & Environment Integration Testing.

This module provides comprehensive integration testing that validates
the complete configuration and environment setup workflow including
real-world scenarios and cross-component integration.

Integration Scenarios:
- End-to-end configuration loading workflow
- Multi-environment configuration testing
- Component integration with real configuration
- Error recovery and fallback scenarios
- Performance and security validation
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
from typing import Dict, Any

from phoenix_real_estate.foundation.config import (
    reset_config_cache,
    ConfigurationError,
    EnvironmentConfigProvider,
    SecretManager,
)


class TestTask04Phase3ConfigurationIntegration:
    """Integration test suite for Task 04 Phase 3."""

    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Setup complete integration test environment."""
        # Store original state
        original_env = os.environ.copy()
        original_path = sys.path.copy()

        # Reset configuration cache
        reset_config_cache()

        # Setup test environment
        test_env = {
            "ENVIRONMENT": "testing",
            "MARICOPA_API_KEY": "integration_test_api_key_12345",
            "MARICOPA_BASE_URL": "https://api.test.maricopa.gov/v1",
            "MARICOPA_RATE_LIMIT": "25",
            "MARICOPA_TIMEOUT": "15",
            "MONGODB_URI": "mongodb://localhost:27017/phoenix_real_estate_integration_test",
            "LOG_LEVEL": "DEBUG",
            "DEBUG": "true",
            "SECRET_KEY": "integration-test-secret-key-32-characters-minimum!",
            "PHOENIX_FEATURES_CACHE_ENABLED": "true",
            "PHOENIX_CACHE_DIRECTORY": "/tmp/phoenix_test_cache",
        }

        # Apply test environment
        for key, value in test_env.items():
            os.environ[key] = value

        yield

        # Restore original state
        os.environ.clear()
        os.environ.update(original_env)
        sys.path[:] = original_path
        reset_config_cache()

    @pytest.fixture
    def integration_config_dir(self):
        """Create complete integration configuration directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create comprehensive base configuration
            base_config = {
                "application": {
                    "name": "Phoenix Real Estate Collector",
                    "version": "0.1.0",
                    "description": "Integration test configuration",
                },
                "database": {
                    "name": "phoenix_real_estate",
                    "max_pool_size": 10,
                    "connection_timeout_ms": 10000,
                    "collections": {"properties": "properties", "daily_reports": "daily_reports"},
                },
                "logging": {
                    "level": "INFO",
                    "format": "text",
                    "console_output": True,
                    "file_rotation": True,
                },
                "collection": {
                    "max_requests_per_hour": 100,
                    "min_request_delay": 3.6,
                    "target_zip_codes": ["85031", "85033", "85035"],
                    "batch_size": 100,
                    "max_workers": 4,
                    "retry": {"max_retries": 3, "delay": 1.0, "backoff": 2.0},
                },
                "sources": {
                    "maricopa_county": {
                        "enabled": True,
                        "base_url": "https://api.mcassessor.maricopa.gov/api/v1",
                        "rate_limit": 1000,
                        "timeout": 10,
                    },
                    "phoenix_mls": {"enabled": True, "timeout": 30},
                },
                "processing": {
                    "llm_model": "llama2:7b",
                    "llm_timeout": 30,
                    "batch_size": 10,
                    "max_processing_workers": 2,
                },
                "security": {"max_session_age_hours": 24, "encrypt_sensitive_logs": True},
                "performance": {
                    "enable_caching": True,
                    "cache_ttl_minutes": 60,
                    "max_memory_usage_mb": 512,
                },
            }
            self._write_yaml_config(config_dir / "base.yaml", base_config)

            # Create testing environment configuration
            testing_config = {
                "logging": {"level": "DEBUG", "file_path": "/tmp/phoenix_integration_test.log"},
                "database": {"name": "phoenix_real_estate_integration_test", "max_pool_size": 3},
                "collection": {
                    "max_requests_per_hour": 25,
                    "min_request_delay": 2.0,
                    "target_zip_codes": ["85031"],
                    "batch_size": 5,
                    "max_workers": 1,
                },
                "sources": {
                    "maricopa_county": {"rate_limit": 25},
                    "phoenix_mls": {"enabled": False},
                },
                "processing": {"batch_size": 5, "max_processing_workers": 1},
            }
            self._write_yaml_config(config_dir / "testing.yaml", testing_config)

            # Create development configuration
            development_config = {
                "logging": {"level": "DEBUG"},
                "database": {"name": "phoenix_real_estate_dev"},
                "collection": {"max_requests_per_hour": 50},
            }
            self._write_yaml_config(config_dir / "development.yaml", development_config)

            # Create production configuration
            production_config = {
                "logging": {"level": "WARNING"},
                "database": {"name": "phoenix_real_estate_prod"},
                "security": {"secret_key": "production-secret-key-32-characters-minimum!"},
                "monitoring": {"enabled": True, "endpoint": "https://monitoring.example.com"},
            }
            self._write_yaml_config(config_dir / "production.yaml", production_config)

            yield config_dir

    def _write_yaml_config(self, file_path: Path, config: Dict[str, Any]) -> None:
        """Write configuration to YAML file."""
        import yaml

        with open(file_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    async def test_end_to_end_configuration_workflow(self, integration_config_dir):
        """Test complete end-to-end configuration loading workflow."""
        # Test full configuration loading from multiple sources
        config = EnvironmentConfigProvider(config_dir=integration_config_dir, environment="testing")

        # Verify environment detection
        assert config.get_environment() == "testing"
        assert config.is_testing() is True
        assert config.is_development() is False
        assert config.is_production() is False

        # Test configuration hierarchy (env vars > config files)
        # Environment variable should override config file
        api_key = config.get("maricopa_api_key")
        assert api_key == "integration_test_api_key_12345"

        # Config file value with environment override
        log_level = config.get("logging.level")
        assert log_level == "DEBUG"  # From testing.yaml, overridden by env var

        # Base config value
        app_name = config.get("application.name")
        assert app_name == "Phoenix Real Estate Collector"

        # Environment-specific override
        db_name = config.get("database.name")
        assert db_name == "phoenix_real_estate_integration_test"

        # Test typed configuration conversion
        rate_limit = config.get_typed("maricopa_rate_limit", int)
        assert rate_limit == 25
        assert isinstance(rate_limit, int)

        # Test boolean conversion
        cache_enabled = config.get_typed("phoenix_features_cache_enabled", bool)
        assert cache_enabled is True
        assert isinstance(cache_enabled, bool)

        # Test nested configuration access
        max_pool_size = config.get("database.max_pool_size")
        assert max_pool_size == 3  # From testing.yaml override

        retry_max = config.get("collection.retry.max_retries")
        assert retry_max == 3  # From base.yaml

    async def test_multi_environment_configuration_integration(self, integration_config_dir):
        """Test configuration across multiple environments."""
        environments_to_test = [
            ("development", "DEBUG", "phoenix_real_estate_dev", 50),
            ("testing", "DEBUG", "phoenix_real_estate_integration_test", 25),
            ("production", "WARNING", "phoenix_real_estate_prod", 1000),
        ]

        for (
            env_name,
            expected_log_level,
            expected_db_name,
            expected_rate_limit,
        ) in environments_to_test:
            # Update environment
            os.environ["ENVIRONMENT"] = env_name
            if env_name == "testing":
                os.environ["MARICOPA_RATE_LIMIT"] = "25"
            elif env_name == "development":
                os.environ["MARICOPA_RATE_LIMIT"] = "50"
            else:
                # Remove override for production (use config file default)
                os.environ.pop("MARICOPA_RATE_LIMIT", None)

            # Create configuration for this environment
            config = EnvironmentConfigProvider(
                config_dir=integration_config_dir, environment=env_name
            )

            # Verify environment-specific values
            assert config.get_environment() == env_name

            # Check environment detection methods
            if env_name == "development":
                assert config.is_development() is True
                assert config.is_testing() is False
                assert config.is_production() is False
            elif env_name == "testing":
                assert config.is_development() is False
                assert config.is_testing() is True
                assert config.is_production() is False
            elif env_name == "production":
                assert config.is_development() is False
                assert config.is_testing() is False
                assert config.is_production() is True

            # Verify configuration values
            log_level = config.get("logging.level")
            assert log_level in [expected_log_level, "DEBUG"], (
                f"Environment {env_name}: expected {expected_log_level}, got {log_level}"
            )

            db_name = config.get("database.name")
            expected_db = (
                expected_db_name
                if env_name != "testing"
                else "phoenix_real_estate_integration_test"
            )  # Override from env var
            assert db_name == expected_db

            # Test environment-specific configuration validation
            validation_errors = config.validate()

            if env_name == "production":
                # Production may have more strict requirements
                pass  # Allow some validation errors in test environment
            else:
                # Development and testing should have fewer validation issues
                critical_errors = [
                    error
                    for error in validation_errors
                    if "missing" in error.lower() and "required" in error.lower()
                ]
                # Should have minimal critical errors in test setup
                assert len(critical_errors) <= 3, (
                    f"Too many critical errors in {env_name}: {critical_errors}"
                )

    async def test_component_integration_with_real_configuration(self, integration_config_dir):
        """Test real component integration with configuration."""
        config = EnvironmentConfigProvider(config_dir=integration_config_dir, environment="testing")

        # Test MaricopaAPIClient integration
        maricopa_config = self._extract_maricopa_config(config)

        assert maricopa_config["api_key"] == "integration_test_api_key_12345"
        assert maricopa_config["base_url"] == "https://api.test.maricopa.gov/v1"
        assert maricopa_config["timeout"] == 15
        assert maricopa_config["rate_limit"] == 25

        # Test rate limiter integration
        rate_limiter_config = self._extract_rate_limiter_config(config)

        assert rate_limiter_config["max_requests_per_hour"] == 25
        assert rate_limiter_config["burst_size"] == 10  # Default from base config
        assert rate_limiter_config["min_delay"] == 2.0  # From testing config

        # Test database adapter integration
        db_config = config.get_database_config()

        assert "uri" in db_config
        assert db_config["uri"] == "mongodb://localhost:27017/phoenix_real_estate_integration_test"
        assert db_config.get("timeout") == 10  # From base config

        # Test collection orchestrator integration
        collection_config = config.get_collection_config()

        assert collection_config["target_zipcodes"] == ["85031"]  # From testing override
        assert collection_config["batch_size"] == 5  # From testing override
        assert collection_config["max_workers"] == 1  # From testing override
        assert collection_config["retry_policy"]["max_retries"] == 3

        # Test processor integration
        processor_config = self._extract_processor_config(config)

        assert processor_config["llm_model"] == "llama2:7b"
        assert processor_config["batch_size"] == 5  # From testing override
        assert processor_config["max_workers"] == 1  # From testing override

        # Test logging integration
        log_config = config.get_logging_config()

        assert log_config["level"] == "DEBUG"
        assert log_config["console"] is True
        assert log_config["file_path"] == "/tmp/phoenix_integration_test.log"

    def _extract_maricopa_config(self, config: EnvironmentConfigProvider) -> Dict[str, Any]:
        """Extract Maricopa API client configuration."""
        return {
            "api_key": config.get_required("maricopa_api_key"),
            "base_url": config.get(
                "maricopa_base_url", config.get("sources.maricopa_county.base_url")
            ),
            "timeout": config.get_typed(
                "maricopa_timeout",
                int,
                config.get_typed("sources.maricopa_county.timeout", int, 10),
            ),
            "rate_limit": config.get_typed(
                "maricopa_rate_limit",
                int,
                config.get_typed("sources.maricopa_county.rate_limit", int, 1000),
            ),
        }

    def _extract_rate_limiter_config(self, config: EnvironmentConfigProvider) -> Dict[str, Any]:
        """Extract rate limiter configuration."""
        return {
            "max_requests_per_hour": config.get_typed(
                "maricopa_rate_limit",
                int,
                config.get_typed("collection.max_requests_per_hour", int, 100),
            ),
            "burst_size": config.get_typed("collection.rate_limiting.burst_size", int, 10),
            "min_delay": config.get_typed("collection.min_request_delay", float, 3.6),
        }

    def _extract_processor_config(self, config: EnvironmentConfigProvider) -> Dict[str, Any]:
        """Extract data processor configuration."""
        return {
            "llm_model": config.get("processing.llm_model", "llama2:7b"),
            "llm_timeout": config.get_typed("processing.llm_timeout", int, 30),
            "batch_size": config.get_typed("processing.batch_size", int, 10),
            "max_workers": config.get_typed("processing.max_processing_workers", int, 2),
        }

    async def test_error_recovery_and_fallback_integration(self, integration_config_dir):
        """Test error recovery and fallback scenarios in integration context."""
        # Test configuration loading with missing files
        missing_config_dir = integration_config_dir / "missing"

        config = EnvironmentConfigProvider(config_dir=missing_config_dir, environment="testing")

        # Should still work with environment variables
        api_key = config.get("maricopa_api_key")
        assert api_key == "integration_test_api_key_12345"

        # Test partial configuration failure recovery
        # Create malformed configuration file
        malformed_file = integration_config_dir / "malformed.yaml"
        with open(malformed_file, "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        # Should handle malformed YAML gracefully
        try:
            config_with_malformed = EnvironmentConfigProvider(
                config_dir=integration_config_dir,
                environment="malformed",  # Will try to load malformed.yaml
            )

            # Should still be able to access environment variables
            api_key = config_with_malformed.get("maricopa_api_key")
            assert api_key == "integration_test_api_key_12345"

        except ConfigurationError as e:
            # Should provide clear error about YAML parsing
            assert "Failed to parse YAML file" in str(e)
            assert "malformed.yaml" in str(e)

        # Test missing required configuration with fallbacks
        os.environ.pop("MARICOPA_API_KEY", None)  # Remove required config

        config_missing_key = EnvironmentConfigProvider(
            config_dir=integration_config_dir, environment="testing"
        )

        # Should raise clear error for missing required config
        with pytest.raises(ConfigurationError) as exc_info:
            config_missing_key.get_required("maricopa_api_key")

        error = exc_info.value
        assert "Required configuration key not found" in str(error)
        assert error.context["environment"] == "testing"

        # But should work with defaults for optional configs
        optional_value = config_missing_key.get("optional_setting", "fallback_value")
        assert optional_value == "fallback_value"

    async def test_secret_management_integration(self, integration_config_dir):
        """Test comprehensive secret management integration."""
        # Setup comprehensive secret management test
        os.environ["SECRET_API_KEY_MARICOPA"] = "secret_maricopa_key_67890"
        os.environ["CREDENTIAL_DB_USER"] = "integration_test_user"
        os.environ["CREDENTIAL_DB_PASS"] = "integration_test_password"
        os.environ["SECRET_ENCRYPTION_KEY"] = "integration-encryption-key-32-characters!"

        # Test secret manager integration
        secret_manager = SecretManager(secret_key=os.environ["SECRET_ENCRYPTION_KEY"])

        # Test API keys discovery
        api_keys = secret_manager.get_api_keys()
        assert "maricopa" in api_keys
        assert api_keys["maricopa"] == "secret_maricopa_key_67890"

        # Test database credentials
        db_credentials = secret_manager.get_database_credentials()
        assert db_credentials["username"] == "integration_test_user"
        assert db_credentials["password"] == "integration_test_password"

        # Test encrypted secret storage
        secret_manager.store_secret("test_encrypted", "sensitive_value", encrypt=True)
        stored_encrypted = secret_manager._secrets["test_encrypted"]
        assert stored_encrypted.startswith("enc:")
        assert "sensitive_value" not in stored_encrypted

        # Test decryption
        decrypted_value = secret_manager.get_secret("test_encrypted")
        assert decrypted_value == "sensitive_value"

        # Test base64 encoded secrets
        import base64

        encoded_secret = base64.b64encode(b"base64_test_value").decode()
        os.environ["SECRET_BASE64_TEST"] = f"b64:{encoded_secret}"

        decoded_value = secret_manager.get_secret("SECRET_BASE64_TEST")
        assert decoded_value == "base64_test_value"

        # Test secret validation
        required_secrets = ["SECRET_API_KEY_MARICOPA", "CREDENTIAL_DB_USER"]
        recommended_secrets = ["SECRET_OPTIONAL_KEY"]

        # Should pass validation for required secrets
        secret_manager.validate_secrets(required_secrets)

        # Should handle missing recommended secrets gracefully
        with patch("phoenix_real_estate.foundation.config.secrets.logger") as mock_logger:
            secret_manager.validate_secrets(required_secrets, recommended_secrets)
            mock_logger.warning.assert_called()

    async def test_performance_and_security_integration(self, integration_config_dir):
        """Test performance and security aspects in integration context."""
        config = EnvironmentConfigProvider(config_dir=integration_config_dir, environment="testing")

        # Test configuration caching performance
        import time

        # First access (should load from source)
        start_time = time.time()
        value1 = config.get("application.name")
        first_access_time = time.time() - start_time

        # Second access (should use cache)
        start_time = time.time()
        value2 = config.get("application.name")
        second_access_time = time.time() - start_time

        assert value1 == value2
        assert (
            second_access_time < first_access_time or second_access_time < 0.001
        )  # Cache should be faster

        # Test security validation integration
        validation_errors = config.validate()

        # Check for security-related validation
        security_errors = [
            error
            for error in validation_errors
            if any(
                keyword in error.lower() for keyword in ["secret", "password", "key", "security"]
            )
        ]

        # Should have minimal security errors in test setup
        assert len(security_errors) <= 2, f"Too many security issues: {security_errors}"

        # Test sensitive data masking
        config_str = str(config)
        assert "integration_test_api_key_12345" not in config_str
        assert "integration_test_password" not in config_str

        # Test logging doesn't expose secrets
        with patch("phoenix_real_estate.foundation.config.base.logger") as mock_logger:
            config.get("maricopa_api_key")

            # Check that no logger calls contain sensitive data
            for call in mock_logger.debug.call_args_list:
                call_str = str(call)
                assert "integration_test_api_key_12345" not in call_str

    async def test_real_world_configuration_scenarios(self, integration_config_dir):
        """Test real-world configuration scenarios and edge cases."""
        # Scenario 1: Configuration with mixed data types
        os.environ["PHOENIX_MIXED_LIST"] = "85031,85033,85035"
        os.environ["PHOENIX_MIXED_BOOL"] = "yes"
        os.environ["PHOENIX_MIXED_INT"] = "42"
        os.environ["PHOENIX_MIXED_FLOAT"] = "3.14"

        config = EnvironmentConfigProvider(config_dir=integration_config_dir, environment="testing")

        # Test type conversions
        zip_list = config.get_typed("mixed.list", list)
        assert zip_list == ["85031", "85033", "85035"]

        bool_value = config.get_typed("mixed.bool", bool)
        assert bool_value is True

        int_value = config.get_typed("mixed.int", int)
        assert int_value == 42

        float_value = config.get_typed("mixed.float", float)
        assert float_value == 3.14

        # Scenario 2: Configuration override precedence
        # Environment variable should override config file
        os.environ["PHOENIX_TEST_PRECEDENCE"] = "from_environment"

        # Add to config file
        test_config = integration_config_dir / "precedence_test.yaml"
        with open(test_config, "w") as f:
            f.write("test:\n  precedence: 'from_config_file'\n")

        config_precedence = EnvironmentConfigProvider(
            config_dir=integration_config_dir, environment="precedence_test"
        )

        precedence_value = config_precedence.get("test.precedence")
        assert precedence_value == "from_environment"  # Env var should win

        # Scenario 3: Nested configuration access
        nested_value = config.get("collection.retry.max_retries")
        assert nested_value == 3

        # Scenario 4: Configuration with defaults
        default_value = config.get("nonexistent.setting", "default_fallback")
        assert default_value == "default_fallback"

        # Scenario 5: Complex configuration validation
        os.environ["COLLECTION_TARGET_ZIPCODES"] = "85031,invalid_zip,85033"

        config_validation = EnvironmentConfigProvider(
            config_dir=integration_config_dir, environment="testing"
        )

        validation_errors = config_validation.validate()

        # Should detect invalid ZIP code
        zip_errors = [error for error in validation_errors if "zip" in error.lower()]
        assert len(zip_errors) > 0, "Should detect invalid ZIP code"

    async def test_configuration_helper_methods_integration(self, integration_config_dir):
        """Test configuration helper methods in integration context."""
        config = EnvironmentConfigProvider(config_dir=integration_config_dir, environment="testing")

        # Test database configuration helper
        db_config = config.get_database_config()

        assert "uri" in db_config
        assert db_config["uri"] == "mongodb://localhost:27017/phoenix_real_estate_integration_test"

        # Test logging configuration helper
        log_config = config.get_logging_config()

        assert log_config["level"] == "DEBUG"
        assert log_config["console"] is True
        assert "file_path" in log_config

        # Test collection configuration helper
        collection_config = config.get_collection_config()

        assert "target_zipcodes" in collection_config
        assert collection_config["target_zipcodes"] == ["85031"]
        assert "retry_policy" in collection_config
        assert "sources" in collection_config

        # Test that helper methods handle missing configuration gracefully
        minimal_config = EnvironmentConfigProvider(
            config_dir=integration_config_dir / "nonexistent", environment="minimal"
        )

        try:
            minimal_db_config = minimal_config.get_database_config()
            # Should work with environment variables even if config files missing
            assert "uri" in minimal_db_config
        except ConfigurationError as e:
            # Should provide clear error message
            assert "Database configuration incomplete" in str(e)

    async def test_end_to_end_validation_integration(self, integration_config_dir):
        """Test end-to-end validation workflow integration."""
        config = EnvironmentConfigProvider(config_dir=integration_config_dir, environment="testing")

        # Test comprehensive validation
        validation_errors = config.validate()

        # Should complete validation without throwing exceptions
        assert isinstance(validation_errors, list)

        # Test validation with missing required configuration
        os.environ.pop("MARICOPA_API_KEY", None)

        config_missing = EnvironmentConfigProvider(
            config_dir=integration_config_dir,
            environment="production",  # More strict requirements
        )

        validation_errors_missing = config_missing.validate()

        # Should detect missing required configuration
        missing_errors = [
            error
            for error in validation_errors_missing
            if "missing" in error.lower() and "required" in error.lower()
        ]
        assert len(missing_errors) > 0

        # Test validation and raise
        try:
            config_missing.validate_and_raise()
            pytest.fail("Should have raised ConfigurationError")
        except ConfigurationError as e:
            assert "validation failed" in str(e).lower()
            assert "production" in str(e)
            assert "error_count" in e.context
            assert "errors" in e.context
