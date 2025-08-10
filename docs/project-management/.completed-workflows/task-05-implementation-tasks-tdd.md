# Task 05: Phoenix MLS Scraper - Implementation Tasks (TDD Version)

## TDD Implementation Philosophy

### Red-Green-Refactor Cycle
1. **Red Phase**: Write failing tests that define expected behavior
2. **Green Phase**: Write minimal code to make tests pass
3. **Refactor Phase**: Improve code quality while maintaining passing tests

### Time Allocation Updates
- Each task now includes 30-40% time for test development
- Tests must be written and failing before implementation begins
- Refactoring time is explicitly allocated

---

## Task Breakdown & Assignments

### Day 1: Foundation & Infrastructure

#### TASK-05-001: Project Structure Setup
**Assignee**: Backend Developer  
**Duration**: 1.5 hours (was 1 hour)  
**Priority**: P0 - Blocker  
**Dependencies**: None

**TDD Process**:

1. **Red Phase (30 min)**: Write failing import tests
```python
# tests/collectors/phoenix_mls/test_imports.py
def test_module_imports():
    """Test all modules can be imported."""
    # These will fail initially
    from phoenix_real_estate.collectors.phoenix_mls import ProxyManager
    from phoenix_real_estate.collectors.phoenix_mls import AntiDetectionManager
    from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSScraper
    from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector
    from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSAdapter
    
    assert ProxyManager is not None
    assert AntiDetectionManager is not None
```

2. **Green Phase (45 min)**: Create structure and basic modules
```bash
# Commands to execute
mkdir -p src/phoenix_real_estate/collectors/phoenix_mls
mkdir -p tests/collectors/phoenix_mls
mkdir -p tests/integration/phoenix_mls

# Create module files with minimal implementation
touch src/phoenix_real_estate/collectors/phoenix_mls/__init__.py

# Add to __init__.py to make imports pass
echo "class ProxyManager: pass" >> src/phoenix_real_estate/collectors/phoenix_mls/__init__.py
```

3. **Refactor Phase (15 min)**: Organize imports properly
```python
# src/phoenix_real_estate/collectors/phoenix_mls/__init__.py
from .proxy_manager import ProxyManager
from .anti_detection import AntiDetectionManager
from .scraper import PhoenixMLSScraper
from .collector import PhoenixMLSCollector
from .adapter import PhoenixMLSAdapter

__all__ = [
    "ProxyManager",
    "AntiDetectionManager", 
    "PhoenixMLSScraper",
    "PhoenixMLSCollector",
    "PhoenixMLSAdapter"
]
```

**Acceptance Criteria**:
- [ ] Import tests written and initially failing
- [ ] All directories created
- [ ] Import tests passing
- [ ] Dependencies installed successfully
- [ ] Module structure properly organized

---

#### TASK-05-002: Proxy Manager Implementation
**Assignee**: Backend Developer  
**Duration**: 4 hours (was 3 hours)  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-05-001

**TDD Process**:

1. **Red Phase (1 hour)**: Write comprehensive proxy manager tests
```python
# tests/collectors/phoenix_mls/test_proxy_manager.py
import pytest
from unittest.mock import Mock, AsyncMock
from phoenix_real_estate.collectors.phoenix_mls import ProxyManager
from phoenix_real_estate.foundation.exceptions import DataCollectionError

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
        # This will fail initially
        proxies = [await proxy_manager.get_proxy() for _ in range(5)]
        
        assert len(set(proxies)) > 1, "Proxies should rotate"
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
```

2. **Green Phase (2 hours)**: Implement minimal proxy manager
```python
# src/phoenix_real_estate/collectors/phoenix_mls/proxy_manager.py
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random
import asyncio
from datetime import datetime, timedelta

from phoenix_real_estate.foundation.config import ConfigProvider
from phoenix_real_estate.foundation.exceptions import DataCollectionError

class ProxyStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILED = "failed"
    TESTING = "testing"

@dataclass
class ProxyInfo:
    host: str
    port: int
    username: str
    password: str
    status: ProxyStatus = ProxyStatus.TESTING
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    average_response_time: float = 0.0
    
    @property
    def url(self) -> str:
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

class ProxyManager:
    def __init__(self, config: ConfigProvider):
        self.config = config
        self.proxies: List[ProxyInfo] = []
        self._initialize_proxies()
    
    def _initialize_proxies(self):
        """Initialize proxy pool from config."""
        # Minimal implementation to pass tests
        username = self.config.get_required("WEBSHARE_USERNAME")
        password = self.config.get_required("WEBSHARE_PASSWORD")
        
        # Create test proxies
        for i in range(5):
            self.proxies.append(ProxyInfo(
                host=f"proxy{i}.webshare.io",
                port=8080 + i,
                username=username,
                password=password
            ))
    
    async def get_proxy(self) -> str:
        """Get next available proxy."""
        if not self.proxies:
            raise DataCollectionError("No proxies available")
        
        # Simple rotation for now
        proxy = random.choice(self.proxies)
        proxy.last_used = datetime.now()
        return proxy.url
    
    async def report_result(self, proxy_url: str, success: bool, response_time: float = 0):
        """Report proxy result."""
        # Find proxy by URL
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                if success:
                    proxy.success_count += 1
                    proxy.status = ProxyStatus.HEALTHY
                else:
                    proxy.failure_count += 1
                    if proxy.failure_count > 3:
                        proxy.status = ProxyStatus.FAILED
                break
    
    def get_proxy_health_stats(self) -> Dict:
        """Get proxy health statistics."""
        healthy = sum(1 for p in self.proxies if p.status == ProxyStatus.HEALTHY)
        return {
            "healthy_proxies": healthy,
            "proxy_details": [
                {"url": p.url, "success_count": p.success_count}
                for p in self.proxies
            ]
        }
```

3. **Refactor Phase (1 hour)**: Add intelligent selection and recovery
```python
# Add to ProxyManager class
async def get_proxy(self) -> str:
    """Get next available proxy with intelligent selection."""
    healthy_proxies = [p for p in self.proxies if p.status in [ProxyStatus.HEALTHY, ProxyStatus.TESTING]]
    
    if not healthy_proxies:
        await self._trigger_recovery()
        raise DataCollectionError("No healthy proxies available")
    
    # Prefer proxies with better success rates
    healthy_proxies.sort(key=lambda p: p.success_rate, reverse=True)
    
    # Add some randomization to top performers
    selection_pool = healthy_proxies[:3] if len(healthy_proxies) >= 3 else healthy_proxies
    proxy = random.choice(selection_pool)
    
    proxy.last_used = datetime.now()
    return proxy.url

async def _trigger_recovery(self):
    """Attempt to recover failed proxies."""
    for proxy in self.proxies:
        if proxy.status == ProxyStatus.FAILED:
            proxy.status = ProxyStatus.TESTING
            proxy.failure_count = 0
```

**Test-First Checkpoints**:
- [ ] All tests written before implementation
- [ ] Tests fail initially (Red)
- [ ] Minimal implementation makes tests pass (Green)
- [ ] Code refactored for quality (Refactor)
- [ ] All tests still passing after refactor

---

#### TASK-05-003: Anti-Detection System
**Assignee**: Backend Developer  
**Duration**: 4 hours (was 3 hours)  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-05-001

**TDD Process**:

1. **Red Phase (1 hour)**: Write anti-detection tests
```python
# tests/collectors/phoenix_mls/test_anti_detection.py
import pytest
from unittest.mock import Mock, AsyncMock
import time
from phoenix_real_estate.collectors.phoenix_mls import AntiDetectionManager

class TestAntiDetection:
    """Test suite for anti-detection mechanisms."""
    
    @pytest.fixture
    def anti_detection(self):
        return AntiDetectionManager()
    
    async def test_user_agent_rotation(self, anti_detection):
        """Test user agent randomization."""
        agents = [anti_detection.get_random_user_agent() for _ in range(10)]
        
        # These assertions will fail initially
        assert len(set(agents)) > 3, "Should have multiple user agents"
        for agent in agents:
            assert "Mozilla" in agent
            assert any(browser in agent for browser in ["Chrome", "Firefox", "Safari"])
    
    async def test_viewport_randomization(self, anti_detection):
        """Test viewport size randomization."""
        viewports = [anti_detection.get_random_viewport() for _ in range(10)]
        
        unique_sizes = set((v["width"], v["height"]) for v in viewports)
        assert len(unique_sizes) > 3, "Should have multiple viewport sizes"
        
        for viewport in viewports:
            assert 1024 <= viewport["width"] <= 1920
            assert 600 <= viewport["height"] <= 1080
    
    async def test_human_like_delays(self, anti_detection):
        """Test human-like delay generation."""
        start = time.time()
        await anti_detection.human_like_delay(1.0, 2.0)
        duration = time.time() - start
        
        assert 1.0 <= duration <= 2.1, "Delay should be within range"
    
    @pytest.mark.asyncio
    async def test_browser_stealth_setup(self, anti_detection):
        """Test browser stealth configuration."""
        mock_page = AsyncMock()
        await anti_detection.setup_page(mock_page)
        
        # Verify stealth scripts added
        assert mock_page.add_init_script.called
        init_script = mock_page.add_init_script.call_args[0][0]
        
        assert "webdriver" in init_script
        assert "chrome" in init_script
        assert "plugins" in init_script
```

2. **Green Phase (2 hours)**: Implement anti-detection manager
```python
# src/phoenix_real_estate/collectors/phoenix_mls/anti_detection.py
import random
import asyncio
from typing import Dict, List

class AntiDetectionManager:
    """Manages anti-detection techniques for web scraping."""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]
        
        self.viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
            {"width": 1280, "height": 720}
        ]
        
        self.timezones = [
            "America/Phoenix",
            "America/Los_Angeles", 
            "America/Denver",
            "America/Chicago"
        ]
    
    def get_random_user_agent(self) -> str:
        """Get random user agent string."""
        return random.choice(self.user_agents)
    
    def get_random_viewport(self) -> Dict[str, int]:
        """Get random viewport dimensions."""
        return random.choice(self.viewports)
    
    async def human_like_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        """Generate human-like delay."""
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)
    
    async def setup_page(self, page):
        """Apply stealth configurations to page."""
        # Add stealth script
        await page.add_init_script("""
            // Override webdriver detection
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # Set viewport
        viewport = self.get_random_viewport()
        await page.set_viewport_size(**viewport)
        
        # Set timezone
        timezone = random.choice(self.timezones)
        await page.emulate_timezone(timezone)
```

3. **Refactor Phase (1 hour)**: Add advanced techniques
```python
# Add to AntiDetectionManager class
async def human_like_mouse_movement(self, page, element):
    """Simulate human-like mouse movement."""
    # Get element position
    box = await element.bounding_box()
    if not box:
        return
    
    # Calculate target with slight randomization
    target_x = box['x'] + box['width'] / 2 + random.uniform(-5, 5)
    target_y = box['y'] + box['height'] / 2 + random.uniform(-5, 5)
    
    # Move in steps to simulate human movement
    steps = random.randint(3, 7)
    for i in range(steps):
        progress = (i + 1) / steps
        # Add curve to movement
        curve_factor = 1 - (2 * progress - 1) ** 2
        
        x = box['x'] + (target_x - box['x']) * progress
        y = box['y'] + (target_y - box['y']) * progress + curve_factor * 20
        
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.03))
    
    await page.mouse.click(target_x, target_y)

async def human_like_typing(self, page, selector: str, text: str):
    """Type text with human-like patterns."""
    element = await page.wait_for_selector(selector)
    await element.click()
    
    for char in text:
        await page.keyboard.type(char)
        # Variable typing speed
        delay = random.uniform(0.05, 0.15)
        if char == ' ':
            delay *= 1.5  # Slower on spaces
        await asyncio.sleep(delay)
```

**Test-First Checkpoints**:
- [ ] Anti-detection tests written first
- [ ] Tests fail before implementation
- [ ] Basic implementation passes tests
- [ ] Advanced features added with tests
- [ ] All tests pass after refactoring

---

### Day 2: Core Implementation

#### TASK-05-004: Web Scraper Engine
**Assignee**: Backend Developer  
**Duration**: 5 hours (was 4 hours)  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-05-002, TASK-05-003

**TDD Process**:

1. **Red Phase (1.5 hours)**: Write scraper engine tests
```python
# tests/collectors/phoenix_mls/test_scraper.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSScraper

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
    
    async def test_context_manager(self, scraper):
        """Test scraper can be used as async context manager."""
        async with scraper as s:
            assert s is not None
            assert hasattr(s, 'browser')
            assert hasattr(s, 'context')
    
    async def test_search_zipcode(self, scraper, mock_browser_context):
        """Test zipcode search functionality."""
        # Setup mock response
        mock_page = mock_browser_context.new_page.return_value
        mock_page.content.return_value = self.mock_html_response()
        
        # This will fail initially
        async with scraper:
            properties = await scraper.search_zipcode("85001", max_pages=1)
        
        assert len(properties) > 0
        assert properties[0]["address"] == "123 Main St, Phoenix, AZ 85001"
        assert properties[0]["price"] == "$450,000"
    
    async def test_proxy_integration(self, scraper):
        """Test proxy is used for all requests."""
        async with scraper:
            # Verify proxy manager was called
            assert scraper.proxy_manager.get_proxy.called
            # Verify browser context uses proxy
            assert 'proxy' in scraper.browser.new_context.call_args.kwargs
```

2. **Green Phase (2.5 hours)**: Implement scraper engine
```python
# src/phoenix_real_estate/collectors/phoenix_mls/scraper.py
import asyncio
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup

from phoenix_real_estate.foundation.config import ConfigProvider
from phoenix_real_estate.foundation.exceptions import DataCollectionError
from .proxy_manager import ProxyManager
from .anti_detection import AntiDetectionManager

class PhoenixMLSScraper:
    """Web scraper for Phoenix MLS listings."""
    
    def __init__(self, config: ConfigProvider):
        self.config = config
        self.base_url = config.get("PHOENIX_MLS_BASE_URL", "https://phoenixmlssearch.com")
        self.proxy_manager = ProxyManager(config)
        self.anti_detection = AntiDetectionManager()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
    
    async def __aenter__(self):
        """Setup browser with proxy and anti-detection."""
        self.playwright = await async_playwright().start()
        
        # Get proxy
        proxy_url = await self.proxy_manager.get_proxy()
        proxy_parts = self._parse_proxy_url(proxy_url)
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Create context with proxy
        self.context = await self.browser.new_context(
            proxy={
                "server": f"http://{proxy_parts['host']}:{proxy_parts['port']}",
                "username": proxy_parts['username'],
                "password": proxy_parts['password']
            },
            user_agent=self.anti_detection.get_random_user_agent(),
            viewport=self.anti_detection.get_random_viewport()
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _parse_proxy_url(self, proxy_url: str) -> Dict[str, str]:
        """Parse proxy URL into components."""
        # Simple implementation for http://user:pass@host:port
        import re
        match = re.match(r'http://([^:]+):([^@]+)@([^:]+):(\d+)', proxy_url)
        if match:
            return {
                'username': match.group(1),
                'password': match.group(2),
                'host': match.group(3),
                'port': match.group(4)
            }
        raise ValueError(f"Invalid proxy URL: {proxy_url}")
    
    async def search_zipcode(self, zipcode: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Search properties by zipcode."""
        if not self.context:
            raise DataCollectionError("Scraper not initialized. Use async context manager.")
        
        page = await self.context.new_page()
        await self.anti_detection.setup_page(page)
        
        try:
            # Navigate to search page
            search_url = f"{self.base_url}/search?zipcode={zipcode}"
            await page.goto(search_url, wait_until="domcontentloaded")
            
            # Extract properties
            properties = []
            properties.extend(await self._extract_properties_from_page(page))
            
            return properties
            
        finally:
            await page.close()
    
    async def _extract_properties_from_page(self, page: Page) -> List[Dict[str, Any]]:
        """Extract property data from current page."""
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        properties = []
        for listing in soup.find_all('div', class_='property-listing'):
            property_data = {
                'address': listing.find('div', class_='property-address').text.strip(),
                'price': listing.find('div', class_='property-price').text.strip(),
                'raw_html': str(listing)
            }
            properties.append(property_data)
        
        return properties
```

3. **Refactor Phase (1 hour)**: Add error handling and pagination
```python
# Add to PhoenixMLSScraper class
async def search_zipcode(self, zipcode: str, max_pages: int = 5) -> List[Dict[str, Any]]:
    """Search properties by zipcode with pagination support."""
    if not self.context:
        raise DataCollectionError("Scraper not initialized. Use async context manager.")
    
    page = await self.context.new_page()
    await self.anti_detection.setup_page(page)
    
    properties = []
    current_page = 1
    
    try:
        while current_page <= max_pages:
            # Navigate to search page
            search_url = f"{self.base_url}/search?zipcode={zipcode}&page={current_page}"
            
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector('.property-listing', timeout=10000)
            except Exception as e:
                # Report proxy failure
                proxy_url = await self.proxy_manager.get_proxy()
                await self.proxy_manager.report_result(proxy_url, False)
                raise DataCollectionError(f"Failed to load page: {str(e)}")
            
            # Extract properties
            page_properties = await self._extract_properties_from_page(page)
            if not page_properties:
                break  # No more results
            
            properties.extend(page_properties)
            
            # Human-like delay
            await self.anti_detection.human_like_delay(1.0, 3.0)
            
            current_page += 1
        
        # Report success
        proxy_url = await self.proxy_manager.get_proxy()
        await self.proxy_manager.report_result(proxy_url, True)
        
        return properties
        
    except Exception as e:
        # Log error with context
        self.logger.error(f"Error scraping zipcode {zipcode}: {str(e)}")
        raise
    finally:
        await page.close()
```

**Test-First Checkpoints**:
- [ ] Scraper tests written before implementation
- [ ] Context manager tests fail initially
- [ ] Basic scraping implementation passes tests
- [ ] Error handling added with tests
- [ ] All integration points tested

---

#### TASK-05-005: Data Extraction & Parsing
**Assignee**: Backend Developer  
**Duration**: 4 hours (was 3 hours)  
**Priority**: P1 - High  
**Dependencies**: TASK-05-004

**TDD Process**:

1. **Red Phase (1 hour)**: Write parser tests
```python
# tests/collectors/phoenix_mls/test_parser.py
import pytest
from bs4 import BeautifulSoup
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper

class TestDataParsing:
    """Test data extraction and parsing."""
    
    @pytest.fixture
    def scraper(self, mock_config):
        return PhoenixMLSScraper(mock_config)
    
    def test_parse_listing_element(self, scraper):
        """Test parsing individual listing element."""
        html = """
        <div class="property-listing">
            <a href="/property/12345" class="property-link">
                <div class="property-address">123 Test Ave, Phoenix, AZ 85001</div>
                <div class="property-price">$350,000</div>
                <div class="property-details">
                    <span class="beds">3 beds</span>
                    <span class="baths">2 baths</span>
                    <span class="sqft">1,500 sqft</span>
                </div>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        listing = soup.find('div', class_='property-listing')
        
        # This will fail initially
        result = scraper._parse_listing_element(listing)
        
        assert result["address"]["street"] == "123 Test Ave"
        assert result["address"]["city"] == "Phoenix"
        assert result["address"]["state"] == "AZ"
        assert result["address"]["zip"] == "85001"
        assert result["price"] == 350000
        assert result["features"]["beds"] == 3
        assert result["features"]["baths"] == 2
        assert result["features"]["sqft"] == 1500
        assert result["property_url"] == "/property/12345"
        assert "raw_html" in result
    
    def test_extract_price_variations(self, scraper):
        """Test price extraction with various formats."""
        test_cases = [
            ("$350,000", 350000),
            ("$1,250,000", 1250000),
            ("$450K", 450000),
            ("$1.5M", 1500000),
            ("Price: $275,000", 275000),
            ("REDUCED! $399,900", 399900)
        ]
        
        for price_text, expected in test_cases:
            result = scraper._extract_price(price_text)
            assert result == expected, f"Failed to parse {price_text}"
```

2. **Green Phase (2 hours)**: Implement parsing logic
```python
# Add to scraper.py
import re
from datetime import datetime

def _parse_listing_element(self, listing_element) -> Dict[str, Any]:
    """Extract property data from listing HTML."""
    # Extract basic fields
    address_elem = listing_element.find('div', class_='property-address')
    price_elem = listing_element.find('div', class_='property-price')
    link_elem = listing_element.find('a', class_='property-link')
    
    # Parse address
    address_text = address_elem.text.strip() if address_elem else ""
    parsed_address = self._parse_address(address_text)
    
    # Extract price
    price_text = price_elem.text.strip() if price_elem else ""
    price_value = self._extract_price(price_text)
    
    # Extract features
    features = self._extract_features(listing_element)
    
    return {
        "source": "phoenix_mls",
        "scraped_at": datetime.utcnow().isoformat(),
        "address": parsed_address,
        "price": price_value,
        "features": features,
        "property_url": link_elem.get('href') if link_elem else None,
        "raw_html": str(listing_element),
        "structured_data": {
            "price_text": price_text,
            "address_text": address_text
        }
    }

def _parse_address(self, address_text: str) -> Dict[str, str]:
    """Parse address into components."""
    # Pattern: "123 Main St, Phoenix, AZ 85001"
    pattern = r'^(.+?),\s*([^,]+),\s*([A-Z]{2})\s*(\d{5})$'
    match = re.match(pattern, address_text)
    
    if match:
        return {
            "street": match.group(1).strip(),
            "city": match.group(2).strip(),
            "state": match.group(3),
            "zip": match.group(4)
        }
    
    return {"full_address": address_text}

def _extract_price(self, price_text: str) -> Optional[int]:
    """Extract numeric price from text."""
    # Remove non-numeric except for K, M indicators
    price_text = price_text.upper()
    
    # Handle millions (e.g., $1.5M)
    if 'M' in price_text:
        match = re.search(r'([\d.]+)\s*M', price_text)
        if match:
            return int(float(match.group(1)) * 1_000_000)
    
    # Handle thousands (e.g., $450K)
    if 'K' in price_text:
        match = re.search(r'(\d+)\s*K', price_text)
        if match:
            return int(match.group(1)) * 1000
    
    # Standard format (e.g., $350,000)
    match = re.search(r'\$?([\d,]+)', price_text)
    if match:
        return int(match.group(1).replace(',', ''))
    
    return None

def _extract_features(self, listing_element) -> Dict[str, Any]:
    """Extract property features."""
    features = {}
    
    # Extract beds
    beds_elem = listing_element.find('span', class_='beds')
    if beds_elem:
        match = re.search(r'(\d+)\s*bed', beds_elem.text, re.I)
        if match:
            features['beds'] = int(match.group(1))
    
    # Extract baths
    baths_elem = listing_element.find('span', class_='baths')
    if baths_elem:
        match = re.search(r'(\d+(?:\.\d+)?)\s*bath', baths_elem.text, re.I)
        if match:
            features['baths'] = float(match.group(1))
    
    # Extract sqft
    sqft_elem = listing_element.find('span', class_='sqft')
    if sqft_elem:
        match = re.search(r'([\d,]+)\s*sq', sqft_elem.text, re.I)
        if match:
            features['sqft'] = int(match.group(1).replace(',', ''))
    
    return features
```

3. **Refactor Phase (1 hour)**: Add flexible parsing
```python
# Add fallback strategies and flexible selectors
def _extract_structured_details(self, soup: BeautifulSoup) -> Dict:
    """Extract detailed property information with fallbacks."""
    details = {}
    
    # Multiple selector strategies
    selector_strategies = [
        {
            'price': ['.property-price', '.listing-price', '[data-price]'],
            'beds': ['.beds', '.bedrooms', '[data-beds]'],
            'baths': ['.baths', '.bathrooms', '[data-baths]'],
            'sqft': ['.sqft', '.square-feet', '[data-sqft]']
        }
    ]
    
    for strategy in selector_strategies:
        for field, selectors in strategy.items():
            if field not in details:
                for selector in selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        details[field] = elem.text.strip()
                        break
    
    # Text search fallback
    if 'beds' not in details:
        text = soup.get_text()
        match = re.search(r'(\d+)\s*(?:bed|br)', text, re.I)
        if match:
            details['beds'] = match.group(1)
    
    return details
```

**Test-First Checkpoints**:
- [ ] Parser tests cover edge cases
- [ ] Tests fail before implementation
- [ ] Basic parsing passes tests
- [ ] Flexible parsing strategies tested
- [ ] 95%+ parsing accuracy achieved

---

#### TASK-05-006: Error Handling Framework
**Assignee**: Backend Developer  
**Duration**: 3 hours (was 2 hours)  
**Priority**: P1 - High  
**Dependencies**: TASK-05-004

**TDD Process**:

1. **Red Phase (1 hour)**: Write error handling tests
```python
# tests/collectors/phoenix_mls/test_error_handling.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSScraper
from phoenix_real_estate.foundation.exceptions import (
    NetworkError, ParsingError, RateLimitError, BrowserCrashError
)

class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.fixture
    async def scraper(self, mock_config):
        scraper = PhoenixMLSScraper(mock_config)
        scraper.logger = Mock()
        return scraper
    
    async def test_network_error_retry(self, scraper):
        """Test exponential backoff on network errors."""
        with patch.object(scraper, '_make_request') as mock_request:
            # Fail twice, then succeed
            mock_request.side_effect = [
                NetworkError("Connection failed"),
                NetworkError("Connection failed"),
                {"success": True}
            ]
            
            result = await scraper._retry_with_backoff(
                scraper._make_request,
                max_retries=3
            )
            
            assert result == {"success": True}
            assert mock_request.call_count == 3
    
    async def test_rate_limit_handling(self, scraper):
        """Test proxy switching on rate limits."""
        original_proxy = await scraper.proxy_manager.get_proxy()
        
        # Simulate rate limit error
        with pytest.raises(RateLimitError):
            await scraper._handle_rate_limit(original_proxy)
        
        # Should switch proxy
        new_proxy = await scraper.proxy_manager.get_proxy()
        assert new_proxy != original_proxy
    
    async def test_browser_crash_recovery(self, scraper):
        """Test browser restart on crash."""
        # Setup context
        async with scraper:
            original_browser = scraper.browser
            
            # Simulate crash
            scraper.browser = None
            
            # Should recover
            await scraper._ensure_browser_alive()
            
            assert scraper.browser is not None
            assert scraper.browser != original_browser
    
    async def test_parsing_error_fallback(self, scraper):
        """Test raw HTML storage on parsing errors."""
        html = "<div>Malformed HTML</div>"
        
        with patch.object(scraper, '_parse_listing_element') as mock_parse:
            mock_parse.side_effect = ParsingError("Parse failed")
            
            result = await scraper._safe_parse_listing(html)
            
            assert result["parse_error"] == True
            assert result["raw_html"] == html
            assert result["error_message"] == "Parse failed"
```

2. **Green Phase (1.5 hours)**: Implement error handling
```python
# Add to scraper.py
import time
from typing import Callable, TypeVar, Any

T = TypeVar('T')

class ErrorHandler:
    """Centralized error handling strategies."""
    
    ERROR_STRATEGIES = {
        NetworkError: {
            "strategy": "exponential_backoff",
            "max_retries": 3,
            "base_delay": 2.0
        },
        ParsingError: {
            "strategy": "store_raw_fallback", 
            "max_retries": 1,
            "flag_for_llm": True
        },
        RateLimitError: {
            "strategy": "proxy_switch_delay",
            "max_retries": 5,
            "delay_multiplier": 2.0
        },
        BrowserCrashError: {
            "strategy": "restart_from_checkpoint",
            "max_retries": 2,
            "checkpoint_interval": 10
        }
    }
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle error with appropriate strategy."""
        error_type = type(error)
        strategy = self.ERROR_STRATEGIES.get(error_type, {})
        
        if strategy.get("strategy") == "exponential_backoff":
            return await self._exponential_backoff_retry(
                context["func"],
                context["args"],
                strategy["max_retries"],
                strategy["base_delay"]
            )
        elif strategy.get("strategy") == "store_raw_fallback":
            return self._store_raw_fallback(context["raw_data"])
        # ... other strategies

# Add to PhoenixMLSScraper
async def _retry_with_backoff(
    self,
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 2.0,
    **kwargs
) -> T:
    """Retry function with exponential backoff."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {str(e)}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                self.logger.error(f"All {max_retries} attempts failed")
    
    raise last_exception

async def _handle_rate_limit(self, current_proxy: str):
    """Handle rate limit by switching proxy."""
    # Report current proxy as degraded
    await self.proxy_manager.report_result(current_proxy, False)
    
    # Get new proxy
    new_proxy = await self.proxy_manager.get_proxy()
    
    # Delay before retry
    await asyncio.sleep(5.0)
    
    raise RateLimitError("Rate limited, switching proxy")

async def _ensure_browser_alive(self):
    """Ensure browser is alive and restart if needed."""
    if not self.browser or not self.browser.is_connected():
        self.logger.warning("Browser crashed, restarting...")
        
        # Clean up old browser
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
        
        # Restart
        await self.__aenter__()

def _safe_parse_listing(self, html: str) -> Dict[str, Any]:
    """Safely parse listing with fallback."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        listing = soup.find('div', class_='property-listing')
        return self._parse_listing_element(listing)
    except Exception as e:
        self.logger.error(f"Parsing failed: {str(e)}")
        return {
            "parse_error": True,
            "raw_html": html,
            "error_message": str(e),
            "scraped_at": datetime.utcnow().isoformat()
        }
```

3. **Refactor Phase (30 min)**: Add checkpoint support
```python
# Add checkpoint/resume capability
class ScraperCheckpoint:
    """Manage scraping checkpoints for recovery."""
    
    def __init__(self):
        self.checkpoints = {}
    
    def save_checkpoint(self, zipcode: str, page: int, properties_collected: int):
        """Save scraping progress."""
        self.checkpoints[zipcode] = {
            "page": page,
            "properties_collected": properties_collected,
            "timestamp": datetime.utcnow()
        }
    
    def get_checkpoint(self, zipcode: str) -> Optional[Dict]:
        """Get last checkpoint for zipcode."""
        return self.checkpoints.get(zipcode)
    
    def clear_checkpoint(self, zipcode: str):
        """Clear checkpoint after successful completion."""
        self.checkpoints.pop(zipcode, None)

# Use in scraper
async def search_zipcode(self, zipcode: str, max_pages: int = 5) -> List[Dict[str, Any]]:
    """Search with checkpoint support."""
    checkpoint = self.checkpoint_manager.get_checkpoint(zipcode)
    start_page = checkpoint["page"] if checkpoint else 1
    properties = []
    
    # ... rest of implementation
```

**Test-First Checkpoints**:
- [ ] Error scenario tests written first
- [ ] Tests verify retry behavior
- [ ] Recovery mechanisms tested
- [ ] Checkpoint functionality verified
- [ ] All error paths covered

---

### Day 3: Integration & Testing

#### TASK-05-007: PhoenixMLS Collector Integration
**Assignee**: Backend Developer  
**Duration**: 4 hours (was 3 hours)  
**Priority**: P0 - Integration Critical  
**Dependencies**: TASK-05-005, TASK-05-006

**TDD Process**:

1. **Red Phase (1 hour)**: Write collector integration tests
```python
# tests/collectors/phoenix_mls/test_collector.py
import pytest
from unittest.mock import Mock, AsyncMock
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector
from phoenix_real_estate.foundation.schemas import Property

class TestPhoenixMLSCollector:
    """Test collector integration with Epic 1."""
    
    @pytest.fixture
    async def collector(self, mock_config, mock_repository):
        return PhoenixMLSCollector(
            config=mock_config,
            repository=mock_repository,
            logger_name="test.phoenix_mls"
        )
    
    async def test_collector_inheritance(self, collector):
        """Test collector properly inherits from DataCollector."""
        from phoenix_real_estate.foundation.collectors import DataCollector
        assert isinstance(collector, DataCollector)
        assert hasattr(collector, 'collect_zipcode')
        assert hasattr(collector, 'adapt_property')
    
    async def test_collect_zipcode_integration(self, collector):
        """Test full collection workflow."""
        # Mock scraper response
        raw_properties = [
            {
                "address": {"street": "123 Main St", "city": "Phoenix", "state": "AZ", "zip": "85001"},
                "price": 350000,
                "features": {"beds": 3, "baths": 2, "sqft": 1500},
                "property_url": "/property/123",
                "scraped_at": "2025-01-20T10:00:00Z"
            }
        ]
        
        with patch.object(collector.scraper, 'search_zipcode', return_value=raw_properties):
            results = await collector.collect_zipcode("85001")
        
        assert len(results) == 1
        assert results[0]["address"]["street"] == "123 Main St"
    
    async def test_adapt_property_schema(self, collector):
        """Test adaptation to Epic 1 Property schema."""
        raw_data = {
            "address": {"street": "123 Main St", "city": "Phoenix", "state": "AZ", "zip": "85001"},
            "price": 350000,
            "features": {"beds": 3, "baths": 2, "sqft": 1500},
            "property_url": "/property/123",
            "scraped_at": "2025-01-20T10:00:00Z"
        }
        
        property_obj = await collector.adapt_property(raw_data)
        
        assert isinstance(property_obj, Property)
        assert property_obj.property_id.startswith("phoenix_mls_")
        assert property_obj.address.street == "123 Main St"
        assert property_obj.prices[0].amount == 350000
        assert property_obj.features.bedrooms == 3
```

2. **Green Phase (2 hours)**: Implement collector
```python
# src/phoenix_real_estate/collectors/phoenix_mls/collector.py
from typing import List, Dict, Any
import hashlib
from datetime import datetime

from phoenix_real_estate.foundation.collectors import DataCollector
from phoenix_real_estate.foundation.config import ConfigProvider
from phoenix_real_estate.foundation.repositories import PropertyRepository
from phoenix_real_estate.foundation.schemas import Property, Address, Price, Features
from .scraper import PhoenixMLSScraper
from .adapter import PhoenixMLSAdapter

class PhoenixMLSCollector(DataCollector):
    """Phoenix MLS data collector with Epic 1 integration."""
    
    def __init__(self, config: ConfigProvider, 
                 repository: PropertyRepository,
                 logger_name: str):
        super().__init__(config, repository, logger_name)
        self.scraper = PhoenixMLSScraper(config)
        self.adapter = PhoenixMLSAdapter(self.data_validator, logger_name)
    
    async def collect_zipcode(self, zipcode: str) -> List[Dict]:
        """Collect properties for zipcode."""
        self.logger.info(f"Starting collection for zipcode: {zipcode}")
        
        try:
            async with self.scraper as scraper:
                raw_properties = await scraper.search_zipcode(zipcode)
            
            self.logger.info(f"Collected {len(raw_properties)} properties")
            return raw_properties
            
        except Exception as e:
            self.logger.error(f"Collection failed for {zipcode}: {str(e)}")
            raise
    
    async def adapt_property(self, raw_data: Dict) -> Property:
        """Convert raw data to Epic 1 Property schema."""
        return await self.adapter.adapt_property(raw_data)
    
    async def collect_and_store(self, zipcode: str) -> int:
        """Collect and store properties for zipcode."""
        raw_properties = await self.collect_zipcode(zipcode)
        stored_count = 0
        
        for raw_data in raw_properties:
            try:
                property_obj = await self.adapt_property(raw_data)
                await self.repository.create(property_obj)
                stored_count += 1
            except Exception as e:
                self.logger.error(f"Failed to store property: {str(e)}")
                # Store raw data for later processing
                await self._store_failed_property(raw_data, str(e))
        
        return stored_count

# src/phoenix_real_estate/collectors/phoenix_mls/adapter.py
class PhoenixMLSAdapter:
    """Adapts Phoenix MLS data to Epic 1 schema."""
    
    def __init__(self, validator, logger_name: str):
        self.validator = validator
        self.logger = logging.getLogger(logger_name)
    
    async def adapt_property(self, raw_data: Dict) -> Property:
        """Convert raw Phoenix MLS data to Property schema."""
        # Generate unique ID
        property_id = self._generate_property_id(raw_data)
        
        # Convert address
        address = Address(
            street=raw_data["address"].get("street", ""),
            city=raw_data["address"].get("city", "Phoenix"),
            state=raw_data["address"].get("state", "AZ"),
            zip_code=raw_data["address"].get("zip", "")
        )
        
        # Convert price
        prices = []
        if raw_data.get("price"):
            prices.append(Price(
                amount=float(raw_data["price"]),
                currency="USD",
                date=datetime.fromisoformat(raw_data["scraped_at"]),
                source="phoenix_mls"
            ))
        
        # Convert features
        raw_features = raw_data.get("features", {})
        features = Features(
            bedrooms=raw_features.get("beds"),
            bathrooms=raw_features.get("baths"),
            square_feet=raw_features.get("sqft"),
            lot_size=raw_features.get("lot_size"),
            year_built=raw_features.get("year_built"),
            property_type=raw_features.get("property_type", "Single Family")
        )
        
        # Create property
        property_obj = Property(
            property_id=property_id,
            address=address,
            prices=prices,
            features=features,
            listing_details=raw_data.get("structured_data", {}),
            last_updated=datetime.utcnow()
        )
        
        # Validate
        self.validator.validate_property(property_obj)
        
        return property_obj
    
    def _generate_property_id(self, raw_data: Dict) -> str:
        """Generate unique property ID."""
        # Use address as base for ID
        address_str = f"{raw_data['address'].get('street', '')}_{raw_data['address'].get('zip', '')}"
        hash_obj = hashlib.md5(address_str.encode())
        return f"phoenix_mls_{hash_obj.hexdigest()[:12]}"
```

3. **Refactor Phase (1 hour)**: Add batch processing
```python
# Add batch processing capabilities
async def collect_and_store_batch(self, zipcodes: List[str]) -> Dict[str, int]:
    """Collect and store properties for multiple zipcodes."""
    results = {}
    
    for zipcode in zipcodes:
        try:
            count = await self.collect_and_store(zipcode)
            results[zipcode] = count
            self.logger.info(f"Stored {count} properties for {zipcode}")
        except Exception as e:
            self.logger.error(f"Failed to process {zipcode}: {str(e)}")
            results[zipcode] = 0
        
        # Rate limiting between zipcodes
        await asyncio.sleep(2.0)
    
    return results

async def _store_failed_property(self, raw_data: Dict, error: str):
    """Store failed property for later processing."""
    failed_record = {
        "raw_data": raw_data,
        "error": error,
        "timestamp": datetime.utcnow(),
        "retry_count": 0
    }
    # Store in separate collection or queue for LLM processing
    await self.repository.store_failed_record(failed_record)
```

**Test-First Checkpoints**:
- [ ] Integration tests written first
- [ ] Epic 1 compliance verified
- [ ] Schema adaptation tested
- [ ] Repository integration tested
- [ ] Error handling verified

---

#### TASK-05-008: Comprehensive Test Suite
**Assignee**: Backend Developer + QA Engineer  
**Duration**: 4 hours (was 3 hours)  
**Priority**: P1 - Quality Gate  
**Dependencies**: TASK-05-007

**TDD Process**:

1. **Red Phase (1.5 hours)**: Write end-to-end tests
```python
# tests/integration/phoenix_mls/test_end_to_end.py
import pytest
import asyncio
import time
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector

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
        
        # Adapt and store
        stored_count = 0
        for raw_data in raw_properties[:5]:  # Test first 5
            property_obj = await collector.adapt_property(raw_data)
            
            # Validate schema compliance
            assert property_obj.property_id
            assert property_obj.address.zip_code == "85001"
            assert property_obj.prices[0].amount > 0
            
            # Store in repository
            await collector.repository.create(property_obj)
            stored_count += 1
        
        # Verify storage
        stored = await collector.repository.find_by_zipcode("85001")
        assert len(stored) >= stored_count
    
    async def test_concurrent_collections(self, collector):
        """Test concurrent zipcode collections."""
        zipcodes = ["85001", "85002", "85003"]
        
        # Collect concurrently
        tasks = [collector.collect_zipcode(zc) for zc in zipcodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded or handled gracefully
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 2  # At least 2 should succeed
    
    async def test_rate_limiting_compliance(self, collector):
        """Test rate limiting under load."""
        start_time = time.time()
        request_count = 0
        
        # Make requests tracking rate
        for _ in range(10):
            try:
                await collector.collect_zipcode("85001")
                request_count += 1
            except RateLimitError:
                # Expected behavior
                pass
        
        duration = time.time() - start_time
        rate = request_count / duration * 60  # requests per minute
        
        assert rate <= 10, f"Rate {rate}/min exceeds limit"
```

2. **Green Phase (1.5 hours)**: Ensure tests pass
```python
# Implement any missing functionality to make tests pass
# This might include rate limiting, concurrent handling, etc.

# Add to collector.py
from asyncio import Semaphore

class PhoenixMLSCollector(DataCollector):
    def __init__(self, config, repository, logger_name):
        super().__init__(config, repository, logger_name)
        self.scraper = PhoenixMLSScraper(config)
        self.adapter = PhoenixMLSAdapter(self.data_validator, logger_name)
        
        # Rate limiting
        self.rate_limit = Semaphore(10)  # 10 concurrent requests max
        self.request_times = []
    
    async def _check_rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        # Remove old entries
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= 10:
            # Wait until we can make another request
            wait_time = 60 - (now - self.request_times[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.request_times.append(now)
```

3. **Refactor Phase (1 hour)**: Add performance tests
```python
# tests/integration/phoenix_mls/test_performance.py
import psutil
import pytest

class TestPerformance:
    """Performance and scalability tests."""
    
    @pytest.mark.benchmark
    async def test_response_time_targets(self, collector, benchmark):
        """Test average response times meet targets."""
        async def collect_single():
            return await collector.collect_zipcode("85001")
        
        result = await benchmark(collect_single)
        assert benchmark.stats["mean"] < 2.0  # Average under 2 seconds
    
    async def test_memory_usage(self, collector):
        """Test memory usage under load."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Collect many properties
        for i in range(10):
            await collector.collect_zipcode(f"8500{i}")
            
            # Check memory after each batch
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            
            assert memory_increase < 200, f"Memory increased by {memory_increase}MB after {i+1} batches"
```

**Test-First Checkpoints**:
- [ ] E2E tests define expected behavior
- [ ] Performance tests set targets
- [ ] All tests initially fail
- [ ] Implementation makes tests pass
- [ ] 90%+ coverage achieved

---

#### TASK-05-009: Documentation Package
**Assignee**: Backend Developer  
**Duration**: 2.5 hours (was 2 hours)  
**Priority**: P2 - Important  
**Dependencies**: TASK-05-008

**TDD Process**:

1. **Red Phase (30 min)**: Write documentation tests
```python
# tests/test_documentation.py
import os
import pytest

class TestDocumentation:
    """Test documentation completeness."""
    
    def test_architecture_doc_exists(self):
        """Test architecture documentation exists."""
        doc_path = "docs/collectors/phoenix_mls_architecture.md"
        assert os.path.exists(doc_path), "Architecture doc missing"
        
        with open(doc_path) as f:
            content = f.read()
            assert "System Design" in content
            assert "Component Interactions" in content
            assert "Data Flow" in content
    
    def test_api_documentation(self):
        """Test API documentation completeness."""
        from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector
        
        # Check docstrings
        assert PhoenixMLSCollector.__doc__
        assert PhoenixMLSCollector.collect_zipcode.__doc__
        assert PhoenixMLSCollector.adapt_property.__doc__
    
    def test_configuration_guide(self):
        """Test configuration documentation."""
        doc_path = "docs/collectors/phoenix_mls_configuration.md"
        assert os.path.exists(doc_path)
        
        with open(doc_path) as f:
            content = f.read()
            # Should document all env vars
            assert "PHOENIX_MLS_BASE_URL" in content
            assert "WEBSHARE_USERNAME" in content
            assert "Troubleshooting" in content
```

2. **Green Phase (1.5 hours)**: Create documentation
```markdown
# docs/collectors/phoenix_mls_architecture.md

# Phoenix MLS Scraper Architecture

## System Design

The Phoenix MLS scraper is designed as a modular, fault-tolerant system for collecting real estate data.

### Component Interactions

```mermaid
graph TD
    A[PhoenixMLSCollector] --> B[PhoenixMLSScraper]
    A --> C[PhoenixMLSAdapter]
    B --> D[ProxyManager]
    B --> E[AntiDetectionManager]
    B --> F[ErrorHandler]
    C --> G[DataValidator]
    A --> H[PropertyRepository]
```

### Data Flow

1. **Collection Request**: Collector receives zipcode request
2. **Proxy Selection**: ProxyManager provides healthy proxy
3. **Browser Setup**: Anti-detection configures browser
4. **Data Scraping**: Scraper extracts property listings
5. **Data Adaptation**: Adapter converts to Epic 1 schema
6. **Validation**: Validator ensures data quality
7. **Storage**: Repository persists validated data

## Security Considerations

- Proxy credentials encrypted in transit
- No sensitive data in logs
- Rate limiting prevents detection
- Browser fingerprinting randomized
```

3. **Refactor Phase (30 min)**: Add examples
```markdown
# Add to configuration.md

## Usage Examples

### Basic Collection
```python
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector

# Initialize collector
collector = PhoenixMLSCollector(config, repository, "phoenix_mls")

# Collect single zipcode
properties = await collector.collect_zipcode("85001")

# Collect and store
count = await collector.collect_and_store("85001")
print(f"Stored {count} properties")
```

### Error Handling
```python
try:
    await collector.collect_zipcode("85001")
except RateLimitError:
    # Wait and retry with different proxy
    await asyncio.sleep(60)
    await collector.collect_zipcode("85001")
except DataCollectionError as e:
    # Log and store for manual review
    logger.error(f"Collection failed: {e}")
```
```

**Test-First Checkpoints**:
- [ ] Documentation tests written first
- [ ] Tests verify completeness
- [ ] Documentation created to pass tests
- [ ] Examples tested and working
- [ ] All sections complete

---

### Day 4: Validation & Launch

#### TASK-05-010: Security Audit
**Assignee**: Security Engineer / Backend Developer  
**Duration**: 2.5 hours (was 2 hours)  
**Priority**: P0 - Gate  
**Dependencies**: TASK-05-008

**TDD Process**:

1. **Red Phase (45 min)**: Write security tests
```python
# tests/collectors/phoenix_mls/test_security.py
import pytest
import logging
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector

class TestSecurity:
    """Security and credential handling tests."""
    
    def test_no_credentials_in_logs(self, caplog, collector):
        """Ensure credentials never appear in logs."""
        # Set sensitive data
        sensitive_proxy = "http://secret_user:secret_pass@proxy.com:8080"
        
        with caplog.at_level(logging.DEBUG):
            collector.logger.debug("Proxy URL", extra={"proxy": sensitive_proxy})
        
        # Check logs are sanitized
        assert "secret_pass" not in caplog.text
        assert "secret_user" not in caplog.text
        assert "****" in caplog.text or "[REDACTED]" in caplog.text
    
    def test_credential_encryption(self, config):
        """Test credentials are encrypted in config."""
        # These should fail if not encrypted
        proxy_user = config.get_required("WEBSHARE_USERNAME")
        proxy_pass = config.get_required("WEBSHARE_PASSWORD")
        
        # Should be encrypted
        assert not proxy_pass.startswith("plain:")
        assert len(proxy_pass) > 20  # Encrypted values are longer
    
    def test_input_validation(self, collector):
        """Test input validation prevents injection."""
        # SQL injection attempt
        malicious_zipcode = "85001'; DROP TABLE properties; --"
        
        with pytest.raises(ValueError, match="Invalid zipcode"):
            await collector.collect_zipcode(malicious_zipcode)
        
        # Path traversal attempt
        malicious_path = "../../../etc/passwd"
        
        with pytest.raises(ValueError):
            await collector._validate_input(malicious_path)
```

2. **Green Phase (1 hour)**: Implement security measures
```python
# Add security utilities
import re
from typing import Any, Dict

class SecurityUtils:
    """Security utilities for Phoenix MLS scraper."""
    
    @staticmethod
    def sanitize_for_logging(data: Any) -> Any:
        """Sanitize sensitive data for logging."""
        if isinstance(data, str):
            # Sanitize proxy URLs
            if "://" in data and "@" in data:
                # Pattern: protocol://user:pass@host:port
                return re.sub(
                    r'://([^:]+):([^@]+)@',
                    r'://[REDACTED]:[REDACTED]@',
                    data
                )
            return data
        elif isinstance(data, dict):
            return {k: SecurityUtils.sanitize_for_logging(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [SecurityUtils.sanitize_for_logging(item) for item in data]
        return data
    
    @staticmethod
    def validate_zipcode(zipcode: str) -> str:
        """Validate zipcode input."""
        if not re.match(r'^\d{5}(-\d{4})?$', zipcode):
            raise ValueError(f"Invalid zipcode format: {zipcode}")
        return zipcode
    
    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL to prevent injection."""
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL scheme: {url}")
        
        # Check for suspicious patterns
        suspicious_patterns = ['../', '%2e%2e', 'file://', 'javascript:']
        for pattern in suspicious_patterns:
            if pattern in url.lower():
                raise ValueError(f"Suspicious URL pattern detected: {pattern}")
        
        return url

# Add to collector
class PhoenixMLSCollector(DataCollector):
    async def collect_zipcode(self, zipcode: str) -> List[Dict]:
        """Collect properties with input validation."""
        # Validate input
        zipcode = SecurityUtils.validate_zipcode(zipcode)
        
        self.logger.info(
            "Starting collection",
            extra=SecurityUtils.sanitize_for_logging({
                "zipcode": zipcode,
                "proxy": await self.scraper.proxy_manager.get_proxy()
            })
        )
        
        # ... rest of implementation
```

3. **Refactor Phase (45 min)**: Add compliance checks
```python
# Add compliance validation
class ComplianceChecker:
    """Ensure legal compliance for web scraping."""
    
    @staticmethod
    def check_robots_txt(url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        # Implementation would check actual robots.txt
        return True
    
    @staticmethod
    def enforce_rate_limits():
        """Ensure rate limiting compliance."""
        # Max 10 requests per minute per Terms of Service
        pass
    
    @staticmethod
    def validate_data_usage(data: Dict) -> Dict:
        """Ensure data usage compliance."""
        # Remove any PII if present
        # Ensure fair use compliance
        return data
```

**Test-First Checkpoints**:
- [ ] Security tests define requirements
- [ ] Tests fail without security measures
- [ ] Security implementation passes tests
- [ ] Compliance validation added
- [ ] All vulnerabilities addressed

---

#### TASK-05-011: Production Configuration
**Assignee**: DevOps / Backend Developer  
**Duration**: 2.5 hours (was 2 hours)  
**Priority**: P0 - Launch Blocker  
**Dependencies**: TASK-05-010

**TDD Process**:

1. **Red Phase (45 min)**: Write configuration tests
```python
# tests/test_production_config.py
import pytest
import os
from phoenix_real_estate.foundation.config import ConfigProvider

class TestProductionConfig:
    """Test production configuration."""
    
    def test_required_env_vars(self):
        """Test all required env vars are set."""
        required_vars = [
            "PHOENIX_MLS_BASE_URL",
            "PHOENIX_MLS_MAX_RETRIES",
            "PHOENIX_MLS_TIMEOUT",
            "WEBSHARE_USERNAME",
            "WEBSHARE_PASSWORD",
            "PROXY_HEALTH_CHECK_INTERVAL"
        ]
        
        config = ConfigProvider()
        for var in required_vars:
            value = config.get_required(var)
            assert value is not None, f"{var} not configured"
    
    def test_resource_limits(self):
        """Test resource limits are configured."""
        config = ConfigProvider()
        
        # Browser memory limit
        memory_limit = config.get_int("BROWSER_MEMORY_LIMIT", 0)
        assert 256 <= memory_limit <= 1024, "Invalid memory limit"
        
        # Concurrent pages
        concurrent_pages = config.get_int("MAX_CONCURRENT_PAGES", 0)
        assert 1 <= concurrent_pages <= 5, "Invalid concurrent pages"
        
        # Request rate
        rate_limit = config.get_int("REQUESTS_PER_MINUTE", 0)
        assert 1 <= rate_limit <= 10, "Invalid rate limit"
```

2. **Green Phase (1 hour)**: Create production config
```yaml
# config/production.yaml
phoenix_mls:
  base_url: "https://phoenixmlssearch.com"
  max_retries: 3
  timeout: 30000
  
  # Resource limits
  browser:
    memory_limit_mb: 512
    concurrent_pages: 3
    headless: true
    
  # Rate limiting
  rate_limiting:
    requests_per_minute: 10
    burst_size: 3
    
  # Proxy configuration
  proxy:
    provider: "webshare"
    health_check_interval: 300
    min_healthy_proxies: 3
    rotation_strategy: "intelligent"
    
  # Error handling
  error_handling:
    max_consecutive_failures: 5
    backoff_multiplier: 2.0
    max_backoff_seconds: 300
    
# Monitoring
monitoring:
  metrics:
    enabled: true
    provider: "prometheus"
    port: 9090
    
  logging:
    level: "INFO"
    format: "json"
    sanitize_sensitive: true
    
  alerts:
    success_rate_threshold: 0.95
    response_time_p99: 2000
    memory_usage_threshold: 0.8
```

3. **Refactor Phase (45 min)**: Add monitoring setup
```python
# src/phoenix_real_estate/collectors/phoenix_mls/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
requests_total = Counter(
    'phoenix_mls_requests_total',
    'Total requests made',
    ['zipcode', 'status']
)

request_duration = Histogram(
    'phoenix_mls_request_duration_seconds',
    'Request duration in seconds',
    ['operation']
)

proxy_health = Gauge(
    'phoenix_mls_proxy_health',
    'Proxy health status',
    ['proxy_host']
)

active_browsers = Gauge(
    'phoenix_mls_active_browsers',
    'Number of active browser instances'
)

# Decorator for timing
def timed_operation(operation_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                requests_total.labels(
                    zipcode=kwargs.get('zipcode', 'unknown'),
                    status='success'
                ).inc()
                return result
            except Exception as e:
                requests_total.labels(
                    zipcode=kwargs.get('zipcode', 'unknown'),
                    status='error'
                ).inc()
                raise
            finally:
                duration = time.time() - start
                request_duration.labels(operation=operation_name).observe(duration)
        return wrapper
    return decorator
```

**Test-First Checkpoints**:
- [ ] Config tests verify requirements
- [ ] Tests fail without proper config
- [ ] Production config created
- [ ] Monitoring implemented
- [ ] All limits enforced

---

#### TASK-05-012: Launch & 24h Monitoring
**Assignee**: Team Lead + Backend Developer  
**Duration**: 2.5 hours + 24h monitoring  
**Priority**: P0 - Launch  
**Dependencies**: TASK-05-011

**TDD Process**:

1. **Red Phase (45 min)**: Write smoke tests
```python
# tests/smoke/test_phoenix_mls_live.py
import pytest
import asyncio
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector

class TestPhoenixMLSSmoke:
    """Production smoke tests."""
    
    @pytest.mark.smoke
    async def test_basic_collection(self, production_config, production_repository):
        """Test basic collection in production."""
        collector = PhoenixMLSCollector(
            production_config,
            production_repository,
            "phoenix_mls.smoke"
        )
        
        # Test single property collection
        properties = await collector.collect_zipcode("85001")
        
        assert len(properties) > 0
        assert properties[0]["address"]
        assert properties[0]["price"]
    
    @pytest.mark.smoke
    async def test_proxy_health(self, production_collector):
        """Test proxy system health."""
        stats = production_collector.scraper.proxy_manager.get_proxy_health_stats()
        
        assert stats["healthy_proxies"] >= 3
        assert stats["total_proxies"] >= 5
        
    @pytest.mark.smoke  
    async def test_rate_limiting(self, production_collector):
        """Test rate limiting is active."""
        # Make rapid requests
        start = time.time()
        for _ in range(5):
            await production_collector.collect_zipcode("85001")
        duration = time.time() - start
        
        # Should take at least 30 seconds with rate limiting
        assert duration >= 30
```

2. **Green Phase (1 hour)**: Deploy and verify
```bash
#!/bin/bash
# deploy.sh

echo "Deploying Phoenix MLS Scraper to production..."

# Run pre-flight checks
echo "Running pre-flight checks..."
python -m phoenix_real_estate.preflight_check

# Run security audit
echo "Running security audit..."
pytest tests/collectors/phoenix_mls/test_security.py -v

# Deploy application
echo "Deploying application..."
./deploy_to_production.sh phoenix-mls-scraper

# Run smoke tests
echo "Running smoke tests..."
pytest tests/smoke/test_phoenix_mls_live.py -v -m smoke

# Verify metrics endpoint
echo "Verifying metrics..."
curl -s http://localhost:9090/metrics | grep phoenix_mls

echo "Deployment complete!"
```

3. **Refactor Phase (45 min)**: Setup monitoring
```python
# Monitoring dashboard setup
class LaunchMonitor:
    """Monitor scraper during first 24 hours."""
    
    def __init__(self, collector):
        self.collector = collector
        self.start_time = time.time()
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "error_types": {}
        }
    
    async def monitor_health(self):
        """Monitor health metrics."""
        while time.time() - self.start_time < 86400:  # 24 hours
            # Check success rate
            success_rate = self.metrics["successful_requests"] / max(self.metrics["total_requests"], 1)
            if success_rate < 0.95:
                await self.alert_team(f"Success rate dropped to {success_rate:.2%}")
            
            # Check response times
            if self.metrics["response_times"]:
                avg_response = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
                if avg_response > 2.0:
                    await self.alert_team(f"Average response time is {avg_response:.2f}s")
            
            # Check proxy health
            proxy_stats = self.collector.scraper.proxy_manager.get_proxy_health_stats()
            if proxy_stats["healthy_proxies"] < 3:
                await self.alert_team(f"Only {proxy_stats['healthy_proxies']} healthy proxies")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def alert_team(self, message: str):
        """Send alert to team."""
        # Implementation would send actual alerts
        print(f"ALERT: {message}")
```

**Test-First Checkpoints**:
- [ ] Smoke tests define success criteria
- [ ] Tests verify production readiness
- [ ] Deployment successful
- [ ] Monitoring active
- [ ] 24h metrics within targets

---

## Updated Task Dependencies

```
Day 1:
TASK-05-001 (Setup + Tests) [1.5h]
    ├→ TASK-05-002 (Proxy Manager TDD) [4h]
    └→ TASK-05-003 (Anti-Detection TDD) [4h]

Day 2:
TASK-05-002 + TASK-05-003
    └→ TASK-05-004 (Scraper Engine TDD) [5h]
         ├→ TASK-05-005 (Data Extraction TDD) [4h]
         └→ TASK-05-006 (Error Handling TDD) [3h]

Day 3:
TASK-05-005 + TASK-05-006
    └→ TASK-05-007 (Collector Integration TDD) [4h]
         ├→ TASK-05-008 (Test Suite Completion) [4h]
         └→ TASK-05-009 (Documentation TDD) [2.5h]

Day 4:
TASK-05-008
    └→ TASK-05-010 (Security Audit TDD) [2.5h]
         └→ TASK-05-011 (Production Config TDD) [2.5h]
              └→ TASK-05-012 (Launch & Monitor) [2.5h + 24h]
```

## TDD Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tests Written First | 100% | All components have tests before implementation |
| Test Coverage | ≥90% | Automated coverage reports |
| Red-Green-Refactor | 100% | All tasks follow cycle |
| Test Execution Time | <5min | Fast feedback loop |
| Documentation Tests | 100% | Docs verified by tests |

## Key TDD Principles Applied

1. **Test First**: Every component has tests written before implementation
2. **Minimal Implementation**: Only write code to make tests pass
3. **Continuous Refactoring**: Improve code while keeping tests green
4. **Fast Feedback**: Tests run quickly for rapid iteration
5. **Living Documentation**: Tests serve as executable specifications