"""Integration tests for ProcessingIntegrator.

Tests the bridge between Epic 1 collectors and Epic 2 processing pipeline.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest

from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from phoenix_real_estate.collectors.processing.pipeline import (
    DataProcessingPipeline,
    ProcessingResult,
)
from phoenix_real_estate.models.property import PropertyDetails
from phoenix_real_estate.orchestration.processing_integrator import (
    ProcessingIntegrator,
    IntegrationResult,
    BatchIntegrationResult,
    IntegrationMode,
)


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock()
    # Mock get method
    config.get.return_value = "test_value"
    # Mock getattr for the integrator's config access pattern
    config.getattr = lambda k, d: lambda key, default: default
    # Mock settings attribute
    config.settings = MagicMock()
    # Add attributes that might be accessed
    config.settings.INTEGRATION_BATCH_SIZE = 10
    config.settings.SAVE_INVALID_PROPERTIES = False
    config.settings.STRICT_VALIDATION = True
    config.settings.BATCH_SIZE = 10
    config.settings.MAX_CONCURRENT_PROCESSING = 5
    config.settings.PROCESSING_TIMEOUT = 60
    config.settings.ENABLE_METRICS = True
    config.settings.RETRY_ATTEMPTS = 2
    config.settings.RETRY_DELAY = 1.0
    return config


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=True)
    repo.find_by_id = AsyncMock(return_value=None)
    repo.bulk_save = AsyncMock(return_value=5)
    return repo


@pytest.fixture
def mock_pipeline():
    """Create mock processing pipeline."""
    pipeline = AsyncMock(spec=DataProcessingPipeline)
    pipeline.initialize = AsyncMock()
    pipeline.close = AsyncMock()
    pipeline._initialized = True
    return pipeline


@pytest.fixture
def mock_maricopa_collector():
    """Create mock Maricopa collector."""
    collector = AsyncMock(spec=MaricopaAPICollector)
    collector.get_source_name.return_value = "maricopa_county"
    return collector


@pytest.fixture
def mock_phoenix_mls_scraper():
    """Create mock Phoenix MLS scraper."""
    scraper = AsyncMock(spec=PhoenixMLSScraper)
    return scraper


@pytest.fixture
def processing_integrator(mock_config, mock_repository, mock_pipeline):
    """Create ProcessingIntegrator instance."""
    return ProcessingIntegrator(
        config=mock_config, repository=mock_repository, pipeline=mock_pipeline
    )


class TestProcessingIntegrator:
    """Test ProcessingIntegrator functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, processing_integrator):
        """Test integrator initialization."""
        await processing_integrator.initialize()

        assert processing_integrator._initialized
        processing_integrator.pipeline.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_maricopa_data(self, processing_integrator, mock_maricopa_collector):
        """Test processing data from Maricopa collector."""
        # Setup test data
        raw_data = {
            "parcel_number": "12345",
            "owner_name": "John Doe",
            "property_address": "123 Main St, Phoenix, AZ 85001",
            "assessed_value": 250000,
            "year_built": 2020,
        }

        # Mock collector response
        mock_maricopa_collector.collect_property_details = AsyncMock(return_value=raw_data)

        # Mock pipeline processing
        property_details = PropertyDetails(
            property_id="12345",
            parcel_number="12345",
            address="123 Main St, Phoenix, AZ 85001",
            owner_name="John Doe",
            assessed_value=Decimal("250000"),
            year_built=2020,
            source="maricopa_county",
            extraction_confidence=0.95,
        )

        processing_result = ProcessingResult(
            is_valid=True,
            property_data=property_details,
            source="maricopa_county",
            processing_time=0.5,
        )

        processing_integrator.pipeline.process_json = AsyncMock(return_value=processing_result)

        # Process data
        await processing_integrator.initialize()
        result = await processing_integrator.process_maricopa_property(
            mock_maricopa_collector, "12345"
        )

        # Verify
        assert isinstance(result, IntegrationResult)
        assert result.success
        assert result.property_id == "12345"
        assert result.source == "maricopa_county"
        assert result.property_data == property_details
        assert result.saved_to_db

        # Verify method calls
        mock_maricopa_collector.collect_property_details.assert_called_once_with("12345")
        processing_integrator.pipeline.process_json.assert_called_once()
        processing_integrator.repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_phoenix_mls_data(self, processing_integrator, mock_phoenix_mls_scraper):
        """Test processing data from Phoenix MLS scraper."""
        # Setup test data
        html_content = "<html><body>Property listing content</body></html>"

        # Mock scraper response
        mock_phoenix_mls_scraper.scrape_property = AsyncMock(return_value=html_content)

        # Mock pipeline processing
        property_details = PropertyDetails(
            property_id="MLS123456",
            mls_number="MLS123456",
            address="456 Oak Ave, Phoenix, AZ 85002",
            price=Decimal("350000"),
            bedrooms=3,
            bathrooms=2.5,
            square_feet=2000,
            source="phoenix_mls",
            extraction_confidence=0.92,
        )

        processing_result = ProcessingResult(
            is_valid=True, property_data=property_details, source="phoenix_mls", processing_time=1.2
        )

        processing_integrator.pipeline.process_html = AsyncMock(return_value=processing_result)

        # Process data
        await processing_integrator.initialize()
        result = await processing_integrator.process_phoenix_mls_property(
            mock_phoenix_mls_scraper, "MLS123456"
        )

        # Verify
        assert isinstance(result, IntegrationResult)
        assert result.success
        assert result.property_id == "MLS123456"
        assert result.source == "phoenix_mls"
        assert result.property_data == property_details
        assert result.saved_to_db

        # Verify method calls
        mock_phoenix_mls_scraper.scrape_property.assert_called_once_with("MLS123456")
        processing_integrator.pipeline.process_html.assert_called_once()
        processing_integrator.repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_processing(self, processing_integrator, mock_maricopa_collector):
        """Test batch processing of multiple properties."""
        # Setup test data
        raw_data_list = [
            {
                "parcel_number": f"1234{i}",
                "property_address": f"{i} Main St, Phoenix, AZ 85001",
                "assessed_value": 250000 + (i * 10000),
            }
            for i in range(5)
        ]

        # Mock collector response
        mock_maricopa_collector.collect_by_zip_codes = AsyncMock(return_value=raw_data_list)

        # Mock pipeline batch processing
        processing_results = []
        for i, data in enumerate(raw_data_list):
            property_details = PropertyDetails(
                property_id=data["parcel_number"],
                parcel_number=data["parcel_number"],
                address=data["property_address"],
                assessed_value=Decimal(str(data["assessed_value"])),
                source="maricopa_county",
            )
            processing_results.append(
                ProcessingResult(
                    is_valid=True, property_data=property_details, source="maricopa_county"
                )
            )

        processing_integrator.pipeline.process_batch_json = AsyncMock(
            return_value=processing_results
        )

        # Process batch
        await processing_integrator.initialize()
        result = await processing_integrator.process_maricopa_batch(
            mock_maricopa_collector, zip_codes=["85001"]
        )

        # Verify
        assert isinstance(result, BatchIntegrationResult)
        assert result.total_processed == 5
        assert result.successful == 5
        assert result.failed == 0
        assert len(result.results) == 5

        # Verify method calls
        mock_maricopa_collector.collect_by_zip_codes.assert_called_once()
        processing_integrator.pipeline.process_batch_json.assert_called_once()
        processing_integrator.repository.bulk_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_mode(self, processing_integrator, mock_maricopa_collector):
        """Test streaming mode processing."""
        # Setup test data
        raw_data_list = [
            {"parcel_number": f"stream{i}", "property_address": f"{i} Stream St"} for i in range(3)
        ]

        # Mock collector with async generator
        async def mock_stream():
            for data in raw_data_list:
                yield data

        mock_maricopa_collector.stream_properties = mock_stream
        mock_maricopa_collector.get_source_name = MagicMock(return_value="maricopa_county")

        # Mock pipeline processing
        async def mock_process(data, source, *args, **kwargs):
            return ProcessingResult(
                is_valid=True,
                property_data=PropertyDetails(
                    property_id=data["parcel_number"],
                    address=data["property_address"],
                    source=source,
                ),
                source=source,
            )

        processing_integrator.pipeline.process_json = mock_process

        # Process stream
        await processing_integrator.initialize()
        results = []
        async for result in processing_integrator.process_stream(
            mock_maricopa_collector, mode=IntegrationMode.STREAMING
        ):
            results.append(result)

        # Verify
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.property_id == f"stream{i}"
            assert result.success

    @pytest.mark.asyncio
    async def test_error_handling(self, processing_integrator, mock_maricopa_collector):
        """Test error handling during processing."""
        # Mock collector error
        mock_maricopa_collector.collect_property_details = AsyncMock(
            side_effect=Exception("API error")
        )

        # Process with error
        await processing_integrator.initialize()
        result = await processing_integrator.process_maricopa_property(
            mock_maricopa_collector, "error_property"
        )

        # Verify error handling
        assert isinstance(result, IntegrationResult)
        assert not result.success
        assert result.property_id == "error_property"
        assert "API error" in result.error
        assert not result.saved_to_db

    @pytest.mark.asyncio
    async def test_metrics_collection(self, processing_integrator, mock_maricopa_collector):
        """Test metrics collection during processing."""
        # Setup successful processing
        mock_maricopa_collector.collect_property_details = AsyncMock(
            return_value={"parcel_number": "12345"}
        )

        processing_integrator.pipeline.process_json = AsyncMock(
            return_value=ProcessingResult(
                is_valid=True,
                property_data=PropertyDetails(property_id="12345", address="Test"),
                processing_time=0.5,
            )
        )

        # Process multiple properties
        await processing_integrator.initialize()
        for i in range(3):
            await processing_integrator.process_maricopa_property(
                mock_maricopa_collector, f"prop{i}"
            )

        # Check metrics
        metrics = processing_integrator.get_metrics()
        assert metrics["total_processed"] >= 3  # May have retries
        assert metrics["successful"] >= 3
        assert metrics["failed"] == 0
        assert metrics["sources"]["maricopa_county"] >= 3
        assert metrics["average_processing_time"] >= 0

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config, mock_repository, mock_pipeline):
        """Test context manager functionality."""
        async with ProcessingIntegrator(
            config=mock_config, repository=mock_repository, pipeline=mock_pipeline
        ) as integrator:
            assert integrator._initialized
            mock_pipeline.initialize.assert_called_once()

        # Verify cleanup
        mock_pipeline.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_property_conversion(self, processing_integrator):
        """Test conversion between PropertyDetails and Property schema."""
        # Create PropertyDetails
        details = PropertyDetails(
            property_id="12345",
            parcel_number="12345",
            address="123 Main St",
            price=Decimal("250000"),
            bedrooms=3,
            bathrooms=2,
            source="maricopa_county",
        )

        # Convert to Property schema
        property_dict = processing_integrator._convert_to_property_schema(details)

        # Verify conversion
        assert isinstance(property_dict, dict)
        assert property_dict["property_id"] == "12345"
        assert property_dict["address"]["street"] == "123 Main St"
        assert property_dict["current_price"] == 250000.0
        assert property_dict["features"]["bedrooms"] == 3
        assert property_dict["features"]["bathrooms"] == 2
        assert property_dict["metadata"]["source"] == "maricopa_county"
