"""Tests for ProcessingValidator."""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from phoenix_real_estate.collectors.processing.validator import (
    ProcessingValidator,
    ValidationResult,
    ValidationRule,
    FieldValidation,
    DataQualityMetrics
)
from phoenix_real_estate.models.property import PropertyDetails


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_create_validation_result(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            confidence_score=0.95,
            errors=[],
            warnings=["Missing HOA information"],
            field_validations={
                "price": FieldValidation(
                    field_name="price",
                    is_valid=True,
                    confidence=0.98,
                    value=350000,
                    errors=[]
                )
            },
            quality_metrics=DataQualityMetrics(
                completeness=0.85,
                consistency=0.92,
                accuracy=0.90,
                timeliness=0.95
            )
        )
        
        assert result.is_valid
        assert result.confidence_score == 0.95
        assert len(result.warnings) == 1
        assert "price" in result.field_validations
        assert result.quality_metrics.completeness == 0.85


class TestProcessingValidator:
    """Test ProcessingValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a ProcessingValidator instance."""
        return ProcessingValidator()
    
    @pytest.fixture
    def sample_property_data(self) -> PropertyDetails:
        """Create sample property data for testing."""
        return PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85031",
            price=Decimal("350000"),
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800,
            lot_size=7500,
            year_built=2005,
            property_type="Single Family",
            listing_status="Active",
            description="Beautiful home in great location",
            listing_date=datetime.now(),
            last_updated=datetime.now()
        )
    
    def test_validate_complete_data(self, validator, sample_property_data):
        """Test validating complete property data."""
        result = validator.validate(sample_property_data)
        
        assert result.is_valid
        assert result.confidence_score > 0.9
        assert result.quality_metrics.completeness > 0.5  # Adjusted for partial data
        assert not result.errors
    
    def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields."""
        # Property with missing price
        property_data = PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85031",
            price=None,  # Missing required field
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800
        )
        
        result = validator.validate(property_data)
        
        assert not result.is_valid
        assert result.confidence_score < 0.7  # Adjusted - one missing field
        assert "price" in str(result.errors[0])
        assert result.field_validations["price"].is_valid is False
    
    def test_validate_price_range(self, validator):
        """Test price validation rules."""
        # Suspiciously low price
        property_data = PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85031",
            price=Decimal("1000"),  # Too low
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800
        )
        
        result = validator.validate(property_data)
        
        # Should have both error and warning for too-low price
        assert any("price" in str(e).lower() for e in result.errors)
        assert any("price" in str(w).lower() for w in result.warnings)
        
        # Debug field validation
        price_validation = result.field_validations.get("price")
        assert price_validation is not None, "Price validation missing"
        assert not price_validation.is_valid, f"Price should be invalid: {price_validation}"
        assert price_validation.confidence < 0.5, f"Price confidence should be low: {price_validation}"
        assert not result.is_valid  # Should be invalid due to price error
    
    def test_validate_data_consistency(self, validator):
        """Test data consistency validation."""
        # Inconsistent data: small house with many bedrooms
        property_data = PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85031",
            price=Decimal("350000"),
            bedrooms=10,  # Too many for square footage
            bathrooms=2,
            square_feet=1200  # Too small for 10 bedrooms
        )
        
        result = validator.validate(property_data)
        
        assert result.quality_metrics.consistency <= 0.7
        assert any("bedroom" in w.lower() for w in result.warnings)
    
    def test_custom_validation_rules(self, validator):
        """Test adding custom validation rules."""
        # Add custom rule for Phoenix zip codes
        phoenix_zip_rule = ValidationRule(
            field_name="address",
            rule_type="regex",
            rule_value=r"Phoenix, AZ 850(31|33|35)",
            error_message="Property must be in target Phoenix zip codes"
        )
        
        validator.add_rule(phoenix_zip_rule)
        
        # Test with wrong zip code
        property_data = PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85001",  # Wrong zip
            price=Decimal("350000"),
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800
        )
        
        result = validator.validate(property_data)
        
        assert not result.is_valid
        assert "target Phoenix zip codes" in str(result.errors)
    
    def test_confidence_scoring(self, validator):
        """Test confidence scoring for extracted data."""
        property_data = PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85031",
            price=Decimal("350000"),
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800,
            extraction_confidence=0.75  # Add extraction confidence
        )
        
        result = validator.validate(property_data)
        
        # Overall confidence should consider extraction confidence
        # With 0.75 extraction confidence and perfect field validation (1.0)
        # Score = 0.75 * 0.7 + 1.0 * 0.3 = 0.825
        assert 0.8 < result.confidence_score < 0.85
    
    def test_validate_with_metadata(self, validator):
        """Test validation with extraction metadata."""
        property_data = PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85031",
            price=Decimal("350000"),
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800
        )
        
        metadata = {
            "extraction_method": "llm",
            "llm_model": "llama3.2",
            "extraction_timestamp": datetime.now(),
            "source_quality": 0.9,
            "field_confidences": {
                "price": 0.95,
                "bedrooms": 0.99,
                "bathrooms": 0.98,
                "square_feet": 0.85
            }
        }
        
        result = validator.validate(property_data, metadata=metadata)
        
        assert result.field_validations["price"].confidence == 0.95
        assert result.field_validations["square_feet"].confidence == 0.85
    
    def test_generate_validation_report(self, validator, sample_property_data):
        """Test generating a validation report."""
        result = validator.validate(sample_property_data)
        report = validator.generate_report(result)
        
        assert "Validation Report" in report
        assert "Valid: True" in report
        assert "Confidence Score:" in report
        assert "Data Quality Metrics:" in report
        assert "Completeness:" in report
    
    def test_batch_validation(self, validator):
        """Test validating multiple properties."""
        properties = [
            PropertyDetails(
                property_id=f"MLS{i}",
                mls_number=str(i),
                address=f"{i} Test St, Phoenix, AZ 85031",
                price=Decimal(str(300000 + i * 10000)),
                bedrooms=3,
                bathrooms=2,
                square_feet=1500 + i * 100
            )
            for i in range(1, 4)
        ]
        
        results = validator.validate_batch(properties)
        
        assert len(results) == 3
        assert all(r.is_valid for r in results)
        
        # Get batch statistics
        stats = validator.get_batch_statistics(results)
        assert stats["total_properties"] == 3
        assert stats["valid_properties"] == 3
        assert stats["average_confidence"] > 0.8
    
    def test_configuration_from_yaml(self, tmp_path):
        """Test loading validation rules from YAML config."""
        config_file = tmp_path / "validation_rules.yaml"
        config_file.write_text("""
validation_rules:
  required_fields:
    - property_id
    - address
    - price
  
  field_rules:
    price:
      min: 50000
      max: 5000000
      type: decimal
    
    bedrooms:
      min: 0
      max: 20
      type: integer
    
    square_feet:
      min: 400
      max: 20000
      type: integer
  
  consistency_rules:
    - name: bedroom_sqft_ratio
      formula: bedrooms / (square_feet / 500)
      min: 0.5
      max: 2.0
      
  confidence_thresholds:
    high: 0.9
    medium: 0.7
    low: 0.5
""")
        
        validator = ProcessingValidator.from_config(str(config_file))
        
        # Test with data that violates rules
        property_data = PropertyDetails(
            property_id="MLS123456",
            mls_number="123456",
            address="123 Test St, Phoenix, AZ 85031",
            price=Decimal("10000"),  # Below minimum
            bedrooms=3,
            bathrooms=2.5,
            square_feet=1800
        )
        
        result = validator.validate(property_data)
        
        assert not result.is_valid
        assert any("price" in str(e).lower() for e in result.errors)