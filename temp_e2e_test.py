import asyncio
import os
import sys
sys.path.insert(0, ".")

from phoenix_real_estate.foundation.config.provider import ConfigProvider
from phoenix_real_estate.collectors.processing.pipeline import DataProcessingPipeline
from phoenix_real_estate.orchestration import ProcessingIntegrator
from phoenix_real_estate.foundation.database.connection import DatabaseConnection
from phoenix_real_estate.foundation.database.repositories import PropertyRepository

async def test_e2e():
    print("=== Phoenix Real Estate E2E Test ===")
    
    # Setup
    os.environ["MONGODB_DATABASE"] = "phoenix_real_estate_e2e_manual"
    config = ConfigProvider()
    
    html_content = """<div class="property-details">
        <h1>Test Property E2E</h1>
        <div class="address">123 E2E Test Street, Phoenix, AZ 85031</div>
        <div class="price">$425,000</div>
        <div class="features">
            <span class="beds">4 beds</span>
            <span class="baths">3 baths</span>
            <span class="sqft">2,200 sq ft</span>
        </div>
        <div class="details">
            <p>MLS#: E2E001</p>
            <p>Year Built: 2020</p>
        </div>
    </div>"""
    
    try:
        print("1. Connecting to database...")
        db_conn = DatabaseConnection.get_instance(config.mongodb_uri, config.mongodb_database)
        await db_conn.connect()
        print("   Database connected successfully")
        
        print("2. Cleaning test database...")
        db = db_conn.get_database()
        collections = await db.list_collection_names()
        for collection in collections:
            await db.drop_collection(collection)
        print(f"   Cleaned {len(collections)} collections")
        
        repository = PropertyRepository(db_conn)
        
        print("3. Initializing processing pipeline...")
        pipeline = DataProcessingPipeline(config)
        integrator = ProcessingIntegrator(config, repository, pipeline)
        print("   Pipeline initialized")
        
        print("4. Processing property with LLM...")
        async with integrator:
            result = await integrator.process_property({
                "html": html_content,
                "property_id": "E2E-TEST-001"
            }, "phoenix_mls")
            
            print(f"   Processing success: {result.success}")
            if result.success:
                print(f"   Property ID: {result.property_id}")
                if result.property_data:
                    print(f"   Address: {result.property_data.address}")
                    print(f"   Price: ${result.property_data.price:,}")
                    print(f"   Bedrooms: {result.property_data.bedrooms}")
                    print(f"   Bathrooms: {result.property_data.bathrooms}")
                
                print("5. Testing database retrieval...")
                saved = await repository.get_by_id(result.property_id)
                print(f"   Retrieved from DB: {saved is not None}")
                
                if saved:
                    print(f"   DB Address: {saved.get(\"address\", {})}")
                    print(f"   DB Price: ${saved.get(\"current_price\", 0):,}")
                
                print("=== E2E TEST PASSED\! ===")
            else:
                print(f"   Processing failed: {result.error}")
                print("=== E2E TEST FAILED ===")
    
    except Exception as e:
        import traceback
        print(f"Exception: {e}")
        print(traceback.format_exc())
        print("=== E2E TEST ERROR ===")
    finally:
        if "db_conn" in locals():
            await db_conn.close()

asyncio.run(test_e2e())

