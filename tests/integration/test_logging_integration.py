"""Integration tests for logging with configuration system."""

import os
import json
import tempfile
from pathlib import Path
import pytest

from phoenix_real_estate.foundation.config import get_config
from phoenix_real_estate.foundation.logging import (
    get_logger,
    configure_logging,
    correlation_context
)


class TestLoggingConfigurationIntegration:
    """Test logging integration with configuration system."""
    
    def test_logging_with_config_system(self):
        """Test that logging integrates properly with configuration system."""
        # Get config and configure logging
        config = get_config()
        logging_config = config.get_logging_config()
        
        # Verify config structure
        assert "level" in logging_config
        assert "format" in logging_config
        assert "console" in logging_config
        
        # Configure logging
        configure_logging(logging_config)
        
        # Get logger and test
        logger = get_logger("test.config.integration")
        
        # Should be able to log at configured level
        logger.info("Test message from config integration")
        logger.debug("Debug message")
        
        # With correlation ID
        with correlation_context() as correlation_id:
            logger.info("Message with correlation", extra={
                "test": "integration",
                "config_env": config.get_environment()
            })
    
    def test_environment_specific_logging(self):
        """Test environment-specific logging behavior."""
        # Test with different environments
        environments = {
            "development": {
                "format": "text",
                "expected_colors": True
            },
            "production": {
                "format": "json",
                "expected_colors": False
            }
        }
        
        for env, expected in environments.items():
            with tempfile.TemporaryDirectory() as temp_dir:
                log_file = Path(temp_dir) / f"{env}.log"
                
                # Configure for specific environment
                configure_logging({
                    "level": "INFO",
                    "format": expected["format"],
                    "console": False,
                    "file_path": str(log_file),
                    "environment": env
                })
                
                logger = get_logger(f"test.{env}")
                logger.info(f"Testing {env} environment")
                
                # Read log file
                with open(log_file, "r") as f:
                    content = f.read().strip()
                
                # Verify format
                if expected["format"] == "json":
                    # Should be valid JSON
                    data = json.loads(content)
                    assert data["level"] == "INFO"
                    assert data["message"] == f"Testing {env} environment"
                else:
                    # Should be text format
                    assert "[INFO]" in content
                    assert f"Testing {env} environment" in content
    
    def test_logging_with_database_config(self):
        """Test logging doesn't expose database credentials."""
        logger = get_logger("test.security")
        
        # Get database config (which might contain sensitive data)
        config = get_config()
        db_config = config.get_database_config()
        
        # Create a log file to capture output
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "security.log"
            
            configure_logging({
                "level": "INFO",
                "format": "json",
                "console": False,
                "file_path": str(log_file)
            })
            
            # Log database config
            logger.info("Database connection attempt", extra={
                "database_uri": db_config.get("uri", ""),
                "database_name": db_config.get("name", ""),
                "api_key": "test-api-key",
                "safe_info": "This should be visible"
            })
            
            # Read and verify
            with open(log_file, "r") as f:
                data = json.loads(f.readline())
            
            # Sensitive fields should be redacted
            if "database_uri" in data["extra"] and data["extra"]["database_uri"]:
                assert data["extra"]["database_uri"] == "[REDACTED]"
            
            assert data["extra"]["api_key"] == "[REDACTED]"
            assert data["extra"]["safe_info"] == "This should be visible"
            
            # Database name is not sensitive
            if "database_name" in data["extra"]:
                assert data["extra"]["database_name"] != "[REDACTED]"
    
    def test_logging_file_rotation_config(self):
        """Test file rotation configuration from config system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "rotating.log"
            
            # Configure with rotation
            configure_logging({
                "level": "INFO",
                "format": "text",
                "console": False,
                "file_path": str(log_file),
                "max_bytes": 1024,  # 1KB for testing
                "backup_count": 3
            })
            
            logger = get_logger("test.rotation")
            
            # Write enough data to trigger rotation
            long_message = "X" * 100
            for i in range(20):
                logger.info(f"Message {i}: {long_message}")
            
            # Check that rotation occurred
            assert log_file.exists()
            # At least one backup should exist
            assert (log_file.parent / "rotating.log.1").exists()
    
    def test_multiple_handlers_from_config(self):
        """Test configuring multiple handlers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_log = Path(temp_dir) / "main.log"
            error_log = Path(temp_dir) / "errors.log"
            
            # Configure with multiple handlers
            configure_logging({
                "level": "DEBUG",
                "format": "json",
                "console": False,
                "file_path": str(main_log),
                "handlers": {
                    "error_file": {
                        "type": "file",
                        "filename": str(error_log),
                        "level": "ERROR",
                        "format": "json"
                    }
                }
            })
            
            logger = get_logger("test.handlers")
            
            # Log at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # Check main log (should have all messages DEBUG and above)
            with open(main_log, "r") as f:
                main_lines = f.readlines()
            assert len(main_lines) == 5
            
            # Check error log (should only have ERROR and CRITICAL)
            with open(error_log, "r") as f:
                error_lines = f.readlines()
            assert len(error_lines) == 2
            
            # Verify content
            for line in error_lines:
                data = json.loads(line)
                assert data["level"] in ["ERROR", "CRITICAL"]


class TestLoggingPerformance:
    """Test logging performance characteristics."""
    
    def test_logging_with_large_context(self):
        """Test logging with large context data."""
        logger = get_logger("test.performance")
        
        # Create large context
        large_context = {
            f"field_{i}": f"value_{i}" * 10
            for i in range(100)
        }
        
        # Should handle large context without issues
        with correlation_context():
            logger.info("Large context test", extra=large_context)
    
    def test_logging_filtering_performance(self):
        """Test that filtering doesn't significantly impact performance."""
        logger = get_logger("test.filter.performance")
        
        # Create context with many sensitive fields
        sensitive_context = {
            f"password_{i}": f"secret_{i}",
            f"api_key_{i}": f"key_{i}",
            f"token_{i}": f"token_{i}",
            f"safe_field_{i}": f"value_{i}"
            for i in range(50)
        }
        
        # Should handle filtering efficiently
        logger.info("Sensitive data test", extra=sensitive_context)


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_environment_configurations(environment):
    """Test logging works correctly in all environments."""
    # Set environment
    os.environ["ENVIRONMENT"] = environment
    
    # Get fresh config
    from phoenix_real_estate.foundation.config import reset_config_cache
    reset_config_cache()
    
    config = get_config()
    logging_config = config.get_logging_config()
    
    # Configure logging
    configure_logging(logging_config)
    
    # Get logger
    logger = get_logger(f"test.env.{environment}")
    
    # Test logging
    with correlation_context() as correlation_id:
        logger.info(f"Testing in {environment}", extra={
            "environment": environment,
            "config_level": logging_config.get("level")
        })
    
    # Reset environment
    os.environ.pop("ENVIRONMENT", None)