"""Rate limiter implementation with observer pattern.

This module provides a thread-safe rate limiting system with sliding window
algorithm, observer pattern for monitoring, and async/await compatibility.
Designed for API clients with configurable safety margins.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Protocol, DefaultDict
from collections import defaultdict, deque
from datetime import datetime
from dataclasses import dataclass

from phoenix_real_estate.foundation.logging.factory import get_logger


@dataclass
class RateLimitStatus:
    """Rate limit status information for backward compatibility.

    This class is maintained for compatibility with existing code that
    expects the RateLimitStatus interface. New code should use the
    get_current_usage() method instead.

    Attributes:
        requests_made: Number of requests made in current window
        requests_remaining: Number of requests remaining in current window
        window_reset_time: When the current rate limit window resets
        is_rate_limited: Whether rate limiting is currently active
        retry_after_seconds: Seconds to wait before next request (if limited)
    """

    requests_made: int
    requests_remaining: int
    window_reset_time: datetime
    is_rate_limited: bool
    retry_after_seconds: float = 0.0


class RateLimitObserver(Protocol):
    """Observer protocol for rate limit notifications.

    Classes implementing this protocol can be registered to receive
    notifications when rate limit events occur.
    """

    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        """Called when a request is made.

        Args:
            source: Source identifier for the request
            timestamp: When the request was made
        """
        pass

    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        """Called when rate limit is hit and waiting is required.

        Args:
            source: Source identifier that hit the limit
            wait_time: Seconds to wait before next request
        """
        pass

    async def on_rate_limit_reset(self, source: str) -> None:
        """Called when rate limit window resets for a source.

        Args:
            source: Source identifier for the reset
        """
        pass


class RateLimiter:
    """Thread-safe rate limiter with sliding window algorithm and observer pattern.

    This rate limiter provides:
    - Sliding window algorithm with configurable safety margins
    - Thread-safe concurrent request handling
    - Observer pattern for monitoring and notifications
    - Per-source rate limiting with shared effective limits
    - Real-time usage tracking and utilization metrics
    - Epic 1 logging integration with structured metadata

    Key Features:
    - Safety margin calculation (1000 → 900 effective limit for 10% margin)
    - Async/await compatible design patterns
    - <100ms response time for rate limit checks
    - Efficient memory usage with automatic cleanup
    - Observer notifications for Epic 4 monitoring integration

    Example:
        >>> limiter = RateLimiter(requests_per_minute=1000, safety_margin=0.10)
        >>> wait_time = await limiter.wait_if_needed('api_source')
        >>> if wait_time == 0:
        ...     # Make API request
        ...     pass
    """

    def __init__(
        self,
        requests_per_minute: int = 1000,
        safety_margin: float = 0.10,
        window_duration: int = 60,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute (default: 1000)
            safety_margin: Safety margin as decimal (0.1 = 10%, default: 0.10)
            window_duration: Rate limit window duration in seconds (default: 60)
        """
        self.requests_per_minute = requests_per_minute
        self.safety_margin = safety_margin
        self.window_duration = window_duration

        # Calculate effective limit with safety margin
        # Example: 1000 requests → 900 effective limit (10% margin)
        self.effective_limit = int(requests_per_minute * (1 - safety_margin))

        # Thread safety
        self._lock = asyncio.Lock()

        # Per-source request tracking using sliding window
        self._source_requests: DefaultDict[str, deque[float]] = defaultdict(deque)

        # Observer management
        self._observers: List[RateLimitObserver] = []

        # Logging integration
        self.logger = get_logger(__name__)

        self.logger.info(
            "Rate limiter initialized",
            extra={
                "requests_per_minute": requests_per_minute,
                "safety_margin_percent": safety_margin * 100,
                "effective_limit": self.effective_limit,
                "window_duration_seconds": window_duration,
            },
        )

    def add_observer(self, observer: RateLimitObserver) -> None:
        """Add a rate limit observer.

        Args:
            observer: Observer to register for notifications
        """
        if observer not in self._observers:
            self._observers.append(observer)
            self.logger.debug(
                "Added rate limit observer", extra={"observer_type": type(observer).__name__}
            )

    def remove_observer(self, observer: RateLimitObserver) -> None:
        """Remove a rate limit observer.

        Args:
            observer: Observer to unregister
        """
        if observer in self._observers:
            self._observers.remove(observer)
            self.logger.debug(
                "Removed rate limit observer", extra={"observer_type": type(observer).__name__}
            )

    async def wait_if_needed(self, source: str) -> float:
        """Main rate limiting method - wait if needed before making request.

        This is the primary method for rate limiting. It checks if a request
        can be made immediately, and if not, calculates and returns the wait time.

        Args:
            source: Source identifier for the request

        Returns:
            Wait time in seconds (0.0 if no wait needed)

        Example:
            >>> wait_time = await limiter.wait_if_needed('maricopa_api')
            >>> if wait_time > 0:
            ...     await asyncio.sleep(wait_time)
            >>> # Now safe to make request
        """
        async with self._lock:
            current_time = time.time()

            # Cleanup old requests first
            self._cleanup_old_requests(source)

            # Check if we can make a request immediately
            current_requests = len(self._source_requests[source])

            if current_requests < self.effective_limit:
                # Record the request and notify observers
                timestamp = datetime.fromtimestamp(current_time)
                self._source_requests[source].append(current_time)

                await self._notify_observers("request_made", source=source, timestamp=timestamp)

                self.logger.debug(
                    "Request allowed immediately",
                    extra={
                        "source": source,
                        "current_requests": current_requests + 1,
                        "effective_limit": self.effective_limit,
                        "utilization_percent": ((current_requests + 1) / self.effective_limit)
                        * 100,
                    },
                )
                return 0.0

            # Rate limit hit - calculate wait time
            if self._source_requests[source]:
                oldest_request = self._source_requests[source][0]
                wait_time = max(0.0, (oldest_request + self.window_duration) - current_time)

                await self._notify_observers("rate_limit_hit", source=source, wait_time=wait_time)

                self.logger.info(
                    "Rate limit hit",
                    extra={
                        "source": source,
                        "wait_time_seconds": wait_time,
                        "current_requests": current_requests,
                        "effective_limit": self.effective_limit,
                    },
                )
                return wait_time

            # No requests in window, should not happen
            return 0.0

    def get_current_usage(self, source: Optional[str] = None) -> dict:
        """Get current usage statistics for monitoring.

        Args:
            source: Specific source to get stats for, or None for all sources

        Returns:
            Dictionary containing usage statistics and utilization metrics

        Example:
            >>> usage = limiter.get_current_usage('maricopa_api')
            >>> print(f"Current usage: {usage['current_requests']}/{usage['effective_limit']}")
            >>> print(f"Utilization: {usage['utilization_percent']}%")
        """
        current_time = time.time()

        if source:
            # Clean up old requests for this source
            self._cleanup_old_requests(source)
            current_requests = len(self._source_requests[source])

            # Calculate next available slot time
            next_available = 0.0
            if current_requests >= self.effective_limit and self._source_requests[source]:
                oldest_request = self._source_requests[source][0]
                next_available = max(0.0, (oldest_request + self.window_duration) - current_time)

            return {
                "source": source,
                "current_requests": current_requests,
                "effective_limit": self.effective_limit,
                "requests_remaining": max(0, self.effective_limit - current_requests),
                "utilization_percent": (current_requests / self.effective_limit) * 100,
                "is_rate_limited": current_requests >= self.effective_limit,
                "next_available_seconds": next_available,
                "window_duration": self.window_duration,
            }
        else:
            # Get stats for all sources
            total_requests = 0
            sources = list(self._source_requests.keys())

            for src in sources:
                self._cleanup_old_requests(src)
                total_requests += len(self._source_requests[src])

            return {
                "total_sources": len(sources),
                "total_current_requests": total_requests,
                "effective_limit_per_source": self.effective_limit,
                "sources": sources,
                "observers_count": len(self._observers),
                "window_duration": self.window_duration,
                "safety_margin_percent": self.safety_margin * 100,
            }

    async def _notify_observers(self, event_type: str, **kwargs) -> None:
        """Notify all registered observers of an event.

        Args:
            event_type: Type of event ('request_made', 'rate_limit_hit', 'rate_limit_reset')
            **kwargs: Event-specific keyword arguments
        """
        if not self._observers:
            return

        # Create notification tasks for all observers
        tasks = []

        for observer in self._observers:
            try:
                if event_type == "request_made":
                    tasks.append(observer.on_request_made(kwargs["source"], kwargs["timestamp"]))
                elif event_type == "rate_limit_hit":
                    tasks.append(observer.on_rate_limit_hit(kwargs["source"], kwargs["wait_time"]))
                elif event_type == "rate_limit_reset":
                    tasks.append(observer.on_rate_limit_reset(kwargs["source"]))
            except Exception as e:
                self.logger.error(
                    "Observer notification failed",
                    extra={
                        "observer_type": type(observer).__name__,
                        "event_type": event_type,
                        "error": str(e),
                    },
                )

        # Execute all notifications concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _cleanup_old_requests(self, source: str) -> None:
        """Remove request timestamps outside the current sliding window.

        This method implements the sliding window cleanup, removing timestamps
        that are older than the window duration. This is called automatically
        before rate limit checks to ensure accurate request counting.

        Args:
            source: Source identifier to clean up
        """
        if source not in self._source_requests:
            return

        current_time = time.time()
        window_start = current_time - self.window_duration
        requests = self._source_requests[source]

        # Remove timestamps outside the sliding window
        removed_count = 0
        while requests and requests[0] < window_start:
            requests.popleft()
            removed_count += 1

        # Log cleanup if significant number of requests were removed
        if removed_count > 0:
            self.logger.debug(
                "Cleaned up old requests",
                extra={
                    "source": source,
                    "removed_requests": removed_count,
                    "remaining_requests": len(requests),
                },
            )

    async def reset_source(self, source: str) -> None:
        """Reset rate limit tracking for a specific source.

        Args:
            source: Source identifier to reset
        """
        async with self._lock:
            if source in self._source_requests:
                self._source_requests[source].clear()

                await self._notify_observers("rate_limit_reset", source=source)

                self.logger.info("Rate limit reset for source", extra={"source": source})

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics for monitoring.

        Returns:
            Dictionary containing detailed performance and utilization metrics
        """
        # Calculate total active sources and requests
        total_sources = len(self._source_requests)
        total_requests = sum(len(requests) for requests in self._source_requests.values())

        # Find most active source
        most_active_source = None
        max_requests = 0

        for source, requests in self._source_requests.items():
            if len(requests) > max_requests:
                max_requests = len(requests)
                most_active_source = source

        return {
            # Configuration
            "configured_limit": self.requests_per_minute,
            "effective_limit": self.effective_limit,
            "safety_margin_percent": self.safety_margin * 100,
            "window_duration_seconds": self.window_duration,
            # Current state
            "total_active_sources": total_sources,
            "total_current_requests": total_requests,
            "observer_count": len(self._observers),
            # Utilization metrics
            "most_active_source": most_active_source,
            "max_source_requests": max_requests,
            "max_source_utilization_percent": (max_requests / self.effective_limit) * 100
            if self.effective_limit > 0
            else 0,
            # Memory efficiency
            "memory_efficient": all(
                len(requests) <= self.effective_limit * 2
                for requests in self._source_requests.values()
            ),
            "cleanup_working": True,  # Always true as cleanup is called before checks
        }

    def get_status(self, source: str = "default") -> RateLimitStatus:
        """Get rate limit status for backward compatibility.

        This method maintains compatibility with existing code that expects
        the old RateLimitStatus interface. New code should use get_current_usage().

        Args:
            source: Source identifier for the request (default: "default")

        Returns:
            RateLimitStatus object with current rate limit information
        """
        usage = self.get_current_usage(source)

        # Calculate window reset time
        current_time = time.time()
        window_reset_time = datetime.fromtimestamp(current_time + self.window_duration)

        return RateLimitStatus(
            requests_made=usage["current_requests"],
            requests_remaining=usage["requests_remaining"],
            window_reset_time=window_reset_time,
            is_rate_limited=usage["is_rate_limited"],
            retry_after_seconds=usage["next_available_seconds"],
        )
