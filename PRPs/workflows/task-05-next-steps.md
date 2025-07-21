# Task 05: Phoenix MLS Scraper - Next Steps

## Implementation Status
✅ **Complete**: All core components implemented with TDD
- ProxyManager (98% coverage)
- AntiDetectionManager (100% coverage)  
- PhoenixMLSScraper (implemented)
- PhoenixMLSParser (implemented)
- Error handling framework

## Immediate Next Steps

### 1. Integration Testing (Priority: High)
```bash
# Test against actual Phoenix MLS site
uv run pytest tests/integration/phoenix_mls/ -v

# Manual verification
uv run python -m phoenix_real_estate.collectors.phoenix_mls.test_live
```

### 2. Selector Updates (Priority: High)
Current selectors are generic. Need site-specific CSS selectors:
- Search form: `input[name="search"]` → actual selector
- Property cards: `.property-card` → actual selector
- Property details: Inspect phoenixmlssearch.com HTML

### 3. Proxy Configuration (Priority: High)
```yaml
# config/proxies.yaml - add real proxies
proxies:
  - host: "actual-proxy.com"
    port: 8080
    username: "user"
    password: "pass"
    type: "http"
```

## New Requirements Discovered

### 1. Captcha Handling
- Phoenix MLS may use reCAPTCHA
- Options: 2captcha API, manual solving, proxy rotation

### 2. Session Management
```python
# Add to scraper.py
async def maintain_session(self):
    """Persist cookies across requests"""
    cookies = await self.context.cookies()
    # Store and restore cookies
```

### 3. Data Normalization
```python
# Add to parser.py
def normalize_address(self, address: str) -> Dict[str, str]:
    """Parse address into components"""
    # Extract: street, city, state, zip
    # Standardize: abbreviations, casing
```

### 4. Site-Specific Error Detection
- Rate limit responses
- Blocked IP patterns
- Session expiration

## Testing TODOs

### 1. Fix Failing Tests
```bash
# Update test fixtures
# Fix proxy_config parameter issues
# Add missing mock configurations
```

### 2. Add Integration Tests
```python
# tests/integration/phoenix_mls/test_live_scraping.py
@pytest.mark.integration
async def test_live_property_search():
    """Test against real Phoenix MLS site"""
    pass
```

### 3. Performance Validation
- Target: 1000+ properties/hour
- Measure: Rate limit compliance
- Monitor: Proxy health

### 4. Mutation Testing
```bash
# Run mutation tests
uv run mutmut run --paths-to-mutate src/phoenix_real_estate/collectors/phoenix_mls/

# View results
uv run mutmut results
```

## Deployment Preparation

### 1. Configuration
```python
# .env.production
PHOENIX_MLS_BASE_URL=https://www.phoenixmlssearch.com
PHOENIX_MLS_RATE_LIMIT=60
PHOENIX_MLS_TIMEOUT=30
```

### 2. Monitoring
- Add Prometheus metrics
- Set up alerts for failures
- Track success rates

### 3. Documentation
- API documentation
- Deployment guide
- Troubleshooting guide

## Timeline
- **Week 1**: Integration testing, selector updates
- **Week 2**: Production deployment, monitoring
- **Week 3**: Performance optimization, scaling