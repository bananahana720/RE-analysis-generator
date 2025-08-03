"""Test suite for Ollama client."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from aiohttp import ClientError

from phoenix_real_estate.collectors.processing import OllamaClient
from phoenix_real_estate.foundation import ConfigProvider


class TestOllamaClient:
    """Test suite for Ollama client."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        from unittest.mock import Mock

        config = Mock(spec=ConfigProvider)

        # Support get() method for compatibility
        config.get = Mock(
            side_effect=lambda key, default=None: {
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "LLM_MODEL": "llama3.2:latest",
                "LLM_TIMEOUT": 30,
                "LLM_MAX_RETRIES": 2,
            }.get(key, default)
        )

        # Support get_typed() method for type-safe configuration access
        def mock_get_typed(key, type_cls, default=None):
            values = {"LLM_TIMEOUT": 30, "LLM_MAX_RETRIES": 2}
            value = values.get(key, default)
            if value is not None and type_cls is not None:
                return type_cls(value)
            return value

        config.get_typed = Mock(side_effect=mock_get_typed)

        return config

    @pytest.fixture
    async def ollama_client(self, test_config):
        """Create Ollama client instance."""
        return OllamaClient(test_config)

    @pytest.mark.asyncio
    async def test_client_initialization(self, test_config):
        """Test client initializes with correct configuration."""
        client = OllamaClient(test_config)

        assert client.base_url == "http://localhost:11434"
        assert client.model_name == "llama3.2:latest"
        assert client.timeout_seconds == 30
        assert client.max_retries == 2
        assert client.session is None  # Not created until used

    @pytest.mark.asyncio
    async def test_context_manager(self, ollama_client):
        """Test client works as async context manager."""
        async with ollama_client as client:
            assert client.session is not None
            assert not client.session.closed

        # Session should be closed after exit
        assert client.session is None or client.session.closed

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_client):
        """Test health check when Ollama is available."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"version": "0.1.20"})

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            # First check version endpoint
            mock_tags_response = AsyncMock()
            mock_tags_response.status = 200
            mock_tags_response.json = AsyncMock(
                return_value={
                    "models": [
                        {"name": "llama3.2:latest", "size": 3825819519},
                        {"name": "codellama:latest", "size": 3791811617},
                    ]
                }
            )

            with patch("aiohttp.ClientSession.get") as mock_get_tags:
                mock_get_tags.return_value.__aenter__.return_value = mock_tags_response

                result = await ollama_client.health_check()
                assert result is True

    @pytest.mark.asyncio
    async def test_health_check_model_not_available(self, ollama_client):
        """Test health check when model is not available."""
        # Version endpoint succeeds
        mock_version_response = AsyncMock()
        mock_version_response.status = 200

        # Tags endpoint returns different models
        mock_tags_response = AsyncMock()
        mock_tags_response.status = 200
        mock_tags_response.json = AsyncMock(return_value={"models": [{"name": "mistral:latest"}]})

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = [
                mock_version_response,
                mock_tags_response,
            ]

            result = await ollama_client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, ollama_client):
        """Test successful completion generation."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "model": "llama3.2:latest",
                "created_at": "2025-01-20T10:00:00Z",
                "response": "Generated text response",
                "done": True,
                "eval_count": 150,
            }
        )

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await ollama_client.generate_completion(
                "Test prompt", system_prompt="You are a helpful assistant", max_tokens=1000
            )

            assert result == "Generated text response"

            # Verify request payload
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["model"] == "llama3.2:latest"
            assert payload["prompt"] == "Test prompt"
            assert payload["system"] == "You are a helpful assistant"
            assert payload["options"]["num_predict"] == 1000
            assert payload["stream"] is False

    @pytest.mark.asyncio
    async def test_extract_structured_data_success(self, ollama_client):
        """Test structured data extraction."""
        extraction_schema = {
            "address": {"type": "string", "description": "Property address"},
            "price": {"type": "number", "description": "Property price"},
        }

        # Mock LLM response with JSON
        mock_llm_response = """I'll extract the property data for you.

<output>
{
  "address": "123 Main St",
  "price": 350000
}
</output>"""

        with patch.object(ollama_client, "generate_completion") as mock_gen:
            mock_gen.return_value = mock_llm_response

            result = await ollama_client.extract_structured_data(
                "<div>Property at 123 Main St for $350,000</div>",
                extraction_schema,
                content_type="html",
            )

            assert result == {"address": "123 Main St", "price": 350000}

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, ollama_client):
        """Test retry mechanism on network errors."""
        # Fail once, then succeed
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"model": "llama3.2:latest", "response": "Success", "done": True}
        )

        with patch("aiohttp.ClientSession.post") as mock_post:
            # First call raises exception, second succeeds
            mock_post.return_value.__aenter__.side_effect = [
                ClientError("Connection failed"),
                mock_response,
            ]

            # Should retry and succeed
            result = await ollama_client.generate_completion("Test")
            assert result == "Success"
            assert mock_post.call_count == 2  # Original + 1 retry

    @pytest.mark.asyncio
    async def test_generate_completion_timeout(self, ollama_client):
        """Test handling of timeout errors."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.side_effect = asyncio.TimeoutError()

            result = await ollama_client.generate_completion("Test prompt")
            assert result is None

    @pytest.mark.asyncio
    async def test_extract_structured_data_invalid_json(self, ollama_client):
        """Test handling of invalid JSON in extraction."""
        mock_llm_response = """Here's the data:
<output>
{invalid json}
</output>"""

        with patch.object(ollama_client, "generate_completion") as mock_gen:
            mock_gen.return_value = mock_llm_response

            result = await ollama_client.extract_structured_data(
                "Test content", {"field": {"type": "string"}}, content_type="text"
            )

            assert result is None
