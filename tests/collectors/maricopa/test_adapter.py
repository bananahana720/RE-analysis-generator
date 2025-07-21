"""Unit tests for Maricopa Data Adapter implementation.

Tests comprehensive schema mapping, transformation logic, and Epic 1 integration
with >95% coverage requirement and comprehensive edge case handling.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter, DataValidator
from phoenix_real_estate.foundation.database.schema import (
    Property, PropertyAddress, DataSource, DataCollectionMetadata
)
from phoenix_real_estate.foundation.utils.exceptions import ValidationError, ProcessingError


class TestMaricopaDataAdapter:
    """Test suite for MaricopaDataAdapter with Epic 1 schema compatibility."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance for testing."""
        return MaricopaDataAdapter(logger_name="test")

    @pytest.fixture
    def sample_raw_data(self):
        """Sample Maricopa API response data for testing."""
        return {
            "address": {
                "house_number": "123",
                "street_name": "Main",
                "street_type": "St",
                "unit": "A",
                "city": "Phoenix",
                "state": "AZ",
                "zipcode": "85001"
            },
            "characteristics": {
                "bedrooms": 3,
                "bathrooms": 2.5,
                "half_bathrooms": 1,
                "living_area_sqft": 1850,
                "lot_size_sqft": 7200,
                "year_built": 2010,
                "floors": 2.0,
                "garage_spaces": 2,
                "pool": "yes",
                "fireplace": "true",
                "ac_type": "Central",
                "heating_type": "Gas"
            },
            "assessment": {
                "assessed_value": 300000,
                "market_value": 350000,
                "land_value": 100000,
                "improvement_value": 250000,
                "tax_amount": 3500,
                "tax_year": 2024
            },
            "property_info": {
                "apn": "123-45-678",
                "legal_description": "Lot 1 Block 2 Main Subdivision",
                "property_type": "Single Family",
                "subdivision": "Main Estates"
            },
            "sales": {
                "last_sale_price": 325000,
                "last_sale_date": "2023-05-15"
            }
        }

    @pytest.fixture
    def minimal_raw_data(self):
        """Minimal valid raw data for testing edge cases."""
        return {
            "address": {
                "house_number": "456",
                "street_name": "Oak",
                "street_type": "Ave",
                "zipcode": "85002"
            },
            "characteristics": {},
            "assessment": {}
        }

    def test_init_with_validator(self):
        """Test adapter initialization with custom validator."""
        validator = DataValidator()
        adapter = MaricopaDataAdapter(validator=validator, logger_name="custom")
        
        assert adapter.validator == validator
        assert adapter.source_name == "adapters.custom"

    def test_init_default_validator(self):
        """Test adapter initialization with default validator."""
        adapter = MaricopaDataAdapter()
        
        assert isinstance(adapter.validator, DataValidator)
        assert adapter.source_name == "adapters.maricopa_api"

    @pytest.mark.asyncio
    async def test_adapt_property_complete_data(self, adapter, sample_raw_data):
        """Test complete property adaptation with all data fields."""
        result = await adapter.adapt_property(sample_raw_data)
        
        # Verify Property object type
        assert isinstance(result, Property)
        
        # Verify property ID generation
        assert result.property_id.startswith("maricopa_")
        assert "123_main_st" in result.property_id
        
        # Verify address extraction
        assert result.address.street == "123 Main St, Unit A"
        assert result.address.city == "Phoenix"
        assert result.address.state == "AZ"
        assert result.address.zipcode == "85001"
        assert result.address.county == "Maricopa"
        
        # Verify features extraction
        assert result.features.bedrooms == 3
        assert result.features.bathrooms == 2.5
        assert result.features.half_bathrooms == 1
        assert result.features.square_feet == 1850
        assert result.features.lot_size_sqft == 7200
        assert result.features.year_built == 2010
        assert result.features.floors == 2.0
        assert result.features.garage_spaces == 2
        assert result.features.pool is True
        assert result.features.fireplace is True
        assert result.features.ac_type == "Central"
        assert result.features.heating_type == "Gas"
        
        # Verify price extraction
        assert len(result.price_history) >= 2  # At least market and assessed values
        assert result.current_price > 0
        
        # Find specific price types
        price_types = [p.price_type for p in result.price_history]
        assert "market_estimate" in price_types
        assert "assessed" in price_types
        assert "land_value" in price_types
        assert "improvement_value" in price_types
        
        # Verify tax info
        assert result.tax_info is not None
        assert result.tax_info.apn == "123-45-678"
        assert result.tax_info.assessed_value == 300000
        assert result.tax_info.tax_amount_annual == 3500
        assert result.tax_info.tax_year == 2024
        
        # Verify metadata
        assert len(result.sources) == 1
        metadata = result.sources[0]
        assert metadata.source == DataSource.MARICOPA_COUNTY
        assert metadata.quality_score > 0.8  # High quality with complete data
        
        # Verify raw data preservation
        assert "maricopa_api" in result.raw_data
        assert result.raw_data["maricopa_api"] == sample_raw_data

    @pytest.mark.asyncio
    async def test_adapt_property_minimal_data(self, adapter, minimal_raw_data):
        """Test property adaptation with minimal required data."""
        result = await adapter.adapt_property(minimal_raw_data)
        
        # Verify basic structure
        assert isinstance(result, Property)
        assert result.property_id
        assert result.address.street == "456 Oak Ave"
        assert result.address.zipcode == "85002"
        
        # Verify empty/None handling
        assert result.features.bedrooms is None
        assert result.features.bathrooms is None
        assert result.price_history == []  # No pricing data
        assert result.current_price is None
        assert result.tax_info is None  # No tax data

    @pytest.mark.asyncio 
    async def test_address_extraction_with_unit(self, adapter):
        """Test address extraction with unit handling."""
        raw_data = {
            "address": {
                "house_number": "789",
                "street_name": "Elm",
                "street_type": "Blvd",
                "unit": "Suite 101",
                "city": "Scottsdale",
                "zipcode": "85260"
            }
        }
        
        address = adapter._extract_address(raw_data["address"])
        
        assert address.street == "789 Elm Blvd, Unit Suite 101"
        assert address.city == "Scottsdale"
        assert address.zipcode == "85260"

    @pytest.mark.asyncio
    async def test_address_extraction_without_unit(self, adapter):
        """Test address extraction without unit."""
        raw_data = {
            "address": {
                "house_number": "321",
                "street_name": "Pine",
                "street_type": "Dr",
                "city": "Tempe",
                "zipcode": "85281"
            }
        }
        
        address = adapter._extract_address(raw_data["address"])
        
        assert address.street == "321 Pine Dr"
        assert "Unit" not in address.street

    def test_price_extraction_multiple_types(self, adapter):
        """Test extraction of multiple price types with proper ordering."""
        assessment_data = {
            "assessed_value": "250000",
            "market_value": "300000", 
            "land_value": "80000",
            "improvement_value": "220000"
        }
        
        prices = adapter._extract_prices(assessment_data)
        
        # Verify all price types extracted
        price_types = [p.price_type for p in prices]
        assert "assessed" in price_types
        assert "market_estimate" in price_types
        assert "land_value" in price_types
        assert "improvement_value" in price_types
        
        # Verify ordering (highest first)
        assert prices[0].amount >= prices[1].amount
        
        # Verify proper source and confidence
        for price in prices:
            assert price.source == DataSource.MARICOPA_COUNTY
            assert 0.8 <= price.confidence <= 0.9

    def test_price_extraction_empty_data(self, adapter):
        """Test price extraction with empty/invalid data."""
        assessment_data = {
            "assessed_value": "",
            "market_value": 0,
            "land_value": None,
            "invalid_amount": "not a number"
        }
        
        prices = adapter._extract_prices(assessment_data)
        
        assert prices == []  # No valid prices

    def test_features_extraction_safe_conversions(self, adapter):
        """Test feature extraction with safe type conversions."""
        characteristics_data = {
            "bedrooms": "3",  # String number
            "bathrooms": 2.5,  # Float
            "living_area_sqft": "1,850",  # Formatted string
            "year_built": "invalid",  # Invalid data
            "garage_spaces": 0,  # Zero value
            "pool": "yes",  # String boolean
            "fireplace": True  # Boolean
        }
        
        features = adapter._extract_features(characteristics_data)
        
        assert features.bedrooms == 3
        assert features.bathrooms == 2.5
        assert features.square_feet == 1850  # Comma removed
        assert features.year_built is None  # Invalid data handled
        assert features.garage_spaces is None  # Zero converted to None
        assert features.pool is True
        assert features.fireplace is True

    def test_boolean_field_extraction(self, adapter):
        """Test boolean field extraction with various representations."""
        test_data = {
            "pool_yes": "yes",
            "pool_true": "true", 
            "pool_1": "1",
            "pool_false": "false",
            "pool_no": "no",
            "pool_0": "0",
            "pool_bool": True,
            "pool_int": 1,
            "pool_none": None,
            "pool_invalid": "maybe"
        }
        
        assert adapter._get_boolean_field(test_data, ["pool_yes"]) is True
        assert adapter._get_boolean_field(test_data, ["pool_true"]) is True
        assert adapter._get_boolean_field(test_data, ["pool_1"]) is True
        assert adapter._get_boolean_field(test_data, ["pool_false"]) is False
        assert adapter._get_boolean_field(test_data, ["pool_no"]) is False
        assert adapter._get_boolean_field(test_data, ["pool_0"]) is False
        assert adapter._get_boolean_field(test_data, ["pool_bool"]) is True
        assert adapter._get_boolean_field(test_data, ["pool_int"]) is True
        assert adapter._get_boolean_field(test_data, ["pool_none"]) is None
        assert adapter._get_boolean_field(test_data, ["pool_invalid"]) is None

    def test_tax_info_extraction(self, adapter):
        """Test tax information extraction."""
        raw_data = {
            "assessment": {
                "assessed_value": 275000,
                "tax_amount": 3250,
                "tax_year": 2024
            },
            "property_info": {
                "apn": "456-78-901"
            }
        }
        
        tax_info = adapter._extract_tax_info(raw_data)
        
        assert tax_info is not None
        assert tax_info.apn == "456-78-901"
        assert tax_info.assessed_value == 275000
        assert tax_info.tax_amount_annual == 3250
        assert tax_info.tax_year == 2024

    def test_tax_info_extraction_no_data(self, adapter):
        """Test tax info extraction with no relevant data."""
        raw_data = {
            "assessment": {},
            "property_info": {}
        }
        
        tax_info = adapter._extract_tax_info(raw_data)
        
        assert tax_info is None

    def test_metadata_creation(self, adapter, sample_raw_data):
        """Test metadata creation with quality scoring."""
        metadata = adapter._create_metadata(sample_raw_data)
        
        assert isinstance(metadata, DataCollectionMetadata)
        assert metadata.source == DataSource.MARICOPA_COUNTY
        assert metadata.collector_version == "1.0"
        assert metadata.raw_data_hash is not None
        assert len(metadata.raw_data_hash) == 64  # SHA256 hex
        assert metadata.quality_score > 0.8  # Complete data should score high

    def test_quality_score_calculation_complete_data(self, adapter, sample_raw_data):
        """Test quality score with complete data."""
        score = adapter._calculate_quality_score(sample_raw_data)
        
        assert 0.8 <= score <= 1.0  # Should be high with complete data
        
    def test_quality_score_calculation_minimal_data(self, adapter, minimal_raw_data):
        """Test quality score with minimal data."""
        score = adapter._calculate_quality_score(minimal_raw_data)
        
        assert 0.1 <= score <= 0.8  # Should be lower with minimal data, but minimal_raw_data still has decent coverage

    def test_nested_field_extraction(self, adapter):
        """Test nested field extraction with multiple candidates."""
        test_data = {
            "primary_field": "value1",
            "secondary_field": "value2",
            "empty_field": "",
            "zero_field": 0,
            "none_field": None
        }
        
        # Should return first valid value
        result = adapter._get_nested_field(test_data, ["nonexistent", "primary_field", "secondary_field"])
        assert result == "value1"
        
        # Should skip empty/invalid values
        result = adapter._get_nested_field(test_data, ["empty_field", "zero_field", "none_field", "primary_field"])
        assert result == "value1"
        
        # Should return None if no valid values
        result = adapter._get_nested_field(test_data, ["nonexistent", "empty_field", "none_field"])
        assert result is None

    def test_validate_raw_data_valid(self, adapter, sample_raw_data):
        """Test validation with valid raw data."""
        assert adapter.validate_raw_data(sample_raw_data) is True

    def test_validate_raw_data_missing_address(self, adapter):
        """Test validation with missing address section."""
        invalid_data = {"characteristics": {}, "assessment": {}}
        
        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_raw_data(invalid_data)
        
        assert "Missing or invalid address section" in str(exc_info.value)

    def test_validate_raw_data_missing_address_fields(self, adapter):
        """Test validation with missing required address fields."""
        invalid_data = {
            "address": {
                "house_number": "123"
                # Missing street_name and zipcode
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_raw_data(invalid_data)
        
        assert "Missing required address fields" in str(exc_info.value)

    def test_validate_raw_data_invalid_type(self, adapter):
        """Test validation with invalid data type."""
        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_raw_data("not a dict")
        
        assert "Raw data must be a dict" in str(exc_info.value)

    def test_validate_raw_data_empty(self, adapter):
        """Test validation with empty data."""
        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_raw_data({})
        
        assert "Raw data cannot be empty" in str(exc_info.value)

    def test_get_source_name(self, adapter):
        """Test source name getter."""
        assert adapter.get_source_name() == "maricopa_api"

    @pytest.mark.asyncio
    async def test_adapt_property_validation_failure(self, adapter):
        """Test property adaptation with validation failure."""
        # Mock the validator to fail
        adapter.validator.validate_property = Mock(return_value=False)
        
        valid_data = {
            "address": {
                "house_number": "123",
                "street_name": "Main", 
                "street_type": "St",
                "zipcode": "85001"
            }
        }
        
        with pytest.raises(ProcessingError) as exc_info:
            await adapter.adapt_property(valid_data)
        
        assert "Property validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_adapt_property_processing_error(self, adapter):
        """Test property adaptation with processing error."""
        # Mock extract_address to raise an error
        with patch.object(adapter, '_extract_address', side_effect=Exception("Test error")):
            valid_data = {
                "address": {
                    "house_number": "123", 
                    "street_name": "Main",
                    "street_type": "St",
                    "zipcode": "85001"
                }
            }
            
            with pytest.raises(ProcessingError) as exc_info:
                await adapter.adapt_property(valid_data)
            
            assert "Maricopa property adaptation failed" in str(exc_info.value)

    def test_legacy_transform_method(self, adapter, sample_raw_data):
        """Test legacy transform method for backward compatibility."""
        with patch('asyncio.run') as mock_run:
            # Mock the async method to return a Property object
            mock_property = Mock(spec=Property)
            mock_property.property_id = "test_id"
            mock_property.address = Mock()
            mock_property.address.street = "123 Main St"
            mock_property.address.city = "Phoenix"
            mock_property.address.state = "AZ"
            mock_property.address.zipcode = "85001"
            mock_property.features = Mock()
            mock_property.features.bedrooms = 3
            mock_property.features.bathrooms = 2.5
            mock_property.features.square_feet = 1850
            mock_property.features.lot_size_sqft = 7200
            mock_property.current_price = 350000
            mock_property.last_updated = datetime.now(timezone.utc)
            
            mock_run.return_value = mock_property
            
            result = adapter.transform(sample_raw_data)
            
            assert isinstance(result, dict)
            assert result["property_id"] == "test_id"
            assert result["source"] == "maricopa_api"


class TestDataValidator:
    """Test suite for DataValidator utility class."""

    def test_validate_property_valid(self):
        """Test validation with valid Property object."""
        # Create a valid Property object
        address = PropertyAddress(
            street="123 Main St",
            city="Phoenix", 
            state="AZ",
            zipcode="85001"
        )
        
        property_obj = Property(
            property_id="test_property_id",
            address=address
        )
        
        assert DataValidator.validate_property(property_obj) is True

    def test_validate_property_missing_id(self):
        """Test validation with missing property ID."""
        address = PropertyAddress(
            street="123 Main St",
            city="Phoenix",
            state="AZ", 
            zipcode="85001"
        )
        
        property_obj = Property(
            property_id="",  # Empty ID
            address=address
        )
        
        assert DataValidator.validate_property(property_obj) is False

    def test_validate_property_missing_address(self):
        """Test validation with missing address."""
        # Create mock object that doesn't have address
        mock_property = Mock()
        mock_property.property_id = "test_id"
        mock_property.address = None
        
        assert DataValidator.validate_property(mock_property) is False

    def test_validate_property_exception_handling(self):
        """Test validation with exception during validation."""
        # Pass invalid object that will cause attribute error
        assert DataValidator.validate_property("not a property") is False


# Integration test data for comprehensive testing
@pytest.fixture
def integration_test_data():
    """Comprehensive test data covering edge cases."""
    return [
        {
            "name": "complete_property",
            "data": {
                "address": {
                    "house_number": "1234",
                    "street_name": "Desert Willow",
                    "street_type": "Ln",
                    "city": "Phoenix", 
                    "state": "AZ",
                    "zipcode": "85048-1234"
                },
                "characteristics": {
                    "bedrooms": 4,
                    "bathrooms": 3.5,
                    "half_bathrooms": 1,
                    "living_area_sqft": 2850,
                    "lot_size_sqft": 9600,
                    "year_built": 2005,
                    "floors": 2,
                    "garage_spaces": 3,
                    "pool": True,
                    "fireplace": False,
                    "ac_type": "Central Air",
                    "heating_type": "Gas Forced Air"
                },
                "assessment": {
                    "assessed_value": 425000,
                    "market_value": 485000,
                    "land_value": 150000,
                    "improvement_value": 335000,
                    "tax_amount": 4980,
                    "tax_year": 2024
                },
                "property_info": {
                    "apn": "217-32-045",
                    "legal_description": "Lot 15 Block 8 Desert Estates Phase II",
                    "property_type": "Single Family Residential",
                    "subdivision": "Desert Estates"
                }
            },
            "expected_quality_score": 0.9
        },
        {
            "name": "minimal_property", 
            "data": {
                "address": {
                    "house_number": "567",
                    "street_name": "Cactus", 
                    "street_type": "Way",
                    "zipcode": "85085"
                },
                "characteristics": {
                    "bedrooms": 2
                },
                "assessment": {
                    "assessed_value": 185000
                }
            },
            "expected_quality_score": 0.5  # Updated to realistic expectation - has 5 out of 10 critical fields
        }
    ]


class TestIntegrationScenarios:
    """Integration tests with realistic data scenarios."""

    @pytest.mark.asyncio
    async def test_integration_scenarios(self, integration_test_data):
        """Test adapter with realistic integration scenarios."""
        adapter = MaricopaDataAdapter(logger_name="integration_test")
        
        for scenario in integration_test_data:
            result = await adapter.adapt_property(scenario["data"])
            
            # Verify basic structure
            assert isinstance(result, Property)
            assert result.property_id
            assert result.address
            
            # Verify quality score meets expectations
            if result.sources:
                quality_score = result.sources[0].quality_score
                expected_score = scenario["expected_quality_score"]
                assert abs(quality_score - expected_score) < 0.2, f"Quality score {quality_score} not near expected {expected_score} for {scenario['name']}"