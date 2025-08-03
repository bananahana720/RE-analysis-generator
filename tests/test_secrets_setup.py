"""
Tests for secrets setup script.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path

# Add src to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSecretsSetup:
    """Test cases for secrets setup functionality."""

    @pytest.fixture
    def temp_env_file(self):
        """Create a temporary .env file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("""
MONGODB_URI=mongodb://localhost:27017
SECRET_KEY=test-secret-key-32chars-long-enough
MARICOPA_API_KEY=0fb33394-8cdb-4ddd-b7bb-ab1e005c2c29
""")
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def secrets_setup(self):
        """Create a secrets setup instance."""
        from scripts.setup_secrets import SecretsSetup
        return SecretsSetup()

    def test_validate_local_env_structure_valid(self, secrets_setup, temp_env_file):
        """Test validation of valid .env file structure."""
        result = secrets_setup.validate_env_file(temp_env_file)
        assert result is True
        assert len(secrets_setup.validation_errors) == 0

    def test_validate_secret_format_api_key(self, secrets_setup):
        """Test API key format validation."""
        valid_key = "0fb33394-8cdb-4ddd-b7bb-ab1e005c2c29"
        assert secrets_setup.validate_secret_format("MARICOPA_API_KEY", valid_key) is True
        
        invalid_key = "invalid-key"
        assert secrets_setup.validate_secret_format("MARICOPA_API_KEY", invalid_key) is False

    def test_generate_github_secrets_config(self, secrets_setup, temp_env_file):
        """Test GitHub Actions secrets configuration generation."""
        config = secrets_setup.generate_github_config(temp_env_file)
        
        assert isinstance(config, dict)
        assert "secrets" in config
        assert "repository_secrets" in config["secrets"]
        
        repo_secrets = config["secrets"]["repository_secrets"]
        assert "MONGODB_URI" in repo_secrets
        assert "SECRET_KEY" in repo_secrets

    def test_categorize_secret(self, secrets_setup):
        """Test proper categorization of secrets."""
        assert secrets_setup.categorize_secret("MARICOPA_API_KEY") == "api_keys"
        assert secrets_setup.categorize_secret("MONGODB_URI") == "database"
        assert secrets_setup.categorize_secret("SECRET_KEY") == "encryption"

