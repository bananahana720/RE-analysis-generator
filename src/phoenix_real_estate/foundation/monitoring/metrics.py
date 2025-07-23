"""Metrics collectors for Phoenix Real Estate monitoring.

Provides specialized metrics collectors for different system components.
"""

import time
import asyncio
import psutil
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from contextlib import asynccontextmanager, contextmanager
from functools import wraps

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    CollectorRegistry,
    generate_latest,
)

from phoenix_real_estate.foundation.logging import get_logger
from .config import MetricsConfig, MetricType

logger = get_logger(__name__)


class BaseMetrics(ABC):
    """Base class for metrics collectors."""

    def __init__(self, registry: CollectorRegistry, prefix: str = ""):
        """Initialize metrics collector.

        Args:
            registry: Prometheus collector registry
            prefix: Metric name prefix
        """
        self.registry = registry
        self.prefix = prefix
        self._metrics: Dict[str, Any] = {}
        self._initialize_metrics()

    @abstractmethod
    def _initialize_metrics(self):
        """Initialize metric collectors."""
        pass

    def _create_metric(
        self,
        metric_type: MetricType,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        **kwargs,
    ) -> Any:
        """Create a metric collector.

        Args:
            metric_type: Type of metric (counter, gauge, etc.)
            name: Metric name
            description: Metric description
            labels: Label names
            **kwargs: Additional arguments for specific metric types

        Returns:
            Metric collector instance
        """
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        labels = labels or []

        metric_class = {
            MetricType.COUNTER: Counter,
            MetricType.GAUGE: Gauge,
            MetricType.HISTOGRAM: Histogram,
            MetricType.SUMMARY: Summary,
        }[metric_type]

        metric_kwargs = {
            "name": full_name,
            "documentation": description,
            "labelnames": labels,
            "registry": self.registry,
        }

        # Add specific kwargs for histogram
        if metric_type == MetricType.HISTOGRAM and "buckets" in kwargs:
            metric_kwargs["buckets"] = kwargs["buckets"]
        # Note: Summary doesn't support quantiles parameter in newer versions

        return metric_class(**metric_kwargs)


class ScraperMetrics(BaseMetrics):
    """Metrics for web scraper operations."""

    def __init__(self, registry: CollectorRegistry, config: MetricsConfig):
        """Initialize scraper metrics."""
        self.config = config
        super().__init__(registry, "scraper")

    def _initialize_metrics(self):
        """Initialize scraper-specific metrics."""
        # Request metrics
        self._metrics["requests_total"] = self._create_metric(
            MetricType.COUNTER,
            "requests_total",
            "Total number of scraping requests",
            labels=["status", "endpoint", "method"],
        )

        # Response time metrics
        self._metrics["response_time_seconds"] = self._create_metric(
            MetricType.HISTOGRAM,
            "response_time_seconds",
            "Response time in seconds",
            labels=["endpoint", "status"],
            buckets=self.config.response_time_buckets,
        )

        # Content size metrics
        self._metrics["content_size_bytes"] = self._create_metric(
            MetricType.HISTOGRAM,
            "content_size_bytes",
            "Content size in bytes",
            labels=["endpoint", "content_type"],
            buckets=self.config.content_size_buckets,
        )

        # Property metrics
        self._metrics["properties_scraped_total"] = self._create_metric(
            MetricType.COUNTER,
            "properties_scraped_total",
            "Total number of properties scraped",
            labels=["zipcode", "status"],
        )

        # Error metrics
        self._metrics["errors_total"] = self._create_metric(
            MetricType.COUNTER,
            "errors_total",
            "Total number of errors",
            labels=["error_type", "endpoint"],
        )

        # Session metrics
        self._metrics["session_valid"] = self._create_metric(
            MetricType.GAUGE,
            "session_valid",
            "Whether the scraper session is valid (1=valid, 0=invalid)",
        )

        self._metrics["session_age_seconds"] = self._create_metric(
            MetricType.GAUGE, "session_age_seconds", "Age of the current session in seconds"
        )

        # Retry metrics
        self._metrics["retries_total"] = self._create_metric(
            MetricType.COUNTER,
            "retries_total",
            "Total number of retry attempts",
            labels=["endpoint", "retry_number"],
        )

    def record_request(self, status: str, endpoint: str, method: str = "GET"):
        """Record a scraping request."""
        self._metrics["requests_total"].labels(
            status=status, endpoint=endpoint, method=method
        ).inc()

    def record_response_time(self, duration: float, endpoint: str, status: str):
        """Record response time for a request."""
        self._metrics["response_time_seconds"].labels(endpoint=endpoint, status=status).observe(
            duration
        )

    def record_content_size(self, size_bytes: int, endpoint: str, content_type: str = "html"):
        """Record content size."""
        self._metrics["content_size_bytes"].labels(
            endpoint=endpoint, content_type=content_type
        ).observe(size_bytes)

    def record_property_scraped(self, zipcode: str, status: str = "success"):
        """Record a property being scraped."""
        self._metrics["properties_scraped_total"].labels(zipcode=zipcode, status=status).inc()

    def record_error(self, error_type: str, endpoint: str):
        """Record an error."""
        self._metrics["errors_total"].labels(error_type=error_type, endpoint=endpoint).inc()

    def set_session_status(self, is_valid: bool, session_age: Optional[float] = None):
        """Set session status."""
        self._metrics["session_valid"].set(1 if is_valid else 0)
        if session_age is not None:
            self._metrics["session_age_seconds"].set(session_age)

    def record_retry(self, endpoint: str, retry_number: int):
        """Record a retry attempt."""
        self._metrics["retries_total"].labels(
            endpoint=endpoint, retry_number=str(retry_number)
        ).inc()

    @contextmanager
    def time_request(self, endpoint: str):
        """Context manager to time a request."""
        start_time = time.time()
        status = "success"
        try:
            yield
        except Exception:
            status = "failed"
            raise
        finally:
            duration = time.time() - start_time
            self.record_response_time(duration, endpoint, status)
            self.record_request(status, endpoint)


class ProxyMetrics(BaseMetrics):
    """Metrics for proxy management."""

    def _initialize_metrics(self):
        """Initialize proxy-specific metrics."""
        # Proxy count metrics
        self._metrics["total_count"] = self._create_metric(
            MetricType.GAUGE, "total_count", "Total number of configured proxies"
        )

        self._metrics["healthy_count"] = self._create_metric(
            MetricType.GAUGE, "healthy_count", "Number of healthy proxies"
        )

        # Proxy request metrics
        self._metrics["requests_total"] = self._create_metric(
            MetricType.COUNTER,
            "requests_total",
            "Total proxy requests",
            labels=["proxy_id", "status"],
        )

        # Proxy health check metrics
        self._metrics["health_check_duration_seconds"] = self._create_metric(
            MetricType.HISTOGRAM,
            "health_check_duration_seconds",
            "Proxy health check duration",
            labels=["proxy_id"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        )

        self._metrics["health_check_failures_total"] = self._create_metric(
            MetricType.COUNTER,
            "health_check_failures_total",
            "Total proxy health check failures",
            labels=["proxy_id", "reason"],
        )

        # Proxy performance metrics
        self._metrics["response_time_seconds"] = self._create_metric(
            MetricType.SUMMARY, "response_time_seconds", "Proxy response time", labels=["proxy_id"]
        )

        # Proxy rotation metrics
        self._metrics["rotations_total"] = self._create_metric(
            MetricType.COUNTER, "rotations_total", "Total number of proxy rotations"
        )

        self._metrics["cooldown_active"] = self._create_metric(
            MetricType.GAUGE,
            "cooldown_active",
            "Number of proxies in cooldown",
        )

    def set_proxy_counts(self, total: int, healthy: int):
        """Set proxy count metrics."""
        self._metrics["total_count"].set(total)
        self._metrics["healthy_count"].set(healthy)

    def record_proxy_request(self, proxy_id: str, status: str):
        """Record a proxy request."""
        self._metrics["requests_total"].labels(proxy_id=proxy_id, status=status).inc()

    def record_health_check(self, proxy_id: str, duration: float, success: bool, reason: str = ""):
        """Record proxy health check results."""
        self._metrics["health_check_duration_seconds"].labels(proxy_id=proxy_id).observe(duration)

        if not success:
            self._metrics["health_check_failures_total"].labels(
                proxy_id=proxy_id, reason=reason
            ).inc()

    def record_proxy_response_time(self, proxy_id: str, duration: float):
        """Record proxy response time."""
        self._metrics["response_time_seconds"].labels(proxy_id=proxy_id).observe(duration)

    def record_rotation(self):
        """Record a proxy rotation."""
        self._metrics["rotations_total"].inc()

    def set_cooldown_count(self, count: int):
        """Set number of proxies in cooldown."""
        self._metrics["cooldown_active"].set(count)


class DatabaseMetrics(BaseMetrics):
    """Metrics for database operations."""

    def _initialize_metrics(self):
        """Initialize database-specific metrics."""
        # Connection metrics
        self._metrics["connections_active"] = self._create_metric(
            MetricType.GAUGE, "connections_active", "Number of active database connections"
        )

        self._metrics["connection_errors_total"] = self._create_metric(
            MetricType.COUNTER,
            "connection_errors_total",
            "Total database connection errors",
            labels=["error_type"],
        )

        # Query metrics
        self._metrics["queries_total"] = self._create_metric(
            MetricType.COUNTER,
            "queries_total",
            "Total database queries",
            labels=["operation", "collection", "status"],
        )

        self._metrics["query_duration_seconds"] = self._create_metric(
            MetricType.HISTOGRAM,
            "query_duration_seconds",
            "Database query duration",
            labels=["operation", "collection"],
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0],
        )

        # Document metrics
        self._metrics["documents_total"] = self._create_metric(
            MetricType.COUNTER,
            "documents_total",
            "Total documents processed",
            labels=["operation", "collection"],
        )

        # Collection size metrics
        self._metrics["collection_size_bytes"] = self._create_metric(
            MetricType.GAUGE,
            "collection_size_bytes",
            "Collection size in bytes",
            labels=["collection"],
        )

        self._metrics["collection_document_count"] = self._create_metric(
            MetricType.GAUGE,
            "collection_document_count",
            "Number of documents in collection",
            labels=["collection"],
        )

    def set_active_connections(self, count: int):
        """Set active connection count."""
        self._metrics["connections_active"].set(count)

    def record_connection_error(self, error_type: str):
        """Record a connection error."""
        self._metrics["connection_errors_total"].labels(error_type=error_type).inc()

    def record_query(self, operation: str, collection: str, status: str, duration: float):
        """Record a database query."""
        self._metrics["queries_total"].labels(
            operation=operation, collection=collection, status=status
        ).inc()

        self._metrics["query_duration_seconds"].labels(
            operation=operation, collection=collection
        ).observe(duration)

    def record_documents(self, operation: str, collection: str, count: int):
        """Record document operations."""
        self._metrics["documents_total"].labels(operation=operation, collection=collection).inc(
            count
        )

    def set_collection_stats(self, collection: str, size_bytes: int, document_count: int):
        """Set collection statistics."""
        self._metrics["collection_size_bytes"].labels(collection=collection).set(size_bytes)

        self._metrics["collection_document_count"].labels(collection=collection).set(document_count)

    @asynccontextmanager
    async def time_query(self, operation: str, collection: str):
        """Async context manager to time a database query."""
        start_time = time.time()
        status = "success"
        try:
            yield
        except Exception:
            status = "failed"
            raise
        finally:
            duration = time.time() - start_time
            self.record_query(operation, collection, status, duration)


class SystemMetrics(BaseMetrics):
    """System-level metrics."""

    def _initialize_metrics(self):
        """Initialize system metrics."""
        # CPU metrics
        self._metrics["cpu_usage_percent"] = self._create_metric(
            MetricType.GAUGE, "cpu_usage_percent", "CPU usage percentage"
        )

        # Memory metrics
        self._metrics["memory_usage_percent"] = self._create_metric(
            MetricType.GAUGE, "memory_usage_percent", "Memory usage percentage"
        )

        self._metrics["memory_used_bytes"] = self._create_metric(
            MetricType.GAUGE, "memory_used_bytes", "Memory used in bytes"
        )

        # Disk metrics
        self._metrics["disk_usage_percent"] = self._create_metric(
            MetricType.GAUGE, "disk_usage_percent", "Disk usage percentage", labels=["path"]
        )

        # Network metrics
        self._metrics["network_bytes_sent"] = self._create_metric(
            MetricType.COUNTER, "network_bytes_sent", "Total network bytes sent"
        )

        self._metrics["network_bytes_received"] = self._create_metric(
            MetricType.COUNTER, "network_bytes_received", "Total network bytes received"
        )

        # Process metrics
        self._metrics["process_threads"] = self._create_metric(
            MetricType.GAUGE, "process_threads", "Number of process threads"
        )

        self._metrics["process_open_files"] = self._create_metric(
            MetricType.GAUGE, "process_open_files", "Number of open file descriptors"
        )

    def collect_system_metrics(self):
        """Collect current system metrics."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self._metrics["cpu_usage_percent"].set(cpu_percent)

            # Memory
            memory = psutil.virtual_memory()
            self._metrics["memory_usage_percent"].set(memory.percent)
            self._metrics["memory_used_bytes"].set(memory.used)

            # Disk
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    self._metrics["disk_usage_percent"].labels(path=partition.mountpoint).set(
                        usage.percent
                    )
                except PermissionError:
                    continue

            # Network (get counters)
            net_io = psutil.net_io_counters()
            if net_io:
                # These are cumulative counters
                self._metrics["network_bytes_sent"]._value.set(net_io.bytes_sent)
                self._metrics["network_bytes_received"]._value.set(net_io.bytes_recv)

            # Process
            process = psutil.Process()
            self._metrics["process_threads"].set(process.num_threads())

            try:
                open_files = len(process.open_files())
                self._metrics["process_open_files"].set(open_files)
            except (psutil.AccessDenied, AttributeError):
                pass

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")


class RateLimitMetrics(BaseMetrics):
    """Metrics for rate limiting."""

    def _initialize_metrics(self):
        """Initialize rate limit metrics."""
        self._metrics["hits_total"] = self._create_metric(
            MetricType.COUNTER,
            "hits_total",
            "Total rate limit hits",
            labels=["endpoint", "limit_type"],
        )

        self._metrics["wait_time_seconds"] = self._create_metric(
            MetricType.HISTOGRAM,
            "wait_time_seconds",
            "Rate limit wait time",
            labels=["endpoint"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
        )

        self._metrics["current_rate"] = self._create_metric(
            MetricType.GAUGE, "current_rate", "Current request rate per minute", labels=["endpoint"]
        )

        self._metrics["limit_remaining"] = self._create_metric(
            MetricType.GAUGE,
            "limit_remaining",
            "Remaining requests in current window",
            labels=["endpoint"],
        )

    def record_rate_limit_hit(self, endpoint: str, limit_type: str, wait_time: float):
        """Record a rate limit hit."""
        self._metrics["hits_total"].labels(endpoint=endpoint, limit_type=limit_type).inc()

        self._metrics["wait_time_seconds"].labels(endpoint=endpoint).observe(wait_time)

    def set_current_rate(self, endpoint: str, rate: float):
        """Set current request rate."""
        self._metrics["current_rate"].labels(endpoint=endpoint).set(rate)

    def set_limit_remaining(self, endpoint: str, remaining: int):
        """Set remaining requests in window."""
        self._metrics["limit_remaining"].labels(endpoint=endpoint).set(remaining)


class MetricsCollector:
    """Main metrics collector that aggregates all metric types."""

    def __init__(self, config: MetricsConfig):
        """Initialize metrics collector.

        Args:
            config: Metrics configuration
        """
        self.config = config
        self.registry = CollectorRegistry()

        # Initialize metric collectors
        self.scraper = ScraperMetrics(self.registry, config)
        self.proxy = ProxyMetrics(self.registry, "proxy")
        self.database = DatabaseMetrics(self.registry, "database")
        self.system = SystemMetrics(self.registry, "system")
        self.rate_limit = RateLimitMetrics(self.registry, "rate_limit")

        # Start background system metrics collection
        if config.enabled:
            self._start_system_metrics_collection()

        logger.info("Metrics collector initialized")

    def _start_system_metrics_collection(self):
        """Start background task for system metrics collection."""

        async def collect_loop():
            while True:
                try:
                    self.system.collect_system_metrics()
                    await asyncio.sleep(self.config.collection_interval)
                except Exception as e:
                    logger.error(f"Error in system metrics collection: {e}")
                    await asyncio.sleep(60)  # Wait longer on error

        # Create task in current event loop if available
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(collect_loop())
        except RuntimeError:
            # No running loop, metrics will be collected manually
            pass

    def get_metrics(self) -> bytes:
        """Get current metrics in Prometheus format.

        Returns:
            Prometheus formatted metrics
        """
        return generate_latest(self.registry)

    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as a dictionary for debugging.

        Returns:
            Dictionary of current metric values
        """
        # This is a simplified representation for debugging
        metrics = {}

        for collector in self.registry._collector_to_names:
            for metric in collector.collect():
                for sample in metric.samples:
                    key = f"{sample.name}{sample.labels}"
                    metrics[key] = sample.value

        return metrics


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(config: Optional[MetricsConfig] = None) -> MetricsCollector:
    """Get or create the global metrics collector.

    Args:
        config: Metrics configuration (required on first call)

    Returns:
        Global metrics collector instance
    """
    global _metrics_collector

    if _metrics_collector is None:
        if config is None:
            config = MetricsConfig()
        _metrics_collector = MetricsCollector(config)

    return _metrics_collector


def _reset_metrics_collector():
    """Reset the global metrics collector (for testing)."""
    global _metrics_collector
    _metrics_collector = None


def metrics_decorator(metric_type: str = "request", labels: Optional[Dict[str, str]] = None):
    """Decorator for automatic metrics collection.

    Args:
        metric_type: Type of metric to collect
        labels: Additional labels
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_metrics_collector()

            if metric_type == "request":
                endpoint = labels.get("endpoint", func.__name__) if labels else func.__name__
                start_time = time.time()
                status = "success"
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception:
                    status = "failed"
                    raise
                finally:
                    duration = time.time() - start_time
                    collector.scraper.record_response_time(duration, endpoint, status)
                    collector.scraper.record_request(status, endpoint)
            else:
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_metrics_collector()

            if metric_type == "request":
                endpoint = labels.get("endpoint", func.__name__) if labels else func.__name__
                with collector.scraper.time_request(endpoint):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
