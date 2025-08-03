"""Comprehensive integration testing suite for Maricopa collector with Epic 1 foundation.

This module provides comprehensive integration testing covering:
- Epic 1 Foundation Integration Tests (ConfigProvider, PropertyRepository, Logging, Exceptions)
- End-to-End Workflow Integration Tests (Complete data collection pipeline)
- Component Integration Testing (Rate limiter, API client, Adapter, Collector)
- Performance & Rate Limiting Integration (Thread safety, memory efficiency)
- Data Integrity & Schema Validation (Schema compatibility, data quality)

Test Strategy:
- Mock external API calls but test real Epic 1 foundation integration
- Use realistic API response data for comprehensive testing
- Test error scenarios at each integration boundary
- Validate performance under simulated load conditions
- Test concurrent operations with thread safety validation
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import psutil
import os

import pytest

from phoenix_real_estate.foundation import (
    PropertyRepository,
    PropertyRepositoryImpl,
    get_logger,
    SecretManager,
)
from phoenix_real_estate.foundation.database.schema import Property
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError,
    ConfigurationError,
    ValidationError,
    ProcessingError,
    DatabaseError,
)
from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter
from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter, DataValidator
from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector


class TestEpic1FoundationIntegration:
    """Epic 1 Foundation Integration Tests - Core infrastructure components."""

    @pytest.fixture
    def real_config_provider(self):
        """Real ConfigProvider instance for foundation integration testing."""
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        return EnvironmentConfigProvider()

    @pytest.fixture
    def mock_mongo_client(self):
        """Mock MongoDB client for repository testing."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection

        # Mock find operations
        mock_collection.find.return_value = []
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock_collection.update_one.return_value = MagicMock(matched_count=1, modified_count=1)
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        return mock_client

    @pytest.fixture
    def real_property_repository(self, mock_mongo_client):
        """Real PropertyRepository instance with mocked MongoDB connection."""
        # Mock DatabaseConnection
        mock_db_connection = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Mock database operations (async methods)
        mock_collection.find.return_value = []
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
        mock_collection.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )
        mock_collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        mock_collection.count_documents = AsyncMock(return_value=0)

        # Mock cursor operations for find operations
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__aiter__.return_value = iter([])  # Empty results
        mock_collection.find.return_value = mock_cursor

        mock_db.__getitem__.return_value = mock_collection

        # Mock the async context manager get_database method
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_db)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db_connection.get_database = MagicMock(return_value=async_context_manager)

        return PropertyRepositoryImpl(mock_db_connection)

    @pytest.fixture
    def real_logger(self):
        """Real logger instance for foundation integration testing."""
        return get_logger("test.integration")

    @pytest.fixture
    def sample_property_data(self):
        """Sample property data for testing."""
        return {
            "property_id": "maricopa_integration_test_001",
            "address": {
                "street": "123 Integration Test Ave",
                "city": "Phoenix",
                "state": "AZ",
                "zipcode": "85001",
            },
            "features": {
                "bedrooms": 3,
                "bathrooms": 2,
                "square_footage": 1500,
                "lot_size": 7200,
                "year_built": 2010,
            },
            "listing_details": {
                "price": 450000,
                "list_date": datetime.now().isoformat(),
                "property_type": "single_family",
                "status": "active",
            },
            "last_updated": datetime.now().isoformat(),
        }

    def test_config_provider_integration(self, real_config_provider):
        """Verify ConfigProvider usage for API credentials and settings."""
        # Test configuration loading
        config = real_config_provider

        # Test string configuration access with defaults
        base_url = config.get("maricopa.api.base_url", "https://default.api.com")
        assert isinstance(base_url, str)
        assert base_url.startswith("http")

        # Test integer configuration access with defaults
        batch_size = config.get_typed("maricopa.collection.batch_size", int, default=100)
        assert isinstance(batch_size, int)
        assert 1 <= batch_size <= 1000

        # Test dictionary configuration access with defaults
        collection_config = config.get_typed("maricopa.collection", dict, default={})
        assert isinstance(collection_config, dict)

        # Test get_required method behavior
        try:
            config.get_required("definitely.missing.key")
        except ConfigurationError:
            # Expected behavior for missing required configuration
            pass

        # Test environment detection
        env = config.get_environment()
        assert isinstance(env, str)
        assert env in ["development", "testing", "staging", "production"]

    @pytest.mark.asyncio
    async def test_property_repository_integration(
        self, real_property_repository, sample_property_data
    ):
        """Verify PropertyRepository data persistence with schema validation."""
        repo = real_property_repository

        # Test Property object creation
        property_obj = Property(**sample_property_data)
        assert property_obj.property_id == "maricopa_integration_test_001"
        assert property_obj.address.city == "Phoenix"
        assert property_obj.features.bedrooms == 3

        # Test repository async operations (mocked MongoDB)
        # Test create operation
        property_dict = property_obj.model_dump()
        result_id = await repo.create(property_dict)
        assert isinstance(result_id, str)

        # Test get operation
        found_property = await repo.get_by_property_id("maricopa_integration_test_001")
        # With mocked MongoDB, this returns None
        assert found_property is None

        # Test search operations
        properties, total_count = await repo.search_by_zipcode("85001")
        assert isinstance(properties, list)
        assert isinstance(total_count, int)

        # Test recent updates
        recent_properties = await repo.get_recent_updates(datetime.now() - timedelta(hours=1))
        assert isinstance(recent_properties, list)

    def test_logging_framework_integration(self, real_logger):
        """Verify structured logging throughout entire workflow."""
        logger = real_logger

        # Test basic logging operations
        logger.info(
            "Integration test started",
            extra={"component": "maricopa_collector", "operation": "integration_test"},
        )

        logger.warning(
            "Test warning with context", extra={"property_id": "test_001", "error_code": "WARN_001"}
        )

        # Test error logging with exception context
        try:
            raise ValueError("Test exception for logging")
        except ValueError:
            logger.error(
                "Test error logging",
                exc_info=True,
                extra={"operation": "test_operation", "error_type": "ValueError"},
            )

        # Test performance logging
        start_time = time.time()
        time.sleep(0.01)  # Simulate work
        duration = time.time() - start_time

        logger.info(
            "Operation completed",
            extra={
                "operation": "test_operation",
                "duration_ms": int(duration * 1000),
                "success": True,
            },
        )

        # Verify logger name and configuration
        assert logger.name == "test.integration"
        assert logger.level <= 20  # INFO level or lower

    def test_exception_hierarchy_compliance(self):
        """Verify Epic 1 exception patterns used correctly throughout."""
        # Test DataCollectionError
        try:
            raise DataCollectionError(
                "Test collection error",
                operation="test_collect",
                source="integration_test",
                original_error=ValueError("Original error"),
            )
        except DataCollectionError as e:
            assert e.operation == "test_collect"
            assert e.source == "integration_test"
            assert isinstance(e.original_error, ValueError)
            assert "Test collection error" in str(e)

        # Test ConfigurationError
        try:
            raise ConfigurationError(
                "Missing configuration", config_key="test.missing.key", expected_type="str"
            )
        except ConfigurationError as e:
            assert e.config_key == "test.missing.key"
            assert e.expected_type == "str"
            assert "Missing configuration" in str(e)

        # Test ValidationError
        try:
            raise ValidationError(
                "Schema validation failed",
                field_name="test_field",
                expected_value="string",
                actual_value=123,
            )
        except ValidationError as e:
            assert e.field_name == "test_field"
            assert e.expected_value == "string"
            assert e.actual_value == 123

        # Test ProcessingError
        try:
            raise ProcessingError(
                "Processing failed",
                stage="transformation",
                data_context={"property_id": "test_001"},
            )
        except ProcessingError as e:
            assert e.stage == "transformation"
            assert e.data_context["property_id"] == "test_001"

    def test_epic1_secret_management_integration(self):
        """Test Secret Management integration with collectors."""
        # Test secret manager directly
        secret_manager = SecretManager()

        # Test getting a secret with default (non-secret name returns None/default)
        secret_value = secret_manager.get_secret("NON_SECRET_NAME", default="default_value")
        assert secret_value is None  # SecretManager returns None for non-secret names

        # Test with proper secret name and environment variable (using SECRET_ prefix)
        with patch.dict(os.environ, {"SECRET_MARICOPA_API": "test_secret_value"}, clear=False):
            secret_value = secret_manager.get_secret("SECRET_MARICOPA_API", default="default")
            assert secret_value == "test_secret_value"

        # Test with CREDENTIAL_ prefix (another valid prefix)
        with patch.dict(os.environ, {"CREDENTIAL_DB_PASS": "test_db_password"}, clear=False):
            secret_value = secret_manager.get_secret("CREDENTIAL_DB_PASS")
            assert secret_value == "test_db_password"

        # Test required secret error handling with proper prefix
        try:
            secret_manager.get_required_secret("SECRET_MISSING_API_KEY")
            assert False, "Should have raised SecretNotFoundError"
        except Exception as e:
            # Expected behavior for missing required secret
            assert "secret" in str(e).lower() or "not found" in str(e).lower()


class TestEndToEndWorkflowIntegration:
    """End-to-End Workflow Integration Tests - Complete data collection pipeline."""

    @pytest.fixture
    def mock_api_responses(self):
        """Realistic API response data for testing."""
        return {
            "zipcode_search": [
                {
                    "property_id": "maricopa_e2e_001",
                    "address": {
                        "street": "123 E2E Test St",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zipcode": "85001",
                    },
                    "basic_info": {"bedrooms": 3, "bathrooms": 2, "price": 425000},
                },
                {
                    "property_id": "maricopa_e2e_002",
                    "address": {
                        "street": "456 Integration Ave",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zipcode": "85001",
                    },
                    "basic_info": {"bedrooms": 4, "bathrooms": 3, "price": 550000},
                },
            ],
            "property_details": {
                "maricopa_e2e_001": {
                    "property_id": "maricopa_e2e_001",
                    "detailed_info": {
                        "square_footage": 1850,
                        "lot_size": 8000,
                        "year_built": 2015,
                        "property_type": "single_family",
                    },
                    "listing_details": {
                        "list_date": "2024-01-15",
                        "status": "active",
                        "days_on_market": 30,
                    },
                }
            },
        }

    @pytest.fixture
    def integrated_collector(self, mock_api_responses):
        """Fully integrated collector with real foundation components and mocked external APIs."""
        # Real foundation components
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        config = EnvironmentConfigProvider()

        # Configure test values
        with patch.object(config, "get") as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "maricopa.api.base_url": "https://test-api.maricopa.gov",
                "maricopa.api.bearer_token": "test_bearer_token",
                "MARICOPA_API_KEY": "test_api_key",
            }.get(key, default)

        with patch.object(config, "get_typed") as mock_get_typed:

            def mock_get_typed_side_effect(key, type_class, default=None):
                if type_class is int:
                    return {
                        "maricopa.collection.batch_size": 50,
                        "maricopa.collection.max_retries": 3,
                        "maricopa.collection.retry_delay_seconds": 1,
                        "MARICOPA_RATE_LIMIT": 1000,
                        "MARICOPA_TIMEOUT": 30,
                    }.get(key, default)
                return default

            mock_get_typed.side_effect = mock_get_typed_side_effect

        # Real repository with mocked MongoDB
        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_mongo_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.return_value = []
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")

        # Mock DatabaseConnection instead of get_mongo_client
        mock_db_connection = MagicMock()
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_db)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db_connection.get_database = MagicMock(return_value=async_context_manager)

        repository = PropertyRepositoryImpl(mock_db_connection)

        # Real logger
        get_logger("test.e2e.collector")

        # Mock external API calls
        mock_client = MagicMock(spec=MaricopaAPIClient)
        mock_client.search_by_zipcode = AsyncMock(return_value=mock_api_responses["zipcode_search"])
        mock_client.get_property_details = AsyncMock(
            side_effect=lambda prop_id: mock_api_responses["property_details"].get(prop_id)
        )
        mock_client.close = AsyncMock()
        mock_client.get_metrics.return_value = {
            "requests_made": 3,
            "success_rate": 1.0,
            "average_response_time": 0.5,
        }

        # Real adapter
        adapter = MaricopaDataAdapter()

        # Create collector with mixed real/mock components
        with patch("phoenix_real_estate.collectors.maricopa.collector.DataValidator"):
            collector = MaricopaAPICollector(
                config=config,
                repository=repository,
                logger_name="test.e2e.collector",
                client=mock_client,
                adapter=adapter,
            )

        return collector

    @pytest.mark.asyncio
    async def test_zipcode_collection_e2e(self, integrated_collector):
        """Test complete zipcode collection workflow with mocked API."""
        collector = integrated_collector

        # Execute end-to-end zipcode collection
        result = await collector.collect_zipcode("85001")

        # Verify results
        assert len(result) == 2
        assert result[0]["property_id"] == "maricopa_e2e_001"
        assert result[1]["property_id"] == "maricopa_e2e_002"

        # Verify API client interaction
        collector.client.search_by_zipcode.assert_called_once_with("85001")

        # Verify logging occurred (logger is real)
        assert collector.logger.name == "test.e2e.collector"

    @pytest.mark.asyncio
    async def test_property_adaptation_e2e(self, integrated_collector, mock_api_responses):
        """Test end-to-end property adaptation from API to repository."""
        collector = integrated_collector

        # Test raw API data to Property object transformation
        raw_property_data = mock_api_responses["zipcode_search"][0]

        # Mock validator to return True
        with patch(
            "phoenix_real_estate.collectors.maricopa.collector.DataValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate_property.return_value = True
            mock_validator_class.return_value = mock_validator

            collector.validator = mock_validator

            # Execute adaptation
            adapted_property = await collector.adapt_property(raw_property_data)

            # Verify adaptation results
            assert adapted_property is not None
            assert hasattr(adapted_property, "property_id")

            # Verify validation was called
            mock_validator.validate_property.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_e2e(self, integrated_collector):
        """Test error handling throughout entire collection workflow."""
        collector = integrated_collector

        # Test network error handling
        collector.client.search_by_zipcode = AsyncMock(side_effect=Exception("Network timeout"))

        with pytest.raises(DataCollectionError) as exc_info:
            await collector.collect_zipcode("85001")

        assert "Collection operation 'collect_zipcode' failed" in str(exc_info.value)
        assert exc_info.value.operation == "collect_zipcode"
        assert exc_info.value.source == "maricopa_api"

        # Test validation error handling
        collector.client.search_by_zipcode = AsyncMock(
            return_value=[{"property_id": "test_001", "invalid": "data"}]
        )

        with patch(
            "phoenix_real_estate.collectors.maricopa.collector.DataValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate_property.return_value = False
            mock_validator_class.return_value = mock_validator

            collector.validator = mock_validator

            with pytest.raises(ValidationError):
                raw_data = {"property_id": "test_001", "invalid": "data"}
                await collector.adapt_property(raw_data)

    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self, integrated_collector):
        """Test API client → adapter → validation → repository pipeline."""
        collector = integrated_collector

        # Set up pipeline test
        zipcode = "85001"

        # Execute full pipeline
        async with collector:
            # Step 1: Collect from API
            properties = await collector.collect_zipcode(zipcode)
            assert len(properties) == 2

            # Step 2: Adapt first property
            raw_property = properties[0]

            with patch(
                "phoenix_real_estate.collectors.maricopa.collector.DataValidator"
            ) as mock_validator_class:
                mock_validator = MagicMock()
                mock_validator.validate_property.return_value = True
                mock_validator_class.return_value = mock_validator
                collector.validator = mock_validator

                adapted_property = await collector.adapt_property(raw_property)
                assert adapted_property is not None

                # Step 3: Save to repository
                save_result = collector.repository.save(adapted_property)
                assert save_result is True

        # Verify client cleanup was called
        collector.client.close.assert_called_once()


class TestComponentIntegrationTesting:
    """Component Integration Testing - Rate limiter, API client, Adapter, Collector."""

    @pytest.fixture
    def integrated_rate_limiter(self):
        """Real rate limiter for integration testing."""
        return RateLimiter(
            requests_per_minute=600, safety_margin=0.10
        )  # 600 per minute = 10 per second

    @pytest.fixture
    def integrated_api_client(self, integrated_rate_limiter):
        """API client with real rate limiter integration."""
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "MARICOPA_API_KEY": "test_api_key",
            "MARICOPA_BASE_URL": "https://test.api.com",
            "maricopa.api.bearer_token": "test_token",
        }.get(key, default)
        config.get_typed.side_effect = (
            lambda key, type_class, default=None: {
                "MARICOPA_TIMEOUT": 30,
                "MARICOPA_RATE_LIMIT": 600,  # 10 per second as requests per minute
            }.get(key, default)
            if type_class is int
            else default
        )

        # Create client with proper configuration
        client = MaricopaAPIClient(config=config, requests_per_hour=600)

        # Mock HTTP session after initialization
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[{"success": True}])
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        client.session = mock_session

        # Replace internal rate limiter with our test rate limiter
        client.rate_limiter = integrated_rate_limiter

        return client

    @pytest.mark.asyncio
    async def test_rate_limiter_integration_with_api_client(self, integrated_api_client):
        """Test rate limiter integration with API client."""
        client = integrated_api_client

        # Test that rate limiter is properly integrated
        assert client.rate_limiter is not None
        assert client.rate_limiter.requests_per_minute == 600
        assert client.rate_limiter.safety_margin == 0.10

        # Test rate limiter usage tracking
        initial_usage = client.rate_limiter.get_current_usage("test_source")
        assert initial_usage["current_requests"] == 0
        assert initial_usage["effective_limit"] == 540  # 600 * 0.9 (10% safety margin)

        # Test rate limiter wait_if_needed method (core integration point)
        start_time = time.time()
        wait_time = await client.rate_limiter.wait_if_needed("test_source")
        elapsed = time.time() - start_time

        # First request should not require waiting
        assert wait_time == 0
        assert elapsed < 0.1  # Should be nearly instantaneous

        # Test rate limiter handles concurrent access
        concurrent_tasks = []
        for i in range(10):
            concurrent_tasks.append(client.rate_limiter.wait_if_needed(f"source_{i}"))

        concurrent_wait_times = await asyncio.gather(*concurrent_tasks)

        # Verify all concurrent access completed
        assert len(concurrent_wait_times) == 10
        assert all(wait_time >= 0 for wait_time in concurrent_wait_times)

    def test_api_client_integration_with_data_adapter(self):
        """Test API client integration with data adapter."""
        adapter = MaricopaDataAdapter()

        # Test API response format compatibility with adapter
        mock_api_response = {
            "property_id": "api_test_001",
            "address": {
                "street_number": "123",
                "street_name": "Test St",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85001",
            },
            "property_details": {
                "bedrooms": 3,
                "bathrooms": 2,
                "square_feet": 1500,
                "lot_size_sq_ft": 7200,
            },
            "listing_info": {"list_price": 450000, "listing_date": "2024-01-15T10:00:00Z"},
        }

        # Test adapter can handle API client response format
        transformed = adapter.transform(mock_api_response)

        assert transformed["property_id"] == "api_test_001"
        assert transformed["address"]["street"].startswith("123")
        assert transformed["address"]["city"] == "Phoenix"
        assert transformed["features"]["bedrooms"] == 3
        assert transformed["listing_details"]["price"] == 450000

    def test_data_adapter_integration_with_property_repository(self):
        """Test data adapter integration with property repository."""
        adapter = MaricopaDataAdapter()

        # Mock repository
        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_mongo_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")

        # Mock DatabaseConnection
        mock_db_connection = MagicMock()
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_db)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db_connection.get_database = MagicMock(return_value=async_context_manager)

        repository = PropertyRepositoryImpl(mock_db_connection)

        # Test adapter output is compatible with repository
        raw_data = {
            "property_id": "adapter_repo_test_001",
            "address": {
                "street_number": "456",
                "street_name": "Repo Test Ave",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85002",
            },
            "property_details": {"bedrooms": 4, "bathrooms": 3, "square_feet": 2000},
        }

        # Transform using adapter
        transformed = adapter.transform(raw_data)

        # Create Property object from transformed data
        property_obj = Property(**transformed)

        # Verify repository can save the property
        result = repository.save(property_obj)
        assert result is True

    @pytest.mark.asyncio
    async def test_collector_orchestration_of_all_components(self):
        """Test collector orchestration of all components."""
        # Create integrated collector with real components
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        config = EnvironmentConfigProvider()

        with patch.object(config, "get") as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "maricopa.api.base_url": "https://test.api.com",
                "maricopa.api.bearer_token": "test_token",
            }.get(key, default)

        with patch.object(config, "get_typed") as mock_get_typed:

            def mock_typed_effect(key, type_class, default=None):
                if type_class is int:
                    return {
                        "maricopa.collection.batch_size": 10,
                        "maricopa.collection.max_retries": 2,
                        "MARICOPA_RATE_LIMIT": 100,
                        "MARICOPA_TIMEOUT": 30,
                    }.get(key, default)
                return default

            mock_get_typed.side_effect = mock_typed_effect

        # Mock repository
        repository = MagicMock(spec=PropertyRepository)
        repository.find_updated_since.return_value = []
        repository.save.return_value = True

        # Real components with mocked external dependencies
        rate_limiter = RateLimiter(requests_per_minute=600)  # 10 per second
        adapter = MaricopaDataAdapter()

        # Mock HTTP session
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value=[
                    {
                        "property_id": "orchestration_test_001",
                        "address": {
                            "street_number": "789",
                            "street_name": "Orchestration St",
                            "city": "Phoenix",
                            "state": "AZ",
                            "zip_code": "85003",
                        },
                        "property_details": {"bedrooms": 3, "bathrooms": 2},
                    }
                ]
            )
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = MaricopaAPIClient(config=config, rate_limiter=rate_limiter)
            client.session = mock_session

            # Create collector
            with patch("phoenix_real_estate.collectors.maricopa.collector.DataValidator"):
                collector = MaricopaAPICollector(
                    config=config, repository=repository, client=client, adapter=adapter
                )

            # Test orchestration
            async with collector:
                properties = await collector.collect_zipcode("85003")
                assert len(properties) == 1
                assert properties[0]["property_id"] == "orchestration_test_001"


class TestPerformanceRateLimitingIntegration:
    """Performance & Rate Limiting Integration - Thread safety, memory efficiency."""

    @pytest.fixture
    def performance_collector(self):
        """Collector configured for performance testing."""
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "maricopa.api.base_url": "https://perf-test.api.com",
            "maricopa.api.bearer_token": "perf_token",
        }.get(key, default)
        config.get_typed.side_effect = (
            lambda key, type_class, default=None: {
                "maricopa.collection.batch_size": 100,
                "MARICOPA_RATE_LIMIT": 1000,
                "MARICOPA_TIMEOUT": 5,
            }.get(key, default)
            if type_class is int
            else default
        )

        repository = MagicMock(spec=PropertyRepository)
        repository.save.return_value = True
        repository.find_updated_since.return_value = []

        # Fast rate limiter for performance testing
        rate_limiter = RateLimiter(requests_per_minute=60000)  # 1000 per second

        # Mock fast API responses
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value=[{"property_id": f"perf_test_{i}", "data": "test"} for i in range(10)]
            )
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = MaricopaAPIClient(config=config, rate_limiter=rate_limiter)
            client.session = mock_session
            adapter = MaricopaDataAdapter()

            with patch("phoenix_real_estate.collectors.maricopa.collector.DataValidator"):
                collector = MaricopaAPICollector(
                    config=config, repository=repository, client=client, adapter=adapter
                )

            return collector

    @pytest.mark.asyncio
    async def test_rate_limiting_compliance_under_load(self, performance_collector):
        """Test rate limiting prevents API violations during collection."""
        collector = performance_collector

        # Configure rate limiter to 10 requests per second
        collector.client.rate_limiter = RateLimiter(requests_per_minute=600)  # 10 per second

        # Execute many requests rapidly
        start_time = time.time()

        tasks = []
        for i in range(20):  # 20 requests with 10/second limit
            tasks.append(collector.collect_zipcode(f"8500{i:02d}"))

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # Verify all requests completed
        assert len(results) == 20

        # Verify rate limiting was enforced (should take at least ~2 seconds)
        assert elapsed >= 1.8  # Account for timing variance

        # Verify no rate limit errors occurred
        for result in results:
            assert isinstance(result, list)  # Successful collection returns list

    @pytest.mark.asyncio
    async def test_concurrent_collection_thread_safety(self, performance_collector):
        """Test thread-safe concurrent collection operations."""
        collector = performance_collector

        # Test concurrent access to collector state
        concurrent_operations = []

        # Create multiple concurrent collection tasks
        for i in range(5):
            concurrent_operations.append(collector.collect_zipcode(f"8500{i}"))

        # Execute concurrently
        results = await asyncio.gather(*concurrent_operations)

        # Verify all operations completed successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, list)

        # Verify collector state remained consistent
        metrics = collector.get_collection_metrics()
        assert "collection_metrics" in metrics

        # Test thread safety of rate limiter
        rate_limiter = collector.client.rate_limiter

        async def rate_limited_operation():
            async with rate_limiter:
                await asyncio.sleep(0.01)  # Simulate work
                return True

        # Execute many concurrent rate-limited operations
        concurrent_rate_operations = [rate_limited_operation() for _ in range(50)]

        rate_results = await asyncio.gather(*concurrent_rate_operations)
        assert len(rate_results) == 50
        assert all(result for result in rate_results)

    @pytest.mark.asyncio
    async def test_memory_usage_during_large_collection(self, performance_collector):
        """Test memory efficiency during large dataset collection."""
        collector = performance_collector

        # Configure for large batch processing
        collector.batch_size = 500

        # Mock large dataset response
        large_dataset = [
            {
                "property_id": f"memory_test_{i}",
                "address": {"street": f"{i} Memory Test St", "city": "Phoenix", "zipcode": "85001"},
                "data": "x" * 100,  # Some data payload
            }
            for i in range(1000)  # 1000 properties
        ]

        collector.client.session.get.return_value.json = AsyncMock(return_value=large_dataset)

        # Monitor memory usage
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Execute large collection
        async with collector:
            result = await collector.collect_zipcode("85001")

            # Force garbage collection
            gc.collect()

            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = memory_after - memory_before

        # Verify collection succeeded
        assert len(result) == 1000

        # Verify memory usage remained reasonable (< 100MB increase)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"

    @pytest.mark.asyncio
    async def test_response_time_benchmarks(self, performance_collector):
        """Validate response time requirements (<30s for zipcode search)."""
        collector = performance_collector

        # Test single zipcode search performance
        start_time = time.time()
        result = await collector.collect_zipcode("85001")
        elapsed = time.time() - start_time

        # Verify response time requirement
        assert elapsed < 30.0, f"Zipcode search took {elapsed:.2f}s, exceeds 30s limit"
        assert len(result) > 0  # Ensure we got results

        # Test batch operations performance
        zipcodes = ["85001", "85002", "85003", "85004", "85005"]

        start_time = time.time()
        batch_results = await asyncio.gather(
            *[collector.collect_zipcode(zipcode) for zipcode in zipcodes]
        )
        batch_elapsed = time.time() - start_time

        # Verify batch performance scales reasonably
        assert batch_elapsed < 60.0, f"Batch search took {batch_elapsed:.2f}s"
        assert len(batch_results) == 5

        # Test property details performance
        start_time = time.time()
        await collector.collect_property_details("test_property_001")
        details_elapsed = time.time() - start_time

        assert details_elapsed < 10.0, f"Property details took {details_elapsed:.2f}s"


class TestDataIntegritySchemaValidation:
    """Data Integrity & Schema Validation - Schema compatibility, data quality."""

    @pytest.fixture
    def validation_test_data(self):
        """Test data for validation scenarios."""
        return {
            "valid_property": {
                "property_id": "validation_test_001",
                "address": {
                    "street": "123 Validation St",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zipcode": "85001",
                },
                "features": {"bedrooms": 3, "bathrooms": 2, "square_footage": 1500},
                "last_updated": datetime.now().isoformat(),
            },
            "invalid_property": {
                "property_id": "validation_test_002",
                "address": {
                    "street": "",  # Invalid empty street
                    "city": "Phoenix",
                    "zipcode": "INVALID",  # Invalid zipcode format
                },
                "features": {
                    "bedrooms": -1,  # Invalid negative bedrooms
                    "bathrooms": 0,
                    "square_footage": "not_a_number",  # Invalid type
                },
                "last_updated": "invalid_date",  # Invalid date format
            },
        }

    def test_end_to_end_data_flow_validation(self, validation_test_data):
        """Test end-to-end data flow validation."""
        adapter = MaricopaDataAdapter()

        # Test valid data flow
        valid_data = validation_test_data["valid_property"]
        transformed = adapter.transform(valid_data)

        # Verify transformation preserves data integrity
        assert transformed["property_id"] == valid_data["property_id"]
        assert transformed["address"]["street"] == valid_data["address"]["street"]
        assert transformed["features"]["bedrooms"] == valid_data["features"]["bedrooms"]

        # Verify Property object can be created
        property_obj = Property(**transformed)
        assert property_obj.property_id == valid_data["property_id"]

    def test_schema_compatibility_between_adapter_and_repository(self, validation_test_data):
        """Test schema compatibility between adapter and repository."""
        adapter = MaricopaDataAdapter()

        # Mock repository
        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_mongo_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")

        # Mock DatabaseConnection
        mock_db_connection = MagicMock()
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_db)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db_connection.get_database = MagicMock(return_value=async_context_manager)

        repository = PropertyRepositoryImpl(mock_db_connection)

        # Test schema compatibility
        valid_data = validation_test_data["valid_property"]
        transformed = adapter.transform(valid_data)
        property_obj = Property(**transformed)

        # Verify repository can handle the property object
        result = repository.save(property_obj)
        assert result is True

    def test_data_quality_preservation_through_transformation(self, validation_test_data):
        """Test data quality preservation through transformation."""
        adapter = MaricopaDataAdapter()
        validator = DataValidator()

        # Test quality preservation
        valid_data = validation_test_data["valid_property"]
        transformed = adapter.transform(valid_data)
        property_obj = Property(**transformed)

        # Verify data quality is preserved
        is_valid = validator.validate_property(property_obj)
        assert is_valid is True

        # Verify required fields are present
        assert property_obj.property_id
        assert property_obj.address["street"]
        assert property_obj.address["city"]
        assert property_obj.features["bedrooms"] > 0

    def test_error_handling_at_each_integration_point(self, validation_test_data):
        """Test error handling at each integration point."""
        adapter = MaricopaDataAdapter()
        validator = DataValidator()

        # Test adapter error handling
        invalid_data = validation_test_data["invalid_property"]

        try:
            transformed = adapter.transform(invalid_data)
            property_obj = Property(**transformed)

            # Validator should catch invalid data
            is_valid = validator.validate_property(property_obj)
            assert is_valid is False

        except (ValidationError, ValueError) as e:
            # Expected behavior for invalid data
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()

        # Test repository error handling
        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Simulate database error
        mock_collection.insert_one.side_effect = Exception("Database connection failed")
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection

        # Mock DatabaseConnection
        mock_db_connection = MagicMock()
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_db)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db_connection.get_database = MagicMock(return_value=async_context_manager)

        repository = PropertyRepositoryImpl(mock_db_connection)

        # Test repository error handling
        valid_data = validation_test_data["valid_property"]
        transformed = adapter.transform(valid_data)
        property_obj = Property(**transformed)

        try:
            result = repository.save(property_obj)
            # Should handle database errors gracefully
            assert result is False or result is None
        except DatabaseError:
            # Expected database error handling
            pass

    def test_concurrent_validation_thread_safety(self, validation_test_data):
        """Test validation thread safety under concurrent access."""
        adapter = MaricopaDataAdapter()
        validator = DataValidator()

        valid_data = validation_test_data["valid_property"]

        def validate_property_thread(thread_id):
            """Thread function for concurrent validation."""
            try:
                # Create unique data for each thread
                thread_data = valid_data.copy()
                thread_data["property_id"] = f"thread_test_{thread_id}"

                # Transform and validate
                transformed = adapter.transform(thread_data)
                property_obj = Property(**transformed)
                is_valid = validator.validate_property(property_obj)

                return is_valid, thread_id
            except Exception as e:
                return False, f"thread_{thread_id}_error: {str(e)}"

        # Run concurrent validation
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate_property_thread, i) for i in range(20)]

            results = []
            for future in as_completed(futures):
                result, thread_id = future.result()
                results.append((result, thread_id))

        # Verify all validations succeeded
        assert len(results) == 20
        successful_validations = sum(1 for result, _ in results if result is True)
        assert successful_validations == 20, (
            f"Only {successful_validations}/20 validations succeeded"
        )


# Performance and integration benchmarks
class TestIntegrationBenchmarks:
    """Integration performance benchmarks and metrics."""

    @pytest.mark.asyncio
    async def test_integration_performance_benchmarks(self):
        """Comprehensive integration performance benchmarks."""
        # Create fully integrated collector
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider

        config = EnvironmentConfigProvider()

        with (
            patch.object(config, "get") as mock_get,
            patch.object(config, "get_typed") as mock_get_typed,
        ):
            mock_get.side_effect = lambda key, default=None: {
                "maricopa.api.base_url": "https://benchmark.api.com",
                "maricopa.api.bearer_token": "benchmark_token",
            }.get(key, default)

            def mock_typed_effect(key, type_class, default=None):
                if type_class is int:
                    return {
                        "maricopa.collection.batch_size": 100,
                        "MARICOPA_RATE_LIMIT": 1000,
                        "MARICOPA_TIMEOUT": 30,
                    }.get(key, default)
                return default

            mock_get_typed.side_effect = mock_typed_effect

            # Mock high-performance repository
            repository = MagicMock(spec=PropertyRepository)
            repository.save.return_value = True
            repository.find_updated_since.return_value = []

            # High-performance components
            rate_limiter = RateLimiter(requests_per_minute=60000)  # 1000 per second
            adapter = MaricopaDataAdapter()

            # Mock fast API responses
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = MagicMock()
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(
                    return_value=[
                        {
                            "property_id": f"benchmark_{i}",
                            "address": {
                                "street_number": str(100 + i),
                                "street_name": "Benchmark St",
                                "city": "Phoenix",
                                "state": "AZ",
                                "zip_code": "85001",
                            },
                            "property_details": {"bedrooms": 3, "bathrooms": 2},
                        }
                        for i in range(50)
                    ]
                )
                mock_session.get = AsyncMock(return_value=mock_response)
                mock_session.close = AsyncMock()
                mock_session_class.return_value = mock_session

                client = MaricopaAPIClient(config=config, rate_limiter=rate_limiter)
                client.session = mock_session

                with patch("phoenix_real_estate.collectors.maricopa.collector.DataValidator"):
                    collector = MaricopaAPICollector(
                        config=config, repository=repository, client=client, adapter=adapter
                    )

                # Benchmark metrics
                benchmarks = {}

                # Benchmark 1: Single collection operation
                start_time = time.time()
                result = await collector.collect_zipcode("85001")
                benchmarks["single_collection_time"] = time.time() - start_time
                benchmarks["single_collection_count"] = len(result)

                # Benchmark 2: Batch collection operations
                zipcodes = [f"8500{i}" for i in range(10)]
                start_time = time.time()
                batch_results = await asyncio.gather(
                    *[collector.collect_zipcode(zipcode) for zipcode in zipcodes]
                )
                benchmarks["batch_collection_time"] = time.time() - start_time
                benchmarks["batch_collection_count"] = sum(len(r) for r in batch_results)

                # Benchmark 3: Adaptation performance
                sample_properties = result[:10] if result else []
                start_time = time.time()

                with patch(
                    "phoenix_real_estate.collectors.maricopa.collector.DataValidator"
                ) as mock_validator_class:
                    mock_validator = MagicMock()
                    mock_validator.validate_property.return_value = True
                    mock_validator_class.return_value = mock_validator
                    collector.validator = mock_validator

                    adapted_properties = []
                    for prop in sample_properties:
                        adapted = await collector.adapt_property(prop)
                        if adapted:
                            adapted_properties.append(adapted)

                benchmarks["adaptation_time"] = time.time() - start_time
                benchmarks["adaptation_count"] = len(adapted_properties)

                # Verify benchmark requirements
                assert benchmarks["single_collection_time"] < 30.0
                assert benchmarks["batch_collection_time"] < 60.0
                assert benchmarks["adaptation_time"] < 5.0

                # Log benchmark results for monitoring
                logger = get_logger("test.benchmarks")
                logger.info(
                    "Integration benchmarks completed",
                    extra={"benchmarks": benchmarks, "test_type": "integration_performance"},
                )
