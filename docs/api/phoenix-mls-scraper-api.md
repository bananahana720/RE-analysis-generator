# Phoenix MLS Scraper API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Components](#core-components)
4. [API Reference](#api-reference)
5. [Configuration Options](#configuration-options)
6. [Error Handling](#error-handling)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

## Overview

The Phoenix MLS Scraper is a robust web scraping system designed to collect real estate property data from the Phoenix MLS Search website. It features advanced anti-detection measures, proxy management, session handling, and comprehensive error recovery mechanisms.

### Key Features
- **Playwright-based browser automation** with stealth mode
- **Intelligent proxy rotation** with health monitoring
- **Anti-detection measures** including user agent rotation and human-like behavior
- **Session persistence** for maintaining authentication
- **Rate limiting** to respect website resources
- **Comprehensive error handling** with automatic recovery
- **Data validation and normalization**

### Architecture
```
phoenix_mls/
├── scraper.py       # Main scraper implementation
├── proxy_manager.py # Proxy rotation and health monitoring
├── anti_detection.py # Anti-detection measures
└── parser.py        # HTML parsing and data extraction
```

## Getting Started

### Installation

```bash
# Install dependencies using uv
uv pip install playwright httpx tenacity beautifulsoup4

# Install Playwright browsers
uv run playwright install chromium
```

### Basic Usage

```python
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSScraper
from phoenix_real_estate.collectors.phoenix_mls import ProxyManager

# Configure scraper
config = {
    "base_url": "https://www.phoenixmlssearch.com",
    "max_retries": 3,
    "timeout": 30,
    "rate_limit": {
        "requests_per_minute": 60
    }
}

# Optional proxy configuration
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

# Initialize scraper
scraper = PhoenixMLSScraper(config, proxy_config)

# Use the scraper
async def main():
    await scraper.initialize_browser()
    try:
        # Search properties by zipcode
        properties = await scraper.search_properties_by_zipcode("85001")
        
        # Scrape individual property details
        for prop in properties:
            details = await scraper.scrape_property_details(prop["url"])
            print(details)
    finally:
        await scraper.close_browser()
```

## Core Components

### PhoenixMLSScraper

The main scraper class that orchestrates the entire scraping process.

#### Key Responsibilities:
- Browser lifecycle management
- Session handling and persistence
- Rate limiting enforcement
- Statistics tracking
- Error recovery coordination

### ProxyManager

Manages proxy rotation and health monitoring for reliable scraping.

#### Features:
- Round-robin proxy rotation
- Health monitoring with automatic recovery
- Thread-safe concurrent usage
- Failure tracking with cooldown periods
- Comprehensive statistics

### AntiDetectionManager

Implements various measures to avoid detection and blocking.

#### Techniques:
- User agent rotation
- Viewport randomization
- Human-like typing delays
- Random mouse movements
- Browser fingerprint randomization
- Realistic interaction patterns

### PhoenixMLSParser

Extracts structured data from HTML content.

#### Capabilities:
- Robust HTML parsing with BeautifulSoup
- Data normalization and validation
- Address parsing and standardization
- Price and numeric value extraction
- Feature and amenity extraction

## API Reference

### PhoenixMLSScraper

#### Constructor
```python
PhoenixMLSScraper(config: Dict[str, Any], proxy_config: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `config`: Main configuration dictionary
  - `base_url` (str): Base URL for Phoenix MLS
  - `max_retries` (int): Maximum retry attempts (default: 3)
  - `timeout` (int): Request timeout in seconds (default: 30)
  - `rate_limit` (dict): Rate limiting configuration
  - `cookies_path` (str): Path for session storage (default: "data/cookies")
- `proxy_config`: Optional proxy manager configuration

#### Methods

##### `async initialize_browser()`
Initialize the Playwright browser with anti-detection settings.

**Example:**
```python
await scraper.initialize_browser()
```

##### `async close_browser()`
Close browser and cleanup resources, saving session data.

**Example:**
```python
await scraper.close_browser()
```

##### `async search_properties_by_zipcode(zipcode: str) -> List[Dict[str, Any]]`
Search for properties in a specific zipcode.

**Parameters:**
- `zipcode` (str): The zipcode to search

**Returns:**
- List of property data dictionaries containing:
  - `url`: Property detail page URL
  - `address`: Property address
  - `price`: Listing price
  - `beds`: Number of bedrooms
  - `baths`: Number of bathrooms
  - `sqft`: Square footage

**Example:**
```python
properties = await scraper.search_properties_by_zipcode("85001")
```

##### `async scrape_property_details(property_url: str) -> Dict[str, Any]`
Scrape detailed information for a specific property.

**Parameters:**
- `property_url` (str): URL of the property detail page

**Returns:**
- Dictionary with comprehensive property details:
  - `address`: Full address
  - `price`: Listing price
  - `beds`: Number of bedrooms
  - `baths`: Number of bathrooms
  - `sqft`: Square footage
  - `lot_size`: Lot size
  - `year_built`: Year built
  - `property_type`: Type of property
  - `description`: Property description
  - `features`: List of features
  - `images`: List of image URLs
  - `raw_html`: Complete HTML for re-parsing
  - `scraped_at`: Timestamp

**Example:**
```python
details = await scraper.scrape_property_details("https://example.com/property/123")
```

##### `async scrape_properties_batch(property_urls: List[str]) -> List[Dict[str, Any]]`
Scrape multiple properties with error recovery and session maintenance.

**Parameters:**
- `property_urls` (List[str]): List of property URLs to scrape

**Returns:**
- List of successfully scraped properties

**Example:**
```python
urls = ["url1", "url2", "url3"]
results = await scraper.scrape_properties_batch(urls)
```

##### `async maintain_session() -> bool`
Maintain session by saving cookies and checking validity.

**Returns:**
- True if session is valid, False if refresh needed

**Example:**
```python
if not await scraper.maintain_session():
    # Handle session expiration
    await scraper.clear_session()
    await scraper.initialize_browser()
```

##### `async save_session() -> bool`
Save current session data (cookies, storage).

**Returns:**
- True if successful, False otherwise

##### `async load_session() -> bool`
Load saved session data.

**Returns:**
- True if loaded successfully, False otherwise

##### `async clear_session()`
Clear all session data and browser cookies.

##### `get_statistics() -> Dict[str, Any]`
Get comprehensive scraper statistics.

**Returns:**
- Dictionary containing:
  - `total_requests`: Total requests made
  - `successful_requests`: Successful requests
  - `failed_requests`: Failed requests
  - `success_rate`: Success percentage
  - `properties_scraped`: Total properties scraped
  - `proxy_stats`: Proxy usage statistics

**Example:**
```python
stats = scraper.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
```

### ProxyManager

#### Constructor
```python
ProxyManager(config: Dict[str, Any])
```

**Parameters:**
- `config`: Proxy configuration
  - `proxies`: List of proxy configurations
  - `max_failures`: Max failures before marking unhealthy (default: 3)
  - `cooldown_minutes`: Cooldown period (default: 5)
  - `health_check_url`: URL for health checks

#### Methods

##### `async get_next_proxy() -> Dict[str, Any]`
Get the next available proxy in rotation.

**Returns:**
- Proxy configuration dictionary

**Raises:**
- `NoHealthyProxiesError`: If no healthy proxies available

##### `async mark_failed(proxy: Dict[str, Any])`
Mark a proxy as failed.

##### `async mark_success(proxy: Dict[str, Any])`
Mark a proxy request as successful.

##### `async check_health(proxy: Dict[str, Any]) -> bool`
Check if a proxy is healthy.

##### `get_statistics() -> Dict[str, Any]`
Get proxy usage statistics.

### AntiDetectionManager

#### Constructor
```python
AntiDetectionManager(config: Dict[str, Any])
```

#### Methods

##### `get_user_agent() -> str`
Get a random user agent string.

##### `get_viewport() -> Tuple[int, int]`
Get random viewport dimensions.

##### `async human_type_delay()`
Simulate human typing delay.

##### `async random_mouse_movement(page)`
Perform random mouse movements.

##### `async human_interaction_sequence(page)`
Execute realistic human interaction sequence.

##### `get_random_headers() -> Dict[str, str]`
Get randomized HTTP headers.

### PhoenixMLSParser

#### Constructor
```python
PhoenixMLSParser()
```

#### Methods

##### `parse_property(html_content: str, property_url: Optional[str] = None) -> PropertyData`
Parse property details from HTML.

**Parameters:**
- `html_content`: HTML content to parse
- `property_url`: Optional URL for resolving relative links

**Returns:**
- `PropertyData` object with extracted information

**Raises:**
- `ValueError`: If required fields are missing

##### `parse_search_results(html_content: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]`
Parse search results page for property listings.

##### `normalize_address(address: str) -> Dict[str, str]`
Normalize and parse address into components.

**Returns:**
- Dictionary with:
  - `street`: Street address
  - `city`: City name
  - `state`: State abbreviation
  - `zip`: ZIP code

**Example:**
```python
components = parser.normalize_address("123 Main St, Phoenix, AZ 85001")
# {'street': '123 Main St', 'city': 'Phoenix', 'state': 'AZ', 'zip': '85001'}
```

##### `validate_data(data: PropertyData) -> List[str]`
Validate property data and return list of issues.

##### `store_html(property_id: str, html_content: str, compress: bool = True)`
Store raw HTML for future re-parsing.

##### `batch_parse(html_list: List[tuple[str, str]]) -> List[PropertyData]`
Parse multiple HTML documents in batch.

## Configuration Options

### Scraper Configuration

```yaml
phoenix_mls:
  base_url: "https://www.phoenixmlssearch.com"
  
  # Rate limiting
  rate_limit:
    requests_per_minute: 60
  
  # Request settings
  timeout: 30  # seconds
  max_retries: 3
  
  # Session management
  cookies_path: "data/cookies"
  session_rotation_interval: 300  # seconds
  
  # Scraping limits
  max_properties_per_session: 100
```

### Proxy Configuration

```yaml
proxy_config:
  proxies:
    - host: "proxy1.example.com"
      port: 8080
      type: "http"
      username: "user1"
      password: "pass1"
    - host: "proxy2.example.com"
      port: 8080
      type: "http"
      username: "user2"
      password: "pass2"
  
  max_failures: 3
  cooldown_minutes: 5
  health_check_url: "https://httpbin.org/ip"
```

### Anti-Detection Configuration

```yaml
anti_detection:
  user_agents:
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36..."
  
  viewports:
    - [1920, 1080]
    - [1366, 768]
    - [1440, 900]
  
  typing_delay_range: [50, 200]  # milliseconds
```

## Error Handling

### Exception Types

#### `ScraperError`
Base exception for all scraper errors.

#### `PropertyNotFoundError`
Raised when a property cannot be found.

#### `RateLimitError`
Raised when rate limit is exceeded.

#### `NoHealthyProxiesError`
Raised when no healthy proxies are available.

#### `ParsingError`
Base exception for parsing errors.

#### `ValidationError`
Raised when data validation fails.

### Error Recovery Strategies

1. **Automatic Retries**: Uses exponential backoff with configurable limits
2. **Proxy Rotation**: Automatically switches proxies on failures
3. **Session Recovery**: Attempts to restore saved sessions
4. **Rate Limit Handling**: Implements exponential backoff
5. **Graceful Degradation**: Falls back to cached data when available

### Example Error Handling

```python
from phoenix_real_estate.collectors.phoenix_mls import (
    PhoenixMLSScraper,
    NoHealthyProxiesError,
    RateLimitError
)

async def scrape_with_error_handling():
    scraper = PhoenixMLSScraper(config)
    
    try:
        await scraper.initialize_browser()
        properties = await scraper.search_properties_by_zipcode("85001")
        
    except NoHealthyProxiesError:
        logger.error("All proxies are unhealthy")
        # Wait for proxy recovery
        await asyncio.sleep(300)
        
    except RateLimitError:
        logger.warning("Rate limit exceeded")
        # Handle rate limiting
        await scraper.handle_rate_limit()
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Save session for recovery
        await scraper.save_session()
        
    finally:
        await scraper.close_browser()
```

## Usage Examples

### Example 1: Basic Property Search

```python
import asyncio
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSScraper

async def search_zipcode():
    config = {
        "base_url": "https://www.phoenixmlssearch.com",
        "timeout": 30
    }
    
    scraper = PhoenixMLSScraper(config)
    await scraper.initialize_browser()
    
    try:
        # Search for properties
        properties = await scraper.search_properties_by_zipcode("85001")
        
        print(f"Found {len(properties)} properties")
        for prop in properties[:5]:  # First 5 properties
            print(f"- {prop['address']}: {prop['price']}")
            
    finally:
        await scraper.close_browser()

# Run the example
asyncio.run(search_zipcode())
```

### Example 2: Batch Processing with Session Management

```python
async def batch_scrape_with_sessions():
    config = {
        "base_url": "https://www.phoenixmlssearch.com",
        "timeout": 30,
        "cookies_path": "data/sessions"
    }
    
    scraper = PhoenixMLSScraper(config)
    
    # Load existing session
    await scraper.initialize_browser()
    if await scraper.load_session():
        print("Loaded existing session")
    
    try:
        # Get property URLs from search
        properties = await scraper.search_properties_by_zipcode("85001")
        urls = [p["url"] for p in properties[:20]]  # First 20
        
        # Batch scrape with session maintenance
        results = await scraper.scrape_properties_batch(urls)
        
        print(f"Successfully scraped {len(results)} properties")
        
        # Save session for next run
        await scraper.save_session()
        
    finally:
        await scraper.close_browser()
```

### Example 3: Advanced Configuration with Proxies

```python
async def scrape_with_proxies():
    # Main configuration
    config = {
        "base_url": "https://www.phoenixmlssearch.com",
        "max_retries": 3,
        "timeout": 30,
        "rate_limit": {
            "requests_per_minute": 30
        }
    }
    
    # Proxy configuration
    proxy_config = {
        "proxies": [
            {
                "host": "premium-datacenter.webshare.io",
                "port": 8080,
                "username": "your_username",
                "password": "your_password",
                "type": "http"
            },
            {
                "host": "premium-residential.webshare.io",
                "port": 8080,
                "username": "your_username",
                "password": "your_password",
                "type": "http"
            }
        ],
        "max_failures": 3,
        "cooldown_minutes": 5,
        "health_check_url": "https://httpbin.org/ip"
    }
    
    scraper = PhoenixMLSScraper(config, proxy_config)
    
    await scraper.initialize_browser()
    
    try:
        # Scrape with proxy rotation
        properties = await scraper.search_properties_by_zipcode("85001")
        
        for prop in properties[:10]:
            details = await scraper.scrape_property_details(prop["url"])
            print(f"Scraped: {details['address']}")
            
            # Random delay between requests
            await asyncio.sleep(random.uniform(2, 5))
        
        # Check statistics
        stats = scraper.get_statistics()
        print(f"\nScraping Statistics:")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Total Requests: {stats['total_requests']}")
        
        if 'proxy_stats' in stats:
            print(f"\nProxy Statistics:")
            print(f"Healthy Proxies: {stats['proxy_stats']['healthy_proxies']}")
            print(f"Failed Proxies: {stats['proxy_stats']['failed_proxies']}")
            
    finally:
        await scraper.close_browser()
```

### Example 4: Data Parsing and Validation

```python
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSParser

def parse_and_validate():
    parser = PhoenixMLSParser()
    
    # Example HTML content
    html_content = """
    <div class="property">
        <h1 class="address">123 Main St, Phoenix, AZ 85001</h1>
        <span class="price">$450,000</span>
        <div class="details">
            <span class="beds">4 beds</span>
            <span class="baths">2.5 baths</span>
            <span class="sqft">2,500 sqft</span>
        </div>
    </div>
    """
    
    try:
        # Parse property
        property_data = parser.parse_property(html_content)
        
        # Validate data
        errors = parser.validate_data(property_data)
        if errors:
            print("Validation errors:", errors)
        else:
            print("Property validated successfully")
            
        # Normalize address
        address_components = parser.normalize_address(property_data.address)
        print(f"Address components: {address_components}")
        
        # Convert to JSON-serializable dict
        data_dict = property_data.to_json_dict()
        print(f"Property data: {json.dumps(data_dict, indent=2)}")
        
    except ValueError as e:
        print(f"Parsing error: {e}")
```

### Example 5: Monitoring and Statistics

```python
async def monitor_scraping_performance():
    config = {
        "base_url": "https://www.phoenixmlssearch.com",
        "timeout": 30
    }
    
    scraper = PhoenixMLSScraper(config)
    await scraper.initialize_browser()
    
    try:
        # Track performance over multiple searches
        zipcodes = ["85001", "85002", "85003", "85004", "85005"]
        
        for zipcode in zipcodes:
            print(f"\nSearching zipcode: {zipcode}")
            
            start_time = time.time()
            properties = await scraper.search_properties_by_zipcode(zipcode)
            elapsed = time.time() - start_time
            
            print(f"Found {len(properties)} properties in {elapsed:.2f} seconds")
            
            # Get current statistics
            stats = scraper.get_statistics()
            print(f"Current success rate: {stats['success_rate']:.1f}%")
            
            # Check for issues
            if stats['failed_requests'] > 0:
                print(f"Warning: {stats['failed_requests']} failed requests")
            
            if stats.get('rate_limited', 0) > 0:
                print(f"Rate limited {stats['rate_limited']} times")
        
        # Final statistics
        final_stats = scraper.get_statistics()
        print(f"\nFinal Statistics:")
        print(f"Total Requests: {final_stats['total_requests']}")
        print(f"Successful: {final_stats['successful_requests']}")
        print(f"Failed: {final_stats['failed_requests']}")
        print(f"Success Rate: {final_stats['success_rate']:.1f}%")
        print(f"Properties Scraped: {final_stats['properties_scraped']}")
        
    finally:
        await scraper.close_browser()
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Browser Initialization Failures

**Symptom**: Error when initializing browser
```
Error: Browser closed unexpectedly
```

**Solutions**:
- Ensure Playwright browsers are installed: `uv run playwright install chromium`
- Check system requirements for headless Chrome
- Verify no other Chrome processes are running
- Try with `headless: false` for debugging

#### 2. Session Expiration

**Symptom**: Requests failing after period of activity

**Solutions**:
```python
# Implement session checking
if not await scraper.maintain_session():
    await scraper.clear_session()
    await scraper.initialize_browser()
    # Re-authenticate if needed
```

#### 3. Rate Limiting

**Symptom**: 429 errors or "Too many requests" messages

**Solutions**:
- Reduce `requests_per_minute` in configuration
- Implement longer delays between requests
- Use the built-in rate limiter properly
- Monitor rate limit statistics

#### 4. Proxy Failures

**Symptom**: `NoHealthyProxiesError` or connection timeouts

**Solutions**:
```python
# Check proxy health
proxy_manager = scraper.proxy_manager
health_status = await proxy_manager.check_all_health()
print(f"Proxy health: {health_status}")

# Manual proxy recovery
await proxy_manager.check_recovery()
```

#### 5. Parsing Errors

**Symptom**: Missing or incorrect data extraction

**Solutions**:
- Check if website structure has changed
- Update selectors in configuration
- Use the parser's `store_html()` to save problematic pages
- Enable debug logging for detailed parsing info

#### 6. Memory Leaks

**Symptom**: Increasing memory usage over time

**Solutions**:
```python
# Periodic cleanup
if scraper.stats['total_requests'] % 100 == 0:
    await scraper.close_browser()
    await scraper.initialize_browser()
```

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
from phoenix_real_estate.foundation.logging import get_logger

# Set debug level
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

# Enable Playwright debugging
config = {
    "browser": {
        "headless": false,
        "slowMo": 100  # Slow down operations
    }
}
```

### Performance Optimization

1. **Enable Caching**:
```python
config = {
    "caching": {
        "enabled": true,
        "cache_ttl_minutes": 60
    }
}
```

2. **Batch Operations**:
```python
# Process in batches to reduce overhead
batch_size = 10
for i in range(0, len(urls), batch_size):
    batch = urls[i:i+batch_size]
    results = await scraper.scrape_properties_batch(batch)
```

3. **Resource Limits**:
```python
config = {
    "resource_limits": {
        "max_memory_usage_mb": 512,
        "max_concurrent_pages": 3
    }
}
```

## Best Practices

### 1. Respect Website Resources
- Always implement rate limiting
- Use appropriate delays between requests
- Respect robots.txt when configured
- Monitor your impact on the website

### 2. Error Handling
- Always use try-finally blocks to ensure cleanup
- Implement proper retry logic with backoff
- Log errors for debugging
- Save session state before handling errors

### 3. Data Quality
- Validate all scraped data
- Handle missing fields gracefully
- Normalize data consistently
- Store raw HTML for re-parsing

### 4. Performance
- Use batch operations when possible
- Implement caching for repeated requests
- Monitor resource usage
- Clean up resources periodically

### 5. Security
- Store credentials securely (use environment variables)
- Sanitize all scraped data
- Use HTTPS proxies when available
- Rotate user agents and browser fingerprints

### 6. Monitoring
- Track success rates
- Monitor proxy health
- Log important events
- Set up alerts for failures

### Example Best Practices Implementation

```python
import os
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_scraper(config, proxy_config=None):
    """Context manager for proper scraper lifecycle."""
    scraper = PhoenixMLSScraper(config, proxy_config)
    
    try:
        await scraper.initialize_browser()
        yield scraper
    finally:
        # Always cleanup
        stats = scraper.get_statistics()
        logger.info(f"Scraping completed: {stats['success_rate']:.1f}% success rate")
        await scraper.close_browser()

async def production_scraping():
    """Production-ready scraping example."""
    
    # Load configuration from environment
    config = {
        "base_url": os.getenv("PHOENIX_MLS_URL", "https://www.phoenixmlssearch.com"),
        "timeout": int(os.getenv("SCRAPER_TIMEOUT", "30")),
        "rate_limit": {
            "requests_per_minute": int(os.getenv("RATE_LIMIT", "30"))
        }
    }
    
    # Proxy configuration from environment
    proxy_config = None
    if os.getenv("PROXY_ENABLED", "false").lower() == "true":
        proxy_config = {
            "proxies": [
                {
                    "host": os.getenv("PROXY_HOST"),
                    "port": int(os.getenv("PROXY_PORT")),
                    "username": os.getenv("PROXY_USER"),
                    "password": os.getenv("PROXY_PASS")
                }
            ]
        }
    
    async with managed_scraper(config, proxy_config) as scraper:
        # Load previous session
        if await scraper.load_session():
            logger.info("Restored previous session")
        
        try:
            # Scrape with monitoring
            properties = await scraper.search_properties_by_zipcode("85001")
            
            for prop in properties:
                # Check resource usage
                stats = scraper.get_statistics()
                if stats.get('rate_limited', 0) > 5:
                    logger.warning("Excessive rate limiting, slowing down")
                    await asyncio.sleep(10)
                
                # Scrape with error handling
                try:
                    details = await scraper.scrape_property_details(prop["url"])
                    # Process details...
                    
                except Exception as e:
                    logger.error(f"Failed to scrape {prop['url']}: {e}")
                    continue
                
                # Maintain session periodically
                if stats['total_requests'] % 50 == 0:
                    await scraper.maintain_session()
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            # Save state for recovery
            await scraper.save_session()
            raise
```

## Conclusion

The Phoenix MLS Scraper provides a robust, production-ready solution for collecting real estate data. By following the documentation and best practices outlined above, you can effectively use the scraper while respecting website resources and maintaining high data quality.

For additional support or to report issues, please refer to the project's issue tracker or contact the development team.