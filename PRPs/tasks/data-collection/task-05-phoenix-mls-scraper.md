# Task 05: Phoenix MLS Web Scraper

## Purpose and Scope

Build a sophisticated web scraper for PhoenixMLSSearch.com that integrates seamlessly with Epic 1's foundation infrastructure while implementing advanced anti-detection techniques, proxy management, and intelligent data extraction. This task focuses on respectful, legal web scraping with comprehensive error handling and monitoring.

### Scope
- Playwright-based web scraper with stealth capabilities
- Proxy rotation management through Webshare.io
- Anti-detection techniques and browser fingerprint randomization
- Dynamic content handling and JavaScript execution
- Data extraction pipeline with Epic 1 integration
- Session management and cookie handling

### Out of Scope
- API-based data collection (covered in Task 4)
- LLM processing implementation (covered in Task 6)
- Multi-source orchestration (covered in Epic 3)

## Foundation Integration Requirements

### Epic 1 Dependencies (MANDATORY)
```python
# Configuration Management
from phoenix_real_estate.foundation.config.base import ConfigProvider

# Database Integration
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.database.schema import Property, PropertyFeatures, PropertyPrice

# Logging Framework
from phoenix_real_estate.foundation.logging.factory import get_logger

# Error Handling
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError, ValidationError, ConfigurationError
)

# Validation and Utilities
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.foundation.utils.helpers import (
    safe_int, safe_float, normalize_address, retry_async, is_valid_zipcode
)
```

## Acceptance Criteria

### AC-1: Proxy Management System
**Acceptance Criteria**: Robust proxy rotation with health monitoring

#### Proxy Manager (`src/phoenix_real_estate/collectors/phoenix_mls/proxy_manager.py`)
```python
"""Proxy rotation and management for PhoenixMLS scraping."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import ConfigurationError, DataCollectionError


class ProxyStatus(Enum):
    """Proxy health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    TESTING = "testing"


@dataclass
class ProxyInfo:
    """Proxy configuration and health information."""
    host: str
    port: int
    username: str
    password: str
    status: ProxyStatus = ProxyStatus.TESTING
    last_used: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    avg_response_time: float = 0.0
    last_health_check: Optional[datetime] = None


class ProxyManager:
    """Proxy rotation manager with health monitoring.
    
    Manages Webshare.io proxy pool with intelligent rotation,
    health monitoring, and failure recovery using Epic 1's
    configuration and logging systems.
    
    Example:
        Basic proxy manager usage:
        
        >>> from phoenix_real_estate.foundation.config.base import ConfigProvider
        >>> config = ConfigProvider()
        >>> manager = ProxyManager(config)
        >>> proxy_url = await manager.get_proxy()
        >>> # Use proxy for web scraping
        >>> await manager.report_result(proxy_url, success=True, response_time=1.2)
    """
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize proxy manager.
        
        Args:
            config: Configuration provider from Epic 1
            
        Raises:
            ConfigurationError: If proxy configuration is missing
        """
        self.config = config
        self.logger = get_logger("phoenix_mls.proxy_manager")
        
        # Load proxy configuration using Epic 1's ConfigProvider
        try:
            self.username = self.config.get_required("WEBSHARE_USERNAME")
            self.password = self.config.get_required("WEBSHARE_PASSWORD")
            self.proxy_endpoints = self.config.get(
                "WEBSHARE_ENDPOINTS",
                "premium-datacenter.webshare.io:8080,premium-datacenter.webshare.io:8081"
            ).split(",")
            
        except Exception as e:
            raise ConfigurationError(
                "Failed to load proxy configuration",
                context={"required_keys": ["WEBSHARE_USERNAME", "WEBSHARE_PASSWORD"]},
                cause=e
            ) from e
        
        # Initialize proxy pool
        self.proxies: List[ProxyInfo] = []
        self._initialize_proxy_pool()
        
        # Health monitoring configuration
        self.health_check_interval = self.config.get("PROXY_HEALTH_CHECK_INTERVAL", 300)
        self.max_failures = self.config.get("PROXY_MAX_FAILURES", 3)
        self.min_healthy_proxies = self.config.get("PROXY_MIN_HEALTHY", 2)
        
        # Usage tracking
        self._last_proxy_index = 0
        self._lock = asyncio.Lock()
        
        self.logger.info(
            "Proxy manager initialized",
            extra={
                "proxy_count": len(self.proxies),
                "health_check_interval": self.health_check_interval,
                "max_failures": self.max_failures
            }
        )
    
    def _initialize_proxy_pool(self) -> None:
        """Initialize proxy pool from configuration."""
        for endpoint in self.proxy_endpoints:
            host, port_str = endpoint.strip().split(":")
            port = int(port_str)
            
            proxy_info = ProxyInfo(
                host=host,
                port=port,
                username=self.username,
                password=self.password
            )
            self.proxies.append(proxy_info)
        
        self.logger.info(
            "Proxy pool initialized",
            extra={"proxy_endpoints": len(self.proxy_endpoints)}
        )
    
    async def get_proxy(self) -> str:
        """Get next available proxy URL.
        
        Returns:
            Proxy URL in format: http://username:password@host:port
            
        Raises:
            DataCollectionError: If no healthy proxies available
        """
        async with self._lock:
            healthy_proxies = [
                proxy for proxy in self.proxies 
                if proxy.status in [ProxyStatus.HEALTHY, ProxyStatus.TESTING]
            ]
            
            if not healthy_proxies:
                await self._attempt_proxy_recovery()
                healthy_proxies = [
                    proxy for proxy in self.proxies 
                    if proxy.status in [ProxyStatus.HEALTHY, ProxyStatus.TESTING]
                ]
                
                if not healthy_proxies:
                    raise DataCollectionError(
                        "No healthy proxies available",
                        context={
                            "total_proxies": len(self.proxies),
                            "failed_proxies": len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
                        }
                    )
            
            # Round-robin selection with some randomization
            if len(healthy_proxies) > 1:
                # Prefer proxies with better success rates
                proxy = max(healthy_proxies, key=lambda p: p.success_count / max(p.success_count + p.failure_count, 1))
                
                # Add some randomness to avoid patterns
                if random.random() < 0.3:  # 30% chance to pick randomly
                    proxy = random.choice(healthy_proxies)
            else:
                proxy = healthy_proxies[0]
            
            proxy.last_used = datetime.utcnow()
            
            proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            
            self.logger.debug(
                "Proxy selected",
                extra={
                    "proxy_host": proxy.host,
                    "proxy_port": proxy.port,
                    "proxy_status": proxy.status.value,
                    "success_rate": proxy.success_count / max(proxy.success_count + proxy.failure_count, 1)
                }
            )
            
            return proxy_url
    
    async def report_result(
        self, 
        proxy_url: str, 
        success: bool, 
        response_time: Optional[float] = None,
        error_details: Optional[str] = None
    ) -> None:
        """Report proxy usage result for health tracking.
        
        Args:
            proxy_url: Proxy URL that was used
            success: Whether the operation succeeded
            response_time: Response time in seconds
            error_details: Error details if operation failed
        """
        async with self._lock:
            # Find proxy by URL
            proxy = self._find_proxy_by_url(proxy_url)
            if not proxy:
                self.logger.warning(
                    "Unknown proxy URL in result report",
                    extra={"proxy_url": proxy_url[:50] + "..."}
                )
                return
            
            # Update statistics
            if success:
                proxy.success_count += 1
                if proxy.status == ProxyStatus.FAILED:
                    proxy.status = ProxyStatus.DEGRADED
                elif proxy.status == ProxyStatus.DEGRADED and proxy.success_count > proxy.failure_count:
                    proxy.status = ProxyStatus.HEALTHY
                elif proxy.status == ProxyStatus.TESTING:
                    proxy.status = ProxyStatus.HEALTHY
                
                if response_time:
                    # Update average response time with exponential smoothing
                    if proxy.avg_response_time == 0:
                        proxy.avg_response_time = response_time
                    else:
                        proxy.avg_response_time = 0.7 * proxy.avg_response_time + 0.3 * response_time
                
            else:
                proxy.failure_count += 1
                
                # Mark as failed if too many consecutive failures
                if proxy.failure_count >= self.max_failures:
                    proxy.status = ProxyStatus.FAILED
                elif proxy.status == ProxyStatus.HEALTHY:
                    proxy.status = ProxyStatus.DEGRADED
            
            total_requests = proxy.success_count + proxy.failure_count
            success_rate = proxy.success_count / max(total_requests, 1)
            
            self.logger.debug(
                "Proxy result reported",
                extra={
                    "proxy_host": proxy.host,
                    "proxy_port": proxy.port,
                    "success": success,
                    "response_time": response_time,
                    "success_rate": success_rate,
                    "status": proxy.status.value,
                    "error_details": error_details[:200] if error_details else None
                }
            )
    
    def _find_proxy_by_url(self, proxy_url: str) -> Optional[ProxyInfo]:
        """Find proxy info by URL."""
        for proxy in self.proxies:
            if f"{proxy.host}:{proxy.port}" in proxy_url:
                return proxy
        return None
    
    async def _attempt_proxy_recovery(self) -> None:
        """Attempt to recover failed proxies."""
        failed_proxies = [p for p in self.proxies if p.status == ProxyStatus.FAILED]
        
        if not failed_proxies:
            return
        
        self.logger.info(
            "Attempting proxy recovery",
            extra={"failed_proxy_count": len(failed_proxies)}
        )
        
        # Reset status for failed proxies to allow retry
        for proxy in failed_proxies:
            proxy.status = ProxyStatus.TESTING
            proxy.failure_count = 0  # Reset failure count for fresh start
        
        self.logger.info(
            "Proxy recovery attempted",
            extra={"recovered_proxy_count": len(failed_proxies)}
        )
    
    def get_proxy_health_stats(self) -> Dict[str, any]:
        """Get comprehensive proxy health statistics."""
        stats = {
            "total_proxies": len(self.proxies),
            "healthy_proxies": len([p for p in self.proxies if p.status == ProxyStatus.HEALTHY]),
            "degraded_proxies": len([p for p in self.proxies if p.status == ProxyStatus.DEGRADED]),
            "failed_proxies": len([p for p in self.proxies if p.status == ProxyStatus.FAILED]),
            "testing_proxies": len([p for p in self.proxies if p.status == ProxyStatus.TESTING]),
            "proxy_details": []
        }
        
        for proxy in self.proxies:
            total_requests = proxy.success_count + proxy.failure_count
            success_rate = proxy.success_count / max(total_requests, 1)
            
            stats["proxy_details"].append({
                "host": proxy.host,
                "port": proxy.port,
                "status": proxy.status.value,
                "success_count": proxy.success_count,
                "failure_count": proxy.failure_count,
                "success_rate": success_rate,
                "avg_response_time": proxy.avg_response_time,
                "last_used": proxy.last_used.isoformat() if proxy.last_used else None
            })
        
        return stats
```

### AC-2: Anti-Detection System
**Acceptance Criteria**: Advanced stealth techniques to avoid detection

#### Anti-Detection Module (`src/phoenix_real_estate/collectors/phoenix_mls/anti_detection.py`)
```python
"""Anti-detection techniques for web scraping."""

import random
from typing import Dict, List, Optional, Any
from playwright.async_api import Page, BrowserContext
from phoenix_real_estate.foundation.logging.factory import get_logger


class AntiDetectionManager:
    """Anti-detection techniques for web scraping.
    
    Implements various techniques to make web scraping appear more
    human-like and avoid detection systems.
    
    Example:
        Basic anti-detection usage:
        
        >>> manager = AntiDetectionManager()
        >>> await manager.setup_page(page)
        >>> await manager.human_like_actions(page)
    """
    
    def __init__(self, logger_name: str = "phoenix_mls.anti_detection") -> None:
        """Initialize anti-detection manager."""
        self.logger = get_logger(logger_name)
        
        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        ]
        
        # Screen resolutions for viewport randomization
        self.screen_resolutions = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
            {"width": 1600, "height": 900}
        ]
        
        self.logger.info("Anti-detection manager initialized")
    
    async def setup_browser_context(self, context: BrowserContext) -> None:
        """Setup browser context with anti-detection measures."""
        # Randomize user agent
        user_agent = random.choice(self.user_agents)
        await context.set_extra_http_headers({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        })
        
        self.logger.debug(
            "Browser context configured",
            extra={"user_agent": user_agent[:50] + "..."}
        )
    
    async def setup_page(self, page: Page) -> None:
        """Setup page with anti-detection measures.
        
        Args:
            page: Playwright page object
        """
        # Randomize viewport
        resolution = random.choice(self.screen_resolutions)
        await page.set_viewport_size(
            width=resolution["width"],
            height=resolution["height"]
        )
        
        # Remove webdriver indicators
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {},
            };
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        # Set random timezone
        timezones = [
            'America/New_York',
            'America/Chicago', 
            'America/Denver',
            'America/Los_Angeles',
            'America/Phoenix'
        ]
        await page.emulate_timezone(random.choice(timezones))
        
        # Set random geolocation (within Arizona)
        await page.set_geolocation({
            'latitude': 33.4484 + random.uniform(-0.5, 0.5),
            'longitude': -112.0740 + random.uniform(-0.5, 0.5)
        })
        
        self.logger.debug(
            "Page anti-detection configured",
            extra={
                "viewport": f"{resolution['width']}x{resolution['height']}",
                "timezone": timezones[0]  # Don't log actual timezone for privacy
            }
        )
    
    async def human_like_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """Add human-like delay between actions.
        
        Args:
            min_seconds: Minimum delay time
            max_seconds: Maximum delay time
        """
        import asyncio
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
        
        self.logger.debug(
            "Human-like delay applied",
            extra={"delay_seconds": round(delay, 2)}
        )
    
    async def human_like_mouse_movement(self, page: Page, element_selector: str) -> None:
        """Perform human-like mouse movement to element.
        
        Args:
            page: Playwright page object
            element_selector: CSS selector of target element
        """
        try:
            # Get element bounding box
            element = page.locator(element_selector)
            box = await element.bounding_box()
            
            if box:
                # Add some randomness to click position
                x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
                y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
                
                # Move mouse in steps for more human-like behavior
                current_pos = await page.evaluate("() => [window.mouseX || 0, window.mouseY || 0]")
                steps = 3 + random.randint(0, 2)
                
                for i in range(steps):
                    step_x = current_pos[0] + (x - current_pos[0]) * (i + 1) / steps
                    step_y = current_pos[1] + (y - current_pos[1]) * (i + 1) / steps
                    
                    await page.mouse.move(step_x, step_y)
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                
                self.logger.debug(
                    "Human-like mouse movement completed",
                    extra={"target_element": element_selector}
                )
                
        except Exception as e:
            self.logger.warning(
                "Mouse movement failed",
                extra={"element": element_selector, "error": str(e)}
            )
    
    async def human_like_typing(self, page: Page, element_selector: str, text: str) -> None:
        """Type text in human-like manner.
        
        Args:
            page: Playwright page object
            element_selector: CSS selector of input element
            text: Text to type
        """
        try:
            await page.click(element_selector)
            await self.human_like_delay(0.2, 0.5)
            
            # Type character by character with random delays
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            self.logger.debug(
                "Human-like typing completed",
                extra={
                    "element": element_selector,
                    "text_length": len(text)
                }
            )
            
        except Exception as e:
            self.logger.warning(
                "Human-like typing failed",
                extra={
                    "element": element_selector,
                    "error": str(e)
                }
            )
    
    async def randomize_request_timing(self) -> None:
        """Add randomized delays between requests."""
        # Base delay with exponential randomization
        base_delay = random.uniform(2.0, 5.0)
        additional_delay = random.expovariate(0.5)  # Exponential distribution
        total_delay = min(base_delay + additional_delay, 15.0)  # Cap at 15 seconds
        
        await asyncio.sleep(total_delay)
        
        self.logger.debug(
            "Request timing randomized",
            extra={"delay_seconds": round(total_delay, 2)}
        )
    
    def get_random_user_agent(self) -> str:
        """Get random user agent string."""
        return random.choice(self.user_agents)
    
    def get_random_viewport(self) -> Dict[str, int]:
        """Get random viewport size."""
        return random.choice(self.screen_resolutions)
```

### AC-3: Web Scraper Implementation
**Acceptance Criteria**: Playwright-based scraper with dynamic content handling

#### PhoenixMLS Scraper (`src/phoenix_real_estate/collectors/phoenix_mls/scraper.py`)
```python
"""PhoenixMLSSearch.com web scraper with anti-detection."""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import DataCollectionError
from phoenix_real_estate.foundation.utils.helpers import retry_async, is_valid_zipcode
from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
from phoenix_real_estate.collectors.phoenix_mls.anti_detection import AntiDetectionManager


class PhoenixMLSScraper:
    """Web scraper for PhoenixMLSSearch.com.
    
    Implements advanced web scraping with anti-detection techniques,
    proxy rotation, and comprehensive error handling using Epic 1's
    foundation infrastructure.
    
    Example:
        Basic scraper usage:
        
        >>> from phoenix_real_estate.foundation.config.base import ConfigProvider
        >>> config = ConfigProvider()
        >>> scraper = PhoenixMLSScraper(config)
        >>> async with scraper:
        >>>     properties = await scraper.search_zipcode("85031")
    """
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize PhoenixMLS scraper.
        
        Args:
            config: Configuration provider from Epic 1
        """
        self.config = config
        self.logger = get_logger("phoenix_mls.scraper")
        
        # Initialize managers
        self.proxy_manager = ProxyManager(config)
        self.anti_detection = AntiDetectionManager("phoenix_mls.anti_detection")
        
        # Scraping configuration
        self.base_url = self.config.get("PHOENIX_MLS_BASE_URL", "https://phoenixmlssearch.com")
        self.max_retries = self.config.get("PHOENIX_MLS_MAX_RETRIES", 3)
        self.page_timeout = self.config.get("PHOENIX_MLS_TIMEOUT", 30000)
        self.respect_robots = self.config.get("RESPECT_ROBOTS_TXT", True)
        
        # Browser management
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        self.logger.info(
            "PhoenixMLS scraper initialized",
            extra={
                "base_url": self.base_url,
                "max_retries": self.max_retries,
                "page_timeout": self.page_timeout
            }
        )
    
    async def __aenter__(self) -> "PhoenixMLSScraper":
        """Async context manager entry."""
        await self._setup_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self._cleanup_browser()
    
    async def _setup_browser(self) -> None:
        """Setup Playwright browser with proxy and anti-detection."""
        try:
            self.playwright = await async_playwright().start()
            
            # Get proxy for this session
            proxy_url = await self.proxy_manager.get_proxy()
            proxy_parts = proxy_url.replace("http://", "").split("@")
            auth_part = proxy_parts[0]
            server_part = proxy_parts[1]
            
            username, password = auth_part.split(":")
            server_host, server_port = server_part.split(":")
            
            # Launch browser with proxy
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                proxy={
                    "server": f"http://{server_host}:{server_port}",
                    "username": username,
                    "password": password
                },
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu"
                ]
            )
            
            # Create context with anti-detection
            self.context = await self.browser.new_context()
            await self.anti_detection.setup_browser_context(self.context)
            
            self._current_proxy_url = proxy_url
            
            self.logger.info(
                "Browser setup completed",
                extra={
                    "proxy_host": server_host,
                    "proxy_port": server_port
                }
            )
            
        except Exception as e:
            await self._cleanup_browser()
            raise DataCollectionError(
                "Failed to setup browser",
                context={"error": str(e)},
                cause=e
            ) from e
    
    async def _cleanup_browser(self) -> None:
        """Cleanup browser resources."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.logger.debug("Browser cleanup completed")
            
        except Exception as e:
            self.logger.warning(
                "Browser cleanup had errors",
                extra={"error": str(e)}
            )
    
    async def search_zipcode(self, zipcode: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Search properties by ZIP code.
        
        Args:
            zipcode: ZIP code to search
            max_pages: Maximum pages to scrape
            
        Returns:
            List of property data dictionaries
            
        Raises:
            DataCollectionError: If search fails
        """
        if not is_valid_zipcode(zipcode):
            raise DataCollectionError(
                f"Invalid ZIP code format: {zipcode}",
                context={"zipcode": zipcode}
            )
        
        try:
            self.logger.info(
                "Starting zipcode search",
                extra={
                    "zipcode": zipcode,
                    "max_pages": max_pages,
                    "source": "phoenix_mls"
                }
            )
            
            properties = []
            
            for page_num in range(1, max_pages + 1):
                try:
                    page_properties = await self._scrape_search_page(zipcode, page_num)
                    
                    if not page_properties:
                        self.logger.info(
                            "No more properties found, stopping pagination",
                            extra={
                                "zipcode": zipcode,
                                "last_page": page_num
                            }
                        )
                        break
                    
                    properties.extend(page_properties)
                    
                    self.logger.debug(
                        "Page scraping completed",
                        extra={
                            "zipcode": zipcode,
                            "page": page_num,
                            "properties_found": len(page_properties),
                            "total_properties": len(properties)
                        }
                    )
                    
                    # Human-like delay between pages
                    await self.anti_detection.randomize_request_timing()
                    
                except Exception as e:
                    self.logger.warning(
                        "Page scraping failed, continuing with next page",
                        extra={
                            "zipcode": zipcode,
                            "page": page_num,
                            "error": str(e)
                        }
                    )
                    continue
            
            self.logger.info(
                "Zipcode search completed",
                extra={
                    "zipcode": zipcode,
                    "total_properties": len(properties),
                    "pages_scraped": min(page_num, max_pages),
                    "source": "phoenix_mls"
                }
            )
            
            return properties
            
        except Exception as e:
            self.logger.error(
                "Zipcode search failed",
                extra={
                    "zipcode": zipcode,
                    "error": str(e),
                    "source": "phoenix_mls"
                }
            )
            raise DataCollectionError(
                f"Failed to search properties for zipcode {zipcode}",
                context={"zipcode": zipcode, "source": "phoenix_mls"},
                cause=e
            ) from e
    
    async def _scrape_search_page(self, zipcode: str, page_num: int) -> List[Dict[str, Any]]:
        """Scrape a single search results page.
        
        Args:
            zipcode: ZIP code being searched
            page_num: Page number to scrape
            
        Returns:
            List of properties found on this page
        """
        async def _scrape_page() -> List[Dict[str, Any]]:
            """Internal scraping function for retry wrapper."""
            page = await self.context.new_page()
            
            try:
                await self.anti_detection.setup_page(page)
                
                # Navigate to search page
                search_url = f"{self.base_url}/search?zipcode={zipcode}&page={page_num}"
                
                start_time = datetime.utcnow()
                response = await page.goto(search_url, timeout=self.page_timeout)
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                if not response or response.status >= 400:
                    await self.proxy_manager.report_result(
                        self._current_proxy_url,
                        success=False,
                        response_time=response_time,
                        error_details=f"HTTP {response.status if response else 'No response'}"
                    )
                    raise DataCollectionError(f"Failed to load search page: HTTP {response.status if response else 'No response'}")
                
                # Wait for dynamic content to load
                await page.wait_for_load_state("domcontentloaded")
                await self.anti_detection.human_like_delay(1.0, 2.0)
                
                # Extract property listings
                properties = await self._extract_property_listings(page)
                
                # Report successful proxy usage
                await self.proxy_manager.report_result(
                    self._current_proxy_url,
                    success=True,
                    response_time=response_time
                )
                
                return properties
                
            finally:
                await page.close()
        
        # Use Epic 1's retry utility
        return await retry_async(
            _scrape_page,
            max_retries=self.max_retries,
            delay=2.0,
            backoff_factor=2.0
        )
    
    async def _extract_property_listings(self, page: Page) -> List[Dict[str, Any]]:
        """Extract property listings from search results page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of extracted property data
        """
        try:
            # Wait for listings to load
            await page.wait_for_selector(".property-listing", timeout=10000)
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            properties = []
            listing_elements = soup.find_all(class_="property-listing")
            
            for listing in listing_elements:
                try:
                    property_data = self._parse_listing_element(listing)
                    if property_data:
                        properties.append(property_data)
                        
                except Exception as e:
                    self.logger.warning(
                        "Failed to parse individual listing",
                        extra={"error": str(e)}
                    )
                    continue
            
            self.logger.debug(
                "Property listings extracted",
                extra={
                    "listings_found": len(listing_elements),
                    "properties_parsed": len(properties)
                }
            )
            
            return properties
            
        except Exception as e:
            self.logger.error(
                "Failed to extract property listings",
                extra={"error": str(e)}
            )
            raise DataCollectionError(
                "Failed to extract property listings from page",
                cause=e
            ) from e
    
    def _parse_listing_element(self, listing_element) -> Optional[Dict[str, Any]]:
        """Parse individual property listing element.
        
        Args:
            listing_element: BeautifulSoup element containing property data
            
        Returns:
            Property data dictionary or None if parsing fails
        """
        try:
            # Extract basic information (adapt selectors based on actual site structure)
            address_elem = listing_element.find(class_="property-address")
            price_elem = listing_element.find(class_="property-price")
            details_elem = listing_element.find(class_="property-details")
            
            if not address_elem:
                return None
            
            # Extract property details
            property_data = {
                "source": "phoenix_mls",
                "scraped_at": datetime.utcnow().isoformat(),
                "address": address_elem.get_text(strip=True) if address_elem else "",
                "price": price_elem.get_text(strip=True) if price_elem else "",
                "details": details_elem.get_text(strip=True) if details_elem else "",
                "raw_html": str(listing_element)  # Store for LLM processing
            }
            
            # Extract additional structured data if available
            beds_elem = listing_element.find(class_="beds")
            baths_elem = listing_element.find(class_="baths")
            sqft_elem = listing_element.find(class_="sqft")
            
            if beds_elem:
                property_data["beds"] = beds_elem.get_text(strip=True)
            if baths_elem:
                property_data["baths"] = baths_elem.get_text(strip=True)
            if sqft_elem:
                property_data["sqft"] = sqft_elem.get_text(strip=True)
            
            return property_data
            
        except Exception as e:
            self.logger.debug(
                "Failed to parse listing element",
                extra={"error": str(e)}
            )
            return None
    
    async def get_property_details(self, property_url: str) -> Optional[Dict[str, Any]]:
        """Get detailed property information from property page.
        
        Args:
            property_url: URL of property details page
            
        Returns:
            Detailed property data or None if not found
        """
        async def _scrape_details() -> Optional[Dict[str, Any]]:
            """Internal details scraping function."""
            page = await self.context.new_page()
            
            try:
                await self.anti_detection.setup_page(page)
                
                start_time = datetime.utcnow()
                response = await page.goto(property_url, timeout=self.page_timeout)
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                if not response or response.status >= 400:
                    await self.proxy_manager.report_result(
                        self._current_proxy_url,
                        success=False,
                        response_time=response_time,
                        error_details=f"HTTP {response.status if response else 'No response'}"
                    )
                    return None
                
                # Wait for content to load
                await page.wait_for_load_state("domcontentloaded")
                await self.anti_detection.human_like_delay(1.0, 2.0)
                
                # Extract detailed property information
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                property_details = {
                    "source": "phoenix_mls",
                    "property_url": property_url,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "full_html": content,  # Store for LLM processing
                    "structured_data": self._extract_structured_details(soup)
                }
                
                # Report successful proxy usage
                await self.proxy_manager.report_result(
                    self._current_proxy_url,
                    success=True,
                    response_time=response_time
                )
                
                return property_details
                
            finally:
                await page.close()
        
        # Use Epic 1's retry utility
        return await retry_async(
            _scrape_details,
            max_retries=self.max_retries,
            delay=2.0,
            backoff_factor=2.0
        )
    
    def _extract_structured_details(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data from property details page.
        
        Args:
            soup: BeautifulSoup object of property page
            
        Returns:
            Dictionary of structured property details
        """
        details = {}
        
        try:
            # Extract key property details (adapt selectors based on actual site)
            details_table = soup.find("table", class_="property-details-table")
            if details_table:
                rows = details_table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower().replace(" ", "_")
                        value = cells[1].get_text(strip=True)
                        details[key] = value
            
            # Extract description
            description_elem = soup.find(class_="property-description")
            if description_elem:
                details["description"] = description_elem.get_text(strip=True)
            
            # Extract features list
            features_elem = soup.find(class_="property-features")
            if features_elem:
                features = []
                feature_items = features_elem.find_all("li")
                for item in feature_items:
                    features.append(item.get_text(strip=True))
                details["features"] = features
            
        except Exception as e:
            self.logger.debug(
                "Failed to extract structured details",
                extra={"error": str(e)}
            )
        
        return details
```

### AC-4: PhoenixMLS Collector Implementation
**Acceptance Criteria**: Complete collector integrating scraper and Epic 1 foundation

#### PhoenixMLS Collector (`src/phoenix_real_estate/collectors/phoenix_mls/collector.py`)
```python
"""PhoenixMLS data collector implementation."""

from typing import List, Dict, Any, Optional

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.foundation.utils.exceptions import DataCollectionError
from phoenix_real_estate.collectors.base.collector import DataCollector
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from phoenix_real_estate.collectors.phoenix_mls.adapter import PhoenixMLSAdapter


class PhoenixMLSCollector(DataCollector):
    """Data collector for PhoenixMLSSearch.com.
    
    Implements web scraping with anti-detection and proxy rotation,
    integrating seamlessly with Epic 1's foundation infrastructure.
    
    Example:
        Basic collector usage:
        
        >>> from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository
        >>> config = ConfigProvider()
        >>> repository = PropertyRepository(...)
        >>> collector = PhoenixMLSCollector(config, repository, "phoenix_mls.collector")
        >>> properties = await collector.collect_zipcode("85031")
    """
    
    def __init__(
        self, 
        config: ConfigProvider, 
        repository: PropertyRepository,
        logger_name: str
    ) -> None:
        """Initialize PhoenixMLS collector.
        
        Args:
            config: Configuration provider from Epic 1
            repository: Property repository from Epic 1
            logger_name: Logger name for structured logging
        """
        super().__init__(config, repository, logger_name)
        
        # Initialize validator using Epic 1's framework
        self.validator = DataValidator()
        
        # Initialize scraper and adapter
        self.scraper = PhoenixMLSScraper(config)
        self.adapter = PhoenixMLSAdapter(self.validator, f"{logger_name}.adapter")
        
        self.logger.info(
            "PhoenixMLS collector initialized",
            extra={
                "source": self.get_source_name(),
                "collector_type": "web_scraper"
            }
        )
    
    def get_source_name(self) -> str:
        """Return source name for identification."""
        return "phoenix_mls"
    
    async def collect_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Collect properties for given ZIP code.
        
        Args:
            zipcode: ZIP code to search
            
        Returns:
            List of raw property data dictionaries
            
        Raises:
            DataCollectionError: If collection fails
        """
        try:
            self.logger.info(
                "Starting zipcode collection",
                extra={
                    "zipcode": zipcode,
                    "source": self.get_source_name()
                }
            )
            
            async with self.scraper as scraper:
                raw_properties = await scraper.search_zipcode(zipcode)
            
            self.logger.info(
                "Zipcode collection completed",
                extra={
                    "zipcode": zipcode,
                    "properties_collected": len(raw_properties),
                    "source": self.get_source_name()
                }
            )
            
            return raw_properties
            
        except Exception as e:
            self.logger.error(
                "Zipcode collection failed",
                extra={
                    "zipcode": zipcode,
                    "error": str(e),
                    "source": self.get_source_name()
                }
            )
            raise DataCollectionError(
                f"Failed to collect properties for zipcode {zipcode}",
                context={"zipcode": zipcode, "source": self.get_source_name()},
                cause=e
            ) from e
    
    async def collect_property_details(self, property_url: str) -> Optional[Dict[str, Any]]:
        """Collect detailed information for specific property.
        
        Args:
            property_url: URL of property details page
            
        Returns:
            Property details dictionary or None if not found
            
        Raises:
            DataCollectionError: If collection fails
        """
        try:
            self.logger.debug(
                "Collecting property details",
                extra={
                    "property_url": property_url,
                    "source": self.get_source_name()
                }
            )
            
            async with self.scraper as scraper:
                property_details = await scraper.get_property_details(property_url)
            
            if property_details:
                self.logger.debug(
                    "Property details collected",
                    extra={
                        "property_url": property_url,
                        "source": self.get_source_name()
                    }
                )
            
            return property_details
            
        except Exception as e:
            self.logger.error(
                "Property details collection failed",
                extra={
                    "property_url": property_url,
                    "error": str(e),
                    "source": self.get_source_name()
                }
            )
            raise DataCollectionError(
                f"Failed to collect details for property {property_url}",
                context={"property_url": property_url, "source": self.get_source_name()},
                cause=e
            ) from e
    
    async def adapt_property(self, raw_data: Dict[str, Any]) -> Property:
        """Adapt raw property data to internal schema.
        
        Args:
            raw_data: Raw property data from scraper
            
        Returns:
            Validated Property object
            
        Raises:
            ValidationError: If adaptation fails
        """
        return await self.adapter.adapt_property(raw_data)
```

## Technical Approach

### Epic 1 Foundation Integration Strategy
1. **Configuration**: Use Epic 1's ConfigProvider for proxy settings and scraping parameters
2. **Database**: Use Epic 1's PropertyRepository for all data persistence  
3. **Logging**: Use Epic 1's structured logging for monitoring and debugging
4. **Error Handling**: Follow Epic 1's exception hierarchy patterns
5. **Validation**: Use Epic 1's DataValidator and utility helpers

### Anti-Detection Strategy
1. **Browser Fingerprinting**: Randomize user agents, viewports, and browser properties
2. **Human-like Behavior**: Random delays, mouse movements, and typing patterns
3. **Proxy Rotation**: Use residential proxies with health monitoring
4. **Request Timing**: Exponential delays with randomization
5. **Session Management**: Proper cookie handling and session rotation

### Development Process
1. **Proxy Management**: Implement robust proxy rotation with health monitoring
2. **Anti-Detection**: Advanced stealth techniques for avoiding detection
3. **Web Scraping**: Playwright-based scraping with dynamic content handling
4. **Data Extraction**: BeautifulSoup parsing with LLM preparation
5. **Integration Testing**: Comprehensive tests validating Epic 1 integration

## Dependencies

### Epic 1 Foundation (REQUIRED)
- Configuration management for proxy credentials and scraping settings
- PropertyRepository for data persistence
- Structured logging framework
- Exception hierarchy and error handling patterns
- Data validation utilities and helpers

### External Dependencies
- `playwright`: Modern web automation and scraping
- `beautifulsoup4`: HTML parsing and data extraction
- `aiohttp`: HTTP client support

### System Dependencies
- Chromium browser (installed by Playwright)
- Network access to PhoenixMLSSearch.com
- Valid Webshare.io proxy credentials

## Risk Assessment

### High Risk
- **Detection and Blocking**: Website detecting scraping and blocking IP addresses
  - **Mitigation**: Advanced anti-detection techniques and proxy rotation
  - **Contingency**: Backup proxy service and detection evasion updates

### Medium Risk
- **Website Structure Changes**: PhoenixMLS changing page structure or selectors
  - **Mitigation**: Flexible parsing with fallback extraction methods
  - **Contingency**: LLM-based extraction for structure changes

### Low Risk
- **Proxy Service Issues**: Webshare.io service degradation
  - **Mitigation**: Health monitoring and automatic failover
  - **Contingency**: Direct connection with reduced functionality

## Testing Requirements

### Unit Tests
- Proxy manager health monitoring and rotation
- Anti-detection techniques effectiveness
- HTML parsing and data extraction accuracy
- Error handling with Epic 1 patterns

### Integration Tests
- Full Epic 1 foundation integration
- End-to-end web scraping with real sites
- Proxy rotation under various conditions
- Performance under rate limiting

### Security Tests
- Proxy credential security
- Anti-detection effectiveness
- Legal compliance verification
- Data privacy protection

## Interface Specifications

### For Epic 3 Orchestration
```python
# Epic 3 will use these interfaces
from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector
from phoenix_real_estate.collectors.base import DataCollector

# Scraper orchestration
collector = PhoenixMLSCollector(config, repository, "orchestration.phoenix_mls")
properties = await collector.collect_zipcode("85031")
```

### For Epic 6 LLM Processing
```python
# Epic 6 will process scraped HTML content
raw_data = {
    "raw_html": "<div class='property-listing'>...</div>",
    "full_html": "<!DOCTYPE html>...",
    "source": "phoenix_mls"
}
# LLM will extract structured data from HTML
```

---

**Task Owner**: Data Engineering Team  
**Estimated Effort**: 3-4 days  
**Priority**: High (core data collection capability)  
**Status**: Ready for Implementation