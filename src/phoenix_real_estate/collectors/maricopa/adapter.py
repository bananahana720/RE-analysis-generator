"""Maricopa County API data adapter implementation.

This module transforms raw data from the Maricopa County API into the
Epic 1 Property schema format for repository storage.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from phoenix_real_estate.foundation.utils.exceptions import ValidationError, ProcessingError
from phoenix_real_estate.foundation.utils.helpers import (
    safe_int,
    safe_float,
    normalize_address,
    generate_property_id,
)
from phoenix_real_estate.foundation.database.schema import (
    Property,
    PropertyAddress,
    PropertyFeatures,
    PropertyPrice,
    PropertyTaxInfo,
    DataSource,
    DataCollectionMetadata,
)
from phoenix_real_estate.collectors.base.adapter import DataAdapter
from phoenix_real_estate.collectors.base.validators import (
    CommonValidators,
    ErrorHandlingUtils,
)


class DataValidator:
    """Simple data validator for Epic 1 schema compatibility."""

    @staticmethod
    def validate_property(property_obj: Property) -> bool:
        """Validate Property object meets schema requirements."""
        try:
            # Basic validation - check essential fields
            if not property_obj or not hasattr(property_obj, "property_id"):
                return False

            if not property_obj.property_id or not property_obj.property_id.strip():
                return False

            if not property_obj.address:
                return False

            if not hasattr(property_obj.address, "street") or not property_obj.address.street:
                return False

            if not hasattr(property_obj.address, "zipcode") or not property_obj.address.zipcode:
                return False

            return True
        except Exception:
            return False


class MaricopaDataAdapter(DataAdapter):
    """Adapter for transforming Maricopa County API data to Epic 1 Property schema.

    This adapter transforms raw JSON data from the Maricopa County API into
    Epic 1 Property objects with proper schema validation and normalization.

    Key Features:
    - Maps Maricopa API responses to Epic 1 Property schema
    - Uses Epic 1 safe utilities for data conversions
    - Handles address normalization with units
    - Extracts multiple price types with history
    - Preserves original data in listing_details
    - Full Epic 1 schema compatibility

    Maricopa API Response Structure:
    {
        "property_info": {"apn": "123-45-678", "legal_description": "..."},
        "address": {"house_number": "123", "street_name": "Main", "street_type": "St"},
        "assessment": {"assessed_value": 300000, "market_value": 350000},
        "characteristics": {"bedrooms": 3, "bathrooms": 2.5, "living_area_sqft": 1800}
    }
    """

    def __init__(
        self, validator: Optional[DataValidator] = None, logger_name: Optional[str] = None
    ) -> None:
        """Initialize the Maricopa data adapter.

        Args:
            validator: DataValidator instance for Epic 1 schema validation
            logger_name: Logger name override for testing
        """
        logger_suffix = logger_name or "maricopa_api"
        super().__init__(f"adapters.{logger_suffix}")
        self.validator = validator or DataValidator()

        # Enhanced field mapping for Maricopa API structure
        self.field_mappings = {
            # Address fields - nested structure
            "address": {
                "house_number": ["house_number", "street_number", "number"],
                "street_name": ["street_name", "street", "name"],
                "street_type": ["street_type", "street_suffix", "type"],
                "unit": ["unit", "apartment", "apt", "suite"],
                "city": ["city", "municipality"],
                "state": ["state", "state_code"],
                "zipcode": ["zip_code", "zipcode", "postal_code"],
            },
            # Property characteristics - nested structure
            "characteristics": {
                "bedrooms": ["bedrooms", "bed_count", "beds"],
                "bathrooms": ["bathrooms", "bath_count", "baths", "full_baths"],
                "half_bathrooms": ["half_bathrooms", "half_baths"],
                "living_area_sqft": ["living_area_sqft", "square_feet", "sqft", "interior_sqft"],
                "lot_size_sqft": ["lot_size_sqft", "lot_size", "land_area_sqft"],
                "year_built": ["year_built", "construction_year"],
                "floors": ["floors", "stories"],
                "garage_spaces": ["garage_spaces", "garage_count"],
                "pool": ["pool", "has_pool"],
                "fireplace": ["fireplace", "has_fireplace"],
                "ac_type": ["ac_type", "cooling", "air_conditioning"],
                "heating_type": ["heating_type", "heating_system"],
            },
            # Assessment/pricing - nested structure
            "assessment": {
                "assessed_value": ["assessed_value", "tax_assessed_value"],
                "market_value": ["market_value", "full_cash_value", "total_value"],
                "land_value": ["land_value", "land_assessed_value"],
                "improvement_value": ["improvement_value", "building_value"],
                "tax_amount": ["tax_amount", "annual_tax", "property_tax"],
                "tax_year": ["tax_year", "assessment_year"],
            },
            # Property info - nested structure
            "property_info": {
                "apn": ["apn", "parcel_number", "parcel_id"],
                "legal_description": ["legal_description", "legal_desc"],
                "property_type": ["property_type", "use_code", "property_class"],
                "subdivision": ["subdivision", "development", "tract"],
            },
            # Sales data - may be nested or flat
            "sales": {
                "last_sale_price": ["last_sale_price", "sale_price", "prior_sale_price"],
                "last_sale_date": ["last_sale_date", "sale_date", "prior_sale_date"],
            },
        }

    async def adapt_property(self, raw_data: Dict[str, Any]) -> Property:
        """Main adaptation method to transform raw Maricopa data to Epic 1 Property.

        Args:
            raw_data: Raw data from Maricopa API

        Returns:
            Property object following Epic 1 schema

        Raises:
            ValidationError: If raw data validation fails
            ProcessingError: If transformation fails
        """
        try:
            # Validate input data
            self.validate_raw_data(raw_data)

            # Extract core components
            address = self._extract_address(raw_data.get("address", {}))
            features = self._extract_features(raw_data.get("characteristics", {}))
            price_history = self._extract_prices(raw_data.get("assessment", {}))
            tax_info = self._extract_tax_info(raw_data)
            metadata = self._create_metadata(raw_data)

            # Generate property ID using Epic 1 utility
            property_id = generate_property_id(address.full_address, address.zipcode, "maricopa")

            # Create Property object
            property_obj = Property(
                property_id=property_id,
                address=address,
                features=features,
                price_history=price_history,
                current_price=price_history[0].amount if price_history else None,
                tax_info=tax_info,
                sources=[metadata],
                raw_data={"maricopa_api": raw_data},
            )

            # Validate with Epic 1 schema
            if not self.validator.validate_property(property_obj):
                raise ProcessingError(
                    "Property validation failed after transformation",
                    context={"property_id": property_id},
                )

            self.logger.debug(f"Successfully adapted Maricopa property: {property_id}")
            return property_obj

        except (ValidationError, ProcessingError):
            raise
        except Exception as e:
            # Use consistent error wrapping
            wrapped_error = ErrorHandlingUtils.wrap_error(
                e,
                "Maricopa property adaptation",
                ProcessingError,
                context={
                    "raw_data_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else None
                },
                sanitize=False  # No sensitive data in this context
            )
            raise wrapped_error from e

    def get_source_name(self) -> str:
        """Get the source name for this adapter."""
        return "maricopa_api"

    def validate_raw_data(self, raw_data: Dict[str, Any]) -> bool:
        """Validate raw Maricopa API data before transformation.

        Args:
            raw_data: Raw data from Maricopa API

        Returns:
            True if data is valid for transformation

        Raises:
            ValidationError: If data is invalid with specific details
        """
        # Validate basic data structure
        CommonValidators.validate_raw_data_structure(raw_data, dict)

        # Check for required address data
        address_data = raw_data.get("address")
        if not address_data or not isinstance(address_data, dict):
            raise ValidationError(
                "Missing or invalid address section in raw data",
                context={"available_sections": list(raw_data.keys())},
            )

        # Validate essential address fields by checking nested values
        required_addr_fields = ["house_number", "street_name", "zipcode"]
        missing_fields = []

        for field in required_addr_fields:
            value = self._get_nested_field(address_data, self.field_mappings["address"][field])
            if not value:
                missing_fields.append(field)

        if missing_fields:
            raise ValidationError(
                f"Missing required address fields: {', '.join(missing_fields)}",
                context={
                    "missing_fields": missing_fields,
                    "address_keys": list(address_data.keys()),
                },
            )

        # Validate APN/parcel number if available
        property_info = raw_data.get("property_info", {})
        if property_info and not self._get_nested_field(
            property_info, self.field_mappings["property_info"]["apn"]
        ):
            self.logger.warning("No APN/parcel number found - may impact data quality")

        return True

    def _extract_address(self, address_info: Dict[str, Any]) -> PropertyAddress:
        """Extract and normalize address from Maricopa API address section.

        Args:
            address_info: Address section from raw API data

        Returns:
            PropertyAddress object with normalized components
        """
        # Extract address components using field mappings
        house_number = (
            self._get_nested_field(address_info, self.field_mappings["address"]["house_number"])
            or ""
        )
        street_name = (
            self._get_nested_field(address_info, self.field_mappings["address"]["street_name"])
            or ""
        )
        street_type = (
            self._get_nested_field(address_info, self.field_mappings["address"]["street_type"])
            or ""
        )
        unit = self._get_nested_field(address_info, self.field_mappings["address"]["unit"])
        city = (
            self._get_nested_field(address_info, self.field_mappings["address"]["city"])
            or "Phoenix"
        )
        state = (
            self._get_nested_field(address_info, self.field_mappings["address"]["state"]) or "AZ"
        )
        zipcode = (
            self._get_nested_field(address_info, self.field_mappings["address"]["zipcode"]) or ""
        )

        # Build street address with unit handling
        street_parts = [house_number, street_name, street_type]
        street_address = " ".join(part for part in street_parts if part).strip()

        if unit:
            street_address = f"{street_address}, Unit {unit}"

        # Normalize using Epic 1 utility
        normalized_street = normalize_address(street_address)

        return PropertyAddress(
            street=normalized_street,
            city=city.title().strip(),
            state=state.upper().strip(),
            zipcode=zipcode.strip(),
            county="Maricopa",
        )

    def _extract_prices(self, assessment_info: Dict[str, Any]) -> List[PropertyPrice]:
        """Extract price information with history from assessment data.

        Args:
            assessment_info: Assessment section from raw API data

        Returns:
            List of PropertyPrice objects with proper date handling
        """
        prices = []
        current_date = datetime.now(timezone.utc)

        # Extract assessed value
        assessed_value = self._get_nested_field(
            assessment_info, self.field_mappings["assessment"]["assessed_value"]
        )
        assessed_float = safe_float(assessed_value)
        if assessed_float and assessed_float > 0:
            prices.append(
                PropertyPrice(
                    amount=assessed_float,
                    date=current_date,
                    price_type="assessed",
                    source=DataSource.MARICOPA_COUNTY,
                    confidence=0.9,
                )
            )

        # Extract market value
        market_value = self._get_nested_field(
            assessment_info, self.field_mappings["assessment"]["market_value"]
        )
        market_float = safe_float(market_value)
        if market_float and market_float > 0:
            prices.append(
                PropertyPrice(
                    amount=market_float,
                    date=current_date,
                    price_type="market_estimate",
                    source=DataSource.MARICOPA_COUNTY,
                    confidence=0.8,
                )
            )

        # Extract land value if available
        land_value = self._get_nested_field(
            assessment_info, self.field_mappings["assessment"]["land_value"]
        )
        land_float = safe_float(land_value)
        if land_float and land_float > 0:
            prices.append(
                PropertyPrice(
                    amount=land_float,
                    date=current_date,
                    price_type="land_value",
                    source=DataSource.MARICOPA_COUNTY,
                    confidence=0.85,
                )
            )

        # Extract improvement value if available
        improvement_value = self._get_nested_field(
            assessment_info, self.field_mappings["assessment"]["improvement_value"]
        )
        improvement_float = safe_float(improvement_value)
        if improvement_float and improvement_float > 0:
            prices.append(
                PropertyPrice(
                    amount=improvement_float,
                    date=current_date,
                    price_type="improvement_value",
                    source=DataSource.MARICOPA_COUNTY,
                    confidence=0.85,
                )
            )

        # Sort by amount descending (highest value first)
        prices.sort(key=lambda p: p.amount, reverse=True)
        return prices

    def _extract_features(self, characteristics: Dict[str, Any]) -> PropertyFeatures:
        """Extract property features with safe conversions.

        Args:
            characteristics: Characteristics section from raw API data

        Returns:
            PropertyFeatures object with normalized data
        """
        # Extract basic features using safe conversions
        bedrooms = safe_int(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["bedrooms"]
            )
        )
        bathrooms = safe_float(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["bathrooms"]
            )
        )
        half_bathrooms = safe_int(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["half_bathrooms"]
            )
        )
        square_feet = safe_int(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["living_area_sqft"]
            )
        )
        lot_size_sqft = safe_int(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["lot_size_sqft"]
            )
        )
        year_built = safe_int(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["year_built"]
            )
        )

        # Extract additional features
        floors = safe_float(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["floors"]
            )
        )
        garage_spaces = safe_int(
            self._get_nested_field(
                characteristics, self.field_mappings["characteristics"]["garage_spaces"]
            )
        )

        # Extract boolean features
        pool = self._get_boolean_field(
            characteristics, self.field_mappings["characteristics"]["pool"]
        )
        fireplace = self._get_boolean_field(
            characteristics, self.field_mappings["characteristics"]["fireplace"]
        )

        # Extract system features
        ac_type = self._get_nested_field(
            characteristics, self.field_mappings["characteristics"]["ac_type"]
        )
        heating_type = self._get_nested_field(
            characteristics, self.field_mappings["characteristics"]["heating_type"]
        )

        return PropertyFeatures(
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            half_bathrooms=half_bathrooms,
            square_feet=square_feet,
            lot_size_sqft=lot_size_sqft,
            year_built=year_built,
            floors=floors,
            garage_spaces=garage_spaces,
            pool=pool,
            fireplace=fireplace,
            ac_type=ac_type,
            heating_type=heating_type,
        )

    def _extract_tax_info(self, raw_data: Dict[str, Any]) -> Optional[PropertyTaxInfo]:
        """Extract tax information from various sections.

        Args:
            raw_data: Complete raw data from API

        Returns:
            PropertyTaxInfo object or None if no tax data available
        """
        # Extract tax data from assessment and property_info sections
        assessment_info = raw_data.get("assessment", {})
        property_info = raw_data.get("property_info", {})

        # Extract APN
        apn = self._get_nested_field(property_info, self.field_mappings["property_info"]["apn"])

        # Extract assessed value (used for tax calculations)
        assessed_value = safe_float(
            self._get_nested_field(
                assessment_info, self.field_mappings["assessment"]["assessed_value"]
            )
        )

        # Extract tax amount and year
        tax_amount = safe_float(
            self._get_nested_field(assessment_info, self.field_mappings["assessment"]["tax_amount"])
        )
        tax_year = safe_int(
            self._get_nested_field(assessment_info, self.field_mappings["assessment"]["tax_year"])
        )

        # Only create PropertyTaxInfo if we have some meaningful data
        if apn or assessed_value or tax_amount:
            return PropertyTaxInfo(
                apn=apn,
                assessed_value=assessed_value,
                tax_amount_annual=tax_amount,
                tax_year=tax_year,
            )

        return None

    def _create_metadata(self, raw_data: Dict[str, Any]) -> DataCollectionMetadata:
        """Create metadata for data collection tracking.

        Args:
            raw_data: Complete raw data from API

        Returns:
            DataCollectionMetadata object
        """
        import hashlib
        import json

        # Create hash of raw data for tracking changes
        raw_data_str = json.dumps(raw_data, sort_keys=True, default=str)
        raw_data_hash = hashlib.sha256(raw_data_str.encode()).hexdigest()

        # Calculate simple quality score based on data completeness
        quality_score = self._calculate_quality_score(raw_data)

        return DataCollectionMetadata(
            source=DataSource.MARICOPA_COUNTY,
            collected_at=datetime.now(timezone.utc),
            collector_version="1.0",
            raw_data_hash=raw_data_hash,
            processing_notes=f"Processed {len(raw_data)} sections",
            quality_score=quality_score,
        )

    def _calculate_quality_score(self, raw_data: Dict[str, Any]) -> float:
        """Calculate data quality score based on completeness.

        Args:
            raw_data: Complete raw data from API

        Returns:
            Quality score between 0.0 and 1.0
        """
        total_fields = 0
        populated_fields = 0

        # Define critical fields and their weights
        critical_fields = {
            "address": ["house_number", "street_name", "zipcode", "city"],
            "characteristics": ["bedrooms", "bathrooms", "living_area_sqft", "year_built"],
            "assessment": ["assessed_value", "market_value"],
            "property_info": ["apn", "legal_description"],
        }

        for section_name, fields in critical_fields.items():
            section = raw_data.get(section_name, {})
            if isinstance(section, dict):
                for field in fields:
                    total_fields += 1
                    value = section.get(field)
                    if value is not None and str(value).strip() and str(value) != "0":
                        populated_fields += 1

        if total_fields == 0:
            return 0.0

        base_score = populated_fields / total_fields

        # Bonus for having APN/parcel number (critical identifier)
        apn = raw_data.get("property_info", {}).get("apn")
        if apn and str(apn).strip():
            base_score = min(1.0, base_score + 0.1)

        return round(base_score, 2)

    def _get_nested_field(self, data: Dict[str, Any], field_names: List[str]) -> Any:
        """Get field value from nested data using multiple possible field names.

        Args:
            data: Nested data dictionary to search
            field_names: List of possible field names to try

        Returns:
            First non-empty value found, or None
        """
        for field_name in field_names:
            if field_name in data and data[field_name] is not None:
                value = data[field_name]
                # Return non-empty strings and non-zero numbers
                if isinstance(value, str) and value.strip():
                    return value.strip()
                elif isinstance(value, (int, float)) and value != 0:
                    return value
                elif not isinstance(value, (str, int, float)) and value:
                    return value
        return None

    def _get_boolean_field(self, data: Dict[str, Any], field_names: List[str]) -> Optional[bool]:
        """Extract boolean value from nested data.

        Args:
            data: Nested data dictionary to search
            field_names: List of possible field names to try

        Returns:
            Boolean value or None if not found/invalid
        """
        value = self._get_nested_field(data, field_names)
        if value is None:
            return None

        # Handle various boolean representations
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ("true", "yes", "y", "1", "on"):
                return True
            elif value_lower in ("false", "no", "n", "0", "off"):
                return False
        elif isinstance(value, (int, float)):
            return bool(value)

        return None

    # Legacy method kept for base class compatibility
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy transform method for base class compatibility.

        This method provides backward compatibility but the main adaptation
        should use the async adapt_property method.
        """
        import asyncio

        try:
            # Run the async method synchronously
            property_obj = asyncio.run(self.adapt_property(raw_data))

            # Convert Property object back to dictionary for legacy compatibility
            return {
                "property_id": property_obj.property_id,
                "address": {
                    "street": property_obj.address.street,
                    "city": property_obj.address.city,
                    "state": property_obj.address.state,
                    "zipcode": property_obj.address.zipcode,
                },
                "features": {
                    "bedrooms": property_obj.features.bedrooms,
                    "bathrooms": property_obj.features.bathrooms,
                    "square_feet": property_obj.features.square_feet,
                    "lot_size_sqft": property_obj.features.lot_size_sqft,
                },
                "current_price": property_obj.current_price,
                "last_updated": property_obj.last_updated.isoformat(),
                "source": "maricopa_api",
            }
        except Exception as e:
            # Use consistent error wrapping
            wrapped_error = ErrorHandlingUtils.wrap_error(
                e,
                "Legacy transform",
                ProcessingError,
                sanitize=False
            )
            raise wrapped_error from e
