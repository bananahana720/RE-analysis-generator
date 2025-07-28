# LLM Processing Troubleshooting Guide

## Table of Contents
1. [Common Issues](#common-issues)
2. [Ollama Service Issues](#ollama-service-issues)
3. [Model Issues](#model-issues)
4. [Extraction Problems](#extraction-problems)
5. [Performance Issues](#performance-issues)
6. [Integration Problems](#integration-problems)
7. [Validation Errors](#validation-errors)
8. [Resource Issues](#resource-issues)
9. [Debugging Tools](#debugging-tools)
10. [Error Reference](#error-reference)

## Common Issues

### Issue: "Ollama service not available"

**Symptoms:**
- `ConnectionError: Cannot connect to Ollama service`
- `aiohttp.ClientConnectorError`
- Health check fails

**Solutions:**

1. **Check if Ollama is running:**
   ```bash
   # Windows
   tasklist | findstr ollama
   
   # Check service endpoint
   curl http://localhost:11434/api/tags
   ```

2. **Start Ollama service:**
   ```bash
   # Start Ollama
   ollama serve
   
   # Or run in background (Windows)
   start /B ollama serve
   ```

3. **Check configuration:**
   ```python
   # Verify URL in .env
   OLLAMA_BASE_URL=http://localhost:11434
   
   # Test in Python
   from phoenix_real_estate.foundation import ConfigProvider
   config = ConfigProvider()
   print(config.settings.OLLAMA_BASE_URL)
   ```

4. **Firewall/Antivirus:**
   - Add exception for port 11434
   - Temporarily disable to test
   - Check Windows Defender settings

### Issue: "Processing timeout"

**Symptoms:**
- `TimeoutError: LLM request timed out`
- Processing takes too long
- Partial results

**Solutions:**

1. **Increase timeout:**
   ```env
   # .env
   LLM_TIMEOUT=60  # Increase from default 30
   ```

2. **Reduce content size:**
   ```python
   # Chunk large content
   from phoenix_real_estate.utils import chunk_content
   
   chunks = chunk_content(html_content, max_size=4096)
   for chunk in chunks:
       result = await pipeline.process_property(chunk)
   ```

3. **Optimize prompts:**
   ```python
   # Use more focused prompts
   extractor.prompt_template = """
   Extract only: address, price, bedrooms, bathrooms
   from the following content. Be concise.
   
   Content: {content}
   """
   ```

### Issue: "High error rate"

**Symptoms:**
- Many failed extractions
- Low success rate (<50%)
- Inconsistent results

**Solutions:**

1. **Check data quality:**
   ```python
   # Add preprocessing
   def preprocess_html(html):
       # Remove scripts and styles
       html = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
       html = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL)
       # Clean whitespace
       html = ' '.join(html.split())
       return html
   
   clean_html = preprocess_html(raw_html)
   result = await pipeline.process_property(clean_html)
   ```

2. **Enable retries:**
   ```python
   # Increase retry attempts
   config.settings.LLM_MAX_RETRIES = 3
   
   # Or per-request
   result = await client.extract_property_data(
       content,
       retry_on_failure=True
   )
   ```

3. **Review validation rules:**
   ```python
   # Relax validation for better success rate
   validator = ProcessingValidator(config)
   validator.strict_mode = False
   
   # Or disable specific rules
   validator.disable_rule("price_range")
   ```

## Ollama Service Issues

### Issue: "Model not found"

**Error:** `404 model 'llama3.2:latest' not found`

**Solution:**
```bash
# Pull the correct model
ollama pull llama3.2:latest

# List available models
ollama list

# Verify model in config
# .env
LLM_MODEL=llama3.2:latest
```

### Issue: "Ollama crashes or hangs"

**Symptoms:**
- Service stops responding
- High memory usage
- System slowdown

**Solutions:**

1. **Check system resources:**
   ```bash
   # Windows - Check memory
   wmic OS get TotalVisibleMemorySize,FreePhysicalMemory
   
   # Monitor Ollama process
   tasklist /fi "imagename eq ollama.exe"
   ```

2. **Restart Ollama:**
   ```bash
   # Stop Ollama
   taskkill /IM ollama.exe /F
   
   # Clear cache
   rmdir /s /q %USERPROFILE%\.ollama\models\.cache
   
   # Restart
   ollama serve
   ```

3. **Reduce model size:**
   ```bash
   # Use smaller model if needed
   ollama pull llama2:7b
   
   # Update config
   LLM_MODEL=llama2:7b
   ```

### Issue: "Port already in use"

**Error:** `bind: address already in use`

**Solution:**
```bash
# Find process using port 11434
netstat -ano | findstr :11434

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or use different port
OLLAMA_HOST=0.0.0.0:11435 ollama serve
```

## Model Issues

### Issue: "Inconsistent extraction results"

**Symptoms:**
- Same input gives different outputs
- Missing fields randomly
- Incorrect data types

**Solutions:**

1. **Set consistent parameters:**
   ```env
   # .env
   LLM_TEMPERATURE=0.1  # Lower = more consistent
   LLM_SEED=42         # Fixed seed
   LLM_TOP_K=10        # Reduce randomness
   ```

2. **Use structured prompts:**
   ```python
   STRUCTURED_PROMPT = """
   Extract exactly these fields as JSON:
   {
     "address": "full street address",
     "price": numeric value only,
     "bedrooms": integer only,
     "bathrooms": float with .5 for half baths
   }
   
   Content: {content}
   """
   ```

3. **Add validation loop:**
   ```python
   async def extract_with_validation(content, max_attempts=3):
       for attempt in range(max_attempts):
           result = await extractor.extract(content)
           if validator.validate(result).is_valid:
               return result
       return None
   ```

### Issue: "Model returns non-JSON response"

**Error:** `JSONDecodeError: Expecting value`

**Solutions:**

1. **Force JSON format:**
   ```python
   # In extraction request
   response = await client._request({
       "model": self.model_name,
       "prompt": prompt,
       "format": "json",  # Force JSON
       "stream": False
   })
   ```

2. **Add response parsing:**
   ```python
   def parse_llm_response(response_text):
       # Try to extract JSON from response
       json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
       if json_match:
           try:
               return json.loads(json_match.group())
           except json.JSONDecodeError:
               pass
       
       # Fallback parsing
       return extract_with_regex(response_text)
   ```

3. **Use fallback extraction:**
   ```python
   try:
       data = await llm_extractor.extract(content)
   except json.JSONDecodeError:
       logger.warning("LLM returned non-JSON, using fallback")
       data = regex_extractor.extract(content)
   ```

## Extraction Problems

### Issue: "Missing required fields"

**Symptoms:**
- Key fields like address or price missing
- Validation failures
- Incomplete property data

**Solutions:**

1. **Improve content preprocessing:**
   ```python
   def enhance_content_visibility(html):
       # Add markers for important sections
       patterns = {
           r'<h1.*?>(.*?)</h1>': '[ADDRESS: {0}]',
           r'\$[\d,]+': '[PRICE: {0}]',
           r'(\d+)\s*(?:bed|br)': '[BEDROOMS: {0}]',
       }
       
       for pattern, template in patterns.items():
           html = re.sub(pattern, 
                        lambda m: template.format(m.group(1)), 
                        html)
       return html
   ```

2. **Use multi-pass extraction:**
   ```python
   async def multi_pass_extraction(content):
       # First pass: general extraction
       data = await extractor.extract(content)
       
       # Second pass: missing fields
       missing = validator.get_missing_fields(data)
       for field in missing:
           value = await extractor.extract_field(content, field)
           if value:
               setattr(data, field, value)
       
       return data
   ```

3. **Add context to prompts:**
   ```python
   # Provide examples in prompt
   PROMPT_WITH_EXAMPLES = """
   Extract property information. Examples:
   - Address: "123 Main St, Phoenix, AZ 85031"
   - Price: 350000 (number only, no symbols)
   - Bedrooms: 3 (integer)
   
   Content: {content}
   """
   ```

### Issue: "Wrong data types extracted"

**Symptoms:**
- Price as string instead of float
- Bedrooms as float instead of int
- Dates in wrong format

**Solutions:**

1. **Add type conversion:**
   ```python
   def convert_types(data):
       converters = {
           'price': lambda x: float(re.sub(r'[^\d.]', '', str(x))),
           'bedrooms': lambda x: int(float(x)),
           'bathrooms': lambda x: float(x),
           'square_feet': lambda x: int(re.sub(r'[^\d]', '', str(x))),
           'year_built': lambda x: int(x) if x else None,
       }
       
       for field, converter in converters.items():
           if hasattr(data, field) and getattr(data, field):
               try:
                   value = getattr(data, field)
                   setattr(data, field, converter(value))
               except (ValueError, TypeError):
                   logger.warning(f"Failed to convert {field}: {value}")
       
       return data
   ```

2. **Specify types in prompt:**
   ```python
   TYPE_SPECIFIC_PROMPT = """
   Extract and return as JSON with correct types:
   {
     "price": <number without $ or commas>,
     "bedrooms": <integer>,
     "bathrooms": <float, use .5 for half>,
     "square_feet": <integer>,
     "year_built": <4-digit integer>
   }
   """
   ```

## Performance Issues

### Issue: "Slow processing speed"

**Symptoms:**
- Processing <1 property per second
- High latency
- Queue backlog

**Solutions:**

1. **Enable caching:**
   ```python
   # Configure aggressive caching
   cache_config = CacheConfig(
       max_size=10000,
       ttl_seconds=7200,
       enable_memory_cache=True,
       enable_disk_cache=True
   )
   
   pipeline.set_cache_manager(CacheManager(cache_config))
   ```

2. **Optimize batch size:**
   ```python
   # Find optimal batch size
   from phoenix_real_estate.collectors.processing import BatchSizeOptimizer
   
   optimizer = BatchSizeOptimizer()
   optimal_size = await optimizer.find_optimal_size(
       sample_data=properties[:100],
       target_latency=0.5
   )
   
   # Use optimal size
   results = await pipeline.process_batch(
       properties,
       batch_size=optimal_size
   )
   ```

3. **Increase concurrency:**
   ```python
   # Configure higher concurrency
   config.settings.LLM_MAX_CONCURRENT = 20
   config.settings.PROCESSING_MAX_CONCURRENT = 20
   
   # Process with more workers
   results = await pipeline.process_batch(
       properties,
       max_concurrency=20
   )
   ```

### Issue: "High memory usage"

**Symptoms:**
- Memory steadily increasing
- Out of memory errors
- System slowdown

**Solutions:**

1. **Enable memory limits:**
   ```python
   # Set resource limits
   from phoenix_real_estate.collectors.processing import ResourceMonitor
   
   monitor = ResourceMonitor(
       max_memory_mb=2048,
       alert_callback=lambda a: logger.warning(a.message)
   )
   await monitor.start()
   ```

2. **Process in smaller batches:**
   ```python
   async def process_with_memory_management(items, batch_size=10):
       for i in range(0, len(items), batch_size):
           batch = items[i:i + batch_size]
           results = await pipeline.process_batch(batch)
           
           # Force garbage collection
           import gc
           gc.collect()
           
           # Clear cache if needed
           if monitor.memory_mb > 1500:
               await cache_manager.clear_old_entries()
   ```

3. **Use streaming processing:**
   ```python
   async def stream_process(source):
       async for item in source:
           result = await pipeline.process_property(item)
           yield result
           # Item is garbage collected after yield
   ```

## Integration Problems

### Issue: "Cannot connect to MongoDB"

**Error:** `ServerSelectionTimeoutError`

**Solution:**
```bash
# Check MongoDB service (Windows)
net start MongoDB

# Verify connection
python -c "from pymongo import MongoClient; client = MongoClient('localhost', 27017); print(client.server_info())"
```

### Issue: "Collector integration failing"

**Symptoms:**
- No data from collectors
- Integration timeout
- Empty results

**Solutions:**

1. **Check collector configuration:**
   ```python
   # Test collectors individually
   from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector
   
   collector = MaricopaAPICollector(config)
   async with collector:
       # Test single fetch
       data = await collector.fetch_property("123-45-678")
       print(data)
   ```

2. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # Or specific module
   logging.getLogger("phoenix_real_estate.orchestration").setLevel(logging.DEBUG)
   ```

3. **Check API keys:**
   ```python
   # Verify API keys are loaded
   print(f"Maricopa API Key: {config.settings.MARICOPA_API_KEY[:10]}...")
   print(f"WebShare API Key: {config.settings.WEBSHARE_API_KEY[:10]}...")
   ```

## Validation Errors

### Issue: "Validation always fails"

**Symptoms:**
- All properties marked invalid
- Too strict validation
- Business logic mismatch

**Solutions:**

1. **Review validation rules:**
   ```python
   # List active rules
   validator = ProcessingValidator(config)
   for rule in validator.rules:
       print(f"{rule.name}: {rule.description}")
   
   # Disable problematic rules
   validator.disable_rule("price_range")
   ```

2. **Add source-specific rules:**
   ```python
   # Different rules for different sources
   validator.add_rule(
       ValidationRule(
           name="mls_price",
           validate=lambda p: p.price > 0 if p.price else True,
           applies_to_sources=["phoenix_mls"]
       )
   )
   ```

3. **Use warning mode:**
   ```python
   # Convert errors to warnings
   validator.strict_mode = False
   
   # Or check warnings separately
   result = validator.validate(property_data)
   if result.warnings:
       logger.warning(f"Validation warnings: {result.warnings}")
   ```

## Resource Issues

### Issue: "Circuit breaker open"

**Symptoms:**
- `CircuitBreakerError: Circuit breaker is open`
- All requests failing fast
- No recovery

**Solutions:**

1. **Check failure cause:**
   ```python
   # Get circuit breaker status
   from phoenix_real_estate.collectors.processing.circuit_breaker import CircuitBreaker
   
   breaker = pipeline._circuit_breaker
   print(f"State: {breaker.state}")
   print(f"Failures: {breaker.failure_count}")
   print(f"Last error: {breaker.last_failure}")
   ```

2. **Manual reset:**
   ```python
   # Force reset if needed
   breaker.reset()
   
   # Or wait for recovery timeout
   await asyncio.sleep(breaker.recovery_timeout)
   ```

3. **Adjust thresholds:**
   ```env
   # .env
   CIRCUIT_BREAKER_FAILURE_THRESHOLD=10  # Increase from 5
   CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30   # Decrease from 60
   ```

### Issue: "Rate limit exceeded"

**Symptoms:**
- `RateLimitError`
- 429 status codes
- Throttling messages

**Solutions:**

1. **Implement rate limiting:**
   ```python
   from asyncio import Semaphore
   
   # Limit concurrent requests
   semaphore = Semaphore(5)
   
   async def rate_limited_process(item):
       async with semaphore:
           return await pipeline.process_property(item)
   ```

2. **Add delays:**
   ```python
   import asyncio
   
   async def process_with_delay(items, delay=0.1):
       results = []
       for item in items:
           result = await pipeline.process_property(item)
           results.append(result)
           await asyncio.sleep(delay)
       return results
   ```

## Debugging Tools

### Enable Detailed Logging

```python
# Enable all debug logs
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Or use environment variable
# export LOG_LEVEL=DEBUG
```

### Performance Profiling

```python
import time
import cProfile
import pstats

# Profile processing
profiler = cProfile.Profile()
profiler.enable()

# Run processing
results = await pipeline.process_batch(items)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
async def process_with_memory_tracking():
    async with DataProcessingPipeline(config) as pipeline:
        results = await pipeline.process_batch(large_dataset)
    return results
```

### Request Inspection

```python
# Enable request logging
import aiohttp

async def log_requests(session, trace_config_ctx, params):
    print(f"Request: {params.method} {params.url}")
    print(f"Headers: {params.headers}")

trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(log_requests)

# Use with client
connector = aiohttp.TCPConnector(trace_configs=[trace_config])
```

### Test Individual Components

```python
# Test script for components
async def test_components():
    config = ConfigProvider()
    
    # Test Ollama connection
    print("Testing Ollama...")
    client = OllamaClient(config)
    health = await client.health_check()
    print(f"Ollama status: {health}")
    
    # Test extraction
    print("\nTesting extraction...")
    extractor = PropertyDataExtractor(config)
    test_html = "<div>123 Main St, $300,000, 3 bed 2 bath</div>"
    result = await extractor.extract(test_html)
    print(f"Extracted: {result}")
    
    # Test validation
    print("\nTesting validation...")
    validator = ProcessingValidator(config)
    validation = validator.validate(result)
    print(f"Valid: {validation.is_valid}")
    print(f"Errors: {validation.errors}")

asyncio.run(test_components())
```

## Error Reference

### Common Error Codes

| Error | Meaning | Solution |
|-------|---------|----------|
| `OLLAMA_001` | Service not available | Start Ollama service |
| `OLLAMA_002` | Model not found | Pull the correct model |
| `PROC_001` | Extraction timeout | Increase timeout or reduce content |
| `PROC_002` | Invalid JSON response | Check model output format |
| `VAL_001` | Required field missing | Improve extraction prompts |
| `VAL_002` | Invalid data type | Add type conversion |
| `INT_001` | Collector connection failed | Check API keys and network |
| `INT_002` | Database connection failed | Start MongoDB service |
| `RES_001` | Memory limit exceeded | Reduce batch size |
| `RES_002` | CPU limit exceeded | Reduce concurrency |

### Getting Help

If you encounter issues not covered here:

1. **Check logs** - Enable debug logging for detailed information
2. **Review configuration** - Ensure all settings are correct
3. **Test components** - Isolate the failing component
4. **Check system resources** - Ensure adequate CPU/memory
5. **Update dependencies** - Run `uv sync` to update packages

For additional support, consult the project documentation or create an issue with:
- Error messages and stack traces
- Configuration settings
- Steps to reproduce
- System information (OS, Python version, etc.)