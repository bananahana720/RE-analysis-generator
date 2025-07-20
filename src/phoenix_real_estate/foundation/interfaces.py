"""Foundation layer protocol definitions.

This module defines the protocols (interfaces) that must be implemented
by concrete classes in the foundation layer. Using Protocol from typing
ensures type safety while maintaining flexibility.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable
from datetime import datetime


@runtime_checkable
class ConfigProvider(Protocol):
    """Protocol for configuration providers.
    
    Implementations should provide methods to retrieve configuration
    values from various sources (environment, files, etc.).
    """
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a configuration value.
        
        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found
            
        Returns:
            The configuration value or default
        """
        ...
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Retrieve a configuration value as integer.
        
        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found
            
        Returns:
            The configuration value as integer
        """
        ...
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Retrieve a configuration value as boolean.
        
        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found
            
        Returns:
            The configuration value as boolean
        """
        ...
    
    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieve a configuration value as dictionary.
        
        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found
            
        Returns:
            The configuration value as dictionary
        """
        ...


@runtime_checkable
class PropertyRepository(Protocol):
    """Protocol for property data repositories.
    
    Implementations should provide methods for CRUD operations
    on property records in the database.
    """
    
    def find_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Find a property by its unique identifier.
        
        Args:
            property_id: The unique property identifier
            
        Returns:
            Property data dict or None if not found
        """
        ...
    
    def find_by_address(self, street: str, city: str, zip_code: str) -> Optional[Dict[str, Any]]:
        """Find a property by address components.
        
        Args:
            street: Street address
            city: City name
            zip_code: ZIP code
            
        Returns:
            Property data dict or None if not found
        """
        ...
    
    def save(self, property_data: Dict[str, Any]) -> str:
        """Save or update a property record.
        
        Args:
            property_data: Property data to save
            
        Returns:
            The property_id of the saved record
        """
        ...
    
    def find_updated_since(self, since: datetime) -> list[Dict[str, Any]]:
        """Find properties updated since a given timestamp.
        
        Args:
            since: Timestamp to search from
            
        Returns:
            List of property records updated after the timestamp
        """
        ...
    
    def delete(self, property_id: str) -> bool:
        """Delete a property record.
        
        Args:
            property_id: The unique property identifier
            
        Returns:
            True if deleted, False if not found
        """
        ...


@runtime_checkable
class Logger(Protocol):
    """Protocol for logger instances.
    
    This protocol matches the standard Python logging.Logger interface
    to ensure compatibility with existing logging infrastructure.
    """
    
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        ...
    
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        ...
    
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        ...
    
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        ...
    
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        ...
    
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        ...
