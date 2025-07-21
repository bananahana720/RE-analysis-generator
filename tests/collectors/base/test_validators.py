"""Unit tests for shared validators module."""

import pytest
from phoenix_real_estate.foundation.utils.exceptions import ValidationError, ConfigurationError
from phoenix_real_estate.collectors.base.validators import (
    CommonValidators,
    ErrorHandlingUtils,
    ValidationPatterns,
)


class TestValidationPatterns:
    """Test validation patterns and constants."""

    def test_property_id_pattern(self):
        """Test property ID pattern matching."""
        pattern = ValidationPatterns.PROPERTY_ID_PATTERN
        
        # Valid patterns
        assert pattern.match("abc123")
        assert pattern.match("property_123")
        assert pattern.match("PROP-123-ABC")
        assert pattern.match("123_abc_DEF")
        
        # Invalid patterns
        assert not pattern.match("property id with spaces")
        assert not pattern.match("prop@123")
        assert not pattern.match("prop#123")
        assert not pattern.match("")

    def test_url_patterns(self):
        """Test URL validation patterns."""
        https_pattern = ValidationPatterns.HTTPS_URL_PATTERN
        http_pattern = ValidationPatterns.HTTP_URL_PATTERN
        
        # HTTPS pattern
        assert https_pattern.match("https://example.com")
        assert not https_pattern.match("http://example.com")
        assert not https_pattern.match("ftp://example.com")
        
        # HTTP pattern
        assert http_pattern.match("http://example.com")
        assert not http_pattern.match("https://example.com")

    def test_sensitive_field_pattern(self):
        """Test sensitive field detection pattern."""
        pattern = ValidationPatterns.SENSITIVE_FIELD_PATTERN
        
        # Should match
        assert pattern.search("api_key")
        assert pattern.search("API_KEY")
        assert pattern.search("token")
        assert pattern.search("auth_token")
        assert pattern.search("password")
        assert pattern.search("secret_key")
        
        # Should not match
        assert not pattern.search("username")
        assert not pattern.search("email")
        assert not pattern.search("property_id")


class TestCommonValidators:
    """Test common validation functions."""

    def test_validate_property_id_valid(self):
        """Test valid property ID validation."""
        # Should not raise
        CommonValidators.validate_property_id("property_123")
        CommonValidators.validate_property_id("PROP-456")
        CommonValidators.validate_property_id("abc_def_123")

    def test_validate_property_id_empty(self):
        """Test property ID validation with empty values."""
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_property_id("")
        assert "Property ID cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_property_id("   ")
        assert "Property ID cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_property_id(None)
        assert "Property ID cannot be empty" in str(exc_info.value)

    def test_validate_property_id_invalid_format(self):
        """Test property ID validation with invalid formats."""
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_property_id("property with spaces")
        assert "Invalid property ID format" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_property_id("prop@123")
        assert "Invalid property ID format" in str(exc_info.value)

    def test_validate_zipcode_valid(self):
        """Test valid ZIP code validation."""
        # Should not raise
        CommonValidators.validate_zipcode("85001")
        CommonValidators.validate_zipcode("85001-1234")
        CommonValidators.validate_zipcode("  85001  ")  # With spaces

    def test_validate_zipcode_invalid(self):
        """Test ZIP code validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_zipcode("")
        assert "ZIP code cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_zipcode("850")
        assert "Invalid ZIP code format" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_zipcode("abcde")
        assert "Invalid ZIP code format" in str(exc_info.value)

    def test_validate_days_back_valid(self):
        """Test valid days_back validation."""
        # Should not raise
        CommonValidators.validate_days_back(1)
        CommonValidators.validate_days_back(30)
        CommonValidators.validate_days_back(365)

    def test_validate_days_back_invalid(self):
        """Test days_back validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_days_back(0)
        assert "days_back must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_days_back(-10)
        assert "days_back must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_days_back(366)
        assert "days_back cannot exceed 365" in str(exc_info.value)

    def test_validate_base_url_https(self):
        """Test base URL validation with HTTPS requirement."""
        # Valid HTTPS URLs
        url = CommonValidators.validate_base_url("https://api.example.com", require_https=True)
        assert url == "https://api.example.com"
        
        # With trailing slash
        url = CommonValidators.validate_base_url("https://api.example.com/", require_https=True)
        assert url == "https://api.example.com"
        
        # HTTP not allowed
        with pytest.raises(ConfigurationError) as exc_info:
            CommonValidators.validate_base_url("http://api.example.com", require_https=True)
        assert "HTTPS-only communication required" in str(exc_info.value)
        
        # Invalid format
        with pytest.raises(ConfigurationError) as exc_info:
            CommonValidators.validate_base_url("not-a-url", require_https=True)
        assert "Invalid base URL format" in str(exc_info.value)

    def test_validate_base_url_no_https_requirement(self):
        """Test base URL validation without HTTPS requirement."""
        # HTTP allowed
        url = CommonValidators.validate_base_url("http://api.example.com", require_https=False)
        assert url == "http://api.example.com"

    def test_validate_required_config(self):
        """Test required configuration validation."""
        # Valid config
        CommonValidators.validate_required_config("api_key_value", "API_KEY")
        CommonValidators.validate_required_config(123, "PORT")
        
        # Missing config
        with pytest.raises(ConfigurationError) as exc_info:
            CommonValidators.validate_required_config(None, "API_KEY")
        assert "Missing required config: API_KEY" in str(exc_info.value)
        
        with pytest.raises(ConfigurationError) as exc_info:
            CommonValidators.validate_required_config("", "DATABASE_URL")
        assert "Missing required config: DATABASE_URL" in str(exc_info.value)

    def test_validate_raw_data_structure(self):
        """Test raw data structure validation."""
        # Valid dict
        CommonValidators.validate_raw_data_structure({"key": "value"}, dict)
        
        # Valid list
        CommonValidators.validate_raw_data_structure([1, 2, 3], list)
        
        # Wrong type
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_raw_data_structure("string", dict)
        assert "Raw data must be a dict" in str(exc_info.value)
        
        # Empty data
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_raw_data_structure({}, dict)
        assert "Raw data cannot be empty" in str(exc_info.value)

    def test_validate_required_fields(self):
        """Test required fields validation."""
        data = {
            "name": "Test",
            "value": 123,
            "empty": "",
            "none": None
        }
        
        # All fields present
        missing = CommonValidators.validate_required_fields(
            data, ["name", "value"], "test_data"
        )
        assert missing == []
        
        # Missing fields
        with pytest.raises(ValidationError) as exc_info:
            CommonValidators.validate_required_fields(
                data, ["name", "empty", "missing"], "test_data"
            )
        assert "Missing required fields in test_data" in str(exc_info.value)
        assert "empty" in str(exc_info.value)
        assert "missing" in str(exc_info.value)


class TestErrorHandlingUtils:
    """Test error handling utilities."""

    def test_sanitize_context(self):
        """Test context sanitization."""
        context = {
            "property_id": "prop_123",
            "api_key": "secret_key",
            "token": "auth_token",
            "password": "my_password",
            "auth_header": "Bearer token",
            "normal_field": "normal_value"
        }
        
        sanitized = ErrorHandlingUtils.sanitize_context(context)
        
        assert sanitized["property_id"] == "prop_123"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["auth_header"] == "[REDACTED]"
        assert sanitized["normal_field"] == "normal_value"

    def test_sanitize_url_for_logging(self):
        """Test URL sanitization."""
        # URLs with credentials
        url = "https://api.example.com?api_key=secret123&other=value"
        sanitized = ErrorHandlingUtils.sanitize_url_for_logging(url)
        assert "api_key=[REDACTED]" in sanitized
        assert "other=value" in sanitized
        
        url = "https://api.example.com?token=auth456&password=pass789"
        sanitized = ErrorHandlingUtils.sanitize_url_for_logging(url)
        assert "token=[REDACTED]" in sanitized
        assert "password=[REDACTED]" in sanitized
        
        # Clean URL
        url = "https://api.example.com/endpoint?id=123"
        sanitized = ErrorHandlingUtils.sanitize_url_for_logging(url)
        assert sanitized == url

    def test_wrap_error_new_exception(self):
        """Test error wrapping with new exception type."""
        original = ValueError("Original error")
        
        wrapped = ErrorHandlingUtils.wrap_error(
            original,
            "test_operation",
            ValidationError,
            context={"key": "value"}
        )
        
        assert isinstance(wrapped, ValidationError)
        assert "test_operation failed" in str(wrapped)
        assert "Original error" in str(wrapped)
        assert wrapped.context["operation"] == "test_operation"
        assert wrapped.context["key"] == "value"
        assert wrapped.original_error == original

    def test_wrap_error_same_type(self):
        """Test error wrapping with same exception type."""
        original = ValidationError("Already wrapped")
        
        wrapped = ErrorHandlingUtils.wrap_error(
            original,
            "test_operation",
            ValidationError
        )
        
        # Should return the same exception
        assert wrapped is original

    def test_wrap_error_with_sanitization(self):
        """Test error wrapping with context sanitization."""
        original = ValueError("Error")
        context = {
            "api_key": "secret",
            "normal": "value"
        }
        
        wrapped = ErrorHandlingUtils.wrap_error(
            original,
            "test_operation",
            ValidationError,
            context=context,
            sanitize=True
        )
        
        assert wrapped.context["api_key"] == "[REDACTED]"
        assert wrapped.context["normal"] == "value"

    def test_wrap_error_without_sanitization(self):
        """Test error wrapping without context sanitization."""
        original = ValueError("Error")
        context = {
            "api_key": "secret",
            "normal": "value"
        }
        
        wrapped = ErrorHandlingUtils.wrap_error(
            original,
            "test_operation",
            ValidationError,
            context=context,
            sanitize=False
        )
        
        assert wrapped.context["api_key"] == "secret"
        assert wrapped.context["normal"] == "value"