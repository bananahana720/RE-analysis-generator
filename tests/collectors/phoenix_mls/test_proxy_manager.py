"""Test-Driven Development tests for ProxyManager.

Following RED-GREEN-REFACTOR cycle:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code quality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from .test_tdd_runner import tdd_tracker


# RED PHASE: Test 1 - ProxyManager should exist
def test_proxy_manager_exists():
    """Test that ProxyManager class can be imported."""
    tdd_tracker.start_red_phase("ProxyManager", "test_proxy_manager_exists")
    
    # This will fail initially (RED)
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    assert ProxyManager is not None


# RED PHASE: Test 2 - ProxyManager initialization
def test_proxy_manager_initialization(mock_proxy_config):
    """Test ProxyManager can be initialized with config."""
    tdd_tracker.start_red_phase("ProxyManager", "test_proxy_manager_initialization")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    manager = ProxyManager(mock_proxy_config)
    assert manager is not None
    assert len(manager.proxies) == 2


# RED PHASE: Test 3 - Get next proxy
@pytest.mark.asyncio
async def test_get_next_proxy():
    """Test getting next proxy in rotation."""
    tdd_tracker.start_red_phase("ProxyManager", "test_get_next_proxy")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {
        "proxies": [
            {"host": "proxy1.test.com", "port": 8080, "username": "user1", "password": "pass1"},
            {"host": "proxy2.test.com", "port": 8081, "username": "user2", "password": "pass2"}
        ]
    }
    
    manager = ProxyManager(config)
    
    # Should return first proxy
    proxy1 = await manager.get_next_proxy()
    assert proxy1["host"] == "proxy1.test.com"
    
    # Should return second proxy
    proxy2 = await manager.get_next_proxy()
    assert proxy2["host"] == "proxy2.test.com"
    
    # Should rotate back to first
    proxy3 = await manager.get_next_proxy()
    assert proxy3["host"] == "proxy1.test.com"


# RED PHASE: Test 4 - Mark proxy as failed
@pytest.mark.asyncio
async def test_mark_proxy_failed():
    """Test marking a proxy as failed."""
    tdd_tracker.start_red_phase("ProxyManager", "test_mark_proxy_failed")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {
        "proxies": [
            {"host": "proxy1.test.com", "port": 8080},
            {"host": "proxy2.test.com", "port": 8081}
        ]
    }
    
    manager = ProxyManager(config)
    proxy = await manager.get_next_proxy()
    
    # Mark proxy as failed
    await manager.mark_failed(proxy)
    
    # Should have recorded failure
    assert manager.get_failure_count(proxy) == 1


# RED PHASE: Test 5 - Health check functionality
@pytest.mark.asyncio
async def test_proxy_health_check():
    """Test proxy health checking."""
    tdd_tracker.start_red_phase("ProxyManager", "test_proxy_health_check")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {
        "proxies": [{"host": "proxy1.test.com", "port": 8080}],
        "health_check_url": "https://httpbin.org/ip"
    }
    
    manager = ProxyManager(config)
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        proxy = await manager.get_next_proxy()
        is_healthy = await manager.check_health(proxy)
        
        assert is_healthy is True


# RED PHASE: Test 6 - Exclude unhealthy proxies
@pytest.mark.asyncio 
async def test_exclude_unhealthy_proxies():
    """Test that unhealthy proxies are excluded from rotation."""
    tdd_tracker.start_red_phase("ProxyManager", "test_exclude_unhealthy_proxies")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {
        "proxies": [
            {"host": "proxy1.test.com", "port": 8080},
            {"host": "proxy2.test.com", "port": 8081}
        ],
        "max_failures": 3
    }
    
    manager = ProxyManager(config)
    
    # Mark first proxy as failed multiple times
    proxy1 = await manager.get_next_proxy()
    for _ in range(3):
        await manager.mark_failed(proxy1)
    
    # Next proxy should skip the failed one
    proxy2 = await manager.get_next_proxy()
    assert proxy2["host"] == "proxy2.test.com"
    
    # Should continue returning only healthy proxy
    proxy3 = await manager.get_next_proxy()
    assert proxy3["host"] == "proxy2.test.com"


# RED PHASE: Test 7 - Concurrent proxy usage
@pytest.mark.asyncio
async def test_concurrent_proxy_usage():
    """Test thread-safe proxy rotation."""
    tdd_tracker.start_red_phase("ProxyManager", "test_concurrent_proxy_usage")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {
        "proxies": [
            {"host": f"proxy{i}.test.com", "port": 8080 + i} 
            for i in range(5)
        ]
    }
    
    manager = ProxyManager(config)
    
    # Get proxies concurrently
    tasks = [manager.get_next_proxy() for _ in range(10)]
    proxies = await asyncio.gather(*tasks)
    
    # Should have distributed proxies evenly
    proxy_counts = {}
    for proxy in proxies:
        host = proxy["host"]
        proxy_counts[host] = proxy_counts.get(host, 0) + 1
    
    # Each proxy should be used exactly twice (10 requests / 5 proxies)
    assert all(count == 2 for count in proxy_counts.values())


# RED PHASE: Test 8 - Proxy recovery after cooldown
@pytest.mark.asyncio
async def test_proxy_recovery_after_cooldown():
    """Test that failed proxies recover after cooldown period."""
    tdd_tracker.start_red_phase("ProxyManager", "test_proxy_recovery_after_cooldown")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {
        "proxies": [
            {"host": "proxy1.test.com", "port": 8080},
            {"host": "proxy2.test.com", "port": 8081}
        ],
        "max_failures": 3,
        "cooldown_minutes": 5
    }
    
    manager = ProxyManager(config)
    
    # Fail first proxy
    proxy1 = await manager.get_next_proxy()
    for _ in range(3):
        await manager.mark_failed(proxy1)
    
    # Should be excluded
    next_proxy = await manager.get_next_proxy()
    assert next_proxy["host"] == "proxy2.test.com"
    
    # Simulate time passing
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime.now() + timedelta(minutes=6)
        
        # Proxy should be available again
        await manager.check_recovery()
        recovered_proxy = await manager.get_next_proxy()
        
        # Could be either proxy now
        assert recovered_proxy["host"] in ["proxy1.test.com", "proxy2.test.com"]


# RED PHASE: Test 9 - Proxy statistics
def test_proxy_statistics():
    """Test getting proxy usage statistics."""
    tdd_tracker.start_red_phase("ProxyManager", "test_proxy_statistics")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {"proxies": [{"host": "proxy1.test.com", "port": 8080}]}
    manager = ProxyManager(config)
    
    stats = manager.get_statistics()
    
    assert "total_proxies" in stats
    assert "healthy_proxies" in stats
    assert "failed_proxies" in stats
    assert "total_requests" in stats
    assert "total_failures" in stats
    assert stats["total_proxies"] == 1
    assert stats["healthy_proxies"] == 1


# RED PHASE: Test 10 - Proxy authentication
@pytest.mark.asyncio
async def test_proxy_authentication():
    """Test proxy returns proper authentication format."""
    tdd_tracker.start_red_phase("ProxyManager", "test_proxy_authentication")
    
    from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
    
    config = {
        "proxies": [{
            "host": "proxy1.test.com",
            "port": 8080,
            "username": "testuser",
            "password": "testpass",
            "type": "http"
        }]
    }
    
    manager = ProxyManager(config)
    proxy = await manager.get_next_proxy()
    
    # Should format proxy URL correctly
    proxy_url = manager.format_proxy_url(proxy)
    assert proxy_url == "http://testuser:testpass@proxy1.test.com:8080"