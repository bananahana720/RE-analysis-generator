# Task 05: Phoenix MLS Web Scraper - TDD Master Workflow

## Overview
This document provides the test-driven development (TDD) master workflow for implementing the Phoenix MLS web scraper with anti-detection capabilities, proxy management, and Epic 1 foundation integration.

**Task ID**: TASK-05  
**Epic**: Epic 2 - Data Collection Infrastructure  
**Priority**: High  
**Estimated Duration**: 4-5 days (increased for TDD)  
**Dependencies**: Epic 1 Foundation (Complete)  
**Methodology**: Test-Driven Development (TDD)

## TDD Workflow Summary

### Phase Distribution
```
Day 1: TDD Foundation & Infrastructure (35% - Tests first, then Proxy/Anti-Detection)
Day 2: TDD Core Implementation (35% - Tests first, then Scraper/Parser)  
Day 3: TDD Integration & Enhancement (20% - Integration tests, then connections)
Day 4-5: TDD Validation & Launch (10% - End-to-end tests, then deployment)
```

### TDD Cycle Time Allocation
- **Red Phase (Write failing tests)**: 40% of development time
- **Green Phase (Make tests pass)**: 35% of development time
- **Refactor Phase (Improve code)**: 25% of development time

### Team Requirements
- **Primary**: 1 Senior Backend Developer (Python, Web Scraping, TDD Expert)
- **Secondary**: 1 QA Engineer (Day 2-5, TDD Pairing)
- **Optional**: 1 Security Engineer (Day 4-5)

## Phase 1: TDD Foundation & Infrastructure (Day 1)

### 1.1 Project Setup with Test Structure (1 hour)
**Owner**: Backend Developer  
**Type**: Sequential  
**TDD Focus**: Test environment setup

```bash
# Create test-first directory structure
mkdir -p tests/unit/collectors/phoenix_mls
mkdir -p tests/integration/phoenix_mls
mkdir -p tests/fixtures/phoenix_mls
mkdir -p src/phoenix_real_estate/collectors/phoenix_mls

# Create test configuration
cat > tests/conftest.py << 'EOF'
"""Test configuration for Phoenix MLS scraper."""
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_browser():
    """Mock Playwright browser for testing."""
    with patch('playwright.async_api.async_playwright') as mock:
        yield mock

@pytest.fixture
def sample_html():
    """Load sample HTML fixtures."""
    # Implementation to follow
    pass
EOF

# Update dependencies for TDD
# Add to pyproject.toml:
# pytest-asyncio = "^0.23.0"
# pytest-mock = "^3.12.0"
# pytest-cov = "^4.1.0"
# playwright = "^1.41.0"
# beautifulsoup4 = "^4.12.3"

# Install dependencies
uv sync --extra dev
playwright install chromium
```

**TDD Deliverables**:
- [ ] Test directory structure created
- [ ] Test fixtures prepared
- [ ] Test configuration complete
- [ ] Coverage reporting enabled

### 1.2 TDD Proxy Management System (4 hours)
**Owner**: Backend Developer  
**Type**: Critical Path  
**TDD Cycle**: Red → Green → Refactor

#### Red Phase: Write Failing Tests (1.5 hours)
```python
# tests/unit/collectors/phoenix_mls/test_proxy_manager.py
import pytest
from src.phoenix_real_estate.collectors.phoenix_mls.proxy_manager import (
    ProxyStatus, ProxyInfo, ProxyManager
)

class TestProxyManager:
    """Test-driven proxy management system."""
    
    def test_proxy_info_initialization(self):
        """Test ProxyInfo dataclass creation."""
        proxy = ProxyInfo(
            url="http://proxy.example.com:8080",
            username="user",
            password="pass"
        )
        assert proxy.url == "http://proxy.example.com:8080"
        assert proxy.success_rate == 1.0
        assert proxy.status == ProxyStatus.HEALTHY
    
    def test_proxy_rotation(self):
        """Test proxy rotation logic."""
        manager = ProxyManager(proxies=[
            ProxyInfo("http://p1.com", "u1", "p1"),
            ProxyInfo("http://p2.com", "u2", "p2")
        ])
        
        proxy1 = manager.get_next_proxy()
        proxy2 = manager.get_next_proxy()
        assert proxy1 != proxy2
    
    @pytest.mark.asyncio
    async def test_proxy_health_monitoring(self):
        """Test proxy health monitoring."""
        manager = ProxyManager()
        proxy = ProxyInfo("http://test.com", "u", "p")
        
        # Mark proxy as failed
        await manager.mark_proxy_failed(proxy)
        assert proxy.status == ProxyStatus.UNHEALTHY
        
        # Test recovery
        await manager.check_proxy_health(proxy)
        # Should attempt recovery
```

#### Green Phase: Implement to Pass Tests (1.5 hours)
```python
# src/phoenix_real_estate/collectors/phoenix_mls/proxy_manager.py
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
import asyncio

class ProxyStatus(Enum):
    """Proxy health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"

@dataclass
class ProxyInfo:
    """Proxy information with metrics."""
    url: str
    username: str
    password: str
    status: ProxyStatus = ProxyStatus.HEALTHY
    success_rate: float = 1.0
    total_requests: int = 0
    failed_requests: int = 0
    
class ProxyManager:
    """Manage proxy rotation and health."""
    # Implementation driven by tests
```

#### Refactor Phase: Improve Design (1 hour)
- Extract common patterns
- Improve error handling
- Add comprehensive logging
- Optimize performance

**TDD Validation Points**:
- [ ] All proxy tests pass
- [ ] 100% test coverage for proxy module
- [ ] No untested code paths
- [ ] Clear test documentation

### 1.3 TDD Anti-Detection Framework (4 hours)
**Owner**: Backend Developer  
**Type**: Critical Path  
**TDD Cycle**: Red → Green → Refactor

#### Red Phase: Anti-Detection Tests (1.5 hours)
```python
# tests/unit/collectors/phoenix_mls/test_anti_detection.py
import pytest
from src.phoenix_real_estate.collectors.phoenix_mls.anti_detection import (
    AntiDetectionManager, BrowserConfig
)

class TestAntiDetection:
    """Test-driven anti-detection system."""
    
    def test_user_agent_rotation(self):
        """Test user agent randomization."""
        manager = AntiDetectionManager()
        agents = set()
        
        for _ in range(10):
            agent = manager.get_random_user_agent()
            agents.add(agent)
        
        assert len(agents) > 5  # Should have variety
    
    def test_viewport_randomization(self):
        """Test viewport size randomization."""
        manager = AntiDetectionManager()
        viewport = manager.get_random_viewport()
        
        assert 1024 <= viewport['width'] <= 1920
        assert 768 <= viewport['height'] <= 1080
    
    @pytest.mark.asyncio
    async def test_human_behavior_simulation(self):
        """Test human-like behavior patterns."""
        manager = AntiDetectionManager()
        
        # Test mouse movement
        movements = await manager.generate_mouse_movements(
            start=(0, 0), end=(100, 100)
        )
        assert len(movements) > 2  # Not direct line
        
        # Test typing patterns
        delay = manager.get_typing_delay()
        assert 50 <= delay <= 200  # Human-like delays
```

## Phase 2: TDD Core Implementation (Day 2)

### 2.1 TDD Web Scraper Engine (5 hours)
**Owner**: Backend Developer  
**Type**: Critical Path  
**TDD Cycle**: Red → Green → Refactor

#### Red Phase: Scraper Tests (2 hours)
```python
# tests/unit/collectors/phoenix_mls/test_scraper.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper

class TestPhoenixMLSScraper:
    """Test-driven scraper implementation."""
    
    @pytest.fixture
    def mock_page(self):
        """Mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        return page
    
    @pytest.mark.asyncio
    async def test_search_zipcode(self, mock_page):
        """Test zipcode search functionality."""
        scraper = PhoenixMLSScraper(
            proxy_manager=Mock(),
            anti_detection=Mock()
        )
        scraper.page = mock_page
        
        results = await scraper.search_zipcode("85031")
        
        assert mock_page.goto.called
        assert "85031" in mock_page.goto.call_args[0][0]
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_property_detail_extraction(self, mock_page, sample_html):
        """Test property detail extraction."""
        scraper = PhoenixMLSScraper()
        mock_page.content.return_value = sample_html
        
        details = await scraper.get_property_details(
            "https://example.com/property/123"
        )
        
        assert details['address'] is not None
        assert details['price'] is not None
        assert 'raw_html' in details
```

#### Green Phase: Implement Scraper (2 hours)
```python
# src/phoenix_real_estate/collectors/phoenix_mls/scraper.py
from typing import List, Dict, Any
import asyncio
from playwright.async_api import async_playwright, Page

class PhoenixMLSScraper:
    """Phoenix MLS web scraper with anti-detection."""
    
    def __init__(self, proxy_manager, anti_detection):
        self.proxy_manager = proxy_manager
        self.anti_detection = anti_detection
        self.page: Optional[Page] = None
    
    async def search_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Search properties by zipcode."""
        # Implementation driven by tests
        pass
    
    async def get_property_details(self, url: str) -> Dict[str, Any]:
        """Extract property details."""
        # Implementation driven by tests
        pass
```

#### Refactor Phase: Optimize Scraper (1 hour)
- Extract reusable components
- Improve error recovery
- Add retry logic
- Optimize selectors

### 2.2 TDD Data Extraction Logic (3 hours)
**Owner**: Backend Developer  
**Type**: Parallel  
**TDD Cycle**: Red → Green → Refactor

#### Red Phase: Parser Tests (1.2 hours)
```python
# tests/unit/collectors/phoenix_mls/test_parser.py
import pytest
from bs4 import BeautifulSoup
from src.phoenix_real_estate.collectors.phoenix_mls.parser import PropertyParser

class TestPropertyParser:
    """Test-driven parser implementation."""
    
    @pytest.fixture
    def sample_listing_html(self):
        """Sample property listing HTML."""
        return """
        <div class="property-card">
            <h3 class="address">123 Main St, Phoenix, AZ 85031</h3>
            <span class="price">$450,000</span>
            <div class="features">
                <span class="beds">3 beds</span>
                <span class="baths">2 baths</span>
                <span class="sqft">1,850 sqft</span>
            </div>
        </div>
        """
    
    def test_extract_address(self, sample_listing_html):
        """Test address extraction."""
        parser = PropertyParser()
        soup = BeautifulSoup(sample_listing_html, 'html.parser')
        
        address = parser.extract_address(soup)
        assert address == "123 Main St, Phoenix, AZ 85031"
    
    def test_extract_price(self, sample_listing_html):
        """Test price extraction."""
        parser = PropertyParser()
        soup = BeautifulSoup(sample_listing_html, 'html.parser')
        
        price = parser.extract_price(soup)
        assert price == "$450,000"
    
    def test_fallback_extraction(self):
        """Test fallback when selectors fail."""
        parser = PropertyParser()
        broken_html = "<div>Incomplete data</div>"
        soup = BeautifulSoup(broken_html, 'html.parser')
        
        result = parser.extract_property_data(soup)
        assert result['extraction_method'] == 'fallback'
        assert result['raw_html'] is not None
```

### 2.3 TDD Error Handling & Recovery (2 hours)
**Owner**: Backend Developer  
**Type**: Sequential  
**TDD Cycle**: Red → Green → Refactor

#### Red Phase: Error Handling Tests (45 minutes)
```python
# tests/unit/collectors/phoenix_mls/test_error_handling.py
import pytest
from src.phoenix_real_estate.collectors.phoenix_mls.exceptions import (
    ScraperException, RateLimitException, ParseException
)

class TestErrorHandling:
    """Test-driven error handling."""
    
    @pytest.mark.asyncio
    async def test_network_error_recovery(self, scraper):
        """Test network error recovery."""
        scraper.page.goto.side_effect = Exception("Network error")
        
        with pytest.raises(ScraperException) as exc_info:
            await scraper.search_zipcode("85031")
        
        assert exc_info.value.retry_count == 3
        assert exc_info.value.recovery_attempted
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, scraper):
        """Test rate limit detection and handling."""
        scraper.page.content.return_value = "Too many requests"
        
        with pytest.raises(RateLimitException):
            await scraper.search_zipcode("85031")
        
        # Should switch proxy
        assert scraper.proxy_manager.switch_proxy.called
```

## Phase 3: TDD Integration & Enhancement (Day 3)

### 3.1 TDD PhoenixMLS Collector Integration (4 hours)
**Owner**: Backend Developer  
**Type**: Critical Path  
**TDD Cycle**: Red → Green → Refactor

#### Red Phase: Integration Tests (1.5 hours)
```python
# tests/integration/phoenix_mls/test_collector.py
import pytest
from src.phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector
from src.phoenix_real_estate.foundation.models import Property

class TestPhoenixMLSCollector:
    """Test-driven collector integration."""
    
    @pytest.mark.asyncio
    async def test_collect_zipcode_integration(self, config, repository):
        """Test full collection workflow."""
        collector = PhoenixMLSCollector(config, repository)
        
        properties = await collector.collect_zipcode("85031")
        
        assert len(properties) > 0
        assert all(isinstance(p, Property) for p in properties)
        assert all(p.source == "phoenix_mls" for p in properties)
    
    @pytest.mark.asyncio
    async def test_data_persistence(self, collector, repository):
        """Test data is properly persisted."""
        await collector.collect_zipcode("85031")
        
        # Verify data in repository
        saved = await repository.find_by_zipcode("85031")
        assert len(saved) > 0
```

### 3.2 TDD Test Suite Enhancement (3 hours)
**Owner**: Backend Developer / QA  
**Type**: Parallel  
**TDD Focus**: Meta-testing

#### Test Coverage Requirements
```yaml
coverage:
  unit_tests:
    target: 100%  # TDD mandates full coverage
    enforcement: strict
    
  integration_tests:
    target: 95%
    scenarios:
      - happy_path
      - error_recovery
      - edge_cases
      
  performance_tests:
    target: All critical paths
    benchmarks:
      - response_time < 2s
      - memory_usage < 500MB
      
  security_tests:
    target: All credential handling
    validation:
      - no_plaintext_secrets
      - secure_proxy_auth
```

### 3.3 TDD Documentation (2 hours)
**Owner**: Backend Developer  
**Type**: Parallel  
**TDD Focus**: Test-driven documentation

Documentation Requirements:
- Test examples as primary documentation
- TDD workflow guide
- Test coverage reports
- Performance benchmarks from tests

## Phase 4-5: TDD Validation & Launch (Day 4-5)

### 4.1 TDD Security Validation (3 hours)
**Owner**: Security Engineer / Backend Developer  
**Type**: Gate  
**TDD Cycle**: Security tests first

#### Red Phase: Security Tests (1.5 hours)
```python
# tests/security/test_phoenix_mls_security.py
import pytest
from src.phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector

class TestSecurityCompliance:
    """Test-driven security validation."""
    
    def test_no_credential_exposure(self, collector):
        """Test credentials are never exposed."""
        # Test logs don't contain credentials
        # Test error messages sanitize secrets
        # Test debug output is safe
        pass
    
    def test_proxy_auth_encryption(self, config):
        """Test proxy authentication is encrypted."""
        # Verify credentials are encrypted at rest
        # Verify secure transmission
        pass
```

### 4.2 TDD Production Readiness (3 hours)
**Owner**: DevOps / Backend Developer  
**Type**: Sequential  
**TDD Focus**: Operational tests

#### Red Phase: Production Tests (1.5 hours)
```python
# tests/production/test_readiness.py
import pytest

class TestProductionReadiness:
    """Test-driven production validation."""
    
    @pytest.mark.performance
    def test_throughput_requirements(self, collector):
        """Test meets throughput requirements."""
        # Must process 1000+ properties/hour
        pass
    
    @pytest.mark.reliability
    def test_error_recovery(self, collector):
        """Test graceful error recovery."""
        # Must recover from all error types
        pass
```

### 4.3 TDD Launch & Monitoring (2 hours)
**Owner**: Team Lead  
**Type**: Sequential  
**TDD Focus**: Live validation tests

Launch Protocol with TDD:
1. Run full test suite in production environment
2. Deploy with feature flags (test in prod)
3. Run smoke tests continuously
4. Monitor test metrics (not just app metrics)
5. Validate against test expectations

## TDD Risk Management

### TDD-Specific Risks
1. **Test Maintenance Overhead** (Medium)
   - Mitigation: Keep tests simple and focused
   - Contingency: Refactor test suite regularly

2. **False Confidence** (Low)
   - Mitigation: Integration and E2E tests
   - Contingency: Manual exploratory testing

3. **Development Speed** (Medium)
   - Mitigation: TDD expertise and pairing
   - Contingency: Selective TDD for critical paths

## TDD Success Metrics

### TDD Compliance KPIs
- Test-First Rate: 100% (all code has tests written first)
- Test Coverage: 100% (no untested code)
- Test Quality: All tests meaningful (no trivial tests)
- Refactor Frequency: ≥1 per feature

### Technical KPIs (Enhanced with TDD)
- Test Suite Runtime: <5 minutes
- Test Reliability: 100% (no flaky tests)
- Mutation Score: >80% (test effectiveness)
- Code Quality: Measurable improvements

### Business KPIs (Validated by Tests)
- Data Accuracy: ≥98% (validated by tests)
- Compliance: 100% (security tests pass)
- Throughput: 1000+ properties/hour (perf tests)
- Reliability: 99.9% uptime (proven by tests)

## TDD Integration Points

### Epic 1 Foundation with TDD
```python
# Test-driven integration
def test_epic1_integration():
    """Test Epic 1 foundation components."""
    config = ConfigProvider()  # Mocked for tests
    repository = PropertyRepository()  # Test double
    logger = get_logger()  # Test logger
    
    # Verify integration points
```

### Epic 3 Orchestration with TDD
```python
# Test orchestration integration
@pytest.mark.asyncio
async def test_orchestration_integration():
    """Test collector works with orchestrator."""
    collector = PhoenixMLSCollector(test_config)
    orchestrator = Orchestrator([collector])
    
    await orchestrator.run_collection("85031")
    # Assert results
```

## TDD Workflow Management

### Daily TDD Standups
- Day 1: Red/Green/Refactor cycles for foundation
- Day 2: Core feature tests and implementation
- Day 3: Integration test progress
- Day 4: Security and performance test results
- Day 5: Production test validation

### TDD Quality Gates
- [ ] Day 1: All foundation tests green
- [ ] Day 2: Core feature tests passing
- [ ] Day 3: Integration tests complete
- [ ] Day 4: Security tests validated
- [ ] Day 5: Production tests verified

### TDD-Specific Checklist
- [ ] No code without failing test first
- [ ] All tests pass before commit
- [ ] Refactoring after each green phase
- [ ] Test documentation maintained
- [ ] Coverage reports reviewed
- [ ] Performance benchmarks met
- [ ] Security tests comprehensive

### TDD Escalation Path
1. Test failures → Pair programming session
2. Coverage gaps → Team review
3. Performance issues → Architecture review
4. Security failures → Security team consultation