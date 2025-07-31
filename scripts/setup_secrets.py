#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secrets setup script for Phoenix Real Estate Data Collector.
"""

import os
import sys
import json
import hashlib
import logging
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from phoenix_real_estate.foundation.config.secrets import SecretManager
except ImportError:
    # Mock for testing when package not installed
    class SecretManager:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SecretsSetup:
    """Handles secrets setup, validation, and GitHub Actions configuration."""
    
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    rotation_log: List[Dict[str, Any]] = field(default_factory=list)
    
    REQUIRED_SECRETS = ["MONGODB_URI", "SECRET_KEY", "MARICOPA_API_KEY"]
    RECOMMENDED_SECRETS = ["WEBSHARE_API_KEY", "CAPTCHA_API_KEY"]
    
    SECRET_PATTERNS = {
        "MARICOPA_API_KEY": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "MONGODB_URI": r"^mongodb(\+srv)?://.*",
        "SECRET_KEY": r"^.{32,}$",
        "WEBSHARE_API_KEY": r"^[a-z0-9]{32,}$",
        "CAPTCHA_API_KEY": r"^[a-z0-9]{32,}$"
    }
    
    def validate_env_file(self, env_file_path: str) -> bool:
        self.validation_errors.clear()
        self.validation_warnings.clear()
        
        if not Path(env_file_path).exists():
            self.validation_errors.append(f"Environment file not found: {env_file_path}")
            return False
        
        try:
            env_vars = self.load_env_variables(env_file_path)
            
            for secret in self.REQUIRED_SECRETS:
                if secret not in env_vars or not env_vars[secret].strip():
                    self.validation_errors.append(f"Missing required secret: {secret}")
                else:
                    if not self.validate_secret_format(secret, env_vars[secret]):
                        self.validation_errors.append(f"Invalid format for secret: {secret}")
            
            return len(self.validation_errors) == 0
            
        except Exception as e:
            self.validation_errors.append(f"Error reading env file: {str(e)}")
            return False
    
    def load_env_variables(self, env_file_path: str) -> Dict[str, str]:
        env_vars = {}
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
        return env_vars
    
    def validate_secret_format(self, secret_name: str, secret_value: str) -> bool:
        if secret_name in self.SECRET_PATTERNS:
            pattern = self.SECRET_PATTERNS[secret_name]
            return bool(re.match(pattern, secret_value))
        return len(secret_value.strip()) > 0
    
    def check_secret_strength(self, secret_name: str, secret_value: str) -> bool:
        min_lengths = {"SECRET_KEY": 32, "MARICOPA_API_KEY": 30}
        min_length = min_lengths.get(secret_name, 8)
        return len(secret_value) >= min_length
    
    def generate_github_config(self, env_file_path: str) -> Dict[str, Any]:
        env_vars = self.load_env_variables(env_file_path)
        repository_secrets = {}
        environment_secrets = {"production": {}, "staging": {}}
        
        for secret, value in env_vars.items():
            category = self.categorize_secret(secret)
            if category in ["database", "encryption"]:
                repository_secrets[secret] = f"<{secret}_VALUE>"
            else:
                environment_secrets["production"][secret] = f"<{secret}_PROD_VALUE>"
        
        return {"secrets": {"repository_secrets": repository_secrets, "environment_secrets": environment_secrets}}
    
    def categorize_secret(self, secret_name: str) -> str:
        if "API_KEY" in secret_name:
            return "api_keys"
        elif "MONGODB" in secret_name:
            return "database"
        elif "SECRET_KEY" in secret_name:
            return "encryption"
        return "other"
    
    def track_secret_rotation(self, secret_name: str, old_value: str, new_value: str) -> Dict[str, Any]:
        return {
            "secret_name": secret_name,
            "rotated_at": datetime.now().isoformat(),
            "old_value_hash": hashlib.sha256(old_value.encode()).hexdigest()[:16],
            "new_value_hash": hashlib.sha256(new_value.encode()).hexdigest()[:16]
        }
    
    def log_secret_access(self, secret_name: str, operation: str, success: bool = True) -> None:
        logger.info(f"Secret access: {secret_name} | operation={operation} | success={success}")
    
    def log_validation_result(self, secret_name: str, is_valid: bool, reason: str) -> None:
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"Secret validation: {secret_name} | status={status} | reason={reason}")
    
    def create_env_backup(self, env_file_path: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{env_file_path}.{timestamp}.backup"
        with open(env_file_path, "r") as original:
            with open(backup_path, "w") as backup:
                backup.write(original.read())
        return backup_path
    
    def export_github_secrets_json(self, env_file_path: str) -> str:
        config = self.generate_github_config(env_file_path)
        export_path = Path(env_file_path).parent / "github_secrets.json"
        with open(export_path, "w") as f:
            json.dump(config["secrets"], f, indent=2)
        return str(export_path)


def main():
    parser = argparse.ArgumentParser(description="Phoenix Real Estate Secrets Setup")
    subparsers = parser.add_subparsers(dest="command")
    
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("env_file")
    
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("env_file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    setup = SecretsSetup()
    
    if args.command == "validate":
        print(f"Validating {args.env_file}...")
        is_valid = setup.validate_env_file(args.env_file)
        print("Validation passed\!" if is_valid else "Validation failed\!")
    
    elif args.command == "generate":
        print(f"Generating GitHub secrets configuration from {args.env_file}...")
        config = setup.generate_github_config(args.env_file)
        print("✅ Configuration generated")


if __name__ == "__main__":
    main()
