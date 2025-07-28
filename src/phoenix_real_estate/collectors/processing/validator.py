"""Data validation for LLM-extracted property information."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

import yaml

from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.models.property import PropertyDetails


logger = get_logger(__name__)


@dataclass
class FieldValidation:
    """Validation result for a single field."""
    
    field_name: str
    is_valid: bool
    confidence: float
    value: Any
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DataQualityMetrics:
    """Metrics for data quality assessment."""
    
    completeness: float  # Percentage of required fields present
    consistency: float   # Data consistency score
    accuracy: float      # Estimated accuracy based on validation rules
    timeliness: float    # Data freshness score


@dataclass
class ValidationResult:
    """Complete validation result for property data."""
    
    is_valid: bool
    confidence_score: float
    errors: List[str]
    warnings: List[str]
    field_validations: Dict[str, FieldValidation]
    quality_metrics: DataQualityMetrics
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationRule:
    """Configurable validation rule."""
    
    field_name: str
    rule_type: str  # 'required', 'range', 'regex', 'consistency'
    rule_value: Any
    error_message: str
    warning_only: bool = False


class ProcessingValidator:
    """Validates extracted property data for quality and consistency."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize validator with optional configuration.
        
        Args:
            config: Validation configuration dictionary
        """
        self.config = config or self._get_default_config()
        self.custom_rules: List[ValidationRule] = []
        self._load_rules_from_config()
    
    @classmethod
    def from_config(cls, config_path: str) -> "ProcessingValidator":
        """Create validator from YAML configuration file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Configured ProcessingValidator instance
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return cls(config)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default validation configuration."""
        return {
            "validation_rules": {
                "required_fields": [
                    "property_id", "address", "price"
                ],
                "field_rules": {
                    "price": {
                        "min": 50000,
                        "max": 5000000,
                        "type": "decimal"
                    },
                    "bedrooms": {
                        "min": 0,
                        "max": 20,
                        "type": "integer"
                    },
                    "bathrooms": {
                        "min": 0,
                        "max": 20,
                        "type": "float"
                    },
                    "square_feet": {
                        "min": 400,
                        "max": 20000,
                        "type": "integer"
                    },
                    "year_built": {
                        "min": 1900,
                        "max": datetime.now().year + 1,
                        "type": "integer"
                    }
                },
                "consistency_rules": [
                    {
                        "name": "bedroom_sqft_ratio",
                        "formula": "bedrooms / (square_feet / 500)",
                        "min": 0.5,
                        "max": 2.0
                    }
                ],
                "confidence_thresholds": {
                    "high": 0.9,
                    "medium": 0.7,
                    "low": 0.5
                }
            }
        }
    
    def _load_rules_from_config(self):
        """Load validation rules from configuration."""
        rules_config = self.config.get("validation_rules", {})
        
        # Load required field rules
        for field_name in rules_config.get("required_fields", []):
            rule = ValidationRule(
                field_name=field_name,
                rule_type="required",
                rule_value=True,
                error_message=f"Required field '{field_name}' is missing"
            )
            self.custom_rules.append(rule)
    
    def add_rule(self, rule: ValidationRule):
        """Add a custom validation rule.
        
        Args:
            rule: ValidationRule to add
        """
        self.custom_rules.append(rule)
    
    def validate(
        self,
        property_data: PropertyDetails,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate property data.
        
        Args:
            property_data: Property data to validate
            metadata: Optional extraction metadata
            
        Returns:
            ValidationResult with detailed validation information
        """
        errors = []
        warnings = []
        field_validations = {}
        
        # Check for missing required fields only
        required_fields = self.config["validation_rules"]["required_fields"]
        for field_name in required_fields:
            value = getattr(property_data, field_name, None)
            if value is None:
                errors.append(f"Required field '{field_name}' is missing")
                field_validations[field_name] = FieldValidation(
                    field_name=field_name,
                    is_valid=False,
                    confidence=0.0,
                    value=None,
                    errors=["Required field missing"]
                )
        
        # Apply field-specific rules to all fields with values
        field_rules = self.config["validation_rules"]["field_rules"]
        
        # First validate all fields that have rules
        for field_name, rules in field_rules.items():
            value = getattr(property_data, field_name, None)
            if value is not None:
                field_validation = self._validate_field(field_name, value, rules)
                # Update or replace any existing validation from required fields check
                field_validations[field_name] = field_validation
                
                if not field_validation.is_valid:
                    errors.extend(field_validation.errors)
                if field_validation.warnings:
                    warnings.extend(field_validation.warnings)
        
        # Then add basic validation for any fields not covered by rules
        from dataclasses import fields
        for property_field in fields(property_data):
            if property_field.name not in field_validations:
                value = getattr(property_data, property_field.name)
                if value is not None and property_field.name not in ['features', 'validation_errors', 'raw_data']:
                    field_validations[property_field.name] = FieldValidation(
                        field_name=property_field.name,
                        is_valid=True,
                        confidence=1.0,
                        value=value
                    )
        
        # Apply custom rules
        for rule in self.custom_rules:
            field_validation = self._apply_custom_rule(property_data, rule)
            if field_validation:
                field_validations[rule.field_name] = field_validation
                if not field_validation.is_valid:
                    if rule.warning_only:
                        warnings.append(rule.error_message)
                    else:
                        errors.append(rule.error_message)
        
        # Check data consistency
        consistency_score = self._check_consistency(property_data, warnings)
        
        # Apply metadata confidence if provided
        if metadata and "field_confidences" in metadata:
            for field_name, confidence in metadata["field_confidences"].items():
                if field_name in field_validations:
                    field_validations[field_name].confidence = confidence
        
        # Calculate overall confidence score
        confidence_score = self._calculate_confidence_score(
            property_data, field_validations, metadata
        )
        
        # Calculate data quality metrics
        quality_metrics = self._calculate_quality_metrics(
            property_data, field_validations, consistency_score
        )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            confidence_score=confidence_score,
            errors=errors,
            warnings=warnings,
            field_validations=field_validations,
            quality_metrics=quality_metrics,
            metadata=metadata
        )
    
    def _validate_field(
        self,
        field_name: str,
        value: Any,
        rules: Dict[str, Any]
    ) -> FieldValidation:
        """Validate a single field against rules.
        
        Args:
            field_name: Name of the field
            value: Field value
            rules: Validation rules for the field
            
        Returns:
            FieldValidation result
        """
        errors = []
        warnings = []
        confidence = 1.0
        
        # Type validation
        expected_type = rules.get("type")
        if expected_type:
            if not self._check_type(value, expected_type):
                errors.append(f"{field_name} has invalid type")
                confidence = 0.0
        
        # Range validation
        min_val = rules.get("min")
        max_val = rules.get("max")
        
        if min_val is not None and value < min_val:
            if field_name == "price" and value < 50000:
                # For prices below minimum, it's an error not just a warning
                errors.append(f"{field_name} value {value} is below minimum {min_val}")
                warnings.append(f"{field_name} value {value} is suspiciously low")
                confidence = 0.3
            else:
                errors.append(f"{field_name} value {value} is below minimum {min_val}")
                confidence = 0.0
        
        if max_val is not None and value > max_val:
            errors.append(f"{field_name} value {value} exceeds maximum {max_val}")
            confidence = 0.0
        
        return FieldValidation(
            field_name=field_name,
            is_valid=len(errors) == 0,
            confidence=confidence,
            value=value,
            errors=errors,
            warnings=warnings
        )
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type.
        
        Args:
            value: Value to check
            expected_type: Expected type name
            
        Returns:
            True if type matches
        """
        type_map = {
            "integer": int,
            "float": (int, float),
            "decimal": (int, float, Decimal),
            "string": str,
            "boolean": bool
        }
        
        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        return True
    
    def _apply_custom_rule(
        self,
        property_data: PropertyDetails,
        rule: ValidationRule
    ) -> Optional[FieldValidation]:
        """Apply a custom validation rule.
        
        Args:
            property_data: Property data to validate
            rule: Custom validation rule
            
        Returns:
            FieldValidation result if applicable
        """
        value = getattr(property_data, rule.field_name, None)
        
        # Skip required rules - they're handled separately
        if rule.rule_type == "required":
            return None
            
        if value is None:
            return None
        
        is_valid = True
        errors = []
        
        if rule.rule_type == "regex":
            pattern = re.compile(rule.rule_value)
            if not pattern.search(str(value)):
                is_valid = False
                errors.append(rule.error_message)
        
        return FieldValidation(
            field_name=rule.field_name,
            is_valid=is_valid,
            confidence=1.0 if is_valid else 0.0,
            value=value,
            errors=errors
        )
    
    def _check_consistency(
        self,
        property_data: PropertyDetails,
        warnings: List[str]
    ) -> float:
        """Check data consistency.
        
        Args:
            property_data: Property data to check
            warnings: List to append warnings to
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        consistency_score = 1.0
        
        # Check bedroom to square feet ratio
        if property_data.bedrooms and property_data.square_feet:
            ratio = property_data.bedrooms / (property_data.square_feet / 500)
            if ratio > 2.0:
                warnings.append(
                    f"Unusual bedroom to square feet ratio: {ratio:.2f}"
                )
                consistency_score *= 0.7
        
        # Add more consistency checks as needed
        
        return consistency_score
    
    def _calculate_confidence_score(
        self,
        property_data: PropertyDetails,
        field_validations: Dict[str, FieldValidation],
        metadata: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence score.
        
        Args:
            property_data: Property data
            field_validations: Field validation results
            metadata: Optional extraction metadata
            
        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        # Start with extraction confidence if available
        if hasattr(property_data, "extraction_confidence") and property_data.extraction_confidence is not None:
            base_confidence = property_data.extraction_confidence
        elif metadata and "source_quality" in metadata:
            base_confidence = metadata["source_quality"]
        else:
            base_confidence = 1.0
        
        # Average field confidences
        if field_validations:
            field_confidence = sum(
                fv.confidence for fv in field_validations.values()
            ) / len(field_validations)
            
            # Penalize heavily if required fields are missing
            required_fields = self.config["validation_rules"]["required_fields"]
            for field_name in required_fields:
                if field_name in field_validations and not field_validations[field_name].is_valid:
                    field_confidence *= 0.5  # Halve confidence for each missing required field
        else:
            field_confidence = 1.0
        
        # Combine scores - weight extraction confidence more heavily when present
        if hasattr(property_data, "extraction_confidence") and property_data.extraction_confidence is not None:
            # When we have extraction confidence, weight it more heavily
            return (base_confidence * 0.7 + field_confidence * 0.3)
        else:
            # Otherwise, rely mostly on field validations
            return (base_confidence * 0.4 + field_confidence * 0.6)
    
    def _calculate_quality_metrics(
        self,
        property_data: PropertyDetails,
        field_validations: Dict[str, FieldValidation],
        consistency_score: float
    ) -> DataQualityMetrics:
        """Calculate data quality metrics.
        
        Args:
            property_data: Property data
            field_validations: Field validation results
            consistency_score: Data consistency score
            
        Returns:
            DataQualityMetrics
        """
        # Calculate completeness using dataclass fields
        from dataclasses import fields
        
        total_fields = 0
        non_null_fields = 0
        
        # Count only meaningful fields (exclude lists and dicts)
        for property_field in fields(property_data):
            if property_field.name not in ['features', 'validation_errors', 'raw_data']:
                total_fields += 1
                value = getattr(property_data, property_field.name)
                if value is not None:
                    non_null_fields += 1
        
        completeness = non_null_fields / total_fields if total_fields > 0 else 0
        
        # Calculate accuracy (based on validation results)
        if field_validations:
            accuracy = sum(
                1 for fv in field_validations.values() if fv.is_valid
            ) / len(field_validations)
        else:
            accuracy = 1.0
        
        # Timeliness (assume fresh data for now)
        timeliness = 0.95
        
        return DataQualityMetrics(
            completeness=completeness,
            consistency=consistency_score,
            accuracy=accuracy,
            timeliness=timeliness
        )
    
    def validate_batch(
        self,
        properties: List[PropertyDetails]
    ) -> List[ValidationResult]:
        """Validate multiple properties.
        
        Args:
            properties: List of properties to validate
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        for property_data in properties:
            result = self.validate(property_data)
            results.append(result)
        return results
    
    def get_batch_statistics(
        self,
        results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """Get statistics for batch validation results.
        
        Args:
            results: List of validation results
            
        Returns:
            Dictionary with batch statistics
        """
        if not results:
            return {}
        
        valid_count = sum(1 for r in results if r.is_valid)
        total_confidence = sum(r.confidence_score for r in results)
        
        return {
            "total_properties": len(results),
            "valid_properties": valid_count,
            "invalid_properties": len(results) - valid_count,
            "average_confidence": total_confidence / len(results),
            "average_completeness": sum(
                r.quality_metrics.completeness for r in results
            ) / len(results),
            "average_consistency": sum(
                r.quality_metrics.consistency for r in results
            ) / len(results)
        }
    
    def generate_report(self, result: ValidationResult) -> str:
        """Generate a human-readable validation report.
        
        Args:
            result: ValidationResult to report on
            
        Returns:
            Formatted report string
        """
        report = ["=== Validation Report ==="]
        report.append(f"Valid: {result.is_valid}")
        report.append(f"Confidence Score: {result.confidence_score:.2%}")
        
        if result.errors:
            report.append("\nErrors:")
            for error in result.errors:
                report.append(f"  - {error}")
        
        if result.warnings:
            report.append("\nWarnings:")
            for warning in result.warnings:
                report.append(f"  - {warning}")
        
        report.append("\nData Quality Metrics:")
        report.append(f"  Completeness: {result.quality_metrics.completeness:.2%}")
        report.append(f"  Consistency: {result.quality_metrics.consistency:.2%}")
        report.append(f"  Accuracy: {result.quality_metrics.accuracy:.2%}")
        report.append(f"  Timeliness: {result.quality_metrics.timeliness:.2%}")
        
        return "\n".join(report)