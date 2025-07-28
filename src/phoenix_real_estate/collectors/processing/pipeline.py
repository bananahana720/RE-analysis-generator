"""Data processing pipeline for property information extraction."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.foundation.utils.helpers import retry_async
from phoenix_real_estate.models.property import PropertyDetails

from .extractor import PropertyDataExtractor
from .validator import ProcessingValidator, ValidationResult


logger = get_logger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single property."""
    
    is_valid: bool
    property_data: Optional[PropertyDetails] = None
    validation_result: Optional[ValidationResult] = None
    source: Optional[str] = None
    processing_time: float = 0.0
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataProcessingPipeline:
    """Orchestrates the complete data processing workflow.
    
    This pipeline coordinates the extraction, validation, and storage of property data
    from various sources using LLM-powered extraction and configurable validation rules.
    """
    
    def __init__(self, config: ConfigProvider) -> None:
        """Initialize the data processing pipeline.
        
        Args:
            config: Configuration provider
        """
        self.config = config
        self.logger = get_logger("processing.pipeline")
        
        # Load configuration
        self.batch_size = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))('BATCH_SIZE', 10)
        self.max_concurrent = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))('MAX_CONCURRENT_PROCESSING', 5)
        self.processing_timeout = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))('PROCESSING_TIMEOUT', 60)
        self.metrics_enabled = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))('ENABLE_METRICS', True)
        self.retry_attempts = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))('RETRY_ATTEMPTS', 2)
        self.retry_delay = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))('RETRY_DELAY', 1.0)
        
        # Components
        self._extractor: Optional[PropertyDataExtractor] = None
        self._validator: Optional[ProcessingValidator] = None
        self._initialized = False
        
        # Metrics
        self._metrics = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'total_processing_time': 0.0,
            'total_confidence': 0.0,
            'errors_by_type': {}
        }
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        self.logger.info(
            "Pipeline initialized",
            extra={
                "batch_size": self.batch_size,
                "max_concurrent": self.max_concurrent,
                "processing_timeout": self.processing_timeout
            }
        )
    
    async def initialize(self) -> None:
        """Initialize pipeline components."""
        if self._initialized:
            return
        
        try:
            # Initialize extractor
            self._extractor = PropertyDataExtractor(self.config)
            await self._extractor.initialize()
            
            # Initialize validator
            validation_config = getattr(self.config, 'getattr', lambda k, d: getattr(self.config.settings, k, d))(
                'VALIDATION_CONFIG', None
            )
            self._validator = ProcessingValidator(validation_config)
            
            self._initialized = True
            self.logger.info("Pipeline initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline: {e}")
            raise ProcessingError(f"Pipeline initialization failed: {str(e)}") from e
    
    async def close(self) -> None:
        """Close pipeline and cleanup resources."""
        if self._extractor:
            await self._extractor.close()
        self._initialized = False
        self.logger.info("Pipeline closed")
    
    async def __aenter__(self) -> "DataProcessingPipeline":
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    def _ensure_initialized(self) -> None:
        """Ensure pipeline is initialized."""
        if not self._initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() or use as context manager.")
    
    async def process_html(
        self,
        html_content: str,
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> ProcessingResult:
        """Process single HTML content.
        
        Args:
            html_content: HTML content to process
            source: Data source identifier
            timeout: Processing timeout in seconds
            strict_validation: Whether to enforce strict validation
            
        Returns:
            ProcessingResult with extraction and validation results
        """
        self._ensure_initialized()
        
        if source not in ["phoenix_mls"]:
            raise ValueError(f"Unsupported source for HTML: {source}")
        
        start_time = time.time()
        result = ProcessingResult(is_valid=False, source=source)
        
        try:
            # Extract data with retry
            extraction_data = await retry_async(
                self._extractor.extract_from_html,
                html_content,
                source,
                timeout,
                strict_validation,
                max_retries=self.retry_attempts,
                delay=self.retry_delay
            )
            
            # Check if extraction returned data
            if extraction_data is None:
                raise ProcessingError("Extraction returned no data")
            
            # Convert to PropertyDetails
            property_data = PropertyDetails.from_extraction_result(extraction_data)
            result.property_data = property_data
            
            # Validate
            validation_result = self._validator.validate(property_data)
            result.validation_result = validation_result
            result.is_valid = validation_result.is_valid
            
            # Update metrics
            if self.metrics_enabled:
                self._update_metrics(result, validation_result)
            
        except asyncio.TimeoutError:
            result.error = f"Processing timeout after {timeout or self.processing_timeout} seconds"
            self.logger.error(result.error)
            raise
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Processing failed: {e}")
            if self.metrics_enabled:
                self._metrics['failed'] += 1
                self._metrics['total_processed'] += 1
                self._update_error_metrics(e)
            raise ProcessingError(f"Failed to process HTML: {str(e)}") from e
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    async def process_json(
        self,
        json_data: Union[Dict[str, Any], str],
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> ProcessingResult:
        """Process single JSON content.
        
        Args:
            json_data: JSON data to process
            source: Data source identifier
            timeout: Processing timeout in seconds
            strict_validation: Whether to enforce strict validation
            
        Returns:
            ProcessingResult with extraction and validation results
        """
        self._ensure_initialized()
        
        if source not in ["maricopa_county"]:
            raise ValueError(f"Unsupported source for JSON: {source}")
        
        start_time = time.time()
        result = ProcessingResult(is_valid=False, source=source)
        
        try:
            # Extract data with retry
            extraction_data = await retry_async(
                self._extractor.extract_from_json,
                json_data,
                source,
                timeout,
                strict_validation,
                max_retries=self.retry_attempts,
                delay=self.retry_delay
            )
            
            # Check if extraction returned data
            if extraction_data is None:
                raise ProcessingError("Extraction returned no data")
            
            # Convert to PropertyDetails
            property_data = PropertyDetails.from_extraction_result(extraction_data)
            result.property_data = property_data
            
            # Validate
            validation_result = self._validator.validate(property_data)
            result.validation_result = validation_result
            result.is_valid = validation_result.is_valid
            
            # Update metrics
            if self.metrics_enabled:
                self._update_metrics(result, validation_result)
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Processing failed: {e}")
            if self.metrics_enabled:
                self._metrics['failed'] += 1
                self._metrics['total_processed'] += 1
                self._update_error_metrics(e)
            raise ProcessingError(f"Failed to process JSON: {str(e)}") from e
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    async def process_batch_html(
        self,
        html_contents: List[str],
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> List[ProcessingResult]:
        """Process batch of HTML contents with concurrency control.
        
        Args:
            html_contents: List of HTML contents to process
            source: Data source identifier
            timeout: Processing timeout per item
            strict_validation: Whether to enforce strict validation
            
        Returns:
            List of ProcessingResult objects
        """
        self._ensure_initialized()
        
        results = []
        
        async def process_with_semaphore(content: str) -> ProcessingResult:
            """Process single item with semaphore control."""
            async with self._semaphore:
                try:
                    return await self.process_html(content, source, timeout, strict_validation)
                except Exception as e:
                    # Return error result instead of raising
                    result = ProcessingResult(
                        is_valid=False,
                        source=source,
                        error=str(e),
                        processing_time=0.0
                    )
                    # Metrics are already updated in process_html, don't double count
                    return result
        
        # Process in batches
        for i in range(0, len(html_contents), self.batch_size):
            batch = html_contents[i:i + self.batch_size]
            
            # Process batch concurrently
            batch_tasks = [process_with_semaphore(content) for content in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
            
            self.logger.info(
                f"Processed batch {i // self.batch_size + 1}",
                extra={
                    "batch_size": len(batch),
                    "successful": sum(1 for r in batch_results if r.is_valid),
                    "failed": sum(1 for r in batch_results if not r.is_valid)
                }
            )
        
        return results
    
    async def process_batch_json(
        self,
        json_items: List[Union[Dict[str, Any], str]],
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> List[ProcessingResult]:
        """Process batch of JSON items with concurrency control.
        
        Args:
            json_items: List of JSON items to process
            source: Data source identifier
            timeout: Processing timeout per item
            strict_validation: Whether to enforce strict validation
            
        Returns:
            List of ProcessingResult objects
        """
        self._ensure_initialized()
        
        results = []
        
        async def process_with_semaphore(item: Union[Dict[str, Any], str]) -> ProcessingResult:
            """Process single item with semaphore control."""
            async with self._semaphore:
                try:
                    return await self.process_json(item, source, timeout, strict_validation)
                except Exception as e:
                    # Return error result instead of raising
                    result = ProcessingResult(
                        is_valid=False,
                        source=source,
                        error=str(e),
                        processing_time=0.0
                    )
                    # Metrics are already updated in process_html, don't double count
                    return result
        
        # Process in batches
        for i in range(0, len(json_items), self.batch_size):
            batch = json_items[i:i + self.batch_size]
            
            # Process batch concurrently
            batch_tasks = [process_with_semaphore(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        
        return results
    
    def _update_metrics(self, result: ProcessingResult, validation_result: ValidationResult) -> None:
        """Update processing metrics.
        
        Args:
            result: Processing result
            validation_result: Validation result
        """
        self._metrics['total_processed'] += 1
        
        if result.is_valid:
            self._metrics['successful'] += 1
        else:
            self._metrics['failed'] += 1
        
        self._metrics['total_processing_time'] += result.processing_time
        
        if validation_result:
            self._metrics['total_confidence'] += validation_result.confidence_score
    
    def _update_error_metrics(self, error: Exception) -> None:
        """Update error metrics.
        
        Args:
            error: Exception that occurred
        """
        error_type = type(error).__name__
        self._metrics['errors_by_type'][error_type] = \
            self._metrics['errors_by_type'].get(error_type, 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics.
        
        Returns:
            Dictionary of metrics
        """
        total = self._metrics['total_processed']
        successful = self._metrics['successful']
        
        metrics = {
            'total_processed': total,
            'successful': successful,
            'failed': self._metrics['failed'],
            'success_rate': successful / total if total > 0 else 0,
            'average_processing_time': (
                self._metrics['total_processing_time'] / total if total > 0 else 0
            ),
            'average_confidence': (
                self._metrics['total_confidence'] / successful if successful > 0 else 0
            ),
            'errors_by_type': dict(self._metrics['errors_by_type'])
        }
        
        return metrics
    
    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self._metrics = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'total_processing_time': 0.0,
            'total_confidence': 0.0,
            'errors_by_type': {}
        }
        self.logger.info("Metrics cleared")
    
    async def process_mixed_batch(
        self,
        items: List[Dict[str, Any]],
        timeout: Optional[int] = None,
        strict_validation: bool = True
    ) -> List[ProcessingResult]:
        """Process batch of mixed content types.
        
        Args:
            items: List of items with 'content', 'source', and 'content_type' keys
            timeout: Processing timeout per item
            strict_validation: Whether to enforce strict validation
            
        Returns:
            List of ProcessingResult objects
            
        Example item:
            {
                'content': '<html>...</html>' or {...},
                'source': 'phoenix_mls' or 'maricopa_county',
                'content_type': 'html' or 'json'
            }
        """
        self._ensure_initialized()
        
        results = []
        
        async def process_item(item: Dict[str, Any]) -> ProcessingResult:
            """Process single mixed item."""
            content = item.get('content')
            source = item.get('source')
            content_type = item.get('content_type')
            
            if not all([content, source, content_type]):
                return ProcessingResult(
                    is_valid=False,
                    error="Missing required fields: content, source, or content_type",
                    source=source
                )
            
            async with self._semaphore:
                try:
                    if content_type == 'html':
                        return await self.process_html(content, source, timeout, strict_validation)
                    elif content_type == 'json':
                        return await self.process_json(content, source, timeout, strict_validation)
                    else:
                        return ProcessingResult(
                            is_valid=False,
                            error=f"Unsupported content type: {content_type}",
                            source=source
                        )
                except Exception as e:
                    return ProcessingResult(
                        is_valid=False,
                        source=source,
                        error=str(e),
                        processing_time=0.0
                    )
        
        # Process all items concurrently with semaphore control
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks)
        
        return results