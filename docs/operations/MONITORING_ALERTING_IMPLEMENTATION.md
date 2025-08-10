# Phoenix Real Estate Data Collection System
## Monitoring & Alerting Implementation Guide

**Version**: 1.0  
**Effective Date**: August 6, 2025  
**Classification**: Production Operations Infrastructure  
**Target Audience**: Operations Team, DevOps Engineers, Technical Staff

---

## 📊 MONITORING ARCHITECTURE OVERVIEW

### Comprehensive Monitoring Stack
```yaml
Monitoring Infrastructure:
  Metrics Collection: Prometheus (primary), Custom Python metrics
  Visualization: Grafana dashboards with real-time updates
  Alerting: Grafana Alerting + Email/Slack integration
  Log Management: Structured logging with rotation and archival
  Health Checks: Custom health monitoring with automated response
  
Integration Points:
  Application Metrics: Phoenix Real Estate collector application
  System Metrics: OS-level resource monitoring
  External Services: API response times and success rates
  Business Metrics: Collection success, data quality, cost tracking
  
Dashboard Categories:
  1. Executive Dashboard: High-level KPIs and business metrics
  2. Operational Dashboard: Real-time system performance and alerts  
  3. Performance Dashboard: Detailed technical metrics and trends
  4. Business Intelligence Dashboard: Market data and analytics
```

### Monitoring Data Flow Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Application   │───▶│     Metrics      │───▶│   Prometheus    │
│   Components    │    │   Collection     │    │    Server       │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • Data Collector│    │ • Custom metrics │    │ • Time series   │
│ • LLM Processor │    │ • Health checks  │    │ • Data storage  │
│ • Database Ops  │    │ • Performance    │    │ • Query engine  │
│ • Email Service │    │ • Business KPIs  │    │ • Alert rules   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Log Files     │    │     Grafana      │    │   Alert         │
│   & Audit       │    │   Dashboards     │    │   Manager       │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • App logs      │    │ • Real-time viz  │    │ • Email alerts  │
│ • Error logs    │    │ • Custom panels  │    │ • Slack notify  │
│ • Audit trail   │    │ • Alert views    │    │ • Escalation    │
│ • Performance   │    │ • Drill-downs    │    │ • Resolution    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 🚀 MONITORING INFRASTRUCTURE SETUP

### Prerequisites and Dependencies
```bash
# Install monitoring infrastructure dependencies
# Note: These would typically be installed on monitoring server

# Prometheus installation (Linux/Windows)
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-2.45.0.linux-amd64.tar.gz
sudo mv prometheus-2.45.0.linux-amd64/prometheus /usr/local/bin/
sudo mv prometheus-2.45.0.linux-amd64/promtool /usr/local/bin/

# Grafana installation
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana

# Start monitoring services
sudo systemctl start prometheus
sudo systemctl start grafana-server
sudo systemctl enable prometheus
sudo systemctl enable grafana-server
```

### Monitoring Infrastructure Deployment
```bash
# Deploy monitoring infrastructure (automated)
echo "Deploying production monitoring infrastructure..."

# 1. Setup monitoring configuration
uv run python scripts/deploy/setup_monitoring.py --production-deployment

# 2. Deploy Prometheus configuration
uv run python scripts/deploy/deploy_prometheus.py --configuration-file=config/monitoring/prometheus.yml

# 3. Deploy Grafana dashboards
uv run python scripts/deploy/deploy_production_monitoring.py --all-dashboards

# 4. Configure alerting rules
uv run python scripts/deploy/alert_configurator.py --setup-production-alerts

# 5. Validate monitoring infrastructure
uv run python scripts/deploy/monitoring_validator.py --comprehensive-validation

# 6. Start monitoring services
uv run python scripts/deploy/monitoring_services.py --start-all-services
```

### Monitoring Service Configuration

#### Prometheus Configuration (`config/monitoring/prometheus.yml`)
```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s
  external_labels:
    monitor: 'phoenix-real-estate'
    environment: 'production'

rule_files:
  - "alert_rules.yml"
  - "recording_rules.yml"

scrape_configs:
  - job_name: 'phoenix-real-estate-app'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 30s
    metrics_path: '/metrics'
    
  - job_name: 'system-metrics'
    static_configs:
      - targets: ['localhost:9100']  # Node Exporter
    scrape_interval: 60s
    
  - job_name: 'mongodb-metrics'
    static_configs:
      - targets: ['localhost:9216']  # MongoDB Exporter
    scrape_interval: 60s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

# Custom recording rules for business metrics
recording_rules:
  - name: phoenix_real_estate_business_metrics
    rules:
      - record: phoenix:collection_success_rate_5m
        expr: rate(phoenix_collections_successful_total[5m]) / rate(phoenix_collections_total[5m])
      
      - record: phoenix:processing_rate_5m  
        expr: rate(phoenix_properties_processed_total[5m])
      
      - record: phoenix:error_rate_5m
        expr: rate(phoenix_errors_total[5m]) / rate(phoenix_requests_total[5m])
      
      - record: phoenix:cost_per_property_daily
        expr: increase(phoenix_daily_cost[24h]) / increase(phoenix_properties_collected_total[24h])
```

#### Grafana Dashboard Configuration
```python
# Automated dashboard deployment script
import json
import requests
from typing import Dict, List

class GrafanaDashboardDeployer:
    def __init__(self, grafana_url: str = "http://localhost:3000", api_key: str = None):
        self.grafana_url = grafana_url
        self.api_key = api_key or "admin"  # Default for local development
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def deploy_executive_dashboard(self) -> Dict:
        """Deploy executive-level dashboard with high-level KPIs"""
        dashboard_config = {
            "dashboard": {
                "title": "Phoenix Real Estate - Executive Dashboard",
                "tags": ["phoenix-real-estate", "executive", "production"],
                "timezone": "America/Phoenix",
                "refresh": "5m",
                "time": {"from": "now-24h", "to": "now"},
                
                "panels": [
                    {
                        "title": "System Status Overview",
                        "type": "stat",
                        "targets": [
                            {"expr": "phoenix:collection_success_rate_5m", "legendFormat": "Success Rate"},
                            {"expr": "up{job='phoenix-real-estate-app'}", "legendFormat": "System Uptime"},
                            {"expr": "phoenix:cost_per_property_daily", "legendFormat": "Cost Efficiency"}
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 0.8},
                                        {"color": "green", "value": 0.95}
                                    ]
                                },
                                "unit": "percent"
                            }
                        }
                    },
                    {
                        "title": "Daily Collection Performance",
                        "type": "timeseries", 
                        "targets": [
                            {"expr": "phoenix:processing_rate_5m * 3600", "legendFormat": "Properties/Hour"},
                            {"expr": "phoenix:collection_success_rate_5m * 100", "legendFormat": "Success Rate %"}
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "custom": {"drawStyle": "line", "lineWidth": 2},
                                "color": {"mode": "palette-classic"}
                            }
                        }
                    },
                    {
                        "title": "Cost and Budget Tracking",
                        "type": "gauge",
                        "targets": [
                            {"expr": "phoenix_budget_utilization_percentage", "legendFormat": "Budget Used"}
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "min": 0,
                                "max": 100,
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 60},
                                        {"color": "orange", "value": 80},
                                        {"color": "red", "value": 95}
                                    ]
                                },
                                "unit": "percent"
                            }
                        }
                    }
                ]
            },
            "overwrite": True
        }
        
        return self._deploy_dashboard(dashboard_config)
    
    def deploy_operational_dashboard(self) -> Dict:
        """Deploy operational dashboard with detailed system metrics"""
        dashboard_config = {
            "dashboard": {
                "title": "Phoenix Real Estate - Operations Dashboard", 
                "tags": ["phoenix-real-estate", "operations", "production"],
                "timezone": "America/Phoenix",
                "refresh": "1m",
                "time": {"from": "now-4h", "to": "now"},
                
                "panels": [
                    {
                        "title": "Real-time Collection Status",
                        "type": "table",
                        "targets": [
                            {
                                "expr": "phoenix_collection_status by (zip_code)",
                                "legendFormat": "{{zip_code}}",
                                "format": "table"
                            }
                        ],
                        "transformations": [
                            {
                                "id": "organize",
                                "options": {
                                    "columns": {
                                        "zip_code": {"displayName": "ZIP Code"},
                                        "Value": {"displayName": "Status"}
                                    }
                                }
                            }
                        ]
                    },
                    {
                        "title": "Error Rate Trends",
                        "type": "timeseries",
                        "targets": [
                            {"expr": "phoenix:error_rate_5m * 100", "legendFormat": "Error Rate %"},
                            {"expr": "rate(phoenix_errors_total[5m])", "legendFormat": "Errors/sec"}
                        ],
                        "alert": {
                            "conditions": [
                                {
                                    "query": {"params": ["A", "5m", "now"]},
                                    "reducer": {"params": [], "type": "last"},
                                    "evaluator": {"params": [10], "type": "gt"}
                                }
                            ],
                            "executionErrorState": "alerting",
                            "frequency": "10s",
                            "handler": 1,
                            "name": "High Error Rate Alert",
                            "noDataState": "no_data"
                        }
                    },
                    {
                        "title": "System Resource Utilization",
                        "type": "timeseries",
                        "targets": [
                            {"expr": "100 - (avg(irate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)", "legendFormat": "CPU Usage %"},
                            {"expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100", "legendFormat": "Memory Usage %"},
                            {"expr": "100 - ((node_filesystem_avail_bytes{mountpoint='/'} * 100) / node_filesystem_size_bytes{mountpoint='/'})", "legendFormat": "Disk Usage %"}
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "max": 100,
                                "min": 0,
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 70},
                                        {"color": "red", "value": 85}
                                    ]
                                },
                                "unit": "percent"
                            }
                        }
                    }
                ]
            },
            "overwrite": True
        }
        
        return self._deploy_dashboard(dashboard_config)
    
    def deploy_performance_dashboard(self) -> Dict:
        """Deploy technical performance dashboard"""
        dashboard_config = {
            "dashboard": {
                "title": "Phoenix Real Estate - Performance Dashboard",
                "tags": ["phoenix-real-estate", "performance", "technical"],
                "timezone": "America/Phoenix", 
                "refresh": "30s",
                "time": {"from": "now-2h", "to": "now"},
                
                "panels": [
                    {
                        "title": "API Response Times",
                        "type": "timeseries",
                        "targets": [
                            {"expr": "histogram_quantile(0.50, phoenix_api_request_duration_seconds_bucket)", "legendFormat": "50th percentile"},
                            {"expr": "histogram_quantile(0.95, phoenix_api_request_duration_seconds_bucket)", "legendFormat": "95th percentile"},
                            {"expr": "histogram_quantile(0.99, phoenix_api_request_duration_seconds_bucket)", "legendFormat": "99th percentile"}
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "s",
                                "custom": {"drawStyle": "line", "lineWidth": 1}
                            }
                        }
                    },
                    {
                        "title": "Database Performance",
                        "type": "timeseries",
                        "targets": [
                            {"expr": "mongodb_op_latencies_histogram_micros{type='read'}", "legendFormat": "Read Latency"},
                            {"expr": "mongodb_op_latencies_histogram_micros{type='write'}", "legendFormat": "Write Latency"},
                            {"expr": "rate(mongodb_operations_total[5m])", "legendFormat": "Operations/sec"}
                        ]
                    },
                    {
                        "title": "LLM Processing Performance", 
                        "type": "timeseries",
                        "targets": [
                            {"expr": "phoenix_llm_processing_duration_seconds", "legendFormat": "Processing Time"},
                            {"expr": "rate(phoenix_llm_requests_total[5m])", "legendFormat": "Requests/sec"},
                            {"expr": "phoenix_llm_batch_size", "legendFormat": "Batch Size"}
                        ]
                    }
                ]
            },
            "overwrite": True
        }
        
        return self._deploy_dashboard(dashboard_config)
    
    def deploy_business_intelligence_dashboard(self) -> Dict:
        """Deploy business intelligence and analytics dashboard"""
        dashboard_config = {
            "dashboard": {
                "title": "Phoenix Real Estate - Business Intelligence", 
                "tags": ["phoenix-real-estate", "business", "analytics"],
                "timezone": "America/Phoenix",
                "refresh": "15m",
                "time": {"from": "now-7d", "to": "now"},
                
                "panels": [
                    {
                        "title": "Data Collection Volume Trends",
                        "type": "timeseries",
                        "targets": [
                            {"expr": "increase(phoenix_properties_collected_total[1d])", "legendFormat": "Daily Collections"},
                            {"expr": "phoenix_data_value_generated_daily", "legendFormat": "Data Value ($)"}
                        ]
                    },
                    {
                        "title": "Market Coverage Analysis",
                        "type": "piechart",
                        "targets": [
                            {"expr": "phoenix_properties_by_zip_code", "legendFormat": "{{zip_code}}"}
                        ]
                    },
                    {
                        "title": "ROI and Value Metrics",
                        "type": "stat",
                        "targets": [
                            {"expr": "phoenix_roi_percentage", "legendFormat": "ROI %"},
                            {"expr": "phoenix_cost_per_property", "legendFormat": "Cost/Property"},
                            {"expr": "phoenix_value_per_property", "legendFormat": "Value/Property"}
                        ]
                    }
                ]
            },
            "overwrite": True
        }
        
        return self._deploy_dashboard(dashboard_config)
    
    def _deploy_dashboard(self, dashboard_config: Dict) -> Dict:
        """Deploy dashboard configuration to Grafana"""
        url = f"{self.grafana_url}/api/dashboards/db"
        
        try:
            response = requests.post(url, json=dashboard_config, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error deploying dashboard: {e}")
            return {"error": str(e)}

# Deployment script usage
def deploy_all_dashboards():
    """Deploy all monitoring dashboards"""
    deployer = GrafanaDashboardDeployer()
    
    dashboards = [
        ("Executive", deployer.deploy_executive_dashboard),
        ("Operational", deployer.deploy_operational_dashboard), 
        ("Performance", deployer.deploy_performance_dashboard),
        ("Business Intelligence", deployer.deploy_business_intelligence_dashboard)
    ]
    
    results = {}
    for name, deploy_func in dashboards:
        print(f"Deploying {name} dashboard...")
        result = deploy_func()
        results[name] = result
        if "error" not in result:
            print(f"✅ {name} dashboard deployed successfully")
        else:
            print(f"❌ {name} dashboard deployment failed: {result['error']}")
    
    return results
```

---

## 🔔 ALERTING SYSTEM CONFIGURATION

### Alert Rule Definitions

#### Critical Production Alerts
```yaml
# config/monitoring/alert_rules.yml
groups:
  - name: phoenix_real_estate_critical
    rules:
      - alert: SystemDown
        expr: up{job="phoenix-real-estate-app"} == 0
        for: 5m
        labels:
          severity: critical
          service: phoenix-real-estate
        annotations:
          summary: "Phoenix Real Estate system is down"
          description: "The Phoenix Real Estate application has been down for more than 5 minutes"
          runbook_url: "https://docs.phoenix-re.com/runbooks/system-down"
      
      - alert: HighErrorRate
        expr: phoenix:error_rate_5m > 0.25
        for: 10m
        labels:
          severity: critical
          service: phoenix-real-estate
        annotations:
          summary: "High error rate detected (>25%)"
          description: "Error rate is {{ $value | humanizePercentage }} for more than 10 minutes"
          runbook_url: "https://docs.phoenix-re.com/runbooks/high-error-rate"
      
      - alert: BudgetExceeded
        expr: phoenix_budget_utilization_percentage > 95
        for: 0m
        labels:
          severity: critical
          service: phoenix-real-estate
        annotations:
          summary: "Budget utilization critical (>95%)"
          description: "Monthly budget utilization is {{ $value }}% - immediate action required"
          runbook_url: "https://docs.phoenix-re.com/runbooks/budget-exceeded"
      
      - alert: CollectionFailure
        expr: phoenix:collection_success_rate_5m < 0.5
        for: 30m
        labels:
          severity: critical
          service: phoenix-real-estate
        annotations:
          summary: "Collection success rate critically low (<50%)"
          description: "Data collection success rate is {{ $value | humanizePercentage }} for 30+ minutes"
          runbook_url: "https://docs.phoenix-re.com/runbooks/collection-failure"

  - name: phoenix_real_estate_warning
    rules:
      - alert: HighResourceUsage
        expr: |
          (
            100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 70
          ) or (
            (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 75
          )
        for: 15m
        labels:
          severity: warning
          service: phoenix-real-estate
        annotations:
          summary: "High resource utilization detected"
          description: "CPU or Memory usage is high for more than 15 minutes"
          runbook_url: "https://docs.phoenix-re.com/runbooks/high-resource-usage"
      
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, phoenix_api_request_duration_seconds_bucket) > 5
        for: 10m
        labels:
          severity: warning
          service: phoenix-real-estate
        annotations:
          summary: "API response times are slow"
          description: "95th percentile response time is {{ $value }}s for 10+ minutes"
          runbook_url: "https://docs.phoenix-re.com/runbooks/slow-response-time"
      
      - alert: BudgetWarning
        expr: phoenix_budget_utilization_percentage > 80
        for: 1h
        labels:
          severity: warning
          service: phoenix-real-estate
        annotations:
          summary: "Budget utilization warning (>80%)"
          description: "Monthly budget utilization is {{ $value }}% - review and optimize"
          runbook_url: "https://docs.phoenix-re.com/runbooks/budget-warning"
      
      - alert: DataQualityDegradation
        expr: phoenix_data_quality_score < 0.9
        for: 2h
        labels:
          severity: warning
          service: phoenix-real-estate
        annotations:
          summary: "Data quality score below threshold"
          description: "Data quality score is {{ $value | humanizePercentage }} for 2+ hours"
          runbook_url: "https://docs.phoenix-re.com/runbooks/data-quality-issues"

  - name: phoenix_real_estate_info
    rules:
      - alert: OptimizationOpportunity
        expr: phoenix_processing_efficiency < 0.8
        for: 4h
        labels:
          severity: info
          service: phoenix-real-estate
        annotations:
          summary: "Processing efficiency optimization opportunity"
          description: "Processing efficiency is {{ $value | humanizePercentage }} - consider optimization"
          runbook_url: "https://docs.phoenix-re.com/runbooks/optimization-opportunities"
      
      - alert: CollectionVolumeChange
        expr: |
          (
            increase(phoenix_properties_collected_total[1d]) / 
            increase(phoenix_properties_collected_total[1d] offset 1d)
          ) - 1 > 0.5 or (
            increase(phoenix_properties_collected_total[1d]) / 
            increase(phoenix_properties_collected_total[1d] offset 1d)
          ) - 1 < -0.5
        for: 0m
        labels:
          severity: info
          service: phoenix-real-estate
        annotations:
          summary: "Significant change in collection volume"
          description: "Daily collection volume changed by more than 50% compared to yesterday"
          runbook_url: "https://docs.phoenix-re.com/runbooks/volume-changes"
```

### Alert Manager Configuration
```yaml
# config/monitoring/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@phoenix-real-estate.com'
  smtp_auth_username: 'alerts@phoenix-real-estate.com'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default-receiver'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 10s
      repeat_interval: 15m
      
    - match:
        severity: warning  
      receiver: 'warning-alerts'
      group_wait: 30s
      repeat_interval: 1h
      
    - match:
        severity: info
      receiver: 'info-alerts'
      repeat_interval: 12h

receivers:
  - name: 'default-receiver'
    email_configs:
      - to: 'operations@phoenix-real-estate.com'
        subject: 'Phoenix Real Estate Alert: {{ .GroupLabels.alertname }}'
        body: |
          Alert Details:
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Severity: {{ .Labels.severity }}
          Service: {{ .Labels.service }}
          Started: {{ .StartsAt.Format "2006-01-02 15:04:05 MST" }}
          {{ if .Annotations.runbook_url }}
          Runbook: {{ .Annotations.runbook_url }}
          {{ end }}
          {{ end }}
  
  - name: 'critical-alerts'
    email_configs:
      - to: 'operations@phoenix-real-estate.com,management@phoenix-real-estate.com'
        subject: 'CRITICAL: Phoenix Real Estate - {{ .GroupLabels.alertname }}'
        body: |
          🚨 CRITICAL ALERT 🚨
          
          This is a critical alert requiring immediate attention.
          
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Started: {{ .StartsAt.Format "2006-01-02 15:04:05 MST" }}
          Duration: {{ .StartsAt | since }}
          
          IMMEDIATE ACTION REQUIRED
          {{ if .Annotations.runbook_url }}
          Runbook: {{ .Annotations.runbook_url }}
          {{ end }}
          {{ end }}
          
          Contact: operations@phoenix-real-estate.com
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#phoenix-real-estate-alerts'
        title: 'CRITICAL: Phoenix Real Estate Alert'
        text: |
          🚨 *CRITICAL ALERT* 🚨
          {{ range .Alerts }}
          *{{ .Annotations.summary }}*
          {{ .Annotations.description }}
          {{ end }}
        
  - name: 'warning-alerts'
    email_configs:
      - to: 'operations@phoenix-real-estate.com'
        subject: 'WARNING: Phoenix Real Estate - {{ .GroupLabels.alertname }}'
        body: |
          ⚠️ WARNING ALERT ⚠️
          
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Started: {{ .StartsAt.Format "2006-01-02 15:04:05 MST" }}
          {{ if .Annotations.runbook_url }}
          Runbook: {{ .Annotations.runbook_url }}
          {{ end }}
          {{ end }}
          
          Please investigate and resolve within SLA timeframe.
        
  - name: 'info-alerts'
    email_configs:
      - to: 'operations@phoenix-real-estate.com'
        subject: 'INFO: Phoenix Real Estate - {{ .GroupLabels.alertname }}'
        body: |
          ℹ️ INFORMATION ALERT ℹ️
          
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
          
          This is informational and can be addressed during normal business hours.
```

---

## 📈 CUSTOM METRICS IMPLEMENTATION

### Application Metrics Collection
```python
# src/phoenix_real_estate/foundation/metrics.py
import time
from typing import Dict, Optional
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
import asyncio
import logging

logger = logging.getLogger(__name__)

class PhoenixMetricsCollector:
    """Comprehensive metrics collector for Phoenix Real Estate system"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._initialize_metrics()
        
    def _initialize_metrics(self):
        """Initialize all application metrics"""
        
        # Collection Performance Metrics
        self.collections_total = Counter(
            'phoenix_collections_total',
            'Total number of collection attempts',
            ['zip_code', 'source'],
            registry=self.registry
        )
        
        self.collections_successful = Counter(
            'phoenix_collections_successful_total', 
            'Total number of successful collections',
            ['zip_code', 'source'],
            registry=self.registry
        )
        
        self.properties_collected = Counter(
            'phoenix_properties_collected_total',
            'Total number of properties collected',
            ['zip_code', 'property_type'],
            registry=self.registry
        )
        
        self.collection_duration = Histogram(
            'phoenix_collection_duration_seconds',
            'Time spent on collection operations',
            ['zip_code', 'source'],
            registry=self.registry,
            buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
        )
        
        # LLM Processing Metrics
        self.llm_requests_total = Counter(
            'phoenix_llm_requests_total',
            'Total LLM processing requests',
            ['model', 'operation'],
            registry=self.registry
        )
        
        self.llm_processing_duration = Histogram(
            'phoenix_llm_processing_duration_seconds',
            'LLM processing time per request',
            ['model'],
            registry=self.registry,
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
        )
        
        self.llm_batch_size = Gauge(
            'phoenix_llm_batch_size',
            'Current LLM processing batch size',
            registry=self.registry
        )
        
        # API Performance Metrics
        self.api_requests_total = Counter(
            'phoenix_api_requests_total',
            'Total API requests made',
            ['api', 'method', 'status'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'phoenix_api_request_duration_seconds',
            'API request response time',
            ['api', 'method'],
            registry=self.registry,
            buckets=[0.1, 0.2, 0.5, 1, 2, 5, 10, 30]
        )
        
        # Database Metrics
        self.database_operations_total = Counter(
            'phoenix_database_operations_total',
            'Total database operations',
            ['operation', 'collection'],
            registry=self.registry
        )
        
        self.database_operation_duration = Histogram(
            'phoenix_database_operation_duration_seconds',
            'Database operation duration',
            ['operation', 'collection'],
            registry=self.registry,
            buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5]
        )
        
        # Business Metrics
        self.data_quality_score = Gauge(
            'phoenix_data_quality_score',
            'Overall data quality score (0-1)',
            registry=self.registry
        )
        
        self.processing_efficiency = Gauge(
            'phoenix_processing_efficiency',
            'Processing efficiency ratio (0-1)',
            registry=self.registry
        )
        
        self.daily_cost = Gauge(
            'phoenix_daily_cost',
            'Current daily operational cost in USD',
            registry=self.registry
        )
        
        self.budget_utilization = Gauge(
            'phoenix_budget_utilization_percentage',
            'Monthly budget utilization percentage',
            registry=self.registry
        )
        
        # System Health Metrics
        self.system_health_score = Gauge(
            'phoenix_system_health_score',
            'Overall system health score (0-1)',
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'phoenix_active_connections',
            'Number of active connections',
            ['service'],
            registry=self.registry
        )
        
        # Error Metrics
        self.errors_total = Counter(
            'phoenix_errors_total',
            'Total number of errors',
            ['component', 'error_type'],
            registry=self.registry
        )
        
        # System Info
        self.build_info = Info(
            'phoenix_build_info',
            'Phoenix Real Estate build information',
            registry=self.registry
        )
        
    def record_collection_attempt(self, zip_code: str, source: str, success: bool, duration: float):
        """Record a collection attempt with timing and success status"""
        self.collections_total.labels(zip_code=zip_code, source=source).inc()
        self.collection_duration.labels(zip_code=zip_code, source=source).observe(duration)
        
        if success:
            self.collections_successful.labels(zip_code=zip_code, source=source).inc()
            
    def record_properties_collected(self, zip_code: str, property_type: str, count: int):
        """Record the number of properties collected"""
        self.properties_collected.labels(zip_code=zip_code, property_type=property_type).inc(count)
        
    def record_llm_processing(self, model: str, operation: str, duration: float, batch_size: int):
        """Record LLM processing metrics"""
        self.llm_requests_total.labels(model=model, operation=operation).inc()
        self.llm_processing_duration.labels(model=model).observe(duration)
        self.llm_batch_size.set(batch_size)
        
    def record_api_request(self, api: str, method: str, status: str, duration: float):
        """Record API request metrics"""
        self.api_requests_total.labels(api=api, method=method, status=status).inc()
        self.api_request_duration.labels(api=api, method=method).observe(duration)
        
    def record_database_operation(self, operation: str, collection: str, duration: float):
        """Record database operation metrics"""
        self.database_operations_total.labels(operation=operation, collection=collection).inc()
        self.database_operation_duration.labels(operation=operation, collection=collection).observe(duration)
        
    def update_business_metrics(self, data_quality: float, efficiency: float, daily_cost: float, budget_util: float):
        """Update business-level metrics"""
        self.data_quality_score.set(data_quality)
        self.processing_efficiency.set(efficiency)
        self.daily_cost.set(daily_cost)
        self.budget_utilization.set(budget_util)
        
    def update_system_health(self, health_score: float):
        """Update overall system health score"""
        self.system_health_score.set(health_score)
        
    def record_error(self, component: str, error_type: str):
        """Record system errors by component and type"""
        self.errors_total.labels(component=component, error_type=error_type).inc()
        
    def set_active_connections(self, service: str, count: int):
        """Set the number of active connections for a service"""
        self.active_connections.labels(service=service).set(count)
        
    def set_build_info(self, version: str, commit: str, build_date: str):
        """Set build information"""
        self.build_info.info({
            'version': version,
            'commit': commit,
            'build_date': build_date
        })
        
    def get_metrics(self) -> str:
        """Get current metrics in Prometheus format"""
        return generate_latest(self.registry)

# Global metrics instance
metrics = PhoenixMetricsCollector()

# Decorator for automatic timing
def time_operation(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to automatically time operations and record metrics"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            finally:
                duration = time.time() - start_time
                if metric_name == 'collection':
                    metrics.record_collection_attempt(
                        labels.get('zip_code', 'unknown'),
                        labels.get('source', 'unknown'),
                        success,
                        duration
                    )
                elif metric_name == 'api':
                    metrics.record_api_request(
                        labels.get('api', 'unknown'),
                        labels.get('method', 'unknown'),
                        'success' if success else 'error',
                        duration
                    )
                
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                duration = time.time() - start_time
                # Record metrics based on metric_name
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Usage example:
# @time_operation('collection', {'zip_code': '85031', 'source': 'maricopa'})
# async def collect_maricopa_data(zip_code: str):
#     # Implementation here
#     pass
```

### Health Check Endpoint Implementation
```python
# src/phoenix_real_estate/foundation/health.py
import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import aiohttp
import pymongo
from .metrics import metrics
from .config import EnvironmentConfigProvider

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    response_time: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class HealthChecker:
    """Comprehensive health checking for all system components"""
    
    def __init__(self, config: EnvironmentConfigProvider):
        self.config = config
        self.checks = {
            'database': self._check_database,
            'llm_service': self._check_llm_service,
            'external_apis': self._check_external_apis,
            'email_service': self._check_email_service,
            'system_resources': self._check_system_resources
        }
        
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks and return results"""
        results = {}
        
        # Run all checks concurrently
        tasks = {name: check() for name, check in self.checks.items()}
        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        for name, result in zip(tasks.keys(), completed):
            if isinstance(result, Exception):
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=0.0,
                    error=str(result)
                )
            else:
                results[name] = result
                
        # Calculate overall system health score
        self._calculate_system_health(results)
        
        return results
        
    async def _check_database(self) -> HealthCheckResult:
        """Check MongoDB database connectivity and performance"""
        start_time = time.time()
        
        try:
            # Get database connection
            mongodb_url = self.config.get_mongodb_url()
            client = pymongo.MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
            
            # Test basic connectivity
            client.admin.command('ping')
            
            # Test performance with a simple query
            db = client[self.config.get_database_name()]
            collection = db.properties
            collection.find_one()
            
            response_time = time.time() - start_time
            
            # Get database stats
            db_stats = db.command('dbstats')
            
            return HealthCheckResult(
                name='database',
                status=HealthStatus.HEALTHY if response_time < 1.0 else HealthStatus.DEGRADED,
                response_time=response_time,
                details={
                    'collections': db_stats.get('collections', 0),
                    'data_size_mb': round(db_stats.get('dataSize', 0) / (1024*1024), 2),
                    'index_size_mb': round(db_stats.get('indexSize', 0) / (1024*1024), 2)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='database',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error=str(e)
            )
            
    async def _check_llm_service(self) -> HealthCheckResult:
        """Check Ollama LLM service availability and performance"""
        start_time = time.time()
        
        try:
            ollama_host = self.config.get('OLLAMA_HOST', 'http://localhost:11434')
            
            async with aiohttp.ClientSession() as session:
                # Check service availability
                async with session.get(f'{ollama_host}/api/tags', timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        raise Exception(f"LLM service returned status {response.status}")
                    
                    tags_data = await response.json()
                    
                # Test model availability
                model_name = self.config.get('OLLAMA_MODEL', 'llama3.2:latest')
                test_payload = {
                    'model': model_name,
                    'prompt': 'Test prompt',
                    'stream': False
                }
                
                async with session.post(
                    f'{ollama_host}/api/generate',
                    json=test_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"LLM generation failed with status {response.status}")
                        
                    generation_data = await response.json()
                    
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name='llm_service',
                status=HealthStatus.HEALTHY if response_time < 30.0 else HealthStatus.DEGRADED,
                response_time=response_time,
                details={
                    'models_available': len(tags_data.get('models', [])),
                    'active_model': model_name,
                    'generation_successful': 'response' in generation_data
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='llm_service',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error=str(e)
            )
            
    async def _check_external_apis(self) -> HealthCheckResult:
        """Check external API connectivity and rate limits"""
        start_time = time.time()
        api_results = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check Maricopa County API
                try:
                    maricopa_url = "https://api.maricopa.county/data/assessor/parcel"
                    async with session.get(
                        maricopa_url,
                        params={'limit': 1},
                        headers={'AUTHORIZATION': self.config.get('MARICOPA_API_KEY', '')},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        api_results['maricopa'] = {
                            'status': response.status,
                            'response_time': time.time() - start_time
                        }
                except Exception as e:
                    api_results['maricopa'] = {'error': str(e)}
                
                # Check WebShare proxy service
                try:
                    proxy_health_url = "https://proxy.webshare.io/api/proxy/status/"
                    async with session.get(
                        proxy_health_url,
                        headers={'Authorization': f"Token {self.config.get('WEBSHARE_API_KEY', '')}"},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        api_results['webshare'] = {
                            'status': response.status,
                            'response_time': time.time() - start_time
                        }
                except Exception as e:
                    api_results['webshare'] = {'error': str(e)}
            
            response_time = time.time() - start_time
            
            # Determine overall API health
            healthy_apis = sum(1 for result in api_results.values() if isinstance(result, dict) and result.get('status') == 200)
            total_apis = len(api_results)
            
            if healthy_apis == total_apis:
                status = HealthStatus.HEALTHY
            elif healthy_apis > 0:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                name='external_apis',
                status=status,
                response_time=response_time,
                details={
                    'apis_checked': total_apis,
                    'apis_healthy': healthy_apis,
                    'api_results': api_results
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='external_apis',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error=str(e)
            )
            
    async def _check_email_service(self) -> HealthCheckResult:
        """Check email service connectivity (SMTP)"""
        start_time = time.time()
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            # Only check if email is enabled
            if not self.config.get('EMAIL_ENABLED', False):
                return HealthCheckResult(
                    name='email_service',
                    status=HealthStatus.HEALTHY,
                    response_time=0.0,
                    details={'status': 'disabled'}
                )
            
            smtp_host = self.config.get('SMTP_HOST')
            smtp_port = int(self.config.get('SMTP_PORT', 587))
            smtp_username = self.config.get('SMTP_USERNAME')
            smtp_password = self.config.get('SMTP_PASSWORD')
            
            # Test SMTP connection
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.quit()
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name='email_service',
                status=HealthStatus.HEALTHY if response_time < 10.0 else HealthStatus.DEGRADED,
                response_time=response_time,
                details={
                    'smtp_host': smtp_host,
                    'smtp_port': smtp_port,
                    'authentication': 'successful'
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='email_service',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error=str(e)
            )
            
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource utilization"""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on resource usage
            if cpu_percent > 85 or memory.percent > 85 or disk.percent > 90:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 70 or memory.percent > 75 or disk.percent > 80:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name='system_resources',
                status=status,
                response_time=response_time,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_percent': disk.percent,
                    'disk_free_gb': round(disk.free / (1024**3), 2)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='system_resources',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    def _calculate_system_health(self, results: Dict[str, HealthCheckResult]):
        """Calculate overall system health score and update metrics"""
        total_checks = len(results)
        healthy_checks = sum(1 for result in results.values() if result.status == HealthStatus.HEALTHY)
        degraded_checks = sum(1 for result in results.values() if result.status == HealthStatus.DEGRADED)
        
        # Calculate health score (0-1)
        health_score = (healthy_checks + (degraded_checks * 0.5)) / total_checks
        
        # Update metrics
        metrics.update_system_health(health_score)
        
        # Record component-specific metrics
        for name, result in results.items():
            if result.error:
                metrics.record_error(name, 'health_check_failure')

# Health check endpoint for HTTP server
async def health_check_endpoint(config: EnvironmentConfigProvider) -> Dict[str, Any]:
    """HTTP endpoint for health checks"""
    checker = HealthChecker(config)
    results = await checker.check_all()
    
    # Convert to JSON-serializable format
    health_data = {
        'status': 'healthy',  # Will be overridden based on results
        'timestamp': time.time(),
        'checks': {}
    }
    
    unhealthy_count = 0
    degraded_count = 0
    
    for name, result in results.items():
        health_data['checks'][name] = {
            'status': result.status.value,
            'response_time': result.response_time,
            'details': result.details,
            'error': result.error
        }
        
        if result.status == HealthStatus.UNHEALTHY:
            unhealthy_count += 1
        elif result.status == HealthStatus.DEGRADED:
            degraded_count += 1
    
    # Determine overall status
    if unhealthy_count > 0:
        health_data['status'] = 'unhealthy'
    elif degraded_count > 0:
        health_data['status'] = 'degraded'
    else:
        health_data['status'] = 'healthy'
        
    return health_data
```

This comprehensive monitoring and alerting implementation provides production-ready infrastructure for the Phoenix Real Estate Data Collection System with real-time dashboards, intelligent alerting, and comprehensive health monitoring.