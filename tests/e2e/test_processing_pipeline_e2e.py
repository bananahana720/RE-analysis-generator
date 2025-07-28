"""End-to-end tests for the LLM processing pipeline.

These tests validate the complete data flow from raw HTML/JSON input
through LLM extraction, validation, and database storage.

Test modes:
- Mock mode: Uses mocked Ollama client for fast, deterministic tests
- Real mode: Uses actual Ollama service for integration validation

Set E2E_MODE=real to test with actual Ollama service.
"""

import asyncio
import time

import pytest

from phoenix_real_estate.collectors.processing.pipeline import ProcessingResult
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError


@pytest.mark.e2e
@pytest.mark.asyncio
class TestProcessingPipelineE2E:
    """End-to-end tests for the LLM processing pipeline."""
    
    @pytest.mark.parametrize("strict_validation", [True, False])
    async def test_single_html_processing(
        self,
        processing_pipeline,
        sample_phoenix_mls_html,
        expected_property_fields,
        e2e_mode,
        performance_tracker,
        strict_validation
    ):
        """Test processing a single Phoenix MLS HTML property."""
        # Arrange
        start_time = time.time()
        
        # Act
        async with processing_pipeline:
            result = await processing_pipeline.process_html(
                sample_phoenix_mls_html,
                "phoenix_mls",
                timeout=30,
                strict_validation=strict_validation
            )
        
        # Record performance
        duration = time.time() - start_time
        performance_tracker.record("single_html_processing", duration, result.is_valid)
        
        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.source == "phoenix_mls"
        assert result.processing_time > 0
        
        if strict_validation:
            assert result.is_valid, f"Processing failed: {result.error}"
            assert result.property_data is not None
            assert result.validation_result is not None
            
            # Check property data
            property_data = result.property_data
            assert property_data.address == "123 Test Street"
            assert property_data.city == "Phoenix"
            assert property_data.state == "AZ"
            assert property_data.zip_code == "85031"
            assert property_data.price == 425000
            assert property_data.bedrooms == 4
            assert property_data.bathrooms == 3.0
            assert property_data.square_feet == 2200
            
            # Check validation
            assert result.validation_result.is_valid
            assert result.validation_result.confidence_score >= 0.7
            assert len(result.validation_result.errors) == 0
        else:
            # With relaxed validation, should still process but may have warnings
            assert result.property_data is not None
    
    @pytest.mark.parametrize("strict_validation", [True, False])
    async def test_single_json_processing(
        self,
        processing_pipeline,
        sample_maricopa_json,
        expected_property_fields,
        e2e_mode,
        performance_tracker,
        strict_validation
    ):
        """Test processing a single Maricopa County JSON property."""
        # Arrange
        start_time = time.time()
        
        # Act
        async with processing_pipeline:
            result = await processing_pipeline.process_json(
                sample_maricopa_json,
                "maricopa_county",
                timeout=30,
                strict_validation=strict_validation
            )
        
        # Record performance
        duration = time.time() - start_time
        performance_tracker.record("single_json_processing", duration, result.is_valid)
        
        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.source == "maricopa_county"
        assert result.processing_time > 0
        
        if strict_validation:
            assert result.is_valid, f"Processing failed: {result.error}"
            assert result.property_data is not None
            
            # Check property data
            property_data = result.property_data
            assert property_data.address == "456 Demo Avenue"
            assert property_data.city == "Phoenix"
            assert property_data.state == "AZ"
            assert property_data.zip_code == "85033"
            assert property_data.price == 385000
            assert property_data.bedrooms == 3
            assert property_data.bathrooms == 2.5
            assert property_data.square_feet == 1850
            assert property_data.year_built == 2015
    
    async def test_batch_html_processing(
        self,
        processing_pipeline,
        test_data_factory,
        performance_tracker
    ):
        """Test batch processing of multiple HTML properties."""
        # Arrange
        html_contents = [
            test_data_factory.create_phoenix_mls_html(
                address=f"{i} Batch St",
                price=300000 + (i * 10000),
                beds=3 + (i % 3),
                mls_number=f"675432{i}"
            )
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Act
        async with processing_pipeline:
            results = await processing_pipeline.process_batch_html(
                html_contents,
                "phoenix_mls",
                timeout=30,
                strict_validation=True
            )
        
        # Record performance
        duration = time.time() - start_time
        success_count = sum(1 for r in results if r.is_valid)
        performance_tracker.record(
            "batch_html_processing",
            duration,
            success_count == len(html_contents)
        )
        
        # Assert
        assert len(results) == 5
        assert all(isinstance(r, ProcessingResult) for r in results)
        assert all(r.source == "phoenix_mls" for r in results)
        
        # Check at least 80% success rate
        assert success_count >= 4, f"Only {success_count}/5 properties processed successfully"
        
        # Verify batch processing was concurrent (should be faster than sequential)
        avg_time_per_property = duration / len(html_contents)
        assert avg_time_per_property < 10, "Batch processing seems too slow"
    
    async def test_batch_json_processing(
        self,
        processing_pipeline,
        test_data_factory,
        performance_tracker
    ):
        """Test batch processing of multiple JSON properties."""
        # Arrange
        json_items = [
            test_data_factory.create_maricopa_json(
                parcel=f"123-45-{i:03d}",
                address=f"{i} Batch Ave",
                value=350000 + (i * 15000),
                beds=2 + (i % 4)
            )
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Act
        async with processing_pipeline:
            results = await processing_pipeline.process_batch_json(
                json_items,
                "maricopa_county",
                timeout=30,
                strict_validation=True
            )
        
        # Record performance
        duration = time.time() - start_time
        success_count = sum(1 for r in results if r.is_valid)
        performance_tracker.record(
            "batch_json_processing",
            duration,
            success_count == len(json_items)
        )
        
        # Assert
        assert len(results) == 5
        assert all(isinstance(r, ProcessingResult) for r in results)
        assert all(r.source == "maricopa_county" for r in results)
        
        # Check success rate
        assert success_count >= 4, f"Only {success_count}/5 properties processed successfully"
    
    async def test_mixed_batch_processing(
        self,
        processing_pipeline,
        sample_batch_data,
        performance_tracker
    ):
        """Test processing mixed HTML and JSON content in one batch."""
        # Arrange
        start_time = time.time()
        
        # Act
        async with processing_pipeline:
            results = await processing_pipeline.process_mixed_batch(
                sample_batch_data,
                timeout=30,
                strict_validation=True
            )
        
        # Record performance
        duration = time.time() - start_time
        success_count = sum(1 for r in results if r.is_valid)
        performance_tracker.record(
            "mixed_batch_processing",
            duration,
            success_count == len(sample_batch_data)
        )
        
        # Assert
        assert len(results) == 3
        
        # Check each result
        html_results = [r for r in results if r.source == "phoenix_mls"]
        json_results = [r for r in results if r.source == "maricopa_county"]
        
        assert len(html_results) == 2
        assert len(json_results) == 1
        
        # Verify at least one from each source succeeded
        assert any(r.is_valid for r in html_results), "No Phoenix MLS properties processed successfully"
        assert any(r.is_valid for r in json_results), "No Maricopa properties processed successfully"
    
    async def test_concurrent_processing_limits(
        self,
        processing_pipeline,
        test_data_factory,
        performance_tracker
    ):
        """Test that concurrent processing respects configured limits."""
        # Arrange
        # Create more items than max concurrent limit
        html_contents = [
            test_data_factory.create_phoenix_mls_html(
                address=f"{i} Concurrent St",
                mls_number=f"675433{i}"
            )
            for i in range(10)
        ]
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent_observed = 0
        lock = asyncio.Lock()
        
        # Monkey-patch to track concurrency
        original_process = processing_pipeline.process_html
        
        async def tracked_process(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent_observed
            
            async with lock:
                concurrent_count += 1
                max_concurrent_observed = max(max_concurrent_observed, concurrent_count)
            
            try:
                result = await original_process(*args, **kwargs)
                return result
            finally:
                async with lock:
                    concurrent_count -= 1
        
        processing_pipeline.process_html = tracked_process
        
        # Act
        async with processing_pipeline:
            results = await processing_pipeline.process_batch_html(
                html_contents,
                "phoenix_mls",
                timeout=30
            )
        
        # Assert
        assert len(results) == 10
        # Should respect MAX_CONCURRENT_PROCESSING setting (3 from conftest)
        assert max_concurrent_observed <= 3, f"Max concurrent exceeded: {max_concurrent_observed}"
        assert max_concurrent_observed > 1, "No concurrency observed"
    
    async def test_error_handling_invalid_html(
        self,
        processing_pipeline,
        performance_tracker
    ):
        """Test error handling for invalid HTML content."""
        # Arrange
        invalid_html = "<div>Incomplete HTML with no property data"
        
        # Act
        async with processing_pipeline:
            with pytest.raises(ProcessingError):
                await processing_pipeline.process_html(
                    invalid_html,
                    "phoenix_mls",
                    timeout=10,
                    strict_validation=True
                )
    
    async def test_error_handling_invalid_source(
        self,
        processing_pipeline
    ):
        """Test error handling for invalid data source."""
        # Act & Assert
        async with processing_pipeline:
            with pytest.raises(ValueError, match="Unsupported source"):
                await processing_pipeline.process_html(
                    "<html></html>",
                    "invalid_source",
                    timeout=10
                )
    
    async def test_timeout_handling(
        self,
        processing_pipeline,
        mock_ollama_client,
        e2e_mode
    ):
        """Test timeout handling in processing."""
        if e2e_mode == "real":
            pytest.skip("Timeout test only runs in mock mode")
        
        # Arrange
        # Make extraction take longer than timeout
        async def slow_extract(*args, **kwargs):
            await asyncio.sleep(5)
            return {"address": "timeout test"}
        
        mock_ollama_client.extract.side_effect = slow_extract
        
        # Act & Assert
        async with processing_pipeline:
            with pytest.raises(asyncio.TimeoutError):
                await processing_pipeline.process_html(
                    "<html>test</html>",
                    "phoenix_mls",
                    timeout=1  # 1 second timeout
                )
    
    async def test_metrics_tracking(
        self,
        processing_pipeline,
        sample_batch_data,
        performance_tracker
    ):
        """Test that pipeline tracks metrics correctly."""
        # Arrange
        async with processing_pipeline:
            # Clear metrics first
            processing_pipeline.clear_metrics()
            
            # Process batch
            await processing_pipeline.process_mixed_batch(
                sample_batch_data,
                timeout=30
            )
            
            # Get metrics
            metrics = processing_pipeline.get_metrics()
        
        # Assert
        assert metrics['total_processed'] == 3
        assert metrics['successful'] >= 1
        assert metrics['failed'] == 3 - metrics['successful']
        assert metrics['success_rate'] == metrics['successful'] / 3
        assert metrics['average_processing_time'] > 0
        assert metrics['average_confidence'] >= 0
        assert isinstance(metrics['errors_by_type'], dict)
    
    @pytest.mark.slow
    async def test_performance_benchmarks(
        self,
        processing_pipeline,
        test_data_factory,
        performance_tracker,
        e2e_mode
    ):
        """Test performance benchmarks for the pipeline."""
        # Skip in real mode as it's slower
        if e2e_mode == "real":
            pytest.skip("Performance benchmark runs only in mock mode")
        
        # Arrange
        test_sizes = [1, 5, 10, 20]
        results_summary = {}
        
        async with processing_pipeline:
            for size in test_sizes:
                # Create test data
                html_contents = [
                    test_data_factory.create_phoenix_mls_html(
                        address=f"{i} Perf Test St",
                        mls_number=f"6754{i:03d}"
                    )
                    for i in range(size)
                ]
                
                # Process and measure
                start_time = time.time()
                results = await processing_pipeline.process_batch_html(
                    html_contents,
                    "phoenix_mls",
                    timeout=30
                )
                duration = time.time() - start_time
                
                # Calculate metrics
                success_count = sum(1 for r in results if r.is_valid)
                avg_time = duration / size
                
                results_summary[size] = {
                    'total_time': duration,
                    'avg_time_per_property': avg_time,
                    'success_rate': success_count / size,
                    'properties_per_second': size / duration
                }
                
                # Performance assertions
                assert avg_time < 2.0, f"Processing too slow: {avg_time}s per property"
                assert success_count >= size * 0.8, f"Success rate too low: {success_count}/{size}"
        
        # Log performance summary
        print("\nPerformance Benchmark Results:")
        for size, metrics in results_summary.items():
            print(f"  Batch size {size}:")
            print(f"    - Total time: {metrics['total_time']:.2f}s")
            print(f"    - Avg per property: {metrics['avg_time_per_property']:.2f}s")
            print(f"    - Properties/sec: {metrics['properties_per_second']:.2f}")
            print(f"    - Success rate: {metrics['success_rate']*100:.1f}%")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestProcessingIntegratorE2E:
    """End-to-end tests for the ProcessingIntegrator."""
    
    async def test_integrator_single_property_flow(
        self,
        processing_integrator,
        sample_phoenix_mls_html,
        test_repository,
        performance_tracker
    ):
        """Test complete flow from HTML to database storage."""
        # Arrange
        property_data = {
            "html": sample_phoenix_mls_html,
            "property_id": "TEST-MLS-001"
        }
        
        start_time = time.time()
        
        # Act
        async with processing_integrator:
            result = await processing_integrator.process_property(
                property_data,
                "phoenix_mls"
            )
        
        # Record performance
        duration = time.time() - start_time
        performance_tracker.record("integrator_single_flow", duration, result.success)
        
        # Assert
        assert result.success
        assert result.property_data is not None
        assert result.saved_to_db
        
        # Verify in database
        saved_property = await test_repository.get_by_id(result.property_id)
        assert saved_property is not None
        assert saved_property['address']['street'] == "123 Test Street"
        assert saved_property['current_price'] == 425000
    
    async def test_integrator_batch_processing(
        self,
        processing_integrator,
        test_data_factory,
        test_repository,
        performance_tracker
    ):
        """Test batch processing through integrator."""
        # Arrange
        batch_data = [
            {
                "html": test_data_factory.create_phoenix_mls_html(
                    address=f"{i} Integration St",
                    mls_number=f"INT{i:03d}"
                ),
                "property_id": f"INT-{i:03d}"
            }
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Act
        async with processing_integrator:
            batch_result = await processing_integrator.process_batch(
                batch_data,
                "phoenix_mls"
            )
        
        # Record performance
        duration = time.time() - start_time
        performance_tracker.record(
            "integrator_batch_processing",
            duration,
            batch_result.successful == len(batch_data)
        )
        
        # Assert
        assert batch_result.total_processed == 5
        assert batch_result.successful >= 4
        assert batch_result.processing_time > 0
        
        # Verify database storage
        for result in batch_result.results:
            if result.success:
                saved = await test_repository.get_by_id(result.property_id)
                assert saved is not None
    
    async def test_integrator_metrics(
        self,
        processing_integrator,
        sample_batch_data
    ):
        """Test integrator metrics tracking."""
        # Arrange
        async with processing_integrator:
            # Clear metrics
            processing_integrator.clear_metrics()
            
            # Process some data
            for item in sample_batch_data:
                await processing_integrator.process_property(
                    item,
                    item['source']
                )
            
            # Get metrics
            metrics = processing_integrator.get_metrics()
        
        # Assert
        assert metrics['total_processed'] == 3
        assert metrics['successful'] >= 1
        assert metrics['saved_to_db'] >= metrics['successful']
        assert 'phoenix_mls' in metrics['sources']
        assert 'maricopa_county' in metrics['sources']
    
    @pytest.mark.slow
    async def test_integrator_error_recovery(
        self,
        processing_integrator,
        test_data_factory
    ):
        """Test integrator's error recovery capabilities."""
        # Arrange
        # Mix valid and invalid data
        mixed_data = [
            {
                "html": test_data_factory.create_phoenix_mls_html(),
                "property_id": "VALID-001"
            },
            {
                "html": "<invalid>no data here</invalid>",
                "property_id": "INVALID-001"
            },
            {
                "html": test_data_factory.create_phoenix_mls_html(
                    address="789 Recovery Rd"
                ),
                "property_id": "VALID-002"
            }
        ]
        
        # Act
        async with processing_integrator:
            batch_result = await processing_integrator.process_batch(
                mixed_data,
                "phoenix_mls"
            )
        
        # Assert
        assert batch_result.total_processed == 3
        assert batch_result.successful >= 2  # Valid ones should succeed
        assert batch_result.failed >= 1  # Invalid one should fail
        assert len(batch_result.errors) >= 1
        
        # Verify valid properties were saved despite errors
        valid_results = [r for r in batch_result.results if r.success]
        assert len(valid_results) >= 2


@pytest.mark.e2e
async def test_complete_e2e_workflow(
    test_config,
    test_repository,
    test_data_factory,
    performance_tracker,
    e2e_mode
):
    """Test the complete end-to-end workflow from collection to storage."""
    # This test simulates the full production workflow
    
    # 1. Initialize pipeline and integrator
    from phoenix_real_estate.collectors.processing.pipeline import DataProcessingPipeline
    from phoenix_real_estate.orchestration import ProcessingIntegrator
    
    pipeline = DataProcessingPipeline(test_config)
    integrator = ProcessingIntegrator(test_config, test_repository, pipeline)
    
    async with integrator:
        # 2. Simulate collecting data from multiple sources
        phoenix_mls_data = [
            {
                "html": test_data_factory.create_phoenix_mls_html(
                    address=f"{i} E2E Street",
                    zip_code="85031",
                    price=300000 + (i * 25000),
                    mls_number=f"E2E{i:03d}"
                ),
                "property_id": f"E2E-MLS-{i:03d}"
            }
            for i in range(3)
        ]
        
        maricopa_data = [
            {
                "json": test_data_factory.create_maricopa_json(
                    parcel=f"E2E-{i:03d}",
                    address=f"{i} E2E Avenue",
                    zip_code="85033",
                    value=350000 + (i * 20000)
                ),
                "property_id": f"E2E-MC-{i:03d}"
            }
            for i in range(2)
        ]
        
        # 3. Process all data
        all_results = []
        
        # Process Phoenix MLS data
        for data in phoenix_mls_data:
            result = await integrator.process_property(data, "phoenix_mls")
            all_results.append(result)
        
        # Process Maricopa data
        for data in maricopa_data:
            result = await integrator.process_property(data, "maricopa_county")
            all_results.append(result)
        
        # 4. Verify results
        successful = sum(1 for r in all_results if r.success)
        assert successful >= 4, f"Only {successful}/5 properties processed successfully"
        
        # 5. Query database to verify storage
        all_properties = await test_repository.get_all(limit=10)
        assert len(all_properties) >= successful
        
        # 6. Test search functionality
        phoenix_properties = await test_repository.find_by_city("Phoenix")
        assert len(phoenix_properties) >= successful
        
        zip_31_properties = await test_repository.find_by_zip("85031")
        zip_33_properties = await test_repository.find_by_zip("85033")
        assert len(zip_31_properties) >= 1
        assert len(zip_33_properties) >= 1
        
        # 7. Get final metrics
        metrics = integrator.get_metrics()
        print("\nE2E Workflow Metrics:")
        print(f"  Total processed: {metrics['total_processed']}")
        print(f"  Successful: {metrics['successful']}")
        print(f"  Success rate: {metrics['success_rate']*100:.1f}%")
        print(f"  Avg processing time: {metrics['average_processing_time']:.2f}s")
        print(f"  Sources: {metrics['sources']}")


# Performance summary fixture
@pytest.fixture(scope="session", autouse=True)
def performance_summary(request, performance_tracker):
    """Print performance summary at end of test session."""
    def print_summary():
        summary = performance_tracker.get_summary()
        if summary:
            print("\n" + "="*60)
            print("E2E TEST PERFORMANCE SUMMARY")
            print("="*60)
            print(f"Total operations: {summary['total_operations']}")
            print(f"Successful: {summary['successful']}")
            print(f"Failed: {summary['failed']}")
            print(f"Average duration: {summary['avg_duration']:.2f}s")
            print(f"Min duration: {summary['min_duration']:.2f}s")
            print(f"Max duration: {summary['max_duration']:.2f}s")
            print(f"Total duration: {summary['total_duration']:.2f}s")
            print("="*60)
    
    request.addfinalizer(print_summary)