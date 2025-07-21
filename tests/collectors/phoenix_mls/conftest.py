"""Test configuration for Phoenix MLS collector tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def mock_proxy_config():
    """Mock proxy configuration for testing."""
    return {
        "proxies": [
            {
                "host": "proxy1.test.com",
                "port": 8080,
                "username": "user1",
                "password": "pass1",
                "type": "http"
            },
            {
                "host": "proxy2.test.com",
                "port": 8081,
                "username": "user2", 
                "password": "pass2",
                "type": "socks5"
            }
        ]
    }


@pytest.fixture
def mock_phoenix_mls_config():
    """Mock Phoenix MLS configuration."""
    return {
        "base_url": "https://www.phoenixmlssearch.com",
        "search_endpoint": "/search",
        "max_retries": 3,
        "timeout": 30,
        "rate_limit": {
            "requests_per_minute": 60,
            "burst_size": 10
        }
    }


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_playwright_page():
    """Mock Playwright page object."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[])
    page.evaluate = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    return page


@pytest.fixture
def mock_browser_context():
    """Mock Playwright browser context."""
    context = AsyncMock()
    context.new_page = AsyncMock()
    return context


@pytest.fixture
def sample_property_html():
    """Sample HTML for a property listing."""
    return '''
    <div class="property-listing">
        <h2 class="address">123 Main St, Phoenix, AZ 85001</h2>
        <span class="price">$450,000</span>
        <div class="details">
            <span class="beds">3 beds</span>
            <span class="baths">2 baths</span>
            <span class="sqft">1,850 sqft</span>
        </div>
        <div class="description">Beautiful home in central Phoenix</div>
    </div>
    '''


@pytest.fixture
def sample_search_results_html():
    """Sample HTML for search results page."""
    return '''
    <div class="search-results">
        <div class="property-card" data-property-id="123">
            <a href="/property/123" class="property-link">
                <span class="address">123 Main St</span>
                <span class="price">$450,000</span>
            </a>
        </div>
        <div class="property-card" data-property-id="456">
            <a href="/property/456" class="property-link">
                <span class="address">456 Oak Ave</span>
                <span class="price">$525,000</span>
            </a>
        </div>
    </div>
    '''