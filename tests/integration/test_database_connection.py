"""Integration tests for MongoDB connection management.

This module contains integration tests that test the DatabaseConnection class
against a real MongoDB instance (when available).
"""

import os
import pytest
import asyncio
from datetime import datetime, timezone

from phoenix_real_estate.foundation.database.connection import DatabaseConnection


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("MONGODB_URI"),
    reason="MONGODB_URI not set - skipping integration tests"
)
class TestDatabaseConnectionIntegration:
    """Integration tests for DatabaseConnection with real MongoDB."""
    
    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up after each test."""
        # Reset singleton before test
        DatabaseConnection._instance = None
        yield
        # Clean up after test
        if DatabaseConnection._instance:
            await DatabaseConnection._instance.close()
        DatabaseConnection._instance = None
    
    @pytest.fixture
    def mongodb_uri(self):
        """Get MongoDB URI from environment."""
        return os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    
    @pytest.fixture
    def test_database_name(self):
        """Get test database name."""
        return "phoenix_re_test"
    
    @pytest.mark.asyncio
    async def test_real_connection(self, mongodb_uri, test_database_name):
        """Test connecting to a real MongoDB instance."""
        db_conn = DatabaseConnection.get_instance(
            mongodb_uri,
            test_database_name
        )
        
        # Connect to database
        await db_conn.connect()
        
        # Verify connection
        assert db_conn._is_connected is True
        
        # Perform health check
        health = await db_conn.health_check()
        assert health["connected"] is True
        assert health["ping_time_ms"] > 0
        assert health["database_stats"] is not None
        
        # Close connection
        await db_conn.close()
        assert db_conn._is_connected is False

    @pytest.mark.asyncio
    async def test_index_creation(self, mongodb_uri, test_database_name):
        """Test that indexes are created correctly."""
        db_conn = DatabaseConnection.get_instance(
            mongodb_uri,
            test_database_name
        )
        
        async with db_conn.get_database() as db:
            # Get index information
            properties_indexes = await db["properties"].index_information()
            daily_reports_indexes = await db["daily_reports"].index_information()
            
            # Verify property_id unique index
            property_id_index = next(
                (idx for idx in properties_indexes.values() 
                 if idx.get("key") == [("property_id", 1)]),
                None
            )
            assert property_id_index is not None
            assert property_id_index.get("unique") is True
            
            # Verify compound indexes exist
            compound_indexes = [
                [("address.zipcode", 1), ("listing.status", 1)],
                [("address.zipcode", 1), ("current_price", -1)],
                [("is_active", 1), ("last_updated", -1)]
            ]
            
            for expected_key in compound_indexes:
                found = any(
                    idx.get("key") == expected_key
                    for idx in properties_indexes.values()
                )
                assert found, f"Compound index {expected_key} not found"
            
            # Verify daily_reports date unique index
            date_index = next(
                (idx for idx in daily_reports_indexes.values()
                 if idx.get("key") == [("date", 1)]),
                None
            )
            assert date_index is not None
            assert date_index.get("unique") is True
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, mongodb_uri, test_database_name):
        """Test handling concurrent database operations."""
        db_conn = DatabaseConnection.get_instance(
            mongodb_uri,
            test_database_name
        )
        
        async def perform_operation(operation_id: int):
            """Perform a database operation."""
            async with db_conn.get_database() as db:
                # Insert a test document
                result = await db["test_concurrent"].insert_one({
                    "operation_id": operation_id,
                    "timestamp": datetime.now(timezone.utc)
                })
                assert result.inserted_id is not None
                
                # Read it back
                doc = await db["test_concurrent"].find_one({
                    "_id": result.inserted_id
                })
                assert doc["operation_id"] == operation_id
        
        # Run multiple operations concurrently
        tasks = [perform_operation(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify all documents were created
        async with db_conn.get_database() as db:
            count = await db["test_concurrent"].count_documents({})
            assert count == 10
            
            # Clean up
            await db["test_concurrent"].drop()

    @pytest.mark.asyncio
    async def test_connection_pool_limits(self, mongodb_uri, test_database_name):
        """Test that connection pool limits are respected."""
        # Create connection with small pool
        db_conn = DatabaseConnection.get_instance(
            mongodb_uri,
            test_database_name,
            max_pool_size=3,
            min_pool_size=1
        )
        
        await db_conn.connect()
        
        # Pool size should be limited
        assert db_conn.max_pool_size == 3
        assert db_conn.min_pool_size == 1
        
        # Perform health check
        health = await db_conn.health_check()
        assert health["connection_pool"]["max_size"] == 3
        assert health["connection_pool"]["min_size"] == 1
    
    @pytest.mark.asyncio
    async def test_database_operations(self, mongodb_uri, test_database_name):
        """Test basic database operations through the connection."""
        db_conn = DatabaseConnection.get_instance(
            mongodb_uri,
            test_database_name
        )
        
        test_collection = "test_operations"
        test_doc = {
            "property_id": "test-123",
            "address": {
                "street": "123 Test St",
                "city": "Phoenix",
                "zipcode": "85001"
            },
            "current_price": 250000,
            "last_updated": datetime.now(timezone.utc)
        }
        
        async with db_conn.get_database() as db:
            # Insert document
            result = await db[test_collection].insert_one(test_doc)
            assert result.inserted_id is not None
            
            # Find document
            found_doc = await db[test_collection].find_one({
                "property_id": "test-123"
            })
            assert found_doc is not None
            assert found_doc["address"]["street"] == "123 Test St"
            
            # Update document
            update_result = await db[test_collection].update_one(
                {"property_id": "test-123"},
                {"": {"current_price": 275000}}
            )
            assert update_result.modified_count == 1
            
            # Verify update
            updated_doc = await db[test_collection].find_one({
                "property_id": "test-123"
            })
            assert updated_doc["current_price"] == 275000
            
            # Delete document
            delete_result = await db[test_collection].delete_one({
                "property_id": "test-123"
            })
            assert delete_result.deleted_count == 1
            
            # Clean up collection
            await db[test_collection].drop()
