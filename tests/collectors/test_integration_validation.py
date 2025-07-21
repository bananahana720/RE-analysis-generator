"""Integration validation tests for collectors.

Validates integration with Epic 1 foundation, Epic 3 orchestration readiness,
Epic 4 monitoring, and end-to-end workflows.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

import pytest

from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector
from phoenix_real_estate.collectors.base import DataCollector, RateLimiter
from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository, get_logger
from phoenix_real_estate.foundation.utils.exceptions import (
    DataCollectionError, ConfigurationError, ValidationError, ProcessingError
)
from phoenix_real_estate.foundation.database.schema import Property


class TestEpic1FoundationIntegration:
    """Test integration with Epic 1 foundation components."""
    
    @pytest.fixture
    def foundation_config(self):
        """Create real foundation ConfigProvider."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "maricopa.api.base_url": "https://api.example.com",
            "maricopa.api.bearer_token": "test_token",
            "MARICOPA_API_KEY": "test_token",
        }.get(key, default)
        
        config.get_typed = Mock(side_effect=lambda key, type_hint, default=None: {
            "maricopa.collection": {},
            "maricopa.collection.batch_size": 100,
            "maricopa.collection.max_retries": 3,
            "maricopa.collection.retry_delay_seconds": 5,
        }.get(key, default))
        
        return config
    
    @pytest.fixture
    def foundation_repository(self):
        """Create real foundation PropertyRepository."""
        repo = Mock(spec=PropertyRepository)
        repo.find_updated_since.return_value = []
        repo.find_by_id.return_value = None
        repo.save.return_value = True
        return repo
    
    def test_foundation_logger_integration(self, foundation_config, foundation_repository):
        """Test that collector uses foundation logging correctly."""
        with patch('phoenix_real_estate.foundation.logging.factory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            collector = MaricopaAPICollector(
                config=foundation_config,
                repository=foundation_repository,
                logger_name="test.collector"
            )
            
            # Verify logger was created with correct name
            mock_get_logger.assert_called_with("test.collector")
            
            # Verify logger is used
            assert collector.logger == mock_logger
            mock_logger.info.assert_called()
    
    def test_foundation_exception_hierarchy(self, foundation_config, foundation_repository):
        """Test proper use of foundation exception hierarchy."""
        collector = MaricopaAPICollector(foundation_config, foundation_repository)
        
        # Mock client to raise an error
        collector.client.search_properties = Mock(
            side_effect=Exception("API Error")
        )
        
        # Should wrap in DataCollectionError
        with pytest.raises(DataCollectionError) as exc_info:
            collector.collect(search_params={"zip_codes": ["85001"]})
        
        # Check exception details
        assert "Collection operation 'collect' failed" in str(exc_info.value)
        assert exc_info.value.context["collector"] == "MaricopaAPICollector"
        assert exc_info.value.original_error is not None
    
    def test_foundation_config_integration(self, foundation_repository):
        """Test configuration provider integration."""
        # Test missing required config
        bad_config = Mock(spec=ConfigProvider)
        bad_config.get.return_value = None
        bad_config.get_typed = Mock(return_value={})
        
        collector = MaricopaAPICollector(bad_config, foundation_repository)
        
        with pytest.raises(ConfigurationError) as exc_info:
            collector.validate_config()
        
        assert "Missing required configuration fields" in str(exc_info.value)
    
    def test_foundation_repository_integration(self, foundation_config):
        """Test repository integration for data storage."""
        repo = Mock(spec=PropertyRepository)
        repo.find_by_id.return_value = None
        repo.save.return_value = True
        repo.find_updated_since.return_value = []
        
        collector = MaricopaAPICollector(foundation_config, repo)
        
        # Mock successful collection
        collector.client.search_properties = Mock(return_value=[
            {"property_id": "TEST123", "address": "123 Test St"}
        ])
        
        collector.adapter.transform_batch = Mock(return_value=[{
            "property_id": "TEST123",
            "address": {"street": "123 Test St", "city": "Phoenix", "zip": "85001"},
            "last_updated": datetime.now().isoformat()
        }])
        
        # Collect and save
        results = collector.collect(
            search_params={"zip_codes": ["85001"]},
            save_to_repository=True
        )
        
        # Verify repository was called
        repo.save.assert_called_once()
        saved_data = repo.save.call_args[0][0]
        assert saved_data["property_id"] == "TEST123"


class TestEpic3OrchestrationInterface:
    """Test Epic 3 orchestration interface readiness."""
    
    @pytest.fixture
    def orchestration_collector(self, foundation_config, foundation_repository):
        """Create collector for orchestration testing."""
        return MaricopaAPICollector(foundation_config, foundation_repository)
    
    def test_strategy_pattern_implementation(self, orchestration_collector):
        """Test that collector implements DataCollector strategy pattern."""
        assert isinstance(orchestration_collector, DataCollector)
        assert hasattr(orchestration_collector, 'collect')
        assert hasattr(orchestration_collector, 'validate_config')
        assert hasattr(orchestration_collector, 'get_collection_status')
    
    @pytest.mark.asyncio
    async def test_async_zipcode_collection(self, orchestration_collector):
        """Test async interface for zipcode collection."""
        # Mock async client method
        orchestration_collector.client.search_by_zipcode = AsyncMock(
            return_value=[
                {"property_id": "PROP1", "zip": "85001"},
                {"property_id": "PROP2", "zip": "85001"}
            ]
        )
        
        # Test async collection
        results = await orchestration_collector.collect_zipcode("85001")
        
        assert len(results) == 2
        assert results[0]["property_id"] == "PROP1"
        
        # Verify logging includes orchestration context
        orchestration_collector.logger.info.assert_called()
        call_args = orchestration_collector.logger.info.call_args
        assert "source" in call_args[1]["extra"]
        assert call_args[1]["extra"]["source"] == "maricopa_api"
    
    @pytest.mark.asyncio
    async def test_property_adaptation(self, orchestration_collector):
        """Test property adaptation for orchestration pipeline."""
        raw_data = {
            "property_id": "TEST123",
            "address": "123 Test St",
            "city": "Phoenix",
            "zip": "85001",
            "beds": 3,
            "baths": 2,
            "sqft": 1500
        }
        
        # Mock adapter
        orchestration_collector.adapter.transform = Mock(return_value={
            "property_id": "TEST123",
            "address": {"street": "123 Test St", "city": "Phoenix", "zip": "85001"},
            "features": {"beds": 3, "baths": 2, "sqft": 1500},
            "last_updated": datetime.now().isoformat()
        })
        
        # Mock validator
        orchestration_collector.validator.validate_property = Mock(return_value=True)
        
        # Test adaptation
        property_obj = await orchestration_collector.adapt_property(raw_data)
        
        assert isinstance(property_obj, Property)
        assert property_obj.property_id == "TEST123"
    
    def test_source_identification(self, orchestration_collector):
        """Test source name for orchestration tracking."""
        assert orchestration_collector.get_source_name() == "maricopa_api"


class TestEpic4MonitoringIntegration:
    """Test Epic 4 monitoring and quality analysis integration."""
    
    def test_observer_pattern_integration(self, foundation_config, foundation_repository):
        """Test rate limiter observer pattern."""
        collector = MaricopaAPICollector(foundation_config, foundation_repository)
        
        # Create observer
        observer_called = {"request": False, "limit": False}
        
        class TestObserver:
            async def on_request_made(self, source, timestamp):
                observer_called["request"] = True
            
            async def on_rate_limit_hit(self, source, wait_time):
                observer_called["limit"] = True
            
            async def on_rate_limit_reset(self, source):
                pass
        
        # Add observer
        observer = TestObserver()
        collector.client.rate_limiter.add_observer(observer)
        
        # Make requests to trigger observer
        async def test_observer():
            # Make requests until rate limit hit
            for i in range(20):
                await collector.client.rate_limiter.wait_if_needed("test")
            
            return observer_called
        
        result = asyncio.run(test_observer())
        assert result["request"] is True  # At least one request made
    
    def test_metrics_collection(self, foundation_config, foundation_repository):
        """Test comprehensive metrics collection."""
        collector = MaricopaAPICollector(foundation_config, foundation_repository)
        
        # Set some metrics
        collector.total_collected = 100
        collector.total_saved = 95
        collector.total_errors = 2
        collector.collection_start_time = datetime.now()
        
        # Get metrics
        metrics = collector.get_collection_metrics()
        
        # Verify metrics structure
        assert "collection_metrics" in metrics
        assert metrics["collection_metrics"]["total_collected"] == 100
        assert metrics["collection_metrics"]["total_saved"] == 95
        assert metrics["collection_metrics"]["total_errors"] == 2
        assert "collection_duration_seconds" in metrics["collection_metrics"]
        assert "collection_rate_per_second" in metrics["collection_metrics"]


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_collection_workflow(self, foundation_config, foundation_repository):
        """Test complete workflow from API request to repository storage."""
        collector = MaricopaAPICollector(foundation_config, foundation_repository)
        
        # Mock the entire pipeline
        raw_response = [
            {
                "property_id": "PROP123",
                "address": "123 Main St",
                "city": "Phoenix",
                "zip": "85001",
                "beds": 3,
                "baths": 2
            }
        ]
        
        transformed_data = [{
            "property_id": "PROP123",
            "address": {"street": "123 Main St", "city": "Phoenix", "zip": "85001"},
            "features": {"beds": 3, "baths": 2},
            "last_updated": datetime.now().isoformat()
        }]
        
        # Mock client
        collector.client.search_properties = Mock(return_value=raw_response)
        
        # Mock adapter
        collector.adapter.transform_batch = Mock(return_value=transformed_data)
        
        # Run collection
        results = collector.collect(
            search_params={"zip_codes": ["85001"]},
            save_to_repository=True
        )
        
        # Verify complete flow
        assert len(results) == 1
        assert results[0]["property_id"] == "PROP123"
        
        # Verify repository save was called
        foundation_repository.save.assert_called_once()
        
        # Verify metrics updated
        assert collector.total_collected == 1
        assert collector.total_saved == 1
    
    def test_error_recovery_workflow(self, foundation_config, foundation_repository):
        """Test error handling and recovery through the workflow."""
        collector = MaricopaAPICollector(foundation_config, foundation_repository)
        
        # Set up retry scenario
        call_count = 0
        
        def mock_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary API error")
            return [{"property_id": "SUCCESS"}]
        
        collector.client.search_properties = Mock(side_effect=mock_search)
        collector.adapter.transform_batch = Mock(return_value=[{
            "property_id": "SUCCESS",
            "address": {"street": "123 Test", "city": "Phoenix", "zip": "85001"},
            "last_updated": datetime.now().isoformat()
        }])
        
        # Should succeed after retries
        results = collector.collect(search_params={"zip_codes": ["85001"]})
        
        assert len(results) == 1
        assert results[0]["property_id"] == "SUCCESS"
        assert call_count == 3  # Two failures + one success
        assert collector.total_errors == 2  # Two errors recorded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])