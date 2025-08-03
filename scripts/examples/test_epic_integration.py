"""Example script demonstrating Epic 1 and Epic 2 integration.

This script shows how to use the ProcessingIntegrator to:
1. Collect data from Maricopa API or Phoenix MLS
2. Process it through the LLM pipeline
3. Save validated results to the database
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phoenix_real_estate.foundation import ConfigProvider, PropertyRepository
from phoenix_real_estate.collectors.maricopa.collector import MaricopaAPICollector
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from phoenix_real_estate.orchestration import ProcessingIntegrator, IntegrationMode


async def test_maricopa_integration():
    """Test integration with Maricopa County API."""
    print("\n=== Testing Maricopa County Integration ===")

    # Initialize components
    config = ConfigProvider()
    repository = PropertyRepository(config)

    # Create integrator
    async with ProcessingIntegrator(config, repository) as integrator:
        # Create Maricopa collector
        collector = MaricopaAPICollector(config, repository)

        # Test single property processing
        print("\n1. Testing single property processing...")
        result = await integrator.process_maricopa_property(
            collector,
            property_id="12345",  # Example property ID
        )

        print(f"   - Success: {result.success}")
        print(f"   - Property ID: {result.property_id}")
        print(f"   - Saved to DB: {result.saved_to_db}")
        print(f"   - Processing time: {result.processing_time:.2f}s")
        if result.error:
            print(f"   - Error: {result.error}")

        # Test batch processing
        print("\n2. Testing batch processing for ZIP codes...")
        batch_result = await integrator.process_maricopa_batch(
            collector,
            zip_codes=["85031", "85033"],
            max_properties=5,  # Limit for testing
        )

        print(f"   - Total processed: {batch_result.total_processed}")
        print(f"   - Successful: {batch_result.successful}")
        print(f"   - Failed: {batch_result.failed}")
        print(f"   - Processing time: {batch_result.processing_time:.2f}s")

        # Show metrics
        print("\n3. Integration metrics:")
        metrics = integrator.get_metrics()
        for key, value in metrics.items():
            print(f"   - {key}: {value}")


async def test_phoenix_mls_integration():
    """Test integration with Phoenix MLS scraper."""
    print("\n=== Testing Phoenix MLS Integration ===")

    # Initialize components
    config = ConfigProvider()
    repository = PropertyRepository(config)

    # Load proxy configuration
    proxy_config = config.get_typed("proxies", dict, default={})

    # Create integrator
    async with ProcessingIntegrator(config, repository) as integrator:
        # Create Phoenix MLS scraper
        scraper_config = {
            "base_url": "https://www.phoenixmlssearch.com",
            "timeout": 30,
            "max_retries": 3,
        }
        scraper = PhoenixMLSScraper(scraper_config, proxy_config)

        # Initialize scraper
        await scraper.initialize_browser()

        try:
            # Test single property processing
            print("\n1. Testing single MLS property processing...")
            result = await integrator.process_phoenix_mls_property(
                scraper,
                property_id="MLS123456",  # Example MLS number
            )

            print(f"   - Success: {result.success}")
            print(f"   - Property ID: {result.property_id}")
            print(f"   - Saved to DB: {result.saved_to_db}")
            print(f"   - Processing time: {result.processing_time:.2f}s")
            if result.error:
                print(f"   - Error: {result.error}")

        finally:
            # Cleanup scraper
            await scraper.close()


async def test_streaming_mode():
    """Test streaming mode processing."""
    print("\n=== Testing Streaming Mode ===")

    # Initialize components
    config = ConfigProvider()
    repository = PropertyRepository(config)

    # Create integrator
    async with ProcessingIntegrator(config, repository) as integrator:
        # Create collector with streaming support
        collector = MaricopaAPICollector(config, repository)

        # Mock streaming method for demonstration
        async def mock_stream():
            """Mock stream generator."""
            for i in range(3):
                yield {
                    "parcel_number": f"stream_{i}",
                    "property_address": f"{i} Streaming Ave, Phoenix, AZ 85001",
                    "assessed_value": 200000 + (i * 10000),
                }

        # Add streaming method to collector
        collector.stream_properties = mock_stream

        print("\nProcessing properties in streaming mode...")
        count = 0
        async for result in integrator.process_stream(collector, mode=IntegrationMode.STREAMING):
            count += 1
            print(f"\n   Property {count}:")
            print(f"   - Property ID: {result.property_id}")
            print(f"   - Success: {result.success}")
            print(f"   - Saved: {result.saved_to_db}")

        print(f"\nTotal streamed: {count} properties")


async def main():
    """Run all integration tests."""
    try:
        # Test Maricopa integration
        await test_maricopa_integration()

        # Test Phoenix MLS integration (optional, requires proxy setup)
        # await test_phoenix_mls_integration()

        # Test streaming mode
        await test_streaming_mode()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("Phoenix Real Estate Epic Integration Demo")
    print("=" * 50)
    asyncio.run(main())
