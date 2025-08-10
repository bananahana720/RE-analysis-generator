import asyncio
import time
from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.orchestration import ProcessingIntegrator

async def test_production_performance():
    print('Starting production performance test...')
    config = EnvironmentConfigProvider()
    
    start_time = time.time()
    async with ProcessingIntegrator(config) as integrator:
        sample_html = '''<div class="property-details"><h1>Beautiful Home in Phoenix</h1><p class="price">50000</p><p class="sqft">2500 sqft</p><p class="beds">4 bedrooms</p><p class="baths">3 bathrooms</p><div class="address">1234 Main St, Phoenix, AZ 85031</div></div>'''
        
        processing_start = time.time()
        results = await integrator.process_maricopa_batch([{
            'property_id': 'test-001',
            'html_content': sample_html,
            'source_url': 'https://recorder.maricopa.gov/test',
            'zip_code': '85031'
        }])
        processing_end = time.time()
        
        processing_time_ms = (processing_end - processing_start) * 1000
        print(f'Single property LLM processing: {processing_time_ms:.1f}ms')
        
        if results and len(results) > 0:
            result = results[0]
            print(f'Processing success: {result.success}')
            if result.success and result.property_details:
                print(f'Extracted price: {result.property_details.price}')
                print(f'Quality score: {result.quality_score:.2f}')
        
    total_time = time.time() - start_time
    print(f'Total test time: {total_time:.1f}s')
    return processing_time_ms

result = asyncio.run(test_production_performance())
print(f'PERFORMANCE RESULT: {result:.1f}ms')
