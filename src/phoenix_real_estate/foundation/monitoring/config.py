"""Monitoring configuration for Phoenix Real Estate.

Defines metrics configuration, alert rules, and thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class MetricType(str, Enum):
    """Prometheus metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class AlertRule:
    """Alert rule configuration.

    Attributes:
        name: Rule name
        expression: PromQL expression
        duration: How long condition must be true
        severity: Alert severity level
        labels: Additional labels
        annotations: Alert annotations (summary, description)
    """

    name: str
    expression: str
    duration: str = "5m"
    severity: AlertSeverity = AlertSeverity.WARNING
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def to_prometheus_rule(self) -> Dict[str, Any]:
        """Convert to Prometheus rule format."""
        rule = {
            "alert": self.name,
            "expr": self.expression,
            "for": self.duration,
            "labels": {"severity": self.severity.value, **self.labels},
            "annotations": self.annotations,
        }
        return rule


@dataclass
class MetricsConfig:
    """Metrics collection configuration.

    Attributes:
        enabled: Whether metrics collection is enabled
        port: Port for metrics HTTP server
        path: Path for metrics endpoint
        collection_interval: How often to collect metrics (seconds)
        retention_period: How long to retain metrics (seconds)
        labels: Default labels for all metrics
    """

    enabled: bool = True
    port: int = 9090
    path: str = "/metrics"
    collection_interval: int = 15
    retention_period: int = 86400  # 24 hours
    labels: Dict[str, str] = field(
        default_factory=lambda: {"service": "phoenix_mls_scraper", "environment": "production"}
    )

    # Histogram buckets for response times (in seconds)
    response_time_buckets: List[float] = field(
        default_factory=lambda: [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
    )

    # Histogram buckets for content sizes (in bytes)
    content_size_buckets: List[float] = field(
        default_factory=lambda: [
            1024,
            5120,
            10240,
            51200,
            102400,
            512000,
            1048576,  # 1KB to 1MB
        ]
    )


@dataclass
class AlertConfig:
    """Alert configuration with predefined rules."""

    rules: List[AlertRule] = field(
        default_factory=lambda: [
            # Scraping alerts
            AlertRule(
                name="HighScrapingFailureRate",
                expression='rate(scraper_requests_total{status="failed"}[5m]) > 0.5',
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                annotations={
                    "summary": "High scraping failure rate detected",
                    "description": "Scraping failure rate is above 50% for 5 minutes",
                },
            ),
            AlertRule(
                name="ScrapingSuccessRateLow",
                expression='(rate(scraper_requests_total{status="success"}[5m]) / rate(scraper_requests_total[5m])) < 0.8',
                duration="10m",
                severity=AlertSeverity.WARNING,
                annotations={
                    "summary": "Low scraping success rate",
                    "description": "Scraping success rate is below 80% for 10 minutes",
                },
            ),
            # Proxy alerts
            AlertRule(
                name="NoHealthyProxies",
                expression="proxy_healthy_count == 0",
                duration="1m",
                severity=AlertSeverity.CRITICAL,
                annotations={
                    "summary": "No healthy proxies available",
                    "description": "All proxies are marked as unhealthy",
                },
            ),
            AlertRule(
                name="LowHealthyProxyCount",
                expression="proxy_healthy_count < 3",
                duration="5m",
                severity=AlertSeverity.WARNING,
                annotations={
                    "summary": "Low number of healthy proxies",
                    "description": "Less than 3 healthy proxies available",
                },
            ),
            AlertRule(
                name="HighProxyFailureRate",
                expression='rate(proxy_requests_total{status="failed"}[5m]) > 0.3',
                duration="5m",
                severity=AlertSeverity.WARNING,
                annotations={
                    "summary": "High proxy failure rate",
                    "description": "Proxy failure rate is above 30% for 5 minutes",
                },
            ),
            # Rate limiting alerts
            AlertRule(
                name="HighRateLimitHits",
                expression="rate(rate_limit_hits_total[5m]) > 10",
                duration="5m",
                severity=AlertSeverity.WARNING,
                annotations={
                    "summary": "High rate limit hits",
                    "description": "Rate limiting is being triggered frequently",
                },
            ),
            # Performance alerts
            AlertRule(
                name="SlowResponseTime",
                expression="histogram_quantile(0.95, rate(scraper_response_time_seconds_bucket[5m])) > 10",
                duration="5m",
                severity=AlertSeverity.WARNING,
                annotations={
                    "summary": "Slow response times",
                    "description": "95th percentile response time is above 10 seconds",
                },
            ),
            AlertRule(
                name="HighMemoryUsage",
                expression="system_memory_usage_percent > 90",
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                annotations={
                    "summary": "High memory usage",
                    "description": "System memory usage is above 90%",
                },
            ),
            # Database alerts
            AlertRule(
                name="DatabaseConnectionFailures",
                expression="rate(database_connection_errors_total[5m]) > 0.1",
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                annotations={
                    "summary": "Database connection failures",
                    "description": "Database connection errors detected",
                },
            ),
            AlertRule(
                name="SlowDatabaseQueries",
                expression="histogram_quantile(0.95, rate(database_query_duration_seconds_bucket[5m])) > 5",
                duration="5m",
                severity=AlertSeverity.WARNING,
                annotations={
                    "summary": "Slow database queries",
                    "description": "95th percentile database query time is above 5 seconds",
                },
            ),
            # Session management alerts
            AlertRule(
                name="SessionExpired",
                expression="scraper_session_valid == 0",
                duration="1m",
                severity=AlertSeverity.WARNING,
                annotations={
                    "summary": "Scraper session expired",
                    "description": "The scraper session has expired and needs renewal",
                },
            ),
        ]
    )

    def get_rules_by_severity(self, severity: AlertSeverity) -> List[AlertRule]:
        """Get all rules of a specific severity."""
        return [rule for rule in self.rules if rule.severity == severity]

    def to_prometheus_config(self) -> Dict[str, Any]:
        """Convert to Prometheus alerting rules format."""
        return {
            "groups": [
                {
                    "name": "phoenix_mls_alerts",
                    "interval": "30s",
                    "rules": [rule.to_prometheus_rule() for rule in self.rules],
                }
            ]
        }
