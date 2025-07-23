"""Demonstration of Phoenix MLS scraper with session management.

This example shows how to use the session management features for
efficient scraping across multiple sessions.
"""

import asyncio
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


async def demo_session_management():
    """Demonstrate session management functionality."""
    # Configuration
    scraper_config = {
        "base_url": "https://www.phoenixmlssearch.com",
        "cookies_path": "data/cookies",  # Where to store session data
        "max_retries": 3,
        "timeout": 30,
        "rate_limit": {
            "requests_per_minute": 30,  # Conservative rate limit
            "burst_size": 5,
        },
    }

    proxy_config = {
        "proxies": [
            # Add your proxy configuration here
            {"host": "proxy1.example.com", "port": 8080, "username": "user", "password": "pass"}
        ],
        "max_failures": 3,
        "cooldown_minutes": 5,
    }

    # Create scraper instance
    scraper = PhoenixMLSScraper(scraper_config, proxy_config)

    try:
        # Initialize browser (will automatically load existing session if available)
        await scraper.initialize_browser()
        logger.info("Browser initialized with session management")

        # Check if we have a valid session
        session_valid = await scraper._check_session_validity()
        logger.info(f"Session valid: {session_valid}")

        # Example: Search for properties in a specific zipcode
        zipcode = "85001"  # Downtown Phoenix
        logger.info(f"Searching for properties in zipcode {zipcode}")

        properties = await scraper.search_properties_by_zipcode(zipcode)
        logger.info(f"Found {len(properties)} properties")

        # Example: Scrape details for a few properties (if found)
        if properties:
            # Limit to first 3 properties for demo
            property_urls = [prop.get("url") for prop in properties[:3] if prop.get("url")]

            if property_urls:
                logger.info(f"Scraping details for {len(property_urls)} properties")
                detailed_properties = await scraper.scrape_properties_batch(property_urls)

                # Display some results
                for prop in detailed_properties:
                    logger.info(f"Property: {prop.get('address', 'Unknown')}")
                    logger.info(f"  Price: {prop.get('price', 'N/A')}")
                    logger.info(
                        f"  Beds: {prop.get('beds', 'N/A')}, Baths: {prop.get('baths', 'N/A')}"
                    )

        # The session will be automatically maintained during batch scraping
        # and saved when the browser is closed

        # Get scraping statistics
        stats = scraper.get_statistics()
        logger.info("Scraping Statistics:")
        logger.info(f"  Total requests: {stats['total_requests']}")
        logger.info(f"  Successful: {stats['successful_requests']}")
        logger.info(f"  Failed: {stats['failed_requests']}")
        logger.info(f"  Success rate: {stats['success_rate']:.1f}%")

    except Exception as e:
        logger.error(f"Error during scraping: {e}")

    finally:
        # Close browser (will automatically save session)
        await scraper.close_browser()
        logger.info("Browser closed and session saved")


async def demo_session_clearing():
    """Demonstrate how to clear session data."""
    scraper_config = {
        "base_url": "https://www.phoenixmlssearch.com",
        "cookies_path": "data/cookies",
    }

    proxy_config = {
        "proxies": [
            {"host": "proxy1.example.com", "port": 8080, "username": "user", "password": "pass"}
        ]
    }

    scraper = PhoenixMLSScraper(scraper_config, proxy_config)

    # Clear any existing session
    await scraper.clear_session()
    logger.info("Session cleared successfully")


async def main():
    """Run the demonstrations."""
    print("Phoenix MLS Scraper - Session Management Demo")
    print("=" * 50)

    # Uncomment to clear session before starting
    # await demo_session_clearing()

    # Run the main demo
    await demo_session_management()


if __name__ == "__main__":
    asyncio.run(main())
