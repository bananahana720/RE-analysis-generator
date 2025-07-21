"""Data collection services for Phoenix Real Estate system.

This package provides data collection components using strategy and observer patterns.
Designed for integration with Epic 1 foundation layer and Epic 3 orchestration.

Key Components:
- Base classes: DataCollector, DataAdapter, RateLimiter (strategy and observer patterns)
- Maricopa implementation: Complete API client with rate limiting and data transformation
- Epic 3 orchestration ready: Uniform interfaces for workflow integration

Architecture:
- DataCollector: Strategy pattern for different data sources
- DataAdapter: Transform raw data to Epic 1 PropertyRepository schema
- RateLimiter: Observer pattern with 10% safety margin for API limits
"""

# Base classes for all collectors
from phoenix_real_estate.collectors.base import (
    DataCollector,
    DataAdapter,
    RateLimiter,
)

# Maricopa County implementation
from phoenix_real_estate.collectors.maricopa import (
    MaricopaAPIClient,
    MaricopaDataAdapter,
    MaricopaAPICollector,
)

__all__ = [
    # Base classes
    "DataCollector",
    "DataAdapter",
    "RateLimiter",
    # Maricopa implementation
    "MaricopaAPIClient",
    "MaricopaDataAdapter",
    "MaricopaAPICollector",
]
