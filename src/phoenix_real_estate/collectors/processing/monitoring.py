"""Resource monitoring and management for LLM processing."""

import asyncio
import time
import psutil
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Deque
import uuid

from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceAlert:
    """Resource alert information."""

    timestamp: datetime
    level: AlertLevel
    resource: str
    current_value: float
    threshold: float
    message: str


@dataclass
class ResourceLimits:
    """Resource usage limits and thresholds."""

    max_memory_mb: float = 1024
    max_cpu_percent: float = 80
    max_concurrent_requests: int = 10
    max_queue_size: int = 100
    alert_thresholds: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "memory": {"warning": 70, "critical": 90},
            "cpu": {"warning": 60, "critical": 80},
            "queue": {"warning": 50, "critical": 80},
        }
    )
    dynamic_adjustment: bool = True

    @property
    def effective_memory_limit(self) -> float:
        """Get effective memory limit after adjustments."""
        return getattr(self, "_adjusted_memory_limit", self.max_memory_mb)

    def check_memory_limit(self, current_mb: float) -> bool:
        """Check if memory usage is within limits."""
        return current_mb <= self.effective_memory_limit

    def check_cpu_limit(self, current_percent: float) -> bool:
        """Check if CPU usage is within limits."""
        return current_percent <= self.max_cpu_percent

    def check_concurrent_limit(self, current: int) -> bool:
        """Check if concurrent requests are within limits."""
        return current <= self.max_concurrent_requests

    def adjust_for_pressure(self, memory_pressure: float = 0.0, cpu_pressure: float = 0.0) -> None:
        """Dynamically adjust limits based on system pressure."""
        if not self.dynamic_adjustment:
            return

        # Reduce limits under pressure
        if memory_pressure > 0.7:
            self._adjusted_memory_limit = self.max_memory_mb * (1 - memory_pressure * 0.3)
        elif memory_pressure < 0.3:
            self._adjusted_memory_limit = self.max_memory_mb

        logger.debug(f"Adjusted memory limit to {self.effective_memory_limit:.1f} MB")


@dataclass
class ResourceMetrics:
    """Container for resource metrics."""

    window_size: int = 100
    _datapoints: Deque[Dict[str, Any]] = field(default_factory=deque)

    def record_datapoint(
        self, memory_mb: float = 0, cpu_percent: float = 0, active_operations: int = 0, **kwargs
    ) -> None:
        """Record a resource measurement datapoint."""
        datapoint = {
            "timestamp": time.time(),
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "active_operations": active_operations,
            **kwargs,
        }

        self._datapoints.append(datapoint)

        # Maintain window size
        while len(self._datapoints) > self.window_size:
            self._datapoints.popleft()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self._datapoints:
            return {
                "avg_memory_mb": 0,
                "max_memory_mb": 0,
                "avg_cpu_percent": 0,
                "max_cpu_percent": 0,
                "max_concurrent_operations": 0,
            }

        memory_values = [d["memory_mb"] for d in self._datapoints]
        cpu_values = [d["cpu_percent"] for d in self._datapoints]
        operation_values = [d["active_operations"] for d in self._datapoints]

        return {
            "avg_memory_mb": sum(memory_values) / len(memory_values),
            "max_memory_mb": max(memory_values),
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
            "max_cpu_percent": max(cpu_values),
            "max_concurrent_operations": max(operation_values),
        }


class ResourceMonitor:
    """Monitors system resources and provides adaptive control."""

    def __init__(self, limits: ResourceLimits):
        """Initialize resource monitor.

        Args:
            limits: Resource limits configuration
        """
        self.limits = limits
        self.metrics = ResourceMetrics()
        self._process = psutil.Process()

        self._active_operations: Dict[str, Dict[str, Any]] = {}
        self._active_reservations: Dict[str, Dict[str, Any]] = {}
        self._alert_callbacks: List[Callable[[ResourceAlert], None]] = []

        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._degraded_mode = False

        # Batch size optimization
        self._batch_size_history: Deque[tuple[int, float]] = deque(maxlen=10)
        self._current_batch_size = 10

    async def start(self) -> None:
        """Start resource monitoring."""
        if self._monitoring_task:
            return

        self._stop_event.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Resource monitoring started")

    async def stop(self) -> None:
        """Stop resource monitoring."""
        if not self._monitoring_task:
            return

        self._stop_event.set()
        await self._monitoring_task
        self._monitoring_task = None
        logger.info("Resource monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Collect metrics
                metrics = await self.get_metrics()

                # Record datapoint
                self.metrics.record_datapoint(
                    memory_mb=metrics["memory_mb"],
                    cpu_percent=metrics["cpu_percent"],
                    active_operations=len(self._active_operations),
                )

                # Check thresholds
                await self._check_thresholds()

                # Adjust limits if needed
                if self.limits.dynamic_adjustment:
                    memory_pressure = metrics["memory_percent"] / 100
                    cpu_pressure = metrics["cpu_percent"] / 100
                    self.limits.adjust_for_pressure(memory_pressure, cpu_pressure)

                # Sleep interval
                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self._degraded_mode = True
                await asyncio.sleep(10)  # Longer sleep on error

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current resource metrics."""
        try:
            # Memory metrics
            memory_info = self._get_memory_usage()

            # CPU metrics
            cpu_percent = self._get_cpu_usage()

            # Process-specific metrics
            process_memory = self._process.memory_info()

            metrics = {
                "memory_mb": memory_info["mb"],
                "memory_percent": memory_info["percent"],
                "cpu_percent": cpu_percent,
                "process_memory_mb": process_memory.rss / 1024 / 1024,
                "active_operations": len(self._active_operations),
                "active_reservations": len(self._active_reservations),
                "queue_size": sum(1 for op in self._active_operations.values() if op.get("queued")),
                "status": "degraded" if self._degraded_mode else "healthy",
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                "memory_mb": 0,
                "memory_percent": 0,
                "cpu_percent": 0,
                "process_memory_mb": 0,
                "active_operations": len(self._active_operations),
                "active_reservations": 0,
                "queue_size": 0,
                "status": "degraded",
            }

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        try:
            mem = psutil.virtual_memory()
            return {"mb": mem.used / 1024 / 1024, "percent": mem.percent}
        except Exception:
            return {"mb": 0, "percent": 0}

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0

    async def _check_thresholds(self) -> None:
        """Check resource thresholds and generate alerts."""
        metrics = await self.get_metrics()

        # Check memory thresholds
        memory_percent = metrics["memory_percent"]
        for level, threshold in self.limits.alert_thresholds["memory"].items():
            if memory_percent >= threshold:
                alert = ResourceAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.WARNING if level == "warning" else AlertLevel.CRITICAL,
                    resource="memory",
                    current_value=memory_percent,
                    threshold=threshold,
                    message=f"Memory usage at {memory_percent:.1f}% (threshold: {threshold}%)",
                )
                self._notify_alert(alert)

        # Check CPU thresholds
        cpu_percent = metrics["cpu_percent"]
        for level, threshold in self.limits.alert_thresholds["cpu"].items():
            if cpu_percent >= threshold:
                alert = ResourceAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.WARNING if level == "warning" else AlertLevel.CRITICAL,
                    resource="cpu",
                    current_value=cpu_percent,
                    threshold=threshold,
                    message=f"CPU usage at {cpu_percent:.1f}% (threshold: {threshold}%)",
                )
                self._notify_alert(alert)

    def _notify_alert(self, alert: ResourceAlert) -> None:
        """Notify registered callbacks about an alert."""
        logger.warning(f"Resource alert: {alert.message}")

        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def on_alert(self, callback: Callable[[ResourceAlert], None]) -> None:
        """Register an alert callback."""
        self._alert_callbacks.append(callback)

    async def check_resource_availability(self, operation_id: str) -> bool:
        """Check if resources are available for an operation."""
        # Check concurrent limit
        if len(self._active_operations) >= self.limits.max_concurrent_requests:
            logger.debug(f"Operation {operation_id} denied: concurrent limit reached")
            return False

        # Check memory availability
        metrics = await self.get_metrics()
        if metrics["memory_percent"] > 90:
            logger.debug(f"Operation {operation_id} denied: high memory usage")
            return False

        # Check CPU availability
        if metrics["cpu_percent"] > 90:
            logger.debug(f"Operation {operation_id} denied: high CPU usage")
            return False

        # Track operation
        self._active_operations[operation_id] = {
            "start_time": time.time(),
            "memory_start": metrics["memory_mb"],
        }

        return True

    async def release_resources(self, operation_id: str) -> None:
        """Release resources for a completed operation."""
        if operation_id in self._active_operations:
            del self._active_operations[operation_id]
            logger.debug(f"Released resources for operation {operation_id}")

    async def track_operation_start(self, operation_id: str) -> None:
        """Track the start of an operation."""
        metrics = await self.get_metrics()
        self._active_operations[operation_id] = {
            "start_time": time.time(),
            "memory_start": metrics["memory_mb"],
            "cpu_samples": [metrics["cpu_percent"]],
        }

    async def track_operation_end(self, operation_id: str) -> None:
        """Track the end of an operation."""
        if operation_id not in self._active_operations:
            return

        metrics = await self.get_metrics()
        operation = self._active_operations[operation_id]

        operation["end_time"] = time.time()
        operation["memory_end"] = metrics["memory_mb"]
        operation["duration_seconds"] = operation["end_time"] - operation["start_time"]
        operation["memory_delta_mb"] = operation["memory_end"] - operation["memory_start"]

        # Store for history
        self._update_batch_size_history(operation)

    def get_operation_metrics(self, operation_id: str) -> Dict[str, Any]:
        """Get metrics for a specific operation."""
        if operation_id not in self._active_operations:
            return {}

        operation = self._active_operations[operation_id]

        result = {
            "duration_seconds": operation.get(
                "duration_seconds", time.time() - operation["start_time"]
            ),
            "memory_delta_mb": operation.get("memory_delta_mb", 0),
        }

        if "cpu_samples" in operation and operation["cpu_samples"]:
            result["avg_cpu_percent"] = sum(operation["cpu_samples"]) / len(
                operation["cpu_samples"]
            )

        return result

    def get_recommended_batch_size(self) -> int:
        """Get recommended batch size based on current resources."""
        metrics_summary = self.metrics.get_summary()

        # Base batch size
        base_size = 10

        # Adjust based on memory usage
        avg_memory = metrics_summary["avg_memory_mb"]
        max_memory = self.limits.max_memory_mb
        memory_factor = 1 - (avg_memory / max_memory) if max_memory > 0 else 0.5

        # Adjust based on CPU usage
        avg_cpu = metrics_summary["avg_cpu_percent"]
        cpu_factor = 1 - (avg_cpu / 100)

        # Calculate recommended size
        recommended = int(base_size * memory_factor * cpu_factor)

        # Apply bounds
        recommended = max(1, min(recommended, 50))

        # Consider history
        if self._batch_size_history:
            # If recent batches were successful, can increase
            recent_success = all(success for _, success in self._batch_size_history[-3:])
            if recent_success:
                recommended = min(recommended + 2, 50)

        self._current_batch_size = recommended
        return recommended

    def _update_batch_size_history(self, operation: Dict[str, Any]) -> None:
        """Update batch size history based on operation performance."""
        duration = operation.get("duration_seconds", 0)
        memory_delta = operation.get("memory_delta_mb", 0)

        # Consider operation successful if it completed reasonably fast
        # and didn't use excessive memory
        success = duration < 5.0 and memory_delta < 100

        self._batch_size_history.append((self._current_batch_size, success))

    async def reserve_resources(
        self, memory_mb: float, cpu_cores: int, duration_seconds: float
    ) -> str:
        """Reserve resources for a future operation."""
        reservation_id = str(uuid.uuid4())

        self._active_reservations[reservation_id] = {
            "memory_mb": memory_mb,
            "cpu_cores": cpu_cores,
            "duration_seconds": duration_seconds,
            "created_at": time.time(),
        }

        # Clean up expired reservations
        await self._cleanup_reservations()

        return reservation_id

    async def release_reservation(self, reservation_id: str) -> None:
        """Release a resource reservation."""
        if reservation_id in self._active_reservations:
            del self._active_reservations[reservation_id]

    async def _cleanup_reservations(self) -> None:
        """Clean up expired reservations."""
        current_time = time.time()
        expired = []

        for res_id, reservation in self._active_reservations.items():
            if current_time - reservation["created_at"] > reservation["duration_seconds"]:
                expired.append(res_id)

        for res_id in expired:
            del self._active_reservations[res_id]

    def get_active_reservations(self) -> Dict[str, Dict[str, Any]]:
        """Get active resource reservations."""
        return dict(self._active_reservations)

    def get_metrics_history(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get metrics history for the specified duration."""
        cutoff_time = time.time() - (minutes * 60)

        history = []
        for datapoint in self.metrics._datapoints:
            if datapoint["timestamp"] >= cutoff_time:
                history.append(datapoint)

        return history

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        summary = self.metrics.get_summary()

        # Add operation statistics
        total_operations = len(self._active_operations)
        completed_operations = sum(1 for op in self._active_operations.values() if "end_time" in op)

        if completed_operations > 0:
            durations = [
                op["duration_seconds"]
                for op in self._active_operations.values()
                if "duration_seconds" in op
            ]
            avg_duration = sum(durations) / len(durations) if durations else 0
        else:
            avg_duration = 0

        return {
            **summary,
            "total_operations": total_operations,
            "completed_operations": completed_operations,
            "avg_duration_seconds": avg_duration,
            "peak_memory_mb": summary["max_memory_mb"],
            "peak_cpu_percent": summary["max_cpu_percent"],
        }


class ProcessingMonitor:
    """Simple processing monitor for compatibility."""

    def __init__(self):
        """Initialize processing monitor."""
        self.start_time = time.time()
        self.processed_count = 0
        self.error_count = 0

    def record_success(self):
        """Record a successful processing."""
        self.processed_count += 1

    def record_error(self):
        """Record a processing error."""
        self.error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": self.processed_count / (self.processed_count + self.error_count)
            if (self.processed_count + self.error_count) > 0
            else 0,
        }
