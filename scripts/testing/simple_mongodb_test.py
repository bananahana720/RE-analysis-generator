"""Simple MongoDB test"""
import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database import DatabaseConnection

async def test_mongodb_operations():
    """Test basic MongoDB operations"""
    print("Testing MongoDB Storage Operations...")
    print("=" * 45)
    
    config = EnvironmentConfigProvider()
    success = False
    
    try:
        # Create database connection
        db = DatabaseConnection(
            uri=config.get("MONGODB_URI", "mongodb://localhost:27017"),
            database_name=config.get("MONGODB_DATABASE", "phoenix_real_estate")
        )
        
        print("[TEST] Connecting to MongoDB...")
        await db.connect()
        
        print("[TEST] Running health check...")
        await db.health_check()
        print("[OK] Health check completed")
        
        # Test collection operations
        print("[TEST] Testing collection operations...")
        async with db.get_database() as database:
            collection = database.get_collection('test_properties')
            
            # Insert test document
            test_doc = {
                "apn": "test-123-456",
                "address": "123 Test St, Phoenix, AZ",
                "test_timestamp": datetime.utcnow(),
                "test_data": "validation_test"
            }
            
            print("[TEST] Inserting test document...")
            result = await collection.insert_one(test_doc)
            
            if result.inserted_id:
                print(f"[OK] Document inserted with ID: {result.inserted_id}")
                
                # Query the document back
                print("[TEST] Querying document...")
                retrieved = await collection.find_one({"apn": "test-123-456"})
                
                if retrieved and retrieved["test_data"] == "validation_test":
                    print("[OK] Document retrieved successfully")
                    
                    # Clean up test document
                    print("[TEST] Cleaning up test document...")
                    delete_result = await collection.delete_one({"apn": "test-123-456"})
                    
                    if delete_result.deleted_count == 1:
                        print("[OK] Test document cleaned up")
                        
                        # Test index operations
                        print("[TEST] Testing indexes...")
                        indexes = await collection.list_indexes().to_list(length=None)
                        print(f"[OK] Found {len(indexes)} indexes")
                        
                        print("[OK] All MongoDB operations successful")
                        success = True
                    else:
                        print("[WARN] Failed to clean up test document")
                        success = False
                else:
                    print("[FAIL] Failed to retrieve test document")
                    success = False
            else:
                print("[FAIL] Failed to insert test document")  
                success = False
        
        await db.close()
        
    except Exception as e:
        print(f"[FAIL] MongoDB operations failed: {e}")
        success = False
    
    print("=" * 45)
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(test_mongodb_operations())
    sys.exit(0 if result else 1)
