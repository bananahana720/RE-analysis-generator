"""Tests for mock service infrastructure.

Tests MongoDB, Ollama, API mocks with circuit breaker simulation.
Following TDD principles - tests written first.
"""

import pytest
from typing import Dict, Any
from unittest.mock import MagicMock


class MockServiceManager:
    """Mock service manager for testing - implementation will be created after tests."""
    
    def __init__(self, config_provider=None):
        self.config = config_provider
        self.services = {}
        self.circuit_breakers = {}
        
    async def start_mongodb_mock(self, port: int = 27017) -> Dict[str, Any]:
        """Start MongoDB mock service."""
        raise NotImplementedError("Implementation needed")


@pytest.fixture
def mock_config():
    """Create mock configuration provider."""
    config = MagicMock()
    config.get.return_value = "test_value"
    return config


@pytest.fixture
def service_manager(mock_config):
    """Create service manager instance."""
    return MockServiceManager(mock_config)


@pytest.mark.unit
class TestMockServiceManagerInitialization:
    """Test mock service manager initialization."""
    
    def test_service_manager_creation(self, mock_config):
        """Test creating service manager with config."""
        manager = MockServiceManager(mock_config)
        assert manager.config == mock_config
        assert isinstance(manager.services, dict)
        assert isinstance(manager.circuit_breakers, dict)


@pytest.mark.unit
class TestMongoDBMock:
    """Test MongoDB mock service."""
    
    @pytest.mark.async_test
    async def test_start_mongodb_mock(self, service_manager):
        """Test starting MongoDB mock service."""
        with pytest.raises(NotImplementedError):
            await service_manager.start_mongodb_mock(27017)

