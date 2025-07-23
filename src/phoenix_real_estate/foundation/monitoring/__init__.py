"""Monitoring module for Phoenix Real Estate.

Provides Prometheus metrics integration for tracking system performance,
scraping success rates, proxy health, and other key indicators.
"""

from .metrics import (
    MetricsCollector,
    ScraperMetrics,
    ProxyMetrics,
    DatabaseMetrics,
    SystemMetrics,
    get_metrics_collector,
)
from .config import MetricsConfig, AlertRule, AlertConfig
from .exporters import PrometheusExporter, start_metrics_server

__all__ = [
    # Core
    "MetricsCollector",
    "get_metrics_collector",
    # Metric Types
    "ScraperMetrics",
    "ProxyMetrics",
    "DatabaseMetrics",
    "SystemMetrics",
    # Configuration
    "MetricsConfig",
    "AlertRule",
    "AlertConfig",
    # Exporters
    "PrometheusExporter",
    "start_metrics_server",
]
