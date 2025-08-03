"""E2E test configuration and fixtures for Phoenix Real Estate processing pipeline.

This module provides E2E-specific pytest fixtures for testing the complete
LLM processing pipeline with both mock and real Ollama integration.
"""

import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from phoenix_real_estate.foundation import ConfigProvider, get_logger
from phoenix_real_estate.foundation.database.connection import DatabaseConnection
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.collectors.processing.pipeline import DataProcessingPipeline
from phoenix_real_estate.collectors.processing.llm_client import OllamaClient
from phoenix_real_estate.orchestration import ProcessingIntegrator

# Load environment variables
load_dotenv()

logger = get_logger("e2e.conftest")


@pytest.fixture(scope="session")
def e2e_mode() -> str:
    """Determine E2E test mode from environment.

    Returns:
        "mock" for mocked Ollama or "real" for actual Ollama integration
    """
    mode = os.environ.get("E2E_MODE", "mock").lower()
    if mode not in ["mock", "real"]:
        raise ValueError(f"Invalid E2E_MODE: {mode}. Must be 'mock' or 'real'")
    return mode


@pytest.fixture(scope="session")
def test_config() -> ConfigProvider:
    """Create test configuration for E2E tests."""
    # Set test-specific environment variables
    os.environ["MONGODB_DATABASE"] = "phoenix_real_estate_e2e_test"
    os.environ["OLLAMA_BASE_URL"] = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    os.environ["OLLAMA_MODEL"] = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
    os.environ["PROCESSING_TIMEOUT"] = "60"
    os.environ["BATCH_SIZE"] = "5"
    os.environ["MAX_CONCURRENT_PROCESSING"] = "3"
    os.environ["ENABLE_METRICS"] = "true"
    os.environ["STRICT_VALIDATION"] = "true"
    os.environ["SAVE_INVALID_PROPERTIES"] = "false"

    config = ConfigProvider()
    logger.info("Test configuration created", extra={"database": config.mongodb_database})
    return config


@pytest_asyncio.fixture
async def test_db_connection(test_config: ConfigProvider) -> DatabaseConnection:
    """Create test database connection."""
    # Get MongoDB configuration
    mongodb_uri = test_config.mongodb_uri
    mongodb_database = test_config.mongodb_database

    # Create connection
    db_conn = DatabaseConnection.get_instance(mongodb_uri, mongodb_database)
    await db_conn.connect()

    # Clean test database
    db = db_conn.get_database()
    collections = await db.list_collection_names()
    for collection in collections:
        await db.drop_collection(collection)

    logger.info("Test database connection established and cleaned")

    yield db_conn

    # Cleanup
    await db.drop_collection("properties")
    await db.drop_collection("collection_history")
    await db.drop_collection("errors")
    await db_conn.close()


@pytest_asyncio.fixture
async def test_repository(test_db_connection: DatabaseConnection) -> PropertyRepository:
    """Create test property repository."""
    repository = PropertyRepository(test_db_connection)
    logger.info("Test repository created")
    return repository


@pytest.fixture
def sample_phoenix_mls_html() -> str:
    """Sample Phoenix MLS HTML content for testing."""
    return """
    <html>
    <body>
        <div class="property-details">
            <h1>Beautiful Home in Phoenix</h1>
            <div class="address">123 Test Street, Phoenix, AZ 85031</div>
            <div class="price">$425,000</div>
            <div class="features">
                <span class="beds">4 beds</span>
                <span class="baths">3 baths</span>
                <span class="sqft">2,200 sq ft</span>
                <span class="lot">8,500 sq ft lot</span>
            </div>
            <div class="details">
                <p>MLS#: 6754321</p>
                <p>Year Built: 2018</p>
                <p>Property Type: Single Family</p>
                <p>Status: Active</p>
                <p>Days on Market: 7</p>
            </div>
            <div class="description">
                This stunning 4-bedroom, 3-bathroom home features modern amenities,
                an open floor plan, and a spacious backyard perfect for entertaining.
                Located in a quiet neighborhood with excellent schools nearby.
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_maricopa_json() -> Dict[str, Any]:
    """Sample Maricopa County API JSON response for testing."""
    return {
        "parcel_number": "123-45-678A",
        "property_address": {
            "address": "456 Demo Avenue",
            "city": "Phoenix",
            "state": "AZ",
            "zip": "85033",
        },
        "owner_info": {
            "name": "TEST OWNER LLC",
            "mailing_address": "PO Box 1234, Phoenix, AZ 85001",
        },
        "property_details": {
            "land_use": "SINGLE FAMILY RESIDENTIAL",
            "year_built": 2015,
            "living_area": 1850,
            "lot_size": 7200,
            "bedrooms": 3,
            "bathrooms": 2.5,
        },
        "valuation": {"market_value": 385000, "assessed_value": 350000, "tax_year": 2024},
    }


@pytest.fixture
def sample_batch_data() -> List[Dict[str, Any]]:
    """Sample batch of mixed property data for testing."""
    return [
        {
            "content": """<div class="property">
                <h2>789 Batch St, Phoenix, AZ 85031</h2>
                <p>Price: $325,000</p>
                <p>3 beds, 2 baths, 1,650 sq ft</p>
                <p>MLS: 6754322</p>
            </div>""",
            "source": "phoenix_mls",
            "content_type": "html",
        },
        {
            "content": {
                "parcel_number": "234-56-789B",
                "property_address": {"address": "321 Batch Ave", "city": "Phoenix", "zip": "85035"},
                "property_details": {
                    "bedrooms": 4,
                    "bathrooms": 2,
                    "living_area": 2000,
                    "year_built": 2020,
                },
                "valuation": {"market_value": 410000},
            },
            "source": "maricopa_county",
            "content_type": "json",
        },
        {
            "content": """<div class="listing">
                <address>555 Test Blvd, Phoenix, AZ 85033</address>
                <div class="price">$475,000</div>
                <div>5 beds | 3 baths | 2,500 sqft</div>
                <div>MLS#: 6754323 | Built: 2019</div>
            </div>""",
            "source": "phoenix_mls",
            "content_type": "html",
        },
    ]


@pytest_asyncio.fixture
async def mock_ollama_client(e2e_mode: str) -> Optional[AsyncMock]:
    """Create mock Ollama client for testing.

    Returns None if in real mode, mock client if in mock mode.
    """
    if e2e_mode == "real":
        return None

    mock_client = AsyncMock(spec=OllamaClient)

    # Mock successful extraction responses
    mock_client.extract.return_value = {
        "address": "123 Test Street",
        "city": "Phoenix",
        "state": "AZ",
        "zip_code": "85031",
        "price": 425000,
        "bedrooms": 4,
        "bathrooms": 3.0,
        "square_feet": 2200,
        "lot_size": 8500,
        "year_built": 2018,
        "property_type": "Single Family",
        "mls_number": "6754321",
        "listing_status": "Active",
        "description": "This stunning 4-bedroom home features modern amenities",
        "extraction_confidence": 0.95,
    }

    # Mock health check
    mock_client.health_check.return_value = True

    # Mock context manager
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    return mock_client


@pytest_asyncio.fixture
async def processing_pipeline(
    test_config: ConfigProvider, mock_ollama_client: Optional[AsyncMock], e2e_mode: str
) -> DataProcessingPipeline:
    """Create processing pipeline for testing."""
    pipeline = DataProcessingPipeline(test_config)

    # If in mock mode, inject the mock client
    if e2e_mode == "mock" and mock_ollama_client:
        # Access the extractor through the pipeline
        await pipeline.initialize()
        if hasattr(pipeline._extractor, "_llm_client"):
            pipeline._extractor._llm_client = mock_ollama_client

    return pipeline


@pytest_asyncio.fixture
async def processing_integrator(
    test_config: ConfigProvider,
    test_repository: PropertyRepository,
    processing_pipeline: DataProcessingPipeline,
) -> ProcessingIntegrator:
    """Create processing integrator for testing."""
    integrator = ProcessingIntegrator(
        config=test_config, repository=test_repository, pipeline=processing_pipeline
    )
    return integrator


@pytest.fixture
def expected_property_fields() -> List[str]:
    """List of expected fields in processed property data."""
    return [
        "property_id",
        "address",
        "city",
        "state",
        "zip_code",
        "price",
        "bedrooms",
        "bathrooms",
        "square_feet",
        "lot_size",
        "year_built",
        "property_type",
        "source",
        "extraction_confidence",
        "extracted_at",
        "last_updated",
    ]


@pytest.fixture
def validation_thresholds() -> Dict[str, Any]:
    """Validation thresholds for property data."""
    return {
        "min_confidence": 0.7,
        "min_price": 50000,
        "max_price": 10000000,
        "min_sqft": 500,
        "max_sqft": 20000,
        "min_bedrooms": 0,
        "max_bedrooms": 20,
        "min_bathrooms": 0,
        "max_bathrooms": 20,
        "min_year_built": 1800,
        "max_year_built": datetime.now().year + 1,
    }


# Test data factories
class E2ETestDataFactory:
    """Factory for generating E2E test data."""

    @staticmethod
    def create_phoenix_mls_html(
        address: str = "123 Test St",
        city: str = "Phoenix",
        zip_code: str = "85031",
        price: int = 350000,
        beds: int = 3,
        baths: float = 2.0,
        sqft: int = 1800,
        mls_number: str = "6754321",
    ) -> str:
        """Create Phoenix MLS HTML with custom values."""
        return f"""
        <div class="property-details">
            <h1>{address}, {city}, AZ {zip_code}</h1>
            <div class="price">${price:,}</div>
            <div class="features">
                <span>{beds} beds</span>
                <span>{baths} baths</span>
                <span>{sqft} sq ft</span>
            </div>
            <div class="mls">MLS#: {mls_number}</div>
        </div>
        """

    @staticmethod
    def create_maricopa_json(
        parcel: str = "123-45-678",
        address: str = "456 Test Ave",
        city: str = "Phoenix",
        zip_code: str = "85033",
        beds: int = 3,
        baths: float = 2.0,
        sqft: int = 1600,
        year_built: int = 2015,
        value: int = 325000,
    ) -> Dict[str, Any]:
        """Create Maricopa County JSON with custom values."""
        return {
            "parcel_number": parcel,
            "property_address": {"address": address, "city": city, "zip": zip_code},
            "property_details": {
                "bedrooms": beds,
                "bathrooms": baths,
                "living_area": sqft,
                "year_built": year_built,
            },
            "valuation": {"market_value": value},
        }


@pytest.fixture
def test_data_factory() -> E2ETestDataFactory:
    """Provide E2E test data factory."""
    return E2ETestDataFactory()


# Performance tracking fixtures
@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests."""

    class PerformanceTracker:
        def __init__(self):
            self.metrics = []

        def record(self, operation: str, duration: float, success: bool = True):
            self.metrics.append(
                {
                    "operation": operation,
                    "duration": duration,
                    "success": success,
                    "timestamp": datetime.now(timezone.utc),
                }
            )

        def get_summary(self) -> Dict[str, Any]:
            if not self.metrics:
                return {}

            durations = [m["duration"] for m in self.metrics]
            success_count = sum(1 for m in self.metrics if m["success"])

            return {
                "total_operations": len(self.metrics),
                "successful": success_count,
                "failed": len(self.metrics) - success_count,
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "total_duration": sum(durations),
            }

    return PerformanceTracker()
