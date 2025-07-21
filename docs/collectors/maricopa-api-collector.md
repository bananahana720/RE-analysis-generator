# Maricopa API Collector Documentation

## Overview

The Maricopa API Collector is a production-ready data collection system that integrates with the Maricopa County real estate API. It implements the DataCollector strategy pattern and provides comprehensive error handling, rate limiting, and monitoring capabilities.

## Architecture

### Component Overview

```
MaricopaAPICollector
├── MaricopaAPIClient (HTTP client with rate limiting)
├── MaricopaDataAdapter (Data transformation layer)
├── DataValidator (Schema validation)
└── RateLimiter (Observer pattern rate limiting)
```

### Key Features

- **Rate Limiting**: Compliant with 900 requests/hour limit with 10% safety margin
- **Error Recovery**: Exponential backoff retry logic with configurable attempts
- **Data Validation**: Comprehensive schema validation using Pydantic
- **Performance Monitoring**: Built-in metrics and observer pattern for tracking
- **Epic Integration**: Full integration with Epic 1 foundation and Epic 3 orchestration

## Configuration

### Required Configuration

```yaml
maricopa:
  api:
    base_url: "https://api.maricopa.gov/v1"
    bearer_token: "your-api-token"
    rate_limit: 900  # requests per hour
    rate_window_seconds: 3600
    safety_margin: 0.1  # 10% safety margin
  
  collection:
    batch_size: 100  # records per batch
    max_retries: 3
    retry_delay_seconds: 5
```

### Environment Variables

- `MARICOPA_API_KEY`: Bearer token for API authentication (required)
- `MARICOPA_API_URL`: Base URL for API (optional, defaults to production)

## Usage Examples

### Basic Collection

```python
from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository
from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector

# Initialize collector
config = ConfigProvider()
repository = PropertyRepository(config)
collector = MaricopaAPICollector(config, repository)

# Validate configuration
if collector.validate_config():
    # Collect properties by ZIP codes
    properties = collector.collect_by_zip_codes(
        zip_codes=["85001", "85002", "85003"],
        max_per_zip=100
    )
```

### Epic 3 Orchestration Integration

```python
# Async collection for orchestration
async def collect_with_orchestration():
    async with MaricopaAPICollector(config, repository) as collector:
        # Collect all properties in a ZIP code
        properties = await collector.collect_zipcode("85001")
        
        # Get detailed property information
        details = await collector.collect_property_details("PROP123456")
        
        # Adapt raw data to Property schema
        property_obj = await collector.adapt_property(raw_data)
```

### Incremental Collection

```python
# Collect only new/updated properties since last run
results = collector.collect(
    search_params={"zip_codes": ["85001"]},
    incremental=True,  # Only get updates since last collection
    save_to_repository=True
)
```

## Error Handling

### Exception Hierarchy

- `DataCollectionError`: General collection failures
- `ConfigurationError`: Invalid or missing configuration
- `ValidationError`: Data validation failures
- `ProcessingError`: Data transformation errors

### Error Recovery

The collector implements automatic retry with exponential backoff:

1. First attempt fails → Wait 5 seconds
2. Second attempt fails → Wait 10 seconds
3. Third attempt fails → Wait 20 seconds
4. Fourth attempt fails → Raise DataCollectionError

### Example Error Handling

```python
try:
    properties = collector.collect_by_zip_codes(["85001"])
except ConfigurationError as e:
    # Handle configuration issues
    logger.error(f"Configuration error: {e}")
except DataCollectionError as e:
    # Handle collection failures
    logger.error(f"Collection failed: {e}")
    # Access context for debugging
    print(e.context)
```

## Performance Characteristics

### Rate Limiting
- **Limit**: 900 requests/hour (15/minute)
- **Safety Margin**: 10% (effective limit: 810/hour)
- **Window**: Sliding 60-second window
- **Enforcement**: Pre-request validation prevents violations

### Response Times
- **ZIP Code Search**: < 30 seconds typical
- **Property Details**: < 5 seconds typical
- **Batch Collection**: Varies by size (100 records ~10 seconds)

### Memory Usage
- **Base Usage**: ~50MB
- **Per 1000 Records**: +10-20MB
- **Maximum Tested**: < 100MB for 10,000 records

### Concurrency
- **Connection Pooling**: Reuses HTTP connections
- **Thread Safety**: Rate limiter is thread-safe
- **Async Support**: Full async/await compatibility

## Monitoring and Metrics

### Collection Metrics

```python
metrics = collector.get_collection_metrics()
print(f"Total collected: {metrics['collection_metrics']['total_collected']}")
print(f"Collection rate: {metrics['collection_metrics']['collection_rate_per_second']}/sec")
print(f"Error count: {metrics['collection_metrics']['total_errors']}")
```

### Rate Limiter Metrics

```python
# Get current usage
usage = collector.client.rate_limiter.get_current_usage("maricopa_api")
print(f"Requests made: {usage['requests_made']}")
print(f"Requests remaining: {usage['requests_remaining']}")

# Get performance metrics
perf = collector.client.rate_limiter.get_performance_metrics()
print(f"Total requests: {perf['total_requests']}")
print(f"Average wait time: {perf['average_wait_time_ms']}ms")
```

### Observer Pattern Integration

```python
class CollectionMonitor:
    async def on_request_made(self, source: str, timestamp: datetime):
        print(f"Request made to {source} at {timestamp}")
    
    async def on_rate_limit_hit(self, source: str, wait_time: float):
        print(f"Rate limit hit for {source}, waiting {wait_time}s")

# Add observer
monitor = CollectionMonitor()
collector.client.rate_limiter.add_observer(monitor)
```

## Security Considerations

### Credential Protection
- API keys are never logged or included in error messages
- URLs with sensitive parameters are sanitized in logs
- All API communication uses HTTPS

### Input Validation
- Property IDs are sanitized to prevent injection
- All user inputs are validated before use
- Schema validation prevents malformed data

### Error Message Security
- No sensitive information in exceptions
- Stack traces sanitized in production
- Context data excludes credentials

## Integration Patterns

### Epic 1 Foundation Integration
- Uses ConfigProvider for all configuration
- Integrates with PropertyRepository for storage
- Uses foundation logging system
- Leverages exception hierarchy

### Epic 3 Orchestration Interface
- Implements async collection methods
- Provides source identification
- Supports property adaptation
- Includes comprehensive logging

### Epic 4 Quality Monitoring
- Observer pattern for rate limiting
- Detailed metrics collection
- Performance benchmarking support
- Error tracking and analysis

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**
   - Check effective limit calculation
   - Verify safety margin configuration
   - Review concurrent request patterns

2. **Authentication Failures**
   - Verify MARICOPA_API_KEY is set
   - Check token expiration
   - Confirm API endpoint accessibility

3. **Data Validation Errors**
   - Review adapter field mappings
   - Check for API response changes
   - Validate schema compatibility

4. **Memory Issues**
   - Reduce batch_size configuration
   - Enable incremental collection
   - Monitor collection metrics

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger("collectors.maricopa").setLevel(logging.DEBUG)

# Get detailed status
status = collector.get_collection_status()
print(f"Collector status: {status}")
```

## API Reference

See the inline documentation in the source code for detailed API reference:
- `src/phoenix_real_estate/collectors/maricopa/collector.py`
- `src/phoenix_real_estate/collectors/maricopa/client.py`
- `src/phoenix_real_estate/collectors/maricopa/adapter.py`