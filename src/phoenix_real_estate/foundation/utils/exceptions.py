"""Exception hierarchy for the Phoenix Real Estate Data Collection System.

This module defines a comprehensive exception hierarchy for handling various
error conditions throughout the system. All exceptions preserve context and
original cause information for better debugging.
"""

from typing import Optional, Any


class PhoenixREError(Exception):
    """Base exception class for all Phoenix Real Estate system errors.
    
    This is the root exception class from which all other custom exceptions
    in the Phoenix Real Estate system inherit. It provides a common interface
    for error handling and context preservation.
    
    Attributes:
        message: The error message describing what went wrong.
        context: Optional dictionary containing additional error context.
        original_error: The original exception that caused this error, if any.
    
    Examples:
        >>> raise PhoenixREError("Something went wrong")
        PhoenixREError: Something went wrong
        
        >>> try:
        ...     int("not a number")
        ... except ValueError as e:
        ...     raise PhoenixREError("Failed to parse number", original_error=e) from e
    """
    
    def __init__(
        self, 
        message: str, 
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        """Initialize the Phoenix Real Estate base exception.
        
        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_error = original_error
        
    def __str__(self) -> str:
        """Return a string representation of the exception."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


class ConfigurationError(PhoenixREError):
    """Raised when there are configuration-related errors.
    
    This exception is used for errors related to application configuration,
    including missing configuration files, invalid settings, or environment
    variable issues.
    
    Examples:
        >>> raise ConfigurationError("Missing API key", context={"key": "PHOENIX_API_KEY"})
        ConfigurationError: Missing API key (context: key=PHOENIX_API_KEY)
        
        >>> raise ConfigurationError(
        ...     "Invalid proxy configuration",
        ...     context={"proxy_url": "invalid-url", "expected_format": "http://host:port"}
        ... )
    """
    pass


class DatabaseError(PhoenixREError):
    """Raised when database operations fail.
    
    This exception covers all database-related errors including connection
    failures, query errors, schema mismatches, and data integrity issues.
    
    Examples:
        >>> raise DatabaseError("Failed to connect to MongoDB", context={"host": "localhost", "port": 27017})
        DatabaseError: Failed to connect to MongoDB (context: host=localhost, port=27017)
        
        >>> raise DatabaseError(
        ...     "Duplicate property ID",
        ...     context={"property_id": "123-main-st-85001", "collection": "properties"}
        ... )
    """
    pass


class ValidationError(PhoenixREError):
    """Raised when data validation fails.
    
    This exception is used when input data doesn't meet the expected format,
    type, or business rules. It's commonly used for validating property data,
    addresses, and API responses.
    
    Examples:
        >>> raise ValidationError("Invalid zipcode format", context={"zipcode": "8500", "expected": "5 digits"})
        ValidationError: Invalid zipcode format (context: zipcode=8500, expected=5 digits)
        
        >>> raise ValidationError(
        ...     "Property missing required fields",
        ...     context={"missing_fields": ["address", "price"], "property_id": "123"}
        ... )
    """
    pass


class DataCollectionError(PhoenixREError):
    """Raised when data collection operations fail.
    
    This exception covers errors during web scraping, API calls, or any
    data retrieval operations. It includes network errors, parsing failures,
    and rate limiting issues.
    
    Examples:
        >>> raise DataCollectionError("Failed to scrape MLS data", context={"url": "https://example.com", "status_code": 404})
        DataCollectionError: Failed to scrape MLS data (context: url=https://example.com, status_code=404)
        
        >>> raise DataCollectionError(
        ...     "Rate limit exceeded",
        ...     context={"source": "PhoenixMLS", "retry_after": 3600, "requests_made": 1000}
        ... )
    """
    pass


class ProcessingError(PhoenixREError):
    """Raised when data processing operations fail.
    
    This exception is used for errors during data transformation, cleaning,
    enrichment, or any processing pipeline operations. It includes LLM
    processing failures and data normalization errors.
    
    Examples:
        >>> raise ProcessingError("Failed to parse property features", context={"raw_data": "3BR/2BA", "parser": "feature_extractor"})
        ProcessingError: Failed to parse property features (context: raw_data=3BR/2BA, parser=feature_extractor)
        
        >>> raise ProcessingError(
        ...     "LLM processing timeout",
        ...     context={"property_id": "123", "timeout_seconds": 30, "model": "local-llm"}
        ... )
    """
    pass


class OrchestrationError(PhoenixREError):
    """Raised when orchestration or workflow operations fail.
    
    This exception covers errors in the orchestration layer, including
    workflow failures, task scheduling issues, and coordination problems
    between different system components.
    
    Examples:
        >>> raise OrchestrationError("Workflow execution failed", context={"workflow": "daily_collection", "step": "validation"})
        OrchestrationError: Workflow execution failed (context: workflow=daily_collection, step=validation)
        
        >>> raise OrchestrationError(
        ...     "Task dependency not met",
        ...     context={"task": "process_data", "missing_dependency": "collect_data", "run_id": "2025-01-20"}
        ... )
    """
    pass
