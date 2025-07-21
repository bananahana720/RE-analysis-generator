"""Tests for enhanced validation and type conversion in configuration provider."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
import yaml
import json

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import ConfigurationError


class TestEnhancedTypeConversion:
    """Test enhanced type conversion with edge cases."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def minimal_config(self, temp_config_dir):
        """Create minimal configuration for testing."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"}
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        return config
    
    def test_empty_string_conversions(self, temp_config_dir, minimal_config):
        """Test handling of empty strings in type conversion."""
        with patch.dict(os.environ, {
            "PHOENIX_EMPTY_STR": "",
            "PHOENIX_SPACE_STR": "   ",
            "PHOENIX_EMPTY_LIST": ""
        }):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            # Empty string to int should fail
            with pytest.raises(ConfigurationError) as exc_info:
                provider.get_typed("empty.str", int)
            assert "empty string" in str(exc_info.value).lower()
            
            # Empty string to float should fail
            with pytest.raises(ConfigurationError) as exc_info:
                provider.get_typed("space.str", float)
            assert "empty string" in str(exc_info.value).lower()
            
            # Empty string to list should return empty list
            assert provider.get_typed("empty.list", list) == []
            
            # Empty string to bool should return False
            assert provider.get_typed("empty.str", bool) is False
    
    def test_enhanced_boolean_conversions(self, temp_config_dir, minimal_config):
        """Test extended boolean string conversions."""
        bool_values = {
            # Extended true values
            "PHOENIX_BOOL_Y": "y",
            "PHOENIX_BOOL_Y_UPPER": "Y",
            "PHOENIX_BOOL_ENABLED": "enabled",
            "PHOENIX_BOOL_ENABLE": "enable",
            "PHOENIX_BOOL_ACTIVE": "active",
            # Extended false values
            "PHOENIX_BOOL_N": "n",
            "PHOENIX_BOOL_N_UPPER": "N",
            "PHOENIX_BOOL_DISABLED": "disabled",
            "PHOENIX_BOOL_DISABLE": "disable",
            "PHOENIX_BOOL_INACTIVE": "inactive",
            "PHOENIX_BOOL_EMPTY": "",
        }
        
        with patch.dict(os.environ, bool_values):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            # True values
            assert provider.get_typed("bool.y", bool) is True
            assert provider.get_typed("bool.y.upper", bool) is True
            assert provider.get_typed("bool.enabled", bool) is True
            assert provider.get_typed("bool.enable", bool) is True
            assert provider.get_typed("bool.active", bool) is True
            
            # False values
            # Debug: check what's actually happening
            val = provider.get("bool.n")
            print(f"Debug: provider.get('bool.n') = {repr(val)}")
            print(f"Debug: provider.config = {provider.config}")
            result = provider.get_typed("bool.n", bool)
            print(f"Debug: provider.get_typed('bool.n', bool) = {result}")
            assert result is False
            assert provider.get_typed("bool.n.upper", bool) is False
            assert provider.get_typed("bool.disabled", bool) is False
            assert provider.get_typed("bool.disable", bool) is False
            assert provider.get_typed("bool.inactive", bool) is False
            assert provider.get_typed("bool.empty", bool) is False
    
    def test_list_parsing_with_separators(self, temp_config_dir, minimal_config):
        """Test list parsing with different separators."""
        with patch.dict(os.environ, {
            "PHOENIX_LIST_COMMA": "item1,item2,item3",
            "PHOENIX_LIST_SEMICOLON": "item1;item2;item3",
            "PHOENIX_LIST_MIXED": "item1,sub1;item2,sub2;item3",
            "PHOENIX_LIST_SPACES": "  item1  ,  item2  ,  item3  ",
            "PHOENIX_LIST_EMPTY_ITEMS": "item1,,item2,,item3",
        }):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            # Comma-separated
            assert provider.get_typed("list.comma", list) == ["item1", "item2", "item3"]
            
            # Semicolon-separated
            assert provider.get_typed("list.semicolon", list) == ["item1", "item2", "item3"]
            
            # Mixed separators (prefer semicolon)
            assert provider.get_typed("list.mixed", list) == ["item1,sub1", "item2,sub2", "item3"]
            
            # With spaces
            assert provider.get_typed("list.spaces", list) == ["item1", "item2", "item3"]
            
            # Empty items filtered out
            assert provider.get_typed("list.empty.items", list) == ["item1", "item2", "item3"]
    
    def test_dict_parsing(self, temp_config_dir, minimal_config):
        """Test dictionary parsing from strings."""
        with patch.dict(os.environ, {
            "PHOENIX_DICT_JSON": '{"key1": "value1", "key2": 123}',
            "PHOENIX_DICT_PAIRS": "key1=value1,key2=value2,key3=value3",
            "PHOENIX_DICT_INVALID": "not a valid dict format"
        }):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            # JSON format
            json_dict = provider.get_typed("dict.json", dict)
            assert json_dict == {"key1": "value1", "key2": 123}
            
            # Key=value pairs
            pairs_dict = provider.get_typed("dict.pairs", dict)
            assert pairs_dict == {"key1": "value1", "key2": "value2", "key3": "value3"}
            
            # Invalid format
            with pytest.raises(ConfigurationError) as exc_info:
                provider.get_typed("dict.invalid", dict)
            assert "Cannot parse" in str(exc_info.value)
    
    def test_numeric_conversions(self, temp_config_dir, minimal_config):
        """Test numeric type conversions between int and float."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"},
            "numbers": {
                "int_value": 42,
                "float_value": 3.14,
                "large_int": 999999999999
            }
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        # Int to float
        assert provider.get_typed("numbers.int_value", float) == 42.0
        
        # Float to int
        assert provider.get_typed("numbers.float_value", int) == 3
        
        # Large numbers
        assert provider.get_typed("numbers.large_int", float) == 999999999999.0
    
    def test_list_to_string_conversion(self, temp_config_dir, minimal_config):
        """Test converting lists to strings."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"},
            "lists": {
                "items": ["apple", "banana", "cherry"],
                "numbers": [1, 2, 3]
            }
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        # List to string
        assert provider.get_typed("lists.items", str) == "apple, banana, cherry"
        assert provider.get_typed("lists.numbers", str) == "1, 2, 3"
    
    def test_error_context_with_key(self, temp_config_dir, minimal_config):
        """Test that conversion errors include key context."""
        with patch.dict(os.environ, {
            "PHOENIX_BAD_INT": "not_a_number",
            "PHOENIX_BAD_FLOAT": "not_a_float"
        }):
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            # Int conversion error should include key
            with pytest.raises(ConfigurationError) as exc_info:
                provider.get_typed("bad.int", int)
            assert "bad.int" in str(exc_info.value)
            assert exc_info.value.context.get("key") == "bad.int"
            
            # Float conversion error should include key
            with pytest.raises(ConfigurationError) as exc_info:
                provider.get_typed("bad.float", float)
            assert "bad.float" in str(exc_info.value)
            assert exc_info.value.context.get("key") == "bad.float"


class TestComprehensiveValidation:
    """Test comprehensive validation framework."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_validation_error_aggregation(self, temp_config_dir):
        """Test that validation collects all errors before reporting."""
        config = {
            # Missing required database.uri
            "logging": {"level": "INVALID_LEVEL"},  # Invalid log level
            "database": {"port": 99999},  # Invalid port
            "collection": {"target_zipcodes": ["85001", "invalid", "12345"]}  # Invalid ZIP
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
        
        # Check that multiple errors were collected
        context = exc_info.value.context
        assert context["error_count"] >= 4  # At least 4 errors
        errors = context["errors"]
        
        # Verify specific errors are present
        error_types = [e["type"] for e in errors]
        assert "missing_required_keys" in error_types
        assert "invalid_log_level" in error_types
        assert "invalid_range" in error_types
        assert "invalid_zipcodes" in error_types
    
    def test_production_specific_validation(self, temp_config_dir):
        """Test production environment specific validation."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"},
            "api": {"key": "test-key"},
            "monitoring": {"enabled": True},
            "security": {"secret_key": "short"},  # Too short for production
            "proxy": {
                "enabled": True,
                # Missing username and password
            }
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="production",
            load_dotenv=False
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            provider.validate_and_raise()
        
        errors = exc_info.value.context["errors"]
        error_types = [e["type"] for e in errors]
        
        # Should have weak secret key error
        assert "weak_secret_key" in error_types
        weak_key_error = next(e for e in errors if e["type"] == "weak_secret_key")
        assert weak_key_error["current_length"] == 5
        
        # Should have missing proxy auth error
        assert "missing_proxy_auth" in error_types
    
    def test_data_type_validation_with_conversion(self, temp_config_dir):
        """Test that type validation attempts conversion before failing."""
        config = {
            "database": {
                "uri": "mongodb://localhost",
                "port": "5432"  # String that can be converted to int
            },
            "logging": {"level": "INFO"},
            "api": {
                "timeout": "30.5",  # String that can be converted to float
                "retries": "not_a_number"  # Cannot be converted
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
        
        errors = exc_info.value.context["errors"]
        
        # Port and timeout should convert successfully (no errors)
        error_keys = [e.get("key") for e in errors if e.get("key")]
        assert "database.port" not in error_keys
        assert "api.timeout" not in error_keys
        
        # Retries should fail
        assert "api.retries" in error_keys
    
    def test_uri_format_validation(self, temp_config_dir):
        """Test database URI format validation."""
        config = {
            "database": {"uri": "invalid://localhost"},  # Invalid protocol
            "logging": {"level": "INFO"}
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
        
        errors = exc_info.value.context["errors"]
        uri_error = next(e for e in errors if e["type"] == "invalid_uri_format")
        assert "mongodb://" in str(uri_error["valid_protocols"])
    
    def test_custom_rule_validation(self, temp_config_dir):
        """Test custom business rule validation."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"},
            "features": {"cache_enabled": True},
            # Missing cache.directory when cache is enabled
            "monitoring": {"enabled": True},
            # Missing monitoring.endpoint
            "collection": {
                "schedule": "invalid cron"  # Invalid cron format
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
        
        errors = exc_info.value.context["errors"]
        error_types = [e["type"] for e in errors]
        
        # Should have dependency errors
        assert "missing_dependency" in error_types
        dep_errors = [e for e in errors if e["type"] == "missing_dependency"]
        assert len(dep_errors) == 2
        
        # Should have cron format error
        assert "invalid_format" in error_types
    
    def test_validation_error_summary_formatting(self, temp_config_dir):
        """Test validation error summary formatting."""
        config = {
            "database": {"port": 99999},
            "logging": {"level": "INVALID"},
            "collection": {"target_zipcodes": ["invalid1", "invalid2"]}
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
        
        summary = exc_info.value.context["summary"]
        
        # Check summary structure
        assert "validation error(s):" in summary
        assert "Missing Required Keys:" in summary
        assert "Invalid Range:" in summary
        assert "Invalid Log Level:" in summary
        assert "Invalid Zipcodes:" in summary


class TestConfigurationHelpers:
    """Test configuration helper methods."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_get_database_config_with_uri(self, temp_config_dir):
        """Test get_database_config with URI."""
        config = {
            "database": {
                "uri": "mongodb://user:pass@localhost:27017/mydb",
                "pool_size": 10,
                "timeout": 30,
                "options": {"ssl": True}
            },
            "logging": {"level": "INFO"}
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        db_config = provider.get_database_config()
        assert db_config["uri"] == "mongodb://user:pass@localhost:27017/mydb"
        assert db_config["pool_size"] == 10
        assert db_config["timeout"] == 30
        assert db_config["options"]["ssl"] is True
    
    def test_get_database_config_with_components(self, temp_config_dir):
        """Test get_database_config with individual components."""
        # Clean up any database-related env vars from previous tests
        db_env_vars = ['PHOENIX_DATABASE_HOST', 'PHOENIX_DATABASE_PORT', 
                       'PHOENIX_DATABASE_NAME', 'PHOENIX_DATABASE_USERNAME',
                       'PHOENIX_DATABASE_PASSWORD', 'DATABASE_HOST']
        original_env = {}
        for var in db_env_vars:
            if var in os.environ:
                original_env[var] = os.environ.pop(var)
        
        try:
            config = {
                "database": {
                    "host": "localhost",
                    "port": 27017,
                    "name": "phoenix_db",
                    "username": "dbuser",
                    "password": "dbpass"
                },
                "logging": {"level": "INFO"}
            }
            config_file = temp_config_dir / "base.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config, f)
            
            provider = EnvironmentConfigProvider(
                config_dir=temp_config_dir,
                load_dotenv=False
            )
            
            db_config = provider.get_database_config()
            assert db_config["host"] == "localhost"
            assert db_config["port"] == 27017
            assert db_config["name"] == "phoenix_db"
            assert db_config["username"] == "dbuser"
            assert db_config["password"] == "dbpass"
        finally:
            # Restore original env vars
            for var, value in original_env.items():
                os.environ[var] = value
    
    def test_get_database_config_missing_required(self, temp_config_dir):
        """Test get_database_config with missing required fields."""
        config = {
            "database": {
                "host": "localhost"
                # Missing name
            },
            "logging": {"level": "INFO"}
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            provider.get_database_config()
        assert "Database configuration incomplete" in str(exc_info.value)
    
    def test_get_logging_config(self, temp_config_dir):
        """Test get_logging_config."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {
                "level": "DEBUG",
                "format": "%(levelname)s: %(message)s",
                "console": False,
                "file_path": "/var/log/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "handlers": {
                    "syslog": {"enabled": True}
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
        
        log_config = provider.get_logging_config()
        assert log_config["level"] == "DEBUG"
        assert log_config["format"] == "%(levelname)s: %(message)s"
        assert log_config["console"] is False
        assert log_config["file_path"] == "/var/log/app.log"
        assert log_config["max_bytes"] == 10485760
        assert log_config["backup_count"] == 5
        assert log_config["handlers"]["syslog"]["enabled"] is True
    
    def test_get_collection_config(self, temp_config_dir):
        """Test get_collection_config."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"},
            "collection": {
                "target_zipcodes": ["85001", "85002", "85003"],
                "schedule": "0 2 * * *",
                "batch_size": 50,
                "max_workers": 8,
                "sources": {
                    "maricopa": {"enabled": True, "priority": 1},
                    "phoenix_mls": {"enabled": False}
                },
                "retry": {
                    "max_retries": 5,
                    "delay": 2.0,
                    "backoff": 1.5
                }
            },
            "proxy": {
                "enabled": True,
                "url": "http://proxy.example.com:8080",
                "username": "proxyuser",
                "password": "proxypass"
            }
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            load_dotenv=False
        )
        
        collection_config = provider.get_collection_config()
        assert collection_config["target_zipcodes"] == ["85001", "85002", "85003"]
        assert collection_config["schedule"] == "0 2 * * *"
        assert collection_config["batch_size"] == 50
        assert collection_config["max_workers"] == 8
        assert collection_config["sources"]["maricopa"]["enabled"] is True
        assert collection_config["sources"]["phoenix_mls"]["enabled"] is False
        assert collection_config["retry_policy"]["max_retries"] == 5
        assert collection_config["proxy"]["enabled"] is True
        assert collection_config["proxy"]["url"] == "http://proxy.example.com:8080"
    
    def test_environment_check_methods(self, temp_config_dir):
        """Test environment checking methods."""
        config = {
            "database": {"uri": "mongodb://localhost"},
            "logging": {"level": "INFO"}
        }
        config_file = temp_config_dir / "base.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        # Test development
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="development",
            load_dotenv=False
        )
        assert provider.is_development() is True
        assert provider.is_testing() is False
        assert provider.is_production() is False
        
        # Test production
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="production",
            load_dotenv=False
        )
        assert provider.is_development() is False
        assert provider.is_testing() is False
        assert provider.is_production() is True
        
        # Test testing
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="test",
            load_dotenv=False
        )
        assert provider.is_development() is False
        assert provider.is_testing() is True
        assert provider.is_production() is False
        
        # Test aliases
        provider = EnvironmentConfigProvider(
            config_dir=temp_config_dir,
            environment="prod",
            load_dotenv=False
        )
        assert provider.is_production() is True