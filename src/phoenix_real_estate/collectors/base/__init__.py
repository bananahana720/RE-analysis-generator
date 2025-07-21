"""Base classes for data collectors.

This module provides abstract base classes and interfaces that define
the common patterns for data collection in the Phoenix Real Estate system.

Key Components:
- DataCollector: Strategy pattern for different data sources
- DataAdapter: Transforms raw data to standardized format
- RateLimiter: Observer pattern for API rate limiting
- CommonValidators: Shared validation utilities
- ErrorHandlingUtils: Consistent error handling patterns
"""

from phoenix_real_estate.collectors.base.collector import DataCollector
from phoenix_real_estate.collectors.base.adapter import DataAdapter
from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter
from phoenix_real_estate.collectors.base.validators import (
    CommonValidators,
    ErrorHandlingUtils,
    ValidationPatterns,
)

__all__ = [
    "DataCollector",
    "DataAdapter",
    "RateLimiter",
    "CommonValidators",
    "ErrorHandlingUtils",
    "ValidationPatterns",
]
