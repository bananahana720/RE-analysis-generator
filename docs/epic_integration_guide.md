# Epic 1 and Epic 2 Integration Guide

## Overview

The `ProcessingIntegrator` class serves as the bridge between Epic 1 data collectors (Maricopa API, Phoenix MLS) and the Epic 2 LLM processing pipeline. This integration enables seamless data flow from collection through processing to database storage.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data Collectors│     │  Processing      │     │   Database      │
│  (Epic 1)       │────▶│  Integrator      │────▶│  (Epic 1)       │
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│ - Maricopa API  │     │ - Orchestration  │     │ - Property      │
│ - Phoenix MLS   │     │ - LLM Pipeline   │     │   Repository    │
│                 │     │ - Validation     │     │ - MongoDB       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Key Components

### ProcessingIntegrator

The main integration class that:
- Manages data flow between collectors and processing pipeline
- Handles both batch and streaming modes
- Provides metrics and monitoring
- Ensures data validation and quality

### Integration Modes

1. **Individual Mode**: Process single properties
2. **Batch Mode**: Process multiple properties efficiently
3. **Streaming Mode**: Process properties as they arrive

### Data Flow

1. **Collection**: Raw data from Maricopa API (JSON) or Phoenix MLS (HTML)
2. **Processing**: LLM extraction and validation through the pipeline
3. **Validation**: Quality checks and data validation
4. **Storage**: Save validated data to MongoDB

## Usage Examples

### Individual Property Processing

```python
from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository
from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector
from phoenix_real_estate.orchestration import ProcessingIntegrator

async def process_single_property():
    # Initialize components
    config = ConfigProvider()
    repository = PropertyRepository(config)
    
    # Create integrator
    async with ProcessingIntegrator(config, repository) as integrator:
        # Create collector
        collector = MaricopaAPICollector(config, repository)
        
        # Process single property
        result = await integrator.process_maricopa_property(
            collector,
            property_id="12345"
        )
        
        if result.success:
            print(f"Property {result.property_id} processed successfully")
            print(f"Confidence: {result.property_data.extraction_confidence}")
        else:
            print(f"Failed: {result.error}")
```

### Batch Processing

```python
async def process_batch():
    async with ProcessingIntegrator(config, repository) as integrator:
        collector = MaricopaAPICollector(config, repository)
        
        # Process multiple ZIP codes
        batch_result = await integrator.process_maricopa_batch(
            collector,
            zip_codes=["85031", "85033", "85035"],
            max_properties=100
        )
        
        print(f"Processed: {batch_result.total_processed}")
        print(f"Success rate: {batch_result.successful / batch_result.total_processed:.2%}")
```

### Streaming Mode

```python
async def process_stream():
    async with ProcessingIntegrator(config, repository) as integrator:
        collector = MaricopaAPICollector(config, repository)
        
        # Process properties as they arrive
        async for result in integrator.process_stream(
            collector,
            mode=IntegrationMode.STREAMING
        ):
            print(f"Processed: {result.property_id} - Success: {result.success}")
```

## Configuration

The integrator uses these configuration keys:

```yaml
# config/base.yaml
INTEGRATION_BATCH_SIZE: 10        # Properties per batch
SAVE_INVALID_PROPERTIES: false    # Whether to save invalid properties
STRICT_VALIDATION: true           # Enforce strict validation

# Processing pipeline settings
BATCH_SIZE: 10                    # Pipeline batch size
MAX_CONCURRENT_PROCESSING: 5      # Concurrent processing limit
PROCESSING_TIMEOUT: 60            # Timeout in seconds
ENABLE_METRICS: true              # Enable metrics collection
```

## Metrics and Monitoring

The integrator provides comprehensive metrics:

```python
metrics = integrator.get_metrics()
# Returns:
# {
#     'total_processed': 150,
#     'successful': 142,
#     'failed': 8,
#     'saved_to_db': 142,
#     'success_rate': 0.947,
#     'average_processing_time': 2.34,
#     'sources': {
#         'maricopa_county': 100,
#         'phoenix_mls': 50
#     },
#     'error_count': 8,
#     'recent_errors': [...]
# }
```

## Error Handling

The integrator implements robust error handling:

1. **Collector Errors**: Caught and logged, continue with next property
2. **Processing Errors**: Validation failures tracked, optional invalid data saving
3. **Database Errors**: Retry logic with exponential backoff
4. **Network Errors**: Automatic retry with configured limits

## Best Practices

1. **Use Context Managers**: Always use `async with` for proper resource cleanup
2. **Monitor Metrics**: Check success rates and processing times regularly
3. **Batch Size Tuning**: Adjust batch size based on system resources
4. **Error Recovery**: Implement retry logic for transient failures
5. **Logging**: Monitor logs for processing issues and bottlenecks

## Testing

Run integration tests:

```bash
# Unit tests
uv run pytest tests/integration/test_processing_integrator.py -v

# Example script
python scripts/examples/test_epic_integration.py
```

## Future Enhancements

1. **Caching**: Add caching layer for frequently accessed properties
2. **Priority Queue**: Process high-priority properties first
3. **Parallel Processing**: Multiple collectors working in parallel
4. **Real-time Updates**: WebSocket support for live updates
5. **Data Enrichment**: Additional data sources integration