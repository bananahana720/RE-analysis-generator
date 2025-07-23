"""
Comprehensive performance benchmarking suite for Phoenix Real Estate configuration system.

This module provides detailed performance metrics, visual reports, and optimization
recommendations for the configuration system. It complements the existing test_performance.py
with more detailed analysis and actionable insights.

Run with: python -m tests.foundation.config.benchmarks
"""

import concurrent.futures
import gc
import json
import os
import platform
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc
import yaml
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import psutil

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from phoenix_real_estate.foundation.config import (
    get_config,
    reset_config_cache,
    BaseConfig,
    Environment,
    EnvironmentFactory,
    ConfigurationValidator,
    get_secret_manager,
    get_secret,
)


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""

    name: str
    metrics: Dict[str, float]
    raw_data: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def mean(self) -> float:
        """Calculate mean value."""
        return statistics.mean(self.raw_data) if self.raw_data else 0.0

    @property
    def median(self) -> float:
        """Calculate median value."""
        return statistics.median(self.raw_data) if self.raw_data else 0.0

    @property
    def p95(self) -> float:
        """Calculate 95th percentile."""
        if not self.raw_data:
            return 0.0
        return statistics.quantiles(self.raw_data, n=20)[18]

    @property
    def p99(self) -> float:
        """Calculate 99th percentile."""
        if not self.raw_data:
            return 0.0
        return statistics.quantiles(self.raw_data, n=100)[98]

    @property
    def max_value(self) -> float:
        """Get maximum value."""
        return max(self.raw_data) if self.raw_data else 0.0

    @property
    def min_value(self) -> float:
        """Get minimum value."""
        return min(self.raw_data) if self.raw_data else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "samples": len(self.raw_data),
            "mean": self.mean,
            "median": self.median,
            "p95": self.p95,
            "p99": self.p99,
            "min": self.min_value,
            "max": self.max_value,
            "metrics": self.metrics,
        }


class BenchmarkSuite:
    """Comprehensive benchmarking suite for configuration system."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize benchmark suite."""
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[BenchmarkResult] = []
        self.system_info = self._collect_system_info()

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for context."""
        return {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "timestamp": datetime.now().isoformat(),
        }

    def run_all_benchmarks(self) -> None:
        """Run all benchmark categories."""
        print("Phoenix Real Estate Configuration System - Performance Benchmarks")
        print("=" * 70)
        print(f"System: {self.system_info['platform']}")
        print(f"CPU: {self.system_info['cpu_count']} cores")
        print(f"Memory: {self.system_info['memory_gb']:.1f} GB")
        print(f"Python: {self.system_info['python_version']}")
        print("=" * 70)

        # Run benchmarks
        self._benchmark_configuration_load_time()
        self._benchmark_validation_performance()
        self._benchmark_concurrent_access()
        self._benchmark_memory_usage()
        self._benchmark_secret_access()
        self._benchmark_environment_processing()
        self._benchmark_yaml_parsing()
        self._benchmark_cache_efficiency()
        self._benchmark_thread_contention()

        # Generate reports
        self._generate_reports()
        self._generate_optimization_recommendations()

    def _benchmark_configuration_load_time(self) -> None:
        """Benchmark configuration load time in various scenarios."""
        print("\n1. Configuration Load Time Benchmarks")
        print("-" * 50)

        # Cold start benchmark
        print("  Testing cold start performance...")
        cold_times = []
        for i in range(10):
            reset_config_cache()
            gc.collect()

            start = time.perf_counter()
            config = get_config()
            elapsed = time.perf_counter() - start
            cold_times.append(elapsed)

            # Cleanup for next iteration
            del config

        result = BenchmarkResult(
            name="config_cold_start", metrics={"unit": "seconds"}, raw_data=cold_times
        )
        self.results.append(result)
        print(f"    Cold start: {result.mean * 1000:.2f}ms (median: {result.median * 1000:.2f}ms)")

        # Warm cache benchmark
        print("  Testing warm cache performance...")
        get_config()  # Warm up
        warm_times = []
        for _ in range(10000):
            start = time.perf_counter()
            config = get_config()
            elapsed = time.perf_counter() - start
            warm_times.append(elapsed)

        result = BenchmarkResult(
            name="config_warm_cache", metrics={"unit": "seconds"}, raw_data=warm_times
        )
        self.results.append(result)
        print(f"    Warm cache: {result.mean * 1000000:.2f}μs (p99: {result.p99 * 1000000:.2f}μs)")

        # Environment-specific load times
        print("  Testing environment-specific load times...")
        for env in ["development", "testing", "production"]:
            os.environ["ENVIRONMENT"] = env
            reset_config_cache()

            env_times = []
            for _ in range(50):
                reset_config_cache()
                start = time.perf_counter()
                config = get_config()
                elapsed = time.perf_counter() - start
                env_times.append(elapsed)
                assert config.environment == Environment.from_string(env)

            result = BenchmarkResult(
                name=f"config_load_{env}",
                metrics={"unit": "seconds", "environment": env},
                raw_data=env_times,
            )
            self.results.append(result)
            print(f"    {env}: {result.mean * 1000:.2f}ms")

    def _benchmark_validation_performance(self) -> None:
        """Benchmark validation performance with various configurations."""
        print("\n2. Validation Performance Benchmarks")
        print("-" * 50)

        factory = EnvironmentFactory()

        # Simple configuration validation
        print("  Testing simple configuration validation...")
        simple_config = BaseConfig(Environment.DEVELOPMENT)
        simple_config.mongodb_uri = "mongodb://localhost:27017"
        simple_config.database_name = "test_db"

        simple_times = []
        for _ in range(1000):
            start = time.perf_counter()
            try:
                factory._validate_config(simple_config)
            except:
                pass
            elapsed = time.perf_counter() - start
            simple_times.append(elapsed)

        result = BenchmarkResult(
            name="validation_simple",
            metrics={"unit": "seconds", "fields": 2},
            raw_data=simple_times,
        )
        self.results.append(result)
        print(f"    Simple (2 fields): {result.mean * 1000:.3f}ms")

        # Complex configuration validation
        print("  Testing complex configuration validation...")
        complex_config = BaseConfig(Environment.PRODUCTION)
        # Add many fields
        for i in range(50):
            setattr(complex_config, f"field_{i}", f"value_{i}")
        complex_config.mongodb_uri = "mongodb://cluster.example.com:27017"
        complex_config.database_name = "production_db"
        complex_config.api_key = "complex_api_key_12345"
        complex_config.port = "8080"

        complex_times = []
        for _ in range(1000):
            start = time.perf_counter()
            try:
                factory._validate_config(complex_config)
            except:
                pass
            elapsed = time.perf_counter() - start
            complex_times.append(elapsed)

        result = BenchmarkResult(
            name="validation_complex",
            metrics={"unit": "seconds", "fields": 54},
            raw_data=complex_times,
        )
        self.results.append(result)
        print(f"    Complex (54 fields): {result.mean * 1000:.3f}ms")

        # Custom validators performance
        print("  Testing custom validators performance...")
        validators = []
        for i in range(20):

            def validator(config, i=i):
                # Simulate validation work
                assert hasattr(config, "environment")
                if i % 2 == 0:
                    assert config.environment in Environment

            validators.append(validator)

        validator = ConfigurationValidator(custom_validators=validators)
        custom_times = []
        for _ in range(100):
            start = time.perf_counter()
            try:
                validator.validate_environment(Environment.DEVELOPMENT)
            except:
                pass
            elapsed = time.perf_counter() - start
            custom_times.append(elapsed)

        result = BenchmarkResult(
            name="validation_custom",
            metrics={"unit": "seconds", "validators": 20},
            raw_data=custom_times,
        )
        self.results.append(result)
        print(f"    Custom (20 validators): {result.mean * 1000:.3f}ms")

    def _benchmark_concurrent_access(self) -> None:
        """Benchmark concurrent access patterns."""
        print("\n3. Concurrent Access Benchmarks")
        print("-" * 50)

        # Read-heavy workload
        print("  Testing read-heavy concurrent access...")
        reset_config_cache()

        def read_worker(duration: float) -> int:
            count = 0
            end_time = time.perf_counter() + duration
            while time.perf_counter() < end_time:
                config = get_config()
                _ = config.environment
                _ = getattr(config, "mongodb_uri", "")
                count += 1
            return count

        thread_counts = [1, 2, 4, 8, 16, 32, 64]
        for threads in thread_counts:
            duration = 2.0
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = [executor.submit(read_worker, duration) for _ in range(threads)]
                total_ops = sum(f.result() for f in futures)

            throughput = total_ops / duration
            result = BenchmarkResult(
                name=f"concurrent_read_{threads}t",
                metrics={"unit": "ops/sec", "threads": threads},
                raw_data=[throughput],
            )
            self.results.append(result)
            print(f"    {threads:2d} threads: {throughput:,.0f} ops/sec")

        # Mixed read/write workload
        print("  Testing mixed read/write workload...")
        reset_config_cache()

        read_counts = []
        write_counts = []

        def mixed_worker(read_ratio: float, duration: float) -> Tuple[int, int]:
            reads = writes = 0
            end_time = time.perf_counter() + duration

            while time.perf_counter() < end_time:
                if time.perf_counter() % 1 < read_ratio:
                    _ = get_config()
                    reads += 1
                else:
                    reset_config_cache()
                    writes += 1

            return reads, writes

        duration = 2.0
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(mixed_worker, 0.9, duration) for _ in range(16)]
            results = [f.result() for f in futures]
            total_reads = sum(r[0] for r in results)
            total_writes = sum(r[1] for r in results)

        result = BenchmarkResult(
            name="concurrent_mixed",
            metrics={
                "unit": "ops/sec",
                "threads": 16,
                "read_ratio": 0.9,
                "read_throughput": total_reads / duration,
                "write_throughput": total_writes / duration,
            },
            raw_data=[total_reads / duration],
        )
        self.results.append(result)
        print(
            f"    Mixed (90% read): {total_reads / duration:,.0f} reads/sec, {total_writes / duration:,.0f} writes/sec"
        )

    def _benchmark_memory_usage(self) -> None:
        """Benchmark memory usage patterns."""
        print("\n4. Memory Usage Benchmarks")
        print("-" * 50)

        # Startup memory
        print("  Testing startup memory usage...")
        reset_config_cache()
        gc.collect()

        process = psutil.Process()
        startup_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Single config instance
        tracemalloc.start()
        config = get_config()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        single_instance_memory = current / 1024  # KB

        result = BenchmarkResult(
            name="memory_single_instance",
            metrics={"unit": "KB", "startup_mb": startup_memory},
            raw_data=[single_instance_memory],
        )
        self.results.append(result)
        print(f"    Single instance: {single_instance_memory:.1f} KB")

        # Sustained usage
        print("  Testing sustained usage memory...")
        reset_config_cache()
        gc.collect()

        tracemalloc.start()
        baseline = tracemalloc.take_snapshot()

        # Simulate sustained usage
        for i in range(1000):
            if i % 100 == 0:
                reset_config_cache()
            config = get_config()
            _ = config.environment
            _ = get_secret(f"SECRET_{i % 10}", "default")

        current = tracemalloc.take_snapshot()
        stats = current.compare_to(baseline, "lineno")
        sustained_memory = sum(stat.size for stat in stats) / 1024  # KB
        tracemalloc.stop()

        result = BenchmarkResult(
            name="memory_sustained",
            metrics={"unit": "KB", "operations": 1000},
            raw_data=[sustained_memory],
        )
        self.results.append(result)
        print(f"    Sustained (1000 ops): {sustained_memory:.1f} KB")

        # Peak memory under load
        print("  Testing peak memory under load...")
        reset_config_cache()
        gc.collect()

        peak_memory = 0

        def memory_monitor():
            nonlocal peak_memory
            process = psutil.Process()
            while getattr(memory_monitor, "running", True):
                current = process.memory_info().rss / 1024 / 1024  # MB
                peak_memory = max(peak_memory, current)
                time.sleep(0.01)

        # Start monitoring
        memory_monitor.running = True
        monitor_thread = threading.Thread(target=memory_monitor)
        monitor_thread.start()

        # Generate load
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            futures = []
            for _ in range(32):
                futures.append(executor.submit(lambda: [get_config() for _ in range(1000)]))
            concurrent.futures.wait(futures)

        # Stop monitoring
        memory_monitor.running = False
        monitor_thread.join()

        result = BenchmarkResult(
            name="memory_peak", metrics={"unit": "MB", "threads": 32}, raw_data=[peak_memory]
        )
        self.results.append(result)
        print(f"    Peak (32 threads): {peak_memory:.1f} MB")

    def _benchmark_secret_access(self) -> None:
        """Benchmark secret access performance."""
        print("\n5. Secret Access Performance")
        print("-" * 50)

        secret_manager = get_secret_manager()

        # Store test secrets
        for i in range(100):
            secret_manager.store_secret(f"TEST_SECRET_{i}", f"value_{i}" * 10)

        # Direct access
        print("  Testing direct secret access...")
        direct_times = []
        for i in range(10000):
            key = f"TEST_SECRET_{i % 100}"
            start = time.perf_counter()
            value = secret_manager.get_secret(key)
            elapsed = time.perf_counter() - start
            direct_times.append(elapsed)

        result = BenchmarkResult(
            name="secret_direct_access", metrics={"unit": "seconds"}, raw_data=direct_times
        )
        self.results.append(result)
        print(f"    Direct access: {result.mean * 1000000:.2f}μs")

        # Encrypted secret access
        print("  Testing encrypted secret access...")
        secret_manager._secret_key = "test_encryption_key"
        for i in range(10):
            secret_manager.store_secret(f"ENCRYPTED_{i}", f"sensitive_{i}", encrypt=True)

        encrypted_times = []
        for i in range(1000):
            key = f"ENCRYPTED_{i % 10}"
            start = time.perf_counter()
            value = secret_manager.get_secret(key)
            elapsed = time.perf_counter() - start
            encrypted_times.append(elapsed)

        result = BenchmarkResult(
            name="secret_encrypted_access", metrics={"unit": "seconds"}, raw_data=encrypted_times
        )
        self.results.append(result)
        print(f"    Encrypted access: {result.mean * 1000000:.2f}μs")

        # Required secret validation
        print("  Testing required secret validation...")
        validation_times = []
        for i in range(1000):
            key = f"TEST_SECRET_{i % 100}"
            start = time.perf_counter()
            try:
                value = secret_manager.get_required_secret(key)
            except:
                pass
            elapsed = time.perf_counter() - start
            validation_times.append(elapsed)

        result = BenchmarkResult(
            name="secret_required_validation",
            metrics={"unit": "seconds"},
            raw_data=validation_times,
        )
        self.results.append(result)
        print(f"    Required validation: {result.mean * 1000000:.2f}μs")

        # Cleanup
        secret_manager._secrets.clear()
        secret_manager._secret_key = None

    def _benchmark_environment_processing(self) -> None:
        """Benchmark environment variable processing."""
        print("\n6. Environment Variable Processing")
        print("-" * 50)

        # Save original environment
        original_env = dict(os.environ)

        try:
            # Small environment (10 variables)
            print("  Testing small environment (10 vars)...")
            os.environ.clear()
            for i in range(10):
                os.environ[f"TEST_VAR_{i}"] = f"value_{i}"

            small_times = []
            for _ in range(1000):
                start = time.perf_counter()
                config = BaseConfig(Environment.DEVELOPMENT)
                elapsed = time.perf_counter() - start
                small_times.append(elapsed)

            result = BenchmarkResult(
                name="env_processing_small",
                metrics={"unit": "seconds", "variables": 10},
                raw_data=small_times,
            )
            self.results.append(result)
            print(f"    Small environment: {result.mean * 1000:.3f}ms")

            # Large environment (1000 variables)
            print("  Testing large environment (1000 vars)...")
            os.environ.clear()
            for i in range(1000):
                os.environ[f"TEST_VAR_{i}"] = f"value_{i}" * 10

            large_times = []
            for _ in range(100):
                start = time.perf_counter()
                config = BaseConfig(Environment.DEVELOPMENT)
                elapsed = time.perf_counter() - start
                large_times.append(elapsed)

            result = BenchmarkResult(
                name="env_processing_large",
                metrics={"unit": "seconds", "variables": 1000},
                raw_data=large_times,
            )
            self.results.append(result)
            print(f"    Large environment: {result.mean * 1000:.3f}ms")

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def _benchmark_yaml_parsing(self) -> None:
        """Benchmark YAML parsing performance."""
        print("\n7. YAML Parsing Performance")
        print("-" * 50)

        # Create test YAML files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Small YAML file
            small_yaml = tmppath / "small.yaml"
            small_data = {
                "database": {"host": "localhost", "port": 27017},
                "api": {"key": "test_key", "timeout": 30},
            }
            with open(small_yaml, "w") as f:
                yaml.dump(small_data, f)

            print("  Testing small YAML parsing...")
            small_times = []
            for _ in range(1000):
                start = time.perf_counter()
                with open(small_yaml, "r") as f:
                    data = yaml.safe_load(f)
                elapsed = time.perf_counter() - start
                small_times.append(elapsed)

            result = BenchmarkResult(
                name="yaml_parse_small",
                metrics={"unit": "seconds", "size_bytes": small_yaml.stat().st_size},
                raw_data=small_times,
            )
            self.results.append(result)
            print(f"    Small YAML ({result.metrics['size_bytes']}B): {result.mean * 1000:.3f}ms")

            # Large YAML file
            large_yaml = tmppath / "large.yaml"
            large_data = {
                f"service_{i}": {
                    "host": f"service{i}.example.com",
                    "port": 8000 + i,
                    "config": {f"param_{j}": f"value_{j}" for j in range(20)},
                }
                for i in range(100)
            }
            with open(large_yaml, "w") as f:
                yaml.dump(large_data, f)

            print("  Testing large YAML parsing...")
            large_times = []
            for _ in range(100):
                start = time.perf_counter()
                with open(large_yaml, "r") as f:
                    data = yaml.safe_load(f)
                elapsed = time.perf_counter() - start
                large_times.append(elapsed)

            result = BenchmarkResult(
                name="yaml_parse_large",
                metrics={"unit": "seconds", "size_bytes": large_yaml.stat().st_size},
                raw_data=large_times,
            )
            self.results.append(result)
            print(
                f"    Large YAML ({result.metrics['size_bytes'] / 1024:.1f}KB): {result.mean * 1000:.3f}ms"
            )

    def _benchmark_cache_efficiency(self) -> None:
        """Benchmark cache efficiency metrics."""
        print("\n8. Cache Efficiency Metrics")
        print("-" * 50)

        # Cache hit ratio under different patterns
        patterns = [
            ("sequential", lambda i: "development"),
            ("round_robin", lambda i: ["development", "testing", "production"][i % 3]),
            ("random", lambda i: ["development", "testing", "production"][hash(i) % 3]),
        ]

        for pattern_name, pattern_func in patterns:
            print(f"  Testing {pattern_name} access pattern...")
            reset_config_cache()

            cache_times = []
            for i in range(1000):
                env = pattern_func(i)
                os.environ["ENVIRONMENT"] = env

                start = time.perf_counter()
                config = get_config()
                elapsed = time.perf_counter() - start
                cache_times.append(elapsed)

            # Calculate cache efficiency
            sorted_times = sorted(cache_times)
            fast_threshold = sorted_times[int(len(sorted_times) * 0.1)]  # 10th percentile
            cache_hits = sum(1 for t in cache_times if t <= fast_threshold)
            hit_ratio = cache_hits / len(cache_times)

            result = BenchmarkResult(
                name=f"cache_efficiency_{pattern_name}",
                metrics={"unit": "seconds", "pattern": pattern_name, "hit_ratio": hit_ratio},
                raw_data=cache_times,
            )
            self.results.append(result)
            print(
                f"    {pattern_name}: {hit_ratio * 100:.1f}% hit rate, {result.mean * 1000:.3f}ms avg"
            )

        # Cache invalidation overhead
        print("  Testing cache invalidation overhead...")
        invalidation_times = []
        for _ in range(1000):
            # Populate cache
            _ = get_config()

            start = time.perf_counter()
            reset_config_cache()
            elapsed = time.perf_counter() - start
            invalidation_times.append(elapsed)

        result = BenchmarkResult(
            name="cache_invalidation", metrics={"unit": "seconds"}, raw_data=invalidation_times
        )
        self.results.append(result)
        print(f"    Invalidation overhead: {result.mean * 1000000:.2f}μs")

    def _benchmark_thread_contention(self) -> None:
        """Benchmark thread contention analysis."""
        print("\n9. Thread Contention Analysis")
        print("-" * 50)

        # Measure lock contention
        print("  Testing lock contention with increasing threads...")

        contention_results = []
        for thread_count in [1, 2, 4, 8, 16, 32, 64]:
            reset_config_cache()

            # Measure time spent waiting for locks
            wait_times = []
            operation_times = []

            def contention_worker():
                for _ in range(100):
                    op_start = time.perf_counter()

                    # This operation requires lock
                    config = get_config()
                    reset_config_cache()

                    op_end = time.perf_counter()
                    operation_times.append(op_end - op_start)

            # Run workers
            start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(contention_worker) for _ in range(thread_count)]
                concurrent.futures.wait(futures)
            total_time = time.perf_counter() - start

            avg_op_time = statistics.mean(operation_times) if operation_times else 0
            ops_per_sec = len(operation_times) / total_time if total_time > 0 else 0

            result = BenchmarkResult(
                name=f"thread_contention_{thread_count}t",
                metrics={
                    "unit": "seconds",
                    "threads": thread_count,
                    "ops_per_sec": ops_per_sec,
                    "efficiency": ops_per_sec / (thread_count * 100 / total_time)
                    if total_time > 0
                    else 0,
                },
                raw_data=[avg_op_time],
            )
            self.results.append(result)
            contention_results.append((thread_count, ops_per_sec))
            print(
                f"    {thread_count:2d} threads: {ops_per_sec:,.0f} ops/sec (efficiency: {result.metrics['efficiency'] * 100:.1f}%)"
            )

        # Analyze scaling efficiency
        baseline_ops = contention_results[0][1]
        print("\n  Scaling efficiency analysis:")
        for threads, ops in contention_results:
            ideal_ops = baseline_ops * threads
            efficiency = (ops / ideal_ops * 100) if ideal_ops > 0 else 0
            print(f"    {threads:2d} threads: {efficiency:.1f}% of ideal linear scaling")

    def _generate_reports(self) -> None:
        """Generate comprehensive benchmark reports."""
        print("\n" + "=" * 70)
        print("GENERATING REPORTS")
        print("=" * 70)

        # JSON report
        json_report = {
            "system_info": self.system_info,
            "benchmarks": [r.to_dict() for r in self.results],
            "summary": self._generate_summary(),
        }

        json_path = (
            self.output_dir / f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(json_path, "w") as f:
            json.dump(json_report, f, indent=2)
        print(f"  JSON report saved to: {json_path}")

        # Markdown report
        md_path = (
            self.output_dir / f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(md_path, "w") as f:
            f.write(self._generate_markdown_report())
        print(f"  Markdown report saved to: {md_path}")

        # Performance dashboard (ASCII art visualization)
        self._print_performance_dashboard()

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate performance summary."""
        summary = {
            "total_benchmarks": len(self.results),
            "performance_scores": {},
            "bottlenecks": [],
            "strengths": [],
        }

        # Calculate performance scores
        for result in self.results:
            if "cold_start" in result.name:
                score = 100 if result.mean < 0.1 else 50 if result.mean < 0.2 else 0
                summary["performance_scores"]["cold_start"] = score
                if score < 50:
                    summary["bottlenecks"].append(f"Cold start time: {result.mean * 1000:.0f}ms")
                else:
                    summary["strengths"].append(f"Fast cold start: {result.mean * 1000:.0f}ms")

            elif "warm_cache" in result.name:
                score = 100 if result.mean < 0.0001 else 50 if result.mean < 0.001 else 0
                summary["performance_scores"]["warm_cache"] = score
                if score == 100:
                    summary["strengths"].append(
                        f"Excellent cache performance: {result.mean * 1000000:.0f}μs"
                    )

            elif "concurrent_read_64t" in result.name:
                throughput = result.raw_data[0] if result.raw_data else 0
                score = 100 if throughput > 1000000 else 50 if throughput > 100000 else 0
                summary["performance_scores"]["concurrency"] = score
                if score < 50:
                    summary["bottlenecks"].append(
                        f"Limited concurrency: {throughput:.0f} ops/sec with 64 threads"
                    )

        return summary

    def _generate_markdown_report(self) -> str:
        """Generate detailed markdown report."""
        report = []
        report.append("# Phoenix Real Estate Configuration System - Performance Report")
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\nSystem: {self.system_info['platform']}")
        report.append(
            f"CPU: {self.system_info['cpu_count']} cores | Memory: {self.system_info['memory_gb']:.1f} GB"
        )

        # Summary section
        summary = self._generate_summary()
        report.append("\n## Executive Summary")

        if summary["strengths"]:
            report.append("\n### Strengths")
            for strength in summary["strengths"]:
                report.append(f"- ✅ {strength}")

        if summary["bottlenecks"]:
            report.append("\n### Bottlenecks")
            for bottleneck in summary["bottlenecks"]:
                report.append(f"- ⚠️ {bottleneck}")

        # Detailed results
        report.append("\n## Detailed Results")

        categories = defaultdict(list)
        for result in self.results:
            category = result.name.split("_")[0]
            categories[category].append(result)

        for category, results in categories.items():
            report.append(f"\n### {category.title()} Performance")
            report.append("\n| Metric | Mean | Median | P95 | P99 | Max |")
            report.append("|--------|------|--------|-----|-----|-----|")

            for result in results:
                unit = result.metrics.get("unit", "ms")
                multiplier = 1000 if unit == "seconds" else 1
                unit_label = "ms" if unit == "seconds" else unit

                report.append(
                    f"| {result.name} | "
                    f"{result.mean * multiplier:.2f}{unit_label} | "
                    f"{result.median * multiplier:.2f}{unit_label} | "
                    f"{result.p95 * multiplier:.2f}{unit_label} | "
                    f"{result.p99 * multiplier:.2f}{unit_label} | "
                    f"{result.max_value * multiplier:.2f}{unit_label} |"
                )

        return "\n".join(report)

    def _print_performance_dashboard(self) -> None:
        """Print ASCII performance dashboard."""
        print("\n" + "=" * 70)
        print("PERFORMANCE DASHBOARD")
        print("=" * 70)

        # Find key metrics
        cold_start = next((r for r in self.results if r.name == "config_cold_start"), None)
        warm_cache = next((r for r in self.results if r.name == "config_warm_cache"), None)
        concurrent = next((r for r in self.results if r.name == "concurrent_read_64t"), None)

        if cold_start:
            self._print_metric_bar("Cold Start", cold_start.mean * 1000, 100, "ms", target=50)

        if warm_cache:
            self._print_metric_bar("Warm Cache", warm_cache.mean * 1000000, 100, "μs", target=50)

        if concurrent:
            throughput = concurrent.raw_data[0] if concurrent.raw_data else 0
            self._print_metric_bar("Concurrency", throughput / 1000, 1000, "k ops/s", target=500)

    def _print_metric_bar(
        self, name: str, value: float, max_value: float, unit: str, target: float = None
    ) -> None:
        """Print a visual metric bar."""
        bar_width = 40
        filled = int((value / max_value) * bar_width)
        filled = min(filled, bar_width)  # Cap at bar width

        bar = "█" * filled + "░" * (bar_width - filled)

        status = "✅" if target and value <= target else "⚠️" if target else "📊"

        print(f"{status} {name:12s} [{bar}] {value:.1f}{unit}")
        if target:
            print(f"   {'':12s}  {'':40s} (target: {target}{unit})")

    def _generate_optimization_recommendations(self) -> None:
        """Generate actionable optimization recommendations."""
        print("\n" + "=" * 70)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 70)

        recommendations = []

        # Analyze results and generate recommendations
        for result in self.results:
            if "cold_start" in result.name and result.mean > 0.1:
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "area": "Cold Start Performance",
                        "issue": f"Cold start time is {result.mean * 1000:.0f}ms (target: <100ms)",
                        "recommendations": [
                            "Pre-load environment files at application startup",
                            "Use lazy loading for non-critical configuration",
                            "Consider caching parsed YAML files",
                            "Optimize file I/O operations",
                        ],
                    }
                )

            if "validation" in result.name and result.mean > 0.01:
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "area": "Validation Performance",
                        "issue": f"Validation takes {result.mean * 1000:.0f}ms",
                        "recommendations": [
                            "Cache validation results for unchanged configs",
                            "Use async validation for non-critical fields",
                            "Optimize regex patterns in validators",
                            "Consider compile-time validation where possible",
                        ],
                    }
                )

            if "concurrent" in result.name and "efficiency" in result.metrics:
                if result.metrics["efficiency"] < 0.5:
                    recommendations.append(
                        {
                            "priority": "HIGH",
                            "area": "Concurrency",
                            "issue": f"Thread efficiency is {result.metrics['efficiency'] * 100:.0f}%",
                            "recommendations": [
                                "Reduce lock contention with read-write locks",
                                "Use thread-local storage for frequently accessed data",
                                "Consider lock-free data structures",
                                "Implement connection pooling for shared resources",
                            ],
                        }
                    )

            if "memory" in result.name and "peak" in result.name:
                if result.raw_data and result.raw_data[0] > 100:  # 100MB
                    recommendations.append(
                        {
                            "priority": "MEDIUM",
                            "area": "Memory Usage",
                            "issue": f"Peak memory usage is {result.raw_data[0]:.0f}MB",
                            "recommendations": [
                                "Implement object pooling for configurations",
                                "Use weak references for cached objects",
                                "Add memory limits to cache size",
                                "Profile memory allocations with tracemalloc",
                            ],
                        }
                    )

        # Print recommendations
        if not recommendations:
            print("✅ No significant performance issues detected!")
            print("   The configuration system is performing well.")
        else:
            # Sort by priority
            priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))

            for rec in recommendations:
                print(f"\n{rec['priority']} Priority - {rec['area']}")
                print(f"Issue: {rec['issue']}")
                print("Recommendations:")
                for r in rec["recommendations"]:
                    print(f"  • {r}")

        # General best practices
        print("\n" + "-" * 70)
        print("GENERAL BEST PRACTICES")
        print("-" * 70)
        print("1. Monitor performance metrics in production")
        print("2. Set up alerts for performance degradation")
        print("3. Run benchmarks after significant changes")
        print("4. Consider A/B testing for optimization changes")
        print("5. Profile before optimizing - measure twice, cut once")


def main():
    """Run the benchmark suite."""
    # Create output directory
    output_dir = Path("benchmark_results")
    output_dir.mkdir(exist_ok=True)

    # Run benchmarks
    suite = BenchmarkSuite(output_dir)
    suite.run_all_benchmarks()

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)
    print(f"Results saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
