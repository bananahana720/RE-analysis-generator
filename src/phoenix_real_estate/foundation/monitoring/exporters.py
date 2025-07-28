"""Prometheus metrics exporters for Phoenix Real Estate.

Provides HTTP server and push gateway exporters for Prometheus metrics.
"""

import threading
from typing import Optional, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import yaml
from pathlib import Path

from prometheus_client import (
    push_to_gateway,
    delete_from_gateway,
    CONTENT_TYPE_LATEST,
)

from phoenix_real_estate.foundation.logging import get_logger
from .config import MetricsConfig, AlertConfig
from .metrics import MetricsCollector, get_metrics_collector

logger = get_logger(__name__)


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Prometheus metrics endpoint."""

    def __init__(self, metrics_collector: MetricsCollector, *args, **kwargs):
        """Initialize handler with metrics collector."""
        self.metrics_collector = metrics_collector
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests for metrics."""
        if self.path == "/metrics":
            self._serve_metrics()
        elif self.path == "/health":
            self._serve_health()
        elif self.path == "/stats":
            self._serve_stats()
        else:
            self.send_error(404, "Not Found")

    def _serve_metrics(self):
        """Serve Prometheus metrics."""
        try:
            metrics_data = self.metrics_collector.get_metrics()

            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(metrics_data)))
            self.end_headers()
            self.wfile.write(metrics_data)

        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
            self.send_error(500, "Internal Server Error")

    def _serve_health(self):
        """Serve health check endpoint."""
        health_data = {
            "status": "healthy",
            "service": "phoenix_mls_scraper",
            "metrics_enabled": True,
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(health_data).encode())

    def _serve_stats(self):
        """Serve current statistics as JSON."""
        try:
            stats = self.metrics_collector.get_metrics_dict()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(stats, default=str).encode())

        except Exception as e:
            logger.error(f"Error serving stats: {e}")
            self.send_error(500, "Internal Server Error")

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"Metrics HTTP: {format % args}")


class PrometheusExporter:
    """Prometheus metrics exporter with HTTP server."""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        config: MetricsConfig,
        alert_config: Optional[AlertConfig] = None,
    ):
        """Initialize Prometheus exporter.

        Args:
            metrics_collector: Metrics collector instance
            config: Metrics configuration
            alert_config: Optional alert configuration
        """
        self.metrics_collector = metrics_collector
        self.config = config
        self.alert_config = alert_config or AlertConfig()
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

        logger.info(f"Prometheus exporter initialized on port {config.port}")

    def start_http_server(self):
        """Start HTTP server for metrics endpoint."""
        if not self.config.enabled:
            logger.info("Metrics collection disabled")
            return

        # Create handler class with metrics collector
        def handler(*args, **kwargs):
            return MetricsHTTPHandler(
                    self.metrics_collector, *args, **kwargs
                )

        # Start HTTP server
        self.server = HTTPServer(("", self.config.port), handler)

        # Run server in separate thread
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        logger.info(
            f"Prometheus metrics server started on port {self.config.port}"
            f" at path {self.config.path}"
        )

    def stop_http_server(self):
        """Stop HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server_thread.join(timeout=5)
            logger.info("Prometheus metrics server stopped")

    def export_alert_rules(self, output_path: str):
        """Export alert rules to file for Prometheus.

        Args:
            output_path: Path to write alert rules file
        """
        alert_config = self.alert_config.to_prometheus_config()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            yaml.dump(alert_config, f, default_flow_style=False)

        logger.info(f"Alert rules exported to {output_path}")

    def push_to_gateway(
        self,
        gateway_url: str,
        job_name: str = "phoenix_mls_scraper",
        grouping_key: Optional[Dict[str, str]] = None,
    ):
        """Push metrics to Prometheus Pushgateway.

        Args:
            gateway_url: URL of Prometheus Pushgateway
            job_name: Job name for metrics grouping
            grouping_key: Additional grouping labels
        """
        try:
            push_to_gateway(
                gateway_url,
                job=job_name,
                registry=self.metrics_collector.registry,
                grouping_key=grouping_key or {},
            )
            logger.debug(f"Metrics pushed to gateway {gateway_url}")

        except Exception as e:
            logger.error(f"Failed to push metrics to gateway: {e}")

    def delete_from_gateway(
        self,
        gateway_url: str,
        job_name: str = "phoenix_mls_scraper",
        grouping_key: Optional[Dict[str, str]] = None,
    ):
        """Delete metrics from Prometheus Pushgateway.

        Args:
            gateway_url: URL of Prometheus Pushgateway
            job_name: Job name for metrics grouping
            grouping_key: Additional grouping labels
        """
        try:
            delete_from_gateway(gateway_url, job=job_name, grouping_key=grouping_key or {})
            logger.debug(f"Metrics deleted from gateway {gateway_url}")

        except Exception as e:
            logger.error(f"Failed to delete metrics from gateway: {e}")


async def start_metrics_server(
    config: Optional[MetricsConfig] = None, alert_config: Optional[AlertConfig] = None
) -> PrometheusExporter:
    """Start Prometheus metrics server.

    Args:
        config: Metrics configuration
        alert_config: Alert configuration

    Returns:
        PrometheusExporter instance
    """
    if config is None:
        config = MetricsConfig()

    # Get or create metrics collector
    collector = get_metrics_collector(config)

    # Create and start exporter
    exporter = PrometheusExporter(collector, config, alert_config)
    exporter.start_http_server()

    return exporter


def generate_prometheus_config(
    scrape_interval: str = "15s",
    evaluation_interval: str = "15s",
    metrics_port: int = 9090,
    alert_manager_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate Prometheus configuration for scraping metrics.

    Args:
        scrape_interval: How often to scrape metrics
        evaluation_interval: How often to evaluate rules
        metrics_port: Port where metrics are exposed
        alert_manager_url: Optional Alertmanager URL

    Returns:
        Prometheus configuration dictionary
    """
    config = {
        "global": {
            "scrape_interval": scrape_interval,
            "evaluation_interval": evaluation_interval,
            "external_labels": {"monitor": "phoenix-mls-monitor", "service": "phoenix-mls-scraper"},
        },
        "rule_files": ["alerts.yml"],
        "scrape_configs": [
            {
                "job_name": "phoenix_mls_scraper",
                "static_configs": [
                    {
                        "targets": [f"localhost:{metrics_port}"],
                        "labels": {"environment": "production", "component": "scraper"},
                    }
                ],
            }
        ],
    }

    if alert_manager_url:
        config["alerting"] = {
            "alertmanagers": [{"static_configs": [{"targets": [alert_manager_url]}]}]
        }

    return config


def export_prometheus_config(
    output_dir: str,
    config: Optional[Dict[str, Any]] = None,
    alert_config: Optional[AlertConfig] = None,
):
    """Export Prometheus configuration files.

    Args:
        output_dir: Directory to write configuration files
        config: Prometheus configuration (generated if not provided)
        alert_config: Alert configuration
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate or use provided config
    if config is None:
        config = generate_prometheus_config()

    # Write prometheus.yml
    with open(output_path / "prometheus.yml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Write alerts.yml
    if alert_config is None:
        alert_config = AlertConfig()

    with open(output_path / "alerts.yml", "w") as f:
        yaml.dump(alert_config.to_prometheus_config(), f, default_flow_style=False)

    logger.info(f"Prometheus configuration exported to {output_dir}")
