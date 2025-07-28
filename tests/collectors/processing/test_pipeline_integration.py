"""Integration test for data processing pipeline."""

import pytest
from phoenix_real_estate.foundation import ConfigProvider
from phoenix_real_estate.collectors.processing import DataProcessingPipeline


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for the processing pipeline."""
    
    def test_pipeline_imports(self):
        """Test that pipeline can be imported."""
        from phoenix_real_estate.collectors.processing import (
            DataProcessingPipeline,
            ProcessingResult,
            OllamaClient,
            PropertyDataExtractor,
            ProcessingValidator
        )
        
        # Verify classes exist
        assert DataProcessingPipeline is not None
        assert ProcessingResult is not None
        assert OllamaClient is not None
        assert PropertyDataExtractor is not None
        assert ProcessingValidator is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_basic_functionality(self):
        """Test basic pipeline functionality with mocks."""
        from unittest.mock import Mock
        
        # Create mock config
        config = Mock(spec=ConfigProvider)
        config.settings = Mock()
        config.settings.BATCH_SIZE = 5
        config.settings.MAX_CONCURRENT_PROCESSING = 3
        config.settings.PROCESSING_TIMEOUT = 60
        config.settings.ENABLE_METRICS = True
        config.settings.RETRY_ATTEMPTS = 2
        config.settings.RETRY_DELAY = 1.0
        config.getattr = lambda name, default=None: getattr(config.settings, name, default)
        
        # Create pipeline
        pipeline = DataProcessingPipeline(config)
        
        # Verify initialization
        assert pipeline.batch_size == 5
        assert pipeline.max_concurrent == 3
        assert pipeline.metrics_enabled is True
        assert not pipeline._initialized
        
        # Test metrics
        metrics = pipeline.get_metrics()
        assert metrics['total_processed'] == 0
        assert metrics['successful'] == 0
        assert metrics['failed'] == 0
    
    def test_processing_result_dataclass(self):
        """Test ProcessingResult dataclass."""
        from phoenix_real_estate.collectors.processing import ProcessingResult
        
        # Create a result
        result = ProcessingResult(
            is_valid=True,
            source="phoenix_mls",
            processing_time=1.5,
            retry_count=0
        )
        
        # Verify attributes
        assert result.is_valid is True
        assert result.property_data is None
        assert result.validation_result is None
        assert result.source == "phoenix_mls"
        assert result.processing_time == 1.5
        assert result.error is None
        assert result.retry_count == 0
        assert isinstance(result.metadata, dict)
    
    def test_pipeline_documentation(self):
        """Test that pipeline has proper documentation."""
        from phoenix_real_estate.collectors.processing import DataProcessingPipeline
        
        # Check class docstring
        assert DataProcessingPipeline.__doc__ is not None
        assert "orchestrates" in DataProcessingPipeline.__doc__.lower()
        
        # Check key methods have docstrings
        assert DataProcessingPipeline.process_html.__doc__ is not None
        assert DataProcessingPipeline.process_json.__doc__ is not None
        assert DataProcessingPipeline.process_batch_html.__doc__ is not None
        assert DataProcessingPipeline.get_metrics.__doc__ is not None