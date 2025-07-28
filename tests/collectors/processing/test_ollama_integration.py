"""Integration tests for Ollama client with real service."""

import pytest
import aiohttp
from unittest.mock import Mock

from phoenix_real_estate.collectors.processing import OllamaClient
from phoenix_real_estate.foundation import ConfigProvider


@pytest.mark.integration
class TestOllamaIntegration:
    """Integration tests that require real Ollama service."""
    
    @pytest.fixture
    def real_config(self):
        """Create real configuration."""
        config = Mock(spec=ConfigProvider)
        config.settings = Mock()
        config.settings.OLLAMA_BASE_URL = "http://localhost:11434"
        config.settings.LLM_MODEL = "llama3.2:latest"
        config.settings.LLM_TIMEOUT = 30
        config.settings.LLM_MAX_RETRIES = 2
        return config
    
    @pytest.mark.asyncio
    async def test_real_health_check(self, real_config):
        """Test health check with real Ollama service."""
        # Skip if Ollama is not running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/version", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip("Ollama service not running")
        except:
            pytest.skip("Ollama service not running")
        
        async with OllamaClient(real_config) as client:
            result = await client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_real_completion(self, real_config):
        """Test completion generation with real Ollama."""
        # Skip if Ollama is not running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/version", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip("Ollama service not running")
        except:
            pytest.skip("Ollama service not running")
        
        async with OllamaClient(real_config) as client:
            # Simple test prompt
            result = await client.generate_completion(
                "What is 2+2? Answer with just the number.",
                max_tokens=10
            )
            
            assert result is not None
            assert "4" in result
    
    @pytest.mark.asyncio
    async def test_real_extraction(self, real_config):
        """Test data extraction with real Ollama."""
        # Skip if Ollama is not running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/version", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip("Ollama service not running")
        except:
            pytest.skip("Ollama service not running")
        
        async with OllamaClient(real_config) as client:
            # Test property data extraction
            html_content = """
            <div class="property">
                <h2>Beautiful Home in Phoenix</h2>
                <p>Address: 123 Main St, Phoenix, AZ 85031</p>
                <p>Price: $450,000</p>
                <p>Bedrooms: 3</p>
                <p>Bathrooms: 2</p>
            </div>
            """
            
            schema = {
                "address": {"type": "string", "description": "Full property address"},
                "price": {"type": "number", "description": "Property price in dollars"},
                "bedrooms": {"type": "integer", "description": "Number of bedrooms"},
                "bathrooms": {"type": "integer", "description": "Number of bathrooms"}
            }
            
            result = await client.extract_structured_data(
                html_content,
                schema,
                content_type="html"
            )
            
            assert result is not None
            assert "address" in result
            assert "price" in result
            assert result["bedrooms"] == 3
            assert result["bathrooms"] == 2