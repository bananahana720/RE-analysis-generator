#!/usr/bin/env python3
"""Configuration Validation Script for Phoenix Real Estate Collector.

This script provides comprehensive validation of configuration across all environments
including security, performance, and integration checks.

Usage:
    python scripts/validate_configuration.py [--environment ENV] [--strict]
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from phoenix_real_estate.foundation.config import (
        get_config,
        reset_config_cache,
        ConfigurationError,
        EnvironmentConfigProvider,
    )
    from phoenix_real_estate.foundation.config.secrets import (
        get_secret_manager,
        SecretNotFoundError,
        SecretValidationError,
    )
except ImportError as e:
    print(f"❌ Failed to import Phoenix Real Estate modules: {e}")
    print("Please ensure you're running from the project root and dependencies are installed:")
    print("  uv run python scripts/validate_configuration.py")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a configuration validation check."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    severity: str = "error"  # error, warning, info


class ConfigurationValidator:
    """Comprehensive configuration validator."""

    def __init__(self, environment: Optional[str] = None, strict_mode: bool = False):
        """Initialize validator."""
        self.environment = environment or os.environ.get("ENVIRONMENT", "development")
        self.strict_mode = strict_mode
        self.results: List[ValidationResult] = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print(f"🔍 Validating configuration for environment: {self.environment}")
        print("=" * 60)

        try:
            # Reset configuration cache
            reset_config_cache()

            # Core validation checks
            self._validate_configuration_loading()
            self._validate_environment_setup()
            self._validate_security_settings()
            self._validate_database_configuration()
            self._validate_api_configuration()
            self._validate_collection_settings()
            self._validate_logging_configuration()
            self._validate_performance_settings()
            self._validate_component_integration()

            # Environment-specific validations
            if self.environment == "production":
                self._validate_production_requirements()
            elif self.environment == "development":
                self._validate_development_setup()
            elif self.environment in ["testing", "test"]:
                self._validate_testing_setup()

            # Report results
            self._report_results()

            # Determine overall success
            error_count = len([r for r in self.results if r.severity == "error"])
            warning_count = len([r for r in self.results if r.severity == "warning"])

            if self.strict_mode:
                return error_count == 0 and warning_count == 0
            else:
                return error_count == 0

        except Exception as e:
            logger.error(f"Validation failed with unexpected error: {e}")
            return False

    def _add_result(
        self,
        success: bool,
        message: str,
        severity: str = "error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a validation result."""
        self.results.append(
            ValidationResult(success=success, message=message, severity=severity, details=details)
        )

    def _validate_configuration_loading(self) -> None:
        """Validate basic configuration loading."""
        print("\n⚙️  Configuration Loading")

        try:
            config = get_config()
            self._add_result(True, "Configuration provider initialized", "info")

            # Test environment detection
            detected_env = config.get_environment()
            if detected_env == self.environment:
                self._add_result(True, f"Environment correctly detected: {detected_env}", "info")
            else:
                self._add_result(
                    False,
                    f"Environment mismatch: expected {self.environment}, got {detected_env}",
                    "error",
                    {"expected": self.environment, "actual": detected_env},
                )

            # Test basic configuration access
            try:
                app_name = config.get("application.name", "Phoenix Real Estate Collector")
                self._add_result(True, f"Application name: {app_name}", "info")
            except Exception as e:
                self._add_result(False, f"Failed to access basic configuration: {e}")

        except Exception as e:
            self._add_result(False, f"Configuration loading failed: {e}")

    def _validate_environment_setup(self) -> None:
        """Validate environment-specific setup."""
        print("\n🌍 Environment Setup")

        try:
            config = get_config()

            # Validate environment helpers
            is_dev = config.is_development()
            is_test = config.is_testing()
            is_prod = config.is_production()

            # Only one should be true
            env_flags = [is_dev, is_test, is_prod]
            true_count = sum(env_flags)

            if true_count == 1:
                self._add_result(True, "Environment detection is unambiguous", "info")
            else:
                self._add_result(
                    False,
                    f"Ambiguous environment detection: dev={is_dev}, test={is_test}, prod={is_prod}",
                    "error",
                )

            # Validate environment-specific requirements
            if self.environment == "production":
                required_vars = ["SECRET_KEY", "API_KEY", "MONITORING_ENABLED"]
                self._validate_required_env_vars(required_vars)
            elif self.environment == "development":
                recommended_vars = ["MARICOPA_API_KEY", "DEBUG", "LOG_LEVEL"]
                self._validate_recommended_env_vars(recommended_vars)

        except Exception as e:
            self._add_result(False, f"Environment setup validation failed: {e}")

    def _validate_security_settings(self) -> None:
        """Validate security configuration."""
        print("\n🔐 Security Settings")

        try:
            config = get_config()
            secret_manager = get_secret_manager()

            # Validate secret key strength
            secret_key = config.get("security.secret_key") or config.get("SECRET_KEY")
            if secret_key:
                if self.environment == "production":
                    if len(secret_key) < 32:
                        self._add_result(
                            False,
                            f"Production secret key too short: {len(secret_key)} chars (minimum 32)",
                            "error",
                        )
                    else:
                        self._add_result(
                            True, "Production secret key meets length requirements", "info"
                        )
                elif self.environment == "development":
                    if len(secret_key) < 16:
                        self._add_result(
                            False,
                            "Development secret key should be at least 16 characters",
                            "warning",
                        )
                    else:
                        self._add_result(True, "Development secret key acceptable", "info")
            else:
                severity = "error" if self.environment == "production" else "warning"
                self._add_result(False, "Secret key not configured", severity)

            # Validate API key security
            api_keys = secret_manager.get_api_keys()
            if api_keys:
                for service, key in api_keys.items():
                    if len(key) < 20:
                        self._add_result(
                            False,
                            f"API key for {service} appears too short ({len(key)} chars)",
                            "warning",
                        )
                    else:
                        self._add_result(
                            True, f"API key for {service} has reasonable length", "info"
                        )

            # Check for common security misconfigurations
            debug_mode = config.get_typed("debug", bool, False)
            if debug_mode and self.environment == "production":
                self._add_result(False, "Debug mode should not be enabled in production", "error")

            # Check logging security
            log_config = config.get_logging_config()
            if log_config.get("level") == "DEBUG" and self.environment == "production":
                self._add_result(False, "DEBUG logging should not be used in production", "warning")

        except Exception as e:
            self._add_result(False, f"Security validation failed: {e}")

    def _validate_database_configuration(self) -> None:
        """Validate database configuration."""
        print("\n🗄️  Database Configuration")

        try:
            config = get_config()
            db_config = config.get_database_config()

            # Check for database URI or connection components
            if "uri" in db_config:
                uri = db_config["uri"]
                if uri.startswith(("mongodb://", "mongodb+srv://")):
                    self._add_result(True, "Database URI format is valid", "info")

                    # Check for development vs production databases
                    if self.environment == "development" and "dev" not in uri.lower():
                        self._add_result(
                            False, "Development should use a development database", "warning"
                        )
                    elif self.environment == "production" and (
                        "dev" in uri.lower() or "test" in uri.lower()
                    ):
                        self._add_result(
                            False, "Production should not use development/test databases", "error"
                        )
                else:
                    self._add_result(False, f"Invalid database URI format: {uri[:20]}...", "error")
            else:
                # Check individual components
                required_components = ["host", "name"]
                missing = [comp for comp in required_components if not db_config.get(comp)]
                if missing:
                    self._add_result(
                        False, f"Missing database components: {', '.join(missing)}", "error"
                    )
                else:
                    self._add_result(True, "Database connection components present", "info")

            # Validate connection pool settings
            pool_size = db_config.get("pool_size", db_config.get("max_pool_size"))
            if pool_size:
                if self.environment == "production" and pool_size < 5:
                    self._add_result(
                        False,
                        f"Production pool size too small: {pool_size} (recommended: 10+)",
                        "warning",
                    )
                elif pool_size > 50:
                    self._add_result(
                        False,
                        f"Pool size very large: {pool_size} (may cause resource issues)",
                        "warning",
                    )
                else:
                    self._add_result(True, f"Database pool size reasonable: {pool_size}", "info")

        except Exception as e:
            self._add_result(False, f"Database configuration validation failed: {e}")

    def _validate_api_configuration(self) -> None:
        """Validate API configuration."""
        print("\n🌐 API Configuration")

        try:
            config = get_config()

            # Validate Maricopa API configuration
            api_key = config.get("MARICOPA_API_KEY") or config.get("maricopa_api_key")
            if api_key:
                if len(api_key) < 10:
                    self._add_result(False, "Maricopa API key appears too short", "warning")
                else:
                    self._add_result(True, "Maricopa API key configured", "info")
            else:
                severity = "error" if self.environment == "production" else "warning"
                self._add_result(False, "Maricopa API key not configured", severity)

            # Validate rate limiting
            rate_limit = config.get_typed("MARICOPA_RATE_LIMIT", int, 1000)
            if self.environment == "development" and rate_limit > 100:
                self._add_result(
                    False,
                    f"Development rate limit too high: {rate_limit} (recommended: ≤100)",
                    "warning",
                )
            elif self.environment == "production" and rate_limit > 2000:
                self._add_result(
                    False,
                    f"Production rate limit very high: {rate_limit} (check API limits)",
                    "warning",
                )
            else:
                self._add_result(True, f"Rate limit configured: {rate_limit}/hour", "info")

            # Validate timeouts
            timeout = config.get_typed("MARICOPA_TIMEOUT", int, 10)
            if timeout < 5:
                self._add_result(False, f"API timeout too short: {timeout}s", "warning")
            elif timeout > 60:
                self._add_result(False, f"API timeout very long: {timeout}s", "warning")
            else:
                self._add_result(True, f"API timeout reasonable: {timeout}s", "info")

        except Exception as e:
            self._add_result(False, f"API configuration validation failed: {e}")

    def _validate_collection_settings(self) -> None:
        """Validate data collection configuration."""
        print("\n📊 Collection Settings")

        try:
            config = get_config()
            collection_config = config.get_collection_config()

            # Validate target ZIP codes
            zip_codes = collection_config.get("target_zipcodes", [])
            if not zip_codes:
                self._add_result(False, "No target ZIP codes configured", "error")
            else:
                # Validate ZIP code formats
                valid_zips = []
                invalid_zips = []

                for zip_code in zip_codes:
                    zip_str = str(zip_code)
                    if len(zip_str) == 5 and zip_str.isdigit():
                        valid_zips.append(zip_str)
                    else:
                        invalid_zips.append(zip_str)

                if invalid_zips:
                    self._add_result(False, f"Invalid ZIP codes: {invalid_zips}", "error")

                if valid_zips:
                    self._add_result(True, f"Valid ZIP codes configured: {len(valid_zips)}", "info")

            # Validate batch size
            batch_size = collection_config.get("batch_size", 100)
            if batch_size < 1:
                self._add_result(False, "Batch size must be positive", "error")
            elif batch_size > 1000:
                self._add_result(
                    False,
                    f"Batch size very large: {batch_size} (may cause memory issues)",
                    "warning",
                )
            else:
                self._add_result(True, f"Batch size reasonable: {batch_size}", "info")

            # Validate retry policy
            retry_policy = collection_config.get("retry_policy", {})
            max_retries = retry_policy.get("max_retries", 3)
            if max_retries < 1:
                self._add_result(False, "Max retries should be at least 1", "warning")
            elif max_retries > 10:
                self._add_result(False, f"Max retries very high: {max_retries}", "warning")
            else:
                self._add_result(
                    True, f"Retry policy configured: {max_retries} max retries", "info"
                )

        except Exception as e:
            self._add_result(False, f"Collection settings validation failed: {e}")

    def _validate_logging_configuration(self) -> None:
        """Validate logging configuration."""
        print("\n📝 Logging Configuration")

        try:
            config = get_config()
            log_config = config.get_logging_config()

            # Validate log level
            log_level = log_config.get("level", "INFO")
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

            if log_level not in valid_levels:
                self._add_result(
                    False, f"Invalid log level: {log_level} (valid: {valid_levels})", "error"
                )
            else:
                # Check environment appropriateness
                if self.environment == "production" and log_level == "DEBUG":
                    self._add_result(
                        False, "DEBUG logging not recommended for production", "warning"
                    )
                elif self.environment == "development" and log_level in ["ERROR", "CRITICAL"]:
                    self._add_result(
                        False, f"Log level {log_level} too restrictive for development", "warning"
                    )
                else:
                    self._add_result(True, f"Log level appropriate: {log_level}", "info")

            # Validate file logging
            file_path = log_config.get("file_path")
            if file_path:
                log_dir = Path(file_path).parent
                if not log_dir.exists() and log_dir.is_absolute():
                    self._add_result(False, f"Log directory does not exist: {log_dir}", "error")
                else:
                    self._add_result(True, "Log file path configured", "info")

            # Check rotation settings
            if file_path:
                max_bytes = log_config.get("max_bytes")
                backup_count = log_config.get("backup_count")

                if not max_bytes:
                    self._add_result(False, "Log rotation max_bytes not configured", "warning")
                elif max_bytes < 1024 * 1024:  # 1MB
                    self._add_result(
                        False, f"Log rotation size too small: {max_bytes} bytes", "warning"
                    )

                if not backup_count or backup_count < 1:
                    self._add_result(
                        False, "Log rotation backup_count should be at least 1", "warning"
                    )

        except Exception as e:
            self._add_result(False, f"Logging configuration validation failed: {e}")

    def _validate_performance_settings(self) -> None:
        """Validate performance-related settings."""
        print("\n⚡ Performance Settings")

        try:
            config = get_config()

            # Validate worker counts
            max_workers = config.get_typed("processing.max_workers", int, 2)
            collection_workers = config.get_typed("collection.max_workers", int, 4)

            import os

            cpu_count = os.cpu_count() or 4

            if max_workers > cpu_count * 2:
                self._add_result(
                    False,
                    f"Too many processing workers: {max_workers} (CPU cores: {cpu_count})",
                    "warning",
                )
            elif max_workers < 1:
                self._add_result(False, "Processing workers must be at least 1", "error")
            else:
                self._add_result(True, f"Processing workers reasonable: {max_workers}", "info")

            # Validate cache settings
            cache_enabled = config.get_typed("features.cache_enabled", bool, True)
            if cache_enabled:
                cache_dir = config.get("cache.directory")
                if not cache_dir:
                    self._add_result(
                        False, "Cache enabled but no cache directory specified", "error"
                    )
                else:
                    self._add_result(True, "Cache configuration complete", "info")

            # Validate memory settings
            max_memory = config.get_typed("performance.max_memory_usage_mb", int, 512)
            if max_memory < 128:
                self._add_result(
                    False, f"Memory limit very low: {max_memory}MB (may cause issues)", "warning"
                )
            elif max_memory > 4096:
                self._add_result(
                    False,
                    f"Memory limit very high: {max_memory}MB (check available RAM)",
                    "warning",
                )
            else:
                self._add_result(True, f"Memory limit reasonable: {max_memory}MB", "info")

        except Exception as e:
            self._add_result(False, f"Performance settings validation failed: {e}")

    def _validate_component_integration(self) -> None:
        """Validate component integration configuration."""
        print("\n🧩 Component Integration")

        try:
            config = get_config()

            # Test configuration access patterns used by components
            test_configs = [
                ("maricopa_api_key", "Maricopa API Client"),
                ("database.uri", "Database Connection"),
                ("collection.target_zipcodes", "Data Collector"),
                ("logging.level", "Logging System"),
                ("processing.llm_model", "Data Processor"),
            ]

            for config_key, component in test_configs:
                try:
                    value = config.get(config_key)
                    if value is not None:
                        self._add_result(True, f"{component} configuration accessible", "info")
                    else:
                        severity = "warning" if config_key.startswith("processing.") else "error"
                        self._add_result(
                            False, f"{component} configuration missing: {config_key}", severity
                        )
                except Exception as e:
                    self._add_result(False, f"{component} configuration error: {e}", "error")

            # Test helper method functionality
            try:
                db_config = config.get_database_config()
                self._add_result(True, "Database configuration helper works", "info")
            except Exception as e:
                self._add_result(False, f"Database configuration helper failed: {e}", "error")

            try:
                log_config = config.get_logging_config()
                self._add_result(True, "Logging configuration helper works", "info")
            except Exception as e:
                self._add_result(False, f"Logging configuration helper failed: {e}", "error")

            try:
                collection_config = config.get_collection_config()
                self._add_result(True, "Collection configuration helper works", "info")
            except Exception as e:
                self._add_result(False, f"Collection configuration helper failed: {e}", "error")

        except Exception as e:
            self._add_result(False, f"Component integration validation failed: {e}")

    def _validate_production_requirements(self) -> None:
        """Validate production-specific requirements."""
        print("\n🏭 Production Requirements")

        try:
            config = get_config()

            # Required production settings
            production_requirements = {
                "security.secret_key": "Production secret key",
                "api.key": "Production API key",
                "monitoring.enabled": "Monitoring system",
            }

            for key, description in production_requirements.items():
                value = config.get(key)
                if not value:
                    self._add_result(
                        False, f"Missing production requirement: {description}", "error"
                    )
                else:
                    self._add_result(
                        True, f"Production requirement satisfied: {description}", "info"
                    )

            # Production security checks
            debug_mode = config.get_typed("debug", bool, False)
            if debug_mode:
                self._add_result(False, "Debug mode must be disabled in production", "error")

            log_level = config.get("logging.level", "INFO")
            if log_level == "DEBUG":
                self._add_result(False, "Debug logging should be disabled in production", "error")

            # Check for development indicators
            db_uri = config.get("database.uri", "")
            if "dev" in db_uri.lower() or "localhost" in db_uri:
                self._add_result(
                    False, "Production should not use development/local database", "error"
                )

        except Exception as e:
            self._add_result(False, f"Production requirements validation failed: {e}")

    def _validate_development_setup(self) -> None:
        """Validate development-specific setup."""
        print("\n🛠️  Development Setup")

        try:
            config = get_config()

            # Development recommendations
            debug_mode = config.get_typed("debug", bool, False)
            if not debug_mode:
                self._add_result(False, "Debug mode recommended for development", "warning")

            log_level = config.get("logging.level", "INFO")
            if log_level not in ["DEBUG", "INFO"]:
                self._add_result(
                    False,
                    f"Development logging should be DEBUG or INFO, not {log_level}",
                    "warning",
                )

            # Check for reasonable development limits
            rate_limit = config.get_typed("MARICOPA_RATE_LIMIT", int, 1000)
            if rate_limit > 100:
                self._add_result(
                    False,
                    f"Development rate limit high: {rate_limit} (consider lowering for safety)",
                    "warning",
                )

        except Exception as e:
            self._add_result(False, f"Development setup validation failed: {e}")

    def _validate_testing_setup(self) -> None:
        """Validate testing environment setup."""
        print("\n🧪 Testing Setup")

        try:
            config = get_config()

            # Testing should use test database
            db_uri = config.get("database.uri", "")
            db_name = config.get("database.name", "")

            if not ("test" in db_uri.lower() or "test" in db_name.lower()):
                self._add_result(False, "Testing environment should use test database", "warning")

            # Testing should have conservative settings
            rate_limit = config.get_typed("MARICOPA_RATE_LIMIT", int, 1000)
            if rate_limit > 50:
                self._add_result(
                    False, f"Testing rate limit should be low: {rate_limit}", "warning"
                )

        except Exception as e:
            self._add_result(False, f"Testing setup validation failed: {e}")

    def _validate_required_env_vars(self, required_vars: List[str]) -> None:
        """Validate required environment variables."""
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                self._add_result(False, f"Missing required environment variable: {var}", "error")
            else:
                self._add_result(True, f"Required environment variable present: {var}", "info")

    def _validate_recommended_env_vars(self, recommended_vars: List[str]) -> None:
        """Validate recommended environment variables."""
        for var in recommended_vars:
            value = os.environ.get(var)
            if not value:
                self._add_result(
                    False, f"Recommended environment variable not set: {var}", "warning"
                )
            else:
                self._add_result(True, f"Recommended environment variable set: {var}", "info")

    def _report_results(self) -> None:
        """Report validation results."""
        print("\n" + "=" * 60)
        print("📊 Configuration Validation Results")
        print("=" * 60)

        # Count results by severity
        error_count = len([r for r in self.results if r.severity == "error"])
        warning_count = len([r for r in self.results if r.severity == "warning"])
        info_count = len([r for r in self.results if r.severity == "info"])

        print(
            f"\nSummary: {error_count} errors, {warning_count} warnings, {info_count} checks passed"
        )

        # Group and display results
        if error_count > 0:
            print("\n❌ Errors:")
            for result in self.results:
                if result.severity == "error":
                    print(f"   {result.message}")

        if warning_count > 0:
            print("\n⚠️  Warnings:")
            for result in self.results:
                if result.severity == "warning":
                    print(f"   {result.message}")

        if info_count > 0 and error_count == 0:
            print("\n✅ Successful Checks:")
            for result in self.results:
                if result.severity == "info" and result.success:
                    print(f"   {result.message}")

        # Provide recommendations
        if error_count > 0:
            print("\n🔧 Recommended Actions:")
            print("   1. Fix all error conditions before deploying")
            print("   2. Review environment-specific requirements")
            print("   3. Validate credentials and API keys")
            print("   4. Re-run validation after fixes")
        elif warning_count > 0:
            print("\n💡 Recommendations:")
            print("   1. Review warning conditions")
            print("   2. Consider fixing warnings for optimal operation")
            print("   3. Use --strict for stricter validation")
        else:
            print("\n🎉 Configuration validation passed!")

        print("\n" + "=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate Phoenix Real Estate configuration")
    parser.add_argument(
        "--environment", help="Environment to validate (development, testing, production)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Strict mode: warnings are treated as failures"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run validation
    validator = ConfigurationValidator(environment=args.environment, strict_mode=args.strict)

    success = validator.validate_all()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
