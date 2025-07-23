"""Tests for repository pattern implementation.

This module contains comprehensive tests for all repository classes including
CRUD operations, queries, aggregations, and error handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from motor.motor_asyncio import AsyncIOMotorCollection

from phoenix_real_estate.foundation.database.repositories import (
    BaseRepository,
    PropertyRepository,
    DailyReportRepository,
    RepositoryFactory,
)
from phoenix_real_estate.foundation.database.connection import DatabaseConnection
from phoenix_real_estate.foundation.utils.exceptions import DatabaseError, ValidationError


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection."""
    connection = Mock(spec=DatabaseConnection)

    # Create async context manager for get_database
    async def get_database_context():
        db = AsyncMock()
        db.__getitem__ = Mock(return_value=AsyncMock())
        return db

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(side_effect=get_database_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    connection.get_database.return_value = mock_context
    return connection


@pytest.fixture
def mock_collection():
    """Create a mock MongoDB collection."""
    collection = Mock(spec=AsyncIOMotorCollection)
    # Set up default async methods
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.replace_one = AsyncMock()
    collection.count_documents = AsyncMock()
    collection.find = Mock()
    collection.aggregate = Mock()
    return collection


@pytest.fixture
def sample_property_data():
    """Create sample property data for testing."""
    return {
        "property_id": "test-property-123",
        "address": {"street": "123 Test St", "city": "Phoenix", "zipcode": "85001"},
        "current_price": 350000,
        "features": {"beds": 3, "baths": 2, "sqft": 1500},
    }


@pytest.fixture
def sample_report_data():
    """Create sample daily report data for testing."""
    return {
        "date": "2025-01-20",
        "properties_collected": 150,
        "properties_processed": 145,
        "errors": 5,
        "duration_seconds": 3600,
        "statistics": {"avg_price": 425000, "total_properties": 1500},
    }


class TestBaseRepository:
    """Test BaseRepository abstract class."""

    class ConcreteRepository(BaseRepository):
        """Concrete implementation for testing."""

        pass

    async def test_init(self, mock_db_connection):
        """Test repository initialization."""
        repo = self.ConcreteRepository("test_collection", mock_db_connection)
        assert repo.collection_name == "test_collection"
        assert repo._db_connection == mock_db_connection
        assert repo._logger is not None

    async def test_get_collection_success(self, mock_db_connection, mock_collection):
        """Test successful collection retrieval."""
        # Setup the mock to return the collection
        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_db
        mock_context.__aexit__.return_value = None

        mock_db_connection.get_database.return_value = mock_context

        repo = self.ConcreteRepository("test_collection", mock_db_connection)

        async with repo._get_collection() as collection:
            assert collection == mock_collection

    async def test_get_collection_error(self, mock_db_connection):
        """Test collection retrieval error handling."""
        mock_db_connection.get_database.side_effect = Exception("Connection failed")

        repo = self.ConcreteRepository("test_collection", mock_db_connection)

        with pytest.raises(DatabaseError) as exc_info:
            async with repo._get_collection():
                pass

        assert "Failed to access collection" in str(exc_info.value)
        assert exc_info.value.context["collection"] == "test_collection"


class TestPropertyRepository:
    """Test PropertyRepository class."""

    @pytest.fixture
    async def property_repo(self, mock_db_connection):
        """Create a PropertyRepository instance."""
        return PropertyRepository(mock_db_connection)

    @pytest.fixture
    def setup_mock_collection(self, mock_db_connection, mock_collection):
        """Set up mock collection for property repository."""
        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_db
        mock_context.__aexit__.return_value = None

        mock_db_connection.get_database.return_value = mock_context
        return mock_collection

    async def test_create_success(self, property_repo, setup_mock_collection, sample_property_data):
        """Test successful property creation."""
        mock_collection = setup_mock_collection
        mock_collection.insert_one.return_value = Mock(inserted_id="test_id")

        property_id = await property_repo.create(sample_property_data)

        assert property_id == "test-property-123"
        mock_collection.insert_one.assert_called_once()

        # Check that timestamps were added
        call_args = mock_collection.insert_one.call_args[0][0]
        assert "created_at" in call_args
        assert "last_updated" in call_args
        assert call_args["is_active"] is True

    async def test_create_missing_property_id(self, property_repo):
        """Test create with missing property_id."""
        with pytest.raises(ValidationError) as exc_info:
            await property_repo.create({"address": {"street": "123 Test St"}})

        assert "Missing required field: property_id" in str(exc_info.value)

    async def test_update_success(self, property_repo, setup_mock_collection):
        """Test successful property update."""
        mock_collection = setup_mock_collection
        mock_collection.update_one.return_value = Mock(modified_count=1)

        updates = {"current_price": 400000, "features.beds": 4}
        result = await property_repo.update("test-property-123", updates)

        assert result is True
        mock_collection.update_one.assert_called_once()

        # Check that last_updated was added
        call_args = mock_collection.update_one.call_args[0]
        assert "last_updated" in call_args[1]["$set"]

    async def test_search_by_zipcode(self, property_repo, setup_mock_collection):
        """Test search by zipcode with pagination."""
        mock_collection = setup_mock_collection
        mock_collection.count_documents.return_value = 25

        # Mock cursor
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor

        # Mock async iteration
        async def mock_aiter(self):
            for doc in [{"property_id": f"prop-{i}", "_id": f"id-{i}"} for i in range(10)]:
                yield doc

        mock_cursor.__aiter__ = mock_aiter
        mock_collection.find.return_value = mock_cursor

        properties, total = await property_repo.search_by_zipcode("85001", skip=10, limit=10)

        assert len(properties) == 10
        assert total == 25
        assert all("_id" not in prop for prop in properties)


class TestDailyReportRepository:
    """Test DailyReportRepository class."""

    @pytest.fixture
    async def report_repo(self, mock_db_connection):
        """Create a DailyReportRepository instance."""
        return DailyReportRepository(mock_db_connection)

    @pytest.fixture
    def setup_mock_collection(self, mock_db_connection, mock_collection):
        """Set up mock collection for report repository."""
        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_db
        mock_context.__aexit__.return_value = None

        mock_db_connection.get_database.return_value = mock_context
        return mock_collection

    async def test_create_report_new(self, report_repo, setup_mock_collection, sample_report_data):
        """Test creating a new daily report."""
        mock_collection = setup_mock_collection
        mock_collection.replace_one.return_value = Mock(upserted_id="new_id")

        report_date = await report_repo.create_report(sample_report_data)

        assert report_date == "2025-01-20"
        mock_collection.replace_one.assert_called_once()


class TestRepositoryFactory:
    """Test RepositoryFactory class."""

    def test_get_property_repository_with_connection(self, mock_db_connection):
        """Test getting property repository with provided connection."""
        # Reset factory first
        RepositoryFactory.reset()

        repo = RepositoryFactory.get_property_repository(mock_db_connection)

        assert isinstance(repo, PropertyRepository)
        assert repo._db_connection == mock_db_connection

    def test_reset_factory(self, mock_db_connection):
        """Test resetting the factory."""
        # Create a repository
        repo1 = RepositoryFactory.get_property_repository(mock_db_connection)

        # Reset
        RepositoryFactory.reset()

        # Should create new instance
        repo2 = RepositoryFactory.get_property_repository(mock_db_connection)
        assert repo1 is not repo2
