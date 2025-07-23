"""Tests for Prometheus exporters."""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from phoenix_real_estate.foundation.monitoring.exporters import (
    PrometheusExporter,
    MetricsHTTPHandler,
    start_metrics_server,
    generate_prometheus_config,
    export_prometheus_config,
)
from phoenix_real_estate.foundation.monitoring import (
    MetricsConfig,
    AlertConfig,
    MetricsCollector,
)
from phoenix_real_estate.foundation.monitoring.metrics import _reset_metrics_collector


@pytest.fixture(autouse=True)
def reset_global_collector():
    """Reset global metrics collector before each test."""
    _reset_metrics_collector()
    yield
    _reset_metrics_collector()


@pytest.fixture
def metrics_config():
    """Create test metrics configuration."""
    return MetricsConfig(
        enabled=True,
        port=9999,  # Use different port for testing
        path="/metrics",
        collection_interval=1,
        labels={"service": "test", "environment": "test"},
    )


@pytest.fixture
def metrics_collector(metrics_config):
    """Create metrics collector for testing."""
    return MetricsCollector(metrics_config)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestPrometheusExporter:
    """Test Prometheus exporter functionality."""

    def test_initialization(self, metrics_collector, metrics_config):
        """Test exporter initialization."""
        exporter = PrometheusExporter(metrics_collector, metrics_config)

        assert exporter.metrics_collector is metrics_collector
        assert exporter.config is metrics_config
        assert exporter.server is None
        assert exporter.server_thread is None

    @patch("phoenix_real_estate.foundation.monitoring.exporters.HTTPServer")
    @patch("threading.Thread")
    def test_start_http_server(self, mock_thread, mock_server, metrics_collector, metrics_config):
        """Test starting HTTP server."""
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        exporter = PrometheusExporter(metrics_collector, metrics_config)
        exporter.start_http_server()

        # Check server was created and started
        mock_server.assert_called_once()
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

        assert exporter.server is mock_server_instance
        assert exporter.server_thread is mock_thread_instance

    def test_start_http_server_disabled(self, metrics_collector):
        """Test starting HTTP server when metrics are disabled."""
        disabled_config = MetricsConfig(enabled=False)
        exporter = PrometheusExporter(metrics_collector, disabled_config)

        exporter.start_http_server()

        # Server should not be started
        assert exporter.server is None
        assert exporter.server_thread is None

    def test_stop_http_server(self, metrics_collector, metrics_config):
        """Test stopping HTTP server."""
        exporter = PrometheusExporter(metrics_collector, metrics_config)

        # Mock server and thread
        mock_server = MagicMock()
        mock_thread = MagicMock()

        exporter.server = mock_server
        exporter.server_thread = mock_thread

        exporter.stop_http_server()

        mock_server.shutdown.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_export_alert_rules(self, metrics_collector, metrics_config, temp_dir):
        """Test exporting alert rules."""
        alert_config = AlertConfig()
        exporter = PrometheusExporter(metrics_collector, metrics_config, alert_config)

        output_path = Path(temp_dir) / "test_alerts.yml"
        exporter.export_alert_rules(str(output_path))

        # Check file was created
        assert output_path.exists()

        # Check content
        with open(output_path) as f:
            content = yaml.safe_load(f)

        assert "groups" in content
        assert len(content["groups"]) > 0
        assert content["groups"][0]["name"] == "phoenix_mls_alerts"

    @patch("prometheus_client.push_to_gateway")
    def test_push_to_gateway(self, mock_push, metrics_collector, metrics_config):
        """Test pushing metrics to gateway."""
        exporter = PrometheusExporter(metrics_collector, metrics_config)

        exporter.push_to_gateway("http://pushgateway:9091", "test_job")

        mock_push.assert_called_once_with(
            "http://pushgateway:9091",
            job="test_job",
            registry=metrics_collector.registry,
            grouping_key={},
        )

    @patch("prometheus_client.delete_from_gateway")
    def test_delete_from_gateway(self, mock_delete, metrics_collector, metrics_config):
        """Test deleting metrics from gateway."""
        exporter = PrometheusExporter(metrics_collector, metrics_config)

        exporter.delete_from_gateway("http://pushgateway:9091", "test_job")

        mock_delete.assert_called_once_with(
            "http://pushgateway:9091", job="test_job", grouping_key={}
        )


class TestMetricsHTTPHandler:
    """Test HTTP handler for metrics endpoint."""

    def test_initialization(self, metrics_collector):
        """Test handler initialization."""
        # Create a mock request for the handler
        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        # The handler expects these parameters
        handler = MetricsHTTPHandler(
            metrics_collector, mock_request, mock_client_address, mock_server
        )

        assert handler.metrics_collector is metrics_collector

    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.send_response")
    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.send_header")
    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.end_headers")
    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.wfile")
    def test_serve_metrics(
        self, mock_wfile, mock_end_headers, mock_send_header, mock_send_response, metrics_collector
    ):
        """Test serving metrics endpoint."""
        # Record some test metrics
        metrics_collector.scraper.record_request("success", "test", "GET")

        # Create handler with mocked methods
        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        handler = MetricsHTTPHandler(
            metrics_collector, mock_request, mock_client_address, mock_server
        )

        # Mock the path
        handler.path = "/metrics"

        # Call the method
        handler._serve_metrics()

        # Check response
        mock_send_response.assert_called_once_with(200)
        mock_send_header.assert_called()
        mock_end_headers.assert_called_once()
        mock_wfile.write.assert_called_once()

    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.send_response")
    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.send_header")
    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.end_headers")
    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.wfile")
    def test_serve_health(
        self, mock_wfile, mock_end_headers, mock_send_header, mock_send_response, metrics_collector
    ):
        """Test serving health endpoint."""
        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        handler = MetricsHTTPHandler(
            metrics_collector, mock_request, mock_client_address, mock_server
        )

        handler.path = "/health"
        handler._serve_health()

        # Check response
        mock_send_response.assert_called_once_with(200)
        mock_send_header.assert_called_with("Content-Type", "application/json")
        mock_end_headers.assert_called_once()

        # Check that health data was written
        mock_wfile.write.assert_called_once()
        written_data = mock_wfile.write.call_args[0][0]
        health_data = json.loads(written_data.decode())

        assert health_data["status"] == "healthy"
        assert health_data["service"] == "phoenix_mls_scraper"

    @patch("phoenix_real_estate.foundation.monitoring.exporters.MetricsHTTPHandler.send_error")
    def test_serve_not_found(self, mock_send_error, metrics_collector):
        """Test serving 404 for unknown paths."""
        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        handler = MetricsHTTPHandler(
            metrics_collector, mock_request, mock_client_address, mock_server
        )

        handler.path = "/unknown"
        handler.do_GET()

        mock_send_error.assert_called_once_with(404, "Not Found")


@pytest.mark.asyncio
async def test_start_metrics_server(metrics_config):
    """Test starting metrics server function."""
    # Use a different port to avoid conflicts
    test_config = MetricsConfig(enabled=True, port=9998, path="/metrics")

    with patch(
        "phoenix_real_estate.foundation.monitoring.exporters.PrometheusExporter.start_http_server"
    ):
        exporter = await start_metrics_server(test_config)

        assert exporter is not None
        assert isinstance(exporter, PrometheusExporter)


def test_generate_prometheus_config():
    """Test generating Prometheus configuration."""
    config = generate_prometheus_config(
        scrape_interval="30s",
        evaluation_interval="30s",
        metrics_port=9090,
        alert_manager_url="localhost:9093",
    )

    assert config["global"]["scrape_interval"] == "30s"
    assert config["global"]["evaluation_interval"] == "30s"
    assert len(config["scrape_configs"]) > 0
    assert config["scrape_configs"][0]["job_name"] == "phoenix_mls_scraper"
    assert "alerting" in config
    assert config["alerting"]["alertmanagers"][0]["static_configs"][0]["targets"] == [
        "localhost:9093"
    ]


def test_generate_prometheus_config_without_alertmanager():
    """Test generating Prometheus config without Alertmanager."""
    config = generate_prometheus_config()

    # Should not have alerting section when no URL provided
    assert "alerting" not in config


def test_export_prometheus_config(temp_dir):
    """Test exporting Prometheus configuration files."""
    output_dir = Path(temp_dir) / "prometheus_config"

    export_prometheus_config(str(output_dir))

    # Check files were created
    prometheus_file = output_dir / "prometheus.yml"
    alerts_file = output_dir / "alerts.yml"

    assert prometheus_file.exists()
    assert alerts_file.exists()

    # Check prometheus.yml content
    with open(prometheus_file) as f:
        prometheus_config = yaml.safe_load(f)

    assert "global" in prometheus_config
    assert "scrape_configs" in prometheus_config

    # Check alerts.yml content
    with open(alerts_file) as f:
        alerts_config = yaml.safe_load(f)

    assert "groups" in alerts_config
    assert len(alerts_config["groups"]) > 0


def test_export_prometheus_config_with_custom_config(temp_dir):
    """Test exporting with custom configuration."""
    output_dir = Path(temp_dir) / "custom_config"

    custom_config = {
        "global": {"scrape_interval": "5s"},
        "scrape_configs": [
            {"job_name": "custom_job", "static_configs": [{"targets": ["localhost:8080"]}]}
        ],
    }

    custom_alert_config = AlertConfig()

    export_prometheus_config(str(output_dir), custom_config, custom_alert_config)

    # Check custom configuration was used
    prometheus_file = output_dir / "prometheus.yml"
    with open(prometheus_file) as f:
        saved_config = yaml.safe_load(f)

    assert saved_config["global"]["scrape_interval"] == "5s"
    assert saved_config["scrape_configs"][0]["job_name"] == "custom_job"
