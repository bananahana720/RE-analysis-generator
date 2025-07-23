# Phoenix MLS Scraper Monitoring

Comprehensive Prometheus-based monitoring and alerting system for the Phoenix MLS scraper.

## Overview

This monitoring system provides:
- **Real-time metrics** collection for scraper performance
- **Proxy health** monitoring and rotation tracking
- **Rate limiting** metrics and threshold alerts
- **Database operation** timing and error tracking
- **System resource** utilization monitoring
- **Session management** status tracking
- **Grafana dashboards** for visualization
- **Alertmanager integration** for notifications

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MLS Scraper   │────│  Metrics API    │────│   Prometheus    │
│                 │    │  (port 9090)    │    │   (port 9091)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │                       │
                                 │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Proxy Manager   │────│ Alert Manager   │────│     Grafana     │
│                 │    │  (port 9093)    │    │   (port 3000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Basic Setup

```python
from phoenix_real_estate.foundation.monitoring import (
    MetricsConfig,
    start_metrics_server,
    get_metrics_collector
)

# Configure metrics
config = MetricsConfig(
    enabled=True,
    port=9090,
    path="/metrics",
    labels={"service": "phoenix_mls", "environment": "production"}
)

# Start metrics server
exporter = await start_metrics_server(config)
print(f"Metrics available at http://localhost:9090/metrics")
```

### 2. Integrate with Scraper

```python
from phoenix_real_estate.collectors.phoenix_mls.metrics_integration import (
    metrics_integrated_scraper,
    metrics_integrated_proxy_manager
)

# Apply metrics decorators
@metrics_integrated_scraper
class MonitoredPhoenixMLSScraper(PhoenixMLSScraper):
    pass

@metrics_integrated_proxy_manager  
class MonitoredProxyManager(ProxyManager):
    pass

# Use monitored classes
scraper = MonitoredPhoenixMLSScraper(scraper_config, proxy_config)
```

### 3. Manual Metrics Collection

```python
# Get metrics collector
collector = get_metrics_collector()

# Record custom metrics
collector.scraper.record_request("success", "search", "GET")
collector.scraper.record_response_time(0.5, "search", "success")
collector.proxy.set_proxy_counts(total=5, healthy=3)
collector.rate_limit.record_rate_limit_hit("phoenix_mls", "limit", 2.0)
```

## Metrics Reference

### Scraper Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|---------|
| `scraper_requests_total` | Counter | Total scraping requests | status, endpoint, method |
| `scraper_response_time_seconds` | Histogram | Response time distribution | endpoint, status |
| `scraper_content_size_bytes` | Histogram | Content size distribution | endpoint, content_type |
| `scraper_properties_scraped_total` | Counter | Properties successfully scraped | zipcode, status |
| `scraper_errors_total` | Counter | Total errors by type | error_type, endpoint |
| `scraper_session_valid` | Gauge | Session validity (1=valid, 0=invalid) | - |
| `scraper_session_age_seconds` | Gauge | Current session age | - |
| `scraper_retries_total` | Counter | Retry attempts | endpoint, retry_number |

### Proxy Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|---------|
| `proxy_total_count` | Gauge | Total configured proxies | - |
| `proxy_healthy_count` | Gauge | Number of healthy proxies | - |
| `proxy_requests_total` | Counter | Proxy requests | proxy_id, status |
| `proxy_health_check_duration_seconds` | Histogram | Health check duration | proxy_id |
| `proxy_health_check_failures_total` | Counter | Health check failures | proxy_id, reason |
| `proxy_response_time_seconds` | Summary | Proxy response times | proxy_id |
| `proxy_rotations_total` | Counter | Total proxy rotations | - |
| `proxy_cooldown_active` | Gauge | Proxies in cooldown | - |

### Database Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|---------|
| `database_connections_active` | Gauge | Active connections | - |
| `database_connection_errors_total` | Counter | Connection errors | error_type |
| `database_queries_total` | Counter | Database queries | operation, collection, status |
| `database_query_duration_seconds` | Histogram | Query duration | operation, collection |
| `database_documents_total` | Counter | Documents processed | operation, collection |
| `database_collection_size_bytes` | Gauge | Collection size | collection |
| `database_collection_document_count` | Gauge | Document count | collection |

### System Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|---------|
| `system_cpu_usage_percent` | Gauge | CPU utilization | - |
| `system_memory_usage_percent` | Gauge | Memory utilization | - |
| `system_memory_used_bytes` | Gauge | Memory used | - |
| `system_disk_usage_percent` | Gauge | Disk utilization | path |
| `system_network_bytes_sent` | Counter | Network bytes sent | - |
| `system_network_bytes_received` | Counter | Network bytes received | - |
| `system_process_threads` | Gauge | Process thread count | - |
| `system_process_open_files` | Gauge | Open file descriptors | - |

### Rate Limit Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|---------|
| `rate_limit_hits_total` | Counter | Rate limit hits | endpoint, limit_type |
| `rate_limit_wait_time_seconds` | Histogram | Wait times | endpoint |
| `rate_limit_current_rate` | Gauge | Current request rate | endpoint |
| `rate_limit_limit_remaining` | Gauge | Remaining requests | endpoint |

## Alert Rules

### Critical Alerts

- **HighScrapingFailureRate**: Failure rate > 50% for 5 minutes
- **NoHealthyProxies**: All proxies unhealthy for 1 minute
- **HighMemoryUsage**: Memory usage > 90% for 5 minutes
- **DatabaseConnectionFailures**: Connection errors detected
- **ScraperNotResponding**: Metrics endpoint down for 5 minutes

### Warning Alerts

- **ScrapingSuccessRateLow**: Success rate < 80% for 10 minutes
- **LowHealthyProxyCount**: < 3 healthy proxies for 5 minutes
- **HighProxyFailureRate**: Proxy failure rate > 30%
- **HighRateLimitHits**: Rate limiting > 10 hits/min
- **SlowResponseTime**: 95th percentile > 10 seconds
- **SlowDatabaseQueries**: 95th percentile > 5 seconds
- **SessionExpired**: Session invalid for 1 minute

### Info Alerts

- **SessionAgeTooOld**: Session > 24 hours old
- **NoPropertiesScraped**: Zero properties in 1 hour

## Configuration Files

### Prometheus Configuration

```yaml
# config/monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'phoenix_mls_scraper'
    scrape_interval: 10s
    metrics_path: /metrics
    static_configs:
      - targets: ['localhost:9090']
        labels:
          environment: 'production'
          component: 'scraper'
```

### Alert Rules

```yaml
# config/monitoring/alerts.yml
groups:
  - name: phoenix_mls_alerts
    interval: 30s
    rules:
      - alert: HighScrapingFailureRate
        expr: rate(scraper_requests_total{status="failed"}[5m]) > 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High scraping failure rate detected"
          description: "Failure rate is {{ $value }}/sec"
```

### Alertmanager Configuration

```yaml
# config/monitoring/alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@phoenix-mls.local'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'critical-alerts'

receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'engineering@company.com'
        subject: '🚨 CRITICAL: Phoenix MLS Alert'
    slack_configs:
      - api_url: 'https://hooks.slack.com/...'
        channel: '#alerts-critical'
```

## Docker Deployment

### Docker Compose

```yaml
# config/monitoring/docker-compose.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9091:9090"]
    volumes:
      - "./prometheus.yml:/etc/prometheus/prometheus.yml"
      - "./alerts.yml:/etc/prometheus/alerts.yml"
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - "grafana_data:/var/lib/grafana"

  alertmanager:
    image: prom/alertmanager:latest
    ports: ["9093:9093"]
    volumes:
      - "./alertmanager.yml:/etc/alertmanager/config.yml"

volumes:
  grafana_data:
```

### Deployment Commands

```bash
# Start monitoring stack
cd config/monitoring
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f alertmanager

# Stop services
docker-compose down
```

## Grafana Dashboards

### Key Dashboards

1. **Scraper Performance**
   - Success rates and response times
   - Properties scraped over time
   - Error rates by type

2. **Proxy Health**
   - Healthy proxy count
   - Proxy rotation frequency
   - Health check failures

3. **System Resources**
   - CPU and memory usage
   - Disk utilization
   - Network traffic

4. **Rate Limiting**
   - Current rates vs limits
   - Rate limit hits over time
   - Wait times distribution

### Dashboard URLs

After starting the stack:
- Prometheus: http://localhost:9091
- Grafana: http://localhost:3000 (admin/admin)
- Alertmanager: http://localhost:9093

## Troubleshooting

### Common Issues

1. **Metrics not appearing**
   ```bash
   # Check if metrics server is running
   curl http://localhost:9090/metrics
   
   # Check Prometheus targets
   # Go to Prometheus UI -> Status -> Targets
   ```

2. **Alerts not firing**
   ```bash
   # Check alert rules syntax
   promtool check rules config/monitoring/alerts.yml
   
   # Check Prometheus rule evaluation
   # Go to Prometheus UI -> Alerts
   ```

3. **High memory usage**
   ```python
   # Reduce metric retention
   config = MetricsConfig(
       collection_interval=60,  # Collect less frequently
       retention_period=3600   # Shorter retention
   )
   ```

### Debugging Commands

```bash
# Test metric collection
python examples/monitoring_demo.py

# Validate configurations
promtool check config config/monitoring/prometheus.yml
promtool check rules config/monitoring/alerts.yml

# Check metrics endpoint
curl http://localhost:9090/metrics | grep scraper_requests_total

# Test alert routing
amtool config routes test --config.file=config/monitoring/alertmanager.yml
```

## Performance Considerations

### Resource Usage

- **Memory**: ~50MB baseline + ~1MB per 10k metrics
- **CPU**: ~2-5% during collection
- **Network**: ~10KB/s metrics traffic
- **Disk**: ~1GB/day for 30-day retention

### Optimization

```python
# Optimize for high-volume scraping
config = MetricsConfig(
    collection_interval=30,  # Less frequent collection
    response_time_buckets=[0.1, 0.5, 1.0, 5.0, 10.0],  # Fewer buckets
    content_size_buckets=[1024, 10240, 102400]  # Fewer buckets
)
```

## Best Practices

1. **Label Cardinality**: Keep label combinations reasonable (< 10k unique combinations)
2. **Metric Naming**: Use consistent prefixes (scraper_, proxy_, database_)
3. **Alert Fatigue**: Set appropriate thresholds and durations
4. **Dashboard Design**: Focus on actionable metrics
5. **Data Retention**: Balance between history and storage costs

## Integration Examples

### Custom Metrics

```python
from phoenix_real_estate.foundation.monitoring import get_metrics_collector

collector = get_metrics_collector()

# Record custom business metrics
collector.scraper.record_property_scraped("85001", "success") 
collector.proxy.record_health_check("proxy1", 0.5, True)
collector.database.record_query("insert", "properties", "success", 0.1)
```

### Decorator Usage

```python
from phoenix_real_estate.foundation.monitoring.metrics import metrics_decorator

@metrics_decorator(metric_type="request", labels={"endpoint": "custom"})
async def custom_scraping_function():
    # Function execution is automatically timed and recorded
    await scrape_data()
```

### Context Managers

```python
async def scrape_with_metrics():
    collector = get_metrics_collector()
    
    # Time database operations
    async with collector.database.time_query("insert", "properties"):
        await db.insert_property(data)
    
    # Time scraper requests  
    with collector.scraper.time_request("property_details"):
        data = await scrape_property(url)
```

## Support

For issues or questions:
1. Check the [troubleshooting](#troubleshooting) section
2. Review metric definitions and alert rules
3. Examine logs for configuration errors
4. Validate Prometheus and Alertmanager configs