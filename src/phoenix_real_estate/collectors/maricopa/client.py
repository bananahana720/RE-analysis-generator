"""Maricopa County API client with rate limiting and authentication.

This module provides a specialized HTTP client for the Maricopa County
Assessor's API with built-in rate limiting, authentication, and error handling.
"""

import time
import asyncio
import aiohttp
import os
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
from phoenix_real_estate.collectors.base.validators import (
    CommonValidators,
    ErrorHandlingUtils,
)


class MaricopaAPIClient(RateLimitObserver):
    """Async HTTP client for Maricopa County Assessor API.

    This client handles authentication, rate limiting, and request management
    for the Maricopa County API. It implements the RateLimitObserver protocol
    to respond to rate limit status changes.

    Key Features:
    - Custom AUTHORIZATION header authentication format
    - Rate limiting with connection pooling (limit=10, limit_per_host=5)
    - Epic 1's retry_async utility for exponential backoff
    - Comprehensive HTTP status code handling (401, 403, 429, 5xx)
    - Request/response logging with security compliance
    - Integration with Epic 1 configuration and logging
    - APN-based property lookup instead of property_id

    Configuration Required:
    - MARICOPA_API_KEY: API token for authentication (custom header format)
    - MARICOPA_BASE_URL: API base URL (default: https://mcassessor.maricopa.gov)
    - MARICOPA_RATE_LIMIT: Rate limit per hour (default: 1000)
    - MARICOPA_TIMEOUT: Request timeout in seconds (default: 30)
    """

    # API endpoints
    ENDPOINTS = {
        "search_property": "/search/property/",
        "search_subdivisions": "/search/sub/",
        "search_rentals": "/search/rental/",
        "parcel_details": "/parcel/{apn}",
        "property_info": "/parcel/{apn}/propertyinfo",
        "property_address": "/parcel/{apn}/address",
        "valuations": "/parcel/{apn}/valuations",
        "residential_details": "/parcel/{apn}/residential-details",
        "commercial_details": "/parcel/{apn}/commercial-details",
        "owner_details": "/parcel/{apn}/owner-details",
        "legal_details": "/parcel/{apn}/legal",
        "building_details": "/parcel/{apn}/building-details",
        "dwelling_details": "/parcel/{apn}/dwelling-details",
        "mapid": "/mapid/parcel/{apn}",
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

        # Log initialization
        self.logger.info(
            f"Maricopa API client initialized: {actual_requests_per_hour} req/hour "
            f"({requests_per_minute:.1f} req/min), timeout: {self.timeout_seconds}s"
        )


    def _validate_apn(self, apn: str) -> str:
        """Validate APN format for Maricopa County.
        
        Args:
            apn: The APN to validate
            
        Returns:
            Cleaned APN string
            
        Raises:
            ValidationError: If APN format is invalid
        """
        if not apn or not apn.strip():
            raise ValidationError("APN cannot be empty")
            
        cleaned_apn = apn.strip()
        
        # Basic APN format validation - should be at least 5 characters
        # Maricopa County APNs are typically in format like "123-45-678"
        if len(cleaned_apn) < 5:
            raise ValidationError("Invalid APN format: APN must be at least 5 characters")
            
        return cleaned_apn

    def _load_config(self) -> None:
        """Load and validate Epic 1 configuration."""
        try:
            # Epic 1 configuration keys - BaseConfig stores env vars as attributes
            self.api_key = getattr(
                self.config, "maricopa_api_key", os.getenv("MARICOPA_API_KEY", "")
            )
            self.base_url = getattr(
                self.config,
                "maricopa_base_url",
                os.getenv("MARICOPA_BASE_URL", "https://mcassessor.maricopa.gov"),
            )
            self.rate_limit = int(
                getattr(
                    self.config, "maricopa_rate_limit", os.getenv("MARICOPA_RATE_LIMIT", "1000")
                )
            )
            self.timeout_seconds = int(
                getattr(self.config, "maricopa_timeout", os.getenv("MARICOPA_TIMEOUT", "30"))
            )

            CommonValidators.validate_required_config(self.api_key, "MARICOPA_API_KEY")

            # Validate base URL format and enforce HTTPS
            self.base_url = CommonValidators.validate_base_url(self.base_url, require_https=True)

        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to load Maricopa API configuration: {str(e)}", original_error=e
            ) from e

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers for requests with secure authentication."""
        return {
            "AUTHORIZATION": self.api_key,  # Custom header format for Maricopa API
            "user-agent": "null",  # Required by Maricopa API documentation
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def search_property(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search properties by query string with pagination support.

        Args:
            query: Search query (address, owner name, APN, etc.)
            page: Page number for pagination (default: 1, 25 results per page)

        Returns:
            Dictionary containing search results and metadata

        Raises:
            DataCollectionError: If search request fails
            ValidationError: If query is invalid
        """
        # Validate query
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")

        try:
            params = {"query": query.strip(), "page": page}
            response_data = await self._make_request(
                "GET", self.ENDPOINTS["search_property"], params=params
            )

            # Log search results
            result_count = len(response_data.get("results", []))
            self.logger.info(
                f"Property search returned {result_count} results for page {page}",
                extra={"query": query[:50], "page": page, "result_count": result_count},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "search_property", query=query[:50], page=page)
            return {"results": [], "error": str(e)}

    async def get_parcel_details(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get all parcel information for a given APN.

        Args:
            apn: Assessor's Parcel Number (APN)

        Returns:
            Complete parcel data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If APN is invalid
        """
        # Validate APN format
        validated_apn = self._validate_apn(apn)

        try:
            endpoint = self.ENDPOINTS["parcel_details"].format(apn=validated_apn)
            response_data = await self._make_request("GET", endpoint)

            self.logger.debug(
                "Retrieved parcel details",
                extra={"apn": "[SANITIZED]", "has_data": bool(response_data)},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "get_parcel_details", apn="[SANITIZED]")

    async def get_property_info(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get property info section for a given APN.

        Args:
            apn: Assessor's Parcel Number (APN)

        Returns:
            Property info data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If APN is invalid
        """
        if not apn or not apn.strip():
            raise ValidationError("APN cannot be empty")

        try:
            endpoint = self.ENDPOINTS["property_info"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)

            self.logger.debug(
                "Retrieved property info",
                extra={"apn": "[SANITIZED]", "has_data": bool(response_data)},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "get_property_info", apn="[SANITIZED]")

    async def get_valuations(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get valuation history for a given APN.

        Args:
            apn: Assessor's Parcel Number (APN)

        Returns:
            Valuation history data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If APN is invalid
        """
        if not apn or not apn.strip():
            raise ValidationError("APN cannot be empty")

        try:
            endpoint = self.ENDPOINTS["valuations"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)

            self.logger.debug(
                "Retrieved valuations",
                extra={"apn": "[SANITIZED]", "has_data": bool(response_data)},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "get_valuations", apn="[SANITIZED]")

    async def get_residential_details(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get residential characteristics for a given APN.

        Args:
            apn: Assessor's Parcel Number (APN)

        Returns:
            Residential details data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If APN is invalid
        """
        if not apn or not apn.strip():
            raise ValidationError("APN cannot be empty")

        try:
            endpoint = self.ENDPOINTS["residential_details"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)

            self.logger.debug(
                "Retrieved residential details",
                extra={"apn": "[SANITIZED]", "has_data": bool(response_data)},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "get_residential_details", apn="[SANITIZED]")

    async def get_owner_details(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get owner information for a given APN.

        Args:
            apn: Assessor's Parcel Number (APN)

        Returns:
            Owner details data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If APN is invalid
        """
        if not apn or not apn.strip():
            raise ValidationError("APN cannot be empty")

        try:
            endpoint = self.ENDPOINTS["owner_details"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)

            self.logger.debug(
                "Retrieved owner details",
                extra={"apn": "[SANITIZED]", "has_data": bool(response_data)},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "get_owner_details", apn="[SANITIZED]")
            return []

    # Backward compatibility methods - these wrap the new API methods
    async def search_by_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Search properties by ZIP code - backward compatibility wrapper.

        This method provides backward compatibility by wrapping the new search_property
        method. It searches for properties in the given ZIP code.

        Args:
            zipcode: Valid US ZIP code (5-digit or ZIP+4 format)

        Returns:
            List of property data dictionaries from the API

        Raises:
            DataCollectionError: If search request fails
            ValidationError: If zipcode is invalid
        """
        # Validate ZIP code format
        CommonValidators.validate_zipcode(zipcode)

        try:
            # Use the new search_property method with zipcode as query
            response_data = await self.search_property(f"zipcode:{zipcode}")

            # Extract properties from response for backward compatibility
            properties = response_data.get("results", [])
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
        """Get detailed property information - backward compatibility wrapper.

        This method provides backward compatibility. If property_id looks like an APN,
        it will use get_parcel_details. Otherwise, it will attempt to search for the property.

        Args:
            property_id: Unique property identifier or APN

        Returns:
            Detailed property data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If property_id is invalid
        """
        CommonValidators.validate_property_id(property_id)

        try:
            # Check if property_id looks like an APN (contains dashes)
            if "-" in property_id:
                # Likely an APN, use get_parcel_details
                return await self.get_parcel_details(property_id)
            else:
                # Try to search for the property and return first result
                search_results = await self.search_property(property_id)
                results = search_results.get("results", [])
                if results:
                    # Get full details for the first result
                    first_result = results[0]
                    if "apn" in first_result:
                        return await self.get_parcel_details(first_result["apn"])
                    return first_result
                return None

        except Exception as e:
            await self._handle_request_error(e, "get_property_details", property_id="[SANITIZED]")

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
        return ErrorHandlingUtils.sanitize_url_for_logging(url)

    async def _handle_request_error(self, error: Exception, operation: str, **context: Any) -> None:
        """Handle and wrap request errors consistently with security compliance.

        Args:
            error: Original exception
            operation: Name of the operation that failed
            **context: Additional context for error tracking (sanitized)
        """
        self.error_count += 1

        # Sanitize context to prevent credential exposure
        sanitized_context = ErrorHandlingUtils.sanitize_context(context)

        self.logger.error(
            f"Maricopa API operation '{operation}' failed: {str(error)}",
            extra={"operation": operation, "context": sanitized_context},
            exc_info=True,
        )

        # Wrap the error with consistent handling
        wrapped_error = ErrorHandlingUtils.wrap_error(
            error,
            f"Maricopa API operation '{operation}'",
            DataCollectionError,
            context=sanitized_context,
            sanitize=False,  # Already sanitized
        )
        raise wrapped_error from error

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
