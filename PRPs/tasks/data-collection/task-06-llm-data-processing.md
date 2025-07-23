# Task 06: LLM Data Processing Pipeline

## Purpose and Scope

Implement a local LLM-powered data processing pipeline that extracts, validates, and enhances property data using Ollama with Llama2:7b. This task integrates seamlessly with Epic 1's foundation infrastructure to provide intelligent data processing while maintaining zero external API costs and ensuring data privacy.

### Scope
- Ollama integration for local LLM processing
- Structured data extraction from unstructured text and HTML
- Data quality validation and enhancement
- Batch processing optimization for efficiency
- Integration with Epic 1's validation and error handling systems
- Fallback mechanisms for when LLM is unavailable

### Out of Scope
- External LLM API integration (keeping costs at $0)
- Real-time processing (focus on batch efficiency)
- Model training or fine-tuning (using pre-trained models)

## System Status & Context

### Current Operational Status (85%)
- **MongoDB**: Collections ready (properties, collection_history, errors)
- **Maricopa API Collector**: Functional with API key integration
- **Phoenix MLS Collector**: HTML extraction implemented
- **WebShare Proxy**: Configured ($1/month active cost)
- **Budget Available**: ~$24/month for LLM infrastructure

### Working Components for Integration
```python
# MongoDB Collections Schema
properties_collection = {
    "_id": ObjectId,
    "address": str,
    "city": str,
    "state": str,
    "zip_code": str,
    "price": float,
    "bedrooms": int,
    "bathrooms": float,
    "square_feet": int,
    "lot_size_sqft": int,
    "year_built": int,
    "property_type": str,
    "features": List[str],
    "source": str,
    "processed_at": datetime,
    "raw_data": dict
}

# Maricopa API Response Format
maricopa_data = {
    "parcel_number": "123-45-678",
    "owner_name": "SMITH JOHN",
    "situs_address": "123 MAIN ST",
    "legal_description": "LOT 1 BLOCK 2",
    "total_assessed_value": 250000,
    "land_value": 50000,
    "improvement_value": 200000,
    "tax_year": 2024
}

# Phoenix MLS HTML Structure
phoenix_mls_html = """
<div class="property-card">
    <span class="price">$350,000</span>
    <div class="address">123 Main St, Phoenix, AZ 85031</div>
    <div class="details">
        <span>3 beds</span> | <span>2 baths</span> | <span>1,500 sqft</span>
    </div>
</div>
"""
```

## Foundation Integration Requirements

### Epic 1 Dependencies (MANDATORY)
```python
# Configuration Management
from phoenix_real_estate.foundation.config.base import ConfigProvider

# Database Integration
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.database.schema import Property, PropertyFeatures, PropertyPrice

# Logging Framework
from phoenix_real_estate.foundation.logging.factory import get_logger

# Error Handling
from phoenix_real_estate.foundation.utils.exceptions import (
    ProcessingError, ValidationError, ConfigurationError
)

# Validation and Utilities
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.foundation.utils.helpers import (
    safe_int, safe_float, normalize_address, retry_async
)
```

### Critical Implementation Details

#### Configuration Access Pattern (IMPORTANT)
```python
# CORRECT - Use getattr() with BaseConfig
config = ConfigProvider()
ollama_url = getattr(config.settings, "OLLAMA_BASE_URL", "http://localhost:11434")
model_name = getattr(config.settings, "LLM_MODEL", "llama2:7b")

# INCORRECT - DO NOT use get() method
# ollama_url = config.get("OLLAMA_BASE_URL")  # This will fail!
```

#### Async/Await Pattern Requirements
```python
# ALL I/O operations MUST be async
async def process_data(content: str) -> Dict[str, Any]:
    async with OllamaClient(config) as client:
        # Use await for all async operations
        if not await client.health_check():
            raise ProcessingError("Ollama service unavailable")
        
        result = await client.extract_structured_data(content, schema)
        return result

# Use async context managers for resource management
async with aiohttp.ClientSession() as session:
    async with session.post(url, json=payload) as response:
        data = await response.json()
```

#### Error Handling with Proper Chaining
```python
try:
    result = await extract_data(content)
except aiohttp.ClientError as e:
    # Always chain exceptions with 'from e'
    raise ProcessingError(
        "Failed to communicate with Ollama",
        context={"url": self.base_url, "error": str(e)},
        cause=e
    ) from e
```

#### Structured Logging Pattern
```python
logger = get_logger("llm.processor")

# Log with structured extra data
logger.info(
    "Processing started",
    extra={
        "batch_size": len(items),
        "source": source,
        "model": self.model_name,
        "timestamp": datetime.utcnow().isoformat()
    }
)

# Include metrics in logs
logger.debug(
    "Extraction completed",
    extra={
        "processing_time_ms": int(elapsed * 1000),
        "tokens_used": response.get("eval_count", 0),
        "success": True
    }
)
```

## Acceptance Criteria

### AC-1: Ollama Client Integration
**Acceptance Criteria**: Local LLM client with robust error handling

#### Ollama Client (`src/phoenix_real_estate/collectors/processing/llm_client.py`)
```python
"""Ollama client for local LLM processing."""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
from aiohttp import ClientSession, ClientTimeout

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError, ConfigurationError
from phoenix_real_estate.foundation.utils.helpers import retry_async


class OllamaClient:
    """Client for local Ollama LLM processing.
    
    Provides structured data extraction and processing using local LLM
    with comprehensive error handling and Epic 1 integration.
    
    Example:
        Basic Ollama client usage:
        
        >>> from phoenix_real_estate.foundation.config.base import ConfigProvider
        >>> config = ConfigProvider()
        >>> client = OllamaClient(config)
        >>> result = await client.extract_property_data(html_content)
    """
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize Ollama client.
        
        Args:
            config: Configuration provider from Epic 1
            
        Raises:
            ConfigurationError: If Ollama configuration is invalid
        """
        self.config = config
        self.logger = get_logger("llm.ollama_client")
        
        # Load configuration using Epic 1's ConfigProvider
        self.base_url = self.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = self.config.get("LLM_MODEL", "llama2:7b")
        self.timeout_seconds = self.config.get("LLM_TIMEOUT", 30)
        self.max_retries = self.config.get("LLM_MAX_RETRIES", 2)
        
        # HTTP client configuration
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
        """Check if Ollama service is available.
        
        Returns:
            True if Ollama is healthy and model is available
        """
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
        """Generate completion using Ollama.
        
        Args:
            prompt: User prompt for completion
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated completion or None if failed
            
        Raises:
            ProcessingError: If generation fails after retries
        """
        try:
            await self._ensure_session()
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.1,  # Low temperature for consistent extraction
                    "top_p": 0.9,
                    "stop": ["</output>", "\n\n---"]  # Stop tokens for structured output
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
            
            async def _generate() -> str:
                """Internal generation function for retry wrapper."""
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
                                "response": error_text[:500],
                                "model": self.model_name
                            }
                        )
                    
                    data = await response.json()
                    completion = data.get("response", "")
                    
                    if not completion.strip():
                        raise ProcessingError(
                            "Empty completion returned from LLM",
                            context={"model": self.model_name}
                        )
                    
                    return completion.strip()
            
            # Use Epic 1's retry utility
            completion = await retry_async(
                _generate,
                max_retries=self.max_retries,
                delay=1.0,
                backoff_factor=2.0
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.debug(
                "LLM completion generated",
                extra={
                    "model": self.model_name,
                    "completion_length": len(completion),
                    "processing_time_seconds": processing_time
                }
            )
            
            return completion
            
        except Exception as e:
            self.logger.error(
                "LLM completion failed",
                extra={
                    "model": self.model_name,
                    "prompt_length": len(prompt),
                    "error": str(e)
                }
            )
            raise ProcessingError(
                "Failed to generate LLM completion",
                context={
                    "model": self.model_name,
                    "prompt_preview": prompt[:200]
                },
                cause=e
            ) from e
    
    async def extract_structured_data(
        self, 
        content: str, 
        extraction_schema: Dict[str, Any],
        content_type: str = "html"
    ) -> Optional[Dict[str, Any]]:
        """Extract structured data from unstructured content.
        
        Args:
            content: Raw content to extract from (HTML, text, etc.)
            extraction_schema: Schema defining what to extract
            content_type: Type of content (html, text, etc.)
            
        Returns:
            Extracted structured data or None if extraction fails
        """
        try:
            # Build extraction prompt
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
            
            # Parse structured output
            extracted_data = self._parse_extraction_output(completion)
            
            self.logger.debug(
                "Structured data extracted",
                extra={
                    "content_type": content_type,
                    "content_length": len(content),
                    "extracted_fields": len(extracted_data) if extracted_data else 0
                }
            )
            
            return extracted_data
            
        except Exception as e:
            self.logger.error(
                "Structured data extraction failed",
                extra={
                    "content_type": content_type,
                    "content_length": len(content),
                    "error": str(e)
                }
            )
            raise ProcessingError(
                "Failed to extract structured data",
                context={"content_type": content_type},
                cause=e
            ) from e
    
    def _build_extraction_system_prompt(
        self, 
        schema: Dict[str, Any], 
        content_type: str
    ) -> str:
        """Build system prompt for data extraction."""
        schema_description = json.dumps(schema, indent=2)
        
        return f"""You are a precise data extraction assistant specializing in real estate property information.

Your task is to extract structured data from {content_type} content according to the provided schema.

EXTRACTION SCHEMA:
{schema_description}

INSTRUCTIONS:
1. Extract only information that is explicitly present in the content
2. Use "null" for missing or unclear information
3. Normalize addresses to standard format (e.g., "123 Main St")
4. Convert prices to numeric values without currency symbols
5. Extract numeric values for bedrooms, bathrooms, square footage
6. Be conservative - if uncertain, use null rather than guessing

OUTPUT FORMAT:
Provide your response as valid JSON matching the schema exactly.
Start your response with <output> and end with </output>.

Example:
<output>
{{
  "address": "123 Main St",
  "price": 350000,
  "bedrooms": 3,
  "bathrooms": 2.5
}}
</output>"""
    
    def _build_extraction_user_prompt(
        self, 
        content: str, 
        schema: Dict[str, Any]
    ) -> str:
        """Build user prompt with content to extract from."""
        # Truncate content if too long
        max_content_length = 4000  # Leave room for prompt overhead
        if len(content) > max_content_length:
            content = content[:max_content_length] + "...[truncated]"
        
        return f"""Extract structured data from the following content:

CONTENT TO EXTRACT FROM:
{content}

Extract the information according to the schema provided in the system prompt. 
Return only valid JSON within <output> tags."""
    
    def _parse_extraction_output(self, completion: str) -> Optional[Dict[str, Any]]:
        """Parse structured output from LLM completion."""
        try:
            # Extract JSON from between output tags
            start_marker = "<output>"
            end_marker = "</output>"
            
            start_idx = completion.find(start_marker)
            end_idx = completion.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                # Try to find JSON without markers
                json_start = completion.find("{")
                json_end = completion.rfind("}")
                
                if json_start != -1 and json_end != -1:
                    json_str = completion[json_start:json_end + 1]
                else:
                    raise ProcessingError("No JSON output found in completion")
            else:
                json_str = completion[start_idx + len(start_marker):end_idx].strip()
            
            # Parse JSON
            extracted_data = json.loads(json_str)
            
            # Validate that it's a dictionary
            if not isinstance(extracted_data, dict):
                raise ProcessingError("Extracted data is not a dictionary")
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            self.logger.warning(
                "Failed to parse LLM JSON output",
                extra={
                    "completion_preview": completion[:200],
                    "json_error": str(e)
                }
            )
            return None
        
        except Exception as e:
            self.logger.warning(
                "Failed to extract structured output",
                extra={
                    "completion_preview": completion[:200],
                    "error": str(e)
                }
            )
            return None
```

### AC-2: Data Extractor Implementation
**Acceptance Criteria**: High-level extraction interface with Epic 1 integration

#### Data Extractor (`src/phoenix_real_estate/collectors/processing/extractor.py`)
```python
"""LLM-powered data extraction for property information."""

from typing import Dict, Any, Optional, List
from datetime import datetime

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError, ValidationError
from phoenix_real_estate.foundation.utils.helpers import safe_int, safe_float, normalize_address
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.collectors.processing.llm_client import OllamaClient


class PropertyDataExtractor:
    """LLM-powered property data extraction.
    
    Extracts structured property information from unstructured text and HTML
    using local LLM with Epic 1 validation and error handling.
    
    Example:
        Basic extractor usage:
        
        >>> from phoenix_real_estate.foundation.config.base import ConfigProvider
        >>> config = ConfigProvider()
        >>> extractor = PropertyDataExtractor(config)
        >>> property_data = await extractor.extract_from_html(html_content)
    """
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize property data extractor.
        
        Args:
            config: Configuration provider from Epic 1
        """
        self.config = config
        self.logger = get_logger("llm.property_extractor")
        
        # Initialize LLM client and validator
        self.llm_client = OllamaClient(config)
        self.validator = DataValidator()
        
        # Extraction configuration
        self.enable_fallback = self.config.get("LLM_ENABLE_FALLBACK", True)
        self.batch_size = self.config.get("LLM_BATCH_SIZE", 5)
        
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
        """Extract property data from HTML content.
        
        Args:
            html_content: HTML content to extract from
            source: Source identifier for logging
            
        Returns:
            Extracted property data dictionary or None if extraction fails
        """
        try:
            self.logger.debug(
                "Starting HTML extraction",
                extra={
                    "content_length": len(html_content),
                    "source": source
                }
            )
            
            # First try LLM extraction
            extracted_data = await self._extract_with_llm(html_content, "html")
            
            if extracted_data:
                # Validate and clean extracted data
                cleaned_data = self._clean_extracted_data(extracted_data)
                
                # Apply Epic 1 validation
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
            
            # Fallback to rule-based extraction if enabled
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
                    "error": str(e),
                    "content_length": len(html_content)
                }
            )
            raise ProcessingError(
                "Failed to extract data from HTML",
                context={"source": source},
                cause=e
            ) from e
    
    async def extract_from_text(self, text_content: str, source: str = "unknown") -> Optional[Dict[str, Any]]:
        """Extract property data from text content.
        
        Args:
            text_content: Text content to extract from
            source: Source identifier for logging
            
        Returns:
            Extracted property data dictionary or None if extraction fails
        """
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
                # Validate and clean extracted data
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
            
            # Fallback to regex-based extraction if enabled
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
        """Extract property data from multiple contents in batch.
        
        Args:
            contents: List of content dictionaries with 'content' and 'type' keys
            source: Source identifier for logging
            
        Returns:
            List of extracted property data dictionaries
        """
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
                
                # Small delay between batches to avoid overwhelming LLM
                if i + self.batch_size < len(contents):
                    await asyncio.sleep(0.5)
            
            successful_extractions = len([r for r in results if r is not None])
            
            self.logger.info(
                "Batch extraction completed",
                extra={
                    "total_items": len(contents),
                    "successful_extractions": successful_extractions,
                    "success_rate": successful_extractions / len(contents),
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
        """Clean and normalize extracted data using Epic 1 utilities."""
        cleaned = {}
        
        try:
            # Clean address using Epic 1 helper
            if data.get("address"):
                cleaned["address"] = normalize_address(data["address"])
            
            # Clean city and state
            if data.get("city"):
                cleaned["city"] = str(data["city"]).strip().title()
            
            if data.get("state"):
                state = str(data["state"]).strip().upper()
                # Normalize common state formats
                if state in ["ARIZONA", "AZ"]:
                    cleaned["state"] = "AZ"
                else:
                    cleaned["state"] = state
            
            # Clean ZIP code
            if data.get("zip_code"):
                zip_code = str(data["zip_code"]).strip()
                # Extract 5-digit ZIP from ZIP+4 if present
                if "-" in zip_code:
                    zip_code = zip_code.split("-")[0]
                if zip_code.isdigit() and len(zip_code) == 5:
                    cleaned["zip_code"] = zip_code
            
            # Clean numeric fields using Epic 1 safe conversion
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
                    converted_value = converter(data[field])
                    if converted_value is not None:
                        cleaned[field] = converted_value
            
            # Clean string fields
            string_fields = ["property_type", "description", "parking", "neighborhood"]
            for field in string_fields:
                if data.get(field):
                    cleaned[field] = str(data[field]).strip()
            
            # Clean features array
            if data.get("features") and isinstance(data["features"], list):
                cleaned["features"] = [
                    str(feature).strip() 
                    for feature in data["features"] 
                    if feature and str(feature).strip()
                ]
            
            return cleaned
            
        except Exception as e:
            self.logger.warning(
                "Data cleaning failed",
                extra={"error": str(e)}
            )
            return data  # Return original data if cleaning fails
    
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
            
            # Simple extraction patterns (customize based on common HTML structures)
            # Price extraction
            price_selectors = [".price", ".property-price", "[data-price]", ".listing-price"]
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_value = safe_float(price_text)
                    if price_value and price_value > 10000:  # Reasonable house price
                        data["price"] = price_value
                        break
            
            # Address extraction
            address_selectors = [".address", ".property-address", "[data-address]"]
            for selector in address_selectors:
                addr_elem = soup.select_one(selector)
                if addr_elem:
                    data["address"] = normalize_address(addr_elem.get_text(strip=True))
                    break
            
            # Bedroom/bathroom extraction
            bed_bath_text = soup.get_text().lower()
            import re
            
            bed_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', bed_bath_text)
            if bed_match:
                data["bedrooms"] = safe_int(bed_match.group(1))
            
            bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', bed_bath_text)
            if bath_match:
                data["bathrooms"] = safe_float(bath_match.group(1))
            
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
            import re
            
            data = {}
            text = text_content.lower()
            
            # Price extraction
            price_patterns = [
                r'\$([0-9,]+)',
                r'price[:\s]+\$?([0-9,]+)',
                r'([0-9,]+)\s*dollars?'
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text)
                if match:
                    price_value = safe_float(match.group(1))
                    if price_value and price_value > 10000:
                        data["price"] = price_value
                        break
            
            # Bedroom extraction
            bed_patterns = [
                r'(\d+)\s*(?:bed|br|bedroom)',
                r'(\d+)\s*bd'
            ]
            
            for pattern in bed_patterns:
                match = re.search(pattern, text)
                if match:
                    data["bedrooms"] = safe_int(match.group(1))
                    break
            
            # Bathroom extraction
            bath_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)',
                r'(\d+(?:\.\d+)?)\s*bth'
            ]
            
            for pattern in bath_patterns:
                match = re.search(pattern, text)
                if match:
                    data["bathrooms"] = safe_float(match.group(1))
                    break
            
            # Square footage extraction
            sqft_patterns = [
                r'(\d+(?:,\d+)?)\s*(?:sq\.?\s?ft|sqft|square\s+feet)',
                r'(\d+(?:,\d+)?)\s*sf'
            ]
            
            for pattern in sqft_patterns:
                match = re.search(pattern, text)
                if match:
                    data["square_feet"] = safe_int(match.group(1))
                    break
            
            return data if data else None
            
        except Exception as e:
            self.logger.debug(
                "Fallback text extraction failed",
                extra={"error": str(e)}
            )
            return None
```

### AC-3: Processing Pipeline Implementation
**Acceptance Criteria**: Orchestrated processing pipeline with batch optimization

#### Processing Pipeline (`src/phoenix_real_estate/collectors/processing/pipeline.py`)
```python
"""Data processing pipeline orchestration."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.collectors.processing.extractor import PropertyDataExtractor
from phoenix_real_estate.collectors.processing.validator import ProcessingValidator


@dataclass
class ProcessingResult:
    """Result of data processing operation."""
    success: bool
    processed_count: int
    failed_count: int
    processing_time_seconds: float
    errors: List[str]


class DataProcessingPipeline:
    """Data processing pipeline with LLM extraction and validation.
    
    Orchestrates the complete data processing workflow from raw content
    to validated property data using Epic 1's foundation infrastructure.
    
    Example:
        Basic pipeline usage:
        
        >>> from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository
        >>> config = ConfigProvider()
        >>> repository = PropertyRepository(...)
        >>> pipeline = DataProcessingPipeline(config, repository)
        >>> result = await pipeline.process_batch(raw_data_list)
    """
    
    def __init__(
        self, 
        config: ConfigProvider, 
        repository: PropertyRepository
    ) -> None:
        """Initialize data processing pipeline.
        
        Args:
            config: Configuration provider from Epic 1
            repository: Property repository from Epic 1
        """
        self.config = config
        self.repository = repository
        self.logger = get_logger("llm.processing_pipeline")
        
        # Initialize pipeline components
        self.extractor = PropertyDataExtractor(config)
        self.validator = ProcessingValidator(config)
        
        # Pipeline configuration
        self.batch_size = self.config.get("PROCESSING_BATCH_SIZE", 10)
        self.max_concurrent = self.config.get("PROCESSING_MAX_CONCURRENT", 3)
        self.enable_storage = self.config.get("PROCESSING_ENABLE_STORAGE", True)
        
        self.logger.info(
            "Data processing pipeline initialized",
            extra={
                "batch_size": self.batch_size,
                "max_concurrent": self.max_concurrent,
                "storage_enabled": self.enable_storage
            }
        )
    
    async def process_single(
        self, 
        raw_data: Dict[str, Any], 
        source: str = "unknown"
    ) -> Optional[Dict[str, Any]]:
        """Process single raw data item.
        
        Args:
            raw_data: Raw data to process
            source: Data source identifier
            
        Returns:
            Processed property data or None if processing failed
        """
        try:
            self.logger.debug(
                "Processing single item",
                extra={
                    "source": source,
                    "data_keys": list(raw_data.keys())
                }
            )
            
            # Determine content type and extract content
            content, content_type = self._extract_content(raw_data)
            if not content:
                self.logger.warning(
                    "No extractable content found",
                    extra={"source": source}
                )
                return None
            
            # Extract structured data
            if content_type == "html":
                extracted_data = await self.extractor.extract_from_html(content, source)
            else:
                extracted_data = await self.extractor.extract_from_text(content, source)
            
            if not extracted_data:
                self.logger.debug(
                    "No data extracted",
                    extra={"source": source}
                )
                return None
            
            # Validate processed data
            validation_result = await self.validator.validate_property_data(extracted_data)
            if not validation_result.is_valid:
                self.logger.warning(
                    "Data validation failed",
                    extra={
                        "source": source,
                        "validation_errors": validation_result.errors
                    }
                )
                return None
            
            # Enhance with metadata
            processed_data = self._enhance_with_metadata(extracted_data, raw_data, source)
            
            # Store if enabled
            if self.enable_storage:
                try:
                    property_id = await self.repository.create(processed_data)
                    processed_data["stored_property_id"] = property_id
                    
                    self.logger.info(
                        "Property data stored",
                        extra={
                            "property_id": property_id,
                            "source": source
                        }
                    )
                    
                except Exception as e:
                    self.logger.warning(
                        "Failed to store property data",
                        extra={
                            "source": source,
                            "error": str(e)
                        }
                    )
                    # Continue processing even if storage fails
            
            self.logger.debug(
                "Single item processing completed",
                extra={
                    "source": source,
                    "success": True
                }
            )
            
            return processed_data
            
        except Exception as e:
            self.logger.error(
                "Single item processing failed",
                extra={
                    "source": source,
                    "error": str(e)
                }
            )
            raise ProcessingError(
                "Failed to process single data item",
                context={"source": source},
                cause=e
            ) from e
    
    async def process_batch(
        self, 
        raw_data_list: List[Dict[str, Any]], 
        source: str = "unknown"
    ) -> ProcessingResult:
        """Process batch of raw data items.
        
        Args:
            raw_data_list: List of raw data items to process
            source: Data source identifier
            
        Returns:
            Processing result with statistics
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(
                "Starting batch processing",
                extra={
                    "batch_size": len(raw_data_list),
                    "source": source
                }
            )
            
            processed_count = 0
            failed_count = 0
            errors = []
            
            # Process in smaller batches to manage concurrency
            for i in range(0, len(raw_data_list), self.batch_size):
                batch = raw_data_list[i:i + self.batch_size]
                
                self.logger.debug(
                    "Processing sub-batch",
                    extra={
                        "batch_number": i // self.batch_size + 1,
                        "batch_size": len(batch),
                        "source": source
                    }
                )
                
                # Create semaphore to limit concurrent processing
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                async def process_with_semaphore(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                    """Process item with concurrency control."""
                    async with semaphore:
                        try:
                            return await self.process_single(item, source)
                        except Exception as e:
                            errors.append(str(e))
                            return None
                
                # Process batch concurrently
                tasks = [process_with_semaphore(item) for item in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count results
                for result in results:
                    if isinstance(result, Exception):
                        failed_count += 1
                        errors.append(str(result))
                    elif result is not None:
                        processed_count += 1
                    else:
                        failed_count += 1
                
                # Small delay between batches
                if i + self.batch_size < len(raw_data_list):
                    await asyncio.sleep(0.5)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                "Batch processing completed",
                extra={
                    "total_items": len(raw_data_list),
                    "processed_count": processed_count,
                    "failed_count": failed_count,
                    "success_rate": processed_count / len(raw_data_list),
                    "processing_time_seconds": processing_time,
                    "source": source
                }
            )
            
            return ProcessingResult(
                success=processed_count > 0,
                processed_count=processed_count,
                failed_count=failed_count,
                processing_time_seconds=processing_time,
                errors=errors[:10]  # Limit error list size
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.error(
                "Batch processing failed",
                extra={
                    "batch_size": len(raw_data_list),
                    "source": source,
                    "error": str(e),
                    "processing_time_seconds": processing_time
                }
            )
            
            return ProcessingResult(
                success=False,
                processed_count=0,
                failed_count=len(raw_data_list),
                processing_time_seconds=processing_time,
                errors=[str(e)]
            )
    
    def _extract_content(self, raw_data: Dict[str, Any]) -> tuple[Optional[str], str]:
        """Extract content from raw data and determine type."""
        # Check for HTML content
        html_fields = ["full_html", "raw_html", "html", "content"]
        for field in html_fields:
            if field in raw_data and raw_data[field]:
                content = str(raw_data[field])
                if "<" in content and ">" in content:  # Simple HTML detection
                    return content, "html"
        
        # Check for text content
        text_fields = ["description", "details", "text", "content"]
        for field in text_fields:
            if field in raw_data and raw_data[field]:
                return str(raw_data[field]), "text"
        
        # Fallback: concatenate all string values
        text_parts = []
        for key, value in raw_data.items():
            if isinstance(value, str) and value.strip():
                text_parts.append(f"{key}: {value}")
        
        if text_parts:
            return "\n".join(text_parts), "text"
        
        return None, "text"
    
    def _enhance_with_metadata(
        self, 
        extracted_data: Dict[str, Any], 
        raw_data: Dict[str, Any], 
        source: str
    ) -> Dict[str, Any]:
        """Enhance extracted data with metadata."""
        enhanced_data = extracted_data.copy()
        
        # Add processing metadata
        enhanced_data.update({
            "source": source,
            "processed_at": datetime.utcnow().isoformat(),
            "processing_method": "llm_extraction",
            "raw_data_keys": list(raw_data.keys()),
            "extraction_confidence": "high"  # Could be enhanced with actual confidence scoring
        })
        
        # Preserve important raw data fields
        preserve_fields = ["scraped_at", "property_url", "listing_id", "source_id"]
        for field in preserve_fields:
            if field in raw_data:
                enhanced_data[f"original_{field}"] = raw_data[field]
        
        return enhanced_data
```

### AC-4: Processing Validator Implementation
**Acceptance Criteria**: Comprehensive validation for processed data

#### Processing Validator (`src/phoenix_real_estate/collectors/processing/validator.py`)
```python
"""LLM processing output validation."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

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
    """Validator for LLM processing outputs.
    
    Provides comprehensive validation of extracted property data
    with confidence scoring and quality assessment.
    
    Example:
        Basic validator usage:
        
        >>> validator = ProcessingValidator(config)
        >>> result = await validator.validate_property_data(extracted_data)
        >>> if result.is_valid:
        >>>     print(f"Validation passed with confidence: {result.confidence_score}")
    """
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize processing validator.
        
        Args:
            config: Configuration provider from Epic 1
        """
        self.config = config
        self.logger = get_logger("llm.processing_validator")
        
        # Initialize Epic 1 validator
        self.base_validator = DataValidator()
        
        # Validation configuration
        self.min_confidence_threshold = self.config.get("VALIDATION_MIN_CONFIDENCE", 0.7)
        self.strict_validation = self.config.get("VALIDATION_STRICT_MODE", False)
        
        # Quality thresholds
        self.min_price = self.config.get("VALIDATION_MIN_PRICE", 10000)
        self.max_price = self.config.get("VALIDATION_MAX_PRICE", 10000000)
        self.min_sqft = self.config.get("VALIDATION_MIN_SQFT", 100)
        self.max_sqft = self.config.get("VALIDATION_MAX_SQFT", 20000)
        
        self.logger.info(
            "Processing validator initialized",
            extra={
                "min_confidence": self.min_confidence_threshold,
                "strict_mode": self.strict_validation
            }
        )
    
    async def validate_property_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate extracted property data.
        
        Args:
            data: Extracted property data to validate
            
        Returns:
            Validation result with errors, warnings, and confidence score
        """
        try:
            errors = []
            warnings = []
            confidence_factors = []
            
            # Basic Epic 1 validation
            if not self.base_validator.validate_property_data(data):
                base_errors = self.base_validator.get_errors()
                errors.extend(base_errors)
                confidence_factors.append(0.0)  # Major penalty for base validation failure
            else:
                confidence_factors.append(1.0)  # Bonus for passing base validation
            
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
                errors.append(f"Price ${price_value:,.0f} is below minimum threshold ${self.min_price:,.0f}")
                return 0.0
            
            if price_value > self.max_price:
                errors.append(f"Price ${price_value:,.0f} is above maximum threshold ${self.max_price:,.0f}")
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

## Cost Management Strategy

### Budget Allocation ($24/month remaining)
```python
# Ollama Infrastructure Costs
- Local GPU Server: $0/month (runs on local machine)
- Ollama Service: $0/month (open source)
- Model Storage: $0/month (one-time 4GB download)
- Processing Costs: $0/month (local compute)

# Actual Monthly Costs
- WebShare Proxy: $1/month (already allocated)
- 2captcha: ~$0.50/month (minimal usage)
- Total: ~$1.50/month
- Remaining: $23.50/month (reserved for scaling)
```

### Processing Efficiency Optimization
```python
class CostOptimizedProcessor:
    """Maximize processing within budget constraints."""
    
    def __init__(self, config: ConfigProvider):
        # Batch processing for efficiency
        self.batch_size = 10  # Process 10 properties at once
        self.max_concurrent = 3  # Limit concurrent LLM calls
        self.cache_ttl = 3600  # Cache results for 1 hour
        
        # Token optimization
        self.max_prompt_length = 4000  # Truncate long content
        self.max_response_tokens = 1000  # Limit response size
        
    async def process_with_caching(self, content: str) -> Dict[str, Any]:
        # Check cache first
        cache_key = hashlib.md5(content.encode()).hexdigest()
        cached = await self.get_from_cache(cache_key)
        if cached:
            return cached
            
        # Process and cache result
        result = await self.extract_data(content)
        await self.save_to_cache(cache_key, result)
        return result
```

## Practical Implementation Examples

### Example 1: Processing Maricopa API Data
```python
async def process_maricopa_property(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process Maricopa API response into standardized format."""
    
    # Convert Maricopa format to text for LLM
    text_content = f"""
    Property Information:
    Parcel: {data.get('parcel_number')}
    Owner: {data.get('owner_name')}
    Address: {data.get('situs_address')}
    Legal: {data.get('legal_description')}
    Total Value: ${data.get('total_assessed_value'):,}
    Land Value: ${data.get('land_value'):,}
    Improvement Value: ${data.get('improvement_value'):,}
    Tax Year: {data.get('tax_year')}
    """
    
    # Extract with LLM
    extractor = PropertyDataExtractor(config)
    result = await extractor.extract_from_text(text_content, "maricopa")
    
    # Enhance with direct mappings
    if result:
        result['parcel_number'] = data.get('parcel_number')
        result['assessed_value'] = data.get('total_assessed_value')
        result['tax_year'] = data.get('tax_year')
    
    return result
```

### Example 2: Processing Phoenix MLS HTML
```python
async def process_phoenix_mls_html(html: str) -> Dict[str, Any]:
    """Process Phoenix MLS HTML into property data."""
    
    # LLM extraction with specific schema
    extraction_schema = {
        "address": {"type": "string", "description": "Full street address"},
        "price": {"type": "number", "description": "Listing price as number"},
        "bedrooms": {"type": "integer", "description": "Number of bedrooms"},
        "bathrooms": {"type": "number", "description": "Number of bathrooms (can be decimal)"},
        "square_feet": {"type": "integer", "description": "Living area square footage"},
        "property_type": {"type": "string", "description": "Type: Single Family, Condo, etc"},
        "year_built": {"type": "integer", "description": "Year constructed"},
        "lot_size_sqft": {"type": "integer", "description": "Lot size in square feet"},
        "mls_number": {"type": "string", "description": "MLS listing number"},
        "listing_date": {"type": "string", "description": "Date listed"},
        "features": {"type": "array", "description": "Property features and amenities"}
    }
    
    extractor = PropertyDataExtractor(config)
    async with extractor.llm_client as client:
        result = await client.extract_structured_data(
            content=html,
            extraction_schema=extraction_schema,
            content_type="html"
        )
    
    return result
```

### Example 3: Batch Processing with Error Recovery
```python
async def process_property_batch(properties: List[Dict[str, Any]]) -> ProcessingResult:
    """Process batch with comprehensive error handling."""
    
    pipeline = DataProcessingPipeline(config, repository)
    results = []
    errors = []
    
    # Process in chunks to manage memory
    chunk_size = 5
    for i in range(0, len(properties), chunk_size):
        chunk = properties[i:i + chunk_size]
        
        try:
            # Check Ollama health before processing
            if not await pipeline.extractor.llm_client.health_check():
                logger.warning("Ollama unavailable, using fallback")
                # Use fallback extraction
                for prop in chunk:
                    fallback_result = await fallback_extraction(prop)
                    results.append(fallback_result)
            else:
                # Process with LLM
                chunk_results = await pipeline.process_batch(chunk)
                results.extend(chunk_results)
                
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            errors.append(str(e))
            # Continue with next batch
            
    return ProcessingResult(
        success=len(results) > 0,
        processed_count=len(results),
        failed_count=len(errors),
        processing_time_seconds=0,
        errors=errors
    )
```

## Integration Requirements

### MongoDB Integration
```python
async def store_processed_property(data: Dict[str, Any]) -> str:
    """Store processed property in MongoDB."""
    
    # Validate before storage
    validator = ProcessingValidator(config)
    validation_result = await validator.validate_property_data(data)
    
    if not validation_result.is_valid:
        raise ValidationError(
            "Property data validation failed",
            context={"errors": validation_result.errors}
        )
    
    # Store using repository
    repository = PropertyRepository(db_client)
    property_id = await repository.create({
        **data,
        "validation_score": validation_result.confidence_score,
        "processed_at": datetime.utcnow(),
        "processing_version": "1.0"
    })
    
    return property_id
```

### Data Validation Before Processing
```python
async def validate_input_data(raw_data: Dict[str, Any]) -> bool:
    """Validate data before LLM processing."""
    
    # Check for minimum required fields
    if not raw_data:
        return False
        
    # Check for extractable content
    has_html = any(key in raw_data for key in ["html", "full_html", "raw_html"])
    has_text = any(key in raw_data for key in ["description", "details", "text"])
    
    if not has_html and not has_text:
        logger.warning("No extractable content found", extra={"keys": list(raw_data.keys())})
        return False
        
    # Check content size
    content_size = sum(len(str(v)) for v in raw_data.values() if isinstance(v, str))
    if content_size < 50:  # Too small to extract meaningful data
        logger.warning("Content too small", extra={"size": content_size})
        return False
        
    return True
```

### Error Recovery Mechanisms
```python
class RecoverableProcessor:
    """Processor with comprehensive error recovery."""
    
    async def process_with_recovery(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        strategies = [
            self._try_llm_extraction,
            self._try_fallback_extraction,
            self._try_basic_extraction,
            self._try_manual_mapping
        ]
        
        for strategy in strategies:
            try:
                result = await strategy(data)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue
                
        # All strategies failed
        await self._record_failure(data, "All extraction strategies failed")
        return None
        
    async def _try_llm_extraction(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Primary LLM extraction strategy."""
        extractor = PropertyDataExtractor(self.config)
        return await extractor.extract_from_html(data.get("html", ""))
        
    async def _try_fallback_extraction(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fallback BeautifulSoup extraction."""
        # Implementation from extractor fallback methods
        pass
        
    async def _try_basic_extraction(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Basic regex extraction."""
        # Implementation from extractor fallback methods
        pass
        
    async def _try_manual_mapping(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Direct field mapping for known formats."""
        if "maricopa" in data.get("source", "").lower():
            return {
                "address": normalize_address(data.get("situs_address", "")),
                "assessed_value": safe_float(data.get("total_assessed_value")),
                "parcel_number": data.get("parcel_number")
            }
        return None
```

## Testing Requirements with Examples

### Unit Test Example
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_ollama_client_health_check():
    """Test Ollama client health check functionality."""
    
    config = ConfigProvider()
    client = OllamaClient(config)
    
    # Mock successful health check
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "models": [{"name": "llama2:7b"}]
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await client.health_check()
        assert result is True
        
    # Mock failed health check
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await client.health_check()
        assert result is False
```

### Integration Test Example
```python
@pytest.mark.asyncio
async def test_end_to_end_processing():
    """Test complete processing pipeline."""
    
    # Setup
    config = ConfigProvider()
    repository = PropertyRepository(test_db_client)
    pipeline = DataProcessingPipeline(config, repository)
    
    # Test data
    test_html = """
    <div class="property">
        <h2>123 Test St, Phoenix, AZ 85031</h2>
        <span class="price">$299,900</span>
        <div class="details">3 beds | 2 baths | 1,450 sqft</div>
    </div>
    """
    
    # Process
    result = await pipeline.process_single(
        {"html": test_html, "source": "test"},
        source="phoenix_mls"
    )
    
    # Assertions
    assert result is not None
    assert result.get("address") == "123 Test St"
    assert result.get("city") == "Phoenix"
    assert result.get("state") == "AZ"
    assert result.get("zip_code") == "85031"
    assert result.get("price") == 299900
    assert result.get("bedrooms") == 3
    assert result.get("bathrooms") == 2
    assert result.get("square_feet") == 1450
```

## Success Metrics and Validation

### Key Performance Indicators
1. **Extraction Accuracy**: >90% correct field extraction
2. **Processing Speed**: <2 seconds per property
3. **Fallback Success**: >70% success when LLM unavailable
4. **Validation Score**: Average confidence >0.8
5. **Error Rate**: <5% processing failures

### Validation Criteria
```python
async def validate_implementation_success():
    """Validate Task 6 implementation meets requirements."""
    
    checks = {
        "ollama_available": await check_ollama_service(),
        "model_loaded": await check_model_availability(),
        "extraction_accuracy": await test_extraction_accuracy(),
        "processing_speed": await test_processing_performance(),
        "error_handling": await test_error_recovery(),
        "mongodb_integration": await test_database_storage(),
        "cost_compliance": await verify_zero_api_costs()
    }
    
    success = all(checks.values())
    print(f"Implementation validation: {'PASSED' if success else 'FAILED'}")
    
    for check, result in checks.items():
        print(f"  {check}: {'✓' if result else '✗'}")
    
    return success
```

## Technical Approach

### Epic 1 Foundation Integration Strategy
1. **Configuration**: Use Epic 1's ConfigProvider for LLM settings and processing parameters
2. **Database**: Use Epic 1's PropertyRepository for storing processed data
3. **Logging**: Use Epic 1's structured logging for processing metrics and debugging
4. **Error Handling**: Follow Epic 1's exception hierarchy patterns
5. **Validation**: Use Epic 1's DataValidator as base validation layer

### Local LLM Integration Strategy
1. **Ollama Client**: Direct HTTP integration with local Ollama service
2. **Model Management**: Use configurable model names with fallback capabilities
3. **Prompt Engineering**: Structured prompts for consistent data extraction
4. **Error Recovery**: Comprehensive fallback mechanisms for LLM unavailability
5. **Batch Processing**: Optimized batch processing for efficiency

### Development Process
1. **Ollama Integration**: HTTP client with health monitoring and error handling
2. **Data Extraction**: Structured prompts and response parsing
3. **Validation Framework**: Multi-layered validation with confidence scoring
4. **Pipeline Orchestration**: Batch processing with concurrency control
5. **Integration Testing**: Comprehensive tests validating Epic 1 integration

## Dependencies

### Epic 1 Foundation (REQUIRED)
- Configuration management for LLM settings and processing parameters
- PropertyRepository for storing processed data
- Structured logging framework
- Exception hierarchy and error handling patterns
- Data validation utilities and helpers

### External Dependencies
- `aiohttp`: HTTP client for Ollama communication
- `beautifulsoup4`: HTML parsing for fallback extraction

### System Dependencies
- Ollama service running locally
- Llama2:7b model downloaded and available
- Sufficient system resources for LLM processing

## Risk Assessment

### High Risk
- **LLM Service Unavailability**: Ollama service down or model unavailable
  - **Mitigation**: Comprehensive health checks and fallback extraction methods
  - **Contingency**: Rule-based extraction when LLM unavailable

### Medium Risk
- **Data Quality Issues**: LLM producing inconsistent or inaccurate extractions
  - **Mitigation**: Multi-layered validation with confidence scoring
  - **Contingency**: Manual review processes for low-confidence extractions

### Low Risk
- **Performance Degradation**: LLM processing taking too long
  - **Mitigation**: Configurable timeouts and batch size optimization
  - **Contingency**: Fallback to simpler extraction methods

## Testing Requirements

### Unit Tests
- Ollama client communication and error handling
- Data extraction accuracy with known inputs
- Validation logic and confidence scoring
- Fallback extraction methods

### Integration Tests
- Full Epic 1 foundation integration
- End-to-end processing pipeline with real data
- LLM health monitoring and recovery
- Performance under various load conditions

### Quality Tests
- Data extraction accuracy benchmarks
- Validation effectiveness metrics
- Processing speed optimization
- Error handling resilience

## Interface Specifications

### For Epic 3 Orchestration
```python
# Epic 3 will use these interfaces
from phoenix_real_estate.collectors.processing import DataProcessingPipeline

# Processing orchestration
pipeline = DataProcessingPipeline(config, repository)
result = await pipeline.process_batch(raw_data_list)
```

### For Epic 4 Quality Analysis
```python
# Epic 4 will monitor processing quality
from phoenix_real_estate.collectors.processing.validator import ProcessingValidator

# Quality monitoring
validator = ProcessingValidator(config)
validation_result = await validator.validate_property_data(extracted_data)
quality_score = validation_result.confidence_score
```

---

**Task Owner**: Data Engineering Team  
**Estimated Effort**: 2-3 days  
**Priority**: High (essential data processing capability)  
**Status**: Ready for Implementation