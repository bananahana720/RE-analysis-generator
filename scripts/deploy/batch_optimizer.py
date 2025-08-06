#!/usr/bin/env python3
"""Batch Processing Optimization System.

Advanced batch processing optimization for Phoenix Real Estate data collection
with adaptive batch sizing, resource monitoring, and performance tuning.

Features:
- Adaptive batch size optimization based on system performance
- Resource utilization monitoring and adjustment
- Cost-aware batch processing to minimize expenses
- Performance benchmarking and continuous improvement
- Intelligent queue management and priority scheduling
"""

import asyncio
import json
import math
import statistics
from datetime import datetime, UTC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, NamedTuple
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class BatchMetrics(NamedTuple):
    """Batch processing performance metrics."""

    batch_size: int
    processing_time: float
    throughput: float  # items per second
    success_rate: float
    resource_usage: Dict[str, float]  # cpu, memory, etc.
    cost_estimate: float
    timestamp: datetime


class OptimizationRecommendation(NamedTuple):
    """Batch optimization recommendation."""

    parameter: str
    current_value: Any
    recommended_value: Any
    expected_improvement: float  # percentage
    confidence: float  # 0-1
    rationale: str


@dataclass
class BatchConfiguration:
    """Batch processing configuration."""

    batch_size: int = 20
    concurrent_batches: int = 2
    timeout_seconds: int = 300
    retry_attempts: int = 3
    priority_threshold: float = 0.8
    resource_limits: Dict[str, float] = field(
        default_factory=lambda: {
            "max_cpu_percent": 75.0,
            "max_memory_percent": 80.0,
            "max_concurrent_requests": 10,
        }
    )
    cost_constraints: Dict[str, float] = field(
        default_factory=lambda: {"max_cost_per_batch": 0.50, "daily_budget_limit": 5.00}
    )


class BatchOptimizer:
    """Intelligent batch processing optimization system."""

    def __init__(self, config_provider: EnvironmentConfigProvider):
        """Initialize batch optimizer.

        Args:
            config_provider: Configuration provider instance
        """
        self.config = config_provider
        self.metrics_history: List[BatchMetrics] = []
        self.optimization_history: List[OptimizationRecommendation] = []

        # Storage
        self.metrics_file = Path("data/optimization/batch_metrics.json")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # Default configuration
        self.current_config = BatchConfiguration()

        # Performance baselines
        self.baseline_metrics = {
            "throughput": 16.67,  # properties per minute (1000/hour)
            "success_rate": 0.95,
            "cost_per_property": 0.005,  # $0.005 per property
            "response_time": 2.0,  # seconds average
        }

        # Optimization parameters
        self.optimization_window = 100  # metrics to consider
        self.min_batch_size = 5
        self.max_batch_size = 100
        self.adaptation_rate = 0.1  # how quickly to adapt

    async def analyze_batch_performance(self, batch_results: List[Dict[str, Any]]) -> BatchMetrics:
        """Analyze batch processing performance.

        Args:
            batch_results: List of batch processing results

        Returns:
            Batch performance metrics
        """
        if not batch_results:
            return BatchMetrics(
                batch_size=0,
                processing_time=0.0,
                throughput=0.0,
                success_rate=0.0,
                resource_usage={},
                cost_estimate=0.0,
                timestamp=datetime.now(UTC),
            )

        # Calculate metrics
        total_items = sum(len(batch.get("items", [])) for batch in batch_results)
        total_time = sum(batch.get("processing_time", 0) for batch in batch_results)
        successful_items = sum(batch.get("successful_count", 0) for batch in batch_results)

        avg_batch_size = total_items / len(batch_results) if batch_results else 0
        throughput = total_items / total_time if total_time > 0 else 0
        success_rate = successful_items / total_items if total_items > 0 else 0

        # Estimate resource usage (simplified)
        resource_usage = {
            "cpu_percent": min(70.0, avg_batch_size * 2.5),
            "memory_mb": min(1000.0, avg_batch_size * 15),
            "network_mbps": min(50.0, avg_batch_size * 0.8),
        }

        # Estimate costs
        cost_estimate = self._estimate_batch_cost(avg_batch_size, total_time)

        metrics = BatchMetrics(
            batch_size=int(avg_batch_size),
            processing_time=total_time,
            throughput=throughput,
            success_rate=success_rate,
            resource_usage=resource_usage,
            cost_estimate=cost_estimate,
            timestamp=datetime.now(UTC),
        )

        # Store metrics
        self.metrics_history.append(metrics)
        await self._save_metrics()

        return metrics

    async def optimize_batch_size(self) -> OptimizationRecommendation:
        """Optimize batch size based on performance history.

        Returns:
            Optimization recommendation for batch size
        """
        if len(self.metrics_history) < 5:
            return OptimizationRecommendation(
                parameter="batch_size",
                current_value=self.current_config.batch_size,
                recommended_value=self.current_config.batch_size,
                expected_improvement=0.0,
                confidence=0.0,
                rationale="Insufficient data for optimization",
            )

        # Analyze recent performance
        recent_metrics = self.metrics_history[-self.optimization_window :]

        # Find optimal batch size based on throughput vs cost
        optimal_size = await self._find_optimal_batch_size(recent_metrics)

        # Calculate expected improvement
        current_performance = self._calculate_performance_score(self.current_config.batch_size)
        optimal_performance = self._calculate_performance_score(optimal_size)

        improvement = ((optimal_performance - current_performance) / current_performance) * 100
        confidence = min(0.95, len(recent_metrics) / self.optimization_window)

        recommendation = OptimizationRecommendation(
            parameter="batch_size",
            current_value=self.current_config.batch_size,
            recommended_value=optimal_size,
            expected_improvement=improvement,
            confidence=confidence,
            rationale=f"Analysis of {len(recent_metrics)} recent batches suggests "
            f"batch size {optimal_size} will improve throughput by {improvement:.1f}%",
        )

        self.optimization_history.append(recommendation)
        return recommendation

    async def optimize_concurrency(self) -> OptimizationRecommendation:
        """Optimize concurrent batch processing.

        Returns:
            Optimization recommendation for concurrency
        """
        if not self.metrics_history:
            return OptimizationRecommendation(
                parameter="concurrent_batches",
                current_value=self.current_config.concurrent_batches,
                recommended_value=self.current_config.concurrent_batches,
                expected_improvement=0.0,
                confidence=0.0,
                rationale="No performance data available",
            )

        # Analyze resource utilization
        recent_metrics = self.metrics_history[-20:]  # Last 20 batches
        avg_cpu = statistics.mean(m.resource_usage.get("cpu_percent", 50) for m in recent_metrics)
        avg_memory = statistics.mean(m.resource_usage.get("memory_mb", 500) for m in recent_metrics)

        # Determine optimal concurrency based on resource usage
        optimal_concurrency = self._calculate_optimal_concurrency(avg_cpu, avg_memory)

        improvement = self._estimate_concurrency_improvement(optimal_concurrency)
        confidence = 0.8 if len(recent_metrics) >= 10 else 0.5

        return OptimizationRecommendation(
            parameter="concurrent_batches",
            current_value=self.current_config.concurrent_batches,
            recommended_value=optimal_concurrency,
            expected_improvement=improvement,
            confidence=confidence,
            rationale=f"Based on {avg_cpu:.1f}% CPU and {avg_memory:.0f}MB memory usage, "
            f"{optimal_concurrency} concurrent batches should improve performance by {improvement:.1f}%",
        )

    async def optimize_resource_allocation(self) -> List[OptimizationRecommendation]:
        """Optimize resource allocation for batch processing.

        Returns:
            List of resource optimization recommendations
        """
        recommendations = []

        if not self.metrics_history:
            return recommendations

        recent_metrics = self.metrics_history[-30:]  # Last 30 batches

        # Memory optimization
        memory_usage = [m.resource_usage.get("memory_mb", 0) for m in recent_metrics]
        if memory_usage:
            avg_memory = statistics.mean(memory_usage)
            max_memory = max(memory_usage)

            if max_memory > 800:  # High memory usage
                recommendations.append(
                    OptimizationRecommendation(
                        parameter="memory_optimization",
                        current_value=f"{avg_memory:.0f}MB average",
                        recommended_value="Implement memory cleanup between batches",
                        expected_improvement=15.0,
                        confidence=0.7,
                        rationale=f"High memory usage ({max_memory:.0f}MB peak) indicates need for cleanup",
                    )
                )

        # CPU optimization
        cpu_usage = [m.resource_usage.get("cpu_percent", 0) for m in recent_metrics]
        if cpu_usage:
            avg_cpu = statistics.mean(cpu_usage)

            if avg_cpu < 40:  # Low CPU usage
                recommendations.append(
                    OptimizationRecommendation(
                        parameter="cpu_optimization",
                        current_value=f"{avg_cpu:.1f}% average",
                        recommended_value="Increase batch size or concurrency",
                        expected_improvement=25.0,
                        confidence=0.8,
                        rationale=f"Low CPU utilization ({avg_cpu:.1f}%) suggests room for increased throughput",
                    )
                )
            elif avg_cpu > 80:  # High CPU usage
                recommendations.append(
                    OptimizationRecommendation(
                        parameter="cpu_optimization",
                        current_value=f"{avg_cpu:.1f}% average",
                        recommended_value="Reduce batch size or add processing delays",
                        expected_improvement=10.0,
                        confidence=0.9,
                        rationale=f"High CPU utilization ({avg_cpu:.1f}%) may cause system instability",
                    )
                )

        return recommendations

    async def generate_optimization_report(self) -> str:
        """Generate comprehensive optimization report.

        Returns:
            Formatted optimization report
        """
        if not self.metrics_history:
            return "No batch processing data available for optimization analysis."

        recent_metrics = self.metrics_history[-30:]  # Last 30 batches

        # Calculate performance statistics
        throughputs = [m.throughput for m in recent_metrics]
        success_rates = [m.success_rate for m in recent_metrics]
        processing_times = [m.processing_time for m in recent_metrics]
        costs = [m.cost_estimate for m in recent_metrics]

        avg_throughput = statistics.mean(throughputs) if throughputs else 0
        avg_success_rate = statistics.mean(success_rates) if success_rates else 0
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0
        total_cost = sum(costs) if costs else 0

        # Get optimization recommendations
        batch_size_rec = await self.optimize_batch_size()
        concurrency_rec = await self.optimize_concurrency()
        resource_recs = await self.optimize_resource_allocation()

        report = f"""
# Phoenix Real Estate - Batch Processing Optimization Report
**Generated**: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Analysis Period**: Last {len(recent_metrics)} batches

## 📈 Current Performance Metrics
- **Average Throughput**: {avg_throughput:.2f} properties/second
- **Success Rate**: {avg_success_rate:.1%}
- **Average Processing Time**: {avg_processing_time:.2f} seconds
- **Total Processing Cost**: ${total_cost:.4f}
- **Properties per Hour**: {avg_throughput * 3600:.0f}

## ⚙️ Current Configuration
- **Batch Size**: {self.current_config.batch_size} properties
- **Concurrent Batches**: {self.current_config.concurrent_batches}
- **Timeout**: {self.current_config.timeout_seconds} seconds
- **Max CPU**: {self.current_config.resource_limits["max_cpu_percent"]:.1f}%
- **Max Memory**: {self.current_config.resource_limits["max_memory_percent"]:.1f}%

## 🎯 Optimization Recommendations

### 1. Batch Size Optimization
- **Current**: {batch_size_rec.current_value} properties
- **Recommended**: {batch_size_rec.recommended_value} properties
- **Expected Improvement**: {batch_size_rec.expected_improvement:.1f}%
- **Confidence**: {batch_size_rec.confidence:.1%}
- **Rationale**: {batch_size_rec.rationale}

### 2. Concurrency Optimization
- **Current**: {concurrency_rec.current_value} concurrent batches
- **Recommended**: {concurrency_rec.recommended_value} concurrent batches
- **Expected Improvement**: {concurrency_rec.expected_improvement:.1f}%
- **Confidence**: {concurrency_rec.confidence:.1%}
- **Rationale**: {concurrency_rec.rationale}
"""

        if resource_recs:
            report += "\n### 3. Resource Optimizations\n"
            for i, rec in enumerate(resource_recs, 1):
                report += f"\n**{i}. {rec.parameter.title()}**\n"
                report += f"- **Current**: {rec.current_value}\n"
                report += f"- **Recommended**: {rec.recommended_value}\n"
                report += f"- **Expected Improvement**: {rec.expected_improvement:.1f}%\n"
                report += f"- **Rationale**: {rec.rationale}\n"

        # Performance comparison with baselines
        report += "\n## 📉 Performance vs Baseline\n"
        throughput_vs_baseline = (avg_throughput * 60) / self.baseline_metrics["throughput"]
        success_vs_baseline = avg_success_rate / self.baseline_metrics["success_rate"]

        report += f"- **Throughput**: {throughput_vs_baseline:.1%} of baseline ({self.baseline_metrics['throughput']:.1f} props/min)\n"
        report += f"- **Success Rate**: {success_vs_baseline:.1%} of baseline ({self.baseline_metrics['success_rate']:.1%})\n"

        # Cost efficiency analysis
        if costs:
            avg_cost_per_item = statistics.mean(
                [c / m.batch_size for c, m in zip(costs, recent_metrics) if m.batch_size > 0]
            )
            cost_efficiency = (
                self.baseline_metrics["cost_per_property"] / avg_cost_per_item
                if avg_cost_per_item > 0
                else 0
            )
            report += f"- **Cost Efficiency**: {cost_efficiency:.1%} of baseline (${self.baseline_metrics['cost_per_property']:.4f}/property)\n"

        return report

    async def apply_recommendations(
        self, recommendations: List[OptimizationRecommendation]
    ) -> BatchConfiguration:
        """Apply optimization recommendations to configuration.

        Args:
            recommendations: List of recommendations to apply

        Returns:
            Updated batch configuration
        """
        new_config = BatchConfiguration(
            batch_size=self.current_config.batch_size,
            concurrent_batches=self.current_config.concurrent_batches,
            timeout_seconds=self.current_config.timeout_seconds,
            retry_attempts=self.current_config.retry_attempts,
            priority_threshold=self.current_config.priority_threshold,
            resource_limits=self.current_config.resource_limits.copy(),
            cost_constraints=self.current_config.cost_constraints.copy(),
        )

        for rec in recommendations:
            # Only apply high-confidence recommendations
            if rec.confidence < 0.6:
                logger.info(f"Skipping low-confidence recommendation: {rec.parameter}")
                continue

            if rec.parameter == "batch_size":
                new_config.batch_size = min(
                    self.max_batch_size, max(self.min_batch_size, rec.recommended_value)
                )
                logger.info(
                    f"Updated batch size: {self.current_config.batch_size} -> {new_config.batch_size}"
                )

            elif rec.parameter == "concurrent_batches":
                new_config.concurrent_batches = max(1, min(5, rec.recommended_value))
                logger.info(
                    f"Updated concurrency: {self.current_config.concurrent_batches} -> {new_config.concurrent_batches}"
                )

        self.current_config = new_config
        return new_config

    def _estimate_batch_cost(self, batch_size: int, processing_time: float) -> float:
        """Estimate cost for a batch processing operation.

        Args:
            batch_size: Number of items in batch
            processing_time: Processing time in seconds

        Returns:
            Estimated cost in dollars
        """
        # Cost components
        api_cost = batch_size * 0.001  # $0.001 per API call
        compute_cost = (processing_time / 3600) * 0.05  # $0.05 per compute hour
        llm_cost = batch_size * 0.002  # $0.002 per LLM request

        return api_cost + compute_cost + llm_cost

    async def _find_optimal_batch_size(self, metrics: List[BatchMetrics]) -> int:
        """Find optimal batch size based on metrics.

        Args:
            metrics: List of batch metrics to analyze

        Returns:
            Optimal batch size
        """
        if not metrics:
            return self.current_config.batch_size

        # Group metrics by batch size and calculate average performance
        size_performance = {}
        for metric in metrics:
            size = metric.batch_size
            if size not in size_performance:
                size_performance[size] = []

            # Calculate performance score (throughput / cost)
            score = metric.throughput / (metric.cost_estimate + 0.001)  # Avoid division by zero
            size_performance[size].append(score)

        # Find size with best average performance
        best_size = self.current_config.batch_size
        best_score = 0

        for size, scores in size_performance.items():
            avg_score = statistics.mean(scores)
            if avg_score > best_score and self.min_batch_size <= size <= self.max_batch_size:
                best_score = avg_score
                best_size = size

        return best_size

    def _calculate_performance_score(self, batch_size: int) -> float:
        """Calculate performance score for a given batch size.

        Args:
            batch_size: Batch size to evaluate

        Returns:
            Performance score
        """
        # Estimate performance based on batch size
        # Larger batches are more efficient but have diminishing returns
        efficiency = min(1.0, batch_size / 50)  # Peaks at size 50
        throughput_factor = math.log(batch_size + 1) / math.log(101)  # Logarithmic scaling

        return efficiency * throughput_factor * 100

    def _calculate_optimal_concurrency(self, avg_cpu: float, avg_memory: float) -> int:
        """Calculate optimal concurrency based on resource usage.

        Args:
            avg_cpu: Average CPU usage percentage
            avg_memory: Average memory usage in MB

        Returns:
            Optimal concurrency level
        """
        # Base concurrency on available resources
        cpu_limit = self.current_config.resource_limits["max_cpu_percent"]
        memory_limit_mb = 2000  # Assume 2GB memory limit

        # Calculate how many more processes we can handle
        cpu_headroom = max(0, cpu_limit - avg_cpu) / avg_cpu if avg_cpu > 0 else 1
        memory_headroom = max(0, memory_limit_mb - avg_memory) / avg_memory if avg_memory > 0 else 1

        # Use the more constraining resource
        headroom = min(cpu_headroom, memory_headroom)

        # Calculate optimal concurrency
        current_concurrency = self.current_config.concurrent_batches
        optimal = max(1, min(5, int(current_concurrency * (1 + headroom * 0.5))))

        return optimal

    def _estimate_concurrency_improvement(self, optimal_concurrency: int) -> float:
        """Estimate improvement from changing concurrency.

        Args:
            optimal_concurrency: Recommended concurrency level

        Returns:
            Expected improvement percentage
        """
        current = self.current_config.concurrent_batches

        if optimal_concurrency == current:
            return 0.0
        elif optimal_concurrency > current:
            # Increasing concurrency - estimate linear improvement up to a point
            improvement = min(50.0, (optimal_concurrency - current) * 20)
            return improvement
        else:
            # Decreasing concurrency might improve efficiency by reducing contention
            return min(15.0, (current - optimal_concurrency) * 5)

    async def _save_metrics(self) -> None:
        """Save metrics to persistent storage."""
        try:
            # Keep only recent metrics to prevent file from growing too large
            recent_metrics = self.metrics_history[-1000:]  # Last 1000 batches

            # Convert to serializable format
            serializable_metrics = []
            for metric in recent_metrics:
                serializable_metrics.append(
                    {
                        "batch_size": metric.batch_size,
                        "processing_time": metric.processing_time,
                        "throughput": metric.throughput,
                        "success_rate": metric.success_rate,
                        "resource_usage": metric.resource_usage,
                        "cost_estimate": metric.cost_estimate,
                        "timestamp": metric.timestamp.isoformat(),
                    }
                )

            with open(self.metrics_file, "w") as f:
                json.dump(serializable_metrics, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save batch metrics: {e}")


async def main():
    """Main batch optimization routine."""
    config = EnvironmentConfigProvider()
    optimizer = BatchOptimizer(config)

    # Simulate some batch results for demonstration
    sample_results = [
        {"items": list(range(20)), "processing_time": 45.0, "successful_count": 18},
        {"items": list(range(25)), "processing_time": 52.0, "successful_count": 24},
        {"items": list(range(15)), "processing_time": 38.0, "successful_count": 15},
    ]

    # Analyze performance
    metrics = await optimizer.analyze_batch_performance(sample_results)
    print(
        f"Batch metrics: {metrics.throughput:.2f} props/sec, {metrics.success_rate:.1%} success rate"
    )

    # Generate optimization report
    report = await optimizer.generate_optimization_report()
    print(report)

    # Get recommendations
    batch_rec = await optimizer.optimize_batch_size()
    concurrency_rec = await optimizer.optimize_concurrency()
    resource_recs = await optimizer.optimize_resource_allocation()

    print("\n## Key Recommendations:")
    print(
        f"1. Batch Size: {batch_rec.current_value} -> {batch_rec.recommended_value} ({batch_rec.expected_improvement:.1f}% improvement)"
    )
    print(
        f"2. Concurrency: {concurrency_rec.current_value} -> {concurrency_rec.recommended_value} ({concurrency_rec.expected_improvement:.1f}% improvement)"
    )

    for rec in resource_recs:
        print(
            f"3. {rec.parameter}: {rec.recommended_value} ({rec.expected_improvement:.1f}% improvement)"
        )


if __name__ == "__main__":
    asyncio.run(main())
