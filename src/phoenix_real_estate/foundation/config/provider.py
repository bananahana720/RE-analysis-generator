"""Configuration provider implementation.

This module provides a concrete implementation of the ConfigProvider protocol
that wraps around EnvironmentConfigProvider to ensure compatibility with the
existing system while providing the simplified interface defined in interfaces.py.
"""

from typing import Any, Dict, Optional
from pathlib import Path

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider


class ConfigProviderImpl:
    """Concrete implementation of ConfigProvider protocol.

    This implementation wraps EnvironmentConfigProvider to provide a simplified
    interface that matches the ConfigProvider protocol defined in interfaces.py.
    It maintains compatibility with the existing system while providing the
    expected interface.
    """

    def __init__(self, config_sources: Optional[list[str]] = None):
        """Initialize the configuration provider.

        Args:
            config_sources: List of configuration sources (files, env vars, etc.)
                          Currently used to determine config directory if provided.
        """
        self.config_sources = config_sources or []
        
        # Extract config directory from sources if provided
        config_dir = None
        if self.config_sources:
            # Look for directory paths in config sources
            for source in self.config_sources:
                if isinstance(source, str):
                    source_path = Path(source)
                    if source_path.is_dir():
                        config_dir = source_path
                        break
                    elif source_path.parent.exists():
                        config_dir = source_path.parent
                        break
        
        # Initialize the underlying EnvironmentConfigProvider
        self._provider = EnvironmentConfigProvider(config_dir=config_dir)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a configuration value.

        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found

        Returns:
            The configuration value or default
        """
        return self._provider.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Retrieve a configuration value as integer.

        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found

        Returns:
            The configuration value as integer
        """
        return self._provider.get_typed(key, int, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Retrieve a configuration value as boolean.

        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found

        Returns:
            The configuration value as boolean
        """
        return self._provider.get_typed(key, bool, default)

    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieve a configuration value as dictionary.

        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found

        Returns:
            The configuration value as dictionary
        """
        if default is None:
            default = {}
        return self._provider.get_typed(key, dict, default)


# Verify the implementation conforms to the protocol
if __name__ == "__main__":
    from phoenix_real_estate.foundation.interfaces import ConfigProvider as ConfigProviderProtocol

    # This should now work without NotImplementedError
    provider: ConfigProviderProtocol = ConfigProviderImpl()
    print("ConfigProviderImpl conforms to ConfigProvider protocol")
    
    # Test basic functionality
    test_value = provider.get("test_key", "default_value")
    print(f"Test get: {test_value}")
