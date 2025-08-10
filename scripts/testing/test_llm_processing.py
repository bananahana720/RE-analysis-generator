"""
Test LLM Processing Pipeline
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.orchestration import ProcessingIntegrator
from phoenix_real_estate.foundation.database.mock import MockPropertyRepository
from phoenix_real_estate.models import PropertyDetails

# Sample property data for LLM processing test
SAMPLE_PROPERTY = {
    "apn": "217-32-045",
    "property_type": "Single Family Residential",
    "legal_description": "Lot 15 Block 8 Desert Estates Phase II",
    "subdivision": "Desert Estates",
    "address": {
        "house_number": "1234",
        "street_name": "Desert Willow",
        "street_type": "Ln",
        "city": "Phoenix",
        "state": "AZ", 
        "zipcode": "85048-1234",
        "full_address": "1234 Desert Willow Ln, Phoenix, AZ 85048-1234",
    },
    "residential_details": {
        "bedrooms": 4,
        "bathrooms": 3.5,
        "living_area_sqft": 2850,
        "lot_size_sqft": 9600,
        "year_built": 2005,
        "floors": 2,
        "garage_spaces": 3,
        "pool": True,
        "fireplace": False,
        "ac_type": "Central Air",
        "heating_type": "Gas Forced Air",
    },
    "valuation": {
        "assessed_value": 425000,
        "market_value": 485000,
        "land_value": 150000,
        "improvement_value": 335000,
        "tax_amount": 4980,
        "tax_year": 2024,
    },
    "ownership": {
        "owner_name": "Jane Smith",
        "mailing_address": "1234 Desert Willow Ln, Phoenix, AZ 85048",
    },
}

async def test_llm_processing_pipeline():
    """Test the complete LLM processing pipeline with sample data"""
    
    print("Phoenix Real Estate - LLM Processing Pipeline Test")
    print("=" * 55)
    
    config = EnvironmentConfigProvider()
    results = {"tests_passed": 0, "tests_failed": 0, "performance": {}}
    
    try:
        print("[TEST] Initializing ProcessingIntegrator...")
        repository = MockPropertyRepository()
        async with ProcessingIntegrator(config, repository) as integrator:
            
            # Test 1: Single property processing
            print("\n[TEST] Processing single property...")
            start_time = time.time()
            
            processed_results = await integrator.process_maricopa_batch([SAMPLE_PROPERTY])
            
            processing_time = time.time() - start_time
            results["performance"]["single_property_ms"] = processing_time * 1000
            
            if processed_results and len(processed_results) > 0:
                print(f"[PASS] Single property processed in {processing_time*1000:.1f}ms")
                results["tests_passed"] += 1
                
                # Check result structure
                result = processed_results[0]
                if "property_summary" in result or "analysis" in result or "processed_data" in result:
                    print(f"[PASS] LLM processing generated structured output")
                    results["tests_passed"] += 1
                else:
                    print(f"[FAIL] LLM processing did not generate expected structure")
                    results["tests_failed"] += 1
                    
            else:
                print(f"[FAIL] Single property processing failed")
                results["tests_failed"] += 1
            
            # Test 2: Batch processing (3 properties)
            print("\n[TEST] Processing batch of properties...")
            batch_data = [SAMPLE_PROPERTY.copy() for _ in range(3)]
            # Modify APNs to make them unique
            for i, prop in enumerate(batch_data):
                prop["apn"] = f"217-32-{45 + i:03d}"
                
            start_time = time.time()
            batch_results = await integrator.process_maricopa_batch(batch_data)
            processing_time = time.time() - start_time
            
            results["performance"]["batch_3_properties_ms"] = processing_time * 1000
            avg_per_property = processing_time / 3 * 1000 if processing_time > 0 else 0
            
            if batch_results and len(batch_results) == 3:
                print(f"[PASS] Batch of 3 properties processed in {processing_time*1000:.1f}ms")
                print(f"[INFO] Average per property: {avg_per_property:.1f}ms")
                results["tests_passed"] += 1
                
                # Check for performance target (<60 seconds per property)
                if avg_per_property < 60000:
                    print(f"[PASS] Performance target met (<60s per property)")
                    results["tests_passed"] += 1
                else:
                    print(f"[WARN] Performance target missed (>{avg_per_property/1000:.1f}s per property)")
                    results["tests_failed"] += 1
            else:
                print(f"[FAIL] Batch processing failed - expected 3, got {len(batch_results) if batch_results else 0}")
                results["tests_failed"] += 1
                
    except Exception as e:
        print(f"[FAIL] LLM Processing Pipeline: {e}")
        results["tests_failed"] += 1
    
    # Performance Summary
    print("\n" + "=" * 50)
    print("LLM Processing Performance Summary:")
    print("=" * 50)
    
    if "single_property_ms" in results["performance"]:
        print(f"Single Property:   {results['performance']['single_property_ms']:.1f}ms")
    
    if "batch_3_properties_ms" in results["performance"]:
        batch_time = results["performance"]["batch_3_properties_ms"]
        avg_time = batch_time / 3
        print(f"Batch (3 props):   {batch_time:.1f}ms total")
        print(f"Average per prop:  {avg_time:.1f}ms ({avg_time/1000:.1f}s)")
    
    # Results Summary
    total_tests = results["tests_passed"] + results["tests_failed"]
    success_rate = (results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nTest Results: {results['tests_passed']}/{total_tests} passed ({success_rate:.1f}%)")
    
    overall_success = results["tests_failed"] == 0
    print(f"Overall Status: {'READY' if overall_success else 'ISSUES DETECTED'}")
    
    return overall_success

if __name__ == "__main__":
    result = asyncio.run(test_llm_processing_pipeline())
    sys.exit(0 if result else 1)
