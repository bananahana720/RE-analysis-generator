# LLM Processing User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Basic Usage](#basic-usage)
6. [Advanced Features](#advanced-features)
7. [Integration with Collectors](#integration-with-collectors)
8. [Performance Optimization](#performance-optimization)
9. [Monitoring and Debugging](#monitoring-and-debugging)
10. [Best Practices](#best-practices)

## Introduction

The LLM Processing system is a core component of the Phoenix Real Estate Data Collector that uses AI to extract structured property information from unstructured HTML and text data. It leverages Ollama with the llama3.2:latest model to provide accurate, validated property data extraction.

### Key Features
- **AI-Powered Extraction**: Uses LLM to understand and extract property details
- **Multi-Source Support**: Works with Maricopa API and Phoenix MLS data
- **Validation Framework**: Ensures data quality with configurable rules
- **Performance Optimization**: Includes caching, batching, and resource monitoring
- **Error Resilience**: Built-in retry logic and fallback mechanisms

## Prerequisites

Before using the LLM Processing system, ensure you have:

1. **Python 3.13.4** installed
2. **Ollama** installed and running
3. **MongoDB** v8.1.2 running locally
4. **Project dependencies** installed via `uv`

### Installing Ollama

1. Download Ollama from [ollama.ai](https://ollama.ai)
2. Install Ollama following the platform-specific instructions
3. Start the Ollama service:
   ```bash
   ollama serve
   ```
4. Pull the required model (2GB download):
   ```bash
   ollama pull llama3.2:latest
   ```

### Verifying Installation

Check that everything is properly installed:

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check MongoDB is running (Windows)
net start MongoDB

# Check Python and uv
python --version  # Should show 3.13.4
uv --version
```

## Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd RE-analysis-generator
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment variables**:
   Create a `.env` file with required settings:
   ```env
   # API Keys
   MARICOPA_API_KEY=your_key_here
   WEBSHARE_API_KEY=your_key_here
   CAPTCHA_API_KEY=your_key_here
   
   # LLM Settings (optional, defaults shown)
   OLLAMA_BASE_URL=http://localhost:11434
   LLM_MODEL=llama3.2:latest
   LLM_TIMEOUT=30
   LLM_MAX_RETRIES=2
   ```

4. **Verify installation**:
   ```bash
   python scripts/testing/test_property_extractor.py
   ```

## Quick Start

Here's a simple example to get started with LLM processing:

```python
import asyncio
from phoenix_real_estate.foundation import ConfigProvider
from phoenix_real_estate.orchestration import ProcessingIntegrator

async def quick_start():
    """Quick start example for LLM processing."""
    # Initialize configuration
    config = ConfigProvider()
    
    # Create processing integrator
    async with ProcessingIntegrator(config) as integrator:
        # Example HTML content
        html_content = """
        <div class="property-details">
            <h1>123 Main St, Phoenix, AZ 85031</h1>
            <span class="price">$350,000</span>
            <div class="features">
                3 bedrooms, 2 bathrooms, 1,500 sq ft
            </div>
        </div>
        """
        
        # Process the property
        result = await integrator.process_property(
            {"html": html_content},
            source="phoenix_mls"
        )
        
        if result.success:
            print(f"Successfully extracted property:")
            print(f"  Address: {result.property_data.address}")
            print(f"  Price: ${result.property_data.price:,.2f}")
            print(f"  Bedrooms: {result.property_data.bedrooms}")
            print(f"  Bathrooms: {result.property_data.bathrooms}")
        else:
            print(f"Extraction failed: {result.error}")

# Run the example
asyncio.run(quick_start())
```

## Basic Usage

### 1. Processing Individual Properties

```python
from phoenix_real_estate.collectors.processing import DataProcessingPipeline
from phoenix_real_estate.foundation import ConfigProvider

async def process_single_property():
    config = ConfigProvider()
    
    async with DataProcessingPipeline(config) as pipeline:
        # Process HTML content
        result = await pipeline.process_property(
            html_content,
            source="phoenix_mls"
        )
        
        if result.is_valid:
            property_data = result.property_data
            print(f"Property: {property_data.address}")
            print(f"Price: ${property_data.price:,.2f}")
            print(f"Type: {property_data.property_type}")
```

### 2. Batch Processing

Process multiple properties efficiently:

```python
async def process_multiple_properties():
    config = ConfigProvider()
    
    async with DataProcessingPipeline(config) as pipeline:
        # List of properties to process
        properties = [
            {"html": html1, "id": "prop1"},
            {"html": html2, "id": "prop2"},
            {"html": html3, "id": "prop3"},
        ]
        
        # Process in batch
        results = await pipeline.process_batch(
            properties,
            source="phoenix_mls",
            max_concurrency=5
        )
        
        # Check results
        for result in results:
            if result.is_valid:
                print(f"✓ Processed: {result.metadata.get('id')}")
            else:
                print(f"✗ Failed: {result.error}")
```

### 3. Using the Extractor Directly

For more control over the extraction process:

```python
from phoenix_real_estate.collectors.processing import PropertyDataExtractor

async def direct_extraction():
    config = ConfigProvider()
    extractor = PropertyDataExtractor(config)
    
    # Extract from HTML
    property_details = await extractor.extract(
        html_content,
        source="phoenix_mls"
    )
    
    # Extract specific field
    price = await extractor.extract_field(
        html_content,
        "price"
    )
    
    print(f"Extracted price: ${price}")
```

## Advanced Features

### 1. Custom Validation Rules

Create custom validation rules for your specific needs:

```python
from phoenix_real_estate.collectors.processing import ValidationRule, ProcessingValidator

# Define custom rule
price_range_rule = ValidationRule(
    name="price_range",
    description="Validate price is within expected range",
    validate=lambda prop: 50000 <= prop.price <= 2000000 if prop.price else False,
    error_message="Price must be between $50,000 and $2,000,000"
)

# Add to validator
validator = ProcessingValidator(config)
validator.add_rule(price_range_rule)
```

### 2. Caching for Performance

Enable caching to avoid redundant LLM calls:

```python
from phoenix_real_estate.collectors.processing import CacheManager, CacheConfig

# Configure cache
cache_config = CacheConfig(
    max_size=1000,
    ttl_seconds=3600,  # 1 hour
    enable_memory_cache=True,
    enable_disk_cache=True,
    cache_dir="./cache/llm"
)

# Create cache manager
cache_manager = CacheManager(cache_config)

# Attach to pipeline
pipeline.set_cache_manager(cache_manager)

# Cache statistics
stats = cache_manager.get_stats()
print(f"Cache hit rate: {stats.hit_rate:.2%}")
```

### 3. Custom Prompts

Customize extraction prompts for specific use cases:

```python
# Set custom prompt template
extractor.prompt_template = """
Extract the following property information:
- Full address (street, city, state, zip)
- Listing price in dollars
- Number of bedrooms and bathrooms
- Square footage
- Property type (house, condo, etc.)
- Year built
- Any special features mentioned

Focus on accuracy and only extract what is clearly stated.

Content to analyze:
{content}
"""
```

### 4. Fallback Extraction

Implement fallback strategies for failed extractions:

```python
async def extract_with_fallback(html_content):
    try:
        # Try LLM extraction first
        result = await pipeline.process_property(html_content)
        if result.is_valid:
            return result.property_data
    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
    
    # Fallback to regex-based extraction
    from phoenix_real_estate.utils.extractors import RegexExtractor
    fallback = RegexExtractor()
    return fallback.extract(html_content)
```

## Integration with Collectors

### Processing Maricopa API Data

```python
async def process_maricopa_data():
    config = ConfigProvider()
    
    async with ProcessingIntegrator(config) as integrator:
        # Process directly from Maricopa collector
        async for result in integrator.process_from_collector(
            "maricopa",
            limit=100
        ):
            if result.success:
                print(f"Processed APN: {result.property_id}")
                # Property is automatically saved to MongoDB
```

### Processing Phoenix MLS Data

```python
async def process_phoenix_mls_data():
    config = ConfigProvider()
    
    async with ProcessingIntegrator(config) as integrator:
        # Process from Phoenix MLS scraper
        async for result in integrator.process_from_collector(
            "phoenix_mls",
            limit=50
        ):
            if result.success:
                prop = result.property_data
                print(f"MLS #{prop.mls_number}: {prop.address}")
```

### Custom Integration

```python
async def custom_integration():
    from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector
    
    config = ConfigProvider()
    collector = MaricopaAPICollector(config)
    pipeline = DataProcessingPipeline(config)
    
    async with collector, pipeline:
        # Fetch raw data
        raw_data = await collector.fetch_property("123-45-678")
        
        # Process with LLM
        result = await pipeline.process_property(
            raw_data,
            source="maricopa_api"
        )
        
        if result.is_valid:
            # Custom handling
            await save_to_custom_db(result.property_data)
```

## Performance Optimization

### 1. Optimal Batch Sizes

```python
from phoenix_real_estate.collectors.processing import BatchSizeOptimizer

optimizer = BatchSizeOptimizer()
optimal_size = await optimizer.find_optimal_size(
    sample_data,
    target_latency=1.0  # 1 second per item
)
print(f"Optimal batch size: {optimal_size}")
```

### 2. Resource Monitoring

```python
from phoenix_real_estate.collectors.processing import ResourceMonitor, ResourceLimits

# Set resource limits
limits = ResourceLimits(
    max_cpu_percent=80,
    max_memory_mb=4096,
    max_concurrent_requests=10
)

monitor = ResourceMonitor(limits=limits)
await monitor.start()

# Monitor during processing
async with monitor.track():
    results = await pipeline.process_batch(items)

# Get metrics
metrics = await monitor.get_metrics()
print(f"Peak CPU: {metrics.peak_cpu_percent}%")
print(f"Peak Memory: {metrics.peak_memory_mb}MB")
```

### 3. Concurrent Processing

```python
async def concurrent_processing():
    config = ConfigProvider()
    
    # Configure concurrency
    config.settings.LLM_MAX_CONCURRENT = 10
    config.settings.LLM_QUEUE_SIZE = 100
    
    async with DataProcessingPipeline(config) as pipeline:
        # Process with high concurrency
        results = await pipeline.process_batch(
            large_dataset,
            max_concurrency=10,
            batch_size=50
        )
```

## Monitoring and Debugging

### 1. Enable Debug Logging

```python
import logging
from phoenix_real_estate.foundation.logging import get_logger

# Set debug level
logging.getLogger("phoenix_real_estate.collectors.processing").setLevel(logging.DEBUG)

# Or use environment variable
# export LOG_LEVEL=DEBUG
```

### 2. Processing Metrics

```python
async def monitor_processing():
    async with ProcessingIntegrator(config) as integrator:
        # Process properties
        await integrator.process_from_collector("maricopa", limit=100)
        
        # Get detailed statistics
        stats = await integrator.get_statistics()
        
        print("Processing Statistics:")
        print(f"  Total Processed: {stats['total_processed']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Success Rate: {stats['success_rate']:.1%}")
        print(f"  Avg Processing Time: {stats['avg_processing_time']:.2f}s")
        print(f"  Cache Hit Rate: {stats['cache_hit_rate']:.1%}")
```

### 3. Error Analysis

```python
# Enable detailed error tracking
pipeline.enable_error_tracking = True

# Process properties
results = await pipeline.process_batch(items)

# Analyze errors
error_summary = pipeline.get_error_summary()
for error_type, count in error_summary.items():
    print(f"{error_type}: {count} occurrences")
```

### 4. Performance Profiling

```python
from phoenix_real_estate.collectors.processing import PerformanceBenchmark

benchmark = PerformanceBenchmark()

# Run benchmark
result = await benchmark.run(
    pipeline=pipeline,
    test_data=sample_properties,
    iterations=10
)

print(f"Throughput: {result.throughput:.2f} items/second")
print(f"P95 Latency: {result.p95_latency:.2f}s")
```

## Best Practices

### 1. Always Use Context Managers

```python
# Good - ensures proper cleanup
async with ProcessingIntegrator(config) as integrator:
    result = await integrator.process_property(data)

# Avoid - may leak resources
integrator = ProcessingIntegrator(config)
result = await integrator.process_property(data)
```

### 2. Handle Errors Gracefully

```python
async def safe_processing(data):
    try:
        result = await pipeline.process_property(data)
        if not result.is_valid:
            logger.warning(f"Validation failed: {result.validation_result.errors}")
            # Handle invalid data
        return result
    except ProcessingError as e:
        logger.error(f"Processing error: {e}")
        # Implement fallback
    except Exception as e:
        logger.exception("Unexpected error")
        # Alert monitoring
```

### 3. Monitor Resource Usage

```python
# Set up alerts for high resource usage
monitor.set_alert_callback(lambda alert: 
    logger.warning(f"Resource alert: {alert.message}")
)
```

### 4. Optimize for Your Use Case

```python
# For high-volume processing
config.settings.LLM_BATCH_SIZE = 100
config.settings.LLM_MAX_CONCURRENT = 20
config.settings.CACHE_SIZE = 10000

# For accuracy-focused processing
config.settings.LLM_MAX_RETRIES = 3
config.settings.VALIDATION_STRICT = True
config.settings.LLM_TEMPERATURE = 0.1
```

### 5. Regular Maintenance

```python
# Clear old cache entries
await cache_manager.cleanup()

# Reset statistics
await integrator.reset_statistics()

# Update model periodically
# ollama pull llama3.2:latest
```

## Troubleshooting

### Common Issues

1. **Ollama service not found**
   - Ensure Ollama is running: `ollama serve`
   - Check the URL in `.env`: `OLLAMA_BASE_URL=http://localhost:11434`

2. **Model not found**
   - Pull the model: `ollama pull llama3.2:latest`
   - Verify model name in config

3. **Slow processing**
   - Enable caching
   - Increase concurrency
   - Check resource limits

4. **High error rate**
   - Review validation rules
   - Check input data quality
   - Enable debug logging

For more troubleshooting tips, see the [Troubleshooting Guide](./llm-processing-troubleshooting.md).