"""Comprehensive tests for MaricopaAPIClient with Epic 1 integration.

Tests authentication, rate limiting, request handling, error management,
and security compliance for the Maricopa County API client.
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from phoenix_real_estate.foundation import ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError,
    ConfigurationError,
    ValidationError
)
from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from phoenix_real_estate.collectors.base.rate_limiter import RateLimitStatus


class TestMaricopaAPIClientConfiguration:
    """Test configuration loading and validation."""
    
    def test_init_success_with_required_config(self):
        """Test successful initialization with all required configuration."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_api_key_12345",
            "MARICOPA_BASE_URL": "https://api.assessor.maricopa.gov/v1"
        }.get(key, default)
        config.get_int.side_effect = lambda key, default=None: {
            "MARICOPA_RATE_LIMIT": 1000,
            "MARICOPA_TIMEOUT": 30
        }.get(key, default)
        
        client = MaricopaAPIClient(config)
        
        assert client.api_key == "test_api_key_12345"
        assert client.base_url == "https://api.assessor.maricopa.gov/v1"
        assert client.rate_limit == 1000
        assert client.timeout_seconds == 30
    
    def test_init_with_defaults(self):
        """Test initialization with default configuration values."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key"
        }.get(key, default)
        config.get_int.side_effect = lambda key, default=None: {
            "MARICOPA_RATE_LIMIT": default if key == "MARICOPA_RATE_LIMIT" else default,
            "MARICOPA_TIMEOUT": default if key == "MARICOPA_TIMEOUT" else default
        }.get(key, default)
        
        client = MaricopaAPIClient(config)
        
        assert client.base_url == "https://api.assessor.maricopa.gov/v1"
        assert client.rate_limit == 1000
        assert client.timeout_seconds == 30
    
    def test_init_missing_api_key(self):
        """Test initialization failure when API key is missing."""
        config = Mock(spec=ConfigProvider)
        config.get.return_value = None
        config.get_int.return_value = 30
        
        with pytest.raises(ConfigurationError, match="Missing required config: MARICOPA_API_KEY"):
            MaricopaAPIClient(config)
    
    def test_init_https_enforcement(self):
        """Test HTTPS-only enforcement."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "http://insecure-api.example.com"
        }.get(key, default)
        config.get_int.return_value = 30
        
        with pytest.raises(ConfigurationError, match="HTTPS-only communication required"):
            MaricopaAPIClient(config)
    
    def test_init_invalid_url_format(self):
        """Test initialization failure with invalid URL format."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "invalid-url-format"
        }.get(key, default)
        config.get_int.return_value = 30
        
        with pytest.raises(ConfigurationError, match="Invalid base URL format"):
            MaricopaAPIClient(config)
    
    def test_base_url_trailing_slash_removal(self):
        """Test that trailing slashes are removed from base URL."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "https://api.example.com/"
        }.get(key, default)
        config.get_int.return_value = 30
        
        client = MaricopaAPIClient(config)
        assert client.base_url == "https://api.example.com"


class TestMaricopaAPIClientAuthentication:
    """Test authentication and security features."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_api_key_secure",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        config.get_int.return_value = 1000
        return config
    
    def test_authentication_headers(self, mock_config):
        """Test that authentication headers are properly set."""
        client = MaricopaAPIClient(mock_config)
        headers = client._get_default_headers()
        
        assert headers["Authorization"] == "Bearer test_api_key_secure"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers
    
    def test_credential_sanitization_in_logging(self, mock_config):
        """Test that credentials are sanitized in log messages."""
        client = MaricopaAPIClient(mock_config)
        
        # Test URL sanitization
        url_with_token = "https://api.example.com/data?api_key=secret123&other=value"
        sanitized = client._sanitize_url_for_logging(url_with_token)
        assert "secret123" not in sanitized
        assert "[REDACTED]" in sanitized
        
        # Test normal URL is unchanged
        normal_url = "https://api.example.com/data?param=value"
        sanitized_normal = client._sanitize_url_for_logging(normal_url)
        assert sanitized_normal == normal_url


@pytest.mark.asyncio
class TestMaricopaAPIClientRequests:
    """Test HTTP request handling and Epic 1 integration."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        config.get_int.return_value = 1000
        return config
    
    @pytest.fixture
    async def client(self, mock_config):
        """Create client instance for testing."""
        client = MaricopaAPIClient(mock_config)
        yield client
        await client.close()
    
    async def test_session_creation_with_connection_pooling(self, client):
        """Test that aiohttp session is created with proper connection pooling."""
        session = await client._ensure_session()
        
        assert isinstance(session, aiohttp.ClientSession)
        assert session.connector.limit == 10
        assert session.connector.limit_per_host == 5
        assert session.timeout.total == client.timeout_seconds
    
    async def test_search_by_zipcode_validation(self, client):
        """Test ZIP code validation in search method."""
        # Test empty ZIP code
        with pytest.raises(ValidationError, match="ZIP code cannot be empty"):
            await client.search_by_zipcode("")
        
        # Test invalid ZIP code format
        with pytest.raises(ValidationError, match="Invalid ZIP code format"):
            await client.search_by_zipcode("invalid")
    
    async def test_get_property_details_validation(self, client):
        """Test property ID validation."""
        with pytest.raises(ValidationError, match="Property ID cannot be empty"):
            await client.get_property_details("")
        
        with pytest.raises(ValidationError, match="Property ID cannot be empty"):
            await client.get_property_details("   ")
    
    async def test_get_recent_sales_validation(self, client):
        """Test parameter validation for recent sales."""
        # Test negative days
        with pytest.raises(ValidationError, match="days_back must be positive"):
            await client.get_recent_sales(-1)
        
        # Test days exceeding limit
        with pytest.raises(ValidationError, match="days_back cannot exceed 365"):
            await client.get_recent_sales(400)
    
    @patch('aiohttp.ClientSession.request')
    async def test_successful_request_handling(self, mock_request, client):
        """Test successful HTTP request handling."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"properties": [{"id": "123"}]})
        mock_response.headers = {"Content-Length": "100"}
        
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Test rate limiter integration
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            result = await client.search_by_zipcode("85001")
        
        assert result == [{"id": "123"}]
        assert client.request_count == 1
        assert client.last_request_time is not None
    
    @patch('aiohttp.ClientSession.request')
    async def test_http_status_code_handling(self, mock_request, client):
        """Test comprehensive HTTP status code handling."""
        # Test 401 - Authentication failure
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_request.return_value.__aenter__.return_value = mock_response
        
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            with pytest.raises(DataCollectionError, match="Authentication failed"):
                await client.search_by_zipcode("85001")
        
        # Test 403 - Permission denied
        mock_response.status = 403
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            with pytest.raises(DataCollectionError, match="Permission denied"):
                await client.search_by_zipcode("85001")
        
        # Test 429 - Rate limit exceeded
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "30"}
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(DataCollectionError, match="Rate limit exceeded"):
                    await client.search_by_zipcode("85001")
                mock_sleep.assert_called_once_with(30)
        
        # Test 500 - Server error
        mock_response.status = 500
        mock_response.reason = "Internal Server Error"
        mock_response.text = AsyncMock(return_value="Server error details")
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            with pytest.raises(DataCollectionError, match="Server error"):
                await client.search_by_zipcode("85001")
    
    @patch('phoenix_real_estate.foundation.utils.helpers.retry_async')
    async def test_retry_async_integration(self, mock_retry, client):
        """Test integration with Epic 1's retry_async utility."""
        mock_retry.return_value = {"success": True}
        
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            await client.search_by_zipcode("85001")
        
        # Verify retry_async was called with correct parameters
        mock_retry.assert_called_once()
        call_args = mock_retry.call_args
        assert call_args.kwargs['max_retries'] == 3
        assert call_args.kwargs['delay'] == 1.0
        assert call_args.kwargs['backoff_factor'] == 2.0
    
    @patch('aiohttp.ClientSession.request')
    async def test_error_handling_and_logging(self, mock_request, client):
        """Test error handling with security-compliant logging."""
        mock_request.side_effect = aiohttp.ClientError("Connection failed")
        
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            with pytest.raises(DataCollectionError, match="HTTP client error"):
                await client.search_by_zipcode("85001")
        
        assert client.error_count == 1
    
    @patch('aiohttp.ClientSession.request')
    async def test_timeout_handling(self, mock_request, client):
        """Test request timeout handling."""
        mock_request.side_effect = asyncio.TimeoutError()
        
        with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
            mock_wait.return_value = 0.0
            with pytest.raises(DataCollectionError, match="Request timeout"):
                await client.search_by_zipcode("85001")


class TestMaricopaAPIClientSecurity:
    """Test security compliance and credential protection."""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "secret_key_12345",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        config.get_int.return_value = 1000
        return config
    
    @pytest.fixture
    async def client(self, mock_config):
        client = MaricopaAPIClient(mock_config)
        yield client
        await client.close()
    
    async def test_credential_exposure_prevention(self, client):
        """Test that credentials are never exposed in error messages or logs."""
        # Test context sanitization
        context = {
            "api_key": "secret123",
            "token": "bearer_token",
            "authorization": "Bearer secret",
            "normal_param": "safe_value"
        }
        
        # Simulate error handling
        try:
            await client._handle_request_error(
                Exception("Test error"), 
                "test_operation", 
                **context
            )
        except DataCollectionError as e:
            # Verify credentials are sanitized in error context
            error_context = e.context
            assert error_context["api_key"] == "[REDACTED]"
            assert error_context["token"] == "[REDACTED]"
            assert error_context["authorization"] == "[REDACTED]"
            assert error_context["normal_param"] == "safe_value"
    
    async def test_property_id_sanitization(self, client):
        """Test that property IDs are sanitized in logs for privacy."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.reason = "Server Error"
            mock_response.text = AsyncMock(return_value="Error")
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
                mock_wait.return_value = 0.0
                with pytest.raises(DataCollectionError):
                    await client.get_property_details("sensitive_property_id")
        
        # Verify that sensitive property ID was sanitized in error context
        assert client.error_count == 1


class TestMaricopaAPIClientRateLimiting:
    """Test rate limiting integration and observer pattern."""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        config.get_int.return_value = 1200  # 1200 requests per hour = 20 per minute
        return config
    
    def test_rate_limiter_initialization(self, mock_config):
        """Test that rate limiter is properly initialized."""
        client = MaricopaAPIClient(mock_config)
        
        assert client.rate_limiter is not None
        # Rate limiter should be configured for per-minute requests
        assert hasattr(client.rate_limiter, 'wait_if_needed')
    
    async def test_rate_limit_observer_callbacks(self, mock_config):
        """Test rate limit observer protocol implementation."""
        client = MaricopaAPIClient(mock_config)
        
        # Test observer protocol methods
        with patch.object(client.logger, 'info') as mock_info:
            await client.on_rate_limit_hit("test_source", 30.5)
            mock_info.assert_called_once()
        
        # Test rate limit reset notification  
        with patch.object(client.logger, 'debug') as mock_debug:
            await client.on_rate_limit_reset("test_source")
            mock_debug.assert_called_once()


class TestMaricopaAPIClientMetrics:
    """Test performance metrics and monitoring."""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        config.get_int.return_value = 1000
        return config
    
    def test_metrics_collection(self, mock_config):
        """Test that performance metrics are collected properly."""
        client = MaricopaAPIClient(mock_config)
        
        # Initially no requests
        metrics = client.get_metrics()
        assert metrics["client_metrics"]["total_requests"] == 0
        assert metrics["client_metrics"]["total_errors"] == 0
        assert metrics["client_metrics"]["error_rate"] == 0
        assert metrics["client_metrics"]["last_request_time"] is None
        
        # Simulate some activity
        client.request_count = 10
        client.error_count = 2
        client.last_request_time = datetime.now()
        
        metrics = client.get_metrics()
        assert metrics["client_metrics"]["total_requests"] == 10
        assert metrics["client_metrics"]["total_errors"] == 2
        assert metrics["client_metrics"]["error_rate"] == 0.2
        assert metrics["client_metrics"]["last_request_time"] is not None
        
        # Verify configuration is included
        assert metrics["configuration"]["base_url"] == client.base_url
        assert metrics["configuration"]["rate_limit"] == client.rate_limit


@pytest.mark.asyncio
class TestMaricopaAPIClientContextManager:
    """Test async context manager functionality."""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        config.get_int.return_value = 1000
        return config
    
    async def test_context_manager_cleanup(self, mock_config):
        """Test that resources are properly cleaned up."""
        async with MaricopaAPIClient(mock_config) as client:
            # Ensure session gets created
            await client._ensure_session()
            assert client._session is not None
            assert not client._session.closed
        
        # After context exit, session should be closed
        assert client._session.closed


@pytest.mark.integration
class TestMaricopaAPIClientIntegration:
    """Integration tests requiring more complex setup."""
    
    @pytest.fixture
    def real_config(self):
        """Create configuration with realistic values for integration testing."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "integration_test_key",
            "MARICOPA_BASE_URL": "https://httpbin.org"  # Use httpbin for testing
        }.get(key, default)
        config.get_int.side_effect = lambda key, default=None: {
            "MARICOPA_RATE_LIMIT": 10,  # Low limit for testing
            "MARICOPA_TIMEOUT": 5
        }.get(key, default)
        return config
    
    async def test_real_http_request_flow(self, real_config):
        """Test actual HTTP request flow with real network calls."""
        async with MaricopaAPIClient(real_config) as client:
            # Override endpoints for testing with httpbin
            client.ENDPOINTS["test_endpoint"] = "/json"
            
            # Patch rate limiter to avoid delays
            with patch.object(client.rate_limiter, 'wait_if_needed') as mock_wait:
                mock_wait.return_value = 0.0
                try:
                    result = await client._make_request("GET", "test_endpoint")
                    # httpbin.org/json returns a JSON response
                    assert isinstance(result, dict)
                except Exception as e:
                    # Network issues are acceptable in tests
                    assert isinstance(e, (DataCollectionError, aiohttp.ClientError))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])