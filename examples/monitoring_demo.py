"""Demo script showing how to use Prometheus monitoring with Phoenix MLS Scraper.

This demonstrates:
- Starting the metrics server
- Integrating metrics with the scraper
- Viewing metrics
- Generating Grafana dashboards
"""

import asyncio
import json
import yaml
from pathlib import Path

from phoenix_real_estate.foundation.monitoring import (
    MetricsConfig,
    start_metrics_server,
    get_metrics_collector,
)
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper
from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager
from phoenix_real_estate.collectors.phoenix_mls.metrics_integration import (
    metrics_integrated_scraper,
    metrics_integrated_proxy_manager,
)


# Apply metrics integration decorators
@metrics_integrated_scraper
class MonitoredPhoenixMLSScraper(PhoenixMLSScraper):
    """Phoenix MLS Scraper with integrated Prometheus metrics."""

    pass


@metrics_integrated_proxy_manager
class MonitoredProxyManager(ProxyManager):
    """Proxy Manager with integrated Prometheus metrics."""

    pass


async def demo_monitoring():
    """Demonstrate monitoring capabilities."""
    print("=== Phoenix MLS Scraper Monitoring Demo ===\n")

    # 1. Configure metrics
    metrics_config = MetricsConfig(
        enabled=True,
        port=9090,
        path="/metrics",
        collection_interval=15,
        labels={"service": "phoenix_mls_scraper", "environment": "demo", "region": "phoenix"},
    )

    # 2. Start metrics server
    print("Starting Prometheus metrics server...")
    exporter = await start_metrics_server(metrics_config)
    print(
        f"[OK] Metrics server running at http://localhost:{metrics_config.port}{metrics_config.path}\n"
    )

    # 3. Export alert rules
    print("Exporting alert rules...")
    exporter.export_alert_rules("config/monitoring/alerts_generated.yml")
    print("[OK] Alert rules exported\n")

    # 4. Create monitored scraper
    scraper_config = {
        "base_url": "https://www.phoenixmlssearch.com",
        "max_retries": 3,
        "timeout": 30,
        "rate_limit": {"requests_per_minute": 60},
    }

    proxy_config = {
        "proxies": [
            {"host": "proxy1.example.com", "port": 8080},
            {"host": "proxy2.example.com", "port": 8080},
            {"host": "proxy3.example.com", "port": 8080},
        ],
        "max_failures": 3,
        "cooldown_minutes": 5,
    }

    print("Initializing monitored scraper...")
    MonitoredPhoenixMLSScraper(scraper_config, proxy_config)
    print("[OK] Scraper initialized with metrics integration\n")

    # 5. Simulate some scraping activity
    print("Simulating scraping activity...")
    metrics_collector = get_metrics_collector()

    # Simulate successful requests
    for i in range(5):
        metrics_collector.scraper.record_request("success", "search", "GET")
        metrics_collector.scraper.record_response_time(0.5 + i * 0.1, "search", "success")
        metrics_collector.scraper.record_property_scraped("85001", "success")

    # Simulate some failures
    for i in range(2):
        metrics_collector.scraper.record_request("failed", "property_details", "GET")
        metrics_collector.scraper.record_error("TimeoutError", "property_details")

    # Simulate proxy metrics
    metrics_collector.proxy.set_proxy_counts(total=3, healthy=2)
    metrics_collector.proxy.record_proxy_request("proxy1", "success")
    metrics_collector.proxy.record_proxy_request("proxy2", "failed")
    metrics_collector.proxy.record_health_check("proxy1", 0.2, True)
    metrics_collector.proxy.record_health_check("proxy2", 5.0, False, "timeout")

    # Simulate rate limiting
    metrics_collector.rate_limit.record_rate_limit_hit("phoenix_mls", "scraper_limit", 5.0)
    metrics_collector.rate_limit.set_current_rate("phoenix_mls", 58.5)
    metrics_collector.rate_limit.set_limit_remaining("phoenix_mls", 2)

    print("[OK] Simulated metrics recorded\n")

    # 6. Display current metrics
    print("Current Metrics Summary:")
    print("-" * 50)

    # Get metrics as text (Prometheus format)
    metrics_text = metrics_collector.get_metrics().decode("utf-8")

    # Parse and display key metrics
    for line in metrics_text.split("\n"):
        if line and not line.startswith("#"):
            # Display some key metrics
            if any(
                key in line
                for key in [
                    "scraper_requests_total",
                    "proxy_healthy_count",
                    "rate_limit_hits_total",
                    "scraper_properties_scraped_total",
                ]
            ):
                print(f"  {line}")

    print("\n[OK] Metrics are being collected and exposed")
    print(f"\nView all metrics at: http://localhost:{metrics_config.port}{metrics_config.path}")

    # 7. Generate Grafana dashboard
    print("\nGenerating Grafana dashboard configuration...")
    dashboard = generate_grafana_dashboard()

    dashboard_path = Path("config/monitoring/grafana_dashboard.json")
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dashboard_path, "w") as f:
        json.dump(dashboard, f, indent=2)

    print(f"[OK] Grafana dashboard saved to {dashboard_path}")

    # 8. Generate docker-compose for full monitoring stack
    print("\nGenerating docker-compose configuration...")
    docker_compose = generate_docker_compose()

    compose_path = Path("config/monitoring/docker-compose.yml")
    with open(compose_path, "w") as f:
        yaml.dump(docker_compose, f, default_flow_style=False)

    print(f"[OK] Docker compose saved to {compose_path}")

    print("\n=== Demo Complete ===")
    print("\nTo start the full monitoring stack:")
    print("  cd config/monitoring")
    print("  docker-compose up -d")
    print("\nThen access:")
    print("  - Prometheus: http://localhost:9091")
    print("  - Grafana: http://localhost:3000 (admin/admin)")
    print("  - Alertmanager: http://localhost:9093")


def generate_grafana_dashboard():
    """Generate a Grafana dashboard configuration."""
    return {
        "dashboard": {
            "title": "Phoenix MLS Scraper Monitoring",
            "tags": ["scraper", "monitoring", "phoenix"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "Scraping Success Rate",
                    "type": "graph",
                    "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                    "targets": [
                        {
                            "expr": 'rate(scraper_requests_total{status="success"}[5m]) / rate(scraper_requests_total[5m]) * 100',
                            "legendFormat": "Success Rate %",
                        }
                    ],
                },
                {
                    "title": "Request Rate",
                    "type": "graph",
                    "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
                    "targets": [
                        {"expr": "rate(scraper_requests_total[5m])", "legendFormat": "{{status}}"}
                    ],
                },
                {
                    "title": "Response Time (95th percentile)",
                    "type": "graph",
                    "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(scraper_response_time_seconds_bucket[5m]))",
                            "legendFormat": "{{endpoint}}",
                        }
                    ],
                },
                {
                    "title": "Proxy Health",
                    "type": "stat",
                    "gridPos": {"x": 12, "y": 8, "w": 6, "h": 8},
                    "targets": [{"expr": "proxy_healthy_count", "legendFormat": "Healthy Proxies"}],
                },
                {
                    "title": "Rate Limit Status",
                    "type": "gauge",
                    "gridPos": {"x": 18, "y": 8, "w": 6, "h": 8},
                    "targets": [
                        {
                            "expr": 'rate_limit_current_rate{endpoint="phoenix_mls"}',
                            "legendFormat": "Requests/min",
                        }
                    ],
                },
                {
                    "title": "Properties Scraped",
                    "type": "graph",
                    "gridPos": {"x": 0, "y": 16, "w": 12, "h": 8},
                    "targets": [
                        {
                            "expr": "increase(scraper_properties_scraped_total[1h])",
                            "legendFormat": "{{zipcode}}",
                        }
                    ],
                },
                {
                    "title": "System Resources",
                    "type": "graph",
                    "gridPos": {"x": 12, "y": 16, "w": 12, "h": 8},
                    "targets": [
                        {"expr": "system_cpu_usage_percent", "legendFormat": "CPU %"},
                        {"expr": "system_memory_usage_percent", "legendFormat": "Memory %"},
                    ],
                },
            ],
            "time": {"from": "now-6h", "to": "now"},
            "refresh": "10s",
        }
    }


def generate_docker_compose():
    """Generate docker-compose configuration for monitoring stack."""
    return {
        "version": "3.8",
        "services": {
            "prometheus": {
                "image": "prom/prometheus:latest",
                "container_name": "prometheus",
                "ports": ["9091:9090"],
                "volumes": [
                    "./prometheus.yml:/etc/prometheus/prometheus.yml",
                    "./alerts.yml:/etc/prometheus/alerts.yml",
                    "prometheus_data:/prometheus",
                ],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--web.enable-lifecycle",
                ],
                "restart": "unless-stopped",
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "container_name": "grafana",
                "ports": ["3000:3000"],
                "environment": {
                    "GF_SECURITY_ADMIN_USER": "admin",
                    "GF_SECURITY_ADMIN_PASSWORD": "admin",
                    "GF_USERS_ALLOW_SIGN_UP": "false",
                },
                "volumes": [
                    "grafana_data:/var/lib/grafana",
                    "./grafana_dashboard.json:/var/lib/grafana/dashboards/dashboard.json",
                ],
                "restart": "unless-stopped",
            },
            "alertmanager": {
                "image": "prom/alertmanager:latest",
                "container_name": "alertmanager",
                "ports": ["9093:9093"],
                "volumes": [
                    "./alertmanager.yml:/etc/alertmanager/config.yml",
                    "alertmanager_data:/alertmanager",
                ],
                "command": [
                    "--config.file=/etc/alertmanager/config.yml",
                    "--storage.path=/alertmanager",
                ],
                "restart": "unless-stopped",
            },
        },
        "volumes": {"prometheus_data": {}, "grafana_data": {}, "alertmanager_data": {}},
        "networks": {"default": {"name": "monitoring"}},
    }


if __name__ == "__main__":
    asyncio.run(demo_monitoring())
