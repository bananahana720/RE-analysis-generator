# Task 05: Phoenix MLS Scraper - Testing Strategy

## Testing Philosophy

### Core Principles
1. **Test-Driven Development**: Write tests before implementation
2. **Comprehensive Coverage**: Target 90%+ for critical paths
3. **Real-World Scenarios**: Test actual scraping conditions
4. **Performance Validation**: Ensure scalability and efficiency
5. **Security First**: Validate all credential handling

### Testing Pyramid
```
         /\
        /E2\      End-to-End Tests (10%)
       /────\     - Full workflow validation
      /Integ.\    Integration Tests (30%)  
     /────────\   - Component interactions
    /   Unit   \  Unit Tests (60%)
   /────────────\ - Individual functions
```

## Test Suite Structure

```
tests/
├── collectors/
│   └── phoenix_mls/
│       ├── conftest.py              # Shared fixtures
│       ├── test_proxy_manager.py    # Proxy system tests
│       ├── test_anti_detection.py   # Anti-detection tests
│       ├── test_scraper.py          # Scraper engine tests
│       ├── test_adapter.py          # Data adapter tests
│       └── test_collector.py        # Collector integration
├── integration/
│   └── phoenix_mls/
│       ├── test_end_to_end.py       # Full workflow tests
│       ├── test_error_recovery.py   # Failure scenario tests
│       └── test_performance.py      # Performance benchmarks
└── smoke/
    └── test_phoenix_mls_live.py     # Production smoke tests
```

## Unit Testing Strategy

### Test Coverage Targets
- **Proxy Manager**: 95% coverage (critical component)
- **Anti-Detection**: 90% coverage (security critical)
- **Scraper Engine**: 90% coverage (core functionality)
- **Data Adapter**: 85% coverage (transformation logic)
- **Error Handlers**: 100% coverage (all paths)

### Proxy Manager Tests

```python
# tests/collectors/phoenix_mls/test_proxy_manager.py

class TestProxyManager:
    """Test suite for proxy rotation and health monitoring."""
    
    @pytest.fixture
    async def proxy_manager(self, mock_config):
        """Create proxy manager with test configuration."""
        mock_config.get_required.side_effect = lambda key: {
            "WEBSHARE_USERNAME": "test_user",
            "WEBSHARE_PASSWORD": "test_pass",
        }.get(key)
        return ProxyManager(mock_config)
    
    async def test_proxy_rotation(self, proxy_manager):
        """Test basic proxy rotation functionality."""
        # Get multiple proxies
        proxies = [await proxy_manager.get_proxy() for _ in range(5)]
        
        # Verify rotation
        assert len(set(proxies)) > 1, "Proxies should rotate"
        
        # Verify format
        for proxy in proxies:
            assert proxy.startswith("http://")
            assert "@" in proxy
            assert ":" in proxy
    
    async def test_health_monitoring(self, proxy_manager):
        """Test proxy health tracking."""
        proxy_url = await proxy_manager.get_proxy()
        
        # Report success
        await proxy_manager.report_result(proxy_url, True, 1.2)
        stats = proxy_manager.get_proxy_health_stats()
        
        assert stats["healthy_proxies"] > 0
        assert any(p["success_count"] > 0 for p in stats["proxy_details"])
    
    async def test_failed_proxy_recovery(self, proxy_manager):
        """Test automatic recovery of failed proxies."""
        # Fail all proxies
        for _ in range(10):
            proxy = await proxy_manager.get_proxy()
            await proxy_manager.report_result(proxy, False)
        
        # Trigger recovery
        with pytest.raises(DataCollectionError):
            await proxy_manager.get_proxy()
        
        # Verify recovery attempted
        stats = proxy_manager.get_proxy_health_stats()
        assert stats["testing_proxies"] > 0
    
    async def test_intelligent_selection(self, proxy_manager):
        """Test proxy selection based on performance."""
        # Setup proxies with different success rates
        proxy1 = await proxy_manager.get_proxy()
        proxy2 = await proxy_manager.get_proxy()
        
        # Make proxy1 more successful
        for _ in range(5):
            await proxy_manager.report_result(proxy1, True, 0.5)
        await proxy_manager.report_result(proxy2, False)
        
        # Verify preference for successful proxy
        selected = [await proxy_manager.get_proxy() for _ in range(10)]
        proxy1_count = selected.count(proxy1)
        
        assert proxy1_count > 5, "Should prefer successful proxy"
```

### Anti-Detection Tests

```python
# tests/collectors/phoenix_mls/test_anti_detection.py

class TestAntiDetection:
    """Test suite for anti-detection mechanisms."""
    
    @pytest.fixture
    def anti_detection(self):
        return AntiDetectionManager()
    
    async def test_user_agent_rotation(self, anti_detection):
        """Test user agent randomization."""
        agents = [anti_detection.get_random_user_agent() for _ in range(10)]
        
        # Verify variety
        assert len(set(agents)) > 3, "Should have multiple user agents"
        
        # Verify format
        for agent in agents:
            assert "Mozilla" in agent
            assert any(browser in agent for browser in ["Chrome", "Firefox", "Safari"])
    
    async def test_viewport_randomization(self, anti_detection):
        """Test viewport size randomization."""
        viewports = [anti_detection.get_random_viewport() for _ in range(10)]
        
        # Verify variety
        unique_sizes = set((v["width"], v["height"]) for v in viewports)
        assert len(unique_sizes) > 3, "Should have multiple viewport sizes"
        
        # Verify reasonable sizes
        for viewport in viewports:
            assert 1024 <= viewport["width"] <= 1920
            assert 600 <= viewport["height"] <= 1080
    
    async def test_human_like_delays(self, anti_detection):
        """Test human-like delay generation."""
        import time
        
        # Test delay timing
        start = time.time()
        await anti_detection.human_like_delay(1.0, 2.0)
        duration = time.time() - start
        
        assert 1.0 <= duration <= 2.1, "Delay should be within range"
    
    @pytest.mark.asyncio
    async def test_browser_stealth_setup(self, anti_detection, mock_page):
        """Test browser stealth configuration."""
        await anti_detection.setup_page(mock_page)
        
        # Verify stealth scripts added
        assert mock_page.add_init_script.called
        init_script = mock_page.add_init_script.call_args[0][0]
        
        # Check for key stealth elements
        assert "webdriver" in init_script
        assert "chrome" in init_script
        assert "plugins" in init_script
        
        # Verify viewport set
        assert mock_page.set_viewport_size.called
        
        # Verify timezone set
        assert mock_page.emulate_timezone.called
```

### Scraper Engine Tests

```python
# tests/collectors/phoenix_mls/test_scraper.py

class TestPhoenixMLSScraper:
    """Test suite for web scraper engine."""
    
    @pytest.fixture
    async def scraper(self, mock_config):
        return PhoenixMLSScraper(mock_config)
    
    @pytest.fixture
    def mock_html_response(self):
        """Sample HTML response for testing."""
        return """
        <div class="property-listing">
            <div class="property-address">123 Main St, Phoenix, AZ 85001</div>
            <div class="property-price">$450,000</div>
            <div class="property-details">3 beds, 2 baths, 1,850 sqft</div>
        </div>
        """
    
    async def test_search_zipcode(self, scraper, mock_browser_context):
        """Test zipcode search functionality."""
        # Setup mock response
        mock_page = mock_browser_context.new_page.return_value
        mock_page.content.return_value = self.mock_html_response()
        
        # Execute search
        async with scraper:
            properties = await scraper.search_zipcode("85001", max_pages=1)
        
        assert len(properties) > 0
        assert properties[0]["address"] == "123 Main St, Phoenix, AZ 85001"
        assert properties[0]["price"] == "$450,000"
    
    async def test_pagination_handling(self, scraper, mock_browser_context):
        """Test multi-page result handling."""
        # Mock multiple pages
        page_contents = [
            self.generate_listings_html(5),  # Page 1
            self.generate_listings_html(5),  # Page 2
            self.generate_listings_html(2),  # Page 3 (partial)
            ""  # Page 4 (empty)
        ]
        
        mock_page = mock_browser_context.new_page.return_value
        mock_page.content.side_effect = page_contents
        
        async with scraper:
            properties = await scraper.search_zipcode("85001", max_pages=5)
        
        assert len(properties) == 12  # 5 + 5 + 2
        assert mock_page.goto.call_count == 4  # Stopped at empty page
    
    async def test_error_recovery(self, scraper, mock_browser_context):
        """Test error handling and recovery."""
        mock_page = mock_browser_context.new_page.return_value
        
        # Simulate network error then success
        mock_page.goto.side_effect = [
            Exception("Network error"),
            Mock(status=200)  # Success on retry
        ]
        mock_page.content.return_value = self.mock_html_response()
        
        async with scraper:
            properties = await scraper.search_zipcode("85001", max_pages=1)
        
        assert len(properties) > 0  # Should succeed after retry
        assert mock_page.goto.call_count >= 2  # Retried
    
    async def test_dynamic_content_handling(self, scraper, mock_browser_context):
        """Test handling of dynamic JavaScript content."""
        mock_page = mock_browser_context.new_page.return_value
        
        # Simulate dynamic content loading
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        
        async with scraper:
            await scraper._scrape_search_page("85001", 1)
        
        # Verify waited for content
        mock_page.wait_for_selector.assert_called_with(
            ".property-listing", 
            timeout=10000
        )
        mock_page.wait_for_load_state.assert_called_with("domcontentloaded")
```

## Integration Testing Strategy

### End-to-End Tests

```python
# tests/integration/phoenix_mls/test_end_to_end.py

class TestPhoenixMLSEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.fixture
    async def collector(self, config, repository):
        """Create fully configured collector."""
        return PhoenixMLSCollector(config, repository, "test.phoenix_mls")
    
    async def test_complete_collection_workflow(self, collector):
        """Test full collection workflow from search to storage."""
        # Execute collection
        raw_properties = await collector.collect_zipcode("85001")
        
        assert len(raw_properties) > 0
        
        # Adapt to schema
        for raw_data in raw_properties[:5]:  # Test first 5
            property_obj = await collector.adapt_property(raw_data)
            
            # Validate schema compliance
            assert property_obj.property_id
            assert property_obj.address.zip_code == "85001"
            assert property_obj.prices[0].amount > 0
            
            # Store in repository
            await collector.repository.create(property_obj)
        
        # Verify storage
        stored = await collector.repository.find_by_zipcode("85001")
        assert len(stored) >= 5
    
    async def test_concurrent_collections(self, collector):
        """Test concurrent zipcode collections."""
        zipcodes = ["85001", "85002", "85003"]
        
        # Collect concurrently
        tasks = [collector.collect_zipcode(zc) for zc in zipcodes]
        results = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        assert all(len(r) > 0 for r in results)
        assert len(results) == 3
    
    async def test_rate_limiting_compliance(self, collector):
        """Test rate limiting under load."""
        start_time = time.time()
        
        # Rapid requests
        for _ in range(10):
            await collector.collect_zipcode("85001")
        
        duration = time.time() - start_time
        
        # Should take at least 60 seconds with rate limiting
        assert duration >= 60, "Rate limiting not enforced"
```

### Error Recovery Tests

```python
# tests/integration/phoenix_mls/test_error_recovery.py

class TestErrorRecovery:
    """Test error scenarios and recovery mechanisms."""
    
    async def test_proxy_failure_recovery(self, collector):
        """Test recovery from proxy failures."""
        # Simulate all proxies failing
        collector.scraper.proxy_manager.proxies = []
        
        with pytest.raises(DataCollectionError) as exc_info:
            await collector.collect_zipcode("85001")
        
        assert "No healthy proxies" in str(exc_info.value)
    
    async def test_parsing_error_fallback(self, collector):
        """Test fallback when parsing fails."""
        # Mock malformed HTML
        with patch.object(collector.scraper, '_extract_property_listings') as mock:
            mock.side_effect = Exception("Parsing failed")
            
            raw_properties = await collector.collect_zipcode("85001")
            
            # Should store raw HTML for LLM processing
            assert all("raw_html" in p for p in raw_properties)
            assert all(p.get("parse_error") for p in raw_properties)
    
    async def test_browser_crash_recovery(self, collector):
        """Test recovery from browser crashes."""
        # Simulate browser crash
        original_browser = collector.scraper.browser
        collector.scraper.browser = None
        
        # Should recover and continue
        properties = await collector.collect_zipcode("85001")
        assert len(properties) > 0
        assert collector.scraper.browser is not None
```

## Performance Testing Strategy

### Benchmarks

```python
# tests/integration/phoenix_mls/test_performance.py

class TestPerformance:
    """Performance and scalability tests."""
    
    async def test_response_time_targets(self, collector):
        """Test average response times meet targets."""
        times = []
        
        for _ in range(10):
            start = time.time()
            await collector.collect_zipcode("85001")
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 2.0, f"Average time {avg_time}s exceeds 2s target"
    
    async def test_memory_usage(self, collector):
        """Test memory usage under load."""
        import psutil
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Collect many properties
        for _ in range(50):
            await collector.collect_zipcode("85001")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 500, f"Memory increased by {memory_increase}MB"
    
    async def test_concurrent_performance(self, collector):
        """Test performance under concurrent load."""
        async def timed_collection(zipcode):
            start = time.time()
            result = await collector.collect_zipcode(zipcode)
            return time.time() - start, len(result)
        
        # Run concurrent collections
        zipcodes = ["85001", "85002", "85003", "85004", "85005"]
        results = await asyncio.gather(*[timed_collection(zc) for zc in zipcodes])
        
        times, counts = zip(*results)
        
        # All should complete within reasonable time
        assert all(t < 5.0 for t in times), "Concurrent requests too slow"
        assert all(c > 0 for c in counts), "All requests should return data"
```

## Security Testing

### Credential Security Tests

```python
# tests/collectors/phoenix_mls/test_security.py

class TestSecurity:
    """Security and credential handling tests."""
    
    def test_no_credentials_in_logs(self, caplog, collector):
        """Ensure credentials never appear in logs."""
        with caplog.at_level(logging.DEBUG):
            collector.logger.debug("Test message", extra={
                "proxy_url": "http://user:pass@proxy.com:8080"
            })
        
        # Check logs don't contain passwords
        log_text = caplog.text
        assert "pass" not in log_text
        assert "user:pass" not in log_text
    
    def test_credential_encryption(self, config):
        """Test credentials are encrypted in config."""
        proxy_user = config.get_required("WEBSHARE_USERNAME")
        proxy_pass = config.get_required("WEBSHARE_PASSWORD")
        
        # Should be encrypted or secured
        assert not proxy_pass.startswith("plain:")
        assert len(proxy_pass) > 20  # Encrypted values are longer
    
    async def test_sanitized_error_messages(self, collector):
        """Test error messages don't leak sensitive data."""
        # Force an error with proxy
        collector.scraper.proxy_manager._current_proxy_url = (
            "http://secret_user:secret_pass@proxy.com:8080"
        )
        
        try:
            raise DataCollectionError("Test error")
        except DataCollectionError as e:
            error_str = str(e)
            assert "secret_pass" not in error_str
            assert "secret_user" not in error_str
```

## Test Fixtures

```python
# tests/collectors/phoenix_mls/conftest.py

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock(spec=ConfigProvider)
    config.get.side_effect = lambda key, default=None: {
        "PHOENIX_MLS_BASE_URL": "https://test.phoenixmls.com",
        "PHOENIX_MLS_MAX_RETRIES": 3,
        "PHOENIX_MLS_TIMEOUT": 5000,
        "PROXY_HEALTH_CHECK_INTERVAL": 60,
    }.get(key, default)
    return config

@pytest.fixture
async def mock_browser_context():
    """Mock Playwright browser context."""
    context = AsyncMock()
    page = AsyncMock()
    
    # Setup page mock
    page.goto.return_value = Mock(status=200)
    page.content.return_value = "<html>test</html>"
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    
    context.new_page.return_value = page
    return context

@pytest.fixture
def sample_property_html():
    """Sample property HTML for testing."""
    return """
    <div class="property-listing">
        <h3 class="property-address">123 Test Ave, Phoenix, AZ 85001</h3>
        <span class="property-price">$350,000</span>
        <div class="property-details">
            <span class="beds">3 beds</span>
            <span class="baths">2 baths</span>
            <span class="sqft">1,500 sqft</span>
        </div>
    </div>
    """
```

## Continuous Integration

### CI Pipeline Configuration

```yaml
# .github/workflows/phoenix-mls-tests.yml

name: Phoenix MLS Scraper Tests

on:
  push:
    paths:
      - 'src/phoenix_real_estate/collectors/phoenix_mls/**'
      - 'tests/collectors/phoenix_mls/**'
      - 'tests/integration/phoenix_mls/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        pip install uv
        uv sync --extra dev
        playwright install chromium
    
    - name: Run unit tests
      run: |
        uv run pytest tests/collectors/phoenix_mls/ -v --cov=phoenix_real_estate.collectors.phoenix_mls --cov-report=xml
    
    - name: Run integration tests
      run: |
        uv run pytest tests/integration/phoenix_mls/ -v
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: phoenix-mls
    
    - name: Check coverage threshold
      run: |
        coverage report --fail-under=90
```

## Test Execution Strategy

### Local Development
```bash
# Run all Phoenix MLS tests
uv run pytest tests/collectors/phoenix_mls/ tests/integration/phoenix_mls/ -v

# Run with coverage
uv run pytest tests/collectors/phoenix_mls/ --cov=phoenix_real_estate.collectors.phoenix_mls --cov-report=html

# Run specific test file
uv run pytest tests/collectors/phoenix_mls/test_scraper.py -v

# Run tests matching pattern
uv run pytest -k "proxy" -v
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: phoenix-mls-tests
        name: Phoenix MLS Tests
        entry: uv run pytest tests/collectors/phoenix_mls/
        language: system
        files: ^src/phoenix_real_estate/collectors/phoenix_mls/
        pass_filenames: false
```

### Performance Testing
```bash
# Run performance benchmarks
uv run pytest tests/integration/phoenix_mls/test_performance.py -v --benchmark-only

# Generate performance report
uv run pytest tests/integration/phoenix_mls/test_performance.py --benchmark-autosave --benchmark-compare
```

## Quality Gates

### Definition of Done
- [ ] All unit tests passing (90%+ coverage)
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] Security tests passing
- [ ] No critical linting issues
- [ ] Documentation updated
- [ ] Code review approved
- [ ] CI pipeline green