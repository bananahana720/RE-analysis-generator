"""Test suite for LLM response caching functionality."""

import asyncio
import pytest
import time
from typing import Dict, Any
from unittest.mock import AsyncMock

from phoenix_real_estate.collectors.processing.cache import (
    CacheManager,
    LRUCache,
    CacheMetrics,
    CacheConfig
)


class TestCacheManager:
    """Test-driven development of caching layer."""
    
    @pytest.fixture
    def sample_property(self) -> Dict[str, Any]:
        """Sample property data for testing."""
        return {
            "address": "123 Main St, Phoenix, AZ 85001",
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 1500,
            "price": 350000,
            "listing_id": "PHX-2024-0001"
        }
    
    @pytest.fixture
    def cache_config(self) -> CacheConfig:
        """Cache configuration for testing."""
        return CacheConfig(
            enabled=True,
            ttl_hours=24,
            max_size_mb=100,
            eviction_policy="lru",
            backend="memory"  # Use in-memory for tests
        )
    
    @pytest.fixture
    async def cache_manager(self, cache_config) -> CacheManager:
        """Create cache manager instance."""
        manager = CacheManager(cache_config)
        await manager.initialize()
        return manager
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_manager, sample_property):
        """Test deterministic cache key generation."""
        # Same data should produce same key
        key1 = cache_manager._generate_cache_key(sample_property, "extraction")
        key2 = cache_manager._generate_cache_key(sample_property, "extraction")
        assert key1 == key2
        assert key1.startswith("llm:extraction:")
        
        # Different operations should produce different keys
        key3 = cache_manager._generate_cache_key(sample_property, "validation")
        assert key1 != key3
        
        # Key should be MD5 hash of deterministic data
        assert len(key1.split(":")[-1]) == 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache_manager, sample_property):
        """Test cache miss returns None."""
        result = await cache_manager.get(sample_property, "extraction")
        assert result is None
        
        # Metrics should reflect miss
        metrics = cache_manager.get_metrics()
        assert metrics["hits"] == 0
        assert metrics["misses"] == 1
        assert metrics["hit_rate"] == 0.0
    
    @pytest.mark.asyncio
    async def test_cache_hit_returns_data(self, cache_manager, sample_property):
        """Test cache hit returns stored data."""
        cached_data = {
            "description": "Beautiful 3BR/2BA home in Phoenix",
            "features": ["pool", "garage", "updated kitchen"],
            "tokens_used": 150,
            "processing_time": 1.23
        }
        
        # Store data
        await cache_manager.set(sample_property, "extraction", cached_data)
        
        # Retrieve data
        result = await cache_manager.get(sample_property, "extraction")
        assert result == cached_data
        
        # Metrics should reflect hit
        metrics = cache_manager.get_metrics()
        assert metrics["hits"] == 1
        assert metrics["misses"] == 0
        assert metrics["hit_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, sample_property):
        """Test cache entries expire after TTL."""
        # Create cache with short TTL
        config = CacheConfig(
            enabled=True,
            ttl_hours=0.0001,  # ~0.36 seconds
            backend="memory"
        )
        manager = CacheManager(config)
        await manager.initialize()
        
        # Store data
        cached_data = {"test": "data"}
        await manager.set(sample_property, "extraction", cached_data)
        
        # Should be available immediately
        result = await manager.get(sample_property, "extraction")
        assert result == cached_data
        
        # Wait for expiration
        await asyncio.sleep(0.5)
        
        # Should be expired
        result = await manager.get(sample_property, "extraction")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_size_limits(self, sample_property):
        """Test cache respects size limits."""
        # Create cache with small size limit
        config = CacheConfig(
            enabled=True,
            max_size_mb=0.001,  # 1KB
            backend="memory"
        )
        manager = CacheManager(config)
        await manager.initialize()
        
        # Try to store large data that exceeds memory limit
        large_data = {"data": "x" * 10000}  # ~10KB
        
        # Should handle gracefully (item won't be stored)
        await manager.set(sample_property, "extraction", large_data)
        
        # Verify item was not stored (too large)
        result = await manager.get(sample_property, "extraction")
        assert result is None
        
        # Verify cache is empty
        metrics = manager.get_metrics()
        assert metrics["entries"] == 0
        
        # Now store smaller data that should fit
        small_data = {"data": "x" * 100}  # ~100 bytes
        await manager.set(sample_property, "extraction", small_data)
        
        # Should be stored successfully
        result = await manager.get(sample_property, "extraction")
        assert result == small_data
        
        metrics = manager.get_metrics()
        assert metrics["entries"] == 1
    
    @pytest.mark.asyncio
    async def test_cache_warmup(self, cache_manager):
        """Test cache warmup functionality."""
        # Prepare warmup data
        properties = [
            {"address": f"{i} Main St", "price": i * 1000}
            for i in range(10)
        ]
        
        responses = [
            {"description": f"Property {i}", "tokens": 100}
            for i in range(10)
        ]
        
        # Warm up cache
        await cache_manager.warmup(properties, responses, "extraction")
        
        # Verify all entries cached
        for prop, expected in zip(properties, responses):
            result = await cache_manager.get(prop, "extraction")
            assert result == expected
        
        metrics = cache_manager.get_metrics()
        assert metrics["entries"] == 10
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_manager, sample_property):
        """Test cache invalidation."""
        # Store data
        cached_data = {"test": "data"}
        await cache_manager.set(sample_property, "extraction", cached_data)
        
        # Verify it's there
        result = await cache_manager.get(sample_property, "extraction")
        assert result == cached_data
        
        # Invalidate specific entry
        await cache_manager.invalidate(sample_property, "extraction")
        
        # Should be gone
        result = await cache_manager.get(sample_property, "extraction")
        assert result is None
        
        # Test pattern invalidation
        await cache_manager.set(sample_property, "extraction", cached_data)
        await cache_manager.set(sample_property, "validation", cached_data)
        
        # Invalidate all for property
        await cache_manager.invalidate_pattern(sample_property)
        
        # Both should be gone
        assert await cache_manager.get(sample_property, "extraction") is None
        assert await cache_manager.get(sample_property, "validation") is None
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache_manager, sample_property):
        """Test thread-safe concurrent access."""
        import asyncio
        
        async def writer(i: int):
            data = {"value": i}
            await cache_manager.set(sample_property, f"op{i}", data)
        
        async def reader(i: int):
            return await cache_manager.get(sample_property, f"op{i}")
        
        # Concurrent writes
        await asyncio.gather(*[writer(i) for i in range(100)])
        
        # Concurrent reads
        results = await asyncio.gather(*[reader(i) for i in range(100)])
        
        # Verify all data intact
        for i, result in enumerate(results):
            assert result == {"value": i}
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, sample_property):
        """Test cache handles backend failures gracefully."""
        config = CacheConfig(enabled=True, backend="redis")
        manager = CacheManager(config)
        
        # Initialize without mocking to trigger fallback
        await manager.initialize()
        
        # Should fallback to memory when Redis unavailable
        assert manager._backend_type == "memory"
        
        # Should still work with in-memory cache
        data = {"test": "data"}
        await manager.set(sample_property, "extraction", data)
        result = await manager.get(sample_property, "extraction")
        assert result == data


class TestLRUCache:
    """Test LRU cache implementation."""
    
    def test_lru_eviction(self):
        """Test least recently used eviction."""
        cache = LRUCache(max_size=3)
        
        # Fill cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # Access key1 to make it recently used
        assert cache.get("key1") == "value1"
        
        # Add new item, should evict key2 (least recently used)
        cache.put("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Still there
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"  # Still there
        assert cache.get("key4") == "value4"  # New item
    
    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LRUCache(max_size=10, ttl_seconds=0.1)
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("key1") is None
    
    def test_size_tracking(self):
        """Test memory size tracking."""
        cache = LRUCache(max_size=10, max_memory_mb=0.001)  # 1KB
        
        # Add large value that exceeds memory limit
        large_value = "x" * 10000  # ~10KB
        cache.put("key1", large_value)
        
        # Large item should not be stored (exceeds memory limit)
        assert cache.size() == 0
        assert cache.memory_used == 0
        
        # Add smaller values that fit
        small_value = "x" * 100  # ~100 bytes
        cache.put("key2", small_value)
        assert cache.size() == 1
        assert cache.memory_used > 0


class TestCacheMetrics:
    """Test cache metrics collection."""
    
    def test_metrics_calculation(self):
        """Test metrics calculations."""
        metrics = CacheMetrics()
        
        # Record some operations
        metrics.record_hit()
        metrics.record_hit()
        metrics.record_miss()
        metrics.record_set(size_bytes=1000)
        metrics.record_eviction()
        
        stats = metrics.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(0.667, rel=0.01)
        assert stats["sets"] == 1
        assert stats["evictions"] == 1
        assert stats["bytes_stored"] == 1000
    
    def test_metrics_reset(self):
        """Test metrics reset."""
        metrics = CacheMetrics()
        
        metrics.record_hit()
        metrics.record_miss()
        
        metrics.reset()
        stats = metrics.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0


class TestCacheIntegration:
    """Integration tests with LLM pipeline."""
    
    @pytest.mark.asyncio
    async def test_llm_client_with_cache(self):
        """Test LLM client integration with caching."""
        from phoenix_real_estate.collectors.processing import OllamaClient
        from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
        
        config = EnvironmentConfigProvider()
        
        # Create cache manager
        cache_config = CacheConfig(enabled=True, backend="memory")
        cache_manager = CacheManager(cache_config)
        await cache_manager.initialize()
        
        # Create client with cache
        client = OllamaClient(config)
        client._cache_manager = cache_manager
        
        # Mock the actual LLM call
        mock_response = "Test response"
        client._generate_completion_impl = AsyncMock(return_value=mock_response)
        
        # First call should hit LLM
        result1 = await client.generate_completion("Test prompt", cache_key="test1")
        assert result1 == mock_response
        assert client._generate_completion_impl.call_count == 1
        
        # Verify cache has the entry
        cache_metrics = cache_manager.get_metrics()
        assert cache_metrics["entries"] == 1
        
        # Second call with same key should hit cache
        result2 = await client.generate_completion("Test prompt", cache_key="test1")
        assert result2 == mock_response
        assert client._generate_completion_impl.call_count == 1  # No additional call
        
        # Third call with different cache key should hit LLM again
        # NOTE: We need to understand that the cache uses the entire data structure for key generation
        # The prompt content matters as well as the cache_key
        result3 = await client.generate_completion("Test prompt", cache_key="test2")
        assert result3 == mock_response
        assert client._generate_completion_impl.call_count == 2
        
        # Should now have 2 entries in cache
        cache_metrics = cache_manager.get_metrics()  
        assert cache_metrics["entries"] == 2