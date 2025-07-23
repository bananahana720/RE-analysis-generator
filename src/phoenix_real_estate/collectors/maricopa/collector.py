"""Maricopa County API collector implementation.

This module provides the complete collector implementation for the Maricopa
County Assessor's API, combining the API client and data adapter into a
unified data collection strategy.
"""

import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository, get_logger
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError,
    ConfigurationError,
    ValidationError,
    ProcessingError,
)
from phoenix_real_estate.foundation.database.schema import Property
from phoenix_real_estate.collectors.base.collector import DataCollector
from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter, DataValidator


class MaricopaAPICollector(DataCollector):
    """Complete collector implementation for Maricopa County API.

    This collector integrates the MaricopaAPIClient and MaricopaDataAdapter
    to provide a complete data collection solution. It implements the
    DataCollector strategy pattern and integrates with Epic 1 foundation
    components and Epic 3 orchestration systems.

    Key Features:
    - Complete API-to-repository data pipeline
    - Configurable collection parameters
    - Duplicate detection and incremental updates
    - Error recovery and retry logic
    - Performance metrics and monitoring
    - Epic 3 orchestration integration ready

    Configuration Required:
    - maricopa.api.*: API client configuration
    - maricopa.collection.batch_size: Records per collection batch (default 100)
    - maricopa.collection.max_retries: Maximum retry attempts (default 3)
    - maricopa.collection.retry_delay_seconds: Delay between retries (default 5)
    """

    def __init__(
        self,
        config: ConfigProvider,
        repository: PropertyRepository,
        logger_name: str = "collectors.maricopa",
        client: Optional[MaricopaAPIClient] = None,
        adapter: Optional[MaricopaDataAdapter] = None,
    ) -> None:
        """Initialize the Maricopa API collector.

        Args:
            config: Configuration provider from Epic 1
            repository: Property repository from Epic 1
            logger_name: Logger name for this collector instance
            client: Optional API client (will create if not provided)
            adapter: Optional data adapter (will create if not provided)
        """
        # Get collection config as dict using get_typed
        collection_config = config.get_typed("maricopa.collection", dict, default={})
        super().__init__(collection_config)

        self.config = config
        self.repository = repository
        self.validator = DataValidator()

        # Initialize Epic 1 logger
        self.logger = get_logger(logger_name)

        # Initialize components
        self.client = client or MaricopaAPIClient(config)
        self.adapter = adapter or MaricopaDataAdapter(self.validator, f"{logger_name}.adapter")

        # Load collection configuration using get_typed
        self.batch_size = config.get_typed("maricopa.collection.batch_size", int, default=100)
        self.max_retries = config.get_typed("maricopa.collection.max_retries", int, default=3)
        self.retry_delay_seconds = config.get_typed(
            "maricopa.collection.retry_delay_seconds", int, default=5
        )

        # Collection metrics
        self.total_collected = 0
        self.total_saved = 0
        self.total_errors = 0
        self.collection_start_time: Optional[datetime] = None

        self.logger.info(
            f"Maricopa collector initialized: batch_size={self.batch_size}, "
            f"max_retries={self.max_retries}"
        )

    def validate_config(self) -> bool:
        """Validate collector configuration.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Validate API client can be configured
            required_fields = ["maricopa.api.base_url"]  # API key is validated by client

            missing_fields = []
            for field in required_fields:
                if not self.config.get(field):
                    missing_fields.append(field)

            if missing_fields:
                raise ConfigurationError(
                    f"Missing required configuration fields: {', '.join(missing_fields)}"
                )

            # Validate batch size is reasonable
            if self.batch_size <= 0 or self.batch_size > 1000:
                raise ConfigurationError(
                    f"Invalid batch_size: {self.batch_size}. Must be between 1 and 1000."
                )

            # Test repository connection
            try:
                # Simple test to verify repository is accessible
                self.repository.find_updated_since(datetime.now() - timedelta(days=1))
            except Exception as e:
                raise ConfigurationError(
                    f"Repository connection test failed: {str(e)}", original_error=e
                ) from e

            return True

        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"Configuration validation failed: {str(e)}", original_error=e
            ) from e

    def collect(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Collect property data from Maricopa County API.

        Args:
            **kwargs: Collection parameters:
                - search_params: Dict with search criteria (zip_codes, date_range, etc.)
                - max_results: Maximum number of records to collect
                - incremental: Whether to do incremental collection since last run
                - save_to_repository: Whether to save results to repository (default True)

        Returns:
            List of collected and transformed property data

        Raises:
            DataCollectionError: If collection fails
        """
        self.collection_start_time = datetime.now()
        collection_id = f"maricopa_{self.collection_start_time.strftime('%Y%m%d_%H%M%S')}"

        try:
            # Extract collection parameters
            search_params = kwargs.get("search_params", {})
            max_results = kwargs.get("max_results")
            incremental = kwargs.get("incremental", False)
            save_to_repository = kwargs.get("save_to_repository", True)

            self._log_collection_start(
                collection_id=collection_id,
                search_params=search_params,
                max_results=max_results,
                incremental=incremental,
            )

            # Prepare search parameters
            if incremental:
                search_params = self._prepare_incremental_search(search_params)

            # Collect raw data from API
            raw_data = self._collect_raw_data(search_params, max_results)

            if not raw_data:
                self.logger.info("No data collected from API")
                return []

            # Transform data using adapter
            transformed_data = self._transform_data_batch(raw_data)

            # Save to repository if requested
            if save_to_repository and transformed_data:
                saved_count = self._save_data_batch(transformed_data)
                self.total_saved = saved_count

                self.logger.info(
                    f"Saved {saved_count}/{len(transformed_data)} properties to repository"
                )

            # Update metrics
            self.total_collected = len(raw_data)
            duration_ms = int((datetime.now() - self.collection_start_time).total_seconds() * 1000)

            self._log_collection_success(len(transformed_data), duration_ms)

            return transformed_data

        except Exception as e:
            self._handle_collection_error(e, "collect", collection_id=collection_id, **kwargs)

    def collect_by_zip_codes(
        self,
        zip_codes: List[str],
        max_per_zip: Optional[int] = None,
        save_to_repository: bool = True,
    ) -> List[Dict[str, Any]]:
        """Collect properties for specific ZIP codes.

        Args:
            zip_codes: List of ZIP codes to collect
            max_per_zip: Maximum properties per ZIP code
            save_to_repository: Whether to save to repository

        Returns:
            List of collected property data
        """
        search_params = {"zip_codes": zip_codes}
        if max_per_zip:
            search_params["limit_per_zip"] = max_per_zip

        return self.collect(
            search_params=search_params,
            max_results=len(zip_codes) * (max_per_zip or 100),
            save_to_repository=save_to_repository,
        )

    def collect_recent_sales(
        self,
        days_back: int = 30,
        zip_codes: Optional[List[str]] = None,
        save_to_repository: bool = True,
    ) -> List[Dict[str, Any]]:
        """Collect recent property sales data.

        Args:
            days_back: Number of days back to search
            zip_codes: Optional ZIP code filter
            save_to_repository: Whether to save to repository

        Returns:
            List of recent sales data
        """
        try:
            # Get recent sales from API
            sales_data = self.client.get_recent_sales(days_back, zip_codes)

            if not sales_data:
                self.logger.info("No recent sales data available")
                return []

            # Transform and optionally save
            transformed_data = self._transform_data_batch(sales_data)

            if save_to_repository and transformed_data:
                self._save_data_batch(transformed_data)

            return transformed_data

        except Exception as e:
            self._handle_collection_error(
                e, "collect_recent_sales", days_back=days_back, zip_codes=zip_codes
            )

    def _collect_raw_data(
        self, search_params: Dict[str, Any], max_results: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Collect raw data from the API with batching and error handling.

        Args:
            search_params: Search parameters for API
            max_results: Maximum results to collect

        Returns:
            List of raw API response data
        """
        collected_data = []
        current_batch = 0

        try:
            while True:
                # Prepare batch parameters
                batch_params = dict(search_params)
                batch_params["offset"] = current_batch * self.batch_size
                batch_params["limit"] = min(
                    self.batch_size,
                    (max_results - len(collected_data)) if max_results else self.batch_size,
                )

                # Collect batch with retries
                batch_data = self._collect_batch_with_retry(batch_params)

                if not batch_data:
                    # No more data available
                    break

                collected_data.extend(batch_data)

                self.logger.debug(
                    f"Collected batch {current_batch + 1}: {len(batch_data)} records "
                    f"(total: {len(collected_data)})"
                )

                # Check if we've reached the limit or got less than batch size
                if (max_results and len(collected_data) >= max_results) or len(
                    batch_data
                ) < self.batch_size:
                    break

                current_batch += 1

                # Brief pause between batches to be respectful
                time.sleep(0.1)

            return collected_data

        except Exception as e:
            raise DataCollectionError(
                f"Raw data collection failed after collecting {len(collected_data)} records",
                context={
                    "collected_count": len(collected_data),
                    "search_params": search_params,
                    "current_batch": current_batch,
                },
                original_error=e,
            ) from e

    def _collect_batch_with_retry(self, batch_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect a single batch with retry logic.

        Args:
            batch_params: Parameters for the batch request

        Returns:
            List of data records for the batch
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return self.client.search_properties(batch_params)

            except Exception as e:
                last_exception = e
                self.total_errors += 1

                if attempt < self.max_retries:
                    wait_time = self.retry_delay_seconds * (2**attempt)  # Exponential backoff
                    self.logger.warning(
                        f"Batch collection attempt {attempt + 1} failed, "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(
                        f"Batch collection failed after {self.max_retries + 1} attempts: {str(e)}"
                    )

        # If we get here, all retries failed
        raise DataCollectionError(
            f"Batch collection failed after {self.max_retries + 1} attempts",
            context={"batch_params": batch_params, "attempts": self.max_retries + 1},
            original_error=last_exception,
        ) from last_exception

    def _transform_data_batch(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform a batch of raw data using the adapter.

        Args:
            raw_data: List of raw API data records

        Returns:
            List of transformed property records
        """
        try:
            return self.adapter.transform_batch(raw_data)
        except Exception as e:
            raise DataCollectionError(
                f"Data transformation failed for batch of {len(raw_data)} records",
                context={"batch_size": len(raw_data)},
                original_error=e,
            ) from e

    def _save_data_batch(self, transformed_data: List[Dict[str, Any]]) -> int:
        """Save transformed data to the repository.

        Args:
            transformed_data: List of transformed property records

        Returns:
            Number of records successfully saved
        """
        saved_count = 0

        for record in transformed_data:
            try:
                # Check if property already exists
                existing = self.repository.find_by_id(record["property_id"])

                if existing:
                    # Update existing record if newer
                    existing_date = datetime.fromisoformat(
                        existing.get("last_updated", "1900-01-01")
                    )
                    new_date = datetime.fromisoformat(record["last_updated"])

                    if new_date > existing_date:
                        self.repository.save(record)
                        saved_count += 1
                        self.logger.debug(f"Updated existing property: {record['property_id']}")
                    else:
                        self.logger.debug(
                            f"Skipped older data for property: {record['property_id']}"
                        )
                else:
                    # Save new record
                    self.repository.save(record)
                    saved_count += 1
                    self.logger.debug(f"Saved new property: {record['property_id']}")

            except Exception as e:
                self.logger.error(
                    f"Failed to save property {record.get('property_id', 'unknown')}: {str(e)}",
                    exc_info=True,
                )
                # Continue with other records

        return saved_count

    def _prepare_incremental_search(self, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare search parameters for incremental collection.

        Args:
            base_params: Base search parameters

        Returns:
            Search parameters with incremental filters
        """
        params = dict(base_params)

        if self.last_collection_time:
            # Search for properties updated since last collection
            params["updated_since"] = self.last_collection_time.isoformat()
            self.logger.info(f"Incremental collection since: {self.last_collection_time}")
        else:
            # First run - collect recent data (last 30 days)
            since_date = datetime.now() - timedelta(days=30)
            params["updated_since"] = since_date.isoformat()
            self.logger.info("First incremental run - collecting last 30 days")

        return params

    def get_collection_metrics(self) -> Dict[str, Any]:
        """Get detailed collection metrics.

        Returns:
            Dictionary with collection performance metrics
        """
        base_metrics = self.get_collection_status()

        # Add client and adapter metrics
        client_metrics = self.client.get_metrics() if self.client else {}

        # Calculate performance metrics
        duration = None
        if self.collection_start_time:
            duration = (datetime.now() - self.collection_start_time).total_seconds()

        collection_rate = None
        if duration and duration > 0:
            collection_rate = self.total_collected / duration  # records per second

        return {
            **base_metrics,
            "collection_metrics": {
                "total_collected": self.total_collected,
                "total_saved": self.total_saved,
                "total_errors": self.total_errors,
                "collection_duration_seconds": duration,
                "collection_rate_per_second": collection_rate,
                "batch_size": self.batch_size,
                "max_retries": self.max_retries,
            },
            "client_metrics": client_metrics,
        }

    def get_source_name(self) -> str:
        """Return source name for Epic 3 orchestration.

        Returns:
            Source identifier string for orchestration tracking
        """
        return "maricopa_api"

    async def collect_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Collect all properties for zipcode with comprehensive logging.

        Epic 3 orchestration interface method for zipcode-based collection.
        Provides detailed logging and error context for orchestration monitoring.

        Args:
            zipcode: ZIP code to collect properties for

        Returns:
            List of raw property data dictionaries

        Raises:
            DataCollectionError: If collection fails with detailed context
        """
        collection_id = f"zipcode_{zipcode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            self.logger.info(
                f"Starting zipcode collection for {zipcode}",
                extra={
                    "collection_id": collection_id,
                    "zipcode": zipcode,
                    "source": self.get_source_name(),
                },
            )

            # Use async API client method
            properties = await self.client.search_by_zipcode(zipcode)

            self.logger.info(
                f"Completed zipcode collection: {len(properties)} properties found",
                extra={
                    "collection_id": collection_id,
                    "zipcode": zipcode,
                    "property_count": len(properties),
                },
            )

            return properties

        except Exception as e:
            self._handle_collection_error(
                e, "collect_zipcode", collection_id=collection_id, zipcode=zipcode
            )

    async def collect_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Collect detailed property information.

        Epic 3 orchestration interface method for individual property collection.
        Provides detailed property information with comprehensive error handling.

        Args:
            property_id: Unique property identifier

        Returns:
            Property data dictionary if found, None if not found

        Raises:
            DataCollectionError: If collection fails with detailed context
        """
        try:
            self.logger.info(
                f"Collecting property details for {property_id}",
                extra={"property_id": property_id, "source": self.get_source_name()},
            )

            # Use API client to get property details
            raw_data = await self.client.get_property_details(property_id)

            if not raw_data:
                self.logger.warning(
                    f"No data found for property {property_id}", extra={"property_id": property_id}
                )
                return None

            # Transform the data
            transformed_data = self.adapter.transform(raw_data)

            self.logger.info(
                f"Successfully collected property details for {property_id}",
                extra={"property_id": property_id, "has_data": bool(transformed_data)},
            )

            return transformed_data

        except Exception as e:
            self._handle_collection_error(e, "collect_property_details", property_id=property_id)

    async def adapt_property(self, raw_data: Dict[str, Any]) -> Property:
        """Adapter integration for Epic 3 orchestration.

        Transforms raw property data into Epic 1 Property schema objects
        for consistent data handling across the orchestration pipeline.

        Args:
            raw_data: Raw property data from API

        Returns:
            Property object conforming to Epic 1 schema

        Raises:
            ValidationError: If data validation fails
            ProcessingError: If transformation fails
        """
        try:
            self.logger.debug(
                "Adapting raw property data to Property schema",
                extra={
                    "property_id": raw_data.get("property_id", "unknown"),
                    "source": self.get_source_name(),
                },
            )

            # Transform using adapter
            transformed_data = self.adapter.transform(raw_data)

            # Convert to Property object
            property_obj = Property(**transformed_data)

            # Validate the Property object
            if not self.validator.validate_property(property_obj):
                raise ValidationError(
                    f"Property validation failed for {property_obj.property_id}",
                    context={"property_id": property_obj.property_id},
                )

            self.logger.debug(
                f"Successfully adapted property {property_obj.property_id}",
                extra={"property_id": property_obj.property_id},
            )

            return property_obj

        except Exception as e:
            property_id = raw_data.get("property_id", "unknown")
            self.logger.error(
                f"Property adaptation failed for {property_id}: {str(e)}",
                extra={"property_id": property_id, "error_type": type(e).__name__},
                exc_info=True,
            )

            if isinstance(e, (ValidationError, ProcessingError)):
                raise

            raise ProcessingError(
                f"Property adaptation failed: {str(e)}",
                context={"property_id": property_id, "source": self.get_source_name()},
                original_error=e,
            ) from e

    async def close(self) -> None:
        """Close collector and cleanup resources."""
        if hasattr(self, "client") and self.client:
            await self.client.close()
        self.logger.info("Maricopa collector closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()
