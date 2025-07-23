# Phoenix MLS Scraper - Quick Reference Guide

## Installation
```bash
uv pip install playwright httpx tenacity beautifulsoup4
uv run playwright install chromium
```

## Basic Setup
```python
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSScraper

config = {
    "base_url": "https://www.phoenixmlssearch.com",
    "timeout": 30,
    "rate_limit": {"requests_per_minute": 60}
}

scraper = PhoenixMLSScraper(config)
```

## Common Operations

### Search Properties by Zipcode
```python
async def search():
    await scraper.initialize_browser()
    try:
        properties = await scraper.search_properties_by_zipcode("85001")
        print(f"Found {len(properties)} properties")
    finally:
        await scraper.close_browser()
```

### Scrape Property Details
```python
async def scrape_details(url):
    await scraper.initialize_browser()
    try:
        details = await scraper.scrape_property_details(url)
        print(f"Address: {details['address']}")
        print(f"Price: {details['price']}")
    finally:
        await scraper.close_browser()
```

### Batch Processing
```python
async def batch_scrape(urls):
    await scraper.initialize_browser()
    try:
        results = await scraper.scrape_properties_batch(urls)
        print(f"Scraped {len(results)} properties")
    finally:
        await scraper.close_browser()
```

## Session Management

### Save/Load Session
```python
# Save session
await scraper.save_session()

# Load session
if await scraper.load_session():
    print("Session restored")

# Clear session
await scraper.clear_session()

# Maintain session
if not await scraper.maintain_session():
    print("Session expired")
```

## Proxy Configuration
```python
proxy_config = {
    "proxies": [
        {
            "host": "proxy.example.com",
            "port": 8080,
            "username": "user",
            "password": "pass"
        }
    ],
    "max_failures": 3,
    "cooldown_minutes": 5
}

scraper = PhoenixMLSScraper(config, proxy_config)
```

## Error Handling
```python
from phoenix_real_estate.collectors.phoenix_mls import (
    NoHealthyProxiesError,
    RateLimitError,
    PropertyNotFoundError
)

try:
    properties = await scraper.search_properties_by_zipcode("85001")
except NoHealthyProxiesError:
    print("All proxies failed")
except RateLimitError:
    await scraper.handle_rate_limit()
except Exception as e:
    print(f"Error: {e}")
```

## Data Parsing
```python
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSParser

parser = PhoenixMLSParser()

# Parse HTML
property_data = parser.parse_property(html_content)

# Normalize address
components = parser.normalize_address("123 Main St, Phoenix, AZ 85001")
# Returns: {'street': '123 Main St', 'city': 'Phoenix', 'state': 'AZ', 'zip': '85001'}

# Validate data
errors = parser.validate_data(property_data)
```

## Statistics
```python
stats = scraper.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Total requests: {stats['total_requests']}")
print(f"Properties scraped: {stats['properties_scraped']}")
```

## Configuration Examples

### Minimal Config
```python
config = {
    "base_url": "https://www.phoenixmlssearch.com"
}
```

### Full Config
```python
config = {
    "base_url": "https://www.phoenixmlssearch.com",
    "search_endpoint": "/search",
    "max_retries": 3,
    "timeout": 30,
    "rate_limit": {
        "requests_per_minute": 60
    },
    "cookies_path": "data/cookies"
}
```

### Production Config (from YAML)
```yaml
phoenix_mls:
  base_url: "https://www.phoenixmlssearch.com"
  rate_limit: 60  # requests per hour
  timeout: 30000  # milliseconds
  max_retries: 3
  browser:
    headless: true
    viewport:
      width: 1920
      height: 1080
```

## Common Patterns

### With Context Manager
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def scraper_context():
    scraper = PhoenixMLSScraper(config)
    await scraper.initialize_browser()
    try:
        yield scraper
    finally:
        await scraper.close_browser()

# Usage
async with scraper_context() as scraper:
    properties = await scraper.search_properties_by_zipcode("85001")
```

### Rate Limited Scraping
```python
async def rate_limited_scrape(zipcodes):
    async with scraper_context() as scraper:
        for zipcode in zipcodes:
            properties = await scraper.search_properties_by_zipcode(zipcode)
            
            # Process properties
            for prop in properties[:5]:  # Limit per zipcode
                details = await scraper.scrape_property_details(prop["url"])
                yield details
                
            # Respect rate limits
            await asyncio.sleep(2)
```

### Error Recovery Pattern
```python
async def scrape_with_recovery(url, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            async with scraper_context() as scraper:
                return await scraper.scrape_property_details(url)
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Browser Debug Mode
```python
config = {
    "base_url": "https://www.phoenixmlssearch.com",
    "browser": {
        "headless": False,  # Show browser
        "slowMo": 100      # Slow down actions
    }
}
```

### Save HTML for Debugging
```python
parser = PhoenixMLSParser()
parser.store_html("property_123", html_content)

# Later retrieve it
stored_html = parser.get_stored_html("property_123")
```

## Performance Tips

1. **Use batch operations** instead of individual requests
2. **Enable caching** for repeated searches
3. **Implement session persistence** to avoid re-authentication
4. **Monitor statistics** to identify bottlenecks
5. **Use proxy rotation** for better throughput
6. **Respect rate limits** to avoid blocking

## Key Classes & Methods

### PhoenixMLSScraper
- `initialize_browser()` - Start browser
- `close_browser()` - Clean up
- `search_properties_by_zipcode(zipcode)` - Search properties
- `scrape_property_details(url)` - Get property details
- `scrape_properties_batch(urls)` - Batch scraping
- `maintain_session()` - Keep session alive
- `get_statistics()` - Performance metrics

### ProxyManager
- `get_next_proxy()` - Get next proxy
- `mark_failed(proxy)` - Mark proxy as failed
- `check_health(proxy)` - Test proxy health
- `get_statistics()` - Proxy usage stats

### AntiDetectionManager
- `get_user_agent()` - Random user agent
- `get_viewport()` - Random viewport size
- `human_interaction_sequence(page)` - Simulate human behavior

### PhoenixMLSParser
- `parse_property(html)` - Extract property data
- `normalize_address(address)` - Parse address components
- `validate_data(data)` - Check data quality
- `batch_parse(html_list)` - Parse multiple properties