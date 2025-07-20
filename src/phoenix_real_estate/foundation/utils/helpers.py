"""Utility functions for the Phoenix Real Estate Data Collection System.

This module provides helper functions for common operations throughout the
system, including type conversions, data validation, and string normalization.
"""

from typing import Optional, TypeVar, Any, Callable



# Type variable for generic functions
T = TypeVar("T")


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Safely convert a value to an integer.
    
    Attempts to convert various input types to integer, returning a default
    value if conversion fails. Handles strings, floats, and other numeric types.
    
    Args:
        value: The value to convert to integer.
        default: The value to return if conversion fails. Defaults to None.
        
    Returns:
        The converted integer value or the default if conversion fails.
        
    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("123.45")
        123
        >>> safe_int("not a number")
        None
        >>> safe_int("not a number", default=0)
        0
        >>> safe_int(123.99)
        123
        >>> safe_int(None, default=42)
        42
    """
    if value is None:
        return default
        
    try:
        # Handle string values
        if isinstance(value, str):
            # Remove common formatting characters
            cleaned = value.strip().replace(",", "")
            # Handle decimal strings by converting to float first
            if "." in cleaned:
                return int(float(cleaned))
            return int(cleaned)
        # Handle numeric types
        return int(value)
    except (ValueError, TypeError, OverflowError):
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely convert a value to a float.
    
    Attempts to convert various input types to float, returning a default
    value if conversion fails. Handles strings with formatting characters.
    
    Args:
        value: The value to convert to float.
        default: The value to return if conversion fails. Defaults to None.
        
    Returns:
        The converted float value or the default if conversion fails.
        
    Examples:
        >>> safe_float("123.45")
        123.45
        >>> safe_float("1,234.56")
        1234.56
        >>> safe_float("not a number")
        None
        >>> safe_float("not a number", default=0.0)
        0.0
        >>> safe_float(123)
        123.0
        >>> safe_float(None, default=99.9)
        99.9
    """
    if value is None:
        return default
        
    try:
        # Handle string values
        if isinstance(value, str):
            # Remove common formatting characters
            cleaned = value.strip().replace(",", "").replace("$", "")
            return float(cleaned)
        # Handle numeric types
        return float(value)
    except (ValueError, TypeError, OverflowError):
        return default


def normalize_address(address: str) -> str:
    """Normalize address string for consistent comparison.
    
    Standardizes address formatting by removing extra whitespace, standardizing
    common abbreviations, and applying consistent capitalization.
    
    Args:
        address: Raw address string to normalize.
        
    Returns:
        Normalized address string with consistent formatting.
        
    Examples:
        >>> normalize_address("123  Main   St.")
        "123 Main St"
        >>> normalize_address("456 elm STREET")
        "456 Elm Street"
        >>> normalize_address("   789 OAK  AVE   ")
        "789 Oak Ave"
    """
    if not address:
        return ""
    
    import re
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', address.strip())
    
    # Standardize common abbreviations
    replacements = {
        r'\bSt\.?': 'St',
        r'\bAve\.?': 'Ave', 
        r'\bRd\.?': 'Rd',
        r'\bDr\.?': 'Dr',
        r'\bBlvd\.?': 'Blvd',
        r'\bCt\.?': 'Ct',
        r'\bLn\.?': 'Ln',
        r'\bPl\.?': 'Pl',
        r'\bPkwy\.?': 'Pkwy',
        r'\bSTREET\b': 'Street',
        r'\bAVENUE\b': 'Avenue',
        r'\bROAD\b': 'Road',
        r'\bDRIVE\b': 'Drive',
        r'\bBOULEVARD\b': 'Boulevard',
        r'\bCOURT\b': 'Court',
        r'\bLANE\b': 'Lane',
        r'\bPLACE\b': 'Place',
        r'\bPARKWAY\b': 'Parkway',
    }
    
    for pattern, replacement in replacements.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    # Apply title case
    return normalized.title()


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    **kwargs: Any
) -> T:
    """Retry async function with exponential backoff.
    
    Executes an async function with automatic retry logic using exponential
    backoff. Useful for handling transient network errors or temporary failures.
    
    Args:
        func: Async function to retry.
        *args: Positional arguments for the function.
        max_retries: Maximum number of retry attempts (default: 3).
        delay: Initial delay between retries in seconds (default: 1.0).
        backoff_factor: Multiplier for delay after each retry (default: 2.0).
        **kwargs: Keyword arguments for the function.
        
    Returns:
        Result of successful function call.
        
    Raises:
        The last exception encountered if all retries fail.
        
    Examples:
        >>> async def fetch_data(url: str) -> dict:
        ...     # Function that might fail due to network issues
        ...     return {"data": "example"}
        >>> result = await retry_async(fetch_data, "http://example.com", max_retries=3)
        
        >>> async def unreliable_task(value: int) -> int:
        ...     # Function that fails sometimes
        ...     return value * 2
        >>> result = await retry_async(
        ...     unreliable_task, 
        ...     5, 
        ...     max_retries=5, 
        ...     delay=0.5, 
        ...     backoff_factor=1.5
        ... )
    """
    import asyncio
    
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries:
                break
                
            await asyncio.sleep(current_delay)
            current_delay *= backoff_factor
    
    # Re-raise the last exception
    if last_exception is not None:
        raise last_exception
    
    # This should never be reached, but satisfies type checker
    raise RuntimeError("Unexpected error in retry_async")


def is_valid_zipcode(zipcode: str) -> bool:
    """Validate ZIP code format.
    
    Checks if a string is a valid US ZIP code in either 5-digit format
    (e.g., "85031") or ZIP+4 format (e.g., "85031-1234").
    
    Args:
        zipcode: ZIP code string to validate.
        
    Returns:
        True if valid ZIP code format, False otherwise.
        
    Examples:
        >>> is_valid_zipcode("85031")
        True
        >>> is_valid_zipcode("85031-1234")
        True
        >>> is_valid_zipcode("850312")
        False
        >>> is_valid_zipcode("85031-12")
        False
        >>> is_valid_zipcode("invalid")
        False
        >>> is_valid_zipcode("")
        False
        >>> is_valid_zipcode("  85031  ")
        True
    """
    if not zipcode:
        return False
    
    import re
    
    # Support both 5-digit and ZIP+4 formats
    pattern = r'^\d{5}(-\d{4})?$'
    return bool(re.match(pattern, zipcode.strip()))


def generate_property_id(address: str, zipcode: str, source: str) -> str:
    """Generate unique property identifier.
    
    Creates a standardized property ID by combining source, normalized address,
    and ZIP code. The ID is lowercase with underscores replacing spaces and
    special characters removed.
    
    Args:
        address: Property address.
        zipcode: Property ZIP code.
        source: Data source name (e.g., "maricopa", "phoenix_mls").
        
    Returns:
        Unique property identifier string.
        
    Examples:
        >>> generate_property_id("123 Main St", "85031", "maricopa")
        'maricopa_123_main_st_85031'
        >>> generate_property_id("456 Elm Street, Unit 2", "85032-1234", "phoenix_mls")
        'phoenix_mls_456_elm_street_unit_2_85032-1234'
        >>> generate_property_id("789 Oak Ave.", "85033", "county")
        'county_789_oak_ave_85033'
    """
    import re
    
    # Normalize address for ID generation
    normalized_addr = normalize_address(address)
    
    # Create safe identifier by removing non-alphanumeric characters
    safe_addr = re.sub(r'[^\w\s]', '', normalized_addr.lower())
    safe_addr = re.sub(r'\s+', '_', safe_addr.strip())
    
    # Ensure source is also safe
    safe_source = re.sub(r'[^\w]', '_', source.lower())
    
    return f"{safe_source}_{safe_addr}_{zipcode}"
