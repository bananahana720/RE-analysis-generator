#\!/usr/bin/env python3
"""Test script for Maricopa County Collector optimized for CI/CD."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database.mock import MockPropertyRepository
from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector


async def test_maricopa_collector(zip_code="85031", mode="test"):
    """Test the Maricopa collector with authentication."""
    print(f"[TEST] Maricopa County Collector - {mode.upper()} mode")
    print("=" * 60)

    # Initialize configuration - don't load .env in CI
    config = EnvironmentConfigProvider(load_dotenv=False)

    # Check if API key is configured (from environment)
    api_key = os.getenv("MARICOPA_API_KEY") or config.get("MARICOPA_API_KEY")
    if not api_key:
        print("[ERROR] MARICOPA_API_KEY not found in environment variables")
        return False

    print(f"[OK] API Key configured: {api_key[:8]}...")

    # Use mock repository for CI testing
    repository = MockPropertyRepository()
    print("[OK] Mock repository initialized")

    # Initialize collector
    collector = MaricopaAPICollector(config, repository)

    try:
        # Test search by ZIP code using correct method
        print(f"[TEST] Collecting properties for ZIP: {zip_code}")
        
        # Use the correct method name
        properties = await collector.collect_zipcode(zip_code)
        
        if mode == "test" and len(properties) > 3:
            properties = properties[:3]  # Limit for test mode
            
        print(f"[OK] Found {len(properties)} properties")
        
        if properties:
            first_property = properties[0]
            print(f"[SAMPLE] First property keys: {list(first_property.keys())[:5]}")
        
        print("[SUCCESS] Maricopa collector test completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] Collector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await collector.close()


def main():
    """Main function with CLI argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Maricopa collector")
    parser.add_argument("--zip-code", default="85031", help="ZIP code to test")
    parser.add_argument("--mode", default="test", choices=["test", "incremental", "full"])
    
    args = parser.parse_args()
    
    success = asyncio.run(test_maricopa_collector(args.zip_code, args.mode))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
