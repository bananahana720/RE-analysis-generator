"""Phoenix MLS Web Scraper.

Main scraper implementation using Playwright with anti-detection measures.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, quote
import re
from tenacity import retry, stop_after_attempt, wait_exponential
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter
from .proxy_manager import ProxyManager, NoHealthyProxiesError
from .anti_detection import AntiDetectionManager

logger = get_logger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class PropertyNotFoundError(ScraperError):
    """Raised when a property cannot be found."""
    pass


class RateLimitError(ScraperError):
    """Raised when rate limit is exceeded."""
    pass


class PhoenixMLSScraper:
    """Web scraper for PhoenixMLSSearch.com with anti-detection measures.
    
    Features:
    - Playwright-based browser automation
    - Proxy rotation and health monitoring
    - Anti-detection measures (user agent, viewport, behavior)
    - Rate limiting and retry logic
    - Session management
    """
    
    def __init__(self, config: Dict[str, Any], proxy_config: Dict[str, Any]):
        """Initialize the scraper with configuration.
        
        Args:
            config: Scraper configuration with:
                - base_url: Base URL for Phoenix MLS
                - max_retries: Maximum retry attempts
                - timeout: Request timeout in seconds
                - rate_limit: Rate limiting configuration
            proxy_config: Proxy manager configuration
        """
        self.config = config
        self.base_url = config.get("base_url", "https://www.phoenixmlssearch.com")
        self.search_endpoint = config.get("search_endpoint", "/search")
        self.max_retries = config.get("max_retries", 3)
        self.timeout_seconds = config.get("timeout", 30)
        self.timeout_ms = self.timeout_seconds * 1000  # Convert to milliseconds
        
        # Initialize managers
        self.proxy_manager = ProxyManager(proxy_config)
        self.anti_detection = AntiDetectionManager({})
        
        # Rate limiting
        rate_config = config.get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            requests_per_minute=rate_config.get("requests_per_minute", 60)
        )
        
        # Browser state
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0,
            "rate_limited": 0,
            "properties_scraped": 0
        }
        
        logger.info(f"PhoenixMLSScraper initialized with base URL: {self.base_url}")
    
    @property
    def timeout(self) -> int:
        """Get timeout in seconds for backward compatibility."""
        return self.timeout_seconds
    
    async def initialize_browser(self):
        """Initialize Playwright browser with anti-detection settings."""
        logger.info("Initializing browser with anti-detection measures")
        
        # Get proxy configuration
        proxy = await self.proxy_manager.get_next_proxy()
        proxy_url = self.proxy_manager.format_proxy_url(proxy)
        
        # Launch browser
        playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                f"--proxy-server={proxy_url}"
            ]
        }
        
        self.browser = await playwright.chromium.launch(**launch_options)
        
        # Create context with anti-detection settings
        viewport = self.anti_detection.get_viewport()
        user_agent = self.anti_detection.get_user_agent()
        
        context_options = {
            "viewport": {"width": viewport[0], "height": viewport[1]},
            "user_agent": user_agent,
            "java_script_enabled": True,
            "bypass_csp": True,
            "ignore_https_errors": True,
            "extra_http_headers": self.anti_detection.get_random_headers()
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Apply additional anti-detection measures
        await self.context.add_init_script("""
            // Override navigator properties
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(self.timeout_ms)
        
        logger.info("Browser initialized successfully")
    
    async def close_browser(self):
        """Close browser and cleanup resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        
        logger.info("Browser closed")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_properties_by_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Search for properties in a specific zipcode.
        
        Args:
            zipcode: The zipcode to search
            
        Returns:
            List of property data dictionaries
        """
        logger.info(f"Searching properties in zipcode: {zipcode}")
        
        # Rate limiting
        wait_time = await self.rate_limiter.wait_if_needed("phoenix_mls")
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        # Ensure browser is initialized
        if not self.page:
            await self.initialize_browser()
        
        try:
            # Navigate to search page
            search_url = urljoin(self.base_url, self.search_endpoint)
            await self.page.goto(search_url, wait_until="networkidle")
            
            # Human-like interaction
            await self.anti_detection.human_interaction_sequence(self.page)
            
            # Fill search form
            search_input = await self.page.wait_for_selector('input[name="search"], input[placeholder*="zip"], #zipcode-input')
            await search_input.click()
            
            # Clear and type with human-like delays
            await search_input.fill("")
            for char in zipcode:
                await search_input.type(char)
                await self.anti_detection.human_type_delay()
            
            # Submit search
            submit_button = await self.page.query_selector('button[type="submit"], button[aria-label*="Search"]')
            if submit_button:
                await submit_button.click()
            else:
                await search_input.press("Enter")
            
            # Wait for results
            await self.page.wait_for_selector('.property-card, .listing-item, .search-result', timeout=10000)
            
            # Random wait
            await self.anti_detection.random_wait(1, 2)
            
            # Extract property links
            properties = await self._extract_search_results()
            
            self.stats["successful_requests"] += 1
            self.stats["properties_scraped"] += len(properties)
            
            logger.info(f"Found {len(properties)} properties in zipcode {zipcode}")
            return properties
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            logger.error(f"Error searching properties in zipcode {zipcode}: {e}")
            raise
        finally:
            self.stats["total_requests"] += 1
    
    async def _extract_search_results(self) -> List[Dict[str, Any]]:
        """Extract property data from search results page."""
        properties = []
        
        # Get all property cards
        property_cards = await self.page.query_selector_all('.property-card, .listing-item')
        
        for card in property_cards:
            try:
                # Extract basic info from card
                property_data = {}
                
                # Property link
                link_element = await card.query_selector('a[href*="property"], a.property-link')
                if link_element:
                    property_data["url"] = await link_element.get_attribute("href")
                    if not property_data["url"].startswith("http"):
                        property_data["url"] = urljoin(self.base_url, property_data["url"])
                
                # Address
                address_element = await card.query_selector('.address, .property-address')
                if address_element:
                    property_data["address"] = await address_element.inner_text()
                
                # Price
                price_element = await card.query_selector('.price, .listing-price')
                if price_element:
                    property_data["price"] = await price_element.inner_text()
                
                # Basic details
                beds_element = await card.query_selector('.beds, [data-testid="beds"]')
                if beds_element:
                    property_data["beds"] = await beds_element.inner_text()
                
                baths_element = await card.query_selector('.baths, [data-testid="baths"]')
                if baths_element:
                    property_data["baths"] = await baths_element.inner_text()
                
                sqft_element = await card.query_selector('.sqft, [data-testid="sqft"]')
                if sqft_element:
                    property_data["sqft"] = await sqft_element.inner_text()
                
                if property_data.get("url"):
                    properties.append(property_data)
                
            except Exception as e:
                logger.warning(f"Error extracting property card data: {e}")
                continue
        
        return properties
    
    async def scrape_property_details(self, property_url: str) -> Dict[str, Any]:
        """Scrape detailed information for a specific property.
        
        Args:
            property_url: URL of the property detail page
            
        Returns:
            Dictionary with property details and raw HTML
        """
        logger.info(f"Scraping property details: {property_url}")
        
        # Rate limiting
        wait_time = await self.rate_limiter.wait_if_needed("phoenix_mls")
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        # Ensure browser is initialized
        if not self.page:
            await self.initialize_browser()
        
        try:
            # Navigate to property page
            await self.page.goto(property_url, wait_until="networkidle")
            
            # Human-like behavior
            await self.anti_detection.human_interaction_sequence(self.page)
            
            # Get raw HTML for future parsing
            raw_html = await self.page.content()
            
            # Extract detailed information
            details = await self._extract_property_details()
            details["url"] = property_url
            details["raw_html"] = raw_html
            details["scraped_at"] = datetime.utcnow().isoformat()
            
            self.stats["successful_requests"] += 1
            
            return details
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            logger.error(f"Error scraping property {property_url}: {e}")
            raise
        finally:
            self.stats["total_requests"] += 1
    
    async def _extract_property_details(self) -> Dict[str, Any]:
        """Extract detailed property information from property page."""
        details = {}
        
        # Address
        address_element = await self.page.query_selector('h1.address, .property-address, [data-testid="address"]')
        if address_element:
            details["address"] = await address_element.inner_text()
        
        # Price
        price_element = await self.page.query_selector('.price, .listing-price, [data-testid="price"]')
        if price_element:
            details["price"] = await price_element.inner_text()
        
        # Property details
        details_selectors = {
            "beds": ['.beds', '[data-testid="beds"]', '.bed-count'],
            "baths": ['.baths', '[data-testid="baths"]', '.bath-count'],
            "sqft": ['.sqft', '[data-testid="sqft"]', '.square-feet'],
            "lot_size": ['.lot-size', '[data-testid="lot-size"]', '.lot-area'],
            "year_built": ['.year-built', '[data-testid="year-built"]', '.built-year'],
            "property_type": ['.property-type', '[data-testid="property-type"]', '.type']
        }
        
        for key, selectors in details_selectors.items():
            for selector in selectors:
                element = await self.page.query_selector(selector)
                if element:
                    details[key] = await element.inner_text()
                    break
        
        # Description
        desc_element = await self.page.query_selector('.description, .property-description, [data-testid="description"]')
        if desc_element:
            details["description"] = await desc_element.inner_text()
        
        # Additional features
        features = []
        feature_elements = await self.page.query_selector_all('.feature-item, .amenity')
        for element in feature_elements:
            feature = await element.inner_text()
            if feature:
                features.append(feature.strip())
        
        if features:
            details["features"] = features
        
        # Images
        image_urls = []
        image_elements = await self.page.query_selector_all('.property-image img, .gallery img')
        for img in image_elements[:10]:  # Limit to 10 images
            src = await img.get_attribute("src")
            if src:
                if not src.startswith("http"):
                    src = urljoin(self.base_url, src)
                image_urls.append(src)
        
        if image_urls:
            details["images"] = image_urls
        
        return details
    
    async def handle_rate_limit(self):
        """Handle rate limit errors with exponential backoff."""
        self.stats["rate_limited"] += 1
        wait_time = min(60, 2 ** self.stats["rate_limited"])
        logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
        await asyncio.sleep(wait_time)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scraper statistics.
        
        Returns:
            Dictionary with scraping statistics
        """
        stats = self.stats.copy()
        
        # Calculate success rate
        if stats["total_requests"] > 0:
            stats["success_rate"] = (stats["successful_requests"] / stats["total_requests"]) * 100
        else:
            stats["success_rate"] = 0
        
        # Add proxy statistics
        stats["proxy_stats"] = self.proxy_manager.get_statistics()
        
        return stats
    
    async def scrape_properties_batch(self, property_urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple properties in batch with error recovery.
        
        Args:
            property_urls: List of property URLs to scrape
            
        Returns:
            List of successfully scraped properties
        """
        results = []
        failed_urls = []
        
        for url in property_urls:
            try:
                property_data = await self.scrape_property_details(url)
                results.append(property_data)
                
                # Random delay between requests
                await self.anti_detection.random_wait(2, 5)
                
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                failed_urls.append(url)
                
                # Handle specific errors
                if "rate limit" in str(e).lower():
                    await self.handle_rate_limit()
                elif isinstance(e, NoHealthyProxiesError):
                    logger.error("No healthy proxies available. Waiting for recovery...")
                    await asyncio.sleep(30)
                
                # Continue with next property
                continue
        
        if failed_urls:
            logger.warning(f"Failed to scrape {len(failed_urls)} properties: {failed_urls}")
        
        return results
    
    def validate_config(self) -> bool:
        """Validate scraper configuration.
        
        Returns:
            True if configuration is valid
        """
        required_fields = ["base_url"]
        
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Missing required configuration field: {field}")
                return False
        
        # Validate URL format
        if not self.base_url.startswith(("http://", "https://")):
            logger.error(f"Invalid base URL: {self.base_url}")
            return False
        
        return True
    
    def __repr__(self) -> str:
        """String representation of PhoenixMLSScraper."""
        return (
            f"PhoenixMLSScraper("
            f"base_url={self.base_url}, "
            f"requests={self.stats['total_requests']}, "
            f"success_rate={self.get_statistics()['success_rate']:.1f}%)"
        )