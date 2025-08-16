#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Secrets Verification Script for Phoenix Real Estate Data Collector.

This script verifies that all required GitHub repository secrets are properly
configured and accessible to workflows.
"""

import os
import sys
import logging
import argparse
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, NamedTuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SecretValidationResult(NamedTuple):
    """Result of secret validation check."""
    secret_name: str
    is_configured: bool
    has_valid_format: bool
    environment: str
    error_message: Optional[str] = None
    warnings: List[str] = None


class EnvironmentSecrets(NamedTuple):
    """Environment-specific secret requirements."""
    environment: str
    required_secrets: List[str]
    optional_secrets: List[str] = []
    fallback_patterns: Dict[str, str] = {}


@dataclass
class GitHubSecretsValidator:
    """Validator for GitHub repository secrets configuration."""
    
    # Secret format patterns for validation
    SECRET_PATTERNS = {
        "TEST_MONGODB_PASSWORD": r"^.{8,}$",  # Minimum 8 characters
        "TEST_MARICOPA_API_KEY": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "TEST_WEBSHARE_API_KEY": r"^[a-zA-Z0-9\-]{20,}$",  # Typical WebShare format
        "TEST_CAPTCHA_API_KEY": r"^[a-zA-Z0-9]{20,}$",  # Typical 2captcha format
        "MONGODB_URL": r"^mongodb(\+srv)?://.*",
        "MARICOPA_API_KEY": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "WEBSHARE_API_KEY": r"^[a-zA-Z0-9\-]{20,}$",
        "CAPTCHA_API_KEY": r"^[a-zA-Z0-9]{20,}$",
    }
    
    # Environment-specific secret requirements
    ENVIRONMENTS = [
        EnvironmentSecrets(
            environment="test",
            required_secrets=[
                "TEST_MONGODB_PASSWORD",
                "TEST_MARICOPA_API_KEY", 
                "TEST_WEBSHARE_API_KEY",
                "TEST_CAPTCHA_API_KEY"
            ],
            fallback_patterns={
                "TEST_MARICOPA_API_KEY": "TEST_MARICOPA_API",
                "TEST_WEBSHARE_API_KEY": "TEST_WEBSHARE_API"
            }
        ),
        EnvironmentSecrets(
            environment="production",
            required_secrets=[
                "MONGODB_URL",
                "MARICOPA_API_KEY",
                "WEBSHARE_API_KEY", 
                "CAPTCHA_API_KEY"
            ],
            fallback_patterns={
                "MARICOPA_API_KEY": "MARICOPA_API",
                "WEBSHARE_API_KEY": "WEBSHARE_API"
            }
        )
    ]
    
    def validate_secret_format(self, secret_name: str, secret_value: str) -> tuple[bool, List[str]]:
        """Validate secret format against expected patterns."""
        warnings = []
        
        if secret_name in self.SECRET_PATTERNS:
            pattern = self.SECRET_PATTERNS[secret_name]
            if not re.match(pattern, secret_value):
                return False, [f"Secret {secret_name} does not match expected format pattern"]
        
        # Basic validations
        if not secret_value or secret_value.strip() == "":
            return False, ["Secret value is empty or whitespace only"]
            
        if secret_value in ["test-key", "your_key_here", "replace_me", "placeholder"]:
            return False, ["Secret appears to contain placeholder value"]
            
        # Warnings for potentially weak secrets
        if len(secret_value) < 10:
            warnings.append("Secret value is quite short, consider using a longer key")
            
        return True, warnings
    
    def validate_environment_secrets(self, environment: str) -> List[SecretValidationResult]:
        """Validate all secrets for a specific environment."""
        results = []
        
        # Find environment configuration
        env_config = None
        for env in self.ENVIRONMENTS:
            if env.environment == environment:
                env_config = env
                break
                
        if not env_config:
            logger.error(f"Unknown environment: {environment}")
            return []
            
        logger.info(f"Validating secrets for {environment} environment...")
        
        # Check required secrets
        for secret_name in env_config.required_secrets:
            secret_value = os.getenv(secret_name)
            
            # Check fallback if primary is missing
            if not secret_value and secret_name in env_config.fallback_patterns:
                fallback_name = env_config.fallback_patterns[secret_name]
                secret_value = os.getenv(fallback_name)
                if secret_value:
                    logger.info(f"Using fallback secret {fallback_name} for {secret_name}")
            
            if not secret_value:
                results.append(SecretValidationResult(
                    secret_name=secret_name,
                    is_configured=False,
                    has_valid_format=False,
                    environment=environment,
                    error_message=f"Required secret {secret_name} is not configured"
                ))
                continue
                
            # Validate format
            format_valid, warnings = self.validate_secret_format(secret_name, secret_value)
            
            results.append(SecretValidationResult(
                secret_name=secret_name,
                is_configured=True,
                has_valid_format=format_valid,
                environment=environment,
                error_message=None if format_valid else f"Invalid format for {secret_name}",
                warnings=warnings or []
            ))
            
        return results
    
    def generate_validation_report(self, environment: str) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        results = self.validate_environment_secrets(environment)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "environment": environment,
            "total_secrets": len(results),
            "configured_count": sum(1 for r in results if r.is_configured),
            "valid_format_count": sum(1 for r in results if r.has_valid_format),
            "missing_secrets": [r.secret_name for r in results if not r.is_configured],
            "invalid_format_secrets": [r.secret_name for r in results if r.is_configured and not r.has_valid_format],
            "all_warnings": [],
            "validation_passed": all(r.is_configured and r.has_valid_format for r in results),
            "results": [asdict(r) for r in results]
        }
        
        # Collect all warnings
        for result in results:
            if result.warnings:
                for warning in result.warnings:
                    report["all_warnings"].append(f"{result.secret_name}: {warning}")
        
        return report
    
    def check_workflow_compatibility(self) -> Dict[str, Any]:
        """Check if secrets are compatible with workflow requirements."""
        compatibility_report = {
            "ci_cd_compatible": True,
            "data_collection_compatible": True,
            "integration_tests_compatible": True,
            "e2e_tests_compatible": True,
            "issues": []
        }
        
        # Check test environment secrets for CI/CD compatibility
        test_results = self.validate_environment_secrets("test")
        test_secrets = {r.secret_name: r for r in test_results}
        
        required_for_ci = ["TEST_MONGODB_PASSWORD", "TEST_MARICOPA_API_KEY", "TEST_WEBSHARE_API_KEY"]
        for secret in required_for_ci:
            if secret not in test_secrets or not test_secrets[secret].is_configured:
                compatibility_report["ci_cd_compatible"] = False
                compatibility_report["integration_tests_compatible"] = False
                compatibility_report["issues"].append(f"CI/CD requires {secret} to be configured")
        
        # Check for E2E test requirements
        if "TEST_CAPTCHA_API_KEY" not in test_secrets or not test_secrets["TEST_CAPTCHA_API_KEY"].is_configured:
            compatibility_report["e2e_tests_compatible"] = False
            compatibility_report["issues"].append("E2E tests require TEST_CAPTCHA_API_KEY")
            
        return compatibility_report
    
    def simulate_github_actions_environment(self) -> Dict[str, Any]:
        """Simulate how secrets would be accessed in GitHub Actions."""
        simulation = {
            "simulated_secrets": {},
            "environment_url_construction": {},
            "potential_issues": []
        }
        
        # Test MongoDB URL construction
        mongodb_password = os.getenv("TEST_MONGODB_PASSWORD")
        if mongodb_password:
            simulated_url = f"mongodb://admin:{mongodb_password}@localhost:27017/"
            simulation["environment_url_construction"]["TEST_MONGODB_URL"] = simulated_url
            
            # Check for URL safety
            if " " in mongodb_password or "@" in mongodb_password:
                simulation["potential_issues"].append("MongoDB password contains characters that may cause URL parsing issues")
        else:
            simulation["potential_issues"].append("Cannot construct TEST_MONGODB_URL without TEST_MONGODB_PASSWORD")
        
        return simulation


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Verify GitHub repository secrets configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_github_secrets.py --environment test
  python verify_github_secrets.py --environment production --output-file report.json
  python verify_github_secrets.py --check-all --verbose
        """
    )
    
    parser.add_argument(
        "--environment", "-e",
        choices=["test", "production", "all"],
        default="test",
        help="Environment to validate secrets for"
    )
    
    parser.add_argument(
        "--output-file", "-o",
        help="Save validation report to JSON file"
    )
    
    parser.add_argument(
        "--check-workflow-compatibility",
        action="store_true",
        help="Check compatibility with workflow requirements"
    )
    
    parser.add_argument(
        "--simulate-github-actions",
        action="store_true", 
        help="Simulate GitHub Actions environment access"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = GitHubSecretsValidator()
    
    # Main validation
    if args.environment == "all":
        environments_to_check = ["test", "production"]
    else:
        environments_to_check = [args.environment]
    
    all_reports = {}
    overall_success = True
    
    for env in environments_to_check:
        logger.info(f"{'='*50}")
        logger.info(f"Validating {env.upper()} environment secrets")
        logger.info(f"{'='*50}")
        
        report = validator.generate_validation_report(env)
        all_reports[env] = report
        
        if not report["validation_passed"]:
            overall_success = False
        
        # Display results
        print(f"\n{env.upper()} Environment Results:")
        print(f"  Total secrets: {report['total_secrets']}")
        print(f"  Configured: {report['configured_count']}")
        print(f"  Valid format: {report['valid_format_count']}")
        print(f"  Validation passed: {'✅' if report['validation_passed'] else '❌'}")
        
        if report["missing_secrets"]:
            print(f"  Missing secrets: {', '.join(report['missing_secrets'])}")
            
        if report["invalid_format_secrets"]:
            print(f"  Invalid format: {', '.join(report['invalid_format_secrets'])}")
            
        if report["all_warnings"]:
            print("  Warnings:")
            for warning in report["all_warnings"]:
                print(f"    - {warning}")
    
    # Workflow compatibility check
    if args.check_workflow_compatibility:
        logger.info("\nChecking workflow compatibility...")
        compatibility = validator.check_workflow_compatibility()
        
        print("\nWorkflow Compatibility:")
        print(f"  CI/CD Pipeline: {'✅' if compatibility['ci_cd_compatible'] else '❌'}")
        print(f"  Integration Tests: {'✅' if compatibility['integration_tests_compatible'] else '❌'}")
        print(f"  E2E Tests: {'✅' if compatibility['e2e_tests_compatible'] else '❌'}")
        
        if compatibility["issues"]:
            print("  Issues:")
            for issue in compatibility["issues"]:
                print(f"    - {issue}")
    
    # GitHub Actions simulation
    if args.simulate_github_actions:
        logger.info("\nSimulating GitHub Actions environment...")
        simulation = validator.simulate_github_actions_environment()
        
        print("\nGitHub Actions Simulation:")
        for key, value in simulation["environment_url_construction"].items():
            print(f"  {key}: {value}")
            
        if simulation["potential_issues"]:
            print("  Potential Issues:")
            for issue in simulation["potential_issues"]:
                print(f"    - {issue}")
    
    # Save report if requested
    if args.output_file:
        full_report = {
            "validation_timestamp": datetime.now().isoformat(),
            "environments": all_reports,
            "overall_success": overall_success,
            "workflow_compatibility": validator.check_workflow_compatibility() if args.check_workflow_compatibility else None,
            "github_actions_simulation": validator.simulate_github_actions_environment() if args.simulate_github_actions else None
        }
        
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(full_report, f, indent=2)
        
        logger.info(f"Validation report saved to: {output_path}")
    
    # Exit with appropriate code
    if overall_success:
        print("\n✅ All validations passed!")
        sys.exit(0)
    else:
        print("\n❌ Validation failed - see details above")
        sys.exit(1)


if __name__ == "__main__":
    main()