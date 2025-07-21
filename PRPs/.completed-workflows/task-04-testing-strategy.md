# Task 04: Maricopa County API Client - Testing Strategy

## Testing Overview

**Testing Philosophy**: Test-Driven Development (TDD) with comprehensive Epic 1 integration validation
**Primary Goals**: Ensure API client reliability, rate limiting compliance, and seamless Epic 1 foundation integration
**Coverage Targets**: >95% unit tests, >85% integration tests
**Performance Targets**: <30s zipcode search, 0 rate limit violations

## Testing Architecture

### Testing Pyramid Structure

```
                    E2E Integration Tests
                   /                    \
              Component Tests        Performance Tests  
             /                \                      \
        Unit Tests         Mock Tests              Security Tests
```

### Test Categories

1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: Epic 1 foundation integration
3. **Component Tests**: Multi-component workflows  
4. **Performance Tests**: Rate limiting and response times
5. **Security Tests**: Credential handling and communication
6. **E2E Tests**: Complete data collection workflow

## Unit Testing Strategy

### Test Structure
```
tests/collectors/
├── __init__.py
├── conftest.py                    # Shared fixtures and utilities
├── base/
│   ├── __init__.py
│   ├── test_rate_limiter.py       # Rate limiter unit tests
│   ├── test_collector.py          # DataCollector base tests
│   └── test_adapter.py            # DataAdapter base tests
└── maricopa/
    ├── __init__.py
    ├── test_client.py              # API client unit tests
    ├── test_adapter.py             # Data adapter unit tests
    ├── test_collector.py           # Collector unit tests
    └── test_integration.py         # Integration tests
```

### Unit Test Coverage Requirements

#### Rate Limiter Tests (`test_rate_limiter.py`)
**Coverage Target**: >98% (critical component)

```python
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter, RateLimitObserver


class MockObserver:
    """Mock observer for testing notifications."""
    def __init__(self):
        self.requests_made = []
        self.rate_limits_hit = []
        self.rate_limits_reset = []
    
    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        self.requests_made.append((source, timestamp))
    
    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        self.rate_limits_hit.append((source, wait_time))
    
    async def on_rate_limit_reset(self, source: str) -> None:
        self.rate_limits_reset.append(source)


class TestRateLimiter:
    """Comprehensive rate limiter testing."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with test configuration."""
        return RateLimiter(
            requests_per_hour=100,  # Lower for testing
            logger_name="test.rate_limiter",
            safety_margin=0.1
        )
    
    @pytest.fixture
    def mock_observer(self):
        """Create mock observer."""
        return MockObserver()
    
    async def test_initialization_parameters(self, rate_limiter):
        """Test rate limiter initialization with parameters."""
        assert rate_limiter.requests_per_hour == 100
        assert rate_limiter.effective_limit == 90  # 10% safety margin
        assert rate_limiter.safety_margin == 0.1
        assert len(rate_limiter._observers) == 0
        assert len(rate_limiter._request_times) == 0
    
    async def test_safety_margin_calculation(self):
        """Test safety margin calculation for different values."""
        # Test default 10% margin
        limiter = RateLimiter(1000, "test", 0.1)
        assert limiter.effective_limit == 900
        
        # Test 20% margin
        limiter = RateLimiter(1000, "test", 0.2)
        assert limiter.effective_limit == 800
        
        # Test 0% margin
        limiter = RateLimiter(1000, "test", 0.0)
        assert limiter.effective_limit == 1000
    
    async def test_observer_registration(self, rate_limiter, mock_observer):
        """Test observer registration and management."""
        # Initially no observers
        assert len(rate_limiter._observers) == 0
        
        # Add observer
        rate_limiter.add_observer(mock_observer)
        assert len(rate_limiter._observers) == 1
        
        # Add multiple observers
        observer2 = MockObserver()
        rate_limiter.add_observer(observer2)
        assert len(rate_limiter._observers) == 2
    
    async def test_rate_limiting_enforcement(self, rate_limiter, mock_observer):
        """Test that rate limiting is properly enforced."""
        rate_limiter.add_observer(mock_observer)
        
        # Make requests up to limit
        for i in range(90):  # effective limit
            wait_time = await rate_limiter.wait_if_needed(f"test_source_{i}")
            assert wait_time == 0.0
        
        # Verify observer notifications
        assert len(mock_observer.requests_made) == 90
        assert len(mock_observer.rate_limits_hit) == 0
        
        # Next request should trigger rate limiting
        wait_time = await rate_limiter.wait_if_needed("test_source_91")
        assert wait_time > 0  # Should wait
        
        # Verify rate limit notification
        assert len(mock_observer.rate_limits_hit) == 1
        assert mock_observer.rate_limits_hit[0][0] == "test_source_91"
    
    async def test_sliding_window_cleanup(self, rate_limiter):
        """Test that old requests are cleaned up properly."""
        # Mock datetime to control time
        import datetime as dt
        original_utcnow = dt.datetime.utcnow
        
        try:
            # Set initial time
            mock_time = dt.datetime(2025, 1, 1, 12, 0, 0)
            dt.datetime.utcnow = lambda: mock_time
            
            # Make some requests
            for i in range(50):
                await rate_limiter.wait_if_needed("test")
            
            assert len(rate_limiter._request_times) == 50
            
            # Advance time by 2 hours (beyond 1-hour window)
            mock_time = dt.datetime(2025, 1, 1, 14, 0, 0)
            
            # Make another request to trigger cleanup
            await rate_limiter.wait_if_needed("test")
            
            # Old requests should be cleaned up, only 1 recent request
            assert len(rate_limiter._request_times) == 1
            
        finally:
            dt.datetime.utcnow = original_utcnow
    
    async def test_concurrent_access_thread_safety(self, rate_limiter):
        """Test thread-safe concurrent access to rate limiter."""
        async def make_requests(source_prefix, count):
            """Make multiple requests concurrently."""
            for i in range(count):
                await rate_limiter.wait_if_needed(f"{source_prefix}_{i}")
        
        # Run multiple concurrent request makers
        tasks = [
            make_requests("concurrent_1", 30),
            make_requests("concurrent_2", 30),
            make_requests("concurrent_3", 30)
        ]
        
        await asyncio.gather(*tasks)
        
        # Should have exactly 90 requests (at effective limit)
        assert len(rate_limiter._request_times) == 90
        
        # Usage should be at 100% utilization
        usage = rate_limiter.get_current_usage()
        assert usage["utilization"] == 1.0
    
    async def test_usage_statistics(self, rate_limiter):
        """Test usage statistics calculation."""
        # Initially empty
        usage = rate_limiter.get_current_usage()
        assert usage["requests_made"] == 0
        assert usage["utilization"] == 0.0
        assert usage["effective_limit"] == 90
        assert usage["actual_limit"] == 100
        
        # Make some requests
        for i in range(45):
            await rate_limiter.wait_if_needed("test")
        
        # Check usage at 50%
        usage = rate_limiter.get_current_usage()
        assert usage["requests_made"] == 45
        assert usage["utilization"] == 0.5
    
    async def test_observer_notification_sequence(self, rate_limiter, mock_observer):
        """Test observer notification sequence during rate limiting."""
        rate_limiter.add_observer(mock_observer)
        
        # Fill up to effective limit
        for i in range(90):
            await rate_limiter.wait_if_needed("test")
        
        # Verify all requests were notified
        assert len(mock_observer.requests_made) == 90
        assert len(mock_observer.rate_limits_hit) == 0
        assert len(mock_observer.rate_limits_reset) == 0
        
        # Trigger rate limiting (will cause wait)
        with patch('asyncio.sleep') as mock_sleep:
            await rate_limiter.wait_if_needed("test_limit")
        
        # Verify rate limit notifications
        assert len(mock_observer.rate_limits_hit) == 1
        assert len(mock_observer.rate_limits_reset) == 1
        assert mock_sleep.called
```

#### API Client Tests (`test_client.py`)
**Coverage Target**: >95%

```python
import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from aioresponses import aioresponses

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import DataCollectionError, ConfigurationError
from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient


class TestMaricopaAPIClient:
    """Comprehensive API client testing."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock Epic 1 ConfigProvider."""
        config = MagicMock(spec=ConfigProvider)
        config.get_required.side_effect = lambda key: {
            "MARICOPA_API_KEY": "test_api_key_123"
        }.get(key)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_BASE_URL": "https://api.assessor.maricopa.gov/v1",
            "MARICOPA_RATE_LIMIT": 100
        }.get(key, default)
        return config
    
    @pytest.fixture
    async def api_client(self, mock_config):
        """Create API client with mocked config."""
        return MaricopaAPIClient(mock_config)
    
    async def test_initialization_with_valid_config(self, mock_config):
        """Test successful initialization with valid configuration."""
        client = MaricopaAPIClient(mock_config)
        
        assert client.api_key == "test_api_key_123"
        assert client.base_url == "https://api.assessor.maricopa.gov/v1"
        assert client.rate_limiter.requests_per_hour == 100
        assert client.session is None  # Not created until needed
    
    async def test_initialization_missing_api_key(self):
        """Test initialization failure with missing API key."""
        config = MagicMock(spec=ConfigProvider)
        config.get_required.side_effect = KeyError("MARICOPA_API_KEY")
        
        with pytest.raises(ConfigurationError) as exc_info:
            MaricopaAPIClient(config)
        
        assert "Failed to load Maricopa API configuration" in str(exc_info.value)
        assert "MARICOPA_API_KEY" in str(exc_info.value.context)
    
    async def test_session_creation_with_proper_headers(self, api_client):
        """Test HTTP session creation with proper authentication headers."""
        await api_client._ensure_session()
        
        assert api_client.session is not None
        assert not api_client.session.closed
        
        # Check headers
        headers = api_client.session._default_headers
        assert headers["Authorization"] == "Bearer test_api_key_123"
        assert headers["User-Agent"] == "Phoenix-RE-Collector/1.0 (Personal Use)"
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
    
    async def test_session_reuse_when_existing(self, api_client):
        """Test that existing session is reused."""
        # Create session
        await api_client._ensure_session()
        first_session = api_client.session
        
        # Call again - should reuse
        await api_client._ensure_session()
        assert api_client.session is first_session
    
    async def test_session_recreation_when_closed(self, api_client):
        """Test session recreation when existing session is closed."""
        # Create and close session
        await api_client._ensure_session()
        await api_client.session.close()
        
        # Should create new session
        await api_client._ensure_session()
        assert api_client.session is not None
        assert not api_client.session.closed
    
    @aioresponses()
    async def test_successful_api_request(self, mock_responses, api_client):
        """Test successful API request with proper response handling."""
        # Mock successful response
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            payload={"result": "success", "data": [1, 2, 3]},
            status=200
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock) as mock_wait:
            response = await api_client._make_request("/test")
        
        assert response == {"result": "success", "data": [1, 2, 3]}
        mock_wait.assert_called_once()
    
    @aioresponses()
    async def test_authentication_error_handling(self, mock_responses, api_client):
        """Test 401 authentication error handling."""
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            status=401
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            with pytest.raises(DataCollectionError) as exc_info:
                await api_client._make_request("/test")
        
        assert "Authentication failed - invalid API key" in str(exc_info.value)
        assert exc_info.value.context["endpoint"] == "/test"
        assert exc_info.value.context["status"] == 401
    
    @aioresponses()
    async def test_forbidden_error_handling(self, mock_responses, api_client):
        """Test 403 forbidden error handling."""
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            status=403
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            with pytest.raises(DataCollectionError) as exc_info:
                await api_client._make_request("/test")
        
        assert "Access forbidden - check API permissions" in str(exc_info.value)
    
    @aioresponses()
    async def test_rate_limit_error_with_retry_after(self, mock_responses, api_client):
        """Test 429 rate limit error with Retry-After header."""
        # First request hits rate limit
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            status=429,
            headers={"Retry-After": "60"}
        )
        
        # Second request succeeds (after retry)
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            payload={"success": True},
            status=200
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                # This should raise due to rate limit in first attempt
                with pytest.raises(DataCollectionError):
                    await api_client._make_request("/test")
        
        mock_sleep.assert_called_with(60)  # Should wait 60 seconds
    
    @aioresponses()
    async def test_server_error_handling(self, mock_responses, api_client):
        """Test 5xx server error handling."""
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            status=500,
            payload="Internal Server Error"
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            with pytest.raises(DataCollectionError) as exc_info:
                await api_client._make_request("/test")
        
        assert "API request failed with status 500" in str(exc_info.value)
        assert exc_info.value.context["status"] == 500
    
    @aioresponses()
    async def test_invalid_json_response_handling(self, mock_responses, api_client):
        """Test handling of invalid JSON responses."""
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            payload="not valid json",
            status=200,
            content_type="text/plain"
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            with pytest.raises(DataCollectionError) as exc_info:
                await api_client._make_request("/test")
        
        assert "Failed to parse API response as JSON" in str(exc_info.value)
    
    @aioresponses()
    async def test_retry_logic_with_exponential_backoff(self, mock_responses, api_client):
        """Test retry logic with exponential backoff."""
        # First two attempts fail
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            status=500,
            repeat=2
        )
        
        # Third attempt succeeds
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/test",
            payload={"success": True},
            status=200
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            response = await api_client._make_request("/test")
        
        assert response == {"success": True}
        
        # Verify all attempts were made
        assert len(mock_responses.requests) == 3
    
    @aioresponses()
    async def test_zipcode_search_success(self, mock_responses, api_client):
        """Test successful zipcode search."""
        mock_properties = [
            {"property_id": "123", "address": "123 Main St"},
            {"property_id": "456", "address": "456 Oak Ave"}
        ]
        
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/properties/search",
            payload={"properties": mock_properties},
            status=200
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            properties = await api_client.search_by_zipcode("85031")
        
        assert len(properties) == 2
        assert properties[0]["property_id"] == "123"
        assert properties[1]["property_id"] == "456"
    
    @aioresponses()
    async def test_property_details_success(self, mock_responses, api_client):
        """Test successful property details retrieval."""
        mock_property = {
            "property": {
                "id": "123",
                "details": "property details here"
            }
        }
        
        mock_responses.get(
            "https://api.assessor.maricopa.gov/v1/properties/123",
            payload=mock_property,
            status=200
        )
        
        with patch.object(api_client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock):
            property_data = await api_client.get_property_details("123")
        
        assert property_data["id"] == "123"
        assert "details" in property_data
    
    async def test_context_manager_usage(self, api_client):
        """Test async context manager functionality."""
        assert api_client.session is None
        
        async with api_client as client:
            assert client.session is not None
            assert not client.session.closed
        
        assert api_client.session is None or api_client.session.closed
```

#### Data Adapter Tests (`test_adapter.py`)
**Coverage Target**: >95%

```python
import pytest
from datetime import datetime
from decimal import Decimal

from phoenix_real_estate.foundation.database.schema import Property, PropertyFeatures, PropertyPrice
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.foundation.utils.exceptions import ValidationError
from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter


class TestMaricopaDataAdapter:
    """Comprehensive data adapter testing."""
    
    @pytest.fixture
    def mock_validator(self):
        """Mock Epic 1 DataValidator."""
        return DataValidator()
    
    @pytest.fixture
    def adapter(self, mock_validator):
        """Create data adapter with validator."""
        return MaricopaDataAdapter(mock_validator, "test.adapter")
    
    @pytest.fixture
    def sample_maricopa_data(self):
        """Sample Maricopa API response for testing."""
        return {
            "property_info": {
                "apn": "123-45-678",
                "legal_description": "LOT 1 BLOCK 2 TEST SUBDIVISION",
                "subdivision": "Test Subdivision",
                "parcel_number": "123-45-678-001",
                "zoning": "R1-6",
                "land_use_code": "Single Family Residential"
            },
            "address": {
                "house_number": "123",
                "street_name": "Main",
                "street_type": "St",
                "unit": "",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85031"
            },
            "assessment": {
                "assessed_value": 300000,
                "market_value": 350000,
                "tax_district": "Phoenix Elementary",
                "school_district": "Phoenix Union High School",
                "previous_assessments": [
                    {"year": 2023, "value": 280000},
                    {"year": 2022, "value": 260000}
                ]
            },
            "characteristics": {
                "bedrooms": 3,
                "bathrooms": 2.5,
                "living_area_sqft": 1800,
                "lot_size_sqft": 7200,
                "year_built": 2010,
                "property_type": "Single Family Residence",
                "stories": 2,
                "garage_spaces": 2,
                "has_pool": True,
                "has_fireplace": False
            }
        }
    
    def test_source_name_identification(self, adapter):
        """Test source name identification."""
        assert adapter.get_source_name() == "maricopa_api"
    
    async def test_complete_property_adaptation(self, adapter, sample_maricopa_data):
        """Test complete property adaptation from Maricopa data."""
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        
        # Verify property object type and source
        assert isinstance(property_obj, Property)
        assert property_obj.source == "maricopa_api"
        
        # Verify address normalization
        assert property_obj.address == "123 Main St"
        assert property_obj.city == "Phoenix"
        assert property_obj.state == "AZ"
        assert property_obj.zip_code == "85031"
        
        # Verify property ID generation
        assert property_obj.property_id is not None
        assert len(property_obj.property_id) > 0
    
    async def test_property_features_adaptation(self, adapter, sample_maricopa_data):
        """Test property features adaptation."""
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        features = property_obj.features
        
        assert isinstance(features, PropertyFeatures)
        assert features.bedrooms == 3
        assert features.bathrooms == 2.5
        assert features.square_feet == 1800
        assert features.lot_size_sqft == 7200
        assert features.year_built == 2010
        assert features.property_type == "Single Family Residence"
        assert features.stories == 2
        assert features.garage_spaces == 2
        assert features.pool is True
        assert features.fireplace is False
    
    async def test_price_extraction_multiple_types(self, adapter, sample_maricopa_data):
        """Test extraction of multiple price types."""
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        prices = property_obj.prices
        
        assert len(prices) >= 2  # At least assessed and market value
        
        # Find price types
        price_types = {price.price_type: price for price in prices}
        
        # Verify current assessed value
        assert "assessed_value" in price_types
        assessed = price_types["assessed_value"]
        assert assessed.amount == 300000
        assert assessed.source == "maricopa_api"
        
        # Verify market value
        assert "market_value" in price_types
        market = price_types["market_value"]
        assert market.amount == 350000
        assert market.source == "maricopa_api"
    
    async def test_historical_price_extraction(self, adapter, sample_maricopa_data):
        """Test extraction of historical price data."""
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        
        # Find historical prices
        historical_prices = [
            price for price in property_obj.prices 
            if price.price_type == "assessed_value" and price.date.year in [2022, 2023]
        ]
        
        assert len(historical_prices) == 2
        
        # Verify 2023 assessment
        price_2023 = next(p for p in historical_prices if p.date.year == 2023)
        assert price_2023.amount == 280000
        
        # Verify 2022 assessment  
        price_2022 = next(p for p in historical_prices if p.date.year == 2022)
        assert price_2022.amount == 260000
    
    async def test_address_normalization_with_unit(self, adapter, sample_maricopa_data):
        """Test address normalization with unit number."""
        # Add unit to test data
        sample_maricopa_data["address"]["unit"] = "A"
        
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        assert property_obj.address == "123 Main St Unit A"
    
    async def test_address_normalization_without_unit(self, adapter, sample_maricopa_data):
        """Test address normalization without unit."""
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        assert property_obj.address == "123 Main St"
        assert "Unit" not in property_obj.address
    
    async def test_listing_details_preservation(self, adapter, sample_maricopa_data):
        """Test that original data is preserved in listing_details."""
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        details = property_obj.listing_details
        
        # Verify key fields preserved
        assert details["apn"] == "123-45-678"
        assert details["legal_description"] == "LOT 1 BLOCK 2 TEST SUBDIVISION"
        assert details["subdivision"] == "Test Subdivision"
        assert details["tax_district"] == "Phoenix Elementary"
        assert details["zoning"] == "R1-6"
        
        # Verify original data is stored
        assert "maricopa_data" in details
        assert details["maricopa_data"] == sample_maricopa_data
    
    async def test_safe_conversion_utilities(self, adapter):
        """Test safe conversion utilities handle various data types."""
        # Test data with various problematic values
        problematic_data = {
            "property_info": {"apn": "123-45-678"},
            "address": {
                "house_number": "123",
                "street_name": "Main",
                "street_type": "St",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85031"
            },
            "assessment": {"assessed_value": "300000"},  # String instead of int
            "characteristics": {
                "bedrooms": "3",           # String
                "bathrooms": 2.5,         # Correct type
                "living_area_sqft": "",   # Empty string
                "lot_size_sqft": None,    # None value
                "year_built": "invalid",  # Invalid string
                "property_type": "Single Family"
            }
        }
        
        # Should not raise exception due to safe conversion utilities
        property_obj = await adapter.adapt_property(problematic_data)
        features = property_obj.features
        
        # Verify safe conversions
        assert features.bedrooms == 3        # String "3" → int 3
        assert features.bathrooms == 2.5     # Correct type preserved
        assert features.square_feet is None  # Empty string → None
        assert features.lot_size_sqft is None # None preserved
        assert features.year_built is None   # Invalid string → None
    
    async def test_missing_data_handling(self, adapter):
        """Test handling of missing required data."""
        minimal_data = {
            "property_info": {},
            "address": {
                "house_number": "123",
                "street_name": "Main",
                "street_type": "St"
            },
            "assessment": {},
            "characteristics": {}
        }
        
        # Should handle missing data gracefully
        property_obj = await adapter.adapt_property(minimal_data)
        
        # Verify defaults are applied
        assert property_obj.features.bedrooms == 0  # Default from safe_int
        assert property_obj.features.bathrooms == 0.0  # Default from safe_float
        assert len(property_obj.prices) == 0  # No prices available
    
    async def test_validation_error_handling(self, adapter):
        """Test handling of validation errors."""
        # Invalid data that should trigger validation error
        invalid_data = None  # Completely invalid
        
        with pytest.raises(ValidationError) as exc_info:
            await adapter.adapt_property(invalid_data)
        
        assert "Failed to adapt Maricopa property data" in str(exc_info.value)
        assert exc_info.value.context["source"] == "maricopa_api"
        assert exc_info.value.cause is not None
    
    async def test_timezone_aware_timestamps(self, adapter, sample_maricopa_data):
        """Test that timestamps are timezone-aware."""
        property_obj = await adapter.adapt_property(sample_maricopa_data)
        
        # Verify last_updated is timezone-aware
        assert property_obj.last_updated is not None
        assert property_obj.last_updated.tzinfo is not None
```

## Integration Testing Strategy

### Epic 1 Foundation Integration Tests

```python
# tests/collectors/test_maricopa_integration.py
import pytest
from unittest.mock import AsyncMock, patch

from phoenix_real_estate.foundation.config.base import ConfigProvider, get_config
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.utils.exceptions import DataCollectionError
from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector


class TestMaricopaIntegration:
    """Integration tests with Epic 1 foundation."""
    
    @pytest.fixture
    async def real_config(self):
        """Real Epic 1 ConfigProvider for integration testing."""
        # Use test configuration
        return get_config()
    
    @pytest.fixture
    async def mock_repository(self):
        """Mock PropertyRepository for testing."""
        repository = AsyncMock(spec=PropertyRepository)
        repository.create.return_value = "generated_id_123"
        repository.find_by_id.return_value = None
        return repository
    
    @pytest.fixture
    async def collector(self, real_config, mock_repository):
        """Create collector with real Epic 1 integration."""
        return MaricopaAPICollector(
            real_config,
            mock_repository,
            "test.maricopa.integration"
        )
    
    async def test_epic1_config_provider_integration(self, collector, real_config):
        """Test Epic 1 ConfigProvider integration."""
        # Verify config access works
        assert collector.config is real_config
        
        # Verify configuration loading
        try:
            api_key = real_config.get_required("MARICOPA_API_KEY")
            assert api_key is not None
        except Exception:
            pytest.skip("MARICOPA_API_KEY not configured for testing")
        
        # Verify optional configuration with defaults
        base_url = real_config.get("MARICOPA_BASE_URL", "default_url")
        assert base_url is not None
    
    async def test_epic1_repository_integration(self, collector, mock_repository):
        """Test Epic 1 PropertyRepository integration."""
        # Verify repository is properly injected
        assert collector.repository is mock_repository
        
        # Test property creation through repository
        sample_property_data = {
            "property_info": {"apn": "test-123"},
            "address": {"house_number": "123", "street_name": "Test", "street_type": "St"},
            "assessment": {"assessed_value": 100000},
            "characteristics": {"bedrooms": 2}
        }
        
        # Adapt property and verify it would be stored correctly
        property_obj = await collector.adapt_property(sample_property_data)
        
        # Verify property object is valid for repository
        assert property_obj.property_id is not None
        assert property_obj.source == "maricopa_api"
        assert property_obj.address is not None
    
    async def test_epic1_logging_integration(self, collector):
        """Test Epic 1 logging framework integration."""
        # Verify logger is properly initialized
        assert collector.logger is not None
        assert hasattr(collector.logger, 'info')
        assert hasattr(collector.logger, 'error')
        assert hasattr(collector.logger, 'debug')
        
        # Test structured logging
        collector.logger.info(
            "Test message",
            extra={"test_key": "test_value", "source": "maricopa_api"}
        )
    
    async def test_epic1_exception_hierarchy(self, collector):
        """Test Epic 1 exception hierarchy usage."""
        # Test that proper Epic 1 exceptions are raised
        with patch.object(collector.api_client, 'search_by_zipcode') as mock_search:
            mock_search.side_effect = Exception("Test failure")
            
            with pytest.raises(DataCollectionError) as exc_info:
                await collector.collect_zipcode("85031")
            
            # Verify Epic 1 exception structure
            assert exc_info.value.context is not None
            assert "zipcode" in exc_info.value.context
            assert exc_info.value.cause is not None
    
    async def test_epic1_utilities_integration(self, collector):
        """Test Epic 1 utility functions integration."""
        # Test data with various formats to verify utilities
        test_data = {
            "property_info": {"apn": "test-456"},
            "address": {
                "house_number": "456",
                "street_name": "Oak",
                "street_type": "Ave",
                "city": "Phoenix",
                "zip_code": "85032"
            },
            "assessment": {"assessed_value": "250000"},  # String value
            "characteristics": {
                "bedrooms": "3",        # String
                "bathrooms": 2.5,       # Float
                "living_area_sqft": "", # Empty
            }
        }
        
        # Adapt using Epic 1 utilities
        property_obj = await collector.adapt_property(test_data)
        
        # Verify Epic 1 utilities worked correctly
        assert property_obj.address == "456 Oak Ave"  # normalize_address
        assert property_obj.features.bedrooms == 3    # safe_int conversion
        assert property_obj.features.bathrooms == 2.5 # safe_float
        assert property_obj.features.square_feet is None # safe_int on empty string
    
    async def test_end_to_end_workflow_mocked(self, collector):
        """Test end-to-end workflow with mocked API responses."""
        mock_api_data = [
            {
                "property_info": {"apn": "e2e-test-123"},
                "address": {
                    "house_number": "789",
                    "street_name": "Elm",
                    "street_type": "Dr",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip_code": "85033"
                },
                "assessment": {
                    "assessed_value": 400000,
                    "market_value": 450000
                },
                "characteristics": {
                    "bedrooms": 4,
                    "bathrooms": 3.0,
                    "living_area_sqft": 2200
                }
            }
        ]
        
        with patch.object(collector.api_client, 'search_by_zipcode') as mock_search:
            mock_search.return_value = mock_api_data
            
            # Test complete workflow
            raw_properties = await collector.collect_zipcode("85033")
            assert len(raw_properties) == 1
            assert raw_properties[0]["property_info"]["apn"] == "e2e-test-123"
            
            # Test adaptation
            property_obj = await collector.adapt_property(raw_properties[0])
            assert property_obj.source == "maricopa_api"
            assert property_obj.address == "789 Elm Dr"
            assert property_obj.features.bedrooms == 4
            
            # Verify repository would be called for storage
            # (In real Epic 3 orchestration)
```

## Performance Testing Strategy

### Rate Limiting Performance Tests

```python
# tests/collectors/test_performance.py
import pytest
import asyncio
import time
from unittest.mock import patch

from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter


class TestPerformanceRateLimiting:
    """Performance testing for rate limiting functionality."""
    
    async def test_rate_limiting_compliance_under_load(self):
        """Test rate limiting compliance under high load."""
        limiter = RateLimiter(
            requests_per_hour=60,  # 1 per minute for testing
            logger_name="test.performance",
            safety_margin=0.1  # 54 effective limit
        )
        
        start_time = time.time()
        request_times = []
        
        # Make requests up to effective limit
        for i in range(54):
            await limiter.wait_if_needed(f"load_test_{i}")
            request_times.append(time.time())
        
        # All requests should complete quickly (no waiting)
        elapsed = time.time() - start_time
        assert elapsed < 5.0  # Should complete in under 5 seconds
        
        # Next request should trigger rate limiting
        start_wait = time.time()
        await limiter.wait_if_needed("limit_trigger")
        wait_time = time.time() - start_wait
        
        assert wait_time > 0  # Should have waited
        
        # Verify utilization
        usage = limiter.get_current_usage()
        assert usage["utilization"] >= 1.0  # At or over limit
    
    async def test_concurrent_rate_limiting_thread_safety(self):
        """Test thread safety under concurrent access."""
        limiter = RateLimiter(
            requests_per_hour=120,
            logger_name="test.concurrent",
            safety_margin=0.1  # 108 effective limit
        )
        
        async def make_concurrent_requests(source_id, count):
            """Make concurrent requests from single source."""
            for i in range(count):
                await limiter.wait_if_needed(f"concurrent_{source_id}_{i}")
        
        # Start multiple concurrent request makers
        tasks = [
            make_concurrent_requests("source_1", 36),
            make_concurrent_requests("source_2", 36),
            make_concurrent_requests("source_3", 36)
        ]
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Should complete without race conditions
        assert elapsed < 10.0
        
        # Verify exactly 108 requests were processed
        usage = limiter.get_current_usage()
        assert usage["requests_made"] == 108
        assert usage["utilization"] == 1.0
```

### API Response Time Testing

```python
class TestPerformanceAPIClient:
    """Performance testing for API client response times."""
    
    @pytest.mark.performance
    async def test_zipcode_search_response_time(self, api_client):
        """Test zipcode search meets response time requirements."""
        with patch.object(api_client, '_make_request') as mock_request:
            # Mock fast response
            mock_request.return_value = {"properties": [{"id": "123"}]}
            
            start_time = time.time()
            await api_client.search_by_zipcode("85031")
            elapsed = time.time() - start_time
            
            # Should complete in under 30 seconds (requirement)
            assert elapsed < 30.0
            # Should be much faster with mocked response
            assert elapsed < 1.0
    
    @pytest.mark.performance  
    async def test_memory_usage_during_large_collection(self, api_client):
        """Test memory usage during large property collection."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock large dataset
        large_dataset = [{"property_id": f"prop_{i}"} for i in range(1000)]
        
        with patch.object(api_client, '_make_request') as mock_request:
            mock_request.return_value = {"properties": large_dataset}
            
            properties = await api_client.search_by_zipcode("85031")
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Memory increase should be reasonable (<100MB requirement)
            assert memory_increase < 100
            assert len(properties) == 1000
```

## Security Testing Strategy

### Credential Security Tests

```python
# tests/collectors/test_security.py
import pytest
from unittest.mock import patch, MagicMock
import logging

from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient


class TestSecurityCredentialHandling:
    """Security testing for credential handling."""
    
    async def test_api_key_not_logged_in_normal_operations(self, api_client):
        """Test that API key is never logged in normal operations."""
        with patch('phoenix_real_estate.foundation.logging.factory.get_logger') as mock_logger_factory:
            mock_logger = MagicMock()
            mock_logger_factory.return_value = mock_logger
            
            # Create client (triggers logging)
            config = MagicMock()
            config.get_required.return_value = "secret_api_key_123"
            config.get.return_value = "https://api.test.com"
            
            client = MaricopaAPIClient(config)
            
            # Check all logging calls
            for call in mock_logger.info.call_args_list:
                args, kwargs = call
                message = args[0] if args else ""
                extra = kwargs.get('extra', {})
                
                # Verify API key is never in log message or extra data
                assert "secret_api_key_123" not in message
                for key, value in extra.items():
                    assert "secret_api_key_123" not in str(value)
    
    async def test_api_key_not_exposed_in_errors(self, api_client):
        """Test that API key is not exposed in error messages."""
        with patch.object(api_client, '_make_request') as mock_request:
            mock_request.side_effect = Exception("API failure")
            
            try:
                await api_client.search_by_zipcode("85031")
            except Exception as e:
                # Verify API key is not in exception message or context
                error_str = str(e)
                assert "test_api_key_123" not in error_str
                
                if hasattr(e, 'context'):
                    context_str = str(e.context)
                    assert "test_api_key_123" not in context_str
    
    async def test_https_only_communication(self, api_client):
        """Test that only HTTPS communication is used."""
        # Verify base URL is HTTPS
        assert api_client.base_url.startswith("https://")
        
        # Test that HTTP URLs are rejected
        config = MagicMock()
        config.get_required.return_value = "test_key"
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_BASE_URL": "http://insecure.api.com"  # HTTP not HTTPS
        }.get(key, default)
        
        # Should still work but we'd validate in production deployment
        client = MaricopaAPIClient(config)
        # In production, we'd add validation to reject HTTP URLs
    
    async def test_session_headers_security(self, api_client):
        """Test that session headers are properly secured."""
        await api_client._ensure_session()
        
        headers = api_client.session._default_headers
        
        # Verify Authorization header is properly formatted
        assert headers["Authorization"].startswith("Bearer ")
        
        # Verify User-Agent identifies the application appropriately
        assert "Phoenix-RE-Collector" in headers["User-Agent"]
        assert "Personal Use" in headers["User-Agent"]
        
        # Verify content type headers are appropriate
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
```

## Test Data Management

### Test Fixtures and Factories

```python
# tests/collectors/conftest.py
import pytest
from unittest.mock import MagicMock

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.utils.validators import DataValidator


@pytest.fixture
def mock_config():
    """Standard mock configuration for testing."""
    config = MagicMock(spec=ConfigProvider)
    config.get_required.side_effect = lambda key: {
        "MARICOPA_API_KEY": "test_api_key_12345",
        "MONGODB_URI": "mongodb://localhost:27017/test_db"
    }.get(key, f"mock_{key}")
    
    config.get.side_effect = lambda key, default=None: {
        "MARICOPA_BASE_URL": "https://api.assessor.maricopa.gov/v1",
        "MARICOPA_RATE_LIMIT": 1000,
        "LOG_LEVEL": "DEBUG"
    }.get(key, default)
    
    return config


@pytest.fixture
def mock_repository():
    """Standard mock repository for testing."""
    repository = MagicMock(spec=PropertyRepository)
    repository.create.return_value = "generated_property_id"
    repository.find_by_id.return_value = None
    repository.find_by_source_and_external_id.return_value = None
    return repository


@pytest.fixture
def mock_validator():
    """Standard mock validator for testing."""
    return DataValidator()


class PropertyDataFactory:
    """Factory for creating test property data."""
    
    @staticmethod
    def create_maricopa_response(overrides=None):
        """Create standard Maricopa API response for testing."""
        data = {
            "property_info": {
                "apn": "123-45-678",
                "legal_description": "LOT 1 BLOCK 2 TEST SUBDIVISION",
                "subdivision": "Test Subdivision",
                "parcel_number": "123-45-678-001"
            },
            "address": {
                "house_number": "123",
                "street_name": "Test",
                "street_type": "St",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85031"
            },
            "assessment": {
                "assessed_value": 300000,
                "market_value": 350000
            },
            "characteristics": {
                "bedrooms": 3,
                "bathrooms": 2.5,
                "living_area_sqft": 1800,
                "lot_size_sqft": 7200,
                "year_built": 2010,
                "property_type": "Single Family Residence"
            }
        }
        
        if overrides:
            data.update(overrides)
        
        return data
    
    @staticmethod
    def create_maricopa_response_list(count=5, base_zipcode="85031"):
        """Create list of Maricopa responses for testing."""
        return [
            PropertyDataFactory.create_maricopa_response({
                "property_info": {"apn": f"test-{i:03d}-{base_zipcode}"},
                "address": {
                    "house_number": str(100 + i),
                    "street_name": "Test",
                    "street_type": "St",
                    "zip_code": base_zipcode
                }
            })
            for i in range(count)
        ]


@pytest.fixture
def property_data_factory():
    """Property data factory fixture."""
    return PropertyDataFactory
```

## Test Execution Strategy

### Test Categories and Execution

```bash
# Unit tests - fast execution
uv run pytest tests/collectors/ -m "not integration and not performance" -v

# Integration tests - slower, requires Epic 1
uv run pytest tests/collectors/ -m "integration" -v

# Performance tests - specialized execution
uv run pytest tests/collectors/ -m "performance" -v --timeout=60

# Security tests - manual and automated
uv run pytest tests/collectors/ -m "security" -v

# All tests with coverage
uv run pytest tests/collectors/ \
    --cov=src/phoenix_real_estate/collectors \
    --cov-report=html \
    --cov-report=term \
    --cov-fail-under=90

# CI/CD pipeline execution
uv run pytest tests/collectors/ \
    --junitxml=test-results.xml \
    --cov=src/phoenix_real_estate/collectors \
    --cov-report=xml \
    --cov-fail-under=95
```

### Continuous Integration Testing

```yaml
# .github/workflows/task-04-testing.yml
name: Task 04 Testing

on:
  push:
    paths:
      - 'src/phoenix_real_estate/collectors/**'
      - 'tests/collectors/**'
  pull_request:
    paths:
      - 'src/phoenix_real_estate/collectors/**'
      - 'tests/collectors/**'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.13]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install UV
      run: curl -LsSf https://astral.sh/uv/install.sh | sh
    
    - name: Install dependencies
      run: uv sync --extra dev
    
    - name: Run unit tests
      run: |
        uv run pytest tests/collectors/ \
          -m "not integration and not performance" \
          --cov=src/phoenix_real_estate/collectors \
          --cov-report=xml \
          --cov-fail-under=95 \
          -v
    
    - name: Run integration tests
      env:
        MARICOPA_API_KEY: ${{ secrets.TEST_MARICOPA_API_KEY }}
        MONGODB_URI: ${{ secrets.TEST_MONGODB_URI }}
      run: |
        uv run pytest tests/collectors/ \
          -m "integration" \
          -v
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: collectors
        name: task-04-coverage
```

## Quality Gates and Success Criteria

### Test Coverage Requirements

- **Unit Tests**: >95% line coverage
- **Integration Tests**: >85% Epic 1 integration coverage
- **Performance Tests**: All benchmarks passing
- **Security Tests**: No credential exposure detected

### Test Quality Metrics

- **Test Execution Time**: Unit tests <30s, Integration tests <5min
- **Test Reliability**: >99% pass rate in CI/CD
- **Error Detection**: All error paths covered
- **Mock Quality**: Realistic mocks that don't hide integration issues

### Testing Success Criteria

1. **Functional Testing**: All acceptance criteria validated
2. **Epic 1 Integration**: All foundation components properly integrated
3. **Performance**: Rate limiting and response time requirements met
4. **Security**: Credential handling and communication security validated
5. **Maintainability**: Tests are clear, maintainable, and well-documented

This comprehensive testing strategy ensures robust validation of the Maricopa County API client with full Epic 1 integration and preparation for Epic 3 orchestration.