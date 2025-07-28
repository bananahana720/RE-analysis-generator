"""
Integration tests for error handling with the LLM processing pipeline.
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from phoenix_real_estate.collectors.processing.error_handling import (
    ErrorRecoveryStrategy,
    CircuitBreaker,
    ProcessingError,
    ErrorType
)
from phoenix_real_estate.collectors.processing.llm_client import OllamaClient
from phoenix_real_estate.collectors.processing.pipeline import (
    DataProcessingPipeline,
    ProcessingResult
)
from phoenix_real_estate.foundation.config.base import ConfigProvider


class TestErrorHandlingIntegration:
    """Test error handling integration with the LLM processing pipeline."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def processing_config(self):
        """Create a processing configuration."""
        return ProcessingConfig(
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )
    
    @pytest.fixture
    def pipeline_config(self):
        """Create a pipeline configuration."""
        return PipelineConfig(
            batch_size=10,
            max_concurrent=3,
            retry_attempts=3,
            retry_delay=1.0
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_llm_failures(self, mock_llm_client, processing_config):
        """Test circuit breaker integration with LLM processor failures."""
        # Configure mock to fail
        mock_llm_client.chat.completions.create.side_effect = Exception("LLM service unavailable")
        
        # Create processor with circuit breaker
        processor = LLMProcessor(mock_llm_client, processing_config)
        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Create error recovery strategy
        error_strategy = ErrorRecoveryStrategy()
        error_strategy.register_circuit_breaker("llm_processor", circuit_breaker)
        
        # Test data
        test_data = {
            "parcel_number": "123-45-678",
            "raw_html": "<div>Test property</div>"
        }
        
        # First two failures should open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await error_strategy.handle_error_with_circuit_breaker(
                    "llm_processor",
                    lambda: processor.process_property(test_data),
                    {"item": test_data}
                )
        
        # Next call should be blocked by circuit breaker
        with pytest.raises(ProcessingError) as exc_info:
            await error_strategy.handle_error_with_circuit_breaker(
                "llm_processor",
                lambda: processor.process_property(test_data),
                {"item": test_data}
            )
        assert "Circuit breaker is open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fallback_extraction_on_llm_parse_error(self, mock_llm_client, processing_config):
        """Test fallback extraction when LLM returns unparseable data."""
        # Configure mock to return invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="This is not valid JSON"))]
        mock_llm_client.chat.completions.create.return_value = mock_response
        
        # Create processor and error strategy
        processor = LLMProcessor(mock_llm_client, processing_config)
        error_strategy = ErrorRecoveryStrategy()
        
        # Test data with fallback information
        test_data = {
            "parcel_number": "123-45-678",
            "raw_html": """
                <div class="property-details">
                    <h1>789 Oak Street, Phoenix, AZ 85033</h1>
                    <p>Price: $425,000</p>
                    <p>3 bed 2 bath</p>
                    <p>1,850 sq ft</p>
                    <p>Built in 2010</p>
                </div>
            """
        }
        
        # Process with fallback enabled
        async def process_with_error():
            # This will raise ValueError due to invalid JSON
            return await processor.process_property(test_data)
        
        result = await error_strategy.handle_error(
            process_with_error,
            {"raw_data": {"description": test_data["raw_html"]}},
            use_fallback=True
        )
        
        # Should have extracted data using fallback
        assert result is not None
        assert result["address"]["street"] == "789 Oak Street"
        assert result["address"]["city"] == "Phoenix"
        assert result["address"]["zip_code"] == "85033"
        assert result["price"] == 425000.0
        assert result["bedrooms"] == 3
        assert result["bathrooms"] == 2.0
        assert result["square_feet"] == 1850
        assert result["year_built"] == 2010
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling_with_pipeline(self, mock_llm_client, processing_config, pipeline_config):
        """Test rate limit error handling in the processing pipeline."""
        # Configure mock to return rate limit error
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ProcessingError("Rate limit exceeded", status_code=429)
            # Return valid response after rate limit clears
            return Mock(choices=[Mock(message=Mock(content='{"price": 300000}'))])
        
        mock_llm_client.chat.completions.create.side_effect = mock_create
        
        # Create pipeline with error handling
        processor = LLMProcessor(mock_llm_client, processing_config)
        pipeline = ProcessingPipeline(processor, pipeline_config)
        error_strategy = ErrorRecoveryStrategy()
        
        # Override rate limit delay for testing
        error_strategy.retry_delays[ErrorType.RATE_LIMIT] = [0.1, 0.2]
        
        # Test batch
        batch = [
            {"parcel_number": f"123-45-{i:03d}", "raw_html": f"<div>Property {i}</div>"}
            for i in range(3)
        ]
        
        # Process with error handling
        start_time = datetime.now()
        results = []
        
        for item in batch:
            result = await error_strategy.handle_error(
                lambda: processor.process_property(item),
                {"item": item},
                max_retries=3
            )
            results.append(result)
        
        # Should have retried with delays
        elapsed = (datetime.now() - start_time).total_seconds()
        assert elapsed >= 0.1  # At least one retry delay
        
        # Should eventually succeed
        assert all(r is not None for r in results)
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue_with_permanent_failures(self, mock_llm_client, processing_config):
        """Test that permanently failed items are added to dead letter queue."""
        # Configure mock to return 404 error
        mock_llm_client.chat.completions.create.side_effect = ProcessingError(
            "Property not found", status_code=404
        )
        
        # Create processor and error strategy
        processor = LLMProcessor(mock_llm_client, processing_config)
        error_strategy = ErrorRecoveryStrategy()
        
        # Test data
        test_items = [
            {"parcel_number": f"999-99-{i:03d}", "raw_html": f"<div>Missing {i}</div>"}
            for i in range(5)
        ]
        
        # Process items - all should fail permanently
        for item in test_items:
            with pytest.raises(ProcessingError):
                await error_strategy.handle_error(
                    lambda: processor.process_property(item),
                    {"item": item},
                    add_to_dlq=True
                )
        
        # Check dead letter queue
        dlq_items = await error_strategy.dead_letter_queue.get_failed_items()
        assert len(dlq_items) == 5
        assert all(item["error_message"] == "Property not found" for item in dlq_items)
        assert all(item["attempt_count"] == 1 for item in dlq_items)  # No retries for permanent errors
    
    @pytest.mark.asyncio
    async def test_error_recovery_with_full_pipeline(self, mock_llm_client, processing_config, pipeline_config):
        """Test comprehensive error recovery with the full processing pipeline."""
        # Configure mock with various failure scenarios
        call_counts = {}
        
        async def mock_create(*args, **kwargs):
            # Extract property ID from the prompt
            prompt = kwargs.get("messages", [{}])[0].get("content", "")
            parcel_num = "unknown"
            if "123-45-001" in prompt:
                parcel_num = "123-45-001"
            elif "123-45-002" in prompt:
                parcel_num = "123-45-002"
            elif "123-45-003" in prompt:
                parcel_num = "123-45-003"
            
            # Track calls per property
            call_counts[parcel_num] = call_counts.get(parcel_num, 0) + 1
            count = call_counts[parcel_num]
            
            # Different failure patterns
            if parcel_num == "123-45-001" and count <= 2:
                # Network error that recovers
                raise ConnectionError("Network timeout")
            elif parcel_num == "123-45-002" and count == 1:
                # One-time rate limit
                raise ProcessingError("Rate limited", status_code=429)
            elif parcel_num == "123-45-003":
                # Always returns invalid data
                return Mock(choices=[Mock(message=Mock(content="Not JSON"))])
            
            # Success response
            return Mock(choices=[Mock(message=Mock(content=f'{{"price": {100000 * int(parcel_num[-1])}}}'))])
        
        mock_llm_client.chat.completions.create.side_effect = mock_create
        
        # Create pipeline with error handling
        processor = LLMProcessor(mock_llm_client, processing_config)
        pipeline = ProcessingPipeline(processor, pipeline_config)
        error_strategy = ErrorRecoveryStrategy()
        
        # Configure circuit breaker
        circuit_breaker = CircuitBreaker(failure_threshold=5)
        error_strategy.register_circuit_breaker("llm_processor", circuit_breaker)
        
        # Test batch with mixed scenarios
        batch = [
            {
                "parcel_number": "123-45-001",
                "raw_html": "<div>Property with network issues</div>"
            },
            {
                "parcel_number": "123-45-002", 
                "raw_html": "<div>Property with rate limit</div>"
            },
            {
                "parcel_number": "123-45-003",
                "raw_html": "<div>Property at 456 Main St, Phoenix, AZ 85001. Price: $350,000</div>"
            }
        ]
        
        # Process batch with error handling
        results = []
        errors = []
        
        for item in batch:
            try:
                result = await error_strategy.handle_error_with_circuit_breaker(
                    "llm_processor",
                    lambda i=item: processor.process_property(i),
                    {"item": item, "raw_data": {"description": item["raw_html"]}},
                    max_retries=3,
                    use_fallback=True,
                    add_to_dlq=True
                )
                results.append(result)
            except Exception as e:
                errors.append((item["parcel_number"], str(e)))
        
        # Verify results
        assert len(results) == 3  # All should have some result
        
        # First property should succeed after retries
        assert results[0] is not None
        assert "price" in results[0] or "error" not in results[0]
        
        # Second property should succeed after rate limit
        assert results[1] is not None
        assert "price" in results[1] or "error" not in results[1]
        
        # Third property should use fallback
        assert results[2] is not None
        if "extraction_method" in results[2]:
            assert results[2]["extraction_method"] == "fallback"
            assert results[2]["price"] == 350000.0
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_mixed_errors(self, mock_llm_client, processing_config, pipeline_config):
        """Test batch processing with various error types."""
        # Track which properties have been called
        processed = set()
        
        async def mock_create(*args, **kwargs):
            prompt = kwargs.get("messages", [{}])[0].get("content", "")
            
            # Extract parcel number
            for i in range(10):
                if f"123-45-{i:03d}" in prompt:
                    parcel_num = f"123-45-{i:03d}"
                    processed.add(parcel_num)
                    
                    # Different responses based on parcel
                    if i % 4 == 0:
                        # Network error
                        raise ConnectionError("Connection failed")
                    elif i % 4 == 1:
                        # Rate limit
                        raise ProcessingError("Rate limited", status_code=429)
                    elif i % 4 == 2:
                        # Invalid response
                        return Mock(choices=[Mock(message=Mock(content="Invalid"))])
                    else:
                        # Success
                        return Mock(choices=[Mock(message=Mock(content=f'{{"price": {100000 + i * 10000}}}'))])
            
            return Mock(choices=[Mock(message=Mock(content='{"price": 100000}'))])
        
        mock_llm_client.chat.completions.create.side_effect = mock_create
        
        # Create components
        processor = LLMProcessor(mock_llm_client, processing_config)
        pipeline = ProcessingPipeline(processor, pipeline_config)
        error_strategy = ErrorRecoveryStrategy()
        
        # Reduce delays for testing
        error_strategy.retry_delays[ErrorType.NETWORK] = [0.01, 0.02]
        error_strategy.retry_delays[ErrorType.RATE_LIMIT] = [0.01]
        
        # Create batch
        batch = [
            {
                "parcel_number": f"123-45-{i:03d}",
                "raw_html": f"<div>Property {i} at {100+i} Main St, Phoenix, AZ 85001. ${100000 + i * 10000}</div>"
            }
            for i in range(10)
        ]
        
        # Process batch
        results = await pipeline.process_batch(batch)
        
        # All items should have been attempted
        assert len(results) == 10
        
        # Check that appropriate error handling occurred
        success_count = sum(1 for r in results if r and "error" not in r)
        assert success_count >= 3  # At least the successful ones
        
        # Verify fallback was used for invalid responses
        fallback_count = sum(1 for r in results if r and r.get("extraction_method") == "fallback")
        assert fallback_count >= 1