# Task 06: LLM Data Processing - Implementation Tasks (TDD Version)

**Status**: 58% Complete (7/12 tasks completed)  
**Test Coverage**: 83 unit tests passing  
**Model**: Llama 3.2:latest (per user specification)  
**Architecture**: OllamaClient → PropertyDataExtractor → ProcessingValidator → DataProcessingPipeline

## TDD Implementation Philosophy

### Red-Green-Refactor Cycle
1. **Red Phase**: Write failing tests that define expected behavior
2. **Green Phase**: Write minimal code to make tests pass
3. **Refactor Phase**: Improve code quality while maintaining passing tests

### Time Allocation Updates
- Each task now includes 30-40% time for test development
- Tests must be written and failing before implementation begins
- Refactoring time is explicitly allocated

---

## Task Breakdown & Assignments

### Day 1: Foundation & Ollama Setup

#### TASK-06-001: Project Structure & Ollama Setup
**Assignee**: Backend Developer  
**Duration**: 2 hours (was 1.5 hours)  
**Priority**: P0 - Blocker  
**Dependencies**: None

**TDD Process**:

1. **Red Phase (45 min)**: Write failing import and setup tests
```python
# tests/collectors/processing/test_imports.py
def test_module_imports():
    """Test all LLM processing modules can be imported."""
    # These will fail initially
    from phoenix_real_estate.collectors.processing import OllamaClient
    from phoenix_real_estate.collectors.processing import PropertyDataExtractor
    from phoenix_real_estate.collectors.processing import ProcessingValidator
    from phoenix_real_estate.collectors.processing import DataProcessingPipeline
    
    assert OllamaClient is not None
    assert PropertyDataExtractor is not None
    assert ProcessingValidator is not None
    assert DataProcessingPipeline is not None

# tests/collectors/processing/test_ollama_setup.py
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
async def test_llama32_model_available():
    """Test llama3.2:latest model is available."""
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:11434/api/tags") as resp:
            data = await resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            assert any("llama3.2:latest" in model for model in models), \
                "llama3.2:latest not found. Run: ollama pull llama3.2:latest"
```

2. **Green Phase (1 hour)**: Create structure and verify Ollama
```bash
# Commands to execute
mkdir -p src/phoenix_real_estate/collectors/processing
mkdir -p tests/collectors/processing
mkdir -p tests/fixtures/llm_processing

# Create module files
touch src/phoenix_real_estate/collectors/processing/__init__.py

# Install Ollama and pull model
# Manual step: Download from https://ollama.ai
ollama pull llama3.2:latest
ollama serve  # Run in separate terminal

# Create basic module structure
echo "class OllamaClient: pass" >> src/phoenix_real_estate/collectors/processing/__init__.py
echo "class PropertyDataExtractor: pass" >> src/phoenix_real_estate/collectors/processing/__init__.py
echo "class ProcessingValidator: pass" >> src/phoenix_real_estate/collectors/processing/__init__.py
echo "class DataProcessingPipeline: pass" >> src/phoenix_real_estate/collectors/processing/__init__.py
```

3. **Refactor Phase (15 min)**: Organize imports properly
```python
# src/phoenix_real_estate/collectors/processing/__init__.py
"""LLM-powered data processing for property information."""

from .llm_client import OllamaClient
from .extractor import PropertyDataExtractor
from .validator import ProcessingValidator
from .pipeline import DataProcessingPipeline

__all__ = [
    "OllamaClient",
    "PropertyDataExtractor",
    "ProcessingValidator",
    "DataProcessingPipeline"
]

# Add version info
__version__ = "0.1.0"
```

**Acceptance Criteria**:
- [ ] Import tests written and initially failing
- [ ] Ollama service installed and running
- [ ] Llama 3.2:latest model downloaded
- [ ] All directories created
- [ ] Import tests passing
- [ ] Module structure properly organized

---

#### TASK-06-002: Ollama Client Implementation
**Assignee**: Backend Developer  
**Duration**: 4.5 hours (was 3 hours)  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-06-001

**TDD Process**:

1. **Red Phase (1.5 hours)**: Write comprehensive Ollama client tests
```python
# tests/collectors/processing/test_ollama_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from aiohttp import ClientError

from phoenix_real_estate.collectors.processing import OllamaClient
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError

class TestOllamaClient:
    """Test suite for Ollama client."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = ConfigProvider()
        setattr(config.settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        setattr(config.settings, "LLM_MODEL", "llama3.2:latest")
        setattr(config.settings, "LLM_TIMEOUT", 30)
        setattr(config.settings, "LLM_MAX_RETRIES", 2)
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
        mock_response.json = AsyncMock(return_value={
            "version": "0.1.20"
        })
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # First check version endpoint
            mock_tags_response = AsyncMock()
            mock_tags_response.status = 200
            mock_tags_response.json = AsyncMock(return_value={
                "models": [
                    {"name": "llama3.2:latest", "size": 3825819519},
                    {"name": "codellama:latest", "size": 3791811617}
                ]
            })
            
            with patch('aiohttp.ClientSession.get') as mock_get_tags:
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
        mock_tags_response.json = AsyncMock(return_value={
            "models": [{"name": "mistral:latest"}]
        })
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.side_effect = [
                mock_version_response,
                mock_tags_response
            ]
            
            result = await ollama_client.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_generate_completion_success(self, ollama_client):
        """Test successful completion generation."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "model": "llama3.2:latest",
            "created_at": "2025-01-20T10:00:00Z",
            "response": "Generated text response",
            "done": True,
            "eval_count": 150
        })
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await ollama_client.generate_completion(
                "Test prompt",
                system_prompt="You are a helpful assistant",
                max_tokens=1000
            )
            
            assert result == "Generated text response"
            
            # Verify request payload
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['model'] == "llama3.2:latest"
            assert payload['prompt'] == "Test prompt"
            assert payload['system'] == "You are a helpful assistant"
            assert payload['options']['num_predict'] == 1000
            assert payload['stream'] is False
    
    @pytest.mark.asyncio
    async def test_extract_structured_data_success(self, ollama_client):
        """Test structured data extraction."""
        extraction_schema = {
            "address": {"type": "string", "description": "Property address"},
            "price": {"type": "number", "description": "Property price"}
        }
        
        # Mock LLM response with JSON
        mock_llm_response = """I'll extract the property data for you.

<output>
{
  "address": "123 Main St",
  "price": 350000
}
</output>"""
        
        with patch.object(ollama_client, 'generate_completion') as mock_gen:
            mock_gen.return_value = mock_llm_response
            
            result = await ollama_client.extract_structured_data(
                "<div>Property at 123 Main St for $350,000</div>",
                extraction_schema,
                content_type="html"
            )
            
            assert result == {"address": "123 Main St", "price": 350000}
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, ollama_client):
        """Test retry mechanism on network errors."""
        # Fail once, then succeed
        mock_responses = [
            ClientError("Connection failed"),  # First attempt fails
            AsyncMock(status=200, json=AsyncMock(return_value={"response": "Success"}))  # Second succeeds
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.side_effect = mock_responses
            
            # Should retry and succeed
            result = await ollama_client.generate_completion("Test")
            assert result == "Success"
            assert mock_post.call_count == 2  # Original + 1 retry
```

2. **Green Phase (2 hours)**: Implement minimal Ollama client
```python
# src/phoenix_real_estate/collectors/processing/llm_client.py
"""Ollama client for local LLM processing."""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
from aiohttp import ClientSession, ClientTimeout

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
                    "stop": ["</output>", "\n\n---"]
                },
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            self.logger.debug(
                "Generating LLM completion",
                extra={
                    "model": self.model_name,
                    "prompt_length": len(prompt),
                    "max_tokens": max_tokens
                }
            )
            
            start_time = datetime.utcnow()
            
            # Use retry utility from Epic 1
            async def _generate() -> str:
                async with self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ProcessingError(
                            f"Ollama API returned status {response.status}",
                            context={
                                "status": response.status,
                                "response": error_text[:500]
                            }
                        )
                    
                    data = await response.json()
                    return data.get("response", "").strip()
            
            completion = await retry_async(
                _generate,
                max_retries=self.max_retries,
                delay=1.0
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.debug(
                "LLM completion generated",
                extra={
                    "completion_length": len(completion),
                    "processing_time_seconds": processing_time
                }
            )
            
            return completion
            
        except Exception as e:
            self.logger.error(
                "LLM completion failed",
                extra={"error": str(e)}
            )
            raise ProcessingError(
                "Failed to generate LLM completion",
                context={"model": self.model_name},
                cause=e
            ) from e
    
    async def extract_structured_data(
        self, 
        content: str, 
        extraction_schema: Dict[str, Any],
        content_type: str = "html"
    ) -> Optional[Dict[str, Any]]:
        """Extract structured data from content."""
        try:
            # Build prompts
            system_prompt = self._build_extraction_system_prompt(extraction_schema, content_type)
            user_prompt = self._build_extraction_user_prompt(content, extraction_schema)
            
            # Generate completion
            completion = await self.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1500
            )
            
            if not completion:
                return None
            
            # Parse output
            return self._parse_extraction_output(completion)
            
        except Exception as e:
            self.logger.error(
                "Structured data extraction failed",
                extra={"error": str(e)}
            )
            raise ProcessingError(
                "Failed to extract structured data",
                context={"content_type": content_type},
                cause=e
            ) from e
    
    def _build_extraction_system_prompt(self, schema: Dict[str, Any], content_type: str) -> str:
        """Build system prompt for extraction."""
        return f"""You are a precise data extraction assistant specializing in real estate property information.

Extract structured data from {content_type} content according to the provided schema.

EXTRACTION SCHEMA:
{json.dumps(schema, indent=2)}

INSTRUCTIONS:
1. Extract only information explicitly present in the content
2. Use null for missing information
3. Normalize addresses to standard format
4. Convert prices to numeric values without currency symbols
5. Return JSON within <output> tags

Example:
<output>
{{"address": "123 Main St", "price": 350000}}
</output>"""
    
    def _build_extraction_user_prompt(self, content: str, schema: Dict[str, Any]) -> str:
        """Build user prompt for extraction."""
        # Truncate if too long
        max_length = 4000
        if len(content) > max_length:
            content = content[:max_length] + "...[truncated]"
        
        return f"""Extract structured data from the following content:

CONTENT:
{content}

Extract according to the schema and return JSON within <output> tags."""
    
    def _parse_extraction_output(self, completion: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from completion."""
        try:
            # Find JSON between output tags
            start = completion.find("<output>")
            end = completion.find("</output>")
            
            if start != -1 and end != -1:
                json_str = completion[start + 8:end].strip()
            else:
                # Try to find raw JSON
                start = completion.find("{")
                end = completion.rfind("}")
                if start != -1 and end != -1:
                    json_str = completion[start:end + 1]
                else:
                    return None
            
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            self.logger.warning(
                "Failed to parse JSON output",
                extra={"error": str(e)}
            )
            return None
```

3. **Refactor Phase (1 hour)**: Improve error handling and performance
```python
# Add to OllamaClient class
    
    async def batch_extract(
        self,
        contents: List[Dict[str, Any]],
        extraction_schema: Dict[str, Any],
        batch_size: int = 5
    ) -> List[Optional[Dict[str, Any]]]:
        """Extract data from multiple contents in batches."""
        results = []
        
        for i in range(0, len(contents), batch_size):
            batch = contents[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self.extract_structured_data(
                    item["content"],
                    extraction_schema,
                    item.get("type", "html")
                )
                for item in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.warning(f"Batch item failed: {result}")
                    results.append(None)
                else:
                    results.append(result)
            
            # Small delay between batches
            if i + batch_size < len(contents):
                await asyncio.sleep(0.5)
        
        return results
    
    def get_extraction_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate confidence score for extracted data."""
        if not extracted_data:
            return 0.0
        
        # Count non-null fields
        total_fields = len(extracted_data)
        non_null_fields = sum(1 for v in extracted_data.values() if v is not None)
        
        # Base confidence on completeness
        confidence = non_null_fields / total_fields if total_fields > 0 else 0.0
        
        # Boost confidence for critical fields
        critical_fields = ["address", "price"]
        critical_present = sum(1 for f in critical_fields if extracted_data.get(f) is not None)
        confidence += (critical_present / len(critical_fields)) * 0.2
        
        return min(confidence, 1.0)
```

**Test-First Checkpoints**:
- [ ] All Ollama client tests written before implementation
- [ ] Tests initially fail (Red phase)
- [ ] Minimal implementation makes tests pass (Green phase)
- [ ] Code refactored for quality (Refactor phase)
- [ ] All tests still passing after refactor
- [ ] Async operations properly handled
- [ ] Epic 1 integration patterns followed

---

### Day 2: Core LLM Implementation

#### TASK-06-003: Property Data Extractor
**Assignee**: Backend Developer  
**Duration**: 5 hours (was 3.5 hours)  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-06-002

**TDD Process**:

1. **Red Phase (1.5 hours)**: Write comprehensive extractor tests
```python
# tests/collectors/processing/test_extractor.py
import pytest
from unittest.mock import Mock, AsyncMock, patch

from phoenix_real_estate.collectors.processing import PropertyDataExtractor, OllamaClient
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError

# Test fixtures
SAMPLE_PHOENIX_MLS_HTML = """
<div class="property-listing">
    <div class="property-address">123 Main St, Phoenix, AZ 85001</div>
    <div class="property-price">$450,000</div>
    <div class="property-details">
        <span class="beds">3 beds</span>
        <span class="baths">2 baths</span>
        <span class="sqft">1,850 sqft</span>
    </div>
    <div class="property-description">
        Beautiful single family home with updated kitchen
    </div>
</div>
"""

SAMPLE_MARICOPA_TEXT = """
Property Information:
Parcel: 123-45-678
Owner: SMITH JOHN
Address: 456 Oak Ave, Phoenix, AZ 85003
Total Value: $275,000
Land Value: $50,000
Improvement Value: $225,000
Tax Year: 2024
"""

class TestPropertyDataExtractor:
    """Test suite for property data extraction."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = ConfigProvider()
        setattr(config.settings, "LLM_ENABLE_FALLBACK", True)
        setattr(config.settings, "LLM_BATCH_SIZE", 5)
        return config
    
    @pytest.fixture
    async def extractor(self, test_config):
        """Create extractor instance."""
        return PropertyDataExtractor(test_config)
    
    @pytest.mark.asyncio
    async def test_extractor_initialization(self, test_config):
        """Test extractor initializes properly."""
        extractor = PropertyDataExtractor(test_config)
        
        assert extractor.llm_client is not None
        assert isinstance(extractor.validator, DataValidator)
        assert extractor.enable_fallback is True
        assert extractor.batch_size == 5
        assert len(extractor.property_schema) > 0
    
    @pytest.mark.asyncio
    async def test_extract_from_html_with_llm_success(self, extractor):
        """Test successful HTML extraction using LLM."""
        # Mock LLM response
        llm_response = {
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001",
            "price": 450000,
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1850,
            "property_type": "Single Family",
            "description": "Beautiful single family home with updated kitchen"
        }
        
        with patch.object(extractor, '_extract_with_llm') as mock_llm:
            mock_llm.return_value = llm_response
            
            result = await extractor.extract_from_html(
                SAMPLE_PHOENIX_MLS_HTML,
                source="phoenix_mls"
            )
            
            assert result is not None
            assert result["address"] == "123 Main St"
            assert result["price"] == 450000
            assert result["bedrooms"] == 3
            assert result["bathrooms"] == 2
            assert result["square_feet"] == 1850
    
    @pytest.mark.asyncio
    async def test_extract_from_html_with_fallback(self, extractor):
        """Test fallback extraction when LLM fails."""
        # Mock LLM failure
        with patch.object(extractor, '_extract_with_llm') as mock_llm:
            mock_llm.return_value = None  # LLM extraction failed
            
            # Mock fallback success
            with patch.object(extractor, '_fallback_html_extraction') as mock_fallback:
                mock_fallback.return_value = {
                    "address": "123 Main St, Phoenix, AZ 85001",
                    "price": 450000
                }
                
                result = await extractor.extract_from_html(
                    SAMPLE_PHOENIX_MLS_HTML,
                    source="phoenix_mls"
                )
                
                assert result is not None
                assert result["price"] == 450000
                assert mock_fallback.called
    
    @pytest.mark.asyncio
    async def test_extract_from_text_success(self, extractor):
        """Test text extraction from Maricopa format."""
        llm_response = {
            "address": "456 Oak Ave",
            "city": "Phoenix",
            "state": "AZ", 
            "zip_code": "85003",
            "price": 275000
        }
        
        with patch.object(extractor, '_extract_with_llm') as mock_llm:
            mock_llm.return_value = llm_response
            
            result = await extractor.extract_from_text(
                SAMPLE_MARICOPA_TEXT,
                source="maricopa"
            )
            
            assert result is not None
            assert result["address"] == "456 Oak Ave"
            assert result["price"] == 275000
    
    @pytest.mark.asyncio
    async def test_data_cleaning(self, extractor):
        """Test data cleaning and normalization."""
        dirty_data = {
            "address": "  123 MAIN ST  ",
            "city": "phoenix",
            "state": "arizona",
            "zip_code": "85001-1234",
            "price": "$450,000",
            "bedrooms": "3 beds",
            "bathrooms": "2.5",
            "square_feet": "1,850 sq ft",
            "features": ["pool", "", "  garage  ", None]
        }
        
        cleaned = extractor._clean_extracted_data(dirty_data)
        
        assert cleaned["address"] == "123 Main St"  # Normalized
        assert cleaned["city"] == "Phoenix"  # Title case
        assert cleaned["state"] == "AZ"  # State abbreviation
        assert cleaned["zip_code"] == "85001"  # 5-digit only
        assert cleaned["price"] == 450000  # Numeric
        assert cleaned["bedrooms"] == 3  # Integer
        assert cleaned["bathrooms"] == 2.5  # Float
        assert cleaned["square_feet"] == 1850  # No commas
        assert cleaned["features"] == ["pool", "garage"]  # Cleaned list
    
    @pytest.mark.asyncio
    async def test_batch_extraction(self, extractor):
        """Test batch extraction with multiple contents."""
        contents = [
            {"content": SAMPLE_PHOENIX_MLS_HTML, "type": "html"},
            {"content": SAMPLE_MARICOPA_TEXT, "type": "text"},
            {"content": "<div>Invalid HTML</div>", "type": "html"}
        ]
        
        # Mock different results
        async def mock_extract_html(content, source):
            if "123 Main St" in content:
                return {"address": "123 Main St", "price": 450000}
            return None
        
        async def mock_extract_text(content, source):
            if "456 Oak Ave" in content:
                return {"address": "456 Oak Ave", "price": 275000}
            return None
        
        with patch.object(extractor, 'extract_from_html', side_effect=mock_extract_html):
            with patch.object(extractor, 'extract_from_text', side_effect=mock_extract_text):
                results = await extractor.extract_batch(contents, source="test")
                
                assert len(results) == 3
                assert results[0]["address"] == "123 Main St"
                assert results[1]["address"] == "456 Oak Ave"
                assert results[2] is None  # Invalid content
    
    @pytest.mark.asyncio
    async def test_validation_integration(self, extractor):
        """Test integration with Epic 1 validator."""
        valid_data = {
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001",
            "price": 450000
        }
        
        invalid_data = {
            "price": -1000  # Invalid price
        }
        
        # Valid data should pass
        assert extractor._validate_extracted_data(valid_data) is True
        
        # Invalid data should fail
        assert extractor._validate_extracted_data(invalid_data) is False
```

2. **Green Phase (2.5 hours)**: Implement property data extractor
```python
# src/phoenix_real_estate/collectors/processing/extractor.py
"""LLM-powered data extraction for property information."""

import asyncio
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError, ValidationError
from phoenix_real_estate.foundation.utils.helpers import safe_int, safe_float, normalize_address
from phoenix_real_estate.foundation.utils.validators import DataValidator
from .llm_client import OllamaClient


class PropertyDataExtractor:
    """LLM-powered property data extraction."""
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize property data extractor."""
        self.config = config
        self.logger = get_logger("llm.property_extractor")
        
        # Initialize components
        self.llm_client = OllamaClient(config)
        self.validator = DataValidator()
        
        # Configuration using getattr pattern
        self.enable_fallback = getattr(config.settings, "LLM_ENABLE_FALLBACK", True)
        self.batch_size = getattr(config.settings, "LLM_BATCH_SIZE", 5)
        
        # Property extraction schema
        self.property_schema = {
            "address": {"type": "string", "description": "Full property address"},
            "city": {"type": "string", "description": "City name"},
            "state": {"type": "string", "description": "State abbreviation"},
            "zip_code": {"type": "string", "description": "ZIP code"},
            "price": {"type": "number", "description": "Property price in dollars"},
            "bedrooms": {"type": "integer", "description": "Number of bedrooms"},
            "bathrooms": {"type": "number", "description": "Number of bathrooms"},
            "square_feet": {"type": "integer", "description": "Living area in square feet"},
            "lot_size_sqft": {"type": "integer", "description": "Lot size in square feet"},
            "year_built": {"type": "integer", "description": "Year property was built"},
            "property_type": {"type": "string", "description": "Type of property"},
            "description": {"type": "string", "description": "Property description"},
            "features": {"type": "array", "description": "List of property features"},
            "parking": {"type": "string", "description": "Parking information"},
            "neighborhood": {"type": "string", "description": "Neighborhood name"}
        }
        
        self.logger.info(
            "Property data extractor initialized",
            extra={
                "schema_fields": len(self.property_schema),
                "batch_size": self.batch_size,
                "fallback_enabled": self.enable_fallback
            }
        )
    
    async def extract_from_html(self, html_content: str, source: str = "unknown") -> Optional[Dict[str, Any]]:
        """Extract property data from HTML content."""
        try:
            self.logger.debug(
                "Starting HTML extraction",
                extra={
                    "content_length": len(html_content),
                    "source": source
                }
            )
            
            # Try LLM extraction first
            extracted_data = await self._extract_with_llm(html_content, "html")
            
            if extracted_data:
                # Clean and validate
                cleaned_data = self._clean_extracted_data(extracted_data)
                
                if self._validate_extracted_data(cleaned_data):
                    self.logger.info(
                        "HTML extraction successful",
                        extra={
                            "source": source,
                            "extracted_fields": len(cleaned_data),
                            "method": "llm"
                        }
                    )
                    return cleaned_data
            
            # Fallback if enabled and LLM failed
            if self.enable_fallback:
                self.logger.info(
                    "Attempting fallback extraction",
                    extra={"source": source}
                )
                fallback_data = await self._fallback_html_extraction(html_content)
                
                if fallback_data and self._validate_extracted_data(fallback_data):
                    self.logger.info(
                        "Fallback extraction successful",
                        extra={
                            "source": source,
                            "extracted_fields": len(fallback_data),
                            "method": "fallback"
                        }
                    )
                    return fallback_data
            
            self.logger.warning(
                "HTML extraction failed",
                extra={
                    "source": source,
                    "content_length": len(html_content)
                }
            )
            return None
            
        except Exception as e:
            self.logger.error(
                "HTML extraction error",
                extra={
                    "source": source,
                    "error": str(e)
                }
            )
            raise ProcessingError(
                "Failed to extract data from HTML",
                context={"source": source},
                cause=e
            ) from e
    
    async def extract_from_text(self, text_content: str, source: str = "unknown") -> Optional[Dict[str, Any]]:
        """Extract property data from text content."""
        try:
            self.logger.debug(
                "Starting text extraction",
                extra={
                    "content_length": len(text_content),
                    "source": source
                }
            )
            
            # Try LLM extraction
            extracted_data = await self._extract_with_llm(text_content, "text")
            
            if extracted_data:
                cleaned_data = self._clean_extracted_data(extracted_data)
                
                if self._validate_extracted_data(cleaned_data):
                    self.logger.info(
                        "Text extraction successful",
                        extra={
                            "source": source,
                            "extracted_fields": len(cleaned_data),
                            "method": "llm"
                        }
                    )
                    return cleaned_data
            
            # Fallback to regex extraction
            if self.enable_fallback:
                fallback_data = await self._fallback_text_extraction(text_content)
                
                if fallback_data and self._validate_extracted_data(fallback_data):
                    self.logger.info(
                        "Text fallback extraction successful",
                        extra={
                            "source": source,
                            "extracted_fields": len(fallback_data),
                            "method": "fallback"
                        }
                    )
                    return fallback_data
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Text extraction error",
                extra={
                    "source": source,
                    "error": str(e)
                }
            )
            raise ProcessingError(
                "Failed to extract data from text",
                context={"source": source},
                cause=e
            ) from e
    
    async def extract_batch(
        self, 
        contents: List[Dict[str, Any]], 
        source: str = "unknown"
    ) -> List[Optional[Dict[str, Any]]]:
        """Extract property data from multiple contents in batch."""
        try:
            self.logger.info(
                "Starting batch extraction",
                extra={
                    "batch_size": len(contents),
                    "source": source
                }
            )
            
            results = []
            
            # Process in configured batch sizes
            for i in range(0, len(contents), self.batch_size):
                batch = contents[i:i + self.batch_size]
                
                self.logger.debug(
                    "Processing batch",
                    extra={
                        "batch_number": i // self.batch_size + 1,
                        "batch_items": len(batch),
                        "source": source
                    }
                )
                
                # Process batch items
                batch_results = []
                for item in batch:
                    content = item.get("content", "")
                    content_type = item.get("type", "html")
                    
                    if content_type == "html":
                        result = await self.extract_from_html(content, source)
                    else:
                        result = await self.extract_from_text(content, source)
                    
                    batch_results.append(result)
                
                results.extend(batch_results)
                
                # Small delay between batches
                if i + self.batch_size < len(contents):
                    await asyncio.sleep(0.5)
            
            successful = len([r for r in results if r is not None])
            
            self.logger.info(
                "Batch extraction completed",
                extra={
                    "total_items": len(contents),
                    "successful_extractions": successful,
                    "success_rate": successful / len(contents) if contents else 0,
                    "source": source
                }
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Batch extraction error",
                extra={
                    "batch_size": len(contents),
                    "source": source,
                    "error": str(e)
                }
            )
            raise ProcessingError(
                "Failed to process batch extraction",
                context={"source": source, "batch_size": len(contents)},
                cause=e
            ) from e
    
    async def _extract_with_llm(self, content: str, content_type: str) -> Optional[Dict[str, Any]]:
        """Extract data using LLM."""
        try:
            async with self.llm_client as client:
                # Check LLM health first
                if not await client.health_check():
                    self.logger.warning("LLM health check failed, skipping LLM extraction")
                    return None
                
                # Extract structured data
                extracted_data = await client.extract_structured_data(
                    content=content,
                    extraction_schema=self.property_schema,
                    content_type=content_type
                )
                
                return extracted_data
                
        except Exception as e:
            self.logger.warning(
                "LLM extraction failed",
                extra={
                    "content_type": content_type,
                    "error": str(e)
                }
            )
            return None
    
    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize extracted data."""
        cleaned = {}
        
        try:
            # Clean address
            if data.get("address"):
                cleaned["address"] = normalize_address(data["address"])
            
            # Clean city
            if data.get("city"):
                cleaned["city"] = str(data["city"]).strip().title()
            
            # Clean state
            if data.get("state"):
                state = str(data["state"]).strip().upper()
                # Normalize state names to abbreviations
                state_map = {"ARIZONA": "AZ", "AZ": "AZ"}
                cleaned["state"] = state_map.get(state, state)
            
            # Clean ZIP code
            if data.get("zip_code"):
                zip_code = str(data["zip_code"]).strip()
                # Extract 5-digit ZIP
                if "-" in zip_code:
                    zip_code = zip_code.split("-")[0]
                if zip_code.isdigit() and len(zip_code) == 5:
                    cleaned["zip_code"] = zip_code
            
            # Clean numeric fields
            numeric_fields = {
                "price": safe_float,
                "bedrooms": safe_int,
                "bathrooms": safe_float,
                "square_feet": safe_int,
                "lot_size_sqft": safe_int,
                "year_built": safe_int
            }
            
            for field, converter in numeric_fields.items():
                if field in data and data[field] is not None:
                    # Handle string values with currency/formatting
                    value = data[field]
                    if isinstance(value, str):
                        # Remove currency symbols and commas
                        value = re.sub(r'[$,]', '', value)
                        # Extract numeric part
                        match = re.search(r'[\d.]+', value)
                        if match:
                            value = match.group()
                    
                    converted = converter(value)
                    if converted is not None:
                        cleaned[field] = converted
            
            # Clean string fields
            string_fields = ["property_type", "description", "parking", "neighborhood"]
            for field in string_fields:
                if data.get(field):
                    cleaned[field] = str(data[field]).strip()
            
            # Clean features array
            if data.get("features") and isinstance(data["features"], list):
                cleaned["features"] = [
                    str(f).strip() 
                    for f in data["features"] 
                    if f and str(f).strip()
                ]
            
            return cleaned
            
        except Exception as e:
            self.logger.warning(
                "Data cleaning failed",
                extra={"error": str(e)}
            )
            return data  # Return original if cleaning fails
    
    def _validate_extracted_data(self, data: Dict[str, Any]) -> bool:
        """Validate extracted data using Epic 1 validator."""
        try:
            # Use Epic 1's DataValidator
            is_valid = self.validator.validate_property_data(data)
            
            if not is_valid:
                validation_errors = self.validator.get_errors()
                self.logger.debug(
                    "Data validation failed",
                    extra={"validation_errors": validation_errors}
                )
            
            return is_valid
            
        except Exception as e:
            self.logger.warning(
                "Data validation error",
                extra={"error": str(e)}
            )
            return False
    
    async def _fallback_html_extraction(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Fallback HTML extraction using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            data = {}
            
            # Price extraction
            price_selectors = [".property-price", ".price", "[data-price]", ".listing-price"]
            for selector in price_selectors:
                elem = soup.select_one(selector)
                if elem:
                    price_text = elem.get_text(strip=True)
                    price_value = safe_float(re.sub(r'[^\d.]', '', price_text))
                    if price_value and price_value > 10000:
                        data["price"] = price_value
                        break
            
            # Address extraction
            addr_selectors = [".property-address", ".address", "[data-address]"]
            for selector in addr_selectors:
                elem = soup.select_one(selector)
                if elem:
                    addr_text = elem.get_text(strip=True)
                    # Try to parse city, state, zip
                    match = re.search(r'([^,]+),\s*([^,]+),\s*([A-Z]{2})\s*(\d{5})', addr_text)
                    if match:
                        data["address"] = normalize_address(match.group(1))
                        data["city"] = match.group(2).strip()
                        data["state"] = match.group(3)
                        data["zip_code"] = match.group(4)
                    else:
                        data["address"] = normalize_address(addr_text)
                    break
            
            # Beds/baths/sqft extraction
            details_text = soup.get_text().lower()
            
            # Bedrooms
            bed_match = re.search(r'(\d+)\s*(?:bed|br)', details_text)
            if bed_match:
                data["bedrooms"] = safe_int(bed_match.group(1))
            
            # Bathrooms
            bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba)', details_text)
            if bath_match:
                data["bathrooms"] = safe_float(bath_match.group(1))
            
            # Square feet
            sqft_match = re.search(r'([\d,]+)\s*(?:sq\.?\s?ft|sqft)', details_text)
            if sqft_match:
                data["square_feet"] = safe_int(sqft_match.group(1).replace(',', ''))
            
            return data if data else None
            
        except Exception as e:
            self.logger.debug(
                "Fallback HTML extraction failed",
                extra={"error": str(e)}
            )
            return None
    
    async def _fallback_text_extraction(self, text_content: str) -> Optional[Dict[str, Any]]:
        """Fallback text extraction using regex patterns."""
        try:
            data = {}
            text = text_content.lower()
            
            # Price extraction
            price_patterns = [
                r'\$([0-9,]+)',
                r'price[:\s]+\$?([0-9,]+)',
                r'value[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    price_value = safe_float(match.group(1).replace(',', ''))
                    if price_value and price_value > 10000:
                        data["price"] = price_value
                        break
            
            # Address extraction
            addr_match = re.search(
                r'address[:\s]+([^\n]+)',
                text_content,  # Use original case
                re.I
            )
            if addr_match:
                addr_text = addr_match.group(1).strip()
                # Try to parse components
                match = re.search(r'([^,]+),\s*([^,]+),\s*([A-Z]{2})\s*(\d{5})', addr_text)
                if match:
                    data["address"] = normalize_address(match.group(1))
                    data["city"] = match.group(2).strip()
                    data["state"] = match.group(3)
                    data["zip_code"] = match.group(4)
                else:
                    data["address"] = normalize_address(addr_text)
            
            return data if data else None
            
        except Exception as e:
            self.logger.debug(
                "Fallback text extraction failed", 
                extra={"error": str(e)}
            )
            return None
```

3. **Refactor Phase (1 hour)**: Add advanced extraction features
```python
# Add to PropertyDataExtractor class

    def get_extraction_metrics(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate extraction quality metrics."""
        if not extracted_data:
            return {
                "completeness": 0.0,
                "confidence": 0.0,
                "field_count": 0,
                "critical_fields_present": 0
            }
        
        # Define field importance weights
        field_weights = {
            "address": 1.0,
            "price": 1.0,
            "city": 0.8,
            "state": 0.8,
            "zip_code": 0.8,
            "bedrooms": 0.7,
            "bathrooms": 0.7,
            "square_feet": 0.7,
            "property_type": 0.5,
            "year_built": 0.5,
            "description": 0.3
        }
        
        # Calculate weighted completeness
        total_weight = sum(field_weights.values())
        present_weight = sum(
            weight for field, weight in field_weights.items()
            if extracted_data.get(field) is not None
        )
        completeness = present_weight / total_weight
        
        # Count critical fields
        critical_fields = ["address", "price"]
        critical_present = sum(
            1 for field in critical_fields
            if extracted_data.get(field) is not None
        )
        
        # Calculate confidence based on multiple factors
        confidence = completeness
        if critical_present == len(critical_fields):
            confidence += 0.2  # Boost for having critical fields
        
        # Penalize if too few fields
        field_count = len([v for v in extracted_data.values() if v is not None])
        if field_count < 3:
            confidence *= 0.5
        
        return {
            "completeness": round(completeness, 3),
            "confidence": round(min(confidence, 1.0), 3),
            "field_count": field_count,
            "critical_fields_present": critical_present
        }
    
    async def extract_with_retry(
        self,
        content: str,
        content_type: str = "html",
        max_attempts: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Extract data with retry logic for improved reliability."""
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                if content_type == "html":
                    result = await self.extract_from_html(content, f"retry_{attempt}")
                else:
                    result = await self.extract_from_text(content, f"retry_{attempt}")
                
                if result:
                    # Check extraction quality
                    metrics = self.get_extraction_metrics(result)
                    if metrics["confidence"] >= 0.7:
                        return result
                    elif attempt < max_attempts - 1:
                        self.logger.warning(
                            "Low confidence extraction, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "confidence": metrics["confidence"]
                            }
                        )
                        await asyncio.sleep(1.0)  # Brief delay before retry
                
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Extraction attempt {attempt + 1} failed",
                    extra={"error": str(e)}
                )
                
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))  # Exponential backoff
        
        if last_error:
            raise ProcessingError(
                "All extraction attempts failed",
                context={"max_attempts": max_attempts},
                cause=last_error
            )
        
        return None
```

**Test-First Checkpoints**:
- [ ] All extractor tests written before implementation
- [ ] Tests verify LLM integration and fallback mechanisms
- [ ] Minimal implementation passes all tests
- [ ] Data cleaning and validation properly tested
- [ ] Batch processing functionality verified
- [ ] Epic 1 patterns properly integrated

---

#### TASK-06-004: Processing Validator
**Assignee**: Backend Developer  
**Duration**: 3.5 hours (was 2.5 hours)  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-06-002

**TDD Process**:

1. **Red Phase (1 hour)**: Write comprehensive validator tests
```python
# tests/collectors/processing/test_validator.py
import pytest
from dataclasses import dataclass
from datetime import datetime

from phoenix_real_estate.collectors.processing import ProcessingValidator
from phoenix_real_estate.collectors.processing.validator import ValidationResult
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.utils.validators import DataValidator

class TestProcessingValidator:
    """Test suite for processing validation."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = ConfigProvider()
        setattr(config.settings, "VALIDATION_MIN_CONFIDENCE", 0.7)
        setattr(config.settings, "VALIDATION_STRICT_MODE", False)
        setattr(config.settings, "VALIDATION_MIN_PRICE", 10000)
        setattr(config.settings, "VALIDATION_MAX_PRICE", 10000000)
        setattr(config.settings, "VALIDATION_MIN_SQFT", 100)
        setattr(config.settings, "VALIDATION_MAX_SQFT", 20000)
        return config
    
    @pytest.fixture
    async def validator(self, test_config):
        """Create validator instance."""
        return ProcessingValidator(test_config)
    
    @pytest.mark.asyncio
    async def test_validator_initialization(self, test_config):
        """Test validator initializes with correct configuration."""
        validator = ProcessingValidator(test_config)
        
        assert validator.base_validator is not None
        assert isinstance(validator.base_validator, DataValidator)
        assert validator.min_confidence_threshold == 0.7
        assert validator.strict_validation is False
        assert validator.min_price == 10000
        assert validator.max_price == 10000000
    
    @pytest.mark.asyncio
    async def test_validate_complete_valid_data(self, validator):
        """Test validation passes for complete valid data."""
        valid_data = {
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001",
            "price": 350000,
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1500,
            "year_built": 2020,
            "property_type": "Single Family"
        }
        
        result = await validator.validate_property_data(valid_data)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.confidence_score >= 0.8
        assert len(result.errors) == 0
        assert len(result.warnings) <= 2  # Minor warnings acceptable
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_fields(self, validator):
        """Test validation fails for missing required fields."""
        invalid_data = {
            "price": 350000,
            "bedrooms": 3
            # Missing address - required field
        }
        
        result = await validator.validate_property_data(invalid_data)
        
        assert result.is_valid is False
        assert "Address is required" in result.errors
        assert result.confidence_score < 0.5
    
    @pytest.mark.asyncio
    async def test_validate_price_boundaries(self, validator):
        """Test price validation with boundary values."""
        # Test too low
        data_low = {
            "address": "123 Main St",
            "city": "Phoenix",
            "price": 5000  # Below minimum
        }
        result_low = await validator.validate_property_data(data_low)
        assert result_low.is_valid is False
        assert any("below minimum threshold" in err for err in result_low.errors)
        
        # Test too high
        data_high = {
            "address": "123 Main St",
            "city": "Phoenix",
            "price": 50000000  # Above maximum
        }
        result_high = await validator.validate_property_data(data_high)
        assert result_high.is_valid is False
        assert any("above maximum threshold" in err for err in result_high.errors)
        
        # Test valid range
        data_valid = {
            "address": "123 Main St",
            "city": "Phoenix",
            "price": 350000  # Valid price
        }
        result_valid = await validator.validate_property_data(data_valid)
        # Should not have price errors
        assert not any("price" in err.lower() for err in result_valid.errors)
    
    @pytest.mark.asyncio
    async def test_validate_property_features(self, validator):
        """Test validation of property features."""
        # Valid features
        data_valid = {
            "address": "123 Main St",
            "bedrooms": 3,
            "bathrooms": 2.5,
            "square_feet": 1500,
            "year_built": 2020
        }
        result_valid = await validator.validate_property_data(data_valid)
        features_confidence = validator._validate_features(data_valid, [], [])
        assert features_confidence > 0.8
        
        # Invalid features
        data_invalid = {
            "address": "123 Main St",
            "bedrooms": -1,  # Invalid
            "bathrooms": 100,  # Unrealistic
            "square_feet": 50,  # Too small
            "year_built": 1500  # Too old
        }
        result_invalid = await validator.validate_property_data(data_invalid)
        assert len(result_invalid.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_validate_location_information(self, validator):
        """Test location validation."""
        # Phoenix area ZIP
        data_phoenix = {
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001"
        }
        result_phoenix = await validator.validate_property_data(data_phoenix)
        location_confidence = validator._validate_location(data_phoenix, [], [])
        assert location_confidence > 0.8
        
        # Non-Phoenix ZIP
        data_other = {
            "address": "123 Main St",
            "city": "Tucson",
            "state": "AZ",
            "zip_code": "85701"  # Tucson ZIP
        }
        result_other = await validator.validate_property_data(data_other)
        assert any("outside Phoenix area" in warn for warn in result_other.warnings)
        
        # Invalid ZIP format
        data_invalid_zip = {
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "ABCDE"  # Invalid
        }
        result_invalid = await validator.validate_property_data(data_invalid_zip)
        assert any("Invalid ZIP code" in warn for warn in result_invalid.warnings)
    
    @pytest.mark.asyncio
    async def test_confidence_score_calculation(self, validator):
        """Test confidence score calculation logic."""
        # Minimal data - low confidence
        minimal_data = {
            "address": "123 Main St"
        }
        minimal_result = await validator.validate_property_data(minimal_data)
        
        # Complete data - high confidence
        complete_data = {
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001",
            "price": 350000,
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1500,
            "year_built": 2020,
            "property_type": "Single Family",
            "lot_size_sqft": 7500,
            "description": "Beautiful home",
            "features": ["pool", "garage"]
        }
        complete_result = await validator.validate_property_data(complete_data)
        
        # Complete data should have higher confidence
        assert complete_result.confidence_score > minimal_result.confidence_score
        assert complete_result.confidence_score >= 0.9
        assert minimal_result.confidence_score < 0.5
    
    @pytest.mark.asyncio
    async def test_strict_validation_mode(self, test_config):
        """Test strict validation mode behavior."""
        # Create validator in strict mode
        setattr(test_config.settings, "VALIDATION_STRICT_MODE", True)
        strict_validator = ProcessingValidator(test_config)
        
        # Data with warnings but no errors
        data_with_warnings = {
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "price": 55000,  # Low but valid - generates warning
            "bedrooms": 1
        }
        
        # In strict mode, warnings affect validity
        result = await strict_validator.validate_property_data(data_with_warnings)
        assert len(result.warnings) > 0
        # Strict mode may reject data with too many warnings
        if len(result.warnings) > 2:
            assert result.is_valid is False
```

2. **Green Phase (1.5 hours)**: Implement processing validator
```python
# src/phoenix_real_estate/collectors/processing/validator.py
"""LLM processing output validation."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.foundation.utils.helpers import is_valid_zipcode


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    confidence_score: float


class ProcessingValidator:
    """Validator for LLM processing outputs."""
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize processing validator."""
        self.config = config
        self.logger = get_logger("llm.processing_validator")
        
        # Initialize Epic 1 validator
        self.base_validator = DataValidator()
        
        # Validation configuration using getattr pattern
        self.min_confidence_threshold = getattr(
            config.settings, "VALIDATION_MIN_CONFIDENCE", 0.7
        )
        self.strict_validation = getattr(
            config.settings, "VALIDATION_STRICT_MODE", False
        )
        
        # Quality thresholds
        self.min_price = getattr(config.settings, "VALIDATION_MIN_PRICE", 10000)
        self.max_price = getattr(config.settings, "VALIDATION_MAX_PRICE", 10000000)
        self.min_sqft = getattr(config.settings, "VALIDATION_MIN_SQFT", 100)
        self.max_sqft = getattr(config.settings, "VALIDATION_MAX_SQFT", 20000)
        
        self.logger.info(
            "Processing validator initialized",
            extra={
                "min_confidence": self.min_confidence_threshold,
                "strict_mode": self.strict_validation
            }
        )
    
    async def validate_property_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate extracted property data."""
        try:
            errors = []
            warnings = []
            confidence_factors = []
            
            # Basic Epic 1 validation
            if not self.base_validator.validate_property_data(data):
                base_errors = self.base_validator.get_errors()
                errors.extend(base_errors)
                confidence_factors.append(0.0)  # Major penalty
            else:
                confidence_factors.append(1.0)  # Bonus for passing
            
            # Address validation
            address_confidence = self._validate_address(data, errors, warnings)
            confidence_factors.append(address_confidence)
            
            # Price validation
            price_confidence = self._validate_price(data, errors, warnings)
            confidence_factors.append(price_confidence)
            
            # Property features validation
            features_confidence = self._validate_features(data, errors, warnings)
            confidence_factors.append(features_confidence)
            
            # Location validation
            location_confidence = self._validate_location(data, errors, warnings)
            confidence_factors.append(location_confidence)
            
            # Data completeness validation
            completeness_confidence = self._validate_completeness(data, warnings)
            confidence_factors.append(completeness_confidence)
            
            # Calculate overall confidence score
            confidence_score = sum(confidence_factors) / len(confidence_factors)
            
            # Determine validity
            is_valid = (
                len(errors) == 0 and 
                confidence_score >= self.min_confidence_threshold
            )
            
            if self.strict_validation:
                # In strict mode, warnings also affect validity
                is_valid = is_valid and len(warnings) <= 2
            
            self.logger.debug(
                "Property data validation completed",
                extra={
                    "is_valid": is_valid,
                    "confidence_score": confidence_score,
                    "error_count": len(errors),
                    "warning_count": len(warnings)
                }
            )
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            self.logger.error(
                "Validation failed with exception",
                extra={"error": str(e)}
            )
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation exception: {str(e)}"],
                warnings=[],
                confidence_score=0.0
            )
    
    def _validate_address(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """Validate address information."""
        confidence = 0.0
        
        # Check address presence and format
        address = data.get("address", "").strip()
        if not address:
            errors.append("Address is required")
            return 0.0
        
        # Basic address format validation
        if len(address) < 5:
            errors.append("Address is too short")
            return 0.1
        
        # Check for common address components
        has_number = any(char.isdigit() for char in address)
        has_street_indicator = any(
            word in address.lower() 
            for word in ["st", "ave", "rd", "dr", "blvd", "ln", "ct", "way", "pl"]
        )
        
        if has_number:
            confidence += 0.5
        else:
            warnings.append("Address missing house number")
        
        if has_street_indicator:
            confidence += 0.5
        else:
            warnings.append("Address missing street type indicator")
        
        return confidence
    
    def _validate_price(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """Validate price information."""
        price = data.get("price")
        
        if price is None:
            warnings.append("Price information missing")
            return 0.3  # Partial confidence for missing optional field
        
        try:
            price_value = float(price)
            
            if price_value < self.min_price:
                errors.append(
                    f"Price ${price_value:,.0f} is below minimum threshold ${self.min_price:,.0f}"
                )
                return 0.0
            
            if price_value > self.max_price:
                errors.append(
                    f"Price ${price_value:,.0f} is above maximum threshold ${self.max_price:,.0f}"
                )
                return 0.0
            
            # Check for reasonable price ranges
            if price_value < 50000:
                warnings.append("Price seems unusually low")
                return 0.7
            
            if price_value > 5000000:
                warnings.append("Price seems unusually high")
                return 0.8
            
            return 1.0  # Price is in reasonable range
            
        except (ValueError, TypeError):
            errors.append("Price is not a valid number")
            return 0.0
    
    def _validate_features(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """Validate property features."""
        confidence = 0.0
        features_checked = 0
        features_valid = 0
        
        # Validate bedrooms
        bedrooms = data.get("bedrooms")
        if bedrooms is not None:
            features_checked += 1
            try:
                bed_count = int(bedrooms)
                if 0 <= bed_count <= 20:
                    features_valid += 1
                else:
                    warnings.append(f"Unusual bedroom count: {bed_count}")
            except (ValueError, TypeError):
                warnings.append("Invalid bedroom count format")
        
        # Validate bathrooms
        bathrooms = data.get("bathrooms")
        if bathrooms is not None:
            features_checked += 1
            try:
                bath_count = float(bathrooms)
                if 0 <= bath_count <= 20:
                    features_valid += 1
                else:
                    warnings.append(f"Unusual bathroom count: {bath_count}")
            except (ValueError, TypeError):
                warnings.append("Invalid bathroom count format")
        
        # Validate square footage
        square_feet = data.get("square_feet")
        if square_feet is not None:
            features_checked += 1
            try:
                sqft = int(square_feet)
                if self.min_sqft <= sqft <= self.max_sqft:
                    features_valid += 1
                else:
                    if sqft < self.min_sqft:
                        warnings.append(f"Square footage {sqft} seems too small")
                    else:
                        warnings.append(f"Square footage {sqft} seems too large")
            except (ValueError, TypeError):
                warnings.append("Invalid square footage format")
        
        # Validate year built
        year_built = data.get("year_built")
        if year_built is not None:
            features_checked += 1
            try:
                year = int(year_built)
                current_year = datetime.now().year
                if 1800 <= year <= current_year + 2:  # Allow for under construction
                    features_valid += 1
                else:
                    warnings.append(f"Unusual year built: {year}")
            except (ValueError, TypeError):
                warnings.append("Invalid year built format")
        
        # Calculate confidence based on valid features
        if features_checked > 0:
            confidence = features_valid / features_checked
        else:
            confidence = 0.5  # Neutral if no features to check
        
        return confidence
    
    def _validate_location(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """Validate location information."""
        confidence = 0.0
        
        # Validate ZIP code
        zip_code = data.get("zip_code", "").strip()
        if zip_code:
            if is_valid_zipcode(zip_code):
                confidence += 0.4
                
                # Check if it's in our target area (Phoenix area ZIP codes)
                phoenix_area_prefixes = ["850", "851", "852", "853"]
                if any(zip_code.startswith(prefix) for prefix in phoenix_area_prefixes):
                    confidence += 0.1
                else:
                    warnings.append(f"ZIP code {zip_code} is outside Phoenix area")
            else:
                warnings.append(f"Invalid ZIP code format: {zip_code}")
        else:
            warnings.append("ZIP code missing")
        
        # Validate city
        city = data.get("city", "").strip()
        if city:
            confidence += 0.3
            
            # Check for common Phoenix area cities
            phoenix_cities = [
                "phoenix", "scottsdale", "tempe", "mesa", "chandler", "glendale",
                "peoria", "gilbert", "surprise", "avondale", "goodyear"
            ]
            if city.lower() in phoenix_cities:
                confidence += 0.1
            else:
                warnings.append(f"City '{city}' is not a common Phoenix area city")
        else:
            warnings.append("City information missing")
        
        # Validate state
        state = data.get("state", "").strip().upper()
        if state == "AZ":
            confidence += 0.1
        elif state:
            warnings.append(f"Property is in {state}, not Arizona")
        else:
            warnings.append("State information missing")
        
        return min(confidence, 1.0)
    
    def _validate_completeness(self, data: Dict[str, Any], warnings: List[str]) -> float:
        """Validate data completeness."""
        # Define required and optional fields
        required_fields = ["address"]
        important_fields = ["price", "bedrooms", "bathrooms", "square_feet"]
        optional_fields = ["year_built", "lot_size_sqft", "property_type", "description"]
        
        # Check required fields
        missing_required = [field for field in required_fields if not data.get(field)]
        if missing_required:
            warnings.extend([f"Missing required field: {field}" for field in missing_required])
            return 0.0
        
        # Check important fields
        present_important = [field for field in important_fields if data.get(field) is not None]
        important_completeness = len(present_important) / len(important_fields)
        
        # Check optional fields
        present_optional = [field for field in optional_fields if data.get(field) is not None]
        optional_completeness = len(present_optional) / len(optional_fields)
        
        # Calculate weighted completeness score
        completeness_score = (
            1.0 +  # Required fields bonus (already checked above)
            important_completeness * 0.8 +
            optional_completeness * 0.2
        ) / 2.0
        
        # Add warnings for missing important fields
        missing_important = [field for field in important_fields if not data.get(field)]
        if missing_important:
            warnings.extend([f"Missing important field: {field}" for field in missing_important])
        
        return min(completeness_score, 1.0)
```

3. **Refactor Phase (1 hour)**: Add advanced validation features
```python
# Add to ProcessingValidator class

    async def validate_batch(
        self,
        data_list: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Validate multiple property data entries."""
        results = []
        
        for data in data_list:
            result = await self.validate_property_data(data)
            results.append(result)
        
        # Log batch statistics
        valid_count = sum(1 for r in results if r.is_valid)
        avg_confidence = sum(r.confidence_score for r in results) / len(results) if results else 0
        
        self.logger.info(
            "Batch validation completed",
            extra={
                "total_items": len(data_list),
                "valid_count": valid_count,
                "validation_rate": valid_count / len(data_list) if data_list else 0,
                "average_confidence": avg_confidence
            }
        )
        
        return results
    
    def get_validation_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """Get a summary of validation result."""
        return {
            "is_valid": result.is_valid,
            "confidence_score": round(result.confidence_score, 3),
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
            "top_errors": result.errors[:3],  # First 3 errors
            "top_warnings": result.warnings[:3],  # First 3 warnings
            "quality_rating": self._get_quality_rating(result.confidence_score)
        }
    
    def _get_quality_rating(self, confidence_score: float) -> str:
        """Convert confidence score to quality rating."""
        if confidence_score >= 0.9:
            return "Excellent"
        elif confidence_score >= 0.8:
            return "Good"
        elif confidence_score >= 0.7:
            return "Fair"
        elif confidence_score >= 0.5:
            return "Poor"
        else:
            return "Very Poor"
    
    def suggest_improvements(self, data: Dict[str, Any], result: ValidationResult) -> List[str]:
        """Suggest improvements for data quality."""
        suggestions = []
        
        # Check for missing critical fields
        critical_fields = ["address", "price", "city", "state", "zip_code"]
        missing_critical = [f for f in critical_fields if not data.get(f)]
        
        if missing_critical:
            suggestions.append(
                f"Add missing critical fields: {', '.join(missing_critical)}"
            )
        
        # Check for low-quality fields
        if data.get("price") and data["price"] < 100000:
            suggestions.append("Verify price - seems unusually low for Phoenix area")
        
        if not data.get("bedrooms") and not data.get("bathrooms"):
            suggestions.append("Add bedroom and bathroom counts for better property details")
        
        if not data.get("square_feet"):
            suggestions.append("Add square footage for property valuation")
        
        # Check validation warnings
        for warning in result.warnings[:3]:
            if "outside Phoenix area" in warning:
                suggestions.append("Verify property location - may be outside target area")
            elif "missing" in warning.lower():
                field = warning.split(":")[-1].strip() if ":" in warning else "data"
                suggestions.append(f"Consider adding {field}")
        
        return suggestions
```

**Test-First Checkpoints**:
- [ ] All validator tests written before implementation
- [ ] Tests cover all validation scenarios
- [ ] Minimal implementation passes tests
- [ ] Confidence scoring properly tested
- [ ] Strict mode behavior verified
- [ ] Integration with Epic 1 validator confirmed

---

### Day 2.5: Cost Management & Caching

#### TASK-06-004A: Redis Cache Implementation
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P0 - Critical for Budget  
**Dependencies**: TASK-06-002

**Objective**: Implement Redis caching layer to reduce LLM API costs by 30%.

**TDD Process**:

1. **Red Phase (1 hour)**: Write cache behavior tests
```python
# tests/processors/test_cache_manager.py
import pytest
import json
import hashlib
from unittest.mock import Mock, AsyncMock
from phoenix_real_estate.processors.cache.cache_manager import CacheManager

class TestCacheManager:
    """Test-driven development of caching layer."""
    
    @pytest.fixture
    def sample_property(self):
        return {
            "address": "123 Main St Phoenix AZ 85031",
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1500,
            "price": 350000,
            "property_type": "single_family"
        }
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock(return_value=True)
        mock.keys = AsyncMock(return_value=[])
        mock.info = AsyncMock(return_value={
            'used_memory': 1024 * 1024 * 10,  # 10MB
            'keyspace_hits': 100,
            'keyspace_misses': 50
        })
        return mock
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, sample_property):
        """Test deterministic cache key generation."""
        manager = CacheManager()
        
        # Same data should produce same key
        key1 = manager._generate_cache_key(sample_property, "description")
        key2 = manager._generate_cache_key(sample_property, "description")
        assert key1 == key2
        
        # Different operations should produce different keys
        key3 = manager._generate_cache_key(sample_property, "analysis")
        assert key1 != key3
        
        # Key should have expected format
        assert key1.startswith("llm:description:")
        assert len(key1) == len("llm:description:") + 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, mock_redis, sample_property):
        """Test cache miss returns None."""
        manager = CacheManager()
        manager.redis = mock_redis
        
        result = await manager.get(sample_property, "description")
        assert result is None
        mock_redis.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_hit_returns_data(self, mock_redis, sample_property):
        """Test cache hit returns stored data."""
        cached_data = {"description": "Beautiful home", "tokens": 150}
        mock_redis.get.return_value = json.dumps(cached_data)
        
        manager = CacheManager()
        manager.redis = mock_redis
        
        result = await manager.get(sample_property, "description")
        assert result == cached_data
    
    @pytest.mark.asyncio
    async def test_cache_set_with_ttl(self, mock_redis, sample_property):
        """Test caching with TTL."""
        manager = CacheManager(ttl_hours=24)
        manager.redis = mock_redis
        
        response = {"description": "Lovely property", "tokens": 200}
        await manager.set(sample_property, "description", response)
        
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 86400  # 24 hours in seconds
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, mock_redis):
        """Test cache statistics reporting."""
        manager = CacheManager()
        manager.redis = mock_redis
        
        stats = await manager.get_stats()
        
        assert stats['memory_used_mb'] == 10.0
        assert stats['hit_rate'] == 100 / 150  # 66.67%
        assert stats['ttl_hours'] == 24
```

2. **Green Phase (1.5 hours)**: Implement caching functionality
```python
# src/phoenix_real_estate/processors/cache/cache_manager.py
import json
import hashlib
from datetime import timedelta
from typing import Dict, Any, Optional
from redis import asyncio as aioredis
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)

class CacheManager:
    """Manages LLM response caching for cost reduction."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_hours: int = 24):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self.ttl = timedelta(hours=ttl_hours)
        
    def _generate_cache_key(self, property_data: Dict[str, Any], operation: str) -> str:
        """Generate deterministic cache key from property data."""
        cache_data = {
            'address': property_data.get('address'),
            'bedrooms': property_data.get('bedrooms'),
            'bathrooms': property_data.get('bathrooms'),
            'square_feet': property_data.get('square_feet'),
            'price': property_data.get('price'),
            'property_type': property_data.get('property_type'),
            'operation': operation
        }
        
        data_str = json.dumps(cache_data, sort_keys=True)
        return f"llm:{operation}:{hashlib.md5(data_str.encode()).hexdigest()}"
    
    async def get(self, property_data: Dict[str, Any], operation: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached LLM response if available."""
        cache_key = self._generate_cache_key(property_data, operation)
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {operation}: {cache_key[:50]}...")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set(self, property_data: Dict[str, Any], operation: str, response: Dict[str, Any]):
        """Cache LLM response with TTL."""
        cache_key = self._generate_cache_key(property_data, operation)
        
        try:
            await self.redis.setex(
                cache_key,
                int(self.ttl.total_seconds()),
                json.dumps(response)
            )
            logger.info(f"Cached {operation} response: {cache_key[:50]}...")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
```

3. **Refactor Phase (30 min)**: Add monitoring and optimization

**Acceptance Criteria**:
- [ ] Cache hit rate > 30% after warm-up
- [ ] TTL configurable per operation type
- [ ] Cache size monitoring implemented
- [ ] Graceful degradation on Redis failure

---

#### TASK-06-004B: Cost Tracking & Budget Control
**Assignee**: Backend Developer  
**Duration**: 2 hours  
**Priority**: P0 - Critical for Budget  
**Dependencies**: TASK-06-002

**Objective**: Implement real-time cost tracking and budget enforcement to stay within $19/month.

**TDD Process**:

1. **Red Phase (45 min)**: Write cost tracking tests
```python
# tests/processors/test_cost_tracker.py
import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch
from phoenix_real_estate.processors.cost.cost_tracker import CostTracker, BudgetExceededException

class TestCostTracker:
    """Test-driven development of cost tracking."""
    
    @pytest.fixture
    def tracker(self):
        return CostTracker(daily_budget=0.63)  # $19/month
    
    def test_initial_state(self, tracker):
        """Test initial state of cost tracker."""
        assert tracker.daily_budget == 0.63
        assert tracker.get_daily_cost() == 0.0
        assert tracker.get_remaining_budget() == 0.63
    
    def test_record_openai_usage(self, tracker):
        """Test recording OpenAI API usage."""
        # GPT-3.5-turbo: $0.50/1M input, $1.50/1M output
        tracker.record_usage(
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500
        )
        
        expected_cost = (1000 * 0.50 / 1_000_000) + (500 * 1.50 / 1_000_000)
        assert tracker.get_daily_cost() == pytest.approx(expected_cost, rel=1e-6)
    
    def test_budget_exceeded_exception(self, tracker):
        """Test budget exceeded exception."""
        # Record usage that exceeds budget
        with pytest.raises(BudgetExceededException) as exc_info:
            tracker.record_usage(
                provider="openai",
                model="gpt-4o",
                input_tokens=200_000,  # Would cost $1.00
                output_tokens=100_000  # Would cost $2.00
            )
        
        assert "Daily budget $0.63 exceeded" in str(exc_info.value)
    
    def test_tiered_model_selection(self, tracker):
        """Test model selection based on remaining budget."""
        # Near budget limit
        tracker._daily_costs[date.today()] = 0.60
        
        model = tracker.select_model_for_budget(property_value=500_000)
        assert model == "ollama/llama3.3:70b"  # Free fallback
        
        # Plenty of budget
        tracker._daily_costs[date.today()] = 0.10
        model = tracker.select_model_for_budget(property_value=500_000)
        assert model == "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_daily_summary(self, tracker):
        """Test daily cost summary generation."""
        # Record some usage
        tracker.record_usage("openai", "gpt-3.5-turbo", 10_000, 5_000)
        tracker.record_usage("ollama", "llama3.3:70b", 50_000, 25_000)
        
        summary = tracker.get_daily_summary()
        
        assert summary['date'] == date.today()
        assert summary['total_cost'] > 0
        assert summary['budget_remaining'] < 0.63
        assert summary['properties_processed'] == 2
        assert 'cost_by_model' in summary
```

2. **Green Phase (1 hour)**: Implement cost tracking
```python
# src/phoenix_real_estate/processors/cost/cost_tracker.py
from datetime import date, datetime
from typing import Dict, Any, Optional
from collections import defaultdict
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)

class BudgetExceededException(Exception):
    """Raised when daily budget is exceeded."""
    pass

class CostTracker:
    """Tracks LLM API costs and enforces budget limits."""
    
    # Pricing per 1M tokens (input/output)
    PRICING = {
        "openai": {
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "gpt-4o": {"input": 5.00, "output": 20.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60}
        },
        "anthropic": {
            "claude-3.5-sonnet": {"input": 3.00, "output": 15.00}
        },
        "ollama": {
            "llama3.3:70b": {"input": 0.0, "output": 0.0},
            "mistral": {"input": 0.0, "output": 0.0}
        }
    }
    
    def __init__(self, daily_budget: float = 0.63):
        self.daily_budget = daily_budget
        self._daily_costs: Dict[date, float] = defaultdict(float)
        self._model_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
    def record_usage(self, provider: str, model: str, input_tokens: int, output_tokens: int):
        """Record token usage and calculate cost."""
        if provider not in self.PRICING or model not in self.PRICING[provider]:
            logger.warning(f"Unknown model {provider}/{model}, assuming zero cost")
            return
            
        pricing = self.PRICING[provider][model]
        cost = (input_tokens * pricing["input"] / 1_000_000) + \
               (output_tokens * pricing["output"] / 1_000_000)
        
        today = date.today()
        self._daily_costs[today] += cost
        
        # Track usage by model
        model_key = f"{provider}/{model}"
        self._model_usage[model_key]["count"] += 1
        self._model_usage[model_key]["input_tokens"] += input_tokens
        self._model_usage[model_key]["output_tokens"] += output_tokens
        
        if self._daily_costs[today] > self.daily_budget:
            raise BudgetExceededException(
                f"Daily budget ${self.daily_budget:.2f} exceeded: "
                f"${self._daily_costs[today]:.2f}"
            )
        
        logger.info(
            f"Recorded {model} usage: {input_tokens} in, {output_tokens} out, "
            f"cost=${cost:.4f}, daily total=${self._daily_costs[today]:.2f}"
        )
    
    def select_model_for_budget(self, property_value: float) -> str:
        """Select appropriate model based on remaining budget."""
        remaining = self.get_remaining_budget()
        
        # If near budget limit, use free models
        if remaining < 0.05:  # Less than $0.05 remaining
            return "ollama/llama3.3:70b"
        
        # Otherwise use tiered selection
        if property_value < 200_000:
            return "ollama/llama3.3:70b"
        elif property_value < 500_000 and remaining > 0.10:
            return "gpt-3.5-turbo"
        elif property_value >= 500_000 and remaining > 0.20:
            return "gpt-4o-mini"
        else:
            return "gpt-3.5-turbo"  # Default fallback
```

3. **Refactor Phase (15 min)**: Add monitoring integration

**Acceptance Criteria**:
- [ ] Real-time cost tracking per API call
- [ ] Daily budget enforcement with exceptions
- [ ] Model selection based on budget remaining
- [ ] Cost reporting and analytics
- [ ] Integration with monitoring system

---

### Day 3: Integration & Pipeline

#### TASK-06-005: Processing Pipeline
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-06-002, TASK-06-003, TASK-06-004

**Objective**: Implement the end-to-end processing pipeline that orchestrates data flow from collectors through LLM processing to database storage.

**TDD Process**:

1. **Red Phase (1 hour)**: Write comprehensive pipeline tests
```python
# tests/processors/test_processing_pipeline.py

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from phoenix_real_estate.processors.pipeline import ProcessingPipeline
from phoenix_real_estate.processors.llm.ollama_client import OllamaClient
from phoenix_real_estate.processors.extractors.property_extractor import PropertyExtractor
from phoenix_real_estate.processors.validators.processing_validator import ProcessingValidator, ValidationResult

class TestProcessingPipeline:
    """Test-driven development of processing pipeline."""
    
    @pytest.fixture
    def mock_components(self):
        """Mock pipeline components."""
        # Mock Ollama client
        mock_ollama = Mock(spec=OllamaClient)
        mock_ollama.health_check = AsyncMock(return_value=True)
        
        # Mock extractor
        mock_extractor = Mock(spec=PropertyExtractor)
        mock_extractor.extract_from_html = AsyncMock(return_value={
            "address": "123 Test St",
            "price": 450000,
            "confidence": 0.95
        })
        
        # Mock validator
        mock_validator = Mock(spec=ProcessingValidator)
        mock_validator.validate_property_data = AsyncMock(return_value=ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            confidence_score=0.9
        ))
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save_processed_property = AsyncMock(return_value=True)
        mock_repo.save_processing_error = AsyncMock(return_value=True)
        
        return {
            'ollama_client': mock_ollama,
            'extractor': mock_extractor,
            'validator': mock_validator,
            'repository': mock_repo
        }
    
    async def test_pipeline_initialization(self, mock_components):
        """Test pipeline initializes with correct components."""
        pipeline = ProcessingPipeline(**mock_components)
        
        assert pipeline.ollama_client == mock_components['ollama_client']
        assert pipeline.extractor == mock_components['extractor']
        assert pipeline.validator == mock_components['validator']
        assert pipeline.repository == mock_components['repository']
        assert pipeline.metrics is not None
    
    async def test_pipeline_processes_single_property(self, mock_components):
        """Pipeline should process a single property end-to-end."""
        pipeline = ProcessingPipeline(**mock_components)
        
        raw_property = {
            '_id': 'test123',
            'html_content': '<div>Property HTML</div>',
            'source': 'phoenix_mls',
            'collected_at': datetime.now()
        }
        
        result = await pipeline.process_property(raw_property)
        
        assert result is not None
        assert result['status'] == 'processed'
        assert result['extracted_data']['address'] == "123 Test St"
        assert result['validation_score'] == 0.9
        assert 'processed_at' in result
        
        # Verify component interactions
        mock_components['extractor'].extract_from_html.assert_called_once()
        mock_components['validator'].validate_property_data.assert_called_once()
        mock_components['repository'].save_processed_property.assert_called_once()
    
    async def test_pipeline_handles_extraction_failure(self, mock_components):
        """Pipeline should handle extraction failures gracefully."""
        # Configure extractor to fail
        mock_components['extractor'].extract_from_html = AsyncMock(return_value=None)
        
        pipeline = ProcessingPipeline(**mock_components)
        
        raw_property = {
            '_id': 'test456',
            'html_content': '<div>Invalid HTML</div>',
            'source': 'phoenix_mls'
        }
        
        result = await pipeline.process_property(raw_property)
        
        assert result['status'] == 'failed'
        assert 'error' in result
        assert result['raw_id'] == 'test456'
        
        # Should save error record
        mock_components['repository'].save_processing_error.assert_called_once()
    
    async def test_pipeline_handles_validation_failure(self, mock_components):
        """Pipeline should handle validation failures."""
        # Configure validator to fail
        mock_components['validator'].validate_property_data = AsyncMock(
            return_value=ValidationResult(
                is_valid=False,
                errors=["Price too low"],
                warnings=[],
                confidence_score=0.3
            )
        )
        
        pipeline = ProcessingPipeline(**mock_components)
        
        result = await pipeline.process_property({
            '_id': 'test789',
            'html_content': '<div>Test</div>'
        })
        
        # Should still save but mark as low quality
        assert result['status'] == 'processed'
        assert result['validation_passed'] is False
        assert result['validation_score'] == 0.3
    
    async def test_pipeline_batch_processing(self, mock_components):
        """Pipeline should efficiently process batches."""
        pipeline = ProcessingPipeline(**mock_components)
        
        properties = [
            {'_id': f'prop{i}', 'html_content': f'<div>Property {i}</div>'}
            for i in range(10)
        ]
        
        results = await pipeline.process_batch(properties, max_concurrent=3)
        
        assert len(results) == 10
        assert all(r['status'] in ['processed', 'failed'] for r in results)
        
        # Should respect concurrency limit
        # Verify by checking call count doesn't exceed batch size
        assert mock_components['extractor'].extract_from_html.call_count == 10
```

2. **Green Phase (1.5 hours)**: Implement processing pipeline
```python
# src/phoenix_real_estate/processors/pipeline.py
"""End-to-end LLM processing pipeline."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from phoenix_real_estate.foundation import get_logger
from phoenix_real_estate.processors.llm.ollama_client import OllamaClient
from phoenix_real_estate.processors.extractors.property_extractor import PropertyExtractor
from phoenix_real_estate.processors.validators.processing_validator import ProcessingValidator

logger = get_logger(__name__)

class ProcessingMetrics:
    """Track pipeline processing metrics."""
    
    def __init__(self):
        self.processed_count = 0
        self.failed_count = 0
        self.total_processing_time = 0.0
        self.start_times = {}
    
    def record_processing_start(self, property_id: str):
        """Record start of processing."""
        self.start_times[property_id] = datetime.now()
    
    def record_processing_success(self, property_id: str, processing_time: float):
        """Record successful processing."""
        self.processed_count += 1
        self.total_processing_time += processing_time
        self.start_times.pop(property_id, None)
    
    def record_processing_failure(self, property_id: str, error: str):
        """Record processing failure."""
        self.failed_count += 1
        self.start_times.pop(property_id, None)

class ProcessingPipeline:
    """Orchestrates end-to-end property processing."""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        extractor: PropertyExtractor,
        validator: ProcessingValidator,
        repository: Any
    ):
        self.ollama_client = ollama_client
        self.extractor = extractor
        self.validator = validator
        self.repository = repository
        self.metrics = ProcessingMetrics()
        
    async def process_property(self, raw_property: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single property through the pipeline."""
        property_id = raw_property['_id']
        
        try:
            # Track processing
            self.metrics.record_processing_start(property_id)
            start_time = datetime.now()
            
            logger.info(f"Processing property {property_id}")
            
            # 1. Extract data using LLM
            extracted_data = await self.extractor.extract_from_html(
                raw_property['html_content'],
                source=raw_property.get('source', 'unknown')
            )
            
            if not extracted_data:
                raise ValueError("Extraction failed - no data returned")
            
            # 2. Validate extracted data
            validation_result = await self.validator.validate_property_data(extracted_data)
            
            # 3. Prepare processed property
            processed_property = {
                '_id': property_id,
                'raw_id': property_id,
                'extracted_data': extracted_data,
                'validation_score': validation_result.confidence_score,
                'validation_passed': validation_result.is_valid,
                'validation_errors': validation_result.errors,
                'validation_warnings': validation_result.warnings,
                'processed_at': datetime.now(),
                'processing_metadata': {
                    'extraction_method': extracted_data.get('extraction_method', 'llm'),
                    'confidence': extracted_data.get('confidence', 0.0),
                    'model_used': getattr(self.ollama_client, 'model_name', 'unknown'),
                    'processing_time': (datetime.now() - start_time).total_seconds()
                },
                'status': 'processed'
            }
            
            # 4. Save to database
            await self.repository.save_processed_property(processed_property)
            
            # Record success
            processing_time = (datetime.now() - start_time).total_seconds()
            self.metrics.record_processing_success(property_id, processing_time)
            
            logger.info(f"Successfully processed property {property_id}")
            return processed_property
            
        except Exception as e:
            logger.error(f"Failed to process property {property_id}: {e}")
            
            # Record failure
            self.metrics.record_processing_failure(property_id, str(e))
            
            # Save error state
            error_record = {
                '_id': property_id,
                'raw_id': property_id,
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now()
            }
            
            await self.repository.save_processing_error(error_record)
            return error_record
    
    async def process_batch(
        self,
        properties: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Process multiple properties concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_limit(prop):
            async with semaphore:
                return await self.process_property(prop)
        
        tasks = [process_with_limit(prop) for prop in properties]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error records
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_record = {
                    '_id': properties[i]['_id'],
                    'status': 'failed',
                    'error': str(result)
                }
                processed_results.append(error_record)
            else:
                processed_results.append(result)
        
        return processed_results
```

3. **Refactor Phase (30 min)**: Add monitoring and optimization
```python
# Enhanced pipeline with retry and monitoring
class ProcessingPipeline:
    """Enhanced pipeline with retry and monitoring."""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        extractor: PropertyExtractor,
        validator: ProcessingValidator,
        repository: Any,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.ollama_client = ollama_client
        self.extractor = extractor
        self.validator = validator
        self.repository = repository
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.metrics = ProcessingMetrics()
    
    async def process_property_with_retry(
        self,
        raw_property: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process property with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await self.process_property(raw_property)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {raw_property['_id']}: {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise
```

**Test-First Checkpoints**:
- [ ] All pipeline tests written before implementation
- [ ] Tests verify end-to-end processing flow
- [ ] Error handling properly tested
- [ ] Batch processing verified
- [ ] Metrics tracking functional

---

#### TASK-06-006: Error Handling & Recovery
**Assignee**: Backend Developer  
**Duration**: 2 hours  
**Priority**: P0 - Critical  
**Dependencies**: TASK-06-005

**Objective**: Implement comprehensive error handling and recovery mechanisms for the LLM processing system.

**TDD Process**:

1. **Red Phase (45 min)**: Write error handling tests
```python
# tests/processors/test_error_handling.py

import pytest
import asyncio
from unittest.mock import Mock, patch
from phoenix_real_estate.processors.error_handler import ProcessingErrorHandler
from phoenix_real_estate.processors.exceptions import (
    OllamaConnectionError,
    ExtractionError,
    ValidationError,
    RecoverableError,
    UnrecoverableError
)

class TestErrorHandling:
    """Test-driven error handling implementation."""
    
    async def test_handle_ollama_connection_error(self):
        """Should handle Ollama connection failures gracefully."""
        handler = ProcessingErrorHandler()
        
        error = OllamaConnectionError("Cannot connect to Ollama")
        recovery_strategy = await handler.handle_error(error)
        
        assert recovery_strategy.action == 'fallback'
        assert recovery_strategy.fallback_method == 'regex_extraction'
        assert recovery_strategy.should_retry is False
    
    async def test_handle_transient_errors_with_retry(self):
        """Should retry transient errors with backoff."""
        handler = ProcessingErrorHandler(max_retries=3)
        
        error = RecoverableError("Temporary network issue")
        
        # First attempt
        strategy = await handler.handle_error(error, attempt=1)
        assert strategy.action == 'retry'
        assert strategy.delay == 1.0  # Exponential backoff
        
        # Final attempt
        strategy = await handler.handle_error(error, attempt=3)
        assert strategy.action == 'fail'  # No more retries
    
    async def test_circuit_breaker_pattern(self):
        """Should implement circuit breaker for repeated failures."""
        handler = ProcessingErrorHandler(
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60
        )
        
        # Simulate repeated failures
        for i in range(5):
            await handler.handle_error(
                OllamaConnectionError("Connection failed"),
                property_id=f"prop{i}"
            )
        
        # Circuit should be open
        assert handler.is_circuit_open('ollama')
        
        # New requests should fail fast
        strategy = await handler.handle_error(
            OllamaConnectionError("Another failure"),
            property_id="prop6"
        )
        assert strategy.action == 'fail_fast'
```

2. **Green Phase (1 hour)**: Implement error handling
```python
# src/phoenix_real_estate/processors/error_handler.py

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
from phoenix_real_estate.foundation import get_logger

logger = get_logger(__name__)

@dataclass
class RecoveryStrategy:
    """Defines how to recover from an error."""
    action: str  # 'retry', 'fallback', 'fail', 'fail_fast'
    delay: float = 0.0
    fallback_method: Optional[str] = None
    should_retry: bool = False
    reason: Optional[str] = None

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, threshold: int = 5, timeout: int = 60):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_counts = defaultdict(int)
        self.last_failure_times = {}
        self.circuit_states = {}
    
    def record_failure(self, service: str):
        """Record a failure for a service."""
        self.failure_counts[service] += 1
        self.last_failure_times[service] = time.time()
        
        if self.failure_counts[service] >= self.threshold:
            self.circuit_states[service] = 'open'
            logger.warning(f"Circuit breaker opened for {service}")
    
    def is_open(self, service: str) -> bool:
        """Check if circuit is open for a service."""
        state = self.circuit_states.get(service, 'closed')
        
        if state == 'open':
            # Check if timeout has passed
            last_failure = self.last_failure_times.get(service, 0)
            if time.time() - last_failure > self.timeout:
                self.circuit_states[service] = 'half_open'
                return False
            return True
        
        return False

class ProcessingErrorHandler:
    """Handles errors during property processing."""
    
    def __init__(
        self,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker(
            threshold=circuit_breaker_threshold,
            timeout=circuit_breaker_timeout
        )
        self.retry_delays = [1.0, 2.0, 4.0]  # Exponential backoff
    
    async def handle_error(
        self,
        error: Exception,
        attempt: int = 1,
        property_id: Optional[str] = None
    ) -> RecoveryStrategy:
        """Determine recovery strategy for an error."""
        # Check circuit breaker first
        if isinstance(error, OllamaConnectionError):
            if self.is_circuit_open('ollama'):
                return RecoveryStrategy(
                    action='fail_fast',
                    reason='circuit_breaker_open'
                )
            
            # Record failure
            self.circuit_breaker.record_failure('ollama')
            
            # Use fallback for connection errors
            return RecoveryStrategy(
                action='fallback',
                fallback_method='regex_extraction',
                should_retry=False
            )
        
        # Handle recoverable errors with retry
        if isinstance(error, RecoverableError):
            if attempt < self.max_retries:
                delay = self.retry_delays[attempt - 1]
                return RecoveryStrategy(
                    action='retry',
                    delay=delay,
                    should_retry=True
                )
            else:
                return RecoveryStrategy(action='fail')
        
        # Default strategy
        return RecoveryStrategy(action='fail')
    
    def is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open for a service."""
        return self.circuit_breaker.is_open(service)
```

3. **Refactor Phase (15 min)**: Add telemetry
```python
# Enhanced error handler with telemetry
class ErrorMetrics:
    """Track error metrics."""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.recovery_attempts = defaultdict(int)
        self.recovery_successes = defaultdict(int)
    
    def record_error(self, error_type: str, property_id: str, attempt: int, context: Dict):
        """Record error occurrence."""
        self.error_counts[error_type] += 1
    
    def record_recovery_attempt(self, property_id: str, strategy: str, success: bool):
        """Record recovery attempt."""
        self.recovery_attempts[strategy] += 1
        if success:
            self.recovery_successes[strategy] += 1
```

**Test-First Checkpoints**:
- [ ] All error handling tests written first
- [ ] Circuit breaker pattern tested
- [ ] Retry logic verified
- [ ] Fallback mechanisms tested
- [ ] Telemetry functional

---

#### TASK-06-007: Epic 1 Integration
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P0 - Critical  
**Dependencies**: TASK-06-005, TASK-06-006

**Objective**: Integrate the LLM processing system with Epic 1's foundation infrastructure.

**TDD Process**:

1. **Red Phase (1 hour)**: Write integration tests
```python
# tests/integration/test_epic1_integration.py

import pytest
from phoenix_real_estate.foundation.config import ConfigProvider
from phoenix_real_estate.foundation.database import DatabaseManager
from phoenix_real_estate.models import RawProperty, ProcessedProperty
from phoenix_real_estate.processors.pipeline import ProcessingPipeline

class TestEpic1Integration:
    """Test integration with Epic 1 foundation."""
    
    @pytest.fixture
    async def foundation_setup(self):
        """Set up Epic 1 foundation components."""
        config = ConfigProvider()
        db_manager = DatabaseManager(config)
        await db_manager.initialize()
        
        yield {
            'config': config,
            'db_manager': db_manager
        }
        
        await db_manager.close()
    
    async def test_pipeline_uses_foundation_config(self, foundation_setup):
        """Pipeline should use Epic 1 configuration."""
        config = foundation_setup['config']
        
        pipeline = ProcessingPipeline.from_config(config)
        
        # Should use configured values
        assert pipeline.ollama_client.base_url == getattr(config, 'ollama', {}).get('base_url')
        assert pipeline.max_concurrent == getattr(config, 'processing', {}).get('max_concurrent', 5)
    
    async def test_pipeline_saves_with_epic1_models(self, foundation_setup):
        """Pipeline should use Epic 1 database models."""
        db_manager = foundation_setup['db_manager']
        pipeline = ProcessingPipeline.from_database(db_manager)
        
        # Create raw property using Epic 1 model
        raw_property = RawProperty(
            source='phoenix_mls',
            external_id='MLS123',
            data={'html_content': '<div>Test property</div>'},
            collected_at=datetime.now()
        )
        
        # Save using Epic 1 repository
        await db_manager.properties.save_raw(raw_property)
        
        # Process through pipeline
        result = await pipeline.process_property(raw_property.to_dict())
        
        # Verify saved as ProcessedProperty model
        processed = await db_manager.properties.get_processed(raw_property.id)
        assert isinstance(processed, ProcessedProperty)
```

2. **Green Phase (1.5 hours)**: Implement integration
```python
# src/phoenix_real_estate/processors/pipeline.py

from phoenix_real_estate.foundation.config import ConfigProvider
from phoenix_real_estate.foundation.database import DatabaseManager
from phoenix_real_estate.foundation import get_logger
from phoenix_real_estate.models import ProcessedProperty
from phoenix_real_estate.repositories import PropertyRepository

class ProcessingPipeline:
    """Pipeline integrated with Epic 1 foundation."""
    
    @classmethod
    def from_config(cls, config: ConfigProvider) -> 'ProcessingPipeline':
        """Create pipeline from Epic 1 configuration."""
        # Initialize components from config
        ollama_client = OllamaClient(
            base_url=getattr(config, 'ollama', {}).get('base_url', 'http://localhost:11434'),
            model_name=getattr(config, 'ollama', {}).get('model', 'llama3.2'),
            timeout=getattr(config, 'ollama', {}).get('timeout', 30.0)
        )
        
        extractor = PropertyExtractor(ollama_client)
        validator = ProcessingValidator()
        
        # Get processing config
        processing_config = getattr(config, 'processing', {})
        
        return cls(
            ollama_client=ollama_client,
            extractor=extractor,
            validator=validator,
            repository=None,
            max_concurrent=processing_config.get('max_concurrent', 5),
            batch_size=processing_config.get('batch_size', 50)
        )
    
    @classmethod
    def from_database(cls, db_manager: DatabaseManager) -> 'ProcessingPipeline':
        """Create pipeline with Epic 1 database integration."""
        config = db_manager.config
        pipeline = cls.from_config(config)
        
        # Set up repository
        pipeline.repository = PropertyRepository(db_manager)
        
        return pipeline
```

3. **Refactor Phase (30 min)**: Configuration schema
```python
# src/phoenix_real_estate/processors/config_schema.py

from pydantic import BaseModel, Field
from typing import Optional

class OllamaConfig(BaseModel):
    """Ollama configuration schema."""
    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="llama3.2")
    timeout: float = Field(default=30.0)

class ProcessingConfig(BaseModel):
    """Processing configuration schema."""
    max_concurrent: int = Field(default=5, ge=1, le=20)
    batch_size: int = Field(default=50, ge=1, le=100)
```

**Test-First Checkpoints**:
- [ ] Integration tests written first
- [ ] Configuration properly loaded
- [ ] Database models integrated
- [ ] Logging follows Epic 1 patterns
- [ ] Repository pattern implemented

---

### Day 4: Testing & Production

#### TASK-06-008: Comprehensive Test Suite
**Assignee**: QA Engineer  
**Duration**: 4 hours  
**Priority**: P1 - Important  
**Dependencies**: TASK-06-007

**Objective**: Create comprehensive test coverage for the LLM processing system.

**Test Categories**:

1. **Unit Tests** (2 hours)
   - 100% coverage for all components
   - Mock external dependencies
   - Test edge cases

2. **Integration Tests** (1 hour)
   - End-to-end processing flow
   - Database integration
   - Error recovery scenarios

3. **Performance Tests** (1 hour)
   - Processing speed benchmarks
   - Memory usage monitoring
   - Concurrent processing limits

**Test Implementation**:
```python
# tests/performance/test_processing_benchmarks.py

import pytest
import time
import asyncio
from phoenix_real_estate.processors.pipeline import ProcessingPipeline

@pytest.mark.benchmark
async def test_single_property_processing_speed(benchmark, pipeline):
    """Single property must process in <2 seconds."""
    sample_property = create_sample_property()
    
    result = await benchmark(pipeline.process_property, sample_property)
    assert benchmark.stats['mean'] < 2.0  # 2 seconds

@pytest.mark.benchmark
async def test_batch_processing_throughput(benchmark, pipeline):
    """Must process 100 properties in <3 minutes."""
    properties = [create_sample_property() for _ in range(100)]
    
    result = await benchmark(pipeline.process_batch, properties)
    assert benchmark.stats['mean'] < 180  # 3 minutes
```

---

#### TASK-06-009: Documentation Package
**Assignee**: Technical Writer  
**Duration**: 2 hours  
**Priority**: P1 - Important  
**Dependencies**: TASK-06-008

**Documentation Components**:

1. **API Documentation**
   - Complete docstrings for all public methods
   - Usage examples
   - Error handling guide

2. **Configuration Guide**
   ```markdown
   # LLM Processing Configuration Guide
   
   ## Ollama Setup
   1. Install Ollama: https://ollama.ai
   2. Pull model: `ollama pull llama3.2`
   3. Start service: `ollama serve`
   
   ## Configuration Options
   - `OLLAMA_BASE_URL`: Ollama service URL (default: http://localhost:11434)
   - `LLM_MODEL`: Model to use (default: llama3.2)
   - `LLM_TIMEOUT`: Request timeout in seconds (default: 30)
   ```

3. **Troubleshooting Guide**
   - Common errors and solutions
   - Performance optimization tips
   - Debugging techniques

---

#### TASK-06-010: Performance Optimization
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P1 - Important  
**Dependencies**: TASK-06-008

**Optimization Areas**:

1. **Batch Processing** (1 hour)
   - Optimal batch sizes
   - Concurrent processing limits
   - Memory management

2. **Caching Strategy** (1 hour)
   - Response caching for similar properties
   - Prompt template caching
   - Model warmup

3. **Resource Management** (1 hour)
   - Connection pooling
   - Memory limits
   - CPU/GPU utilization

---

#### TASK-06-011: Production Configuration
**Assignee**: DevOps Engineer  
**Duration**: 2 hours  
**Priority**: P1 - Important  
**Dependencies**: TASK-06-010

**Configuration Areas**:

1. **Environment Setup**
   ```yaml
   # config/production.yaml
   ollama:
     base_url: "http://localhost:11434"
     model: "llama3.2"
     timeout: 30
     max_retries: 3
   
   processing:
     batch_size: 50
     max_concurrent: 5
     fallback_enabled: true
     circuit_breaker_threshold: 5
     circuit_breaker_timeout: 60
   
   validation:
     min_confidence: 0.7
     strict_mode: false
     min_price: 10000
     max_price: 10000000
   ```

2. **Monitoring Setup**
   - Prometheus metrics
   - Grafana dashboards
   - Alert configuration

3. **Deployment Scripts**
   ```bash
   #!/bin/bash
   # scripts/start_processing.sh
   
   # Check Ollama is running
   if ! curl -s http://localhost:11434/api/version > /dev/null; then
       echo "ERROR: Ollama not running. Start with: ollama serve"
       exit 1
   fi
   
   # Check model is available
   if ! ollama list | grep -q "llama3.2"; then
       echo "ERROR: Model not found. Pull with: ollama pull llama3.2"
       exit 1
   fi
   
   # Start processing pipeline
   python -m phoenix_real_estate.processors.run_pipeline
   ```

---

#### TASK-06-012: Launch & Monitoring
**Assignee**: Operations Team  
**Duration**: 2 hours  
**Priority**: P0 - Critical  
**Dependencies**: TASK-06-011

**Launch Tasks**:

1. **Pre-Launch Checklist** (30 min)
   - [ ] Ollama service running
   - [ ] Model downloaded and available
   - [ ] Database connected
   - [ ] All tests passing
   - [ ] Configuration verified
   - [ ] Monitoring enabled

2. **Launch Procedure** (30 min)
   - Start processing pipeline
   - Verify initial processing
   - Monitor first 10 properties
   - Check error rates

3. **Post-Launch Monitoring** (1 hour)
   - Processing success rate (target: >90%)
   - Average processing time (target: <2s)
   - Error rates (target: <5%)
   - Resource usage (CPU <80%, Memory <4GB)

**Monitoring Dashboard**:
```python
# src/phoenix_real_estate/processors/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Define metrics
properties_processed = Counter(
    'llm_properties_processed_total',
    'Total properties processed',
    ['status', 'source']
)

processing_duration = Histogram(
    'llm_processing_duration_seconds',
    'Property processing duration',
    ['source']
)

extraction_accuracy = Gauge(
    'llm_extraction_accuracy',
    'Current extraction accuracy rate'
)

ollama_health = Gauge(
    'ollama_service_health',
    'Ollama service health status'
)
```

---

## Summary & Next Steps

### TDD Implementation Timeline
- **Day 1**: Foundation & Ollama Setup (TASK-06-001, TASK-06-002)
- **Day 2**: Core LLM Implementation (TASK-06-003, TASK-06-004)
- **Day 3**: Integration & Pipeline (TASK-06-005, TASK-06-006, TASK-06-007)
- **Day 4**: Testing & Production (TASK-06-008 through TASK-06-012)

### Success Metrics
- [ ] 100% test coverage for new code
- [ ] All tests written before implementation
- [ ] <2 second processing time per property
- [ ] >90% extraction accuracy
- [ ] Zero external API costs
- [ ] Seamless Epic 1 integration

### Key TDD Benefits Realized
1. **Predictable LLM Behavior**: Mock-first approach ensures consistent testing
2. **Quality Assurance**: Tests define and enforce quality standards
3. **Rapid Development**: Clear test-driven path accelerates implementation
4. **Regression Prevention**: Comprehensive test suite prevents future breaks
5. **Documentation**: Tests serve as living documentation of system behavior

---

*This document provides detailed TDD implementation tasks for Task 6: LLM Data Processing*