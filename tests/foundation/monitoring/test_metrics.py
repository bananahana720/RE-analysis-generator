"""Tests for Prometheus metrics collectors."""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from phoenix_real_estate.foundation.monitoring.metrics import (
    ScraperMetrics,
    ProxyMetrics,
    DatabaseMetrics,
    SystemMetrics,
    RateLimitMetrics,
    MetricsCollector,
    get_metrics_collector,
    metrics_decorator,
    _reset_metrics_collector,
)
from phoenix_real_estate.foundation.monitoring.config import MetricsConfig
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    """Create a fresh Prometheus registry."""
    return CollectorRegistry()


@pytest.fixture(autouse=True)
def reset_global_collector():
    """Reset global metrics collector before each test."""
    _reset_metrics_collector()
    yield
    _reset_metrics_collector()


@pytest.fixture
def metrics_config():
    """Create test metrics configuration."""
    return MetricsConfig(
        enabled=True,
        port=9090,
        collection_interval=1,  # Fast collection for tests
        labels={"service": "test", "environment": "test"},
    )


class TestScraperMetrics:
    """Test scraper metrics collection."""

    def test_initialization(self, registry, metrics_config):
        """Test scraper metrics initialization."""
        metrics = ScraperMetrics(registry, metrics_config)

        assert "requests_total" in metrics._metrics
        assert "response_time_seconds" in metrics._metrics
        assert "properties_scraped_total" in metrics._metrics
        assert "errors_total" in metrics._metrics

    def test_record_request(self, registry, metrics_config):
        """Test recording requests."""
        metrics = ScraperMetrics(registry, metrics_config)

        # Record successful request
        metrics.record_request("success", "search", "GET")

        # Get metric value
        request_metric = metrics._metrics["requests_total"]
        value = request_metric.labels(
            status="success", endpoint="search", method="GET"
        )._value.get()
        assert value == 1.0

    def test_record_response_time(self, registry, metrics_config):
        """Test recording response times."""
        metrics = ScraperMetrics(registry, metrics_config)

        # Record response time
        metrics.record_response_time(0.5, "search", "success")

        # Check histogram was updated
        response_time_metric = metrics._metrics["response_time_seconds"]
        samples = list(response_time_metric.labels(endpoint="search", status="success").collect())
        assert len(samples) > 0

    def test_record_property_scraped(self, registry, metrics_config):
        """Test recording scraped properties."""
        metrics = ScraperMetrics(registry, metrics_config)

        # Record scraped property
        metrics.record_property_scraped("85001", "success")

        # Check counter
        property_metric = metrics._metrics["properties_scraped_total"]
        value = property_metric.labels(zipcode="85001", status="success")._value.get()
        assert value == 1.0

    def test_record_error(self, registry, metrics_config):
        """Test error recording."""
        metrics = ScraperMetrics(registry, metrics_config)

        # Record error
        metrics.record_error("TimeoutError", "search")

        # Check counter
        error_metric = metrics._metrics["errors_total"]
        value = error_metric.labels(error_type="TimeoutError", endpoint="search")._value.get()
        assert value == 1.0

    def test_session_status(self, registry, metrics_config):
        """Test session status tracking."""
        metrics = ScraperMetrics(registry, metrics_config)

        # Set session status
        metrics.set_session_status(True, 3600.0)

        # Check gauges
        valid_metric = metrics._metrics["session_valid"]
        age_metric = metrics._metrics["session_age_seconds"]

        assert valid_metric._value.get() == 1.0
        assert age_metric._value.get() == 3600.0

    def test_time_request_context_manager(self, registry, metrics_config):
        """Test request timing context manager."""
        metrics = ScraperMetrics(registry, metrics_config)

        # Time successful request
        with metrics.time_request("test_endpoint"):
            time.sleep(0.1)  # Small delay

        # Check metrics were recorded
        request_metric = metrics._metrics["requests_total"]
        response_time_metric = metrics._metrics["response_time_seconds"]

        request_value = request_metric.labels(
            status="success", endpoint="test_endpoint", method="GET"
        )._value.get()
        assert request_value == 1.0

    def test_time_request_with_exception(self, registry, metrics_config):
        """Test request timing with exception."""
        metrics = ScraperMetrics(registry, metrics_config)

        # Time failed request
        with pytest.raises(ValueError):
            with metrics.time_request("test_endpoint"):
                raise ValueError("Test error")

        # Check failed request was recorded
        request_metric = metrics._metrics["requests_total"]
        request_value = request_metric.labels(
            status="failed", endpoint="test_endpoint", method="GET"
        )._value.get()
        assert request_value == 1.0


class TestProxyMetrics:
    """Test proxy metrics collection."""

    def test_initialization(self, registry):
        """Test proxy metrics initialization."""
        metrics = ProxyMetrics(registry, "proxy")

        assert "total_count" in metrics._metrics
        assert "healthy_count" in metrics._metrics
        assert "requests_total" in metrics._metrics
        assert "health_check_duration_seconds" in metrics._metrics

    def test_proxy_counts(self, registry):
        """Test setting proxy counts."""
        metrics = ProxyMetrics(registry, "proxy")

        metrics.set_proxy_counts(total=5, healthy=3)

        total_metric = metrics._metrics["total_count"]
        healthy_metric = metrics._metrics["healthy_count"]

        assert total_metric._value.get() == 5.0
        assert healthy_metric._value.get() == 3.0

    def test_proxy_request(self, registry):
        """Test proxy request recording."""
        metrics = ProxyMetrics(registry, "proxy")

        metrics.record_proxy_request("proxy1", "success")

        request_metric = metrics._metrics["requests_total"]
        value = request_metric.labels(proxy_id="proxy1", status="success")._value.get()
        assert value == 1.0

    def test_health_check(self, registry):
        """Test health check recording."""
        metrics = ProxyMetrics(registry, "proxy")

        # Record successful health check
        metrics.record_health_check("proxy1", 0.5, True)

        duration_metric = metrics._metrics["health_check_duration_seconds"]
        # Check that histogram was updated (we can't easily check exact values)
        assert duration_metric.labels(proxy_id="proxy1") is not None

    def test_health_check_failure(self, registry):
        """Test failed health check recording."""
        metrics = ProxyMetrics(registry, "proxy")

        # Record failed health check
        metrics.record_health_check("proxy2", 5.0, False, "timeout")

        failure_metric = metrics._metrics["health_check_failures_total"]
        value = failure_metric.labels(proxy_id="proxy2", reason="timeout")._value.get()
        assert value == 1.0


class TestDatabaseMetrics:
    """Test database metrics collection."""

    def test_initialization(self, registry):
        """Test database metrics initialization."""
        metrics = DatabaseMetrics(registry, "database")

        assert "connections_active" in metrics._metrics
        assert "queries_total" in metrics._metrics
        assert "query_duration_seconds" in metrics._metrics
        assert "documents_total" in metrics._metrics

    def test_connection_metrics(self, registry):
        """Test connection metrics."""
        metrics = DatabaseMetrics(registry, "database")

        metrics.set_active_connections(10)
        metrics.record_connection_error("timeout")

        conn_metric = metrics._metrics["connections_active"]
        error_metric = metrics._metrics["connection_errors_total"]

        assert conn_metric._value.get() == 10.0
        assert error_metric.labels(error_type="timeout")._value.get() == 1.0

    def test_query_metrics(self, registry):
        """Test query metrics."""
        metrics = DatabaseMetrics(registry, "database")

        metrics.record_query("insert", "properties", "success", 0.1)

        query_metric = metrics._metrics["queries_total"]
        value = query_metric.labels(
            operation="insert", collection="properties", status="success"
        )._value.get()
        assert value == 1.0

    @pytest.mark.asyncio
    async def test_time_query_context_manager(self, registry):
        """Test query timing context manager."""
        metrics = DatabaseMetrics(registry, "database")

        # Time successful query
        async with metrics.time_query("select", "properties"):
            await asyncio.sleep(0.01)  # Small delay

        # Check metrics were recorded
        query_metric = metrics._metrics["queries_total"]
        value = query_metric.labels(
            operation="select", collection="properties", status="success"
        )._value.get()
        assert value == 1.0


class TestSystemMetrics:
    """Test system metrics collection."""

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_partitions")
    @patch("psutil.net_io_counters")
    @patch("psutil.Process")
    def test_collect_system_metrics(
        self,
        mock_process,
        mock_net_io,
        mock_disk_partitions,
        mock_virtual_memory,
        mock_cpu_percent,
        registry,
    ):
        """Test system metrics collection."""
        # Mock system data
        mock_cpu_percent.return_value = 50.0

        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.used = 8 * 1024**3  # 8GB
        mock_virtual_memory.return_value = mock_memory

        mock_disk_partitions.return_value = []  # No partitions for simplicity

        mock_net_io_obj = Mock()
        mock_net_io_obj.bytes_sent = 1000000
        mock_net_io_obj.bytes_recv = 2000000
        mock_net_io.return_value = mock_net_io_obj

        mock_process_obj = Mock()
        mock_process_obj.num_threads.return_value = 10
        mock_process_obj.open_files.return_value = []
        mock_process.return_value = mock_process_obj

        # Create metrics and collect
        metrics = SystemMetrics(registry, "system")
        metrics.collect_system_metrics()

        # Check metrics were set
        cpu_metric = metrics._metrics["cpu_usage_percent"]
        memory_metric = metrics._metrics["memory_usage_percent"]
        threads_metric = metrics._metrics["process_threads"]

        assert cpu_metric._value.get() == 50.0
        assert memory_metric._value.get() == 60.0
        assert threads_metric._value.get() == 10.0


class TestRateLimitMetrics:
    """Test rate limit metrics collection."""

    def test_initialization(self, registry):
        """Test rate limit metrics initialization."""
        metrics = RateLimitMetrics(registry, "rate_limit")

        assert "hits_total" in metrics._metrics
        assert "wait_time_seconds" in metrics._metrics
        assert "current_rate" in metrics._metrics
        assert "limit_remaining" in metrics._metrics

    def test_rate_limit_hit(self, registry):
        """Test rate limit hit recording."""
        metrics = RateLimitMetrics(registry, "rate_limit")

        metrics.record_rate_limit_hit("test_endpoint", "scraper_limit", 5.0)

        hits_metric = metrics._metrics["hits_total"]
        value = hits_metric.labels(
            endpoint="test_endpoint", limit_type="scraper_limit"
        )._value.get()
        assert value == 1.0

    def test_current_rate(self, registry):
        """Test current rate setting."""
        metrics = RateLimitMetrics(registry, "rate_limit")

        metrics.set_current_rate("test_endpoint", 45.5)

        rate_metric = metrics._metrics["current_rate"]
        value = rate_metric.labels(endpoint="test_endpoint")._value.get()
        assert value == 45.5


class TestMetricsCollector:
    """Test main metrics collector."""

    def test_initialization(self, metrics_config):
        """Test metrics collector initialization."""
        collector = MetricsCollector(metrics_config)

        assert collector.scraper is not None
        assert collector.proxy is not None
        assert collector.database is not None
        assert collector.system is not None
        assert collector.rate_limit is not None

    def test_get_metrics(self, metrics_config):
        """Test getting metrics in Prometheus format."""
        collector = MetricsCollector(metrics_config)

        # Record some metrics
        collector.scraper.record_request("success", "test", "GET")
        collector.proxy.set_proxy_counts(5, 3)

        # Get metrics
        metrics_data = collector.get_metrics()

        assert isinstance(metrics_data, bytes)
        assert b"scraper_requests_total" in metrics_data
        assert b"proxy_total_count" in metrics_data

    def test_get_metrics_dict(self, metrics_config):
        """Test getting metrics as dictionary."""
        collector = MetricsCollector(metrics_config)

        # Record some metrics
        collector.scraper.record_request("success", "test", "GET")

        # Get metrics dict
        metrics_dict = collector.get_metrics_dict()

        assert isinstance(metrics_dict, dict)
        assert len(metrics_dict) > 0


class TestMetricsDecorator:
    """Test metrics decorator."""

    @pytest.mark.asyncio
    async def test_async_function_decorator(self, metrics_config):
        """Test decorator on async function."""
        # Get metrics collector
        collector = get_metrics_collector(metrics_config)

        @metrics_decorator(metric_type="request", labels={"endpoint": "test_func"})
        async def test_async_func():
            await asyncio.sleep(0.01)
            return "success"

        # Call decorated function
        result = await test_async_func()

        assert result == "success"

        # Check metrics were recorded
        request_metric = collector.scraper._metrics["requests_total"]
        value = request_metric.labels(
            status="success", endpoint="test_func", method="GET"
        )._value.get()
        assert value == 1.0

    def test_sync_function_decorator(self, metrics_config):
        """Test decorator on sync function."""
        # Get metrics collector
        collector = get_metrics_collector(metrics_config)

        @metrics_decorator(metric_type="request", labels={"endpoint": "sync_func"})
        def test_sync_func():
            return "success"

        # Call decorated function
        result = test_sync_func()

        assert result == "success"

        # Check metrics were recorded
        request_metric = collector.scraper._metrics["requests_total"]
        value = request_metric.labels(
            status="success", endpoint="sync_func", method="GET"
        )._value.get()
        assert value == 1.0

    @pytest.mark.asyncio
    async def test_decorator_with_exception(self, metrics_config):
        """Test decorator handles exceptions correctly."""
        # Get metrics collector
        collector = get_metrics_collector(metrics_config)

        @metrics_decorator(metric_type="request", labels={"endpoint": "error_func"})
        async def test_error_func():
            raise ValueError("Test error")

        # Call decorated function
        with pytest.raises(ValueError):
            await test_error_func()

        # Check failed request was recorded
        request_metric = collector.scraper._metrics["requests_total"]
        value = request_metric.labels(
            status="failed", endpoint="error_func", method="GET"
        )._value.get()
        assert value == 1.0


def test_get_metrics_collector_singleton(metrics_config):
    """Test that get_metrics_collector returns singleton."""
    collector1 = get_metrics_collector(metrics_config)
    collector2 = get_metrics_collector()

    assert collector1 is collector2
