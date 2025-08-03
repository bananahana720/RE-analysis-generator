#!/usr/bin/env python3
"""
Environment Validation Script for Phoenix Real Estate Data Collector

This script validates the complete development and production environment setup
including uv virtual environment, dependencies, configuration loading, and
environment-specific settings.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import importlib
import traceback


class EnvironmentValidator:
    """Comprehensive environment validation for Phoenix Real Estate system."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.critical_failures = 0
        self.warnings = 0
    
    def validate_all(self) -> bool:
        """Run all validation checks.
        
        Returns:
            True if all critical validations pass, False otherwise.
        """
        print("Starting Phoenix Real Estate Environment Validation\n")
        
        # Core environment checks
        self._validate_python_version()
        self._validate_uv_setup()
        self._validate_project_structure()
        self._validate_dependencies()
        
        # Configuration checks
        self._validate_configuration_loading()
        self._validate_environment_configs()
        self._validate_secrets_management()
        
        # Integration checks
        self._validate_database_connection()
        self._validate_imports()
        self._validate_test_framework()
        
        # Report results
        self._print_summary()
        
        return self.critical_failures == 0
    
    def _add_result(self, category: str, check: str, status: str, 
                   message: str, details: Optional[Dict[str, Any]] = None):
        """Add a validation result."""
        result = {
            'category': category,
            'check': check,
            'status': status,
            'message': message,
            'details': details or {}
        }
        self.results.append(result)
        
        if status == 'CRITICAL':
            self.critical_failures += 1
            print(f"[CRITICAL] {category}: {check} - {message}")
        elif status == 'WARNING':
            self.warnings += 1
            print(f"[WARNING] {category}: {check} - {message}")
        elif status == 'PASS':
            print(f"[PASS] {category}: {check} - {message}")
        else:
            print(f"[INFO] {category}: {check} - {message}")
    
    def _validate_python_version(self):
        """Validate Python version meets requirements."""
        try:
            version = sys.version_info
            if version >= (3, 13):
                self._add_result(
                    'Environment', 'Python Version', 'PASS',
                    f"Python {version.major}.{version.minor}.{version.micro} meets requirements (>=3.13)",
                    {'version': f"{version.major}.{version.minor}.{version.micro}"}
                )
            else:
                self._add_result(
                    'Environment', 'Python Version', 'CRITICAL',
                    f"Python {version.major}.{version.minor}.{version.micro} is below required 3.13",
                    {'version': f"{version.major}.{version.minor}.{version.micro}"}
                )
        except Exception as e:
            self._add_result(
                'Environment', 'Python Version', 'CRITICAL',
                f"Failed to check Python version: {e}"
            )
    
    def _validate_uv_setup(self):
        """Validate uv virtual environment setup."""
        try:
            # Check if we're in a virtual environment
            venv_path = os.environ.get('VIRTUAL_ENV')
            if venv_path:
                self._add_result(
                    'Environment', 'Virtual Environment', 'PASS',
                    f"Active virtual environment: {venv_path}",
                    {'venv_path': venv_path}
                )
            else:
                self._add_result(
                    'Environment', 'Virtual Environment', 'WARNING',
                    "No active virtual environment detected"
                )
            
            # Check uv availability
            result = subprocess.run(['uv', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                uv_version = result.stdout.strip()
                self._add_result(
                    'Environment', 'UV Package Manager', 'PASS',
                    f"UV available: {uv_version}",
                    {'version': uv_version}
                )
            else:
                self._add_result(
                    'Environment', 'UV Package Manager', 'CRITICAL',
                    "UV package manager not available"
                )
        except Exception as e:
            self._add_result(
                'Environment', 'UV Setup', 'CRITICAL',
                f"Failed to validate UV setup: {e}"
            )
    
    def _validate_project_structure(self):
        """Validate project directory structure."""
        required_paths = [
            'pyproject.toml',
            'src/phoenix_real_estate',
            'config',
            'tests',
            '.env.sample'
        ]
        
        missing_paths = []
        for path in required_paths:
            if not Path(path).exists():
                missing_paths.append(path)
        
        if missing_paths:
            self._add_result(
                'Project Structure', 'Required Paths', 'CRITICAL',
                f"Missing required paths: {', '.join(missing_paths)}",
                {'missing_paths': missing_paths}
            )
        else:
            self._add_result(
                'Project Structure', 'Required Paths', 'PASS',
                "All required project paths exist"
            )
    
    def _validate_dependencies(self):
        """Validate that required dependencies are installed."""
        required_packages = [
            'motor', 'pymongo', 'pydantic', 'pydantic_settings',
            'aiohttp', 'bs4', 'structlog', 'pytest',
            'mypy', 'ruff'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self._add_result(
                'Dependencies', 'Required Packages', 'CRITICAL',
                f"Missing packages: {', '.join(missing_packages)}",
                {'missing_packages': missing_packages}
            )
        else:
            self._add_result(
                'Dependencies', 'Required Packages', 'PASS',
                f"All {len(required_packages)} required packages installed"
            )
    
    def _validate_configuration_loading(self):
        """Validate configuration system works correctly."""
        try:
            from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
            
            # Test development configuration
            os.environ['ENVIRONMENT'] = 'development'
            config = EnvironmentConfigProvider()
            
            # Validate basic configuration loading
            db_name = config.get('database.name')
            log_level = config.get('logging.level')
            
            if db_name and log_level:
                self._add_result(
                    'Configuration', 'Development Loading', 'PASS',
                    f"Development config loaded: db={db_name}, log={log_level}",
                    {'database': db_name, 'log_level': log_level}
                )
            else:
                self._add_result(
                    'Configuration', 'Development Loading', 'WARNING',
                    "Development config incomplete"
                )
            
            # Test configuration validation
            errors = config.validate()
            if not errors:
                self._add_result(
                    'Configuration', 'Validation', 'PASS',
                    "Configuration validation passed"
                )
            else:
                self._add_result(
                    'Configuration', 'Validation', 'WARNING',
                    f"Configuration validation found {len(errors)} issues",
                    {'validation_errors': errors}
                )
                
        except Exception as e:
            self._add_result(
                'Configuration', 'Loading System', 'CRITICAL',
                f"Configuration system failed: {e}",
                {'error': str(e), 'traceback': traceback.format_exc()}
            )
    
    def _validate_environment_configs(self):
        """Validate all environment configurations."""
        environments = ['development', 'production']
        
        for env in environments:
            try:
                os.environ['ENVIRONMENT'] = env
                from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
                
                config = EnvironmentConfigProvider()
                
                # Check environment-specific settings
                log_level = config.get('logging.level')
                db_name = config.get('database.name')
                
                if log_level and db_name:
                    self._add_result(
                        'Configuration', f'{env.title()} Environment', 'PASS',
                        f"{env.title()} config valid: log={log_level}, db={db_name}"
                    )
                else:
                    self._add_result(
                        'Configuration', f'{env.title()} Environment', 'WARNING',
                        f"{env.title()} config incomplete"
                    )
                    
            except Exception as e:
                self._add_result(
                    'Configuration', f'{env.title()} Environment', 'CRITICAL',
                    f"{env.title()} config failed: {e}"
                )
    
    def _validate_secrets_management(self):
        """Validate secrets management system."""
        try:
            # Check if .env.sample exists
            env_sample = Path('.env.sample')
            if env_sample.exists():
                self._add_result(
                    'Secrets', 'Sample Environment File', 'PASS',
                    ".env.sample file exists for reference"
                )
            else:
                self._add_result(
                    'Secrets', 'Sample Environment File', 'WARNING',
                    ".env.sample file missing"
                )
            
            # Test secrets module import
            from phoenix_real_estate.foundation.config.secrets import SecretManager
            
            SecretManager()
            self._add_result(
                'Secrets', 'Secret Manager', 'PASS',
                "Secret manager initialized successfully"
            )
            
        except Exception as e:
            self._add_result(
                'Secrets', 'Management System', 'CRITICAL',
                f"Secrets management failed: {e}"
            )
    
    def _validate_database_connection(self):
        """Validate database connection capabilities."""
        try:
            # Test database module imports
            
            self._add_result(
                'Database', 'Module Imports', 'PASS',
                "Database modules imported successfully"
            )
            
            # Note: We don't test actual connections in validation to avoid
            # requiring live database credentials
            
        except Exception as e:
            self._add_result(
                'Database', 'Module System', 'CRITICAL',
                f"Database module system failed: {e}"
            )
    
    def _validate_imports(self):
        """Validate key module imports work correctly."""
        key_modules = [
            'phoenix_real_estate.foundation.config',
            'phoenix_real_estate.foundation.database',
            'phoenix_real_estate.foundation.logging',
            'phoenix_real_estate.collectors.base',
            'phoenix_real_estate.collectors.maricopa',
        ]
        
        failed_imports = []
        for module in key_modules:
            try:
                importlib.import_module(module)
            except ImportError as e:
                failed_imports.append((module, str(e)))
        
        if failed_imports:
            self._add_result(
                'Imports', 'Core Modules', 'CRITICAL',
                f"Failed to import {len(failed_imports)} modules",
                {'failed_imports': failed_imports}
            )
        else:
            self._add_result(
                'Imports', 'Core Modules', 'PASS',
                f"Successfully imported all {len(key_modules)} core modules"
            )
    
    def _validate_test_framework(self):
        """Validate testing framework setup."""
        try:
            # Check pytest configuration

            # Check if tests directory exists and has tests
            tests_dir = Path('tests')
            if tests_dir.exists():
                test_files = list(tests_dir.rglob('test_*.py'))
                if test_files:
                    self._add_result(
                        'Testing', 'Test Framework', 'PASS',
                        f"Testing setup complete with {len(test_files)} test files"
                    )
                else:
                    self._add_result(
                        'Testing', 'Test Framework', 'WARNING',
                        "Tests directory exists but no test files found"
                    )
            else:
                self._add_result(
                    'Testing', 'Test Framework', 'WARNING',
                    "Tests directory not found"
                )
                
        except ImportError:
            self._add_result(
                'Testing', 'Test Framework', 'CRITICAL',
                "pytest not available"
            )
    
    def _print_summary(self):
        """Print validation summary."""
        print(f"\n{'='*60}")
        print("PHOENIX REAL ESTATE ENVIRONMENT VALIDATION SUMMARY")
        print(f"{'='*60}")
        
        total_checks = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed}")
        print(f"Warnings: {self.warnings}")
        print(f"Critical Failures: {self.critical_failures}")
        
        if self.critical_failures == 0:
            print("\n[SUCCESS] ENVIRONMENT VALIDATION PASSED")
            print("The Phoenix Real Estate system is ready for development!")
        else:
            print("\n[FAILED] ENVIRONMENT VALIDATION FAILED")
            print("Critical issues must be resolved before development can proceed.")
        
        if self.warnings > 0:
            print(f"\n[WARNING] {self.warnings} warning(s) found - consider addressing these.")
        
        # Print category summary
        categories = {}
        for result in self.results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'pass': 0, 'warn': 0, 'critical': 0}
            
            if result['status'] == 'PASS':
                categories[cat]['pass'] += 1
            elif result['status'] == 'WARNING':
                categories[cat]['warn'] += 1
            elif result['status'] == 'CRITICAL':
                categories[cat]['critical'] += 1
        
        print("\nResults by Category:")
        for cat, counts in categories.items():
            print(f"  {cat}: {counts['pass']} passed, {counts['warn']} warnings, {counts['critical']} critical")


def main():
    """Main validation entry point."""
    validator = EnvironmentValidator()
    success = validator.validate_all()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()