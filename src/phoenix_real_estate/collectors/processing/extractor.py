"""Property data extraction using LLM."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.foundation.logging import get_logger

from .llm_client import OllamaClient


logger = get_logger(__name__)


class PropertyDataExtractor:
    """Extracts structured property data using LLM.
    
    This class uses Ollama LLM to extract structured property information
    from various sources including HTML (Phoenix MLS) and JSON (Maricopa County).
    """
    
    def __init__(self, config: ConfigProvider):
        """Initialize the property data extractor.
        
        Args:
            config: Configuration provider
        """
        self.config = config
        self._llm_client: Optional[OllamaClient] = None
        self._validator = None  # Validation happens in pipeline
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the extractor and its dependencies."""
        if self._initialized:
            return
            
        try:
            # Initialize LLM client
            self._llm_client = OllamaClient(self.config)
            await self._llm_client._ensure_session()
            
            self._initialized = True
            logger.info("PropertyDataExtractor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PropertyDataExtractor: {e}")
            raise ProcessingError(f"Initialization failed: {str(e)}") from e
            
    async def close(self) -> None:
        """Close the extractor and cleanup resources."""
        if self._llm_client:
            await self._llm_client.close()
        self._initialized = False
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def extract_from_html(
        self,
        html_content: str,
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> Dict[str, Any]:
        """Extract property data from HTML content.
        
        Args:
            html_content: HTML content to extract from
            source: Source identifier (e.g., 'phoenix_mls')
            timeout: Extraction timeout in seconds
            strict_validation: Whether to enforce strict validation
            
        Returns:
            Extracted property data with metadata
            
        Raises:
            ProcessingError: If extraction fails
            ValueError: If source is not supported
        """
        if not self._initialized:
            await self.initialize()
            
        if source not in ["phoenix_mls"]:
            raise ValueError(f"Unsupported source for HTML extraction: {source}")
            
        try:
            # Get extraction prompt and schema
            await self.get_extraction_prompt(html_content, source)
            schema = await self.get_extraction_schema(source)
            
            # Extract data using LLM
            timeout = timeout or self.config.get_typed('EXTRACTION_TIMEOUT', int, default=30)
            
            extracted_data = await asyncio.wait_for(
                self._llm_client.extract_structured_data(
                    content=html_content,
                    extraction_schema=schema,
                    content_type="html"
                ),
                timeout=timeout
            )
            
            # Add metadata
            extracted_data["source"] = source
            extracted_data["extracted_at"] = datetime.now(timezone.utc).isoformat()
            
            # Validation is now handled by the pipeline
            # Just return the extracted data
                
            return extracted_data
            
        except asyncio.TimeoutError:
            logger.error(f"Extraction timeout after {timeout} seconds")
            raise
        except Exception as e:
            logger.error(f"HTML extraction failed: {e}")
            raise ProcessingError(f"Failed to extract from HTML: {str(e)}") from e
            
    async def extract_from_json(
        self,
        json_data: Union[Dict[str, Any], str],
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> Dict[str, Any]:
        """Extract property data from JSON content.
        
        Args:
            json_data: JSON data (dict or string) to extract from
            source: Source identifier (e.g., 'maricopa_county')
            timeout: Extraction timeout in seconds
            strict_validation: Whether to enforce strict validation
            
        Returns:
            Extracted property data with metadata
            
        Raises:
            ProcessingError: If extraction fails
            ValueError: If source is not supported
        """
        if not self._initialized:
            await self.initialize()
            
        if source not in ["maricopa_county"]:
            raise ValueError(f"Unsupported source for JSON extraction: {source}")
            
        try:
            # Convert to string if needed
            if isinstance(json_data, dict):
                json_str = json.dumps(json_data)
            else:
                json_str = json_data
                json_data = json.loads(json_str)  # Parse to validate
                
            # For Maricopa data, we need to parse the address
            if source == "maricopa_county":
                # Extract address using LLM
                
                address_schema = {
                    "street": "string",
                    "city": "string", 
                    "state": "string",
                    "zip_code": "string"
                }
                
                timeout = timeout or self.config.get_typed('EXTRACTION_TIMEOUT', int, default=30)
                
                parsed_address = await asyncio.wait_for(
                    self._llm_client.extract_structured_data(
                        content=json_data.get("property_address", ""),
                        extraction_schema=address_schema,
                        content_type="text"
                    ),
                    timeout=timeout
                )
                
                # Build structured data
                lot_size = json_data.get("lot_size")
                if isinstance(lot_size, str) and lot_size.isdigit():
                    lot_size = int(lot_size)
                    
                extracted_data = {
                    "parcel_number": json_data.get("parcel_number"),
                    "owner_name": json_data.get("owner_name"),
                    "property_address": json_data.get("property_address"),
                    "assessed_value": json_data.get("assessed_value"),
                    "year_built": json_data.get("year_built"),
                    "square_feet": json_data.get("square_footage"),
                    "lot_size": lot_size,
                    "property_type": json_data.get("property_type"),
                    "address": parsed_address,
                    "source": source,
                    "extracted_at": datetime.now(timezone.utc).isoformat()
                }
                
            # Validation is now handled by the pipeline
            # Just return the extracted data
                
            return extracted_data
            
        except asyncio.TimeoutError:
            logger.error(f"Extraction timeout after {timeout} seconds")
            raise
        except Exception as e:
            logger.error(f"JSON extraction failed: {e}")
            raise ProcessingError(f"Failed to extract from JSON: {str(e)}") from e
            
    async def get_extraction_prompt(self, content: str, source: str) -> str:
        """Generate extraction prompt based on content type and source.
        
        Args:
            content: Content to analyze
            source: Source identifier
            
        Returns:
            Formatted prompt for LLM extraction
        """
        if source == "phoenix_mls":
            return """
            Extract property information from this HTML listing.
            Focus on extracting:
            - price (numeric value only)
            - bedrooms (number)
            - bathrooms (number, can be decimal)
            - square_feet (number)
            - property_type (e.g., Single Family Home, Condo, Townhouse)
            - address (structured with street, city, state, zip_code)
            - year_built (if available)
            - lot_size (number) and lot_units (acres, sqft, etc.) if available
            - features (list of key features mentioned)
            - description (full property description text)
            
            Return the data as structured JSON matching the provided schema.
            """
        elif source == "maricopa_county":
            return """
            Extract property information from this JSON data.
            Focus on extracting:
            - parcel_number
            - owner_name
            - property_address (full address string)
            - assessed_value
            - year_built
            - square_footage
            - lot_size
            - property_type
            
            Return the data as structured JSON matching the provided schema.
            """
        else:
            return "Extract property information from this content."
            
    async def get_extraction_schema(self, source: str) -> Dict[str, Any]:
        """Get extraction schema for the given source.
        
        Args:
            source: Source identifier
            
        Returns:
            Schema dictionary for structured extraction
        """
        if source == "phoenix_mls":
            return {
                "price": "number",
                "bedrooms": "integer",
                "bathrooms": "number",
                "square_feet": "integer",
                "property_type": "string",
                "address": {
                    "street": "string",
                    "city": "string",
                    "state": "string",
                    "zip_code": "string"
                },
                "year_built": "integer (optional)",
                "lot_size": "number (optional)",
                "lot_units": "string (optional)",
                "features": "array of strings (optional)",
                "description": "string (optional)"
            }
        elif source == "maricopa_county":
            return {
                "parcel_number": "string",
                "owner_name": "string",
                "property_address": "string",
                "assessed_value": "number",
                "year_built": "integer",
                "square_footage": "integer",
                "lot_size": "string",
                "property_type": "string"
            }
        else:
            return {}
            
    async def extract_batch(
        self,
        items: List[Union[str, Dict[str, Any]]],
        source: str,
        content_type: str = "html",
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> List[Dict[str, Any]]:
        """Extract data from multiple items in batch.
        
        Args:
            items: List of content items to process
            source: Source identifier
            content_type: Type of content ('html' or 'json')
            timeout: Timeout per item in seconds
            strict_validation: Whether to enforce strict validation
            
        Returns:
            List of extracted property data
        """
        results = []
        
        for item in items:
            try:
                if content_type == "html":
                    result = await self.extract_from_html(
                        item, source, timeout, strict_validation
                    )
                elif content_type == "json":
                    result = await self.extract_from_json(
                        item, source, timeout, strict_validation
                    )
                else:
                    raise ValueError(f"Unsupported content type: {content_type}")
                    
                results.append(result)
                
            except Exception as e:
                logger.error(f"Batch extraction failed for item: {e}")
                # Continue processing other items
                results.append({
                    "error": str(e),
                    "source": source,
                    "extracted_at": datetime.now(timezone.utc).isoformat()
                })
                
        return results