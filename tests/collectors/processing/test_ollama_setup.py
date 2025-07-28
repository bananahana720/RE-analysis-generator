"""Test Ollama service setup and availability."""

import pytest
import aiohttp


@pytest.mark.asyncio
async def test_ollama_service_available():
    """Test Ollama service is running locally."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:11434/api/version") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "version" in data
        except aiohttp.ClientError:
            pytest.fail("Ollama service not running. Run: ollama serve")


@pytest.mark.asyncio
async def test_llama3_model_available():
    """Test llama3.2:latest model is available."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:11434/api/tags") as resp:
                data = await resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                assert any("llama3.2:latest" in model for model in models), \
                    "llama3.2:latest not found. Run: ollama pull llama3.2:latest"
        except aiohttp.ClientError:
            pytest.fail("Cannot connect to Ollama service")


@pytest.mark.asyncio
async def test_ollama_generate_endpoint():
    """Test Ollama generate endpoint is accessible."""
    async with aiohttp.ClientSession() as session:
        try:
            # Test with a simple prompt
            payload = {
                "model": "llama3.2:latest",
                "prompt": "Hello",
                "stream": False
            }
            async with session.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "response" in data
                assert data.get("done") is True
        except aiohttp.ClientError:
            pytest.fail("Cannot generate with Ollama")