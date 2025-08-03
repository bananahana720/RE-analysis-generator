#!/usr/bin/env python3
"""Phoenix MLS Scraper Performance Validation Script.

Tests whether the scraper can achieve the target of 1000+ properties per hour
while maintaining rate limit compliance and proxy health.

This script simulates realistic scraping scenarios and measures:
- Throughput (properties/hour)
- Success rate (%)
- Rate limit compliance
- Resource usage (memory, CPU)
- Proxy performance
- Error rates and recovery
"""

import asyncio
import time
import psutil
import argparse
import json
import statistics
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import signal
import traceback
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class PerformanceValidator:
    """Validates Phoenix MLS scraper performance against targets."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the performance validator.

        Args:
            config: Configuration dictionary with test parameters
        """
        self.config = config
        self.target_properties_per_hour = config.get("target_properties_per_hour", 1000)
        self.test_duration_minutes = config.get("test_duration_minutes", 60)
        self.sample_interval_seconds = config.get("sample_interval_seconds", 60)

        # Phoenix zipcodes for testing
        self.test_zipcodes = config.get(
            "test_zipcodes",
            [
                "85001",
                "85003",
                "85004",
                "85006",
                "85007",
                "85008",
                "85009",
                "85012",
                "85013",
                "85014",
                "85015",
                "85016",
                "85018",
                "85020",
                "85021",
                "85022",
                "85023",
                "85024",
                "85027",
                "85028",
                "85029",
            ],
        )

        # Metrics storage
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "total_properties_scraped": 0,
            "total_properties_attempted": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited_events": 0,
            "proxy_failures": 0,
            "throughput_samples": [],
            "response_times": [],
            "memory_usage_samples": [],
            "cpu_usage_samples": [],
            "error_types": defaultdict(int),
            "proxy_performance": {},
            "rate_limit_compliance": True,
        }

        # Performance tracking
        self.properties_per_minute = defaultdict(int)
        self.current_minute = None
        self.running = False

        # Process monitoring
        self.process = psutil.Process()

    async def run_validation(self) -> Dict[str, Any]:
        """Run the complete performance validation test.

        Returns:
            Dictionary with validation results and metrics
        """
        logger.info("Starting performance validation test")
        logger.info(f"Target: {self.target_properties_per_hour} properties/hour")
        logger.info(f"Duration: {self.test_duration_minutes} minutes")

        # Load scraper configuration
        scraper_config = self._load_scraper_config()
        proxy_config = self._load_proxy_config()

        # Initialize scraper
        scraper = PhoenixMLSScraper(scraper_config, proxy_config)

        # Set up signal handling for graceful shutdown
        self._setup_signal_handlers()

        try:
            # Initialize browser
            await scraper.initialize_browser()

            # Start validation
            self.metrics["start_time"] = datetime.now(UTC)
            self.running = True

            # Create concurrent tasks
            tasks = [
                self._scraping_task(scraper),
                self._monitoring_task(),
                self._throughput_monitor(),
            ]

            # Run for specified duration
            await asyncio.gather(*tasks)

        except KeyboardInterrupt:
            logger.info("Validation interrupted by user")
        except Exception as e:
            logger.error(f"Validation error: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.running = False
            self.metrics["end_time"] = datetime.now(UTC)

            # Close browser
            await scraper.close_browser()

            # Get final statistics
            self.metrics["scraper_stats"] = scraper.get_statistics()

        # Generate report
        return self._generate_report()

    async def _scraping_task(self, scraper: PhoenixMLSScraper):
        """Main scraping task that runs property searches.

        Args:
            scraper: The Phoenix MLS scraper instance
        """
        zipcode_index = 0
        batch_size = 20  # Properties to scrape per batch

        while self.running and self._should_continue():
            try:
                # Select next zipcode
                zipcode = self.test_zipcodes[zipcode_index % len(self.test_zipcodes)]
                zipcode_index += 1

                # Search properties in zipcode
                start_time = time.time()
                properties = await scraper.search_properties_by_zipcode(zipcode)
                search_time = time.time() - start_time

                if properties:
                    logger.info(
                        f"Found {len(properties)} properties in {zipcode} ({search_time:.2f}s)"
                    )

                    # Scrape details for a batch of properties
                    property_urls = [p.get("url") for p in properties[:batch_size] if p.get("url")]

                    if property_urls:
                        # Track batch start
                        batch_start = time.time()
                        self.metrics["total_properties_attempted"] += len(property_urls)

                        # Scrape batch
                        results = await scraper.scrape_properties_batch(property_urls)

                        # Record metrics
                        batch_time = time.time() - batch_start
                        self.metrics["total_properties_scraped"] += len(results)
                        self.metrics["successful_requests"] += len(results)
                        self.metrics["response_times"].extend(
                            [batch_time / len(results)] * len(results)
                        )

                        # Track per-minute throughput
                        self._update_throughput(len(results))

                        logger.info(
                            f"Scraped {len(results)}/{len(property_urls)} properties "
                            f"({batch_time:.2f}s, {len(results) / batch_time:.1f} props/s)"
                        )
                else:
                    logger.warning(f"No properties found in {zipcode}")

                # Rate limit compliance check
                rate_limiter_usage = scraper.rate_limiter.get_current_usage("phoenix_mls")
                if rate_limiter_usage["is_rate_limited"]:
                    self.metrics["rate_limited_events"] += 1
                    self.metrics["rate_limit_compliance"] = False
                    logger.warning("Rate limit exceeded!")

            except Exception as e:
                self.metrics["failed_requests"] += 1
                self.metrics["error_types"][type(e).__name__] += 1
                logger.error(f"Scraping error: {e}")

                # Small delay on error
                await asyncio.sleep(5)

    async def _monitoring_task(self):
        """Monitor system resources during the test."""
        while self.running:
            try:
                # CPU usage
                cpu_percent = self.process.cpu_percent(interval=1)
                self.metrics["cpu_usage_samples"].append(cpu_percent)

                # Memory usage
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.metrics["memory_usage_samples"].append(memory_mb)

                # Log current status
                if len(self.metrics["cpu_usage_samples"]) % 10 == 0:
                    logger.info(
                        f"Resources - CPU: {cpu_percent:.1f}%, "
                        f"Memory: {memory_mb:.1f}MB, "
                        f"Properties: {self.metrics['total_properties_scraped']}"
                    )

                await asyncio.sleep(self.sample_interval_seconds)

            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.sample_interval_seconds)

    async def _throughput_monitor(self):
        """Monitor and log throughput metrics."""
        while self.running:
            await asyncio.sleep(60)  # Check every minute

            if self.metrics["start_time"]:
                elapsed_hours = (
                    datetime.now(UTC) - self.metrics["start_time"]
                ).total_seconds() / 3600
                if elapsed_hours > 0:
                    current_rate = self.metrics["total_properties_scraped"] / elapsed_hours
                    self.metrics["throughput_samples"].append(current_rate)

                    logger.info(
                        f"Current rate: {current_rate:.0f} properties/hour "
                        f"(Target: {self.target_properties_per_hour})"
                    )

    def _update_throughput(self, count: int):
        """Update per-minute throughput tracking.

        Args:
            count: Number of properties scraped
        """
        current_minute = datetime.now().replace(second=0, microsecond=0)

        if self.current_minute != current_minute:
            self.current_minute = current_minute

        self.properties_per_minute[current_minute] += count

    def _should_continue(self) -> bool:
        """Check if the test should continue running.

        Returns:
            True if test should continue, False otherwise
        """
        if not self.metrics["start_time"]:
            return True

        elapsed_minutes = (datetime.now(UTC) - self.metrics["start_time"]).total_seconds() / 60
        return elapsed_minutes < self.test_duration_minutes

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info("Received interrupt signal, shutting down...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _load_scraper_config(self) -> Dict[str, Any]:
        """Load scraper configuration.

        Returns:
            Scraper configuration dictionary
        """
        return {
            "base_url": "https://www.phoenixmlssearch.com",
            "search_endpoint": "/search",
            "max_retries": 3,
            "timeout": 30,
            "rate_limit": {
                "requests_per_minute": 60,  # Conservative for testing
                "safety_margin": 0.1,
            },
            "cookies_path": "data/cookies",
        }

    def _load_proxy_config(self) -> Optional[Dict[str, Any]]:
        """Load proxy configuration if available.

        Returns:
            Proxy configuration dictionary or None
        """
        proxy_config_path = Path("config/proxies.yaml")
        if proxy_config_path.exists():
            try:
                import yaml

                with open(proxy_config_path) as f:
                    config = yaml.safe_load(f)
                    return config.get("proxy_manager", {})
            except Exception as e:
                logger.warning(f"Failed to load proxy config: {e}")

        return None

    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report.

        Returns:
            Performance validation report
        """
        # Calculate test duration
        if self.metrics["start_time"] and self.metrics["end_time"]:
            duration = self.metrics["end_time"] - self.metrics["start_time"]
            duration_hours = duration.total_seconds() / 3600
            duration_minutes = duration.total_seconds() / 60
        else:
            duration_hours = 0
            duration_minutes = 0

        # Calculate throughput
        if duration_hours > 0:
            actual_properties_per_hour = self.metrics["total_properties_scraped"] / duration_hours
        else:
            actual_properties_per_hour = 0

        # Calculate success rate
        if self.metrics["total_properties_attempted"] > 0:
            success_rate = (
                self.metrics["successful_requests"] / self.metrics["total_properties_attempted"]
            ) * 100
        else:
            success_rate = 0

        # Calculate resource usage statistics
        avg_cpu = (
            statistics.mean(self.metrics["cpu_usage_samples"])
            if self.metrics["cpu_usage_samples"]
            else 0
        )
        max_cpu = max(self.metrics["cpu_usage_samples"]) if self.metrics["cpu_usage_samples"] else 0
        avg_memory = (
            statistics.mean(self.metrics["memory_usage_samples"])
            if self.metrics["memory_usage_samples"]
            else 0
        )
        max_memory = (
            max(self.metrics["memory_usage_samples"]) if self.metrics["memory_usage_samples"] else 0
        )

        # Calculate response time statistics
        if self.metrics["response_times"]:
            avg_response_time = statistics.mean(self.metrics["response_times"])
            p95_response_time = statistics.quantiles(self.metrics["response_times"], n=20)[
                18
            ]  # 95th percentile
            p99_response_time = statistics.quantiles(self.metrics["response_times"], n=100)[
                98
            ]  # 99th percentile
        else:
            avg_response_time = 0
            p95_response_time = 0
            p99_response_time = 0

        # Build report
        report = {
            "summary": {
                "test_passed": actual_properties_per_hour >= self.target_properties_per_hour,
                "target_properties_per_hour": self.target_properties_per_hour,
                "actual_properties_per_hour": round(actual_properties_per_hour, 2),
                "total_properties_scraped": self.metrics["total_properties_scraped"],
                "success_rate": round(success_rate, 2),
                "rate_limit_compliant": self.metrics["rate_limit_compliance"],
                "test_duration_minutes": round(duration_minutes, 2),
            },
            "throughput": {
                "properties_per_hour": round(actual_properties_per_hour, 2),
                "properties_per_minute": round(actual_properties_per_hour / 60, 2),
                "average_throughout_samples": round(
                    statistics.mean(self.metrics["throughput_samples"]), 2
                )
                if self.metrics["throughput_samples"]
                else 0,
                "peak_properties_per_minute": max(self.properties_per_minute.values())
                if self.properties_per_minute
                else 0,
            },
            "performance": {
                "avg_response_time_seconds": round(avg_response_time, 3),
                "p95_response_time_seconds": round(p95_response_time, 3),
                "p99_response_time_seconds": round(p99_response_time, 3),
                "avg_cpu_percent": round(avg_cpu, 2),
                "max_cpu_percent": round(max_cpu, 2),
                "avg_memory_mb": round(avg_memory, 2),
                "max_memory_mb": round(max_memory, 2),
            },
            "reliability": {
                "total_requests": self.metrics["successful_requests"]
                + self.metrics["failed_requests"],
                "successful_requests": self.metrics["successful_requests"],
                "failed_requests": self.metrics["failed_requests"],
                "rate_limited_events": self.metrics["rate_limited_events"],
                "error_breakdown": dict(self.metrics["error_types"]),
            },
            "recommendations": self._generate_recommendations(
                actual_properties_per_hour, success_rate
            ),
            "raw_metrics": self.metrics,
        }

        return report

    def _generate_recommendations(self, actual_rate: float, success_rate: float) -> List[str]:
        """Generate performance optimization recommendations.

        Args:
            actual_rate: Actual properties per hour achieved
            success_rate: Success rate percentage

        Returns:
            List of recommendations
        """
        recommendations = []

        # Throughput recommendations
        if actual_rate < self.target_properties_per_hour:
            shortfall = self.target_properties_per_hour - actual_rate
            recommendations.append(
                f"Throughput is {shortfall:.0f} properties/hour below target. "
                "Consider: increasing concurrent requests, optimizing parsing, "
                "or adding more proxies."
            )

        # Success rate recommendations
        if success_rate < 95:
            recommendations.append(
                f"Success rate is {success_rate:.1f}%. "
                "Consider: improving error handling, adding retries, "
                "or investigating common failure patterns."
            )

        # Rate limit recommendations
        if self.metrics["rate_limited_events"] > 0:
            recommendations.append(
                f"Rate limiting occurred {self.metrics['rate_limited_events']} times. "
                "Consider: reducing request rate, implementing better backoff, "
                "or distributing load across more sources."
            )

        # Resource usage recommendations
        if self.metrics["cpu_usage_samples"]:
            avg_cpu = statistics.mean(self.metrics["cpu_usage_samples"])
            if avg_cpu > 80:
                recommendations.append(
                    f"High CPU usage ({avg_cpu:.1f}%). "
                    "Consider: optimizing parsing logic, using async operations, "
                    "or implementing caching."
                )

        if self.metrics["memory_usage_samples"]:
            max_memory = max(self.metrics["memory_usage_samples"])
            if max_memory > 1024:  # 1GB
                recommendations.append(
                    f"High memory usage ({max_memory:.0f}MB). "
                    "Consider: implementing memory cleanup, limiting concurrent operations, "
                    "or streaming large responses."
                )

        # Error pattern recommendations
        if self.metrics["error_types"]:
            most_common_error = max(
                self.metrics["error_types"], key=self.metrics["error_types"].get
            )
            recommendations.append(
                f"Most common error: {most_common_error} ({self.metrics['error_types'][most_common_error]} occurrences). "
                "Investigate and implement specific handling for this error type."
            )

        if not recommendations:
            recommendations.append(
                "Performance meets all targets. No immediate optimizations needed."
            )

        return recommendations


def print_report(report: Dict[str, Any]):
    """Print formatted performance report.

    Args:
        report: Performance validation report
    """
    print("\n" + "=" * 80)
    print("PHOENIX MLS SCRAPER PERFORMANCE VALIDATION REPORT")
    print("=" * 80)

    # Summary
    print("\n📊 SUMMARY")
    print("-" * 40)
    summary = report["summary"]
    status = "✅ PASSED" if summary["test_passed"] else "❌ FAILED"
    print(f"Test Status: {status}")
    print(f"Target: {summary['target_properties_per_hour']} properties/hour")
    print(f"Actual: {summary['actual_properties_per_hour']} properties/hour")
    print(f"Total Properties: {summary['total_properties_scraped']}")
    print(f"Success Rate: {summary['success_rate']}%")
    print(f"Rate Limit Compliant: {'Yes' if summary['rate_limit_compliant'] else 'No'}")
    print(f"Test Duration: {summary['test_duration_minutes']} minutes")

    # Throughput
    print("\n⚡ THROUGHPUT")
    print("-" * 40)
    throughput = report["throughput"]
    print(f"Properties/Hour: {throughput['properties_per_hour']}")
    print(f"Properties/Minute: {throughput['properties_per_minute']}")
    print(f"Peak Properties/Minute: {throughput['peak_properties_per_minute']}")

    # Performance
    print("\n🚀 PERFORMANCE")
    print("-" * 40)
    perf = report["performance"]
    print(f"Avg Response Time: {perf['avg_response_time_seconds']}s")
    print(f"P95 Response Time: {perf['p95_response_time_seconds']}s")
    print(f"P99 Response Time: {perf['p99_response_time_seconds']}s")
    print(f"CPU Usage: {perf['avg_cpu_percent']}% avg, {perf['max_cpu_percent']}% max")
    print(f"Memory Usage: {perf['avg_memory_mb']}MB avg, {perf['max_memory_mb']}MB max")

    # Reliability
    print("\n🛡️ RELIABILITY")
    print("-" * 40)
    reliability = report["reliability"]
    print(f"Total Requests: {reliability['total_requests']}")
    print(f"Successful: {reliability['successful_requests']}")
    print(f"Failed: {reliability['failed_requests']}")
    print(f"Rate Limited: {reliability['rate_limited_events']}")

    if reliability["error_breakdown"]:
        print("\nError Breakdown:")
        for error_type, count in reliability["error_breakdown"].items():
            print(f"  - {error_type}: {count}")

    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 40)
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"{i}. {rec}")

    print("\n" + "=" * 80)


async def main():
    """Main entry point for performance validation."""
    parser = argparse.ArgumentParser(description="Validate Phoenix MLS scraper performance")
    parser.add_argument(
        "--duration", type=int, default=10, help="Test duration in minutes (default: 10)"
    )
    parser.add_argument(
        "--target", type=int, default=1000, help="Target properties per hour (default: 1000)"
    )
    parser.add_argument("--output", type=str, help="Output file for JSON report")
    parser.add_argument("--zipcodes", nargs="+", help="Specific zipcodes to test")

    args = parser.parse_args()

    # Configuration
    config = {
        "target_properties_per_hour": args.target,
        "test_duration_minutes": args.duration,
        "sample_interval_seconds": 10,
    }

    if args.zipcodes:
        config["test_zipcodes"] = args.zipcodes

    # Run validation
    validator = PerformanceValidator(config)
    report = await validator.run_validation()

    # Print report
    print_report(report)

    # Save JSON report if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert datetime objects to strings
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=serialize_datetime)

        print(f"\nReport saved to: {output_path}")

    # Exit with appropriate code
    sys.exit(0 if report["summary"]["test_passed"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
