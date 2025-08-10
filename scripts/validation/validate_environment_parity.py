#!/usr/bin/env python3
"""
Environment Parity Validation Script
Validates configuration consistency across development, testing, and production environments
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

import yaml


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue."""
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'configuration', 'service', 'security', 'performance'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    
@dataclass
class ValidationResult:
    """Results of environment validation."""
    environment: str
    status: str  # 'pass', 'fail', 'warning'
    issues: List[ValidationIssue] = field(default_factory=list)
    config_data: Dict[str, Any] = field(default_factory=dict)


class EnvironmentParityValidator:
    """Validates configuration parity across environments."""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.logger = self._setup_logging()
        self.environments = ['development', 'testing', 'production']
        self.configs: Dict[str, Dict[str, Any]] = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for validation."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_environment_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all environment configurations."""
        configs = {}
        
        for env in self.environments:
            config_path = self.config_dir / "environments" / f"{env}.yaml"
            
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        configs[env] = yaml.safe_load(f)
                    self.logger.info(f"Loaded configuration for {env}")
                except Exception as e:
                    self.logger.error(f"Failed to load {env} config: {e}")
                    configs[env] = {}
            else:
                self.logger.warning(f"Configuration file not found for {env}")
                configs[env] = {}
                
        # Load base service configuration
        base_services_path = self.config_dir / "services" / "base-services.yaml"
        if base_services_path.exists():
            try:
                with open(base_services_path, 'r') as f:
                    configs['base_services'] = yaml.safe_load(f)
            except Exception as e:
                self.logger.error(f"Failed to load base services config: {e}")
                configs['base_services'] = {}
        
        self.configs = configs
        return configs
        
    def validate_environment(self, env_name: str) -> ValidationResult:
        """Validate a specific environment configuration."""
        result = ValidationResult(environment=env_name, status='pass')
        
        if env_name not in self.configs:
            result.issues.append(ValidationIssue(
                severity='error',
                category='configuration',
                message=f'Configuration file missing for environment: {env_name}',
                details={'expected_path': f'config/environments/{env_name}.yaml'}
            ))
            result.status = 'fail'
            return result
            
        config = self.configs[env_name]
        result.config_data = config
        
        # Validate required sections
        self._validate_required_sections(config, result)
        
        # Validate service configurations
        self._validate_service_configs(config, result)
        
        # Validate environment variables
        self._validate_environment_variables(config, result)
        
        # Validate health checks
        self._validate_health_checks(config, result)
        
        # Validate security settings
        self._validate_security_settings(config, result)
        
        # Environment-specific validations
        self._validate_environment_specific(env_name, config, result)
        
        # Determine overall status
        if any(issue.severity == 'error' for issue in result.issues):
            result.status = 'fail'
        elif any(issue.severity == 'warning' for issue in result.issues):
            result.status = 'warning'
        else:
            result.status = 'pass'
            
        return result
        
    def _validate_required_sections(self, config: Dict[str, Any], result: ValidationResult):
        """Validate that required configuration sections exist."""
        required_sections = [
            'environment',
            'services',
            'logging',
            'collection',
            'sources',
            'processing',
            'validation',
            'performance',
            'error_handling',
            'features',
            'health_checks',
            'security'
        ]
        
        for section in required_sections:
            if section not in config:
                result.issues.append(ValidationIssue(
                    severity='error',
                    category='configuration',
                    message=f'Missing required configuration section: {section}',
                    details={'section': section}
                ))
                
    def _validate_service_configs(self, config: Dict[str, Any], result: ValidationResult):
        """Validate service configurations."""
        services = config.get('services', {})
        
        # Validate MongoDB configuration
        mongodb_config = services.get('mongodb', {})
        if not mongodb_config:
            result.issues.append(ValidationIssue(
                severity='error',
                category='service',
                message='MongoDB service configuration missing',
                details={'service': 'mongodb'}
            ))
        else:
            # Check required MongoDB fields
            required_mongodb_fields = ['connection_string', 'database']
            for field in required_mongodb_fields:
                if field not in mongodb_config:
                    result.issues.append(ValidationIssue(
                        severity='error',
                        category='service',
                        message=f'MongoDB missing required field: {field}',
                        details={'service': 'mongodb', 'field': field}
                    ))
                    
        # Validate Ollama configuration
        ollama_config = services.get('ollama', {})
        if not ollama_config:
            result.issues.append(ValidationIssue(
                severity='error',
                category='service',
                message='Ollama service configuration missing',
                details={'service': 'ollama'}
            ))
        else:
            # Check required Ollama fields
            required_ollama_fields = ['base_url', 'model', 'timeout']
            for field in required_ollama_fields:
                if field not in ollama_config:
                    result.issues.append(ValidationIssue(
                        severity='warning',
                        category='service',
                        message=f'Ollama missing recommended field: {field}',
                        details={'service': 'ollama', 'field': field}
                    ))
                    
    def _validate_environment_variables(self, config: Dict[str, Any], result: ValidationResult):
        """Validate environment variable usage."""
        # Check for proper environment variable syntax
        config_str = yaml.dump(config)
        
        # Look for environment variable patterns
        import re
        env_var_pattern = r'\$\{([^}]+)\}'
        env_vars = re.findall(env_var_pattern, config_str)
        
        # Secret variables that should not have defaults
        secret_vars = {
            'MONGODB_URL', 'MARICOPA_API_KEY', 'WEBSHARE_API_KEY', 
            'CAPTCHA_API_KEY', 'SECRET_KEY', 'PARTICLE_API_KEY'
        }
        
        for env_var in env_vars:
            # Check for proper default value syntax
            if ':-' not in env_var:
                # Only warn for non-secret variables without defaults
                var_name = env_var.split(':-')[0] if ':-' in env_var else env_var
                if var_name not in secret_vars:
                    result.issues.append(ValidationIssue(
                        severity='info',
                        category='configuration',
                        message=f'Non-secret environment variable without default value: {env_var}',
                        details={'env_var': env_var}
                    ))
                
    def _validate_health_checks(self, config: Dict[str, Any], result: ValidationResult):
        """Validate health check configurations."""
        health_checks = config.get('health_checks', {})
        
        # Check that basic health checks are configured
        expected_health_checks = ['mongodb', 'ollama', 'system']
        
        for check in expected_health_checks:
            if check not in health_checks:
                result.issues.append(ValidationIssue(
                    severity='warning',
                    category='configuration',
                    message=f'Health check not configured for service: {check}',
                    details={'service': check}
                ))
                
    def _validate_security_settings(self, config: Dict[str, Any], result: ValidationResult):
        """Validate security configurations."""
        security = config.get('security', {})
        environment_name = config.get('environment', {}).get('name', 'unknown')
        
        # Skip general security validation for testing - will be handled in environment-specific validation
        if environment_name == 'testing':
            return
            
        # Check for security best practices (production and development)
        if not security.get('encrypt_sensitive_logs', False):
            severity = 'error' if environment_name == 'production' else 'warning'
            result.issues.append(ValidationIssue(
                severity=severity,
                category='security',
                message='Sensitive log encryption disabled',
                details={'setting': 'encrypt_sensitive_logs'}
            ))
            
        if not security.get('sanitize_raw_data', False):
            severity = 'error' if environment_name == 'production' else 'warning'
            result.issues.append(ValidationIssue(
                severity=severity,
                category='security',
                message='Raw data sanitization disabled',
                details={'setting': 'sanitize_raw_data'}
            ))
            
    def _validate_environment_specific(self, env_name: str, config: Dict[str, Any], result: ValidationResult):
        """Validate environment-specific requirements."""
        if env_name == 'production':
            # Production-specific validations
            self._validate_production_config(config, result)
        elif env_name == 'testing':
            # Testing-specific validations
            self._validate_testing_config(config, result)
        elif env_name == 'development':
            # Development-specific validations
            self._validate_development_config(config, result)
            
    def _validate_production_config(self, config: Dict[str, Any], result: ValidationResult):
        """Validate production-specific requirements."""
        # Check logging configuration
        logging_config = config.get('logging', {})
        if logging_config.get('level') != 'INFO':
            result.issues.append(ValidationIssue(
                severity='warning',
                category='configuration',
                message='Production should use INFO log level',
                details={'current_level': logging_config.get('level')}
            ))
            
        if logging_config.get('format') != 'json':
            result.issues.append(ValidationIssue(
                severity='warning',
                category='configuration',
                message='Production should use JSON log format',
                details={'current_format': logging_config.get('format')}
            ))
            
        # Check security settings
        security = config.get('security', {})
        if not security.get('encrypt_sensitive_logs', False):
            result.issues.append(ValidationIssue(
                severity='error',
                category='security',
                message='Production must encrypt sensitive logs',
                details={'setting': 'encrypt_sensitive_logs'}
            ))
            
        # Check feature flags
        features = config.get('features', {})
        if features.get('debug_mode', False):
            result.issues.append(ValidationIssue(
                severity='error',
                category='security',
                message='Debug mode should be disabled in production',
                details={'setting': 'debug_mode'}
            ))
            
    def _validate_testing_config(self, config: Dict[str, Any], result: ValidationResult):
        """Validate testing-specific requirements."""
        # Check that external APIs are disabled
        features = config.get('features', {})
        if features.get('external_apis_enabled', True):
            result.issues.append(ValidationIssue(
                severity='error',
                category='configuration',
                message='External APIs should be disabled in testing',
                details={'setting': 'external_apis_enabled'}
            ))
            
        # Check that caching is disabled
        performance = config.get('performance', {})
        if performance.get('enable_caching', True):
            result.issues.append(ValidationIssue(
                severity='warning',
                category='configuration',
                message='Caching should be disabled for consistent tests',
                details={'setting': 'enable_caching'}
            ))
            
        # In testing, relaxed security is acceptable for debugging
        security = config.get('security', {})
        if not security.get('encrypt_sensitive_logs', False):
            result.issues.append(ValidationIssue(
                severity='info',
                category='security',
                message='Sensitive log encryption disabled (acceptable for testing)',
                details={'setting': 'encrypt_sensitive_logs'}
            ))
            
        if not security.get('sanitize_raw_data', False):
            result.issues.append(ValidationIssue(
                severity='info',
                category='security',
                message='Raw data sanitization disabled (acceptable for testing)',
                details={'setting': 'sanitize_raw_data'}
            ))
            
    def _validate_development_config(self, config: Dict[str, Any], result: ValidationResult):
        """Validate development-specific requirements."""
        # Check logging configuration
        logging_config = config.get('logging', {})
        if logging_config.get('level') != 'DEBUG':
            result.issues.append(ValidationIssue(
                severity='info',
                category='configuration',
                message='Development may want DEBUG log level',
                details={'current_level': logging_config.get('level')}
            ))
            
    def validate_parity_across_environments(self) -> List[ValidationIssue]:
        """Validate configuration parity across environments."""
        issues = []
        
        # Check for critical configuration differences
        critical_sections = ['services', 'health_checks']
        
        for section in critical_sections:
            section_configs = {}
            
            for env in self.environments:
                if env in self.configs:
                    section_configs[env] = self.configs[env].get(section, {})
                    
            # Compare service configurations
            if section == 'services':
                issues.extend(self._validate_service_parity(section_configs))
                
        return issues
        
    def _validate_service_parity(self, service_configs: Dict[str, Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate service configuration parity."""
        issues = []
        
        # Check MongoDB configuration consistency
        mongodb_configs = {
            env: config.get('mongodb', {})
            for env, config in service_configs.items()
        }
        
        # Check for consistent database naming patterns
        databases = {}
        for env, mongodb_config in mongodb_configs.items():
            db_name = mongodb_config.get('database', '')
            if db_name:
                databases[env] = db_name
                
        # Validate database naming consistency
        if len(databases) > 1:
            # Extract expected database names (handle template variables)
            cleaned_databases = {}
            for env, db_name in databases.items():
                # Handle template variables like ${MONGODB_DATABASE:-phoenix_real_estate_dev}
                if db_name.startswith('${') and ':-' in db_name:
                    # Extract default value from ${VAR:-default} pattern
                    default_value = db_name.split(':-')[1].rstrip('}')
                    cleaned_databases[env] = default_value
                else:
                    cleaned_databases[env] = db_name
                    
            # Determine base name from production or any available environment
            base_name = None
            if 'production' in cleaned_databases:
                base_name = cleaned_databases['production']
            else:
                # Try to infer from development or testing
                for env, db_name in cleaned_databases.items():
                    if env == 'development' and db_name.endswith('_dev'):
                        base_name = db_name[:-4]  # Remove '_dev'
                        break
                    elif env == 'testing' and db_name.endswith('_test'):
                        base_name = db_name[:-5]  # Remove '_test'
                        break
                        
            if base_name:
                for env, db_name in cleaned_databases.items():
                    expected_suffix = {'development': '_dev', 'testing': '_test', 'production': ''}
                    expected_name = base_name + expected_suffix.get(env, '')
                    
                    if db_name != expected_name:
                        issues.append(ValidationIssue(
                            severity='info',
                            category='configuration',
                            message=f'Database name follows non-standard pattern in {env}',
                            details={
                                'environment': env,
                                'current': db_name,
                                'suggested': expected_name,
                                'base_name': base_name
                            }
                        ))
                        
        return issues
        
    def print_validation_report(self, results: List[ValidationResult]) -> bool:
        """Print validation report and return overall success status."""
        print("\n=== Environment Parity Validation Report ===")
        print(f"Validation Time: {__import__('time').strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 50)
        
        overall_success = True
        
        for result in results:
            status_icon = {
                'pass': '[PASS]',
                'fail': '[FAIL]',  
                'warning': '[WARN]'
            }.get(result.status, '[UNKN]')
            
            print(f"\n{status_icon} Environment: {result.environment.upper()}")
            print(f"   Status: {result.status}")
            
            if result.issues:
                print(f"   Issues: {len(result.issues)}")
                
                # Group issues by severity
                errors = [i for i in result.issues if i.severity == 'error']
                warnings = [i for i in result.issues if i.severity == 'warning']
                info = [i for i in result.issues if i.severity == 'info']
                
                if errors:
                    print(f"     Errors: {len(errors)}")
                    for issue in errors[:3]:  # Show first 3 errors
                        print(f"       - {issue.message}")
                        
                if warnings:
                    print(f"     Warnings: {len(warnings)}")
                    for issue in warnings[:3]:  # Show first 3 warnings
                        print(f"       - {issue.message}")
                        
                if info:
                    print(f"     Info: {len(info)}")
                    
                if result.status == 'fail':
                    overall_success = False
                    
        # Check cross-environment parity
        parity_issues = self.validate_parity_across_environments()
        if parity_issues:
            print(f"\n[WARN] Cross-Environment Issues: {len(parity_issues)}")
            for issue in parity_issues[:5]:  # Show first 5
                print(f"   - {issue.message}")
                
        print("\n" + "=" * 50)
        
        if overall_success and not parity_issues:
            print("[SUCCESS] Overall Status: VALIDATION PASSED")
            print("All environments have consistent configuration.")
        else:
            print("[FAILED] Overall Status: VALIDATION FAILED")
            print("Configuration inconsistencies found that need attention.")
            overall_success = False
            
        return overall_success
        
    def export_json_report(self, results: List[ValidationResult], output_path: str):
        """Export validation results to JSON file."""
        report_data = {
            'timestamp': __import__('time').strftime('%Y-%m-%dT%H:%M:%SZ'),
            'overall_status': 'pass' if all(r.status == 'pass' for r in results) else 'fail',
            'environments': []
        }
        
        for result in results:
            env_data = {
                'name': result.environment,
                'status': result.status,
                'issues': [
                    {
                        'severity': issue.severity,
                        'category': issue.category,
                        'message': issue.message,
                        'details': issue.details
                    }
                    for issue in result.issues
                ]
            }
            report_data['environments'].append(env_data)
            
        # Add cross-environment issues
        parity_issues = self.validate_parity_across_environments()
        if parity_issues:
            report_data['cross_environment_issues'] = [
                {
                    'severity': issue.severity,
                    'category': issue.category,
                    'message': issue.message,
                    'details': issue.details
                }
                for issue in parity_issues
            ]
            
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        self.logger.info(f"Validation report exported to: {output_path}")


def main():
    """Main entry point for environment parity validation."""
    parser = argparse.ArgumentParser(
        description='Environment Parity Validator - Check configuration consistency'
    )
    parser.add_argument(
        '--environments', '-e',
        nargs='+',
        default=['development', 'testing', 'production'],
        help='Environments to validate'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output JSON report to specified file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    try:
        # Initialize validator
        validator = EnvironmentParityValidator()
        
        # Load configurations
        print("Loading environment configurations...")
        validator.load_environment_configs()
        
        # Validate each environment
        results = []
        for env in args.environments:
            result = validator.validate_environment(env)
            results.append(result)
            
        # Print report
        success = validator.print_validation_report(results)
        
        # Export JSON report if requested
        if args.output:
            validator.export_json_report(results, args.output)
            
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Validation failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()