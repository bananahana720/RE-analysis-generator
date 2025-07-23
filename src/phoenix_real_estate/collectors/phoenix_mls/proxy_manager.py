"""Proxy Manager for Phoenix MLS Scraper.

Handles proxy rotation, health checks, and failure recovery.
"""

import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from threading import Lock

from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class ProxyError(Exception):
    """Base exception for proxy-related errors."""

    pass


class NoHealthyProxiesError(ProxyError):
    """Raised when no healthy proxies are available."""

    pass


class ProxyManager:
    """Manages proxy rotation and health monitoring for web scraping.

    Features:
    - Round-robin proxy rotation
    - Health monitoring and automatic recovery
    - Thread-safe concurrent usage
    - Failure tracking with cooldown periods
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize ProxyManager with configuration.

        Args:
            config: Dictionary containing:
                - proxies: List of proxy configurations
                - max_failures: Maximum failures before marking unhealthy (default: 3)
                - cooldown_minutes: Minutes before retry after max failures (default: 5)
                - health_check_url: URL for health checks (default: httpbin.org/ip)
        """
        self.config = config
        self.proxies = config.get("proxies", [])

        if not self.proxies:
            raise ValueError("No proxies configured")

        # Thread-safe rotation
        self.current_index = 0
        self.lock = Lock()

        # Health tracking
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_failure_time: Dict[str, datetime] = {}
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)

        # Configuration with defaults
        self.max_failures = config.get("max_failures", 3)
        self.cooldown_minutes = config.get("cooldown_minutes", 5)
        self.health_check_url = config.get("health_check_url", "https://httpbin.org/ip")

        logger.info(f"ProxyManager initialized with {len(self.proxies)} proxies")

    async def get_next_proxy(self) -> Dict[str, Any]:
        """Get the next available proxy in rotation.

        Returns:
            Dictionary containing proxy information

        Raises:
            NoHealthyProxiesError: If no healthy proxies are available
        """
        with self.lock:
            # Check for available proxies
            available_proxies = self._get_available_proxies()
            if not available_proxies:
                logger.error("No healthy proxies available")
                raise NoHealthyProxiesError("No healthy proxies available")

            # Find next available proxy in rotation
            attempts = 0
            while attempts < len(self.proxies):
                proxy = self.proxies[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.proxies)
                attempts += 1

                if self._is_proxy_available(proxy):
                    proxy_key = self._get_proxy_key(proxy)
                    self.request_counts[proxy_key] += 1
                    logger.debug(f"Selected proxy: {proxy_key}")
                    return proxy.copy()

            # Should not reach here if available_proxies > 0
            raise NoHealthyProxiesError("Failed to find available proxy")

    def _get_available_proxies(self) -> List[Dict[str, Any]]:
        """Get list of currently available proxies.

        Returns:
            List of available proxy configurations
        """
        return [p for p in self.proxies if self._is_proxy_available(p)]

    def _is_proxy_available(self, proxy: Dict[str, Any]) -> bool:
        """Check if a proxy is available for use.

        Args:
            proxy: Proxy configuration to check

        Returns:
            True if proxy is available, False otherwise
        """
        proxy_key = self._get_proxy_key(proxy)

        # Check if proxy has exceeded failure threshold
        if self.failure_counts[proxy_key] >= self.max_failures:
            # Check if cooldown period has passed
            last_failure = self.last_failure_time.get(proxy_key)
            if last_failure:
                cooldown_end = last_failure + timedelta(minutes=self.cooldown_minutes)
                if datetime.now() < cooldown_end:
                    return False
                else:
                    # Reset after cooldown
                    logger.info(f"Proxy {proxy_key} recovered after cooldown")
                    self._reset_proxy_health(proxy_key)

        return True

    def _get_proxy_key(self, proxy: Dict[str, Any]) -> str:
        """Get unique identifier for a proxy.

        Args:
            proxy: Proxy configuration

        Returns:
            Unique string identifier
        """
        return f"{proxy['host']}:{proxy['port']}"

    def _reset_proxy_health(self, proxy_key: str):
        """Reset health tracking for a proxy.

        Args:
            proxy_key: Unique proxy identifier
        """
        self.failure_counts[proxy_key] = 0
        if proxy_key in self.last_failure_time:
            del self.last_failure_time[proxy_key]

    async def mark_failed(self, proxy: Dict[str, Any]):
        """Mark a proxy as failed.

        Args:
            proxy: The proxy that failed
        """
        proxy_key = self._get_proxy_key(proxy)
        self.failure_counts[proxy_key] += 1
        self.last_failure_time[proxy_key] = datetime.now()

        logger.warning(
            f"Proxy {proxy_key} failed. "
            f"Total failures: {self.failure_counts[proxy_key]}/{self.max_failures}"
        )

    async def mark_success(self, proxy: Dict[str, Any]):
        """Mark a proxy request as successful.

        Args:
            proxy: The proxy that succeeded
        """
        proxy_key = self._get_proxy_key(proxy)
        self.success_counts[proxy_key] += 1

    def get_failure_count(self, proxy: Dict[str, Any]) -> int:
        """Get the failure count for a proxy.

        Args:
            proxy: The proxy to check

        Returns:
            Number of failures
        """
        return self.failure_counts[self._get_proxy_key(proxy)]

    async def check_health(self, proxy: Dict[str, Any]) -> bool:
        """Check if a proxy is healthy by making a test request.

        Args:
            proxy: The proxy to check

        Returns:
            True if healthy, False otherwise
        """
        proxy_url = self.format_proxy_url(proxy)
        proxy_key = self._get_proxy_key(proxy)

        try:
            logger.debug(f"Health check for proxy {proxy_key}")

            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url}, timeout=httpx.Timeout(10.0)
            ) as client:
                response = await client.get(self.health_check_url)

                if response.status_code == 200:
                    logger.debug(f"Proxy {proxy_key} is healthy")
                    return True
                else:
                    logger.warning(
                        f"Proxy {proxy_key} health check failed: status {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Proxy {proxy_key} health check error: {e}")
            return False

    async def check_all_health(self) -> Dict[str, bool]:
        """Check health of all proxies.

        Returns:
            Dictionary mapping proxy keys to health status
        """
        health_status = {}

        for proxy in self.proxies:
            proxy_key = self._get_proxy_key(proxy)
            health_status[proxy_key] = await self.check_health(proxy)

        return health_status

    async def check_recovery(self):
        """Check if any failed proxies have recovered after cooldown."""
        now = datetime.now()
        recovered = []

        for proxy_key, last_failure in list(self.last_failure_time.items()):
            cooldown_end = last_failure + timedelta(minutes=self.cooldown_minutes)
            if now >= cooldown_end:
                self._reset_proxy_health(proxy_key)
                recovered.append(proxy_key)

        if recovered:
            logger.info(f"Proxies recovered after cooldown: {recovered}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive proxy usage statistics.

        Returns:
            Dictionary with detailed statistics
        """
        available_proxies = self._get_available_proxies()
        healthy_count = len(available_proxies)
        failed_count = len(self.proxies) - healthy_count

        total_requests = sum(self.request_counts.values())
        total_successes = sum(self.success_counts.values())
        total_failures = sum(self.failure_counts.values())

        stats = {
            "total_proxies": len(self.proxies),
            "healthy_proxies": healthy_count,
            "failed_proxies": failed_count,
            "total_requests": total_requests,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": ((total_successes / total_requests * 100) if total_requests > 0 else 0),
            "proxy_details": {},
        }

        # Add per-proxy details
        for proxy in self.proxies:
            proxy_key = self._get_proxy_key(proxy)
            stats["proxy_details"][proxy_key] = {
                "requests": self.request_counts[proxy_key],
                "successes": self.success_counts[proxy_key],
                "failures": self.failure_counts[proxy_key],
                "is_healthy": self._is_proxy_available(proxy),
                "last_failure": self.last_failure_time.get(proxy_key),
            }

        return stats

    def format_proxy_url(self, proxy: Dict[str, Any]) -> str:
        """Format proxy configuration into URL string.

        Args:
            proxy: Proxy configuration with host, port, and optional auth

        Returns:
            Formatted proxy URL string
        """
        proto = proxy.get("type", "http")
        host = proxy["host"]
        port = proxy["port"]

        # Add authentication if provided
        if "username" in proxy and "password" in proxy:
            auth = f"{proxy['username']}:{proxy['password']}@"
        else:
            auth = ""

        return f"{proto}://{auth}{host}:{port}"

    def __repr__(self) -> str:
        """String representation of ProxyManager."""
        stats = self.get_statistics()
        return (
            f"ProxyManager("
            f"total={stats['total_proxies']}, "
            f"healthy={stats['healthy_proxies']}, "
            f"failed={stats['failed_proxies']})"
        )
