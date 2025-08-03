"""Performance optimization and benchmarking for LLM processing."""

import time
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Deque
from datetime import datetime

from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""

    name: str
    samples: List[Dict[str, Any]] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def add_sample(self, duration: float, success: bool = True, **kwargs) -> None:
        """Add a sample to the benchmark."""
        self.samples.append(
            {"duration": duration, "success": success, "timestamp": time.time(), **kwargs}
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Calculate benchmark statistics."""
        if not self.samples:
            return {
                "count": 0,
                "avg_duration": 0,
                "min_duration": 0,
                "max_duration": 0,
                "p50_duration": 0,
                "p95_duration": 0,
                "success_rate": 0,
            }

        durations = [s["duration"] for s in self.samples]
        successes = [s["success"] for s in self.samples]

        # Sort for percentiles
        sorted_durations = sorted(durations)
        count = len(durations)

        return {
            "count": count,
            "avg_duration": statistics.mean(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p50_duration": sorted_durations[int(count * 0.5)],
            "p95_duration": sorted_durations[int(count * 0.95)] if count > 20 else max(durations),
            "success_rate": sum(successes) / len(successes),
            "total_duration": self.end_time - self.start_time
            if self.end_time and self.start_time
            else 0,
        }

    def compare_to(self, other: "BenchmarkResult") -> Dict[str, Any]:
        """Compare this benchmark to another."""
        self_stats = self.get_statistics()
        other_stats = other.get_statistics()

        if self_stats["count"] == 0 or other_stats["count"] == 0:
            return {"is_improvement": False, "error": "Insufficient data"}

        avg_improvement = (
            (self_stats["avg_duration"] - other_stats["avg_duration"])
            / self_stats["avg_duration"]
            * 100
        )
        p95_improvement = (
            (self_stats["p95_duration"] - other_stats["p95_duration"])
            / self_stats["p95_duration"]
            * 100
        )

        return {
            "avg_improvement_percent": avg_improvement,
            "p95_improvement_percent": p95_improvement,
            "success_rate_change": other_stats["success_rate"] - self_stats["success_rate"],
            "is_improvement": avg_improvement > 0
            and other_stats["success_rate"] >= self_stats["success_rate"],
        }


class PerformanceBenchmark:
    """Context manager for performance benchmarking."""

    def __init__(self, name: str):
        """Initialize benchmark.

        Args:
            name: Benchmark name
        """
        self.name = name
        self.result = BenchmarkResult(name)
        self._operation_start: Optional[float] = None

    async def __aenter__(self) -> "PerformanceBenchmark":
        """Start benchmark."""
        self.result.start_time = time.time()
        self._operation_start = time.time()
        logger.info(f"Starting benchmark: {self.name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """End benchmark."""
        self.result.end_time = time.time()
        logger.info(
            f"Completed benchmark: {self.name} "
            f"(duration: {self.result.end_time - self.result.start_time:.2f}s)"
        )

    def record_operation(self, duration: float, success: bool = True, **kwargs) -> None:
        """Record an operation in the benchmark."""
        self.result.add_sample(duration, success, **kwargs)

    def get_results(self) -> BenchmarkResult:
        """Get benchmark results."""
        return self.result


class BatchSizeOptimizer:
    """Optimizes batch size based on performance metrics."""

    def __init__(self, initial_size: int = 10, min_size: int = 1, max_size: int = 100):
        """Initialize batch size optimizer.

        Args:
            initial_size: Starting batch size
            min_size: Minimum allowed batch size
            max_size: Maximum allowed batch size
        """
        self.current_size = initial_size
        self.min_size = min_size
        self.max_size = max_size

        # Performance history
        self.history: Deque[Dict[str, Any]] = deque(maxlen=20)

        # Optimization parameters
        self.target_duration = 2.0  # Target seconds per item
        self.target_success_rate = 0.9
        self.adjustment_factor = 0.2

    def record_batch_performance(
        self, batch_size: int, duration: float, success_rate: float, memory_usage_mb: float
    ) -> None:
        """Record batch performance metrics.

        Args:
            batch_size: Size of the batch
            duration: Total duration in seconds
            success_rate: Proportion of successful items
            memory_usage_mb: Memory used during processing
        """
        per_item_duration = duration / batch_size if batch_size > 0 else duration

        self.history.append(
            {
                "batch_size": batch_size,
                "duration": duration,
                "per_item_duration": per_item_duration,
                "success_rate": success_rate,
                "memory_usage_mb": memory_usage_mb,
                "timestamp": time.time(),
            }
        )

    def get_optimal_batch_size(self) -> int:
        """Calculate optimal batch size based on history."""
        if len(self.history) < 3:
            return self.current_size

        # Analyze recent performance
        recent = list(self.history)[-5:]

        # Calculate average metrics
        avg_per_item_duration = statistics.mean(h["per_item_duration"] for h in recent)
        avg_success_rate = statistics.mean(h["success_rate"] for h in recent)
        avg_memory = statistics.mean(h["memory_usage_mb"] for h in recent)

        # Determine adjustment direction
        adjustment = 0

        # Performance-based adjustment
        if (
            avg_per_item_duration < self.target_duration * 0.8
            and avg_success_rate > self.target_success_rate
        ):
            # Performance is good, can increase batch size
            adjustment = self.adjustment_factor
        elif (
            avg_per_item_duration > self.target_duration * 1.2
            or avg_success_rate < self.target_success_rate * 0.9
        ):
            # Performance is poor, decrease batch size
            adjustment = -self.adjustment_factor

        # Memory-based adjustment
        if avg_memory > 800:  # High memory usage
            adjustment = min(adjustment, -0.1)

        # Apply adjustment
        new_size = int(self.current_size * (1 + adjustment))
        new_size = max(self.min_size, min(new_size, self.max_size))

        # Gradual change
        if new_size > self.current_size:
            new_size = min(new_size, self.current_size + 5)
        elif new_size < self.current_size:
            new_size = max(new_size, self.current_size - 5)

        self.current_size = new_size

        logger.debug(
            f"Batch size optimization: {self.current_size} "
            f"(per-item: {avg_per_item_duration:.2f}s, success: {avg_success_rate:.2%})"
        )

        return self.current_size


class PerformanceOptimizer:
    """Analyzes performance metrics and provides optimization recommendations."""

    def __init__(self):
        """Initialize performance optimizer."""
        self.metrics_history: Deque[Dict[str, Any]] = deque(maxlen=100)

        # Performance targets
        self.targets = {
            "processing_time": 2.0,  # seconds per property
            "memory_usage": 80,  # percent
            "cpu_usage": 70,  # percent
            "cache_hit_rate": 0.3,  # 30% minimum
            "error_rate": 0.05,  # 5% maximum
            "concurrent_limit": 10,  # maximum concurrent operations
        }

    def analyze_and_recommend(self, metrics: Dict[str, Any]) -> List[str]:
        """Analyze metrics and provide recommendations.

        Args:
            metrics: Current performance metrics

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Processing time
        if metrics.get("avg_processing_time", 0) > self.targets["processing_time"]:
            recommendations.append(
                f"Processing time ({metrics['avg_processing_time']:.1f}s) exceeds target. "
                "Consider: reducing batch size, enabling caching, or optimizing prompts."
            )

        # Memory usage
        if metrics.get("memory_usage_percent", 0) > self.targets["memory_usage"]:
            recommendations.append(
                f"High memory usage ({metrics['memory_usage_percent']:.0f}%). "
                "Consider: reducing batch size, implementing streaming, or increasing memory limits."
            )

        # CPU usage
        if metrics.get("cpu_usage_percent", 0) > self.targets["cpu_usage"]:
            recommendations.append(
                f"High CPU usage ({metrics['cpu_usage_percent']:.0f}%). "
                "Consider: reducing concurrency, optimizing algorithms, or scaling horizontally."
            )

        # Cache performance
        if metrics.get("cache_hit_rate", 0) < self.targets["cache_hit_rate"]:
            recommendations.append(
                f"Low cache hit rate ({metrics.get('cache_hit_rate', 0):.1%}). "
                "Consider: increasing cache size, adjusting TTL, or warming cache with common queries."
            )

        # Error rate
        if metrics.get("error_rate", 0) > self.targets["error_rate"]:
            recommendations.append(
                f"High error rate ({metrics['error_rate']:.1%}). "
                "Consider: implementing retry logic, improving error handling, or checking service health."
            )

        # Concurrency
        if metrics.get("concurrency", 0) > self.targets["concurrent_limit"]:
            recommendations.append(
                f"Exceeding concurrency limit ({metrics['concurrency']}). "
                "Consider: implementing queue throttling or increasing resource allocation."
            )

        # Batch size optimization
        if metrics.get("batch_size", 0) > 0:
            items_per_second = metrics.get("batch_size", 1) / metrics.get("avg_processing_time", 1)
            if items_per_second < 5:
                recommendations.append(
                    f"Low throughput ({items_per_second:.1f} items/sec). "
                    "Consider: parallel processing, batch size optimization, or infrastructure upgrade."
                )

        return recommendations

    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        if not self.metrics_history:
            return {"status": "insufficient_data"}

        # Analyze trends
        recent_metrics = list(self.metrics_history)[-10:]

        # Calculate trends
        processing_times = [m.get("avg_processing_time", 0) for m in recent_metrics]
        memory_usage = [m.get("memory_usage_percent", 0) for m in recent_metrics]
        error_rates = [m.get("error_rate", 0) for m in recent_metrics]

        report = {
            "status": "analyzed",
            "sample_size": len(recent_metrics),
            "trends": {
                "processing_time": {
                    "current": processing_times[-1] if processing_times else 0,
                    "average": statistics.mean(processing_times) if processing_times else 0,
                    "trend": "increasing"
                    if len(processing_times) > 1 and processing_times[-1] > processing_times[0]
                    else "stable",
                },
                "memory_usage": {
                    "current": memory_usage[-1] if memory_usage else 0,
                    "average": statistics.mean(memory_usage) if memory_usage else 0,
                    "peak": max(memory_usage) if memory_usage else 0,
                },
                "error_rate": {
                    "current": error_rates[-1] if error_rates else 0,
                    "average": statistics.mean(error_rates) if error_rates else 0,
                },
            },
            "recommendations": self.analyze_and_recommend(
                recent_metrics[-1] if recent_metrics else {}
            ),
            "timestamp": datetime.now().isoformat(),
        }

        return report


class ConcurrencyOptimizer:
    """Optimizes concurrent processing based on system resources."""

    def __init__(self, initial_concurrency: int = 5):
        """Initialize concurrency optimizer.

        Args:
            initial_concurrency: Starting concurrency level
        """
        self.current_concurrency = initial_concurrency
        self.min_concurrency = 1
        self.max_concurrency = 20

        # Performance tracking
        self.performance_window: Deque[Dict[str, Any]] = deque(maxlen=10)

    def record_performance(
        self,
        concurrency: int,
        avg_response_time: float,
        error_rate: float,
        resource_usage: Dict[str, float],
    ) -> None:
        """Record performance at a given concurrency level."""
        self.performance_window.append(
            {
                "concurrency": concurrency,
                "avg_response_time": avg_response_time,
                "error_rate": error_rate,
                "cpu_usage": resource_usage.get("cpu", 0),
                "memory_usage": resource_usage.get("memory", 0),
                "timestamp": time.time(),
            }
        )

    def get_optimal_concurrency(self) -> int:
        """Calculate optimal concurrency level."""
        if len(self.performance_window) < 3:
            return self.current_concurrency

        # Find the sweet spot balancing throughput and resource usage
        best_score = -1
        best_concurrency = self.current_concurrency

        # Group by concurrency level
        concurrency_groups = {}
        for perf in self.performance_window:
            c = perf["concurrency"]
            if c not in concurrency_groups:
                concurrency_groups[c] = []
            concurrency_groups[c].append(perf)

        for concurrency, perfs in concurrency_groups.items():
            # Calculate average metrics
            avg_response = statistics.mean(p["avg_response_time"] for p in perfs)
            avg_error = statistics.mean(p["error_rate"] for p in perfs)
            avg_cpu = statistics.mean(p["cpu_usage"] for p in perfs)
            avg_memory = statistics.mean(p["memory_usage"] for p in perfs)

            # Score calculation (higher is better)
            # Prioritize low response time and error rate
            throughput_score = 1 / (avg_response + 0.1)  # Avoid division by zero
            reliability_score = 1 - avg_error
            resource_score = 1 - (avg_cpu / 100 + avg_memory / 100) / 2

            # Weighted score
            score = throughput_score * 0.4 + reliability_score * 0.4 + resource_score * 0.2

            if score > best_score:
                best_score = score
                best_concurrency = concurrency

        # Apply gradual adjustment
        if best_concurrency > self.current_concurrency:
            new_concurrency = min(best_concurrency, self.current_concurrency + 2)
        elif best_concurrency < self.current_concurrency:
            new_concurrency = max(best_concurrency, self.current_concurrency - 2)
        else:
            new_concurrency = self.current_concurrency

        # Apply bounds
        new_concurrency = max(self.min_concurrency, min(new_concurrency, self.max_concurrency))

        self.current_concurrency = new_concurrency
        return new_concurrency
