# LLM Processing API Documentation

## Overview

The LLM Processing system provides AI-powered property data extraction from HTML and text sources using Ollama with the llama3.2:latest model. This API enables automated extraction of structured property information with validation, caching, and performance optimization.

## Core Components

### OllamaClient

The client for interacting with the local Ollama LLM service.

```python
from phoenix_real_estate.collectors.processing import OllamaClient
from phoenix_real_estate.foundation import ConfigProvider

async with OllamaClient(ConfigProvider()) as client:
    result = await client.extract_property_data(html_content)
```

#### Methods

##### `extract_property_data(content: str, source: str = "unknown", retry_on_failure: bool = True) -> Dict[str, Any]`

Extracts property data from HTML or text content.

**Parameters:**
- `content` (str): The HTML or text content to process
- `source` (str): Source identifier (e.g., "phoenix_mls", "maricopa_api")
- `retry_on_failure` (bool): Whether to retry on extraction failure

**Returns:**
- Dictionary containing extracted property fields

**Raises:**
- `ProcessingError`: If extraction fails after all retries

**Example:**
```python
data = await client.extract_property_data(
    html_content,
    source="phoenix_mls",
    retry_on_failure=True
)
```

##### `health_check() -> Dict[str, Any]`

Checks if the Ollama service is running and accessible.

**Returns:**
- Dictionary with `status`, `model`, and `version` fields

**Example:**
```python
health = await client.health_check()
if health["status"] != "ok":
    raise RuntimeError("Ollama service not available")
```

### PropertyDataExtractor

Handles the extraction logic and prompt engineering for property data.

```python
from phoenix_real_estate.collectors.processing import PropertyDataExtractor
from phoenix_real_estate.foundation import ConfigProvider

extractor = PropertyDataExtractor(ConfigProvider())
```

#### Methods

##### `extract(raw_data: Union[str, Dict[str, Any]], source: str = "unknown") -> PropertyDetails`

Extracts property details from raw data.

**Parameters:**
- `raw_data`: HTML string or dictionary of property data
- `source`: Data source identifier

**Returns:**
- `PropertyDetails` object with extracted information

**Example:**
```python
property_details = await extractor.extract(
    html_content,
    source="phoenix_mls"
)
```

##### `extract_field(content: str, field_name: str) -> Optional[Any]`

Extracts a specific field from content.

**Parameters:**
- `content`: Text content to process
- `field_name`: Name of the field to extract

**Returns:**
- Extracted field value or None

### DataProcessingPipeline

Orchestrates the complete extraction, validation, and storage workflow.

```python
from phoenix_real_estate.collectors.processing import DataProcessingPipeline
from phoenix_real_estate.foundation import ConfigProvider

async with DataProcessingPipeline(ConfigProvider()) as pipeline:
    result = await pipeline.process_property(raw_data, source="phoenix_mls")
```

#### Methods

##### `process_property(raw_data: Union[str, Dict[str, Any]], source: str = "unknown", metadata: Optional[Dict[str, Any]] = None) -> ProcessingResult`

Processes a single property through the complete pipeline.

**Parameters:**
- `raw_data`: Raw property data (HTML or dict)
- `source`: Data source identifier
- `metadata`: Additional metadata to attach

**Returns:**
- `ProcessingResult` object containing:
  - `is_valid`: Whether processing succeeded
  - `property_data`: Extracted PropertyDetails (if valid)
  - `validation_result`: Validation details
  - `processing_time`: Time taken in seconds
  - `error`: Error message (if failed)

**Example:**
```python
result = await pipeline.process_property(
    html_content,
    source="phoenix_mls",
    metadata={"listing_id": "12345"}
)

if result.is_valid:
    print(f"Extracted: {result.property_data.address}")
else:
    print(f"Failed: {result.error}")
```

##### `process_batch(items: List[Dict[str, Any]], source: str = "unknown", max_concurrency: int = 5) -> List[ProcessingResult]`

Processes multiple properties concurrently.

**Parameters:**
- `items`: List of property data items
- `source`: Data source identifier
- `max_concurrency`: Maximum concurrent operations

**Returns:**
- List of ProcessingResult objects

**Example:**
```python
results = await pipeline.process_batch(
    property_list,
    source="maricopa_api",
    max_concurrency=10
)

successful = [r for r in results if r.is_valid]
print(f"Processed {len(successful)}/{len(results)} successfully")
```

### ProcessingValidator

Validates extracted property data against configurable rules.

```python
from phoenix_real_estate.collectors.processing import ProcessingValidator
from phoenix_real_estate.foundation import ConfigProvider

validator = ProcessingValidator(ConfigProvider())
```

#### Methods

##### `validate(property_data: PropertyDetails, source: Optional[str] = None) -> ValidationResult`

Validates property data against all configured rules.

**Parameters:**
- `property_data`: PropertyDetails object to validate
- `source`: Optional source identifier for source-specific rules

**Returns:**
- `ValidationResult` containing:
  - `is_valid`: Overall validation status
  - `errors`: List of validation errors
  - `warnings`: List of validation warnings
  - `metadata`: Additional validation metadata

**Example:**
```python
result = validator.validate(property_details, source="phoenix_mls")
if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")
```

### ProcessingIntegrator

Bridges data collectors with the LLM processing pipeline.

```python
from phoenix_real_estate.orchestration import ProcessingIntegrator
from phoenix_real_estate.foundation import ConfigProvider

async with ProcessingIntegrator(ConfigProvider()) as integrator:
    result = await integrator.process_property(
        raw_data,
        source="phoenix_mls"
    )
```

#### Methods

##### `process_from_collector(collector_name: str, limit: Optional[int] = None) -> AsyncIterator[IntegrationResult]`

Processes data directly from a collector.

**Parameters:**
- `collector_name`: Name of the collector ("maricopa" or "phoenix_mls")
- `limit`: Maximum number of properties to process

**Yields:**
- `IntegrationResult` objects for each processed property

**Example:**
```python
async for result in integrator.process_from_collector("maricopa", limit=100):
    if result.success:
        print(f"Processed: {result.property_id}")
    else:
        print(f"Failed: {result.error}")
```

## Data Models

### ProcessingResult

Result of processing a single property.

```python
@dataclass
class ProcessingResult:
    is_valid: bool
    property_data: Optional[PropertyDetails] = None
    validation_result: Optional[ValidationResult] = None
    source: Optional[str] = None
    processing_time: float = 0.0
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### ValidationResult

Result of validating property data.

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### PropertyDetails

Extracted property information.

```python
@dataclass
class PropertyDetails:
    # Address information
    address: str
    city: str
    state: str
    zip_code: str
    
    # Property characteristics
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    lot_size: Optional[float] = None
    year_built: Optional[int] = None
    property_type: Optional[str] = None
    
    # Listing information
    price: Optional[float] = None
    listing_date: Optional[datetime] = None
    mls_number: Optional[str] = None
    status: Optional[str] = None
    
    # Additional details
    description: Optional[str] = None
    features: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
```

## Error Handling

The API uses custom exceptions for error handling:

```python
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError

try:
    result = await pipeline.process_property(data)
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    # Handle error appropriately
```

Common error types:
- `ProcessingError`: General processing failures
- `ValidationError`: Data validation failures
- `ConnectionError`: Ollama service connection issues
- `TimeoutError`: Processing timeout exceeded

## Performance Optimization

### Caching

Enable caching to reduce redundant LLM calls:

```python
from phoenix_real_estate.collectors.processing import CacheConfig, CacheManager

cache_config = CacheConfig(
    max_size=1000,
    ttl_seconds=3600,
    enable_memory_cache=True,
    enable_disk_cache=True
)

cache_manager = CacheManager(cache_config)
pipeline.set_cache_manager(cache_manager)
```

### Batch Processing

Use batch processing for better throughput:

```python
# Process in batches of 50 with 10 concurrent operations
results = await pipeline.process_batch(
    items,
    source="maricopa_api",
    max_concurrency=10,
    batch_size=50
)
```

### Resource Monitoring

Monitor resource usage during processing:

```python
from phoenix_real_estate.collectors.processing import ResourceMonitor

monitor = ResourceMonitor()
await monitor.start()

# ... processing operations ...

metrics = await monitor.get_metrics()
print(f"CPU Usage: {metrics.cpu_percent}%")
print(f"Memory Usage: {metrics.memory_mb}MB")
```

## Example: Complete Processing Flow

```python
import asyncio
from phoenix_real_estate.orchestration import ProcessingIntegrator
from phoenix_real_estate.foundation import ConfigProvider

async def process_properties():
    """Complete example of processing properties."""
    config = ConfigProvider()
    
    async with ProcessingIntegrator(config) as integrator:
        # Process from Maricopa API
        maricopa_results = []
        async for result in integrator.process_from_collector("maricopa", limit=10):
            maricopa_results.append(result)
            if result.success:
                print(f"✓ Processed Maricopa property: {result.property_id}")
            else:
                print(f"✗ Failed: {result.error}")
        
        # Process individual property from Phoenix MLS
        phoenix_data = {"html": "<div>Property listing HTML...</div>"}
        result = await integrator.process_property(phoenix_data, "phoenix_mls")
        
        if result.success:
            print(f"✓ Processed Phoenix MLS property")
            print(f"  Address: {result.property_data.address}")
            print(f"  Price: ${result.property_data.price:,.2f}")
        
        # Get processing statistics
        stats = await integrator.get_statistics()
        print(f"\nProcessing Statistics:")
        print(f"  Total: {stats['total_processed']}")
        print(f"  Success: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")

if __name__ == "__main__":
    asyncio.run(process_properties())
```

## API Reference Summary

| Component | Purpose | Key Methods |
|-----------|---------|-------------|
| `OllamaClient` | LLM service interface | `extract_property_data()`, `health_check()` |
| `PropertyDataExtractor` | Extraction logic | `extract()`, `extract_field()` |
| `DataProcessingPipeline` | Workflow orchestration | `process_property()`, `process_batch()` |
| `ProcessingValidator` | Data validation | `validate()` |
| `ProcessingIntegrator` | Collector integration | `process_from_collector()`, `process_property()` |
| `CacheManager` | Performance caching | `get()`, `set()`, `clear()` |
| `ResourceMonitor` | Resource tracking | `start()`, `get_metrics()` |