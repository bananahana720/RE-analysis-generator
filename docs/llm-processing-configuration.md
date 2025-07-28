# LLM Processing Configuration Guide

## Overview

This guide covers all configuration options for the LLM Processing system in the Phoenix Real Estate Data Collector. The system uses a hierarchical configuration approach with environment variables, YAML files, and programmatic overrides.

## Table of Contents
1. [Configuration Hierarchy](#configuration-hierarchy)
2. [Core LLM Settings](#core-llm-settings)
3. [Processing Pipeline Configuration](#processing-pipeline-configuration)
4. [Validation Configuration](#validation-configuration)
5. [Caching Configuration](#caching-configuration)
6. [Performance Settings](#performance-settings)
7. [Resource Limits](#resource-limits)
8. [Integration Settings](#integration-settings)
9. [Advanced Configuration](#advanced-configuration)
10. [Configuration Examples](#configuration-examples)

## Configuration Hierarchy

The configuration system follows this precedence order (highest to lowest):

1. **Programmatic overrides** - Set directly in code
2. **Environment variables** - From `.env` file or system
3. **YAML configuration files** - From `config/` directory
4. **Default values** - Built-in defaults

### Loading Configuration

```python
from phoenix_real_estate.foundation import ConfigProvider

# Standard loading
config = ConfigProvider()

# With custom config directory
config = ConfigProvider(config_dir="./custom/config")

# With environment override
config = ConfigProvider(env="production")
```

## Core LLM Settings

These settings control the Ollama LLM client behavior.

### Environment Variables (.env)

```env
# Ollama Service Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:latest
LLM_TIMEOUT=30
LLM_MAX_RETRIES=2

# Model Parameters
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9
LLM_TOP_K=40
LLM_NUM_PREDICT=2048
LLM_SEED=42

# Request Configuration
LLM_STREAM=false
LLM_FORMAT=json
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `OLLAMA_BASE_URL` | string | `http://localhost:11434` | Ollama service endpoint |
| `LLM_MODEL` | string | `llama3.2:latest` | Model to use for extraction |
| `LLM_TIMEOUT` | int | 30 | Request timeout in seconds |
| `LLM_MAX_RETRIES` | int | 2 | Maximum retry attempts |
| `LLM_TEMPERATURE` | float | 0.3 | Model temperature (0-1) |
| `LLM_TOP_P` | float | 0.9 | Nucleus sampling parameter |
| `LLM_TOP_K` | int | 40 | Top-k sampling parameter |
| `LLM_NUM_PREDICT` | int | 2048 | Maximum tokens to generate |
| `LLM_SEED` | int | 42 | Random seed for reproducibility |
| `LLM_STREAM` | bool | false | Enable streaming responses |
| `LLM_FORMAT` | string | json | Response format |

### Programmatic Configuration

```python
# Override settings in code
config.settings.LLM_MODEL = "llama3.2:latest"
config.settings.LLM_TEMPERATURE = 0.1  # Lower for more consistent output
config.settings.LLM_MAX_RETRIES = 3
```

## Processing Pipeline Configuration

Configure the data processing pipeline behavior.

### Pipeline Settings (config/processing.yaml)

```yaml
processing:
  # Extraction settings
  extraction:
    max_content_length: 50000  # Maximum HTML content size
    chunk_size: 4096          # Size for content chunking
    overlap_size: 256         # Overlap between chunks
    
  # Retry configuration
  retry:
    max_attempts: 3
    initial_delay: 1.0        # seconds
    exponential_base: 2.0
    max_delay: 30.0
    
  # Timeout settings
  timeouts:
    extraction: 30            # seconds
    validation: 5
    total_pipeline: 60
    
  # Batch processing
  batch:
    default_size: 50
    max_concurrent: 10
    queue_size: 1000
```

### Environment Variable Overrides

```env
# Pipeline settings
PROCESSING_MAX_CONTENT_LENGTH=50000
PROCESSING_CHUNK_SIZE=4096
PROCESSING_MAX_CONCURRENT=10
PROCESSING_BATCH_SIZE=50
```

### Using Pipeline Configuration

```python
from phoenix_real_estate.collectors.processing import DataProcessingPipeline

# Load with custom settings
pipeline = DataProcessingPipeline(config)

# Override batch settings
results = await pipeline.process_batch(
    items,
    max_concurrency=20,  # Override default
    batch_size=100       # Override default
)
```

## Validation Configuration

Configure data validation rules and behavior.

### Validation Rules (config/validation.yaml)

```yaml
validation:
  # Global settings
  strict_mode: false          # Fail on warnings
  required_fields:
    - address
    - city
    - state
    - zip_code
    
  # Field-specific rules
  fields:
    price:
      min: 10000
      max: 10000000
      required: true
      
    bedrooms:
      min: 0
      max: 20
      type: integer
      
    bathrooms:
      min: 0
      max: 10
      type: float
      allow_half: true
      
    square_feet:
      min: 100
      max: 50000
      type: integer
      
    year_built:
      min: 1800
      max: 2024
      type: integer
      
    zip_code:
      pattern: "^85\\d{3}$"   # Phoenix area zips
      
  # Source-specific rules
  sources:
    phoenix_mls:
      required_fields:
        - mls_number
        - listing_date
        - status
        
    maricopa_api:
      required_fields:
        - apn
        - assessed_value
```

### Custom Validation Rules

```python
from phoenix_real_estate.collectors.processing import ValidationRule, ProcessingValidator

# Create custom validator
validator = ProcessingValidator(config)

# Add custom rule
phoenix_zip_rule = ValidationRule(
    name="phoenix_zip",
    description="Validate Phoenix area ZIP codes",
    validate=lambda prop: prop.zip_code in ["85031", "85033", "85035"],
    error_message="Property must be in target ZIP codes"
)

validator.add_rule(phoenix_zip_rule)

# Source-specific rule
mls_rule = ValidationRule(
    name="mls_format",
    description="Validate MLS number format",
    validate=lambda prop: bool(re.match(r"^\d{6,8}$", prop.mls_number or "")),
    error_message="Invalid MLS number format",
    applies_to_sources=["phoenix_mls"]
)

validator.add_rule(mls_rule)
```

## Caching Configuration

Configure caching to improve performance and reduce LLM calls.

### Cache Settings (config/cache.yaml)

```yaml
cache:
  # Memory cache
  memory:
    enabled: true
    max_size: 1000            # Maximum entries
    ttl_seconds: 3600         # 1 hour
    
  # Disk cache
  disk:
    enabled: true
    directory: "./cache/llm"
    max_size_mb: 1024         # 1GB
    ttl_seconds: 86400        # 24 hours
    compression: true
    
  # Redis cache (optional)
  redis:
    enabled: false
    host: localhost
    port: 6379
    db: 0
    key_prefix: "llm_cache:"
    ttl_seconds: 3600
    
  # Cache key generation
  key_generation:
    include_model: true       # Include model name in key
    include_source: true      # Include data source
    hash_algorithm: "sha256"
```

### Environment Variables

```env
# Cache settings
CACHE_ENABLED=true
CACHE_MEMORY_SIZE=1000
CACHE_DISK_ENABLED=true
CACHE_DISK_PATH=./cache/llm
CACHE_TTL_SECONDS=3600
```

### Programmatic Cache Configuration

```python
from phoenix_real_estate.collectors.processing import CacheManager, CacheConfig

# Custom cache configuration
cache_config = CacheConfig(
    max_size=5000,
    ttl_seconds=7200,
    enable_memory_cache=True,
    enable_disk_cache=True,
    cache_dir="./data/cache",
    compression_enabled=True
)

# Create cache manager
cache_manager = CacheManager(cache_config)

# Attach to pipeline
pipeline.set_cache_manager(cache_manager)

# Clear cache programmatically
await cache_manager.clear()

# Get cache statistics
stats = cache_manager.get_stats()
print(f"Hit rate: {stats.hit_rate:.2%}")
```

## Performance Settings

Optimize processing performance with these settings.

### Performance Configuration (config/performance.yaml)

```yaml
performance:
  # Batch optimization
  batch_optimization:
    enabled: true
    target_latency: 1.0       # seconds per item
    min_batch_size: 10
    max_batch_size: 200
    adjustment_factor: 0.2
    
  # Concurrency settings
  concurrency:
    max_workers: 10
    queue_size: 1000
    semaphore_limit: 20
    
  # Request pooling
  connection_pool:
    size: 20
    timeout: 30
    max_keepalive: 300
    
  # Circuit breaker
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    recovery_timeout: 60
    half_open_requests: 3
```

### Performance Tuning

```python
from phoenix_real_estate.collectors.processing import PerformanceOptimizer

# Create optimizer
optimizer = PerformanceOptimizer(config)

# Find optimal settings
optimal_config = await optimizer.optimize(
    sample_data=test_properties,
    target_throughput=100,  # items per second
    max_latency=2.0        # seconds
)

# Apply optimizations
config.update(optimal_config)
```

## Resource Limits

Control resource usage to prevent system overload.

### Resource Configuration (config/resources.yaml)

```yaml
resources:
  # CPU limits
  cpu:
    max_percent: 80
    warning_percent: 70
    
  # Memory limits
  memory:
    max_mb: 4096              # 4GB
    warning_mb: 3072          # 3GB
    
  # Request limits
  requests:
    max_concurrent: 20
    max_queue_size: 1000
    timeout_seconds: 60
    
  # Rate limiting
  rate_limits:
    requests_per_second: 10
    burst_size: 20
    
  # Monitoring
  monitoring:
    enabled: true
    interval_seconds: 5
    alert_enabled: true
```

### Resource Monitoring

```python
from phoenix_real_estate.collectors.processing import ResourceMonitor, ResourceLimits

# Configure limits
limits = ResourceLimits(
    max_cpu_percent=80,
    max_memory_mb=4096,
    max_concurrent_requests=20
)

# Create monitor
monitor = ResourceMonitor(limits=limits)

# Set up alerts
monitor.set_alert_callback(lambda alert: 
    logger.warning(f"Resource alert: {alert.message}")
)

# Start monitoring
await monitor.start()

# Get current metrics
metrics = await monitor.get_metrics()
print(f"CPU: {metrics.cpu_percent}%")
print(f"Memory: {metrics.memory_mb}MB")
```

## Integration Settings

Configure integration with data collectors and storage.

### Integration Configuration (config/integration.yaml)

```yaml
integration:
  # Collector settings
  collectors:
    maricopa:
      batch_size: 100
      concurrent_requests: 5
      retry_attempts: 3
      
    phoenix_mls:
      batch_size: 50
      concurrent_requests: 3
      use_proxy: true
      
  # Storage settings
  storage:
    mongodb:
      batch_insert: true
      batch_size: 100
      write_concern: 1
      
  # Dead letter queue
  dlq:
    enabled: true
    max_retries: 3
    retry_delay: 300          # 5 minutes
    storage: "mongodb"
    collection: "processing_dlq"
```

### Integration Usage

```python
from phoenix_real_estate.orchestration import ProcessingIntegrator

# Create integrator with custom settings
integrator = ProcessingIntegrator(config)

# Process with collector-specific settings
async for result in integrator.process_from_collector(
    "maricopa",
    limit=1000,
    batch_size=200  # Override default
):
    # Handle results
    pass
```

## Advanced Configuration

### Custom Prompt Templates

```yaml
prompts:
  extraction:
    system: |
      You are a real estate data extraction specialist.
      Extract property information accurately and completely.
      
    template: |
      Extract the following property details from the content:
      {fields}
      
      Return as JSON with these exact field names.
      
    fields:
      - address
      - price
      - bedrooms
      - bathrooms
      - square_feet
      
  validation:
    template: |
      Validate the extracted data for completeness and accuracy.
```

### Feature Flags

```yaml
features:
  # Experimental features
  experimental:
    adaptive_prompts: false
    multi_model_ensemble: false
    
  # Processing features
  processing:
    chunk_processing: true
    parallel_validation: true
    smart_retries: true
    
  # Monitoring features
  monitoring:
    detailed_metrics: true
    performance_tracking: true
    error_analysis: true
```

### Logging Configuration

```yaml
logging:
  # Log levels by module
  levels:
    phoenix_real_estate.collectors.processing: DEBUG
    phoenix_real_estate.orchestration: INFO
    ollama_client: DEBUG
    
  # Structured logging
  structured:
    enabled: true
    format: json
    include_context: true
    
  # Log outputs
  outputs:
    - type: console
      level: INFO
      
    - type: file
      level: DEBUG
      path: ./logs/llm_processing.log
      rotation: daily
      retention_days: 7
```

## Configuration Examples

### High-Performance Configuration

```python
# config/environments/production.yaml
production:
  llm:
    model: "llama3.2:latest"
    temperature: 0.1
    max_retries: 3
    timeout: 45
    
  processing:
    batch_size: 100
    max_concurrent: 20
    
  cache:
    memory_size: 5000
    disk_enabled: true
    ttl_seconds: 7200
    
  resources:
    max_cpu_percent: 90
    max_memory_mb: 8192
```

### Development Configuration

```python
# config/environments/development.yaml
development:
  llm:
    model: "llama3.2:latest"
    temperature: 0.3
    max_retries: 1
    timeout: 60
    
  processing:
    batch_size: 10
    max_concurrent: 2
    
  validation:
    strict_mode: false
    
  logging:
    level: DEBUG
    structured: false
```

### Minimal Configuration

```env
# .env - Minimal setup
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:latest
```

### Loading Environment-Specific Config

```python
import os
from phoenix_real_estate.foundation import ConfigProvider

# Load based on environment
env = os.getenv("ENVIRONMENT", "development")
config = ConfigProvider(env=env)

# Or explicitly
config_prod = ConfigProvider(env="production")
config_dev = ConfigProvider(env="development")
```

## Best Practices

1. **Start with defaults** - The system has sensible defaults for most use cases
2. **Use environment variables** - For sensitive data and deployment-specific settings
3. **Version control YAML files** - Except for sensitive configurations
4. **Monitor and adjust** - Use metrics to tune performance settings
5. **Document changes** - Keep track of configuration modifications

## Troubleshooting Configuration Issues

### Common Problems

1. **Configuration not loading**
   ```python
   # Check config path
   print(config.config_dir)
   
   # Verify settings
   print(config.settings.LLM_MODEL)
   ```

2. **Environment variables not working**
   ```bash
   # Check .env file location
   # Must be in project root
   
   # Verify loading
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('LLM_MODEL'))"
   ```

3. **Performance issues**
   ```python
   # Enable performance monitoring
   config.settings.PERFORMANCE_TRACKING = True
   
   # Check resource usage
   monitor = ResourceMonitor()
   metrics = await monitor.get_metrics()
   ```

For more details, see the [Troubleshooting Guide](./llm-processing-troubleshooting.md).