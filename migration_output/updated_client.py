"""Maricopa County API client with rate limiting and authentication.

This module provides a specialized HTTP client for the Maricopa County
Assessor's API with built-in rate limiting, authentication, and error handling.

UPDATED: Uses real API endpoints at https://mcassessor.maricopa.gov
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
    for the Maricopa County API using the REAL endpoints and authentication.

    Key Features:
    - AUTHORIZATION header authentication (not Bearer token)
    - Real API endpoints at https://mcassessor.maricopa.gov
    - Pagination support for search results (25 per page)
    - Comprehensive parcel detail endpoints
    - Rate limiting with connection pooling
    - Epic 1's retry_async utility for exponential backoff
    - Comprehensive HTTP status code handling

    Configuration Required:
    - MARICOPA_API_KEY: API token for AUTHORIZATION header
    - MARICOPA_BASE_URL: API base URL (default: https://mcassessor.maricopa.gov)
    - MARICOPA_RATE_LIMIT: Rate limit per hour (default: 1000)
    - MARICOPA_TIMEOUT: Request timeout in seconds (default: 30)
    """

    # REAL API endpoints from official documentation
    ENDPOINTS = {
        # Search endpoints
        "search_property": "/search/property/?q={query}",
        "search_property_paged": "/search/property/?q={query}&page={page}",
        "search_subdivisions": "/search/sub/?q={query}",
        "search_rentals": "/search/rental/?q={query}",
        
        # Parcel detail endpoints
        "parcel_details": "/parcel/{apn}",
        "property_info": "/parcel/{apn}/propertyinfo",
        "property_address": "/parcel/{apn}/address", 
        "property_valuations": "/parcel/{apn}/valuations",
        "residential_details": "/parcel/{apn}/residential-details",
        "owner_details": "/parcel/{apn}/owner-details",
        
        # Mapping endpoints
        "mapid_parcel": "/mapid/parcel/{apn}",
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
                "MARICOPA_BASE_URL", "https://mcassessor.maricopa.gov"  # CORRECTED URL
            )
            self.rate_limit = self.config.get_int("MARICOPA_RATE_LIMIT", 1000)
            self.timeout_seconds = self.config.get_int("MARICOPA_TIMEOUT", 30)

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
        """Get default HTTP headers for requests with CORRECTED authentication."""
        return {
            "AUTHORIZATION": self.api_key,  # CORRECTED: Use AUTHORIZATION, not Bearer
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Phoenix-RE-Data-Collector/1.0",
        }

    async def search_properties(self, query: str, page: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search properties using the real API endpoint.

        Args:
            query: Search query (ZIP code, address, APN, etc.)
            page: Optional page number for pagination (25 results per page)

        Returns:
            List of property data dictionaries from the API

        Raises:
            DataCollectionError: If search request fails
            ValidationError: If query is invalid
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        try:
            if page:
                endpoint = self.ENDPOINTS["search_property_paged"].format(
                    query=query.strip(), page=page
                )
            else:
                endpoint = self.ENDPOINTS["search_property"].format(query=query.strip())
                
            response_data = await self._make_request("GET", endpoint)

            # Extract properties from response - real API format
            if isinstance(response_data, dict):
                properties = response_data.get("results", response_data.get("properties", []))
                if isinstance(properties, dict):
                    properties = [properties]  # Handle single result
            else:
                properties = response_data if isinstance(response_data, list) else []

            self.logger.info(
                f"Property search returned {len(properties)} results",
                extra={"query": "[SANITIZED]", "page": page, "result_count": len(properties)},
            )
            return properties

        except Exception as e:
            await self._handle_request_error(e, "search_properties", query="[SANITIZED]", page=page)

    async def get_parcel_details(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get detailed parcel information using real API endpoint.

        Args:
            apn: Assessor Parcel Number (with or without dashes/dots/spaces)

        Returns:
            Detailed parcel data dictionary or None if not found

        Raises:
            DataCollectionError: If request fails
            ValidationError: If APN is invalid
        """
        if not apn or not apn.strip():
            raise ValueError("APN cannot be empty")

        try:
            endpoint = self.ENDPOINTS["parcel_details"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)

            self.logger.debug(
                "Retrieved parcel details",
                extra={"apn": "[SANITIZED]", "has_data": bool(response_data)},
            )
            return response_data

        except Exception as e:
            await self._handle_request_error(e, "get_parcel_details", apn="[SANITIZED]")

    async def get_property_info(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get property information for a parcel.

        Args:
            apn: Assessor Parcel Number

        Returns:
            Property information dictionary

        Raises:
            DataCollectionError: If request fails
        """
        try:
            endpoint = self.ENDPOINTS["property_info"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)
            return response_data
        except Exception as e:
            await self._handle_request_error(e, "get_property_info", apn="[SANITIZED]")

    async def get_property_address(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get property address for a parcel.

        Args:
            apn: Assessor Parcel Number

        Returns:
            Property address dictionary

        Raises:
            DataCollectionError: If request fails
        """
        try:
            endpoint = self.ENDPOINTS["property_address"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)
            return response_data
        except Exception as e:
            await self._handle_request_error(e, "get_property_address", apn="[SANITIZED]")

    async def get_property_valuations(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get valuation history for a parcel (past 5 years).

        Args:
            apn: Assessor Parcel Number

        Returns:
            Valuation history dictionary

        Raises:
            DataCollectionError: If request fails
        """
        try:
            endpoint = self.ENDPOINTS["property_valuations"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)
            return response_data
        except Exception as e:
            await self._handle_request_error(e, "get_property_valuations", apn="[SANITIZED]")

    async def get_owner_details(self, apn: str) -> Optional[Dict[str, Any]]:
        """Get owner details for a parcel.

        Args:
            apn: Assessor Parcel Number

        Returns:
            Owner details dictionary

        Raises:
            DataCollectionError: If request fails
        """
        try:
            endpoint = self.ENDPOINTS["owner_details"].format(apn=apn.strip())
            response_data = await self._make_request("GET", endpoint)
            return response_data
        except Exception as e:
            await self._handle_request_error(e, "get_owner_details", apn="[SANITIZED]")

    async def search_subdivisions(self, query: str) -> List[Dict[str, Any]]:
        """Search subdivisions by name.

        Args:
            query: Subdivision name to search

        Returns:
            List of subdivision data with parcel counts

        Raises:
            DataCollectionError: If request fails
        """
        try:
            endpoint = self.ENDPOINTS["search_subdivisions"].format(query=query.strip())
            response_data = await self._make_request("GET", endpoint)
            
            subdivisions = response_data.get("results", []) if isinstance(response_data, dict) else response_data
            return subdivisions if isinstance(subdivisions, list) else [subdivisions]
            
        except Exception as e:
            await self._handle_request_error(e, "search_subdivisions", query="[SANITIZED]")

    # ... [Rest of the methods remain the same: _ensure_session, _make_request, etc.]
    # ... [Just update the error handling for new API response format]

    async def _handle_request_error(self, error: Exception, operation: str, **context: Any) -> None:
        """Handle and wrap request errors with updated error patterns.

        Args:
            error: Original exception
            operation: Name of the operation that failed
            **context: Additional context for error tracking (sanitized)
        """
        self.error_count += 1

        # Sanitize context to prevent credential exposure
        sanitized_context = ErrorHandlingUtils.sanitize_context(context)

        # Check for API-specific error patterns
        error_message = str(error)
        if "Unauthorized access" in error_message:
            error_message = "Authentication failed - check MARICOPA_API_KEY and contact Maricopa County for access"

        self.logger.error(
            f"Maricopa API operation '{operation}' failed: {error_message}",
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

    # ... [Rest of class implementation remains similar]

# DEPRECATED METHODS (remove these):
# - search_by_zipcode() -> use search_properties()
# - get_property_details() -> use get_parcel_details() 
# - get_recent_sales() -> NOT AVAILABLE in real API
