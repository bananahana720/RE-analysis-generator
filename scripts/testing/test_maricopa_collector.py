#!/usr/bin/env python3
"""
Test script for Maricopa County Collector.

This script tests the Maricopa collector with the fixed authentication headers.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.collectors.maricopa import MaricopaAPICollector


async def test_maricopa_collector():
    """Test the Maricopa collector with authentication."""
    print("[TEST] Maricopa County Collector")
    print("=" * 60)

    # Initialize configuration
    config = EnvironmentConfigProvider(load_dotenv=True)

    # Check if API key is configured
    api_key = config.get("MARICOPA_API_KEY")
    if not api_key:
        print("[ERROR] MARICOPA_API_KEY not found in .env file")
        print("Please set MARICOPA_API_KEY in your .env file")
        return False

    print(f"[OK] API Key configured: {api_key[:8]}...")

    # Initialize collector
    collector = MaricopaAPICollector(config)

    try:
        # Test 1: Search by ZIP code
        print("\n[TEST 1] Search by ZIP code 85031")
        print("-" * 40)

        properties = await collector.collect_by_zipcode("85031", limit=3)

        if properties:
            print(f"[SUCCESS] Found {len(properties)} properties")
            for i, prop in enumerate(properties, 1):
                print(f"\nProperty {i}:")
                print(f"  APN: {prop.get('apn', 'N/A')}")
                print(f"  Address: {prop.get('address', {}).get('full_address', 'N/A')}")
                print(f"  Owner: {prop.get('owner_name', 'N/A')}")
                print(f"  Value: ${prop.get('assessed_value', 0):,}")
        else:
            print("[WARNING] No properties found")

        # Test 2: Get property details
        if properties and properties[0].get("apn"):
            apn = properties[0]["apn"]
            print(f"\n[TEST 2] Get details for APN: {apn}")
            print("-" * 40)

            details = await collector.get_property_details(apn)

            if details:
                print("[SUCCESS] Retrieved property details")
                print(f"  Bedrooms: {details.get('bedrooms', 'N/A')}")
                print(f"  Bathrooms: {details.get('bathrooms', 'N/A')}")
                print(f"  Square Feet: {details.get('square_feet', 'N/A')}")
                print(f"  Year Built: {details.get('year_built', 'N/A')}")
                print(f"  Property Type: {details.get('property_type', 'N/A')}")
            else:
                print("[WARNING] No details found")

        # Test 3: Test metrics
        print("\n[TEST 3] Collector Metrics")
        print("-" * 40)

        metrics = collector.get_metrics()
        print(f"Total Requests: {metrics.get('total_requests', 0)}")
        print(f"Successful: {metrics.get('successful_requests', 0)}")
        print(f"Failed: {metrics.get('failed_requests', 0)}")
        if metrics.get("total_requests", 0) > 0:
            success_rate = (metrics.get("successful_requests", 0) / metrics["total_requests"]) * 100
            print(f"Success Rate: {success_rate:.1f}%")

        print("\n[SUCCESS] All tests completed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        await collector.close()


async def main():
    """Main function."""
    success = await test_maricopa_collector()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
