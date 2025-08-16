#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Secrets Configuration Assistant for Phoenix Real Estate Data Collector.

This script provides step-by-step guidance for configuring missing repository
secrets that are preventing CI/CD workflows from running.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional
import json


@dataclass
class SecretConfig:
    """Configuration for a required secret."""
    name: str
    description: str
    environment: str
    format_hint: str
    example_value: str
    is_critical: bool = True
    fallback_name: Optional[str] = None


class GitHubSecretsSetupAssistant:
    """Assistant for GitHub repository secrets configuration."""
    
    def __init__(self):
        self.required_secrets = [
            SecretConfig(
                name="TEST_MONGODB_PASSWORD",
                description="Password for test MongoDB instance",
                environment="Default (no environment restriction)",
                format_hint="Minimum 8 characters, secure password",
                example_value="test_mongodb_secure_password_123",
                is_critical=True
            ),
            SecretConfig(
                name="TEST_MARICOPA_API_KEY",
                description="Maricopa County API key for testing",
                environment="Default (no environment restriction)", 
                format_hint="UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                example_value="12345678-90ab-cdef-1234-567890abcdef",
                is_critical=True,
                fallback_name="TEST_MARICOPA_API"
            ),
            SecretConfig(
                name="TEST_WEBSHARE_API_KEY",
                description="WebShare proxy API key for testing",
                environment="Default (no environment restriction)",
                format_hint="WebShare API key format (20+ characters)",
                example_value="abcdef12-3456-7890-abcd-ef1234567890",
                is_critical=True,
                fallback_name="TEST_WEBSHARE_API"
            ),
            SecretConfig(
                name="TEST_CAPTCHA_API_KEY", 
                description="2captcha API key for E2E testing",
                environment="Default (no environment restriction)",
                format_hint="2captcha API key format (20+ characters)",
                example_value="fedcba09-8765-4321-fedc-ba0987654321",
                is_critical=True
            )
        ]
    
    def display_setup_banner(self):
        """Display setup banner with current status."""
        print("=" * 70)
        print("🔧 GitHub Repository Secrets Configuration Assistant")
        print("=" * 70)
        print()
        print("⚠️  CRITICAL STATUS: CI/CD workflows are failing due to missing secrets!")
        print()
        print("This assistant will guide you through configuring the required")
        print("repository secrets to restore workflow functionality.")
        print()
    
    def display_missing_secrets_summary(self):
        """Display summary of missing secrets."""
        print("📋 MISSING SECRETS SUMMARY")
        print("-" * 30)
        print()
        
        for i, secret in enumerate(self.required_secrets, 1):
            status = "❌ MISSING"
            print(f"{i}. {secret.name}")
            print(f"   Status: {status}")
            print(f"   Purpose: {secret.description}")
            if secret.fallback_name:
                print(f"   Fallback: {secret.fallback_name}")
            print()
    
    def display_step_by_step_instructions(self):
        """Display step-by-step configuration instructions."""
        print("🎯 STEP-BY-STEP CONFIGURATION INSTRUCTIONS")
        print("=" * 50)
        print()
        
        print("STEP 1: Access Repository Settings")
        print("-" * 35)
        print("1. Navigate to your GitHub repository")
        print("2. Click 'Settings' (top navigation, right side)")
        print("3. In left sidebar, go to 'Secrets and variables' → 'Actions'")
        print()
        
        print("STEP 2: Configure Each Secret")
        print("-" * 30)
        print("Click 'New repository secret' and add each of the following:")
        print()
        
        for i, secret in enumerate(self.required_secrets, 1):
            print(f"Secret #{i}: {secret.name}")
            print(f"  Name: {secret.name}")
            print(f"  Value: [Request from admin - {secret.format_hint}]")
            print(f"  Environment: {secret.environment}")
            print(f"  Example format: {secret.example_value}")
            if secret.fallback_name:
                print(f"  Alternative name: {secret.fallback_name}")
            print()
    
    def display_verification_steps(self):
        """Display verification steps."""
        print("✅ STEP 3: Verify Configuration")
        print("-" * 32)
        print()
        print("After configuring all secrets, verify they work:")
        print()
        print("Method 1: Use Test Workflow")
        print("  1. Go to 'Actions' tab in repository")
        print("  2. Select 'Test Secrets Access' workflow")
        print("  3. Click 'Run workflow'")
        print("  4. Select 'test' environment")
        print("  5. Click 'Run workflow'")
        print("  6. Check that all secrets are marked as '✅ Available'")
        print()
        print("Method 2: Run CI/CD Pipeline")
        print("  1. Go to 'Actions' tab")
        print("  2. Select 'Continuous Integration & Deployment'")
        print("  3. Click 'Run workflow' on main branch")
        print("  4. Verify 'validate-secrets' job passes")
        print()
    
    def display_security_reminders(self):
        """Display security best practices."""
        print("🔒 SECURITY BEST PRACTICES")
        print("-" * 27)
        print()
        print("✅ Use test/sandbox API keys when available")
        print("❌ Never use production API keys for test secrets")
        print("✅ Generate strong, unique passwords for databases")
        print("❌ Never commit actual secret values to git")
        print("✅ Regularly rotate API keys and passwords")
        print("✅ Document secret ownership and renewal dates")
        print()
    
    def display_troubleshooting_guide(self):
        """Display troubleshooting guide."""
        print("🛠️  TROUBLESHOOTING GUIDE")
        print("-" * 24)
        print()
        
        troubleshooting_steps = [
            ("Workflow still fails after configuration", [
                "Verify all 4 secrets are configured exactly as specified",
                "Check that secrets are in 'Default' environment, not 'Production'",
                "Ensure secret names match exactly (case-sensitive)",
                "Try re-running the workflow after a few minutes"
            ]),
            ("API authentication errors in tests", [
                "Verify API keys are valid and not expired",
                "Ensure you're using test/sandbox keys, not production",
                "Check API key format matches expected pattern",
                "Test API keys manually if possible"
            ]),
            ("MongoDB connection failures", [
                "Verify TEST_MONGODB_PASSWORD is at least 8 characters",
                "Check password doesn't contain special characters that break URLs",
                "Ensure MongoDB container starts successfully in CI"
            ])
        ]
        
        for issue, solutions in troubleshooting_steps:
            print(f"Issue: {issue}")
            for solution in solutions:
                print(f"  → {solution}")
            print()
    
    def generate_configuration_checklist(self) -> Dict:
        """Generate configuration checklist for tracking progress."""
        checklist = {
            "configuration_checklist": {
                "repository_access": {
                    "description": "Access repository settings",
                    "completed": False,
                    "steps": [
                        "Navigate to repository Settings",
                        "Go to Secrets and variables → Actions"
                    ]
                },
                "secrets_configuration": {
                    "description": "Configure all required secrets",
                    "completed": False,
                    "secrets": {}
                },
                "verification": {
                    "description": "Verify secrets are accessible",
                    "completed": False,
                    "steps": [
                        "Run Test Secrets Access workflow",
                        "Verify all secrets show as available",
                        "Run CI/CD pipeline to confirm fix"
                    ]
                }
            },
            "contact_info": {
                "documentation": "docs/deployment/GITHUB_SECRETS_CONFIGURATION.md",
                "test_workflow": ".github/workflows/test-secrets-access.yml",
                "validation_script": "scripts/validation/verify_github_secrets.py"
            }
        }
        
        # Add individual secret tracking
        for secret in self.required_secrets:
            checklist["configuration_checklist"]["secrets_configuration"]["secrets"][secret.name] = {
                "configured": False,
                "description": secret.description,
                "format_hint": secret.format_hint,
                "fallback_name": secret.fallback_name
            }
        
        return checklist
    
    def save_checklist(self, filename: str = "secrets_configuration_checklist.json"):
        """Save configuration checklist to file."""
        checklist = self.generate_configuration_checklist()
        
        output_path = Path("reports") / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(checklist, f, indent=2)
        
        print(f"📄 Configuration checklist saved to: {output_path}")
        return output_path
    
    def run_interactive_setup(self):
        """Run interactive setup assistant."""
        self.display_setup_banner()
        self.display_missing_secrets_summary()
        self.display_step_by_step_instructions()
        self.display_verification_steps()
        self.display_security_reminders()
        self.display_troubleshooting_guide()
        
        print("📄 DOCUMENTATION AND RESOURCES")
        print("-" * 32)
        print("Detailed instructions: docs/deployment/GITHUB_SECRETS_CONFIGURATION.md")
        print("Test workflow: .github/workflows/test-secrets-access.yml")
        print("Python validator: scripts/validation/verify_github_secrets.py")
        print()
        
        # Save checklist
        self.save_checklist()
        
        print("🎯 NEXT ACTIONS")
        print("-" * 13)
        print("1. Follow the step-by-step instructions above")
        print("2. Configure all 4 missing secrets in repository settings")
        print("3. Run the test workflow to verify configuration")
        print("4. Check off items in the saved checklist as you complete them")
        print()
        print("⚠️  CI/CD workflows will remain broken until ALL secrets are configured!")
        print()


def main():
    """Main execution function."""
    assistant = GitHubSecretsSetupAssistant()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "checklist":
            checklist_path = assistant.save_checklist()
            print(f"Configuration checklist saved to: {checklist_path}")
        elif command == "summary":
            assistant.display_missing_secrets_summary()
        elif command == "instructions":
            assistant.display_step_by_step_instructions()
        elif command == "troubleshoot":
            assistant.display_troubleshooting_guide()
        else:
            print("Unknown command. Available commands: checklist, summary, instructions, troubleshoot")
            sys.exit(1)
    else:
        # Run full interactive setup
        assistant.run_interactive_setup()


if __name__ == "__main__":
    main()