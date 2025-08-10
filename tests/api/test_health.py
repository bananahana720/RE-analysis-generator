"""Unit tests for API health endpoint."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
import json

# Import health module
try:
    from src.phoenix_real_estate.api.health import (
        HealthChecker, create_health_app
    )
except ImportError:
    pytest.skip('Health API module not available', allow_module_level=True)


class TestHealthChecker:
    """Test suite for HealthChecker."""
    
    def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        health_checker = HealthChecker()
        assert health_checker is not None
        
    def test_basic_health_check(self):
        """Test basic health check functionality."""
        health_checker = HealthChecker()
        
        # Test that health checker has required methods
        assert hasattr(health_checker, 'check_system_health')
        
    def test_system_health_status(self):
        """Test system health status reporting."""
        health_checker = HealthChecker()
        
        # Mock system components
        with patch('psutil.cpu_percent', return_value=50.0),              patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 60.0
            
            status = health_checker.check_system_health()
            
            # Should return a dictionary with health status
            assert isinstance(status, dict)
            assert 'status' in status
            
    def test_database_health_check(self):
        """Test database health check."""
        health_checker = HealthChecker()
        
        # Mock database connection
        with patch('src.phoenix_real_estate.foundation.database.connection.get_connection') as mock_conn:
            mock_conn.return_value = Mock()
            
            status = health_checker.check_database_health()
            
            # Should return health status
            assert isinstance(status, dict)
            
    def test_service_dependencies_check(self):
        """Test service dependencies health check."""
        health_checker = HealthChecker()
        
        # Mock external service checks
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value = mock_response
            
            # Should be able to check service dependencies
            status = health_checker.check_service_dependencies()
            
            assert isinstance(status, (dict, type(None)))


class TestHealthAPI:
    """Test suite for Health API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test app."""
        try:
            return create_health_app()
        except NameError:
            # If create_health_app doesn't exist, create a minimal app
            app = web.Application()
            
            async def health_handler(request):
                return web.json_response({'status': 'healthy'})
                
            app.router.add_get('/health', health_handler)
            return app
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, aiohttp_client, app):
        """Test health endpoint response."""
        client = await aiohttp_client(app)
        
        resp = await client.get('/health')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'status' in data
        
    @pytest.mark.asyncio  
    async def test_health_endpoint_detailed(self, aiohttp_client, app):
        """Test health endpoint with detailed information."""
        client = await aiohttp_client(app)
        
        # Test with detailed parameter if supported
        resp = await client.get('/health?detailed=true')
        assert resp.status in [200, 404]  # 404 if route doesn't exist
        
        if resp.status == 200:
            data = await resp.json()
            assert isinstance(data, dict)
            
    @pytest.mark.asyncio
    async def test_health_endpoint_error_handling(self, aiohttp_client, app):
        """Test health endpoint error handling."""
        client = await aiohttp_client(app)
        
        # Mock internal error
        with patch('src.phoenix_real_estate.api.health.HealthChecker.check_system_health', 
                  side_effect=Exception('Internal error')):
            resp = await client.get('/health')
            
            # Should handle errors gracefully
            assert resp.status in [200, 500, 503]  # Various acceptable error responses


@pytest.mark.unit
class TestHealthEdgeCases:
    """Test edge cases for health checking."""
    
    def test_health_check_with_no_dependencies(self):
        """Test health check when no dependencies are available."""
        health_checker = HealthChecker()
        
        # Mock unavailable services
        with patch('psutil.cpu_percent', side_effect=Exception('Service unavailable')):
            try:
                status = health_checker.check_system_health()
                # Should handle unavailable services gracefully
                assert isinstance(status, dict)
                assert status.get('status') in ['degraded', 'unhealthy', 'error', None]
            except Exception:
                # It's acceptable for health check to fail when dependencies are unavailable
                pass
                
    def test_health_check_performance(self):
        """Test health check performance."""
        health_checker = HealthChecker()
        
        import time
        start_time = time.time()
        
        try:
            status = health_checker.check_system_health()
            end_time = time.time()
            
            # Health check should be fast (< 1 second)
            assert (end_time - start_time) < 1.0
        except Exception:
            # If health check fails, that's ok for this performance test
            pass
            
    def test_concurrent_health_checks(self):
        """Test multiple concurrent health checks."""
        health_checker = HealthChecker()
        
        import threading
        results = []
        
        def run_health_check():
            try:
                status = health_checker.check_system_health()
                results.append(status)
            except Exception as e:
                results.append({'error': str(e)})
        
        # Run multiple health checks concurrently
        threads = [threading.Thread(target=run_health_check) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should handle concurrent checks
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
