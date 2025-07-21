# Task 04: Maricopa County API Client - Implementation Workflow

## Overview

**Task**: Implement robust, rate-limited Maricopa County Assessor API client
**Epic**: Epic 2 - Data Collection Engine
**Strategy**: Systematic Backend Implementation
**Duration**: 2-3 days
**Priority**: High (foundational for Epic 2)
**Team**: Data Engineering Team

## Workflow Strategy: Systematic Backend Implementation

### Auto-Activated Personas
- **Primary**: Backend Developer (API integration, authentication, rate limiting)
- **Supporting**: Architect (system design), QA (testing strategy), Security (credential handling)

### MCP Server Integration
- **Context7**: aiohttp patterns, HTTP client best practices, authentication patterns
- **Sequential**: Rate limiting logic, error handling workflows, retry strategies
- **Playwright**: Integration testing, performance validation

### SuperClaude Framework Integration
- **Wave Mode**: Disabled (sequential dependencies in API client → adapter → collector)
- **Sub-Agent Delegation**: Used for parallel testing and documentation
- **Quality Gates**: Full 8-step validation cycle with security focus

## Phase-Based Implementation Plan

## Phase 1: Foundation Setup & Architecture Design
**Timeline**: Day 1 Morning (2-3 hours)
**Dependencies**: Epic 1 foundation complete
**Risk Level**: Low

### Epic 1 Integration Validation
**Duration**: 30 minutes | **Persona**: Backend

```bash
# Verify Epic 1 foundation components
uv run python -c "
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import DataCollectionError
print('✅ Epic 1 foundation verified')
"
```

**Quality Gates**:
- [ ] ConfigProvider accessible and functional
- [ ] PropertyRepository and schema available
- [ ] Logging factory operational
- [ ] Exception hierarchy importable

### Project Structure Creation
**Duration**: 30 minutes | **Persona**: Architect

Create collector package structure:
```
src/phoenix_real_estate/collectors/
├── __init__.py                    # Package exports
├── base/                          # Base classes and utilities
│   ├── __init__.py
│   ├── collector.py               # DataCollector abstract base
│   ├── adapter.py                 # DataAdapter abstract base
│   └── rate_limiter.py            # RateLimiter with observer pattern
└── maricopa/                      # Maricopa-specific implementation
    ├── __init__.py
    ├── client.py                  # MaricopaAPIClient
    ├── adapter.py                 # MaricopaDataAdapter
    └── collector.py               # MaricopaAPICollector
```

**Architecture Decisions**:
- **Strategy Pattern**: DataCollector base for Epic 3 orchestration
- **Observer Pattern**: Rate limiting with monitoring capabilities
- **Adapter Pattern**: Clean API response → Property schema conversion
- **Dependency Injection**: Epic 1 components injected for testability

### API Architecture Design
**Duration**: 45 minutes | **Persona**: Backend + Security

**Core Design Principles**:
1. **Rate Limiting**: Conservative 10% safety margin (900 req/hour effective from 1000 limit)
2. **Authentication**: Bearer token with secure session management
3. **Error Handling**: Epic 1 exception hierarchy with proper chaining
4. **Retry Logic**: Exponential backoff using Epic 1's `retry_async`
5. **Security**: No credential logging, HTTPS-only communication

**Data Flow Architecture**:
```
API Request → Rate Limiter → Authentication → HTTP Client
     ↓
Response → Validation → Adapter → Property Schema → Repository
```

**Risk Mitigation**:
- **API Violations**: Conservative rate limiting with observer monitoring
- **Authentication Failures**: Comprehensive error handling and clear messaging
- **Schema Changes**: Flexible adapter with extensive validation
- **Performance Issues**: Connection pooling and timeout management

**Quality Gates**:
- [ ] Architecture supports Epic 3 orchestration requirements
- [ ] Rate limiting prevents API violations
- [ ] Error handling follows Epic 1 patterns
- [ ] Security requirements addressed

## Phase 2: Core Implementation
**Timeline**: Day 1 Afternoon - Day 2 (8-12 hours)
**Dependencies**: Phase 1 complete
**Risk Level**: Medium-High (API integration complexity)

### Rate Limiter Implementation
**Duration**: 2 hours | **Priority**: Critical | **Persona**: Backend

**File**: `src/phoenix_real_estate/collectors/base/rate_limiter.py`

**Implementation Steps**:

1. **Observer Protocol** (20 minutes)
```python
from typing import Protocol
from datetime import datetime

class RateLimitObserver(Protocol):
    """Observer protocol for rate limiting events."""
    async def on_request_made(self, source: str, timestamp: datetime) -> None: ...
    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None: ...
    async def on_rate_limit_reset(self, source: str) -> None: ...
```

2. **Core Rate Limiter** (90 minutes)
- Sliding window algorithm with asyncio.Lock for thread safety
- Safety margin calculation (1000 → 900 effective limit)
- Epic 1 structured logging integration
- Observer notification system for monitoring

3. **Usage Statistics** (20 minutes)
- Real-time usage tracking and utilization metrics
- Performance monitoring integration points

4. **Unit Tests** (10 minutes setup)
```python
# tests/collectors/base/test_rate_limiter.py
async def test_rate_limiting_compliance()
async def test_observer_notifications()
async def test_safety_margin_enforcement()
async def test_concurrent_request_handling()
```

**Quality Gates**:
- [ ] Rate limiter enforces 900 req/hour effective limit
- [ ] Observer notifications functional
- [ ] Epic 1 logging integration working
- [ ] Thread-safe concurrent access

### Base Classes Implementation
**Duration**: 90 minutes | **Persona**: Architect + Backend

**DataCollector Strategy Pattern** (45 minutes)
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DataCollector(ABC):
    """Abstract base for data collectors supporting Epic 3 orchestration."""
    
    def __init__(self, config: ConfigProvider, repository: PropertyRepository, logger_name: str):
        self.config = config
        self.repository = repository
        self.logger = get_logger(logger_name)
    
    @abstractmethod
    async def collect_zipcode(self, zipcode: str) -> List[Dict[str, Any]]: ...
    
    @abstractmethod
    async def adapt_property(self, raw_data: Dict[str, Any]) -> Property: ...
    
    @abstractmethod
    def get_source_name(self) -> str: ...
```

**DataAdapter Pattern** (45 minutes)
```python
class DataAdapter(ABC):
    """Abstract base for data source adaptation to internal schema."""
    
    def __init__(self, validator: DataValidator, logger_name: str):
        self.validator = validator
        self.logger = get_logger(logger_name)
    
    @abstractmethod
    async def adapt_property(self, raw_data: Dict[str, Any]) -> Property: ...
    
    @abstractmethod
    def get_source_name(self) -> str: ...
```

**Quality Gates**:
- [ ] Strategy pattern supports multiple data sources
- [ ] Epic 1 dependency injection working
- [ ] Abstract methods enforce consistent interface

### Maricopa API Client Implementation
**Duration**: 3 hours | **Priority**: Critical | **Persona**: Backend

**File**: `src/phoenix_real_estate/collectors/maricopa/client.py`

**Implementation Phases**:

1. **Authentication & Session Management** (45 minutes)
- Epic 1 ConfigProvider integration for secure API key management
- aiohttp ClientSession with proper headers and connection pooling
- Async context manager support for resource cleanup

2. **Rate-Limited Request Handling** (90 minutes)
- RateLimiter integration with observer pattern
- Epic 1's `retry_async` for exponential backoff
- Comprehensive HTTP status code handling:
  - 401: Authentication failure with clear error
  - 403: Permission issues with context
  - 429: Rate limit with Retry-After header parsing
  - 5xx: Server errors with appropriate backoff

3. **API Endpoint Implementation** (45 minutes)
```python
async def search_by_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
    """Search properties by ZIP code with comprehensive error handling."""
    
async def get_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed property information with validation."""
```

4. **Error Handling & Logging** (30 minutes)
- Epic 1 `DataCollectionError` with proper context
- Structured logging with request/response metadata
- Exception chaining preserving root causes

**Security Requirements**:
- [ ] API keys never logged or exposed
- [ ] HTTPS-only communication enforced
- [ ] Authentication errors handled securely
- [ ] Request/response sanitized in logs

**Quality Gates**:
- [ ] Authentication working with test credentials
- [ ] Rate limiting integration functional
- [ ] All error paths properly handled
- [ ] Structured logging with context

### Data Adapter Implementation
**Duration**: 2 hours | **Priority**: High | **Persona**: Backend

**File**: `src/phoenix_real_estate/collectors/maricopa/adapter.py`

**Implementation Steps**:

1. **Schema Mapping Analysis** (30 minutes)
```python
# Maricopa API Response → Epic 1 Property Schema
maricopa_response = {
    "property_info": {"apn": "123-45-678"},
    "address": {"house_number": "123", "street_name": "Main", "street_type": "St"},
    "assessment": {"assessed_value": 300000, "market_value": 350000},
    "characteristics": {"bedrooms": 3, "bathrooms": 2.5, "living_area_sqft": 1800}
}
```

2. **Core Adaptation Logic** (60 minutes)
- Epic 1's `normalize_address()` for address standardization
- Epic 1's `safe_int()`, `safe_float()` for type-safe conversions
- Epic 1's `generate_property_id()` for unique identification
- PropertyFeatures and PropertyPrice object creation

3. **Address Normalization** (15 minutes)
```python
def _extract_address(self, address_info: Dict[str, Any]) -> str:
    """Extract and format address using Epic 1 utilities."""
    house_number = address_info.get("house_number", "")
    street_name = address_info.get("street_name", "")
    street_type = address_info.get("street_type", "")
    # Use Epic 1's normalize_address for standardization
```

4. **Price Extraction with History** (15 minutes)
- Multiple price types (assessed_value, market_value)
- Historical assessment data preservation
- Proper date handling with timezone awareness

**Data Integrity Requirements**:
- [ ] All Epic 1 `safe_*` utilities used for conversions
- [ ] Address normalization working correctly
- [ ] Property schema validation passing
- [ ] Price history preserved with proper dates

**Quality Gates**:
- [ ] Schema conversion 100% accurate
- [ ] Validation errors properly handled
- [ ] Epic 1 utilities integrated correctly
- [ ] Original data preserved in listing_details

### Collector Integration
**Duration**: 90 minutes | **Priority**: High | **Persona**: Backend + Architect

**File**: `src/phoenix_real_estate/collectors/maricopa/collector.py`

**Implementation Components**:

1. **DataCollector Implementation** (45 minutes)
```python
class MaricopaAPICollector(DataCollector):
    """Maricopa County data collector with Epic 1 integration."""
    
    def __init__(self, config: ConfigProvider, repository: PropertyRepository, logger_name: str):
        super().__init__(config, repository, logger_name)
        self.validator = DataValidator()
        self.api_client = MaricopaAPIClient(config)
        self.adapter = MaricopaDataAdapter(self.validator, f"{logger_name}.adapter")
```

2. **Collection Methods** (30 minutes)
- Zipcode-based property collection with pagination support
- Individual property detail collection
- Proper error handling and logging throughout

3. **Epic 3 Orchestration Interface** (15 minutes)
- Strategy pattern compliance for multi-source orchestration
- Consistent error handling and logging
- Source identification for tracking and analytics

**Integration Requirements**:
- [ ] DataCollector strategy pattern implemented
- [ ] Epic 3 orchestration interface ready
- [ ] All Epic 1 dependencies properly injected
- [ ] Source identification working

**Quality Gates**:
- [ ] End-to-end collection workflow functional
- [ ] Epic 1 repository integration working
- [ ] Error handling comprehensive
- [ ] Logging structured and contextual

## Phase 3: Testing & Quality Validation
**Timeline**: Day 2 Evening - Day 3 (4-6 hours)
**Dependencies**: Core implementation complete
**Risk Level**: Medium

### Unit Testing Implementation
**Duration**: 2 hours | **Persona**: QA + Backend

**Test Structure**:
```
tests/collectors/
├── base/
│   ├── test_rate_limiter.py      # Rate limiting functionality
│   ├── test_collector.py         # Base collector tests
│   └── test_adapter.py           # Base adapter tests
└── maricopa/
    ├── test_client.py            # API client tests
    ├── test_adapter.py           # Data adapter tests
    ├── test_collector.py         # Collector integration tests
    └── test_integration.py       # Full integration tests
```

**Critical Test Coverage**:

1. **Rate Limiter Tests** (30 minutes)
```python
async def test_rate_limiting_enforced():
    """Verify rate limiter prevents API violations."""
    
async def test_safety_margin_calculation():
    """Verify 10% safety margin applied correctly."""
    
async def test_observer_notifications():
    """Verify observer pattern notifications."""
```

2. **API Client Tests** (45 minutes)
```python
async def test_authentication_headers():
    """Verify Bearer token authentication."""
    
async def test_rate_limiting_integration():
    """Verify rate limiter integration."""
    
async def test_error_handling_comprehensive():
    """Test 401, 403, 429, 5xx error handling."""
    
async def test_retry_logic_exponential_backoff():
    """Verify retry logic with backoff."""
```

3. **Data Adapter Tests** (45 minutes)
```python
async def test_property_adaptation_complete():
    """Verify complete property adaptation."""
    
async def test_address_normalization():
    """Test address normalization using Epic 1 utilities."""
    
async def test_price_extraction_with_history():
    """Verify price extraction including historical data."""
```

**Test Quality Targets**:
- [ ] >95% unit test coverage
- [ ] All error paths tested
- [ ] Epic 1 integration mocked appropriately
- [ ] Performance benchmarks for rate limiting

### Integration Testing
**Duration**: 2 hours | **Persona**: QA + Backend

**File**: `tests/collectors/test_maricopa_integration.py`

**Integration Test Scope**:

1. **Epic 1 Foundation Integration** (45 minutes)
```python
async def test_config_provider_integration():
    """Verify ConfigProvider usage for API credentials."""
    
async def test_property_repository_integration():
    """Verify PropertyRepository data persistence."""
    
async def test_logging_framework_integration():
    """Verify structured logging throughout workflow."""
    
async def test_exception_hierarchy_compliance():
    """Verify Epic 1 exception patterns used correctly."""
```

2. **End-to-End Workflow Testing** (45 minutes)
```python
async def test_zipcode_collection_e2e():
    """Test complete zipcode collection workflow."""
    
async def test_property_adaptation_e2e():
    """Test end-to-end property adaptation."""
    
async def test_error_handling_e2e():
    """Test error handling throughout entire workflow."""
```

3. **Performance & Rate Limiting Validation** (30 minutes)
- Rate limiting compliance under simulated load
- Memory usage during extended operations
- Response time benchmarking for zipcode searches
- Concurrent request handling validation

**Integration Quality Targets**:
- [ ] All Epic 1 integrations verified
- [ ] E2E workflow functional with real API
- [ ] Performance within acceptable limits (<30s for zipcode)
- [ ] Rate limiting preventing actual API violations

### Configuration & Environment Setup
**Duration**: 1 hour | **Persona**: DevOps + Backend

**Environment Variables Setup**:
```bash
# Production configuration
MARICOPA_API_KEY=your_production_api_key
MARICOPA_BASE_URL=https://api.assessor.maricopa.gov/v1
MARICOPA_RATE_LIMIT=1000

# Development configuration  
MARICOPA_API_KEY=test_key_for_development
MARICOPA_RATE_LIMIT=100  # Lower limit for development testing
```

**Configuration Validation**:
1. **Epic 1 ConfigProvider Integration** (20 minutes)
- Test configuration loading from multiple sources
- Validate required vs optional configuration handling
- Test configuration error messages

2. **Security Validation** (20 minutes)
- Verify API keys not logged
- Test secure credential storage
- Validate HTTPS enforcement

3. **Development Environment Setup** (20 minutes)
```bash
# Add to .env for development
echo "MARICOPA_API_KEY=test_development_key" >> .env
echo "MARICOPA_RATE_LIMIT=50" >> .env

# Verify configuration loading
uv run python -c "
from phoenix_real_estate.foundation.config.base import get_config
config = get_config()
key = config.get_required('MARICOPA_API_KEY')
print(f'✅ API Key configured: {key[:8]}...')
print(f'✅ Rate limit: {config.get(\"MARICOPA_RATE_LIMIT\", 1000)}')
"
```

**Configuration Quality Gates**:
- [ ] Configuration loading from all sources working
- [ ] API credentials secured and validated
- [ ] Development vs production environments separated
- [ ] Configuration documentation complete

## Phase 4: Quality Gates & Final Validation
**Timeline**: Day 3 (2-3 hours)
**Dependencies**: All implementation and testing complete
**Risk Level**: Low

### SuperClaude 8-Step Validation Cycle

**Step 1: Syntax Validation** (15 minutes)
```bash
# Code formatting and basic syntax
uv run ruff check src/phoenix_real_estate/collectors/ --fix
uv run ruff format src/phoenix_real_estate/collectors/

# Import validation
uv run python -c "
from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector
from phoenix_real_estate.collectors.base import DataCollector, DataAdapter, RateLimiter
print('✅ All imports successful')
"
```

**Step 2: Type Checking** (15 minutes)
```bash
# Comprehensive type validation
uv run mypy src/phoenix_real_estate/collectors/ --strict

# Pydantic schema compliance
uv run python -c "
from phoenix_real_estate.foundation.database.schema import Property
from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter
print('✅ Schema compliance verified')
"
```

**Step 3: Linting & Code Quality** (15 minutes)
```bash
# Final code quality check
uv run ruff check src/phoenix_real_estate/collectors/ --statistics
# Review complexity metrics and maintainability scores
```

**Step 4: Security Validation** (30 minutes)
**Persona**: Security + Backend

- [ ] **Credential Security**: API keys never logged or exposed in error messages
- [ ] **HTTPS Enforcement**: All API communication over HTTPS only
- [ ] **Input Validation**: All user inputs properly validated and sanitized
- [ ] **Authentication Security**: Auth failures handled without credential exposure
- [ ] **Error Message Security**: No sensitive information in error responses

**Step 5: Test Coverage & Quality** (30 minutes)
```bash
# Comprehensive test coverage
uv run pytest tests/collectors/ --cov=src/phoenix_real_estate/collectors --cov-report=html --cov-fail-under=90

# Test performance and reliability
uv run pytest tests/collectors/test_maricopa_integration.py::test_rate_limiting_performance -v
```

**Coverage Targets**:
- [ ] >95% unit test coverage
- [ ] >85% integration test coverage
- [ ] All error paths tested
- [ ] Performance benchmarks passing

**Step 6: Performance Validation** (30 minutes)
**Persona**: Performance + Backend

- [ ] **Rate Limiting**: Verified compliance with 900 req/hour effective limit
- [ ] **Response Time**: <30s for zipcode searches under normal conditions
- [ ] **Memory Usage**: <100MB during extended operations
- [ ] **Concurrent Handling**: Proper handling of multiple simultaneous requests
- [ ] **Connection Management**: Efficient connection pooling and cleanup

**Step 7: Documentation Validation** (30 minutes)
**Persona**: Scribe + Backend

- [ ] **Code Documentation**: Comprehensive docstrings for all public methods
- [ ] **API Usage Examples**: Clear examples for Epic 3 orchestration integration
- [ ] **Configuration Guide**: Complete setup and configuration documentation
- [ ] **Error Handling Guide**: Documentation of all error scenarios and responses
- [ ] **Integration Patterns**: Documentation for Epic 1 foundation integration

**Step 8: Integration Validation** (15 minutes)
**Persona**: QA + Architect

- [ ] **Epic 1 Foundation**: All foundation components properly integrated
- [ ] **Epic 3 Interface**: DataCollector strategy pattern ready for orchestration
- [ ] **Epic 4 Monitoring**: Observer pattern ready for quality analysis
- [ ] **E2E Workflow**: Complete workflow from API request to repository storage
- [ ] **Error Recovery**: Graceful handling and recovery from all error conditions

### Final Acceptance Criteria Validation

**Technical Acceptance Criteria**:
- [ ] **AC-1**: MaricopaAPIClient with authentication, rate limiting, error handling
- [ ] **AC-2**: MaricopaDataAdapter converting API responses to Property schema
- [ ] **AC-3**: MaricopaAPICollector integrating client and adapter
- [ ] **AC-4**: RateLimiter with observer pattern and Epic 1 logging
- [ ] **AC-5**: Comprehensive integration tests validating Epic 1 integration

**Performance Acceptance Criteria**:
- [ ] Rate limiting prevents API violations (0 violations in testing)
- [ ] Response time <30s for zipcode searches
- [ ] >99% success rate for valid API requests
- [ ] Memory usage <100MB during extended operations

**Quality Acceptance Criteria**:
- [ ] >95% unit test coverage, >85% integration test coverage
- [ ] All Epic 1 foundation components properly integrated
- [ ] Comprehensive error handling with proper exception chaining
- [ ] Security requirements met (no credential exposure)
- [ ] Documentation complete and accurate

## Risk Management & Contingency Planning

### High Risk: API Rate Limit Violations
**Impact**: API access suspended, data collection halted
**Probability**: Medium (if rate limiting fails)
**Mitigation**:
- Conservative 10% safety margin (900 req/hour effective)
- Real-time usage monitoring with observer pattern
- Circuit breaker for extended failures
**Contingency**:
- Extended backoff periods (up to 2 hours)
- Alert system for approaching rate limits
- Manual intervention procedures documented

### Medium Risk: API Schema Changes
**Impact**: Data collection failures, schema validation errors
**Probability**: Low (stable government API)
**Mitigation**:
- Comprehensive data validation in adapter
- Flexible adapter pattern design for easy updates
- Schema version tracking and compatibility checks
**Contingency**:
- Rapid adapter update procedures
- Fallback to cached/previous data during transitions
- Error reporting and notification system

### Medium Risk: Authentication/Authorization Issues
**Impact**: API access denied, data collection halted
**Probability**: Low (stable API keys)
**Mitigation**:
- Clear configuration error messages
- API key validation at application startup
- Secure credential management using Epic 1 patterns
**Contingency**:
- Configuration troubleshooting documentation
- API key rotation procedures
- Support contact procedures documented

### Low Risk: Performance Degradation
**Impact**: Slow data collection, user experience issues
**Probability**: Low (optimized implementation)
**Mitigation**:
- Connection pooling and timeout management
- Performance monitoring and alerting
- Resource usage optimization
**Contingency**:
- Performance tuning procedures
- Scaling strategies documented
- Alternative collection strategies

## Success Metrics & KPIs

### Technical Performance Metrics
- **Rate Limiting Compliance**: 0 API violations, <900 req/hour actual usage
- **Response Time Performance**: <30s average for zipcode searches
- **Reliability Score**: >99% success rate for valid API requests
- **Error Recovery Rate**: >95% successful recovery from transient errors

### Quality Assurance Metrics
- **Test Coverage**: >95% unit tests, >85% integration tests
- **Code Quality Score**: Ruff compliance score >95%
- **Documentation Coverage**: 100% public API documented
- **Security Compliance**: 0 security violations in scanning

### Integration Success Metrics
- **Epic 1 Integration**: 100% foundation components integrated successfully
- **Configuration Management**: All config sources working (env vars, files, defaults)
- **Logging Integration**: Structured logs with proper context in all components
- **Error Handling**: All error paths tested and properly handled

### Business Value Metrics
- **Data Collection Readiness**: API client ready for Epic 3 orchestration
- **Scalability Preparation**: Architecture supports multiple data sources
- **Maintainability Score**: Clean architecture following SOLID principles
- **Time to Market**: Implementation completed within 2-3 day estimate

## Next Steps & Epic Integration

### Epic 3 Orchestration Integration
```python
# Ready for Epic 3 multi-source orchestration
from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector
from phoenix_real_estate.foundation.config.base import get_config
from phoenix_real_estate.foundation.database.repositories import PropertyRepository

# Factory pattern for collector creation
config = get_config()
repository = PropertyRepository(config)
collector = MaricopaAPICollector(config, repository, "orchestration.maricopa")

# Epic 3 orchestration interface
properties = await collector.collect_zipcode("85031")
for raw_data in properties:
    property_obj = await collector.adapt_property(raw_data)
    await repository.create(property_obj)
```

### Epic 4 Quality Analysis Integration
```python
# Ready for Epic 4 quality monitoring
from phoenix_real_estate.collectors.base.rate_limiter import RateLimitObserver

class QualityMonitorObserver(RateLimitObserver):
    """Quality monitoring integration for Epic 4."""
    
    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        # Track rate limiting events for quality analysis
        # Report to Epic 4 monitoring systems
        
    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        # Track request patterns for performance analysis
        # Feed data to Epic 4 analytics engine
```

### Task 05 & Task 06 Integration Points
- **Task 05 (Phoenix MLS Scraper)**: Shared base classes (DataCollector, DataAdapter)
- **Task 06 (LLM Data Processing)**: Property schema compatibility for processing pipeline
- **Parallel Development**: Base classes enable parallel development of other collectors

This comprehensive workflow ensures robust, secure, and maintainable implementation of the Maricopa County API client with full Epic 1 integration and preparation for Epic 3 orchestration.