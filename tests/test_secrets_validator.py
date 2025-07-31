"""
Tests for secrets validation script.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSecretsValidator:
    """Test cases for secrets validator functionality."""

    @pytest.fixture
    def secrets_validator(self):
        """Create a secrets validator instance."""
        from scripts.validate_secrets import SecretsValidator
        return SecretsValidator()

    @pytest.fixture
    def valid_env_vars(self):
        """Provide valid environment variables for testing."""
        return {
            "MONGODB_URI": "mongodb://localhost:27017",
            "SECRET_KEY": "ae-Bg7V9gs-XIoRTQqbSYs_zboAONkGhha1cuKvHkPM",
            "MARICOPA_API_KEY": "0fb33394-8cdb-4ddd-b7bb-ab1e005c2c29"
        }

    def test_validate_all_secrets_present_valid(self, secrets_validator, valid_env_vars):
        """Test validation passes when all required secrets are present and valid."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            result = secrets_validator.validate_all_secrets()
            
            assert result.is_valid is True
            assert len(result.errors) == 0

    def test_validate_all_secrets_missing_required(self, secrets_validator):
        """Test validation fails when required secrets are missing."""
        incomplete_vars = {
            "MONGODB_URI": "mongodb://localhost:27017"
            # Missing other required secrets
        }
        
        with patch.dict(os.environ, incomplete_vars, clear=True):
            result = secrets_validator.validate_all_secrets()
            
            assert result.is_valid is False
            assert len(result.errors) > 0
            
            error_messages = " ".join(result.errors)
            assert "MARICOPA_API_KEY" in error_messages
            assert "SECRET_KEY" in error_messages

    def test_validate_secret_format_maricopa_api_key(self, secrets_validator):
        """Test Maricopa API key format validation."""
        # Valid UUID format
        valid_key = "0fb33394-8cdb-4ddd-b7bb-ab1e005c2c29"
        assert secrets_validator.validate_secret_format("MARICOPA_API_KEY", valid_key) is True
        
        # Invalid format
        invalid_key = "invalid-key-format"
        assert secrets_validator.validate_secret_format("MARICOPA_API_KEY", invalid_key) is False

    def test_validate_secret_format_mongodb_uri(self, secrets_validator):
        """Test MongoDB URI format validation."""
        # Valid local URI
        valid_uri = "mongodb://localhost:27017"
        assert secrets_validator.validate_secret_format("MONGODB_URI", valid_uri) is True
        
        # Valid Atlas URI  
        atlas_uri = "mongodb+srv://user:pass@cluster.mongodb.net/db"
        assert secrets_validator.validate_secret_format("MONGODB_URI", atlas_uri) is True
        
        # Invalid URI
        invalid_uri = "not-a-mongodb-uri"
        assert secrets_validator.validate_secret_format("MONGODB_URI", invalid_uri) is False

    def test_secret_health_monitoring(self, secrets_validator, valid_env_vars):
        """Test secret health monitoring functionality."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            health_result = secrets_validator.monitor_secret_health("MONGODB_URI")
            
            assert health_result.is_healthy is True
            assert health_result.response_time is not None
            assert health_result.last_checked is not None

    def test_error_handling_missing_secret(self, secrets_validator):
        """Test error handling when secret is missing."""
        with patch.dict(os.environ, {}, clear=True):
            health_result = secrets_validator.monitor_secret_health("NONEXISTENT_SECRET")
            
            assert health_result.is_healthy is False
            assert "not found" in health_result.error_message

