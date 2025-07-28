#!/usr/bin/env python3
"""Quick MongoDB Atlas Connection Test.

Simple script to quickly test if MongoDB Atlas connection is working.

Usage:
    python scripts/test_db_connection.py
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phoenix_real_estate.foundation.config.environment import get_config
from phoenix_real_estate.foundation.database.connection import get_database_connection


async def test_connection():
    """Test basic MongoDB connection."""
    print("Testing MongoDB Atlas Connection...")
    print("-" * 40)
    
    try:
        # Load configuration
        config = get_config()
        
        # Check if we have MongoDB configuration
        if not hasattr(config, 'mongodb_uri') or not config.mongodb_uri:
            print("ERROR: MONGODB_URI not found in configuration")
            print("TIP: Run: python scripts/setup_mongodb_atlas.py")
            return False
            
        # Get database name
        database_name = getattr(config, 'database_name', None) or getattr(config, 'mongodb_database', None)
        if not database_name:
            print("ERROR: DATABASE_NAME not found in configuration")
            return False
            
        print(f"Database: Database: {database_name}")
        print(f"Environment: Environment: {config.environment.value}")
        
        # Test connection
        print("Connecting Connecting to MongoDB Atlas...")
        db_connection = await get_database_connection(config.mongodb_uri, database_name)
        
        print("SUCCESS: Connection established!")
        
        # Test ping
        print("Testing Testing database ping...")
        health = await db_connection.health_check()
        
        if health.get('connected', False):
            ping_time = health.get('ping_time_ms', 0)
            print(f"SUCCESS: Ping successful: {ping_time}ms")
            
            # Show database stats if available
            if health.get('database_stats'):
                stats = health['database_stats']
                print(f"Collections: Collections: {stats.get('collections', 0)}")
                print(f"Data size: Data size: {stats.get('data_size', 0)} bytes")
            
            return True
        else:
            print("ERROR: Ping failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Connection failed: {str(e)}")
        print()
        print("TIP: Troubleshooting tips:")
        print("   1. Check your MongoDB Atlas connection string")
        print("   2. Verify network access settings (IP whitelist)")
        print("   3. Confirm database user credentials")
        print("   4. Run setup: python scripts/setup_mongodb_atlas.py")
        return False


async def main():
    """Main function."""
    # Check if .env exists
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("ERROR: No .env file found!")
        print("TIP: Run setup first: python scripts/setup_mongodb_atlas.py")
        return 1
    
    success = await test_connection()
    
    if success:
        print()
        print("SUCCESS: MongoDB Atlas connection is working!")
        print("Ready Ready to run full validation: python scripts/validate_mongodb_atlas.py")
        return 0
    else:
        print()
        print("ERROR: Connection test failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)