"""
LLM Processing Service

Production service for running the LLM processing pipeline with health checks,
monitoring, and graceful shutdown handling.
"""

import asyncio
import signal
import sys
from typing import Optional

# Windows-compatible uvloop import
try:
    import uvloop

    # Only use uvloop on Unix-like systems
    if sys.platform != "win32":
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    # uvloop not available (Windows or not installed)
    pass
from aiohttp import web
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from phoenix_real_estate.foundation import EnvironmentConfigProvider, get_logger
from phoenix_real_estate.foundation.database import DatabaseConnection
from phoenix_real_estate.orchestration import ProcessingIntegrator
from phoenix_real_estate.collectors.processing.monitoring import (
    ProcessingMonitor,
    ResourceMonitor,
    ResourceLimits,
)
from phoenix_real_estate.collectors.processing import OllamaClient
from phoenix_real_estate.api.health import (
    HealthCheckService,
    detailed_health_handler,
    component_health_handler,
)

# Set up high-performance event loop

# Metrics
processing_requests = Counter(
    "llm_processing_requests_total", "Total number of processing requests", ["source", "status"]
)
processing_duration = Histogram(
    "llm_processing_duration_seconds", "Processing request duration", ["source"]
)
active_connections = Gauge("llm_active_connections", "Number of active LLM connections")
queue_size = Gauge("llm_processing_queue_size", "Current size of processing queue")
memory_usage = Gauge("llm_memory_usage_bytes", "Current memory usage in bytes")


class LLMProcessingService:
    """Production LLM processing service with monitoring and health checks."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the service."""
        self.logger = get_logger(__name__)
        self.config = EnvironmentConfigProvider(environment="production")
        self.db_client: Optional[DatabaseConnection] = None
        self.processing_integrator: Optional[ProcessingIntegrator] = None
        self.monitor: Optional[ProcessingMonitor] = None
        self.resource_monitor: Optional[ResourceMonitor] = None
        self.health_service: Optional[HealthCheckService] = None
        self.app = web.Application()
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Processing queue
        self.processing_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.workers: list[asyncio.Task] = []

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes for health checks and metrics."""
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/health/llm", self.llm_health_check)
        self.app.router.add_get("/health/detailed", detailed_health_handler)
        self.app.router.add_get("/health/component/{component}", component_health_handler)
        self.app.router.add_get("/metrics", self.metrics_handler)
        self.app.router.add_post("/process", self.process_property)

    async def health_check(self, request: web.Request) -> web.Response:
        """Basic health check endpoint."""
        if self.running:
            return web.json_response({"status": "healthy", "service": "llm_processor"})
        return web.json_response({"status": "unhealthy", "service": "llm_processor"}, status=503)

    async def llm_health_check(self, request: web.Request) -> web.Response:
        """Detailed LLM health check."""
        health_data = {"status": "healthy", "components": {}}

        # Check database connection
        try:
            if self.db_client:
                await self.db_client.health_check()
                health_data["components"]["database"] = "healthy"
        except Exception as e:
            health_data["components"]["database"] = f"unhealthy: {str(e)}"
            health_data["status"] = "degraded"

        # Check Ollama connection
        try:
            if self.processing_integrator:
                # Simple test to check if Ollama is responsive
                test_result = await self.processing_integrator.pipeline.llm_client.health_check()
                health_data["components"]["ollama"] = "healthy" if test_result else "unhealthy"
        except Exception as e:
            health_data["components"]["ollama"] = f"unhealthy: {str(e)}"
            health_data["status"] = "unhealthy"

        # Check queue status
        queue_percent = (self.processing_queue.qsize() / self.processing_queue.maxsize) * 100
        if queue_percent > 80:
            health_data["components"]["queue"] = f"warning: {queue_percent:.1f}% full"
            health_data["status"] = "degraded"
        else:
            health_data["components"]["queue"] = f"healthy: {queue_percent:.1f}% full"

        # Check memory usage
        import psutil

        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        memory_limit_mb = 3072  # From systemd config
        memory_percent = (memory_mb / memory_limit_mb) * 100

        if memory_percent > 80:
            health_data["components"]["memory"] = f"warning: {memory_percent:.1f}% used"
            health_data["status"] = "degraded"
        else:
            health_data["components"]["memory"] = f"healthy: {memory_percent:.1f}% used"

        # Update metrics
        memory_usage.set(process.memory_info().rss)
        queue_size.set(self.processing_queue.qsize())

        status_code = 200 if health_data["status"] == "healthy" else 503
        return web.json_response(health_data, status=status_code)

    async def metrics_handler(self, request: web.Request) -> web.Response:
        """Prometheus metrics endpoint."""
        metrics_data = generate_latest()
        return web.Response(body=metrics_data, content_type=CONTENT_TYPE_LATEST)

    async def process_property(self, request: web.Request) -> web.Response:
        """Process a property through the LLM pipeline."""
        try:
            data = await request.json()
            source = data.get("source", "unknown")

            # Add to processing queue
            await self.processing_queue.put(data)
            processing_requests.labels(source=source, status="queued").inc()

            return web.json_response(
                {"status": "queued", "queue_position": self.processing_queue.qsize()}
            )

        except Exception as e:
            self.logger.error("Failed to queue processing request", error=str(e))
            processing_requests.labels(source="unknown", status="error").inc()
            return web.json_response({"error": "Failed to process request"}, status=500)

    async def _process_worker(self, worker_id: int):
        """Worker to process items from the queue."""
        self.logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)

                source = item.get("source", "unknown")

                # Process the item
                with processing_duration.labels(source=source).time():
                    try:
                        result = await self.processing_integrator.process_property(
                            item["data"], source
                        )

                        if result:
                            processing_requests.labels(source=source, status="success").inc()
                            # Store result in database
                            if self.db_client:
                                await self.db_client.properties.insert_one(result)
                        else:
                            processing_requests.labels(source=source, status="failed").inc()

                    except Exception as e:
                        self.logger.error(
                            f"Worker {worker_id} processing error", error=str(e), source=source
                        )
                        processing_requests.labels(source=source, status="error").inc()

            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error", error=str(e))
                await asyncio.sleep(1)

        self.logger.info(f"Worker {worker_id} stopped")

    async def start(self):
        """Start the service."""
        self.logger.info("Starting LLM Processing Service...")

        try:
            # Initialize database connection
            self.db_client = DatabaseConnection(self.config)
            await self.db_client.connect()

            # Initialize processing integrator
            self.processing_integrator = ProcessingIntegrator(self.config)
            await self.processing_integrator.__aenter__()

            # Initialize monitor
            self.monitor = ProcessingMonitor()

            # Initialize resource monitor
            resource_limits = ResourceLimits(
                max_memory_mb=3072,  # 3GB limit
                max_cpu_percent=80,
                max_concurrent_requests=10,
            )
            self.resource_monitor = ResourceMonitor(resource_limits)
            await self.resource_monitor.start()

            # Initialize health service
            self.health_service = HealthCheckService(
                db_client=self.db_client,
                ollama_client=self.processing_integrator.pipeline._extractor._client,
                resource_monitor=self.resource_monitor,
                processing_queue=self.processing_queue,
            )

            # Store health service in app for handlers
            self.app["health_service"] = self.health_service

            # Set running flag
            self.running = True

            # Start worker tasks
            num_workers = 2  # From config
            for i in range(num_workers):
                worker = asyncio.create_task(self._process_worker(i))
                self.workers.append(worker)

            self.logger.info(f"Started {num_workers} processing workers")

            # Setup signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)

            # Start web server
            runner = web.AppRunner(self.app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", 8080)
            await site.start()

            self.logger.info("LLM Processing Service started successfully")
            self.logger.info("Health check: http://localhost:8080/health")
            self.logger.info("Metrics: http://localhost:8080/metrics")

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Cleanup
            await self.stop()
            await site.stop()
            await runner.cleanup()

        except Exception as e:
            self.logger.error("Failed to start service", error=str(e))
            await self.stop()
            raise

    async def stop(self):
        """Stop the service gracefully."""
        self.logger.info("Stopping LLM Processing Service...")

        # Set running flag to false
        self.running = False

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        # Stop resource monitor
        if self.resource_monitor:
            await self.resource_monitor.stop()

        # Close connections
        if self.processing_integrator:
            await self.processing_integrator.__aexit__(None, None, None)

        if self.db_client:
            await self.db_client.close()

        self.logger.info("LLM Processing Service stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()


async def main():
    """Main entry point."""
    service = LLMProcessingService()
    try:
        await service.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger = get_logger(__name__)
        logger.error("Service crashed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM Processing Service")
    parser.add_argument("--health-check", action="store_true", help="Run health check and exit")

    args = parser.parse_args()

    if args.health_check:
        # Run a simple health check
        async def health_check():
            """Simple health check for systemd."""
            try:
                config = EnvironmentConfigProvider(environment="production")

                # Check MongoDB
                db_client = DatabaseConnection(config)
                await db_client.connect()
                await db_client.health_check()
                await db_client.close()

                # Check Ollama
                async with OllamaClient(config) as ollama:
                    if not await ollama.health_check():
                        print("Ollama health check failed")
                        sys.exit(1)

                print("Health check passed")
                sys.exit(0)

            except Exception as e:
                print(f"Health check failed: {e}")
                sys.exit(1)

        asyncio.run(health_check())
    else:
        # Run the service
        asyncio.run(main())
