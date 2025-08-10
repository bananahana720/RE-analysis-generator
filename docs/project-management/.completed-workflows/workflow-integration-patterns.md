# Workflow Integration Patterns

## Overview

This document describes the integration patterns between GitHub Actions workflows and the Phoenix Real Estate system's Epic components, with special emphasis on Task 6 LLM processing integration.

## Epic Integration Architecture

### Component Hierarchy

```
GitHub Actions Workflows
    ├── Epic 1: Foundation Infrastructure
    │   ├── ConfigProvider (secrets, environment)
    │   ├── DatabaseClient (MongoDB connections)
    │   └── MetricsCollector (telemetry)
    │
    ├── Epic 2: Data Collection Engine  
    │   ├── CombinedCollector (Maricopa + Phoenix MLS)
    │   ├── CollectionMetrics (success rates)
    │   └── ProxyManager (WebShare integration)
    │
    ├── Epic 3: Automation & Orchestration
    │   ├── OrchestrationEngine (workflow control)
    │   ├── WorkflowMonitor (execution tracking)
    │   └── ExecutionContext (state management)
    │
    └── Task 6: LLM Processing Pipeline
        ├── ProcessingIntegrator (orchestration)
        ├── OllamaClient (model inference)
        ├── PropertyDataExtractor (parsing)
        └── ProcessingValidator (quality checks)
```

## Integration Patterns

### Pattern 1: Configuration Loading Chain

**Purpose**: Seamlessly integrate GitHub Secrets with Epic 1's ConfigProvider

```python
# Pattern: GitHub Secrets → Environment → ConfigProvider → Components

class GitHubActionsConfig:
    """Bridge between GitHub Actions and Epic 1 configuration."""
    
    def __init__(self):
        self.logger = get_logger("github.actions.config")
        
    def load_from_secrets(self) -> ConfigProvider:
        """Load configuration from GitHub Secrets environment."""
        
        # Step 1: Collect GitHub Secrets
        secrets = {
            # Epic 1 Foundation
            "MONGODB_CONNECTION_STRING": os.getenv("MONGODB_CONNECTION_STRING"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            
            # Epic 2 Collection
            "MARICOPA_API_KEY": os.getenv("MARICOPA_API_KEY"),
            "WEBSHARE_USERNAME": os.getenv("WEBSHARE_USERNAME"),
            "WEBSHARE_PASSWORD": os.getenv("WEBSHARE_PASSWORD"),
            
            # Task 6 LLM Processing
            "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "llama3.2:latest"),
            "PROCESSING_BATCH_SIZE": int(os.getenv("PROCESSING_BATCH_SIZE", "10")),
            "PROCESSING_TIMEOUT": int(os.getenv("PROCESSING_TIMEOUT", "30"))
        }
        
        # Step 2: Validate required configuration
        self._validate_required_secrets(secrets)
        
        # Step 3: Create Epic 1 compatible ConfigProvider
        return ConfigProvider(secrets)
```

### Pattern 2: LLM Service Lifecycle Management

**Purpose**: Manage Ollama service within GitHub Actions constraints

```yaml
# Pattern: Service Startup → Health Check → Model Loading → Ready State

- name: Initialize LLM Service
  run: |
    # Install Ollama (cached in Docker layer)
    if ! command -v ollama &> /dev/null; then
      curl -fsSL https://ollama.ai/install.sh | sh
    fi
    
    # Start service with resource limits
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_NUM_PARALLEL=2 \
    ollama serve &
    
    # Wait for service readiness
    for i in {1..30}; do
      if curl -s http://localhost:11434/api/version; then
        echo "Ollama service ready"
        break
      fi
      sleep 2
    done
    
    # Pull model if not cached
    if ! ollama list | grep -q "llama3.2:latest"; then
      ollama pull llama3.2:latest
    fi
```

### Pattern 3: Orchestration Engine with LLM Integration

**Purpose**: Integrate ProcessingIntegrator into Epic 3's orchestration flow

```python
# Pattern: Collect → Process → Validate → Store

class EnhancedOrchestrationEngine(OrchestrationEngine):
    """Orchestration engine with LLM processing integration."""
    
    def __init__(self, config: ConfigProvider):
        super().__init__(config)
        self.processing_integrator = None
        
    async def initialize(self):
        """Initialize with LLM processing support."""
        await super().initialize()
        
        # Initialize LLM processing pipeline
        self.processing_integrator = ProcessingIntegrator(self.config)
        await self.processing_integrator.__aenter__()
        
    async def run_collection_with_processing(self):
        """Run collection workflow with integrated LLM processing."""
        
        # Step 1: Collect raw data using Epic 2
        raw_properties = await self.combined_collector.collect_all()
        
        # Step 2: Process through LLM pipeline (Task 6)
        processed_results = []
        for batch in self._batch_properties(raw_properties):
            try:
                # Process batch with retry logic
                results = await self._process_batch_with_retry(batch)
                processed_results.extend(results)
                
                # Update metrics
                await self.metrics.record_processing_batch(
                    batch_size=len(batch),
                    success_count=len(results),
                    avg_confidence=self._calculate_avg_confidence(results)
                )
                
            except Exception as e:
                # Fallback: Store raw data
                await self._store_raw_fallback(batch)
                self.logger.error(f"LLM processing failed: {e}")
        
        # Step 3: Validate and store results
        validation_stats = await self._validate_results(processed_results)
        await self.repository.store_processed_batch(processed_results)
        
        return {
            "collected": len(raw_properties),
            "processed": len(processed_results),
            "validation": validation_stats
        }
```

### Pattern 4: Error Handling and Recovery

**Purpose**: Graceful degradation when LLM processing fails

```python
# Pattern: Try LLM → Catch Failure → Fallback → Log → Continue

class LLMFailureHandler:
    """Handles LLM processing failures with fallback strategies."""
    
    def __init__(self, config: ConfigProvider):
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=300  # 5 minutes
        )
        
    async def process_with_fallback(self, properties: List[Dict]) -> Dict:
        """Process properties with automatic fallback."""
        
        # Check circuit breaker state
        if self.circuit_breaker.is_open():
            return await self._fallback_processing(properties)
        
        try:
            # Attempt LLM processing
            async with ProcessingIntegrator(self.config) as integrator:
                results = await integrator.process_maricopa_batch(properties)
                
                # Reset circuit breaker on success
                self.circuit_breaker.record_success()
                
                return {
                    "status": "success",
                    "results": results,
                    "fallback_used": False
                }
                
        except (OllamaClientError, TimeoutError) as e:
            # Record failure
            self.circuit_breaker.record_failure()
            
            # Log with context
            logger.error(
                "LLM processing failed",
                extra={
                    "error": str(e),
                    "properties_count": len(properties),
                    "circuit_state": self.circuit_breaker.state
                }
            )
            
            # Execute fallback
            return await self._fallback_processing(properties)
    
    async def _fallback_processing(self, properties: List[Dict]) -> Dict:
        """Fallback to storing raw data."""
        # Store raw HTML for later processing
        stored_count = 0
        for prop in properties:
            await self.repository.store_raw_property(prop)
            stored_count += 1
            
        return {
            "status": "fallback",
            "stored_raw": stored_count,
            "fallback_used": True,
            "reason": "LLM service unavailable"
        }
```

### Pattern 5: Monitoring and Metrics Collection

**Purpose**: Comprehensive metrics across all integrated components

```python
# Pattern: Collect Metrics → Aggregate → Report → Alert

class IntegratedMetricsCollector:
    """Unified metrics collection for workflows."""
    
    def __init__(self, config: ConfigProvider):
        self.epic1_metrics = MetricsCollector(config)  # Foundation
        self.collection_metrics = CollectionMetrics()   # Epic 2
        self.workflow_metrics = WorkflowMonitor()       # Epic 3
        self.llm_metrics = LLMMetricsCollector()       # Task 6
        
    async def collect_workflow_metrics(self, workflow_result: Dict) -> Dict:
        """Aggregate metrics from all components."""
        
        metrics = {
            # Workflow execution metrics
            "workflow": {
                "execution_time": workflow_result["duration"],
                "github_actions_minutes": self._calculate_actions_minutes(),
                "status": workflow_result["status"]
            },
            
            # Epic 2: Collection metrics
            "collection": {
                "total_attempted": self.collection_metrics.total_attempts,
                "success_rate": self.collection_metrics.success_rate,
                "api_calls": self.collection_metrics.api_calls,
                "proxy_rotations": self.collection_metrics.proxy_rotations
            },
            
            # Task 6: LLM processing metrics
            "llm_processing": {
                "total_processed": self.llm_metrics.total_processed,
                "average_latency": self.llm_metrics.avg_processing_time,
                "confidence_score": self.llm_metrics.avg_confidence,
                "cache_hit_rate": self.llm_metrics.cache_hit_rate,
                "model_load_time": self.llm_metrics.model_load_time
            },
            
            # Resource usage
            "resources": {
                "memory_peak_mb": self._get_memory_peak(),
                "cpu_usage_avg": self._get_cpu_average(),
                "disk_io_mb": self._get_disk_io()
            }
        }
        
        # Send to monitoring systems
        await self._send_to_prometheus(metrics)
        await self._update_github_summary(metrics)
        
        return metrics
```

## TDD Testing Patterns

### Pattern 6: Mocking LLM Services

**Purpose**: Enable unit testing without actual LLM service

```python
# Pattern: Mock Service → Inject → Test → Verify

class MockOllamaClient:
    """Mock Ollama client for testing."""
    
    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or self._default_responses()
        self.call_history = []
        
    async def generate(self, prompt: str, model: str) -> Dict:
        """Mock LLM generation."""
        self.call_history.append({
            "prompt": prompt,
            "model": model,
            "timestamp": datetime.now(UTC)
        })
        
        # Return canned response based on prompt patterns
        if "property details" in prompt.lower():
            return self.responses["property_extraction"]
        
        return self.responses["default"]
    
    def _default_responses(self) -> Dict:
        """Default mock responses."""
        return {
            "property_extraction": {
                "response": json.dumps({
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "square_feet": 1500,
                    "confidence_score": 0.95
                })
            },
            "default": {
                "response": "{}"
            }
        }

# Usage in tests
@pytest.fixture
def mock_ollama():
    """Fixture for mocked Ollama client."""
    return MockOllamaClient()

async def test_workflow_with_mocked_llm(mock_ollama):
    """Test workflow with mocked LLM processing."""
    with patch('phoenix_real_estate.collectors.processing.ollama_client.OllamaClient', return_value=mock_ollama):
        workflow = GitHubActionsDailyCollection()
        result = await workflow.run()
        
        # Verify LLM was called
        assert len(mock_ollama.call_history) > 0
        assert result["llm_processing"]["success"] is True
```

## Best Practices

### 1. Configuration Management
- Use GitHub Secrets for all sensitive data
- Validate configuration on workflow startup
- Provide sensible defaults for optional settings
- Log configuration state (without secrets) for debugging

### 2. Service Management
- Always check service health before use
- Implement graceful startup with retries
- Use circuit breakers for external services
- Clean up resources in finally blocks

### 3. Error Handling
- Implement multiple fallback strategies
- Log errors with full context
- Create GitHub Issues for critical failures
- Continue processing remaining items on partial failures

### 4. Performance Optimization
- Cache LLM model between runs
- Batch process properties for efficiency
- Use parallel processing where safe
- Monitor and alert on performance degradation

### 5. Testing Strategy
- Mock all external services in unit tests
- Use fixtures for complex test data
- Test error scenarios thoroughly
- Validate metrics collection accuracy

## Integration Checklist

### Pre-Deployment
- [ ] All Epic components integrated successfully
- [ ] LLM service startup tested in CI environment
- [ ] Error handling paths validated
- [ ] Metrics collection verified
- [ ] Resource limits confirmed within budget

### Deployment
- [ ] GitHub Secrets configured correctly
- [ ] Workflows syntactically valid
- [ ] Service health checks passing
- [ ] First run monitored closely
- [ ] Alerts configured and tested

### Post-Deployment
- [ ] Daily collection success rate > 95%
- [ ] LLM processing confidence > 90%
- [ ] Resource usage within limits
- [ ] No critical errors in logs
- [ ] Metrics dashboard operational

## Troubleshooting Guide

### Common Issues

1. **Ollama Service Won't Start**
   - Check available memory (need 3GB+)
   - Verify no port conflicts on 11434
   - Check Docker daemon is running
   - Review service logs for errors

2. **LLM Processing Timeouts**
   - Increase PROCESSING_TIMEOUT setting
   - Check model is fully downloaded
   - Verify CPU resources available
   - Consider smaller batch sizes

3. **Configuration Loading Failures**
   - Verify all required secrets set
   - Check secret names match exactly
   - Validate JSON/YAML syntax
   - Review workflow logs for details

4. **Integration Test Failures**
   - Ensure all mocks properly configured
   - Check Epic component versions
   - Verify test database clean
   - Review async context management

## Next Steps

1. Implement production monitoring dashboards
2. Create automated performance regression tests
3. Document runbook for common operations
4. Plan for multi-model support
5. Design A/B testing framework for model comparison