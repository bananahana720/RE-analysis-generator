# Epic 2: Data Collection Engine

## Executive Summary

### Purpose
Build a robust, scalable data collection engine that integrates seamlessly with Epic 1's foundation infrastructure to gather real estate data from multiple sources. This epic implements intelligent data collection strategies with anti-detection capabilities, rate limiting, and local LLM processing while maintaining strict budget constraints and legal compliance.

### Scope
- Maricopa County API client with intelligent rate limiting
- PhoenixMLSSearch.com web scraper with anti-detection
- Local LLM integration for data extraction and processing
- Proxy management and rotation system
- Data pipeline orchestration with error recovery
- Collection monitoring and metrics

### Dependencies
**Epic 1: Foundation Infrastructure** (REQUIRED)
- `phoenix_real_estate.foundation.database.repositories.PropertyRepository`
- `phoenix_real_estate.foundation.config.base.ConfigProvider`
- `phoenix_real_estate.foundation.logging.factory.get_logger`
- `phoenix_real_estate.foundation.utils.exceptions.*`
- `phoenix_real_estate.foundation.database.schema.Property`

### Budget Alignment
- Proxy Service (Webshare.io): $5/month (100GB/month)
- Local LLM Processing: $0/month (Ollama + Llama3.2:latest) ✅ **OPERATIONAL**
- API Usage: $0/month (within Maricopa County limits)
- Total: $5/month (within $1-25/month budget)

## Technical Architecture

### Core Design Patterns

#### Strategy Pattern for Data Sources
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.database.repositories import PropertyRepository

class DataCollector(ABC):
    """Base strategy for collecting real estate data."""
    
    def __init__(
        self, 
        config: ConfigProvider, 
        repository: PropertyRepository,
        logger_name: str
    ) -> None:
        self.config = config
        self.repository = repository
        self.logger = get_logger(logger_name)
        self._rate_limiter: Optional[RateLimiter] = None
    
    @abstractmethod
    async def collect_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """Collect properties for given ZIP code."""
        pass
    
    @abstractmethod
    async def collect_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Collect detailed information for specific property."""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return human-readable source name."""
        pass
```

#### Observer Pattern for Rate Limiting
```python
from typing import Protocol, List
from datetime import datetime

class RateLimitObserver(Protocol):
    """Observer for rate limiting events."""
    
    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        """Called when a request is made."""
        ...
    
    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        """Called when rate limit is encountered."""
        ...
    
    async def on_rate_limit_reset(self, source: str) -> None:
        """Called when rate limit resets."""
        ...

class RateLimiter:
    """Rate limiter with observer pattern for monitoring."""
    
    def __init__(self, requests_per_hour: int, logger_name: str) -> None:
        self.requests_per_hour = requests_per_hour
        self.logger = get_logger(logger_name)
        self._observers: List[RateLimitObserver] = []
        self._request_times: List[datetime] = []
    
    def add_observer(self, observer: RateLimitObserver) -> None:
        """Add rate limit observer."""
        self._observers.append(observer)
    
    async def wait_if_needed(self, source: str) -> float:
        """Wait if rate limit would be exceeded."""
        # Implementation uses Epic 1's logging for metrics
        pass
```

#### Adapter Pattern for External Data
```python
from phoenix_real_estate.foundation.database.schema import Property, PropertyFeatures, PropertyPrice
from phoenix_real_estate.foundation.utils.validators import DataValidator
from phoenix_real_estate.foundation.utils.exceptions import ValidationError

class DataAdapter(ABC):
    """Adapter for converting external data to internal Property schema."""
    
    def __init__(self, validator: DataValidator, logger_name: str) -> None:
        self.validator = validator
        self.logger = get_logger(logger_name)
    
    @abstractmethod
    async def adapt_property(self, external_data: Dict[str, Any]) -> Property:
        """Convert external property data to internal Property model."""
        pass
    
    async def validate_and_adapt(self, external_data: Dict[str, Any]) -> Property:
        """Validate external data and adapt to internal schema."""
        try:
            # Use Epic 1's validation framework
            if not self.validator.validate_property_data(external_data):
                raise ValidationError(
                    "Property data validation failed",
                    context={"errors": self.validator.get_errors()}
                )
            
            property_obj = await self.adapt_property(external_data)
            
            self.logger.info(
                "Property data adapted successfully",
                extra={
                    "property_id": property_obj.property_id,
                    "source": self.get_source_name()
                }
            )
            
            return property_obj
            
        except Exception as e:
            self.logger.error(
                "Failed to adapt property data",
                extra={
                    "error": str(e),
                    "source": self.get_source_name(),
                    "data_sample": str(external_data)[:200]
                }
            )
            raise ValidationError(
                "Property data adaptation failed",
                context={"original_error": str(e)},
                cause=e
            ) from e
```

#### Factory Pattern for Collector Creation
```python
from enum import Enum
from phoenix_real_estate.foundation.config.environment import Environment

class DataSourceType(Enum):
    MARICOPA_API = "maricopa_api"
    PHOENIX_MLS = "phoenix_mls"
    COMBINED = "combined"

class CollectorFactory:
    """Factory for creating data collectors based on configuration."""
    
    @staticmethod
    async def create_collector(
        source_type: DataSourceType,
        config: ConfigProvider,
        repository: PropertyRepository
    ) -> DataCollector:
        """Create appropriate collector for source type."""
        
        if source_type == DataSourceType.MARICOPA_API:
            from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector
            return MaricopaAPICollector(config, repository, "maricopa.collector")
        
        elif source_type == DataSourceType.PHOENIX_MLS:
            from phoenix_real_estate.collectors.phoenix_mls import PhoenixMLSCollector
            return PhoenixMLSCollector(config, repository, "phoenix_mls.collector")
        
        elif source_type == DataSourceType.COMBINED:
            from phoenix_real_estate.collectors.combined import CombinedCollector
            return CombinedCollector(config, repository, "combined.collector")
        
        else:
            raise ValueError(f"Unknown source type: {source_type}")
```

### Module Organization

```
src/phoenix_real_estate/
├── collectors/                    # Data collection layer (Epic 2)
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── collector.py          # Base DataCollector ABC
│   │   ├── rate_limiter.py       # Rate limiting with observers
│   │   ├── adapter.py            # Data adaptation base classes
│   │   └── factory.py            # Collector factory
│   ├── maricopa/
│   │   ├── __init__.py
│   │   ├── client.py             # Maricopa County API client
│   │   ├── collector.py          # MaricopaAPICollector implementation
│   │   ├── adapter.py            # Maricopa data adapter
│   │   └── schemas.py            # Maricopa-specific response schemas
│   ├── phoenix_mls/
│   │   ├── __init__.py
│   │   ├── scraper.py            # Web scraping engine
│   │   ├── collector.py          # PhoenixMLSCollector implementation
│   │   ├── adapter.py            # Phoenix MLS data adapter
│   │   ├── anti_detection.py     # Anti-detection strategies
│   │   └── proxy_manager.py      # Proxy rotation management
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── llm_client.py         # Local LLM integration (Ollama)
│   │   ├── extractor.py          # Data extraction with LLM
│   │   ├── validator.py          # LLM output validation
│   │   └── pipeline.py           # Processing pipeline orchestration
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── metrics.py            # Collection metrics and monitoring
│   │   ├── health_check.py       # Source health monitoring
│   │   └── alerts.py             # Error alerting system
│   └── combined/
│       ├── __init__.py
│       ├── collector.py          # Multi-source orchestration
│       ├── deduplication.py      # Cross-source data deduplication
│       └── reconciliation.py     # Data conflict resolution
```

### Integration with Epic 1 Foundation

#### Configuration Integration
```python
# Epic 2 extends Epic 1's configuration system
from phoenix_real_estate.foundation.config.base import ConfigProvider

class CollectionConfig:
    """Collection-specific configuration using Epic 1's ConfigProvider."""
    
    def __init__(self, config: ConfigProvider) -> None:
        self.config = config
    
    @property
    def maricopa_api_key(self) -> str:
        """Maricopa County API key from configuration."""
        return self.config.get_required("MARICOPA_API_KEY")
    
    @property
    def maricopa_rate_limit(self) -> int:
        """Maricopa API rate limit (requests per hour)."""
        return self.config.get("MARICOPA_RATE_LIMIT", 1000)
    
    @property
    def proxy_username(self) -> str:
        """Webshare proxy username."""
        return self.config.get_required("WEBSHARE_USERNAME")
    
    @property
    def target_zip_codes(self) -> List[str]:
        """Target ZIP codes for collection."""
        zip_codes_str = self.config.get_required("TARGET_ZIP_CODES")
        return [z.strip() for z in zip_codes_str.split(",")]
    
    @property
    def llm_model(self) -> str:
        """Local LLM model name."""
        return self.config.get("LLM_MODEL", "llama3.2:latest")
    
    @property
    def min_request_delay(self) -> float:
        """Minimum delay between requests in seconds."""
        return self.config.get("MIN_REQUEST_DELAY", 3.6)
```

#### Database Integration
```python
# Epic 2 uses Epic 1's PropertyRepository exclusively
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.database.schema import Property

class CollectionService:
    """Service layer for data collection operations."""
    
    def __init__(
        self, 
        repository: PropertyRepository, 
        collector: DataCollector,
        logger_name: str
    ) -> None:
        self.repository = repository
        self.collector = collector
        self.logger = get_logger(logger_name)
    
    async def collect_and_store(self, zipcode: str) -> int:
        """Collect properties and store using Epic 1's repository."""
        try:
            # Collect raw data using strategy pattern
            raw_properties = await self.collector.collect_zipcode(zipcode)
            
            stored_count = 0
            for raw_property in raw_properties:
                try:
                    # Adapt to internal schema
                    property_obj = await self.collector.adapt_property(raw_property)
                    
                    # Store using Epic 1's repository pattern
                    property_id = await self.repository.create(property_obj.model_dump())
                    
                    stored_count += 1
                    self.logger.info(
                        "Property stored successfully",
                        extra={
                            "property_id": property_id,
                            "zipcode": zipcode,
                            "source": self.collector.get_source_name()
                        }
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to store individual property",
                        extra={
                            "error": str(e),
                            "zipcode": zipcode,
                            "source": self.collector.get_source_name()
                        }
                    )
                    # Continue processing other properties
                    continue
            
            self.logger.info(
                "Collection completed",
                extra={
                    "zipcode": zipcode,
                    "total_collected": len(raw_properties),
                    "successfully_stored": stored_count,
                    "source": self.collector.get_source_name()
                }
            )
            
            return stored_count
            
        except Exception as e:
            self.logger.error(
                "Collection failed for zipcode",
                extra={
                    "error": str(e),
                    "zipcode": zipcode,
                    "source": self.collector.get_source_name()
                }
            )
            raise DataCollectionError(
                f"Failed to collect data for zipcode {zipcode}",
                context={"zipcode": zipcode, "source": self.collector.get_source_name()},
                cause=e
            ) from e
```

#### Logging Integration
```python
# Epic 2 uses Epic 1's structured logging throughout
from phoenix_real_estate.foundation.logging.factory import get_logger

class CollectionMetrics:
    """Metrics collection using Epic 1's logging framework."""
    
    def __init__(self, logger_name: str) -> None:
        self.logger = get_logger(logger_name)
    
    async def record_collection_start(
        self, 
        source: str, 
        zipcode: str, 
        expected_count: Optional[int] = None
    ) -> None:
        """Record start of collection operation."""
        self.logger.info(
            "Collection started",
            extra={
                "event_type": "collection_start",
                "source": source,
                "zipcode": zipcode,
                "expected_count": expected_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def record_collection_complete(
        self,
        source: str,
        zipcode: str,
        collected_count: int,
        stored_count: int,
        duration_seconds: float
    ) -> None:
        """Record completion of collection operation."""
        self.logger.info(
            "Collection completed",
            extra={
                "event_type": "collection_complete",
                "source": source,
                "zipcode": zipcode,
                "collected_count": collected_count,
                "stored_count": stored_count,
                "duration_seconds": duration_seconds,
                "success_rate": stored_count / max(collected_count, 1),
                "properties_per_second": collected_count / max(duration_seconds, 0.1),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def record_rate_limit_hit(
        self,
        source: str,
        wait_time_seconds: float,
        requests_made: int
    ) -> None:
        """Record rate limit encountered."""
        self.logger.warning(
            "Rate limit encountered",
            extra={
                "event_type": "rate_limit_hit",
                "source": source,
                "wait_time_seconds": wait_time_seconds,
                "requests_made": requests_made,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

## Detailed Requirements

### Functional Requirements

#### FR-1: Maricopa County API Integration
- **Requirement**: Reliable integration with Maricopa County Assessor API
- **Acceptance Criteria**:
  - Respect 1000 requests/hour rate limit with intelligent throttling
  - Handle API key authentication and rotation
  - Graceful handling of API downtime and errors
  - Automatic retry with exponential backoff for transient failures
  - Data validation against Maricopa response schemas

#### FR-2: PhoenixMLSSearch.com Web Scraping
- **Requirement**: Robust web scraping with anti-detection capabilities
- **Acceptance Criteria**:
  - Proxy rotation through Webshare.io service
  - Browser fingerprint randomization and stealth techniques
  - Respect robots.txt and implement conservative rate limiting
  - Handle dynamic content loading and JavaScript-rendered pages
  - Session management and cookie handling

#### FR-3: Local LLM Data Processing
- **Requirement**: Local LLM integration for data extraction and cleaning
- **Acceptance Criteria**:
  - Ollama integration with Llama2:7b model for data processing
  - Structured data extraction from unstructured text
  - Data quality validation and error correction
  - Batch processing for efficiency
  - Fallback to rule-based extraction when LLM unavailable

#### FR-4: Data Pipeline Orchestration
- **Requirement**: Coordinated data collection across multiple sources
- **Acceptance Criteria**:
  - Sequential and parallel collection strategies
  - Cross-source data deduplication and reconciliation
  - Error recovery and partial failure handling
  - Progress monitoring and resumable operations
  - Data quality metrics and validation

#### FR-5: Monitoring and Alerting
- **Requirement**: Comprehensive monitoring of collection operations
- **Acceptance Criteria**:
  - Real-time metrics on collection success rates
  - Source health monitoring and failure detection
  - Rate limit tracking and optimization
  - Data quality metrics and anomaly detection
  - Performance metrics and optimization insights

### Non-Functional Requirements

#### NFR-1: Performance
- **Data Collection Rate**: 10-20 properties/minute per source
- **Rate Limit Compliance**: 100% compliance with API limits
- **Memory Usage**: < 200MB total for all collectors
- **CPU Usage**: < 30% average during active collection

#### NFR-2: Reliability
- **Error Recovery**: Automatic retry for transient failures
- **Partial Failure Handling**: Continue collection despite individual failures
- **Data Integrity**: 100% data validation before storage
- **Source Availability**: Graceful degradation when sources unavailable

#### NFR-3: Security
- **Credential Management**: Secure handling of API keys and proxy credentials
- **Legal Compliance**: Respect robots.txt and rate limiting
- **Data Privacy**: No collection of personally identifiable information
- **Anti-Detection**: Stealth techniques to avoid blocking

#### NFR-4: Maintainability
- **Test Coverage**: 90%+ for all collection modules
- **Configuration Management**: All settings externally configurable
- **Logging Observability**: Comprehensive structured logging
- **Error Handling**: Consistent error patterns using Epic 1's exception hierarchy

## Implementation Tasks

### Task 4: Maricopa County API Client
**File**: `task-04-maricopa-api-client.md`
- Implement API client with rate limiting and authentication
- Create data adapter for Maricopa response format
- Add comprehensive error handling and retry logic
- Integrate with Epic 1's configuration and repository systems

### Task 5: PhoenixMLS Web Scraper
**File**: `task-05-phoenix-mls-scraper.md`
- Build web scraper with anti-detection capabilities
- Implement proxy rotation and session management
- Create data extraction pipeline with LLM processing
- Add monitoring and health checking

### Task 6: LLM Data Processing Pipeline ✅ **COMPLETE**
**File**: `task-06-llm-data-processing.md`  
**Status**: 🎉 **Production-Ready** - All 12 tasks complete with troubleshooting fixes
- ✅ Ollama integration operational with llama3.2:latest model
- ✅ ProcessingIntegrator bridges collectors with LLM pipeline
- ✅ 83 comprehensive unit tests + E2E integration complete
- ✅ PropertyDataExtractor with source-specific processing
- ✅ ProcessingValidator with confidence scoring and quality metrics
- Implement structured data extraction from unstructured text
- Add data validation and quality checks
- Create batch processing and optimization strategies

## Constraints & Limitations

### Technical Constraints
- **API Rate Limits**: Maricopa County 1000 req/hour, PhoenixMLS conservative scraping
- **Proxy Bandwidth**: Webshare.io 100GB/month limit
- **Local Processing**: LLM processing limited by local hardware capabilities
- **Memory Constraints**: Must operate within reasonable memory limits

### Budget Constraints
- **Proxy Service**: $5/month Webshare.io plan
- **Local LLM**: $0/month using Ollama ✅ **OPERATIONAL** with llama3.2:latest
- **API Usage**: $0/month within free tier limits
- **Total Budget**: $5/month (20% of maximum budget)

### Legal Constraints
- **Personal Use Only**: System must be clearly marked for personal use
- **Robots.txt Compliance**: Must respect website scraping policies
- **Rate Limiting**: Conservative approach to avoid overwhelming sources
- **Data Usage**: No commercial use or redistribution of collected data

### Performance Constraints
- **Collection Speed**: Balance between efficiency and respectful usage
- **Resource Usage**: Minimize impact on local system resources
- **Error Rates**: Maintain low error rates to avoid source blocking
- **Data Quality**: Balance speed with data accuracy and completeness

## Risk Assessment

### High Risk Items

#### R-1: Source Blocking/Detection
- **Risk**: Web scraping detection leading to IP blocking
- **Impact**: Loss of data collection capability from Phoenix MLS
- **Mitigation**:
  - Implement advanced anti-detection techniques
  - Use proxy rotation with residential proxies
  - Conservative rate limiting and request patterns
  - Browser fingerprint randomization
- **Owner**: Data Collection Team

#### R-2: API Rate Limit Violations
- **Risk**: Exceeding Maricopa County API rate limits
- **Impact**: Temporary or permanent API access suspension
- **Mitigation**:
  - Intelligent rate limiting with safety margins
  - Request queuing and throttling
  - Monitoring and alerting for rate limit approach
  - Graceful handling of rate limit responses
- **Owner**: Data Collection Team

### Medium Risk Items

#### R-3: Data Quality Issues
- **Risk**: Poor data extraction or validation failures
- **Impact**: Inaccurate or incomplete property data
- **Mitigation**:
  - Multi-stage validation pipeline
  - LLM output verification
  - Cross-source data validation
  - Human-reviewable error logs
- **Owner**: Data Processing Team

#### R-4: Proxy Service Reliability
- **Risk**: Webshare.io service outages or bandwidth exhaustion
- **Impact**: Inability to perform web scraping
- **Mitigation**:
  - Monitor bandwidth usage with alerts
  - Implement fallback direct connection for emergencies
  - Consider backup proxy service for critical operations
  - Optimize proxy usage patterns
- **Owner**: Infrastructure Team

### Low Risk Items

#### R-5: LLM Processing Failures ✅ **MITIGATED**
- **Risk**: Local LLM becomes unavailable or produces poor results
- **Status**: ✅ **Risk mitigated** - Comprehensive error handling and fallback strategies implemented
- **Impact**: Reduced data extraction quality
- **Mitigation**:
  - Implement rule-based fallback extraction
  - ✅ Monitor LLM response quality - Quality validation system operational
  - Consider alternative local models
  - Manual review processes for critical data
- **Owner**: Data Processing Team

## Testing Strategy

### Unit Testing Framework
```python
# Example test structure for collectors
import pytest
from unittest.mock import AsyncMock, patch
from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector
from phoenix_real_estate.foundation.config.base import ConfigProvider

class TestMaricopaAPICollector:
    @pytest.fixture
    async def collector(self):
        mock_config = AsyncMock(spec=ConfigProvider)
        mock_repository = AsyncMock()
        return MaricopaAPICollector(mock_config, mock_repository, "test.maricopa")
    
    async def test_collect_zipcode_success(self, collector):
        # Test successful data collection
        mock_response = {"properties": [{"address": "123 Main St"}]}
        
        with patch.object(collector, '_make_api_request', return_value=mock_response):
            properties = await collector.collect_zipcode("85031")
            
        assert len(properties) > 0
        assert properties[0]["address"] == "123 Main St"
    
    async def test_rate_limit_handling(self, collector):
        # Test rate limit compliance
        with patch.object(collector._rate_limiter, 'wait_if_needed') as mock_wait:
            await collector.collect_zipcode("85031")
            mock_wait.assert_called_once()
```

### Integration Testing
- **API Integration**: Test against real Maricopa County API with test data
- **Web Scraping**: Test against staging or test instances of target sites
- **LLM Processing**: ✅ **Validated** - 94% extraction accuracy achieved with comprehensive test datasets
- **End-to-End**: Full pipeline testing with real data sources

### Performance Testing
- **Rate Limiting**: Verify compliance with API limits under load
- **Memory Usage**: Profile memory consumption during extended operations
- **Concurrency**: Test concurrent collection from multiple sources
- **Error Recovery**: Test resilience under various failure scenarios

### Acceptance Testing
- **Data Quality**: Validate extracted data against known good sources
- **Error Handling**: Verify graceful degradation under failure conditions
- **Monitoring**: Test alerting and metrics collection
- **Configuration**: Validate all configuration scenarios

## Success Metrics

### Key Performance Indicators

#### KPI-1: Collection Success Rate
- **Metric**: Percentage of successful property collections
- **Target**: 95% success rate across all sources
- **Measurement**: Daily success rate tracking

#### KPI-2: Data Quality Score
- **Metric**: Percentage of collected properties passing validation
- **Target**: 98% data quality score
- **Measurement**: Automated validation pipeline metrics

#### KPI-3: Rate Limit Compliance
- **Metric**: Percentage of requests within rate limits
- **Target**: 100% compliance with no violations
- **Measurement**: Rate limiting monitoring and alerts

#### KPI-4: Collection Efficiency
- **Metric**: Properties collected per hour per source
- **Target**: 600-1200 properties/hour per source
- **Measurement**: Performance monitoring dashboard

### Acceptance Criteria

#### Business Criteria
- [ ] Epic 3 can build automated orchestration on collection interfaces
- [ ] Data quality meets requirements for analysis and reporting
- [ ] Collection engine operates within budget constraints
- [ ] Legal compliance maintained across all sources

#### Technical Criteria
- [ ] 90%+ test coverage for all collection modules
- [ ] Integration with Epic 1 foundation verified
- [ ] Performance targets met under realistic load
- [ ] Error handling follows Epic 1 patterns

#### Quality Criteria
- [ ] Code passes all ruff formatting and linting checks
- [ ] Type hints pass mypy strict mode validation
- [ ] Security scan shows no vulnerabilities
- [ ] Documentation complete for all public interfaces

## Interface Definitions for Dependent Epics

### Epic 3: Automation & Orchestration
```python
# Interfaces that Epic 3 will consume
from phoenix_real_estate.collectors.base import DataCollector
from phoenix_real_estate.collectors.monitoring import CollectionMetrics
from phoenix_real_estate.collectors.combined import CombinedCollector

class CollectionOrchestrator:
    """Interface for Epic 3 automation."""
    
    def __init__(
        self,
        collectors: List[DataCollector],
        config: ConfigProvider,
        repository: PropertyRepository
    ) -> None:
        # Epic 3 will orchestrate Epic 2 collectors
        pass
    
    async def run_daily_collection(self, zip_codes: List[str]) -> Dict[str, int]:
        """Run daily collection across all sources."""
        pass
```

### Epic 4: Quality & Analytics
```python
# Interfaces that Epic 4 will consume
from phoenix_real_estate.collectors.monitoring import CollectionMetrics

class QualityAnalyzer:
    """Interface for Epic 4 quality analysis."""
    
    def __init__(self, metrics: CollectionMetrics) -> None:
        # Epic 4 will analyze Epic 2 collection quality
        pass
    
    async def analyze_collection_quality(self, timeframe: str) -> Dict[str, float]:
        """Analyze data quality metrics."""
        pass
```

## Dependencies for Future Epics

### Epic 3 Dependencies
- `phoenix_real_estate.collectors.base.DataCollector`
- `phoenix_real_estate.collectors.maricopa.MaricopaAPICollector`
- `phoenix_real_estate.collectors.phoenix_mls.PhoenixMLSCollector`
- `phoenix_real_estate.collectors.combined.CombinedCollector`
- `phoenix_real_estate.collectors.monitoring.CollectionMetrics`

### Epic 4 Dependencies
- `phoenix_real_estate.collectors.monitoring.CollectionMetrics`
- `phoenix_real_estate.collectors.monitoring.HealthCheck`
- Collection quality metrics and analysis interfaces

## Implementation Guidelines

### Code Quality Standards
- **Epic 1 Integration**: All components must use Epic 1's foundation abstractions
- **Type Safety**: Complete type hints with mypy validation
- **Error Handling**: Use Epic 1's exception hierarchy consistently
- **Testing**: Test-driven development with comprehensive coverage
- **Documentation**: Clear docstrings with usage examples

### Security Guidelines
- **Credential Security**: Use Epic 1's configuration system for secrets
- **Rate Limiting**: Implement conservative rate limiting strategies
- **Legal Compliance**: Respect all website terms of service
- **Data Privacy**: No collection of personally identifiable information

### Performance Guidelines
- **Resource Efficiency**: Minimize memory and CPU usage
- **Rate Limit Compliance**: Never exceed source rate limits
- **Error Recovery**: Implement robust retry and recovery mechanisms
- **Monitoring**: Comprehensive metrics and alerting

## Validation Checklist

### Pre-Implementation
- [ ] Epic 1 foundation interfaces reviewed and understood
- [ ] All task specifications created with Epic 1 integration
- [ ] Configuration requirements defined using Epic 1 patterns
- [ ] Interface definitions complete for Epic 3/4 consumption

### Implementation Phase
- [ ] All collectors use Epic 1's PropertyRepository exclusively
- [ ] Configuration managed through Epic 1's ConfigProvider
- [ ] Logging uses Epic 1's structured logging framework
- [ ] Error handling follows Epic 1's exception patterns

### Post-Implementation
- [ ] Integration tests pass with Epic 1 foundation
- [ ] Performance benchmarks meet targets
- [ ] Security scan shows no vulnerabilities
- [ ] Epic 3/4 interface contracts validated

---

**Epic Owner**: Data Engineering Team  
**Created**: 2025-01-20  
**Status**: Planning  
**Estimated Effort**: 7-10 days  
**Dependencies**: Epic 1 (Foundation Infrastructure)