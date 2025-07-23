"""Integration tests for Maricopa County API client and adapter.

This module provides end-to-end integration tests that validate the complete
workflow from API requests through data transformation and Epic 1 schema compliance.
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from phoenix_real_estate.foundation import ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError,
    ValidationError,
    ProcessingError,
)
from phoenix_real_estate.foundation.database.schema import Property, DataSource
from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter


class TestMaricopaIntegration:
    """Integration tests for complete Maricopa workflow."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_api_key_integration",
            "MARICOPA_BASE_URL": "https://api.assessor.maricopa.gov/v1",
        }.get(key, default)
        config.get_int.side_effect = lambda key, default=None: {
            "MARICOPA_RATE_LIMIT": 100,  # Low limit for testing
            "MARICOPA_TIMEOUT": 10,
        }.get(key, default)
        return config

    @pytest.fixture
    async def client(self, mock_config):
        """Create client instance for testing."""
        client = MaricopaAPIClient(mock_config)
        yield client
        await client.close()

    @pytest.fixture
    def adapter(self):
        """Create adapter instance for testing."""
        return MaricopaDataAdapter(logger_name="integration_test")

    @pytest.fixture
    def realistic_api_response(self):
        """Realistic API response based on Maricopa County documentation."""
        return {
            "apn": "123-45-678",
            "parcel_id": "12345678",
            "property_type": "Residential",
            "legal_description": "Lot 15 Block 8 Desert Estates Phase II",
            "subdivision": "Desert Estates",
            "situs_address": {
                "house_number": "1234",
                "street_name": "Desert Willow",
                "street_type": "Ln",
                "city": "Phoenix",
                "state": "AZ",
                "zipcode": "85048-1234",
                "full_address": "1234 Desert Willow Ln, Phoenix, AZ 85048-1234"
            },
            "residential_details": {
                "bedrooms": 4,
                "bathrooms": 3.5,
                "half_bathrooms": 1,
                "living_area_sqft": 2850,
                "lot_size_sqft": 9600,
                "year_built": 2005,
                "floors": 2,
                "garage_spaces": 3,
                "pool": "Yes",
                "fireplace": "No",
                "ac_type": "Central Air",
                "heating_type": "Gas Forced Air"
            },
            "valuation": {
                "assessed_value": 425000,
                "market_value": 485000,
                "land_value": 150000,
                "improvement_value": 335000,
                "tax_amount": 4980,
                "tax_year": 2024,
                "assessment_date": "2024-01-01"
            },
            "ownership": {
                "owner_name": "Jane Smith",
                "mailing_address": "1234 Desert Willow Ln, Phoenix, AZ 85048"
            },
            "sales_history": [
                {
                    "sale_price": 450000,
                    "sale_date": "2023-06-15",
                    "document_type": "Warranty Deed",
                    "buyer": "Jane Smith",
                    "seller": "ABC Properties LLC"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_complete_workflow_search_to_property(self, client, adapter, realistic_api_response):
        """Test complete workflow: search → get details → adapt data."""
        # Mock search response
        search_response = {
            "Real Property": [
                {"apn": "123-45-678", "property_type": "Residential"},
                {"apn": "124-46-789", "property_type": "Residential"}
            ],
            "totals": {"Real Property": 2}
        }

        with patch("aiohttp.ClientSession.request") as mock_request:
            # Mock search request
            mock_search_response = AsyncMock()
            mock_search_response.status = 200
            mock_search_response.json = AsyncMock(return_value=search_response)
            mock_search_response.headers = {"Content-Length": "300"}

            # Mock details request
            mock_details_response = AsyncMock()
            mock_details_response.status = 200
            mock_details_response.json = AsyncMock(return_value=realistic_api_response)
            mock_details_response.headers = {"Content-Length": "1500"}

            # Configure mock to return different responses for different URLs
            def mock_request_side_effect(*args, **kwargs):
                if "search/property" in str(kwargs.get("url", "")):
                    return mock_search_response
                else:
                    return mock_details_response

            mock_request.return_value.__aenter__.side_effect = mock_request_side_effect

            with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                mock_wait.return_value = 0.0

                # Step 1: Search for properties
                search_results = await client.search_property("85048")
                assert len(search_results) == 2
                assert search_results[0]["apn"] == "123-45-678"

                # Step 2: Get detailed property data
                property_details = await client.get_parcel_details("123-45-678")
                assert property_details["apn"] == "123-45-678"
                assert property_details["property_type"] == "Residential"

                # Step 3: Transform to Epic 1 schema
                property_obj = await adapter.adapt_property(property_details)
                
                # Verify complete transformation
                assert isinstance(property_obj, Property)
                assert property_obj.property_id.startswith("maricopa_")
                assert property_obj.address.street == "1234 Desert Willow Ln"
                assert property_obj.address.city == "Phoenix"
                assert property_obj.features.bedrooms == 4
                assert property_obj.features.bathrooms == 3.5
                assert len(property_obj.price_history) > 0
                assert property_obj.current_price == 485000  # Market value should be current price
                assert property_obj.sources[0].source == DataSource.MARICOPA_COUNTY

    @pytest.mark.asyncio
    async def test_pagination_handling(self, client):
        """Test pagination across multiple pages of search results."""
        page_1_response = {
            "Real Property": [{"apn": f"12{i}-45-678", "property_type": "Residential"} for i in range(25)],
            "totals": {"Real Property": 50}
        }
        
        page_2_response = {
            "Real Property": [{"apn": f"13{i}-45-678", "property_type": "Residential"} for i in range(25)],
            "totals": {"Real Property": 50}
        }

        with patch("aiohttp.ClientSession.request") as mock_request:
            # Configure responses for different pages
            mock_responses = [
                AsyncMock(status=200, json=AsyncMock(return_value=page_1_response)),
                AsyncMock(status=200, json=AsyncMock(return_value=page_2_response))
            ]
            
            for response in mock_responses:
                response.headers = {"Content-Length": "2000"}

            mock_request.return_value.__aenter__.side_effect = mock_responses

            with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                mock_wait.return_value = 0.0

                # Test pagination
                page_1_results = await client.search_property("85001", page=1)
                page_2_results = await client.search_property("85001", page=2)

                assert len(page_1_results) == 25
                assert len(page_2_results) == 25
                assert page_1_results[0]["apn"].startswith("120")
                assert page_2_results[0]["apn"].startswith("130")

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, client):
        """Test rate limiting behavior during high-volume requests."""
        # Configure rapid requests to trigger rate limiting
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"Real Property": [], "totals": {"Real Property": 0}})
            mock_response.headers = {"Content-Length": "100"}
            mock_request.return_value.__aenter__.return_value = mock_response

            # Track rate limiter calls
            rate_limit_calls = []
            
            async def mock_wait(source):
                rate_limit_calls.append(source)
                return 0.1  # Small delay to simulate rate limiting

            with patch.object(client.rate_limiter, "wait_if_needed", side_effect=mock_wait):
                # Make multiple rapid requests
                tasks = [client.search_property(f"8500{i}") for i in range(5)]
                results = await asyncio.gather(*tasks)

                # Verify rate limiting was applied
                assert len(rate_limit_calls) == 5
                assert all(source == "maricopa_api" for source in rate_limit_calls)
                assert len(results) == 5

    @pytest.mark.asyncio
    async def test_error_recovery_and_retry(self, client, adapter):
        """Test error recovery and retry mechanisms."""
        # Simulate server error followed by success
        responses = [
            AsyncMock(status=500, reason="Internal Server Error", text=AsyncMock(return_value="Server Error")),
            AsyncMock(status=200, json=AsyncMock(return_value={"apn": "123-45-678", "address": {"house_number": "123", "street_name": "Main", "street_type": "St", "zipcode": "85001"}}))
        ]
        
        for response in responses:
            response.headers = {"Content-Length": "200"}

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.side_effect = responses

            with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                mock_wait.return_value = 0.0
                
                # First call should fail and retry, second call should succeed
                with patch("asyncio.sleep", new_callable=AsyncMock):  # Speed up retries
                    with patch("time.sleep"):
                        result = await client.get_parcel_details("123-45-678")

                assert result["apn"] == "123-45-678"
                assert client.error_count >= 1  # At least one error was recorded

    @pytest.mark.asyncio
    async def test_data_quality_validation(self, adapter):
        """Test data quality validation and error handling."""
        # Test with high-quality data
        high_quality_data = {
            "apn": "123-45-678",
            "property_type": "Residential",
            "legal_description": "Lot 15 Block 8 Test Subdivision",
            "address": {
                "house_number": "1234",
                "street_name": "Test",
                "street_type": "St",
                "city": "Phoenix",
                "state": "AZ",
                "zipcode": "85001"
            },
            "residential_details": {
                "bedrooms": 3,
                "bathrooms": 2.5,
                "living_area_sqft": 1850,
                "year_built": 2010
            },
            "valuation": {
                "assessed_value": 300000,
                "market_value": 350000,
                "tax_amount": 3500,
                "tax_year": 2024
            }
        }

        result = await adapter.adapt_property(high_quality_data)
        assert result.sources[0].quality_score > 0.8

        # Test with low-quality data (missing critical fields)
        low_quality_data = {
            "apn": "456-78-901",
            "address": {
                "house_number": "456",
                "street_name": "Oak",
                "street_type": "Ave",
                "zipcode": "85002"
            }
            # Missing most other data
        }

        result = await adapter.adapt_property(low_quality_data)
        assert result.sources[0].quality_score < 0.7

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, client):
        """Test handling of concurrent API requests."""
        with patch("aiohttp.ClientSession.request") as mock_request:
            # Create different responses for each request
            responses = []
            for i in range(10):
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"apn": f"12{i}-45-678", "address": {"zipcode": f"8500{i}"}})
                mock_response.headers = {"Content-Length": "300"}
                responses.append(mock_response)

            mock_request.return_value.__aenter__.side_effect = responses

            with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                mock_wait.return_value = 0.1  # Small delay for rate limiting

                # Make concurrent requests
                tasks = [client.get_parcel_details(f"12{i}-45-678") for i in range(10)]
                results = await asyncio.gather(*tasks)

                # Verify all requests completed successfully
                assert len(results) == 10
                for i, result in enumerate(results):
                    assert result["apn"] == f"12{i}-45-678"

                # Verify rate limiting was applied to all requests
                assert mock_wait.call_count == 10

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, client):
        """Test handling of authentication errors."""
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_request.return_value.__aenter__.return_value = mock_response

            with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                mock_wait.return_value = 0.0

                with pytest.raises(DataCollectionError, match="Authentication failed"):
                    await client.search_property("85001")

                assert client.error_count >= 1

    @pytest.mark.asyncio
    async def test_malformed_data_handling(self, adapter):
        """Test handling of malformed API responses."""
        # Test completely invalid data
        with pytest.raises(ValidationError, match="Raw data must be a dict"):
            await adapter.adapt_property("not a dictionary")

        # Test missing required fields
        with pytest.raises(ValidationError, match="Missing or invalid address section"):
            await adapter.adapt_property({"apn": "123-45-678"})

        # Test invalid address data
        with pytest.raises(ValidationError, match="Missing required address fields"):
            await adapter.adapt_property({
                "apn": "123-45-678",
                "address": {"incomplete": "data"}
            })

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, client):
        """Test that performance metrics are properly collected."""
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"Real Property": [], "totals": {"Real Property": 0}})
            mock_response.headers = {"Content-Length": "150"}
            mock_request.return_value.__aenter__.return_value = mock_response

            with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                mock_wait.return_value = 0.0

                # Make several requests
                for i in range(3):
                    await client.search_property(f"8500{i}")

                # Check metrics
                metrics = client.get_metrics()
                assert metrics["client_metrics"]["total_requests"] == 3
                assert metrics["client_metrics"]["total_errors"] == 0
                assert metrics["client_metrics"]["error_rate"] == 0.0
                assert metrics["client_metrics"]["last_request_time"] is not None

                # Check rate limiting metrics
                assert "rate_limiting" in metrics
                assert "configuration" in metrics

    @pytest.mark.asyncio 
    async def test_large_result_set_handling(self, client, adapter):
        """Test handling of large result sets and memory efficiency."""
        # Simulate large search result
        large_response = {
            "Real Property": [
                {"apn": f"{i:03d}-45-678", "property_type": "Residential"} 
                for i in range(100)
            ],
            "totals": {"Real Property": 100}
        }

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=large_response)
            mock_response.headers = {"Content-Length": "10000"}
            mock_request.return_value.__aenter__.return_value = mock_response

            with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                mock_wait.return_value = 0.0

                results = await client.search_property("85001")
                
                # Verify large result set handling
                assert len(results) == 100
                assert results[0]["apn"] == "000-45-678"
                assert results[99]["apn"] == "099-45-678"

                # Verify memory efficiency (no excessive duplication)
                assert client.request_count == 1


@pytest.mark.integration
class TestMaricopaProductionScenarios:
    """Integration tests simulating production scenarios."""

    @pytest.fixture
    def production_config(self):
        """Production-like configuration for testing."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "production_test_key",
            "MARICOPA_BASE_URL": "https://api.assessor.maricopa.gov/v1",
        }.get(key, default)
        config.get_int.side_effect = lambda key, default=None: {
            "MARICOPA_RATE_LIMIT": 1000,  # Production rate limit
            "MARICOPA_TIMEOUT": 30,
        }.get(key, default)
        return config

    @pytest.mark.asyncio
    async def test_high_volume_data_collection(self, production_config):
        """Test high-volume data collection scenario."""
        async with MaricopaAPIClient(production_config) as client:
            adapter = MaricopaDataAdapter(logger_name="production_test")

            # Simulate realistic batch processing
            zip_codes = ["85001", "85002", "85003", "85004", "85005"]
            properties_collected = 0

            with patch("aiohttp.ClientSession.request") as mock_request:
                # Mock responses for each zip code
                def create_mock_response(zip_code):
                    mock_response = AsyncMock()
                    mock_response.status = 200
                    mock_response.json = AsyncMock(return_value={
                        "Real Property": [
                            {"apn": f"{zip_code[-3:]}-{i:02d}-{j:03d}", "property_type": "Residential"}
                            for i in range(2) for j in range(5)  # 10 properties per zip
                        ],
                        "totals": {"Real Property": 10}
                    })
                    mock_response.headers = {"Content-Length": "2000"}
                    return mock_response

                responses = [create_mock_response(zip_code) for zip_code in zip_codes]
                mock_request.return_value.__aenter__.side_effect = responses

                with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                    mock_wait.return_value = 0.05  # Realistic rate limiting delay

                    # Process each zip code
                    for zip_code in zip_codes:
                        results = await client.search_property(zip_code)
                        properties_collected += len(results)

                    # Verify collection completed successfully
                    assert properties_collected == 50  # 10 properties × 5 zip codes
                    assert client.error_count == 0
                    assert mock_wait.call_count == 5  # Rate limiting applied to each request

    @pytest.mark.asyncio
    async def test_data_pipeline_resilience(self, production_config):
        """Test data pipeline resilience under various failure conditions."""
        async with MaricopaAPIClient(production_config) as client:
            adapter = MaricopaDataAdapter(logger_name="resilience_test")

            # Simulate mixed success/failure scenario
            responses = [
                AsyncMock(status=500, reason="Server Error"),  # Failure
                AsyncMock(status=200, json=AsyncMock(return_value={"Real Property": [{"apn": "123-45-678"}], "totals": {"Real Property": 1}})),  # Success
                AsyncMock(status=429, headers={"Retry-After": "1"}),  # Rate limit
                AsyncMock(status=200, json=AsyncMock(return_value={"Real Property": [{"apn": "124-46-789"}], "totals": {"Real Property": 1}})),  # Success
            ]

            for response in responses:
                if not hasattr(response, 'headers'):
                    response.headers = {"Content-Length": "100"}

            with patch("aiohttp.ClientSession.request") as mock_request:
                mock_request.return_value.__aenter__.side_effect = responses

                with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
                    mock_wait.return_value = 0.0

                    # Speed up retries for testing
                    with patch("asyncio.sleep", new_callable=AsyncMock):
                        with patch("time.sleep"):
                            successful_requests = 0
                            failed_requests = 0

                            for i in range(4):
                                try:
                                    result = await client.search_property(f"8500{i}")
                                    successful_requests += 1
                                except DataCollectionError:
                                    failed_requests += 1

                            # Verify resilience - some requests should succeed despite failures
                            assert successful_requests >= 2
                            assert client.error_count >= 1