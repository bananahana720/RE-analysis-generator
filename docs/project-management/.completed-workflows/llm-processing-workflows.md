# LLM Processing Workflows for GitHub Actions

## Overview

This document provides comprehensive patterns and workflows for integrating Ollama-based LLM processing into GitHub Actions CI/CD pipelines, based on Task 6 implementation experience.

## Ollama Service Management

### Service Installation and Startup

```yaml
# .github/workflows/daily-collection.yml - LLM Service Setup
- name: Setup Ollama Service
  id: ollama-setup
  run: |
    echo "::group::Installing Ollama"
    
    # Check if Ollama is already installed (cached)
    if command -v ollama &> /dev/null; then
      echo "Ollama already installed"
    else
      echo "Installing Ollama..."
      curl -fsSL https://ollama.ai/install.sh | sh
    fi
    
    echo "::endgroup::"
    
    echo "::group::Starting Ollama Service"
    
    # Configure resource limits for GitHub Actions
    export OLLAMA_MAX_LOADED_MODELS=1
    export OLLAMA_NUM_PARALLEL=2
    export OLLAMA_MODELS=/tmp/ollama/models
    
    # Start service in background
    nohup ollama serve > ollama.log 2>&1 &
    echo $! > ollama.pid
    
    # Wait for service to be ready
    echo "Waiting for Ollama service..."
    for i in {1..30}; do
      if curl -s http://localhost:11434/api/version > /dev/null; then
        echo "✅ Ollama service is ready"
        break
      fi
      echo "Waiting... ($i/30)"
      sleep 2
    done
    
    # Verify service is running
    if ! curl -s http://localhost:11434/api/version > /dev/null; then
      echo "❌ Ollama service failed to start"
      cat ollama.log
      exit 1
    fi
    
    echo "::endgroup::"
```

### Model Management

```yaml
- name: Manage LLM Model
  id: model-setup
  run: |
    echo "::group::Model Setup"
    
    # Check if model is already available
    if ollama list | grep -q "llama3.2:latest"; then
      echo "✅ Model already available"
    else
      echo "📥 Pulling llama3.2:latest model..."
      
      # Pull with progress tracking
      ollama pull llama3.2:latest --verbose
      
      if [ $? -ne 0 ]; then
        echo "❌ Failed to pull model"
        exit 1
      fi
    fi
    
    # Verify model size and info
    ollama show llama3.2:latest --modelfile
    
    # Warm up the model with a test prompt
    echo "🔥 Warming up model..."
    echo "Test prompt" | ollama run llama3.2:latest "Say hello" --verbose
    
    echo "::endgroup::"
```

## Python Integration Patterns

### Workflow-Aware ProcessingIntegrator

```python
# src/phoenix_real_estate/automation/workflows/llm_integration.py
"""LLM processing integration for GitHub Actions workflows."""

import asyncio
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.orchestration import ProcessingIntegrator
from phoenix_real_estate.collectors.processing.ollama_client import OllamaClient


class WorkflowLLMProcessor:
    """LLM processor optimized for GitHub Actions workflows."""
    
    def __init__(self, config: ConfigProvider):
        self.config = config
        self.logger = get_logger("workflow.llm.processor")
        self.processing_integrator: Optional[ProcessingIntegrator] = None
        
        # GitHub Actions specific configuration
        self.is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
        self.workflow_run_id = os.getenv("GITHUB_RUN_ID")
        
        # Performance settings for CI environment
        self.batch_size = int(os.getenv("LLM_BATCH_SIZE", "5"))
        self.timeout_seconds = int(os.getenv("LLM_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        
    async def initialize(self) -> Dict[str, Any]:
        """Initialize LLM processing with health checks."""
        try:
            self.logger.info(
                "Initializing LLM processor",
                extra={
                    "github_actions": self.is_github_actions,
                    "workflow_run_id": self.workflow_run_id
                }
            )
            
            # Verify Ollama service health
            health_status = await self._check_ollama_health()
            if not health_status["healthy"]:
                raise RuntimeError(f"Ollama service unhealthy: {health_status}")
            
            # Initialize ProcessingIntegrator
            self.processing_integrator = ProcessingIntegrator(self.config)
            await self.processing_integrator.__aenter__()
            
            # Verify model availability
            model_status = await self._verify_model()
            
            return {
                "initialized": True,
                "health": health_status,
                "model": model_status,
                "settings": {
                    "batch_size": self.batch_size,
                    "timeout": self.timeout_seconds,
                    "max_retries": self.max_retries
                }
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize LLM processor",
                extra={"error": str(e)}
            )
            raise
    
    async def process_properties_with_monitoring(
        self, 
        properties: List[Dict]
    ) -> Dict[str, Any]:
        """Process properties with comprehensive monitoring."""
        start_time = datetime.now(UTC)
        results = {
            "processed": [],
            "failed": [],
            "metrics": {}
        }
        
        try:
            # Process in batches for memory efficiency
            for i in range(0, len(properties), self.batch_size):
                batch = properties[i:i + self.batch_size]
                
                self.logger.info(
                    f"Processing batch {i//self.batch_size + 1}",
                    extra={
                        "batch_size": len(batch),
                        "total_properties": len(properties)
                    }
                )
                
                # Process with retry logic
                batch_results = await self._process_batch_with_retry(batch)
                
                # Separate successful and failed
                for idx, result in enumerate(batch_results):
                    if result and result.get("confidence_score", 0) > 0.7:
                        results["processed"].append(result)
                    else:
                        results["failed"].append({
                            "property": batch[idx],
                            "reason": "Low confidence or processing error",
                            "result": result
                        })
                
                # GitHub Actions progress reporting
                if self.is_github_actions:
                    progress = (i + len(batch)) / len(properties) * 100
                    print(f"::notice ::LLM Processing Progress: {progress:.1f}%")
            
            # Calculate final metrics
            duration = (datetime.now(UTC) - start_time).total_seconds()
            results["metrics"] = {
                "total_processed": len(results["processed"]),
                "total_failed": len(results["failed"]),
                "success_rate": len(results["processed"]) / len(properties) if properties else 0,
                "processing_time": duration,
                "avg_time_per_property": duration / len(properties) if properties else 0
            }
            
            # Log summary for GitHub Actions
            if self.is_github_actions:
                self._output_github_summary(results["metrics"])
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Property processing failed",
                extra={"error": str(e)}
            )
            results["error"] = str(e)
            return results
    
    async def _process_batch_with_retry(self, batch: List[Dict]) -> List[Dict]:
        """Process batch with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                # Use ProcessingIntegrator for batch processing
                results = await self.processing_integrator.process_maricopa_batch(batch)
                return results
                
            except Exception as e:
                wait_time = 2 ** attempt  # Exponential backoff
                self.logger.warning(
                    f"Batch processing attempt {attempt + 1} failed",
                    extra={
                        "error": str(e),
                        "retry_in": wait_time
                    }
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    # Final attempt failed
                    return [None] * len(batch)
        
        return [None] * len(batch)
    
    async def _check_ollama_health(self) -> Dict[str, Any]:
        """Check Ollama service health."""
        try:
            client = OllamaClient(
                base_url=self.config.get("OLLAMA_HOST", "http://localhost:11434")
            )
            
            # Check version endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{client.base_url}/api/version") as resp:
                    if resp.status == 200:
                        version_info = await resp.json()
                        return {
                            "healthy": True,
                            "version": version_info
                        }
                    else:
                        return {
                            "healthy": False,
                            "error": f"HTTP {resp.status}"
                        }
                        
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _verify_model(self) -> Dict[str, Any]:
        """Verify model availability and readiness."""
        try:
            model_name = self.config.get("OLLAMA_MODEL", "llama3.2:latest")
            
            # Test model with simple prompt
            client = OllamaClient(
                base_url=self.config.get("OLLAMA_HOST", "http://localhost:11434")
            )
            
            test_response = await client.generate(
                prompt="Extract: 3 bed 2 bath",
                model=model_name
            )
            
            return {
                "available": True,
                "model": model_name,
                "test_passed": bool(test_response)
            }
            
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _output_github_summary(self, metrics: Dict[str, Any]):
        """Output summary for GitHub Actions."""
        summary = f"""
## 🤖 LLM Processing Summary

- **Total Processed**: {metrics['total_processed']}
- **Success Rate**: {metrics['success_rate']*100:.1f}%
- **Processing Time**: {metrics['processing_time']:.1f}s
- **Avg Time/Property**: {metrics['avg_time_per_property']:.2f}s
"""
        
        # Write to GitHub Actions summary
        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a") as f:
                f.write(summary)
        
        # Also output as notice
        print(f"::notice title=LLM Processing Complete::{metrics['total_processed']} properties processed with {metrics['success_rate']*100:.1f}% success rate")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.processing_integrator:
            await self.processing_integrator.__aexit__(None, None, None)
```

## Error Handling Patterns

### Graceful Degradation Strategy

```yaml
- name: Run Collection with LLM Processing
  id: collection
  continue-on-error: true
  run: |
    # Set error handling mode
    export LLM_FALLBACK_ENABLED=true
    
    # Run collection with timeout
    timeout 75m uv run python -m phoenix_real_estate.automation.workflows.daily_collection
    
    # Capture exit code
    echo "exit_code=$?" >> $GITHUB_OUTPUT

- name: Handle LLM Processing Failures
  if: steps.collection.outputs.exit_code != '0'
  run: |
    echo "::warning::Collection completed with errors"
    
    # Check if LLM processing failed
    if grep -q "Ollama service unavailable" logs/collection.log; then
      echo "::error::LLM processing failed - storing raw data for later processing"
      
      # Run fallback storage
      uv run python -m phoenix_real_estate.automation.workflows.store_raw_fallback
    fi
```

### Circuit Breaker Implementation

```python
class LLMCircuitBreaker:
    """Circuit breaker for LLM service failures."""
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 300,
        half_open_attempts: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.half_open_count = 0
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                self.half_open_count = 0
            else:
                raise CircuitOpenError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if self.last_failure_time is None:
            return False
            
        time_since_failure = (datetime.now(UTC) - self.last_failure_time).seconds
        return time_since_failure >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == "half-open":
            self.half_open_count += 1
            if self.half_open_count >= self.half_open_attempts:
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
        elif self.state == "half-open":
            self.state = "open"
            logger.warning("Circuit breaker reopened during half-open state")
```

## Performance Optimization

### Caching Strategy

```yaml
- name: Setup LLM Model Cache
  run: |
    # Use GitHub Actions cache for model files
    echo "Setting up model cache..."
    
    # Create cache directory
    mkdir -p ${{ runner.temp }}/ollama-cache
    export OLLAMA_MODELS=${{ runner.temp }}/ollama-cache
    
    # Check cache size
    du -sh $OLLAMA_MODELS || echo "Cache empty"

- name: Cache Ollama Models
  uses: actions/cache@v3
  with:
    path: ${{ runner.temp }}/ollama-cache
    key: ollama-models-${{ hashFiles('**/ollama-model-version.txt') }}
    restore-keys: |
      ollama-models-
```

### Batch Processing Optimization

```python
class OptimizedBatchProcessor:
    """Optimized batch processing for GitHub Actions."""
    
    def __init__(self, config: ConfigProvider):
        self.config = config
        
        # Optimize for GitHub Actions runners (2 CPU, 7GB RAM)
        self.optimal_batch_size = self._calculate_optimal_batch_size()
        self.parallel_workers = min(2, os.cpu_count())
        
    def _calculate_optimal_batch_size(self) -> int:
        """Calculate optimal batch size based on available resources."""
        # Estimate based on model size and available memory
        available_memory_gb = 7  # GitHub Actions runner
        model_memory_gb = 2      # llama3.2:latest
        overhead_gb = 1          # Python + other processes
        
        usable_memory_gb = available_memory_gb - model_memory_gb - overhead_gb
        
        # Assume ~10MB per property in memory
        properties_per_gb = 100
        
        return int(usable_memory_gb * properties_per_gb)
    
    async def process_optimized(self, properties: List[Dict]) -> List[Dict]:
        """Process properties with optimal batching."""
        results = []
        
        # Split into optimal batches
        batches = [
            properties[i:i + self.optimal_batch_size]
            for i in range(0, len(properties), self.optimal_batch_size)
        ]
        
        # Process batches with progress reporting
        for idx, batch in enumerate(batches):
            self.logger.info(
                f"Processing batch {idx + 1}/{len(batches)}",
                extra={"batch_size": len(batch)}
            )
            
            # Process batch
            batch_results = await self._process_single_batch(batch)
            results.extend(batch_results)
            
            # Report progress to GitHub Actions
            if os.getenv("GITHUB_ACTIONS"):
                progress = (idx + 1) / len(batches) * 100
                print(f"::group::Batch {idx + 1} Complete ({progress:.0f}%)")
                print(f"Processed: {len(batch)} properties")
                print(f"Success rate: {self._calculate_success_rate(batch_results):.1f}%")
                print("::endgroup::")
        
        return results
```

## Monitoring and Alerting

### GitHub Actions Annotations

```python
class GitHubActionsReporter:
    """Reporter for GitHub Actions workflow runs."""
    
    def __init__(self):
        self.is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
        
    def report_error(self, error: str, file: str = None, line: int = None):
        """Report error as GitHub Actions annotation."""
        if not self.is_github_actions:
            return
            
        if file and line:
            print(f"::error file={file},line={line}::{error}")
        else:
            print(f"::error::{error}")
    
    def report_warning(self, warning: str):
        """Report warning as GitHub Actions annotation."""
        if not self.is_github_actions:
            return
            
        print(f"::warning::{warning}")
    
    def report_notice(self, message: str, title: str = None):
        """Report notice as GitHub Actions annotation."""
        if not self.is_github_actions:
            return
            
        if title:
            print(f"::notice title={title}::{message}")
        else:
            print(f"::notice::{message}")
    
    def create_summary(self, results: Dict[str, Any]):
        """Create job summary for GitHub Actions."""
        if not self.is_github_actions:
            return
            
        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if not summary_file:
            return
            
        summary = self._format_summary(results)
        
        with open(summary_file, "w") as f:
            f.write(summary)
    
    def _format_summary(self, results: Dict[str, Any]) -> str:
        """Format results as markdown summary."""
        return f"""
# 📊 Daily Collection Results

## Overview
- **Status**: {'✅ Success' if results['success'] else '❌ Failed'}
- **Duration**: {results['duration_minutes']:.1f} minutes
- **Properties Collected**: {results['total_collected']}

## LLM Processing
- **Properties Processed**: {results['llm']['processed']}
- **Success Rate**: {results['llm']['success_rate']*100:.1f}%
- **Average Confidence**: {results['llm']['avg_confidence']:.2f}
- **Processing Time**: {results['llm']['processing_time']:.1f}s

## Resource Usage
- **GitHub Actions Minutes**: {results['github_minutes']:.1f}
- **Memory Peak**: {results['memory_peak_mb']:.0f} MB
- **Cache Hit Rate**: {results['cache_hit_rate']*100:.1f}%

## Errors and Warnings
{self._format_errors(results.get('errors', []))}

---
*Generated at {datetime.now(UTC).isoformat()}*
"""
```

## Testing in CI Environment

### Integration Test Setup

```yaml
- name: Run LLM Integration Tests
  run: |
    # Start Ollama in test mode
    export OLLAMA_DEBUG=1
    export OLLAMA_MODELS=/tmp/test-models
    
    # Use smaller model for tests
    ollama pull tinyllama:latest
    
    # Run integration tests
    uv run pytest tests/integration/test_llm_workflow.py \
      -v \
      --cov=phoenix_real_estate.automation.workflows \
      --cov-report=xml \
      --cov-report=term-missing
```

### Mock Strategies for Unit Tests

```python
@pytest.fixture
def mock_ollama_for_ci():
    """Mock Ollama for CI environment tests."""
    with patch('phoenix_real_estate.collectors.processing.ollama_client.OllamaClient') as mock:
        # Configure mock
        instance = mock.return_value
        instance.generate = AsyncMock(
            return_value={
                "response": json.dumps({
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "confidence_score": 0.95
                })
            }
        )
        
        yield instance

async def test_workflow_in_ci(mock_ollama_for_ci):
    """Test workflow in CI environment."""
    # Set CI environment variables
    os.environ["GITHUB_ACTIONS"] = "true"
    os.environ["GITHUB_RUN_ID"] = "12345"
    
    # Run workflow
    workflow = GitHubActionsDailyCollection()
    result = await workflow.run()
    
    # Verify CI-specific behavior
    assert result["github_actions_mode"] is True
    assert mock_ollama_for_ci.generate.called
```

## Best Practices

### 1. Resource Management
- Always set memory limits for Ollama
- Use model caching to reduce download time
- Clean up model files in post-job steps
- Monitor memory usage throughout workflow

### 2. Error Recovery
- Implement circuit breakers for service failures
- Store raw data when LLM processing fails
- Use GitHub Issues for critical error tracking
- Provide detailed error context in logs

### 3. Performance
- Optimize batch sizes for runner specs
- Use parallel processing where safe
- Cache processed results aggressively
- Monitor processing time per property

### 4. Monitoring
- Use GitHub Actions annotations effectively
- Create comprehensive job summaries
- Track metrics across workflow runs
- Alert on performance degradation

### 5. Testing
- Mock LLM services in unit tests
- Use smaller models for integration tests
- Test failure scenarios thoroughly
- Validate resource usage in tests

## Troubleshooting Checklist

### Service Issues
- [ ] Verify Ollama service is running: `curl http://localhost:11434/api/version`
- [ ] Check model is downloaded: `ollama list`
- [ ] Review service logs: `cat ollama.log`
- [ ] Verify port 11434 is not in use: `lsof -i :11434`

### Performance Issues
- [ ] Check available memory: `free -h`
- [ ] Monitor CPU usage: `top`
- [ ] Review batch sizes in logs
- [ ] Check for model loading delays

### Integration Issues
- [ ] Verify ProcessingIntegrator initialization
- [ ] Check configuration loading
- [ ] Review error handling paths
- [ ] Validate timeout settings

### GitHub Actions Specific
- [ ] Check runner specifications
- [ ] Verify secret availability
- [ ] Review artifact uploads
- [ ] Monitor minute usage