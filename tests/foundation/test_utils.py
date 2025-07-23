"""Unit tests for utility functions in the Phoenix Real Estate Data Collection System.

This module tests all helper functions from src/phoenix_real_estate/foundation/utils/helpers.py,
including type conversions, address normalization, async retry behavior, zipcode validation,
and property ID generation.
"""

import pytest
from typing import Any, Optional

from phoenix_real_estate.foundation.utils.helpers import (
    safe_int,
    safe_float,
    normalize_address,
    is_valid_zipcode,
    generate_property_id,
    retry_async,
)


class TestSafeInt:
    """Test cases for the safe_int function."""

    @pytest.mark.unit
    def test_safe_int_with_valid_string(self):
        """Test converting valid string numbers to integers."""
        assert safe_int("123") == 123
        assert safe_int("0") == 0
        assert safe_int("-456") == -456
        assert safe_int("+789") == 789

    @pytest.mark.unit
    def test_safe_int_with_decimal_string(self):
        """Test converting decimal strings to integers."""
        assert safe_int("123.45") == 123
        assert safe_int("999.99") == 999
        assert safe_int("-123.45") == -123
        assert safe_int("0.999") == 0

    @pytest.mark.unit
    def test_safe_int_with_formatted_string(self):
        """Test converting formatted strings with commas."""
        assert safe_int("1,234") == 1234
        assert safe_int("1,000,000") == 1000000
        assert safe_int("10,000.50") == 10000

    @pytest.mark.unit
    def test_safe_int_with_whitespace(self):
        """Test handling strings with leading/trailing whitespace."""
        assert safe_int("  123  ") == 123
        assert safe_int("\t456\n") == 456
        assert safe_int(" 789 ") == 789

    @pytest.mark.unit
    def test_safe_int_with_numeric_types(self):
        """Test converting various numeric types."""
        assert safe_int(123) == 123
        assert safe_int(123.99) == 123
        assert safe_int(0.1) == 0
        assert safe_int(-456.78) == -456

    @pytest.mark.unit
    def test_safe_int_with_boolean(self):
        """Test converting boolean values."""
        assert safe_int(True) == 1
        assert safe_int(False) == 0

    @pytest.mark.unit
    def test_safe_int_with_invalid_input(self):
        """Test handling invalid input with default None."""
        assert safe_int("not a number") is None
        assert safe_int("abc123") is None
        assert safe_int("") is None
        assert safe_int("1.2.3") is None
        # "1,2,3,4" becomes "1234" after comma removal, which is valid

    @pytest.mark.unit
    def test_safe_int_with_none_input(self):
        """Test handling None input."""
        assert safe_int(None) is None
        assert safe_int(None, default=42) == 42

    @pytest.mark.unit
    def test_safe_int_with_custom_default(self):
        """Test using custom default values."""
        assert safe_int("invalid", default=0) == 0
        assert safe_int("", default=-1) == -1
        assert safe_int(None, default=999) == 999

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "value,expected",
        [
            (float("inf"), None),
            (float("-inf"), None),
            (float("nan"), None),
        ],
    )
    def test_safe_int_with_special_floats(self, value: float, expected: Optional[int]):
        """Test handling special float values."""
        assert safe_int(value) == expected

    @pytest.mark.unit
    def test_safe_int_with_large_numbers(self):
        """Test handling very large numbers."""
        assert safe_int("999999999999") == 999999999999
        assert safe_int(10**10) == 10000000000


class TestSafeFloat:
    """Test cases for the safe_float function."""

    @pytest.mark.unit
    def test_safe_float_with_valid_string(self):
        """Test converting valid string numbers to floats."""
        assert safe_float("123.45") == 123.45
        assert safe_float("0.0") == 0.0
        assert safe_float("-456.78") == -456.78
        assert safe_float("123") == 123.0

    @pytest.mark.unit
    def test_safe_float_with_formatted_string(self):
        """Test converting formatted strings with commas and currency."""
        assert safe_float("1,234.56") == 1234.56
        assert safe_float("$1,234.56") == 1234.56
        assert safe_float("$999") == 999.0
        assert safe_float("1,000,000.99") == 1000000.99

    @pytest.mark.unit
    def test_safe_float_with_whitespace(self):
        """Test handling strings with leading/trailing whitespace."""
        assert safe_float("  123.45  ") == 123.45
        assert safe_float("\t456.78\n") == 456.78
        assert safe_float(" $789.01 ") == 789.01

    @pytest.mark.unit
    def test_safe_float_with_numeric_types(self):
        """Test converting various numeric types."""
        assert safe_float(123) == 123.0
        assert safe_float(123.45) == 123.45
        assert safe_float(0) == 0.0
        assert safe_float(-456) == -456.0

    @pytest.mark.unit
    def test_safe_float_with_boolean(self):
        """Test converting boolean values."""
        assert safe_float(True) == 1.0
        assert safe_float(False) == 0.0

    @pytest.mark.unit
    def test_safe_float_with_invalid_input(self):
        """Test handling invalid input with default None."""
        assert safe_float("not a number") is None
        assert safe_float("abc123.45") is None
        assert safe_float("") is None
        assert safe_float("1.2.3.4") is None
        assert safe_float("$$$") is None

    @pytest.mark.unit
    def test_safe_float_with_none_input(self):
        """Test handling None input."""
        assert safe_float(None) is None
        assert safe_float(None, default=99.9) == 99.9

    @pytest.mark.unit
    def test_safe_float_with_custom_default(self):
        """Test using custom default values."""
        assert safe_float("invalid", default=0.0) == 0.0
        assert safe_float("", default=-1.5) == -1.5
        assert safe_float(None, default=999.99) == 999.99

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "value,expected",
        [
            (float("inf"), float("inf")),
            (float("-inf"), float("-inf")),
        ],
    )
    def test_safe_float_with_special_values(self, value: float, expected: float):
        """Test handling special float values."""
        assert safe_float(value) == expected

    @pytest.mark.unit
    def test_safe_float_with_scientific_notation(self):
        """Test handling scientific notation strings."""
        assert safe_float("1.23e2") == 123.0
        assert safe_float("1.5e-3") == 0.0015
        assert safe_float("-2.5e4") == -25000.0

    @pytest.mark.unit
    def test_safe_float_precision(self):
        """Test float precision handling."""
        result = safe_float("123.456789012345")
        assert abs(result - 123.456789012345) < 1e-10


class TestEdgeCases:
    """Test edge cases for utility functions."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "func,value,expected",
        [
            (safe_int, [], None),
            (safe_int, {}, None),
            (safe_int, object(), None),
            (safe_float, [], None),
            (safe_float, {}, None),
            (safe_float, object(), None),
        ],
    )
    def test_non_numeric_objects(self, func, value: Any, expected: Any):
        """Test handling of non-numeric objects."""
        assert func(value) == expected

    @pytest.mark.unit
    def test_overflow_handling(self):
        """Test handling of numeric overflow."""
        # Python 3 handles big integers well, but test the function behavior
        huge_number = "9" * 100
        result = safe_int(huge_number)
        assert result == int(huge_number)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "func,input_val,default,expected",
        [
            (safe_int, "123", 999, 123),  # Valid input ignores default
            (safe_int, "invalid", 999, 999),  # Invalid uses default
            (safe_float, "123.45", 999.9, 123.45),  # Valid input ignores default
            (safe_float, "invalid", 999.9, 999.9),  # Invalid uses default
        ],
    )
    def test_default_behavior(self, func, input_val: str, default: Any, expected: Any):
        """Test that defaults are only used when conversion fails."""
        assert func(input_val, default=default) == expected


# Additional tests for missing utility functions


class TestNormalizeAddress:
    """Test cases for the normalize_address function."""

    @pytest.mark.unit
    def test_normalize_address_basic(self):
        """Test basic address normalization."""
        assert normalize_address("123  Main   St.") == "123 Main St"
        assert normalize_address("456 elm STREET") == "456 Elm Street"
        assert normalize_address("789 OAK AVE") == "789 Oak Ave"

    @pytest.mark.unit
    def test_normalize_address_empty(self):
        """Test handling of empty inputs."""
        assert normalize_address("") == ""
        assert normalize_address("   ") == ""


class TestIsValidZipcode:
    """Test cases for the is_valid_zipcode function."""

    @pytest.mark.unit
    def test_valid_zipcode_formats(self):
        """Test validation of valid ZIP code formats."""
        assert is_valid_zipcode("85031") is True
        assert is_valid_zipcode("85031-1234") is True
        assert is_valid_zipcode("  85031  ") is True

    @pytest.mark.unit
    def test_invalid_zipcode_formats(self):
        """Test validation of invalid ZIP code formats."""
        assert is_valid_zipcode("invalid") is False
        assert is_valid_zipcode("850312") is False
        assert is_valid_zipcode("") is False


class TestGeneratePropertyId:
    """Test cases for the generate_property_id function."""

    @pytest.mark.unit
    def test_generate_property_id_basic(self):
        """Test basic property ID generation."""
        result = generate_property_id("123 Main St", "85031", "maricopa")
        assert result == "maricopa_123_main_st_85031"

    @pytest.mark.unit
    def test_generate_property_id_normalization(self):
        """Test property ID generation with normalization."""
        result = generate_property_id("456 Elm Street, Unit 2", "85032-1234", "phoenix_mls")
        assert result == "phoenix_mls_456_elm_street_unit_2_85032-1234"


class TestRetryAsync:
    """Test cases for the retry_async function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test retry_async when function succeeds."""

        async def successful_function(value: int) -> int:
            return value * 2

        result = await retry_async(successful_function, 5)
        assert result == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_async_failure(self):
        """Test retry_async when function fails."""

        async def failing_function() -> None:
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await retry_async(failing_function, max_retries=1, delay=0.01)
