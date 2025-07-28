"""
Error handling and recovery strategies for the processing pipeline.

This module provides robust error handling with circuit breakers, dead letter queues,
and fallback extraction methods for resilient data processing.
"""
import asyncio
import json
import re
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Tuple

from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class ErrorType(Enum):
    """Classification of error types for recovery strategies."""
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    DATA_ERROR = "data_error"
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Recovery actions for different error types."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    WAIT_AND_RETRY = "wait_and_retry"
    REFRESH_AND_RETRY = "refresh_and_retry"
    USE_FALLBACK = "use_fallback"
    SKIP = "skip"
    LOG_AND_SKIP = "log_and_skip"


class CircuitState(Enum):
    """States for the circuit breaker pattern."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


class ProcessingError(Exception):
    """Custom exception for processing errors with additional context."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 error_type: Optional[ErrorType] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.context = context or {}


class ErrorClassifier:
    """Classifies errors and determines recovery actions."""
    
    def __init__(self):
        """Initialize the error classifier with pattern mappings."""
        self.error_patterns = {
            ErrorType.NETWORK: [
                r"connection.*refused",
                r"connection.*error",
                r"timeout",
                r"getaddrinfo.*failed",
                r"network.*unreachable",
                r"cannot.*connect"
            ],
            ErrorType.RATE_LIMIT: [
                r"rate.*limit",
                r"too.*many.*requests",
                r"throttl",
                r"quota.*exceeded"
            ],
            ErrorType.AUTHENTICATION: [
                r"unauthorized",
                r"forbidden",
                r"authentication.*failed",
                r"invalid.*credentials",
                r"access.*denied"
            ],
            ErrorType.DATA_ERROR: [
                r"invalid.*json",
                r"parsing.*error",
                r"missing.*field",
                r"type.*error",
                r"value.*error",
                r"key.*error"
            ],
            ErrorType.TEMPORARY: [
                r"service.*unavailable",
                r"bad.*gateway",
                r"gateway.*timeout",
                r"maintenance"
            ],
            ErrorType.PERMANENT: [
                r"not.*found",
                r"gone",
                r"method.*not.*allowed",
                r"not.*implemented"
            ]
        }
        
        self.status_code_mapping = {
            401: ErrorType.AUTHENTICATION,
            403: ErrorType.AUTHENTICATION,
            404: ErrorType.PERMANENT,
            410: ErrorType.PERMANENT,
            429: ErrorType.RATE_LIMIT,
            500: ErrorType.TEMPORARY,
            502: ErrorType.TEMPORARY,
            503: ErrorType.TEMPORARY,
            504: ErrorType.TEMPORARY
        }
        
        self.recovery_actions = {
            ErrorType.NETWORK: RecoveryAction.RETRY_WITH_BACKOFF,
            ErrorType.RATE_LIMIT: RecoveryAction.WAIT_AND_RETRY,
            ErrorType.AUTHENTICATION: RecoveryAction.REFRESH_AND_RETRY,
            ErrorType.DATA_ERROR: RecoveryAction.USE_FALLBACK,
            ErrorType.TEMPORARY: RecoveryAction.RETRY_WITH_BACKOFF,
            ErrorType.PERMANENT: RecoveryAction.SKIP,
            ErrorType.UNKNOWN: RecoveryAction.LOG_AND_SKIP
        }
    
    def classify(self, error: Exception) -> ErrorType:
        """
        Classify an error into one of the defined error types.
        
        Args:
            error: The exception to classify
            
        Returns:
            ErrorType: The classified error type
        """
        # Check if it's a ProcessingError with status code
        if isinstance(error, ProcessingError) and error.status_code:
            if error.status_code in self.status_code_mapping:
                return self.status_code_mapping[error.status_code]
        
        # Check error type
        error_name = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # Check specific error types
        if isinstance(error, (ConnectionError, asyncio.TimeoutError)):
            return ErrorType.NETWORK
        elif isinstance(error, (ValueError, KeyError, TypeError)):
            return ErrorType.DATA_ERROR
        
        # Check error message patterns
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return error_type
                if re.search(pattern, error_name, re.IGNORECASE):
                    return error_type
        
        return ErrorType.UNKNOWN
    
    def get_recovery_action(self, error_type: ErrorType) -> RecoveryAction:
        """
        Get the recommended recovery action for an error type.
        
        Args:
            error_type: The classified error type
            
        Returns:
            RecoveryAction: The recommended recovery action
        """
        return self.recovery_actions.get(error_type, RecoveryAction.LOG_AND_SKIP)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    
    The circuit breaker prevents cascading failures by blocking calls to a failing service
    after a threshold of failures is reached.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._success_count = 0
    
    @property
    def state(self) -> CircuitState:
        """Get the current circuit state."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and \
               datetime.now() - self._last_failure_time > timedelta(seconds=self.recovery_timeout):
                self._state = CircuitState.HALF_OPEN
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Get the current failure count."""
        return self._failure_count
    
    @property
    def last_failure_time(self) -> Optional[datetime]:
        """Get the last failure timestamp."""
        return self._last_failure_time
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        # Update state check first
        current_state = self.state
        return current_state != CircuitState.OPEN
    
    def record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            logger.info("Circuit breaker closed after successful recovery")
        
        self._success_count += 1
    
    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        # Check if we're in half-open state first
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened after failure in half-open state")
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
    
    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function with circuit breaker protection.
        
        Args:
            func: The async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The function result
            
        Raises:
            ProcessingError: If circuit is open
            Exception: If function fails
        """
        if not self.can_execute():
            raise ProcessingError(
                "Circuit breaker is open",
                error_type=ErrorType.TEMPORARY
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception:
            self.record_failure()
            raise


class DeadLetterQueue:
    """
    Dead letter queue for storing items that failed processing.
    
    Provides functionality to store, retrieve, and retry failed items.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the dead letter queue.
        
        Args:
            max_size: Maximum number of items to store
        """
        self.max_size = max_size
        self._queue: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
    
    async def add_failed_item(self, item: Dict[str, Any], error: Exception, 
                            attempt_count: int):
        """
        Add a failed item to the queue.
        
        Args:
            item: The item that failed processing
            error: The error that occurred
            attempt_count: Number of processing attempts
        """
        async with self._lock:
            failed_item = {
                "item": item,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "attempt_count": attempt_count,
                "timestamp": datetime.now().isoformat()
            }
            self._queue.append(failed_item)
            
            logger.warning(
                f"Added item to dead letter queue: {item.get('parcel_number', 'unknown')}, "
                f"error: {error}, attempts: {attempt_count}"
            )
    
    async def get_failed_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get failed items from the queue.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of failed items
        """
        async with self._lock:
            items = list(self._queue)
            if limit:
                items = items[:limit]
            return items
    
    async def get_items_by_error_type(self, error_type: str) -> List[Dict[str, Any]]:
        """
        Get failed items filtered by error type.
        
        Args:
            error_type: The error type to filter by
            
        Returns:
            List of failed items with the specified error type
        """
        async with self._lock:
            return [
                item for item in self._queue
                if item["error_type"] == error_type
            ]
    
    async def retry_item(self, index: int, retry_func: Callable) -> Any:
        """
        Retry a specific item from the queue.
        
        Args:
            index: Index of the item to retry
            retry_func: Async function to retry the item with
            
        Returns:
            Result of the retry function
            
        Raises:
            Exception: If retry fails
        """
        async with self._lock:
            if index >= len(self._queue):
                raise IndexError(f"Invalid index: {index}")
            
            failed_item = self._queue[index]
            original_item = failed_item["item"]
        
        try:
            # Retry outside the lock to avoid blocking
            result = await retry_func(original_item)
            
            # Remove from queue on success
            async with self._lock:
                del self._queue[index]
            
            logger.info("Successfully retried item from dead letter queue")
            return result
            
        except Exception as e:
            # Update the failed item with new error
            async with self._lock:
                self._queue[index]["error_type"] = type(e).__name__
                self._queue[index]["error_message"] = str(e)
                self._queue[index]["attempt_count"] += 1
                self._queue[index]["timestamp"] = datetime.now().isoformat()
            raise
    
    def size(self) -> int:
        """Get the current size of the queue."""
        return len(self._queue)
    
    async def clear(self):
        """Clear all items from the queue."""
        async with self._lock:
            self._queue.clear()
    
    async def export_to_file(self, filepath: str):
        """
        Export failed items to a JSON file.
        
        Args:
            filepath: Path to the output file
        """
        async with self._lock:
            items = list(self._queue)
        
        with open(filepath, 'w') as f:
            json.dump(items, f, indent=2, default=str)
        
        logger.info(f"Exported {len(items)} failed items to {filepath}")


class FallbackExtractor:
    """Fallback extraction methods for when structured parsing fails."""
    
    def __init__(self):
        """Initialize the fallback extractor with regex patterns."""
        self.address_pattern = re.compile(
            r'(\d+\s+[A-Za-z\s]+?(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl|Circle|Cir|Way))\s*,?\s*'
            r'([A-Za-z\s]+?)\s*,?\s*(AZ|Arizona)\s*,?\s*(\d{5})?',
            re.IGNORECASE
        )
        
        self.price_pattern = re.compile(
            r'\$\s*([0-9,]+(?:\.[0-9]+)?)\s*([KMkm]?)|([0-9]+(?:\.[0-9]+)?)\s*([KMkm])',
            re.IGNORECASE
        )
        
        self.bed_bath_patterns = [
            re.compile(r'(\d+)\s*(?:bed|br|bedroom)', re.IGNORECASE),
            re.compile(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', re.IGNORECASE),
            re.compile(r'(\d+)BR/(\d+(?:\.\d+)?)BA', re.IGNORECASE),
            re.compile(r'studio', re.IGNORECASE)
        ]
        
        self.sqft_pattern = re.compile(
            r'([0-9,]+)\s*(?:sq\.?\s*ft\.?|sqft|square\s*feet)',
            re.IGNORECASE
        )
        
        self.year_pattern = re.compile(
            r'(?:built|constructed|year).*?(19\d{2}|20\d{2})',
            re.IGNORECASE
        )
        
        self.parcel_pattern = re.compile(
            r'(?:APN|Parcel\s*(?:Number|#)?)[:\s#]+([0-9]+[\-A-Za-z0-9]*)',
            re.IGNORECASE
        )
    
    def extract_address_from_text(self, text: str) -> Dict[str, Optional[str]]:
        """Extract address components from unstructured text."""
        match = self.address_pattern.search(text)
        if match:
            return {
                "street": match.group(1).strip() if match.group(1) else None,
                "city": match.group(2).strip() if match.group(2) else None,
                "state": match.group(3).strip() if match.group(3) else None,
                "zip_code": match.group(4) if match.group(4) else None
            }
        return {"street": None, "city": None, "state": None, "zip_code": None}
    
    def extract_price_from_text(self, text: str) -> Optional[float]:
        """Extract price from text."""
        match = self.price_pattern.search(text)
        if match:
            # Try first pattern (with $)
            if match.group(1):
                price_str = match.group(1)
                price = float(price_str.replace(',', ''))
                suffix = match.group(2)
                if suffix and suffix.upper() == 'K':
                    price *= 1000
                elif suffix and suffix.upper() == 'M':
                    price *= 1000000
                return price
            # Try second pattern (without $)
            elif match.group(3):
                price_str = match.group(3)
                price = float(price_str)
                suffix = match.group(4)
                if suffix and suffix.upper() == 'K':
                    price *= 1000
                elif suffix and suffix.upper() == 'M':
                    price *= 1000000
                return price
        return None
    
    def extract_bedrooms_bathrooms(self, text: str) -> Tuple[Optional[int], Optional[float]]:
        """Extract bedroom and bathroom counts from text."""
        beds = None
        baths = None
        
        # Check for studio
        if self.bed_bath_patterns[3].search(text):
            beds = 0
        
        # Check combined pattern (e.g., 3BR/2BA)
        combined_match = self.bed_bath_patterns[2].search(text)
        if combined_match:
            beds = int(combined_match.group(1))
            baths = float(combined_match.group(2))
        else:
            # Check individual patterns
            bed_match = self.bed_bath_patterns[0].search(text)
            if bed_match:
                beds = int(bed_match.group(1))
            
            bath_match = self.bed_bath_patterns[1].search(text)
            if bath_match:
                baths = float(bath_match.group(1))
        
        return beds, baths
    
    def extract_square_footage(self, text: str) -> Optional[int]:
        """Extract square footage from text."""
        match = self.sqft_pattern.search(text)
        if match:
            return int(match.group(1).replace(',', ''))
        return None
    
    def extract_year_built(self, text: str) -> Optional[int]:
        """Extract year built from text."""
        match = self.year_pattern.search(text)
        if match:
            return int(match.group(1))
        return None
    
    def extract_parcel_number(self, text: str) -> Optional[str]:
        """Extract parcel number from text."""
        match = self.parcel_pattern.search(text)
        if match:
            return match.group(1)
        return None
    
    async def extract_from_raw_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract property information from raw data using fallback methods.
        
        Args:
            raw_data: Raw data that failed normal parsing
            
        Returns:
            Extracted property information
        """
        # Combine all text fields
        text_fields = []
        for key, value in raw_data.items():
            if isinstance(value, str):
                text_fields.append(value)
        
        combined_text = " ".join(text_fields)
        
        # Extract using fallback methods
        address = self.extract_address_from_text(combined_text)
        price = self.extract_price_from_text(combined_text)
        beds, baths = self.extract_bedrooms_bathrooms(combined_text)
        sqft = self.extract_square_footage(combined_text)
        year_built = self.extract_year_built(combined_text)
        parcel = self.extract_parcel_number(combined_text)
        
        return {
            "address": address,
            "price": price,
            "bedrooms": beds,
            "bathrooms": baths,
            "square_feet": sqft,
            "year_built": year_built,
            "parcel_number": parcel,
            "extraction_method": "fallback",
            "raw_data": raw_data
        }


class ErrorRecoveryStrategy:
    """
    Main error recovery strategy coordinating all error handling components.
    """
    
    def __init__(self):
        """Initialize the error recovery strategy."""
        self.error_classifier = ErrorClassifier()
        self.dead_letter_queue = DeadLetterQueue()
        self.fallback_extractor = FallbackExtractor()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Retry configuration
        self.retry_delays = {
            ErrorType.NETWORK: [1, 2, 4, 8],  # Exponential backoff
            ErrorType.RATE_LIMIT: [60, 120, 300],  # Longer waits
            ErrorType.TEMPORARY: [2, 5, 10],
            ErrorType.AUTHENTICATION: [1, 5],  # Quick retry then longer
        }
    
    def register_circuit_breaker(self, service_name: str, circuit_breaker: CircuitBreaker):
        """Register a circuit breaker for a service."""
        self.circuit_breakers[service_name] = circuit_breaker
    
    async def handle_error(self, func: Callable, context: Dict[str, Any],
                          max_retries: int = 3, use_fallback: bool = True,
                          add_to_dlq: bool = True) -> Optional[Any]:
        """
        Handle errors with appropriate recovery strategies.
        
        Args:
            func: The async function to execute
            context: Context information for error handling
            max_retries: Maximum number of retry attempts
            use_fallback: Whether to use fallback extraction on data errors
            add_to_dlq: Whether to add failed items to dead letter queue
            
        Returns:
            Result of the function or fallback, or None if failed
        """
        last_error = None
        attempt = 0
        
        while attempt <= max_retries:
            try:
                return await func()
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                # Classify the error
                error_type = self.error_classifier.classify(e)
                recovery_action = self.error_classifier.get_recovery_action(error_type)
                
                logger.warning(
                    f"Error occurred (attempt {attempt}/{max_retries + 1}): "
                    f"{type(e).__name__}: {str(e)}, "
                    f"classified as: {error_type.value}, "
                    f"recovery action: {recovery_action.value}"
                )
                
                # Handle based on recovery action
                if recovery_action == RecoveryAction.SKIP:
                    logger.info("Skipping due to permanent error")
                    break
                
                elif recovery_action == RecoveryAction.USE_FALLBACK and use_fallback:
                    if "raw_data" in context:
                        logger.info("Attempting fallback extraction")
                        try:
                            return await self.fallback_extractor.extract_from_raw_data(
                                context["raw_data"]
                            )
                        except Exception as fallback_error:
                            logger.error(f"Fallback extraction failed: {fallback_error}")
                
                elif recovery_action in [RecoveryAction.RETRY_WITH_BACKOFF, 
                                       RecoveryAction.WAIT_AND_RETRY]:
                    if attempt <= max_retries:
                        # Get delay based on error type
                        delays = self.retry_delays.get(error_type, [1, 2, 4])
                        delay_index = min(attempt - 1, len(delays) - 1)
                        delay = delays[delay_index]
                        
                        logger.info(f"Waiting {delay} seconds before retry")
                        await asyncio.sleep(delay)
                        continue
                
                elif recovery_action == RecoveryAction.REFRESH_AND_RETRY:
                    # TODO: Implement credential refresh logic
                    logger.warning("Authentication refresh not yet implemented")
                    break
                
                # If we've exhausted retries or can't recover, break
                if attempt > max_retries:
                    break
        
        # Add to dead letter queue if enabled
        if add_to_dlq and last_error and "item" in context:
            await self.dead_letter_queue.add_failed_item(
                context["item"],
                last_error,
                attempt
            )
        
        # Raise the last error
        if last_error:
            raise last_error
        
        return None
    
    async def handle_error_with_circuit_breaker(self, service_name: str,
                                              func: Callable, context: Dict[str, Any],
                                              **kwargs) -> Any:
        """
        Handle errors with circuit breaker protection.
        
        Args:
            service_name: Name of the service (for circuit breaker lookup)
            func: The async function to execute
            context: Context information
            **kwargs: Additional arguments for handle_error
            
        Returns:
            Result of the function
        """
        circuit_breaker = self.circuit_breakers.get(service_name)
        
        if circuit_breaker:
            # Wrap the function with circuit breaker
            async def wrapped_func():
                return await circuit_breaker.execute_async(func)
            
            return await self.handle_error(wrapped_func, context, **kwargs)
        else:
            # No circuit breaker registered, use normal error handling
            return await self.handle_error(func, context, **kwargs)