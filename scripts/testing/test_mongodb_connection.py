#!/usr/bin/env python3
"""Test MongoDB connection and set up Phoenix Real Estate database."""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


async def test_and_setup_mongodb():
    """Test MongoDB connection and create database structure."""
    print("[TEST] Testing MongoDB Connection")
    print("=" * 60)

    # Connection details
    mongodb_uri = "mongodb://localhost:27017"
    database_name = "phoenix_real_estate"

    try:
        # 1. Test Connection
        print("\n[1] Connecting to MongoDB...")
        print(f"    URI: {mongodb_uri}")

        client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=5000)

        # Ping the server
        await client.admin.command("ping")
        print("    [OK] Connection successful!")

        # Get server info
        server_info = await client.server_info()
        print(f"    [OK] MongoDB version: {server_info['version']}")
        print(f"    [OK] Server: {server_info.get('gitVersion', 'Unknown')[:8]}...")

        # 2. List databases
        print("\n[2] Checking existing databases...")
        databases = await client.list_database_names()
        print(f"    Found {len(databases)} databases: {', '.join(databases)}")

        # 3. Create/Access phoenix_real_estate database
        print(f"\n[3] Setting up '{database_name}' database...")
        db = client[database_name]

        # 4. Create collections with indexes
        print("\n[4] Creating collections and indexes...")

        # Properties collection
        properties = db["properties"]
        print("    Creating 'properties' collection...")

        # Create indexes
        await properties.create_index("property_id", unique=True)
        await properties.create_index("address.zip")
        await properties.create_index("last_updated")
        await properties.create_index([("address.city", 1), ("address.zip", 1)])
        print("    [OK] Properties indexes created")

        # Test insert
        test_property = {
            "property_id": "TEST-001",
            "address": {"street": "123 Test Street", "city": "Phoenix", "zip": "85001"},
            "features": {"beds": 3, "baths": 2, "sqft": 1500},
            "prices": [{"date": datetime.now(), "amount": 350000, "source": "test"}],
            "last_updated": datetime.now(),
            "source": "test",
            "test_record": True,
        }

        # Insert and retrieve
        await properties.replace_one({"property_id": "TEST-001"}, test_property, upsert=True)
        print("    [OK] Test property inserted")

        # Retrieve it
        retrieved = await properties.find_one({"property_id": "TEST-001"})
        print(f"    [OK] Test property retrieved: {retrieved['address']['street']}")

        # Clean up test record
        await properties.delete_one({"property_id": "TEST-001"})
        print("    [OK] Test property cleaned up")

        # 5. Create other collections
        print("\n[5] Creating additional collections...")

        # Collection history
        collection_history = db["collection_history"]
        await collection_history.create_index([("timestamp", -1)])
        await collection_history.create_index("source")
        print("    [OK] Collection history indexes created")

        # Errors collection
        errors = db["errors"]
        await errors.create_index([("timestamp", -1)])
        await errors.create_index("error_type")
        print("    [OK] Errors collection indexes created")

        # 6. Database statistics
        print("\n[6] Database statistics...")
        stats = await db.command("dbstats")
        print(f"    Database size: {stats.get('dataSize', 0):,} bytes")
        print(f"    Collections: {stats.get('collections', 0)}")
        print(f"    Indexes: {stats.get('indexes', 0)}")

        # 7. Summary
        print("\n" + "=" * 60)
        print("[SUCCESS] MongoDB Setup Complete!")
        print("\nConnection Details:")
        print(f"  URI: {mongodb_uri}")
        print(f"  Database: {database_name}")
        print("\nCollections Created:")
        print("  - properties (with indexes)")
        print("  - collection_history")
        print("  - errors")
        print("\n[READY] Database ready for data collection!")

        return True

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}")
        print(f"Details: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure MongoDB service is running:")
        print("     net start MongoDB")
        print("  2. Check if MongoDB is listening on port 27017")
        print("  3. Check Windows Firewall settings")
        return False

    finally:
        if "client" in locals():
            client.close()


if __name__ == "__main__":
    success = asyncio.run(test_and_setup_mongodb())
    exit(0 if success else 1)
