"""Tests for PropertyDataExtractor - LLM-powered property data extraction."""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from phoenix_real_estate.collectors.processing import PropertyDataExtractor
from phoenix_real_estate.collectors.processing.llm_client import OllamaClient
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError


# Test fixtures
SAMPLE_PHOENIX_MLS_HTML = """
<div class="property-details">
    <h1>$450,000 - 4BR/3BA Single Family Home</h1>
    <div class="address">123 Main St, Phoenix, AZ 85033</div>
    <div class="specs">
        <span>2,500 sq ft</span>
        <span>Built 2005</span>
        <span>0.25 acre lot</span>
    </div>
    <div class="description">
        Beautiful move-in ready home with upgraded kitchen, pool, and mountain views.
        Located in quiet neighborhood near schools and shopping.
    </div>
</div>
"""

SAMPLE_MARICOPA_JSON = {
    "parcel_number": "123-45-678",
    "owner_name": "SMITH JOHN & JANE",
    "property_address": "123 MAIN ST PHOENIX AZ 85033",
    "assessed_value": 385000,
    "year_built": 2005,
    "square_footage": 2500,
    "lot_size": "10890",
    "property_type": "SINGLE FAMILY RESIDENTIAL",
}

EXPECTED_EXTRACTED_DATA = {
    "price": 450000,
    "bedrooms": 4,
    "bathrooms": 3.0,
    "square_feet": 2500,
    "property_type": "Single Family Home",
    "address": {"street": "123 Main St", "city": "Phoenix", "state": "AZ", "zip_code": "85033"},
    "year_built": 2005,
    "lot_size": 0.25,
    "lot_units": "acres",
    "features": ["upgraded kitchen", "pool", "mountain views"],
    "description": "Beautiful move-in ready home with upgraded kitchen, pool, and mountain views. Located in quiet neighborhood near schools and shopping.",
    "source": "phoenix_mls",
    "extracted_at": "2024-01-01T12:00:00Z",
}


class TestPropertyDataExtractor:
    """Test suite for PropertyDataExtractor."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for testing."""
        config = Mock(spec=ConfigProvider)

        # Support get() method
        config.get = Mock(
            side_effect=lambda key, default=None: {
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "LLM_MODEL": "llama3.2:latest",
            }.get(key, default)
        )

        # Support get_typed() method for type-safe configuration access
        def mock_get_typed(key, type_cls, default=None):
            values = {"EXTRACTION_TIMEOUT": 30, "LLM_TIMEOUT": 30, "LLM_MAX_RETRIES": 2}
            value = values.get(key, default)
            if value is not None and type_cls is not None:
                return type_cls(value)
            return value

        config.get_typed = Mock(side_effect=mock_get_typed)
        return config

    @pytest.fixture
    def mock_ollama_client(self):
        """Create mock Ollama client."""
        client = AsyncMock(spec=OllamaClient)
        client.is_healthy = AsyncMock(return_value=True)
        client.initialize = AsyncMock(return_value=None)
        client.close = AsyncMock(return_value=None)
        client._ensure_session = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    async def extractor(self, mock_config, mock_ollama_client):
        """Create PropertyDataExtractor instance with mocks."""
        # Mock the class constructor to return our mock instance
        with patch(
            "phoenix_real_estate.collectors.processing.extractor.OllamaClient",
            return_value=mock_ollama_client,
        ):
            extractor = PropertyDataExtractor(mock_config)
            await extractor.initialize()
            yield extractor
            await extractor.close()

    # Basic initialization tests
    async def test_initialization(self, mock_config):
        """Test extractor initialization."""
        extractor = PropertyDataExtractor(mock_config)
        assert extractor.config == mock_config
        assert extractor._llm_client is None
        assert extractor._validator is None
        assert not extractor._initialized

    async def test_initialize_creates_clients(self, extractor):
        """Test that initialize creates necessary clients."""
        assert extractor._initialized
        assert extractor._llm_client is not None
        # Note: _validator is always None now as validation happens in pipeline
        assert extractor._validator is None

    async def test_context_manager(self, mock_config, mock_ollama_client):
        """Test extractor as context manager."""
        with patch(
            "phoenix_real_estate.collectors.processing.extractor.OllamaClient",
            return_value=mock_ollama_client,
        ):
            async with PropertyDataExtractor(mock_config) as extractor:
                assert extractor._initialized
                # Verify the client's _ensure_session was called
                mock_ollama_client._ensure_session.assert_called()

    # Phoenix MLS extraction tests
    async def test_extract_phoenix_mls_data(self, extractor, mock_ollama_client):
        """Test extraction from Phoenix MLS HTML."""
        # Mock LLM response
        mock_response = {
            "price": 450000,
            "bedrooms": 4,
            "bathrooms": 3.0,
            "square_feet": 2500,
            "property_type": "Single Family Home",
            "address": {
                "street": "123 Main St",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85033",
            },
            "year_built": 2005,
            "lot_size": 0.25,
            "lot_units": "acres",
            "features": ["upgraded kitchen", "pool", "mountain views"],
            "description": "Beautiful move-in ready home with upgraded kitchen, pool, and mountain views. Located in quiet neighborhood near schools and shopping.",
        }
        mock_ollama_client.extract_structured_data = AsyncMock(return_value=mock_response)

        result = await extractor.extract_from_html(SAMPLE_PHOENIX_MLS_HTML, source="phoenix_mls")

        assert result["price"] == 450000
        assert result["bedrooms"] == 4
        assert result["bathrooms"] == 3.0
        assert result["square_feet"] == 2500
        assert result["property_type"] == "Single Family Home"
        assert result["address"]["zip_code"] == "85033"
        assert "pool" in result["features"]
        assert result["source"] == "phoenix_mls"
        assert "extracted_at" in result

    # Maricopa County extraction tests
    async def test_extract_maricopa_data(self, extractor, mock_ollama_client):
        """Test extraction from Maricopa County JSON."""
        # Mock LLM response for address parsing
        mock_address = {
            "street": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85033",
        }
        mock_ollama_client.extract_structured_data = AsyncMock(return_value=mock_address)

        result = await extractor.extract_from_json(SAMPLE_MARICOPA_JSON, source="maricopa_county")

        assert result["parcel_number"] == "123-45-678"
        assert result["owner_name"] == "SMITH JOHN & JANE"
        assert result["assessed_value"] == 385000
        assert result["year_built"] == 2005
        assert result["square_feet"] == 2500
        assert result["lot_size"] == 10890
        assert result["property_type"] == "SINGLE FAMILY RESIDENTIAL"
        assert result["address"]["street"] == "123 Main St"
        assert result["source"] == "maricopa_county"
        assert "extracted_at" in result

    # Prompt engineering tests
    async def test_get_extraction_prompt(self, extractor):
        """Test prompt generation for different content types."""
        # Test Phoenix MLS prompt
        mls_prompt = await extractor.get_extraction_prompt(SAMPLE_PHOENIX_MLS_HTML, "phoenix_mls")
        assert "Extract property information" in mls_prompt
        assert "HTML" in mls_prompt
        assert "price" in mls_prompt
        assert "bedrooms" in mls_prompt

        # Test Maricopa County prompt
        maricopa_prompt = await extractor.get_extraction_prompt(
            json.dumps(SAMPLE_MARICOPA_JSON), "maricopa_county"
        )
        assert "Extract property information" in maricopa_prompt
        assert "JSON" in maricopa_prompt
        assert "parcel_number" in maricopa_prompt

    # Schema validation tests
    async def test_get_extraction_schema(self, extractor):
        """Test extraction schema generation."""
        # Test Phoenix MLS schema
        mls_schema = await extractor.get_extraction_schema("phoenix_mls")
        assert "price" in mls_schema
        assert "bedrooms" in mls_schema
        assert "bathrooms" in mls_schema
        assert "address" in mls_schema
        assert isinstance(mls_schema["address"], dict)

        # Test Maricopa County schema
        maricopa_schema = await extractor.get_extraction_schema("maricopa_county")
        assert "parcel_number" in maricopa_schema
        assert "assessed_value" in maricopa_schema
        assert "owner_name" in maricopa_schema

    # Validation tests (removed as validation is now handled by pipeline)

    # Error handling tests
    async def test_llm_failure_handling(self, extractor, mock_ollama_client):
        """Test handling of LLM extraction failures."""
        mock_ollama_client.extract_structured_data = AsyncMock(
            side_effect=ProcessingError("LLM extraction failed")
        )

        with pytest.raises(ProcessingError) as exc_info:
            await extractor.extract_from_html(SAMPLE_PHOENIX_MLS_HTML, source="phoenix_mls")

        assert "LLM extraction failed" in str(exc_info.value)

    async def test_invalid_source_handling(self, extractor):
        """Test handling of invalid source types."""
        with pytest.raises(ValueError) as exc_info:
            await extractor.extract_from_html(SAMPLE_PHOENIX_MLS_HTML, source="invalid_source")

        assert "Unsupported source" in str(exc_info.value)

    # Batch processing tests
    async def test_batch_extraction(self, extractor, mock_ollama_client):
        """Test batch extraction of multiple properties."""
        mock_ollama_client.extract_structured_data = AsyncMock(
            side_effect=[
                {"price": 450000, "bedrooms": 4},
                {"price": 525000, "bedrooms": 5},
                {"price": 380000, "bedrooms": 3},
            ]
        )

        html_batch = [SAMPLE_PHOENIX_MLS_HTML] * 3
        results = await extractor.extract_batch(
            html_batch, source="phoenix_mls", content_type="html"
        )

        assert len(results) == 3
        assert results[0]["price"] == 450000
        assert results[1]["price"] == 525000
        assert results[2]["price"] == 380000

    # Performance tests
    async def test_extraction_timeout(self, extractor, mock_ollama_client):
        """Test extraction timeout handling."""
        import asyncio

        async def slow_extraction(*args, **kwargs):
            await asyncio.sleep(60)  # Longer than timeout
            return {}

        mock_ollama_client.extract_structured_data = slow_extraction

        with pytest.raises(asyncio.TimeoutError):
            await extractor.extract_from_html(
                SAMPLE_PHOENIX_MLS_HTML,
                source="phoenix_mls",
                timeout=1,  # 1 second timeout
            )

    # Integration test with real schema
    async def test_full_extraction_pipeline(self, extractor, mock_ollama_client):
        """Test complete extraction pipeline."""
        # Mock successful extraction
        mock_ollama_client.extract_structured_data = AsyncMock(return_value=EXPECTED_EXTRACTED_DATA)

        result = await extractor.extract_from_html(SAMPLE_PHOENIX_MLS_HTML, source="phoenix_mls")

        # Verify all expected fields
        assert result["price"] == EXPECTED_EXTRACTED_DATA["price"]
        assert result["bedrooms"] == EXPECTED_EXTRACTED_DATA["bedrooms"]
        assert result["bathrooms"] == EXPECTED_EXTRACTED_DATA["bathrooms"]
        assert result["square_feet"] == EXPECTED_EXTRACTED_DATA["square_feet"]
        assert result["property_type"] == EXPECTED_EXTRACTED_DATA["property_type"]
        assert result["address"] == EXPECTED_EXTRACTED_DATA["address"]
        assert result["year_built"] == EXPECTED_EXTRACTED_DATA["year_built"]
        assert result["lot_size"] == EXPECTED_EXTRACTED_DATA["lot_size"]
        assert result["features"] == EXPECTED_EXTRACTED_DATA["features"]
        assert result["description"] == EXPECTED_EXTRACTED_DATA["description"]
        assert result["source"] == "phoenix_mls"
        assert "extracted_at" in result
