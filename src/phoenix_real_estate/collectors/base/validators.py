"""Shared validation utilities for collectors.

This module provides common validation logic, patterns, and error handling
utilities to eliminate code duplication across collectors.
"""

from typing import Any, Dict, Optional, List
import re

from phoenix_real_estate.foundation.utils.exceptions import ValidationError, ConfigurationError
from phoenix_real_estate.foundation.utils.helpers import is_valid_zipcode


class ValidationPatterns:
    """Common validation patterns and constants."""
    
    # Property ID pattern - alphanumeric with hyphens and underscores
    PROPERTY_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
    
    # URL patterns
    HTTPS_URL_PATTERN = re.compile(r'^https://')
    HTTP_URL_PATTERN = re.compile(r'^http://')
    
    # Field name patterns for sensitive data
    SENSITIVE_FIELD_PATTERN = re.compile(r'(api_key|token|auth|password|secret)', re.IGNORECASE)


class CommonValidators:
    """Shared validation functions for collectors."""
    
    @staticmethod
    def validate_property_id(property_id: str) -> None:
        """Validate property ID format.
        
        Args:
            property_id: Property identifier to validate
            
        Raises:
            ValidationError: If property ID is invalid
        """
        if not property_id or not property_id.strip():
            raise ValidationError("Property ID cannot be empty")
        
        if not ValidationPatterns.PROPERTY_ID_PATTERN.match(property_id.strip()):
            raise ValidationError(
                f"Invalid property ID format: {property_id}",
                context={"property_id": property_id}
            )
    
    @staticmethod
    def validate_zipcode(zipcode: str) -> None:
        """Validate ZIP code format.
        
        Args:
            zipcode: ZIP code to validate
            
        Raises:
            ValidationError: If ZIP code is invalid
        """
        if not zipcode or not zipcode.strip():
            raise ValidationError("ZIP code cannot be empty")
        
        if not is_valid_zipcode(zipcode):
            raise ValidationError(f"Invalid ZIP code format: {zipcode}")
    
    @staticmethod
    def validate_days_back(days_back: int) -> None:
        """Validate days_back parameter for recent sales queries.
        
        Args:
            days_back: Number of days to look back
            
        Raises:
            ValidationError: If days_back is invalid
        """
        if days_back <= 0:
            raise ValidationError("days_back must be positive")
        if days_back > 365:
            raise ValidationError("days_back cannot exceed 365")
    
    @staticmethod
    def validate_base_url(base_url: str, require_https: bool = True) -> str:
        """Validate and normalize base URL.
        
        Args:
            base_url: URL to validate
            require_https: Whether to require HTTPS
            
        Returns:
            Normalized URL without trailing slash
            
        Raises:
            ConfigurationError: If URL is invalid
        """
        if not base_url:
            raise ConfigurationError("Base URL cannot be empty")
        
        if require_https and not ValidationPatterns.HTTPS_URL_PATTERN.match(base_url):
            if ValidationPatterns.HTTP_URL_PATTERN.match(base_url):
                raise ConfigurationError(
                    "HTTPS-only communication required, HTTP URLs not allowed"
                )
            else:
                raise ConfigurationError(f"Invalid base URL format: {base_url}")
        
        # Remove trailing slash
        return base_url.rstrip("/")
    
    @staticmethod
    def validate_required_config(config_value: Any, config_name: str) -> None:
        """Validate required configuration value.
        
        Args:
            config_value: Configuration value to check
            config_name: Name of the configuration for error messages
            
        Raises:
            ConfigurationError: If configuration is missing
        """
        if not config_value:
            raise ConfigurationError(f"Missing required config: {config_name}")
    
    @staticmethod
    def validate_raw_data_structure(raw_data: Any, required_type: type = dict) -> None:
        """Validate basic raw data structure.
        
        Args:
            raw_data: Raw data to validate
            required_type: Expected type of the data
            
        Raises:
            ValidationError: If data structure is invalid
        """
        if not isinstance(raw_data, required_type):
            raise ValidationError(f"Raw data must be a {required_type.__name__}")
        
        if not raw_data:
            raise ValidationError("Raw data cannot be empty")
    
    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any], 
        required_fields: List[str],
        context_name: str = "data"
    ) -> List[str]:
        """Validate that required fields are present in data.
        
        Args:
            data: Dictionary to check
            required_fields: List of required field names
            context_name: Name for error context
            
        Returns:
            List of missing fields (empty if all present)
            
        Raises:
            ValidationError: If any required fields are missing
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None or (
                isinstance(data[field], str) and not data[field].strip()
            ):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields in {context_name}: {', '.join(missing_fields)}",
                context={
                    "missing_fields": missing_fields,
                    "available_fields": list(data.keys())
                }
            )
        
        return missing_fields


class ErrorHandlingUtils:
    """Utilities for consistent error handling and wrapping."""
    
    @staticmethod
    def sanitize_context(context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context dictionary to prevent credential exposure.
        
        Args:
            context: Context dictionary to sanitize
            
        Returns:
            Sanitized context with sensitive values redacted
        """
        sanitized = {}
        
        for key, value in context.items():
            # Check if key contains sensitive terms
            if ValidationPatterns.SENSITIVE_FIELD_PATTERN.search(key):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and ValidationPatterns.SENSITIVE_FIELD_PATTERN.search(key):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def sanitize_url_for_logging(url: str) -> str:
        """Sanitize URL for logging to prevent credential exposure.
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL with credentials redacted
        """
        if ValidationPatterns.SENSITIVE_FIELD_PATTERN.search(url.lower()):
            # Replace query parameters that might contain credentials
            import re
            return re.sub(
                r"([?&](?:api_key|token|auth|password|secret)=)[^&]*", 
                r"\1[REDACTED]", 
                url,
                flags=re.IGNORECASE
            )
        return url
    
    @staticmethod
    def wrap_error(
        error: Exception,
        operation: str,
        error_class: type,
        context: Optional[Dict[str, Any]] = None,
        sanitize: bool = True
    ) -> Exception:
        """Wrap an exception with consistent error handling.
        
        Args:
            error: Original exception
            operation: Operation that failed
            error_class: Exception class to use for wrapping
            context: Additional context
            sanitize: Whether to sanitize the context
            
        Returns:
            Wrapped exception of the specified type
        """
        # Sanitize context if needed
        safe_context = {}
        if context:
            safe_context = ErrorHandlingUtils.sanitize_context(context) if sanitize else context
        
        safe_context["operation"] = operation
        
        # Re-raise if already the target type
        if isinstance(error, error_class):
            return error
        
        # Create wrapped exception
        return error_class(
            f"{operation} failed: {str(error)}",
            context=safe_context,
            original_error=error
        )