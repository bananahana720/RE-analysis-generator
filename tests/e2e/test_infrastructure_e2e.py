#!/usr/bin/env python3
"""
Infrastructure E2E tests that validate the complete system setup.

These tests verify that all components work together without
requiring access to the actual Phoenix MLS website.
"""

import asyncio
import pytest
from datetime import datetime
import os
import sys
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from phoenix_real_estate.foundation.config import get_config, reset_config_cache
from phoenix_real_estate.foundation.database.connection import DatabaseConnection
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.monitoring import MetricsCollector


class MockPhoenixMLSCollector:
    """Mock collector for E2E testing."""
    
    async def collect_data(self) -> Dict[str, Any]:
        """Simulate data collection."""
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Return mock property data
        return {
            "properties": [
                {
                    "property_id": "MOCK-001",
                    "address": {
                        "street": "123 Test St",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zip": "85031"
                    },
                    "features": {
                        "beds": 3,
                        "baths": 2,
                        "sqft": 1500,
                        "year_built": 2020
                    },
                    "listing": {
                        "price": 350000,
                        "status": "active",
                        "days_on_market": 7
                    },
                    "source": "mock_mls",
                    "last_updated": datetime.utcnow()
                },
                {
                    "property_id": "MOCK-002",
                    "address": {
                        "street": "456 Demo Ave",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zip": "85033"
                    },
                    "features": {
                        "beds": 4,
                        "baths": 3,
                        "sqft": 2200,
                        "year_built": 2018
                    },
                    "listing": {
                        "price": 450000,
                        "status": "active",
                        "days_on_market": 14
                    },
                    "source": "mock_mls",
                    "last_updated": datetime.utcnow()
                }
            ],
            "metadata": {
                "total_found": 2,
                "collection_time": 0.1,
                "success": True
            }
        }


@pytest.mark.e2e
class TestInfrastructureE2E:
    """End-to-end tests for the complete infrastructure."""
    
    @pytest.fixture
    async def test_config(self):
        """Create test config."""
        reset_config_cache()  # Reset any cached config
        os.environ["MONGODB_DATABASE"] = "phoenix_real_estate_e2e_test"
        config = get_config()
        return config
    
    @pytest.fixture
    async def test_db_client(self, test_config):
        """Create test database client."""
        # Get MongoDB URI and database name from config
        mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        mongodb_database = os.environ.get("MONGODB_DATABASE", "phoenix_real_estate_e2e_test")
        
        db_conn = DatabaseConnection.get_instance(mongodb_uri, mongodb_database)
        await db_conn.connect()
        
        # Clean test database
        db = db_conn.get_database()
        collections = await db.list_collection_names()
        for collection in collections:
            await db.drop_collection(collection)
        
        yield db_conn
        
        # Cleanup
        await db.drop_collection("properties")
        await db.drop_collection("collection_history") 
        await db.drop_collection("errors")
        await db_conn.close()
    
    @pytest.mark.asyncio
    async def test_complete_data_pipeline(self, test_config, test_db_client):
        """Test the complete data collection and storage pipeline."""
        # Initialize components
        repository = PropertyRepository(test_db_client)
        collector = MockPhoenixMLSCollector()
        metrics = MetricsCollector()
        
        # Start metrics collection
        metrics_task = asyncio.create_task(metrics.start())
        
        try:
            # Phase 1: Collect data
            print("\n[Phase 1] Collecting data...")
            collection_result = await collector.collect_data()
            
            assert collection_result["metadata"]["success"], "Data collection failed"
            assert len(collection_result["properties"]) > 0, "No properties collected"
            
            # Phase 2: Store data
            print("[Phase 2] Storing data...")
            stored_count = 0
            
            for property_data in collection_result["properties"]:
                result = await repository.upsert_property(property_data)
                if result:
                    stored_count += 1
                    metrics.record_property_stored()
            
            assert stored_count == len(collection_result["properties"]), \
                f"Not all properties stored: {stored_count}/{len(collection_result['properties'])}"
            
            # Phase 3: Verify storage
            print("[Phase 3] Verifying storage...")
            db_count = await repository.count_properties()
            assert db_count == stored_count, f"Database count mismatch: {db_count} vs {stored_count}"
            
            # Phase 4: Test retrieval
            print("[Phase 4] Testing retrieval...")
            all_properties = await repository.get_all_properties(limit=10)
            assert len(all_properties) == stored_count, "Retrieved property count mismatch"
            
            # Verify property data integrity
            for prop in all_properties:
                assert "property_id" in prop, "Missing property_id"
                assert "address" in prop, "Missing address"
                assert "features" in prop, "Missing features"
                assert "source" in prop, "Missing source"
            
            # Phase 5: Test search functionality
            print("[Phase 5] Testing search...")
            phoenix_properties = await repository.find_properties_by_city("Phoenix")
            assert len(phoenix_properties) == stored_count, "City search failed"
            
            zip_properties = await repository.find_properties_by_zip("85031")
            assert len(zip_properties) >= 1, "Zip code search failed"
            
            # Phase 6: Test metrics
            print("[Phase 6] Checking metrics...")
            current_metrics = metrics.get_metrics()
            assert current_metrics["properties_stored"] == stored_count, "Metrics count mismatch"
            
            print("\n[SUCCESS] All pipeline phases completed successfully!")
            
        finally:
            # Stop metrics collection
            metrics.stop()
            try:
                await asyncio.wait_for(metrics_task, timeout=1.0)
            except asyncio.TimeoutError:
                metrics_task.cancel()
    
    @pytest.mark.asyncio
    async def test_error_handling_pipeline(self, test_config, test_db_client):
        """Test error handling throughout the pipeline."""
        repository = PropertyRepository(test_db_client)
        
        # Test handling invalid property data
        invalid_property = {
            "property_id": None,  # Invalid
            "address": "Not a proper address format"  # Invalid
        }
        
        # Should handle gracefully without crashing
        result = await repository.upsert_property(invalid_property)
        assert result is not None  # Should still process despite issues
        
        # Test duplicate handling
        valid_property = {
            "property_id": "DUP-001",
            "address": {
                "street": "789 Duplicate St",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85035"
            },
            "source": "test",
            "last_updated": datetime.utcnow()
        }
        
        # Insert twice
        result1 = await repository.upsert_property(valid_property)
        result2 = await repository.upsert_property(valid_property)
        
        # Should handle duplicates gracefully
        assert result1 is not None
        assert result2 is not None
        
        # Count should still be 1
        count = await repository.count_properties({"property_id": "DUP-001"})
        assert count == 1, "Duplicate was not handled correctly"
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_performance_characteristics(self, test_config, test_db_client):
        """Test performance characteristics of the pipeline."""
        import time
        import psutil
        
        repository = PropertyRepository(test_db_client)
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate test data
        num_properties = 100
        properties = []
        for i in range(num_properties):
            properties.append({
                "property_id": f"PERF-{i:04d}",
                "address": {
                    "street": f"{i} Performance St",
                    "city": "Phoenix",
                    "state": "AZ", 
                    "zip": "85031"
                },
                "features": {
                    "beds": 3,
                    "baths": 2,
                    "sqft": 1500 + i * 10
                },
                "listing": {
                    "price": 300000 + i * 1000,
                    "status": "active"
                },
                "source": "performance_test",
                "last_updated": datetime.utcnow()
            })
        
        # Measure insertion performance
        start_time = time.time()
        
        # Batch insert
        insert_tasks = []
        for prop in properties:
            insert_tasks.append(repository.upsert_property(prop))
        
        await asyncio.gather(*insert_tasks)
        
        insert_time = time.time() - start_time
        
        # Measure retrieval performance
        retrieve_start = time.time()
        await repository.get_all_properties(limit=num_properties)
        retrieve_time = time.time() - retrieve_start
        
        # Calculate metrics
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = final_memory - initial_memory
        
        # Performance assertions
        avg_insert_time = insert_time / num_properties
        avg_retrieve_time = retrieve_time / num_properties
        
        print("\nPerformance Metrics:")
        print(f"  Total Properties: {num_properties}")
        print(f"  Total Insert Time: {insert_time:.2f}s")
        print(f"  Avg Insert Time: {avg_insert_time*1000:.2f}ms per property")
        print(f"  Total Retrieve Time: {retrieve_time:.2f}s") 
        print(f"  Avg Retrieve Time: {avg_retrieve_time*1000:.2f}ms per property")
        print(f"  Memory Used: {memory_used:.2f}MB")
        
        # Performance thresholds
        assert avg_insert_time < 0.1, f"Insert too slow: {avg_insert_time:.3f}s per property"
        assert avg_retrieve_time < 0.01, f"Retrieve too slow: {avg_retrieve_time:.3f}s per property"
        assert memory_used < 50, f"Excessive memory usage: {memory_used:.2f}MB"


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])