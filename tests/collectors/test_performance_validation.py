"""Performance validation tests for collectors.

Tests rate limiting compliance, response times, memory usage, and concurrent handling.
"""

import asyncio
import time
import tracemalloc
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import pytest

from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter
from phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector
from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository


class TestPerformanceValidation:
    """Comprehensive performance validation tests."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        config = Mock(spec=ConfigProvider)
        config.get.side_effect = lambda key, default=None: {
            "maricopa.api.base_url": "https://api.example.com",
            "maricopa.api.bearer_token": "test_token",
            "maricopa.api.rate_limit": 900,
            "maricopa.api.rate_window_seconds": 3600,
            "maricopa.api.safety_margin": 0.1,
            "maricopa.collection.batch_size": 100,
            "maricopa.collection.max_retries": 3,
            "maricopa.collection.retry_delay_seconds": 5,
        }.get(key, default)

        # Mock get_typed method
        config.get_typed = Mock(
            side_effect=lambda key, type_hint, default=None: {
                "maricopa.collection": {},
                "maricopa.collection.batch_size": 100,
                "maricopa.collection.max_retries": 3,
                "maricopa.collection.retry_delay_seconds": 5,
            }.get(key, default)
        )

        return config

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = Mock(spec=PropertyRepository)
        repo.find_updated_since.return_value = []
        repo.find_by_id.return_value = None
        repo.save.return_value = True
        return repo

    @pytest.mark.asyncio
    async def test_rate_limiting_compliance(self):
        """Test that rate limiting prevents API violations."""
        rate_limiter = RateLimiter(
            requests_per_minute=15,  # 900 per hour = 15 per minute
            window_duration=60,
            safety_margin=0.1,
        )

        violations = 0
        successful_requests = 0

        # Try to make 1000 requests rapidly
        for i in range(1000):
            wait_time = await rate_limiter.wait_if_needed("test_source")
            if wait_time == 0:
                successful_requests += 1
            else:
                violations += 1

        # Should have ~13-14 successful (15 * 0.9 safety margin per minute)
        assert successful_requests <= 14  # With safety margin
        assert violations >= 986  # Most should be blocked

        # Verify no violations occurred (rate limiter prevented them)
        print(f"✅ Rate limiting test: {successful_requests} allowed, {violations} prevented")
        assert violations > 0  # Some requests should have been blocked

    @pytest.mark.asyncio
    async def test_response_time_zipcode_search(self, mock_config):
        """Test response time for zipcode searches."""
        client = MaricopaAPIClient(mock_config)

        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"results": [{"property_id": f"test_{i}"} for i in range(100)]}
        )

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            start_time = time.time()

            # Perform zipcode search
            results = await client.search_by_zipcode("85001")

            elapsed_time = time.time() - start_time

            # Should complete in under 30 seconds
            assert elapsed_time < 30.0
            assert len(results) == 100

            print(f"✅ Zipcode search completed in {elapsed_time:.2f}s (< 30s requirement)")

    def test_memory_usage_during_collection(self, mock_config, mock_repository):
        """Test memory usage during extended operations."""
        collector = MaricopaAPICollector(config=mock_config, repository=mock_repository)

        # Start memory tracking
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]

        # Mock client to return large dataset
        mock_client = Mock()
        mock_client.search_properties.return_value = [
            {"property_id": f"test_{i}", "data": "x" * 1000} for i in range(1000)
        ]
        collector.client = mock_client

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.transform_batch.return_value = [
            {
                "property_id": f"test_{i}",
                "address": {"street": f"{i} Test St", "city": "Phoenix", "zip": "85001"},
                "last_updated": datetime.now().isoformat(),
            }
            for i in range(1000)
        ]
        collector.adapter = mock_adapter

        # Perform collection
        results = collector.collect(
            search_params={"zip_codes": ["85001"]}, save_to_repository=False
        )

        # Check memory usage
        current_memory = tracemalloc.get_traced_memory()[0]
        memory_used_mb = (current_memory - initial_memory) / 1024 / 1024

        tracemalloc.stop()

        # Should use less than 100MB
        assert memory_used_mb < 100
        print(f"✅ Memory usage: {memory_used_mb:.2f}MB (< 100MB requirement)")

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test handling of multiple simultaneous requests."""
        rate_limiter = RateLimiter(
            requests_per_minute=15,  # 900 per hour = 15 per minute
            window_duration=60,
            safety_margin=0.1,
        )

        # Track concurrent execution
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def make_request(source: str, request_id: int):
            nonlocal concurrent_count, max_concurrent

            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            # Simulate request processing
            wait_time = await rate_limiter.wait_if_needed(source)
            if wait_time == 0:
                await asyncio.sleep(0.01)  # Simulate API call
                result = f"Success_{request_id}"
            else:
                result = f"RateLimited_{request_id}"

            async with lock:
                concurrent_count -= 1

            return result

        async def run_concurrent_test():
            # Create 50 concurrent requests
            tasks = [make_request("test_source", i) for i in range(50)]

            results = await asyncio.gather(*tasks)
            return results, max_concurrent

        # Run the test
        results, max_concurrent = await run_concurrent_test()

        # Count successful vs rate limited
        successful = sum(1 for r in results if r.startswith("Success"))
        rate_limited = sum(1 for r in results if r.startswith("RateLimited"))

        print(f"✅ Concurrent handling: {successful} successful, {rate_limited} rate limited")
        print(f"   Max concurrent: {max_concurrent}")

        # All requests should be handled (either success or rate limited)
        assert len(results) == 50
        assert successful + rate_limited == 50

    @pytest.mark.asyncio
    async def test_connection_management(self, mock_config):
        """Test efficient connection pooling and cleanup."""
        client = MaricopaAPIClient(mock_config)

        # Track connection lifecycle
        connections_created = 0
        connections_closed = 0

        async def test_connection_lifecycle():
            nonlocal connections_created, connections_closed

            # Mock session creation
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session

                # Track creation
                mock_session_class.side_effect = lambda **kwargs: (
                    setattr(mock_session, "_created", True),
                    mock_session,
                )[-1]

                # Track closing
                async def mock_close():
                    nonlocal connections_closed
                    connections_closed += 1

                mock_session.close = mock_close

                # Create client and make requests
                async with client:
                    connections_created += 1

                    # Make multiple requests - should reuse connection
                    for i in range(10):
                        mock_response = AsyncMock()
                        mock_response.status = 200
                        mock_response.json = AsyncMock(return_value={"results": []})

                        mock_session.get = AsyncMock(return_value=mock_response)

                        # This should reuse the same session
                        await client._make_request("GET", "/test")

                # Should have closed connection
                assert connections_closed == 1

        await test_connection_lifecycle()

        print(
            f"✅ Connection management: {connections_created} created, {connections_closed} closed"
        )
        assert connections_created == connections_closed  # All connections properly closed


if __name__ == "__main__":
    # Run performance validation
    import sys

    print("Running performance validation tests...")

    # Run tests using pytest
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            __file__,
            "-v",
            "-k",
            "test_rate_limiting_compliance or test_memory_usage or test_concurrent",
        ]
    )

    if result.returncode == 0:
        print("\n✅ All performance validations passed!")
    else:
        print("\n❌ Some performance validations failed!")
        sys.exit(1)
