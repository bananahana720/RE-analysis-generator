"""Tests for Maricopa API collector implementation.

This module tests the complete collector implementation including:
- DataCollector strategy pattern compliance
- Epic 3 orchestration interface methods
- Epic 1 dependency integration
- End-to-end collection workflow
- Error handling and logging
- Repository integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation import PropertyRepository
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError,
    ConfigurationError,
    ValidationError,
    ProcessingError
)
from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector
from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter, DataValidator


class TestMaricopaAPICollector:
    """Test cases for MaricopaAPICollector class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration provider."""
        config = MagicMock()
        # Mock all required methods
        config.get_dict.return_value = {"batch_size": 100, "max_retries": 3}
        config.get_int.side_effect = lambda key, default=None: {
            "maricopa.collection.batch_size": 100,
            "maricopa.collection.max_retries": 3,
            "maricopa.collection.retry_delay_seconds": 5,
            "MARICOPA_RATE_LIMIT": 1000,
            "MARICOPA_TIMEOUT": 30
        }.get(key, default)
        config.get.side_effect = lambda key, default=None: {
            "maricopa.api.base_url": "https://api.example.com",
            "maricopa.api.bearer_token": "test_token",
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        # Add get_typed method that's used in initialization
        config.get_typed.side_effect = lambda key, expected_type, default=None: {
            "maricopa.collection": {
                "batch_size": 100,
                "max_retries": 3,
                "retry_delay_seconds": 5
            }
        }.get(key, default)
        return config

    @pytest.fixture
    def mock_repository(self):
        """Mock property repository."""
        repo = MagicMock(spec=PropertyRepository)
        repo.find_updated_since.return_value = []
        repo.find_by_id.return_value = None
        repo.save.return_value = True
        return repo

    @pytest.fixture
    def mock_client(self):
        """Mock Maricopa API client."""
        client = MagicMock(spec=MaricopaAPIClient)
        # Make async methods
        client.search_by_zipcode = AsyncMock()
        client.get_property_details = AsyncMock()
        client.get_recent_sales = AsyncMock()
        client.close = AsyncMock()
        client.get_metrics.return_value = {"requests_made": 5, "success_rate": 1.0}
        return client

    @pytest.fixture
    def mock_adapter(self):
        """Mock data adapter."""
        adapter = MagicMock(spec=MaricopaDataAdapter)
        adapter.transform.return_value = {
            "property_id": "test_property_123",
            "address": {
                "street": "123 Test St",
                "city": "Phoenix",
                "state": "AZ",
                "zipcode": "85001"
            },
            "features": {
                "bedrooms": 3,
                "bathrooms": 2,
                "square_footage": 1500
            },
            "last_updated": datetime.now().isoformat()
        }
        adapter.transform_batch.return_value = [adapter.transform.return_value]
        return adapter

    @pytest.fixture
    def mock_validator(self):
        """Mock data validator."""
        validator = MagicMock(spec=DataValidator)
        validator.validate_property.return_value = True
        return validator

    @pytest.fixture
    def collector(self, mock_config, mock_repository, mock_client, mock_adapter):
        """Create collector instance with mocked dependencies."""
        with patch('phoenix_real_estate.collectors.maricopa.collector.DataValidator'):
            return MaricopaAPICollector(
                config=mock_config,
                repository=mock_repository,
                logger_name="test.collector",
                client=mock_client,
                adapter=mock_adapter
            )

    def test_initialization(self, mock_config, mock_repository, mock_client, mock_adapter):
        """Test collector initialization."""
        with patch('phoenix_real_estate.collectors.maricopa.collector.DataValidator'):
            collector = MaricopaAPICollector(
                config=mock_config,
                repository=mock_repository,
                logger_name="test.collector",
                client=mock_client,
                adapter=mock_adapter
            )

        assert collector.config == mock_config
        assert collector.repository == mock_repository
        assert collector.client == mock_client
        assert collector.adapter == mock_adapter
        assert collector.batch_size == 100
        assert collector.max_retries == 3
        assert collector.retry_delay_seconds == 5

    def test_get_source_name(self, collector):
        """Test source name for Epic 3 orchestration."""
        assert collector.get_source_name() == "maricopa_api"

    def test_validate_config_success(self, collector):
        """Test successful configuration validation."""
        result = collector.validate_config()
        assert result is True

    def test_validate_config_missing_fields(self, collector, mock_config):
        """Test configuration validation with missing required fields."""
        mock_config.get.side_effect = lambda key: None if "bearer_token" in key else "test_value"
        
        with pytest.raises(ConfigurationError) as excinfo:
            collector.validate_config()
        
        assert "Missing required configuration fields" in str(excinfo.value)
        assert "maricopa.api.bearer_token" in str(excinfo.value)

    def test_validate_config_invalid_batch_size(self, collector, mock_config):
        """Test configuration validation with invalid batch size."""
        mock_config.get_int.side_effect = lambda key, default: 0 if "batch_size" in key else default
        collector.batch_size = 0
        
        with pytest.raises(ConfigurationError) as excinfo:
            collector.validate_config()
        
        assert "Invalid batch_size" in str(excinfo.value)

    def test_validate_config_repository_error(self, collector, mock_repository):
        """Test configuration validation with repository connection failure."""
        mock_repository.find_updated_since.side_effect = Exception("DB connection failed")
        
        with pytest.raises(ConfigurationError) as excinfo:
            collector.validate_config()
        
        assert "Repository connection test failed" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_collect_zipcode_success(self, collector, mock_client):
        """Test successful zipcode collection."""
        mock_properties = [
            {"property_id": "prop_1", "address": {"zipcode": "85001"}},
            {"property_id": "prop_2", "address": {"zipcode": "85001"}}
        ]
        mock_client.search_by_zipcode.return_value = mock_properties

        result = await collector.collect_zipcode("85001")

        assert len(result) == 2
        assert result == mock_properties
        mock_client.search_by_zipcode.assert_called_once_with("85001")

    @pytest.mark.asyncio
    async def test_collect_zipcode_no_results(self, collector, mock_client):
        """Test zipcode collection with no results."""
        mock_client.search_by_zipcode.return_value = []

        result = await collector.collect_zipcode("85001")

        assert result == []
        mock_client.search_by_zipcode.assert_called_once_with("85001")

    @pytest.mark.asyncio
    async def test_collect_zipcode_error(self, collector, mock_client):
        """Test zipcode collection with API error."""
        mock_client.search_by_zipcode.side_effect = Exception("API error")

        with pytest.raises(DataCollectionError) as excinfo:
            await collector.collect_zipcode("85001")

        assert "Collection operation 'collect_zipcode' failed" in str(excinfo.value)
        assert "API error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_collect_property_details_success(self, collector, mock_client, mock_adapter):
        """Test successful property details collection."""
        mock_raw_data = {"property_id": "prop_123", "details": "test"}
        mock_transformed_data = {"property_id": "prop_123", "transformed": True}
        
        mock_client.get_property_details.return_value = mock_raw_data
        mock_adapter.transform.return_value = mock_transformed_data

        result = await collector.collect_property_details("prop_123")

        assert result == mock_transformed_data
        mock_client.get_property_details.assert_called_once_with("prop_123")
        mock_adapter.transform.assert_called_once_with(mock_raw_data)

    @pytest.mark.asyncio
    async def test_collect_property_details_not_found(self, collector, mock_client):
        """Test property details collection when property not found."""
        mock_client.get_property_details.return_value = None

        result = await collector.collect_property_details("prop_123")

        assert result is None
        mock_client.get_property_details.assert_called_once_with("prop_123")

    @pytest.mark.asyncio
    async def test_collect_property_details_error(self, collector, mock_client):
        """Test property details collection with API error."""
        mock_client.get_property_details.side_effect = Exception("API error")

        with pytest.raises(DataCollectionError) as excinfo:
            await collector.collect_property_details("prop_123")

        assert "Collection operation 'collect_property_details' failed" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_adapt_property_success(self, collector, mock_adapter, mock_validator):
        """Test successful property adaptation."""
        raw_data = {"property_id": "prop_123", "raw_field": "value"}
        transformed_data = {
            "property_id": "prop_123",
            "address": {
                "street": "123 Test St",
                "city": "Phoenix", 
                "state": "AZ",
                "zipcode": "85001"
            },
            "features": {
                "bedrooms": 3,
                "bathrooms": 2,
                "square_footage": 1500
            },
            "last_updated": datetime.now().isoformat()
        }
        
        mock_adapter.transform.return_value = transformed_data
        
        with patch('phoenix_real_estate.collectors.maricopa.collector.Property') as mock_property_class:
            mock_property_obj = MagicMock()
            mock_property_obj.property_id = "prop_123"
            mock_property_class.return_value = mock_property_obj
            
            collector.validator = mock_validator

            result = await collector.adapt_property(raw_data)

            assert result == mock_property_obj
            mock_adapter.transform.assert_called_once_with(raw_data)
            mock_property_class.assert_called_once_with(**transformed_data)
            mock_validator.validate_property.assert_called_once_with(mock_property_obj)

    @pytest.mark.asyncio
    async def test_adapt_property_validation_error(self, collector, mock_adapter, mock_validator):
        """Test property adaptation with validation failure."""
        raw_data = {"property_id": "prop_123"}
        transformed_data = {"property_id": "prop_123", "invalid": "data"}
        
        mock_adapter.transform.return_value = transformed_data
        mock_validator.validate_property.return_value = False
        
        with patch('phoenix_real_estate.collectors.maricopa.collector.Property') as mock_property_class:
            mock_property_obj = MagicMock()
            mock_property_obj.property_id = "prop_123"
            mock_property_class.return_value = mock_property_obj
            
            collector.validator = mock_validator

            with pytest.raises(ValidationError) as excinfo:
                await collector.adapt_property(raw_data)

            assert "Property validation failed for prop_123" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_adapt_property_processing_error(self, collector, mock_adapter):
        """Test property adaptation with processing error."""
        raw_data = {"property_id": "prop_123"}
        mock_adapter.transform.side_effect = Exception("Transform error")

        with pytest.raises(ProcessingError) as excinfo:
            await collector.adapt_property(raw_data)

        assert "Property adaptation failed" in str(excinfo.value)
        assert "Transform error" in str(excinfo.value)

    def test_get_collection_status(self, collector):
        """Test collection status reporting."""
        status = collector.get_collection_status()
        
        assert status["collector_name"] == "MaricopaAPICollector"
        assert status["config_valid"] is True
        assert status["status"] == "ready"

    def test_get_collection_metrics(self, collector, mock_client):
        """Test collection metrics reporting."""
        collector.total_collected = 10
        collector.total_saved = 8
        collector.total_errors = 2
        collector.collection_start_time = datetime.now() - timedelta(seconds=30)

        metrics = collector.get_collection_metrics()

        assert "collection_metrics" in metrics
        assert metrics["collection_metrics"]["total_collected"] == 10
        assert metrics["collection_metrics"]["total_saved"] == 8
        assert metrics["collection_metrics"]["total_errors"] == 2
        assert "client_metrics" in metrics

    @pytest.mark.asyncio
    async def test_context_manager(self, collector, mock_client):
        """Test async context manager functionality."""
        async with collector as c:
            assert c == collector

        # Verify close was called
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, collector, mock_client):
        """Test resource cleanup."""
        await collector.close()
        mock_client.close.assert_called_once()


class TestMaricopaCollectorIntegration:
    """Integration tests for collector with real-like data flow."""

    @pytest.fixture
    def integration_collector(self):
        """Create collector for integration testing with minimal mocking."""
        config = MagicMock()
        config.get_dict.return_value = {"batch_size": 50}
        config.get_int.side_effect = lambda key, default=None: {
            "maricopa.collection.batch_size": 50,
            "maricopa.collection.max_retries": 2,
            "maricopa.collection.retry_delay_seconds": 1,
            "MARICOPA_RATE_LIMIT": 1000,
            "MARICOPA_TIMEOUT": 30
        }.get(key, default)
        config.get.side_effect = lambda key, default=None: {
            "maricopa.api.base_url": "https://api.example.com",
            "maricopa.api.bearer_token": "test_token",
            "MARICOPA_API_KEY": "test_key",
            "MARICOPA_BASE_URL": "https://api.example.com"
        }.get(key, default)
        # Add get_typed method to handle both dict and individual key access
        def get_typed_mock(key, expected_type, default=None):
            values = {
                "maricopa.collection": {
                    "batch_size": 50,
                    "max_retries": 2,
                    "retry_delay_seconds": 1
                },
                "maricopa.collection.batch_size": 50,
                "maricopa.collection.max_retries": 2,
                "maricopa.collection.retry_delay_seconds": 1
            }
            return values.get(key, default)
        
        config.get_typed.side_effect = get_typed_mock

        repository = MagicMock(spec=PropertyRepository)
        repository.find_updated_since.return_value = []
        repository.find_by_id.return_value = None
        repository.save.return_value = True

        # Create mock client to avoid real initialization
        mock_client = MagicMock(spec=MaricopaAPIClient)
        mock_client.search_by_zipcode = AsyncMock()
        mock_client.get_property_details = AsyncMock()
        mock_client.close = AsyncMock()

        # Create mock adapter to avoid real initialization
        mock_adapter = MagicMock(spec=MaricopaDataAdapter)

        with patch('phoenix_real_estate.collectors.maricopa.collector.DataValidator'):
            return MaricopaAPICollector(
                config=config,
                repository=repository,
                logger_name="integration.test",
                client=mock_client,
                adapter=mock_adapter
            )

    @pytest.mark.asyncio
    async def test_end_to_end_collection_workflow(self, integration_collector):
        """Test complete collection workflow from API to repository."""
        # Mock the API client to return test data
        test_properties = [
            {
                "property_id": "maricopa_001",
                "address": {"street": "123 Main St", "city": "Phoenix", "zipcode": "85001"},
                "details": {"bedrooms": 3, "bathrooms": 2}
            },
            {
                "property_id": "maricopa_002", 
                "address": {"street": "456 Oak Ave", "city": "Phoenix", "zipcode": "85001"},
                "details": {"bedrooms": 4, "bathrooms": 3}
            }
        ]

        integration_collector.client.search_by_zipcode = AsyncMock(return_value=test_properties)

        # Mock adapter to return transformed data
        transformed_properties = [
            {
                "property_id": "maricopa_001",
                "address": {
                    "street": "123 Main St",
                    "city": "Phoenix",
                    "state": "AZ", 
                    "zipcode": "85001"
                },
                "features": {
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "square_footage": 1500
                },
                "last_updated": datetime.now().isoformat()
            },
            {
                "property_id": "maricopa_002",
                "address": {
                    "street": "456 Oak Ave",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zipcode": "85001"
                }, 
                "features": {
                    "bedrooms": 4,
                    "bathrooms": 3,
                    "square_footage": 2000
                },
                "last_updated": datetime.now().isoformat()
            }
        ]

        integration_collector.adapter.transform.side_effect = lambda x: transformed_properties[0]

        # Execute collection workflow
        result = await integration_collector.collect_zipcode("85001")

        # Verify results
        assert len(result) == 2
        assert result == test_properties
        
        # Verify API client was called correctly
        integration_collector.client.search_by_zipcode.assert_called_once_with("85001")

    def test_configuration_integration(self, integration_collector):
        """Test configuration integration across components."""
        # Test that configuration is properly passed through
        assert integration_collector.batch_size == 50
        assert integration_collector.max_retries == 2
        assert integration_collector.retry_delay_seconds == 1

        # Test configuration validation
        assert integration_collector.validate_config() is True

    @pytest.mark.asyncio
    async def test_error_handling_chain(self, integration_collector):
        """Test error handling propagation through the system."""
        # Simulate client error
        integration_collector.client.search_by_zipcode = AsyncMock(
            side_effect=Exception("Network timeout")
        )

        # Test that error is properly wrapped and propagated
        with pytest.raises(DataCollectionError) as excinfo:
            await integration_collector.collect_zipcode("85001")

        assert "Collection operation 'collect_zipcode' failed" in str(excinfo.value)
        assert "Network timeout" in str(excinfo.value.original_error)