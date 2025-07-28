#!/usr/bin/env python3
"""Test data collection pipeline with Maricopa API."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.phoenix_real_estate.collectors.maricopa.client import MaricopaAPIClient
from src.phoenix_real_estate.foundation.config import get_config


async def test_data_collection():
    """Test Maricopa API data collection."""
    print("Testing Maricopa API Data Collection")
    print("=" * 50)
    
    try:
        # Initialize client
        config = get_config()
        client = MaricopaAPIClient(config)
        
        # Test property search for ZIP 85031
        print("\n[TEST] Searching properties in ZIP 85031...")
        results = await client.search_property('85031', page=1)
        
        if results and 'results' in results:
            print(f"✅ Found {len(results['results'])} properties")
            
            # Show first property
            if results['results']:
                first = results['results'][0]
                print(f"\nFirst Property:")
                print(f"  - APN: {first.get('APN', 'N/A')}")
                print(f"  - Address: {first.get('PropertyAddress', 'N/A')}")
                print(f"  - Owner: {first.get('OwnerName', 'N/A')}")
        else:
            print("❌ No results returned")
            
        # Test parcel details
        if results and results.get('results'):
            apn = results['results'][0].get('APN')
            if apn:
                print(f"\n[TEST] Getting details for APN {apn}...")
                details = await client.get_parcel_details(apn)
                if details:
                    print(f"✅ Retrieved parcel details")
                    print(f"  - Use Code: {details.get('UseCode', 'N/A')}")
                    print(f"  - Total Market Value: ${details.get('TotalMarketValue', 0):,.2f}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_data_collection())