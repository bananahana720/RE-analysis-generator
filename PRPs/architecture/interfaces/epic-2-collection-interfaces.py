"""
Phoenix Real Estate System - Epic 2 Data Collection Engine Interfaces

This module defines the interfaces and contracts for the data collection layer,
including collectors, processors, adapters, and monitoring components. These
interfaces enable Epic 3 orchestration and Epic 4 quality monitoring while
building on Epic 1's foundation services.

Key Design Principles:
- Strategy pattern for different data sources (Maricopa, PhoenixMLS)
- Observer pattern for rate limiting and monitoring
- Adapter pattern for external data format conversion
- Factory pattern for collector creation and configuration
- Clean integration with Epic 1 foundation interfaces
"""

from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Union, Protocol, runtime_checkable,
    TypeVar, Generic, Awaitable, AsyncIterator, Callable
)
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio

# Import Epic 1 foundation interfaces
from .epic_1_foundation_interfaces import (
    ConfigProvider, PropertyRepository, Logger, MetricsCollector,
    BasePhoenixException, HealthCheckResult
)

# ==============================================================================
# Core Types and Enumerations
# ==============================================================================

class DataSourceType(Enum):
    """Supported data source types."""
    MARICOPA_API = "maricopa_api"
    PHOENIX_MLS = "phoenix_mls"
    COMBINED = "combined"

class CollectionStatus(Enum):
    """Collection operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

class DataQuality(Enum):
    """Data quality levels."""
    HIGH = "high"        # >95% completeness
    MEDIUM = "medium"    # 80-95% completeness
    LOW = "low"         # 60-80% completeness
    POOR = "poor"       # <60% completeness

@dataclass
class CollectionMetrics:
    """Metrics for a collection operation."""
    source: str
    zipcode: str
    start_time: datetime
    end_time: Optional[datetime] = None
    properties_found: int = 0
    properties_stored: int = 0
    errors_encountered: int = 0
    rate_limit_hits: int = 0
    processing_time_ms: float = 0.0
    data_quality_score: float = 0.0
    status: CollectionStatus = CollectionStatus.PENDING

@dataclass
class PropertyFeatures:
    """Structured property features extracted from data sources."""
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    garage_spaces: Optional[int] = None
    pool: Optional[bool] = None
    hoa_fee: Optional[float] = None

@dataclass
class PropertyPrice:
    """Property pricing information."""
    amount: float
    currency: str = "USD"
    price_type: str = "listing"  # listing, sale, assessment
    date: datetime = field(default_factory=datetime.utcnow)
    source: str = ""

@dataclass
class PropertyAddress:
    """Structured property address information."""
    street: str
    city: str
    state: str = "AZ"
    zipcode: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# ==============================================================================
# Data Collection Interfaces
# ==============================================================================

@runtime_checkable
class DataCollector(Protocol):
    """
    Base interface for all data collectors.
    
    This protocol defines the contract that all collectors (Maricopa API,
    PhoenixMLS scraper, etc.) must implement. Epic 3 orchestration depends
    on this interface for coordinating collection activities.
    """
    
    def get_source_name(self) -> str:
        """Return human-readable source name for logging and metrics."""
        ...
    
    def get_source_type(self) -> DataSourceType:
        """Return data source type for routing and configuration."""
        ...
    
    async def collect_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """
        Collect properties for given ZIP code.
        
        Args:
            zipcode: 5-digit ZIP code to collect
            
        Returns:
            List of raw property data dictionaries
            
        Raises:
            DataCollectionError: If collection fails
            RateLimitError: If rate limit exceeded
        """
        ...
    
    async def collect_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Collect detailed information for specific property.
        
        Args:
            property_id: External property identifier
            
        Returns:
            Detailed property data or None if not found
        """
        ...
    
    async def health_check(self) -> HealthCheckResult:
        """
        Check collector health and data source availability.
        
        Returns:
            Health check result with status and metrics
        """
        ...
    
    async def get_collection_metrics(self) -> Dict[str, Any]:
        """
        Get collection performance metrics.
        
        Returns:
            Metrics including success rates, timing, errors
        """
        ...

class BaseDataCollector(ABC):
    """
    Abstract base class for data collectors with common functionality.
    
    Provides standard implementation patterns for configuration, logging,
    repository access, and error handling that all collectors can inherit.
    """
    
    def __init__(
        self,
        config: ConfigProvider,
        repository: PropertyRepository,
        logger_name: str
    ) -> None:
        self.config = config
        self.repository = repository
        self.logger = self._create_logger(logger_name)
        self._rate_limiter: Optional['RateLimiter'] = None
        self._metrics: CollectionMetrics = CollectionMetrics(
            source=self.get_source_name(),
            zipcode="",
            start_time=datetime.utcnow()
        )
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return human-readable source name."""
        pass
    
    @abstractmethod
    def get_source_type(self) -> DataSourceType:
        """Return data source type."""
        pass
    
    @abstractmethod
    async def _fetch_raw_data(self, zipcode: str) -> List[Dict[str, Any]]:
        """Fetch raw data from external source (to be implemented by subclasses)."""
        pass
    
    @abstractmethod
    async def _adapt_property_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt raw data to internal property schema (to be implemented by subclasses)."""
        pass
    
    async def collect_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Standard collection workflow with error handling and metrics."""
        self._metrics = CollectionMetrics(
            source=self.get_source_name(),
            zipcode=zipcode,
            start_time=datetime.utcnow(),
            status=CollectionStatus.IN_PROGRESS
        )
        
        try:
            # Rate limiting
            if self._rate_limiter:
                await self._rate_limiter.wait_if_needed(self.get_source_name())
            
            # Fetch and process data
            raw_properties = await self._fetch_raw_data(zipcode)
            self._metrics.properties_found = len(raw_properties)
            
            processed_properties = []
            for raw_property in raw_properties:
                try:
                    adapted_property = await self._adapt_property_data(raw_property)
                    processed_properties.append(adapted_property)
                    self._metrics.properties_stored += 1
                    
                except Exception as e:
                    self._metrics.errors_encountered += 1
                    self.logger.warning(
                        "Failed to adapt property data",
                        extra={"error": str(e), "source": self.get_source_name()}
                    )
            
            self._metrics.end_time = datetime.utcnow()
            self._metrics.processing_time_ms = (
                self._metrics.end_time - self._metrics.start_time
            ).total_seconds() * 1000
            self._metrics.status = CollectionStatus.COMPLETED
            
            self.logger.info(
                "Collection completed",
                extra={
                    "source": self.get_source_name(),
                    "zipcode": zipcode,
                    "properties_found": self._metrics.properties_found,
                    "properties_stored": self._metrics.properties_stored,
                    "processing_time_ms": self._metrics.processing_time_ms
                }
            )
            
            return processed_properties
            
        except Exception as e:
            self._metrics.status = CollectionStatus.FAILED
            self._metrics.end_time = datetime.utcnow()
            
            self.logger.error(
                "Collection failed",
                extra={
                    "source": self.get_source_name(),
                    "zipcode": zipcode,
                    "error": str(e)
                }
            )
            raise DataCollectionError(
                f"Collection failed for {self.get_source_name()} zipcode {zipcode}",
                context={
                    "source": self.get_source_name(),
                    "zipcode": zipcode,
                    "metrics": self._metrics.__dict__
                },
                cause=e
            ) from e
    
    def _create_logger(self, logger_name: str) -> Logger:
        """Create logger instance (to be implemented with Epic 1 integration)."""
        # This would use Epic 1's get_logger function
        pass

# ==============================================================================
# Rate Limiting and Monitoring Interfaces
# ==============================================================================

@runtime_checkable
class RateLimitObserver(Protocol):
    """Observer interface for rate limiting events."""
    
    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        """Called when a request is made."""
        ...
    
    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        """Called when rate limit is encountered."""
        ...
    
    async def on_rate_limit_reset(self, source: str) -> None:
        """Called when rate limit resets."""
        ...

class RateLimiter(ABC):
    """
    Abstract rate limiter with observer pattern for monitoring.
    
    Implements rate limiting strategies with configurable limits and
    monitoring integration for Epic 4 quality assurance.
    """
    
    def __init__(self, requests_per_hour: int, logger_name: str) -> None:
        self.requests_per_hour = requests_per_hour
        self.logger = self._create_logger(logger_name)
        self._observers: List[RateLimitObserver] = []
        self._request_times: List[datetime] = []
        self._lock = asyncio.Lock()
    
    def add_observer(self, observer: RateLimitObserver) -> None:
        """Add rate limit observer for monitoring."""
        self._observers.append(observer)
    
    def remove_observer(self, observer: RateLimitObserver) -> None:
        """Remove rate limit observer."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    @abstractmethod
    async def wait_if_needed(self, source: str) -> float:
        """
        Wait if rate limit would be exceeded.
        
        Args:
            source: Source identifier for logging
            
        Returns:
            Time waited in seconds (0 if no wait needed)
        """
        pass
    
    async def _notify_observers_request_made(self, source: str) -> None:
        """Notify observers that a request was made."""
        timestamp = datetime.utcnow()
        for observer in self._observers:
            try:
                await observer.on_request_made(source, timestamp)
            except Exception as e:
                self.logger.warning(f"Observer notification failed: {e}")
    
    async def _notify_observers_rate_limit_hit(self, source: str, wait_time: float) -> None:
        """Notify observers that rate limit was hit."""
        for observer in self._observers:
            try:
                await observer.on_rate_limit_hit(source, wait_time)
            except Exception as e:
                self.logger.warning(f"Observer notification failed: {e}")
    
    def _create_logger(self, logger_name: str) -> Logger:
        """Create logger instance (to be implemented with Epic 1 integration)."""
        pass

# ==============================================================================
# Data Processing and Adaptation Interfaces
# ==============================================================================

@runtime_checkable
class DataAdapter(Protocol):
    """
    Interface for converting external data to internal property schema.
    
    Adapters handle the transformation of data from external sources (Maricopa API,
    PhoenixMLS) into the standardized internal property format used by Epic 1's
    PropertyRepository.
    """
    
    async def adapt_property(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert external property data to internal schema.
        
        Args:
            external_data: Raw data from external source
            
        Returns:
            Property data in internal schema format
            
        Raises:
            ValidationError: If external data cannot be adapted
        """
        ...
    
    def get_source_schema_version(self) -> str:
        """Return version of external source schema supported."""
        ...
    
    def get_supported_fields(self) -> List[str]:
        """Return list of fields this adapter can process."""
        ...

@runtime_checkable
class LLMProcessor(Protocol):
    """
    Interface for Local Large Language Model processing.
    
    Handles intelligent data extraction from unstructured text sources,
    particularly for PhoenixMLS web scraping where property descriptions
    need to be parsed into structured data.
    """
    
    async def extract_property_features(self, raw_text: str) -> PropertyFeatures:
        """
        Extract structured property features from unstructured text.
        
        Args:
            raw_text: Unstructured property description text
            
        Returns:
            Structured property features
            
        Raises:
            ProcessingError: If LLM processing fails
        """
        ...
    
    async def extract_price_information(self, raw_text: str) -> List[PropertyPrice]:
        """
        Extract price information from text.
        
        Args:
            raw_text: Text containing price information
            
        Returns:
            List of extracted price information
        """
        ...
    
    async def extract_address_components(self, raw_text: str) -> PropertyAddress:
        """
        Extract and structure address information.
        
        Args:
            raw_text: Text containing address information
            
        Returns:
            Structured address components
        """
        ...
    
    async def validate_extraction_quality(self, extracted_data: Dict[str, Any]) -> float:
        """
        Validate quality of extracted data.
        
        Args:
            extracted_data: Data extracted by LLM
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        ...
    
    async def health_check(self) -> HealthCheckResult:
        """Check LLM service health and availability."""
        ...

# ==============================================================================
# Collection Strategy and Factory Interfaces
# ==============================================================================

@runtime_checkable
class CollectionStrategy(Protocol):
    """
    Strategy interface for different collection approaches.
    
    Enables Epic 3 orchestration to choose between sequential, parallel,
    or mixed collection strategies based on configuration and requirements.
    """
    
    async def collect_multiple_zipcodes(
        self,
        collectors: List[DataCollector],
        zipcodes: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect data from multiple ZIP codes using strategy.
        
        Args:
            collectors: List of available collectors
            zipcodes: List of ZIP codes to collect
            
        Returns:
            Dictionary mapping ZIP codes to collected properties
        """
        ...
    
    def get_strategy_name(self) -> str:
        """Return strategy name for logging and configuration."""
        ...
    
    async def estimate_completion_time(
        self,
        collectors: List[DataCollector],
        zipcodes: List[str]
    ) -> timedelta:
        """Estimate time to complete collection with this strategy."""
        ...

class CollectorFactory(ABC):
    """
    Factory for creating data collector instances.
    
    Provides centralized creation of collectors with proper dependency injection
    and configuration management. Used by Epic 3 orchestration to initialize
    collection components.
    """
    
    @staticmethod
    @abstractmethod
    async def create_collector(
        source_type: DataSourceType,
        config: ConfigProvider,
        repository: PropertyRepository
    ) -> DataCollector:
        """
        Create collector instance for specified source type.
        
        Args:
            source_type: Type of data source to create collector for
            config: Configuration provider for collector setup
            repository: Repository for data storage
            
        Returns:
            Configured collector instance
            
        Raises:
            ConfigurationError: If collector cannot be configured
        """
        pass
    
    @staticmethod
    @abstractmethod
    async def get_available_collectors() -> List[DataSourceType]:
        """Get list of available collector types."""
        pass
    
    @staticmethod
    @abstractmethod
    async def validate_collector_config(
        source_type: DataSourceType,
        config: ConfigProvider
    ) -> bool:
        """Validate configuration for collector type."""
        pass

# ==============================================================================
# Monitoring and Quality Interfaces
# ==============================================================================

@runtime_checkable
class CollectionMonitor(Protocol):
    """
    Interface for monitoring collection operations.
    
    Provides monitoring capabilities used by Epic 4 quality assurance
    to track collection performance, data quality, and system health.
    """
    
    async def record_collection_start(
        self,
        source: str,
        zipcode: str,
        expected_count: Optional[int] = None
    ) -> None:
        """Record start of collection operation."""
        ...
    
    async def record_collection_complete(
        self,
        source: str,
        zipcode: str,
        collected_count: int,
        stored_count: int,
        duration_seconds: float,
        quality_score: float
    ) -> None:
        """Record completion of collection operation."""
        ...
    
    async def record_collection_error(
        self,
        source: str,
        zipcode: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Record collection error for analysis."""
        ...
    
    async def record_rate_limit_event(
        self,
        source: str,
        wait_time_seconds: float,
        requests_made: int
    ) -> None:
        """Record rate limiting event."""
        ...
    
    async def get_collection_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get collection summary for date range."""
        ...

@runtime_checkable
class DataQualityValidator(Protocol):
    """
    Interface for validating data quality.
    
    Provides data quality assessment capabilities used throughout the
    collection pipeline and by Epic 4 quality monitoring.
    """
    
    async def validate_property_data(self, property_data: Dict[str, Any]) -> bool:
        """
        Validate property data completeness and accuracy.
        
        Args:
            property_data: Property data to validate
            
        Returns:
            True if data meets quality standards
        """
        ...
    
    async def calculate_quality_score(self, property_data: Dict[str, Any]) -> float:
        """
        Calculate quality score for property data.
        
        Args:
            property_data: Property data to score
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        ...
    
    async def get_validation_errors(self, property_data: Dict[str, Any]) -> List[str]:
        """
        Get list of validation errors for property data.
        
        Args:
            property_data: Property data to validate
            
        Returns:
            List of validation error messages
        """
        ...
    
    async def validate_collection_batch(
        self,
        properties: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate entire collection batch and provide summary.
        
        Args:
            properties: List of properties to validate
            
        Returns:
            Validation summary with scores and error counts
        """
        ...

# ==============================================================================
# Exception Classes for Data Collection
# ==============================================================================

class DataCollectionError(BasePhoenixException):
    """Data collection operation errors."""
    
    def __init__(
        self,
        message: str,
        *,
        source: Optional[str] = None,
        zipcode: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if source:
            context['source'] = source
        if zipcode:
            context['zipcode'] = zipcode
        
        # Collection errors are often recoverable
        kwargs.setdefault('recoverable', True)
        kwargs.setdefault('retry_after_seconds', 300)
        
        super().__init__(message, context=context, **kwargs)

class ProcessingError(BasePhoenixException):
    """Data processing and LLM errors."""
    
    def __init__(
        self,
        message: str,
        *,
        processor: Optional[str] = None,
        input_data: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if processor:
            context['processor'] = processor
        if input_data:
            # Truncate input data for logging
            context['input_data'] = input_data[:200] + "..." if len(input_data) > 200 else input_data
        
        super().__init__(message, context=context, **kwargs)

class RateLimitError(DataCollectionError):
    """Rate limit exceeded errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('recoverable', True)
        kwargs.setdefault('retry_after_seconds', 3600)  # 1 hour
        super().__init__(message, **kwargs)

class ProxyError(DataCollectionError):
    """Proxy connection or rotation errors."""
    pass

class AdaptationError(BasePhoenixException):
    """Data adaptation and schema conversion errors."""
    
    def __init__(
        self,
        message: str,
        *,
        source_schema: Optional[str] = None,
        target_schema: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if source_schema:
            context['source_schema'] = source_schema
        if target_schema:
            context['target_schema'] = target_schema
        
        super().__init__(message, context=context, **kwargs)

# ==============================================================================
# Integration Contracts for Other Epics
# ==============================================================================

class Epic2ServiceProvider(ABC):
    """
    Service provider interface for Epic 2 data collection services.
    
    This interface defines what Epic 2 provides to Epic 3 orchestration
    and Epic 4 quality monitoring for integration purposes.
    """
    
    @property
    @abstractmethod
    def available_collectors(self) -> List[DataCollector]:
        """List of available data collectors."""
        pass
    
    @property
    @abstractmethod
    def collection_monitor(self) -> CollectionMonitor:
        """Collection monitoring interface."""
        pass
    
    @property
    @abstractmethod
    def data_quality_validator(self) -> DataQualityValidator:
        """Data quality validation interface."""
        pass
    
    @abstractmethod
    async def create_collector(
        self,
        source_type: DataSourceType,
        config: ConfigProvider,
        repository: PropertyRepository
    ) -> DataCollector:
        """Create collector instance for orchestration."""
        pass
    
    @abstractmethod
    async def get_collection_strategy(self, strategy_name: str) -> CollectionStrategy:
        """Get collection strategy for orchestration."""
        pass
    
    @abstractmethod
    async def health_check_all_collectors(self) -> Dict[str, HealthCheckResult]:
        """Perform health check on all collectors."""
        pass

# ==============================================================================
# Usage Examples and Documentation
# ==============================================================================

"""
Example Usage for Epic 3 (Automation & Orchestration):

```python
from phoenix_real_estate.collection import Epic2ServiceProvider, DataSourceType

class OrchestrationEngine:
    def __init__(
        self,
        foundation: Epic1ServiceProvider,
        collection: Epic2ServiceProvider
    ):
        self.config = foundation.config
        self.repository = foundation.repository
        self.logger = foundation.get_logger("automation.orchestration")
        self.collection = collection
    
    async def run_daily_collection(self) -> Dict[str, Any]:
        # Get available collectors from Epic 2
        collectors = []
        for source_type in [DataSourceType.MARICOPA_API, DataSourceType.PHOENIX_MLS]:
            try:
                collector = await self.collection.create_collector(
                    source_type, self.config, self.repository
                )
                collectors.append(collector)
            except Exception as e:
                self.logger.warning(f"Failed to create {source_type} collector: {e}")
        
        # Execute collection using Epic 2 strategy
        strategy = await self.collection.get_collection_strategy("sequential")
        zip_codes = self.config.get_required("TARGET_ZIP_CODES").split(",")
        
        results = await strategy.collect_multiple_zipcodes(collectors, zip_codes)
        
        return {
            "success": True,
            "collectors_used": len(collectors),
            "zip_codes_processed": len(zip_codes),
            "properties_collected": sum(len(props) for props in results.values())
        }
```

Example Usage for Epic 4 (Quality Assurance):

```python
from phoenix_real_estate.collection import Epic2ServiceProvider

class CollectionQualityMonitor:
    def __init__(
        self,
        foundation: Epic1ServiceProvider,
        collection: Epic2ServiceProvider
    ):
        self.config = foundation.config
        self.logger = foundation.get_logger("quality.collection")
        self.collection_monitor = collection.collection_monitor
        self.quality_validator = collection.data_quality_validator
    
    async def assess_collection_quality(self) -> Dict[str, Any]:
        # Check collector health
        health_results = await self.collection.health_check_all_collectors()
        
        # Get collection summary
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        summary = await self.collection_monitor.get_collection_summary(yesterday, now)
        
        # Calculate quality metrics
        overall_health = all(result.healthy for result in health_results.values())
        collection_success_rate = summary.get('success_rate', 0.0)
        data_quality_score = summary.get('avg_quality_score', 0.0)
        
        return {
            "overall_health": overall_health,
            "collection_success_rate": collection_success_rate,
            "data_quality_score": data_quality_score,
            "collector_health": {name: result.healthy for name, result in health_results.items()},
            "summary": summary
        }
```
"""