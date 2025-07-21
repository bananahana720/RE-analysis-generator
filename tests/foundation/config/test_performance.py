"""
Performance benchmarks for Phoenix Real Estate configuration system.

Focuses on:
- Load time benchmarks
- Validation performance
- Concurrent access throughput
- Memory efficiency
- Cache performance
"""

import concurrent.futures
import gc
import os
import statistics
import time
import tracemalloc
from typing import List, Tuple, Dict, Any
import threading

import pytest

from phoenix_real_estate.foundation.config import (
    get_config,
    reset_config_cache,
    BaseConfig,
    Environment,
    EnvironmentFactory,
    get_secret_manager,
    get_secret,
    SecretManager,
)


@pytest.mark.production
@pytest.mark.benchmark
class TestLoadTimeBenchmarks:
    """Benchmark configuration load times."""

    def test_cold_start_load_time(self):
        """Benchmark initial configuration load time (cold start)."""
        # Ensure cold start
        reset_config_cache()
        gc.collect()
        
        # Measure cold start
        start = time.perf_counter()
        config = get_config()
        cold_time = time.perf_counter() - start
        
        # Verify config loaded correctly
        assert config is not None
        assert config.environment in Environment
        
        # Performance requirement: < 100ms for cold start
        assert cold_time < 0.1, f"Cold start took {cold_time:.3f}s (limit: 100ms)"
        
        # Report
        print(f"\nCold start load time: {cold_time*1000:.2f}ms")

    def test_warm_cache_load_time(self):
        """Benchmark configuration load time with warm cache."""
        # Warm up cache
        reset_config_cache()
        _ = get_config()
        
        # Benchmark warm cache access
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            config = get_config()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p50 = statistics.median(times)
        p95 = statistics.quantiles(times, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(times, n=100)[98]  # 99th percentile
        
        # Performance requirements
        assert avg_time < 0.0001, f"Average warm cache time {avg_time*1000:.3f}ms exceeds 0.1ms"
        assert p99 < 0.001, f"P99 warm cache time {p99*1000:.3f}ms exceeds 1ms"
        
        # Report
        print(f"\nWarm cache performance:")
        print(f"  Average: {avg_time*1000:.3f}ms")
        print(f"  P50: {p50*1000:.3f}ms")
        print(f"  P95: {p95*1000:.3f}ms")
        print(f"  P99: {p99*1000:.3f}ms")

    def test_environment_switch_performance(self):
        """Benchmark performance of switching between environments."""
        original_env = os.environ.get('ENVIRONMENT', 'development')
        
        try:
            times = []
            environments = ['development', 'testing', 'production']
            
            for env in environments * 10:  # 30 switches
                os.environ['ENVIRONMENT'] = env
                reset_config_cache()
                
                start = time.perf_counter()
                config = get_config()
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                
                assert config.environment == Environment.from_string(env)
            
            avg_switch_time = statistics.mean(times)
            max_switch_time = max(times)
            
            # Performance requirements
            assert avg_switch_time < 0.01, f"Average switch time {avg_switch_time:.3f}s exceeds 10ms"
            assert max_switch_time < 0.05, f"Max switch time {max_switch_time:.3f}s exceeds 50ms"
            
            print(f"\nEnvironment switch performance:")
            print(f"  Average: {avg_switch_time*1000:.2f}ms")
            print(f"  Max: {max_switch_time*1000:.2f}ms")
            
        finally:
            os.environ['ENVIRONMENT'] = original_env


@pytest.mark.production
@pytest.mark.benchmark
class TestValidationPerformance:
    """Benchmark configuration validation performance."""

    def test_basic_validation_speed(self):
        """Benchmark basic configuration validation."""
        factory = EnvironmentFactory()
        config = BaseConfig(Environment.DEVELOPMENT)
        
        # Set some values to validate
        config.mongodb_uri = "mongodb://localhost:27017"
        config.database_name = "test_db"
        config.api_key = "test_key_123"
        config.port = "8080"
        
        # Benchmark validation
        times = []
        for _ in range(100):
            start = time.perf_counter()
            try:
                factory._validate_config(config)
            except:
                pass  # We're testing performance, not correctness
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Performance requirement: < 50ms
        assert avg_time < 0.05, f"Average validation time {avg_time:.3f}s exceeds 50ms"
        assert max_time < 0.1, f"Max validation time {max_time:.3f}s exceeds 100ms"
        
        print(f"\nValidation performance:")
        print(f"  Average: {avg_time*1000:.2f}ms")
        print(f"  Max: {max_time*1000:.2f}ms")

    def test_complex_validation_performance(self):
        """Benchmark validation with many custom validators."""
        # Create custom validators
        def validator1(config): 
            assert hasattr(config, 'environment')
        
        def validator2(config):
            if hasattr(config, 'api_key'):
                assert len(getattr(config, 'api_key', '')) >= 6
        
        def validator3(config):
            if hasattr(config, 'port'):
                port = getattr(config, 'port', None)
                if port:
                    assert 1 <= int(port) <= 65535
        
        validators = [validator1, validator2, validator3] * 10  # 30 validators
        
        from phoenix_real_estate.foundation.config import ConfigurationValidator
        validator = ConfigurationValidator(custom_validators=validators)
        
        # Benchmark
        start = time.perf_counter()
        try:
            validator.validate_environment(Environment.DEVELOPMENT)
        except:
            pass  # Testing performance
        elapsed = time.perf_counter() - start
        
        # Even with 30 validators, should be fast
        assert elapsed < 0.2, f"Complex validation took {elapsed:.3f}s"
        
        print(f"\nComplex validation (30 validators): {elapsed*1000:.2f}ms")


@pytest.mark.production
@pytest.mark.benchmark
class TestConcurrentAccessPerformance:
    """Benchmark concurrent access performance."""

    def test_throughput_10_threads(self):
        """Measure throughput with 10 concurrent threads."""
        reset_config_cache()
        operations_per_thread = []
        duration = 2.0  # Run for 2 seconds
        
        def worker() -> int:
            count = 0
            end_time = time.perf_counter() + duration
            
            while time.perf_counter() < end_time:
                config = get_config()
                _ = config.environment
                _ = getattr(config, 'mongodb_uri', '')
                count += 1
            
            return count
        
        # Run benchmark
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            operations_per_thread = [f.result() for f in futures]
        actual_duration = time.perf_counter() - start
        
        total_operations = sum(operations_per_thread)
        throughput = total_operations / actual_duration
        
        # Performance requirement: > 100,000 ops/sec with 10 threads
        assert throughput > 100000, f"Throughput {throughput:.0f} ops/s below 100k ops/s"
        
        print(f"\n10-thread throughput: {throughput:,.0f} ops/s")
        print(f"  Total operations: {total_operations:,}")
        print(f"  Per thread avg: {statistics.mean(operations_per_thread):,.0f}")

    def test_throughput_scaling(self):
        """Test how throughput scales with thread count."""
        reset_config_cache()
        thread_counts = [1, 2, 4, 8, 16, 32]
        results = []
        
        for thread_count in thread_counts:
            # Run test
            total_ops = 0
            duration = 1.0
            
            def worker() -> int:
                count = 0
                end_time = time.perf_counter() + duration
                while time.perf_counter() < end_time:
                    _ = get_config()
                    count += 1
                return count
            
            start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(worker) for _ in range(thread_count)]
                total_ops = sum(f.result() for f in futures)
            actual_duration = time.perf_counter() - start
            
            throughput = total_ops / actual_duration
            results.append((thread_count, throughput))
        
        # Print scaling report
        print("\nThroughput scaling:")
        baseline = results[0][1]  # Single thread throughput
        for threads, throughput in results:
            scaling = throughput / baseline
            print(f"  {threads:2d} threads: {throughput:8,.0f} ops/s ({scaling:.1f}x scaling)")
        
        # Config access is mostly cached, so we don't expect linear scaling
        # But we should see that it doesn't degrade with more threads
        assert results[-1][1] > results[0][1] * 0.8  # 32 threads should be at least 80% of single thread


@pytest.mark.production
@pytest.mark.benchmark
class TestMemoryEfficiency:
    """Benchmark memory usage and efficiency."""

    def test_memory_overhead_per_config(self):
        """Measure memory overhead of configuration instances."""
        reset_config_cache()
        gc.collect()
        
        # Start memory tracking
        tracemalloc.start()
        
        # Get baseline
        baseline = tracemalloc.take_snapshot()
        
        # Create many config accesses
        configs = []
        for i in range(100):
            if i % 10 == 0:
                reset_config_cache()  # Force new instances
            config = get_config()
            configs.append(config)  # Keep reference
        
        # Take snapshot
        current = tracemalloc.take_snapshot()
        
        # Calculate difference
        stats = current.compare_to(baseline, 'lineno')
        total_memory = sum(stat.size for stat in stats)
        
        # Stop tracking
        tracemalloc.stop()
        
        # Memory per config instance (approximately)
        memory_per_config = total_memory / 10  # We created ~10 unique instances
        
        # Should be reasonable (< 100KB per instance)
        assert memory_per_config < 100 * 1024, f"Config uses {memory_per_config/1024:.1f}KB per instance"
        
        print(f"\nMemory usage:")
        print(f"  Per config instance: ~{memory_per_config/1024:.1f}KB")
        print(f"  Total for 100 accesses: {total_memory/1024:.1f}KB")

    def test_secret_storage_memory_efficiency(self):
        """Test memory efficiency of secret storage."""
        secret_manager = get_secret_manager()
        
        # Clear any existing secrets
        secret_manager._secrets.clear()
        gc.collect()
        
        # Start tracking
        tracemalloc.start()
        baseline = tracemalloc.take_snapshot()
        
        # Store many secrets
        for i in range(1000):
            secret_manager.store_secret(f'SECRET_{i}', f'value_{i}' * 10)  # ~60 bytes each
        
        current = tracemalloc.take_snapshot()
        stats = current.compare_to(baseline, 'lineno')
        total_memory = sum(stat.size for stat in stats)
        
        tracemalloc.stop()
        
        # Calculate overhead
        # Each secret is about 60 bytes of data, but Python dicts have overhead
        expected_data_size = 1000 * 60  # 1000 secrets * ~60 bytes
        overhead = total_memory - expected_data_size
        overhead_ratio = overhead / expected_data_size
        
        # Python dictionaries have significant overhead for keys and structure
        # A more realistic expectation is < 300% overhead
        assert overhead_ratio < 3.0, f"Secret storage overhead {overhead_ratio:.1%} exceeds 300%"
        
        print(f"\nSecret storage efficiency:")
        print(f"  Data size: {expected_data_size/1024:.1f}KB")
        print(f"  Total memory: {total_memory/1024:.1f}KB")
        print(f"  Overhead: {overhead_ratio:.1%}")
        
        # Cleanup
        secret_manager._secrets.clear()


@pytest.mark.production
@pytest.mark.benchmark
class TestCachePerformance:
    """Benchmark caching performance."""

    def test_cache_hit_rate(self):
        """Test cache hit rate under various access patterns."""
        reset_config_cache()
        
        # Pattern 1: Sequential access (should have 100% hit rate)
        cache_misses = 0
        for i in range(1000):
            start = time.perf_counter()
            _ = get_config()
            elapsed = time.perf_counter() - start
            # First access is a miss, rest should be hits
            if elapsed > 0.001:  # Arbitrary threshold for cache miss
                cache_misses += 1
        
        hit_rate = (1000 - cache_misses) / 1000
        assert hit_rate > 0.99, f"Sequential hit rate {hit_rate:.1%} below 99%"
        
        print(f"\nCache performance:")
        print(f"  Sequential hit rate: {hit_rate:.1%}")
        
        # Pattern 2: With periodic resets
        reset_config_cache()
        cache_misses = 0
        for i in range(1000):
            if i % 100 == 0:
                reset_config_cache()
            start = time.perf_counter()
            _ = get_config()
            elapsed = time.perf_counter() - start
            if elapsed > 0.001:
                cache_misses += 1
        
        expected_misses = 10  # Reset every 100, so ~10 misses
        actual_miss_rate = cache_misses / 1000
        expected_miss_rate = expected_misses / 1000
        
        assert abs(actual_miss_rate - expected_miss_rate) < 0.02, \
            f"Unexpected miss rate: {actual_miss_rate:.1%}"
        
        print(f"  With resets hit rate: {(1-actual_miss_rate):.1%}")

    def test_cache_invalidation_performance(self):
        """Test performance of cache invalidation."""
        # Pre-populate cache
        _ = get_config()
        
        # Benchmark cache reset
        times = []
        for _ in range(100):
            start = time.perf_counter()
            reset_config_cache()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            # Re-populate for next iteration
            _ = get_config()
        
        avg_reset_time = statistics.mean(times)
        max_reset_time = max(times)
        
        # Should be very fast
        assert avg_reset_time < 0.0001, f"Average reset time {avg_reset_time*1000:.3f}ms exceeds 0.1ms"
        assert max_reset_time < 0.001, f"Max reset time {max_reset_time*1000:.3f}ms exceeds 1ms"
        
        print(f"\nCache invalidation performance:")
        print(f"  Average: {avg_reset_time*1000:.3f}ms")
        print(f"  Max: {max_reset_time*1000:.3f}ms")


@pytest.mark.production
@pytest.mark.benchmark
class TestComprehensiveBenchmark:
    """Comprehensive benchmark simulating production usage."""

    def test_production_workload_simulation(self):
        """Simulate a realistic production workload."""
        reset_config_cache()
        
        # Workload parameters
        duration = 5.0  # 5 second test
        read_threads = 20
        write_threads = 2
        secret_threads = 5
        
        # Metrics
        metrics = {
            'config_reads': 0,
            'cache_resets': 0,
            'secret_reads': 0,
            'errors': 0
        }
        metrics_lock = threading.Lock()
        
        def config_reader():
            """Simulates service reading configuration."""
            end_time = time.perf_counter() + duration
            while time.perf_counter() < end_time:
                try:
                    config = get_config()
                    _ = config.environment
                    _ = getattr(config, 'mongodb_uri', '')
                    with metrics_lock:
                        metrics['config_reads'] += 1
                except Exception:
                    with metrics_lock:
                        metrics['errors'] += 1
                time.sleep(0.001)  # Simulate work
        
        def cache_manager():
            """Simulates periodic cache invalidation."""
            end_time = time.perf_counter() + duration
            while time.perf_counter() < end_time:
                try:
                    reset_config_cache()
                    with metrics_lock:
                        metrics['cache_resets'] += 1
                except Exception:
                    with metrics_lock:
                        metrics['errors'] += 1
                time.sleep(0.1)  # Reset every 100ms
        
        def secret_reader():
            """Simulates service reading secrets."""
            end_time = time.perf_counter() + duration
            while time.perf_counter() < end_time:
                try:
                    for i in range(10):
                        _ = get_secret(f'SECRET_KEY_{i}', 'default')
                    with metrics_lock:
                        metrics['secret_reads'] += 10
                except Exception:
                    with metrics_lock:
                        metrics['errors'] += 1
                time.sleep(0.005)  # Simulate work
        
        # Run workload
        print("\nRunning production workload simulation...")
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=read_threads + write_threads + secret_threads) as executor:
            futures = []
            
            # Start readers
            for _ in range(read_threads):
                futures.append(executor.submit(config_reader))
            
            # Start cache managers
            for _ in range(write_threads):
                futures.append(executor.submit(cache_manager))
            
            # Start secret readers
            for _ in range(secret_threads):
                futures.append(executor.submit(secret_reader))
            
            # Wait for completion
            concurrent.futures.wait(futures)
        
        actual_duration = time.perf_counter() - start_time
        
        # Calculate rates
        config_read_rate = metrics['config_reads'] / actual_duration
        secret_read_rate = metrics['secret_reads'] / actual_duration
        reset_rate = metrics['cache_resets'] / actual_duration
        
        # Report
        print(f"\nProduction workload results ({actual_duration:.1f}s):")
        print(f"  Config reads: {metrics['config_reads']:,} ({config_read_rate:,.0f}/s)")
        print(f"  Secret reads: {metrics['secret_reads']:,} ({secret_read_rate:,.0f}/s)")
        print(f"  Cache resets: {metrics['cache_resets']:,} ({reset_rate:.1f}/s)")
        print(f"  Errors: {metrics['errors']}")
        
        # Performance requirements
        assert config_read_rate > 10000, f"Config read rate {config_read_rate:.0f}/s below 10k/s"
        assert secret_read_rate > 5000, f"Secret read rate {secret_read_rate:.0f}/s below 5k/s"
        assert metrics['errors'] == 0, f"Errors occurred: {metrics['errors']}"


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup():
    """Clean up after each test."""
    yield
    reset_config_cache()
    gc.collect()