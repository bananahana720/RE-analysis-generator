"""Tests for base configuration provider implementation."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
import yaml

from phoenix_real_estate.foundation.config.base import (
    ConfigProvider,
    EnvironmentConfigProvider,
)
from phoenix_real_estate.foundation.utils.exceptions import ConfigurationError


class TestConfigProviderAbstractClass:
    """Test the ConfigProvider abstract base class."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that ConfigProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ConfigProvider()
    
    def test_interface_methods_required(self):
        """Test that subclasses must implement all required methods."""
        class IncompleteProvider(ConfigProvider):
            pass
        
        with pytest.raises(TypeError):
            IncompleteProvider()


class TestEnvironmentConfigProvider:
    """Test the EnvironmentConfigProvider implementation."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def base_config(self, temp_config_dir):
        """Create a base configuration file."""
        config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "phoenix_re"
            },
            "api": {
                "timeout": 30,
                "retries": 3
            },
            "features": {
                "cache_enabled": True,
                "debug": False
            }
        }
        
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        return config
    
    @pytest.fixture
    def dev_config(self, temp_config_dir):
        """Create a development environment configuration file."""
        config = {
            "database": {
                "host": "dev.localhost",
                "name": "phoenix_re_dev"
            },
            "features": {
                "debug": True
            }
        }
        
        config_file = temp_config_dir / "development.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        return config
    
    def test_load_base_config_only(self, temp_config_dir, base_config):
        """Test loading only base configuration."""
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="production",
            load_dotenv=False
        )
        
        assert provider.get("database.host") == "localhost"
        assert provider.get("database.port") == 5432
        assert provider.get("api.timeout") == 30
    
    def test_environment_override(self, temp_config_dir, base_config, dev_config):
        """Test environment-specific config overrides base config."""
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="development",
            load_dotenv=False
        )
        
        # Development overrides
        assert provider.get("database.host") == "dev.localhost"
        assert provider.get("database.name") == "phoenix_re_dev"
        assert provider.get("features.debug") is True
        
        # Base values still present
        assert provider.get("database.port") == 5432
        assert provider.get("api.timeout") == 30
    
    def test_environment_variable_override(self, temp_config_dir, base_config):
        """Test environment variables override config files."""
        with patch.dict(os.environ, {
            "PHOENIX_DATABASE_HOST": "env.localhost",
            "PHOENIX_DATABASE_PORT": "3306",
            "PHOENIX_API_TIMEOUT": "60"
        }):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                environment="development",
                load_dotenv=False
            )
            
            assert provider.get("database.host") == "env.localhost"
            assert provider.get("database.port") == "3306"
            assert provider.get("api.timeout") == "60"
    
    def test_get_with_default(self, temp_config_dir, base_config):
        """Test get() with default value."""
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        assert provider.get("missing.key") is None
        assert provider.get("missing.key", "default") == "default"
        assert provider.get("database.host", "default") == "localhost"
    
    def test_get_required_success(self, temp_config_dir, base_config):
        """Test get_required() with existing key."""
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        assert provider.get_required("database.host") == "localhost"
    
    def test_get_required_missing_key(self, temp_config_dir, base_config):
        """Test get_required() raises error for missing key."""
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            provider.get_required("missing.required.key")
        
        assert "Required configuration key not found" in str(exc_info.value)
        assert "missing.required.key" in str(exc_info.value)
    
    def test_get_typed_conversions(self, temp_config_dir, base_config):
        """Test get_typed() type conversions."""
        with patch.dict(os.environ, {
            "PHOENIX_TEST_BOOL_TRUE": "true",
            "PHOENIX_TEST_BOOL_FALSE": "false",
            "PHOENIX_TEST_INT": "42",
            "PHOENIX_TEST_FLOAT": "3.14",
            "PHOENIX_TEST_LIST": "item1,item2,item3"
        }):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            # Test boolean conversions
            assert provider.get_typed("test.bool.true", bool) is True
            assert provider.get_typed("test.bool.false", bool) is False
            
            # Test numeric conversions
            assert provider.get_typed("test.int", int) == 42
            assert provider.get_typed("test.float", float) == 3.14
            
            # Test list conversion
            assert provider.get_typed("test.list", list) == ["item1", "item2", "item3"]
            
            # Test with defaults
            assert provider.get_typed("missing", int, 100) == 100
            assert provider.get_typed("missing", bool, True) is True
    
    def test_boolean_string_conversions(self, temp_config_dir, base_config):
        """Test various boolean string conversions."""
        bool_values = {
            "PHOENIX_BOOL_TRUE1": "true",
            "PHOENIX_BOOL_TRUE2": "yes",
            "PHOENIX_BOOL_TRUE3": "1",
            "PHOENIX_BOOL_TRUE4": "on",
            "PHOENIX_BOOL_FALSE1": "false",
            "PHOENIX_BOOL_FALSE2": "no",
            "PHOENIX_BOOL_FALSE3": "0",
            "PHOENIX_BOOL_FALSE4": "off",
        }
        
        with patch.dict(os.environ, bool_values):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            # True values
            assert provider.get_typed("bool.true1", bool) is True
            assert provider.get_typed("bool.true2", bool) is True
            assert provider.get_typed("bool.true3", bool) is True
            assert provider.get_typed("bool.true4", bool) is True
            
            # False values
            assert provider.get_typed("bool.false1", bool) is False
            assert provider.get_typed("bool.false2", bool) is False
            assert provider.get_typed("bool.false3", bool) is False
            assert provider.get_typed("bool.false4", bool) is False
    
    def test_invalid_type_conversion(self, temp_config_dir, base_config):
        """Test get_typed() raises error for invalid conversions."""
        with patch.dict(os.environ, {"PHOENIX_INVALID_INT": "not_a_number"}):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            with pytest.raises(ConfigurationError) as exc_info:
                provider.get_typed("invalid.int", int)
            
            assert "Cannot convert 'not_a_number' to int" in str(exc_info.value)
    
    def test_get_environment(self, temp_config_dir, base_config):
        """Test get_environment() returns correct environment."""
        # Default environment
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        assert provider.get_environment() == "development"
        
        # Explicit environment
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="production",
            load_dotenv=False
        )
        assert provider.get_environment() == "production"
        
        # Environment from env var
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            assert provider.get_environment() == "staging"
    
    def test_validate_production_requirements(self, temp_config_dir):
        """Test validation enforces production requirements."""
        # Create minimal production config
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"},
            "api": {"key": "secret"},
            "security": {"secret_key": "a" * 32},  # 32 chars for production
            "monitoring": {"enabled": True, "endpoint": "http://monitor.example.com"}
        }
        
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="production",
            load_dotenv=False
        )
        
        # Should not raise
        provider.validate_and_raise()
    
    def test_validate_missing_production_keys(self, temp_config_dir, base_config):
        """Test validation fails for missing production keys."""
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="production",
            load_dotenv=False
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            provider.validate_and_raise()
        
        assert "Required configuration keys missing" in str(exc_info.value)
        assert "production" in str(exc_info.value)
    
    def test_validate_invalid_zipcode(self, temp_config_dir):
        """Test validation fails for invalid ZIP codes."""
        config = {
            "collection": {
                "target_zipcodes": ["85001", "12345", "invalid", "85032-1234"]
            }
        }
        
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            provider.validate_and_raise()
        
        assert "Invalid ZIP codes" in str(exc_info.value)
        # The error context structure has changed in the enhanced version
        assert "invalid" in str(exc_info.value)
    
    def test_validate_invalid_port(self, temp_config_dir):
        """Test validation fails for invalid port number."""
        config = {
            "database": {
                "port": 99999  # Invalid port
            }
        }
        
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            provider.validate_and_raise()
        
        # Check for port validation error message in new format
        error_str = str(exc_info.value)
        assert "Port number out of valid range" in error_str or "Invalid port number" in error_str
        # The context structure has changed in the enhanced version
        assert "99999" in error_str
    
    def test_caching_behavior(self, temp_config_dir, base_config):
        """Test configuration values are cached."""
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        # First access
        value1 = provider.get("database.host")
        
        # Modify the underlying config (simulating external change)
        provider.config["database"]["host"] = "modified"
        
        # Second access should return cached value
        value2 = provider.get("database.host")
        
        assert value1 == value2 == "localhost"
        assert provider._cache["database.host"] == "localhost"
    
    def test_nested_config_access(self, temp_config_dir):
        """Test deeply nested configuration access."""
        config = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep_value"
                        }
                    }
                }
            }
        }
        
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        assert provider.get("level1.level2.level3.level4.value") == "deep_value"
    
    def test_yaml_parse_error(self, temp_config_dir):
        """Test handling of invalid YAML files."""
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(ConfigurationError) as exc_info:
            EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
        
        # The error is wrapped, so check the outer error message
        assert "Failed to load configuration" in str(exc_info.value)
        # Check that the original error is preserved
        assert exc_info.value.original_error is not None
    
    def test_missing_config_directory(self):
        """Test handling of missing configuration directory."""
        provider = EnvironmentConfigProvider(
            config_dir="/nonexistent/directory",
            load_dotenv=False
        )
        
        # Should not fail - just no config loaded
        assert provider.get("any.key") is None