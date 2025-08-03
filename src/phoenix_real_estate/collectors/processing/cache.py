"""Caching layer for LLM responses to reduce costs and improve performance."""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable, List
import sys

from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheConfig:
    """Configuration for cache system."""

    enabled: bool = True
    ttl_hours: float = 24.0
    max_size_mb: float = 100.0
    eviction_policy: str = "lru"  # lru, lfu, fifo
    backend: str = "memory"  # memory, redis
    redis_url: Optional[str] = None
    warmup_on_start: bool = False
    compression_enabled: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if self.backend == "redis" and not self.redis_url:
            logger.warning("Redis backend selected but no URL provided, falling back to memory")
            self.backend = "memory"


@dataclass
class CacheMetrics:
    """Metrics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    bytes_stored: int = 0
    bytes_retrieved: int = 0

    def record_hit(self, size_bytes: int = 0) -> None:
        """Record a cache hit."""
        self.hits += 1
        self.bytes_retrieved += size_bytes

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1

    def record_set(self, size_bytes: int = 0) -> None:
        """Record a cache set operation."""
        self.sets += 1
        self.bytes_stored += size_bytes

    def record_eviction(self) -> None:
        """Record a cache eviction."""
        self.evictions += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "sets": self.sets,
            "evictions": self.evictions,
            "bytes_stored": self.bytes_stored,
            "bytes_retrieved": self.bytes_retrieved,
            "total_requests": total_requests,
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0
        self.bytes_stored = 0
        self.bytes_retrieved = 0


class LRUCache:
    """Least Recently Used cache implementation with TTL support."""

    def __init__(
        self, max_size: int = 1000, ttl_seconds: float = 86400, max_memory_mb: float = 100
    ):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time to live for entries in seconds
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

        self._cache: OrderedDict[str, tuple[Any, float, int]] = OrderedDict()
        self._lock = asyncio.Lock()
        self.memory_used = 0
        self.eviction_count = 0

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value."""
        if isinstance(value, str):
            return len(value.encode("utf-8"))
        elif isinstance(value, (dict, list)):
            return len(json.dumps(value).encode("utf-8"))
        else:
            return sys.getsizeof(value)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None

        value, timestamp, size = self._cache[key]

        # Check TTL
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            self.memory_used -= size
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return value

    async def get_async(self, key: str) -> Optional[Any]:
        """Async get for async contexts."""
        async with self._lock:
            return self.get(key)

    def put(self, key: str, value: Any) -> None:
        """Put value in cache."""
        self._put_internal_sync(key, value)

    async def put_async(self, key: str, value: Any) -> None:
        """Async put for async contexts."""
        async with self._lock:
            self._put_internal_sync(key, value)

    def _put_internal_sync(self, key: str, value: Any) -> None:
        """Internal put implementation (sync version)."""
        size = self._estimate_size(value)

        # Remove old entry if exists
        if key in self._cache:
            _, _, old_size = self._cache[key]
            self.memory_used -= old_size

        # Check if the single item is too large for the cache
        if size > self.max_memory_bytes:
            logger.warning(
                f"Item too large for cache: {size} bytes > {self.max_memory_bytes} bytes"
            )
            # Don't store items that exceed the memory limit
            return

        # Check memory limit - evict until we have enough space
        while self.memory_used + size > self.max_memory_bytes and self._cache:
            self._evict_one()

        # Check size limit
        while len(self._cache) >= self.max_size:
            self._evict_one()

        # Add new entry
        self._cache[key] = (value, time.time(), size)
        self.memory_used += size

    def _evict_one(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Remove oldest (first) item
        key, (_, _, size) = self._cache.popitem(last=False)
        self.memory_used -= size
        self.eviction_count += 1
        logger.debug(f"Evicted cache entry: {key[:50]}...")

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self.memory_used = 0

    def size(self) -> int:
        """Get number of entries in cache."""
        return len(self._cache)


class CacheManager:
    """Manages caching for LLM responses."""

    def __init__(self, config: CacheConfig):
        """Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._metrics = CacheMetrics()
        self._backend_type = config.backend
        self._backend: Optional[Any] = None
        self._initialized = False
        self._alert_callbacks: List[Callable] = []

    async def initialize(self) -> None:
        """Initialize cache backend."""
        if self._initialized:
            return

        if not self.config.enabled:
            logger.info("Cache disabled by configuration")
            self._initialized = True
            return

        try:
            if self.config.backend == "redis":
                await self._init_redis()
            else:
                await self._init_memory()

            self._initialized = True
            logger.info(f"Cache initialized with {self._backend_type} backend")

        except Exception as e:
            logger.error(f"Failed to initialize {self.config.backend} cache: {e}")
            # Fallback to memory
            if self.config.backend != "memory":
                logger.info("Falling back to memory cache")
                self._backend_type = "memory"
                await self._init_memory()
                self._initialized = True

    async def _init_memory(self) -> None:
        """Initialize in-memory cache."""
        self._backend = LRUCache(
            max_size=10000,
            ttl_seconds=self.config.ttl_hours * 3600,
            max_memory_mb=self.config.max_size_mb,
        )

    async def _init_redis(self) -> None:
        """Initialize Redis cache."""
        try:
            import redis.asyncio as redis

            self._backend = await redis.from_url(
                self.config.redis_url or "redis://localhost:6379", decode_responses=True
            )
            # Test connection
            await self._backend.ping()
        except ImportError:
            raise RuntimeError("redis package not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")

    def _generate_cache_key(self, property_data: Dict[str, Any], operation: str) -> str:
        """Generate deterministic cache key from property data.

        Args:
            property_data: Property information or LLM data
            operation: Type of operation (extraction, validation, completion, etc.)

        Returns:
            Cache key string
        """
        # Check if this is LLM completion data (has prompt and cache_key)
        if "prompt" in property_data and "cache_key" in property_data:
            # For LLM completion caching, use prompt and cache_key
            cache_data = {
                "prompt": property_data.get("prompt", ""),
                "cache_key": property_data.get("cache_key", ""),
                "operation": operation,
            }
        else:
            # For property data caching, use property fields
            cache_data = {
                "address": property_data.get("address", ""),
                "bedrooms": property_data.get("bedrooms", 0),
                "bathrooms": property_data.get("bathrooms", 0),
                "sqft": property_data.get("sqft", 0),
                "price": property_data.get("price", 0),
                "listing_id": property_data.get("listing_id", ""),
                "operation": operation,
            }

        # Create deterministic string representation
        data_str = json.dumps(cache_data, sort_keys=True)

        # Generate hash (not for security, just for caching)
        hash_value = hashlib.md5(data_str.encode(), usedforsecurity=False).hexdigest()

        return f"llm:{operation}:{hash_value}"

    async def get(self, property_data: Dict[str, Any], operation: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached LLM response if available.

        Args:
            property_data: Property information
            operation: Type of operation

        Returns:
            Cached response or None if not found
        """
        if not self.config.enabled or not self._initialized:
            return None

        cache_key = self._generate_cache_key(property_data, operation)

        try:
            if self._backend_type == "memory":
                cached = await self._backend.get_async(cache_key)
            else:
                cached = await self._backend.get(cache_key)
                if cached:
                    cached = json.loads(cached)

            if cached:
                self._metrics.record_hit(len(json.dumps(cached)))
                logger.debug(f"Cache hit for {operation}: {cache_key[:50]}...")
                return cached
            else:
                self._metrics.record_miss()
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self._metrics.record_miss()
            return None

    async def set(
        self, property_data: Dict[str, Any], operation: str, response: Dict[str, Any]
    ) -> None:
        """Cache LLM response with TTL.

        Args:
            property_data: Property information
            operation: Type of operation
            response: LLM response to cache
        """
        if not self.config.enabled or not self._initialized:
            return

        cache_key = self._generate_cache_key(property_data, operation)

        try:
            response_str = json.dumps(response)
            size_bytes = len(response_str.encode())

            if self._backend_type == "memory":
                await self._backend.put_async(cache_key, response)
            else:
                await self._backend.setex(
                    cache_key, int(self.config.ttl_hours * 3600), response_str
                )

            self._metrics.record_set(size_bytes)
            logger.debug(f"Cached {operation} response: {cache_key[:50]}...")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def warmup(
        self, properties: List[Dict[str, Any]], responses: List[Dict[str, Any]], operation: str
    ) -> None:
        """Warm up cache with pre-computed responses.

        Args:
            properties: List of property data
            responses: Corresponding LLM responses
            operation: Type of operation
        """
        if not self.config.enabled or not self._initialized:
            return

        logger.info(f"Warming up cache with {len(properties)} entries for {operation}")

        for prop, resp in zip(properties, responses):
            await self.set(prop, operation, resp)

    async def invalidate(self, property_data: Dict[str, Any], operation: str) -> None:
        """Invalidate specific cache entry.

        Args:
            property_data: Property information
            operation: Type of operation
        """
        if not self.config.enabled or not self._initialized:
            return

        cache_key = self._generate_cache_key(property_data, operation)

        try:
            if self._backend_type == "memory":
                # Memory backend doesn't have delete, so we set None
                await self._backend.put_async(cache_key, None)
            else:
                await self._backend.delete(cache_key)

            logger.debug(f"Invalidated cache entry: {cache_key[:50]}...")

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def invalidate_pattern(self, property_data: Dict[str, Any]) -> None:
        """Invalidate all cache entries for a property.

        Args:
            property_data: Property information
        """
        # For now, invalidate common operations
        # In production, would use Redis SCAN with pattern
        operations = ["extraction", "validation", "analysis"]

        for op in operations:
            await self.invalidate(property_data, op)

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics.

        Returns:
            Dictionary of cache metrics
        """
        stats = self._metrics.get_stats()

        if self._backend_type == "memory" and self._backend:
            stats["entries"] = self._backend.size()
            stats["memory_used_mb"] = self._backend.memory_used / 1024 / 1024
            stats["evictions"] = self._backend.eviction_count

        return stats

    async def close(self) -> None:
        """Close cache connections."""
        if self._backend_type == "redis" and self._backend:
            await self._backend.close()

        self._initialized = False
        logger.info("Cache manager closed")
