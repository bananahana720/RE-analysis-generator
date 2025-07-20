"""Unit tests for MongoDB connection management.

This module contains comprehensive unit tests for the DatabaseConnection class,
including connection lifecycle, retry logic, pool management, health checks,
singleton pattern, and error handling scenarios.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import (
    ConnectionFailure
)

from phoenix_real_estate.foundation.database.connection import DatabaseConnection
from phoenix_real_estate.foundation.utils.exceptions import DatabaseError, ConfigurationError


class TestDatabaseConnection:
    """Test suite for DatabaseConnection class."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton instance before each test."""
        DatabaseConnection._instance = None
        yield
        DatabaseConnection._instance = None
    
    @pytest.fixture
    def mock_motor_client(self):
        """Create a mock Motor client."""
        mock_client = MagicMock(spec=AsyncIOMotorClient)
        mock_db = MagicMock(spec=AsyncIOMotorDatabase)
        mock_client.__getitem__.return_value = mock_db
        
        # Mock admin commands
        mock_admin = MagicMock()
        mock_admin.command = AsyncMock(return_value={"ok": 1})
        mock_client.admin = mock_admin
        
        return mock_client, mock_db
    
    def test_init_valid_config(self):
        """Test initialization with valid configuration."""
        db_conn = DatabaseConnection(
            uri="mongodb://localhost:27017",
            database_name="test_db",
            max_pool_size=5,
            min_pool_size=2
        )
        
        assert db_conn.uri == "mongodb://localhost:27017"
        assert db_conn.database_name == "test_db"
        assert db_conn.max_pool_size == 5
        assert db_conn.min_pool_size == 2
        assert db_conn._is_connected is False
    
    def test_init_empty_uri_raises_error(self):
        """Test initialization with empty URI raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="MongoDB URI cannot be empty"):
            DatabaseConnection("", "test_db")
    
    def test_init_empty_database_name_raises_error(self):
        """Test initialization with empty database name raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Database name cannot be empty"):
            DatabaseConnection("mongodb://localhost:27017", "")
    
    def test_init_max_pool_size_limit(self):
        """Test that max pool size is limited to Atlas free tier limit."""
        with patch('phoenix_real_estate.foundation.database.connection.logger') as mock_logger:
            db_conn = DatabaseConnection(
                uri="mongodb://localhost:27017",
                database_name="test_db",
                max_pool_size=20  # Exceeds limit
            )
            
            assert db_conn.max_pool_size == 10
            mock_logger.warning.assert_called_once()
    
    def test_singleton_pattern(self):
        """Test that get_instance returns the same instance."""
        instance1 = DatabaseConnection.get_instance(
            "mongodb://localhost:27017",
            "test_db"
        )
        instance2 = DatabaseConnection.get_instance(
            "mongodb://localhost:27017",
            "test_db"
        )
        
        assert instance1 is instance2
    
    def test_singleton_thread_safety(self):
        """Test singleton pattern is thread-safe."""
        instances = []
        
        def create_instance():
            instance = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            instances.append(instance)
        
        import threading
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_motor_client):
        """Test successful connection to MongoDB."""
        mock_client, mock_db = mock_motor_client
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            await db_conn.connect()
            
            assert db_conn._is_connected is True
            assert db_conn._client is mock_client
            assert db_conn._database is mock_db
    
    @pytest.mark.asyncio
    async def test_connect_already_connected(self, mock_motor_client):
        """Test calling connect when already connected."""
        mock_client, mock_db = mock_motor_client
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            await db_conn.connect()
            
            # Reset mock to verify it's not called again
            mock_client.admin.command.reset_mock()
            
            # Connect again
            await db_conn.connect()
            
            # Should not ping again
            mock_client.admin.command.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_connect_retry_on_failure(self, mock_motor_client):
        """Test connection retry logic on failure."""
        mock_client, mock_db = mock_motor_client
        
        # First two calls fail, third succeeds
        mock_client.admin.command = AsyncMock(
            side_effect=[
                ConnectionFailure("Connection failed"),
                ConnectionFailure("Connection failed"),
                {"ok": 1}
            ]
        )
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            await db_conn.connect()
            
            assert db_conn._is_connected is True
            assert mock_client.admin.command.call_count == 3
    
    @pytest.mark.asyncio
    async def test_connect_max_retries_exceeded(self, mock_motor_client):
        """Test connection fails after max retries."""
        mock_client, _ = mock_motor_client
        
        # All calls fail
        mock_client.admin.command = AsyncMock(
            side_effect=ConnectionFailure("Connection failed")
        )
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            with pytest.raises(DatabaseError, match="Failed to connect to MongoDB"):
                await db_conn.connect()
            
            assert db_conn._is_connected is False

    @pytest.mark.asyncio
    async def test_health_check_connected(self, mock_motor_client):
        """Test health check when connected."""
        mock_client, mock_db = mock_motor_client
        
        # Mock dbStats command
        mock_db.command = AsyncMock(return_value={
            "collections": 2,
            "dataSize": 1024,
            "storageSize": 2048,
            "indexes": 5
        })
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            await db_conn.connect()
            
            health = await db_conn.health_check()
            
            assert health["connected"] is True
            assert health["ping_time_ms"] is not None
            assert health["database_stats"]["collections"] == 2
            assert health["database_stats"]["data_size"] == 1024
    
    @pytest.mark.asyncio
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        db_conn = DatabaseConnection.get_instance(
            "mongodb://localhost:27017",
            "test_db"
        )
        
        health = await db_conn.health_check()
        
        assert health["connected"] is False
        assert health["ping_time_ms"] is None
        assert health["database_stats"] is None
    
    @pytest.mark.asyncio
    async def test_get_database_context_manager(self, mock_motor_client):
        """Test get_database as async context manager."""
        mock_client, mock_db = mock_motor_client
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            async with db_conn.get_database() as db:
                assert db is mock_db
                assert db_conn._is_connected is True
    
    @pytest.mark.asyncio
    async def test_get_database_auto_connect(self, mock_motor_client):
        """Test get_database automatically connects if not connected."""
        mock_client, mock_db = mock_motor_client
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            assert db_conn._is_connected is False
            
            async with db_conn.get_database() as db:
                assert db is mock_db
                assert db_conn._is_connected is True
    
    @pytest.mark.asyncio
    async def test_create_indexes(self, mock_motor_client):
        """Test index creation for collections."""
        mock_client, mock_db = mock_motor_client
        
        # Mock collections
        mock_properties = MagicMock()
        mock_properties.create_index = AsyncMock()
        mock_daily_reports = MagicMock()
        mock_daily_reports.create_index = AsyncMock()
        
        mock_db.__getitem__.side_effect = lambda name: {
            "properties": mock_properties,
            "daily_reports": mock_daily_reports
        }[name]
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            await db_conn.connect()
            
            # Verify all expected indexes were created
            assert mock_properties.create_index.call_count >= 12  # All single and compound indexes
            assert mock_daily_reports.create_index.call_count == 1
            
            # Verify specific index calls
            mock_properties.create_index.assert_any_call("property_id", unique=True)
            mock_properties.create_index.assert_any_call("address.zipcode")
            mock_daily_reports.create_index.assert_called_once_with("date", unique=True)

    @pytest.mark.asyncio
    async def test_close(self, mock_motor_client):
        """Test closing the database connection."""
        mock_client, mock_db = mock_motor_client
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            db_conn = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            await db_conn.connect()
            assert db_conn._is_connected is True
            
            await db_conn.close()
            
            assert db_conn._is_connected is False
            assert db_conn._client is None
            assert db_conn._database is None
            mock_client.close.assert_called_once()
    
    def test_mask_uri(self):
        """Test URI masking for security."""
        db_conn = DatabaseConnection(
            "mongodb://user:password@localhost:27017",
            "test_db"
        )
        
        masked = db_conn._mask_uri("mongodb://user:password@localhost:27017")
        assert masked == "mongodb://user:****@localhost:27017"
        
        # Test URI without password
        masked = db_conn._mask_uri("mongodb://localhost:27017")
        assert masked == "mongodb://localhost:27017"
    
    def test_repr(self):
        """Test string representation of DatabaseConnection."""
        db_conn = DatabaseConnection(
            "mongodb://localhost:27017",
            "test_db",
            max_pool_size=5,
            min_pool_size=2
        )
        
        repr_str = repr(db_conn)
        assert "DatabaseConnection" in repr_str
        assert "database='test_db'" in repr_str
        assert "connected=False" in repr_str
        assert "pool_size=2-5" in repr_str
    
    @pytest.mark.asyncio
    async def test_reset_instance(self, mock_motor_client):
        """Test resetting singleton instance."""
        mock_client, mock_db = mock_motor_client
        
        with patch('phoenix_real_estate.foundation.database.connection.AsyncIOMotorClient',
                  return_value=mock_client):
            # Create instance
            instance1 = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            # Mock index creation
            mock_collection = MagicMock()
            mock_collection.create_index = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            
            await instance1.connect()
            
            # Reset instance
            DatabaseConnection.reset_instance()
            
            # Get new instance
            instance2 = DatabaseConnection.get_instance(
                "mongodb://localhost:27017",
                "test_db"
            )
            
            assert instance1 is not instance2
            assert DatabaseConnection._instance is instance2
