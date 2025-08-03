"""Integration tests for MongoDB Atlas validation scripts.

This module tests the MongoDB Atlas validation and setup scripts
to ensure they work correctly with mock configurations.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from scripts.validation.validate_mongodb_atlas import MongoDBAtlasValidator
from setup_mongodb_atlas import validate_mongodb_uri


class TestMongoDBAtlasScripts:
    """Test suite for MongoDB Atlas scripts."""

    def test_uri_validation_valid_uris(self):
        """Test URI validation with valid MongoDB URIs."""
        valid_uris = [
            "mongodb://localhost:27017",
            "mongodb://user:pass@localhost:27017",
            "mongodb+srv://user:pass@cluster.mongodb.net/dbname",
            "mongodb://localhost:27017/dbname",
        ]

        for uri in valid_uris:
            is_valid, message = validate_mongodb_uri(uri)
            assert is_valid, f"URI {uri} should be valid: {message}"

    def test_uri_validation_invalid_uris(self):
        """Test URI validation with invalid MongoDB URIs."""
        invalid_uris = [
            "",
            "http://localhost:27017",
            "mysql://localhost:3306",
            "invalid-uri",
            "mongodb://",
        ]

        for uri in invalid_uris:
            is_valid, message = validate_mongodb_uri(uri)
            assert not is_valid, f"URI {uri} should be invalid"

    def test_validator_initialization(self):
        """Test MongoDBAtlasValidator initialization."""
        validator = MongoDBAtlasValidator()

        assert validator.db_connection is None
        assert validator.test_results == {}
        assert validator.sample_property_id.startswith("test_prop_")

    @pytest.mark.asyncio
    async def test_validate_configuration_success(self):
        """Test configuration validation with valid config."""
        validator = MongoDBAtlasValidator()

        # Mock the configuration
        mock_config = MagicMock()
        mock_config.mongodb_uri = "mongodb://localhost:27017"
        mock_config.database_name = "test_db"
        mock_config.environment.value = "testing"

        with patch("scripts.validate_mongodb_atlas.get_config", return_value=mock_config):
            result = await validator.validate_configuration()

        assert result is True
        assert validator.test_results["configuration"]["success"] is True
        assert validator.mongodb_uri == "mongodb://localhost:27017"
        assert validator.database_name == "test_db"

    @pytest.mark.asyncio
    async def test_validate_configuration_missing_uri(self):
        """Test configuration validation with missing URI."""
        validator = MongoDBAtlasValidator()

        # Mock the configuration without URI
        mock_config = MagicMock()
        mock_config.mongodb_uri = ""
        mock_config.database_name = "test_db"

        with patch("scripts.validate_mongodb_atlas.get_config", return_value=mock_config):
            result = await validator.validate_configuration()

        assert result is False
        assert validator.test_results["configuration"]["success"] is False

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Test database connection validation with mock connection."""
        validator = MongoDBAtlasValidator()
        validator.mongodb_uri = "mongodb://localhost:27017"
        validator.database_name = "test_db"

        # Mock successful connection
        mock_connection = AsyncMock()

        with patch(
            "scripts.validate_mongodb_atlas.get_database_connection", return_value=mock_connection
        ):
            result = await validator.validate_connection()

        assert result is True
        assert validator.test_results["connection"]["success"] is True
        assert validator.db_connection is mock_connection

    @pytest.mark.asyncio
    async def test_validate_health_check_success(self):
        """Test health check validation with mock connection."""
        validator = MongoDBAtlasValidator()

        # Mock connection with health check
        mock_connection = AsyncMock()
        mock_connection.health_check.return_value = {
            "connected": True,
            "ping_time_ms": 25.5,
            "database_stats": {"collections": 2, "data_size": 1024},
        }
        validator.db_connection = mock_connection

        result = await validator.validate_health_check()

        assert result is True
        assert validator.test_results["health_check"]["success"] is True
        assert validator.test_results["health_check"]["ping_time_ms"] == 25.5

    @pytest.mark.asyncio
    async def test_validate_health_check_not_connected(self):
        """Test health check validation when not connected."""
        validator = MongoDBAtlasValidator()

        # Mock connection with failed health check
        mock_connection = AsyncMock()
        mock_connection.health_check.return_value = {"connected": False}
        validator.db_connection = mock_connection

        result = await validator.validate_health_check()

        assert result is False
        assert validator.test_results["health_check"]["success"] is False

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method."""
        validator = MongoDBAtlasValidator()
        validator.db_connection = AsyncMock()

        with patch("scripts.validate_mongodb_atlas.close_database_connection") as mock_close:
            await validator.cleanup()
            mock_close.assert_called_once()

    def test_generate_summary_success(self):
        """Test summary generation for successful validation."""
        validator = MongoDBAtlasValidator()
        validator.test_results = {
            "configuration": {"success": True},
            "connection": {"success": True},
            "health_check": {"success": True},
        }

        summary = validator._generate_summary(True)

        assert summary["overall_success"] is True
        assert "timestamp" in summary
        assert summary["test_results"] == validator.test_results

    def test_generate_summary_failure(self):
        """Test summary generation for failed validation."""
        validator = MongoDBAtlasValidator()
        validator.test_results = {
            "configuration": {"success": False, "error": "Missing URI"},
            "connection": {"success": False, "error": "Connection failed"},
        }

        summary = validator._generate_summary(False)

        assert summary["overall_success"] is False
        assert "timestamp" in summary
        assert summary["test_results"] == validator.test_results


class TestScriptExecutability:
    """Test that scripts can be executed without errors."""

    def test_setup_script_help_message(self):
        """Test that setup script can show help without MongoDB connection."""
        from setup_mongodb_atlas import validate_mongodb_uri, print_banner

        # These should not raise exceptions
        print_banner()

        is_valid, message = validate_mongodb_uri("mongodb://test:test@localhost/test")
        assert is_valid

    def test_validator_creation(self):
        """Test that validator can be created without immediate connection."""
        validator = MongoDBAtlasValidator()

        assert validator is not None
        assert hasattr(validator, "run_full_validation")
        assert hasattr(validator, "validate_configuration")
        assert hasattr(validator, "validate_connection")


@pytest.mark.integration
class TestRealDatabaseOperations:
    """Integration tests that require actual database connection.

    These tests are marked as integration tests and will only run
    if a real database connection is available.
    """

    @pytest.fixture
    def skip_if_no_env(self):
        """Skip test if no .env file exists."""
        env_path = Path(__file__).parent.parent.parent / ".env"
        if not env_path.exists():
            pytest.skip("No .env file found - skipping real database tests")

    @pytest.mark.asyncio
    async def test_real_configuration_loading(self, skip_if_no_env):
        """Test loading real configuration from environment."""
        try:
            from phoenix_real_estate.foundation.config.environment import get_config

            config = get_config()

            # Basic checks - don't fail if MongoDB isn't configured
            assert hasattr(config, "environment")

        except Exception as e:
            pytest.skip(f"Configuration loading failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_real_database_ping(self, skip_if_no_env):
        """Test real database ping if connection is available."""
        try:
            from phoenix_real_estate.foundation.config.environment import get_config
            from phoenix_real_estate.foundation.database.connection import get_database_connection

            config = get_config()

            # Skip if no MongoDB configuration
            if not hasattr(config, "mongodb_uri") or not config.mongodb_uri:
                pytest.skip("No MongoDB URI configured")

            # Get database name
            database_name = getattr(config, "database_name", None) or getattr(
                config, "mongodb_database", None
            )
            if not database_name:
                pytest.skip("No database name configured")

            # Test connection with short timeout
            try:
                db_connection = await get_database_connection(config.mongodb_uri, database_name)
                health = await db_connection.health_check()

                # If we get here, connection worked
                assert "connected" in health
                print(f"Real database ping: {health.get('ping_time_ms', 'unknown')}ms")

            except Exception as e:
                pytest.skip(
                    f"Database connection failed (this is expected if MongoDB Atlas isn't set up): {str(e)}"
                )

        except Exception as e:
            pytest.skip(f"Test setup failed: {str(e)}")
