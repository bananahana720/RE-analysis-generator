"""Data adapter base class for transforming raw data to standardized format.

This module defines the DataAdapter abstract base class that standardizes
the transformation of raw collector data into the property schema format
expected by the Epic 1 PropertyRepository.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from phoenix_real_estate.foundation import Logger, get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError


class DataAdapter(ABC):
    """Abstract base class for data adapters.

    Data adapters implement the adapter pattern to transform raw data
    from various sources into the standardized property schema format
    used by the Epic 1 PropertyRepository.

    Key Features:
    - Adapter pattern implementation
    - Data validation and normalization
    - Integration with Epic 1 property schema
    - Epic 3 orchestration pipeline ready

    Attributes:
        logger: Logger instance from Epic 1 foundation
        source_name: Name of the data source being adapted
    """

    def __init__(self, source_name: str) -> None:
        """Initialize the data adapter.

        Args:
            source_name: Name of the data source (e.g., "maricopa_api", "mls_web")
        """
        self.logger: Logger = get_logger(f"adapters.{source_name}")
        self.source_name = source_name

    @abstractmethod
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw data to standardized property schema.

        This method must be implemented by concrete adapters to define
        how raw source data is transformed to the standard property format.

        Args:
            raw_data: Raw data dictionary from the collector

        Returns:
            Standardized property data dictionary matching the schema

        Raises:
            ValidationError: If raw data is invalid or incomplete
            ProcessingError: If transformation fails
        """
        pass

    @abstractmethod
    def validate_raw_data(self, raw_data: Dict[str, Any]) -> bool:
        """Validate raw data before transformation.

        Args:
            raw_data: Raw data to validate

        Returns:
            True if data is valid for transformation

        Raises:
            ValidationError: If data is invalid with specific details
        """
        pass

    def transform_batch(self, raw_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform a batch of raw data records.

        Args:
            raw_data_list: List of raw data dictionaries

        Returns:
            List of transformed property data dictionaries

        Raises:
            ProcessingError: If batch transformation fails
        """
        transformed_records = []
        failed_records = []

        for i, raw_record in enumerate(raw_data_list):
            try:
                if self.validate_raw_data(raw_record):
                    transformed = self.transform(raw_record)
                    if self._validate_transformed_data(transformed):
                        transformed_records.append(transformed)
                    else:
                        failed_records.append((i, "transformed_validation_failed"))
                else:
                    failed_records.append((i, "raw_validation_failed"))

            except Exception as e:
                self.logger.warning(
                    f"Failed to transform record {i}: {str(e)}",
                    extra={"record_index": i, "error": str(e)},
                )
                failed_records.append((i, str(e)))

        if failed_records:
            self.logger.info(
                f"Batch transformation completed with {len(failed_records)} failures out of {len(raw_data_list)} records"
            )

        if not transformed_records and failed_records:
            raise ProcessingError(
                f"All records failed transformation in batch of {len(raw_data_list)}",
                context={"source": self.source_name, "failed_records": len(failed_records)},
            )

        return transformed_records

    def _validate_transformed_data(self, transformed_data: Dict[str, Any]) -> bool:
        """Validate transformed data matches property schema.

        Args:
            transformed_data: Data after transformation

        Returns:
            True if data matches expected property schema
        """
        required_fields = ["property_id", "address", "last_updated"]

        try:
            # Check required fields exist
            for field in required_fields:
                if field not in transformed_data:
                    self.logger.error(f"Missing required field: {field}")
                    return False

            # Validate address structure
            address = transformed_data.get("address", {})
            if not isinstance(address, dict):
                self.logger.error("Address must be a dictionary")
                return False

            address_fields = ["street", "city", "zip_code"]
            for field in address_fields:
                if field not in address or not address[field]:
                    self.logger.error(f"Missing required address field: {field}")
                    return False

            # Validate property_id is not empty
            if not transformed_data.get("property_id"):
                self.logger.error("Property ID cannot be empty")
                return False

            # Validate last_updated is datetime or ISO string
            last_updated = transformed_data.get("last_updated")
            if isinstance(last_updated, str):
                try:
                    datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                except ValueError:
                    self.logger.error("Invalid last_updated datetime format")
                    return False
            elif not isinstance(last_updated, datetime):
                self.logger.error("last_updated must be datetime or ISO string")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False

    def _generate_property_id(self, address_data: Dict[str, str]) -> str:
        """Generate a unique property ID from address data.

        Args:
            address_data: Dictionary with street, city, zip_code

        Returns:
            Unique property identifier string
        """
        street = str(address_data.get("street", "")).lower().strip()
        city = str(address_data.get("city", "")).lower().strip()
        zip_code = str(address_data.get("zip_code", "")).strip()

        # Clean and normalize street address
        street_cleaned = "".join(c for c in street if c.isalnum() or c.isspace())
        street_cleaned = "-".join(street_cleaned.split())

        # Clean city name
        city_cleaned = "".join(c for c in city if c.isalnum() or c.isspace())
        city_cleaned = "-".join(city_cleaned.split())

        return f"{street_cleaned}-{city_cleaned}-{zip_code}"

    def _normalize_price(self, price_value: Any) -> Optional[float]:
        """Normalize price values to float.

        Args:
            price_value: Raw price value (string, int, float)

        Returns:
            Normalized price as float, or None if invalid
        """
        if price_value is None:
            return None

        try:
            # Handle string prices with $ and commas
            if isinstance(price_value, str):
                cleaned = price_value.replace("$", "").replace(",", "").strip()
                return float(cleaned) if cleaned else None

            # Handle numeric values
            return float(price_value) if price_value else None

        except (ValueError, TypeError):
            self.logger.warning(f"Could not normalize price value: {price_value}")
            return None

    def _extract_numeric_features(self, raw_data: Dict[str, Any]) -> Dict[str, Optional[int]]:
        """Extract numeric property features (beds, baths, sqft).

        Args:
            raw_data: Raw data containing property features

        Returns:
            Dictionary with normalized numeric features
        """
        features = {}

        # Extract beds
        beds = raw_data.get("beds") or raw_data.get("bedrooms") or raw_data.get("bed_count")
        features["beds"] = self._normalize_integer(beds)

        # Extract baths
        baths = raw_data.get("baths") or raw_data.get("bathrooms") or raw_data.get("bath_count")
        features["baths"] = self._normalize_integer(baths)

        # Extract square footage
        sqft = (
            raw_data.get("sqft")
            or raw_data.get("square_feet")
            or raw_data.get("living_area")
            or raw_data.get("interior_sqft")
        )
        features["sqft"] = self._normalize_integer(sqft)

        # Extract lot size
        lot_size = raw_data.get("lot_size") or raw_data.get("lot_sqft") or raw_data.get("land_area")
        features["lot_size"] = self._normalize_integer(lot_size)

        return features

    def _normalize_integer(self, value: Any) -> Optional[int]:
        """Normalize values to integer.

        Args:
            value: Raw value to normalize

        Returns:
            Normalized integer or None if invalid
        """
        if value is None:
            return None

        try:
            if isinstance(value, str):
                cleaned = "".join(c for c in value if c.isdigit())
                return int(cleaned) if cleaned else None
            return int(float(value)) if value else None
        except (ValueError, TypeError):
            return None
