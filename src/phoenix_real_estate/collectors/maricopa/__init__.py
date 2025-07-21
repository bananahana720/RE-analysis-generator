"""Maricopa County API collector implementation.

This module provides a complete implementation for collecting property data
from the Maricopa County Assessor's API, including rate limiting, authentication,
and data transformation.

Key Components:
- MaricopaAPIClient: HTTP client with authentication and rate limiting
- MaricopaDataAdapter: Transforms Maricopa API data to property schema
- MaricopaAPICollector: Complete collector implementing DataCollector strategy
"""

from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter
from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector

__all__ = [
    "MaricopaAPIClient",
    "MaricopaDataAdapter",
    "MaricopaAPICollector",
]
