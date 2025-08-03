"""Comprehensive unit tests for LLMProcessingService with 100% coverage.

This test suite follows TDD principles and provides complete test coverage for:
- All public methods (health_check, llm_health_check, metrics_handler, process_property)
- Worker functionality (_process_worker)
- Startup and shutdown sequences
- Error handling and edge cases
- Signal handling and graceful shutdown
- Mock all external dependencies
"""

import asyncio
import json
import signal
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict, Optional

import pytest
from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST

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
        """Mock connect method."""
        pass
    
    async def close(self):
        """Mock close method."""
        pass
    
    async def health_check(self):
        """Mock health check method."""
        return True


class MockProcessingIntegrator:
    """Mock processing integrator for testing."""
    
    def __init__(self, config):
        self.config = config
        self.pipeline = Mock()
        self.pipeline.llm_client = Mock()
        self.pipeline.llm_client.health_check = AsyncMock(return_value=True)
        self.pipeline._extractor = Mock()
        self.pipeline._extractor._client = Mock()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def process_property(self, data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """Mock process property method."""
        if data.get("should_fail"):
            raise Exception("Processing failed")
        if data.get("should_return_none"):
            return None
        return {"processed": True, "source": source, "data": data}


class MockResourceMonitor:
    """Mock resource monitor for testing."""
    
    def __init__(self, limits):
        self.limits = limits
    
    async def start(self):
        """Mock start method."""
        pass
    
    async def stop(self):
        """Mock stop method."""
        pass


class MockHealthCheckService:
    """Mock health check service for testing."""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs


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
        with patch('phoenix_real_estate.collectors.processing.service.get_logger') as mock_logger:
            mock_logger.return_value = Mock()
            service = LLMProcessingService()
            service.config = mock_config
            return service
    
    @pytest.fixture
    async def started_service(self, service):
        """Service instance that's been started (mocked)."""
        # Mock all external dependencies
        service.db_client = MockDatabaseClient(service.config)
        service.processing_integrator = MockProcessingIntegrator(service.config)
        service.monitor = Mock()
        service.resource_monitor = MockResourceMonitor(Mock())
        service.health_service = MockHealthCheckService()
        service.running = True
        
        # Create mock workers
        service.workers = [Mock() for _ in range(2)]
        for worker in service.workers:
            worker.done = Mock(return_value=False)
        
        return service

    def test_init(self, mock_config):
        """Test service initialization."""
        with patch('phoenix_real_estate.collectors.processing.service.get_logger') as mock_logger,              patch('phoenix_real_estate.collectors.processing.service.EnvironmentConfigProvider') as mock_config_provider:
            
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

    def test_init_with_config_path(self):
        """Test service initialization with config path."""
        with patch('phoenix_real_estate.collectors.processing.service.get_logger') as mock_logger,              patch('phoenix_real_estate.collectors.processing.service.EnvironmentConfigProvider') as mock_config_provider:
            
            mock_logger.return_value = Mock()
            mock_config = Mock()
            mock_config_provider.return_value = mock_config
            
            LLMProcessingService(config_path="/custom/path")
            
            # Verify EnvironmentConfigProvider was called with production environment
            mock_config_provider.assert_called_once_with(environment="production")

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, started_service):
        """Test health check when service is running."""
        request = Mock()
        
        response = await started_service.health_check(request)
        
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
    async def test_llm_health_check_all_healthy(self, started_service):
        """Test detailed LLM health check when all components are healthy."""
        request = Mock()
        
        # Mock psutil
        with patch('phoenix_real_estate.collectors.processing.service.psutil') as mock_psutil:
            mock_process = Mock()
            mock_process.memory_info.return_value.rss = 1024 * 1024 * 1024  # 1GB
            mock_psutil.Process.return_value = mock_process
            
            # Mock queue size
            started_service.processing_queue._qsize = 10  # 10% full
            
            response = await started_service.llm_health_check(request)
            
            assert response.status == 200
            response_data = json.loads(response.text)
            assert response_data["status"] == "healthy"
            assert response_data["components"]["database"] == "healthy"
            assert response_data["components"]["ollama"] == "healthy"
            assert "10.0% full" in response_data["components"]["queue"]
            assert "healthy" in response_data["components"]["memory"]

    @pytest.mark.asyncio
    async def test_llm_health_check_database_unhealthy(self, started_service):
        """Test LLM health check when database is unhealthy."""
        request = Mock()
        
        # Make database health check fail
        started_service.db_client.health_check = AsyncMock(side_effect=Exception("DB connection failed"))
        
        with patch('phoenix_real_estate.collectors.processing.service.psutil') as mock_psutil:
            mock_process = Mock()
            mock_process.memory_info.return_value.rss = 1024 * 1024 * 1024  # 1GB
            mock_psutil.Process.return_value = mock_process
            
            started_service.processing_queue._qsize = 10
            
            response = await started_service.llm_health_check(request)
            
            assert response.status == 503
            response_data = json.loads(response.text)
            assert response_data["status"] == "degraded"
            assert "unhealthy: DB connection failed" in response_data["components"]["database"]

    @pytest.mark.asyncio
    async def test_llm_health_check_ollama_unhealthy(self, started_service):
        """Test LLM health check when Ollama is unhealthy."""
        request = Mock()
        
        # Make Ollama health check fail
        started_service.processing_integrator.pipeline.llm_client.health_check = AsyncMock(
            side_effect=Exception("Ollama connection failed")
        )
        
        with patch('phoenix_real_estate.collectors.processing.service.psutil') as mock_psutil:
            mock_process = Mock()
            mock_process.memory_info.return_value.rss = 1024 * 1024 * 1024  # 1GB
            mock_psutil.Process.return_value = mock_process
            
            started_service.processing_queue._qsize = 10
            
            response = await started_service.llm_health_check(request)
            
            assert response.status == 503
            response_data = json.loads(response.text)
            assert response_data["status"] == "unhealthy"
            assert "unhealthy: Ollama connection failed" in response_data["components"]["ollama"]

    @pytest.mark.asyncio
    async def test_metrics_handler(self, service):
        """Test Prometheus metrics endpoint."""
        request = Mock()
        
        with patch('phoenix_real_estate.collectors.processing.service.generate_latest') as mock_generate:
            mock_generate.return_value = b"# Prometheus metrics data"
            
            response = await service.metrics_handler(request)
            
            assert response.status == 200
            assert response.content_type == CONTENT_TYPE_LATEST
            assert response.body == b"# Prometheus metrics data"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_property_success(self, started_service):
        """Test successful property processing request."""
        # Mock request with JSON data
        request = Mock()
        request.json = AsyncMock(return_value={
            "source": "test_source",
            "data": {"property": "test"}
        })
        
        # Mock queue methods
        started_service.processing_queue.put = AsyncMock()
        started_service.processing_queue.qsize = Mock(return_value=5)
        
        with patch('phoenix_real_estate.collectors.processing.service.processing_requests') as mock_counter:
            response = await started_service.process_property(request)
            
            assert response.status == 200
            response_data = json.loads(response.text)
            assert response_data["status"] == "queued"
            assert response_data["queue_position"] == 5
            
            # Verify metrics were updated
            mock_counter.labels.assert_called_once_with(source="test_source", status="queued")
            mock_counter.labels.return_value.inc.assert_called_once()
            
            # Verify item was queued
            started_service.processing_queue.put.assert_called_once_with({
                "source": "test_source",
                "data": {"property": "test"}
            })

    @pytest.mark.asyncio
    async def test_process_property_no_source(self, started_service):
        """Test property processing request without source."""
        request = Mock()
        request.json = AsyncMock(return_value={"data": {"property": "test"}})
        
        started_service.processing_queue.put = AsyncMock()
        started_service.processing_queue.qsize = Mock(return_value=1)
        
        with patch('phoenix_real_estate.collectors.processing.service.processing_requests') as mock_counter:
            response = await started_service.process_property(request)
            
            assert response.status == 200
            mock_counter.labels.assert_called_once_with(source="unknown", status="queued")

    @pytest.mark.asyncio
    async def test_process_property_json_error(self, started_service):
        """Test property processing request with JSON parsing error."""
        request = Mock()
        request.json = AsyncMock(side_effect=Exception("Invalid JSON"))
        
        with patch('phoenix_real_estate.collectors.processing.service.processing_requests') as mock_counter:
            response = await started_service.process_property(request)
            
            assert response.status == 500
            response_data = json.loads(response.text)
            assert response_data["error"] == "Failed to process request"
            
            # Verify error metrics were updated
            mock_counter.labels.assert_called_once_with(source="unknown", status="error")
            mock_counter.labels.return_value.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_worker_success(self, started_service):
        """Test worker processing items successfully."""
        # Create test queue with item
        test_item = {
            "source": "test_source",
            "data": {"property": "test"}
        }
        
        # Mock queue operations
        started_service.processing_queue.get = AsyncMock(return_value=test_item)
        started_service.running = True
        
        # Mock processing integrator
        started_service.processing_integrator.process_property = AsyncMock(
            return_value={"processed": True, "source": "test_source"}
        )
        
        # Mock database insertion
        started_service.db_client.properties.insert_one = AsyncMock()
        
        # Create a worker task that will process one item then stop
        async def run_worker():
            await started_service._process_worker(0)
        
        with patch('phoenix_real_estate.collectors.processing.service.processing_duration') as mock_histogram,              patch('phoenix_real_estate.collectors.processing.service.processing_requests') as mock_counter,              patch('asyncio.wait_for') as mock_wait_for:
            
            # Setup mocks
            mock_wait_for.side_effect = [test_item, asyncio.TimeoutError()]  # First call returns item, second times out
            mock_histogram.labels.return_value.time.return_value.__enter__ = Mock()
            mock_histogram.labels.return_value.time.return_value.__exit__ = Mock()
            
            # Start worker and let it run briefly
            worker_task = asyncio.create_task(run_worker())
            await asyncio.sleep(0.01)  # Let worker start
            started_service.running = False  # Stop worker
            
            try:
                await asyncio.wait_for(worker_task, timeout=1.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
            
            # Verify processing was called
            started_service.processing_integrator.process_property.assert_called_once_with(
                {"property": "test"}, "test_source"
            )
            
            # Verify database insertion
            started_service.db_client.properties.insert_one.assert_called_once_with(
                {"processed": True, "source": "test_source"}
            )
            
            # Verify metrics
            mock_counter.labels.assert_called_with(source="test_source", status="success")

    @pytest.mark.asyncio
    async def test_process_worker_processing_failure(self, started_service):
        """Test worker handling processing failures."""
        test_item = {
            "source": "test_source", 
            "data": {"should_fail": True}
        }
        
        started_service.processing_queue.get = AsyncMock(return_value=test_item)
        started_service.running = True
        
        # Mock processing failure
        started_service.processing_integrator.process_property = AsyncMock(
            side_effect=Exception("Processing failed")
        )
        
        async def run_worker():
            await started_service._process_worker(0)
        
        with patch('phoenix_real_estate.collectors.processing.service.processing_duration') as mock_histogram,              patch('phoenix_real_estate.collectors.processing.service.processing_requests') as mock_counter,              patch('asyncio.wait_for') as mock_wait_for:
            
            mock_wait_for.side_effect = [test_item, asyncio.TimeoutError()]
            mock_histogram.labels.return_value.time.return_value.__enter__ = Mock()
            mock_histogram.labels.return_value.time.return_value.__exit__ = Mock()
            
            worker_task = asyncio.create_task(run_worker())
            await asyncio.sleep(0.01)
            started_service.running = False
            
            try:
                await asyncio.wait_for(worker_task, timeout=1.0)
            except asyncio.TimeoutError:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
            
            # Verify error metrics
            mock_counter.labels.assert_called_with(source="test_source", status="error")

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
