"""Test suite for resource monitoring functionality."""

import pytest
import asyncio
from unittest.mock import patch

from phoenix_real_estate.collectors.processing.monitoring import (
    ResourceMonitor,
    ResourceMetrics,
    ResourceLimits,
    AlertLevel
)


class TestResourceMonitor:
    """Test resource monitoring system."""
    
    @pytest.fixture
    def resource_limits(self) -> ResourceLimits:
        """Resource limits for testing."""
        return ResourceLimits(
            max_memory_mb=1024,
            max_cpu_percent=80,
            max_concurrent_requests=10,
            max_queue_size=100,
            alert_thresholds={
                "memory": {"warning": 70, "critical": 90},
                "cpu": {"warning": 60, "critical": 80},
                "queue": {"warning": 50, "critical": 80}
            }
        )
    
    @pytest.fixture
    async def monitor(self, resource_limits) -> ResourceMonitor:
        """Create resource monitor instance."""
        monitor = ResourceMonitor(resource_limits)
        await monitor.start()
        yield monitor
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_memory_monitoring(self, monitor):
        """Test memory usage monitoring."""
        # Get current memory usage
        metrics = await monitor.get_metrics()
        
        assert "memory_mb" in metrics
        assert "memory_percent" in metrics
        assert metrics["memory_mb"] > 0
        assert 0 <= metrics["memory_percent"] <= 100
        
        # Test memory tracking over time
        await monitor.track_operation_start("test_op")
        
        # Simulate memory allocation
        [0] * (10 * 1024 * 1024)  # ~40MB
        
        await monitor.track_operation_end("test_op")
        
        # Check operation metrics
        op_metrics = monitor.get_operation_metrics("test_op")
        assert op_metrics["memory_delta_mb"] >= 0
    
    @pytest.mark.asyncio
    async def test_cpu_monitoring(self, monitor):
        """Test CPU usage monitoring."""
        metrics = await monitor.get_metrics()
        
        assert "cpu_percent" in metrics
        assert 0 <= metrics["cpu_percent"] <= 100
        
        # Test CPU tracking during computation
        await monitor.track_operation_start("cpu_test")
        
        # Simulate CPU-intensive operation
        import hashlib
        for _ in range(1000):
            hashlib.sha256(b"test" * 1000).hexdigest()
        
        await monitor.track_operation_end("cpu_test")
        
        op_metrics = monitor.get_operation_metrics("cpu_test")
        assert "avg_cpu_percent" in op_metrics
        assert op_metrics["duration_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, monitor):
        """Test concurrent request limiting."""
        # Fill up concurrent slots
        operations = []
        for i in range(10):  # Max concurrent is 10
            op_id = f"op_{i}"
            can_proceed = await monitor.check_resource_availability(op_id)
            assert can_proceed is True
            operations.append(op_id)
        
        # 11th request should be denied
        can_proceed = await monitor.check_resource_availability("op_11")
        assert can_proceed is False
        
        # Complete one operation
        await monitor.release_resources(operations[0])
        
        # Now 11th can proceed
        can_proceed = await monitor.check_resource_availability("op_11")
        assert can_proceed is True
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, monitor):
        """Test resource alert generation."""
        alerts = []
        
        # Set up alert callback
        monitor.on_alert(lambda alert: alerts.append(alert))
        
        # Simulate high memory usage
        with patch.object(monitor, '_get_memory_usage', return_value={"percent": 75}):
            await monitor._check_thresholds()
        
        # Should have warning alert
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.WARNING
        assert alerts[0].resource == "memory"
        assert alerts[0].current_value == 75
        
        # Simulate critical CPU usage
        alerts.clear()
        with patch.object(monitor, '_get_cpu_usage', return_value=85):
            await monitor._check_thresholds()
        
        # Should have critical alert
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.CRITICAL
        assert alerts[0].resource == "cpu"
    
    @pytest.mark.asyncio
    async def test_adaptive_batch_sizing(self, monitor):
        """Test dynamic batch size adjustment."""
        # Start with default batch size
        initial_batch_size = monitor.get_recommended_batch_size()
        assert initial_batch_size > 0
        
        # Simulate high resource usage
        with patch.object(monitor, '_get_memory_usage', return_value={"percent": 85}):
            with patch.object(monitor, '_get_cpu_usage', return_value=75):
                new_batch_size = monitor.get_recommended_batch_size()
        
        # Batch size should decrease under load
        assert new_batch_size < initial_batch_size
        
        # Simulate low resource usage
        with patch.object(monitor, '_get_memory_usage', return_value={"percent": 30}):
            with patch.object(monitor, '_get_cpu_usage', return_value=20):
                new_batch_size = monitor.get_recommended_batch_size()
        
        # Batch size should increase when resources available
        assert new_batch_size > initial_batch_size
    
    @pytest.mark.asyncio
    async def test_resource_reservation(self, monitor):
        """Test resource reservation system."""
        # Reserve resources for operation
        reservation_id = await monitor.reserve_resources(
            memory_mb=100,
            cpu_cores=2,
            duration_seconds=10
        )
        
        assert reservation_id is not None
        
        # Check reservation is tracked
        active_reservations = monitor.get_active_reservations()
        assert reservation_id in active_reservations
        assert active_reservations[reservation_id]["memory_mb"] == 100
        
        # Release reservation
        await monitor.release_reservation(reservation_id)
        
        # Check reservation is gone
        active_reservations = monitor.get_active_reservations()
        assert reservation_id not in active_reservations
    
    @pytest.mark.asyncio
    async def test_monitoring_persistence(self, monitor):
        """Test metrics persistence and history."""
        # Collect metrics over time
        for i in range(5):
            await monitor.track_operation_start(f"op_{i}")
            await asyncio.sleep(0.1)
            await monitor.track_operation_end(f"op_{i}")
        
        # Get historical metrics
        history = monitor.get_metrics_history(minutes=1)
        assert len(history) > 0
        
        # Check aggregated stats
        stats = monitor.get_aggregate_stats()
        assert stats["total_operations"] == 5
        assert stats["avg_duration_seconds"] > 0
        assert "peak_memory_mb" in stats
        assert "peak_cpu_percent" in stats
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, resource_limits):
        """Test monitor handles system API failures."""
        monitor = ResourceMonitor(resource_limits)
        
        # Mock psutil failure
        with patch("psutil.virtual_memory", side_effect=Exception("API Error")):
            await monitor.start()
            
            # Should still work with defaults
            metrics = await monitor.get_metrics()
            assert metrics["memory_mb"] == 0  # Default fallback
            assert metrics["status"] == "degraded"


class TestResourceMetrics:
    """Test resource metrics collection."""
    
    def test_metrics_aggregation(self):
        """Test metrics aggregation."""
        metrics = ResourceMetrics()
        
        # Record multiple data points
        for i in range(10):
            metrics.record_datapoint(
                memory_mb=100 + i * 10,
                cpu_percent=20 + i * 5,
                active_operations=i
            )
        
        # Get aggregated stats
        stats = metrics.get_summary()
        assert stats["avg_memory_mb"] == 145  # (100+110+...+190)/10
        assert stats["max_memory_mb"] == 190
        assert stats["avg_cpu_percent"] == 42.5
        assert stats["max_cpu_percent"] == 65
        assert stats["max_concurrent_operations"] == 9
    
    def test_sliding_window(self):
        """Test sliding window for metrics."""
        metrics = ResourceMetrics(window_size=5)
        
        # Fill window
        for i in range(10):
            metrics.record_datapoint(memory_mb=i * 10)
        
        # Should only keep last 5
        assert len(metrics._datapoints) == 5
        assert metrics.get_summary()["avg_memory_mb"] == 70  # (50+60+70+80+90)/5


class TestResourceLimits:
    """Test resource limit enforcement."""
    
    def test_limit_validation(self):
        """Test resource limit validation."""
        limits = ResourceLimits(
            max_memory_mb=1024,
            max_cpu_percent=80,
            max_concurrent_requests=10
        )
        
        # Test memory limit
        assert limits.check_memory_limit(500) is True
        assert limits.check_memory_limit(2000) is False
        
        # Test CPU limit
        assert limits.check_cpu_limit(50) is True
        assert limits.check_cpu_limit(90) is False
        
        # Test concurrent limit
        assert limits.check_concurrent_limit(5) is True
        assert limits.check_concurrent_limit(15) is False
    
    def test_dynamic_adjustment(self):
        """Test dynamic limit adjustment."""
        limits = ResourceLimits(
            max_memory_mb=1024,
            dynamic_adjustment=True
        )
        
        # Simulate system under pressure
        limits.adjust_for_pressure(memory_pressure=0.8)
        
        # Limits should be reduced
        assert limits.effective_memory_limit < 1024
        
        # Simulate system recovery
        limits.adjust_for_pressure(memory_pressure=0.3)
        
        # Limits should increase back
        assert limits.effective_memory_limit > limits.effective_memory_limit


class TestIntegrationWithPipeline:
    """Test integration with processing pipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_resource_awareness(self, monitor):
        """Test pipeline respects resource limits."""
        from phoenix_real_estate.collectors.processing import DataProcessingPipeline
        from phoenix_real_estate.foundation.config import ConfigProvider
        
        config = ConfigProvider()
        pipeline = DataProcessingPipeline(config)
        pipeline._resource_monitor = monitor
        
        # Mock heavy processing
        async def mock_process(content, source):
            # Check resources before processing
            if not await monitor.check_resource_availability(f"process_{id(content)}"):
                raise ResourceError("Insufficient resources")
            
            await asyncio.sleep(0.1)  # Simulate processing
            return {"processed": True}
        
        pipeline.process_html = mock_process
        
        # Process multiple items concurrently
        items = ["content"] * 20
        
        # Should handle resource constraints gracefully
        results = await pipeline.process_batch_html(items, "test_source")
        
        # Some might fail due to resource limits
        successful = sum(1 for r in results if r.is_valid)
        assert successful <= 10  # Max concurrent limit


class ResourceError(Exception):
    """Resource-related error."""
    pass