"""Ollama client for local LLM processing."""

import asyncio
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.foundation.utils.helpers import retry_async


class OllamaClient:
    """Client for local Ollama LLM processing."""
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize Ollama client."""
        self.config = config
        self.logger = get_logger("llm.ollama_client")
        
        # Load configuration - CORRECT pattern using getattr
        self.base_url = getattr(config.settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = getattr(config.settings, "LLM_MODEL", "llama3.2:latest") 
        self.timeout_seconds = getattr(config.settings, "LLM_TIMEOUT", 30)
        self.max_retries = getattr(config.settings, "LLM_MAX_RETRIES", 2)
        
        # HTTP client setup
        self.timeout = ClientTimeout(total=self.timeout_seconds)
        self.session: Optional[ClientSession] = None
        
        self.logger.info(
            "Ollama client initialized",
            extra={
                "base_url": self.base_url,
                "model": self.model_name,
                "timeout_seconds": self.timeout_seconds
            }
        )
    
    async def __aenter__(self) -> "OllamaClient":
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available."""
        if self.session is None or self.session.closed:
            self.session = ClientSession(
                timeout=self.timeout,
                connector=aiohttp.TCPConnector(limit=5, limit_per_host=2)
            )
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available."""
        try:
            await self._ensure_session()
            
            # Check service health
            async with self.session.get(f"{self.base_url}/api/version") as response:
                if response.status != 200:
                    return False
            
            # Check if model is available
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    return False
                
                data = await response.json()
                models = [model.get("name", "") for model in data.get("models", [])]
                model_available = any(self.model_name in model for model in models)
                
                if not model_available:
                    self.logger.warning(
                        "LLM model not found",
                        extra={
                            "requested_model": self.model_name,
                            "available_models": models
                        }
                    )
                    return False
            
            self.logger.debug("Ollama health check passed")
            return True
            
        except Exception as e:
            self.logger.warning(
                "Ollama health check failed",
                extra={"error": str(e)}
            )
            return False
    
    async def generate_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """Generate completion using Ollama."""
        # Use retry wrapper
        return await retry_async(
            self._generate_completion_impl,
            prompt,
            system_prompt,
            max_tokens,
            max_retries=self.max_retries,
            delay=1.0,
            backoff_factor=2.0
        )
    
    async def _generate_completion_impl(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """Internal implementation of generate_completion."""
        try:
            await self._ensure_session()
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.1,  # Low for consistency
                    "top_p": 0.9,
                    "seed": 42  # For reproducibility
                },
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Make request
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    self.logger.error(
                        "Ollama API error",
                        extra={
                            "status": response.status,
                            "response": await response.text()
                        }
                    )
                    return None
                
                data = await response.json()
                
                # Extract response text
                response_text = data.get("response", "")
                
                self.logger.debug(
                    "Completion generated",
                    extra={
                        "prompt_length": len(prompt),
                        "response_length": len(response_text),
                        "eval_count": data.get("eval_count", 0)
                    }
                )
                
                return response_text
                
        except asyncio.TimeoutError:
            self.logger.error("Ollama request timed out")
            return None
        except ClientError as e:
            self.logger.error(
                "HTTP client error",
                extra={"error": str(e)}
            )
            raise  # Let retry_async handle it
        except Exception as e:
            self.logger.error(
                "Unexpected error generating completion",
                extra={"error": str(e)}
            )
            return None
    
    async def extract_structured_data(
        self,
        content: str,
        extraction_schema: Dict[str, Any],
        content_type: str = "text"
    ) -> Optional[Dict[str, Any]]:
        """Extract structured data using LLM."""
        # Build prompt for extraction
        schema_description = self._build_schema_description(extraction_schema)
        
        prompt = f"""Extract the following information from the {content_type} content:

{schema_description}

Content:
{content}

Important: Respond with ONLY the JSON data wrapped in <output> tags.
Example: <output>{{"field": "value"}}</output>
"""
        
        system_prompt = "You are a data extraction specialist. Extract information accurately and return only JSON data."
        
        # Generate completion
        response = await self.generate_completion(
            prompt,
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        if not response:
            return None
        
        # Extract JSON from response
        return self._extract_json_from_response(response)
    
    def _build_schema_description(self, schema: Dict[str, Any]) -> str:
        """Build human-readable schema description."""
        lines = []
        for field, spec in schema.items():
            field_type = spec.get("type", "string")
            description = spec.get("description", f"The {field}")
            lines.append(f"- {field} ({field_type}): {description}")
        return "\n".join(lines)
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data from LLM response."""
        try:
            # Look for content between <output> tags
            match = re.search(r'<output>\s*(\{.*?\})\s*</output>', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            
            # Fallback: try to find any JSON-like structure
            match = re.search(r'\{[^{}]*\}', response)
            if match:
                return json.loads(match.group(0))
            
            self.logger.warning(
                "No JSON found in response",
                extra={"response_preview": response[:200]}
            )
            return None
            
        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse JSON from response",
                extra={"error": str(e), "response_preview": response[:200]}
            )
            return None