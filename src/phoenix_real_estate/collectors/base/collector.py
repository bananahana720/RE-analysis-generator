"""Abstract base class for data collectors.

This module defines the DataCollector abstract base class that implements
the strategy pattern for different data collection sources. All concrete
collectors must inherit from this class and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from phoenix_real_estate.foundation import Logger, get_logger
from phoenix_real_estate.foundation.utils.exceptions import DataCollectionError


class DataCollector(ABC):
    """Abstract base class for data collectors using strategy pattern.

    This class defines the interface that all data collectors must implement.
    It provides common functionality like logging and error handling while
    leaving the specific data collection logic to concrete implementations.

    Key Features:
    - Strategy pattern implementation
    - Integrated logging with Epic 1 foundation
    - Exception hierarchy integration
    - Epic 3 orchestration readiness

    Attributes:
        logger: Logger instance from Epic 1 foundation
        config: Configuration provider from Epic 1
        last_collection_time: Timestamp of last successful collection
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the data collector.

        Args:
            config: Optional configuration dictionary for the collector
        """
        self.logger: Logger = get_logger(f"collectors.{self.__class__.__name__}")
        self.config = config or {}
        self.last_collection_time: Optional[datetime] = None

    @abstractmethod
    def collect(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Collect raw data from the source.

        This method must be implemented by concrete collectors to define
        how data is retrieved from their specific source.

        Args:
            **kwargs: Source-specific parameters for data collection

        Returns:
            List of raw data dictionaries from the source

        Raises:
            DataCollectionError: If collection fails for any reason
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the collector configuration.

        This method should verify that all required configuration
        parameters are present and valid for the specific collector.

        Returns:
            True if configuration is valid, False otherwise

        Raises:
            ConfigurationError: If configuration is invalid or missing
        """
        pass

    def get_collection_status(self) -> Dict[str, Any]:
        """Get current collection status and metadata.

        Returns:
            Dictionary containing collection status information
        """
        return {
            "collector_name": self.__class__.__name__,
            "last_collection_time": self.last_collection_time.isoformat()
            if self.last_collection_time
            else None,
            "config_valid": self.validate_config(),
            "status": "ready" if self.validate_config() else "configuration_error",
        }

    def _log_collection_start(self, **kwargs: Any) -> None:
        """Log the start of a collection operation.

        Args:
            **kwargs: Collection parameters to include in log
        """
        self.logger.info(
            f"Starting data collection with {self.__class__.__name__}",
            extra={"collection_params": kwargs},
        )

    def _log_collection_success(self, record_count: int, duration_ms: int) -> None:
        """Log successful completion of collection operation.

        Args:
            record_count: Number of records collected
            duration_ms: Collection duration in milliseconds
        """
        self.last_collection_time = datetime.now()
        self.logger.info(
            f"Collection completed successfully: {record_count} records in {duration_ms}ms"
        )

    def _log_collection_error(self, error: Exception, **context: Any) -> None:
        """Log collection operation failure.

        Args:
            error: The exception that occurred
            **context: Additional context information
        """
        self.logger.error(
            f"Collection failed: {str(error)}",
            extra={"error_type": type(error).__name__, "context": context},
            exc_info=True,
        )

    def _handle_collection_error(self, error: Exception, operation: str, **context: Any) -> None:
        """Handle and wrap collection errors consistently.

        Args:
            error: Original exception that occurred
            operation: Description of the operation that failed
            **context: Additional context for error tracking

        Raises:
            DataCollectionError: Wrapped exception with context
        """
        self._log_collection_error(error, operation=operation, **context)
        raise DataCollectionError(
            f"Collection operation '{operation}' failed: {str(error)}",
            context={"collector": self.__class__.__name__, "operation": operation, **context},
            original_error=error,
        ) from error
