# LLM Processing Monitoring Guide

This guide covers the comprehensive monitoring and launch setup for the Phoenix Real Estate LLM Processing Service.

## Quick Start

### 1. Launch the Service

```bash
# Start with full validation and monitoring
python scripts/launch_llm_processing.py

# The script will:
# - Validate all dependencies (MongoDB, Ollama, ports, memory)
# - Start the LLM processing service
# - Display monitoring endpoints
```

### 2. Check Status

```bash
# Live monitoring dashboard
python scripts/check_llm_status.py

# One-time status check
python scripts/check_llm_status.py --once
```

## Monitoring Endpoints

### Health Checks

- **Basic Health**: `http://localhost:8080/health`
  - Simple alive check
  - Returns 200 if service is running

- **Detailed Health**: `http://localhost:8080/health/detailed`
  - Comprehensive health status
  - Component health scores
  - Resource usage
  - System metrics

- **Component Health**: `http://localhost:8080/health/component/{component}`
  - Available components: `database`, `ollama`, `queue`, `resources`
  - Detailed status for specific components

### Metrics

- **Prometheus Metrics**: `http://localhost:8080/metrics`
  - All metrics in Prometheus format
  - Processing statistics
  - Resource usage
  - Performance metrics

## Prometheus Setup

### 1. Start Prometheus

```bash
# Windows
prometheus.exe --config.file=config/prometheus/prometheus.yml

# Linux/Mac
prometheus --config.file=config/prometheus/prometheus.yml
```

### 2. Access Prometheus UI

Open `http://localhost:9090` in your browser.

### 3. Key Metrics

```promql
# Success rate
sum(rate(llm_processing_requests_total{status="success"}[5m])) / sum(rate(llm_processing_requests_total[5m]))

# Processing latency (95th percentile)
histogram_quantile(0.95, rate(llm_processing_duration_seconds_bucket[5m]))

# Queue size
llm_processing_queue_size

# Memory usage
llm_memory_usage_bytes / (1024 * 1024)  # In MB

# Cache hit rate
sum(llm_cache_hits_total) / (sum(llm_cache_hits_total) + sum(llm_cache_misses_total))
```

## Grafana Dashboard

### 1. Import Dashboard

1. Open Grafana: `http://localhost:3000`
2. Go to Dashboards → Import
3. Upload: `config/grafana/dashboards/llm_processing_dashboard.json`

### 2. Dashboard Panels

- **Success Rate Gauge**: Overall processing success rate
- **Request Rate**: Requests per second by status
- **Queue Size**: Current processing queue size
- **Processing Duration**: 50th and 95th percentile latencies
- **Memory Usage**: Process memory vs limit
- **Cache Hit Rate**: LLM cache effectiveness
- **Circuit Breaker State**: Ollama connection health
- **Dead Letter Queue**: Failed items count

## Alerts

Configured alerts in `config/prometheus/alerts/llm_processing_alerts.yml`:

### Critical Alerts

- **LLMProcessingServiceDown**: Service unreachable for 2 minutes
- **OllamaServiceDown**: Ollama LLM service down for 2 minutes
- **ProcessingQueueFull**: Queue at 90%+ capacity
- **CriticalProcessingErrorRate**: Error rate above 25%
- **CriticalMemoryUsage**: Memory usage above 95% of limit

### Warning Alerts

- **HighProcessingLatency**: 95th percentile > 30 seconds
- **ProcessingQueueBacklog**: Queue > 50 items for 5 minutes
- **HighProcessingErrorRate**: Error rate above 10%
- **HighMemoryUsage**: Memory above 80% of limit
- **CircuitBreakerOpen**: LLM circuit breaker open

## Resource Monitoring

### Dynamic Resource Management

The system automatically adjusts based on resource pressure:

- **Memory Pressure**: Reduces batch sizes when memory > 70%
- **CPU Pressure**: Throttles concurrent operations when CPU > 80%
- **Queue Pressure**: Slows intake when queue > 50%

### Resource Limits

Default limits (configurable):
- **Memory**: 3GB maximum
- **CPU**: 80% maximum
- **Concurrent Operations**: 10 maximum
- **Queue Size**: 100 maximum

## Troubleshooting

### Service Won't Start

1. Check validation output from launch script
2. Verify MongoDB is running: `net start MongoDB`
3. Verify Ollama is running: `ollama serve`
4. Check port availability: `netstat -ano | findstr :8080`

### High Error Rate

1. Check Ollama health: `http://localhost:8080/health/component/ollama`
2. View circuit breaker state in metrics
3. Check dead letter queue size
4. Review logs for specific errors

### Memory Issues

1. Monitor memory usage: `http://localhost:8080/health/component/resources`
2. Check for memory leaks in metrics history
3. Reduce batch size or concurrent operations
4. Increase memory limit if needed

### Performance Issues

1. Check processing duration metrics
2. Review cache hit rate (should be > 30%)
3. Monitor CPU usage during processing
4. Check batch size optimization

## Best Practices

### 1. Regular Monitoring

- Keep status dashboard open during heavy processing
- Set up Prometheus alerts for critical thresholds
- Review Grafana dashboard daily

### 2. Capacity Planning

- Monitor peak usage patterns
- Plan for 20% headroom on resources
- Scale workers based on queue depth

### 3. Maintenance

- Clear dead letter queue weekly
- Review error patterns in logs
- Update Ollama models as needed
- Archive old metrics data

## Configuration

### Environment Variables

```bash
# Processing limits
LLM_MAX_WORKERS=2
LLM_QUEUE_SIZE=100
LLM_MEMORY_LIMIT_MB=3072

# Monitoring
PROMETHEUS_RETENTION_DAYS=30
METRICS_ENABLED=true
RESOURCE_MONITORING_ENABLED=true
```

### Service Configuration

Edit `config/processing.yaml`:

```yaml
processing:
  workers: 2
  queue_size: 100
  batch_size: 10
  timeout: 60

monitoring:
  prometheus:
    enabled: true
    port: 8080
  alerts:
    email: admin@example.com
  resource_limits:
    memory_mb: 3072
    cpu_percent: 80
```

## Integration with CI/CD

### Health Check in Deploy Script

```bash
# Wait for service to be healthy
timeout=60
while [ $timeout -gt 0 ]; do
  if curl -f http://localhost:8080/health/detailed; then
    echo "Service is healthy"
    break
  fi
  sleep 5
  timeout=$((timeout - 5))
done
```

### Monitoring in Production

1. Use external monitoring service (e.g., Datadog, New Relic)
2. Set up PagerDuty integration for critical alerts
3. Configure log aggregation (ELK stack)
4. Enable distributed tracing for debugging