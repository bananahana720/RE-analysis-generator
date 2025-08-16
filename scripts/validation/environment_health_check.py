#!/usr/bin/env python3
"""
Environment Health Check Script
Validates service availability and configuration consistency across environments
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp
import pymongo
import yaml


@dataclass
class HealthCheckResult:
    """Health check result for a service."""
    service: str
    status: str  # 'healthy', 'unhealthy', 'unknown'
    message: str
    response_time_ms: float
    details: Dict[str, Any]


@dataclass
class EnvironmentConfig:
    """Environment configuration loaded from YAML files."""
    name: str
    description: str
    services: Dict[str, Any]
    features: Dict[str, bool]
    health_checks: Dict[str, Any]


class EnvironmentHealthChecker:
    """Environment health checker with service validation."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.logger = self._setup_logging()
        self.config: Optional[EnvironmentConfig] = None
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for health checks."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_environment_config(self) -> EnvironmentConfig:
        """Load environment-specific configuration."""
        try:
            # Load environment-specific config
            env_config_path = self.config_dir / "environments" / f"{self.environment}.yaml"
            if not env_config_path.exists():
                raise FileNotFoundError(f"Environment config not found: {env_config_path}")
                
            with open(env_config_path, 'r') as f:
                env_data = yaml.safe_load(f)
                
            # Load base services config
            services_config_path = self.config_dir / "services" / "base-services.yaml"
            if services_config_path.exists():
                with open(services_config_path, 'r') as f:
                    services_data = yaml.safe_load(f)
            else:
                services_data = {}
                
            # Merge configurations
            config = EnvironmentConfig(
                name=env_data.get('environment', {}).get('name', self.environment),
                description=env_data.get('environment', {}).get('description', ''),
                services=env_data.get('services', {}),
                features=env_data.get('features', {}),
                health_checks=env_data.get('health_checks', services_data.get('health_checks', {}))
            )
            
            self.config = config
            self.logger.info(f"Loaded configuration for environment: {config.name}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load environment config: {e}")
            raise
            
    def _expand_environment_variables(self, value: str) -> str:
        """Expand environment variables in configuration values."""
        if isinstance(value, str) and '${' in value:
            # Handle ${VAR:-default} syntax
            import re
            pattern = r'\$\{([^}]+)\}'
            
            def replace_env_var(match):
                env_expr = match.group(1)
                if ':-' in env_expr:
                    var_name, default_value = env_expr.split(':-', 1)
                    return os.getenv(var_name, default_value)
                else:
                    return os.getenv(env_expr, '')
                    
            return re.sub(pattern, replace_env_var, value)
        return value
        
    async def check_mongodb_health(self) -> HealthCheckResult:
        """Check MongoDB service health."""
        start_time = time.time()
        
        try:
            # Get MongoDB configuration
            mongodb_config = self.config.services.get('mongodb', {})
            connection_string = self._expand_environment_variables(
                mongodb_config.get('connection_string', 'mongodb://localhost:27017')
            )
            database_name = self._expand_environment_variables(
                mongodb_config.get('database', 'phoenix_real_estate')
            )
            
            # Parse connection string to handle different formats
            if not connection_string.startswith('mongodb'):
                connection_string = f"mongodb://{connection_string}"
                
            # Create MongoDB client with timeout
            client = pymongo.MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # Test connection
            client.admin.command('ping')
            
            # Check database accessibility
            db = client[database_name]
            collections = db.list_collection_names()
            
            response_time = (time.time() - start_time) * 1000
            
            details = {
                'connection_string': connection_string.replace(
                    connection_string.split('@')[0] + '@', '***:***@'
                ) if '@' in connection_string else connection_string,
                'database': database_name,
                'collections_count': len(collections),
                'server_info': str(client.server_info().get('version', 'Unknown'))
            }
            
            client.close()
            
            return HealthCheckResult(
                service='mongodb',
                status='healthy',
                message=f'MongoDB connection successful to database "{database_name}"',
                response_time_ms=response_time,
                details=details
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                service='mongodb',
                status='unhealthy',
                message=f'MongoDB connection failed: {str(e)}',
                response_time_ms=response_time,
                details={'error': str(e)}
            )
            
    async def check_ollama_health(self) -> HealthCheckResult:
        """Check Ollama LLM service health."""
        start_time = time.time()
        
        try:
            # Get Ollama configuration
            ollama_config = self.config.services.get('ollama', {})
            base_url = self._expand_environment_variables(
                ollama_config.get('base_url', 'http://localhost:11434')
            )
            model_name = self._expand_environment_variables(
                ollama_config.get('model', 'llama3.2:latest')
            )
            
            # Skip health check for mock model in testing
            if model_name == 'mock':
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    service='ollama',
                    status='healthy',
                    message='Mock LLM service (testing environment)',
                    response_time_ms=response_time,
                    details={'model': 'mock', 'mode': 'testing'}
                )
            
            # Check Ollama service health
            async with aiohttp.ClientSession() as session:
                # Check service availability
                async with session.get(f"{base_url}/api/tags", timeout=10) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama service returned status {response.status}")
                        
                    data = await response.json()
                    models = data.get('models', [])
                    
            response_time = (time.time() - start_time) * 1000
            
            # Check if required model is available
            available_models = [model.get('name', '') for model in models]
            model_available = any(model_name in model for model in available_models)
            
            details = {
                'service_url': base_url,
                'required_model': model_name,
                'model_available': model_available,
                'available_models': available_models[:5]  # Limit to first 5
            }
            
            if model_available:
                status = 'healthy'
                message = f'Ollama service healthy with model "{model_name}"'
            else:
                status = 'unhealthy'
                message = f'Ollama service healthy but model "{model_name}" not available'
                
            return HealthCheckResult(
                service='ollama',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                service='ollama',
                status='unhealthy',
                message=f'Ollama service check failed: {str(e)}',
                response_time_ms=response_time,
                details={'error': str(e)}
            )
            
    async def check_system_health(self) -> HealthCheckResult:
        """Check system resource health."""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get system metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get thresholds from config
            health_config = self.config.health_checks.get('system', {})
            memory_threshold = health_config.get('memory_threshold_percent', 85)
            disk_threshold = health_config.get('disk_threshold_percent', 90)
            
            response_time = (time.time() - start_time) * 1000
            
            details = {
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'cpu_percent': cpu_percent,
                'memory_threshold': memory_threshold,
                'disk_threshold': disk_threshold
            }
            
            # Check if system is healthy
            issues = []
            if memory.percent > memory_threshold:
                issues.append(f"High memory usage: {memory.percent}%")
            if disk.percent > disk_threshold:
                issues.append(f"High disk usage: {disk.percent}%")
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent}%")
                
            if issues:
                status = 'unhealthy'
                message = f'System resource issues: {", ".join(issues)}'
            else:
                status = 'healthy'
                message = 'System resources within normal ranges'
                
            return HealthCheckResult(
                service='system',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except ImportError:
            # psutil not available
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service='system',
                status='unknown',
                message='System monitoring not available (psutil not installed)',
                response_time_ms=response_time,
                details={'error': 'psutil not installed'}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service='system',
                status='unhealthy',
                message=f'System health check failed: {str(e)}',
                response_time_ms=response_time,
                details={'error': str(e)}
            )
            
    async def check_all_services(self) -> List[HealthCheckResult]:
        """Check all configured services."""
        if not self.config:
            raise ValueError("Environment configuration not loaded")
            
        health_checks = []
        
        # Check which services are enabled for health checks
        health_config = self.config.health_checks
        
        # MongoDB health check
        if health_config.get('mongodb', {}).get('enabled', True):
            mongodb_result = await self.check_mongodb_health()
            health_checks.append(mongodb_result)
            
        # Ollama health check  
        if health_config.get('ollama', {}).get('enabled', True):
            ollama_result = await self.check_ollama_health()
            health_checks.append(ollama_result)
            
        # System health check
        if health_config.get('system', {}).get('enabled', True):
            system_result = await self.check_system_health()
            health_checks.append(system_result)
            
        return health_checks
        
    def print_health_report(self, results: List[HealthCheckResult]) -> bool:
        """Print a formatted health report and return overall health status."""
        print("\n=== Environment Health Check Report ===")
        print(f"Environment: {self.config.name}")
        print(f"Description: {self.config.description}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
        print("=" * 45)
        
        overall_healthy = True
        
        for result in results:
            status_icon = {
                'healthy': '✅',
                'unhealthy': '❌',
                'unknown': '❓'
            }.get(result.status, '❓')
            
            print(f"\n{status_icon} {result.service.upper()}")
            print(f"   Status: {result.status}")
            print(f"   Message: {result.message}")
            print(f"   Response Time: {result.response_time_ms:.1f}ms")
            
            if result.details:
                print("   Details:")
                for key, value in result.details.items():
                    if isinstance(value, list):
                        print(f"     {key}: {', '.join(str(v) for v in value)}")
                    else:
                        print(f"     {key}: {value}")
                        
            if result.status == 'unhealthy':
                overall_healthy = False
                
        print("\n" + "=" * 45)
        
        if overall_healthy:
            print("🎉 Overall Status: HEALTHY")
            print("All services are operating normally.")
        else:
            print("🚨 Overall Status: UNHEALTHY")
            print("One or more services require attention.")
            
        return overall_healthy
        
    def export_json_report(self, results: List[HealthCheckResult], output_path: str):
        """Export health check results to JSON file."""
        report_data = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'environment': self.config.name,
            'description': self.config.description,
            'overall_status': 'healthy' if all(r.status == 'healthy' for r in results) else 'unhealthy',
            'services': [
                {
                    'service': result.service,
                    'status': result.status,
                    'message': result.message,
                    'response_time_ms': result.response_time_ms,
                    'details': result.details
                }
                for result in results
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        self.logger.info(f"Health check report exported to: {output_path}")


async def main():
    """Main entry point for health check script."""
    parser = argparse.ArgumentParser(
        description='Environment Health Check - Validate service availability and configuration'
    )
    parser.add_argument(
        '--environment', '-e',
        default=os.getenv('ENVIRONMENT', 'development'),
        help='Environment to check (development, testing, production)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output JSON report to specified file'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick health check (skip detailed validations)'
    )
    parser.add_argument(
        '--services',
        nargs='+',
        choices=['mongodb', 'ollama', 'system'],
        help='Specific services to check (default: all enabled)'
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
        # Initialize health checker
        checker = EnvironmentHealthChecker(environment=args.environment)
        
        # Load environment configuration
        config = checker.load_environment_config()
        
        print(f"Starting health check for environment: {config.name}")
        if args.verbose:
            print(f"Configuration loaded from: {checker.config_dir}")
            
        # Run health checks
        results = await checker.check_all_services()
        
        # Print report
        overall_healthy = checker.print_health_report(results)
        
        # Export JSON report if requested
        if args.output:
            checker.export_json_report(results, args.output)
            
        # Exit with appropriate code
        sys.exit(0 if overall_healthy else 1)
        
    except Exception as e:
        print(f"❌ Health check failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())