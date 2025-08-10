"""Integration tests for Phoenix Real Estate project structure validation.

This module validates that the project structure is correctly set up and all
foundation packages can be imported properly.
"""

import pytest
from pathlib import Path


def test_package_imports():
    """Test that all foundation packages can be imported."""
    from phoenix_real_estate.foundation import ConfigProvider, get_logger
    from phoenix_real_estate.foundation.utils.exceptions import PhoenixREError

    assert ConfigProvider is not None
    assert get_logger is not None
    assert PhoenixREError is not None


def test_utility_function_imports():
    """Test that all utility functions can be imported."""
    from phoenix_real_estate.foundation.utils.helpers import (
        safe_int,
        safe_float,
        normalize_address,
        is_valid_zipcode,
        generate_property_id,
        retry_async,
    )

    # Test that functions are callable
    assert callable(safe_int)
    assert callable(safe_float)
    assert callable(normalize_address)
    assert callable(is_valid_zipcode)
    assert callable(generate_property_id)
    assert callable(retry_async)


def test_exception_hierarchy():
    """Test that exception hierarchy is properly defined."""
    from phoenix_real_estate.foundation.utils.exceptions import (
        PhoenixREError,
        ConfigurationError,
        DatabaseError,
        ValidationError,
        DataCollectionError,
        ProcessingError,
        OrchestrationError,
    )

    # Test inheritance
    assert issubclass(ConfigurationError, PhoenixREError)
    assert issubclass(DatabaseError, PhoenixREError)
    assert issubclass(ValidationError, PhoenixREError)
    assert issubclass(DataCollectionError, PhoenixREError)
    assert issubclass(ProcessingError, PhoenixREError)
    assert issubclass(OrchestrationError, PhoenixREError)


def test_project_structure():
    """Validate project directory structure."""
    project_root = Path(__file__).parent.parent.parent

    expected_dirs = [
        "src/phoenix_real_estate/foundation/config",
        "src/phoenix_real_estate/foundation/database",
        "src/phoenix_real_estate/foundation/logging",
        "src/phoenix_real_estate/foundation/utils",
        "tests/foundation",
        "tests/integration",
        "config",
        "docs",
    ]

    for dir_path in expected_dirs:
        assert (project_root / dir_path).exists(), f"Missing directory: {dir_path}"


def test_critical_files_exist():
    """Test that critical project files exist."""
    project_root = Path(__file__).parent.parent.parent

    critical_files = [
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "docs/project-overview/CLAUDE.md",
        "src/phoenix_real_estate/__init__.py",
        "src/phoenix_real_estate/foundation/__init__.py",
        "src/phoenix_real_estate/foundation/utils/__init__.py",
        "src/phoenix_real_estate/foundation/utils/helpers.py",
        "src/phoenix_real_estate/foundation/utils/exceptions.py",
        "tests/conftest.py",
    ]

    for file_path in critical_files:
        assert (project_root / file_path).exists(), f"Missing critical file: {file_path}"


@pytest.mark.integration
def test_foundation_layer_integration():
    """Test that foundation layer components work together."""
    from phoenix_real_estate.foundation.utils.helpers import safe_int, normalize_address
    from phoenix_real_estate.foundation.utils.exceptions import ValidationError

    # Test basic utility function integration
    assert safe_int("123") == 123
    assert normalize_address("123 Main St.") == "123 Main St"

    # Test exception creation with context
    error = ValidationError("Test error", context={"field": "test"})
    assert error.message == "Test error"
    assert error.context["field"] == "test"


@pytest.mark.integration
def test_async_functionality():
    """Test that async utilities work properly."""
    import asyncio
    from phoenix_real_estate.foundation.utils.helpers import retry_async

    async def test_async_integration():
        async def simple_async_func(value: int) -> int:
            return value * 2

        result = await retry_async(simple_async_func, 5)
        return result

    # Run the async test
    result = asyncio.run(test_async_integration())
    assert result == 10


def test_package_metadata():
    """Test that package can be properly installed and has metadata."""
    import phoenix_real_estate

    # Test that the package has a proper module structure
    assert hasattr(phoenix_real_estate, "foundation")

    # Test that we can access the foundation module
    from phoenix_real_estate import foundation

    assert foundation is not None


@pytest.mark.integration
def test_comprehensive_utility_workflow():
    """Test a comprehensive workflow using multiple utility functions."""
    from phoenix_real_estate.foundation.utils.helpers import (
        safe_int,
        safe_float,
        normalize_address,
        is_valid_zipcode,
        generate_property_id,
    )

    # Simulate processing property data
    raw_price = "$1,234,567.89"
    raw_bedrooms = "3.0"
    raw_address = "123  Main   STREET"
    raw_zipcode = "  85031  "
    source = "test-source"

    # Process the data using utility functions
    price = safe_float(raw_price)
    bedrooms = safe_int(raw_bedrooms)
    address = normalize_address(raw_address)
    zipcode_valid = is_valid_zipcode(raw_zipcode)
    property_id = generate_property_id(address, raw_zipcode.strip(), source)

    # Verify the workflow results
    assert price == 1234567.89
    assert bedrooms == 3
    assert address == "123 Main Street"
    assert zipcode_valid is True
    assert property_id == "test_source_123_main_street_85031"


def test_error_handling_integration():
    """Test integrated error handling across utility functions."""
    from phoenix_real_estate.foundation.utils.helpers import safe_int, safe_float
    from phoenix_real_estate.foundation.utils.exceptions import PhoenixREError

    # Test that utility functions handle invalid data gracefully
    assert safe_int("invalid") is None
    assert safe_int("invalid", default=0) == 0
    assert safe_float("invalid") is None
    assert safe_float("invalid", default=0.0) == 0.0

    # Test that we can create and raise custom exceptions
    try:
        raise PhoenixREError("Test integration error", context={"component": "test"})
    except PhoenixREError as e:
        assert str(e) == "Test integration error (context: component=test)"
        assert e.context["component"] == "test"
