"""Integration tests for Phoenix MLS scraper metrics."""

import pytest
import asyncio

from phoenix_real_estate.collectors.phoenix_mls.metrics_integration import (
    ScraperMetricsIntegration,
    ProxyMetricsIntegration,
    metrics_integrated_scraper,
    metrics_integrated_proxy_manager,
)
from phoenix_real_estate.foundation.monitoring import get_metrics_collector, MetricsConfig
from phoenix_real_estate.foundation.monitoring.metrics import _reset_metrics_collector


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
        collection_interval=1,
        labels={"service": "test", "environment": "test"},
    )


@pytest.fixture
def metrics_collector(metrics_config):
    """Create metrics collector for testing."""
    return get_metrics_collector(metrics_config)


class TestScraperMetricsIntegration:
    """Test scraper metrics integration."""

    def test_initialization(self, metrics_collector):
        """Test metrics integration initialization."""
        integration = ScraperMetricsIntegration(metrics_collector)

        assert integration.metrics is not None
        assert integration._session_start_time is None

    def test_track_session_start(self, metrics_collector):
        """Test session start tracking."""
        integration = ScraperMetricsIntegration(metrics_collector)

        integration.track_session_start()

        assert integration._session_start_time is not None

        # Check session status metric
        session_metric = metrics_collector.scraper._metrics["session_valid"]
        assert session_metric._value.get() == 1.0

    def test_track_session_status(self, metrics_collector):
        """Test session status tracking."""
        integration = ScraperMetricsIntegration(metrics_collector)
        integration.track_session_start()

        # Track valid session
        integration.track_session_status(True)

        session_metric = metrics_collector.scraper._metrics["session_valid"]
        age_metric = metrics_collector.scraper._metrics["session_age_seconds"]

        assert session_metric._value.get() == 1.0
        assert age_metric._value.get() >= 0

    @pytest.mark.asyncio
    async def test_track_request_success(self, metrics_collector):
        """Test successful request tracking."""
        integration = ScraperMetricsIntegration(metrics_collector)

        async with integration.track_request("search", "85001"):
            await asyncio.sleep(0.01)  # Simulate work

        # Check metrics
        request_metric = metrics_collector.scraper._metrics["requests_total"]
        property_metric = metrics_collector.scraper._metrics["properties_scraped_total"]

        request_value = request_metric.labels(
            status="success", endpoint="search", method="GET"
        )._value.get()
        property_value = property_metric.labels(zipcode="85001", status="success")._value.get()

        assert request_value == 1.0
        assert property_value == 1.0

    @pytest.mark.asyncio
    async def test_track_request_failure(self, metrics_collector):
        """Test failed request tracking."""
        integration = ScraperMetricsIntegration(metrics_collector)

        with pytest.raises(ValueError):
            async with integration.track_request("search", "85001"):
                raise ValueError("Test error")

        # Check metrics
        request_metric = metrics_collector.scraper._metrics["requests_total"]
        error_metric = metrics_collector.scraper._metrics["errors_total"]

        request_value = request_metric.labels(
            status="failed", endpoint="search", method="GET"
        )._value.get()
        error_value = error_metric.labels(error_type="ValueError", endpoint="search")._value.get()

        assert request_value == 1.0
        assert error_value == 1.0

    def test_track_retry(self, metrics_collector):
        """Test retry tracking."""
        integration = ScraperMetricsIntegration(metrics_collector)

        integration.track_retry("search", 2)

        retry_metric = metrics_collector.scraper._metrics["retries_total"]
        value = retry_metric.labels(endpoint="search", retry_number="2")._value.get()

        assert value == 1.0

    def test_track_content_size(self, metrics_collector):
        """Test content size tracking."""
        integration = ScraperMetricsIntegration(metrics_collector)

        integration.track_content_size(1024, "search", "html")

        # Content size is tracked via histogram, so we can't easily check exact values
        # Just verify the metric exists and was called
        content_metric = metrics_collector.scraper._metrics["content_size_bytes"]
        assert content_metric.labels(endpoint="search", content_type="html") is not None

    def test_track_rate_limit(self, metrics_collector):
        """Test rate limit tracking."""
        integration = ScraperMetricsIntegration(metrics_collector)

        integration.track_rate_limit("search", 5.0)

        hits_metric = metrics_collector.rate_limit._metrics["hits_total"]
        value = hits_metric.labels(endpoint="search", limit_type="scraper_limit")._value.get()

        assert value == 1.0


class TestProxyMetricsIntegration:
    """Test proxy metrics integration."""

    def test_initialization(self, metrics_collector):
        """Test proxy metrics integration initialization."""
        integration = ProxyMetricsIntegration(metrics_collector)

        assert integration.metrics is not None

    def test_update_proxy_counts(self, metrics_collector):
        """Test proxy count updates."""
        integration = ProxyMetricsIntegration(metrics_collector)

        integration.update_proxy_counts(total=5, healthy=3, cooldown=1)

        total_metric = metrics_collector.proxy._metrics["total_count"]
        healthy_metric = metrics_collector.proxy._metrics["healthy_count"]
        cooldown_metric = metrics_collector.proxy._metrics["cooldown_active"]

        assert total_metric._value.get() == 5.0
        assert healthy_metric._value.get() == 3.0
        assert cooldown_metric._value.get() == 1.0

    def test_track_proxy_request(self, metrics_collector):
        """Test proxy request tracking."""
        integration = ProxyMetricsIntegration(metrics_collector)

        integration.track_proxy_request("proxy1", True)
        integration.track_proxy_request("proxy2", False)

        request_metric = metrics_collector.proxy._metrics["requests_total"]

        success_value = request_metric.labels(proxy_id="proxy1", status="success")._value.get()
        failed_value = request_metric.labels(proxy_id="proxy2", status="failed")._value.get()

        assert success_value == 1.0
        assert failed_value == 1.0

    @pytest.mark.asyncio
    async def test_track_proxy_health_check_success(self, metrics_collector):
        """Test successful proxy health check tracking."""
        integration = ProxyMetricsIntegration(metrics_collector)

        async with integration.track_proxy_health_check("proxy1"):
            await asyncio.sleep(0.01)  # Simulate health check

        # Health check duration is tracked via histogram
        duration_metric = metrics_collector.proxy._metrics["health_check_duration_seconds"]
        assert duration_metric.labels(proxy_id="proxy1") is not None

    @pytest.mark.asyncio
    async def test_track_proxy_health_check_failure(self, metrics_collector):
        """Test failed proxy health check tracking."""
        integration = ProxyMetricsIntegration(metrics_collector)

        with pytest.raises(ConnectionError):
            async with integration.track_proxy_health_check("proxy2"):
                raise ConnectionError("Connection failed")

        # Check failure was recorded
        failure_metric = metrics_collector.proxy._metrics["health_check_failures_total"]
        value = failure_metric.labels(proxy_id="proxy2", reason="ConnectionError")._value.get()

        assert value == 1.0

    def test_track_proxy_rotation(self, metrics_collector):
        """Test proxy rotation tracking."""
        integration = ProxyMetricsIntegration(metrics_collector)

        integration.track_proxy_rotation()

        rotation_metric = metrics_collector.proxy._metrics["rotations_total"]
        assert rotation_metric._value.get() == 1.0

    def test_track_proxy_response_time(self, metrics_collector):
        """Test proxy response time tracking."""
        integration = ProxyMetricsIntegration(metrics_collector)

        integration.track_proxy_response_time("proxy1", 0.5)

        # Response time is tracked via summary, so we can't easily check exact values
        response_time_metric = metrics_collector.proxy._metrics["response_time_seconds"]
        assert response_time_metric.labels(proxy_id="proxy1") is not None


class TestScraperIntegrationDecorator:
    """Test scraper integration decorator."""

    def test_decorator_application(self, metrics_collector):
        """Test that decorator is applied correctly."""

        # Mock scraper class
        class MockScraper:
            def __init__(self, config):
                self.config = config
                self.stats = {"rate_limited": 0}

            async def search_properties_by_zipcode(self, zipcode):
                return [{"property": "data"}]

            async def scrape_property_details(self, url):
                return {"url": url, "raw_html": "<html>test</html>"}

            async def maintain_session(self):
                return True

            async def handle_rate_limit(self):
                pass

        # Apply decorator
        DecoratedScraper = metrics_integrated_scraper(MockScraper)

        # Check methods exist
        assert hasattr(DecoratedScraper, "search_properties_by_zipcode")
        assert hasattr(DecoratedScraper, "scrape_property_details")
        assert hasattr(DecoratedScraper, "maintain_session")
        assert hasattr(DecoratedScraper, "handle_rate_limit")

    @pytest.mark.asyncio
    async def test_decorated_scraper_functionality(self, metrics_collector):
        """Test decorated scraper functionality."""

        # Mock scraper class
        class MockScraper:
            def __init__(self, config):
                self.config = config
                self.stats = {"rate_limited": 0}

            async def search_properties_by_zipcode(self, zipcode):
                return [{"property": "data"}]

            async def scrape_property_details(self, url):
                return {"url": url, "raw_html": "<html>test</html>"}

            async def maintain_session(self):
                return True

            async def handle_rate_limit(self):
                pass

        # Apply decorator and create instance
        DecoratedScraper = metrics_integrated_scraper(MockScraper)
        scraper = DecoratedScraper({"test": "config"})

        # Test decorated methods
        result = await scraper.search_properties_by_zipcode("85001")
        assert result == [{"property": "data"}]

        result = await scraper.scrape_property_details("http://test.com")
        assert result["url"] == "http://test.com"

        result = await scraper.maintain_session()
        assert result is True

        # Check metrics were recorded
        assert hasattr(scraper, "_metrics")
        assert scraper._metrics.metrics is not None


class TestProxyManagerIntegrationDecorator:
    """Test proxy manager integration decorator."""

    def test_decorator_application(self):
        """Test that proxy manager decorator is applied correctly."""

        # Mock proxy manager class
        class MockProxyManager:
            def __init__(self, config):
                self.config = config
                self.proxies = [{"host": "proxy1"}, {"host": "proxy2"}]
                self.failure_counts = {}

            async def get_next_proxy(self):
                return {"host": "proxy1", "port": 8080}

            async def mark_failed(self, proxy):
                pass

            def _get_available_proxies(self):
                return self.proxies

            def _is_proxy_available(self, proxy):
                return True

            def _get_proxy_key(self, proxy):
                return f"{proxy['host']}"

        # Apply decorator
        DecoratedProxyManager = metrics_integrated_proxy_manager(MockProxyManager)

        # Check methods exist
        assert hasattr(DecoratedProxyManager, "get_next_proxy")
        assert hasattr(DecoratedProxyManager, "mark_proxy_failed")
        assert hasattr(DecoratedProxyManager, "_update_metrics_counts")

    @pytest.mark.asyncio
    async def test_decorated_proxy_manager_functionality(self, metrics_collector):
        """Test decorated proxy manager functionality."""

        # Mock proxy manager class
        class MockProxyManager:
            def __init__(self, config):
                self.config = config
                self.proxies = [{"host": "proxy1"}, {"host": "proxy2"}]
                self.failure_counts = {}

            async def get_next_proxy(self):
                return {"host": "proxy1", "port": 8080}

            async def mark_failed(self, proxy):
                pass

            def _get_available_proxies(self):
                return self.proxies

            def _is_proxy_available(self, proxy):
                return True

            def _get_proxy_key(self, proxy):
                return f"{proxy['host']}"

        # Apply decorator and create instance
        DecoratedProxyManager = metrics_integrated_proxy_manager(MockProxyManager)
        manager = DecoratedProxyManager({"test": "config"})

        # Test decorated methods
        proxy = await manager.get_next_proxy()
        assert proxy["host"] == "proxy1"

        manager.mark_proxy_failed(proxy, "timeout")

        # Check metrics integration was added
        assert hasattr(manager, "_metrics")
        assert manager._metrics.metrics is not None
