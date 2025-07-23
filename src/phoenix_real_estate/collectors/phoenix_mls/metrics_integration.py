"""Metrics integration for Phoenix MLS scraper.

Provides integration between the scraper and Prometheus metrics collection.
"""

import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.monitoring import (
    MetricsCollector,
    get_metrics_collector,
)

logger = get_logger(__name__)


class ScraperMetricsIntegration:
    """Integration layer between Phoenix MLS scraper and metrics collection."""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize metrics integration.

        Args:
            metrics_collector: Optional metrics collector instance
        """
        self.metrics = metrics_collector or get_metrics_collector()
        self._session_start_time: Optional[float] = None

    def track_session_start(self):
        """Track when a new session starts."""
        self._session_start_time = time.time()
        self.metrics.scraper.set_session_status(True, 0)

    def track_session_status(self, is_valid: bool):
        """Track session validity status."""
        age = None
        if self._session_start_time:
            age = time.time() - self._session_start_time
        self.metrics.scraper.set_session_status(is_valid, age)

    @asynccontextmanager
    async def track_request(self, endpoint: str, zipcode: Optional[str] = None):
        """Context manager to track a scraping request.

        Args:
            endpoint: The endpoint being scraped
            zipcode: Optional zipcode for property tracking

        Yields:
            None
        """
        start_time = time.time()
        status = "success"
        error_type = None

        try:
            yield
        except Exception as e:
            status = "failed"
            error_type = type(e).__name__
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time

            # Basic request metrics
            self.metrics.scraper.record_request(status, endpoint)
            self.metrics.scraper.record_response_time(duration, endpoint, status)

            # Error tracking
            if error_type:
                self.metrics.scraper.record_error(error_type, endpoint)

            # Property tracking
            if zipcode and status == "success":
                self.metrics.scraper.record_property_scraped(zipcode, status)

    def track_retry(self, endpoint: str, retry_number: int):
        """Track a retry attempt."""
        self.metrics.scraper.record_retry(endpoint, retry_number)

    def track_content_size(self, size_bytes: int, endpoint: str, content_type: str = "html"):
        """Track content size."""
        self.metrics.scraper.record_content_size(size_bytes, endpoint, content_type)

    def track_rate_limit(self, endpoint: str, wait_time: float):
        """Track rate limit hit."""
        self.metrics.rate_limit.record_rate_limit_hit(endpoint, "scraper_limit", wait_time)

    def update_rate_limit_stats(self, endpoint: str, current_rate: float, remaining: int):
        """Update rate limit statistics."""
        self.metrics.rate_limit.set_current_rate(endpoint, current_rate)
        self.metrics.rate_limit.set_limit_remaining(endpoint, remaining)


class ProxyMetricsIntegration:
    """Integration layer between proxy manager and metrics collection."""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize metrics integration.

        Args:
            metrics_collector: Optional metrics collector instance
        """
        self.metrics = metrics_collector or get_metrics_collector()

    def update_proxy_counts(self, total: int, healthy: int, cooldown: int):
        """Update proxy count metrics."""
        self.metrics.proxy.set_proxy_counts(total, healthy)
        self.metrics.proxy.set_cooldown_count(cooldown)

    def track_proxy_request(self, proxy_id: str, success: bool):
        """Track a proxy request."""
        status = "success" if success else "failed"
        self.metrics.proxy.record_proxy_request(proxy_id, status)

    @asynccontextmanager
    async def track_proxy_health_check(self, proxy_id: str):
        """Context manager to track proxy health check.

        Args:
            proxy_id: Proxy identifier

        Yields:
            None
        """
        start_time = time.time()
        success = True
        reason = ""

        try:
            yield
        except Exception as e:
            success = False
            reason = type(e).__name__
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.proxy.record_health_check(proxy_id, duration, success, reason)

    def track_proxy_rotation(self):
        """Track a proxy rotation event."""
        self.metrics.proxy.record_rotation()

    def track_proxy_response_time(self, proxy_id: str, duration: float):
        """Track proxy response time."""
        self.metrics.proxy.record_proxy_response_time(proxy_id, duration)


def metrics_integrated_scraper(scraper_class):
    """Decorator to add metrics integration to a scraper class.

    This decorator wraps key methods of the scraper to automatically
    collect metrics without modifying the original code.

    Args:
        scraper_class: The scraper class to decorate

    Returns:
        Decorated scraper class with metrics integration
    """
    original_init = scraper_class.__init__

    def new_init(self, *args, **kwargs):
        """Enhanced init with metrics integration."""
        original_init(self, *args, **kwargs)
        self._metrics = ScraperMetricsIntegration()
        self._metrics.track_session_start()

    # Wrap search_properties_by_zipcode
    original_search = scraper_class.search_properties_by_zipcode

    async def new_search(self, zipcode: str) -> Any:
        """Enhanced search with metrics tracking."""
        async with self._metrics.track_request("search", zipcode):
            result = await original_search(self, zipcode)
            # Track content size if available
            if hasattr(result, "__len__"):
                size = len(str(result).encode())
                self._metrics.track_content_size(size, "search")
            return result

    # Wrap scrape_property_details
    original_scrape = scraper_class.scrape_property_details

    async def new_scrape(self, property_url: str) -> Any:
        """Enhanced scrape with metrics tracking."""
        async with self._metrics.track_request("property_details"):
            result = await original_scrape(self, property_url)
            # Track HTML size
            if "raw_html" in result:
                size = len(result["raw_html"].encode())
                self._metrics.track_content_size(size, "property_details", "html")
            return result

    # Wrap maintain_session
    original_maintain = scraper_class.maintain_session

    async def new_maintain(self) -> bool:
        """Enhanced session maintenance with metrics."""
        result = await original_maintain(self)
        self._metrics.track_session_status(result)
        return result

    # Wrap handle_rate_limit
    original_rate_limit = scraper_class.handle_rate_limit

    async def new_rate_limit(self):
        """Enhanced rate limit handling with metrics."""
        wait_time = min(60, 2 ** self.stats["rate_limited"])
        self._metrics.track_rate_limit("phoenix_mls", wait_time)
        await original_rate_limit(self)

    # Apply wrapped methods
    scraper_class.__init__ = new_init
    scraper_class.search_properties_by_zipcode = new_search
    scraper_class.scrape_property_details = new_scrape
    scraper_class.maintain_session = new_maintain
    scraper_class.handle_rate_limit = new_rate_limit

    return scraper_class


def metrics_integrated_proxy_manager(proxy_manager_class):
    """Decorator to add metrics integration to proxy manager class.

    Args:
        proxy_manager_class: The proxy manager class to decorate

    Returns:
        Decorated proxy manager class with metrics integration
    """
    original_init = proxy_manager_class.__init__

    def new_init(self, *args, **kwargs):
        """Enhanced init with metrics integration."""
        original_init(self, *args, **kwargs)
        self._metrics = ProxyMetricsIntegration()
        # Initial count update
        self._update_metrics_counts()

    def _update_metrics_counts(self):
        """Update proxy count metrics."""
        total = len(self.proxies)
        healthy = len(self._get_available_proxies())
        cooldown = sum(1 for proxy in self.proxies if not self._is_proxy_available(proxy))
        self._metrics.update_proxy_counts(total, healthy, cooldown)

    # Wrap get_next_proxy
    original_get_next = proxy_manager_class.get_next_proxy

    async def new_get_next(self) -> Any:
        """Enhanced get_next_proxy with metrics."""
        proxy = await original_get_next(self)
        proxy_key = self._get_proxy_key(proxy)
        self._metrics.track_proxy_request(proxy_key, True)
        self._metrics.track_proxy_rotation()
        return proxy

    # Wrap mark_failed
    original_mark_failed = proxy_manager_class.mark_failed

    async def new_mark_failed(self, proxy: Dict[str, Any]):
        """Enhanced mark_failed with metrics."""
        proxy_key = self._get_proxy_key(proxy)
        self._metrics.track_proxy_request(proxy_key, False)
        await original_mark_failed(self, proxy)
        self._update_metrics_counts()

    # Wrap check_health
    if hasattr(proxy_manager_class, "check_health"):
        original_check_health = proxy_manager_class.check_health

        async def new_check_health(self, proxy: Dict[str, Any]) -> bool:
            """Enhanced check_health with metrics."""
            proxy_key = self._get_proxy_key(proxy)
            async with self._metrics.track_proxy_health_check(proxy_key):
                return await original_check_health(self, proxy)

        proxy_manager_class.check_health = new_check_health

    # Apply wrapped methods
    proxy_manager_class.__init__ = new_init
    proxy_manager_class.get_next_proxy = new_get_next
    proxy_manager_class.mark_failed = new_mark_failed
    proxy_manager_class._update_metrics_counts = _update_metrics_counts

    return proxy_manager_class
