"""Phoenix Real Estate Data Collection System.

This package provides tools for collecting, processing, and managing
real estate data from Phoenix, Arizona sources including Maricopa County
records and MLS listings.
"""

__version__ = "0.1.0"

# Re-export foundation components for convenient access
from phoenix_real_estate.foundation import (
    ConfigProvider,
    PropertyRepository,
    get_logger,
)

__all__ = [
    "__version__",
    "ConfigProvider",
    "PropertyRepository",
    "get_logger",
]
