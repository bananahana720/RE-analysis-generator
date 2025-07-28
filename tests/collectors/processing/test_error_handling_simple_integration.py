"""
Simple integration tests for error handling components.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock

from phoenix_real_estate.collectors.processing.error_handling import (
    ErrorRecoveryStrategy,
    CircuitBreaker,
    ProcessingError,
    ErrorType
)


class TestSimpleErrorHandlingIntegration:
    """Simple integration tests for error handling components."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_protects_service(self):
        """Test that circuit breaker protects a failing service."""
        # Create a mock service
        call_count = 0
        
        async def failing_service():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Service unavailable")
        
        # Set up error recovery with circuit breaker
        strategy = ErrorRecoveryStrategy()
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        strategy.register_circuit_breaker("test_service", breaker)
        
        # First 3 calls should fail and open the circuit
        for i in range(3):
            with pytest.raises(ConnectionError):
                await strategy.handle_error_with_circuit_breaker(
                    "test_service",
                    failing_service,
                    {},
                    max_retries=0
                )
        
        assert call_count == 3
        
        # Next call should be blocked by open circuit
        with pytest.raises(ProcessingError) as exc_info:
            await strategy.handle_error_with_circuit_breaker(
                "test_service",
                failing_service,
                {},
                max_retries=0
            )
        
        assert "Circuit breaker is open" in str(exc_info.value)
        assert call_count == 3  # Service not called
    
    @pytest.mark.asyncio
    async def test_fallback_extraction_workflow(self):
        """Test the complete fallback extraction workflow."""
        # Create test data that would fail normal parsing
        raw_property_data = {
            "html": """
                <div class="listing">
                    <h1>Beautiful Home in Phoenix</h1>
                    <p class="address">1234 Sunset Blvd, Phoenix, AZ 85033</p>
                    <span class="price">$389,900</span>
                    <div class="details">
                        <span>4 bedrooms</span>
                        <span>2.5 bathrooms</span>
                        <span>2,100 sqft</span>
                        <span>Built in 2018</span>
                    </div>
                    <div class="meta">
                        APN: 502-12-345A
                    </div>
                </div>
            """,
            "failed_parse": True
        }
        
        # Mock parser that fails
        async def failing_parser():
            raise ValueError("Failed to parse structured data")
        
        # Use error recovery with fallback
        strategy = ErrorRecoveryStrategy()
        
        result = await strategy.handle_error(
            failing_parser,
            {"raw_data": {"description": raw_property_data["html"]}},
            use_fallback=True,
            max_retries=0
        )
        
        # Verify fallback extraction worked
        assert result is not None
        assert result["extraction_method"] == "fallback"
        assert result["address"]["street"] == "1234 Sunset Blvd"
        assert result["address"]["city"] == "Phoenix"
        assert result["address"]["zip_code"] == "85033"
        assert result["price"] == 389900.0
        assert result["bedrooms"] == 4
        assert result["bathrooms"] == 2.5
        assert result["square_feet"] == 2100
        assert result["year_built"] == 2018
        assert result["parcel_number"] == "502-12-345A"
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue_workflow(self):
        """Test the dead letter queue workflow for failed items."""
        strategy = ErrorRecoveryStrategy()
        
        # Create test items
        test_items = [
            {"id": 1, "data": "item1"},
            {"id": 2, "data": "item2"},
            {"id": 3, "data": "item3"}
        ]
        
        # Mock processor that always fails
        async def always_fails():
            raise ProcessingError("Permanent failure", status_code=404)
        
        # Process items - all should fail and go to DLQ
        for item in test_items:
            with pytest.raises(ProcessingError):
                await strategy.handle_error(
                    always_fails,
                    {"item": item},
                    max_retries=1,
                    add_to_dlq=True
                )
        
        # Verify items in DLQ
        dlq_items = await strategy.dead_letter_queue.get_failed_items()
        assert len(dlq_items) == 3
        assert all(item["error_message"] == "Permanent failure" for item in dlq_items)
        
        # Test retry from DLQ
        successful_retry = AsyncMock(return_value={"success": True})
        result = await strategy.dead_letter_queue.retry_item(0, successful_retry)
        assert result == {"success": True}
        
        # Item should be removed from DLQ
        dlq_items = await strategy.dead_letter_queue.get_failed_items()
        assert len(dlq_items) == 2
    
    @pytest.mark.asyncio
    async def test_error_classification_and_recovery(self):
        """Test that different error types trigger appropriate recovery actions."""
        strategy = ErrorRecoveryStrategy()
        
        # Test scenarios with expected behaviors
        scenarios = [
            {
                "error": ConnectionError("Network error"),
                "expected_retries": 3,
                "expected_delay": True
            },
            {
                "error": ProcessingError("Rate limited", status_code=429),
                "expected_retries": 3,
                "expected_delay": True
            },
            {
                "error": ProcessingError("Not found", status_code=404),
                "expected_retries": 0,
                "expected_delay": False
            }
        ]
        
        for scenario in scenarios:
            call_count = 0
            
            async def test_func():
                nonlocal call_count
                call_count += 1
                raise scenario["error"]
            
            try:
                await strategy.handle_error(
                    test_func,
                    {},
                    max_retries=3
                )
            except Exception:
                pass
            
            # Verify retry behavior
            if scenario["expected_retries"] > 0:
                assert call_count > 1
            else:
                assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_comprehensive_error_recovery_flow(self):
        """Test a complete error recovery flow with multiple strategies."""
        strategy = ErrorRecoveryStrategy()
        
        # Register circuit breaker
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=1)
        strategy.register_circuit_breaker("api", breaker)
        
        # Mock API that has intermittent failures
        call_count = 0
        
        async def flaky_api():
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                raise ConnectionError("Network timeout")
            elif call_count == 3:
                raise ProcessingError("Rate limited", status_code=429)
            elif call_count == 4:
                # Return invalid data that needs fallback
                raise ValueError("Invalid response format")
            else:
                return {"status": "success", "data": "processed"}
        
        # Context with fallback data
        context = {
            "raw_data": {
                "description": "Property at 789 Main St, Phoenix, AZ 85001. $250,000, 3BR/2BA, 1500 sqft"
            }
        }
        
        # Process with full error recovery
        result = await strategy.handle_error_with_circuit_breaker(
            "api",
            flaky_api,
            context,
            max_retries=5,
            use_fallback=True
        )
        
        # Should eventually succeed
        assert result is not None
        assert call_count == 5  # All attempts made
        
        # Circuit should still be closed (under threshold)
        assert breaker.state.value == "closed"
    
    @pytest.mark.asyncio
    async def test_error_recovery_metrics(self):
        """Test that error recovery tracks metrics correctly."""
        strategy = ErrorRecoveryStrategy()
        
        # Track various error types
        error_counts = {
            ErrorType.NETWORK: 0,
            ErrorType.RATE_LIMIT: 0,
            ErrorType.DATA_ERROR: 0
        }
        
        test_errors = [
            ConnectionError("Network error"),
            ProcessingError("Rate limited", status_code=429),
            ValueError("Invalid data"),
            asyncio.TimeoutError("Timeout"),
            ProcessingError("Too many requests", status_code=429)
        ]
        
        for error in test_errors:
            error_type = strategy.error_classifier.classify(error)
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Verify classification
        assert error_counts[ErrorType.NETWORK] == 2  # Connection + Timeout
        assert error_counts[ErrorType.RATE_LIMIT] == 2
        assert error_counts[ErrorType.DATA_ERROR] == 1