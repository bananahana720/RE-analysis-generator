"""Phoenix MLS Web Scraper.

Main scraper implementation using Playwright with anti-detection measures.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from urllib.parse import urljoin
from pathlib import Path
import pickle
from tenacity import retry, stop_after_attempt, wait_exponential
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter
from .proxy_manager import ProxyManager, NoHealthyProxiesError
from .anti_detection import AntiDetectionManager
from .captcha_handler import CaptchaHandler

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
    - Site-specific error pattern detection and automatic recovery
    """

    def __init__(self, config: Dict[str, Any], proxy_config: Optional[Dict[str, Any]] = None):
        """Initialize the scraper with configuration.

        Args:
            config: Scraper configuration with:
                - base_url: Base URL for Phoenix MLS
                - max_retries: Maximum retry attempts
                - timeout: Request timeout in seconds
                - rate_limit: Rate limiting configuration
            proxy_config: Optional proxy manager configuration
        """
        self.config = config
        self.base_url = config.get("base_url", "https://www.phoenixmlssearch.com")
        self.search_endpoint = config.get("search_endpoint", "/search")
        self.max_retries = config.get("max_retries", 3)
        self.timeout_seconds = config.get("timeout", 30)
        self.timeout_ms = self.timeout_seconds * 1000  # Convert to milliseconds

        # Initialize managers
        self.proxy_manager = ProxyManager(proxy_config) if proxy_config else None
        self.anti_detection = AntiDetectionManager({})

        # Initialize captcha handler
        captcha_config = config.get("captcha", {})
        self.captcha_handler = CaptchaHandler(captcha_config)

        # Rate limiting
        rate_config = config.get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            requests_per_minute=rate_config.get("requests_per_minute", 60)
        )

        # Browser state
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Session management
        self.cookies_path = Path(config.get("cookies_path", "data/cookies"))
        self.cookies_path.mkdir(parents=True, exist_ok=True)
        self.session_file = self.cookies_path / "phoenix_mls_session.pkl"
        self.cookies: List[Dict[str, Any]] = []
        self.local_storage: Dict[str, Any] = {}
        self.session_storage: Dict[str, Any] = {}

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0,
            "rate_limited": 0,
            "properties_scraped": 0,
            "errors_detected": {
                "rate_limit": 0,
                "blocked_ip": 0,
                "session_expired": 0,
                "captcha": 0,
                "maintenance": 0,
                "other": 0,
            },
        }

        logger.info(f"PhoenixMLSScraper initialized with base URL: {self.base_url}")

    @property
    def timeout(self) -> int:
        """Get timeout in seconds for backward compatibility."""
        return self.timeout_seconds

    async def initialize_browser(self):
        """Initialize Playwright browser with anti-detection settings."""
        logger.info("Initializing browser with anti-detection measures")

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
            ],
        }

        # Add proxy if available
        self._current_proxy = None
        if self.proxy_manager:
            try:
                proxy = await self.proxy_manager.get_next_proxy()
                self._current_proxy = proxy
                proxy_url = self.proxy_manager.format_proxy_url(proxy)
                launch_options["args"].append(f"--proxy-server={proxy_url}")
                logger.info(f"Using proxy: {proxy_url}")
            except NoHealthyProxiesError:
                logger.warning("No healthy proxies available, proceeding without proxy")
        else:
            logger.info("No proxy configuration, proceeding without proxy")

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
            "extra_http_headers": self.anti_detection.get_random_headers(),
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

        # Load existing session if available
        await self.load_session()

        logger.info("Browser initialized successfully")

    async def close_browser(self):
        """Close browser and cleanup resources."""
        # Save session before closing
        await self.save_session()

        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

        logger.info("Browser closed")

    async def load_session(self) -> bool:
        """Load saved session data (cookies, local storage, session storage).

        Returns:
            True if session was loaded successfully, False otherwise
        """
        if not self.session_file.exists():
            logger.info("No saved session found")
            return False

        try:
            with open(self.session_file, "rb") as f:
                session_data = pickle.load(f)

            self.cookies = session_data.get("cookies", [])
            self.local_storage = session_data.get("local_storage", {})
            self.session_storage = session_data.get("session_storage", {})

            # Apply session data to browser context if initialized
            if self.context and self.cookies:
                await self.context.add_cookies(self.cookies)
                logger.info(f"Loaded {len(self.cookies)} cookies from session")

            # Apply storage data if page exists
            if self.page:
                await self._restore_storage()

            logger.info("Session loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False

    async def save_session(self) -> bool:
        """Save current session data (cookies, local storage, session storage).

        Returns:
            True if session was saved successfully, False otherwise
        """
        if not self.context:
            logger.warning("No browser context to save session from")
            return False

        try:
            # Get current cookies
            self.cookies = await self.context.cookies()

            # Get storage data if page exists
            if self.page:
                await self._extract_storage()

            # Save session data
            session_data = {
                "cookies": self.cookies,
                "local_storage": self.local_storage,
                "session_storage": self.session_storage,
                "saved_at": datetime.now(UTC).isoformat(),
            }

            with open(self.session_file, "wb") as f:
                pickle.dump(session_data, f)

            logger.info(f"Session saved with {len(self.cookies)} cookies")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    async def _extract_storage(self):
        """Extract local storage and session storage from the current page."""
        if not self.page:
            return

        try:
            # Extract local storage
            self.local_storage = await self.page.evaluate("""
                () => {
                    const items = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        items[key] = localStorage.getItem(key);
                    }
                    return items;
                }
            """)

            # Extract session storage
            self.session_storage = await self.page.evaluate("""
                () => {
                    const items = {};
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        items[key] = sessionStorage.getItem(key);
                    }
                    return items;
                }
            """)

        except Exception as e:
            logger.warning(f"Failed to extract storage: {e}")

    async def _restore_storage(self):
        """Restore local storage and session storage to the current page."""
        if not self.page:
            return

        try:
            # Restore local storage
            if self.local_storage:
                await self.page.evaluate(
                    """
                    (items) => {
                        Object.entries(items).forEach(([key, value]) => {
                            localStorage.setItem(key, value);
                        });
                    }
                """,
                    self.local_storage,
                )

            # Restore session storage
            if self.session_storage:
                await self.page.evaluate(
                    """
                    (items) => {
                        Object.entries(items).forEach(([key, value]) => {
                            sessionStorage.setItem(key, value);
                        });
                    }
                """,
                    self.session_storage,
                )

        except Exception as e:
            logger.warning(f"Failed to restore storage: {e}")

    async def maintain_session(self) -> bool:
        """Maintain session by periodically saving cookies and checking session validity.

        This method should be called periodically during scraping to ensure
        session persistence and to handle session expiration gracefully.

        Returns:
            True if session is valid and maintained, False if session needs refresh
        """
        if not self.context or not self.page:
            logger.warning("No active browser session to maintain")
            return False

        try:
            # Save current session state
            await self.save_session()

            # Check if we're still logged in or session is valid
            # This checks for common indicators of active sessions
            session_valid = await self._check_session_validity()

            if not session_valid:
                logger.warning("Session appears to be invalid or expired")
                # Try to restore from saved session
                if await self.load_session():
                    # Re-check validity after restore
                    session_valid = await self._check_session_validity()
                    if session_valid:
                        logger.info("Session restored successfully")
                        return True
                return False

            logger.debug("Session is valid and maintained")
            return True

        except Exception as e:
            logger.error(f"Error maintaining session: {e}")
            return False

    async def _check_session_validity(self) -> bool:
        """Check if the current session is still valid.

        Returns:
            True if session appears valid, False otherwise
        """
        if not self.page:
            return False

        try:
            # Check for common session indicators
            # These selectors should be adjusted based on actual Phoenix MLS site
            session_indicators = [
                ".user-menu",  # User menu typically shown when logged in
                ".logout-button",  # Logout button presence
                "[data-user-id]",  # User ID attributes
                ".account-menu",  # Account menu
                "#user-dashboard",  # User dashboard elements
            ]

            for selector in session_indicators:
                element = await self.page.query_selector(selector)
                if element:
                    logger.debug(f"Found session indicator: {selector}")
                    return True

            # Check for login page indicators (negative check)
            login_indicators = [".login-form", "#login-button", ".signin-prompt"]

            for selector in login_indicators:
                element = await self.page.query_selector(selector)
                if element:
                    logger.debug(f"Found login indicator: {selector}")
                    return False

            # If we can't determine definitively, check cookies
            current_cookies = await self.context.cookies()
            # Look for session cookies (common names)
            session_cookie_names = [
                "session",
                "sess",
                "auth",
                "token",
                "PHPSESSID",
                "ASP.NET_SessionId",
            ]

            for cookie in current_cookies:
                if any(name in cookie.get("name", "").lower() for name in session_cookie_names):
                    # Check if cookie is not expired
                    expires = cookie.get("expires", float("inf"))
                    if expires > datetime.now(UTC).timestamp():
                        logger.debug(f"Found valid session cookie: {cookie['name']}")
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False

    async def clear_session(self):
        """Clear saved session data and current browser session.

        This removes all saved cookies, storage data, and deletes the session file.
        Useful for testing or when session data is corrupted.
        """
        try:
            # Clear in-memory session data
            self.cookies = []
            self.local_storage = {}
            self.session_storage = {}

            # Clear browser context cookies if available
            if self.context:
                await self.context.clear_cookies()
                logger.info("Cleared browser cookies")

            # Clear page storage if available
            if self.page:
                await self.page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
                logger.info("Cleared browser storage")

            # Delete session file
            if self.session_file.exists():
                self.session_file.unlink()
                logger.info(f"Deleted session file: {self.session_file}")

            logger.info("Session cleared successfully")

        except Exception as e:
            logger.error(f"Error clearing session: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
            response = await self.page.goto(search_url, wait_until="networkidle")

            # Check for captcha immediately after navigation
            if await self.captcha_handler.handle_captcha(
                self.page, response.status if response else None
            ):
                logger.info("Captcha detected and handled during navigation")
                # Wait for page to reload after captcha solution
                await self.page.wait_for_load_state("networkidle")

            # Human-like interaction
            await self.anti_detection.human_interaction_sequence(self.page)

            # Fill search form
            search_input = await self.page.wait_for_selector(
                'input[name="search"], input[placeholder*="zip"], #zipcode-input'
            )
            await search_input.click()

            # Clear and type with human-like delays
            await search_input.fill("")
            for char in zipcode:
                await search_input.type(char)
                await self.anti_detection.human_type_delay()

            # Submit search
            submit_button = await self.page.query_selector(
                'button[type="submit"], button[aria-label*="Search"]'
            )
            if submit_button:
                await submit_button.click()
            else:
                await search_input.press("Enter")

            # Wait for results
            await self.page.wait_for_selector(
                ".property-card, .listing-item, .search-result", timeout=10000
            )

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
        property_cards = await self.page.query_selector_all(".property-card, .listing-item")

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
                address_element = await card.query_selector(".address, .property-address")
                if address_element:
                    property_data["address"] = await address_element.inner_text()

                # Price
                price_element = await card.query_selector(".price, .listing-price")
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
            response = await self.page.goto(property_url, wait_until="networkidle")

            # Check for captcha after navigation
            if await self.captcha_handler.handle_captcha(
                self.page, response.status if response else None
            ):
                logger.info("Captcha detected and handled during property page navigation")
                await self.page.wait_for_load_state("networkidle")

            # Human-like behavior
            await self.anti_detection.human_interaction_sequence(self.page)

            # Get raw HTML for future parsing
            raw_html = await self.page.content()

            # Extract detailed information
            details = await self._extract_property_details()
            details["url"] = property_url
            details["raw_html"] = raw_html
            details["scraped_at"] = datetime.now(UTC).isoformat()

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
        address_element = await self.page.query_selector(
            'h1.address, .property-address, [data-testid="address"]'
        )
        if address_element:
            details["address"] = await address_element.inner_text()

        # Price
        price_element = await self.page.query_selector(
            '.price, .listing-price, [data-testid="price"]'
        )
        if price_element:
            details["price"] = await price_element.inner_text()

        # Property details
        details_selectors = {
            "beds": [".beds", '[data-testid="beds"]', ".bed-count"],
            "baths": [".baths", '[data-testid="baths"]', ".bath-count"],
            "sqft": [".sqft", '[data-testid="sqft"]', ".square-feet"],
            "lot_size": [".lot-size", '[data-testid="lot-size"]', ".lot-area"],
            "year_built": [".year-built", '[data-testid="year-built"]', ".built-year"],
            "property_type": [".property-type", '[data-testid="property-type"]', ".type"],
        }

        for key, selectors in details_selectors.items():
            for selector in selectors:
                element = await self.page.query_selector(selector)
                if element:
                    details[key] = await element.inner_text()
                    break

        # Description
        desc_element = await self.page.query_selector(
            '.description, .property-description, [data-testid="description"]'
        )
        if desc_element:
            details["description"] = await desc_element.inner_text()

        # Additional features
        features = []
        feature_elements = await self.page.query_selector_all(".feature-item, .amenity")
        for element in feature_elements:
            feature = await element.inner_text()
            if feature:
                features.append(feature.strip())

        if features:
            details["features"] = features

        # Images
        image_urls = []
        image_elements = await self.page.query_selector_all(".property-image img, .gallery img")
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
        if self.proxy_manager:
            stats["proxy_stats"] = self.proxy_manager.get_statistics()
        else:
            stats["proxy_stats"] = {"message": "No proxy configuration"}

        # Add captcha handling statistics
        stats["captcha_stats"] = self.captcha_handler.get_statistics()

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
        session_check_interval = 10  # Check session every 10 properties

        for idx, url in enumerate(property_urls):
            try:
                # Periodically maintain session
                if idx > 0 and idx % session_check_interval == 0:
                    if not await self.maintain_session():
                        logger.warning("Session maintenance failed, attempting to continue")

                property_data = await self.scrape_property_details(url)
                results.append(property_data)

                # Random delay between requests
                await self.anti_detection.random_wait(2, 5)

            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                failed_urls.append(url)

                # Check if this is a known error type that we can handle
                error_handled = False

                # Check for DataCollectionError with error detection context
                if hasattr(e, "context") and "error_type" in e.context:
                    error_type = e.context["error_type"]
                    if error_type in ["rate_limit", "blocked_ip", "session_expired"]:
                        logger.info(
                            f"Detected {error_type} error, already handled by error detection"
                        )
                        error_handled = True

                # Fallback to string-based detection for backward compatibility
                if not error_handled:
                    if "rate limit" in str(e).lower():
                        await self.handle_rate_limit()
                        error_handled = True
                    elif "captcha" in str(e).lower() or "verification" in str(e).lower():
                        logger.info("Potential captcha error detected in batch processing")
                        # Try to handle captcha on current page if available
                        if self.page:
                            try:
                                captcha_handled = await self.captcha_handler.handle_captcha(
                                    self.page
                                )
                                if captcha_handled:
                                    logger.info("Captcha handled successfully in batch processing")
                                    error_handled = True
                            except Exception as captcha_error:
                                logger.warning(
                                    f"Failed to handle captcha in batch: {captcha_error}"
                                )
                    elif isinstance(e, NoHealthyProxiesError):
                        logger.error("No healthy proxies available. Waiting for recovery...")
                        await asyncio.sleep(30)
                        error_handled = True

                # For CAPTCHA or human intervention required, break the batch
                if "captcha" in str(e).lower() or "human intervention" in str(e).lower():
                    logger.error(
                        "CAPTCHA or human intervention required. Stopping batch processing."
                    )
                    break

                # Continue with next property
                continue

        # Save session at the end of batch
        await self.save_session()

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
