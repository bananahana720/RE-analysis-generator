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

        # Load configuration using config.get_typed
        self.batch_size = config.get_typed("BATCH_SIZE", int, default=10)
        self.max_concurrent = config.get_typed("MAX_CONCURRENT_PROCESSING", int, default=5)
        self.processing_timeout = config.get_typed("PROCESSING_TIMEOUT", int, default=60)
        self.metrics_enabled = config.get_typed("ENABLE_METRICS", bool, default=True)
        self.retry_attempts = config.get_typed("RETRY_ATTEMPTS", int, default=2)
        self.retry_delay = config.get_typed("RETRY_DELAY", float, default=1.0)

        # Performance features
        self.cache_enabled = config.get_typed("CACHE_ENABLED", bool, default=True)
        self.resource_monitoring_enabled = config.get_typed(
            "RESOURCE_MONITORING_ENABLED", bool, default=True
        )
        self.adaptive_batch_sizing = config.get_typed("ADAPTIVE_BATCH_SIZING", bool, default=True)

        # Components
        self._extractor: Optional[PropertyDataExtractor] = None
        self._validator: Optional[ProcessingValidator] = None
        self._cache_manager: Optional[Any] = None
        self._resource_monitor: Optional[Any] = None
        self._batch_optimizer: Optional[Any] = None
        self._initialized = False

        # Metrics
        self._metrics = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "total_processing_time": 0.0,
            "total_confidence": 0.0,
            "errors_by_type": {},
        }

        # Concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        self.logger.info(
            "Pipeline initialized",
            extra={
                "batch_size": self.batch_size,
                "max_concurrent": self.max_concurrent,
                "processing_timeout": self.processing_timeout,
                "cache_enabled": self.cache_enabled,
                "resource_monitoring": self.resource_monitoring_enabled,
            },
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
            validation_config = self.config.get("VALIDATION_CONFIG", None)
            self._validator = ProcessingValidator(validation_config)

            # Initialize cache if enabled
            if self.cache_enabled:
                from .cache import CacheManager, CacheConfig

                cache_config = CacheConfig(
                    enabled=True,
                    ttl_hours=self.config.get_typed("CACHE_TTL_HOURS", float, default=24),
                    max_size_mb=self.config.get_typed("CACHE_MAX_SIZE_MB", float, default=100),
                    backend=self.config.get("CACHE_BACKEND", "memory"),
                )
                self._cache_manager = CacheManager(cache_config)
                await self._cache_manager.initialize()

                # Inject cache into extractor's LLM client
                if hasattr(self._extractor, "_client"):
                    self._extractor._client._cache_manager = self._cache_manager

            # Initialize resource monitor if enabled
            if self.resource_monitoring_enabled:
                from .monitoring import ResourceMonitor, ResourceLimits

                resource_limits = ResourceLimits(
                    max_memory_mb=self.config.get_typed("MAX_MEMORY_MB", int, default=1024),
                    max_cpu_percent=self.config.get_typed("MAX_CPU_PERCENT", int, default=80),
                    max_concurrent_requests=self.max_concurrent,
                )
                self._resource_monitor = ResourceMonitor(resource_limits)
                await self._resource_monitor.start()

            # Initialize batch optimizer if enabled
            if self.adaptive_batch_sizing:
                from .performance import BatchSizeOptimizer

                self._batch_optimizer = BatchSizeOptimizer(
                    initial_size=self.batch_size,
                    min_size=1,
                    max_size=self.config.get_typed("MAX_BATCH_SIZE", int, default=100),
                )

            self._initialized = True
            self.logger.info("Pipeline initialized successfully with performance features")

        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline: {e}")
            raise ProcessingError(f"Pipeline initialization failed: {str(e)}") from e

    async def close(self) -> None:
        """Close pipeline and cleanup resources."""
        if self._extractor:
            await self._extractor.close()

        if self._cache_manager:
            await self._cache_manager.close()

        if self._resource_monitor:
            await self._resource_monitor.stop()

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
            raise RuntimeError(
                "Pipeline not initialized. Call initialize() or use as context manager."
            )

    async def process_html(
        self,
        html_content: str,
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True,
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
                delay=self.retry_delay,
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
                self._metrics["failed"] += 1
                self._metrics["total_processed"] += 1
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
        strict_validation: bool = True,
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
                delay=self.retry_delay,
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
                self._metrics["failed"] += 1
                self._metrics["total_processed"] += 1
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
        strict_validation: bool = True,
    ) -> List[ProcessingResult]:
        """Process batch of HTML contents with concurrency control and dynamic sizing.

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

        async def process_with_monitoring(content: str) -> ProcessingResult:
            """Process single item with resource monitoring."""
            operation_id = f"process_{id(content)}"

            # Check resource availability
            if self._resource_monitor:
                if not await self._resource_monitor.check_resource_availability(operation_id):
                    await asyncio.sleep(1)  # Brief wait before retry
                    if not await self._resource_monitor.check_resource_availability(operation_id):
                        return ProcessingResult(
                            is_valid=False,
                            source=source,
                            error="Insufficient resources",
                            processing_time=0.0,
                        )

            async with self._semaphore:
                try:
                    if self._resource_monitor:
                        await self._resource_monitor.track_operation_start(operation_id)

                    result = await self.process_html(content, source, timeout, strict_validation)

                    if self._resource_monitor:
                        await self._resource_monitor.track_operation_end(operation_id)

                    return result
                except Exception as e:
                    if self._resource_monitor:
                        await self._resource_monitor.release_resources(operation_id)

                    # Return error result instead of raising
                    result = ProcessingResult(
                        is_valid=False, source=source, error=str(e), processing_time=0.0
                    )
                    return result

        # Process in dynamically sized batches
        current_batch_size = self.batch_size
        if self._batch_optimizer:
            current_batch_size = self._batch_optimizer.get_optimal_batch_size()
        if self._resource_monitor:
            # Further adjust based on current resources
            recommended_size = self._resource_monitor.get_recommended_batch_size()
            current_batch_size = min(current_batch_size, recommended_size)

        for i in range(0, len(html_contents), current_batch_size):
            batch = html_contents[i : i + current_batch_size]
            batch_start = time.time()

            # Process batch concurrently
            batch_tasks = [process_with_monitoring(content) for content in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)

            batch_duration = time.time() - batch_start
            successful_count = sum(1 for r in batch_results if r.is_valid)

            # Record performance for optimization
            if self._batch_optimizer:
                self._batch_optimizer.record_batch_performance(
                    batch_size=len(batch),
                    duration=batch_duration,
                    success_rate=successful_count / len(batch) if batch else 0,
                    memory_usage_mb=0,  # Will be filled by resource monitor
                )

            self.logger.info(
                f"Processed batch {i // current_batch_size + 1}",
                extra={
                    "batch_size": len(batch),
                    "successful": successful_count,
                    "failed": sum(1 for r in batch_results if not r.is_valid),
                    "duration": batch_duration,
                    "per_item_time": batch_duration / len(batch) if batch else 0,
                },
            )

            # Update batch size for next iteration if adaptive
            # FIXED: Disabled adaptive batch sizing mid-loop to prevent duplicate processing
            # if self._batch_optimizer and self.adaptive_batch_sizing:
            #     current_batch_size = self._batch_optimizer.get_optimal_batch_size()
        return results

    async def process_batch_json(
        self,
        json_items: List[Union[Dict[str, Any], str]],
        source: str,
        timeout: Optional[int] = None,
        strict_validation: bool = True,
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
                        is_valid=False, source=source, error=str(e), processing_time=0.0
                    )
                    # Metrics are already updated in process_html, don't double count
                    return result

        # Process in batches
        for i in range(0, len(json_items), self.batch_size):
            batch = json_items[i : i + self.batch_size]

            # Process batch concurrently
            batch_tasks = [process_with_semaphore(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)

        return results

    def _update_metrics(
        self, result: ProcessingResult, validation_result: ValidationResult
    ) -> None:
        """Update processing metrics.

        Args:
            result: Processing result
            validation_result: Validation result
        """
        self._metrics["total_processed"] += 1

        if result.is_valid:
            self._metrics["successful"] += 1
        else:
            self._metrics["failed"] += 1

        self._metrics["total_processing_time"] += result.processing_time

        if validation_result:
            self._metrics["total_confidence"] += validation_result.confidence_score

    def _update_error_metrics(self, error: Exception) -> None:
        """Update error metrics.

        Args:
            error: Exception that occurred
        """
        error_type = type(error).__name__
        self._metrics["errors_by_type"][error_type] = (
            self._metrics["errors_by_type"].get(error_type, 0) + 1
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics including performance data.

        Returns:
            Dictionary of metrics
        """
        total = self._metrics["total_processed"]
        successful = self._metrics["successful"]

        metrics = {
            "total_processed": total,
            "successful": successful,
            "failed": self._metrics["failed"],
            "success_rate": successful / total if total > 0 else 0,
            "average_processing_time": (
                self._metrics["total_processing_time"] / total if total > 0 else 0
            ),
            "average_confidence": (
                self._metrics["total_confidence"] / successful if successful > 0 else 0
            ),
            "errors_by_type": dict(self._metrics["errors_by_type"]),
        }

        # Add cache metrics if available
        if self._cache_manager:
            cache_metrics = self._cache_manager.get_metrics()
            metrics["cache"] = {
                "hit_rate": cache_metrics.get("hit_rate", 0),
                "hits": cache_metrics.get("hits", 0),
                "misses": cache_metrics.get("misses", 0),
                "entries": cache_metrics.get("entries", 0),
                "memory_used_mb": cache_metrics.get("memory_used_mb", 0),
            }

        # Add resource metrics if available
        if self._resource_monitor:
            resource_metrics = asyncio.run(self._resource_monitor.get_metrics())
            metrics["resources"] = {
                "memory_mb": resource_metrics.get("memory_mb", 0),
                "memory_percent": resource_metrics.get("memory_percent", 0),
                "cpu_percent": resource_metrics.get("cpu_percent", 0),
                "active_operations": resource_metrics.get("active_operations", 0),
            }

        # Add batch optimization metrics if available
        if self._batch_optimizer:
            metrics["batch_optimization"] = {
                "current_batch_size": self._batch_optimizer.current_size,
                "optimal_batch_size": self._batch_optimizer.get_optimal_batch_size(),
            }

        return metrics

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self._metrics = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "total_processing_time": 0.0,
            "total_confidence": 0.0,
            "errors_by_type": {},
        }
        self.logger.info("Metrics cleared")

    async def process_mixed_batch(
        self,
        items: List[Dict[str, Any]],
        timeout: Optional[int] = None,
        strict_validation: bool = True,
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
            content = item.get("content")
            source = item.get("source")
            content_type = item.get("content_type")

            if not all([content, source, content_type]):
                return ProcessingResult(
                    is_valid=False,
                    error="Missing required fields: content, source, or content_type",
                    source=source,
                )

            async with self._semaphore:
                try:
                    if content_type == "html":
                        return await self.process_html(content, source, timeout, strict_validation)
                    elif content_type == "json":
                        return await self.process_json(content, source, timeout, strict_validation)
                    else:
                        return ProcessingResult(
                            is_valid=False,
                            error=f"Unsupported content type: {content_type}",
                            source=source,
                        )
                except Exception as e:
                    return ProcessingResult(
                        is_valid=False, source=source, error=str(e), processing_time=0.0
                    )

        # Process all items concurrently with semaphore control
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks)

        return results
