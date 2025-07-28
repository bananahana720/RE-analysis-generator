"""Test script for PropertyDataExtractor."""

import asyncio
from phoenix_real_estate.collectors.processing import PropertyDataExtractor
from phoenix_real_estate.foundation.config.settings import get_settings

# Sample Phoenix MLS HTML
SAMPLE_HTML = """
<div class="property-details">
    <h1>$525,000 - 5BR/3BA Single Family Home</h1>
    <div class="address">456 Oak Street, Phoenix, AZ 85031</div>
    <div class="specs">
        <span>3,200 sq ft</span>
        <span>Built 2010</span>
        <span>0.33 acre lot</span>
    </div>
    <div class="description">
        Stunning home with modern updates including granite countertops, 
        stainless steel appliances, and a resort-style backyard with pool and spa.
        Perfect for entertaining!
    </div>
</div>
"""

# Sample Maricopa County JSON
SAMPLE_JSON = {
    "parcel_number": "456-78-901",
    "owner_name": "JOHNSON ROBERT & MARY",
    "property_address": "456 OAK ST PHOENIX AZ 85031",
    "assessed_value": 425000,
    "year_built": 2010,
    "square_footage": 3200,
    "lot_size": "14374",
    "property_type": "SINGLE FAMILY RESIDENTIAL"
}


async def test_extractor():
    """Test the PropertyDataExtractor with sample data."""
    print("Testing PropertyDataExtractor...\n")
    
    # Get settings
    settings = get_settings()
    
    # Create config mock for testing
    class MockConfig:
        def __init__(self):
            self.settings = settings
    
    config = MockConfig()
    
    # Create extractor
    async with PropertyDataExtractor(config) as extractor:
        print("✓ Extractor initialized successfully\n")
        
        # Test Phoenix MLS extraction
        print("Testing Phoenix MLS HTML extraction...")
        try:
            mls_result = await extractor.extract_from_html(
                SAMPLE_HTML,
                source="phoenix_mls"
            )
            print("✓ Extracted MLS data:")
            print(f"  - Price: ${mls_result.get('price', 'N/A'):,}")
            print(f"  - Bedrooms: {mls_result.get('bedrooms', 'N/A')}")
            print(f"  - Bathrooms: {mls_result.get('bathrooms', 'N/A')}")
            print(f"  - Square Feet: {mls_result.get('square_feet', 'N/A'):,}")
            print(f"  - Address: {mls_result.get('address', {})}")
            print(f"  - Features: {mls_result.get('features', [])}")
            print()
        except Exception as e:
            print(f"✗ MLS extraction failed: {e}\n")
        
        # Test Maricopa County extraction
        print("Testing Maricopa County JSON extraction...")
        try:
            maricopa_result = await extractor.extract_from_json(
                SAMPLE_JSON,
                source="maricopa_county"
            )
            print("✓ Extracted Maricopa data:")
            print(f"  - Parcel: {maricopa_result.get('parcel_number', 'N/A')}")
            print(f"  - Owner: {maricopa_result.get('owner_name', 'N/A')}")
            print(f"  - Assessed Value: ${maricopa_result.get('assessed_value', 'N/A'):,}")
            print(f"  - Year Built: {maricopa_result.get('year_built', 'N/A')}")
            print(f"  - Lot Size: {maricopa_result.get('lot_size', 'N/A')}")
            print(f"  - Address: {maricopa_result.get('address', {})}")
            print()
        except Exception as e:
            print(f"✗ Maricopa extraction failed: {e}\n")
        
        # Test batch extraction
        print("Testing batch extraction...")
        try:
            batch_results = await extractor.extract_batch(
                [SAMPLE_HTML] * 2,
                source="phoenix_mls",
                content_type="html"
            )
            print(f"✓ Batch extraction completed: {len(batch_results)} items processed")
            for i, result in enumerate(batch_results):
                if "error" not in result:
                    print(f"  - Item {i+1}: ${result.get('price', 'N/A'):,} - {result.get('address', {}).get('street', 'N/A')}")
                else:
                    print(f"  - Item {i+1}: Error - {result['error']}")
        except Exception as e:
            print(f"✗ Batch extraction failed: {e}")
    
    print("\n✓ All tests completed!")


if __name__ == "__main__":
    print("Note: This test requires Ollama to be running with llama3.2:latest model")
    print("If Ollama is not available, the extraction will fail.\n")
    asyncio.run(test_extractor())