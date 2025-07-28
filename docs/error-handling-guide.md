# Error Handling and Recovery Guide

## Overview

The Phoenix Real Estate Data Collector includes a comprehensive error handling and recovery system designed to ensure reliable data processing even when facing various failure scenarios. This guide covers the key components and usage patterns.

## Key Components

### 1. Error Classification System

The `ErrorClassifier` automatically categorizes errors and determines appropriate recovery actions:

```python
from phoenix_real_estate.collectors.processing.error_handling import ErrorClassifier, ErrorType

classifier = ErrorClassifier()
error_type = classifier.classify(exception)
recovery_action = classifier.get_recovery_action(error_type)
```

**Error Types:**
- `NETWORK`: Connection errors, timeouts
- `RATE_LIMIT`: API rate limiting (HTTP 429)
- `AUTHENTICATION`: Auth failures (HTTP 401/403)
- `DATA_ERROR`: Parsing/validation errors
- `TEMPORARY`: Service unavailable (HTTP 502/503)
- `PERMANENT`: Not found (HTTP 404/410)
- `UNKNOWN`: Unclassified errors

### 2. Circuit Breaker Pattern

Prevents cascading failures by blocking calls to failing services:

```python
from phoenix_real_estate.collectors.processing.error_handling import CircuitBreaker

# Create circuit breaker
breaker = CircuitBreaker(
    failure_threshold=5,     # Opens after 5 failures
    recovery_timeout=60,     # Waits 60s before half-open
    expected_exception=Exception
)

# Use with async functions
async def protected_call():
    return await breaker.execute_async(risky_function)
```

**Circuit States:**
- `CLOSED`: Normal operation
- `OPEN`: Blocking all calls
- `HALF_OPEN`: Testing recovery

### 3. Dead Letter Queue

Stores items that failed processing for later analysis or retry:

```python
from phoenix_real_estate.collectors.processing.error_handling import DeadLetterQueue

dlq = DeadLetterQueue(max_size=1000)

# Add failed item
await dlq.add_failed_item(item, error, attempt_count=3)

# Retrieve failed items
failed_items = await dlq.get_failed_items()

# Retry specific item
result = await dlq.retry_item(0, retry_function)

# Export for analysis
await dlq.export_to_file("failed_items.json")
```

### 4. Fallback Extraction

When structured parsing fails, fallback extractors use regex patterns:

```python
from phoenix_real_estate.collectors.processing.error_handling import FallbackExtractor

extractor = FallbackExtractor()

# Extract from raw text
raw_text = "3BR/2BA home at 123 Main St, Phoenix, AZ 85001. $350,000"
result = await extractor.extract_from_raw_data({"description": raw_text})

# Individual extractors available:
price = extractor.extract_price_from_text(raw_text)
address = extractor.extract_address_from_text(raw_text)
beds, baths = extractor.extract_bedrooms_bathrooms(raw_text)
```

### 5. Error Recovery Strategy

Coordinates all error handling components:

```python
from phoenix_real_estate.collectors.processing.error_handling import ErrorRecoveryStrategy

strategy = ErrorRecoveryStrategy()

# Register circuit breakers
strategy.register_circuit_breaker("maricopa_api", circuit_breaker)

# Handle errors with full recovery
result = await strategy.handle_error(
    async_function,
    context={"item": data, "raw_data": raw_html},
    max_retries=3,
    use_fallback=True,
    add_to_dlq=True
)
```

## Usage Patterns

### Basic Error Handling

```python
async def process_property_with_recovery(property_data):
    strategy = ErrorRecoveryStrategy()
    
    async def process():
        # Your processing logic here
        return await llm_processor.process(property_data)
    
    try:
        result = await strategy.handle_error(
            process,
            context={"item": property_data},
            max_retries=3
        )
        return result
    except Exception as e:
        logger.error(f"Processing failed after retries: {e}")
        return None
```

### Circuit Breaker Protection

```python
# Setup circuit breakers for external services
strategy = ErrorRecoveryStrategy()

# Maricopa API circuit breaker
maricopa_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=300)
strategy.register_circuit_breaker("maricopa_api", maricopa_breaker)

# Phoenix MLS circuit breaker
mls_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=600)
strategy.register_circuit_breaker("phoenix_mls", mls_breaker)

# Use in processing
async def fetch_with_protection(service_name, fetch_function):
    return await strategy.handle_error_with_circuit_breaker(
        service_name,
        fetch_function,
        context={},
        max_retries=2
    )
```

### Batch Processing with Error Recovery

```python
async def process_batch_with_recovery(items):
    strategy = ErrorRecoveryStrategy()
    results = []
    
    for item in items:
        try:
            result = await strategy.handle_error(
                lambda: process_item(item),
                context={"item": item, "raw_data": item.get("html")},
                max_retries=3,
                use_fallback=True,
                add_to_dlq=True
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Item {item['id']} failed: {e}")
            results.append(None)
    
    # Check dead letter queue
    failed_count = strategy.dead_letter_queue.size()
    if failed_count > 0:
        logger.warning(f"{failed_count} items in dead letter queue")
    
    return results
```

### Fallback Extraction Example

```python
async def process_with_fallback(raw_html):
    strategy = ErrorRecoveryStrategy()
    
    async def parse_structured():
        # Try structured parsing
        parsed = await parser.parse(raw_html)
        if not parsed or not parsed.get("price"):
            raise ValueError("Incomplete parse")
        return parsed
    
    # Will automatically use fallback if parsing fails
    result = await strategy.handle_error(
        parse_structured,
        context={"raw_data": {"description": raw_html}},
        use_fallback=True
    )
    
    return result
```

## Configuration

### Retry Delays

Default retry delays by error type:
- `NETWORK`: [1, 2, 4, 8] seconds (exponential backoff)
- `RATE_LIMIT`: [60, 120, 300] seconds
- `TEMPORARY`: [2, 5, 10] seconds
- `AUTHENTICATION`: [1, 5] seconds

### Custom Configuration

```python
# Customize retry delays
strategy = ErrorRecoveryStrategy()
strategy.retry_delays[ErrorType.RATE_LIMIT] = [30, 60, 120]

# Configure circuit breaker
breaker = CircuitBreaker(
    failure_threshold=10,    # More tolerant
    recovery_timeout=120,    # Longer recovery
    expected_exception=ProcessingError
)
```

## Monitoring and Debugging

### Circuit Breaker Status

```python
# Check circuit breaker state
if breaker.state == CircuitState.OPEN:
    logger.warning(f"Circuit open, failures: {breaker.failure_count}")
    logger.warning(f"Last failure: {breaker.last_failure_time}")
```

### Dead Letter Queue Analysis

```python
# Analyze failed items
failed_items = await dlq.get_failed_items()
error_summary = {}

for item in failed_items:
    error_type = item["error_type"]
    error_summary[error_type] = error_summary.get(error_type, 0) + 1

logger.info(f"Failed items by error type: {error_summary}")

# Export for offline analysis
await dlq.export_to_file(f"dlq_{datetime.now().isoformat()}.json")
```

### Logging

The error handling system logs key events:
- Circuit breaker state changes
- Retry attempts and delays
- Dead letter queue additions
- Fallback extraction usage

Enable debug logging for detailed traces:
```python
import logging
logging.getLogger("phoenix_real_estate.collectors.processing.error_handling").setLevel(logging.DEBUG)
```

## Best Practices

1. **Configure Circuit Breakers**: Set appropriate thresholds based on service reliability
2. **Monitor Dead Letter Queue**: Regularly check and analyze failed items
3. **Test Fallback Extractors**: Ensure patterns match your data formats
4. **Set Reasonable Timeouts**: Balance between giving services time to respond and failing fast
5. **Use Context**: Provide rich context for better error recovery
6. **Handle Permanent Failures**: Don't retry 404s and other permanent errors
7. **Log Strategically**: Log enough to debug issues without overwhelming logs

## Testing

```python
# Test error handling
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_error_recovery():
    strategy = ErrorRecoveryStrategy()
    
    # Mock function that fails then succeeds
    mock_func = AsyncMock(side_effect=[
        ConnectionError("Network error"),
        ConnectionError("Network error"),
        {"success": True}
    ])
    
    result = await strategy.handle_error(
        mock_func,
        context={},
        max_retries=3
    )
    
    assert result == {"success": True}
    assert mock_func.call_count == 3
```