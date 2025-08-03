"""Performance benchmark tests for LLM processing pipeline."""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock

from phoenix_real_estate.collectors.processing import DataProcessingPipeline, OllamaClient
from phoenix_real_estate.collectors.processing.performance import (
    PerformanceBenchmark,
    BenchmarkResult,
    PerformanceOptimizer,
    BatchSizeOptimizer,
)
from phoenix_real_estate.foundation.config import get_config


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        config = get_config()
        # Override for testing
        config.settings.BATCH_SIZE = 10
        config.settings.MAX_CONCURRENT_PROCESSING = 5
        config.settings.LLM_TIMEOUT = 30
        return config

    @pytest.fixture
    def sample_properties(self) -> List[Dict[str, Any]]:
        """Generate sample property data."""
        properties = []
        for i in range(100):
            properties.append(
                {
                    "html": f"<div>Property {i} details...</div>",
                    "address": f"{i} Main St, Phoenix, AZ",
                    "price": 100000 + i * 1000,
                    "bedrooms": (i % 4) + 1,
                    "bathrooms": (i % 3) + 1,
                }
            )
        return properties

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_single_property_processing_speed(self, config):
        """Benchmark single property processing."""
        benchmark = PerformanceBenchmark("single_property_processing")

        # Mock LLM response
        async def mock_llm_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate LLM delay
            return {
                "description": "Test property",
                "features": ["pool", "garage"],
                "confidence": 0.95,
            }

        async with DataProcessingPipeline(config) as pipeline:
            # Mock the LLM call
            pipeline._extractor._client.extract_structured_data = mock_llm_response

            # Run benchmark
            async with benchmark:
                for _ in range(10):
                    start = time.time()

                    result = await pipeline.process_html("<div>Test property</div>", "phoenix_mls")

                    duration = time.time() - start
                    benchmark.record_operation(duration, success=result.is_valid)

            # Get results
            results = benchmark.get_results()

            # Performance requirements
            assert results.avg_duration < 2.0  # Less than 2 seconds average
            assert results.p95_duration < 3.0  # 95th percentile under 3 seconds
            assert results.success_rate > 0.9  # 90% success rate

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_batch_processing_throughput(self, config, sample_properties):
        """Benchmark batch processing throughput."""
        benchmark = PerformanceBenchmark("batch_processing_throughput")

        async with DataProcessingPipeline(config) as pipeline:
            # Mock for speed
            pipeline._extractor.extract_from_html = AsyncMock(
                return_value={"description": "Test", "confidence": 0.9}
            )

            batch_sizes = [5, 10, 20, 50]
            throughputs = []

            for batch_size in batch_sizes:
                pipeline.batch_size = batch_size
                batch = [p["html"] for p in sample_properties[:batch_size]]

                async with benchmark:
                    start = time.time()
                    results = await pipeline.process_batch_html(batch, "phoenix_mls")
                    duration = time.time() - start

                throughput = len(results) / duration
                throughputs.append(throughput)

                # Log for analysis
                print(f"Batch size {batch_size}: {throughput:.2f} properties/second")

            # Throughput should increase with batch size (to a point)
            assert throughputs[1] > throughputs[0]  # 10 > 5
            assert max(throughputs) > 10  # At least 10 properties/second

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_memory_usage_scaling(self, config, sample_properties):
        """Test memory usage scales appropriately."""
        import psutil
        import gc

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        async with DataProcessingPipeline(config) as pipeline:
            # Mock for consistency
            pipeline._extractor.extract_from_html = AsyncMock(
                return_value={"description": "Test", "confidence": 0.9}
            )

            # Process increasing batches
            memory_readings = []

            for size in [10, 50, 100]:
                gc.collect()  # Clean up before measurement

                batch = [p["html"] for p in sample_properties[:size]]
                await pipeline.process_batch_html(batch, "phoenix_mls")

                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                memory_readings.append(memory_increase)

                print(f"Batch {size}: +{memory_increase:.2f} MB")

            # Memory should not grow linearly with batch size
            # (indicates proper cleanup and streaming)
            memory_ratio = memory_readings[-1] / memory_readings[0]
            batch_ratio = 100 / 10

            assert memory_ratio < batch_ratio * 0.5  # Much less than linear growth

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrent_processing_limits(self, config):
        """Test concurrent processing performance."""
        PerformanceBenchmark("concurrent_processing")

        async def simulate_processing(delay: float):
            await asyncio.sleep(delay)
            return {"processed": True}

        async with DataProcessingPipeline(config) as pipeline:
            pipeline._extractor.extract_from_html = lambda *args: simulate_processing(0.1)

            # Test different concurrency levels
            concurrency_levels = [1, 5, 10, 20]
            processing_times = []

            for max_concurrent in concurrency_levels:
                pipeline.max_concurrent = max_concurrent
                pipeline._semaphore = asyncio.Semaphore(max_concurrent)

                items = ["<div>Test</div>"] * 50

                start = time.time()
                await pipeline.process_batch_html(items, "phoenix_mls")
                duration = time.time() - start

                processing_times.append(duration)
                print(f"Concurrency {max_concurrent}: {duration:.2f}s")

            # Higher concurrency should reduce total time (up to a point)
            assert processing_times[1] < processing_times[0]  # 5 < 1
            assert processing_times[2] < processing_times[1]  # 10 < 5

            # But returns should diminish
            improvement_1_to_5 = processing_times[0] - processing_times[1]
            improvement_10_to_20 = processing_times[2] - processing_times[3]
            assert improvement_1_to_5 > improvement_10_to_20

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_cache_performance_impact(self, config):
        """Test cache impact on performance."""
        from phoenix_real_estate.collectors.processing.cache import CacheManager, CacheConfig

        # Create cache
        cache_config = CacheConfig(enabled=True, backend="memory")
        cache = CacheManager(cache_config)
        await cache.initialize()

        async with OllamaClient(config) as client:
            client._cache_manager = cache

            # Mock LLM response
            call_count = 0

            async def mock_generate(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.5)  # Simulate LLM delay
                return "Test response"

            client._generate_completion_impl = mock_generate

            # First run - no cache
            no_cache_times = []
            for i in range(10):
                start = time.time()
                await client.generate_completion(f"Prompt {i}")
                no_cache_times.append(time.time() - start)

            first_run_calls = call_count

            # Second run - with cache
            call_count = 0
            cache_times = []
            for i in range(10):
                start = time.time()
                await client.generate_completion(f"Prompt {i}")
                cache_times.append(time.time() - start)

            second_run_calls = call_count

            # Cache should dramatically improve performance
            avg_no_cache = statistics.mean(no_cache_times)
            avg_cache = statistics.mean(cache_times)

            assert avg_cache < avg_no_cache * 0.1  # 90% improvement
            assert second_run_calls == 0  # All cache hits
            assert first_run_calls == 10  # All cache misses

            # Get cache metrics
            metrics = cache.get_metrics()
            assert metrics["hit_rate"] == 0.5  # 10 hits / 20 total


class TestPerformanceOptimizer:
    """Test performance optimization strategies."""

    @pytest.mark.asyncio
    async def test_adaptive_batch_sizing(self):
        """Test dynamic batch size optimization."""
        optimizer = BatchSizeOptimizer(initial_size=10, min_size=5, max_size=100)

        # Simulate good performance
        for _ in range(5):
            optimizer.record_batch_performance(
                batch_size=10, duration=1.0, success_rate=0.95, memory_usage_mb=100
            )

        # Should recommend increase
        new_size = optimizer.get_optimal_batch_size()
        assert new_size > 10

        # Simulate degraded performance
        for _ in range(5):
            optimizer.record_batch_performance(
                batch_size=50, duration=10.0, success_rate=0.7, memory_usage_mb=900
            )

        # Should recommend decrease
        new_size = optimizer.get_optimal_batch_size()
        assert new_size < 50

    @pytest.mark.asyncio
    async def test_circuit_breaker_performance(self):
        """Test circuit breaker impact on performance."""
        from phoenix_real_estate.foundation.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            failure_threshold=3, recovery_timeout=1.0, expected_exception=Exception
        )

        # Simulate failures
        failure_count = 0

        async def failing_operation():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception("Service unavailable")
            return "Success"

        # Test performance during failures
        start = time.time()
        results = []

        for _ in range(10):
            try:
                result = await breaker.call(failing_operation)
                results.append(("success", result))
            except Exception as e:
                results.append(("failure", str(e)))

        duration = time.time() - start

        # Circuit breaker should prevent cascading failures
        assert duration < 2.0  # Fast fail after opening

        # Count outcomes
        successes = sum(1 for r in results if r[0] == "success")
        circuit_open_errors = sum(1 for r in results if "Circuit breaker is open" in str(r[1]))

        assert circuit_open_errors > 0  # Circuit opened
        assert successes < 10  # Not all succeeded

    def test_performance_recommendations(self):
        """Test performance optimization recommendations."""
        optimizer = PerformanceOptimizer()

        # Analyze performance data
        metrics = {
            "avg_processing_time": 3.5,  # Above target
            "memory_usage_percent": 85,  # High
            "cpu_usage_percent": 90,  # Very high
            "cache_hit_rate": 0.1,  # Low
            "error_rate": 0.15,  # High
            "batch_size": 50,
            "concurrency": 20,
        }

        recommendations = optimizer.analyze_and_recommend(metrics)

        # Should recommend optimizations
        assert any("cache" in r.lower() for r in recommendations)  # Improve caching
        assert any("batch" in r.lower() for r in recommendations)  # Reduce batch size
        assert any("concurrency" in r.lower() for r in recommendations)  # Reduce concurrency
        assert any("resource" in r.lower() for r in recommendations)  # Resource constraints


class TestBenchmarkResult:
    """Test benchmark result analysis."""

    def test_result_statistics(self):
        """Test benchmark result calculations."""
        result = BenchmarkResult("test_benchmark")

        # Add sample data
        durations = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0, 2.5, 3.0]
        for d in durations:
            result.add_sample(duration=d, success=d < 2.0)

        stats = result.get_statistics()

        assert stats["count"] == 10
        assert stats["avg_duration"] == pytest.approx(1.35, rel=0.01)
        assert stats["min_duration"] == 0.5
        assert stats["max_duration"] == 3.0
        assert stats["p50_duration"] == pytest.approx(0.95, rel=0.1)
        assert stats["p95_duration"] == pytest.approx(2.75, rel=0.1)
        assert stats["success_rate"] == 0.7  # 7 out of 10

    def test_result_comparison(self):
        """Test comparing benchmark results."""
        result1 = BenchmarkResult("before_optimization")
        result2 = BenchmarkResult("after_optimization")

        # Before optimization
        for _ in range(100):
            result1.add_sample(duration=2.0 + (0.5 * (time.time() % 1)), success=True)

        # After optimization
        for _ in range(100):
            result2.add_sample(duration=1.0 + (0.3 * (time.time() % 1)), success=True)

        comparison = result1.compare_to(result2)

        assert comparison["avg_improvement_percent"] > 40  # >40% improvement
        assert comparison["p95_improvement_percent"] > 30  # >30% improvement at p95
        assert comparison["is_improvement"] is True
