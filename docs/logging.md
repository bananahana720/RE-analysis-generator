# Phoenix Real Estate Logging System

## Overview

The Phoenix Real Estate logging system provides structured, environment-aware logging with support for:

- **Structured Logging**: JSON format in production, human-readable text in development
- **Correlation IDs**: Automatic request tracing across all log entries
- **Environment-Specific Configuration**: Different formats and handlers per environment
- **Sensitive Data Protection**: Automatic filtering of passwords, API keys, and credentials
- **Log Rotation**: Size-based and time-based rotation with configurable retention
- **Multiple Handlers**: Console, file, and custom handlers with different log levels

## Quick Start

### Basic Usage

```python
from phoenix_real_estate.foundation.logging import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Log messages at different levels
logger.debug("Detailed debugging information")
logger.info("General informational message")
logger.warning("Warning about potential issues")
logger.error("Error occurred but application continues")
logger.critical("Critical error requiring immediate attention")
```

### With Correlation Tracking

```python
from phoenix_real_estate.foundation.logging import get_logger, correlation_context

logger = get_logger(__name__)

# All logs within this context will share the same correlation ID
with correlation_context() as correlation_id:
    logger.info(f"Starting request processing: {correlation_id}")
    logger.info("Step 1 completed")
    logger.info("Step 2 completed")
    # correlation_id is automatically included in all logs
```

### With Extra Context

```python
logger = get_logger(__name__)

# Add contextual information to log entries
logger.info("Property saved", extra={
    "property_id": "prop_123",
    "source": "maricopa",
    "zip_code": "85031",
    "price": 450000
})
```

### Exception Logging

```python
logger = get_logger(__name__)

try:
    # Some operation that might fail
    process_property_data()
except Exception as e:
    # Logs the exception with full traceback
    logger.exception("Failed to process property data")
    # Or use error with exc_info
    logger.error("Processing failed", exc_info=True, extra={
        "property_id": property_id
    })
```

## Configuration

### Via Configuration System

The logging system automatically integrates with the Phoenix Real Estate configuration system:

```python
from phoenix_real_estate.foundation.config import get_config
from phoenix_real_estate.foundation.logging import configure_logging

# Get logging configuration from config system
config = get_config()
logging_config = config.get_logging_config()

# Apply configuration
configure_logging(logging_config)
```

### Manual Configuration

```python
from phoenix_real_estate.foundation.logging import configure_logging

configure_logging({
    "level": "INFO",                    # Minimum log level
    "format": "json",                   # "json" or "text"
    "console": True,                    # Enable console output
    "file_path": "logs/app.log",       # Log file path
    "max_bytes": 10 * 1024 * 1024,     # 10MB rotation size
    "backup_count": 5,                  # Keep 5 backup files
    "environment": "production",        # Current environment
    "handlers": {                       # Additional handlers
        "error_file": {
            "type": "file",
            "filename": "logs/errors.log",
            "level": "ERROR"
        }
    }
})
```

### Environment Variables

Configure logging via environment variables:

```bash
# Basic configuration
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# File logging
LOG_FILE_PATH=logs/phoenix_real_estate.log
LOGGING_MAX_BYTES=52428800  # 50MB
LOGGING_BACKUP_COUNT=10

# Phoenix-specific overrides
PHOENIX_LOGGING_LEVEL=INFO
PHOENIX_LOGGING_FILE_PATH=logs/app.log
```

## Log Formats

### JSON Format (Production)

```json
{
    "timestamp": "2025-01-20T10:30:45.123Z",
    "level": "INFO",
    "logger": "phoenix_real_estate.collectors.maricopa",
    "message": "Property data collected",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "location": {
        "file": "/app/collectors/maricopa.py",
        "line": 145,
        "function": "collect_property"
    },
    "context": {
        "thread": 123456,
        "thread_name": "MainThread",
        "process": 789,
        "process_name": "MainProcess"
    },
    "extra": {
        "property_id": "prop_123",
        "source": "maricopa",
        "duration_ms": 234
    }
}
```

### Text Format (Development)

```
2025-01-20 10:30:45.123 [INFO] [phoenix_real_estate.collectors.maricopa] [550e8400-e29b-41d4-a716-446655440000] Property data collected {property_id: prop_123, source: maricopa, duration_ms: 234}
```

With colors enabled, log levels are highlighted:
- DEBUG: Cyan
- INFO: Green
- WARNING: Yellow
- ERROR: Red
- CRITICAL: Magenta

## Advanced Features

### Custom Log Context

```python
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)

# Use log_with_context for structured context
logger.log_with_context(
    "INFO",
    "Batch processing completed",
    context={
        "batch_id": "batch_123",
        "total_properties": 150,
        "successful": 148,
        "failed": 2,
        "duration_seconds": 45.3
    }
)
```

### Multiple Handlers

Configure different handlers for different purposes:

```python
configure_logging({
    "level": "DEBUG",
    "console": True,
    "file_path": "logs/app.log",
    "handlers": {
        "errors": {
            "type": "file",
            "filename": "logs/errors.log",
            "level": "ERROR",
            "max_bytes": 50 * 1024 * 1024,
            "backup_count": 10
        },
        "security": {
            "type": "file",
            "filename": "logs/security.log",
            "level": "WARNING",
            "format": "json"
        },
        "performance": {
            "type": "timed_file",
            "filename": "logs/performance.log",
            "when": "midnight",
            "backup_count": 30
        }
    }
})
```

### Time-Based Rotation

```python
configure_logging({
    "handlers": {
        "daily_logs": {
            "type": "timed_file",
            "filename": "logs/app.log",
            "when": "midnight",     # Rotate at midnight
            "interval": 1,          # Every 1 day
            "backup_count": 30,     # Keep 30 days
            "utc": True            # Use UTC time
        }
    }
})
```

Rotation options for `when`:
- `'S'`: Seconds
- `'M'`: Minutes
- `'H'`: Hours
- `'D'`: Days
- `'midnight'`: Roll over at midnight
- `'W0'-'W6'`: Weekly (0=Monday, 6=Sunday)

## Security Features

### Automatic Sensitive Data Filtering

The logging system automatically redacts sensitive information:

```python
logger.info("User authentication", extra={
    "username": "john.doe",              # Visible
    "password": "secret123",             # Redacted as [REDACTED]
    "api_key": "key-abc-123",           # Redacted as [REDACTED]
    "mongodb_uri": "mongodb://...",      # Redacted as [REDACTED]
    "session_id": "sess-456"            # Visible
})
```

Fields containing these keywords are automatically redacted:
- password
- secret
- api_key
- token
- auth
- credential
- private_key
- mongodb_uri
- database_uri

### Nested Object Filtering

Sensitive data in nested objects is also filtered:

```python
logger.info("API request", extra={
    "request": {
        "url": "/api/properties",
        "headers": {
            "Authorization": "Bearer token123",  # Redacted
            "User-Agent": "Phoenix/1.0"         # Visible
        }
    }
})
```

## Performance Considerations

### Log Level Performance

Set appropriate log levels for production:

```python
# Development
configure_logging({"level": "DEBUG"})  # Verbose logging

# Production
configure_logging({"level": "INFO"})   # Standard logging

# High-performance production
configure_logging({"level": "WARNING"}) # Minimal logging
```

### Async Logging

For high-throughput applications, consider buffering:

```python
# Use delay=True to defer file opening
configure_logging({
    "file_path": "logs/app.log",
    "handlers": {
        "async_file": {
            "type": "file",
            "filename": "logs/async.log",
            "delay": True  # Don't open file until first write
        }
    }
})
```

## Best Practices

### 1. Use Appropriate Log Levels

```python
# Use DEBUG for detailed diagnostic information
logger.debug(f"Calculated price per sqft: ${price_per_sqft:.2f}")

# Use INFO for general information
logger.info("Starting daily property collection")

# Use WARNING for potentially harmful situations
logger.warning("API rate limit approaching: 95% used")

# Use ERROR for error events that don't stop the application
logger.error("Failed to fetch property details, will retry")

# Use CRITICAL for events that might cause the application to abort
logger.critical("Database connection lost, cannot continue")
```

### 2. Include Relevant Context

```python
# Good: Includes actionable context
logger.error("Property validation failed", extra={
    "property_id": property_id,
    "validation_errors": errors,
    "source": data_source
})

# Bad: Generic message without context
logger.error("Validation failed")
```

### 3. Use Correlation IDs for Related Operations

```python
from phoenix_real_estate.foundation.logging import correlation_context

async def process_property_batch(properties):
    with correlation_context() as correlation_id:
        logger.info(f"Processing batch of {len(properties)} properties")
        
        for property in properties:
            try:
                await process_single_property(property)
                logger.debug(f"Processed property {property['id']}")
            except Exception as e:
                logger.error(f"Failed to process property {property['id']}", 
                           exc_info=True)
        
        logger.info("Batch processing completed")
```

### 4. Avoid Logging in Tight Loops

```python
# Bad: Logs for every iteration
for i in range(10000):
    logger.debug(f"Processing item {i}")
    process_item(i)

# Good: Log summary information
logger.info(f"Processing {len(items)} items")
for i, item in enumerate(items):
    process_item(item)
    if i % 1000 == 0:
        logger.debug(f"Processed {i} items")
logger.info(f"Completed processing {len(items)} items")
```

### 5. Structure Your Logger Names

```python
# Use hierarchical names matching your module structure
logger = get_logger("phoenix_real_estate.collectors.maricopa")
logger = get_logger("phoenix_real_estate.processors.llm")
logger = get_logger("phoenix_real_estate.api.properties")

# This allows fine-grained control over log levels
logging.getLogger("phoenix_real_estate.collectors").setLevel(logging.DEBUG)
logging.getLogger("phoenix_real_estate.api").setLevel(logging.WARNING)
```

## Troubleshooting

### Common Issues

1. **No log output visible**
   - Check log level configuration
   - Ensure console handler is enabled
   - Verify logger name matches configuration

2. **Log files not created**
   - Check file permissions
   - Ensure parent directory exists
   - Verify file path is absolute

3. **Sensitive data appearing in logs**
   - Check field names match filter patterns
   - Ensure formatters are properly configured
   - Verify no custom handlers bypass filtering

4. **Performance issues**
   - Reduce log level in production
   - Enable file handler delay
   - Implement log sampling for high-frequency events

### Debug Logging Configuration

```python
# Enable detailed logging about the logging system itself
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("phoenix_real_estate.foundation.logging").setLevel(logging.DEBUG)
```

## Integration Examples

### With Database Operations

```python
from phoenix_real_estate.foundation.logging import get_logger, correlation_context

logger = get_logger(__name__)

async def save_property(property_data):
    with correlation_context() as correlation_id:
        logger.info("Saving property", extra={
            "property_id": property_data.get("property_id"),
            "source": property_data.get("source")
        })
        
        try:
            result = await db.properties.insert_one(property_data)
            logger.info("Property saved successfully", extra={
                "inserted_id": str(result.inserted_id)
            })
            return result
        except Exception as e:
            logger.error("Failed to save property", 
                       exc_info=True,
                       extra={"property_data": property_data})
            raise
```

### With API Endpoints

```python
from fastapi import FastAPI, Request
from phoenix_real_estate.foundation.logging import get_logger, set_correlation_id

app = FastAPI()
logger = get_logger(__name__)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Set correlation ID for request
    correlation_id = request.headers.get("X-Correlation-ID") or set_correlation_id()
    
    logger.info("Incoming request", extra={
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else None
    })
    
    try:
        response = await call_next(request)
        logger.info("Request completed", extra={
            "status_code": response.status_code
        })
        return response
    except Exception as e:
        logger.error("Request failed", exc_info=True)
        raise
    finally:
        clear_correlation_id()
```

### With Data Collection

```python
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger("phoenix_real_estate.collectors")

class MaricopaCollector:
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    async def collect_properties(self, zip_codes):
        self.logger.info(f"Starting collection for {len(zip_codes)} ZIP codes")
        
        for zip_code in zip_codes:
            try:
                properties = await self._fetch_properties(zip_code)
                self.logger.info(f"Collected {len(properties)} properties", extra={
                    "zip_code": zip_code,
                    "source": "maricopa"
                })
            except Exception as e:
                self.logger.error(f"Collection failed for ZIP code {zip_code}", 
                                exc_info=True)
```

## Summary

The Phoenix Real Estate logging system provides a robust, secure, and performant logging solution that:

- Automatically adapts to different environments
- Protects sensitive information
- Enables request tracing with correlation IDs
- Supports multiple output formats and destinations
- Integrates seamlessly with the configuration system
- Provides rich context for debugging and monitoring

By following the best practices and examples in this guide, you can effectively use logging to monitor, debug, and maintain your Phoenix Real Estate application.