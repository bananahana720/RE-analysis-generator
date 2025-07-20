"""MongoDB connection management for Phoenix Real Estate Data Collection System.

This module provides robust MongoDB connection management with automatic recovery,
connection pooling optimized for Atlas free tier, and comprehensive error handling.
"""

import asyncio
import threading
from typing import Optional, Any, Dict
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from phoenix_real_estate.foundation.utils.helpers import retry_async
from phoenix_real_estate.foundation.utils.exceptions import DatabaseError, ConfigurationError
from phoenix_real_estate.foundation.logging.factory import get_logger


# Module logger
logger = get_logger(__name__)


class DatabaseConnection:
    """MongoDB connection manager with automatic recovery and connection pooling.

    This class implements a thread-safe singleton pattern for managing MongoDB
    connections. It provides connection pooling optimized for Atlas free tier,
    automatic retry logic, health checks, and index management.

    Attributes:
        uri: MongoDB connection URI
        database_name: Name of the database to connect to
        max_pool_size: Maximum number of connections in the pool (default: 10)
        min_pool_size: Minimum number of connections in the pool (default: 1)
        max_idle_time_ms: Maximum idle time for connections in milliseconds
        server_selection_timeout_ms: Server selection timeout in milliseconds

    Examples:
        >>> # Get singleton instance
        >>> db_conn = DatabaseConnection.get_instance("mongodb://localhost:27017", "phoenix_re")
        >>>
        >>> # Use as async context manager
        >>> async with db_conn.get_database() as db:
        ...     collection = db["properties"]
        ...     await collection.find_one({"property_id": "123"})
    """

    _instance: Optional["DatabaseConnection"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        uri: str,
        database_name: str,
        max_pool_size: int = 10,
        min_pool_size: int = 1,
        max_idle_time_ms: int = 30000,
        server_selection_timeout_ms: int = 30000,
    ) -> None:
        """Initialize the database connection manager.

        Note: Use get_instance() instead of directly instantiating this class.

        Args:
            uri: MongoDB connection URI
            database_name: Name of the database
            max_pool_size: Maximum connections in pool (Atlas free tier limit: 10)
            min_pool_size: Minimum connections in pool
            max_idle_time_ms: Maximum idle time for connections
            server_selection_timeout_ms: Server selection timeout

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not uri:
            raise ConfigurationError("MongoDB URI cannot be empty")
        if not database_name:
            raise ConfigurationError("Database name cannot be empty")
        if max_pool_size > 10:
            logger.warning(
                "Max pool size %d exceeds Atlas free tier limit of 10, setting to 10", max_pool_size
            )
            max_pool_size = 10

        self.uri = uri
        self.database_name = database_name
        self.max_pool_size = max_pool_size
        self.min_pool_size = min_pool_size
        self.max_idle_time_ms = max_idle_time_ms
        self.server_selection_timeout_ms = server_selection_timeout_ms

        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected = False
        self._indexes_created = False

        logger.info(
            "DatabaseConnection initialized for %s with pool size %d-%d",
            database_name,
            min_pool_size,
            max_pool_size,
        )

    @classmethod
    def get_instance(cls, uri: str, database_name: str, **kwargs: Any) -> "DatabaseConnection":
        """Get or create the singleton database connection instance.

        This method ensures thread-safe singleton initialization.

        Args:
            uri: MongoDB connection URI
            database_name: Name of the database
            **kwargs: Additional arguments passed to __init__

        Returns:
            The singleton DatabaseConnection instance

        Examples:
            >>> db = DatabaseConnection.get_instance(
            ...     "mongodb://localhost:27017",
            ...     "phoenix_re"
            ... )
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(uri, database_name, **kwargs)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        with cls._lock:
            if cls._instance is not None:
                asyncio.create_task(cls._instance.close())
            cls._instance = None

    async def connect(self) -> None:
        """Establish connection to MongoDB with retry logic.

        This method creates the Motor client and verifies the connection
        using exponential backoff retry logic.

        Raises:
            DatabaseError: If connection cannot be established after retries
        """
        if self._is_connected:
            logger.debug("Already connected to MongoDB")
            return

        logger.info("Connecting to MongoDB at %s", self._mask_uri(self.uri))

        try:
            # Create Motor client with optimized settings for Atlas free tier
            self._client = AsyncIOMotorClient(
                self.uri,
                maxPoolSize=self.max_pool_size,
                minPoolSize=self.min_pool_size,
                maxIdleTimeMS=self.max_idle_time_ms,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
                retryWrites=True,
                retryReads=True,
            )

            # Get database reference
            self._database = self._client[self.database_name]

            # Verify connection with retry logic
            await retry_async(self._ping, max_retries=3, delay=1.0, backoff_factor=2.0)

            self._is_connected = True
            logger.info("Successfully connected to MongoDB database '%s'", self.database_name)

            # Create indexes if not already created
            if not self._indexes_created:
                await self._create_indexes()

        except Exception as e:
            error_msg = f"Failed to connect to MongoDB: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                context={"uri": self._mask_uri(self.uri), "database": self.database_name},
                original_error=e,
            ) from e

    async def _ping(self) -> bool:
        """Ping the database to verify connection.

        Returns:
            True if ping successful

        Raises:
            DatabaseError: If ping fails
        """
        if not self._client:
            raise DatabaseError("No MongoDB client available")

        try:
            result = await self._client.admin.command("ping")
            return result.get("ok", 0) == 1
        except Exception as e:
            raise DatabaseError(
                "MongoDB ping failed", context={"error": str(e)}, original_error=e
            ) from e

    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check on the database connection.

        Returns:
            Dictionary containing health check results including:
            - connected: Whether connection is established
            - ping_time_ms: Ping response time in milliseconds
            - database_stats: Database statistics if available
            - connection_pool: Connection pool statistics

        Examples:
            >>> health = await db_conn.health_check()
            >>> print(f"Connected: {health['connected']}")
            >>> print(f"Ping time: {health['ping_time_ms']}ms")
        """
        health_status = {
            "connected": False,
            "ping_time_ms": None,
            "database_stats": None,
            "connection_pool": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not self._is_connected or not self._client:
            return health_status

        try:
            # Measure ping time
            start_time = asyncio.get_event_loop().time()
            ping_result = await self._ping()
            ping_time = (asyncio.get_event_loop().time() - start_time) * 1000

            health_status["connected"] = ping_result
            health_status["ping_time_ms"] = round(ping_time, 2)

            # Get database stats
            if self._database:
                stats = await self._database.command("dbStats")
                health_status["database_stats"] = {
                    "collections": stats.get("collections", 0),
                    "data_size": stats.get("dataSize", 0),
                    "storage_size": stats.get("storageSize", 0),
                    "indexes": stats.get("indexes", 0),
                }

            # Get connection pool stats (if available)
            # Note: Motor doesn't expose pool stats directly, this is a placeholder
            health_status["connection_pool"] = {
                "max_size": self.max_pool_size,
                "min_size": self.min_pool_size,
            }

        except Exception as e:
            logger.error("Health check failed: %s", str(e))
            health_status["error"] = str(e)

        return health_status

    @asynccontextmanager
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance as an async context manager.

        This method ensures the connection is established before returning
        the database instance.

        Yields:
            AsyncIOMotorDatabase instance

        Raises:
            DatabaseError: If connection cannot be established

        Examples:
            >>> async with db_conn.get_database() as db:
            ...     collection = db["properties"]
            ...     result = await collection.find_one()
        """
        if not self._is_connected:
            await self.connect()

        if not self._database:
            raise DatabaseError("Database not available after connection")

        try:
            yield self._database
        except Exception as e:
            logger.error("Database operation failed: %s", str(e))
            raise DatabaseError(
                "Database operation failed", context={"error": str(e)}, original_error=e
            ) from e

    async def _create_indexes(self) -> None:
        """Create required indexes for optimal query performance.

        This method creates all necessary indexes for the properties and
        daily_reports collections to ensure optimal query performance.
        """
        if not self._database:
            raise DatabaseError("Database not available for index creation")

        logger.info("Creating database indexes")

        try:
            # Properties collection indexes
            properties_collection = self._database["properties"]

            # Single field indexes
            await properties_collection.create_index("property_id", unique=True)
            await properties_collection.create_index("address.zipcode")
            await properties_collection.create_index("address.street")
            await properties_collection.create_index("listing.status")
            await properties_collection.create_index("listing.mls_id")
            await properties_collection.create_index("current_price")
            await properties_collection.create_index("last_updated")
            await properties_collection.create_index("is_active")
            await properties_collection.create_index("sources.source")

            # Compound indexes for common query patterns
            await properties_collection.create_index(
                [("address.zipcode", 1), ("listing.status", 1)]
            )
            await properties_collection.create_index(
                [("address.zipcode", 1), ("current_price", -1)]
            )
            await properties_collection.create_index([("is_active", 1), ("last_updated", -1)])

            # Daily reports collection indexes
            daily_reports_collection = self._database["daily_reports"]
            await daily_reports_collection.create_index("date", unique=True)

            self._indexes_created = True
            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error("Failed to create indexes: %s", str(e))
            raise DatabaseError(
                "Index creation failed", context={"error": str(e)}, original_error=e
            ) from e

    async def close(self) -> None:
        """Close the database connection and clean up resources.

        This method gracefully shuts down the connection pool and
        releases all resources.
        """
        if self._client:
            logger.info("Closing MongoDB connection")
            self._client.close()
            self._client = None
            self._database = None
            self._is_connected = False
            self._indexes_created = False
            logger.info("MongoDB connection closed")

    def _mask_uri(self, uri: str) -> str:
        """Mask sensitive information in MongoDB URI for logging.

        Args:
            uri: MongoDB connection URI

        Returns:
            URI with password masked
        """
        import re

        # Mask password in URI
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)

    def __repr__(self) -> str:
        """String representation of the DatabaseConnection instance."""
        return (
            f"DatabaseConnection("
            f"database='{self.database_name}', "
            f"connected={self._is_connected}, "
            f"pool_size={self.min_pool_size}-{self.max_pool_size}"
            f")"
        )


# Factory functions for module-level access

_connection_instance: Optional[DatabaseConnection] = None


async def get_database_connection(
    uri: str, database_name: str, **kwargs: Any
) -> DatabaseConnection:
    """Get or create a database connection instance.

    This factory function provides a convenient way to get a database connection
    without directly managing the singleton pattern. It ensures that only one
    connection instance exists for the application lifecycle.

    Args:
        uri: MongoDB connection URI
        database_name: Name of the database
        **kwargs: Additional arguments passed to DatabaseConnection

    Returns:
        Connected DatabaseConnection instance

    Raises:
        DatabaseError: If connection cannot be established

    Examples:
        >>> # Get connection instance
        >>> conn = await get_database_connection(
        ...     "mongodb://localhost:27017",
        ...     "phoenix_re"
        ... )
        >>>
        >>> # Use connection
        >>> async with conn.get_database() as db:
        ...     collection = db["properties"]
        ...     doc = await collection.find_one()
    """
    global _connection_instance

    if _connection_instance is None:
        _connection_instance = DatabaseConnection.get_instance(uri, database_name, **kwargs)
        await _connection_instance.connect()

    return _connection_instance


async def close_database_connection() -> None:
    """Close the current database connection and clean up resources.

    This function ensures proper cleanup of the database connection and
    resets the module-level instance. It should be called during application
    shutdown to ensure graceful termination.

    Examples:
        >>> # During application shutdown
        >>> await close_database_connection()
    """
    global _connection_instance

    if _connection_instance is not None:
        await _connection_instance.close()
        DatabaseConnection.reset_instance()
        _connection_instance = None
        logger.info("Database connection closed and instance reset")
