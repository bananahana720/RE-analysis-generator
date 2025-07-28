"""Processing Integrator for bridging collectors and LLM processing.

This module provides the integration layer between Epic 1 data collectors
(Maricopa API, Phoenix MLS) and Epic 2 LLM processing pipeline.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from phoenix_real_estate.collectors.processing.pipeline import (
    DataProcessingPipeline,
    ProcessingResult,
)
from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository, get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.models.property import PropertyDetails


logger = get_logger(__name__)


class IntegrationMode(Enum):
    """Processing integration modes."""
    
    BATCH = "batch"
    STREAMING = "streaming"
    INDIVIDUAL = "individual"


@dataclass
class IntegrationResult:
    """Result of processing a single property through the integration."""
    
    success: bool
    property_id: str
    source: str
    property_data: Optional[PropertyDetails] = None
    saved_to_db: bool = False
    processing_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchIntegrationResult:
    """Result of processing a batch of properties."""
    
    total_processed: int
    successful: int
    failed: int
    processing_time: float
    results: List[IntegrationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProcessingIntegrator:
    """Integrates data collectors with LLM processing pipeline.
    
    This class serves as the bridge between Epic 1 collectors and Epic 2
    processing, handling:
    - Data collection from various sources
    - LLM processing through the pipeline
    - Database storage of validated results
    - Metrics and monitoring
    - Error handling and recovery
    
    Supports both batch and streaming modes for efficient processing.
    """
    
    def __init__(
        self,
        config: ConfigProvider,
        repository: PropertyRepository,
        pipeline: Optional[DataProcessingPipeline] = None,
    ) -> None:
        """Initialize the processing integrator.
        
        Args:
            config: Configuration provider
            repository: Property repository for database operations
            pipeline: Optional processing pipeline (will create if not provided)
        """
        self.config = config
        self.repository = repository
        self.logger = logger
        
        # Initialize pipeline if not provided
        self.pipeline = pipeline or DataProcessingPipeline(config)
        
        # Configuration
        self.batch_size = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))(
            'INTEGRATION_BATCH_SIZE', 10
        )
        self.save_invalid = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))(
            'SAVE_INVALID_PROPERTIES', False
        )
        self.strict_validation = getattr(config, 'getattr', lambda k, d: getattr(config.settings, k, d))(
            'STRICT_VALIDATION', True
        )
        
        # Metrics
        self._metrics = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'saved_to_db': 0,
            'total_processing_time': 0.0,
            'sources': {},
            'errors': []
        }
        
        self._initialized = False
        
        self.logger.info(
            "ProcessingIntegrator initialized",
            extra={
                "batch_size": self.batch_size,
                "save_invalid": self.save_invalid,
                "strict_validation": self.strict_validation
            }
        )
    
    async def initialize(self) -> None:
        """Initialize the integrator and its components."""
        if self._initialized:
            return
        
        try:
            # Initialize pipeline
            await self.pipeline.initialize()
            
            self._initialized = True
            self.logger.info("ProcessingIntegrator initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize integrator: {e}")
            raise ProcessingError(f"Integrator initialization failed: {str(e)}") from e
    
    async def close(self) -> None:
        """Close integrator and cleanup resources."""
        if self.pipeline:
            await self.pipeline.close()
        self._initialized = False
        self.logger.info("ProcessingIntegrator closed")
    
    async def __aenter__(self) -> "ProcessingIntegrator":
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    def _ensure_initialized(self) -> None:
        """Ensure integrator is initialized."""
        if not self._initialized:
            raise RuntimeError("Integrator not initialized. Call initialize() or use as context manager.")
    
    async def process_maricopa_property(
        self,
        collector: MaricopaAPICollector,
        property_id: str,
        save_to_db: bool = True
    ) -> IntegrationResult:
        """Process a single property from Maricopa collector.
        
        Args:
            collector: Maricopa API collector instance
            property_id: Property ID to collect and process
            save_to_db: Whether to save to database
            
        Returns:
            IntegrationResult with processing outcome
        """
        self._ensure_initialized()
        start_time = time.time()
        
        result = IntegrationResult(
            success=False,
            property_id=property_id,
            source="maricopa_county"
        )
        
        try:
            # Collect raw data
            self.logger.info(f"Collecting property {property_id} from Maricopa")
            raw_data = await collector.collect_property_details(property_id)
            
            if not raw_data:
                raise ProcessingError(f"No data found for property {property_id}")
            
            # Process through LLM pipeline
            self.logger.info(f"Processing property {property_id} through LLM pipeline")
            processing_result = await self.pipeline.process_json(
                raw_data,
                "maricopa_county",
                strict_validation=self.strict_validation
            )
            
            # Update result
            result.property_data = processing_result.property_data
            result.success = processing_result.is_valid
            
            # Save to database if requested and valid
            if save_to_db and (processing_result.is_valid or self.save_invalid):
                await self._save_to_database(processing_result.property_data)
                result.saved_to_db = True
            
            # Update metrics
            self._update_metrics(result, processing_result)
            
            self.logger.info(
                f"Successfully processed property {property_id}",
                extra={
                    "property_id": property_id,
                    "valid": processing_result.is_valid,
                    "saved": result.saved_to_db
                }
            )
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Failed to process property {property_id}: {e}")
            self._metrics['failed'] += 1
            self._metrics['total_processed'] += 1
            self._metrics['errors'].append(f"{property_id}: {str(e)}")
        
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    async def process_phoenix_mls_property(
        self,
        scraper: PhoenixMLSScraper,
        property_id: str,
        save_to_db: bool = True
    ) -> IntegrationResult:
        """Process a single property from Phoenix MLS scraper.
        
        Args:
            scraper: Phoenix MLS scraper instance
            property_id: Property ID (MLS number) to scrape and process
            save_to_db: Whether to save to database
            
        Returns:
            IntegrationResult with processing outcome
        """
        self._ensure_initialized()
        start_time = time.time()
        
        result = IntegrationResult(
            success=False,
            property_id=property_id,
            source="phoenix_mls"
        )
        
        try:
            # Scrape property HTML
            self.logger.info(f"Scraping property {property_id} from Phoenix MLS")
            html_content = await scraper.scrape_property(property_id)
            
            if not html_content:
                raise ProcessingError(f"No content scraped for property {property_id}")
            
            # Process through LLM pipeline
            self.logger.info(f"Processing property {property_id} through LLM pipeline")
            processing_result = await self.pipeline.process_html(
                html_content,
                "phoenix_mls",
                strict_validation=self.strict_validation
            )
            
            # Update result
            result.property_data = processing_result.property_data
            result.success = processing_result.is_valid
            
            # Save to database if requested and valid
            if save_to_db and (processing_result.is_valid or self.save_invalid):
                await self._save_to_database(processing_result.property_data)
                result.saved_to_db = True
            
            # Update metrics
            self._update_metrics(result, processing_result)
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Failed to process property {property_id}: {e}")
            self._metrics['failed'] += 1
            self._metrics['total_processed'] += 1
            self._metrics['errors'].append(f"{property_id}: {str(e)}")
        
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    async def process_maricopa_batch(
        self,
        collector: MaricopaAPICollector,
        zip_codes: Optional[List[str]] = None,
        max_properties: Optional[int] = None,
        save_to_db: bool = True
    ) -> BatchIntegrationResult:
        """Process a batch of properties from Maricopa collector.
        
        Args:
            collector: Maricopa API collector instance
            zip_codes: List of ZIP codes to collect
            max_properties: Maximum number of properties to process
            save_to_db: Whether to save to database
            
        Returns:
            BatchIntegrationResult with batch processing outcome
        """
        self._ensure_initialized()
        start_time = time.time()
        
        batch_result = BatchIntegrationResult(
            total_processed=0,
            successful=0,
            failed=0,
            processing_time=0.0
        )
        
        try:
            # Collect properties
            self.logger.info(f"Collecting properties from ZIP codes: {zip_codes}")
            raw_properties = await collector.collect_by_zip_codes(
                zip_codes=zip_codes or [],
                max_per_zip=max_properties,
                save_to_repository=False  # We'll save after processing
            )
            
            if not raw_properties:
                self.logger.warning("No properties collected")
                return batch_result
            
            # Process in batches through pipeline
            self.logger.info(f"Processing {len(raw_properties)} properties through LLM pipeline")
            processing_results = await self.pipeline.process_batch_json(
                raw_properties,
                "maricopa_county",
                strict_validation=self.strict_validation
            )
            
            # Process results and save to database
            valid_properties = []
            for proc_result in processing_results:
                integration_result = IntegrationResult(
                    success=proc_result.is_valid,
                    property_id=proc_result.property_data.property_id if proc_result.property_data else "unknown",
                    source="maricopa_county",
                    property_data=proc_result.property_data,
                    processing_time=proc_result.processing_time,
                    error=proc_result.error
                )
                
                batch_result.results.append(integration_result)
                batch_result.total_processed += 1
                
                if proc_result.is_valid:
                    batch_result.successful += 1
                    if save_to_db and proc_result.property_data:
                        valid_properties.append(proc_result.property_data)
                else:
                    batch_result.failed += 1
                    if proc_result.error:
                        batch_result.errors.append(proc_result.error)
            
            # Bulk save valid properties
            if valid_properties and save_to_db:
                saved_count = await self._bulk_save_to_database(valid_properties)
                self.logger.info(f"Saved {saved_count} properties to database")
                
                # Update saved status
                for result in batch_result.results:
                    if result.success:
                        result.saved_to_db = True
            
            # Update metrics
            self._metrics['total_processed'] += batch_result.total_processed
            self._metrics['successful'] += batch_result.successful
            self._metrics['failed'] += batch_result.failed
            
        except Exception as e:
            batch_result.errors.append(f"Batch processing error: {str(e)}")
            self.logger.error(f"Batch processing failed: {e}")
        
        finally:
            batch_result.processing_time = time.time() - start_time
            self._metrics['total_processing_time'] += batch_result.processing_time
        
        return batch_result
    
    async def process_stream(
        self,
        collector: Union[MaricopaAPICollector, PhoenixMLSScraper],
        mode: IntegrationMode = IntegrationMode.STREAMING,
        **kwargs
    ) -> AsyncIterator[IntegrationResult]:
        """Process properties in streaming mode.
        
        Args:
            collector: Data collector instance
            mode: Integration mode
            **kwargs: Additional arguments for collector
            
        Yields:
            IntegrationResult for each processed property
        """
        self._ensure_initialized()
        
        if not hasattr(collector, 'stream_properties'):
            raise ValueError(f"Collector {type(collector).__name__} does not support streaming")
        
        # Stream properties from collector
        async for raw_data in collector.stream_properties(**kwargs):
            try:
                # Determine source and content type
                source = collector.get_source_name() if hasattr(collector, 'get_source_name') else "unknown"
                
                # Process based on content type
                if source == "maricopa_county":
                    processing_result = await self.pipeline.process_json(
                        raw_data,
                        source,
                        strict_validation=self.strict_validation
                    )
                elif source == "phoenix_mls":
                    processing_result = await self.pipeline.process_html(
                        raw_data,
                        source,
                        strict_validation=self.strict_validation
                    )
                else:
                    raise ValueError(f"Unknown source: {source}")
                
                # Create integration result
                result = IntegrationResult(
                    success=processing_result.is_valid,
                    property_id=processing_result.property_data.property_id if processing_result.property_data else "unknown",
                    source=source,
                    property_data=processing_result.property_data,
                    processing_time=processing_result.processing_time
                )
                
                # Save if valid
                if result.success and result.property_data:
                    await self._save_to_database(result.property_data)
                    result.saved_to_db = True
                
                # Update metrics
                self._update_metrics(result, processing_result)
                
                yield result
                
            except Exception as e:
                self.logger.error(f"Stream processing error: {e}")
                yield IntegrationResult(
                    success=False,
                    property_id="unknown",
                    source=source,
                    error=str(e)
                )
    
    def _convert_to_property_schema(self, property_details: PropertyDetails) -> Dict[str, Any]:
        """Convert PropertyDetails to database Property schema dict.
        
        Args:
            property_details: PropertyDetails from LLM processing
            
        Returns:
            Dict representing Property for database storage
        """
        # Create address object
        address = {
            "street": property_details.street or property_details.address,
            "city": property_details.city or "Phoenix",
            "state": property_details.state or "AZ",
            "zipcode": property_details.zip_code or "85001",
            "county": "Maricopa"
        }
        
        # Create features object
        features = {
            "bedrooms": property_details.bedrooms,
            "bathrooms": property_details.bathrooms,
            "square_feet": property_details.square_feet,
            "lot_size_sqft": property_details.lot_size,
            "year_built": property_details.year_built
        }
        
        # Map source to DataSource enum
        source_map = {
            "maricopa_county": "maricopa_county",
            "phoenix_mls": "phoenix_mls"
        }
        
        # Map property type
        property_type_map = {
            "single family": "single_family",
            "single_family": "single_family",
            "townhouse": "townhouse",
            "condo": "condo",
            "apartment": "apartment",
            "manufactured": "manufactured",
            "vacant_land": "vacant_land",
            "commercial": "commercial"
        }
        property_type = property_type_map.get(
            (property_details.property_type or "").lower().replace("-", "_"),
            "other"
        )
        
        # Build property dict
        property_dict = {
            "property_id": property_details.property_id,
            "address": address,
            "property_type": property_type,
            "features": features,
            "current_price": float(property_details.price) if property_details.price else None,
            "metadata": {
                "parcel_number": property_details.parcel_number,
                "mls_number": property_details.mls_number,
                "owner_name": property_details.owner_name,
                "description": property_details.description,
                "listing_status": property_details.listing_status,
                "extraction_confidence": property_details.extraction_confidence,
                "validation_errors": property_details.validation_errors,
                "extracted_at": property_details.extracted_at.isoformat() if property_details.extracted_at else None,
                "last_updated": (property_details.last_updated or datetime.now(UTC)).isoformat(),
                "source": source_map.get(property_details.source, property_details.source)
            }
        }
        
        return property_dict
    
    async def _save_to_database(self, property_details: PropertyDetails) -> bool:
        """Save a single property to the database.
        
        Args:
            property_details: Property details to save
            
        Returns:
            True if saved successfully
        """
        try:
            property_obj = self._convert_to_property_schema(property_details)
            await self.repository.save(property_obj)
            self._metrics['saved_to_db'] += 1
            return True
        except Exception as e:
            self.logger.error(f"Failed to save property {property_details.property_id}: {e}")
            return False
    
    async def _bulk_save_to_database(self, properties: List[PropertyDetails]) -> int:
        """Bulk save properties to the database.
        
        Args:
            properties: List of property details to save
            
        Returns:
            Number of properties saved successfully
        """
        try:
            property_objects = [
                self._convert_to_property_schema(prop)
                for prop in properties
            ]
            
            saved_count = await self.repository.bulk_save(property_objects)
            self._metrics['saved_to_db'] += saved_count
            return saved_count
            
        except Exception as e:
            self.logger.error(f"Failed to bulk save {len(properties)} properties: {e}")
            return 0
    
    def _update_metrics(self, result: IntegrationResult, processing_result: ProcessingResult) -> None:
        """Update integration metrics.
        
        Args:
            result: Integration result
            processing_result: Processing pipeline result
        """
        self._metrics['total_processed'] += 1
        
        if result.success:
            self._metrics['successful'] += 1
        else:
            self._metrics['failed'] += 1
        
        self._metrics['total_processing_time'] += result.processing_time
        
        # Update source metrics
        source = result.source
        if source not in self._metrics['sources']:
            self._metrics['sources'][source] = 0
        self._metrics['sources'][source] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current integration metrics.
        
        Returns:
            Dictionary of metrics
        """
        total = self._metrics['total_processed']
        
        return {
            'total_processed': total,
            'successful': self._metrics['successful'],
            'failed': self._metrics['failed'],
            'saved_to_db': self._metrics['saved_to_db'],
            'success_rate': self._metrics['successful'] / total if total > 0 else 0,
            'average_processing_time': (
                self._metrics['total_processing_time'] / total if total > 0 else 0
            ),
            'sources': dict(self._metrics['sources']),
            'error_count': len(self._metrics['errors']),
            'recent_errors': self._metrics['errors'][-10:]  # Last 10 errors
        }
    
    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self._metrics = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'saved_to_db': 0,
            'total_processing_time': 0.0,
            'sources': {},
            'errors': []
        }
        self.logger.info("Integration metrics cleared")