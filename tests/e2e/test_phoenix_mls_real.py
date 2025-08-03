#!/usr/bin/env python3
"""
Real Playwright-based E2E tests for Phoenix MLS data collection.

These tests use actual browser automation to validate the complete
data collection pipeline against the Phoenix MLS website.
"""

import pytest
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from phoenix_real_estate.collection.phoenix_mls_scraper import PhoenixMLSScraper
from phoenix_real_estate.config.settings import Settings
from phoenix_real_estate.database.mongo_client import MongoDBClient
from phoenix_real_estate.database.property_repository import PropertyRepository


class TestPhoenixMLSE2E:
    """End-to-end tests for Phoenix MLS data collection."""
    
    @pytest.fixture
    async def settings(self):
        """Load test settings."""
        settings = Settings()
        # Override for test environment
        settings.MONGODB_DATABASE = "phoenix_real_estate_test"
        settings.PHOENIX_MLS_TEST_MODE = True
        return settings
    
    @pytest.fixture
    async def browser(self):
        """Create Playwright browser instance."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=os.environ.get("HEADLESS", "true").lower() == "true",
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def test_database(self, settings):
        """Set up test database."""
        db_client = MongoDBClient(settings)
        await db_client.connect()
        
        # Clean test database
        db = db_client.get_database()
        await db.drop_collection("properties")
        await db.drop_collection("collection_history")
        await db.drop_collection("errors")
        
        yield db_client
        
        # Cleanup after tests
        await db.drop_collection("properties")
        await db.drop_collection("collection_history")
        await db.drop_collection("errors")
        await db_client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_phoenix_mls_navigation(self, browser: Browser):
        """Test basic navigation to Phoenix MLS website."""
        page = await browser.new_page()
        
        try:
            # Navigate to Phoenix MLS
            response = await page.goto(
                "https://armls.com/search/85031", 
                wait_until="networkidle",
                timeout=30000
            )
            
            # Verify successful navigation
            assert response is not None, "Failed to navigate to Phoenix MLS"
            assert response.status == 200, f"Unexpected status code: {response.status}"
            
            # Check for key page elements
            title = await page.title()
            assert title is not None, "Page title is missing"
            
            # Look for search or listing elements
            # These selectors need to be updated based on actual site structure
            search_elements = await page.query_selector_all('[data-testid="search"]')
            listing_elements = await page.query_selector_all('[data-testid="listing"]')
            
            # Verify page loaded with expected elements
            assert len(search_elements) > 0 or len(listing_elements) > 0, \
                "No search or listing elements found on page"
                
        finally:
            await page.close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_property_search_and_parse(self, browser: Browser, settings: Settings):
        """Test searching for properties and parsing results."""
        PhoenixMLSScraper(settings)
        page = await browser.new_page()
        
        try:
            # Test search for zip code 85031
            await page.goto("https://armls.com/search/85031", wait_until="networkidle")
            
            # Wait for listings to load
            await page.wait_for_selector('.listing-card', timeout=10000)
            
            # Get all listing cards
            listings = await page.query_selector_all('.listing-card')
            assert len(listings) > 0, "No property listings found"
            
            # Parse first listing
            if listings:
                first_listing = listings[0]
                
                # Extract property data
                property_data = await self._extract_property_data(page, first_listing)
                
                # Validate extracted data
                assert property_data is not None, "Failed to extract property data"
                assert 'address' in property_data, "Address missing from property data"
                assert 'price' in property_data, "Price missing from property data"
                
                # Log extracted data for debugging
                print(f"Extracted property: {property_data}")
                
        except Exception as e:
            # Take screenshot for debugging
            await page.screenshot(path="test_failure_screenshot.png")
            raise e
        finally:
            await page.close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.integration
    async def test_full_collection_pipeline(
        self, 
        browser: Browser, 
        settings: Settings, 
        test_database: MongoDBClient
    ):
        """Test complete data collection pipeline from search to storage."""
        # Initialize repository
        repo = PropertyRepository(test_database)
        
        # Create scraper with test browser
        PhoenixMLSScraper(settings)
        
        # Perform search and collection
        page = await browser.new_page()
        
        try:
            # Navigate to search page
            await page.goto("https://armls.com/search/85031", wait_until="networkidle")
            
            # Wait for listings
            await page.wait_for_selector('.listing-card', timeout=10000)
            
            # Collect properties
            properties_collected = []
            listings = await page.query_selector_all('.listing-card')
            
            for i, listing in enumerate(listings[:3]):  # Test first 3 properties
                property_data = await self._extract_property_data(page, listing)
                if property_data:
                    # Add metadata
                    property_data['property_id'] = f"TEST-{i+1}"
                    property_data['source'] = 'phoenix_mls'
                    property_data['last_updated'] = datetime.utcnow()
                    
                    # Save to database
                    await repo.upsert_property(property_data)
                    properties_collected.append(property_data)
            
            # Verify data was saved
            assert len(properties_collected) > 0, "No properties were collected"
            
            # Verify database storage
            saved_count = await repo.count_properties()
            assert saved_count == len(properties_collected), \
                f"Database count mismatch: {saved_count} vs {len(properties_collected)}"
            
            # Test retrieval
            for prop in properties_collected:
                saved_prop = await repo.get_property(prop['property_id'])
                assert saved_prop is not None, f"Property {prop['property_id']} not found in database"
                assert saved_prop['address'] == prop['address'], "Address mismatch"
                
        finally:
            await page.close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_handling_and_recovery(self, browser: Browser, settings: Settings):
        """Test error handling and recovery mechanisms."""
        page = await browser.new_page()
        
        try:
            # Test invalid URL handling
            response = await page.goto(
                "https://armls.com/invalid-page-12345", 
                wait_until="networkidle"
            )
            
            # Should handle 404 gracefully
            if response.status == 404:
                # Expected behavior
                pass
            else:
                # Test timeout handling
                with pytest.raises(Exception):
                    await page.wait_for_selector('.non-existent-selector', timeout=1000)
                    
        finally:
            await page.close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.benchmark
    async def test_scraping_performance(self, browser: Browser, settings: Settings):
        """Test scraping performance and resource usage."""
        import time
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        page = await browser.new_page()
        start_time = time.time()
        
        try:
            # Navigate and measure load time
            await page.goto("https://armls.com/search/85031", wait_until="networkidle")
            
            load_time = time.time() - start_time
            
            # Wait for listings
            await page.wait_for_selector('.listing-card', timeout=10000)
            
            # Measure parsing time
            parse_start = time.time()
            listings = await page.query_selector_all('.listing-card')
            properties = []
            
            for listing in listings[:10]:  # Parse first 10
                prop_data = await self._extract_property_data(page, listing)
                if prop_data:
                    properties.append(prop_data)
            
            parse_time = time.time() - parse_start
            
            # Check performance metrics
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = final_memory - initial_memory
            
            # Performance assertions
            assert load_time < 10, f"Page load too slow: {load_time:.2f}s"
            assert parse_time < 5, f"Parsing too slow: {parse_time:.2f}s"
            assert memory_used < 100, f"Excessive memory usage: {memory_used:.2f}MB"
            
            # Log performance metrics
            print("\nPerformance Metrics:")
            print(f"  Page Load Time: {load_time:.2f}s")
            print(f"  Parse Time: {parse_time:.2f}s")
            print(f"  Memory Used: {memory_used:.2f}MB")
            print(f"  Properties Parsed: {len(properties)}")
            
        finally:
            await page.close()
    
    async def _extract_property_data(self, page: Page, listing_element) -> Optional[Dict[str, Any]]:
        """Extract property data from a listing element."""
        try:
            # These selectors need to be updated based on actual site structure
            address = await listing_element.query_selector('.address')
            price = await listing_element.query_selector('.price')
            beds = await listing_element.query_selector('.beds')
            baths = await listing_element.query_selector('.baths')
            sqft = await listing_element.query_selector('.sqft')
            
            property_data = {
                'address': await address.text_content() if address else None,
                'price': await price.text_content() if price else None,
                'beds': await beds.text_content() if beds else None,
                'baths': await baths.text_content() if baths else None,
                'sqft': await sqft.text_content() if sqft else None,
                'scraped_at': datetime.utcnow()
            }
            
            # Clean and validate data
            if property_data['address']:
                property_data['address'] = property_data['address'].strip()
            
            if property_data['price']:
                # Extract numeric price
                price_text = property_data['price'].replace('$', '').replace(',', '')
                try:
                    property_data['price_numeric'] = float(price_text)
                except ValueError:
                    property_data['price_numeric'] = None
            
            return property_data
            
        except Exception as e:
            print(f"Error extracting property data: {e}")
            return None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])