"""Mock service infrastructure for workflow testing.

Provides MongoDB, Ollama, and API mocks with circuit breaker simulation.
"""

import random
from typing import Dict, Any, List, Optional

from phoenix_real_estate.foundation import ConfigProvider, get_logger
from phoenix_real_estate.foundation.utils.exceptions import DatabaseError, PhoenixREError


class MockServiceManager:
    """Manages mock services for workflow testing."""

    def __init__(self, config_provider: Optional[ConfigProvider] = None):
        """Initialize mock service manager."""
        self.config = config_provider or ConfigProvider()
        self.logger = get_logger(__name__)
        self.services = {}
        self.circuit_breakers = {}

    async def start_mongodb_mock(self, port: int = 27017) -> Dict[str, Any]:
        """Start MongoDB mock service."""
        mock_service = MockMongoDBService()
        await mock_service.start()

        self.services["mongodb"] = mock_service

        self.logger.info(f"Started MongoDB mock on port {port}")
        return {
            "service": "mongodb",
            "status": "running",
            "port": port,
            "collections": list(mock_service.collections.keys()),
        }

    async def start_ollama_mock(self, port: int = 11434) -> Dict[str, Any]:
        """Start Ollama LLM mock service."""
        mock_service = MockOllamaService()
        await mock_service.start()

        self.services["ollama"] = mock_service

        self.logger.info(f"Started Ollama mock on port {port}")
        return {"service": "ollama", "status": "running", "port": port, "model": "llama3.2:latest"}

    async def start_api_mocks(self, apis: List[str]) -> Dict[str, Any]:
        """Start API mock services."""
        started_apis = {}

        for api in apis:
            if api == "maricopa_api":
                mock_api = MockMaricopaAPI()
            elif api == "webshare_proxy":
                mock_api = MockWebShareProxy()
            elif api == "captcha_api":
                mock_api = MockCaptchaAPI()
            else:
                continue

            await mock_api.start()
            self.services[api] = mock_api
            started_apis[api] = {"status": "running", "endpoint": f"http://localhost:8080/{api}"}

        self.logger.info(f"Started {len(started_apis)} API mocks")
        return {"apis": started_apis}

    async def simulate_circuit_breaker(self, service_name: str, failure_rate: float = 0.5) -> None:
        """Simulate circuit breaker behavior."""
        if service_name in self.services:
            service = self.services[service_name]
            service.circuit_breaker_active = True
            service.failure_rate = failure_rate

            self.circuit_breakers[service_name] = {"active": True, "failure_rate": failure_rate}

            self.logger.info(
                f"Activated circuit breaker for {service_name} with {failure_rate * 100}% failure rate"
            )


class MockMongoDBService:
    """Mock MongoDB service for testing."""

    def __init__(self):
        """Initialize MongoDB mock."""
        self.is_running = False
        self.collections = {"properties": [], "processing_cache": [], "validation_results": []}
        self.circuit_breaker_active = False
        self.failure_rate = 0.0

    async def start(self):
        """Start the mock MongoDB service."""
        self.is_running = True

    async def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Mock insert operation."""
        if self.circuit_breaker_active and random.random() < self.failure_rate:
            raise DatabaseError("Circuit breaker active for MongoDB")

        if collection not in self.collections:
            self.collections[collection] = []

        document_id = f"mock_id_{len(self.collections[collection])}"
        document["_id"] = document_id
        self.collections[collection].append(document)

        return document_id

    async def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mock find operation."""
        if self.circuit_breaker_active and random.random() < self.failure_rate:
            raise DatabaseError("Circuit breaker active for MongoDB")

        if collection not in self.collections:
            return None

        # Simple query matching
        for doc in self.collections[collection]:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc

        return None


class MockOllamaService:
    """Mock Ollama LLM service for testing."""

    def __init__(self):
        """Initialize Ollama mock."""
        self.is_running = False
        self.model_loaded = False
        self.circuit_breaker_active = False
        self.failure_rate = 0.0

    async def start(self):
        """Start the mock Ollama service."""
        self.is_running = True
        self.model_loaded = True

    async def generate_response(
        self, prompt: str, model: str = "llama3.2:latest"
    ) -> Dict[str, Any]:
        """Mock LLM response generation."""
        if self.circuit_breaker_active and random.random() < self.failure_rate:
            raise PhoenixREError("Circuit breaker active for Ollama")

        # Generate mock response based on prompt
        if "property" in prompt.lower():
            response = {
                "address": "123 Mock St, Phoenix, AZ 85001",
                "beds": 3,
                "baths": 2,
                "sqft": 1500,
                "price": 350000,
            }
        else:
            response = {"message": "Mock LLM response"}

        return {"model": model, "response": response, "done": True}

    async def check_model_availability(self, model: str) -> bool:
        """Mock model availability check."""
        return model == "llama3.2:latest"


class MockMaricopaAPI:
    """Mock Maricopa County API."""

    def __init__(self):
        self.is_running = False

    async def start(self):
        self.is_running = True


class MockWebShareProxy:
    """Mock WebShare proxy service."""

    def __init__(self):
        self.is_running = False

    async def start(self):
        self.is_running = True


class MockCaptchaAPI:
    """Mock 2captcha API service."""

    def __init__(self):
        self.is_running = False

    async def start(self):
        self.is_running = True
