# Task 7: GitHub Actions Workflow - TDD Subtasks

## Overview
This document outlines TDD-based subtasks for implementing GitHub Actions workflows, organized by talent/role for optimal task assignment.

## Talent Organization

### 1. DevOps Engineer (Primary)
**Focus**: CI/CD pipelines, GitHub Actions, deployment automation

### 2. Backend Developer
**Focus**: Python integration, Epic connections, error handling

### 3. QA Engineer
**Focus**: Testing workflows, quality gates, monitoring

### 4. Security Engineer
**Focus**: Secrets management, security scanning, access control

---

## Phase 1: Basic Workflow Setup (Days 1-2)

### Subtask 1.1: GitHub Actions Environment Configuration [DevOps Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_github_environment.py
import pytest
from unittest.mock import patch, MagicMock
import os

class TestGitHubEnvironmentSetup:
    """Test GitHub Actions environment configuration."""
    
    def test_environment_variables_validation(self):
        """Test that required environment variables are validated."""
        # Given: Missing required environment variables
        with patch.dict(os.environ, {}, clear=True):
            from phoenix_real_estate.automation.workflows.github_environment import GitHubEnvironmentValidator
            
            # When: Validating environment
            validator = GitHubEnvironmentValidator()
            
            # Then: Should identify missing variables
            missing = validator.get_missing_required_variables()
            assert "MONGODB_CONNECTION_STRING" in missing
            assert "MARICOPA_API_KEY" in missing
            assert "TARGET_ZIP_CODES" in missing
    
    def test_github_secrets_loading(self):
        """Test loading configuration from GitHub Secrets."""
        # Given: GitHub Secrets in environment
        test_env = {
            "MONGODB_CONNECTION_STRING": "mongodb://test:27017",
            "MARICOPA_API_KEY": "test-api-key",
            "TARGET_ZIP_CODES": "85031,85033,85035"
        }
        
        with patch.dict(os.environ, test_env):
            from phoenix_real_estate.automation.workflows.github_environment import GitHubSecretsLoader
            
            # When: Loading secrets
            loader = GitHubSecretsLoader()
            config = loader.load_configuration()
            
            # Then: Configuration should be properly loaded
            assert config.get("MONGODB_CONNECTION_STRING") == "mongodb://test:27017"
            assert config.get("MARICOPA_API_KEY") == "test-api-key"
            assert config.get("TARGET_ZIP_CODES") == ["85031", "85033", "85035"]
    
    def test_configuration_file_generation(self):
        """Test generation of configuration files for GitHub Actions."""
        # Given: Configuration data
        config_data = {
            "ENVIRONMENT": "github_actions",
            "LOG_LEVEL": "INFO",
            "WORKFLOW_TIMEOUT_MINUTES": 75
        }
        
        from phoenix_real_estate.automation.workflows.github_environment import ConfigurationGenerator
        
        # When: Generating configuration
        generator = ConfigurationGenerator()
        config_path = generator.generate_config_file(config_data)
        
        # Then: Configuration file should be created
        assert config_path.exists()
        assert config_path.suffix == ".yaml"
        # Verify content structure
        import yaml
        with open(config_path) as f:
            loaded_config = yaml.safe_load(f)
        assert loaded_config["environment"] == "github_actions"
```

**Implementation Tasks**:
1. Create `GitHubEnvironmentValidator` class
2. Implement `GitHubSecretsLoader` for secret management
3. Build `ConfigurationGenerator` for config file creation
4. Add validation for all required Epic 1-3 configuration

---

### Subtask 1.2: Daily Collection Workflow YAML [DevOps Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_workflow_yaml.py
import pytest
import yaml
from pathlib import Path

class TestWorkflowYAML:
    """Test GitHub Actions workflow YAML generation and validation."""
    
    def test_daily_collection_workflow_structure(self):
        """Test daily collection workflow YAML structure."""
        from phoenix_real_estate.automation.workflows.yaml_generator import DailyCollectionWorkflow
        
        # Given: Workflow configuration
        config = {
            "schedule_cron": "0 10 * * *",  # 3 AM Phoenix time
            "python_version": "3.12.4",
            "timeout_minutes": 90
        }
        
        # When: Generating workflow YAML
        workflow = DailyCollectionWorkflow(config)
        yaml_content = workflow.generate()
        
        # Then: YAML should have correct structure
        parsed = yaml.safe_load(yaml_content)
        assert parsed["name"] == "Daily Real Estate Data Collection"
        assert parsed["on"]["schedule"][0]["cron"] == "0 10 * * *"
        assert parsed["on"]["workflow_dispatch"] is not None
        assert parsed["jobs"]["collect-data"]["timeout-minutes"] == 90
    
    def test_workflow_steps_validation(self):
        """Test that workflow contains all required steps."""
        from phoenix_real_estate.automation.workflows.yaml_generator import DailyCollectionWorkflow
        
        # When: Generating workflow
        workflow = DailyCollectionWorkflow({})
        yaml_content = workflow.generate()
        parsed = yaml.safe_load(yaml_content)
        
        # Then: Should have all required steps
        steps = parsed["jobs"]["collect-data"]["steps"]
        step_names = [step["name"] for step in steps]
        
        assert "Checkout Repository" in step_names
        assert "Set up Python" in step_names
        assert "Install UV Package Manager" in step_names
        assert "Configure Environment" in step_names
        assert "Run Data Collection" in step_names
        assert "Generate Collection Report" in step_names
        assert "Upload Collection Artifacts" in step_names
        assert "Notify on Failure" in step_names
    
    def test_secret_references(self):
        """Test that workflow properly references GitHub Secrets."""
        from phoenix_real_estate.automation.workflows.yaml_generator import DailyCollectionWorkflow
        
        # When: Generating workflow
        workflow = DailyCollectionWorkflow({})
        yaml_content = workflow.generate()
        
        # Then: Should reference secrets correctly
        assert "${{ secrets.MONGODB_CONNECTION_STRING }}" in yaml_content
        assert "${{ secrets.MARICOPA_API_KEY }}" in yaml_content
        assert "${{ secrets.WEBSHARE_USERNAME }}" in yaml_content
        assert "${{ secrets.WEBSHARE_PASSWORD }}" in yaml_content
```

**Implementation Tasks**:
1. Create `DailyCollectionWorkflow` YAML generator
2. Implement proper cron scheduling for Phoenix timezone
3. Add all required workflow steps with proper ordering
4. Configure secret references and environment variables

---

### Subtask 1.3: Error Handling and Notifications [Backend Developer]

**TDD Test First**:
```python
# tests/automation/workflows/test_error_handling.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestWorkflowErrorHandling:
    """Test error handling and notification system."""
    
    @pytest.mark.asyncio
    async def test_workflow_failure_notification(self):
        """Test that workflow failures trigger notifications."""
        from phoenix_real_estate.automation.workflows.notifications import WorkflowNotifier
        
        # Given: A workflow failure
        failure_context = {
            "workflow_name": "daily-collection",
            "run_id": "12345",
            "error": "Database connection failed",
            "timestamp": "2024-01-15T10:00:00Z"
        }
        
        # When: Notifying failure
        notifier = WorkflowNotifier()
        with patch.object(notifier, '_create_github_issue') as mock_create_issue:
            await notifier.notify_failure(failure_context)
        
        # Then: Should create GitHub issue
        mock_create_issue.assert_called_once()
        issue_data = mock_create_issue.call_args[0][0]
        assert "Daily Collection Failed" in issue_data["title"]
        assert "12345" in issue_data["body"]
        assert "automation" in issue_data["labels"]
        assert "failure" in issue_data["labels"]
    
    @pytest.mark.asyncio
    async def test_transient_error_retry(self):
        """Test retry mechanism for transient errors."""
        from phoenix_real_estate.automation.workflows.error_handler import WorkflowErrorHandler
        
        # Given: A transient error
        handler = WorkflowErrorHandler(max_retries=3, retry_delay=1)
        
        # Mock function that fails twice then succeeds
        mock_func = AsyncMock(side_effect=[
            Exception("Network timeout"),
            Exception("Connection reset"),
            {"success": True, "data": "collected"}
        ])
        
        # When: Running with retry
        result = await handler.run_with_retry(mock_func, "test_operation")
        
        # Then: Should retry and eventually succeed
        assert result["success"] is True
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_critical_error_handling(self):
        """Test handling of critical non-retryable errors."""
        from phoenix_real_estate.automation.workflows.error_handler import WorkflowErrorHandler
        
        # Given: A critical error
        handler = WorkflowErrorHandler()
        critical_error = ValueError("Invalid configuration")
        
        # When: Handling critical error
        with pytest.raises(ValueError):
            await handler.handle_error(critical_error, "test_operation", is_critical=True)
        
        # Then: Should log and re-raise without retry
        # Verify logging happened (would need to mock logger)
```

**Implementation Tasks**:
1. Create `WorkflowNotifier` for GitHub issue creation
2. Implement `WorkflowErrorHandler` with retry logic
3. Add error classification (transient vs critical)
4. Build comprehensive error reporting

---

## Phase 2: Advanced Orchestration (Days 2-3)

### Subtask 2.1: Epic 3 Orchestration Integration [Backend Developer]

**TDD Test First**:
```python
# tests/automation/workflows/test_orchestration_integration.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestOrchestrationIntegration:
    """Test integration with Epic 3 orchestration engine."""
    
    @pytest.mark.asyncio
    async def test_orchestration_engine_initialization(self):
        """Test proper initialization of orchestration engine."""
        from phoenix_real_estate.automation.workflows.daily_collection import GitHubActionsDailyCollection
        
        # Given: GitHub Actions environment
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            # When: Creating daily collection workflow
            workflow = GitHubActionsDailyCollection()
            
            # Then: Orchestration engine should be initialized
            assert workflow.orchestration_engine is not None
            assert workflow.workflow_monitor is not None
            assert workflow.config.get("EXECUTION_ENVIRONMENT") == "github_actions"
    
    @pytest.mark.asyncio
    async def test_workflow_execution_with_orchestration(self):
        """Test workflow execution using orchestration engine."""
        from phoenix_real_estate.automation.workflows.daily_collection import GitHubActionsDailyCollection
        
        # Given: Initialized workflow
        workflow = GitHubActionsDailyCollection()
        
        # Mock orchestration engine
        mock_result = {
            "success": True,
            "metrics": {
                "total_properties": 150,
                "collection_duration_seconds": 3600,
                "success_rate": 0.95
            }
        }
        workflow.orchestration_engine.run_daily_workflow = AsyncMock(return_value=mock_result)
        
        # When: Running workflow
        result = await workflow.run()
        
        # Then: Should execute orchestration and return results
        assert result["success"] is True
        assert result["workflow_result"]["metrics"]["total_properties"] == 150
        assert "execution_report" in result
        assert "context" in result
    
    @pytest.mark.asyncio
    async def test_workflow_monitoring_integration(self):
        """Test workflow monitoring and metrics collection."""
        from phoenix_real_estate.automation.workflows.daily_collection import GitHubActionsDailyCollection
        
        # Given: Workflow with monitoring
        workflow = GitHubActionsDailyCollection()
        workflow.workflow_monitor.on_workflow_started = AsyncMock()
        workflow.workflow_monitor.on_workflow_completed = AsyncMock()
        
        # When: Running workflow
        workflow.orchestration_engine.run_daily_workflow = AsyncMock(
            return_value={"success": True, "metrics": {}}
        )
        await workflow.run()
        
        # Then: Should track workflow lifecycle
        workflow.workflow_monitor.on_workflow_started.assert_called_once()
        workflow.workflow_monitor.on_workflow_completed.assert_called_once()
        
        # Verify context passed to monitor
        start_call = workflow.workflow_monitor.on_workflow_started.call_args
        assert start_call[0][0] == "github_actions_daily_collection"
        assert "run_id" in start_call[0][1]
```

**Implementation Tasks**:
1. Create `GitHubActionsDailyCollection` class
2. Integrate Epic 3 `OrchestrationEngine`
3. Add `WorkflowMonitor` integration
4. Implement execution context tracking

---

### Subtask 2.2: LLM Processing Integration [Backend Developer]

**TDD Test First**:
```python
# tests/automation/workflows/test_llm_integration.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

class TestLLMProcessingIntegration:
    """Test LLM processing integration with GitHub Actions workflows."""
    
    @pytest.mark.asyncio
    async def test_ollama_service_initialization(self):
        """Test Ollama service initialization in workflow context."""
        from phoenix_real_estate.automation.workflows.llm_integration import OllamaServiceManager
        
        # Given: GitHub Actions environment
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="llama3.2:latest")
            
            # When: Initializing Ollama service
            manager = OllamaServiceManager()
            result = await manager.initialize()
            
            # Then: Service should be started and model loaded
            assert result["service_status"] == "running"
            assert result["model_loaded"] == "llama3.2:latest"
            assert mock_run.call_count >= 2  # serve + pull commands
    
    @pytest.mark.asyncio
    async def test_processing_integrator_workflow_integration(self):
        """Test ProcessingIntegrator integration with workflow."""
        from phoenix_real_estate.automation.workflows.daily_collection import GitHubActionsDailyCollection
        from phoenix_real_estate.orchestration import ProcessingIntegrator
        
        # Given: Workflow with mock ProcessingIntegrator
        mock_integrator = AsyncMock(spec=ProcessingIntegrator)
        mock_integrator.process_maricopa_batch.return_value = [
            {"property_id": "123", "confidence_score": 0.95}
        ]
        
        with patch('phoenix_real_estate.automation.workflows.daily_collection.ProcessingIntegrator', return_value=mock_integrator):
            workflow = GitHubActionsDailyCollection()
            
            # When: Running workflow with collected properties
            properties = [{"html": "<div>property data</div>"}]
            result = await workflow.process_with_llm(properties)
            
            # Then: Properties should be processed through LLM
            assert mock_integrator.process_maricopa_batch.called
            assert result["processed_count"] == 1
            assert result["average_confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_llm_failure_handling(self):
        """Test handling of LLM processing failures."""
        from phoenix_real_estate.automation.workflows.llm_integration import LLMProcessingHandler
        
        # Given: LLM service failure
        handler = LLMProcessingHandler()
        with patch('phoenix_real_estate.orchestration.ProcessingIntegrator') as mock_integrator:
            mock_integrator.side_effect = Exception("Ollama service unavailable")
            
            # When: Processing with failed LLM
            result = await handler.process_with_fallback([{"html": "data"}])
            
            # Then: Should fallback gracefully
            assert result["fallback_used"] is True
            assert result["error"] == "Ollama service unavailable"
            assert result["raw_data_stored"] is True
    
    @pytest.mark.asyncio
    async def test_processing_metrics_collection(self):
        """Test LLM processing metrics collection."""
        from phoenix_real_estate.automation.workflows.metrics import LLMMetricsCollector
        
        # Given: Processing results
        processing_results = [
            {"property_id": "1", "processing_time": 1.2, "confidence_score": 0.95},
            {"property_id": "2", "processing_time": 1.5, "confidence_score": 0.92}
        ]
        
        # When: Collecting metrics
        collector = LLMMetricsCollector()
        metrics = collector.calculate_metrics(processing_results)
        
        # Then: Metrics should be calculated correctly
        assert metrics["total_processed"] == 2
        assert metrics["average_processing_time"] == 1.35
        assert metrics["average_confidence_score"] == 0.935
        assert metrics["processing_success_rate"] == 1.0
    
    def test_ollama_health_check_script(self):
        """Test Ollama health check script generation."""
        from phoenix_real_estate.automation.workflows.scripts import OllamaScriptGenerator
        
        # When: Generating health check script
        generator = OllamaScriptGenerator()
        script = generator.generate_health_check()
        
        # Then: Script should contain required checks
        assert "curl -s http://localhost:11434/api/version" in script
        assert "ollama serve" in script
        assert "ollama pull llama3.2:latest" in script
        assert "sleep" in script  # Wait for service startup
```

**Implementation Tasks**:
1. Create `OllamaServiceManager` for service lifecycle
2. Integrate `ProcessingIntegrator` into workflow
3. Implement `LLMProcessingHandler` with fallback logic
4. Add `LLMMetricsCollector` for processing metrics
5. Create health check and startup scripts

---

### Subtask 2.3: Execution Reporting System [QA Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_execution_reporting.py
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestExecutionReporting:
    """Test execution reporting for GitHub Actions artifacts."""
    
    def test_execution_report_generation(self):
        """Test generation of execution reports."""
        from phoenix_real_estate.automation.workflows.reporting import ExecutionReportGenerator
        
        # Given: Workflow execution results
        workflow_result = {
            "success": True,
            "metrics": {
                "total_properties": 100,
                "success_rate": 0.92,
                "duration_seconds": 3600
            },
            "collectors": {
                "maricopa": {"collected": 80, "errors": 5},
                "phoenix_mls": {"collected": 20, "errors": 2}
            }
        }
        
        # When: Generating report
        generator = ExecutionReportGenerator()
        report = generator.generate_report(workflow_result)
        
        # Then: Report should contain all required sections
        assert report["report_type"] == "github_actions_daily_collection"
        assert "execution_time" in report
        assert report["workflow_result"] == workflow_result
        assert "system_info" in report
        assert "resource_usage" in report
    
    def test_report_file_creation(self):
        """Test that reports are saved correctly for artifacts."""
        from phoenix_real_estate.automation.workflows.reporting import ExecutionReportGenerator
        
        # Given: Report generator with temp directory
        with patch("pathlib.Path.mkdir"):
            generator = ExecutionReportGenerator()
            workflow_result = {"success": True, "metrics": {}}
            
            # When: Saving report
            report_path = generator.save_report(workflow_result, "daily-collection")
            
            # Then: Report file should be created
            assert report_path.name.startswith("daily-collection-")
            assert report_path.suffix == ".json"
            assert report_path.parent.name == "reports"
    
    def test_failure_report_generation(self):
        """Test generation of failure reports with debugging info."""
        from phoenix_real_estate.automation.workflows.reporting import FailureReportGenerator
        
        # Given: A workflow failure
        error = ValueError("Database connection failed")
        context = {
            "run_id": "12345",
            "environment": "production",
            "timestamp": "2024-01-15T10:00:00Z"
        }
        
        # When: Generating failure report
        generator = FailureReportGenerator()
        report = generator.generate_failure_report(error, context)
        
        # Then: Report should contain debugging information
        assert report["report_type"] == "github_actions_failure"
        assert report["error_details"]["type"] == "ValueError"
        assert report["error_details"]["message"] == "Database connection failed"
        assert "traceback" in report["error_details"]
        assert report["context"] == context
        assert "system_state" in report
```

**Implementation Tasks**:
1. Create `ExecutionReportGenerator` class
2. Implement `FailureReportGenerator` for error reports
3. Add artifact-friendly JSON formatting
4. Include system and resource usage metrics

---

### Subtask 2.3: Resource Usage Monitoring [DevOps Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_resource_monitoring.py
import pytest
from unittest.mock import patch, MagicMock

class TestResourceMonitoring:
    """Test resource usage monitoring for GitHub Actions."""
    
    def test_github_actions_minutes_tracking(self):
        """Test tracking of GitHub Actions minutes usage."""
        from phoenix_real_estate.automation.workflows.monitoring import GitHubActionsResourceMonitor
        
        # Given: Resource monitor
        monitor = GitHubActionsResourceMonitor()
        
        # When: Recording workflow execution
        monitor.start_workflow("daily-collection")
        # Simulate 5 minute execution
        with patch("time.time", side_effect=[0, 300]):
            monitor.end_workflow("daily-collection")
        
        # Then: Should track minutes used
        usage = monitor.get_minutes_used()
        assert usage["daily-collection"] == 5.0
        assert monitor.get_total_minutes_used() == 5.0
    
    def test_memory_usage_monitoring(self):
        """Test memory usage monitoring during execution."""
        from phoenix_real_estate.automation.workflows.monitoring import MemoryMonitor
        
        # Given: Memory monitor
        monitor = MemoryMonitor()
        
        # Mock psutil
        with patch("psutil.Process") as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 512 * 1024 * 1024  # 512MB
            
            # When: Getting memory usage
            usage_mb = monitor.get_current_usage_mb()
            
            # Then: Should return usage in MB
            assert usage_mb == 512.0
    
    def test_resource_limits_enforcement(self):
        """Test enforcement of resource limits."""
        from phoenix_real_estate.automation.workflows.monitoring import ResourceLimitEnforcer
        
        # Given: Resource limits
        limits = {
            "max_memory_mb": 1024,
            "max_minutes": 90,
            "max_artifact_size_mb": 100
        }
        
        enforcer = ResourceLimitEnforcer(limits)
        
        # When: Checking limits
        # Memory within limit
        assert enforcer.check_memory_limit(800) is True
        assert enforcer.check_memory_limit(1200) is False
        
        # Minutes within limit
        assert enforcer.check_minutes_limit(60) is True
        assert enforcer.check_minutes_limit(95) is False
```

**Implementation Tasks**:
1. Create `GitHubActionsResourceMonitor` for minute tracking
2. Implement `MemoryMonitor` for memory usage
3. Build `ResourceLimitEnforcer` for limit checking
4. Add resource usage to execution reports

---

## Phase 3: Quality Assurance (Days 3-4)

### Subtask 3.1: Quality Assurance Workflow [QA Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_qa_workflow.py
import pytest
import yaml
from unittest.mock import patch, MagicMock

class TestQAWorkflow:
    """Test quality assurance workflow implementation."""
    
    def test_qa_workflow_yaml_structure(self):
        """Test QA workflow YAML generation."""
        from phoenix_real_estate.automation.workflows.yaml_generator import QAWorkflow
        
        # Given: QA workflow configuration
        config = {
            "schedule_cron": "0 2 * * 0",  # Weekly Sunday 2 AM UTC
            "environments": ["development", "staging"],
            "python_version": "3.12.4"
        }
        
        # When: Generating QA workflow
        workflow = QAWorkflow(config)
        yaml_content = workflow.generate()
        parsed = yaml.safe_load(yaml_content)
        
        # Then: Should have matrix strategy
        assert parsed["name"] == "Quality Assurance and Integration Tests"
        assert parsed["jobs"]["integration-tests"]["strategy"]["matrix"]["environment"] == ["development", "staging"]
        assert "Epic 1-2-3 Integration Test" in [step["name"] for step in parsed["jobs"]["integration-tests"]["steps"]]
    
    @pytest.mark.asyncio
    async def test_integration_test_execution(self):
        """Test execution of integration tests."""
        from phoenix_real_estate.automation.workflows.qa_runner import IntegrationTestRunner
        
        # Given: Test runner
        runner = IntegrationTestRunner(environment="staging")
        
        # Mock test execution
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "All tests passed"
            
            # When: Running integration tests
            result = await runner.run_epic_integration_tests()
            
            # Then: Should execute pytest with correct parameters
            assert result["success"] is True
            mock_run.assert_called()
            call_args = mock_run.call_args[0][0]
            assert "pytest" in call_args
            assert "tests/integration/" in call_args
            assert "--cov=phoenix_real_estate" in call_args
    
    def test_performance_benchmarking(self):
        """Test performance benchmark execution."""
        from phoenix_real_estate.automation.workflows.benchmarks import PerformanceBenchmark
        
        # Given: Performance benchmark
        benchmark = PerformanceBenchmark()
        
        # Mock benchmark results
        mock_results = {
            "collection_speed": {
                "properties_per_minute": 50,
                "average_response_time_ms": 200
            },
            "resource_usage": {
                "peak_memory_mb": 512,
                "cpu_usage_percent": 45
            }
        }
        
        with patch.object(benchmark, '_run_benchmark', return_value=mock_results):
            # When: Running benchmarks
            results = benchmark.run()
            
            # Then: Should return performance metrics
            assert results["collection_speed"]["properties_per_minute"] == 50
            assert results["resource_usage"]["peak_memory_mb"] == 512
```

**Implementation Tasks**:
1. Create `QAWorkflow` YAML generator
2. Implement `IntegrationTestRunner` for Epic integration tests
3. Build `PerformanceBenchmark` for performance testing
4. Add test result aggregation and reporting

---

### Subtask 3.2: Security Scanning Integration [Security Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_security_scanning.py
import pytest
from unittest.mock import patch, MagicMock

class TestSecurityScanning:
    """Test security scanning integration."""
    
    def test_bandit_security_scan(self):
        """Test Bandit security scanning integration."""
        from phoenix_real_estate.automation.workflows.security import SecurityScanner
        
        # Given: Security scanner
        scanner = SecurityScanner()
        
        # Mock bandit execution
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "errors": [],
                "results": [],
                "metrics": {"high": 0, "medium": 0, "low": 0}
            })
            
            # When: Running security scan
            results = scanner.run_bandit_scan("src/")
            
            # Then: Should execute bandit and parse results
            assert results["passed"] is True
            assert results["high_severity_issues"] == 0
            mock_run.assert_called()
            assert "-r src/" in " ".join(mock_run.call_args[0][0])
    
    def test_dependency_vulnerability_scan(self):
        """Test dependency vulnerability scanning."""
        from phoenix_real_estate.automation.workflows.security import DependencyScanner
        
        # Given: Dependency scanner
        scanner = DependencyScanner()
        
        # Mock safety check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "No known security vulnerabilities found"
            
            # When: Scanning dependencies
            results = scanner.scan_dependencies()
            
            # Then: Should run safety check
            assert results["vulnerabilities_found"] == 0
            assert results["scan_passed"] is True
    
    def test_secrets_detection(self):
        """Test detection of exposed secrets."""
        from phoenix_real_estate.automation.workflows.security import SecretsDetector
        
        # Given: Secrets detector
        detector = SecretsDetector()
        
        # Test file content with potential secret
        test_content = '''
        API_KEY = "sk-1234567890abcdef"
        DATABASE_URL = "mongodb://user:pass@localhost"
        '''
        
        # When: Scanning for secrets
        with patch("builtins.open", mock_open(read_data=test_content)):
            results = detector.scan_file("config.py")
        
        # Then: Should detect potential secrets
        assert len(results["potential_secrets"]) >= 1
        assert any("API_KEY" in str(secret) for secret in results["potential_secrets"])
```

**Implementation Tasks**:
1. Create `SecurityScanner` for Bandit integration
2. Implement `DependencyScanner` for vulnerability checking
3. Build `SecretsDetector` for secret detection
4. Add security report generation

---

### Subtask 3.3: QA Report Generation [QA Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_qa_reporting.py
import pytest
from pathlib import Path
import json

class TestQAReporting:
    """Test QA report generation."""
    
    def test_qa_summary_report_generation(self):
        """Test generation of comprehensive QA summary."""
        from phoenix_real_estate.automation.workflows.reporting import QASummaryGenerator
        
        # Given: QA test results
        test_results = {
            "unit_tests": {
                "passed": 150,
                "failed": 2,
                "coverage": 92.5
            },
            "integration_tests": {
                "passed": 25,
                "failed": 0,
                "duration_seconds": 300
            },
            "performance_benchmarks": {
                "collection_speed": 50,
                "memory_usage_mb": 512
            },
            "security_scan": {
                "vulnerabilities": 0,
                "code_issues": 3
            }
        }
        
        # When: Generating QA summary
        generator = QASummaryGenerator()
        summary = generator.generate_summary(test_results)
        
        # Then: Summary should aggregate all results
        assert summary["overall_status"] == "PASSED_WITH_WARNINGS"  # Due to 2 unit test failures
        assert summary["test_coverage"] == 92.5
        assert summary["total_tests_run"] == 177
        assert summary["quality_score"] >= 0.9  # High score despite minor issues
    
    def test_qa_artifact_packaging(self):
        """Test packaging of QA artifacts for upload."""
        from phoenix_real_estate.automation.workflows.reporting import QAArtifactPackager
        
        # Given: Various QA reports
        reports = {
            "qa_summary.json": {"status": "passed"},
            "performance_report.json": {"metrics": {}},
            "security_report.json": {"vulnerabilities": 0}
        }
        
        # When: Packaging artifacts
        packager = QAArtifactPackager()
        artifact_dir = packager.package_reports(reports, "qa-run-123")
        
        # Then: All reports should be in artifact directory
        assert artifact_dir.exists()
        assert (artifact_dir / "qa_summary.json").exists()
        assert (artifact_dir / "performance_report.json").exists()
        assert (artifact_dir / "security_report.json").exists()
```

**Implementation Tasks**:
1. Create `QASummaryGenerator` for report aggregation
2. Implement `QAArtifactPackager` for artifact preparation
3. Add quality scoring algorithm
4. Build comprehensive QA dashboard data

---

## Phase 4: Production Hardening (Days 4-5)

### Subtask 4.1: Container Build Optimization [DevOps Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_container_optimization.py
import pytest
from unittest.mock import patch, MagicMock

class TestContainerOptimization:
    """Test Docker container optimization."""
    
    def test_dockerfile_generation(self):
        """Test optimized Dockerfile generation."""
        from phoenix_real_estate.automation.workflows.docker import DockerfileGenerator
        
        # Given: Container configuration
        config = {
            "python_version": "3.12.4",
            "base_image": "python:3.12.4-slim",
            "optimize_size": True
        }
        
        # When: Generating Dockerfile
        generator = DockerfileGenerator(config)
        dockerfile_content = generator.generate()
        
        # Then: Should use multi-stage build
        assert "FROM python:3.12.4-slim AS builder" in dockerfile_content
        assert "FROM python:3.12.4-slim" in dockerfile_content
        assert "COPY --from=builder" in dockerfile_content
        assert "RUN pip install --no-cache-dir" in dockerfile_content
    
    def test_container_size_validation(self):
        """Test container size stays under 500MB limit."""
        from phoenix_real_estate.automation.workflows.docker import ContainerSizeValidator
        
        # Given: Built container
        validator = ContainerSizeValidator()
        
        # Mock docker image inspect
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json.dumps({
                "Size": 450 * 1024 * 1024  # 450MB
            })
            
            # When: Validating size
            result = validator.validate_image_size("phoenix-real-estate:latest")
            
            # Then: Should pass validation
            assert result["passed"] is True
            assert result["size_mb"] == 450
            assert result["size_mb"] < 500  # Under limit
    
    def test_layer_caching_configuration(self):
        """Test Docker layer caching setup."""
        from phoenix_real_estate.automation.workflows.yaml_generator import BuildWorkflow
        
        # When: Generating build workflow
        workflow = BuildWorkflow({})
        yaml_content = workflow.generate()
        parsed = yaml.safe_load(yaml_content)
        
        # Then: Should configure layer caching
        build_step = next(
            step for step in parsed["jobs"]["build"]["steps"] 
            if step["name"] == "Build and Push Docker Image"
        )
        assert build_step["with"]["cache-from"] == "type=gha"
        assert build_step["with"]["cache-to"] == "type=gha,mode=max"
```

**Implementation Tasks**:
1. Create `DockerfileGenerator` with multi-stage builds
2. Implement `ContainerSizeValidator` for size limits
3. Configure GitHub Actions caching
4. Add container security scanning

---

### Subtask 4.2: Deployment Workflow [DevOps Engineer]

**TDD Test First**:
```python
# tests/automation/workflows/test_deployment.py
import pytest
from unittest.mock import patch, AsyncMock

class TestDeploymentWorkflow:
    """Test deployment workflow implementation."""
    
    @pytest.mark.asyncio
    async def test_production_deployment_gates(self):
        """Test production deployment requires approval."""
        from phoenix_real_estate.automation.workflows.deployment import DeploymentManager
        
        # Given: Deployment manager
        manager = DeploymentManager(environment="production")
        
        # When: Checking deployment requirements
        requirements = await manager.check_deployment_requirements()
        
        # Then: Should require specific conditions
        assert requirements["requires_approval"] is True
        assert requirements["required_branch"] == "main"
        assert requirements["required_tests_passed"] is True
    
    @pytest.mark.asyncio
    async def test_deployment_rollback_capability(self):
        """Test deployment rollback mechanism."""
        from phoenix_real_estate.automation.workflows.deployment import DeploymentManager
        
        # Given: Failed deployment
        manager = DeploymentManager(environment="production")
        deployment_id = "deploy-123"
        
        # Mock deployment failure
        with patch.object(manager, '_deploy_image') as mock_deploy:
            mock_deploy.side_effect = Exception("Deployment failed")
            
            # When: Deployment fails
            try:
                await manager.deploy(deployment_id)
            except Exception:
                # Then: Should trigger rollback
                rollback_result = await manager.rollback(deployment_id)
                assert rollback_result["success"] is True
                assert rollback_result["rolled_back_to"] == "previous-version"
    
    def test_deployment_metadata_tagging(self):
        """Test deployment metadata and tagging."""
        from phoenix_real_estate.automation.workflows.deployment import DeploymentTagger
        
        # Given: Deployment context
        context = {
            "commit_sha": "abc123",
            "build_number": "456",
            "timestamp": "2024-01-15T10:00:00Z",
            "triggered_by": "schedule"
        }
        
        # When: Creating deployment tags
        tagger = DeploymentTagger()
        tags = tagger.create_deployment_tags(context)
        
        # Then: Should create comprehensive tags
        assert "v1.0.456" in tags
        assert "latest" in tags
        assert "sha-abc123" in tags
        assert len(tags) >= 3
```

**Implementation Tasks**:
1. Create `DeploymentManager` with environment gates
2. Implement rollback capability
3. Build `DeploymentTagger` for version management
4. Add deployment verification checks

---

### Subtask 4.3: Operational Documentation [Backend Developer]

**TDD Test First**:
```python
# tests/automation/workflows/test_documentation.py
import pytest
from pathlib import Path

class TestOperationalDocumentation:
    """Test operational documentation generation."""
    
    def test_runbook_generation(self):
        """Test generation of operational runbooks."""
        from phoenix_real_estate.automation.workflows.documentation import RunbookGenerator
        
        # Given: System configuration and workflows
        config = {
            "workflows": ["daily-collection", "build-deploy", "qa"],
            "environments": ["development", "staging", "production"],
            "monitoring_endpoints": ["metrics", "health", "status"]
        }
        
        # When: Generating runbook
        generator = RunbookGenerator()
        runbook = generator.generate_runbook(config)
        
        # Then: Runbook should contain operational procedures
        assert "Daily Collection Workflow" in runbook
        assert "Troubleshooting Guide" in runbook
        assert "Rollback Procedures" in runbook
        assert "Monitoring and Alerts" in runbook
        assert "Emergency Contacts" in runbook
    
    def test_secrets_documentation(self):
        """Test documentation of required secrets."""
        from phoenix_real_estate.automation.workflows.documentation import SecretsDocumentationGenerator
        
        # Given: Required secrets configuration
        secrets_config = {
            "MONGODB_CONNECTION_STRING": {
                "description": "MongoDB connection string",
                "format": "mongodb://user:pass@host:port/db",
                "required": True
            },
            "MARICOPA_API_KEY": {
                "description": "Maricopa County API key",
                "format": "alphanumeric string",
                "required": True
            }
        }
        
        # When: Generating documentation
        generator = SecretsDocumentationGenerator()
        docs = generator.generate_secrets_guide(secrets_config)
        
        # Then: Should document all secrets
        assert "## Required GitHub Secrets" in docs
        assert "MONGODB_CONNECTION_STRING" in docs
        assert "mongodb://user:pass@host:port/db" in docs
        assert "### How to Configure" in docs
    
    def test_monitoring_guide_generation(self):
        """Test generation of monitoring guide."""
        from phoenix_real_estate.automation.workflows.documentation import MonitoringGuideGenerator
        
        # Given: Monitoring configuration
        monitoring_config = {
            "metrics": [
                "workflow_execution_time",
                "collection_success_rate",
                "github_actions_minutes_used"
            ],
            "alerts": [
                {"name": "workflow_failure", "threshold": "3 consecutive failures"},
                {"name": "high_resource_usage", "threshold": "> 80% limit"}
            ]
        }
        
        # When: Generating monitoring guide
        generator = MonitoringGuideGenerator()
        guide = generator.generate_guide(monitoring_config)
        
        # Then: Should include monitoring procedures
        assert "## Key Metrics" in guide
        assert "workflow_execution_time" in guide
        assert "## Alert Configuration" in guide
        assert "workflow_failure" in guide
```

**Implementation Tasks**:
1. Create `RunbookGenerator` for operational procedures
2. Implement `SecretsDocumentationGenerator`
3. Build `MonitoringGuideGenerator`
4. Generate comprehensive ops documentation

---

## Summary

### Task Distribution by Role

**DevOps Engineer (Primary)**:
- Subtask 1.1: GitHub Actions Environment Configuration
- Subtask 1.2: Daily Collection Workflow YAML
- Subtask 2.3: Resource Usage Monitoring
- Subtask 4.1: Container Build Optimization
- Subtask 4.2: Deployment Workflow

**Backend Developer**:
- Subtask 1.3: Error Handling and Notifications
- Subtask 2.1: Epic 3 Orchestration Integration
- Subtask 2.2: LLM Processing Integration
- Subtask 4.3: Operational Documentation

**QA Engineer**:
- Subtask 2.3: Execution Reporting System
- Subtask 3.1: Quality Assurance Workflow
- Subtask 3.3: QA Report Generation

**Security Engineer**:
- Subtask 3.2: Security Scanning Integration

### TDD Implementation Strategy

1. **Write Tests First**: Each subtask starts with comprehensive test cases
2. **Test Categories**:
   - Unit tests for individual components
   - Integration tests for Epic connections
   - System tests for complete workflows
   - LLM-specific tests for Ollama integration
3. **Coverage Requirements**: Minimum 90% for all new code
4. **Continuous Validation**: Tests run on every commit via GitHub Actions
5. **Total Test Cases**: 88+ (includes 5 new LLM integration tests)

### Success Metrics

- All tests passing (100%)
- Code coverage > 90%
- Workflows execute within resource limits
- Documentation complete and validated
- Security scans passing
- Performance benchmarks met