"""Anti-Detection Manager for Phoenix MLS Scraper.

Implements browser fingerprinting countermeasures and human-like behavior.
"""

import asyncio
import random
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import json

from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class AntiDetectionManager:
    """Manages anti-detection measures for web scraping.
    
    Features:
    - User agent rotation
    - Viewport randomization
    - Human-like typing and mouse movements
    - Browser fingerprint randomization
    - Realistic interaction patterns
    """
    
    # Default user agents if none provided
    DEFAULT_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    
    # Default viewport sizes
    DEFAULT_VIEWPORTS = [
        (1920, 1080),  # Full HD
        (1366, 768),   # Common laptop
        (1440, 900),   # MacBook
        (1536, 864),   # Surface
        (1600, 900),   # HD+
        (1280, 720),   # HD
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize AntiDetectionManager with configuration.
        
        Args:
            config: Configuration dictionary with:
                - user_agents: List of user agent strings
                - viewports: List of (width, height) tuples
                - typing_delay_range: Tuple of (min_ms, max_ms)
        """
        self.config = config
        self.user_agents = config.get("user_agents", self.DEFAULT_USER_AGENTS)
        self.viewports = config.get("viewports", self.DEFAULT_VIEWPORTS)
        self.typing_delay_range = config.get("typing_delay_range", (50, 200))
        
        logger.info(
            f"AntiDetectionManager initialized with {len(self.user_agents)} user agents "
            f"and {len(self.viewports)} viewports"
        )
    
    def get_user_agent(self) -> str:
        """Get a random user agent string.
        
        Returns:
            Random user agent from configured list
        """
        agent = random.choice(self.user_agents)
        logger.debug(f"Selected user agent: {agent[:50]}...")
        return agent
    
    def get_viewport(self) -> Tuple[int, int]:
        """Get random viewport dimensions.
        
        Returns:
            Tuple of (width, height)
        """
        viewport = random.choice(self.viewports)
        logger.debug(f"Selected viewport: {viewport[0]}x{viewport[1]}")
        return viewport
    
    async def human_type_delay(self):
        """Simulate human typing delay between keystrokes."""
        delay_ms = random.randint(*self.typing_delay_range)
        await asyncio.sleep(delay_ms / 1000)
    
    async def random_mouse_movement(self, page):
        """Perform random mouse movements on the page.
        
        Args:
            page: Playwright page object
        """
        # Get current viewport size
        viewport = await page.viewport_size()
        if not viewport:
            viewport = {"width": 1920, "height": 1080}
        
        # Generate random coordinates within viewport
        x = random.randint(100, min(viewport["width"] - 100, 1820))
        y = random.randint(100, min(viewport["height"] - 100, 980))
        
        # Move mouse with random steps
        steps = random.randint(5, 15)
        await page.mouse.move(x, y, steps=steps)
        
        logger.debug(f"Mouse moved to ({x}, {y}) in {steps} steps")
    
    async def configure_browser_context(self, context):
        """Configure browser context with anti-detection settings.
        
        Args:
            context: Playwright browser context
        """
        # Set random user agent
        user_agent = self.get_user_agent()
        await context.set_extra_http_headers({
            "User-Agent": user_agent
        })
        
        # Note: Viewport is set during context creation in scraper.py
        # This method focuses on headers and other runtime settings
        
        logger.info("Browser context configured with anti-detection settings")
    
    async def random_scroll(self, page):
        """Perform random scrolling on the page.
        
        Args:
            page: Playwright page object
        """
        scroll_options = [
            # Scroll down by random amount
            f"window.scrollBy(0, {random.randint(100, 500)})",
            # Scroll to random position
            f"window.scrollTo(0, {random.randint(200, 1000)})",
            # Smooth scroll
            f"window.scrollBy({{top: {random.randint(100, 300)}, behavior: 'smooth'}})"
        ]
        
        scroll_script = random.choice(scroll_options)
        await page.evaluate(scroll_script)
        
        # Wait for scroll to complete
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        logger.debug(f"Executed scroll: {scroll_script}")
    
    async def random_wait(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Wait for a random duration.
        
        Args:
            min_seconds: Minimum wait time
            max_seconds: Maximum wait time
        """
        wait_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Waiting {wait_time:.2f} seconds")
        await asyncio.sleep(wait_time)
    
    def generate_fingerprint(self) -> Dict[str, Any]:
        """Generate randomized browser fingerprint.
        
        Returns:
            Dictionary with fingerprint properties
        """
        # Common canvas fingerprint values
        canvas_fingerprints = [
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        ]
        
        # Common WebGL vendor/renderer combinations
        webgl_vendors = [
            {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)"},
            {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0)"},
            {"vendor": "Google Inc. (AMD)", "renderer": "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)"},
            {"vendor": "Intel Inc.", "renderer": "Intel Iris OpenGL Engine"},
            {"vendor": "Apple Inc.", "renderer": "Apple M1"}
        ]
        
        # Common timezones
        timezones = [
            "America/New_York",
            "America/Chicago", 
            "America/Denver",
            "America/Los_Angeles",
            "America/Phoenix"
        ]
        
        # Common languages
        languages = [
            ["en-US", "en"],
            ["en-US", "en", "es"],
            ["en-GB", "en"],
            ["en-CA", "en", "fr"]
        ]
        
        # Common platforms
        platforms = ["Win32", "MacIntel", "Linux x86_64"]
        
        # Hardware concurrency (CPU cores)
        hardware_concurrency = random.choice([4, 6, 8, 12, 16])
        
        webgl = random.choice(webgl_vendors)
        
        fingerprint = {
            "canvas": random.choice(canvas_fingerprints),
            "webgl": {
                "vendor": webgl["vendor"],
                "renderer": webgl["renderer"]
            },
            "timezone": random.choice(timezones),
            "language": random.choice(languages),
            "platform": random.choice(platforms),
            "hardware_concurrency": hardware_concurrency,
            "device_memory": random.choice([4, 8, 16, 32]),
            "screen": {
                "width": random.choice([1920, 2560, 1440, 1366]),
                "height": random.choice([1080, 1440, 900, 768]),
                "color_depth": 24,
                "pixel_depth": 24
            }
        }
        
        logger.debug(f"Generated fingerprint for platform: {fingerprint['platform']}")
        return fingerprint
    
    async def human_interaction_sequence(self, page):
        """Execute a realistic human interaction sequence.
        
        Args:
            page: Playwright page object
        """
        # Random initial wait
        await self.random_wait(0.5, 1.5)
        
        # Mouse movement
        await self.random_mouse_movement(page)
        
        # Small wait
        await self.random_wait(0.3, 0.8)
        
        # Scroll
        await self.random_scroll(page)
        
        # Another mouse movement
        await self.random_mouse_movement(page)
        
        logger.debug("Completed human interaction sequence")
    
    def get_random_headers(self) -> Dict[str, str]:
        """Get randomized HTTP headers.
        
        Returns:
            Dictionary of HTTP headers
        """
        user_agent = self.get_user_agent()
        
        # Common accept headers
        accept_headers = [
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        ]
        
        # Common accept-language headers
        accept_languages = [
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,es;q=0.8",
            "en-GB,en;q=0.9",
            "en-US,en;q=0.5"
        ]
        
        headers = {
            "User-Agent": user_agent,
            "Accept": random.choice(accept_headers),
            "Accept-Language": random.choice(accept_languages),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        
        return headers
    
    def __repr__(self) -> str:
        """String representation of AntiDetectionManager."""
        return (
            f"AntiDetectionManager("
            f"user_agents={len(self.user_agents)}, "
            f"viewports={len(self.viewports)})"
        )