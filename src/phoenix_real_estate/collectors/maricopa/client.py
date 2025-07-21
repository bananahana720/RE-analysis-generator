"""Maricopa County API client with rate limiting and authentication.

This module provides a specialized HTTP client for the Maricopa County
Assessor's API with built-in rate limiting, authentication, and error handling.
"""

import time
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional
from datetime import datetime

from phoenix_real_estate.foundation import Logger, get_logger, ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError,
    ConfigurationError,
    ValidationError,
)
from phoenix_real_estate.foundation.utils.helpers import retry_async
from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter, RateLimitObserver


class MaricopaAPIClient(RateLimitObserver):
    """Async HTTP client for Maricopa County Assessor API.

    This client handles authentication, rate limiting, and request management
    for the Maricopa County API. It implements the RateLimitObserver protocol
    to respond to rate limit status changes.

    Key Features:
    - Bearer token authentication with secure credential handling
    - Rate limiting with connection pooling (limit=10, limit_per_host=5)
    - Epic 1's retry_async utility for exponential backoff
    - Comprehensive HTTP status code handling (401, 403, 429, 5xx)
    - Request/response logging with security compliance
    - Integration with Epic 1 configuration and logging

    Configuration Required:
    - MARICOPA_API_KEY: Bearer token for authentication
    - MARICOPA_BASE_URL: API base URL (default: https://api.assessor.maricopa.gov/v1)
    - MARICOPA_RATE_LIMIT: Rate limit per hour (default: 1000)
    - MARICOPA_TIMEOUT: Request timeout in seconds (default: 30)
    """

    # API endpoints
    ENDPOINTS = {
        "search_by_zipcode": "/properties/search/zipcode/{zipcode}",
        "property_details": "/properties/{property_id}",
        "recent_sales": "/sales/recent",
        "property_history": "/properties/{property_id}/history",
    }

    def __init__(self, config: ConfigProvider, requests_per_hour: Optional[int] = None) -> None:
        """Initialize the Maricopa API client.

        Args:
            config: Configuration provider from Epic 1 foundation
            requests_per_hour: Override default rate limit

        Raises:
            ConfigurationError: If required configuration is missing
        """
        self.config = config
        self.logger: Logger = get_logger("collectors.maricopa.client")

        # Load configuration
        self._load_config()

        # Set up rate limiting (convert hourly limit to per-minute)
        actual_requests_per_hour = requests_per_hour or self.rate_limit
        requests_per_minute = actual_requests_per_hour / 60.0

        self.rate_limiter = RateLimiter(
            requests_per_minute=int(requests_per_minute),
            safety_margin=0.10,  # 10% safety margin
            window_duration=60,  # 60 second windows
        )
        self.rate_limiter.add_observer(self)

        # Session will be initialized in async context
        self._session: Optional[aiohttp.ClientSession] = None

        # Metrics tracking
        self.request_count = 0
        self.error_count = 0
        self.last_request_time: Optional[datetime] = None

        self.logger.info(
            f"Maricopa API client initialized: {actual_requests_per_hour} req/hour "
            f"({requests_per_minute:.1f} req/min), timeout: {self.timeout_seconds}s"
        )

    def _load_config(self) -> None:
        """Load and validate Epic 1 configuration."""
        try:
            # Epic 1 configuration keys
            self.api_key = self.config.get("MARICOPA_API_KEY")
            self.base_url = self.config.get(
                "MARICOPA_BASE_URL", "https://api.assessor.maricopa.gov/v1"
            )
            self.rate_limit = self.config.get_int("MARICOPA_RATE_LIMIT", 1000)
            self.timeout_seconds = self.config.get_int("MARICOPA_TIMEOUT", 30)

            if not self.api_key:
                raise ConfigurationError("Missing required config: MARICOPA_API_KEY")

            # Validate base URL format and enforce HTTPS
            if not self.base_url.startswith("https://"):
                if self.base_url.startswith("http://"):
                    raise ConfigurationError(
                        "HTTPS-only communication required, HTTP URLs not allowed"
                    )
                else:
                    raise ConfigurationError(f"Invalid base URL format: {self.base_url}")

            # Remove trailing slash from base URL
            self.base_url = self.base_url.rstrip("/")

        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to load Maricopa API configuration: {str(e)}", original_error=e
            ) from e

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers for requests with secure authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Phoenix-RE-Data-Collector/1.0",
        }

    async def search_by_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Search properties by ZIP code with validation and logging.

        Args:
            zipcode: Valid US ZIP code (5-digit or ZIP+4 format)

        Returns:
            List of property data dictionaries from the API

        Raises:
            DataCollectionError: If search request fails
            ValidationError: If zipcode is invalid
        """
        if not zipcode or not zipcode.strip():
            raise ValidationError("ZIP code cannot be empty")

        # Validate ZIP code format
        from phoenix_real_estate.foundation.utils.helpers import is_valid_zipcode

        if not is_valid_zipcode(zipcode):
            raise ValidationError(f"Invalid ZIP code format: {zipcode}")

        try:
            endpoint = self.ENDPOINTS["search_by_zipcode"].format(zipcode=zipcode.strip())
            response_data = await self._make_request("GET", endpoint)

            # Extract properties from response
            properties = response_data.get("properties", [])
            if isinstance(properties, dict):
                properties = [properties]  # Handle single result

            self.logger.info(
                f"ZIP code search returned {len(properties)} results",
                extra={"zipcode": zipcode, "result_count": len(properties)},
            )
            return properties

        except Exception as e:
            await self._handle_request_error(e, "search_by_zipcode", zipcode=zipcode)

    async def get_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed property information with error handling.

        Args:
            property_id: Unique property identifier

        Returns:
            Detailed property data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If property_id is invalid
        """
        if not property_id or not property_id.strip():
            raise ValidationError("Property ID cannot be empty")

        try:
            endpoint = self.ENDPOINTS["property_details"].format(property_id=property_id.strip())
            response_data = await self._make_request("GET", endpoint)

            self.logger.debug(
                "Retrieved property details",
                extra={"property_id": "[SANITIZED]", "has_data": bool(response_data)},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "get_property_details", property_id="[SANITIZED]")

    async def get_recent_sales(
        self, days_back: int = 30, zip_codes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get recent property sales data.

        Args:
            days_back: Number of days back to search
            zip_codes: Optional list of zip codes to filter by

        Returns:
            List of recent sales data

        Raises:
            DataCollectionError: If request fails
            ValidationError: If parameters are invalid
        """
        if days_back <= 0:
            raise ValidationError("days_back must be positive")
        if days_back > 365:
            raise ValidationError("days_back cannot exceed 365")

        params = {"days_back": days_back}
        if zip_codes:
            params["zip_codes"] = ",".join(zip_codes)

        try:
            response_data = await self._make_request("GET", "recent_sales", params=params)

            sales = response_data.get("sales", [])
            if isinstance(sales, dict):
                sales = [sales]

            self.logger.info(
                "Retrieved recent sales data",
                extra={"days_back": days_back, "result_count": len(sales)},
            )
            return sales

        except Exception as e:
            await self._handle_request_error(
                e,
                "get_recent_sales",
                days_back=days_back,
                zip_codes="[SANITIZED]" if zip_codes else None,
            )

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session is initialized with proper connection pooling."""
        if self._session is None or self._session.closed:
            # Connection pooling configuration
            connector = aiohttp.TCPConnector(
                limit=10,  # Total connection pool size
                limit_per_host=5,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                enable_cleanup_closed=True,
            )

            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(
                headers=self._get_default_headers(), connector=connector, timeout=timeout
            )
        return self._session

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting, authentication and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path or full endpoint from ENDPOINTS
            params: URL parameters
            json_data: JSON payload for POST/PUT requests

        Returns:
            JSON response data as dictionary

        Raises:
            DataCollectionError: If request fails after retries
        """
        # Build full URL
        if endpoint.startswith("/"):
            url = f"{self.base_url}{endpoint}"
        elif endpoint in self.ENDPOINTS:
            url = f"{self.base_url}{self.ENDPOINTS[endpoint]}"
        else:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Apply rate limiting
        await self.rate_limiter.wait_if_needed("maricopa_api")

        # Use Epic 1's retry_async utility for exponential backoff
        return await retry_async(
            self._make_single_request,
            method,
            url,
            params,
            json_data,
            max_retries=3,
            delay=1.0,
            backoff_factor=2.0,
        )

    async def _make_single_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a single HTTP request with comprehensive error handling.

        Args:
            method: HTTP method
            url: Full URL to request
            params: URL parameters
            json_data: JSON payload

        Returns:
            JSON response data

        Raises:
            DataCollectionError: For various HTTP error conditions
        """
        session = await self._ensure_session()
        start_time = time.time()

        try:
            async with session.request(
                method=method, url=url, params=params, json=json_data
            ) as response:
                duration_ms = int((time.time() - start_time) * 1000)

                # Update metrics
                self.request_count += 1
                self.last_request_time = datetime.now()

                # Log request (sanitize URL for security)
                sanitized_url = self._sanitize_url_for_logging(url)
                self.logger.debug(
                    f"{method} {sanitized_url} -> {response.status} ({duration_ms}ms)",
                    extra={
                        "method": method,
                        "status_code": response.status,
                        "duration_ms": duration_ms,
                        "response_size": response.headers.get("Content-Length", "unknown"),
                    },
                )

                # Handle different HTTP status codes
                if response.status == 200:
                    return await response.json()

                elif response.status == 401:
                    # Authentication failure
                    self.error_count += 1
                    raise DataCollectionError(
                        "Authentication failed - invalid API key",
                        context={"status_code": 401, "url": self._sanitize_url_for_logging(url)},
                    )

                elif response.status == 403:
                    # Permission denied
                    self.error_count += 1
                    raise DataCollectionError(
                        "Permission denied - insufficient API access",
                        context={"status_code": 403, "url": self._sanitize_url_for_logging(url)},
                    )

                elif response.status == 429:
                    # Rate limit exceeded - parse Retry-After header
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self.logger.warning(
                        f"API rate limit exceeded, waiting {retry_after}s",
                        extra={"retry_after": retry_after},
                    )
                    await asyncio.sleep(retry_after)
                    raise DataCollectionError(
                        f"Rate limit exceeded, retry after {retry_after}s",
                        context={"status_code": 429, "retry_after": retry_after},
                    )

                elif 500 <= response.status < 600:
                    # Server error - will be retried by retry_async
                    self.error_count += 1
                    error_text = await response.text()
                    raise DataCollectionError(
                        f"Server error: {response.status} - {response.reason}",
                        context={
                            "status_code": response.status,
                            "response_text": error_text[:200] if error_text else None,
                        },
                    )

                else:
                    # Other client errors (400, 404, etc.)
                    self.error_count += 1
                    error_text = await response.text()
                    raise DataCollectionError(
                        f"HTTP {response.status}: {response.reason}",
                        context={
                            "status_code": response.status,
                            "response_text": error_text[:200] if error_text else None,
                        },
                    )

        except aiohttp.ClientError as e:
            self.error_count += 1
            raise DataCollectionError(
                f"HTTP client error: {str(e)}",
                context={"url": self._sanitize_url_for_logging(url), "method": method},
                original_error=e,
            ) from e
        except asyncio.TimeoutError as e:
            self.error_count += 1
            raise DataCollectionError(
                f"Request timeout after {self.timeout_seconds}s",
                context={
                    "url": self._sanitize_url_for_logging(url),
                    "timeout": self.timeout_seconds,
                },
                original_error=e,
            ) from e
        except Exception as e:
            self.error_count += 1
            raise DataCollectionError(
                f"Unexpected error during HTTP request: {str(e)}",
                context={"url": self._sanitize_url_for_logging(url), "method": method},
                original_error=e,
            ) from e

    def _sanitize_url_for_logging(self, url: str) -> str:
        """Sanitize URL for logging to prevent credential exposure."""
        if "api_key" in url.lower() or "token" in url.lower():
            # Replace query parameters that might contain credentials
            import re

            return re.sub(r"([?&](?:api_key|token|auth)=)[^&]*", r"\1[REDACTED]", url)
        return url

    async def _handle_request_error(self, error: Exception, operation: str, **context: Any) -> None:
        """Handle and wrap request errors consistently with security compliance.

        Args:
            error: Original exception
            operation: Name of the operation that failed
            **context: Additional context for error tracking (sanitized)
        """
        self.error_count += 1

        # Sanitize context to prevent credential exposure
        sanitized_context = {}
        for key, value in context.items():
            if key in ("api_key", "token", "authorization"):
                sanitized_context[key] = "[REDACTED]"
            elif isinstance(value, str) and ("token" in key.lower() or "key" in key.lower()):
                sanitized_context[key] = "[REDACTED]"
            else:
                sanitized_context[key] = value

        self.logger.error(
            f"Maricopa API operation '{operation}' failed: {str(error)}",
            extra={"operation": operation, "context": sanitized_context},
            exc_info=True,
        )

        # Re-raise if already a DataCollectionError
        if isinstance(error, DataCollectionError):
            raise error

        # Wrap other exceptions
        raise DataCollectionError(
            f"Maricopa API operation '{operation}' failed: {str(error)}",
            context={"operation": operation, **sanitized_context},
            original_error=error,
        ) from error

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics.

        Returns:
            Dictionary containing client performance metrics
        """
        rate_limit_metrics = self.rate_limiter.get_performance_metrics()

        return {
            "client_metrics": {
                "total_requests": self.request_count,
                "total_errors": self.error_count,
                "error_rate": self.error_count / max(1, self.request_count),
                "last_request_time": self.last_request_time.isoformat()
                if self.last_request_time
                else None,
            },
            "rate_limiting": rate_limit_metrics,
            "configuration": {
                "base_url": self.base_url,
                "rate_limit": self.rate_limit,
                "timeout_seconds": self.timeout_seconds,
            },
        }

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        self.logger.info("Maricopa API client closed")

    # RateLimitObserver protocol implementation
    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        """Called when a request is made."""
        pass  # No specific action needed for request notifications

    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        """Called when rate limit is hit and waiting is required."""
        self.logger.info(f"Rate limit hit for {source}, waiting {wait_time:.1f}s")

    async def on_rate_limit_reset(self, source: str) -> None:
        """Called when rate limit window resets for a source."""
        self.logger.debug(f"Rate limit window reset for {source}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()
