"""Demo script showing LLM processing performance optimizations."""

import asyncio
import time
from phoenix_real_estate.foundation.config import get_config
from phoenix_real_estate.collectors.processing import (
    DataProcessingPipeline,
    CacheManager,
    CacheConfig,
    ResourceMonitor,
    ResourceLimits,
    BatchSizeOptimizer
)


async def demo_cache_performance():
    """Demonstrate cache performance improvements."""
    print("\n=== Cache Performance Demo ===")
    
    # Create cache
    cache_config = CacheConfig(
        enabled=True,
        backend="memory",
        ttl_hours=24
    )
    cache = CacheManager(cache_config)
    await cache.initialize()
    
    # Simulate property data
    property_data = {
        "address": "123 Main St, Phoenix, AZ",
        "price": 350000,
        "bedrooms": 3,
        "bathrooms": 2
    }
    
    # First access - cache miss
    start = time.time()
    await cache.get(property_data, "extraction")
    miss_time = time.time() - start
    print(f"Cache miss time: {miss_time*1000:.2f}ms")
    
    # Store in cache
    await cache.set(property_data, "extraction", {
        "description": "Beautiful 3BR/2BA home",
        "features": ["pool", "garage"],
        "confidence": 0.95
    })
    
    # Second access - cache hit
    start = time.time()
    await cache.get(property_data, "extraction")
    hit_time = time.time() - start
    print(f"Cache hit time: {hit_time*1000:.2f}ms")
    print(f"Speedup: {miss_time/hit_time:.0f}x")
    
    # Show metrics
    metrics = cache.get_metrics()
    print("\nCache metrics:")
    print(f"  Hits: {metrics['hits']}")
    print(f"  Misses: {metrics['misses']}")
    print(f"  Hit rate: {metrics['hit_rate']:.2%}")


async def demo_resource_monitoring():
    """Demonstrate resource monitoring."""
    print("\n=== Resource Monitoring Demo ===")
    
    # Create monitor
    limits = ResourceLimits(
        max_memory_mb=1024,
        max_cpu_percent=80,
        max_concurrent_requests=5
    )
    monitor = ResourceMonitor(limits)
    await monitor.start()
    
    try:
        # Get current metrics
        metrics = await monitor.get_metrics()
        print("Current resources:")
        print(f"  Memory: {metrics['memory_mb']:.1f} MB ({metrics['memory_percent']:.1f}%)")
        print(f"  CPU: {metrics['cpu_percent']:.1f}%")
        
        # Simulate operations
        print("\nSimulating operations...")
        for i in range(3):
            op_id = f"operation_{i}"
            if await monitor.check_resource_availability(op_id):
                print(f"  Operation {i}: Resources available [OK]")
                await monitor.track_operation_start(op_id)
                await asyncio.sleep(0.1)  # Simulate work
                await monitor.track_operation_end(op_id)
            else:
                print(f"  Operation {i}: Resources limited [BLOCKED]")
        
        # Show operation metrics
        for i in range(3):
            metrics = monitor.get_operation_metrics(f"operation_{i}")
            if metrics:
                print(f"\n  Operation {i} metrics:")
                print(f"    Duration: {metrics['duration_seconds']:.3f}s")
                print(f"    Memory delta: {metrics['memory_delta_mb']:.1f} MB")
    
    finally:
        await monitor.stop()


async def demo_batch_optimization():
    """Demonstrate dynamic batch size optimization."""
    print("\n=== Batch Size Optimization Demo ===")
    
    optimizer = BatchSizeOptimizer(
        initial_size=5,
        min_size=1,
        max_size=50
    )
    
    print(f"Initial batch size: {optimizer.current_size}")
    
    # Simulate different performance scenarios
    scenarios = [
        # (batch_size, duration, success_rate, memory_mb)
        (5, 2.0, 0.95, 100),   # Good performance
        (5, 2.1, 0.96, 110),   # Still good
        (5, 1.8, 0.98, 90),    # Excellent - should increase
        (10, 3.5, 0.94, 200),  # Slightly worse with larger batch
        (10, 4.0, 0.92, 250),  # Getting worse
        (10, 5.0, 0.85, 300),  # Poor - should decrease
    ]
    
    for i, (size, duration, success, memory) in enumerate(scenarios):
        optimizer.record_batch_performance(
            batch_size=size,
            duration=duration,
            success_rate=success,
            memory_usage_mb=memory
        )
        
        optimal = optimizer.get_optimal_batch_size()
        print(f"\nAfter scenario {i+1}:")
        print(f"  Performance: {duration:.1f}s, {success:.0%} success, {memory:.0f}MB")
        print(f"  Optimal batch size: {optimal}")


async def demo_integrated_pipeline():
    """Demonstrate integrated pipeline with all optimizations."""
    print("\n=== Integrated Pipeline Demo ===")
    
    config = get_config()
    
    # Create pipeline with performance features
    pipeline = DataProcessingPipeline(config)
    
    # Initialize performance components
    await pipeline.initialize()
    
    print("Pipeline initialized with:")
    print(f"  Cache: {'Enabled' if pipeline.cache_enabled else 'Disabled'}")
    print(f"  Resource monitoring: {'Enabled' if pipeline.resource_monitoring_enabled else 'Disabled'}")
    print(f"  Adaptive batch sizing: {'Enabled' if pipeline.adaptive_batch_sizing else 'Disabled'}")
    
    # Get initial metrics
    metrics = pipeline.get_metrics()
    print("\nInitial metrics:")
    print(f"  Total processed: {metrics['total_processed']}")
    
    await pipeline.close()


async def main():
    """Run all demos."""
    print("=" * 60)
    print("LLM Processing Performance Optimizations Demo")
    print("=" * 60)
    
    await demo_cache_performance()
    await demo_resource_monitoring()
    await demo_batch_optimization()
    await demo_integrated_pipeline()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())