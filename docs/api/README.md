# Phoenix Real Estate API Documentation

This directory contains comprehensive API documentation for the Phoenix Real Estate data collection system.

## Available Documentation

### Phoenix MLS Scraper
- **[Full API Documentation](phoenix-mls-scraper-api.md)** - Complete API reference with detailed explanations, configuration options, and usage examples
- **[Quick Reference Guide](phoenix-mls-quick-reference.md)** - Condensed reference for common operations and patterns

## Overview

The Phoenix Real Estate system provides automated data collection from multiple sources:

### 1. Phoenix MLS Scraper (`phoenix_mls/`)
Web scraping system for PhoenixMLSSearch.com with advanced features:
- Browser automation using Playwright
- Anti-detection measures
- Proxy management and rotation
- Session persistence
- Rate limiting
- Comprehensive error handling

### 2. Maricopa County API Collector
Direct API integration for official county records (documentation coming soon)

## Quick Links

### Getting Started
```python
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSScraper

# Basic setup
config = {"base_url": "https://www.phoenixmlssearch.com"}
scraper = PhoenixMLSScraper(config)

# Search properties
async with scraper:
    properties = await scraper.search_properties_by_zipcode("85001")
```

### Key Features
- **Robust Data Collection** - Handle failures gracefully with retry logic
- **Anti-Detection** - Avoid blocking with human-like behavior
- **Session Management** - Maintain authentication across requests
- **Proxy Support** - Rotate through multiple proxies
- **Data Validation** - Ensure data quality and consistency

### Documentation Structure
```
docs/api/
├── README.md                        # This file
├── phoenix-mls-scraper-api.md      # Full API documentation
└── phoenix-mls-quick-reference.md  # Quick reference guide
```

## Contributing

When adding new collectors or features:
1. Document all public methods with docstrings
2. Include usage examples in the documentation
3. Update the quick reference guide
4. Add configuration examples

## Support

For issues or questions:
- Check the troubleshooting section in the full documentation
- Review the usage examples
- Examine the error handling patterns