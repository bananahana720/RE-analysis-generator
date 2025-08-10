# Task 7: GitHub Actions Workflow

## Overview

### Objective
Design and implement comprehensive GitHub Actions workflows for automated daily data collection, deployment management, and CI/CD integration that orchestrates Epic 1's foundation infrastructure and Epic 2's data collection engine within the free tier constraints.

### Epic Integration
**Builds upon Epic 1**: Uses ConfigProvider for secrets, structured logging for workflow monitoring, and exception handling patterns
**Orchestrates Epic 2**: Triggers data collectors, coordinates collection strategies, and monitors collection metrics
**Enables Epic 4**: Provides workflow execution data and quality metrics for analysis

### Dependencies
- Epic 1: `foundation.config.base.ConfigProvider`, `foundation.logging.factory.get_logger`
- Epic 2: `collectors.combined.CombinedCollector`, `collectors.monitoring.CollectionMetrics`
- Docker containerization for deployment
- GitHub Secrets for configuration management

## Technical Requirements

### Functional Requirements

#### FR-1: Daily Data Collection Workflow
```yaml
# .github/workflows/daily-collection.yml
name: Daily Real Estate Data Collection

on:
  schedule:
    # 3 AM Phoenix time (10 AM UTC)
    - cron: '0 10 * * *'
  workflow_dispatch:  # Manual trigger for testing

env:
  PYTHON_VERSION: '3.12.4'
  CONTAINER_REGISTRY: docker.io
  IMAGE_NAME: phoenix-real-estate

jobs:
  collect-data:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install UV Package Manager
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH
          
      - name: Install Dependencies
        run: |
          uv sync --dev
          
      - name: Configure Environment
        env:
          # Epic 1 Configuration Secrets
          MONGODB_CONNECTION_STRING: ${{ secrets.MONGODB_CONNECTION_STRING }}
          MARICOPA_API_KEY: ${{ secrets.MARICOPA_API_KEY }}
          
          # Epic 2 Collection Secrets
          WEBSHARE_USERNAME: ${{ secrets.WEBSHARE_USERNAME }}
          WEBSHARE_PASSWORD: ${{ secrets.WEBSHARE_PASSWORD }}
          
          # Epic 3 Automation Configuration
          TARGET_ZIP_CODES: ${{ secrets.TARGET_ZIP_CODES }}
          ORCHESTRATION_MODE: "sequential"
          DEPLOYMENT_ENVIRONMENT: "production"
        run: |
          # Create configuration file using Epic 1's patterns
          python scripts/setup_github_environment.py
          
      - name: Run Data Collection
        run: |
          # Execute Epic 3's orchestration engine
          uv run python -m phoenix_real_estate.automation.workflows.daily_collection
        timeout-minutes: 75
        
      - name: Generate Collection Report
        if: always()
        run: |
          # Generate report using Epic 1's repository and Epic 3's reporting
          uv run python -m phoenix_real_estate.automation.reporting.daily_summary
          
      - name: Upload Collection Artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: collection-report-${{ github.run_number }}
          path: |
            reports/daily-*.json
            logs/collection-*.log
          retention-days: 30
          
      - name: Notify on Failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            // Epic 3 failure notification using GitHub API
            const issueBody = `
            ## Daily Collection Workflow Failed
            
            **Run ID**: ${{ github.run_id }}
            **Timestamp**: ${new Date().toISOString()}
            **Environment**: production
            
            Please investigate the failure and restart collection if needed.
            `;
            
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Daily Collection Failed - ' + new Date().toDateString(),
              body: issueBody,
              labels: ['automation', 'failure', 'high-priority']
            });
```

#### FR-2: Container Build and Deploy Workflow
```yaml
# .github/workflows/build-deploy.yml
name: Build and Deploy Containers

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: docker.io
  IMAGE_NAME: phoenix-real-estate

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12.4'
          
      - name: Install UV and Dependencies
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH
          uv sync --dev
          
      - name: Run Epic 1 Foundation Tests
        run: |
          uv run pytest python_modules/tests/foundation/ -v --cov=phoenix_real_estate.foundation
          
      - name: Run Epic 2 Collection Tests
        run: |
          uv run pytest python_modules/tests/collectors/ -v --cov=phoenix_real_estate.collectors
          
      - name: Run Epic 3 Automation Tests
        run: |
          uv run pytest python_modules/tests/automation/ -v --cov=phoenix_real_estate.automation
          
      - name: Type Check with Pyright
        run: |
          uv run pyright src/
          
      - name: Code Quality Check
        run: |
          uv run ruff check src/
          uv run ruff format --check src/

  build:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
      
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
          
      - name: Extract Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
            
      - name: Build and Push Docker Image
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./docker/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            PYTHON_VERSION=3.12.4
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            VCS_REF=${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
      - name: Deploy to Production
        env:
          IMAGE_TAG: ${{ needs.build.outputs.image-tag }}
        run: |
          echo "Deploying image: $IMAGE_TAG"
          # Epic 3 deployment logic would be implemented here
          # For this system, deployment might mean updating container registry
          # and triggering scheduled workflows
```

#### FR-3: Quality Assurance Workflow
```yaml
# .github/workflows/quality-assurance.yml
name: Quality Assurance and Integration Tests

on:
  schedule:
    # Weekly QA run every Sunday at 2 AM UTC
    - cron: '0 2 * * 0'
  workflow_dispatch:

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [development, staging]
        
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12.4'
          
      - name: Install Dependencies
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH
          uv sync --dev
          
      - name: Configure Test Environment
        env:
          ENVIRONMENT: ${{ matrix.environment }}
          MONGODB_CONNECTION_STRING: ${{ secrets.MONGODB_CONNECTION_STRING_TEST }}
          MARICOPA_API_KEY: ${{ secrets.MARICOPA_API_KEY_TEST }}
        run: |
          # Set up test configuration using Epic 1's patterns
          python scripts/setup_test_environment.py --env $ENVIRONMENT
          
      - name: Epic 1-2-3 Integration Test
        run: |
          # Test complete integration from Epic 1 through Epic 3
          uv run pytest tests/integration/ -v --cov=phoenix_real_estate
          
      - name: Performance Benchmarks
        run: |
          # Run performance tests for Epic 3 orchestration
          uv run python -m phoenix_real_estate.automation.benchmarks.performance_test
          
      - name: Security Scan
        run: |
          uv run bandit -r src/
          uv run safety check
          
      - name: Generate QA Report
        run: |
          # Generate comprehensive QA report for Epic 4
          uv run python -m phoenix_real_estate.automation.reporting.qa_summary
          
      - name: Upload QA Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: qa-report-${{ matrix.environment }}-${{ github.run_number }}
          path: |
            reports/qa-*.json
            reports/performance-*.json
            reports/security-*.json
```

### Integration Patterns

#### Epic 1 Configuration Integration
```python
# scripts/setup_github_environment.py
"""
GitHub Actions environment setup using Epic 1's configuration patterns.
"""

import os
import sys
from pathlib import Path

# Add project root to path for Epic imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.config.environment import Environment
from phoenix_real_estate.foundation.logging.factory import get_logger

class GitHubActionsConfig:
    """GitHub Actions configuration setup using Epic 1 patterns."""
    
    def __init__(self) -> None:
        self.logger = get_logger("github.actions.setup")
        
        # Create Epic 1 compatible configuration
        self.config = self._create_config_provider()
        
    def _create_config_provider(self) -> ConfigProvider:
        """Create configuration provider with GitHub secrets."""
        
        # Epic 1 configuration with GitHub Actions secrets
        config_data = {
            # Epic 1 Foundation Configuration
            "ENVIRONMENT": os.getenv("DEPLOYMENT_ENVIRONMENT", "production"),
            "MONGODB_CONNECTION_STRING": os.getenv("MONGODB_CONNECTION_STRING"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            
            # Epic 2 Collection Configuration
            "MARICOPA_API_KEY": os.getenv("MARICOPA_API_KEY"),
            "WEBSHARE_USERNAME": os.getenv("WEBSHARE_USERNAME"),
            "WEBSHARE_PASSWORD": os.getenv("WEBSHARE_PASSWORD"),
            "TARGET_ZIP_CODES": os.getenv("TARGET_ZIP_CODES"),
            
            # Epic 3 Automation Configuration
            "ORCHESTRATION_MODE": os.getenv("ORCHESTRATION_MODE", "sequential"),
            "WORKFLOW_TIMEOUT_MINUTES": int(os.getenv("WORKFLOW_TIMEOUT_MINUTES", "75")),
            "GITHUB_ACTIONS_ENABLED": True,
            "MAX_CONCURRENT_COLLECTORS": int(os.getenv("MAX_CONCURRENT_COLLECTORS", "2"))
        }
        
        # Validate required configuration
        required_keys = [
            "MONGODB_CONNECTION_STRING",
            "MARICOPA_API_KEY",
            "TARGET_ZIP_CODES"
        ]
        
        missing_keys = [key for key in required_keys if not config_data.get(key)]
        if missing_keys:
            self.logger.error(
                "Missing required configuration",
                extra={"missing_keys": missing_keys}
            )
            raise ValueError(f"Missing required configuration: {missing_keys}")
        
        # Create Epic 1 compatible config provider
        return ConfigProvider(config_data)
    
    def setup_environment(self) -> None:
        """Set up GitHub Actions environment."""
        try:
            self.logger.info("Setting up GitHub Actions environment")
            
            # Validate Epic 1 database connection
            self._validate_database_connection()
            
            # Validate Epic 2 collector configuration
            self._validate_collector_configuration()
            
            # Set up Epic 3 automation environment
            self._setup_automation_environment()
            
            self.logger.info("GitHub Actions environment setup completed")
            
        except Exception as e:
            self.logger.error(
                "GitHub Actions environment setup failed",
                extra={"error": str(e)}
            )
            raise
    
    def _validate_database_connection(self) -> None:
        """Validate Epic 1 database connection."""
        from phoenix_real_estate.foundation.database.connection import DatabaseClient
        
        try:
            db_client = DatabaseClient(self.config)
            # Test connection (would need to implement ping method)
            self.logger.info("Database connection validated")
            
        except Exception as e:
            self.logger.error(
                "Database connection validation failed",
                extra={"error": str(e)}
            )
            raise
    
    def _validate_collector_configuration(self) -> None:
        """Validate Epic 2 collector configuration."""
        try:
            # Validate target ZIP codes
            zip_codes = self.config.get_required("TARGET_ZIP_CODES").split(",")
            zip_codes = [z.strip() for z in zip_codes if z.strip()]
            
            if not zip_codes:
                raise ValueError("No valid ZIP codes configured")
            
            self.logger.info(
                "Collector configuration validated",
                extra={"zip_code_count": len(zip_codes)}
            )
            
        except Exception as e:
            self.logger.error(
                "Collector configuration validation failed",
                extra={"error": str(e)}
            )
            raise
    
    def _setup_automation_environment(self) -> None:
        """Set up Epic 3 automation environment."""
        try:
            # Create necessary directories
            os.makedirs("reports", exist_ok=True)
            os.makedirs("logs", exist_ok=True)
            
            # Set up logging configuration
            log_config = {
                "level": self.config.get("LOG_LEVEL", "INFO"),
                "format": "structured",
                "output": "logs/github-actions.log"
            }
            
            self.logger.info(
                "Automation environment setup completed",
                extra={"log_config": log_config}
            )
            
        except Exception as e:
            self.logger.error(
                "Automation environment setup failed",
                extra={"error": str(e)}
            )
            raise

if __name__ == "__main__":
    try:
        setup = GitHubActionsConfig()
        setup.setup_environment()
        print("✅ GitHub Actions environment setup successful")
        
    except Exception as e:
        print(f"❌ GitHub Actions environment setup failed: {e}")
        sys.exit(1)
```

#### Workflow Execution Module
```python
# src/phoenix_real_estate/automation/workflows/daily_collection.py
"""
Daily collection workflow for GitHub Actions integration.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.database.connection import DatabaseClient
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.monitoring.metrics import MetricsCollector

from phoenix_real_estate.automation.orchestration.engine import OrchestrationEngine
from phoenix_real_estate.automation.workflows.base import WorkflowCommand
from phoenix_real_estate.automation.monitoring.workflow_monitor import WorkflowMonitor

class GitHubActionsDailyCollection:
    """Daily collection workflow for GitHub Actions execution."""
    
    def __init__(self) -> None:
        self.logger = get_logger("github.actions.daily_collection")
        
        # Initialize Epic 1 components
        self.config = self._load_configuration()
        self.db_client = DatabaseClient(self.config)
        self.repository = PropertyRepository(self.db_client)
        self.metrics = MetricsCollector(self.config, "github.actions.metrics")
        
        # Initialize Epic 3 orchestration
        self.orchestration_engine = OrchestrationEngine(
            self.config, self.repository, self.metrics
        )
        self.workflow_monitor = WorkflowMonitor(
            self.metrics, "github.actions.monitor"
        )
        
    def _load_configuration(self) -> ConfigProvider:
        """Load configuration for GitHub Actions environment."""
        try:
            # Configuration should be set up by setup_github_environment.py
            config_data = {}  # Would load from environment or config file
            
            # Add GitHub Actions specific settings
            config_data.update({
                "EXECUTION_ENVIRONMENT": "github_actions",
                "WORKFLOW_RUN_ID": os.getenv("GITHUB_RUN_ID"),
                "WORKFLOW_RUN_NUMBER": os.getenv("GITHUB_RUN_NUMBER"),
                "REPOSITORY": os.getenv("GITHUB_REPOSITORY"),
                "COMMIT_SHA": os.getenv("GITHUB_SHA")
            })
            
            return ConfigProvider(config_data)
            
        except Exception as e:
            self.logger.error(
                "Failed to load GitHub Actions configuration",
                extra={"error": str(e)}
            )
            raise
    
    async def run(self) -> Dict[str, Any]:
        """Execute daily collection workflow."""
        workflow_context = {
            "execution_environment": "github_actions",
            "run_id": self.config.get("WORKFLOW_RUN_ID"),
            "run_number": self.config.get("WORKFLOW_RUN_NUMBER"),
            "repository": self.config.get("REPOSITORY"),
            "commit_sha": self.config.get("COMMIT_SHA"),
            "started_at": datetime.utcnow().isoformat()
        }
        
        await self.workflow_monitor.on_workflow_started(
            "github_actions_daily_collection", 
            workflow_context
        )
        
        try:
            self.logger.info(
                "Starting GitHub Actions daily collection",
                extra=workflow_context
            )
            
            # Initialize Epic 3 orchestration engine with Epic 2 collectors
            await self.orchestration_engine.initialize()
            
            # Execute daily workflow orchestrating Epic 2 collectors
            workflow_result = await self.orchestration_engine.run_daily_workflow()
            
            # Generate execution report
            report_data = await self._generate_execution_report(workflow_result)
            
            # Record final metrics
            final_metrics = {
                **workflow_result.get("metrics", {}),
                "execution_duration_seconds": (
                    datetime.utcnow() - datetime.fromisoformat(workflow_context["started_at"].replace("Z", "+00:00"))
                ).total_seconds(),
                "github_actions_minutes_used": self._estimate_minutes_used()
            }
            
            await self.workflow_monitor.on_workflow_completed(
                "github_actions_daily_collection",
                final_metrics
            )
            
            self.logger.info(
                "GitHub Actions daily collection completed successfully",
                extra={
                    "workflow_result": workflow_result,
                    "final_metrics": final_metrics
                }
            )
            
            return {
                "success": True,
                "workflow_result": workflow_result,
                "execution_report": report_data,
                "metrics": final_metrics,
                "context": workflow_context
            }
            
        except Exception as e:
            await self.workflow_monitor.on_workflow_failed(
                "github_actions_daily_collection",
                str(e),
                workflow_context
            )
            
            self.logger.error(
                "GitHub Actions daily collection failed",
                extra={
                    "error": str(e),
                    "context": workflow_context
                }
            )
            
            # Generate failure report
            failure_report = await self._generate_failure_report(e, workflow_context)
            
            return {
                "success": False,
                "error": str(e),
                "failure_report": failure_report,
                "context": workflow_context
            }
    
    async def _generate_execution_report(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution report for GitHub Actions artifacts."""
        try:
            report = {
                "report_type": "github_actions_daily_collection",
                "execution_time": datetime.utcnow().isoformat(),
                "workflow_result": workflow_result,
                "system_info": {
                    "python_version": sys.version,
                    "platform": sys.platform,
                    "epic_versions": {
                        "foundation": "1.0.0",  # Would get from Epic 1
                        "collection": "1.0.0",  # Would get from Epic 2
                        "automation": "1.0.0"   # Would get from Epic 3
                    }
                },
                "resource_usage": {
                    "estimated_minutes": self._estimate_minutes_used(),
                    "memory_peak_mb": self._get_memory_usage(),
                    "execution_duration_minutes": workflow_result.get("metrics", {}).get("duration_seconds", 0) / 60
                }
            }
            
            # Save report for GitHub Actions artifacts
            report_path = Path("reports/daily-collection-report.json")
            report_path.parent.mkdir(exist_ok=True)
            
            import json
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(
                "Execution report generated",
                extra={"report_path": str(report_path)}
            )
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Failed to generate execution report",
                extra={"error": str(e)}
            )
            return {"error": "Failed to generate execution report"}
    
    async def _generate_failure_report(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate failure report for debugging."""
        try:
            failure_report = {
                "report_type": "github_actions_failure",
                "error_time": datetime.utcnow().isoformat(),
                "error_details": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "traceback": "".join(traceback.format_tb(error.__traceback__)) if error.__traceback__ else None
                },
                "context": context,
                "system_state": {
                    "memory_usage_mb": self._get_memory_usage(),
                    "estimated_minutes_used": self._estimate_minutes_used()
                }
            }
            
            # Save failure report
            report_path = Path("reports/daily-collection-failure.json")
            report_path.parent.mkdir(exist_ok=True)
            
            import json
            with open(report_path, "w") as f:
                json.dump(failure_report, f, indent=2)
            
            return failure_report
            
        except Exception as report_error:
            self.logger.error(
                "Failed to generate failure report",
                extra={"error": str(report_error)}
            )
            return {"error": "Failed to generate failure report"}
    
    def _estimate_minutes_used(self) -> float:
        """Estimate GitHub Actions minutes used."""
        # Simple estimation based on workflow duration
        # In reality, this would track actual workflow execution time
        return 5.0  # Estimated minutes per run
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

async def main():
    """Main entry point for GitHub Actions daily collection."""
    try:
        workflow = GitHubActionsDailyCollection()
        result = await workflow.run()
        
        if result["success"]:
            print("✅ Daily collection completed successfully")
            sys.exit(0)
        else:
            print(f"❌ Daily collection failed: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Fatal error in daily collection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Non-Functional Requirements

#### NFR-1: Resource Management
- **GitHub Actions Minutes**: < 10 minutes per daily run (200 minutes/month total)
- **Artifact Storage**: < 100MB per workflow run, 30-day retention
- **Container Size**: < 500MB final image size
- **Memory Usage**: < 1GB during workflow execution

#### NFR-2: Reliability
- **Workflow Success Rate**: 95% successful daily executions
- **Error Recovery**: Automatic retry for transient failures (max 3 attempts)
- **Notification System**: GitHub Issues for workflow failures
- **Monitoring**: Comprehensive workflow metrics and logging

#### NFR-3: Security
- **Secret Management**: All sensitive data in GitHub Secrets
- **Container Security**: Non-root execution, minimal base image
- **Access Control**: Minimal repository permissions
- **Audit Trail**: Complete workflow execution logging

## Implementation Plan

### Phase 1: Basic Workflow Setup (Days 1-2)
- [ ] Create daily collection workflow with basic Epic 1/2 integration
- [ ] Set up GitHub Secrets management
- [ ] Implement environment configuration scripts
- [ ] Add basic error handling and notifications

### Phase 2: Advanced Orchestration (Days 2-3)
- [ ] Integrate Epic 3 orchestration engine
- [ ] Add workflow monitoring and metrics collection
- [ ] Implement comprehensive error recovery
- [ ] Create execution reporting system

### Phase 3: Quality Assurance (Days 3-4)
- [ ] Add quality assurance workflow
- [ ] Implement performance benchmarking
- [ ] Add security scanning integration
- [ ] Create comprehensive test suite

### Phase 4: Production Hardening (Days 4-5)
- [ ] Optimize resource usage and performance
- [ ] Add comprehensive monitoring and alerting
- [ ] Implement deployment workflows
- [ ] Create operational documentation

## Testing Strategy

### Unit Tests
```python
# tests/automation/workflows/test_github_actions.py
import pytest
from unittest.mock import AsyncMock, patch
from phoenix_real_estate.automation.workflows.daily_collection import GitHubActionsDailyCollection

class TestGitHubActionsDailyCollection:
    @pytest.fixture
    async def workflow(self):
        with patch('phoenix_real_estate.automation.workflows.daily_collection.ConfigProvider'):
            return GitHubActionsDailyCollection()
    
    async def test_workflow_execution_success(self, workflow):
        # Test successful workflow execution
        with patch.object(workflow.orchestration_engine, 'run_daily_workflow') as mock_run:
            mock_run.return_value = {
                "success": True,
                "metrics": {"total_properties": 100}
            }
            
            result = await workflow.run()
            
            assert result["success"] is True
            assert "execution_report" in result
    
    async def test_epic_integration(self, workflow):
        # Test integration with Epic 1 and Epic 2 components
        assert workflow.repository is not None
        assert workflow.metrics is not None
        assert workflow.orchestration_engine is not None
```

### Integration Tests
- **Epic 1-2-3 Integration**: Test complete workflow from configuration through execution
- **GitHub Actions Environment**: Test in actual GitHub Actions runner
- **Error Scenarios**: Test failure handling and recovery
- **Resource Constraints**: Test within GitHub Actions limits

## Success Criteria

### Acceptance Criteria
- [ ] Daily workflow executes automatically at scheduled time
- [ ] Complete integration with Epic 1 configuration and Epic 2 collectors
- [ ] Workflow completes within 75 minutes
- [ ] Uses < 10 GitHub Actions minutes per run
- [ ] Generates comprehensive execution reports
- [ ] Handles failures gracefully with notifications
- [ ] Provides monitoring data for Epic 4 analysis

### Quality Gates
- [ ] 90%+ test coverage for workflow modules
- [ ] All integration tests pass in GitHub Actions environment
- [ ] Security scan shows no vulnerabilities
- [ ] Performance benchmarks meet targets
- [ ] Documentation complete for operations team

---

**Task Owner**: DevOps Engineer  
**Epic**: Epic 3 - Automation & Orchestration  
**Estimated Effort**: 5 days  
**Dependencies**: Epic 1 (Foundation), Epic 2 (Collection), Docker containerization  
**Deliverables**: GitHub Actions workflows, configuration scripts, monitoring integration, documentation