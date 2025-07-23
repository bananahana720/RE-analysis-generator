"""Integration tests for configuration management system."""

import os
import tempfile
from pathlib import Path
import pytest
import yaml
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

from phoenix_real_estate.foundation.config import (
    EnvironmentConfigProvider,
    EnvironmentFactory,
    get_config,
    reset_config_cache,
    SecretManager,
    get_secret_manager,
    get_secret,
    get_required_secret,
)
from phoenix_real_estate.foundation.utils.exceptions import ConfigurationError


class TestConfigurationIntegration:
    """Test integration between configuration components."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset configuration cache before each test."""
        reset_config_cache()
        yield
        reset_config_cache()

    @pytest.fixture
    def full_config_setup(self):
        """Create a full configuration setup with all files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Base configuration
            base_config = {
                "application": {"name": "Phoenix Real Estate", "version": "1.0.0"},
                "database": {"name": "phoenix_real_estate", "max_pool_size": 10},
                "logging": {"level": "INFO", "format": "text"},
                "collection": {
                    "max_requests_per_hour": 100,
                    "target_zip_codes": ["85031", "85033"],
                },
            }

            # Development configuration
            dev_config = {
                "logging": {"level": "DEBUG"},
                "database": {"name": "phoenix_real_estate_dev"},
            }

            # Testing configuration
            test_config = {
                "logging": {"level": "DEBUG", "console_output": False},
                "database": {"name": "phoenix_real_estate_test"},
                "collection": {"max_requests_per_hour": 10},
            }

            # Production configuration
            prod_config = {
                "logging": {"level": "WARNING", "format": "json"},
                "database": {"max_pool_size": 20},
                "security": {"encrypt_logs": True},
            }

            # Write configuration files
            with open(config_dir / "base.yaml", "w") as f:
                yaml.dump(base_config, f)
            with open(config_dir / "development.yaml", "w") as f:
                yaml.dump(dev_config, f)
            with open(config_dir / "testing.yaml", "w") as f:
                yaml.dump(test_config, f)
            with open(config_dir / "production.yaml", "w") as f:
                yaml.dump(prod_config, f)

            # Create .env files
            env_file = Path(tmpdir) / ".env"
            with open(env_file, "w") as f:
                f.write("# Base environment file\n")
                f.write("API_KEY=base_api_key\n")
                f.write("DATABASE_URL=postgres://base\n")

            env_local = Path(tmpdir) / ".env.local"
            with open(env_local, "w") as f:
                f.write("# Local overrides\n")
                f.write("API_KEY=local_api_key\n")
                f.write("DEBUG=true\n")

            yield {
                "tmpdir": tmpdir,
                "config_dir": config_dir,
                "env_file": env_file,
                "env_local": env_local,
            }

    def test_full_configuration_lifecycle(self, full_config_setup):
        """Test complete configuration loading and access."""
        tmpdir = full_config_setup["tmpdir"]
        config_dir = full_config_setup["config_dir"]

        # Test development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            os.chdir(tmpdir)  # Change to temp directory for .env loading
            config = EnvironmentFactory.create_config(config_dir=config_dir)

            assert config.get_environment() == "development"
            assert config.get("logging.level") == "DEBUG"
            assert config.get("database.name") == "phoenix_real_estate_dev"
            assert config.get("collection.max_requests_per_hour") == 100

            # Check .env loading
            assert config.get("api.key") == "local_api_key"  # .env.local overrides .env
            assert config.get_typed("debug", bool) is True

    def test_environment_switching(self, full_config_setup):
        """Test switching between environments."""
        config_dir = full_config_setup["config_dir"]

        # Development
        dev_config = EnvironmentFactory.create_development_config(config_dir)
        assert dev_config.get("logging.level") == "DEBUG"
        assert dev_config.get("database.name") == "phoenix_real_estate_dev"

        # Testing
        test_config = EnvironmentFactory.create_testing_config(config_dir)
        assert test_config.get("logging.level") == "DEBUG"
        assert test_config.get("database.name") == "phoenix_real_estate_test"
        assert test_config.get("collection.max_requests_per_hour") == 10

        # Production
        prod_config = EnvironmentFactory.create_production_config(config_dir)
        assert prod_config.get("logging.level") == "WARNING"
        assert prod_config.get("logging.format") == "json"
        assert prod_config.get("database.max_pool_size") == 20
        assert prod_config.get_typed("security.encrypt_logs", bool) is True

    def test_secret_manager_integration(self, full_config_setup):
        """Test secret manager with configuration."""
        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "my_secret_key",
                "MONGODB_URI": "mongodb://user:pass@host:27017/db",
                "WEBSHARE_USERNAME": "proxy_user",
                "WEBSHARE_PASSWORD": "proxy_pass",
                "SECRET_API_KEY": "secret_api_123",
                "CREDENTIAL_OAUTH_TOKEN": "oauth_token_456",
            },
        ):
            secret_manager = SecretManager()

            # Test direct secret access
            assert secret_manager.get_secret("SECRET_KEY") == "my_secret_key"
            assert secret_manager.get_secret("MONGODB_URI") == "mongodb://user:pass@host:27017/db"

            # Test prefix detection
            assert secret_manager.get_secret("API_KEY") == "secret_api_123"
            assert secret_manager.get_secret("OAUTH_TOKEN") == "oauth_token_456"

            # Test credential helpers
            db_creds = secret_manager.get_database_credentials()
            assert db_creds["uri"] == "mongodb://user:pass@host:27017/db"

            proxy_creds = secret_manager.get_proxy_credentials()
            assert proxy_creds["username"] == "proxy_user"
            assert proxy_creds["password"] == "proxy_pass"

    def test_configuration_validation_integration(self, full_config_setup):
        """Test validation across environments."""
        config_dir = full_config_setup["config_dir"]

        # Test with missing required values
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            config = EnvironmentConfigProvider(
                config_dir=config_dir, environment="production", load_dotenv=False
            )

            # List-based validation
            errors = config.validate()
            assert isinstance(errors, list)
            assert any("database.uri" in error for error in errors)

    def test_environment_variable_precedence(self, full_config_setup):
        """Test that environment variables override all other sources."""
        config_dir = full_config_setup["config_dir"]

        with patch.dict(
            os.environ,
            {
                "PHOENIX_DATABASE_NAME": "env_override_db",
                "MONGODB_DATABASE": "direct_override_db",
                "LOG_LEVEL": "ERROR",
                "PHOENIX_LOGGING_LEVEL": "CRITICAL",
            },
        ):
            config = EnvironmentConfigProvider(
                config_dir=config_dir, environment="development", load_dotenv=False
            )

            # Direct mapping takes precedence over PHOENIX_ prefix
            assert config.get("database.name") == "direct_override_db"
            # PHOENIX_ prefix takes precedence over config files
            assert config.get("logging.level") == "CRITICAL"

    def test_global_config_singleton(self, full_config_setup):
        """Test global configuration singleton behavior."""
        config_dir = full_config_setup["config_dir"]

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Patch the default config directory
            import phoenix_real_estate.foundation.config.environment as env_module

            original_create = env_module.EnvironmentFactory.create_config

            def patched_create(environment=None, config_dir=None, env_file=None):
                return original_create(
                    environment=environment,
                    config_dir=config_dir or full_config_setup["config_dir"],
                    env_file=env_file,
                )

            with patch.object(env_module.EnvironmentFactory, "create_config", patched_create):
                # First call creates instance
                config1 = get_config("development")
                # Second call returns same instance
                config2 = get_config("development")

                assert config1 is config2

                # Different environment creates new instance
                config3 = get_config("testing")
                assert config3 is not config1

    def test_thread_safety(self, full_config_setup):
        """Test thread-safe configuration access."""
        config_dir = full_config_setup["config_dir"]
        results = {}

        def load_config(env_name):
            """Load configuration in a thread."""
            config = get_config(env_name)
            return (env_name, id(config), config.get_environment())

        # Patch the config directory for all threads
        import phoenix_real_estate.foundation.config.environment as env_module

        original_create = env_module.EnvironmentFactory.create_config

        def patched_create(environment=None, config_dir=None, env_file=None):
            return original_create(
                environment=environment,
                config_dir=config_dir or full_config_setup["config_dir"],
                env_file=env_file,
            )

        with patch.object(env_module.EnvironmentFactory, "create_config", patched_create):
            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit multiple requests for same environment
                futures = []
                for i in range(10):
                    env = "development" if i < 5 else "testing"
                    future = executor.submit(load_config, env)
                    futures.append(future)

                # Collect results
                for future in as_completed(futures):
                    env_name, config_id, actual_env = future.result()
                    if env_name not in results:
                        results[env_name] = set()
                    results[env_name].add(config_id)
                    assert actual_env == env_name

            # Verify singleton behavior - same ID for same environment
            assert len(results["development"]) == 1
            assert len(results["testing"]) == 1

    def test_performance_requirements(self, full_config_setup):
        """Test that configuration loads within performance requirements."""
        config_dir = full_config_setup["config_dir"]

        # Measure configuration load time
        start_time = time.perf_counter()
        config = EnvironmentConfigProvider(
            config_dir=config_dir, environment="production", load_dotenv=False
        )
        load_time = time.perf_counter() - start_time

        # Should load in under 100ms
        assert load_time < 0.1, f"Configuration load took {load_time:.3f}s"

        # Measure validation time
        start_time = time.perf_counter()
        errors = config.validate()
        validation_time = time.perf_counter() - start_time

        # Should validate in under 50ms
        assert validation_time < 0.05, f"Validation took {validation_time:.3f}s"

    def test_encryption_integration(self, full_config_setup):
        """Test secret encryption/decryption."""
        secret_manager = SecretManager(secret_key="test_key_123")

        # Test storing and retrieving encrypted secret
        stored = secret_manager.store_secret("test_secret", "sensitive_value", encrypt=True)
        assert stored.startswith("enc:")
        assert "sensitive_value" not in stored

        # Simulate loading from environment
        with patch.dict(os.environ, {"TEST_SECRET": stored}):
            retrieved = secret_manager.get_secret("TEST_SECRET")
            assert retrieved == "sensitive_value"

    def test_configuration_error_handling(self, full_config_setup):
        """Test comprehensive error handling."""
        config_dir = full_config_setup["config_dir"]

        # Test with corrupted YAML
        bad_yaml = config_dir / "bad.yaml"
        with open(bad_yaml, "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        with pytest.raises(ConfigurationError) as exc_info:
            EnvironmentConfigProvider(config_dir=config_dir, environment="bad", load_dotenv=False)

        assert "Failed to parse YAML" in str(exc_info.value)

    def test_convenience_functions(self, full_config_setup):
        """Test module-level convenience functions."""
        with patch.dict(os.environ, {"SECRET_API_TOKEN": "token123", "PUBLIC_KEY": "not_a_secret"}):
            # Test get_secret
            assert get_secret("API_TOKEN") == "token123"
            assert get_secret("MISSING_SECRET", "default") == "default"

            # Test get_required_secret
            assert get_required_secret("API_TOKEN") == "token123"

            from phoenix_real_estate.foundation.config.secrets import SecretNotFoundError

            with pytest.raises(SecretNotFoundError):
                get_required_secret("MISSING_REQUIRED")


class TestProductionScenarios:
    """Test real-world production scenarios."""

    def test_mongodb_atlas_configuration(self):
        """Test MongoDB Atlas connection string handling."""
        with patch.dict(
            os.environ,
            {
                "MONGODB_URI": "mongodb+srv://user:pass@cluster.mongodb.net/db?retryWrites=true",
                "ENVIRONMENT": "production",
            },
        ):
            config = get_config("production")
            db_config = config.get_database_config()

            assert "mongodb+srv://" in db_config["uri"]
            assert "retryWrites=true" in db_config["uri"]

    def test_github_actions_environment(self):
        """Test configuration in GitHub Actions environment."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_ACTIONS": "true",
                "ENVIRONMENT": "testing",
                "MONGODB_URI": "mongodb://localhost:27017/test",
                "SECRET_KEY": "${{ secrets.SECRET_KEY }}",  # Simulated GitHub secret
            },
            clear=True,
        ):
            config = get_config("testing")
            assert config.get_environment() == "testing"

            # Secrets should be loaded
            secret_manager = get_secret_manager()
            assert secret_manager.get_secret("MONGODB_URI") == "mongodb://localhost:27017/test"

    def test_docker_environment(self):
        """Test configuration in Docker container."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "MONGODB_URI": "mongodb://mongo:27017/phoenix",
                "LOG_LEVEL": "INFO",
                "PHOENIX_CACHE_ENABLED": "true",
            },
        ):
            config = get_config("production")

            # Docker typically uses service names as hostnames
            assert "mongo:27017" in config.get_required("database.uri")
            assert config.get_typed("cache.enabled", bool) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
