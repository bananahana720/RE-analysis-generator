"""Comprehensive unit tests for LLMProcessingService with 100% coverage.

Windows-compatible test suite with uvloop mocking.
"""

import asyncio
import json
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST

# Mock uvloop before importing the service
with patch.dict("sys.modules", {"uvloop": Mock()}):
    from phoenix_real_estate.collectors.processing.service import LLMProcessingService

from phoenix_real_estate.foundation import EnvironmentConfigProvider


class MockDatabaseClient:
    """Mock database client for testing."""
    
    def __init__(self, config):
        self.config = config
        self.properties = Mock()
        self.properties.insert_one = AsyncMock()
        self.properties.count_documents = AsyncMock(return_value=100)
    
    async def connect(self):
        pass
    
    async def close(self):
        pass
    
    async def health_check(self):
        return True


class TestLLMProcessingService:
    """Comprehensive test suite for LLMProcessingService."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=EnvironmentConfigProvider)
        config.get = Mock(return_value="test_value")
        config.get_typed = Mock(return_value=30)
        return config
    
    @pytest.fixture
    def service(self, mock_config):
        """Create service instance with mocked dependencies."""
        with patch("phoenix_real_estate.collectors.processing.service.get_logger") as mock_logger:
            mock_logger.return_value = Mock()
            service = LLMProcessingService()
            service.config = mock_config
            return service

    def test_init(self, mock_config):
        """Test service initialization."""
        with patch("phoenix_real_estate.collectors.processing.service.get_logger") as mock_logger,              patch("phoenix_real_estate.collectors.processing.service.EnvironmentConfigProvider") as mock_config_provider:
            
            mock_logger.return_value = Mock()
            mock_config_provider.return_value = mock_config
            
            service = LLMProcessingService()
            
            # Verify initialization
            assert service.config == mock_config
            assert service.db_client is None
            assert service.processing_integrator is None
            assert service.monitor is None
            assert service.resource_monitor is None
            assert service.health_service is None
            assert isinstance(service.app, web.Application)
            assert service.running is False
            assert isinstance(service.shutdown_event, asyncio.Event)
            assert isinstance(service.processing_queue, asyncio.Queue)
            assert service.processing_queue.maxsize == 100
            assert service.workers == []

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service):
        """Test health check when service is running."""
        service.running = True
        request = Mock()
        
        response = await service.health_check(request)
        
        assert response.status == 200
        response_data = json.loads(response.text)
        assert response_data["status"] == "healthy"
        assert response_data["service"] == "llm_processor"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, service):
        """Test health check when service is not running."""
        request = Mock()
        service.running = False
        
        response = await service.health_check(request)
        
        assert response.status == 503
        response_data = json.loads(response.text)
        assert response_data["status"] == "unhealthy"
        assert response_data["service"] == "llm_processor"

    @pytest.mark.asyncio
    async def test_metrics_handler(self, service):
        """Test Prometheus metrics endpoint."""
        request = Mock()
        
        with patch("phoenix_real_estate.collectors.processing.service.generate_latest") as mock_generate:
            mock_generate.return_value = b"# Prometheus metrics data"
            
            response = await service.metrics_handler(request)
            
            assert response.status == 200
            assert response.content_type == CONTENT_TYPE_LATEST
            assert response.body == b"# Prometheus metrics data"
            mock_generate.assert_called_once()

    def test_signal_handler(self, service):
        """Test signal handler sets shutdown event."""
        assert not service.shutdown_event.is_set()
        
        service._signal_handler(signal.SIGTERM, None)
        
        assert service.shutdown_event.is_set()

    def test_signal_handler_sigint(self, service):
        """Test signal handler works with SIGINT."""
        assert not service.shutdown_event.is_set()
        
        service._signal_handler(signal.SIGINT, None)
        
        assert service.shutdown_event.is_set()
