"""Pytest configuration and fixtures for Phoenix Real Estate Data Collection System tests.

This module provides common pytest fixtures, test data factories, and utilities
used across all test modules. It includes support for async tests and shared
test helpers.
"""

import asyncio
from typing import Any, Dict, List
from datetime import datetime, timezone

import pytest

from phoenix_real_estate.foundation.utils.exceptions import (
    PhoenixREError,
    ConfigurationError,
    DatabaseError,
    ValidationError,
)


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_property_data() -> Dict[str, Any]:
    """Provide sample property data for testing.

    Returns:
        A dictionary containing typical property information.
    """
    return {
        "property_id": "123-main-st-85001",
        "address": {"street": "123 Main St", "city": "Phoenix", "state": "AZ", "zip": "85001"},
        "prices": [
            {
                "date": datetime.now(timezone.utc).isoformat(),
                "amount": 350000.0,
                "source": "PhoenixMLS",
            }
        ],
        "features": {"beds": 3, "baths": 2.5, "sqft": 1850, "lot_size": 6500, "year_built": 2005},
        "listing_details": {
            "status": "Active",
            "days_on_market": 15,
            "listing_type": "For Sale",
            "mls_number": "6754321",
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_numeric_conversions() -> List[Dict[str, Any]]:
    """Provide test cases for numeric conversion functions.

    Returns:
        A list of dictionaries with input values and expected results.
    """
    return [
        # Integer conversions
        {"type": "int", "input": "123", "expected": 123},
        {"type": "int", "input": "123.45", "expected": 123},
        {"type": "int", "input": "1,234", "expected": 1234},
        {"type": "int", "input": "  456  ", "expected": 456},
        {"type": "int", "input": "not a number", "expected": None},
        {"type": "int", "input": "", "expected": None},
        {"type": "int", "input": None, "expected": None},
        {"type": "int", "input": 123.99, "expected": 123},
        {"type": "int", "input": True, "expected": 1},
        {"type": "int", "input": False, "expected": 0},
        # Float conversions
        {"type": "float", "input": "123.45", "expected": 123.45},
        {"type": "float", "input": "1,234.56", "expected": 1234.56},
        {"type": "float", "input": "$1,234.56", "expected": 1234.56},
        {"type": "float", "input": "  789.01  ", "expected": 789.01},
        {"type": "float", "input": "123", "expected": 123.0},
        {"type": "float", "input": "not a number", "expected": None},
        {"type": "float", "input": "", "expected": None},
        {"type": "float", "input": None, "expected": None},
        {"type": "float", "input": 456, "expected": 456.0},
        {"type": "float", "input": True, "expected": 1.0},
        {"type": "float", "input": False, "expected": 0.0},
    ]


@pytest.fixture
def sample_exception_contexts() -> List[Dict[str, Any]]:
    """Provide test cases for exception handling.

    Returns:
        A list of dictionaries with exception scenarios.
    """
    return [
        {
            "exception_class": PhoenixREError,
            "message": "Base error occurred",
            "context": {"operation": "test", "timestamp": "2025-01-20T10:00:00Z"},
            "expected_str": "Base error occurred (context: operation=test, timestamp=2025-01-20T10:00:00Z)",
        },
        {
            "exception_class": ConfigurationError,
            "message": "Missing API key",
            "context": {"key": "PHOENIX_API_KEY", "source": "environment"},
            "expected_str": "Missing API key (context: key=PHOENIX_API_KEY, source=environment)",
        },
        {
            "exception_class": DatabaseError,
            "message": "Connection failed",
            "context": {"host": "localhost", "port": 27017},
            "expected_str": "Connection failed (context: host=localhost, port=27017)",
        },
        {
            "exception_class": ValidationError,
            "message": "Invalid data format",
            "context": None,
            "expected_str": "Invalid data format",
        },
    ]


class PropertyDataFactory:
    """Factory for generating test property data with various configurations."""

    @staticmethod
    def create_minimal() -> Dict[str, Any]:
        """Create minimal valid property data."""
        return {
            "property_id": "test-property-001",
            "address": {"street": "123 Test St", "city": "Phoenix", "zip": "85001"},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def create_complete() -> Dict[str, Any]:
        """Create complete property data with all fields."""
        return {
            "property_id": "test-property-002",
            "address": {
                "street": "456 Complete Ave",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85002",
            },
            "prices": [
                {
                    "date": datetime.now(timezone.utc).isoformat(),
                    "amount": 450000.0,
                    "source": "PhoenixMLS",
                }
            ],
            "features": {
                "beds": 4,
                "baths": 3.0,
                "sqft": 2200,
                "lot_size": 8500,
                "year_built": 2010,
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


@pytest.fixture
def property_factory() -> PropertyDataFactory:
    """Provide a property data factory for tests.

    Returns:
        A PropertyDataFactory instance.
    """
    return PropertyDataFactory()


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that test individual components in isolation"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that test component interactions"
    )
    config.addinivalue_line("markers", "async_test: Tests that require async execution")
    config.addinivalue_line("markers", "slow: Tests that take longer than usual to execute")
