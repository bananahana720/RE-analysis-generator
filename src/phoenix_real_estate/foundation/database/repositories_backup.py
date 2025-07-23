"""Repository pattern implementation for Phoenix Real Estate Data Collection System.

This module provides repository classes for database operations with clean abstractions,
proper error handling, and support for MongoDB operations including aggregations.
"""

import asyncio
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pymongo.errors import DuplicateKeyError, OperationFailure

from phoenix_real_estate.foundation.database.connection import DatabaseConnection
from phoenix_real_estate.foundation.utils.exceptions import (
    DatabaseError,
    ValidationError,
    ConfigurationError,
)
from phoenix_real_estate.foundation.logging.factory import get_logger


# Type variable for generic repository
T = TypeVar("T", bound=Dict[str, Any])

# Module logger
logger = get_logger(__name__)


class BaseRepository(ABC):
    """Abstract base repository providing common database operations.

    This class provides a foundation for all repositories with common functionality
    like connection management, error handling, and logging.

    Attributes:
        collection_name: Name of the MongoDB collection
        _db_connection: Database connection instance
        _logger: Logger instance for this repository
    """

    def __init__(self, collection_name: str, db_connection: DatabaseConnection) -> None:
        """Initialize the base repository.

        Args:
            collection_name: Name of the MongoDB collection
            db_connection: Database connection instance
        """
        self.collection_name = collection_name
        self._db_connection = db_connection
        self._logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @asynccontextmanager
    async def _get_collection(self):
        """Get collection instance as an async context manager.

        Yields:
            AsyncIOMotorCollection instance

        Raises:
            DatabaseError: If database operations fail
        """
        try:
            async with self._db_connection.get_database() as db:
                yield db[self.collection_name]
        except Exception as e:
            self._logger.error("Failed to get collection '%s': %s", self.collection_name, str(e))
            raise DatabaseError(
                f"Failed to access collection '{self.collection_name}'",
                context={"collection": self.collection_name, "error": str(e)},
                original_error=e,
            ) from e

    async def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute a database operation with retry logic.

        Args:
            operation: The async operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            DatabaseError: If operation fails after retries
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await operation(*args, **kwargs)
            except OperationFailure as e:
                if attempt == max_retries - 1:
                    raise DatabaseError(
                        "Database operation failed after retries",
                        context={"operation": operation.__name__, "attempts": max_retries},
                        original_error=e,
                    ) from e
                await asyncio.sleep(2**attempt)  # Exponential backoff

    def _log_operation(self, operation: str, context: Dict[str, Any]) -> None:
        """Log a database operation with context.

        Args:
            operation: Name of the operation
            context: Operation context for logging
        """
        self._logger.debug(
            "Repository operation: %s on %s",
            operation,
            self.collection_name,
            extra={"context": context},
        )


class PropertyRepository(BaseRepository):
    """Repository for property-related database operations.

    This repository handles all CRUD operations for property documents,
    including complex queries, aggregations, and price history management.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        """Initialize the property repository.

        Args:
            db_connection: Database connection instance
        """
        super().__init__("properties", db_connection)

    async def create(self, property_data: Dict[str, Any]) -> str:
        """Create a new property record with duplicate checking.

        Args:
            property_data: Property data to insert

        Returns:
            The property_id of the created record

        Raises:
            ValidationError: If property_data is invalid
            DatabaseError: If creation fails or duplicate exists
        """
        # Validate required fields
        if "property_id" not in property_data:
            raise ValidationError(
                "Missing required field: property_id", context={"data": property_data}
            )

        property_id = property_data["property_id"]
        self._log_operation("create", {"property_id": property_id})

        try:
            async with self._get_collection() as collection:
                # Add timestamps
                now = datetime.now(timezone.utc)
                property_data["created_at"] = now
                property_data["last_updated"] = now
                property_data["is_active"] = property_data.get("is_active", True)

                # Insert with duplicate checking
                await collection.insert_one(property_data)

                self._logger.info("Created property: %s", property_id)
                return property_id

        except DuplicateKeyError:
            raise DatabaseError(
                f"Property with ID '{property_id}' already exists",
                context={"property_id": property_id},
            )
        except Exception as e:
            self._logger.error("Failed to create property %s: %s", property_id, str(e))
            raise DatabaseError(
                "Failed to create property",
                context={"property_id": property_id, "error": str(e)},
                original_error=e,
            ) from e

    async def get_by_property_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get a property by its unique identifier.

        Args:
            property_id: The unique property identifier

        Returns:
            Property document or None if not found

        Raises:
            DatabaseError: If query fails
        """
        self._log_operation("get_by_property_id", {"property_id": property_id})

        try:
            async with self._get_collection() as collection:
                property_doc = await collection.find_one({"property_id": property_id})

                if property_doc:
                    # Remove MongoDB _id from response
                    property_doc.pop("_id", None)

                return property_doc

        except Exception as e:
            self._logger.error("Failed to get property %s: %s", property_id, str(e))
            raise DatabaseError(
                "Failed to retrieve property",
                context={"property_id": property_id, "error": str(e)},
                original_error=e,
            ) from e

    async def update(self, property_id: str, updates: Dict[str, Any]) -> bool:
        """Update a property with partial updates.

        Args:
            property_id: The property to update
            updates: Fields to update (partial update supported)

        Returns:
            True if updated, False if not found

        Raises:
            ValidationError: If updates are invalid
            DatabaseError: If update fails
        """
        if not updates:
            raise ValidationError("No updates provided")

        self._log_operation("update", {"property_id": property_id, "fields": list(updates.keys())})

        try:
            async with self._get_collection() as collection:
                # Add update timestamp
                updates["last_updated"] = datetime.now(timezone.utc)

                # Perform update
                result = await collection.update_one({"property_id": property_id}, {"": updates})

                if result.modified_count > 0:
                    self._logger.info(
                        "Updated property %s with %d fields", property_id, len(updates)
                    )
                    return True
                return False

        except Exception as e:
            self._logger.error("Failed to update property %s: %s", property_id, str(e))
            raise DatabaseError(
                "Failed to update property",
                context={"property_id": property_id, "error": str(e)},
                original_error=e,
            ) from e

    async def upsert(self, property_data: Dict[str, Any]) -> Tuple[str, bool]:
        """Insert or update a property (idempotent operation).

        Args:
            property_data: Property data to upsert

        Returns:
            Tuple of (property_id, was_created) where was_created is True if inserted

        Raises:
            ValidationError: If property_data is invalid
            DatabaseError: If upsert fails
        """
        if "property_id" not in property_data:
            raise ValidationError(
                "Missing required field: property_id", context={"data": property_data}
            )

        property_id = property_data["property_id"]
        self._log_operation("upsert", {"property_id": property_id})

        try:
            async with self._get_collection() as collection:
                # Check if exists
                existing = await collection.find_one({"property_id": property_id}, {"_id": 1})

                now = datetime.now(timezone.utc)
                property_data["last_updated"] = now

                if existing:
                    # Update existing
                    await collection.replace_one({"property_id": property_id}, property_data)
                    self._logger.info("Updated existing property: %s", property_id)
                    return property_id, False
                else:
                    # Create new
                    property_data["created_at"] = now
                    property_data["is_active"] = property_data.get("is_active", True)
                    await collection.insert_one(property_data)
                    self._logger.info("Created new property: %s", property_id)
                    return property_id, True

        except Exception as e:
            self._logger.error("Failed to upsert property %s: %s", property_id, str(e))
            raise DatabaseError(
                "Failed to upsert property",
                context={"property_id": property_id, "error": str(e)},
                original_error=e,
            ) from e

    async def search_by_zipcode(
        self,
        zipcode: str,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "last_updated",
        sort_order: int = -1,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search properties by zipcode with pagination.

        Args:
            zipcode: ZIP code to search
            skip: Number of documents to skip (for pagination)
            limit: Maximum number of documents to return
            sort_by: Field to sort by
            sort_order: Sort order (1 for ascending, -1 for descending)

        Returns:
            Tuple of (properties list, total count)

        Raises:
            DatabaseError: If search fails
        """
        self._log_operation("search_by_zipcode", {"zipcode": zipcode, "skip": skip, "limit": limit})

        try:
            async with self._get_collection() as collection:
                # Build query
                query = {"address.zipcode": zipcode, "is_active": True}

                # Get total count
                total_count = await collection.count_documents(query)

                # Get paginated results
                cursor = collection.find(query).sort(sort_by, sort_order).skip(skip).limit(limit)
                properties = []

                async for doc in cursor:
                    doc.pop("_id", None)
                    properties.append(doc)

                self._logger.info(
                    "Found %d properties in zipcode %s (showing %d-%d)",
                    total_count,
                    zipcode,
                    skip + 1,
                    min(skip + limit, total_count),
                )

                return properties, total_count

        except Exception as e:
            self._logger.error("Failed to search by zipcode %s: %s", zipcode, str(e))
            raise DatabaseError(
                "Failed to search properties by zipcode",
                context={"zipcode": zipcode, "error": str(e)},
                original_error=e,
            ) from e

    async def get_recent_updates(self, since: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """Get properties updated since a given timestamp.

        Args:
            since: Timestamp to search from
            limit: Maximum number of results

        Returns:
            List of recently updated properties

        Raises:
            DatabaseError: If query fails
        """
        self._log_operation("get_recent_updates", {"since": since.isoformat(), "limit": limit})

        try:
            async with self._get_collection() as collection:
                cursor = (
                    collection.find({"last_updated": {"": since}, "is_active": True})
                    .sort("last_updated", -1)
                    .limit(limit)
                )

                properties = []
                async for doc in cursor:
                    doc.pop("_id", None)
                    properties.append(doc)

                self._logger.info(
                    "Found %d properties updated since %s", len(properties), since.isoformat()
                )

                return properties

        except Exception as e:
            self._logger.error("Failed to get recent updates: %s", str(e))
            raise DatabaseError(
                "Failed to get recent updates",
                context={"since": since.isoformat(), "error": str(e)},
                original_error=e,
            ) from e

    async def get_price_statistics(self, zipcode: str) -> Dict[str, Any]:
        """Get price statistics for a zipcode using aggregation pipeline.

        Args:
            zipcode: ZIP code to analyze

        Returns:
            Dictionary with price statistics including min, max, avg, median

        Raises:
            DatabaseError: If aggregation fails
        """
        self._log_operation("get_price_statistics", {"zipcode": zipcode})

        try:
            async with self._get_collection() as collection:
                pipeline = [
                    # Match active properties in zipcode with valid prices
                    {
                        "": {
                            "address.zipcode": zipcode,
                            "is_active": True,
                            "current_price": {"$exists": True, "$gt": 0},
                        }
                    },
                    # Group and calculate statistics
                    {
                        "": {
                            "_id": ".zipcode",
                            "count": {"": 1},
                            "avg_price": {"": ""},
                            "min_price": {"": ""},
                            "max_price": {"": ""},
                            "prices": {"": ""},
                        }
                    },
                    # Calculate percentiles
                    {
                        "": {
                            "_id": 0,
                            "zipcode": "",
                            "count": 1,
                            "avg_price": {"": ["", 2]},
                            "min_price": 1,
                            "max_price": 1,
                            "median_price": {"": ["", {"": {"": [{"": ""}, 2]}}]},
                        }
                    },
                ]

                # Execute aggregation
                cursor = collection.aggregate(pipeline)
                results = await cursor.to_list(length=1)

                if results:
                    stats = results[0]
                    self._logger.info(
                        "Calculated price statistics for zipcode %s: %d properties",
                        zipcode,
                        stats.get("count", 0),
                    )
                    return stats
                else:
                    return {
                        "zipcode": zipcode,
                        "count": 0,
                        "avg_price": None,
                        "min_price": None,
                        "max_price": None,
                        "median_price": None,
                    }

        except Exception as e:
            self._logger.error("Failed to get price statistics for %s: %s", zipcode, str(e))
            raise DatabaseError(
                "Failed to calculate price statistics",
                context={"zipcode": zipcode, "error": str(e)},
                original_error=e,
            ) from e

    async def add_price_history(
        self, property_id: str, price: float, date: datetime, source: str
    ) -> bool:
        """Add a price history entry to a property.

        Args:
            property_id: The property to update
            price: New price value
            date: Date of the price
            source: Source of the price information

        Returns:
            True if added successfully, False if property not found

        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If update fails
        """
        if price <= 0:
            raise ValidationError("Price must be positive", context={"price": price})

        self._log_operation(
            "add_price_history", {"property_id": property_id, "price": price, "source": source}
        )

        try:
            async with self._get_collection() as collection:
                # Build price history entry
                price_entry = {"price": price, "date": date, "source": source}

                # Update property
                result = await collection.update_one(
                    {"property_id": property_id},
                    {
                        "$push": {"price_history": price_entry},
                        "$set": {
                            "current_price": price,
                            "last_updated": datetime.now(timezone.utc),
                        },
                    },
                )

                if result.modified_count > 0:
                    self._logger.info(
                        "Added price history to property %s: $%.2f from %s",
                        property_id,
                        price,
                        source,
                    )
                    return True
                return False

        except Exception as e:
            self._logger.error("Failed to add price history: %s", str(e))
            raise DatabaseError(
                "Failed to add price history",
                context={"property_id": property_id, "price": price, "error": str(e)},
                original_error=e,
            ) from e


class DailyReportRepository(BaseRepository):
    """Repository for daily report operations.

    This repository handles operations for daily collection and processing reports.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        """Initialize the daily report repository.

        Args:
            db_connection: Database connection instance
        """
        super().__init__("daily_reports", db_connection)

    async def create_report(self, report_data: Dict[str, Any]) -> str:
        """Create or update a daily report (upsert by date).

        Args:
            report_data: Report data including date and statistics

        Returns:
            The date string of the report

        Raises:
            ValidationError: If report_data is invalid
            DatabaseError: If creation fails
        """
        if "date" not in report_data:
            raise ValidationError("Missing required field: date", context={"data": report_data})

        report_date = report_data["date"]
        self._log_operation("create_report", {"date": report_date})

        try:
            async with self._get_collection() as collection:
                # Add timestamps
                now = datetime.now(timezone.utc)
                report_data["created_at"] = report_data.get("created_at", now)
                report_data["last_updated"] = now

                # Upsert by date
                result = await collection.replace_one(
                    {"date": report_date}, report_data, upsert=True
                )

                if result.upserted_id:
                    self._logger.info("Created new daily report for %s", report_date)
                else:
                    self._logger.info("Updated existing daily report for %s", report_date)

                return report_date

        except Exception as e:
            self._logger.error("Failed to create report for %s: %s", report_date, str(e))
            raise DatabaseError(
                "Failed to create daily report",
                context={"date": report_date, "error": str(e)},
                original_error=e,
            ) from e

    async def get_recent_reports(
        self, days: int = 7, include_stats: bool = True
    ) -> List[Dict[str, Any]]:
        """Get recent daily reports with optional statistics.

        Args:
            days: Number of days to look back
            include_stats: Whether to include full statistics

        Returns:
            List of daily reports

        Raises:
            DatabaseError: If query fails
        """
        self._log_operation("get_recent_reports", {"days": days, "include_stats": include_stats})

        try:
            async with self._get_collection() as collection:
                # Calculate date range
                end_date = datetime.now(timezone.utc)
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                start_date = start_date.replace(day=start_date.day - days)

                # Build projection
                projection = {"_id": 0}
                if not include_stats:
                    projection.update(
                        {
                            "date": 1,
                            "properties_collected": 1,
                            "properties_processed": 1,
                            "errors": 1,
                            "duration_seconds": 1,
                        }
                    )

                # Query reports
                cursor = collection.find({"created_at": {"": start_date}}, projection).sort(
                    "date", -1
                )

                reports = []
                async for doc in cursor:
                    reports.append(doc)

                self._logger.info("Found %d daily reports for the last %d days", len(reports), days)

                return reports

        except Exception as e:
            self._logger.error("Failed to get recent reports: %s", str(e))
            raise DatabaseError(
                "Failed to get recent reports",
                context={"days": days, "error": str(e)},
                original_error=e,
            ) from e


class RepositoryFactory:
    """Factory for creating repository instances with dependency injection.

    This factory ensures proper initialization and dependency management
    for all repository instances.
    """

    _repositories: Dict[Type[BaseRepository], BaseRepository] = {}

    @classmethod
    def get_property_repository(
        cls, db_connection: Optional[DatabaseConnection] = None
    ) -> PropertyRepository:
        """Get or create a PropertyRepository instance.

        Args:
            db_connection: Optional database connection to use

        Returns:
            PropertyRepository instance

        Raises:
            ConfigurationError: If no connection available
        """
        if PropertyRepository not in cls._repositories:
            if not db_connection:
                # Try to get default connection
                from phoenix_real_estate.foundation.config.provider import ConfigProvider

                config = ConfigProvider()
                db_uri = config.get("MONGODB_URI")
                db_name = config.get("MONGODB_DATABASE", "phoenix_real_estate")

                if not db_uri:
                    raise ConfigurationError("No MongoDB URI configured")

                db_connection = DatabaseConnection.get_instance(db_uri, db_name)

            cls._repositories[PropertyRepository] = PropertyRepository(db_connection)

        return cls._repositories[PropertyRepository]

    @classmethod
    def get_daily_report_repository(
        cls, db_connection: Optional[DatabaseConnection] = None
    ) -> DailyReportRepository:
        """Get or create a DailyReportRepository instance.

        Args:
            db_connection: Optional database connection to use

        Returns:
            DailyReportRepository instance

        Raises:
            ConfigurationError: If no connection available
        """
        if DailyReportRepository not in cls._repositories:
            if not db_connection:
                # Try to get default connection
                from phoenix_real_estate.foundation.config.provider import ConfigProvider

                config = ConfigProvider()
                db_uri = config.get("MONGODB_URI")
                db_name = config.get("MONGODB_DATABASE", "phoenix_real_estate")

                if not db_uri:
                    raise ConfigurationError("No MongoDB URI configured")

                db_connection = DatabaseConnection.get_instance(db_uri, db_name)

            cls._repositories[DailyReportRepository] = DailyReportRepository(db_connection)

        return cls._repositories[DailyReportRepository]

    @classmethod
    def reset(cls) -> None:
        """Reset all repository instances (mainly for testing)."""
        cls._repositories.clear()
