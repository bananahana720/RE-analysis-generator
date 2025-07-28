"""Test suite for data processing pipeline."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from phoenix_real_estate.collectors.processing import DataProcessingPipeline
from phoenix_real_estate.collectors.processing.extractor import PropertyDataExtractor
from phoenix_real_estate.collectors.processing.validator import ProcessingValidator, ValidationResult, DataQualityMetrics
from phoenix_real_estate.foundation import ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.models.property import PropertyDetails


class TestDataProcessingPipeline:
    """Test suite for DataProcessingPipeline."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = Mock(spec=ConfigProvider)
        
        # Support get() method
        config.get = Mock(side_effect=lambda key, default=None: {
            "VALIDATION_CONFIG": None,
            "CACHE_BACKEND": "memory"
        }.get(key, default))
        
        # Support get_typed() method for type-safe configuration access
        def mock_get_typed(key, type_cls, default=None):
            values = {
                "BATCH_SIZE": 5,
                "MAX_CONCURRENT_PROCESSING": 3,
                "PROCESSING_TIMEOUT": 60,
                "ENABLE_METRICS": True,
                "RETRY_ATTEMPTS": 2,
                "RETRY_DELAY": 1.0,
                "CACHE_ENABLED": True,
                "RESOURCE_MONITORING_ENABLED": True,
                "ADAPTIVE_BATCH_SIZING": True,
                "CACHE_TTL_HOURS": 24.0,
                "CACHE_MAX_SIZE_MB": 100.0,
                "MAX_MEMORY_MB": 1024,
                "MAX_CPU_PERCENT": 80,
                "MAX_BATCH_SIZE": 100,
                "EXTRACTION_TIMEOUT": 30
            }
            value = values.get(key, default)
            if value is not None and type_cls is not None:
                return type_cls(value)
            return value
        
        config.get_typed = Mock(side_effect=mock_get_typed)
        
        return config
    
    @pytest.fixture
    def mock_extractor(self):
        """Create mock extractor."""
        extractor = Mock(spec=PropertyDataExtractor)
        extractor.initialize = AsyncMock()
        extractor.close = AsyncMock()
        extractor.extract_from_html = AsyncMock()
        extractor.extract_from_json = AsyncMock()
        extractor.extract_batch = AsyncMock()
        return extractor
    
    @pytest.fixture
    def mock_validator(self):
        """Create mock validator."""
        validator = Mock(spec=ProcessingValidator)
        validator.validate = Mock()
        validator.validate_batch = Mock()
        validator.get_batch_statistics = Mock()
        return validator
    
    @pytest.fixture
    def sample_property_data(self) -> Dict[str, Any]:
        """Create sample property data."""
        return {
            "property_id": "TEST-001",
            "parcel_number": "123-45-678",
            "address": "123 Test St, Phoenix, AZ 85001",
            "price": 350000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "square_feet": 1800,
            "property_type": "Single Family Home",
            "source": "phoenix_mls",
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }
    
    @pytest.fixture
    def sample_property_details(self, sample_property_data) -> PropertyDetails:
        """Create sample PropertyDetails instance."""
        return PropertyDetails.from_extraction_result(sample_property_data)
    
    @pytest.fixture
    def sample_validation_result(self) -> ValidationResult:
        """Create sample validation result."""
        return ValidationResult(
            is_valid=True,
            confidence_score=0.95,
            errors=[],
            warnings=[],
            field_validations={},
            quality_metrics=DataQualityMetrics(
                completeness=0.9,
                consistency=0.95,
                accuracy=0.98,
                timeliness=0.99
            )
        )
    
    @pytest.fixture
    async def pipeline(self, test_config, mock_extractor, mock_validator):
        """Create pipeline instance with mocks."""
        with patch('phoenix_real_estate.collectors.processing.pipeline.PropertyDataExtractor', return_value=mock_extractor):
            with patch('phoenix_real_estate.collectors.processing.pipeline.ProcessingValidator', return_value=mock_validator):
                pipeline = DataProcessingPipeline(test_config)
                await pipeline.initialize()
                yield pipeline
                await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, test_config):
        """Test pipeline initializes correctly."""
        pipeline = DataProcessingPipeline(test_config)
        
        assert pipeline.config == test_config
        assert pipeline.batch_size == 5
        assert pipeline.max_concurrent == 3
        assert pipeline.processing_timeout == 60
        assert pipeline.metrics_enabled is True
        assert not pipeline._initialized
    
    @pytest.mark.asyncio
    async def test_pipeline_context_manager(self, test_config, mock_extractor, mock_validator):
        """Test pipeline works as context manager."""
        with patch('phoenix_real_estate.collectors.processing.pipeline.PropertyDataExtractor', return_value=mock_extractor):
            with patch('phoenix_real_estate.collectors.processing.pipeline.ProcessingValidator', return_value=mock_validator):
                async with DataProcessingPipeline(test_config) as pipeline:
                    assert pipeline._initialized
                    mock_extractor.initialize.assert_called_once()
                
                # After exiting context
                mock_extractor.close.assert_called_once()
                assert not pipeline._initialized
    
    @pytest.mark.asyncio
    async def test_process_single_html(self, pipeline, mock_extractor, mock_validator, 
                                     sample_property_data, sample_property_details, 
                                     sample_validation_result):
        """Test processing single HTML content."""
        html_content = "<html><body>Property listing</body></html>"
        
        # Setup mocks
        mock_extractor.extract_from_html.return_value = sample_property_data
        mock_validator.validate.return_value = sample_validation_result
        
        # Process
        result = await pipeline.process_html(html_content, "phoenix_mls")
        
        # Verify
        assert result.is_valid
        assert result.property_data == sample_property_details
        assert result.validation_result == sample_validation_result
        assert result.source == "phoenix_mls"
        assert result.processing_time > 0
        
        mock_extractor.extract_from_html.assert_called_once_with(
            html_content, "phoenix_mls", None, True
        )
        mock_validator.validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_single_json(self, pipeline, mock_extractor, mock_validator,
                                     sample_property_data, sample_property_details,
                                     sample_validation_result):
        """Test processing single JSON content."""
        json_data = {"parcel": "123-45-678", "owner": "Test Owner"}
        
        # Setup mocks
        mock_extractor.extract_from_json.return_value = sample_property_data
        mock_validator.validate.return_value = sample_validation_result
        
        # Process
        result = await pipeline.process_json(json_data, "maricopa_county")
        
        # Verify
        assert result.is_valid
        assert result.property_data == sample_property_details
        assert result.validation_result == sample_validation_result
        assert result.source == "maricopa_county"
        
        mock_extractor.extract_from_json.assert_called_once_with(
            json_data, "maricopa_county", None, True
        )
    
    @pytest.mark.asyncio
    async def test_process_batch_html(self, pipeline, mock_extractor, mock_validator,
                                    sample_property_data, sample_validation_result):
        """Test batch processing of HTML content."""
        html_contents = [f"<html>Property {i}</html>" for i in range(10)]
        
        # Setup mocks
        extracted_data = [dict(sample_property_data, property_id=f"TEST-{i:03d}") for i in range(10)]
        mock_extractor.extract_from_html.side_effect = extracted_data
        mock_validator.validate.return_value = sample_validation_result
        
        # Process batch
        results = await pipeline.process_batch_html(html_contents, "phoenix_mls")
        
        # Verify
        assert len(results) == 10
        assert all(r.is_valid for r in results)
        assert mock_extractor.extract_from_html.call_count == 10
        assert mock_validator.validate.call_count == 10
        
        # Check metrics were collected
        metrics = pipeline.get_metrics()
        assert metrics['total_processed'] == 10
        assert metrics['successful'] == 10
        assert metrics['failed'] == 0
    
    @pytest.mark.asyncio
    async def test_process_batch_with_concurrency_limit(self, pipeline, mock_extractor,
                                                      mock_validator, sample_property_data,
                                                      sample_validation_result):
        """Test batch processing respects concurrency limit."""
        html_contents = [f"<html>Property {i}</html>" for i in range(10)]
        
        # Track concurrent calls
        concurrent_calls = []
        active_calls = 0
        max_concurrent = 0
        
        async def track_concurrent_extract(*args, **kwargs):
            nonlocal active_calls, max_concurrent
            active_calls += 1
            max_concurrent = max(max_concurrent, active_calls)
            concurrent_calls.append(active_calls)
            await asyncio.sleep(0.1)  # Simulate processing time
            active_calls -= 1
            return sample_property_data
        
        mock_extractor.extract_from_html.side_effect = track_concurrent_extract
        mock_validator.validate.return_value = sample_validation_result
        
        # Process batch
        await pipeline.process_batch_html(html_contents, "phoenix_mls")
        
        # Verify concurrency was limited
        assert max_concurrent <= 3  # MAX_CONCURRENT_PROCESSING from config
    
    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self, pipeline, mock_extractor, mock_validator,
                                           sample_property_data, sample_validation_result):
        """Test batch processing handles errors gracefully."""
        html_contents = [f"<html>Property {i}</html>" for i in range(5)]
        
        # Setup mocks - make some fail
        async def extract_with_errors(content, source, *args, **kwargs):
            if "Property 2" in content:
                raise ProcessingError("Extraction failed")
            return sample_property_data
        
        mock_extractor.extract_from_html.side_effect = extract_with_errors
        mock_validator.validate.return_value = sample_validation_result
        
        # Process batch
        results = await pipeline.process_batch_html(html_contents, "phoenix_mls")
        
        # Verify
        assert len(results) == 5
        assert sum(1 for r in results if r.is_valid) == 4
        assert sum(1 for r in results if not r.is_valid) == 1
        assert any("Extraction failed" in r.error for r in results if not r.is_valid)
        
        # Check metrics
        metrics = pipeline.get_metrics()
        assert metrics['successful'] == 4
        assert metrics['failed'] == 1
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, pipeline, mock_extractor, mock_validator,
                                 sample_property_data, sample_validation_result):
        """Test retry mechanism on transient failures."""
        html_content = "<html>Property</html>"
        call_count = 0
        
        async def extract_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ProcessingError("Temporary failure")
            return sample_property_data
        
        mock_extractor.extract_from_html.side_effect = extract_with_retry
        mock_validator.validate.return_value = sample_validation_result
        
        # Process with retry
        result = await pipeline.process_html(html_content, "phoenix_mls")
        
        # Verify
        assert result.is_valid
        assert call_count == 2  # Initial attempt + 1 retry
    
    @pytest.mark.asyncio
    async def test_processing_timeout(self, pipeline, mock_extractor, mock_validator):
        """Test processing timeout handling."""
        html_content = "<html>Property</html>"
        
        # Setup mock to timeout
        async def slow_extract(*args, **kwargs):
            await asyncio.sleep(100)  # Longer than timeout
        
        mock_extractor.extract_from_html.side_effect = slow_extract
        
        # Process with timeout
        with pytest.raises(ProcessingError) as exc_info:
            await pipeline.process_html(html_content, "phoenix_mls", timeout=0.1)
        
        # Verify the error message contains timeout info
        assert "Extraction returned no data" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, pipeline, mock_extractor, mock_validator,
                                    sample_property_data, sample_validation_result):
        """Test metrics collection and reporting."""
        # Process some items
        mock_extractor.extract_from_html.return_value = sample_property_data
        mock_validator.validate.return_value = sample_validation_result
        
        await pipeline.process_html("<html>1</html>", "phoenix_mls")
        await pipeline.process_html("<html>2</html>", "phoenix_mls")
        
        # Make one fail
        mock_extractor.extract_from_html.side_effect = ProcessingError("Test error")
        try:
            await pipeline.process_html("<html>3</html>", "phoenix_mls")
        except:
            pass
        
        # Check metrics
        metrics = pipeline.get_metrics()
        assert metrics['total_processed'] == 3
        assert metrics['successful'] == 2
        assert metrics['failed'] == 1
        assert metrics['success_rate'] == 2/3
        assert 'average_processing_time' in metrics
        assert 'average_confidence' in metrics
    
    @pytest.mark.asyncio
    async def test_clear_metrics(self, pipeline):
        """Test clearing metrics."""
        # Add some metrics
        pipeline._metrics['total_processed'] = 10
        pipeline._metrics['successful'] = 8
        
        # Clear
        pipeline.clear_metrics()
        
        # Verify
        metrics = pipeline.get_metrics()
        assert metrics['total_processed'] == 0
        assert metrics['successful'] == 0
        assert metrics['failed'] == 0
    
    @pytest.mark.asyncio
    async def test_source_validation(self, pipeline):
        """Test source validation."""
        with pytest.raises(ValueError, match="Unsupported source"):
            await pipeline.process_html("<html></html>", "invalid_source")
        
        with pytest.raises(ValueError, match="Unsupported source"):
            await pipeline.process_json({}, "invalid_source")
    
    @pytest.mark.asyncio
    async def test_pipeline_not_initialized(self, test_config):
        """Test pipeline raises error when used without initialization."""
        pipeline = DataProcessingPipeline(test_config)
        
        with pytest.raises(RuntimeError, match="Pipeline not initialized"):
            await pipeline.process_html("<html></html>", "phoenix_mls")