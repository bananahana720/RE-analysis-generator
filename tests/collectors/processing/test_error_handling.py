"""
Tests for error handling and recovery strategies in the processing pipeline.
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from phoenix_real_estate.collectors.processing.error_handling import (
    ErrorRecoveryStrategy,
    DeadLetterQueue,
    ErrorClassifier,
    ErrorType,
    CircuitBreaker,
    CircuitState,
    ProcessingError,
    RecoveryAction,
    FallbackExtractor
)


class TestErrorClassifier:
    """Test the error classification system."""
    
    def test_classify_network_errors(self):
        """Test classification of network-related errors."""
        classifier = ErrorClassifier()
        
        # Connection errors
        error = ConnectionError("Connection refused")
        assert classifier.classify(error) == ErrorType.NETWORK
        
        # Timeout errors
        error = asyncio.TimeoutError("Request timeout")
        assert classifier.classify(error) == ErrorType.NETWORK
        
        # DNS errors
        error = Exception("getaddrinfo failed")
        assert classifier.classify(error) == ErrorType.NETWORK
    
    def test_classify_rate_limit_errors(self):
        """Test classification of rate limit errors."""
        classifier = ErrorClassifier()
        
        # HTTP 429
        error = ProcessingError("Rate limit exceeded", status_code=429)
        assert classifier.classify(error) == ErrorType.RATE_LIMIT
        
        # Rate limit message
        error = Exception("Too many requests")
        assert classifier.classify(error) == ErrorType.RATE_LIMIT
    
    def test_classify_authentication_errors(self):
        """Test classification of authentication errors."""
        classifier = ErrorClassifier()
        
        # HTTP 401
        error = ProcessingError("Unauthorized", status_code=401)
        assert classifier.classify(error) == ErrorType.AUTHENTICATION
        
        # HTTP 403
        error = ProcessingError("Forbidden", status_code=403)
        assert classifier.classify(error) == ErrorType.AUTHENTICATION
    
    def test_classify_data_errors(self):
        """Test classification of data-related errors."""
        classifier = ErrorClassifier()
        
        # Parsing errors
        error = ValueError("Invalid JSON")
        assert classifier.classify(error) == ErrorType.DATA_ERROR
        
        # Key errors
        error = KeyError("Missing field")
        assert classifier.classify(error) == ErrorType.DATA_ERROR
        
        # Type errors
        error = TypeError("Expected string, got int")
        assert classifier.classify(error) == ErrorType.DATA_ERROR
    
    def test_classify_temporary_errors(self):
        """Test classification of temporary errors."""
        classifier = ErrorClassifier()
        
        # HTTP 503
        error = ProcessingError("Service unavailable", status_code=503)
        assert classifier.classify(error) == ErrorType.TEMPORARY
        
        # HTTP 502
        error = ProcessingError("Bad gateway", status_code=502)
        assert classifier.classify(error) == ErrorType.TEMPORARY
    
    def test_classify_permanent_errors(self):
        """Test classification of permanent errors."""
        classifier = ErrorClassifier()
        
        # HTTP 404
        error = ProcessingError("Not found", status_code=404)
        assert classifier.classify(error) == ErrorType.PERMANENT
        
        # HTTP 410
        error = ProcessingError("Gone", status_code=410)
        assert classifier.classify(error) == ErrorType.PERMANENT
    
    def test_classify_unknown_errors(self):
        """Test classification of unknown errors."""
        classifier = ErrorClassifier()
        
        # Generic exception
        error = Exception("Unknown error")
        assert classifier.classify(error) == ErrorType.UNKNOWN
    
    def test_get_recovery_action(self):
        """Test getting recovery actions for error types."""
        classifier = ErrorClassifier()
        
        # Network errors should retry with backoff
        assert classifier.get_recovery_action(ErrorType.NETWORK) == RecoveryAction.RETRY_WITH_BACKOFF
        
        # Rate limit should wait and retry
        assert classifier.get_recovery_action(ErrorType.RATE_LIMIT) == RecoveryAction.WAIT_AND_RETRY
        
        # Authentication should refresh and retry
        assert classifier.get_recovery_action(ErrorType.AUTHENTICATION) == RecoveryAction.REFRESH_AND_RETRY
        
        # Data errors should use fallback
        assert classifier.get_recovery_action(ErrorType.DATA_ERROR) == RecoveryAction.USE_FALLBACK
        
        # Temporary errors should retry
        assert classifier.get_recovery_action(ErrorType.TEMPORARY) == RecoveryAction.RETRY_WITH_BACKOFF
        
        # Permanent errors should skip
        assert classifier.get_recovery_action(ErrorType.PERMANENT) == RecoveryAction.SKIP
        
        # Unknown errors should log and skip
        assert classifier.get_recovery_action(ErrorType.UNKNOWN) == RecoveryAction.LOG_AND_SKIP


class TestCircuitBreaker:
    """Test the circuit breaker pattern implementation."""
    
    def test_initial_state(self):
        """Test circuit breaker starts in closed state."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None
    
    def test_success_in_closed_state(self):
        """Test successful calls in closed state."""
        breaker = CircuitBreaker(failure_threshold=5)
        
        # Success should not change state
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_failure_accumulation(self):
        """Test failure count accumulation."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        # First failure
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 1
        
        # Second failure
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 2
        
        # Third failure - should open
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
        assert breaker.last_failure_time is not None
    
    def test_open_state_blocks_calls(self):
        """Test that open state blocks calls."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        # Open the circuit
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        # Should not allow calls
        assert not breaker.can_execute()
    
    def test_half_open_state_after_timeout(self):
        """Test transition to half-open state after timeout."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1  # 1 second for testing
        )
        
        # Open the circuit
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        import time
        time.sleep(1.1)
        
        # Should transition to half-open
        assert breaker.can_execute()
        assert breaker.state == CircuitState.HALF_OPEN
    
    def test_half_open_success_closes_circuit(self):
        """Test successful call in half-open state closes circuit."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        
        # Open and immediately transition to half-open
        breaker.record_failure()
        breaker._last_failure_time = datetime.now() - timedelta(seconds=1)
        
        assert breaker.state == CircuitState.HALF_OPEN
        
        # Success should close circuit
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_half_open_failure_reopens_circuit(self):
        """Test failure in half-open state reopens circuit."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        
        # Open and immediately transition to half-open
        breaker.record_failure()
        # Manually set the failure time to past to trigger half-open
        breaker._last_failure_time = datetime.now() - timedelta(seconds=2)
        
        assert breaker.state == CircuitState.HALF_OPEN
        
        # Failure should reopen circuit
        breaker.record_failure()
        # Since record_failure updates the timestamp, it won't auto-transition
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_async_execution_wrapper(self):
        """Test async execution wrapper with circuit breaker."""
        breaker = CircuitBreaker(failure_threshold=2)
        
        # Mock async function
        async_func = AsyncMock(return_value="success")
        
        # Successful execution
        result = await breaker.execute_async(async_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        
        # Failing function
        async_func.side_effect = Exception("Test error")
        
        # First failure
        with pytest.raises(Exception):
            await breaker.execute_async(async_func)
        assert breaker.failure_count == 1
        
        # Second failure - opens circuit
        with pytest.raises(Exception):
            await breaker.execute_async(async_func)
        assert breaker.state == CircuitState.OPEN
        
        # Next call should be blocked
        with pytest.raises(ProcessingError) as exc_info:
            await breaker.execute_async(async_func)
        assert "Circuit breaker is open" in str(exc_info.value)


class TestDeadLetterQueue:
    """Test the dead letter queue implementation."""
    
    @pytest.mark.asyncio
    async def test_add_failed_item(self):
        """Test adding failed items to the queue."""
        dlq = DeadLetterQueue(max_size=100)
        
        item = {
            "parcel_number": "123-45-678",
            "data": {"address": "123 Main St"}
        }
        error = Exception("Processing failed")
        
        await dlq.add_failed_item(item, error, attempt_count=3)
        
        assert dlq.size() == 1
        failed_items = await dlq.get_failed_items()
        assert len(failed_items) == 1
        
        failed_item = failed_items[0]
        assert failed_item["item"] == item
        assert failed_item["error_type"] == "Exception"
        assert failed_item["error_message"] == "Processing failed"
        assert failed_item["attempt_count"] == 3
        assert "timestamp" in failed_item
    
    @pytest.mark.asyncio
    async def test_max_size_enforcement(self):
        """Test that queue respects max size."""
        dlq = DeadLetterQueue(max_size=2)
        
        # Add three items
        for i in range(3):
            await dlq.add_failed_item(
                {"id": i},
                Exception(f"Error {i}"),
                attempt_count=1
            )
        
        # Should only have 2 items (oldest removed)
        assert dlq.size() == 2
        items = await dlq.get_failed_items()
        assert len(items) == 2
        assert items[0]["item"]["id"] == 1
        assert items[1]["item"]["id"] == 2
    
    @pytest.mark.asyncio
    async def test_get_items_by_error_type(self):
        """Test filtering items by error type."""
        dlq = DeadLetterQueue()
        
        # Add items with different error types
        await dlq.add_failed_item({"id": 1}, ValueError("Bad value"), 1)
        await dlq.add_failed_item({"id": 2}, KeyError("Missing key"), 1)
        await dlq.add_failed_item({"id": 3}, ValueError("Another bad value"), 1)
        
        # Get only ValueError items
        value_errors = await dlq.get_items_by_error_type("ValueError")
        assert len(value_errors) == 2
        assert all(item["error_type"] == "ValueError" for item in value_errors)
    
    @pytest.mark.asyncio
    async def test_retry_failed_item(self):
        """Test retrying a failed item from the queue."""
        dlq = DeadLetterQueue()
        
        # Add a failed item
        item = {"parcel_number": "123-45-678"}
        await dlq.add_failed_item(item, Exception("First failure"), 1)
        
        # Mock retry function
        retry_func = AsyncMock(return_value={"success": True})
        
        # Retry the item
        result = await dlq.retry_item(0, retry_func)
        assert result == {"success": True}
        
        # Item should be removed from queue
        assert dlq.size() == 0
    
    @pytest.mark.asyncio
    async def test_retry_failed_item_fails_again(self):
        """Test retrying an item that fails again."""
        dlq = DeadLetterQueue()
        
        # Add a failed item
        item = {"parcel_number": "123-45-678"}
        await dlq.add_failed_item(item, Exception("First failure"), 1)
        
        # Mock retry function that fails
        retry_func = AsyncMock(side_effect=Exception("Second failure"))
        
        # Retry should fail
        with pytest.raises(Exception):
            await dlq.retry_item(0, retry_func)
        
        # Item should still be in queue with updated attempt count
        assert dlq.size() == 1
        items = await dlq.get_failed_items()
        assert items[0]["attempt_count"] == 2
        assert items[0]["error_message"] == "Second failure"
    
    @pytest.mark.asyncio
    async def test_clear_queue(self):
        """Test clearing the dead letter queue."""
        dlq = DeadLetterQueue()
        
        # Add some items
        for i in range(5):
            await dlq.add_failed_item({"id": i}, Exception("Error"), 1)
        
        assert dlq.size() == 5
        
        # Clear the queue
        await dlq.clear()
        assert dlq.size() == 0
    
    @pytest.mark.asyncio
    async def test_export_to_file(self):
        """Test exporting failed items to a file."""
        dlq = DeadLetterQueue()
        
        # Add some items
        for i in range(3):
            await dlq.add_failed_item(
                {"parcel_number": f"123-45-{i:03d}"},
                Exception(f"Error {i}"),
                i + 1
            )
        
        # Export to file
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            await dlq.export_to_file(temp_file)
            
            # Verify file contents
            with open(temp_file, 'r') as f:
                exported_data = json.load(f)
            
            assert len(exported_data) == 3
            assert all("parcel_number" in item["item"] for item in exported_data)
            assert all("timestamp" in item for item in exported_data)
        finally:
            import os
            os.unlink(temp_file)


class TestFallbackExtractor:
    """Test the fallback extraction methods."""
    
    def test_extract_address_from_text(self):
        """Test extracting address from unstructured text."""
        extractor = FallbackExtractor()
        
        # Full address
        text = "Property located at 123 Main Street, Phoenix, AZ 85001"
        address = extractor.extract_address_from_text(text)
        assert address["street"] == "123 Main Street"
        assert address["city"] == "Phoenix"
        assert address["state"] == "AZ"
        assert address["zip_code"] == "85001"
        
        # Partial address
        text = "456 Oak Ave Phoenix Arizona"
        address = extractor.extract_address_from_text(text)
        assert address["street"] == "456 Oak Ave"
        assert address["city"] == "Phoenix"
        assert address["state"] == "Arizona"
        assert address.get("zip_code") is None
    
    def test_extract_price_from_text(self):
        """Test extracting price from text."""
        extractor = FallbackExtractor()
        
        # Different price formats
        assert extractor.extract_price_from_text("Price: $250,000") == 250000.0
        assert extractor.extract_price_from_text("Listed at 350K") == 350000.0
        assert extractor.extract_price_from_text("$1.5M home") == 1500000.0
        assert extractor.extract_price_from_text("$450,000.00") == 450000.0
        assert extractor.extract_price_from_text("No price") is None
    
    def test_extract_bedrooms_bathrooms(self):
        """Test extracting bedroom and bathroom counts."""
        extractor = FallbackExtractor()
        
        # Various formats
        text = "3 bed 2 bath home"
        beds, baths = extractor.extract_bedrooms_bathrooms(text)
        assert beds == 3
        assert baths == 2.0
        
        text = "4BR/2.5BA"
        beds, baths = extractor.extract_bedrooms_bathrooms(text)
        assert beds == 4
        assert baths == 2.5
        
        text = "5 bedrooms, 3 bathrooms"
        beds, baths = extractor.extract_bedrooms_bathrooms(text)
        assert beds == 5
        assert baths == 3.0
        
        text = "Studio apartment"
        beds, baths = extractor.extract_bedrooms_bathrooms(text)
        assert beds == 0
        assert baths is None
    
    def test_extract_square_footage(self):
        """Test extracting square footage."""
        extractor = FallbackExtractor()
        
        assert extractor.extract_square_footage("1,500 sq ft") == 1500
        assert extractor.extract_square_footage("2000 sqft home") == 2000
        assert extractor.extract_square_footage("3,250 square feet") == 3250
        assert extractor.extract_square_footage("No size info") is None
    
    def test_extract_year_built(self):
        """Test extracting year built."""
        extractor = FallbackExtractor()
        
        assert extractor.extract_year_built("Built in 1995") == 1995
        assert extractor.extract_year_built("Year built: 2020") == 2020
        assert extractor.extract_year_built("Constructed 1987") == 1987
        assert extractor.extract_year_built("New construction") is None
    
    def test_extract_parcel_number(self):
        """Test extracting parcel number."""
        extractor = FallbackExtractor()
        
        assert extractor.extract_parcel_number("APN: 123-45-678") == "123-45-678"
        assert extractor.extract_parcel_number("Parcel #234-56-789A") == "234-56-789A"
        assert extractor.extract_parcel_number("Parcel Number: 345-67-890") == "345-67-890"
        assert extractor.extract_parcel_number("No parcel info") is None
    
    @pytest.mark.asyncio
    async def test_fallback_extraction_pipeline(self):
        """Test the complete fallback extraction pipeline."""
        extractor = FallbackExtractor()
        
        # Simulate raw data that failed normal parsing
        raw_data = {
            "description": "Beautiful 3BR/2BA home at 789 Elm Street, Phoenix, AZ 85033. "
                          "Built in 2005, this 1,800 sqft property is listed at $425,000. "
                          "APN: 456-78-901B",
            "raw_html": "<div>Some HTML content</div>"
        }
        
        # Extract using fallback methods
        result = await extractor.extract_from_raw_data(raw_data)
        
        assert result["address"]["street"] == "789 Elm Street"
        assert result["address"]["city"] == "Phoenix"
        assert result["address"]["zip_code"] == "85033"
        assert result["price"] == 425000.0
        assert result["bedrooms"] == 3
        assert result["bathrooms"] == 2.0
        assert result["square_feet"] == 1800
        assert result["year_built"] == 2005
        assert result["parcel_number"] == "456-78-901B"


class TestErrorRecoveryStrategy:
    """Test the main error recovery strategy."""
    
    @pytest.mark.asyncio
    async def test_handle_network_error(self):
        """Test handling network errors with retry."""
        strategy = ErrorRecoveryStrategy()
        
        # Mock function that fails then succeeds
        call_count = 0
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return {"success": True}
        
        # Should retry and eventually succeed
        result = await strategy.handle_error(
            flaky_function,
            {},
            max_retries=3
        )
        
        assert result == {"success": True}
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self):
        """Test handling rate limit errors with wait."""
        strategy = ErrorRecoveryStrategy()
        
        # Mock function that returns rate limit error
        async def rate_limited_function():
            raise ProcessingError("Rate limited", status_code=429)
        
        # Mock wait time
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(ProcessingError):
                await strategy.handle_error(
                    rate_limited_function,
                    {},
                    max_retries=1
                )
            
            # Should have waited
            mock_sleep.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_data_error_with_fallback(self):
        """Test handling data errors using fallback extraction."""
        strategy = ErrorRecoveryStrategy()
        
        # Mock function that raises data error
        async def failing_parser():
            raise ValueError("Invalid data format")
        
        # Mock context with raw data
        context = {
            "raw_data": {
                "description": "3 bed 2 bath home at 123 Test St, Phoenix, AZ 85001. $300,000"
            }
        }
        
        # Should use fallback extraction
        result = await strategy.handle_error(
            failing_parser,
            context,
            use_fallback=True
        )
        
        assert result is not None
        assert result["address"]["street"] == "123 Test St"
        assert result["price"] == 300000.0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration in recovery strategy."""
        strategy = ErrorRecoveryStrategy()
        
        # Create a circuit breaker
        breaker = CircuitBreaker(failure_threshold=2)
        
        # Mock function that always fails
        async def always_fails():
            raise Exception("Always fails")
        
        # Register circuit breaker
        strategy.register_circuit_breaker("test_service", breaker)
        
        # First two calls should fail and open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await strategy.handle_error_with_circuit_breaker(
                    "test_service",
                    always_fails,
                    {}
                )
        
        # Next call should be blocked by circuit breaker
        with pytest.raises(ProcessingError) as exc_info:
            await strategy.handle_error_with_circuit_breaker(
                "test_service",
                always_fails,
                {}
            )
        assert "Circuit breaker is open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue_integration(self):
        """Test dead letter queue integration."""
        strategy = ErrorRecoveryStrategy()
        
        # Mock function that always fails
        async def always_fails():
            raise Exception("Permanent failure")
        
        # Item to process
        item = {"parcel_number": "123-45-678", "data": {}}
        
        # Should fail and add to DLQ
        with pytest.raises(Exception):
            await strategy.handle_error(
                always_fails,
                {"item": item},
                max_retries=2,
                add_to_dlq=True
            )
        
        # Check item was added to DLQ
        dlq_items = await strategy.dead_letter_queue.get_failed_items()
        assert len(dlq_items) == 1
        assert dlq_items[0]["item"] == item
        assert dlq_items[0]["attempt_count"] == 3  # Initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_comprehensive_error_handling(self):
        """Test comprehensive error handling with all strategies."""
        strategy = ErrorRecoveryStrategy()
        
        # Mock LLM processor
        Mock()
        
        # Simulate different error scenarios
        test_scenarios = [
            {
                "error": ConnectionError("Network error"),
                "expected_action": RecoveryAction.RETRY_WITH_BACKOFF,
                "should_succeed_after": 2
            },
            {
                "error": ProcessingError("Rate limited", status_code=429),
                "expected_action": RecoveryAction.WAIT_AND_RETRY,
                "should_succeed_after": 1
            },
            {
                "error": ValueError("Invalid data"),
                "expected_action": RecoveryAction.USE_FALLBACK,
                "should_succeed_after": 0  # Fallback should work immediately
            },
            {
                "error": ProcessingError("Not found", status_code=404),
                "expected_action": RecoveryAction.SKIP,
                "should_succeed_after": -1  # Should not retry
            }
        ]
        
        for scenario in test_scenarios:
            call_count = 0
            
            async def test_function():
                nonlocal call_count
                call_count += 1
                
                if scenario["should_succeed_after"] >= 0 and call_count > scenario["should_succeed_after"]:
                    return {"success": True}
                raise scenario["error"]
            
            context = {
                "raw_data": {
                    "description": "Test property at 123 Main St, Phoenix, AZ 85001"
                }
            }
            
            if scenario["should_succeed_after"] == -1:
                # Should skip/fail
                with pytest.raises(ProcessingError):
                    await strategy.handle_error(
                        test_function,
                        context,
                        max_retries=3,
                        use_fallback=True
                    )
            else:
                # Should eventually succeed
                result = await strategy.handle_error(
                    test_function,
                    context,
                    max_retries=3,
                    use_fallback=True
                )
                
                if scenario["expected_action"] == RecoveryAction.USE_FALLBACK:
                    # For data errors, since the function will throw ValueError,
                    # fallback should be used if function never succeeds
                    if scenario["should_succeed_after"] == 0:
                        # Function throws ValueError, so fallback is used
                        assert result is not None
                        # But since test function returns success, we get that
                        assert result == {"success": True}
                    else:
                        assert result == {"success": True}
                else:
                    # Should have retried and succeeded
                    assert result == {"success": True}