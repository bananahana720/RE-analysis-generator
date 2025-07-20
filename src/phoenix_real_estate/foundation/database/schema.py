from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class PydanticObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        """Support for Pydantic v2."""
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


class PropertyType(str, Enum):
    """Property type enumeration."""

    SINGLE_FAMILY = "single_family"
    TOWNHOUSE = "townhouse"
    CONDO = "condo"
    APARTMENT = "apartment"
    MANUFACTURED = "manufactured"
    VACANT_LAND = "vacant_land"
    COMMERCIAL = "commercial"
    OTHER = "other"


class ListingStatus(str, Enum):
    """Listing status enumeration."""

    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class DataSource(str, Enum):
    """Data source enumeration."""

    MARICOPA_COUNTY = "maricopa_county"
    PHOENIX_MLS = "phoenix_mls"
    PARTICLE_SPACE = "particle_space"
    MANUAL_ENTRY = "manual_entry"


class PropertyAddress(BaseModel):
    """Property address information."""

    street: str = Field(..., description="Street address")
    city: str = Field(default="Phoenix", description="City name")
    state: str = Field(default="AZ", description="State abbreviation")
    zipcode: str = Field(..., description="ZIP code")
    county: str = Field(default="Maricopa", description="County name")

    @field_validator("zipcode")
    @classmethod
    def validate_zipcode(cls, v: str) -> str:
        """Validate ZIP code format."""
        import re

        if not re.match(r"^\d{5}(-\d{4})?$", v):
            raise ValueError("Invalid ZIP code format")
        return v

    @computed_field
    @property
    def full_address(self) -> str:
        """Get full formatted address."""
        return f"{self.street}, {self.city}, {self.state} {self.zipcode}"


class PropertyFeatures(BaseModel):
    """Property physical features."""

    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[float] = Field(None, ge=0, le=20)
    half_bathrooms: Optional[int] = Field(None, ge=0, le=10)
    square_feet: Optional[int] = Field(None, ge=100, le=50000)
    lot_size_sqft: Optional[int] = Field(None, ge=100, le=10000000)
    year_built: Optional[int] = Field(None, ge=1800)
    floors: Optional[float] = Field(None, ge=1, le=10)
    garage_spaces: Optional[int] = Field(None, ge=0, le=10)
    pool: Optional[bool] = None
    fireplace: Optional[bool] = None
    ac_type: Optional[str] = None
    heating_type: Optional[str] = None

    @field_validator("year_built")
    @classmethod
    def validate_year_built(cls, v: Optional[int]) -> Optional[int]:
        """Validate year built is reasonable."""
        if v is not None and v > datetime.now().year + 5:
            raise ValueError("Year built cannot be more than 5 years in the future")
        return v


class PropertyPrice(BaseModel):
    """Property price information at a point in time."""

    amount: float = Field(..., ge=0, description="Price amount in USD")
    date: datetime = Field(..., description="Date of this price")
    price_type: str = Field(..., description="Type of price (listing, sale, estimate)")
    source: DataSource = Field(..., description="Source of price information")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate price amount is reasonable."""
        if v > 50_000_000:  # $50M max
            raise ValueError("Price amount seems unreasonably high")
        return v


class PropertyListing(BaseModel):
    """Property listing information."""

    mls_id: Optional[str] = None
    listing_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    status: ListingStatus = ListingStatus.UNKNOWN
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None
    brokerage: Optional[str] = None
    listing_url: Optional[str] = None
    description: Optional[str] = None
    virtual_tour_url: Optional[str] = None
    photos: List[str] = Field(default_factory=list)


class PropertyTaxInfo(BaseModel):
    """Property tax and assessment information."""

    apn: Optional[str] = Field(None, description="Assessor's Parcel Number")
    assessed_value: Optional[float] = Field(None, ge=0)
    tax_amount_annual: Optional[float] = Field(None, ge=0)
    tax_year: Optional[int] = None
    homestead_exemption: Optional[bool] = None

    @field_validator("tax_year")
    @classmethod
    def validate_tax_year(cls, v: Optional[int]) -> Optional[int]:
        """Validate tax year is reasonable."""
        current_year = datetime.now().year
        if v is not None and (v < 1900 or v > current_year + 1):
            raise ValueError("Tax year must be between 1900 and next year")
        return v


class PropertySale(BaseModel):
    """Property sale history record."""

    sale_date: datetime
    sale_price: float = Field(..., ge=0)
    buyer_name: Optional[str] = None
    seller_name: Optional[str] = None
    financing_type: Optional[str] = None
    deed_type: Optional[str] = None
    document_number: Optional[str] = None


class DataCollectionMetadata(BaseModel):
    """Metadata about data collection process."""

    source: DataSource
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    collector_version: Optional[str] = None
    raw_data_hash: Optional[str] = None
    processing_notes: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)


class Property(BaseModel):
    """Complete property record."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    # Unique identifiers
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    property_id: str = Field(..., description="System-generated unique ID")

    # Core information
    address: PropertyAddress
    property_type: PropertyType = PropertyType.SINGLE_FAMILY
    features: PropertyFeatures = Field(default_factory=PropertyFeatures)

    # Pricing information
    current_price: Optional[float] = Field(None, ge=0)
    price_history: List[PropertyPrice] = Field(default_factory=list)

    # Listing information
    listing: Optional[PropertyListing] = None

    # Government data
    tax_info: Optional[PropertyTaxInfo] = None
    sale_history: List[PropertySale] = Field(default_factory=list)

    # Data provenance
    sources: List[DataCollectionMetadata] = Field(default_factory=list)

    # Tracking
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    # Flexible storage
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def latest_price_date(self) -> Optional[datetime]:
        """Get date of most recent price update."""
        if not self.price_history:
            return None
        return max(price.date for price in self.price_history)

    @computed_field
    @property
    def days_on_market(self) -> Optional[int]:
        """Calculate days on market if listing is active."""
        if not self.listing or not self.listing.listing_date:
            return None
        if self.listing.status not in [ListingStatus.ACTIVE, ListingStatus.PENDING]:
            return None
        now = datetime.now(UTC)
        listing_date = self.listing.listing_date
        if listing_date.tzinfo is None:
            listing_date = listing_date.replace(tzinfo=UTC)
        return (now - listing_date).days


class DailyReport(BaseModel):
    """Daily collection summary report."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Collection statistics
    total_properties_processed: int = 0
    new_properties_found: int = 0
    properties_updated: int = 0

    # By source breakdown
    properties_by_source: Dict[DataSource, int] = Field(default_factory=dict)

    # By zip code breakdown
    properties_by_zipcode: Dict[str, int] = Field(default_factory=dict)

    # Price analysis
    price_statistics: Dict[str, float] = Field(
        default_factory=dict
    )  # min, max, avg, median

    # Quality metrics
    data_quality_score: Optional[float] = Field(None, ge=0, le=1)
    error_count: int = 0
    warning_count: int = 0

    # Performance metrics
    collection_duration_seconds: Optional[float] = None
    api_requests_made: int = 0
    rate_limit_hits: int = 0

    # Raw data for analysis
    raw_metrics: Dict[str, Any] = Field(default_factory=dict)