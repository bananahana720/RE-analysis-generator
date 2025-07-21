"""Additional tests for ProxyManager edge cases and error handling."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import (
    ProxyManager, NoHealthyProxiesError
)


def test_proxy_manager_no_proxies_error():
    """Test ProxyManager raises error when no proxies configured."""
    config = {"proxies": []}
    
    with pytest.raises(ValueError, match="No proxies configured"):
        ProxyManager(config)


@pytest.mark.asyncio
async def test_all_proxies_failed_error():
    """Test error when all proxies are failed."""
    config = {
        "proxies": [{"host": "proxy1.test.com", "port": 8080}],
        "max_failures": 1
    }
    
    manager = ProxyManager(config)
    proxy = await manager.get_next_proxy()
    
    # Mark proxy as failed beyond threshold
    await manager.mark_failed(proxy)
    
    # Should raise NoHealthyProxiesError
    with pytest.raises(NoHealthyProxiesError):
        await manager.get_next_proxy()


@pytest.mark.asyncio
async def test_mark_success():
    """Test marking proxy as successful."""
    config = {"proxies": [{"host": "proxy1.test.com", "port": 8080}]}
    manager = ProxyManager(config)
    
    proxy = await manager.get_next_proxy()
    await manager.mark_success(proxy)
    
    stats = manager.get_statistics()
    assert stats["total_successes"] == 1
    assert stats["proxy_details"]["proxy1.test.com:8080"]["successes"] == 1


@pytest.mark.asyncio
async def test_check_all_health():
    """Test checking health of all proxies."""
    config = {
        "proxies": [
            {"host": "proxy1.test.com", "port": 8080},
            {"host": "proxy2.test.com", "port": 8081}
        ]
    }
    
    manager = ProxyManager(config)
    
    with patch('httpx.AsyncClient') as mock_client:
        # First proxy healthy, second unhealthy
        mock_responses = [
            Mock(status_code=200),
            Mock(status_code=500)
        ]
        
        async def mock_get(*args, **kwargs):
            return mock_responses.pop(0)
        
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        health_status = await manager.check_all_health()
        
        assert health_status["proxy1.test.com:8080"] is True
        assert health_status["proxy2.test.com:8081"] is False


def test_proxy_manager_repr():
    """Test string representation of ProxyManager."""
    config = {
        "proxies": [
            {"host": "proxy1.test.com", "port": 8080},
            {"host": "proxy2.test.com", "port": 8081}
        ]
    }
    
    manager = ProxyManager(config)
    repr_str = repr(manager)
    
    assert "ProxyManager" in repr_str
    assert "total=2" in repr_str
    assert "healthy=2" in repr_str
    assert "failed=0" in repr_str


@pytest.mark.asyncio
async def test_proxy_health_check_exception():
    """Test proxy health check with network exception."""
    config = {"proxies": [{"host": "proxy1.test.com", "port": 8080}]}
    manager = ProxyManager(config)
    
    proxy = await manager.get_next_proxy()
    
    with patch('httpx.AsyncClient') as mock_client:
        # Simulate network error
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")
        
        is_healthy = await manager.check_health(proxy)
        assert is_healthy is False


@pytest.mark.asyncio
async def test_proxy_recovery_reset():
    """Test that proxy health is properly reset after recovery."""
    config = {
        "proxies": [{"host": "proxy1.test.com", "port": 8080}],
        "max_failures": 2,
        "cooldown_minutes": 1
    }
    
    manager = ProxyManager(config)
    proxy = await manager.get_next_proxy()
    
    # Fail the proxy twice
    await manager.mark_failed(proxy)
    await manager.mark_failed(proxy)
    
    # Should be unhealthy
    assert manager._is_proxy_available(proxy) is False
    
    # Simulate time passing
    proxy_key = manager._get_proxy_key(proxy)
    manager.last_failure_time[proxy_key] = datetime.now() - timedelta(minutes=2)
    
    # Check recovery
    await manager.check_recovery()
    
    # Should be healthy again
    assert manager._is_proxy_available(proxy) is True
    assert manager.get_failure_count(proxy) == 0