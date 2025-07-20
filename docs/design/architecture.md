# Phoenix Real Estate System - Architecture Documentation

## Overview

The Phoenix Real Estate Data Collection System is built using clean architecture principles to ensure maintainability, testability, and scalability. This document explains the architectural decisions, design patterns, and implementation strategies used throughout the system.

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   External Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ GitHub       │  │ Maricopa     │  │ PhoenixMLS   │    │
│  │ Actions      │  │ County API   │  │ Website      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Orchestration│  │ Collectors   │  │ Processors   │    │
│  │ Engine       │  │              │  │ (LLM)        │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Foundation Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Repository   │  │ Configuration│  │ Logging &    │    │
│  │ Pattern      │  │ Management   │  │ Monitoring   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ MongoDB      │  │ Webshare.io  │  │ Ollama       │    │
│  │ Atlas        │  │ Proxies      │  │ LLM          │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Clean Architecture Principles

### 1. Dependency Rule

Dependencies only point inward. The inner layers (foundation) know nothing about the outer layers (application/infrastructure).

```python
# ✅ Correct: Application layer depends on Foundation
from phoenix_real_estate.foundation import PropertyRepository

# ❌ Wrong: Foundation depends on Application
from phoenix_real_estate.collectors import MaricopaCollector  # Never in foundation!
```

### 2. Layer Responsibilities

#### Foundation Layer (Core Business Logic)
- **Purpose**: Contains enterprise business rules and core abstractions
- **Components**:
  - Repository interfaces
  - Domain entities
  - Configuration abstractions
  - Logging interfaces
  - Exception hierarchy
- **Dependencies**: None (pure Python)

#### Application Layer (Use Cases)
- **Purpose**: Orchestrates the flow of data and implements use cases
- **Components**:
  - Data collectors
  - Processing engines
  - Orchestration workflows
  - Report generators
- **Dependencies**: Foundation layer only

#### Infrastructure Layer (Frameworks & Drivers)
- **Purpose**: Implements technical details and external integrations
- **Components**:
  - Database connections
  - API clients
  - Web scrapers
  - File system operations
- **Dependencies**: Foundation and Application layers

#### External Layer (External Systems)
- **Purpose**: External services and triggers
- **Components**:
  - GitHub Actions
  - MongoDB Atlas
  - External APIs
  - Web services
- **Dependencies**: Interacts through Infrastructure layer

### 3. Interface Segregation

Each component exposes only the methods it needs:

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class DataCollector(ABC):
    """Interface for all data collectors."""
    
    @abstractmethod
    async def collect_properties(
        self, 
        zip_codes: List[str]
    ) -> List[Property]:
        """Collect properties for given ZIP codes."""
        pass

class Repository(ABC):
    """Base repository interface."""
    
    @abstractmethod
    async def save(self, entity: Entity) -> str:
        """Save entity and return ID."""
        pass
    
    @abstractmethod
    async def find_by_id(self, entity_id: str) -> Optional[Entity]:
        """Find entity by ID."""
        pass

class PropertyRepository(Repository):
    """Specific repository for Property entities."""
    
    async def find_by_zip_code(
        self, 
        zip_code: str
    ) -> List[Property]:
        """Find properties by ZIP code."""
        pass
```

## Design Patterns

### 1. Repository Pattern

Abstracts data persistence details from business logic:

```python
# Foundation layer - defines interface
class PropertyRepository(ABC):
    @abstractmethod
    async def create(self, property_data: PropertyCreate) -> Property:
        pass
    
    @abstractmethod
    async def find_by_address(self, address: Address) -> Optional[Property]:
        pass

# Infrastructure layer - implements interface
class MongoPropertyRepository(PropertyRepository):
    def __init__(self, database: AsyncIOMotorDatabase):
        self._collection = database.properties
    
    async def create(self, property_data: PropertyCreate) -> Property:
        # MongoDB-specific implementation
        result = await self._collection.insert_one(property_data.dict())
        return Property(id=str(result.inserted_id), **property_data.dict())
```

### 2. Factory Pattern

Creates objects without specifying exact classes:

```python
# Logging factory
class LoggerFactory:
    @staticmethod
    def create_logger(
        name: str,
        config: LogConfig
    ) -> structlog.BoundLogger:
        """Create configured logger instance."""
        processors = LoggerFactory._build_processors(config)
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        return structlog.get_logger(name)

# Usage
logger = LoggerFactory.create_logger("collector", log_config)
```

### 3. Strategy Pattern

Allows switching algorithms at runtime:

```python
# Collection strategies
class CollectionStrategy(ABC):
    @abstractmethod
    async def collect(self, target: str) -> List[Property]:
        pass

class APICollectionStrategy(CollectionStrategy):
    async def collect(self, target: str) -> List[Property]:
        # API-specific collection logic
        pass

class WebScrapingStrategy(CollectionStrategy):
    async def collect(self, target: str) -> List[Property]:
        # Web scraping logic with proxy rotation
        pass

# Orchestrator uses strategies
class CollectionOrchestrator:
    def __init__(self, strategy: CollectionStrategy):
        self._strategy = strategy
    
    async def execute_collection(self, targets: List[str]) -> List[Property]:
        results = []
        for target in targets:
            properties = await self._strategy.collect(target)
            results.extend(properties)
        return results
```

### 4. Observer Pattern

Monitors system events and metrics:

```python
# Event system
class EventType(Enum):
    COLLECTION_STARTED = "collection_started"
    COLLECTION_COMPLETED = "collection_completed"
    ERROR_OCCURRED = "error_occurred"

class EventObserver(ABC):
    @abstractmethod
    async def on_event(self, event: Event) -> None:
        pass

class MetricsObserver(EventObserver):
    async def on_event(self, event: Event) -> None:
        if event.type == EventType.COLLECTION_COMPLETED:
            await self._record_collection_metrics(event.data)

class LoggingObserver(EventObserver):
    async def on_event(self, event: Event) -> None:
        logger.info(f"Event: {event.type}", **event.data)

# Event publisher
class EventPublisher:
    def __init__(self):
        self._observers: List[EventObserver] = []
    
    def subscribe(self, observer: EventObserver):
        self._observers.append(observer)
    
    async def publish(self, event: Event):
        for observer in self._observers:
            await observer.on_event(event)
```

### 5. Command Pattern

Encapsulates requests as objects:

```python
# Workflow commands
class WorkflowCommand(ABC):
    @abstractmethod
    async def execute(self) -> WorkflowResult:
        pass
    
    @abstractmethod
    async def undo(self) -> None:
        pass

class CollectPropertiesCommand(WorkflowCommand):
    def __init__(
        self,
        collector: DataCollector,
        zip_codes: List[str],
        repository: PropertyRepository
    ):
        self._collector = collector
        self._zip_codes = zip_codes
        self._repository = repository
        self._collected_ids: List[str] = []
    
    async def execute(self) -> WorkflowResult:
        properties = await self._collector.collect_properties(self._zip_codes)
        
        for property_data in properties:
            property_obj = await self._repository.create(property_data)
            self._collected_ids.append(property_obj.id)
        
        return WorkflowResult(
            success=True,
            data={"collected_count": len(properties)}
        )
    
    async def undo(self) -> None:
        # Rollback by deleting collected properties
        for property_id in self._collected_ids:
            await self._repository.delete(property_id)
```

## Package Structure Explanation

### Foundation Package (`src/phoenix_real_estate/foundation/`)

The foundation package contains core business logic and abstractions:

```
foundation/
├── __init__.py          # Public API exports
├── interfaces.py        # Core interfaces and protocols
├── config/
│   ├── __init__.py
│   └── provider.py     # Configuration abstraction
├── database/
│   ├── __init__.py
│   └── repository.py   # Repository pattern implementation
├── logging/
│   ├── __init__.py
│   └── factory.py      # Logger factory
└── utils/
    ├── __init__.py
    ├── exceptions.py   # Exception hierarchy
    └── helpers.py      # Utility functions
```

**Key Design Decisions**:
- All interfaces defined in `interfaces.py` for easy reference
- Configuration is abstracted to support multiple sources
- Repository pattern hides database implementation details
- Structured logging with contextual information
- Consistent exception hierarchy for error handling

### Collectors Package (`src/phoenix_real_estate/collectors/`)

Implements data collection from various sources:

```
collectors/
├── __init__.py
├── base.py             # Base collector with common functionality
├── maricopa_api.py     # Maricopa County API collector
├── phoenix_mls.py      # PhoenixMLS web scraper
└── strategies/
    ├── __init__.py
    ├── rate_limiter.py # Rate limiting strategy
    └── retry.py        # Retry logic with backoff
```

**Key Design Decisions**:
- Base class provides common functionality (logging, metrics)
- Each collector is independent and can be tested in isolation
- Strategy pattern for rate limiting and retry logic
- Async/await for efficient I/O operations

### Processors Package (`src/phoenix_real_estate/processors/`)

Handles data processing and transformation:

```
processors/
├── __init__.py
├── base.py             # Base processor interface
├── llm_processor.py    # Local LLM processing
└── validators/
    ├── __init__.py
    ├── address.py      # Address validation
    └── property.py     # Property data validation
```

**Key Design Decisions**:
- Local LLM processing for privacy
- Validation separated from processing
- Structured output with confidence scores
- Error handling for malformed data

### Orchestration Package (`src/phoenix_real_estate/orchestration/`)

Coordinates the entire workflow:

```
orchestration/
├── __init__.py
├── engine.py           # Main orchestration engine
├── workflows/
│   ├── __init__.py
│   ├── daily.py       # Daily collection workflow
│   └── weekly.py      # Weekly analysis workflow
└── schedulers/
    ├── __init__.py
    └── github_actions.py # GitHub Actions integration
```

**Key Design Decisions**:
- Workflow pattern for different collection strategies
- Pluggable schedulers (GitHub Actions, cron, etc.)
- Comprehensive error handling and recovery
- Progress tracking and reporting

## Interface Design Rationale

### 1. Dependency Inversion

All dependencies point to abstractions, not concretions:

```python
# ✅ Good: Depends on abstraction
class CollectionOrchestrator:
    def __init__(
        self,
        collectors: List[DataCollector],  # Interface
        repository: PropertyRepository,   # Interface
        logger: Logger                   # Interface
    ):
        self._collectors = collectors
        self._repository = repository
        self._logger = logger

# ❌ Bad: Depends on concrete implementation
class CollectionOrchestrator:
    def __init__(self):
        self._collector = MaricopaAPICollector()  # Concrete class
        self._repository = MongoPropertyRepository()  # Concrete class
```

### 2. Interface Segregation

Interfaces are focused and cohesive:

```python
# ✅ Good: Focused interfaces
class Readable(Protocol):
    async def read(self, identifier: str) -> Optional[Entity]:
        ...

class Writable(Protocol):
    async def write(self, entity: Entity) -> str:
        ...

class Repository(Readable, Writable):
    """Combines reading and writing capabilities."""
    pass

# ❌ Bad: Fat interface
class Repository(Protocol):
    async def read(self, identifier: str) -> Optional[Entity]:
        ...
    
    async def write(self, entity: Entity) -> str:
        ...
    
    async def bulk_import(self, file_path: str) -> int:
        ...
    
    async def export_to_csv(self, output_path: str) -> None:
        ...
    
    # Too many responsibilities!
```

### 3. Protocol-Oriented Design

Using Python protocols for maximum flexibility:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Collector(Protocol):
    """Protocol for data collectors."""
    
    async def collect(self, target: str) -> List[Property]:
        """Collect properties from target."""
        ...
    
    @property
    def source_name(self) -> str:
        """Name of the data source."""
        ...

# Any class implementing these methods works
class CustomCollector:
    async def collect(self, target: str) -> List[Property]:
        return []
    
    @property
    def source_name(self) -> str:
        return "custom"

# Type checking works
def process_collector(collector: Collector) -> None:
    assert isinstance(collector, Collector)  # True!
```

## Future Extension Points

### 1. New Data Sources

Add new collectors by implementing the `DataCollector` interface:

```python
class ZillowCollector(DataCollector):
    """Collect data from Zillow API."""
    
    async def collect_properties(
        self,
        zip_codes: List[str]
    ) -> List[Property]:
        # Implementation here
        pass
```

### 2. Alternative Storage

Replace MongoDB with another database by implementing `PropertyRepository`:

```python
class PostgresPropertyRepository(PropertyRepository):
    """PostgreSQL implementation of property storage."""
    
    def __init__(self, connection_string: str):
        self._engine = create_async_engine(connection_string)
    
    async def create(self, property_data: PropertyCreate) -> Property:
        # PostgreSQL-specific implementation
        pass
```

### 3. New Processing Strategies

Add new processors for different data types:

```python
class ImageProcessor(DataProcessor):
    """Process property images for feature extraction."""
    
    async def process(
        self,
        images: List[Image]
    ) -> PropertyFeatures:
        # ML-based image analysis
        pass
```

### 4. Additional Workflows

Create new workflows for different schedules or purposes:

```python
class HourlyPriceCheckWorkflow(Workflow):
    """Check price changes every hour for tracked properties."""
    
    async def execute(self) -> WorkflowResult:
        tracked_properties = await self._get_tracked_properties()
        # Price checking logic
        pass
```

## Performance Considerations

### 1. Asynchronous I/O

All I/O operations use async/await for efficiency:

```python
# Concurrent collection from multiple sources
async def collect_all_sources(collectors: List[DataCollector]) -> List[Property]:
    tasks = [
        collector.collect_properties(["85001"])
        for collector in collectors
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_properties = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Collection failed", error=str(result))
        else:
            all_properties.extend(result)
    
    return all_properties
```

### 2. Connection Pooling

Database connections are pooled for efficiency:

```python
class DatabaseConfig:
    max_connections: int = 10
    min_connections: int = 2
    connection_timeout: float = 10.0

class MongoConnectionPool:
    def __init__(self, config: DatabaseConfig):
        self._client = AsyncIOMotorClient(
            config.connection_string,
            maxPoolSize=config.max_connections,
            minPoolSize=config.min_connections,
            serverSelectionTimeoutMS=int(config.connection_timeout * 1000)
        )
```

### 3. Caching Strategy

Implement caching where appropriate:

```python
from functools import lru_cache
from typing import Dict

class ConfigurationCache:
    def __init__(self, config_provider: ConfigProvider):
        self._provider = config_provider
        self._cache: Dict[str, Any] = {}
    
    @lru_cache(maxsize=128)
    def get_cached(self, key: str) -> Any:
        """Get configuration value with caching."""
        if key not in self._cache:
            self._cache[key] = self._provider.get(key)
        return self._cache[key]
```

### 4. Batch Processing

Process data in batches for efficiency:

```python
async def batch_save_properties(
    repository: PropertyRepository,
    properties: List[Property],
    batch_size: int = 100
) -> List[str]:
    """Save properties in batches."""
    saved_ids = []
    
    for i in range(0, len(properties), batch_size):
        batch = properties[i:i + batch_size]
        
        # Save batch concurrently
        tasks = [repository.create(prop) for prop in batch]
        results = await asyncio.gather(*tasks)
        
        saved_ids.extend([r.id for r in results])
    
    return saved_ids
```

## Security Considerations

### 1. Configuration Security

Sensitive data never hardcoded:

```python
class SecureConfigProvider(ConfigProvider):
    """Secure configuration with encryption support."""
    
    def __init__(self):
        self._load_from_environment()
        self._load_from_secret_manager()
    
    def get_secret(self, key: str) -> str:
        """Get decrypted secret value."""
        encrypted = os.environ.get(f"ENCRYPTED_{key}")
        if encrypted:
            return self._decrypt(encrypted)
        raise ConfigurationError(f"Secret {key} not found")
```

### 2. Input Validation

All external input validated:

```python
from pydantic import BaseModel, validator

class AddressInput(BaseModel):
    """Validated address input."""
    
    street: str
    city: str
    state: str
    zip_code: str
    
    @validator("zip_code")
    def validate_zip_code(cls, v):
        if not re.match(r"^\d{5}(-\d{4})?$", v):
            raise ValueError("Invalid ZIP code format")
        return v
    
    @validator("state")
    def validate_state(cls, v):
        if v.upper() != "AZ":
            raise ValueError("Only Arizona properties supported")
        return v.upper()
```

### 3. Rate Limiting

Protect against API abuse:

```python
class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(
        self,
        rate: float,
        burst: int
    ):
        self._rate = rate
        self._burst = burst
        self._tokens = burst
        self._last_update = time.time()
    
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary."""
        while self._tokens < tokens:
            await self._refill()
            await asyncio.sleep(0.1)
        
        self._tokens -= tokens
```

### 4. Error Information Security

Never expose sensitive data in errors:

```python
class SecureError(Exception):
    """Base exception with secure error messages."""
    
    def __init__(
        self,
        public_message: str,
        internal_details: Optional[str] = None
    ):
        self.public_message = public_message
        self.internal_details = internal_details
        super().__init__(public_message)
    
    def log_internal(self, logger: Logger) -> None:
        """Log internal details securely."""
        if self.internal_details:
            logger.error(
                "Internal error details",
                details=self.internal_details,
                _private=True  # Flag for secure logging
            )
```

## Testing Strategy

### 1. Unit Testing

Test individual components in isolation:

```python
@pytest.mark.asyncio
async def test_property_repository_create():
    """Test property creation in repository."""
    # Arrange
    mock_db = AsyncMock()
    repository = MongoPropertyRepository(mock_db)
    property_data = PropertyCreate(
        address=Address(
            street="123 Main St",
            city="Phoenix",
            state="AZ",
            zip_code="85001"
        ),
        features=PropertyFeatures(beds=3, baths=2, sqft=1500)
    )
    
    # Act
    result = await repository.create(property_data)
    
    # Assert
    assert result.id is not None
    mock_db.properties.insert_one.assert_called_once()
```

### 2. Integration Testing

Test component interactions:

```python
@pytest.mark.integration
async def test_collection_workflow():
    """Test complete collection workflow."""
    # Setup real test database
    test_db = await create_test_database()
    
    # Create real components
    config = ConfigProvider(Environment.TESTING)
    repository = MongoPropertyRepository(test_db)
    collector = MaricopaAPICollector(config, repository)
    orchestrator = CollectionOrchestrator([collector], repository)
    
    # Execute workflow
    result = await orchestrator.run_daily_collection()
    
    # Verify results
    assert result.success
    assert result.properties_collected > 0
    
    # Cleanup
    await cleanup_test_database(test_db)
```

### 3. Contract Testing

Verify interface implementations:

```python
class TestDataCollectorContract:
    """Contract tests for DataCollector implementations."""
    
    @pytest.fixture
    def collector_implementation(self) -> DataCollector:
        """Override in subclasses to provide implementation."""
        raise NotImplementedError
    
    async def test_implements_collect_method(self, collector_implementation):
        """Test that collector implements required method."""
        assert hasattr(collector_implementation, "collect_properties")
        assert callable(collector_implementation.collect_properties)
    
    async def test_returns_property_list(self, collector_implementation):
        """Test that collector returns correct type."""
        result = await collector_implementation.collect_properties(["85001"])
        assert isinstance(result, list)
        assert all(isinstance(p, Property) for p in result)
```

## Monitoring and Observability

### 1. Structured Logging

Consistent log format across the system:

```python
logger = structlog.get_logger()

# Rich contextual logging
logger.info(
    "collection_started",
    collector="maricopa_api",
    zip_codes=["85001", "85002"],
    request_id=request_id
)

# Automatic context preservation
with structlog.contextvars.bind_contextvars(
    user_id=user_id,
    session_id=session_id
):
    await process_user_request()  # All logs include context
```

### 2. Metrics Collection

Track key performance indicators:

```python
class MetricsCollector:
    """Collect and expose system metrics."""
    
    def __init__(self):
        self._metrics = {
            "properties_collected": Counter("properties_collected_total"),
            "collection_duration": Histogram("collection_duration_seconds"),
            "api_errors": Counter("api_errors_total"),
            "cache_hits": Counter("cache_hits_total")
        }
    
    def record_collection(
        self,
        source: str,
        count: int,
        duration: float
    ):
        self._metrics["properties_collected"].labels(source=source).inc(count)
        self._metrics["collection_duration"].labels(source=source).observe(duration)
```

### 3. Health Checks

System health monitoring endpoints:

```python
class HealthChecker:
    """System health check implementation."""
    
    async def check_health(self) -> HealthStatus:
        """Check overall system health."""
        checks = {
            "database": self._check_database(),
            "api_connectivity": self._check_api_connectivity(),
            "disk_space": self._check_disk_space(),
            "memory_usage": self._check_memory_usage()
        }
        
        results = await asyncio.gather(
            *checks.values(),
            return_exceptions=True
        )
        
        return HealthStatus(
            healthy=all(r.healthy for r in results if not isinstance(r, Exception)),
            checks=dict(zip(checks.keys(), results))
        )
```

## Deployment Architecture

### 1. Container Structure

Multi-stage Docker builds for optimization:

```dockerfile
# Build stage
FROM python:3.13-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Runtime stage
FROM python:3.13-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

CMD ["python", "-m", "phoenix_real_estate.orchestration.workflows.daily"]
```

### 2. Environment Management

Environment-specific configurations:

```yaml
# config/production.yaml
database:
  connection_string: ${MONGO_CONNECTION_STRING}
  max_connections: 20
  timeout: 30

collection:
  rate_limit:
    requests_per_hour: 1000
    burst_size: 50
  retry:
    max_attempts: 3
    backoff_factor: 2

monitoring:
  log_level: INFO
  metrics_enabled: true
  health_check_interval: 60
```

### 3. Scalability Considerations

Design for horizontal scaling:

```python
class DistributedOrchestrator:
    """Orchestrator with distributed locking."""
    
    def __init__(
        self,
        lock_manager: DistributedLockManager
    ):
        self._lock_manager = lock_manager
    
    async def run_exclusive_task(
        self,
        task_id: str,
        task_func: Callable
    ) -> Any:
        """Run task with distributed lock."""
        async with self._lock_manager.acquire(f"task:{task_id}"):
            # Only one instance runs this task
            return await task_func()
```

## Conclusion

The Phoenix Real Estate Data Collection System architecture provides:

1. **Maintainability**: Clean separation of concerns and dependency inversion
2. **Testability**: All components can be tested in isolation
3. **Extensibility**: Easy to add new data sources and features
4. **Reliability**: Comprehensive error handling and monitoring
5. **Performance**: Efficient async I/O and resource management
6. **Security**: Input validation and secure configuration

The architecture follows industry best practices while remaining pragmatic and focused on delivering value within the project's constraints.