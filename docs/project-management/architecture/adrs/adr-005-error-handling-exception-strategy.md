# ADR-005: Error Handling and Exception Strategy

## Status
**ACCEPTED** - Implemented in Epic 1 Foundation Infrastructure

## Context
The Phoenix Real Estate Data Collection System requires a comprehensive error handling strategy that provides consistent error management across all four epics. The system must handle:

- Network failures and API timeouts (Epic 2 data collection)
- Database connection issues (Epic 1 foundation)
- Workflow execution failures (Epic 3 orchestration)
- Quality validation errors (Epic 4 monitoring)
- LLM processing failures and proxy issues
- Partial failure scenarios where some components succeed while others fail
- Error recovery and retry mechanisms
- Comprehensive error logging and debugging information

Several error handling approaches were considered:

### Option 1: Generic Exception Handling
- Use Python's built-in exceptions
- Simple but lacks context and structure
- Difficult to implement consistent error handling patterns
- No standardized error information or recovery strategies

### Option 2: Custom Exception Hierarchy with Context
- Structured exception hierarchy with domain-specific exceptions
- Rich error context including cause chain and recovery information
- Standardized error handling patterns across all epics
- Integration with logging and monitoring systems

### Option 3: Result Pattern (Rust-style)
- Explicit error handling with Result[T, Error] types
- No exceptions, all errors are values
- Verbose but explicit error handling
- Not idiomatic in Python ecosystem

## Decision
**We will implement Custom Exception Hierarchy with Context** as the primary error handling strategy.

### Architecture Decision
```
BasePhoenixException (root)
├── ConfigurationError (Epic 1)
├── DatabaseError (Epic 1)
├── DataCollectionError (Epic 2)
├── ProcessingError (Epic 2)
├── OrchestrationError (Epic 3)
├── WorkflowExecutionError (Epic 3)
├── QualityAssuranceError (Epic 4)
└── ValidationError (Epic 4)
```

### Key Implementation
```python
# Epic 1: Foundation exception framework
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

class BasePhoenixException(Exception):
    """Base exception for all Phoenix Real Estate system errors."""
    
    def __init__(
        self,
        message: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = False,
        retry_after_seconds: Optional[int] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause
        self.recoverable = recoverable
        self.retry_after_seconds = retry_after_seconds
        self.timestamp = datetime.utcnow()
        self.traceback_info = traceback.format_exc()
    
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
            "traceback": self.traceback_info
        }
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " | ".join(parts)
```

## Consequences

### Positive Consequences
1. **Consistency**: Standardized error handling patterns across all epics
2. **Rich Context**: Detailed error information for debugging and monitoring
3. **Recoverability**: Clear indication of which errors can be retried
4. **Traceability**: Complete error chain preservation for root cause analysis
5. **Integration**: Seamless integration with Epic 1's logging framework
6. **Monitoring**: Structured error data for Epic 4's quality monitoring
7. **Documentation**: Self-documenting error scenarios and recovery strategies

### Negative Consequences
1. **Complexity**: More complex than generic exception handling
2. **Learning Curve**: Developers must understand exception hierarchy
3. **Verbosity**: More code required for proper exception handling
4. **Performance**: Minor overhead from context and metadata collection

## Epic-Specific Exception Classes

### Epic 1: Foundation Infrastructure Exceptions
```python
class ConfigurationError(BasePhoenixException):
    """Configuration loading or validation errors."""
    
    def __init__(self, message: str, *, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        super().__init__(message, context=context, **kwargs)

class DatabaseError(BasePhoenixException):
    """Database connection or operation errors."""
    
    def __init__(
        self, 
        message: str, 
        *, 
        operation: Optional[str] = None,
        property_id: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if operation:
            context['operation'] = operation
        if property_id:
            context['property_id'] = property_id
        
        # Database errors are often recoverable
        kwargs.setdefault('recoverable', True)
        kwargs.setdefault('retry_after_seconds', 30)
        
        super().__init__(message, context=context, **kwargs)

class LoggingError(BasePhoenixException):
    """Logging system failures."""
    pass
```

### Epic 2: Data Collection Exceptions
```python
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
```

### Epic 3: Automation & Orchestration Exceptions
```python
class OrchestrationError(BasePhoenixException):
    """Orchestration engine errors."""
    
    def __init__(
        self,
        message: str,
        *,
        orchestration_mode: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if orchestration_mode:
            context['orchestration_mode'] = orchestration_mode
        
        super().__init__(message, context=context, **kwargs)

class WorkflowExecutionError(BasePhoenixException):
    """Workflow execution errors."""
    
    def __init__(
        self,
        message: str,
        *,
        workflow_name: Optional[str] = None,
        step: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if workflow_name:
            context['workflow_name'] = workflow_name
        if step:
            context['step'] = step
        
        super().__init__(message, context=context, **kwargs)

class DeploymentError(BasePhoenixException):
    """Deployment operation errors."""
    
    def __init__(
        self,
        message: str,
        *,
        environment: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if environment:
            context['environment'] = environment
        
        super().__init__(message, context=context, **kwargs)
```

### Epic 4: Quality Assurance Exceptions
```python
class QualityAssuranceError(BasePhoenixException):
    """Quality monitoring and validation errors."""
    
    def __init__(
        self,
        message: str,
        *,
        quality_check: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if quality_check:
            context['quality_check'] = quality_check
        
        super().__init__(message, context=context, **kwargs)

class ValidationError(BasePhoenixException):
    """Data or system validation errors."""
    
    def __init__(
        self,
        message: str,
        *,
        validator: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if validator:
            context['validator'] = validator
        if validation_errors:
            context['validation_errors'] = validation_errors
        
        super().__init__(message, context=context, **kwargs)

class ComplianceError(QualityAssuranceError):
    """Compliance validation errors."""
    
    def __init__(
        self,
        message: str,
        *,
        compliance_rule: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if compliance_rule:
            context['compliance_rule'] = compliance_rule
        
        # Compliance errors are typically not recoverable
        kwargs.setdefault('recoverable', False)
        
        super().__init__(message, context=context, **kwargs)
```

## Error Handling Patterns

### Retry Mechanism with Exponential Backoff
```python
import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')

async def retry_with_backoff(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    logger: Optional[Logger] = None
) -> T:
    """Retry operation with exponential backoff for recoverable errors."""
    
    for attempt in range(max_retries + 1):
        try:
            return await operation()
            
        except BasePhoenixException as e:
            if not e.recoverable or attempt == max_retries:
                if logger:
                    logger.error(
                        "Operation failed permanently",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "error": e.to_dict()
                        }
                    )
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            if e.retry_after_seconds:
                delay = max(delay, e.retry_after_seconds)
            
            if logger:
                logger.warning(
                    "Operation failed, retrying",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "retry_delay": delay,
                        "error": e.to_dict()
                    }
                )
            
            await asyncio.sleep(delay)
```

### Circuit Breaker Pattern
```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        logger_name: str = "circuit_breaker"
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.logger = get_logger(logger_name)
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Execute operation through circuit breaker."""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise OrchestrationError(
                    "Circuit breaker is open",
                    context={"failure_count": self.failure_count},
                    recoverable=True,
                    retry_after_seconds=self.reset_timeout
                )
        
        try:
            result = await operation()
            self._on_success()
            return result
            
        except BasePhoenixException as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.reset_timeout)
    
    def _on_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.logger.info("Circuit breaker reset to closed state")
    
    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(
                "Circuit breaker opened",
                extra={"failure_count": self.failure_count}
            )
```

### Graceful Degradation Pattern
```python
from typing import Optional, Union

class GracefulDegradation:
    """Handle partial failures with graceful degradation."""
    
    @staticmethod
    async def collect_with_fallback(
        primary_collector: DataCollector,
        fallback_collector: Optional[DataCollector],
        zipcode: str,
        logger: Logger
    ) -> List[Dict[str, Any]]:
        """Attempt collection with primary, fallback to secondary if needed."""
        
        try:
            # Try primary collector
            properties = await primary_collector.collect_zipcode(zipcode)
            logger.info(
                "Primary collection successful",
                extra={
                    "source": primary_collector.get_source_name(),
                    "zipcode": zipcode,
                    "property_count": len(properties)
                }
            )
            return properties
            
        except BasePhoenixException as e:
            logger.error(
                "Primary collection failed",
                extra={
                    "source": primary_collector.get_source_name(),
                    "zipcode": zipcode,
                    "error": e.to_dict()
                }
            )
            
            # Try fallback if available
            if fallback_collector:
                try:
                    properties = await fallback_collector.collect_zipcode(zipcode)
                    logger.warning(
                        "Fallback collection successful",
                        extra={
                            "source": fallback_collector.get_source_name(),
                            "zipcode": zipcode,
                            "property_count": len(properties)
                        }
                    )
                    return properties
                    
                except BasePhoenixException as fallback_error:
                    logger.error(
                        "Fallback collection also failed",
                        extra={
                            "source": fallback_collector.get_source_name(),
                            "zipcode": zipcode,
                            "error": fallback_error.to_dict()
                        }
                    )
            
            # Re-raise original error if no fallback or fallback failed
            raise e
```

## Integration with Logging Framework
```python
# Epic 1: Logging integration with error handling
class ErrorLoggingHandler:
    """Handle error logging with structured format."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def log_exception(
        self,
        exception: BasePhoenixException,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log exception with full context and structure."""
        
        log_data = exception.to_dict()
        if additional_context:
            log_data['additional_context'] = additional_context
        
        # Determine log level based on recoverability
        if exception.recoverable:
            self.logger.warning("Recoverable error occurred", extra=log_data)
        else:
            self.logger.error("Non-recoverable error occurred", extra=log_data)
    
    def log_error_recovery(
        self,
        original_error: BasePhoenixException,
        recovery_action: str,
        success: bool
    ) -> None:
        """Log error recovery attempts."""
        
        self.logger.info(
            "Error recovery attempted",
            extra={
                "original_error": original_error.to_dict(),
                "recovery_action": recovery_action,
                "recovery_success": success
            }
        )
```

## Error Monitoring and Alerting
```python
# Epic 4: Quality monitoring integration
class ErrorMonitor:
    """Monitor error patterns for quality assurance."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.error_counts: Dict[str, int] = {}
    
    async def record_error(self, exception: BasePhoenixException) -> None:
        """Record error for monitoring and alerting."""
        
        error_type = exception.__class__.__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Record metrics
        await self.metrics.record_counter(
            name="error_count",
            value=1,
            tags={
                "error_type": error_type,
                "recoverable": str(exception.recoverable),
                "epic": self._determine_epic(exception)
            }
        )
        
        # Check for error rate thresholds
        if self._should_alert(error_type):
            await self._send_alert(exception)
    
    def _determine_epic(self, exception: BasePhoenixException) -> str:
        """Determine which epic the error originated from."""
        class_name = exception.__class__.__name__
        
        if class_name in ['ConfigurationError', 'DatabaseError', 'LoggingError']:
            return 'foundation'
        elif class_name in ['DataCollectionError', 'ProcessingError', 'RateLimitError', 'ProxyError']:
            return 'collection'
        elif class_name in ['OrchestrationError', 'WorkflowExecutionError', 'DeploymentError']:
            return 'automation'
        elif class_name in ['QualityAssuranceError', 'ValidationError', 'ComplianceError']:
            return 'quality'
        else:
            return 'unknown'
```

## Testing Error Handling
```python
# Test framework for error handling
class TestErrorHandling:
    def test_exception_hierarchy(self):
        """Test that all custom exceptions inherit from BasePhoenixException."""
        config_error = ConfigurationError("Test config error")
        assert isinstance(config_error, BasePhoenixException)
        assert config_error.to_dict()['exception_type'] == 'ConfigurationError'
    
    def test_error_context_preservation(self):
        """Test that error context is preserved through exception chain."""
        original_error = DatabaseError(
            "Connection failed",
            context={"host": "localhost", "port": 27017}
        )
        
        collection_error = DataCollectionError(
            "Failed to store property",
            context={"property_id": "123"},
            cause=original_error
        )
        
        assert collection_error.cause == original_error
        assert collection_error.context["property_id"] == "123"
    
    async def test_retry_mechanism(self):
        """Test retry mechanism with recoverable errors."""
        attempt_count = 0
        
        async def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise DataCollectionError("Temporary failure", recoverable=True)
            return "success"
        
        result = await retry_with_backoff(failing_operation, max_retries=3)
        assert result == "success"
        assert attempt_count == 3
```

## Validation Criteria
- [ ] All custom exceptions inherit from BasePhoenixException
- [ ] Exception hierarchy covers all error scenarios across all epics
- [ ] Error context is properly preserved through exception chains
- [ ] Retry mechanisms work correctly for recoverable errors
- [ ] Circuit breaker prevents cascading failures
- [ ] Error logging provides sufficient debugging information
- [ ] Error monitoring and alerting functions correctly
- [ ] Graceful degradation handles partial failures appropriately
- [ ] Performance impact of error handling is minimal (<1% overhead)

## References
- Epic 1: Foundation Infrastructure logging and configuration integration
- Epic 2: Data Collection Engine error scenarios and recovery
- Epic 3: Automation & Orchestration workflow error handling
- Epic 4: Quality Assurance error monitoring and alerting
- Python exception handling best practices
- System reliability and error recovery patterns

---
**Author**: Integration Architect  
**Date**: 2025-01-20  
**Review**: Architecture Review Board, Development Team  
**Next Review**: After Epic 1 foundation implementation completion