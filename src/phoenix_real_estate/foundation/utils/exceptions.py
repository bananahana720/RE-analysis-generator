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
        original_error: Optional[Exception] = None,
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

    Attributes:
        config_key: The configuration key that caused the error.
        expected_type: The expected type/format for the configuration value.

    Examples:
        >>> raise ConfigurationError("Missing API key", config_key="PHOENIX_API_KEY")
        ConfigurationError: Missing API key (context: config_key=PHOENIX_API_KEY)

        >>> raise ConfigurationError(
        ...     "Invalid proxy configuration",
        ...     config_key="proxy_url",
        ...     expected_type="URL format",
        ...     context={"actual_value": "invalid-url", "expected_format": "http://host:port"}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
    ) -> None:
        """Initialize the ConfigurationError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            config_key: The configuration key that caused the error.
            expected_type: The expected type/format for the configuration value.
        """
        context = context or {}
        if config_key is not None:
            context["config_key"] = config_key
        if expected_type is not None:
            context["expected_type"] = expected_type

        super().__init__(message, context, original_error)
        self.config_key = config_key
        self.expected_type = expected_type


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

    Attributes:
        field_name: The name of the field that failed validation.
        expected_value: The expected value or format.
        actual_value: The actual value that failed validation.

    Examples:
        >>> raise ValidationError("Invalid zipcode format", field_name="zipcode", expected_value="5 digits", actual_value="8500")
        ValidationError: Invalid zipcode format (context: field_name=zipcode, expected_value=5 digits, actual_value=8500)

        >>> raise ValidationError(
        ...     "Property missing required fields",
        ...     context={"missing_fields": ["address", "price"], "property_id": "123"}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        field_name: Optional[str] = None,
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
    ) -> None:
        """Initialize the ValidationError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            field_name: The name of the field that failed validation.
            expected_value: The expected value or format.
            actual_value: The actual value that failed validation.
        """
        context = context or {}
        if field_name is not None:
            context["field_name"] = field_name
        if expected_value is not None:
            context["expected_value"] = expected_value
        if actual_value is not None:
            context["actual_value"] = actual_value

        super().__init__(message, context, original_error)
        self.field_name = field_name
        self.expected_value = expected_value
        self.actual_value = actual_value


class DataCollectionError(PhoenixREError):
    """Raised when data collection operations fail.

    This exception covers errors during web scraping, API calls, or any
    data retrieval operations. It includes network errors, parsing failures,
    and rate limiting issues.

    Attributes:
        operation: The specific operation that failed (e.g., 'collect_zipcode', 'get_property_details').
        source: The data source where the error occurred (e.g., 'maricopa_api', 'phoenix_mls').

    Examples:
        >>> raise DataCollectionError("Failed to scrape MLS data", context={"url": "https://example.com", "status_code": 404})
        DataCollectionError: Failed to scrape MLS data (context: url=https://example.com, status_code=404)

        >>> raise DataCollectionError(
        ...     "Rate limit exceeded",
        ...     operation="collect_zipcode",
        ...     source="maricopa_api",
        ...     context={"retry_after": 3600, "requests_made": 1000}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        operation: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Initialize the DataCollectionError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            operation: The specific operation that failed.
            source: The data source where the error occurred.
        """
        context = context or {}
        if operation is not None:
            context["operation"] = operation
        if source is not None:
            context["source"] = source

        super().__init__(message, context, original_error)
        self.operation = operation
        self.source = source


class ProcessingError(PhoenixREError):
    """Raised when data processing operations fail.

    This exception is used for errors during data transformation, cleaning,
    enrichment, or any processing pipeline operations. It includes LLM
    processing failures and data normalization errors.

    Attributes:
        stage: The processing stage where the error occurred (e.g., 'transformation', 'validation').
        data_context: Context about the data being processed when error occurred.

    Examples:
        >>> raise ProcessingError("Failed to parse property features", stage="transformation", context={"raw_data": "3BR/2BA", "parser": "feature_extractor"})
        ProcessingError: Failed to parse property features (context: stage=transformation, raw_data=3BR/2BA, parser=feature_extractor)

        >>> raise ProcessingError(
        ...     "LLM processing timeout",
        ...     stage="llm_processing",
        ...     data_context={"property_id": "123", "timeout_seconds": 30, "model": "local-llm"}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        stage: Optional[str] = None,
        data_context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the ProcessingError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            stage: The processing stage where the error occurred.
            data_context: Context about the data being processed when error occurred.
        """
        context = context or {}
        if stage is not None:
            context["stage"] = stage
        if data_context is not None:
            context.update(data_context)

        super().__init__(message, context, original_error)
        self.stage = stage
        self.data_context = data_context or {}


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


class RateLimitError(DataCollectionError):
    """Raised when rate limiting constraints are violated.

    This exception is a specialized DataCollectionError for rate limiting
    scenarios, including API rate limits, request throttling, and quota
    exceeded situations.

    Attributes:
        retry_after: Seconds to wait before retrying, if known.
        current_rate: Current request rate when limit was hit.
        limit: The rate limit that was exceeded.

    Examples:
        >>> raise RateLimitError("API rate limit exceeded", context={"retry_after": 60, "limit": "1000/hour"})
        RateLimitError: API rate limit exceeded (context: retry_after=60, limit=1000/hour)

        >>> raise RateLimitError(
        ...     "Request throttled",
        ...     context={"current_rate": 15.2, "limit": 10.0, "window": "per_second"}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        retry_after: Optional[int] = None,
        current_rate: Optional[float] = None,
        limit: Optional[str] = None,
    ) -> None:
        """Initialize the RateLimitError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            retry_after: Seconds to wait before retrying.
            current_rate: Current request rate when limit was hit.
            limit: The rate limit that was exceeded.
        """
        context = context or {}
        if retry_after is not None:
            context["retry_after"] = retry_after
        if current_rate is not None:
            context["current_rate"] = current_rate
        if limit is not None:
            context["limit"] = limit

        super().__init__(message, context, original_error)
        self.retry_after = retry_after
        self.current_rate = current_rate
        self.limit = limit


class AuthenticationError(DataCollectionError):
    """Raised when authentication or authorization fails.

    This exception is used for authentication failures, expired tokens,
    invalid API keys, and authorization issues when accessing external
    data sources.

    Attributes:
        auth_type: Type of authentication that failed (e.g., 'bearer_token', 'api_key').
        endpoint: The endpoint or service where auth failed.

    Examples:
        >>> raise AuthenticationError("Invalid API key", context={"auth_type": "api_key", "endpoint": "maricopa_api"})
        AuthenticationError: Invalid API key (context: auth_type=api_key, endpoint=maricopa_api)

        >>> raise AuthenticationError(
        ...     "Token expired",
        ...     context={"auth_type": "bearer_token", "expires_at": "2025-01-20T10:00:00Z"}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        auth_type: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        """Initialize the AuthenticationError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            auth_type: Type of authentication that failed.
            endpoint: The endpoint or service where auth failed.
        """
        context = context or {}
        if auth_type is not None:
            context["auth_type"] = auth_type
        if endpoint is not None:
            context["endpoint"] = endpoint

        super().__init__(message, context, original_error)
        self.auth_type = auth_type
        self.endpoint = endpoint


class CaptchaError(DataCollectionError):
    """Base exception for captcha-related errors.

    This exception is the base class for all captcha-related errors including
    detection failures, solving failures, and service integration issues.

    Attributes:
        captcha_type: Type of captcha encountered (e.g., 'recaptcha_v2', 'image').
        page_url: URL of the page where captcha was encountered.

    Examples:
        >>> raise CaptchaError("Captcha encountered", captcha_type="recaptcha_v2", page_url="https://example.com")
        CaptchaError: Captcha encountered (context: captcha_type=recaptcha_v2, page_url=https://example.com)
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        captcha_type: Optional[str] = None,
        page_url: Optional[str] = None,
    ) -> None:
        """Initialize the CaptchaError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            captcha_type: Type of captcha encountered.
            page_url: URL where captcha was encountered.
        """
        context = context or {}
        if captcha_type is not None:
            context["captcha_type"] = captcha_type
        if page_url is not None:
            context["page_url"] = page_url

        super().__init__(message, context, original_error)
        self.captcha_type = captcha_type
        self.page_url = page_url


class CaptchaDetectionError(CaptchaError):
    """Raised when captcha detection fails or encounters errors.

    This exception is used when the system fails to properly detect or identify
    the type of captcha on a page.

    Examples:
        >>> raise CaptchaDetectionError("Failed to identify captcha type", context={"selectors_tried": 5})
        CaptchaDetectionError: Failed to identify captcha type (context: selectors_tried=5)
    """

    pass


class CaptchaSolvingError(CaptchaError):
    """Raised when captcha solving fails.

    This exception is used when the captcha solving service fails to solve
    a captcha, including timeouts, API errors, or invalid responses.

    Attributes:
        service: The captcha solving service that failed (e.g., '2captcha').
        error_code: Service-specific error code if available.

    Examples:
        >>> raise CaptchaSolvingError("2captcha timeout", service="2captcha", context={"task_id": "123", "timeout": 120})
        CaptchaSolvingError: 2captcha timeout (context: service=2captcha, task_id=123, timeout=120)
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        service: Optional[str] = None,
        error_code: Optional[str] = None,
        captcha_type: Optional[str] = None,
        page_url: Optional[str] = None,
    ) -> None:
        """Initialize the CaptchaSolvingError.

        Args:
            message: The error message.
            context: Optional dictionary with additional context information.
            original_error: The original exception that caused this error.
            service: The captcha solving service that failed.
            error_code: Service-specific error code.
            captcha_type: Type of captcha that failed to solve.
            page_url: URL where captcha was encountered.
        """
        context = context or {}
        if service is not None:
            context["service"] = service
        if error_code is not None:
            context["error_code"] = error_code

        super().__init__(message, context, original_error, captcha_type, page_url)
        self.service = service
        self.error_code = error_code
