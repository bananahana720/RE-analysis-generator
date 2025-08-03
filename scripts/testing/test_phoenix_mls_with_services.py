#!/usr/bin/env python3
"""
Test Phoenix MLS scraper with proxy and captcha services.

This script tests the complete Phoenix MLS data collection pipeline
with configured proxy and captcha services.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.async_api import async_playwright
from src.phoenix_real_estate.foundation.config import get_config
from src.phoenix_real_estate.foundation.logging import get_logger
from src.phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from src.phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
from src.phoenix_real_estate.collectors.phoenix_mls.captcha_handler import CaptchaHandler

logger = get_logger(__name__)


class PhoenixMLSServiceTester:
    """Test Phoenix MLS with all services configured."""

    def __init__(self):
        self.config = get_config()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "proxy_test": None,
            "captcha_test": None,
            "scraper_test": None,
            "properties_found": 0,
            "errors": [],
        }

    async def test_proxy_manager(self) -> bool:
        """Test proxy manager initialization and health."""
        print("\n[TEST] Testing Proxy Manager...")

        try:
            proxy_manager = ProxyManager(self.config)

            # Check if proxies are loaded
            proxy_count = len(proxy_manager.proxies)
            print(f"[INFO] Loaded {proxy_count} proxies")

            if proxy_count == 0:
                print("[ERROR] No proxies loaded! Check proxy configuration.")
                self.test_results["errors"].append("No proxies available")
                return False

            # Get a proxy
            proxy = await proxy_manager.get_proxy()
            if proxy:
                print(f"[OK] Got proxy: {proxy.get('host')}:{proxy.get('port')}")
                self.test_results["proxy_test"] = "PASSED"
                return True
            else:
                print("[ERROR] Failed to get proxy")
                self.test_results["proxy_test"] = "FAILED"
                return False

        except Exception as e:
            print(f"[ERROR] Proxy manager test failed: {e}")
            self.test_results["proxy_test"] = "ERROR"
            self.test_results["errors"].append(f"Proxy error: {str(e)}")
            return False

    async def test_captcha_handler(self) -> bool:
        """Test captcha handler initialization."""
        print("\n[TEST] Testing Captcha Handler...")

        try:
            captcha_handler = CaptchaHandler(self.config)

            # Check if service is configured
            if not captcha_handler.enabled:
                print("[WARNING] Captcha service not enabled")
                self.test_results["captcha_test"] = "DISABLED"
                return True

            # Test service availability
            service_name = captcha_handler.service
            api_key = captcha_handler.api_key

            if not api_key:
                print("[ERROR] Captcha API key not configured")
                self.test_results["captcha_test"] = "NOT_CONFIGURED"
                return False

            print(f"[OK] Captcha service configured: {service_name}")
            print("[OK] API key present")
            self.test_results["captcha_test"] = "CONFIGURED"
            return True

        except Exception as e:
            print(f"[ERROR] Captcha handler test failed: {e}")
            self.test_results["captcha_test"] = "ERROR"
            self.test_results["errors"].append(f"Captcha error: {str(e)}")
            return False

    async def test_phoenix_mls_scraper(self) -> bool:
        """Test actual Phoenix MLS scraping with services."""
        print("\n[TEST] Testing Phoenix MLS Scraper...")

        try:
            # Initialize scraper
            PhoenixMLSScraper(self.config)

            # Test with a single zip code
            test_zip = "85031"
            print(f"[INFO] Testing with zip code: {test_zip}")

            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=True, args=["--disable-blink-features=AutomationControlled"]
                )

                # Create context with proxy
                proxy_manager = ProxyManager(self.config)
                proxy = await proxy_manager.get_proxy()

                context_options = {
                    "viewport": {"width": 1920, "height": 1080},
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }

                if proxy:
                    context_options["proxy"] = {
                        "server": f"http://{proxy['host']}:{proxy['port']}",
                        "username": proxy.get("username"),
                        "password": proxy.get("password"),
                    }

                context = await browser.new_context(**context_options)
                page = await context.new_page()

                # Try to navigate to Phoenix MLS
                try:
                    print("[INFO] Navigating to Phoenix MLS...")
                    response = await page.goto(
                        f"https://armls.com/search/{test_zip}",
                        wait_until="networkidle",
                        timeout=30000,
                    )

                    if response and response.ok:
                        print(f"[OK] Successfully loaded page (status: {response.status})")

                        # Wait a bit for content to load
                        await page.wait_for_timeout(3000)

                        # Take screenshot for debugging
                        screenshot_path = (
                            f"test_phoenix_mls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        )
                        await page.screenshot(path=screenshot_path)
                        print(f"[INFO] Screenshot saved: {screenshot_path}")

                        # Check for captcha
                        captcha_detected = await self._check_for_captcha(page)
                        if captcha_detected:
                            print("[WARNING] Captcha detected on page")
                            self.test_results["errors"].append("Captcha detected")

                        # Try to find property listings
                        listings = await page.query_selector_all(
                            '.listing-card, .property-card, [data-testid="listing"]'
                        )
                        if listings:
                            print(f"[OK] Found {len(listings)} property listings")
                            self.test_results["properties_found"] = len(listings)
                            self.test_results["scraper_test"] = "PASSED"
                            return True
                        else:
                            print("[WARNING] No property listings found")
                            print("[INFO] This might be due to:")
                            print("  - Incorrect selectors (need to update)")
                            print("  - Page structure changed")
                            print("  - Access blocked")
                            self.test_results["scraper_test"] = "NO_LISTINGS"
                            return False
                    else:
                        print(
                            f"[ERROR] Failed to load page (status: {response.status if response else 'None'})"
                        )
                        self.test_results["scraper_test"] = "LOAD_FAILED"
                        return False

                except Exception as e:
                    print(f"[ERROR] Navigation failed: {e}")
                    self.test_results["scraper_test"] = "NAVIGATION_ERROR"
                    self.test_results["errors"].append(f"Navigation error: {str(e)}")
                    return False

                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            print(f"[ERROR] Scraper test failed: {e}")
            self.test_results["scraper_test"] = "ERROR"
            self.test_results["errors"].append(f"Scraper error: {str(e)}")
            return False

    async def _check_for_captcha(self, page) -> bool:
        """Check if captcha is present on the page."""
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'div[class*="g-recaptcha"]',
            'div[id*="captcha"]',
            ".captcha",
            "#captcha",
        ]

        for selector in captcha_selectors:
            element = await page.query_selector(selector)
            if element:
                return True

        return False

    async def run_all_tests(self):
        """Run all service tests."""
        print("Phoenix MLS Service Test Suite")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Test proxy manager
        proxy_ok = await self.test_proxy_manager()

        # Test captcha handler
        captcha_ok = await self.test_captcha_handler()

        # Only test scraper if proxy is working
        if proxy_ok:
            await self.test_phoenix_mls_scraper()
        else:
            print("\n[SKIP] Skipping scraper test due to proxy issues")
            self.test_results["scraper_test"] = "SKIPPED"

        # Generate report
        self._generate_report()

        # Return overall status
        return proxy_ok and captcha_ok

    def _generate_report(self):
        """Generate test report."""
        print("\n" + "=" * 60)
        print("Test Results Summary")
        print("=" * 60)

        # Status symbols
        status_symbols = {
            "PASSED": "✅",
            "FAILED": "❌",
            "ERROR": "⚠️",
            "SKIPPED": "⏭️",
            "CONFIGURED": "✅",
            "NOT_CONFIGURED": "❌",
            "DISABLED": "⏸️",
            "NO_LISTINGS": "⚠️",
            "LOAD_FAILED": "❌",
            "NAVIGATION_ERROR": "❌",
        }

        # Print results
        print(
            f"Proxy Manager: {status_symbols.get(self.test_results['proxy_test'], '❓')} {self.test_results['proxy_test']}"
        )
        print(
            f"Captcha Handler: {status_symbols.get(self.test_results['captcha_test'], '❓')} {self.test_results['captcha_test']}"
        )
        print(
            f"Phoenix MLS Scraper: {status_symbols.get(self.test_results['scraper_test'], '❓')} {self.test_results['scraper_test']}"
        )

        if self.test_results["properties_found"] > 0:
            print(f"Properties Found: {self.test_results['properties_found']}")

        if self.test_results["errors"]:
            print("\nErrors:")
            for error in self.test_results["errors"]:
                print(f"  - {error}")

        # Save report
        report_path = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\n[INFO] Detailed report saved to: {report_path}")

        # Next steps
        print("\nNext Steps:")
        if self.test_results["scraper_test"] == "NO_LISTINGS":
            print("1. Run: python scripts/testing/discover_phoenix_mls_selectors.py")
            print("   This will help identify the correct selectors for property listings")

        if self.test_results["proxy_test"] == "FAILED":
            print("1. Check your WebShare credentials in .env")
            print("2. Verify your WebShare account is active")

        if self.test_results["captcha_test"] == "NOT_CONFIGURED":
            print("1. Add your 2captcha API key to .env")
            print("2. Set CAPTCHA_SERVICE=2captcha in .env")


async def main():
    """Run the service tests."""
    # Check for required environment variables
    required_vars = ["WEBSHARE_USERNAME", "WEBSHARE_PASSWORD", "CAPTCHA_API_KEY"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"[ERROR] Missing environment variables: {', '.join(missing_vars)}")
        print("[ACTION] Please update your .env file with the required credentials")
        print("\nYou can run: python scripts/setup/configure_services.py")
        sys.exit(1)

    # Run tests
    tester = PhoenixMLSServiceTester()
    success = await tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
