"""Property data models for LLM processing."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class PropertyDetails:
    """Structured property details extracted by LLM.

    This model represents property data after LLM extraction and processing,
    designed to work with the ProcessingValidator.
    """

    # Required fields
    property_id: str
    address: str

    # Core identifiers
    mls_number: Optional[str] = None
    parcel_number: Optional[str] = None

    # Location details
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Pricing
    price: Optional[Decimal] = None
    assessed_value: Optional[Decimal] = None

    # Physical attributes
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    lot_size: Optional[int] = None
    lot_units: Optional[str] = None  # 'sqft', 'acres'
    year_built: Optional[int] = None

    # Property characteristics
    property_type: Optional[str] = None
    listing_status: Optional[str] = None

    # Description and features
    description: Optional[str] = None
    features: List[str] = field(default_factory=list)

    # Owner information
    owner_name: Optional[str] = None

    # Dates
    listing_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    extracted_at: Optional[datetime] = None

    # Data quality
    extraction_confidence: Optional[float] = None  # 0.0 to 1.0
    source: Optional[str] = None  # 'phoenix_mls', 'maricopa_county'
    validation_errors: List[str] = field(default_factory=list)

    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Perform post-initialization processing."""
        # Convert price to Decimal if needed
        if self.price is not None and not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))

        # Convert assessed_value to Decimal if needed
        if self.assessed_value is not None and not isinstance(self.assessed_value, Decimal):
            self.assessed_value = Decimal(str(self.assessed_value))

        # Ensure bathrooms is float
        if self.bathrooms is not None and isinstance(self.bathrooms, int):
            self.bathrooms = float(self.bathrooms)

    @classmethod
    def from_extraction_result(cls, extraction_data: Dict[str, Any]) -> "PropertyDetails":
        """Create PropertyDetails from extraction result.

        Args:
            extraction_data: Dictionary from PropertyDataExtractor

        Returns:
            PropertyDetails instance
        """
        # Handle address parsing
        address_data = extraction_data.get("address", {})
        if isinstance(address_data, dict):
            street = address_data.get("street")
            city = address_data.get("city")
            state = address_data.get("state")
            zip_code = address_data.get("zip_code")
            full_address = extraction_data.get("property_address", "")
        else:
            street = city = state = zip_code = None
            full_address = str(address_data) if address_data else ""

        # Create instance
        return cls(
            property_id=extraction_data.get(
                "property_id", extraction_data.get("parcel_number", "")
            ),
            mls_number=extraction_data.get("mls_number"),
            parcel_number=extraction_data.get("parcel_number"),
            address=full_address or extraction_data.get("property_address", ""),
            street=street,
            city=city,
            state=state,
            zip_code=zip_code,
            price=extraction_data.get("price"),
            assessed_value=extraction_data.get("assessed_value"),
            bedrooms=extraction_data.get("bedrooms"),
            bathrooms=extraction_data.get("bathrooms"),
            square_feet=extraction_data.get("square_feet") or extraction_data.get("square_footage"),
            lot_size=extraction_data.get("lot_size"),
            lot_units=extraction_data.get("lot_units"),
            year_built=extraction_data.get("year_built"),
            property_type=extraction_data.get("property_type"),
            listing_status=extraction_data.get("listing_status"),
            description=extraction_data.get("description"),
            features=extraction_data.get("features", []),
            owner_name=extraction_data.get("owner_name"),
            listing_date=extraction_data.get("listing_date"),
            last_updated=extraction_data.get("last_updated"),
            extracted_at=extraction_data.get("extracted_at"),
            extraction_confidence=extraction_data.get("extraction_confidence"),
            source=extraction_data.get("source"),
            validation_errors=extraction_data.get("validation_errors", []),
            raw_data=extraction_data.get("raw_data", {}),
        )
