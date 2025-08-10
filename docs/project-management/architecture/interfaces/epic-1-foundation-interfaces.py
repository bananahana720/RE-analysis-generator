"""
Phoenix Real Estate System - Epic 1 Foundation Infrastructure Interfaces

This module defines the core interfaces and protocols provided by Epic 1 that all other epics
depend upon. These interfaces establish the architectural contracts for configuration management,
data persistence, logging, monitoring, and error handling.

Key Design Principles:
- Protocol-based design for type safety and testability
- Abstract base classes for implementation guidance
- Comprehensive type hints for IDE and static analysis support
- Integration with dependency injection patterns
- Support for multiple environments (dev/test/prod)
"""

from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    Protocol,
    runtime_checkable,
    TypeVar,
    Awaitable,
    AsyncContextManager,
)
from datetime import datetime, UTC
from enum import Enum
from dataclasses import dataclass

# ==============================================================================
# Core Types and Enumerations
# ==============================================================================

T = TypeVar("T")
ConfigValue = Union[str, int, float, bool, List[Any], Dict[str, Any]]


class Environment(Enum):
    """Environment types supported by the system."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(Enum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class HealthCheckResult:
    """Result of a component health check."""

    component: str
    healthy: bool
    message: str
    timestamp: datetime
    response_time_ms: float
    metadata: Dict[str, Any]


# ==============================================================================
# Configuration Management Interfaces
# ==============================================================================


@runtime_checkable
class ConfigProvider(Protocol):
    """
    Configuration management interface for environment-aware configuration.

    Provides layered configuration resolution:
    1. Environment variables (highest priority)
    2. Environment-specific files (config/production.yaml)
    3. Base configuration (config/base.yaml)
    4. Default values (lowest priority)
    """

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with optional default.

        Args:
            key: Configuration key (supports nested keys with __ separator)
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config.get("DATABASE__CONNECTION_TIMEOUT", 30)
        """
        ...

    def get_required(self, key: str) -> Any:
        """
        Get required configuration value, raise error if missing.

        Args:
            key: Configuration key

        Returns:
            Configuration value

        Raises:
            ConfigurationError: If required key is missing
        """
        ...

    def get_int(self, key: str, default: Optional[int] = None) -> int:
        """Get configuration value as integer with type validation."""
        ...

    def get_float(self, key: str, default: Optional[float] = None) -> float:
        """Get configuration value as float with type validation."""
        ...

    def get_bool(self, key: str, default: Optional[bool] = None) -> bool:
        """Get configuration value as boolean with type validation."""
        ...

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """Get configuration value as list with type validation."""
        ...

    @property
    def environment(self) -> Environment:
        """Current environment (development/testing/production)."""
        ...

    def validate_required_keys(self, required_keys: List[str]) -> None:
        """
        Validate that all required configuration keys are present.

        Args:
            required_keys: List of required configuration keys

        Raises:
            ConfigurationError: If any required keys are missing
        """
        ...


class ConfigurationFactory(ABC):
    """Factory for creating environment-specific configuration providers."""

    @staticmethod
    @abstractmethod
    async def create_config(environment: Environment) -> ConfigProvider:
        """Create configuration provider for specified environment."""
        pass


# ==============================================================================
# Database and Repository Interfaces
# ==============================================================================


@runtime_checkable
class DatabaseConnection(Protocol):
    """Database connection management interface."""

    async def connect(self) -> None:
        """Establish database connection with retry logic."""
        ...

    async def disconnect(self) -> None:
        """Close database connection gracefully."""
        ...

    async def ping(self) -> bool:
        """Test database connectivity."""
        ...

    @property
    def is_connected(self) -> bool:
        """Check if connection is currently active."""
        ...

    async def get_connection_info(self) -> Dict[str, Any]:
        """Get connection metadata for monitoring."""
        ...


@runtime_checkable
class PropertyRepository(Protocol):
    """
    Property data repository interface.

    Provides data access layer abstraction for property information.
    All Epic 2 collectors and Epic 3 orchestration must use this interface
    for data persistence to ensure consistency and testability.
    """

    async def create(self, property_data: Dict[str, Any]) -> str:
        """
        Create new property record.

        Args:
            property_data: Property information following standard schema

        Returns:
            Unique property identifier

        Raises:
            DatabaseError: If creation fails
            ValidationError: If property data invalid
        """
        ...

    async def get_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve property by unique identifier.

        Args:
            property_id: Unique property identifier

        Returns:
            Property data or None if not found
        """
        ...

    async def update(self, property_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing property record.

        Args:
            property_id: Unique property identifier
            updates: Fields to update

        Returns:
            True if update successful, False if property not found

        Raises:
            DatabaseError: If update operation fails
        """
        ...

    async def delete(self, property_id: str) -> bool:
        """
        Delete property record.

        Args:
            property_id: Unique property identifier

        Returns:
            True if deletion successful, False if property not found
        """
        ...

    async def search_by_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        """
        Search properties by ZIP code.

        Args:
            zipcode: 5-digit ZIP code

        Returns:
            List of properties in the specified ZIP code
        """
        ...

    async def search_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search properties by multiple criteria.

        Args:
            criteria: Search criteria (price_range, beds, baths, etc.)

        Returns:
            List of properties matching criteria
        """
        ...

    async def get_collection_stats(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get collection statistics for date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Statistics including count, sources, quality metrics
        """
        ...

    async def bulk_create(self, properties: List[Dict[str, Any]]) -> List[str]:
        """
        Create multiple property records efficiently.

        Args:
            properties: List of property data dictionaries

        Returns:
            List of created property identifiers
        """
        ...


class RepositoryFactory(ABC):
    """Factory for creating repository implementations."""

    @staticmethod
    @abstractmethod
    async def create_repository(
        config: ConfigProvider, connection: DatabaseConnection
    ) -> PropertyRepository:
        """Create repository instance with database connection."""
        pass


# ==============================================================================
# Logging and Monitoring Interfaces
# ==============================================================================


@runtime_checkable
class Logger(Protocol):
    """
    Structured logging interface for system-wide logging.

    Provides consistent logging patterns across all epics with support for
    structured data, correlation IDs, and environment-specific formatting.
    """

    def debug(self, message: str, *, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug-level message with optional structured data."""
        ...

    def info(self, message: str, *, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info-level message with optional structured data."""
        ...

    def warning(self, message: str, *, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning-level message with optional structured data."""
        ...

    def error(self, message: str, *, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error-level message with optional structured data."""
        ...

    def critical(self, message: str, *, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log critical-level message with optional structured data."""
        ...

    def exception(self, message: str, *, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log exception with full traceback information."""
        ...

    @property
    def name(self) -> str:
        """Logger name for identification."""
        ...

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracing."""
        ...


def get_logger(name: str) -> Logger:
    """
    Get logger instance for specified name.

    This is the primary interface for all epics to obtain logger instances.
    Loggers are configured based on environment and provide consistent
    formatting and output handling.

    Args:
        name: Logger name (typically module.component)

    Returns:
        Configured logger instance
    """
    ...


@runtime_checkable
class MetricsCollector(Protocol):
    """
    Metrics collection interface for monitoring and observability.

    Provides standardized metrics collection used by Epic 3 orchestration
    and Epic 4 quality monitoring for performance tracking and alerting.
    """

    async def record_counter(
        self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record counter metric (monotonically increasing value).

        Args:
            name: Metric name
            value: Counter increment (default 1)
            tags: Optional tags for metric classification
        """
        ...

    async def record_gauge(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record gauge metric (point-in-time value).

        Args:
            name: Metric name
            value: Current gauge value
            tags: Optional tags for metric classification
        """
        ...

    async def record_histogram(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record histogram metric (distribution of values).

        Args:
            name: Metric name
            value: Measured value
            tags: Optional tags for metric classification
        """
        ...

    async def record_timing(
        self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record timing metric (operation duration).

        Args:
            name: Metric name
            duration_ms: Duration in milliseconds
            tags: Optional tags for metric classification
        """
        ...

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all recorded metrics."""
        ...


@runtime_checkable
class HealthChecker(Protocol):
    """Health checking interface for system components."""

    async def check_health(self, component: str) -> HealthCheckResult:
        """
        Check health of specified component.

        Args:
            component: Component name to check

        Returns:
            Health check result with status and metadata
        """
        ...

    async def check_all_components(self) -> Dict[str, HealthCheckResult]:
        """Check health of all registered components."""
        ...

    def register_component(self, name: str, check_function: Awaitable[HealthCheckResult]) -> None:
        """Register component for health checking."""
        ...


# ==============================================================================
# Error Handling and Exception Interfaces
# ==============================================================================


class BasePhoenixException(Exception):
    """
    Base exception for all Phoenix Real Estate system errors.

    Provides structured error information including context, recoverability,
    and retry guidance for consistent error handling across all epics.
    """

    def __init__(
        self,
        message: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = False,
        retry_after_seconds: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause
        self.recoverable = recoverable
        self.retry_after_seconds = retry_after_seconds
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "exception_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "recoverable": self.recoverable,
            "retry_after_seconds": self.retry_after_seconds,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }


class ConfigurationError(BasePhoenixException):
    """Configuration loading or validation errors."""

    def __init__(self, message: str, *, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        super().__init__(message, context=context, **kwargs)


class DatabaseError(BasePhoenixException):
    """Database connection or operation errors."""

    def __init__(
        self,
        message: str,
        *,
        operation: Optional[str] = None,
        property_id: Optional[str] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if operation:
            context["operation"] = operation
        if property_id:
            context["property_id"] = property_id

        # Database errors are often recoverable
        kwargs.setdefault("recoverable", True)
        kwargs.setdefault("retry_after_seconds", 30)

        super().__init__(message, context=context, **kwargs)


class ValidationError(BasePhoenixException):
    """Data validation errors."""

    def __init__(self, message: str, *, validation_errors: Optional[List[str]] = None, **kwargs):
        context = kwargs.get("context", {})
        if validation_errors:
            context["validation_errors"] = validation_errors
        super().__init__(message, context=context, **kwargs)


class LoggingError(BasePhoenixException):
    """Logging system failures."""

    pass


# ==============================================================================
# Utility and Helper Interfaces
# ==============================================================================


@runtime_checkable
class Configurable(Protocol):
    """Protocol for components that require configuration."""

    def configure(self, config: ConfigProvider) -> None:
        """Configure component with provided configuration."""
        ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for data validation."""

    def validate(self) -> bool:
        """Validate data, return True if valid."""
        ...

    def get_errors(self) -> List[str]:
        """Get list of validation errors."""
        ...


@runtime_checkable
class Serializable(Protocol):
    """Protocol for data serialization."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        ...

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Serializable":
        """Create instance from dictionary representation."""
        ...


@runtime_checkable
class AsyncInitializable(Protocol):
    """Protocol for components requiring async initialization."""

    async def initialize(self) -> None:
        """Initialize component asynchronously."""
        ...

    async def cleanup(self) -> None:
        """Clean up resources asynchronously."""
        ...


class RetryPolicy(ABC):
    """Abstract base class for retry policies."""

    @abstractmethod
    async def should_retry(self, exception: Exception, attempt: int, max_attempts: int) -> bool:
        """Determine if operation should be retried."""
        pass

    @abstractmethod
    async def get_delay(self, attempt: int) -> float:
        """Get delay before next retry attempt."""
        pass


# ==============================================================================
# Context Managers and Resource Management
# ==============================================================================


@runtime_checkable
class DatabaseTransaction(AsyncContextManager[None], Protocol):
    """Database transaction context manager."""

    async def commit(self) -> None:
        """Commit transaction changes."""
        ...

    async def rollback(self) -> None:
        """Rollback transaction changes."""
        ...


@runtime_checkable
class ConnectionPool(Protocol):
    """Database connection pool interface."""

    async def acquire(self) -> DatabaseConnection:
        """Acquire connection from pool."""
        ...

    async def release(self, connection: DatabaseConnection) -> None:
        """Release connection back to pool."""
        ...

    @property
    def size(self) -> int:
        """Current pool size."""
        ...

    @property
    def available(self) -> int:
        """Available connections."""
        ...


# ==============================================================================
# Factory and Builder Interfaces
# ==============================================================================


class FoundationFactory(ABC):
    """
    Factory for creating Epic 1 foundation components.

    Provides centralized creation of foundation components with proper
    dependency injection and configuration management.
    """

    @staticmethod
    @abstractmethod
    async def create_config_provider(environment: Environment) -> ConfigProvider:
        """Create configuration provider for environment."""
        pass

    @staticmethod
    @abstractmethod
    async def create_database_connection(config: ConfigProvider) -> DatabaseConnection:
        """Create database connection with configuration."""
        pass

    @staticmethod
    @abstractmethod
    async def create_repository(
        config: ConfigProvider, connection: DatabaseConnection
    ) -> PropertyRepository:
        """Create property repository with dependencies."""
        pass

    @staticmethod
    @abstractmethod
    async def create_metrics_collector(config: ConfigProvider) -> MetricsCollector:
        """Create metrics collector with configuration."""
        pass

    @staticmethod
    @abstractmethod
    async def create_health_checker(config: ConfigProvider) -> HealthChecker:
        """Create health checker with configuration."""
        pass


# ==============================================================================
# Integration Contracts for Other Epics
# ==============================================================================


class Epic1ServiceProvider(ABC):
    """
    Service provider interface for Epic 1 foundation services.

    This interface defines what Epic 1 provides to Epic 2, 3, and 4 for
    integration purposes. It serves as the main dependency injection point
    for foundation services.
    """

    @property
    @abstractmethod
    def config(self) -> ConfigProvider:
        """Configuration provider instance."""
        pass

    @property
    @abstractmethod
    def repository(self) -> PropertyRepository:
        """Property repository instance."""
        pass

    @property
    @abstractmethod
    def metrics(self) -> MetricsCollector:
        """Metrics collector instance."""
        pass

    @property
    @abstractmethod
    def health_checker(self) -> HealthChecker:
        """Health checker instance."""
        pass

    @abstractmethod
    def get_logger(self, name: str) -> Logger:
        """Get logger instance for specified name."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize all foundation services."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown all foundation services gracefully."""
        pass


# ==============================================================================
# Usage Examples and Documentation
# ==============================================================================

"""
Example Usage for Epic 2 (Data Collection Engine):

```python
from phoenix_real_estate.foundation import Epic1ServiceProvider

class MaricopaAPICollector:
    def __init__(self, foundation: Epic1ServiceProvider):
        self.config = foundation.config
        self.repository = foundation.repository
        self.logger = foundation.get_logger("maricopa.collector")
    
    async def collect_zipcode(self, zipcode: str) -> List[Dict[str, Any]]:
        api_key = self.config.get_required("MARICOPA_API_KEY")
        
        try:
            # Collect data from API
            properties = await self._fetch_properties(api_key, zipcode)
            
            # Store via repository
            for property_data in properties:
                property_id = await self.repository.create(property_data)
                self.logger.info(
                    "Property stored",
                    extra={"property_id": property_id, "zipcode": zipcode}
                )
            
            return properties
            
        except Exception as e:
            self.logger.error(
                "Collection failed",
                extra={"zipcode": zipcode, "error": str(e)}
            )
            raise DataCollectionError(
                f"Failed to collect data for zipcode {zipcode}",
                context={"zipcode": zipcode},
                cause=e
            ) from e
```

Example Usage for Epic 3 (Automation & Orchestration):

```python
from phoenix_real_estate.foundation import Epic1ServiceProvider

class OrchestrationEngine:
    def __init__(self, foundation: Epic1ServiceProvider):
        self.config = foundation.config
        self.repository = foundation.repository
        self.metrics = foundation.metrics
        self.logger = foundation.get_logger("automation.orchestration")
    
    async def run_daily_workflow(self) -> Dict[str, Any]:
        await self.metrics.record_counter("workflow_started")
        
        try:
            # Get configuration
            zip_codes = self.config.get_required("TARGET_ZIP_CODES").split(",")
            
            # Execute collection workflow
            results = await self._orchestrate_collection(zip_codes)
            
            # Generate report using repository
            report = await self._generate_report()
            
            await self.metrics.record_counter("workflow_completed")
            return {"success": True, "results": results, "report": report}
            
        except Exception as e:
            await self.metrics.record_counter("workflow_failed")
            self.logger.error("Workflow failed", extra={"error": str(e)})
            raise
```
"""
