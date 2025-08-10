"""Test script for LLM processing performance optimizations."""

import asyncio
import time
from typing import List, Dict, Any

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.collectors.processing import DataProcessingPipeline, PerformanceBenchmark


async def generate_test_data(count: int = 100) -> List[Dict[str, Any]]:
    """Generate test property data."""
    properties = []

    for i in range(count):
        properties.append(
            {
                "html": f"""
            <div class="property-details">
                <h2>{i} Main Street, Phoenix, AZ 85001</h2>
                <div class="price">${100000 + i * 1000}</div>
                <div class="details">
                    <span>{(i % 4) + 1} bedrooms</span>
                    <span>{(i % 3) + 1} bathrooms</span>
                    <span>{1000 + i * 50} sqft</span>
                </div>
                <div class="description">
                    Beautiful home in the heart of Phoenix. Features include updated kitchen,
                    spacious living areas, and a lovely backyard. Perfect for families or
                    investors looking for a great opportunity in a prime location.
                </div>
            </div>
            """,
                "source": "phoenix_mls",
            }
        )

    return properties


async def test_cache_performance():
    """Test cache impact on performance."""
    print("\n=== Cache Performance Test ===")

    config = EnvironmentConfigProvider()

    # Test without cache
    print("\nTesting without cache...")
    config.settings.CACHE_ENABLED = False

    async with DataProcessingPipeline(config) as pipeline:
        properties = await generate_test_data(20)

        start = time.time()
        results = await pipeline.process_batch_html([p["html"] for p in properties], "phoenix_mls")
        no_cache_duration = time.time() - start

        print(f"Without cache: {no_cache_duration:.2f}s ({len(results)} properties)")
        print(f"Success rate: {sum(1 for r in results if r.is_valid) / len(results):.2%}")

    # Test with cache (second run)
    print("\nTesting with cache...")
    config.settings.CACHE_ENABLED = True

    async with DataProcessingPipeline(config) as pipeline:
        # First run to populate cache
        await pipeline.process_batch_html([p["html"] for p in properties], "phoenix_mls")

        # Second run with cache
        start = time.time()
        results = await pipeline.process_batch_html([p["html"] for p in properties], "phoenix_mls")
        cache_duration = time.time() - start

        metrics = pipeline.get_metrics()
        cache_metrics = metrics.get("cache", {})

        print(f"\nWith cache: {cache_duration:.2f}s ({len(results)} properties)")
        print(f"Cache hit rate: {cache_metrics.get('hit_rate', 0):.2%}")
        print(
            f"Performance improvement: {(no_cache_duration - cache_duration) / no_cache_duration:.1%}"
        )


async def test_batch_size_optimization():
    """Test dynamic batch size optimization."""
    print("\n=== Batch Size Optimization Test ===")

    config = EnvironmentConfigProvider()
    config.settings.ADAPTIVE_BATCH_SIZING = True
    config.settings.BATCH_SIZE = 5  # Start small

    async with DataProcessingPipeline(config) as pipeline:
        properties = await generate_test_data(100)

        print("\nProcessing batches with adaptive sizing...")

        # Process in chunks to see adaptation
        chunk_size = 20
        for i in range(0, len(properties), chunk_size):
            chunk = properties[i : i + chunk_size]

            start = time.time()
            results = await pipeline.process_batch_html([p["html"] for p in chunk], "phoenix_mls")
            duration = time.time() - start

            metrics = pipeline.get_metrics()
            batch_metrics = metrics.get("batch_optimization", {})

            print(f"\nChunk {i // chunk_size + 1}:")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Current batch size: {batch_metrics.get('current_batch_size', 'N/A')}")
            print(f"  Optimal batch size: {batch_metrics.get('optimal_batch_size', 'N/A')}")
            print(f"  Success rate: {sum(1 for r in results if r.is_valid) / len(results):.2%}")


async def test_resource_monitoring():
    """Test resource monitoring and adaptive control."""
    print("\n=== Resource Monitoring Test ===")

    config = EnvironmentConfigProvider()
    config.settings.RESOURCE_MONITORING_ENABLED = True
    config.settings.MAX_MEMORY_MB = 512  # Simulate constraint
    config.settings.MAX_CPU_PERCENT = 70

    async with DataProcessingPipeline(config) as pipeline:
        properties = await generate_test_data(50)

        print("\nProcessing with resource monitoring...")

        # Set up alert monitoring
        alerts_received = []
        if pipeline._resource_monitor:
            pipeline._resource_monitor.on_alert(lambda alert: alerts_received.append(alert))

        results = await pipeline.process_batch_html([p["html"] for p in properties], "phoenix_mls")

        metrics = pipeline.get_metrics()
        resource_metrics = metrics.get("resources", {})

        print(f"\nProcessed {len(results)} properties")
        print(
            f"Memory usage: {resource_metrics.get('memory_mb', 0):.1f} MB "
            f"({resource_metrics.get('memory_percent', 0):.1f}%)"
        )
        print(f"CPU usage: {resource_metrics.get('cpu_percent', 0):.1f}%")
        print(f"Active operations: {resource_metrics.get('active_operations', 0)}")
        print(f"Resource alerts: {len(alerts_received)}")


async def run_performance_benchmark():
    """Run comprehensive performance benchmark."""
    print("\n=== Comprehensive Performance Benchmark ===")

    config = EnvironmentConfigProvider()
    # Enable all optimizations
    config.settings.CACHE_ENABLED = True
    config.settings.RESOURCE_MONITORING_ENABLED = True
    config.settings.ADAPTIVE_BATCH_SIZING = True

    benchmark = PerformanceBenchmark("full_pipeline_optimization")

    async with benchmark:
        async with DataProcessingPipeline(config) as pipeline:
            properties = await generate_test_data(200)

            # Process in waves to test sustained performance
            wave_size = 50
            for wave in range(4):
                wave_properties = properties[wave * wave_size : (wave + 1) * wave_size]

                print(f"\nProcessing wave {wave + 1}...")
                start = time.time()

                results = await pipeline.process_batch_html(
                    [p["html"] for p in wave_properties], "phoenix_mls"
                )

                duration = time.time() - start
                success_count = sum(1 for r in results if r.is_valid)

                benchmark.record_operation(
                    duration=duration,
                    success=success_count == len(results),
                    wave=wave,
                    items_processed=len(results),
                    success_rate=success_count / len(results),
                )

                print(f"  Duration: {duration:.2f}s")
                print(f"  Throughput: {len(results) / duration:.1f} items/second")
                print(f"  Success rate: {success_count / len(results):.2%}")

            # Final metrics
            print("\n=== Final Performance Metrics ===")
            metrics = pipeline.get_metrics()

            print("\nProcessing:")
            print(f"  Total processed: {metrics['total_processed']}")
            print(f"  Success rate: {metrics['success_rate']:.2%}")
            print(f"  Avg processing time: {metrics['average_processing_time']:.2f}s")

            if "cache" in metrics:
                print("\nCache:")
                print(f"  Hit rate: {metrics['cache']['hit_rate']:.2%}")
                print(f"  Entries: {metrics['cache']['entries']}")
                print(f"  Memory used: {metrics['cache']['memory_used_mb']:.1f} MB")

            if "resources" in metrics:
                print("\nResources:")
                print(f"  Memory: {metrics['resources']['memory_mb']:.1f} MB")
                print(f"  CPU: {metrics['resources']['cpu_percent']:.1f}%")

    # Benchmark results
    stats = benchmark.get_results().get_statistics()
    print("\n=== Benchmark Statistics ===")
    print(f"Total duration: {stats['total_duration']:.2f}s")
    print(f"Average wave duration: {stats['avg_duration']:.2f}s")
    print(f"Min/Max duration: {stats['min_duration']:.2f}s / {stats['max_duration']:.2f}s")
    print(f"P95 duration: {stats['p95_duration']:.2f}s")


async def main(mode="test"):
    """Run all performance tests."""
    print("=" * 60)
    print(f"LLM Processing Performance Optimization Tests (mode: {mode})")
    print("=" * 60)

    # Run individual tests
    await test_cache_performance()
    await test_batch_size_optimization()
    await test_resource_monitoring()

    # Run comprehensive benchmark
    await run_performance_benchmark()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


def run_main():
    """Main function with CLI argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(description="Test LLM processing performance optimizations")
    parser.add_argument(
        "--mode",
        default="test",
        choices=["test", "incremental", "full"],
        help="Test mode (default: test)",
    )

    args = parser.parse_args()
    asyncio.run(main(args.mode))


if __name__ == "__main__":
    run_main()
