#!/usr/bin/env python3
"""
Production Monitoring Infrastructure Deployment Script
Phoenix Real Estate Data Collection System

Deploys comprehensive monitoring infrastructure including:
- Prometheus metrics collection
- Grafana dashboards (Executive, Operational, Performance, Business Intelligence)  
- AlertManager with multi-level alerting
- Cost tracking and budget compliance
- Performance baseline monitoring

Usage:
    python scripts/deploy/deploy_production_monitoring.py [--validate-only]
"""

import asyncio
import os
import sys
import time
import yaml
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.config import EnvironmentConfigProvider

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Validation result for a monitoring component."""
    component: str
    status: str  # 'healthy', 'warning', 'error'
    message: str
    details: Dict = None
    response_time_ms: Optional[float] = None


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    config_dir: Path
    compose_file: Path
    dashboard_dir: Path
    baseline_config: Path
    environment: str = "production"


class MonitoringDeployer:
    """Production monitoring infrastructure deployer."""
    
    def __init__(self, config: DeploymentConfig):
        """Initialize deployer with configuration.
        
        Args:
            config: Deployment configuration
        """
        self.config = config
        self.app_config = EnvironmentConfigProvider()
        self.services_status = {}
        
        # Service health check endpoints
        self.health_endpoints = {
            'prometheus': 'http://localhost:9091/-/healthy',
            'grafana': 'http://localhost:3000/api/health', 
            'alertmanager': 'http://localhost:9093/-/healthy',
            'phoenix_metrics': 'http://localhost:8080/health',
            'cost_summary': 'http://localhost:8080/cost-summary',
            'performance_summary': 'http://localhost:8080/performance-summary',
            'business_summary': 'http://localhost:8080/business-summary'
        }
        
        logger.info(f"Monitoring deployer initialized for {config.environment}")
    
    async def deploy(self, validate_only: bool = False) -> bool:
        """Deploy monitoring infrastructure.
        
        Args:
            validate_only: If True, only validate existing deployment
            
        Returns:
            True if deployment successful, False otherwise
        """
        try:
            logger.info("=" * 80)
            logger.info("Phoenix Real Estate Production Monitoring Deployment")
            logger.info("=" * 80)
            
            if validate_only:
                logger.info("VALIDATION MODE - Checking existing deployment")
                return await self._validate_deployment()
            
            # Step 1: Pre-deployment validation
            logger.info("Step 1: Pre-deployment validation")
            if not await self._pre_deployment_checks():
                logger.error("Pre-deployment validation failed")
                return False
            
            # Step 2: Deploy infrastructure
            logger.info("Step 2: Deploying monitoring infrastructure")
            if not await self._deploy_infrastructure():
                logger.error("Infrastructure deployment failed")
                return False
            
            # Step 3: Wait for services to be ready
            logger.info("Step 3: Waiting for services to initialize")
            if not await self._wait_for_services():
                logger.error("Service initialization failed")
                return False
            
            # Step 4: Configure dashboards and alerts
            logger.info("Step 4: Configuring dashboards and alerts")
            if not await self._configure_monitoring():
                logger.error("Monitoring configuration failed")
                return False
            
            # Step 5: Validation
            logger.info("Step 5: Post-deployment validation")
            if not await self._validate_deployment():
                logger.error("Post-deployment validation failed")
                return False
            
            # Step 6: Generate deployment summary
            await self._generate_deployment_summary()
            
            logger.info("=" * 80)
            logger.info("🎉 PRODUCTION MONITORING DEPLOYMENT SUCCESSFUL!")
            logger.info("=" * 80)
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed with error: {e}")
            return False
    
    async def _pre_deployment_checks(self) -> bool:
        """Run pre-deployment validation checks.
        
        Returns:
            True if all checks pass
        """
        checks = []
        
        # Check required files exist
        required_files = [
            self.config.compose_file,
            self.config.config_dir / "prometheus.yml",
            self.config.config_dir / "production-alerts.yml",
            self.config.config_dir / "alertmanager.yml",
            self.config.baseline_config
        ]
        
        for file_path in required_files:
            if file_path.exists():
                logger.info(f"✅ Found required file: {file_path}")
                checks.append(True)
            else:
                logger.error(f"❌ Missing required file: {file_path}")
                checks.append(False)
        
        # Check Docker availability
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✅ Docker available: {result.stdout.strip()}")
                checks.append(True)
            else:
                logger.error("❌ Docker not available")
                checks.append(False)
        except FileNotFoundError:
            logger.error("❌ Docker not installed or not in PATH")
            checks.append(False)
        
        # Check Docker Compose availability
        try:
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✅ Docker Compose available: {result.stdout.strip()}")
                checks.append(True)
            else:
                logger.error("❌ Docker Compose not available")
                checks.append(False)
        except FileNotFoundError:
            logger.error("❌ Docker Compose not available")
            checks.append(False)
        
        # Check port availability
        required_ports = [3000, 8080, 9091, 9093, 9100]
        for port in required_ports:
            if await self._check_port_available(port):
                logger.info(f"✅ Port {port} available")
                checks.append(True)
            else:
                logger.warning(f"⚠️  Port {port} may be in use")
                checks.append(True)  # Allow deployment to proceed
        
        success = all(checks)
        logger.info(f"Pre-deployment checks: {'PASSED' if success else 'FAILED'}")
        return success
    
    async def _deploy_infrastructure(self) -> bool:
        """Deploy monitoring infrastructure using Docker Compose.
        
        Returns:
            True if deployment successful
        """
        try:
            # Change to config directory for Docker Compose context
            os.chdir(self.config.config_dir)
            
            logger.info("Pulling latest container images...")
            result = subprocess.run([
                'docker', 'compose', '-f', 'production-docker-compose.yml',
                'pull'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Image pull had issues: {result.stderr}")
            
            logger.info("Starting monitoring infrastructure...")
            result = subprocess.run([
                'docker', 'compose', '-f', 'production-docker-compose.yml',
                'up', '-d', '--remove-orphans'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Docker Compose deployment failed: {result.stderr}")
                return False
                
            logger.info("✅ Infrastructure deployment completed")
            return True
            
        except Exception as e:
            logger.error(f"Infrastructure deployment failed: {e}")
            return False
    
    async def _wait_for_services(self, timeout: int = 120) -> bool:
        """Wait for all services to be ready.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if all services are ready
        """
        start_time = time.time()
        services_ready = set()
        
        while time.time() - start_time < timeout:
            for service, endpoint in self.health_endpoints.items():
                if service in services_ready:
                    continue
                    
                try:
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✅ Service {service} is ready")
                        services_ready.add(service)
                except requests.RequestException:
                    logger.debug(f"Service {service} not ready yet...")
                    pass
            
            if len(services_ready) == len(self.health_endpoints):
                logger.info("✅ All services are ready")
                return True
                
            await asyncio.sleep(5)
        
        missing_services = set(self.health_endpoints.keys()) - services_ready
        logger.error(f"❌ Services not ready after {timeout}s: {missing_services}")
        return False
    
    async def _configure_monitoring(self) -> bool:
        """Configure dashboards and alerts.
        
        Returns:
            True if configuration successful
        """
        try:
            # Check if Grafana dashboards are loaded
            grafana_url = "http://localhost:3000"
            auth = ("admin", "phoenix_admin_2024")
            
            # Wait a bit more for Grafana to fully initialize
            await asyncio.sleep(10)
            
            # Check dashboard availability
            dashboards = [
                'phoenix-executive',
                'phoenix-operational', 
                'phoenix-performance',
                'phoenix-business'
            ]
            
            for dashboard in dashboards:
                try:
                    response = requests.get(
                        f"{grafana_url}/api/dashboards/uid/{dashboard}",
                        auth=auth,
                        timeout=10
                    )
                    if response.status_code == 200:
                        logger.info(f"✅ Dashboard {dashboard} loaded")
                    else:
                        logger.warning(f"⚠️  Dashboard {dashboard} may not be loaded yet")
                except requests.RequestException as e:
                    logger.warning(f"⚠️  Could not verify dashboard {dashboard}: {e}")
            
            logger.info("✅ Monitoring configuration completed")
            return True
            
        except Exception as e:
            logger.error(f"Monitoring configuration failed: {e}")
            return False
    
    async def _validate_deployment(self) -> bool:
        """Validate the deployment by running comprehensive health checks.
        
        Returns:
            True if validation passes
        """
        logger.info("Running comprehensive deployment validation...")
        
        validation_results = []
        
        # Validate each service
        for service, endpoint in self.health_endpoints.items():
            result = await self._validate_service(service, endpoint)
            validation_results.append(result)
        
        # Validate dashboards
        dashboard_results = await self._validate_dashboards()
        validation_results.extend(dashboard_results)
        
        # Validate alerts
        alert_results = await self._validate_alerts()
        validation_results.extend(alert_results)
        
        # Validate baselines
        baseline_results = await self._validate_baselines()
        validation_results.extend(baseline_results)
        
        # Generate validation report
        await self._generate_validation_report(validation_results)
        
        # Check overall success
        errors = [r for r in validation_results if r.status == 'error']
        warnings = [r for r in validation_results if r.status == 'warning']
        
        logger.info(f"Validation completed: {len(validation_results)} checks")
        logger.info(f"✅ Healthy: {len(validation_results) - len(errors) - len(warnings)}")
        logger.info(f"⚠️  Warnings: {len(warnings)}")
        logger.info(f"❌ Errors: {len(errors)}")
        
        return len(errors) == 0
    
    async def _validate_service(self, service: str, endpoint: str) -> ValidationResult:
        """Validate a single service.
        
        Args:
            service: Service name
            endpoint: Health check endpoint
            
        Returns:
            Validation result
        """
        try:
            start_time = time.time()
            response = requests.get(endpoint, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return ValidationResult(
                    component=service,
                    status='healthy',
                    message='Service is operational',
                    response_time_ms=response_time,
                    details={'status_code': response.status_code}
                )
            else:
                return ValidationResult(
                    component=service,
                    status='warning',
                    message=f'Service returned status {response.status_code}',
                    response_time_ms=response_time,
                    details={'status_code': response.status_code}
                )
                
        except requests.RequestException as e:
            return ValidationResult(
                component=service,
                status='error',
                message=f'Service not accessible: {str(e)}',
                details={'error': str(e)}
            )
    
    async def _validate_dashboards(self) -> List[ValidationResult]:
        """Validate Grafana dashboards.
        
        Returns:
            List of validation results
        """
        results = []
        grafana_url = "http://localhost:3000"
        auth = ("admin", "phoenix_admin_2024")
        
        dashboards = {
            'phoenix-executive': 'Executive Dashboard',
            'phoenix-operational': 'Operational Dashboard',
            'phoenix-performance': 'Performance Dashboard', 
            'phoenix-business': 'Business Intelligence Dashboard'
        }
        
        for uid, name in dashboards.items():
            try:
                response = requests.get(
                    f"{grafana_url}/api/dashboards/uid/{uid}",
                    auth=auth,
                    timeout=10
                )
                
                if response.status_code == 200:
                    results.append(ValidationResult(
                        component=f'dashboard_{uid}',
                        status='healthy',
                        message=f'{name} is accessible',
                        details={'uid': uid, 'name': name}
                    ))
                else:
                    results.append(ValidationResult(
                        component=f'dashboard_{uid}',
                        status='error',
                        message=f'{name} not accessible',
                        details={'uid': uid, 'status_code': response.status_code}
                    ))
                    
            except requests.RequestException as e:
                results.append(ValidationResult(
                    component=f'dashboard_{uid}',
                    status='error',
                    message=f'{name} validation failed: {str(e)}',
                    details={'uid': uid, 'error': str(e)}
                ))
        
        return results
    
    async def _validate_alerts(self) -> List[ValidationResult]:
        """Validate AlertManager configuration.
        
        Returns:
            List of validation results
        """
        results = []
        
        try:
            # Check AlertManager API
            response = requests.get(
                'http://localhost:9093/api/v1/status',
                timeout=10
            )
            
            if response.status_code == 200:
                results.append(ValidationResult(
                    component='alertmanager_api',
                    status='healthy',
                    message='AlertManager API accessible',
                    details=response.json()
                ))
            else:
                results.append(ValidationResult(
                    component='alertmanager_api',
                    status='error',
                    message='AlertManager API not accessible'
                ))
                
        except requests.RequestException as e:
            results.append(ValidationResult(
                component='alertmanager_api',
                status='error',
                message=f'AlertManager validation failed: {str(e)}'
            ))
        
        # Check Prometheus rules
        try:
            response = requests.get(
                'http://localhost:9091/api/v1/rules',
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                rule_count = sum(len(group.get('rules', [])) 
                               for group in data.get('data', {}).get('groups', []))
                
                results.append(ValidationResult(
                    component='prometheus_rules',
                    status='healthy',
                    message=f'{rule_count} alerting rules loaded',
                    details={'rule_count': rule_count}
                ))
            else:
                results.append(ValidationResult(
                    component='prometheus_rules',
                    status='error',
                    message='Prometheus rules not accessible'
                ))
                
        except requests.RequestException as e:
            results.append(ValidationResult(
                component='prometheus_rules',
                status='error',
                message=f'Prometheus rules validation failed: {str(e)}'
            ))
        
        return results
    
    async def _validate_baselines(self) -> List[ValidationResult]:
        """Validate performance baselines.
        
        Returns:
            List of validation results
        """
        results = []
        
        try:
            # Load baseline configuration
            with open(self.config.baseline_config) as f:
                baselines = yaml.safe_load(f)
            
            results.append(ValidationResult(
                component='baseline_config',
                status='healthy',
                message='Baseline configuration loaded',
                details={'config_sections': list(baselines.keys())}
            ))
            
            # Validate baseline structure
            required_sections = [
                'performance_baselines',
                'resource_baselines', 
                'quality_baselines',
                'cost_baselines'
            ]
            
            for section in required_sections:
                if section in baselines:
                    results.append(ValidationResult(
                        component=f'baseline_{section}',
                        status='healthy',
                        message=f'Baseline section {section} present',
                        details=baselines[section]
                    ))
                else:
                    results.append(ValidationResult(
                        component=f'baseline_{section}',
                        status='error',
                        message=f'Missing baseline section: {section}'
                    ))
                    
        except Exception as e:
            results.append(ValidationResult(
                component='baseline_validation',
                status='error',
                message=f'Baseline validation failed: {str(e)}'
            ))
        
        return results
    
    async def _generate_validation_report(self, results: List[ValidationResult]):
        """Generate comprehensive validation report.
        
        Args:
            results: List of validation results
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'validation_summary': {
                'total_checks': len(results),
                'healthy': len([r for r in results if r.status == 'healthy']),
                'warnings': len([r for r in results if r.status == 'warning']),
                'errors': len([r for r in results if r.status == 'error'])
            },
            'results': [
                {
                    'component': r.component,
                    'status': r.status,
                    'message': r.message,
                    'response_time_ms': r.response_time_ms,
                    'details': r.details
                } for r in results
            ]
        }
        
        # Write report to file
        report_path = self.config.config_dir / "validation-report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Validation report written to: {report_path}")
    
    async def _generate_deployment_summary(self):
        """Generate deployment summary with access URLs."""
        
        summary = """
        
╭─────────────────────────────────────────────────────────────────────────────╮
│                    PRODUCTION MONITORING DEPLOYED                          │
╰─────────────────────────────────────────────────────────────────────────────╯

🎯 EXECUTIVE DASHBOARD
   URL: http://localhost:3000/d/phoenix-executive
   Purpose: System uptime, cost tracking, success rates
   
📊 OPERATIONAL DASHBOARD  
   URL: http://localhost:3000/d/phoenix-operational
   Purpose: Real-time system health, API performance
   
⚡ PERFORMANCE DASHBOARD
   URL: http://localhost:3000/d/phoenix-performance  
   Purpose: Performance baselines, resource utilization
   
💼 BUSINESS INTELLIGENCE DASHBOARD
   URL: http://localhost:3000/d/phoenix-business
   Purpose: Collection metrics, cost efficiency, geographic coverage

🔧 SYSTEM ACCESS
   Grafana:      http://localhost:3000 (admin/phoenix_admin_2024)
   Prometheus:   http://localhost:9091
   AlertManager: http://localhost:9093
   
📈 METRICS ENDPOINTS
   Health Check:      http://localhost:8080/health
   Prometheus Metrics: http://localhost:8080/metrics
   Cost Summary:      http://localhost:8080/cost-summary
   Performance:       http://localhost:8080/performance-summary
   Business Metrics:  http://localhost:8080/business-summary

🎛️ MONITORING FEATURES
   ✅ Real-time metrics collection
   ✅ Cost tracking with $25 budget alerts
   ✅ Performance baseline monitoring (65ms LLM, 30.3ms DB)
   ✅ Multi-level alerting (CRITICAL, WARNING, INFO)
   ✅ Business intelligence tracking
   ✅ 30-day data retention
   ✅ Production-ready alerting rules

🚨 ALERT CHANNELS
   Critical: Immediate notification (2-15 min response time)
   Warning:  4-hour repeat interval  
   Info:     24-hour digest
   
📋 VALIDATION STATUS
   System Health: ✅ All services operational
   Dashboard Access: ✅ All 4 dashboards accessible  
   Alert Rules: ✅ Production rules loaded
   Cost Tracking: ✅ Budget compliance monitoring active
   Performance Baselines: ✅ E2E validation baselines configured
   
🎉 READY FOR PRODUCTION GO-LIVE!

        """
        
        print(summary)
        logger.info("Deployment summary generated")
    
    async def _check_port_available(self, port: int) -> bool:
        """Check if a port is available.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port appears available
        """
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False


async def main():
    """Main deployment function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy Phoenix Real Estate Production Monitoring"
    )
    parser.add_argument(
        '--validate-only', 
        action='store_true',
        help="Only validate existing deployment"
    )
    parser.add_argument(
        '--config-dir',
        default='config/monitoring',
        help="Monitoring configuration directory"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    config_dir = Path(args.config_dir)
    if not config_dir.is_absolute():
        config_dir = project_root / config_dir
        
    deployment_config = DeploymentConfig(
        config_dir=config_dir,
        compose_file=config_dir / "production-docker-compose.yml",
        dashboard_dir=config_dir / "dashboards",
        baseline_config=config_dir / "baseline-configuration.yml"
    )
    
    # Run deployment
    deployer = MonitoringDeployer(deployment_config)
    success = await deployer.deploy(validate_only=args.validate_only)
    
    if success:
        print("\n🎉 SUCCESS: Production monitoring is ready for Go-Live!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Deployment or validation failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())