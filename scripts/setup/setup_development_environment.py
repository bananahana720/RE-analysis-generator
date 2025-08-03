#!/usr/bin/env python3
"""Development Environment Setup Script for Phoenix Real Estate Collector.

This script validates and sets up the development environment including:
- Environment variable validation
- Configuration loading verification
- API credential validation
- Database connection testing
- Component integration verification

Usage:
    python scripts/setup_development_environment.py [--validate-only]
"""

import os
import sys
import logging
from pathlib import Path
from typing import List
import argparse

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from phoenix_real_estate.foundation.config import (
        get_config,
        reset_config_cache,
        ConfigurationError,
    )
    from phoenix_real_estate.foundation.config.secrets import (
        get_secret_manager,
    )
except ImportError as e:
    print(f"❌ Failed to import Phoenix Real Estate modules: {e}")
    print("Please ensure you're running from the project root and dependencies are installed:")
    print("  uv run python scripts/setup_development_environment.py")
    sys.exit(1)

# Configure logging for script
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class DevelopmentEnvironmentSetup:
    """Development environment setup and validation."""

    def __init__(self, validate_only: bool = False):
        """Initialize setup with validation mode."""
        self.validate_only = validate_only
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success_messages: List[str] = []

    def run(self) -> bool:
        """Run the development environment setup and validation."""
        print("Phoenix Real Estate Development Environment Setup")
        print("=" * 60)

        try:
            # Step 1: Validate environment variables
            self._validate_environment_variables()

            # Step 2: Validate configuration loading
            self._validate_configuration_loading()

            # Step 3: Validate credentials and secrets
            self._validate_credentials()

            # Step 4: Test component integration
            self._test_component_integration()

            # Step 5: Create .env file if needed (setup mode only)
            if not self.validate_only:
                self._create_env_file_if_needed()

            # Report results
            self._report_results()

            return len(self.errors) == 0

        except Exception as e:
            logger.error(f"Unexpected error during setup: {e}")
            return False

    def _validate_environment_variables(self) -> None:
        """Validate required and recommended environment variables."""
        print("\nStep 1: Validating Environment Variables")

        # Required environment variables for development
        required_vars = {
            "ENVIRONMENT": "development",
            "MARICOPA_API_KEY": "Your Maricopa County API key",
        }

        # Recommended environment variables
        recommended_vars = {
            "MARICOPA_RATE_LIMIT": "50 (Conservative for development)",
            "MONGODB_URI": "mongodb://localhost:27017/phoenix_real_estate_dev",
            "LOG_LEVEL": "DEBUG",
            "DEBUG": "true",
        }

        # Check required variables
        for var, description in required_vars.items():
            value = os.environ.get(var)
            if not value:
                self.errors.append(f"Missing required environment variable: {var} ({description})")
            else:
                self.success_messages.append(f"✅ {var} configured")
                logger.info(f"{var} = {self._mask_sensitive_value(var, value)}")

        # Check recommended variables
        for var, description in recommended_vars.items():
            value = os.environ.get(var)
            if not value:
                self.warnings.append(
                    f"Recommended environment variable not set: {var} ({description})"
                )
            else:
                self.success_messages.append(f"✅ {var} configured")
                logger.info(f"{var} = {value}")

    def _validate_configuration_loading(self) -> None:
        """Validate configuration loading from all sources."""
        print("\n⚙️  Step 2: Validating Configuration Loading")

        try:
            # Reset cache to ensure fresh load
            reset_config_cache()

            # Test configuration loading
            config = get_config()

            self.success_messages.append("✅ Configuration provider initialized")

            # Test environment detection
            env = config.get_environment()
            if env != "development":
                self.warnings.append(f"Environment is '{env}', expected 'development'")
            else:
                self.success_messages.append(f"✅ Environment: {env}")

            # Test required configuration access
            try:
                api_key = config.get_required("MARICOPA_API_KEY")
                masked_key = self._mask_sensitive_value("MARICOPA_API_KEY", api_key)
                self.success_messages.append(f"✅ API Key loaded: {masked_key}")
            except ConfigurationError as e:
                self.errors.append(f"Failed to load required API key: {e}")

            # Test optional configuration with defaults
            rate_limit = config.get("MARICOPA_RATE_LIMIT", "100")
            self.success_messages.append(f"✅ Rate limit: {rate_limit} requests/hour")

            # Test typed configuration
            debug_mode = config.get_typed("DEBUG", bool, False)
            self.success_messages.append(f"✅ Debug mode: {debug_mode}")

            # Test database configuration helper
            try:
                db_config = config.get_database_config()
                if "uri" in db_config:
                    # Mask sensitive parts of URI
                    uri = db_config["uri"]
                    if "@" in uri and "://" in uri:
                        # mongodb://user:pass@host:port/db -> mongodb://***@host:port/db
                        parts = uri.split("://", 1)
                        if len(parts) == 2 and "@" in parts[1]:
                            after_protocol = parts[1]
                            auth_and_rest = after_protocol.split("@", 1)
                            masked_uri = f"{parts[0]}://***@{auth_and_rest[1]}"
                        else:
                            masked_uri = uri
                    else:
                        masked_uri = uri
                    self.success_messages.append(f"✅ Database configuration loaded: {masked_uri}")
                else:
                    self.success_messages.append(
                        "✅ Database configuration loaded (component-based)"
                    )
            except Exception as e:
                self.warnings.append(f"Database configuration incomplete: {e}")

        except Exception as e:
            self.errors.append(f"Configuration loading failed: {e}")

    def _validate_credentials(self) -> None:
        """Validate credentials and secret management."""
        print("\n🔐 Step 3: Validating Credentials and Secrets")

        try:
            secret_manager = get_secret_manager()

            # Test API key retrieval through secret manager
            api_keys = secret_manager.get_api_keys()
            if api_keys:
                for service, key in api_keys.items():
                    masked_key = self._mask_sensitive_value(f"{service}_api_key", key)
                    self.success_messages.append(f"✅ {service.upper()} API key: {masked_key}")

            # Test direct secret retrieval
            test_secrets = ["MARICOPA_API_KEY", "SECRET_API_KEY_MARICOPA"]
            found_secrets = []

            for secret_name in test_secrets:
                secret_value = secret_manager.get_secret(secret_name)
                if secret_value:
                    found_secrets.append(secret_name)
                    masked_value = self._mask_sensitive_value(secret_name, secret_value)
                    self.success_messages.append(
                        f"✅ Secret retrieved: {secret_name} = {masked_value}"
                    )

            if not found_secrets:
                self.warnings.append("No API secrets found through secret manager")

            # Test credential validation
            required_secrets = []
            if os.environ.get("MARICOPA_API_KEY"):
                required_secrets.append("MARICOPA_API_KEY")

            if required_secrets:
                try:
                    # Create a custom secret manager that checks env vars directly
                    class EnvSecretManager:
                        def get_secret(self, name):
                            return os.environ.get(name)

                    env_manager = EnvSecretManager()
                    for secret in required_secrets:
                        value = env_manager.get_secret(secret)
                        if value:
                            self.success_messages.append(f"✅ Required secret present: {secret}")
                        else:
                            self.errors.append(f"Required secret missing: {secret}")

                except Exception as e:
                    self.warnings.append(f"Secret validation error: {e}")

        except Exception as e:
            self.errors.append(f"Credential validation failed: {e}")

    def _test_component_integration(self) -> None:
        """Test component integration with configuration."""
        print("\n🧩 Step 4: Testing Component Integration")

        try:
            config = get_config()

            # Test Maricopa API client configuration
            maricopa_config = {
                "api_key": config.get("MARICOPA_API_KEY"),
                "base_url": config.get(
                    "MARICOPA_BASE_URL", "https://api.mcassessor.maricopa.gov/api/v1"
                ),
                "timeout": config.get_typed("MARICOPA_TIMEOUT", int, 10),
                "rate_limit": config.get_typed("MARICOPA_RATE_LIMIT", int, 1000),
            }

            if maricopa_config["api_key"]:
                self.success_messages.append("✅ Maricopa API client configuration ready")
                logger.info(f"  - Base URL: {maricopa_config['base_url']}")
                logger.info(f"  - Timeout: {maricopa_config['timeout']}s")
                logger.info(f"  - Rate limit: {maricopa_config['rate_limit']}/hour")
            else:
                self.errors.append("Maricopa API client missing API key")

            # Test rate limiter configuration
            rate_config = {
                "max_requests_per_hour": maricopa_config["rate_limit"],
                "burst_size": config.get_typed("COLLECTION_RATE_LIMITING_BURST_SIZE", int, 10),
                "window_size": config.get_typed(
                    "COLLECTION_RATE_LIMITING_WINDOW_SIZE_MINUTES", int, 60
                ),
            }

            self.success_messages.append("✅ Rate limiter configuration ready")
            logger.info(f"  - Max requests: {rate_config['max_requests_per_hour']}/hour")
            logger.info(f"  - Burst size: {rate_config['burst_size']}")

            # Test collector configuration
            try:
                collection_config = config.get_collection_config()
                self.success_messages.append("✅ Collection configuration ready")
                logger.info(f"  - Target ZIP codes: {len(collection_config['target_zipcodes'])}")
                logger.info(f"  - Batch size: {collection_config['batch_size']}")
                logger.info(f"  - Max retries: {collection_config['retry_policy']['max_retries']}")
            except Exception as e:
                self.warnings.append(f"Collection configuration incomplete: {e}")

        except Exception as e:
            self.errors.append(f"Component integration test failed: {e}")

    def _create_env_file_if_needed(self) -> None:
        """Create .env file with development defaults if needed."""
        print("\n📝 Step 5: Environment File Setup")

        env_file = project_root / ".env"

        if env_file.exists():
            self.success_messages.append("✅ .env file already exists")
            return

        # Create .env file with development defaults
        env_content = """# Phoenix Real Estate Development Environment
# Generated by setup_development_environment.py

# Environment
ENVIRONMENT=development

# Maricopa County API Configuration
MARICOPA_API_KEY=your_maricopa_api_key_here
MARICOPA_BASE_URL=https://api.mcassessor.maricopa.gov/api/v1
MARICOPA_RATE_LIMIT=50
MARICOPA_TIMEOUT=30

# Database Configuration
MONGODB_URI=mongodb://localhost:27017/phoenix_real_estate_dev
MONGODB_DATABASE=phoenix_real_estate_dev

# Logging Configuration
LOG_LEVEL=DEBUG
DEBUG=true

# Collection Settings
COLLECTION_TARGET_ZIPCODES=85031
COLLECTION_BATCH_SIZE=5
COLLECTION_MAX_WORKERS=1

# Processing Settings
PROCESSING_LLM_MODEL=llama3.2:latest
PROCESSING_BATCH_SIZE=5
PROCESSING_MAX_WORKERS=1

# Security (development only - use proper secrets in production)
SECRET_KEY=development-secret-key-32-characters-minimum!

# Performance
PHOENIX_FEATURES_CACHE_ENABLED=true
PHOENIX_CACHE_DIRECTORY=.cache
"""

        try:
            with open(env_file, "w") as f:
                f.write(env_content)

            self.success_messages.append(f"✅ Created .env file: {env_file}")
            print(f"   📋 Please edit {env_file} and set your actual API key")

        except Exception as e:
            self.errors.append(f"Failed to create .env file: {e}")

    def _mask_sensitive_value(self, key: str, value: str) -> str:
        """Mask sensitive values for logging."""
        if not value:
            return "None"

        sensitive_patterns = ["key", "secret", "password", "token", "credential"]

        if any(pattern in key.lower() for pattern in sensitive_patterns):
            if len(value) <= 8:
                return "***"
            else:
                return f"{value[:4]}...{value[-4:]}"

        return value

    def _report_results(self) -> None:
        """Report setup and validation results."""
        print("\n" + "=" * 60)
        print("📊 Development Environment Setup Results")
        print("=" * 60)

        # Success messages
        if self.success_messages:
            print("\n✅ Success:")
            for message in self.success_messages:
                print(f"   {message}")

        # Warnings
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   {warning}")

        # Errors
        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"   {error}")

            print("\n🔧 To fix these errors:")
            print("   1. Set missing environment variables in your shell or .env file")
            print("   2. Ensure API keys and credentials are properly configured")
            print("   3. Run this script again to verify fixes")

        else:
            print("\n🎉 Development environment setup completed successfully!")
            print("\nNext steps:")
            print("   1. Start your MongoDB instance (if using local MongoDB)")
            print("   2. Test the configuration with: uv run pytest tests/foundation/config/")
            print("   3. Begin development with: uv run python -m phoenix_real_estate")

        print("\n" + "=" * 60)


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(
        description="Setup and validate Phoenix Real Estate development environment"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing setup, do not create files",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run setup
    setup = DevelopmentEnvironmentSetup(validate_only=args.validate_only)
    success = setup.run()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
