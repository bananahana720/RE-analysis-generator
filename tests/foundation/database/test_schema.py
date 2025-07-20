"""Tests for database schema models."""

import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import ValidationError

from phoenix_real_estate.foundation.database.schema import (
    PydanticObjectId, PropertyType, ListingStatus, DataSource,
    PropertyAddress, PropertyFeatures, PropertyPrice, PropertyListing,
    PropertyTaxInfo, PropertySale, DataCollectionMetadata,
    Property, DailyReport
)


class TestEnumerations:
    """Test enumeration classes."""
    
    def test_property_type_values(self):
        """Test PropertyType enum has expected values."""
        assert PropertyType.SINGLE_FAMILY.value == "single_family"
        assert PropertyType.TOWNHOUSE.value == "townhouse"
        assert PropertyType.CONDO.value == "condo"
        assert len(PropertyType) == 8
    
    def test_listing_status_values(self):
        """Test ListingStatus enum has expected values."""
        assert ListingStatus.ACTIVE.value == "active"
        assert ListingStatus.PENDING.value == "pending"
        assert ListingStatus.SOLD.value == "sold"
        assert len(ListingStatus) == 6
    
    def test_data_source_values(self):
        """Test DataSource enum has expected values."""
        assert DataSource.MARICOPA_COUNTY.value == "maricopa_county"
        assert DataSource.PHOENIX_MLS.value == "phoenix_mls"
        assert len(DataSource) == 4


class TestPydanticObjectId:
    """Test custom ObjectId type."""
    
    def test_valid_object_id(self):
        """Test validation of valid ObjectId."""
        valid_id = ObjectId()
        result = PydanticObjectId.validate(str(valid_id))
        assert isinstance(result, ObjectId)
    
    def test_invalid_object_id(self):
        """Test validation of invalid ObjectId."""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            PydanticObjectId.validate("invalid_id")


class TestPropertyAddress:
    """Test PropertyAddress model."""
    
    def test_valid_address(self):
        """Test creating valid address."""
        address = PropertyAddress(
            street="123 Main St",
            zipcode="85001"
        )
        assert address.street == "123 Main St"
        assert address.city == "Phoenix"  # default
        assert address.state == "AZ"  # default
        assert address.zipcode == "85001"
        assert address.county == "Maricopa"  # default
    
    def test_full_address_computed(self):
        """Test full_address computed property."""
        address = PropertyAddress(
            street="123 Main St",
            zipcode="85001"
        )
        assert address.full_address == "123 Main St, Phoenix, AZ 85001"
    
    def test_zipcode_validation_valid(self):
        """Test valid zipcode formats."""
        # 5 digit
        address1 = PropertyAddress(street="123 Main", zipcode="85001")
        assert address1.zipcode == "85001"
        
        # 9 digit with dash
        address2 = PropertyAddress(street="123 Main", zipcode="85001-1234")
        assert address2.zipcode == "85001-1234"
    
    def test_zipcode_validation_invalid(self):
        """Test invalid zipcode formats."""
        with pytest.raises(ValidationError) as exc_info:
            PropertyAddress(street="123 Main", zipcode="123")
        assert "Invalid ZIP code format" in str(exc_info.value)
        
        with pytest.raises(ValidationError):
            PropertyAddress(street="123 Main", zipcode="ABCDE")


class TestPropertyFeatures:
    """Test PropertyFeatures model."""
    
    def test_valid_features(self):
        """Test creating valid features."""
        features = PropertyFeatures(
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800,
            year_built=2010
        )
        assert features.bedrooms == 3
        assert features.bathrooms == 2.5
        assert features.square_feet == 1800
        assert features.year_built == 2010
    
    def test_optional_fields(self):
        """Test all fields are optional."""
        features = PropertyFeatures()
        assert features.bedrooms is None
        assert features.bathrooms is None
        assert features.pool is None
    
    def test_validation_boundaries(self):
        """Test field validation boundaries."""
        # Valid boundaries
        features = PropertyFeatures(
            bedrooms=0,
            bathrooms=0,
            square_feet=100,
            lot_size_sqft=100,
            year_built=1800,
            floors=1.0,
            garage_spaces=0
        )
        assert features.bedrooms == 0
        
        # Invalid: negative bedrooms
        with pytest.raises(ValidationError):
            PropertyFeatures(bedrooms=-1)
        
        # Invalid: too many bedrooms
        with pytest.raises(ValidationError):
            PropertyFeatures(bedrooms=21)
        
        # Invalid: square_feet too small
        with pytest.raises(ValidationError):
            PropertyFeatures(square_feet=99)
    
    def test_year_built_validation(self):
        """Test year_built validation."""
        current_year = datetime.now().year
        
        # Valid: current year
        features1 = PropertyFeatures(year_built=current_year)
        assert features1.year_built == current_year
        
        # Valid: 5 years in future
        features2 = PropertyFeatures(year_built=current_year + 5)
        assert features2.year_built == current_year + 5
        
        # Invalid: more than 5 years in future
        with pytest.raises(ValidationError) as exc_info:
            PropertyFeatures(year_built=current_year + 6)
        assert "cannot be more than 5 years in the future" in str(exc_info.value)


class TestPropertyPrice:
    """Test PropertyPrice model."""
    
    def test_valid_price(self):
        """Test creating valid price."""
        now = datetime.now()
        price = PropertyPrice(
            amount=350000,
            date=now,
            price_type="listing",
            source=DataSource.PHOENIX_MLS
        )
        assert price.amount == 350000
        assert price.date == now
        assert price.price_type == "listing"
        assert price.source == DataSource.PHOENIX_MLS
    
    def test_confidence_score(self):
        """Test confidence score validation."""
        # Valid confidence
        price1 = PropertyPrice(
            amount=100000,
            date=datetime.now(),
            price_type="estimate",
            source=DataSource.MANUAL_ENTRY,
            confidence=0.85
        )
        assert price1.confidence == 0.85
        
        # Invalid: confidence > 1
        with pytest.raises(ValidationError):
            PropertyPrice(
                amount=100000,
                date=datetime.now(),
                price_type="estimate",
                source=DataSource.MANUAL_ENTRY,
                confidence=1.5
            )
    
    def test_amount_validation(self):
        """Test price amount validation."""
        # Valid amount
        price1 = PropertyPrice(
            amount=1000000,
            date=datetime.now(),
            price_type="sale",
            source=DataSource.MARICOPA_COUNTY
        )
        assert price1.amount == 1000000
        
        # Invalid: negative amount
        with pytest.raises(ValidationError):
            PropertyPrice(
                amount=-100,
                date=datetime.now(),
                price_type="sale",
                source=DataSource.MARICOPA_COUNTY
            )
        
        # Invalid: unreasonably high
        with pytest.raises(ValidationError) as exc_info:
            PropertyPrice(
                amount=51_000_000,
                date=datetime.now(),
                price_type="sale",
                source=DataSource.MARICOPA_COUNTY
            )
        assert "unreasonably high" in str(exc_info.value)


class TestPropertyListing:
    """Test PropertyListing model."""
    
    def test_valid_listing(self):
        """Test creating valid listing."""
        listing = PropertyListing(
            mls_id="MLS123456",
            listing_date=datetime.now(),
            status=ListingStatus.ACTIVE,
            agent_name="John Doe",
            photos=["photo1.jpg", "photo2.jpg"]
        )
        assert listing.mls_id == "MLS123456"
        assert listing.status == ListingStatus.ACTIVE
        assert len(listing.photos) == 2
    
    def test_default_values(self):
        """Test default values."""
        listing = PropertyListing()
        assert listing.status == ListingStatus.UNKNOWN
        assert listing.photos == []


class TestPropertyTaxInfo:
    """Test PropertyTaxInfo model."""
    
    def test_valid_tax_info(self):
        """Test creating valid tax info."""
        tax_info = PropertyTaxInfo(
            apn="123-45-678",
            assessed_value=250000,
            tax_amount_annual=3500,
            tax_year=2024
        )
        assert tax_info.apn == "123-45-678"
        assert tax_info.assessed_value == 250000
        assert tax_info.tax_amount_annual == 3500
        assert tax_info.tax_year == 2024
    
    def test_tax_year_validation(self):
        """Test tax year validation."""
        current_year = datetime.now().year
        
        # Valid: current year
        tax1 = PropertyTaxInfo(tax_year=current_year)
        assert tax1.tax_year == current_year
        
        # Valid: next year
        tax2 = PropertyTaxInfo(tax_year=current_year + 1)
        assert tax2.tax_year == current_year + 1
        
        # Invalid: too old
        with pytest.raises(ValidationError):
            PropertyTaxInfo(tax_year=1899)
        
        # Invalid: too far future
        with pytest.raises(ValidationError):
            PropertyTaxInfo(tax_year=current_year + 2)


class TestProperty:
    """Test main Property model."""
    
    def test_minimal_property(self):
        """Test creating property with minimal required fields."""
        prop = Property(
            property_id="test_123",
            address=PropertyAddress(
                street="123 Test St",
                zipcode="85001"
            )
        )
        assert prop.property_id == "test_123"
        assert prop.address.street == "123 Test St"
        assert prop.property_type == PropertyType.SINGLE_FAMILY  # default
        assert prop.is_active is True  # default
        assert isinstance(prop.features, PropertyFeatures)
        assert prop.price_history == []
    
    def test_complete_property(self):
        """Test creating property with all fields."""
        now = datetime.now()
        prop = Property(
            property_id="test_456",
            address=PropertyAddress(
                street="456 Complete Ave",
                zipcode="85002"
            ),
            property_type=PropertyType.CONDO,
            features=PropertyFeatures(
                bedrooms=2,
                bathrooms=2.0,
                square_feet=1200
            ),
            current_price=275000,
            price_history=[
                PropertyPrice(
                    amount=275000,
                    date=now,
                    price_type="listing",
                    source=DataSource.PHOENIX_MLS
                )
            ],
            listing=PropertyListing(
                mls_id="MLS789",
                status=ListingStatus.ACTIVE,
                listing_date=now
            ),
            tax_info=PropertyTaxInfo(
                assessed_value=250000,
                tax_amount_annual=3000
            ),
            sources=[
                DataCollectionMetadata(
                    source=DataSource.PHOENIX_MLS,
                    quality_score=0.95
                )
            ]
        )
        
        assert prop.property_type == PropertyType.CONDO
        assert prop.features.bedrooms == 2
        assert prop.current_price == 275000
        assert len(prop.price_history) == 1
        assert prop.listing.mls_id == "MLS789"
        assert prop.tax_info.assessed_value == 250000
        assert len(prop.sources) == 1
    
    def test_computed_fields(self):
        """Test computed fields."""
        # Test latest_price_date
        old_date = datetime.now() - timedelta(days=30)
        new_date = datetime.now()
        
        prop = Property(
            property_id="test_computed",
            address=PropertyAddress(street="789 Compute Ln", zipcode="85003"),
            price_history=[
                PropertyPrice(
                    amount=300000,
                    date=old_date,
                    price_type="listing",
                    source=DataSource.PHOENIX_MLS
                ),
                PropertyPrice(
                    amount=295000,
                    date=new_date,
                    price_type="listing",
                    source=DataSource.PHOENIX_MLS
                )
            ]
        )
        
        assert prop.latest_price_date == new_date
        
        # Test days_on_market
        listing_date = datetime.now() - timedelta(days=15)
        prop2 = Property(
            property_id="test_dom",
            address=PropertyAddress(street="321 Market St", zipcode="85004"),
            listing=PropertyListing(
                listing_date=listing_date,
                status=ListingStatus.ACTIVE
            )
        )
        
        assert prop2.days_on_market == 15
        
        # Test days_on_market with sold property (should be None)
        prop3 = Property(
            property_id="test_sold",
            address=PropertyAddress(street="654 Sold Ave", zipcode="85005"),
            listing=PropertyListing(
                listing_date=listing_date,
                status=ListingStatus.SOLD
            )
        )
        
        assert prop3.days_on_market is None
    
    def test_model_serialization(self):
        """Test model serialization."""
        prop = Property(
            property_id="test_serial",
            address=PropertyAddress(
                street="987 Serial Blvd",
                zipcode="85006"
            ),
            first_seen=datetime.now()
        )
        
        # Test dict conversion
        prop_dict = prop.model_dump(by_alias=True)
        assert "property_id" in prop_dict
        assert prop_dict["property_id"] == "test_serial"
        
        # Test JSON serialization
        prop_json = prop.model_dump_json()
        assert isinstance(prop_json, str)
        assert "test_serial" in prop_json


class TestDailyReport:
    """Test DailyReport model."""
    
    def test_minimal_report(self):
        """Test creating report with minimal fields."""
        report = DailyReport()
        assert isinstance(report.date, datetime)
        assert report.total_properties_processed == 0
        assert report.new_properties_found == 0
        assert report.properties_updated == 0
        assert report.error_count == 0
    
    def test_complete_report(self):
        """Test creating report with all fields."""
        now = datetime.now()
        report = DailyReport(
            date=now,
            total_properties_processed=150,
            new_properties_found=15,
            properties_updated=130,
            properties_by_source={
                DataSource.PHOENIX_MLS: 100,
                DataSource.MARICOPA_COUNTY: 50
            },
            properties_by_zipcode={
                "85001": 30,
                "85002": 45,
                "85003": 75
            },
            price_statistics={
                "min": 150000,
                "max": 1500000,
                "avg": 425000,
                "median": 380000
            },
            data_quality_score=0.93,
            error_count=3,
            warning_count=8,
            collection_duration_seconds=3600.5,
            api_requests_made=2000,
            rate_limit_hits=5
        )
        
        assert report.date == now
        assert report.total_properties_processed == 150
        assert report.properties_by_source[DataSource.PHOENIX_MLS] == 100
        assert report.properties_by_zipcode["85001"] == 30
        assert report.price_statistics["avg"] == 425000
        assert report.data_quality_score == 0.93
        assert report.collection_duration_seconds == 3600.5
    
    def test_quality_score_validation(self):
        """Test data quality score validation."""
        # Valid score
        report1 = DailyReport(data_quality_score=0.85)
        assert report1.data_quality_score == 0.85
        
        # Invalid: > 1
        with pytest.raises(ValidationError):
            DailyReport(data_quality_score=1.5)
        
        # Invalid: negative
        with pytest.raises(ValidationError):
            DailyReport(data_quality_score=-0.1)


class TestSchemaIntegration:
    """Test schema integration scenarios."""
    
    def test_property_with_multiple_price_updates(self):
        """Test property with price history tracking."""
        prop = Property(
            property_id="test_price_history",
            address=PropertyAddress(
                street="111 Price History Dr",
                zipcode="85007"
            ),
            current_price=400000
        )
        
        # Add price history
        for i in range(3):
            price_date = datetime.now() - timedelta(days=30 * (3 - i))
            prop.price_history.append(
                PropertyPrice(
                    amount=380000 + (i * 10000),
                    date=price_date,
                    price_type="listing",
                    source=DataSource.PHOENIX_MLS
                )
            )
        
        assert len(prop.price_history) == 3
        assert prop.price_history[-1].amount == 400000
        assert prop.latest_price_date == prop.price_history[-1].date
    
    def test_property_lifecycle(self):
        """Test property through different lifecycle stages."""
        # Start with active listing
        prop = Property(
            property_id="test_lifecycle",
            address=PropertyAddress(
                street="222 Lifecycle Ln",
                zipcode="85008"
            ),
            listing=PropertyListing(
                status=ListingStatus.ACTIVE,
                listing_date=datetime.now() - timedelta(days=30)
            )
        )
        
        assert prop.days_on_market == 30
        
        # Update to pending
        prop.listing.status = ListingStatus.PENDING
        assert prop.days_on_market == 30  # Still counts
        
        # Update to sold
        prop.listing.status = ListingStatus.SOLD
        assert prop.days_on_market is None  # No longer on market
        
        # Mark as inactive
        prop.is_active = False
        assert prop.is_active is False
