import asyncio
import time
from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.orchestration import ProcessingIntegrator

async def test_production_performance():
    print("Starting production performance test...")
    config = EnvironmentConfigProvider()
    
    # Test single property processing speed
    start_time = time.time()
    async with ProcessingIntegrator(config) as integrator:
        # Sample property data
        sample_html = """
        <div class="property-details">
            <h1>Beautiful Home in Phoenix</h1>
            <p class="price">$450000</p>
            <p class="sqft">2500 sqft</p>
            <p class="beds">4 bedrooms</p>
            <p class="baths">3 bathrooms</p>
            <div class="address">1234 Main St, Phoenix, AZ 85031</div>
        </div>
        """
        
        # Process single property
        processing_start = time.time()
        results = await integrator.process_maricopa_batch([{
            'property_id': 'test-001',
            'html_content': sample_html,
            'source_url': 'https://recorder.maricopa.gov/test',
            'zip_code': '85031'
        }])
        processing_end = time.time()
        
        processing_time_ms = (processing_end - processing_start) * 1000
        print(f"Single property LLM processing: {processing_time_ms:.1f}ms")
        
        if results and len(results) > 0:
            result = results[0]
            print(f"Processing success: {result.success}")
            if result.success and result.property_details:
                print(f"Extracted price: ${result.property_details.price:,}" if result.property_details.price else "No price")
                print(f"Extracted sqft: {result.property_details.sqft}" if result.property_details.sqft else "No sqft")
                print(f"Quality score: {result.quality_score:.2f}")
        
    total_time = time.time() - start_time
    print(f"Total test time: {total_time:.1f}s")
    return processing_time_ms

if __name__ == "__main__":
    result = asyncio.run(test_production_performance())
    print(f"PERFORMANCE RESULT: {result:.1f}ms")
EOF < /dev/null
