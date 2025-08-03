"""Enhanced health check endpoints for comprehensive system monitoring."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import psutil
from aiohttp import web

from phoenix_real_estate.foundation import get_logger
from phoenix_real_estate.foundation.database import DatabaseConnection
from phoenix_real_estate.collectors.processing.llm_client import OllamaClient
from phoenix_real_estate.collectors.processing.monitoring import ResourceMonitor

logger = get_logger(__name__)


class HealthCheckService:
    """Comprehensive health check service with detailed component status."""

    def __init__(
        self,
        db_client: Optional[DatabaseConnection] = None,
        ollama_client: Optional[OllamaClient] = None,
        resource_monitor: Optional[ResourceMonitor] = None,
        processing_queue: Optional[asyncio.Queue] = None,
    ):
        """Initialize health check service."""
        self.db_client = db_client
        self.ollama_client = ollama_client
        self.resource_monitor = resource_monitor
        self.processing_queue = processing_queue
        self.start_time = time.time()

        # Track component health history
        self.health_history: Dict[str, List[Dict[str, Any]]] = {
            "database": [],
            "ollama": [],
            "queue": [],
            "memory": [],
            "cpu": [],
        }
        self.max_history_size = 100

    def _add_health_record(self, component: str, healthy: bool, details: str) -> None:
        """Add a health record to history."""
        record = {"timestamp": datetime.now().isoformat(), "healthy": healthy, "details": details}

        if component not in self.health_history:
            self.health_history[component] = []

        self.health_history[component].append(record)

        # Maintain history size
        if len(self.health_history[component]) > self.max_history_size:
            self.health_history[component].pop(0)

    def _calculate_health_score(self, component: str, window_minutes: int = 5) -> float:
        """Calculate health score based on recent history."""
        if component not in self.health_history:
            return 1.0

        history = self.health_history[component]
        if not history:
            return 1.0

        # Filter recent records
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_records = [
            r for r in history if datetime.fromisoformat(r["timestamp"]) > cutoff_time
        ]

        if not recent_records:
            return 1.0

        # Calculate health score
        healthy_count = sum(1 for r in recent_records if r["healthy"])
        return healthy_count / len(recent_records)

    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connection and performance."""
        start_time = time.time()

        try:
            if not self.db_client:
                return {
                    "status": "unavailable",
                    "message": "Database client not configured",
                    "response_time_ms": 0,
                }

            # Basic connectivity check
            await self.db_client.health_check()

            # Performance check - count documents
            count = 0
            try:
                async with self.db_client.get_database() as db:
                    properties_collection = db["properties"]
                    count = await properties_collection.count_documents({})
            except Exception as e:
                logger.warning(f"Could not count documents: {e}")
                count = -1

            response_time = (time.time() - start_time) * 1000

            health_data = {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "document_count": count,
                "connection_pool": {
                    "max_size": getattr(self.db_client, "max_pool_size", 0),
                    "min_size": getattr(self.db_client, "min_pool_size", 0),
                },
            }

            self._add_health_record("database", True, f"Response time: {response_time:.2f}ms")
            return health_data

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self._add_health_record("database", False, str(e))

            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round(response_time, 2),
            }

    async def check_ollama_health(self) -> Dict[str, Any]:
        """Check Ollama service health and model availability."""
        start_time = time.time()

        try:
            if not self.ollama_client:
                return {
                    "status": "unavailable",
                    "message": "Ollama client not configured",
                    "response_time_ms": 0,
                }

            # Check if service is alive
            is_healthy = await self.ollama_client.health_check()

            if not is_healthy:
                raise Exception("Ollama health check failed")

            # Get model info
            model_info = {
                "name": self.ollama_client.model_name,
                "base_url": self.ollama_client.base_url,
                "timeout_seconds": self.ollama_client.timeout_seconds,
            }

            # Test with a simple prompt
            test_start = time.time()
            try:
                await self.ollama_client.generate_completion("Test prompt", max_tokens=10)
                inference_time = (time.time() - test_start) * 1000
                model_info["test_inference_ms"] = round(inference_time, 2)
            except Exception:
                model_info["test_inference_ms"] = None

            response_time = (time.time() - start_time) * 1000

            health_data = {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "model": model_info,
            }

            self._add_health_record("ollama", True, f"Response time: {response_time:.2f}ms")
            return health_data

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self._add_health_record("ollama", False, str(e))

            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round(response_time, 2),
            }

    def check_queue_health(self) -> Dict[str, Any]:
        """Check processing queue status."""
        try:
            if not self.processing_queue:
                return {"status": "unavailable", "message": "Processing queue not configured"}

            current_size = self.processing_queue.qsize()
            max_size = self.processing_queue.maxsize
            utilization = (current_size / max_size) * 100 if max_size > 0 else 0

            # Determine health status
            if utilization > 90:
                status = "critical"
                self._add_health_record("queue", False, f"Queue at {utilization:.1f}% capacity")
            elif utilization > 70:
                status = "warning"
                self._add_health_record("queue", True, f"Queue at {utilization:.1f}% capacity")
            else:
                status = "healthy"
                self._add_health_record("queue", True, f"Queue at {utilization:.1f}% capacity")

            return {
                "status": status,
                "current_size": current_size,
                "max_size": max_size,
                "utilization_percent": round(utilization, 2),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # Memory info
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()

            # CPU info
            cpu_percent = psutil.cpu_percent(interval=0.1)
            process_cpu = process.cpu_percent()

            # Disk info
            disk = psutil.disk_usage("/")

            # Determine health status
            memory_status = "healthy"
            if memory.percent > 90:
                memory_status = "critical"
                self._add_health_record("memory", False, f"System memory at {memory.percent:.1f}%")
            elif memory.percent > 80:
                memory_status = "warning"
                self._add_health_record("memory", True, f"System memory at {memory.percent:.1f}%")
            else:
                self._add_health_record("memory", True, f"System memory at {memory.percent:.1f}%")

            cpu_status = "healthy"
            if cpu_percent > 90:
                cpu_status = "critical"
                self._add_health_record("cpu", False, f"CPU at {cpu_percent:.1f}%")
            elif cpu_percent > 70:
                cpu_status = "warning"
                self._add_health_record("cpu", True, f"CPU at {cpu_percent:.1f}%")
            else:
                self._add_health_record("cpu", True, f"CPU at {cpu_percent:.1f}%")

            return {
                "memory": {
                    "status": memory_status,
                    "system": {
                        "total_mb": round(memory.total / 1024 / 1024, 2),
                        "available_mb": round(memory.available / 1024 / 1024, 2),
                        "percent_used": round(memory.percent, 2),
                    },
                    "process": {
                        "rss_mb": round(process_memory.rss / 1024 / 1024, 2),
                        "vms_mb": round(process_memory.vms / 1024 / 1024, 2),
                    },
                },
                "cpu": {
                    "status": cpu_status,
                    "system_percent": round(cpu_percent, 2),
                    "process_percent": round(process_cpu, 2),
                    "core_count": psutil.cpu_count(),
                },
                "disk": {
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                    "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                    "percent_used": round(disk.percent, 2),
                },
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def check_resource_monitor(self) -> Dict[str, Any]:
        """Check resource monitor status if available."""
        try:
            if not self.resource_monitor:
                return {"status": "unavailable", "message": "Resource monitor not configured"}

            metrics = await self.resource_monitor.get_metrics()
            stats = self.resource_monitor.get_aggregate_stats()

            return {
                "status": metrics.get("status", "unknown"),
                "current_metrics": {
                    "memory_mb": round(metrics.get("memory_mb", 0), 2),
                    "cpu_percent": round(metrics.get("cpu_percent", 0), 2),
                    "active_operations": metrics.get("active_operations", 0),
                    "queue_size": metrics.get("queue_size", 0),
                },
                "aggregate_stats": {
                    "avg_memory_mb": round(stats.get("avg_memory_mb", 0), 2),
                    "peak_memory_mb": round(stats.get("peak_memory_mb", 0), 2),
                    "avg_cpu_percent": round(stats.get("avg_cpu_percent", 0), 2),
                    "peak_cpu_percent": round(stats.get("peak_cpu_percent", 0), 2),
                    "total_operations": stats.get("total_operations", 0),
                    "avg_duration_seconds": round(stats.get("avg_duration_seconds", 0), 2),
                },
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_uptime(self) -> Dict[str, Any]:
        """Get service uptime information."""
        uptime_seconds = time.time() - self.start_time

        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        return {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_human": f"{days}d {hours}h {minutes}m {seconds}s",
        }

    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status of all components."""
        # Run all health checks in parallel
        results = await asyncio.gather(
            self.check_database_health(),
            self.check_ollama_health(),
            self.check_resource_monitor(),
            return_exceptions=True,
        )

        database_health = (
            results[0]
            if not isinstance(results[0], Exception)
            else {"status": "error", "error": str(results[0])}
        )

        ollama_health = (
            results[1]
            if not isinstance(results[1], Exception)
            else {"status": "error", "error": str(results[1])}
        )

        resource_monitor_health = (
            results[2]
            if not isinstance(results[2], Exception)
            else {"status": "error", "error": str(results[2])}
        )

        # Get synchronous checks
        queue_health = self.check_queue_health()
        system_resources = self.check_system_resources()
        uptime = self.get_uptime()

        # Calculate overall health score
        component_scores = {
            "database": self._calculate_health_score("database"),
            "ollama": self._calculate_health_score("ollama"),
            "queue": self._calculate_health_score("queue"),
            "memory": self._calculate_health_score("memory"),
            "cpu": self._calculate_health_score("cpu"),
        }

        overall_score = sum(component_scores.values()) / len(component_scores)

        # Determine overall status
        if overall_score >= 0.9:
            overall_status = "healthy"
        elif overall_score >= 0.7:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "health_score": round(overall_score, 3),
            "component_scores": {k: round(v, 3) for k, v in component_scores.items()},
            "uptime": uptime,
            "components": {
                "database": database_health,
                "ollama": ollama_health,
                "queue": queue_health,
                "resource_monitor": resource_monitor_health,
                "system_resources": system_resources,
            },
        }


# Standalone health check endpoints for use in web applications
async def basic_health_handler(request: web.Request) -> web.Response:
    """Basic health check endpoint."""
    health_service = request.app.get("health_service")

    if health_service:
        # Simple alive check
        return web.json_response(
            {
                "status": "healthy",
                "service": "llm_processor",
                "timestamp": datetime.now().isoformat(),
            }
        )
    else:
        return web.json_response(
            {
                "status": "unhealthy",
                "service": "llm_processor",
                "error": "Health service not initialized",
            },
            status=503,
        )


async def detailed_health_handler(request: web.Request) -> web.Response:
    """Detailed health check endpoint."""
    health_service = request.app.get("health_service")

    if not health_service:
        return web.json_response(
            {"status": "error", "error": "Health service not initialized"}, status=503
        )

    try:
        health_data = await health_service.get_comprehensive_health()

        # Determine HTTP status code
        if health_data["status"] == "healthy":
            status_code = 200
        elif health_data["status"] == "degraded":
            status_code = 200  # Still return 200 for degraded
        else:
            status_code = 503

        return web.json_response(health_data, status=status_code)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response(
            {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()},
            status=503,
        )


async def component_health_handler(request: web.Request) -> web.Response:
    """Component-specific health check endpoint."""
    component = request.match_info.get("component")
    health_service = request.app.get("health_service")

    if not health_service:
        return web.json_response(
            {"status": "error", "error": "Health service not initialized"}, status=503
        )

    valid_components = ["database", "ollama", "queue", "resources"]

    if component not in valid_components:
        return web.json_response(
            {"error": f"Invalid component. Valid components: {', '.join(valid_components)}"},
            status=400,
        )

    try:
        # Initialize result to avoid unbound variable error
        result: Dict[str, Any] = {"status": "error", "error": "Unknown component"}

        if component == "database":
            result = await health_service.check_database_health()
        elif component == "ollama":
            result = await health_service.check_ollama_health()
        elif component == "queue":
            result = health_service.check_queue_health()
        elif component == "resources":
            result = health_service.check_system_resources()

        return web.json_response(
            {"component": component, "timestamp": datetime.now().isoformat(), **result}
        )

    except Exception as e:
        logger.error(f"Component health check failed for {component}: {e}")
        return web.json_response(
            {
                "component": component,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
            status=503,
        )
