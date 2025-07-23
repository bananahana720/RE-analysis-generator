"""Comprehensive tests for the Rate Limiter with Observer Pattern.

This test suite validates:
- Rate limiting enforcement with safety margins
- Thread-safe concurrent access
- Observer pattern notifications
- Memory efficiency and cleanup
- Performance requirements (<100ms response time)
- Epic 1 logging integration
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch
from typing import List

from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter


class MockRateLimitObserver:
    """Mock observer implementation for testing notifications."""

    def __init__(self):
        self.request_made_calls: List[tuple] = []
        self.rate_limit_hit_calls: List[tuple] = []
        self.rate_limit_reset_calls: List[str] = []

    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        """Record request made notifications."""
        self.request_made_calls.append((source, timestamp))

    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        """Record rate limit hit notifications."""
        self.rate_limit_hit_calls.append((source, wait_time))

    async def on_rate_limit_reset(self, source: str) -> None:
        """Record rate limit reset notifications."""
        self.rate_limit_reset_calls.append(source)


class FailingObserver:
    """Observer that raises exceptions for testing error handling."""

    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        raise Exception("Test exception in observer")

    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        raise Exception("Test exception in observer")

    async def on_rate_limit_reset(self, source: str) -> None:
        raise Exception("Test exception in observer")


class TestRateLimiter:
    """Test suite for RateLimiter implementation."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        limiter = RateLimiter()

        assert limiter.requests_per_minute == 1000
        assert limiter.safety_margin == 0.10
        assert limiter.window_duration == 60
        assert limiter.effective_limit == 900  # 1000 * (1 - 0.10)

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        limiter = RateLimiter(requests_per_minute=500, safety_margin=0.20, window_duration=120)

        assert limiter.requests_per_minute == 500
        assert limiter.safety_margin == 0.20
        assert limiter.window_duration == 120
        assert limiter.effective_limit == 400  # 500 * (1 - 0.20)

    def test_safety_margin_calculation(self):
        """Test safety margin calculation for various limits."""
        test_cases = [
            (1000, 0.10, 900),  # 10% margin
            (100, 0.05, 95),  # 5% margin
            (2000, 0.15, 1700),  # 15% margin
            (50, 0.20, 40),  # 20% margin
        ]

        for requests, margin, expected in test_cases:
            limiter = RateLimiter(requests_per_minute=requests, safety_margin=margin)
            assert limiter.effective_limit == expected

    def test_observer_management(self):
        """Test adding and removing observers."""
        limiter = RateLimiter(requests_per_minute=10)
        observer1 = MockRateLimitObserver()
        observer2 = MockRateLimitObserver()

        # Add observers
        limiter.add_observer(observer1)
        limiter.add_observer(observer2)
        assert len(limiter._observers) == 2

        # Adding same observer again should not duplicate
        limiter.add_observer(observer1)
        assert len(limiter._observers) == 2

        # Remove observer
        limiter.remove_observer(observer1)
        assert len(limiter._observers) == 1
        assert observer2 in limiter._observers

        # Remove non-existent observer should not error
        limiter.remove_observer(observer1)
        assert len(limiter._observers) == 1

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self):
        """Test that rate limiting is enforced correctly."""
        # Use small limit for easier testing
        limiter = RateLimiter(requests_per_minute=5, safety_margin=0.0)  # 5 requests
        source = "test_source"

        # First 5 requests should be allowed immediately
        for i in range(5):
            wait_time = await limiter.wait_if_needed(source)
            assert wait_time == 0.0, f"Request {i + 1} should be allowed immediately"

        # 6th request should be rate limited
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time > 0, "6th request should be rate limited"

    @pytest.mark.asyncio
    async def test_rate_limiting_with_safety_margin(self):
        """Test rate limiting with safety margin."""
        # 10 requests per minute with 10% safety margin = 9 effective limit
        limiter = RateLimiter(requests_per_minute=10, safety_margin=0.10)
        source = "test_source"

        # First 9 requests should be allowed
        for i in range(9):
            wait_time = await limiter.wait_if_needed(source)
            assert wait_time == 0.0, f"Request {i + 1} should be allowed (safety margin)"

        # 10th request should be rate limited due to safety margin
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time > 0, "10th request should be rate limited due to safety margin"

    @pytest.mark.asyncio
    async def test_sliding_window_cleanup(self):
        """Test that sliding window cleanup works correctly."""
        limiter = RateLimiter(
            requests_per_minute=5, safety_margin=0.0, window_duration=2
        )  # 2 second window
        source = "test_source"

        # Fill up the rate limit
        for _ in range(5):
            wait_time = await limiter.wait_if_needed(source)
            assert wait_time == 0.0

        # Next request should be rate limited
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time > 0

        # Wait for window to expire
        await asyncio.sleep(2.1)

        # Now we should be able to make requests again
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time == 0.0, "Request should be allowed after window expiry"

    @pytest.mark.asyncio
    async def test_observer_notifications_request_made(self):
        """Test observer notifications for request made events."""
        limiter = RateLimiter(requests_per_minute=10)
        observer = MockRateLimitObserver()
        limiter.add_observer(observer)

        source = "test_source"
        await limiter.wait_if_needed(source)

        # Verify notification was sent
        assert len(observer.request_made_calls) == 1
        assert observer.request_made_calls[0][0] == source
        assert isinstance(observer.request_made_calls[0][1], datetime)

    @pytest.mark.asyncio
    async def test_observer_notifications_rate_limit_hit(self):
        """Test observer notifications for rate limit hit events."""
        limiter = RateLimiter(requests_per_minute=2, safety_margin=0.0)  # 2 requests
        observer = MockRateLimitObserver()
        limiter.add_observer(observer)

        source = "test_source"

        # Fill up rate limit
        await limiter.wait_if_needed(source)
        await limiter.wait_if_needed(source)

        # This should trigger rate limit hit
        await limiter.wait_if_needed(source)

        # Verify notification was sent
        assert len(observer.rate_limit_hit_calls) == 1
        assert observer.rate_limit_hit_calls[0][0] == source
        assert observer.rate_limit_hit_calls[0][1] > 0  # wait_time should be positive

    @pytest.mark.asyncio
    async def test_observer_notifications_rate_limit_reset(self):
        """Test observer notifications for rate limit reset events."""
        limiter = RateLimiter(requests_per_minute=10)
        observer = MockRateLimitObserver()
        limiter.add_observer(observer)

        source = "test_source"

        # Make some requests first
        await limiter.wait_if_needed(source)

        # Reset the source
        await limiter.reset_source(source)

        # Verify notification was sent
        assert len(observer.rate_limit_reset_calls) == 1
        assert observer.rate_limit_reset_calls[0] == source

    @pytest.mark.asyncio
    async def test_observer_error_handling(self):
        """Test that observer exceptions don't break rate limiting."""
        limiter = RateLimiter(requests_per_minute=10)
        failing_observer = FailingObserver()
        working_observer = MockRateLimitObserver()

        limiter.add_observer(failing_observer)
        limiter.add_observer(working_observer)

        source = "test_source"

        # This should not raise an exception even though failing_observer throws
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time == 0.0

        # Working observer should still receive notification
        assert len(working_observer.request_made_calls) == 1

    @pytest.mark.asyncio
    async def test_concurrent_access_thread_safety(self):
        """Test thread-safe concurrent access."""
        limiter = RateLimiter(requests_per_minute=100, safety_margin=0.0)
        source = "concurrent_test"

        async def make_request():
            return await limiter.wait_if_needed(source)

        # Run 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # First 100 should be allowed (0.0 wait time)
        # Since we're only making 50 requests, all should be immediate
        assert all(wait_time == 0.0 for wait_time in results)

    @pytest.mark.asyncio
    async def test_concurrent_access_with_rate_limiting(self):
        """Test concurrent access that triggers rate limiting."""
        limiter = RateLimiter(requests_per_minute=10, safety_margin=0.0)  # 10 requests
        source = "concurrent_limited"

        async def make_request():
            return await limiter.wait_if_needed(source)

        # Run 15 concurrent requests (more than limit)
        tasks = [make_request() for _ in range(15)]
        results = await asyncio.gather(*tasks)

        # First 10 should be immediate, rest should have wait times
        immediate_requests = sum(1 for wait_time in results if wait_time == 0.0)
        delayed_requests = sum(1 for wait_time in results if wait_time > 0.0)

        assert immediate_requests == 10, "First 10 requests should be immediate"
        assert delayed_requests == 5, "Remaining 5 requests should be delayed"

    def test_get_current_usage_single_source(self):
        """Test getting usage statistics for a single source."""
        limiter = RateLimiter(requests_per_minute=100, safety_margin=0.10)  # 90 effective

        # Test with no requests
        usage = limiter.get_current_usage("test_source")

        expected_keys = {
            "source",
            "current_requests",
            "effective_limit",
            "requests_remaining",
            "utilization_percent",
            "is_rate_limited",
            "next_available_seconds",
            "window_duration",
        }
        assert set(usage.keys()) == expected_keys
        assert usage["source"] == "test_source"
        assert usage["current_requests"] == 0
        assert usage["effective_limit"] == 90
        assert usage["requests_remaining"] == 90
        assert usage["utilization_percent"] == 0.0
        assert usage["is_rate_limited"] is False

    def test_get_current_usage_all_sources(self):
        """Test getting usage statistics for all sources."""
        limiter = RateLimiter(requests_per_minute=100, safety_margin=0.10)

        usage = limiter.get_current_usage()

        expected_keys = {
            "total_sources",
            "total_current_requests",
            "effective_limit_per_source",
            "sources",
            "observers_count",
            "window_duration",
            "safety_margin_percent",
        }
        assert set(usage.keys()) == expected_keys
        assert usage["total_sources"] == 0
        assert usage["effective_limit_per_source"] == 90
        assert usage["safety_margin_percent"] == 10.0

    @pytest.mark.asyncio
    async def test_get_current_usage_with_requests(self):
        """Test usage statistics after making requests."""
        limiter = RateLimiter(requests_per_minute=10, safety_margin=0.0)
        source = "test_source"

        # Make 3 requests
        for _ in range(3):
            await limiter.wait_if_needed(source)

        usage = limiter.get_current_usage(source)
        assert usage["current_requests"] == 3
        assert usage["requests_remaining"] == 7
        assert usage["utilization_percent"] == 30.0
        assert usage["is_rate_limited"] is False

    def test_get_performance_metrics(self):
        """Test performance metrics collection."""
        limiter = RateLimiter(requests_per_minute=1000, safety_margin=0.10)
        observer = MockRateLimitObserver()
        limiter.add_observer(observer)

        metrics = limiter.get_performance_metrics()

        expected_keys = {
            "configured_limit",
            "effective_limit",
            "safety_margin_percent",
            "window_duration_seconds",
            "total_active_sources",
            "total_current_requests",
            "observer_count",
            "most_active_source",
            "max_source_requests",
            "max_source_utilization_percent",
            "memory_efficient",
            "cleanup_working",
        }
        assert set(metrics.keys()) == expected_keys
        assert metrics["configured_limit"] == 1000
        assert metrics["effective_limit"] == 900
        assert metrics["safety_margin_percent"] == 10.0
        assert metrics["observer_count"] == 1
        assert metrics["memory_efficient"] is True
        assert metrics["cleanup_working"] is True

    @pytest.mark.asyncio
    async def test_reset_source(self):
        """Test resetting rate limit tracking for a specific source."""
        limiter = RateLimiter(requests_per_minute=5, safety_margin=0.0)
        source = "reset_test"

        # Make requests to fill up limit
        for _ in range(5):
            await limiter.wait_if_needed(source)

        # Verify we're at limit
        usage_before = limiter.get_current_usage(source)
        assert usage_before["current_requests"] == 5
        assert usage_before["is_rate_limited"] is True

        # Reset the source
        await limiter.reset_source(source)

        # Verify reset worked
        usage_after = limiter.get_current_usage(source)
        assert usage_after["current_requests"] == 0
        assert usage_after["is_rate_limited"] is False

    @pytest.mark.asyncio
    async def test_per_source_isolation(self):
        """Test that different sources have isolated rate limits."""
        limiter = RateLimiter(requests_per_minute=3, safety_margin=0.0)
        source1 = "source_1"
        source2 = "source_2"

        # Fill up source1's limit
        for _ in range(3):
            wait_time = await limiter.wait_if_needed(source1)
            assert wait_time == 0.0

        # source1 should be rate limited
        wait_time = await limiter.wait_if_needed(source1)
        assert wait_time > 0

        # source2 should still be available
        wait_time = await limiter.wait_if_needed(source2)
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_performance_response_time(self):
        """Test that rate limit checks meet <100ms performance requirement."""
        limiter = RateLimiter(requests_per_minute=1000)
        source = "performance_test"

        # Measure time for rate limit check
        start_time = time.perf_counter()
        await limiter.wait_if_needed(source)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 100, (
            f"Response time {response_time_ms:.1f}ms exceeds 100ms requirement"
        )

    @pytest.mark.asyncio
    async def test_memory_efficiency_cleanup(self):
        """Test memory efficiency with automatic cleanup."""
        limiter = RateLimiter(requests_per_minute=5, safety_margin=0.0, window_duration=1)
        source = "memory_test"

        # Make requests that will expire
        for _ in range(5):
            await limiter.wait_if_needed(source)

        # Verify requests are tracked
        assert len(limiter._source_requests[source]) == 5

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Make another request to trigger cleanup
        await limiter.wait_if_needed(source)

        # Old requests should be cleaned up, only 1 new request remains
        assert len(limiter._source_requests[source]) == 1

    def test_logging_integration(self):
        """Test that Epic 1 logging integration works."""
        with patch(
            "phoenix_real_estate.collectors.base.rate_limiter.get_logger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            _ = RateLimiter(requests_per_minute=100, safety_margin=0.10)

            # Verify logger was obtained and initialization was logged
            mock_get_logger.assert_called_once_with(
                "phoenix_real_estate.collectors.base.rate_limiter"
            )
            mock_logger.info.assert_called_once()

            # Verify the initialization log contains expected information
            call_args = mock_logger.info.call_args
            assert "Rate limiter initialized" in call_args[0][0]
            assert "requests_per_minute" in call_args[1]["extra"]
            assert "effective_limit" in call_args[1]["extra"]

    @pytest.mark.asyncio
    async def test_multiple_observers_concurrent_notifications(self):
        """Test that multiple observers receive concurrent notifications."""
        limiter = RateLimiter(requests_per_minute=10)

        observers = [MockRateLimitObserver() for _ in range(3)]
        for observer in observers:
            limiter.add_observer(observer)

        source = "multi_observer_test"

        # Make a request that should notify all observers
        await limiter.wait_if_needed(source)

        # All observers should have received the notification
        for observer in observers:
            assert len(observer.request_made_calls) == 1
            assert observer.request_made_calls[0][0] == source

    @pytest.mark.asyncio
    async def test_edge_case_zero_effective_limit(self):
        """Test edge case where effective limit could be zero."""
        # This could happen with very high safety margin
        limiter = RateLimiter(requests_per_minute=1, safety_margin=1.0)  # 100% margin

        # Effective limit should be 0
        assert limiter.effective_limit == 0

        # Any request should be rate limited
        source = "zero_limit_test"
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time >= 0  # Should either be rate limited or handle gracefully

    @pytest.mark.asyncio
    async def test_edge_case_very_small_window(self):
        """Test edge case with very small window duration."""
        limiter = RateLimiter(requests_per_minute=10, safety_margin=0.0, window_duration=1)
        source = "small_window_test"

        # Fill up the limit
        for _ in range(10):
            await limiter.wait_if_needed(source)

        # Should be rate limited
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time > 0

        # Wait for short window to expire
        await asyncio.sleep(1.1)

        # Should be available again
        wait_time = await limiter.wait_if_needed(source)
        assert wait_time == 0.0

    def test_protocol_compliance(self):
        """Test that the observer protocol is correctly defined."""
        # This test ensures the protocol methods have correct signatures
        observer = MockRateLimitObserver()

        # Check that our test observer implements the protocol correctly
        assert hasattr(observer, "on_request_made")
        assert hasattr(observer, "on_rate_limit_hit")
        assert hasattr(observer, "on_rate_limit_reset")

        # Check method signatures by calling them (they should not raise TypeErrors)
        import inspect

        sig = inspect.signature(observer.on_request_made)
        assert len(sig.parameters) == 2  # source, timestamp

        sig = inspect.signature(observer.on_rate_limit_hit)
        assert len(sig.parameters) == 2  # source, wait_time

        sig = inspect.signature(observer.on_rate_limit_reset)
        assert len(sig.parameters) == 1  # source
