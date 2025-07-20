# Task 11: Monitoring & Observability

## Overview
Implement comprehensive monitoring and observability across all Phoenix Real Estate system components, extending Epic 1's monitoring framework to provide real-time insights into system health, performance, and quality.

## Integration Requirements

### Epic 1 Foundation Monitoring Extension
```python
# Extend foundation monitoring capabilities
from phoenix_real_estate.foundation.monitoring import MetricsCollector, HealthChecker
from phoenix_real_estate.foundation.logging import get_logger

class EnhancedSystemMonitor(HealthChecker):
    """Extended monitoring for all system components"""
    
    def __init__(self):
        super().__init__()
        self.metrics = MetricsCollector()
        self.logger = get_logger("system_monitor")
        
        # Epic-specific monitors
        self.foundation_monitor = FoundationMonitor()
        self.collection_monitor = CollectionMonitor()
        self.automation_monitor = AutomationMonitor()
        
    async def get_system_health(self):
        """Comprehensive system health check"""
        health_data = {
            'timestamp': datetime.now(),
            'foundation': await self.foundation_monitor.get_health(),
            'collection': await self.collection_monitor.get_health(),
            'automation': await self.automation_monitor.get_health(),
            'overall_score': 0.0
        }
        
        # Calculate overall health score
        epic_scores = [h['score'] for h in health_data.values() if isinstance(h, dict) and 'score' in h]
        health_data['overall_score'] = sum(epic_scores) / len(epic_scores) if epic_scores else 0.0
        
        return health_data
```

### Epic 2 Collection Monitoring Integration
```python
# Monitor data collection processes
from phoenix_real_estate.data_collection.monitoring import CollectionMetrics, DataQualityMetrics

class CollectionQualityMonitor:
    """Monitor collection processes and data quality"""
    
    def __init__(self):
        self.collection_metrics = CollectionMetrics()
        self.quality_metrics = DataQualityMetrics()
        self.logger = get_logger("collection_monitor")
        
    async def monitor_collection_pipeline(self, pipeline_result):
        """Monitor collection pipeline execution"""
        metrics = {
            'timestamp': datetime.now(),
            'properties_collected': pipeline_result.properties_collected,
            'success_rate': pipeline_result.success_rate,
            'error_count': pipeline_result.error_count,
            'processing_time': pipeline_result.processing_time,
            'data_quality_score': await self._calculate_quality_score(pipeline_result)
        }
        
        await self.collection_metrics.record_pipeline_execution(metrics)
        
        # Alert on quality issues
        if metrics['data_quality_score'] < 0.8:
            await self._send_quality_alert(metrics)
        
        return metrics
```

### Epic 3 Automation Monitoring Integration
```python
# Monitor automation workflows
from phoenix_real_estate.automation.monitoring import WorkflowMetrics, OrchestrationMonitor

class WorkflowHealthMonitor:
    """Monitor workflow execution and orchestration"""
    
    def __init__(self):
        self.workflow_metrics = WorkflowMetrics()
        self.orchestration_monitor = OrchestrationMonitor()
        self.logger = get_logger("workflow_monitor")
        
    async def monitor_workflow_execution(self, workflow_id: str, result):
        """Monitor individual workflow execution"""
        execution_metrics = {
            'workflow_id': workflow_id,
            'timestamp': datetime.now(),
            'status': result.status,
            'duration': result.duration,
            'success': result.success,
            'error_details': result.error_details,
            'resource_usage': result.resource_usage
        }
        
        await self.workflow_metrics.record_execution(execution_metrics)
        
        # Monitor for performance degradation
        if execution_metrics['duration'] > self._get_duration_threshold(workflow_id):
            await self._send_performance_alert(execution_metrics)
```

## Monitoring Architecture

### Central Observability Platform
```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio

@dataclass
class SystemMetrics:
    timestamp: datetime
    component: str
    metrics: Dict[str, float]
    alerts: List[str]
    health_score: float

class ObservabilityPlatform:
    """Central platform for system observability"""
    
    def __init__(self):
        self.metrics_store = MetricsStore()
        self.alert_manager = AlertManager()
        self.dashboard = RealTimeDashboard()
        self.trace_collector = DistributedTraceCollector()
        
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        # Parallel metric collection
        tasks = [
            self._collect_foundation_metrics(),
            self._collect_collection_metrics(),
            self._collect_automation_metrics(),
            self._collect_quality_metrics()
        ]
        
        metric_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate metrics
        all_metrics = {}
        all_alerts = []
        health_scores = []
        
        for component, result in zip(['foundation', 'collection', 'automation', 'quality'], metric_results):
            if not isinstance(result, Exception):
                all_metrics[component] = result.metrics
                all_alerts.extend(result.alerts)
                health_scores.append(result.health_score)
        
        return SystemMetrics(
            timestamp=datetime.now(),
            component='system',
            metrics=all_metrics,
            alerts=all_alerts,
            health_score=sum(health_scores) / len(health_scores) if health_scores else 0.0
        )
```

### Real-Time Dashboard
```python
class RealTimeDashboard:
    """Real-time system dashboard"""
    
    def __init__(self):
        self.websocket_manager = WebSocketManager()
        self.cache = DashboardCache(ttl=30)  # 30-second cache
        
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time dashboard data"""
        if cached_data := self.cache.get('dashboard'):
            return cached_data
            
        dashboard_data = {
            'timestamp': datetime.now(),
            'system_overview': await self._get_system_overview(),
            'epic_health': await self._get_epic_health(),
            'quality_metrics': await self._get_quality_metrics(),
            'performance_trends': await self._get_performance_trends(),
            'active_alerts': await self._get_active_alerts(),
            'recent_activities': await self._get_recent_activities()
        }
        
        self.cache.set('dashboard', dashboard_data)
        await self.websocket_manager.broadcast(dashboard_data)
        
        return dashboard_data
    
    async def _get_system_overview(self):
        """Get high-level system overview"""
        return {
            'uptime': await self._calculate_system_uptime(),
            'total_properties': await self._get_total_property_count(),
            'daily_collection_rate': await self._get_daily_collection_rate(),
            'data_quality_score': await self._get_overall_quality_score(),
            'error_rate': await self._get_error_rate(),
            'performance_score': await self._get_performance_score()
        }
```

## Monitoring Components

### 1. Distributed Tracing
```python
import opentelemetry.trace as trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class DistributedTracing:
    """Distributed tracing across all system components"""
    
    def __init__(self):
        # Setup OpenTelemetry
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        
        # Jaeger exporter (or alternative for budget constraints)
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=14268,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
    def trace_workflow_execution(self, workflow_name: str):
        """Trace complete workflow execution"""
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span(f"workflow.{workflow_name}") as span:
            span.set_attribute("workflow.name", workflow_name)
            span.set_attribute("epic", "automation")
            
            # Add custom attributes
            yield span
    
    def trace_data_collection(self, collector_name: str):
        """Trace data collection operations"""
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span(f"collection.{collector_name}") as span:
            span.set_attribute("collector.name", collector_name)
            span.set_attribute("epic", "collection")
            
            yield span
```

### 2. Log Aggregation
```python
from phoenix_real_estate.foundation.logging import get_logger
import json

class CentralizedLogging:
    """Centralized log aggregation and analysis"""
    
    def __init__(self):
        self.logger = get_logger("centralized_logging")
        self.log_aggregator = LogAggregator()
        self.log_analyzer = LogAnalyzer()
        
    async def aggregate_logs(self, time_range: timedelta = timedelta(hours=1)):
        """Aggregate logs from all system components"""
        end_time = datetime.now()
        start_time = end_time - time_range
        
        # Collect logs from all epics
        epic_logs = {
            'foundation': await self._get_foundation_logs(start_time, end_time),
            'collection': await self._get_collection_logs(start_time, end_time),
            'automation': await self._get_automation_logs(start_time, end_time),
            'quality': await self._get_quality_logs(start_time, end_time)
        }
        
        # Analyze log patterns
        analysis = await self.log_analyzer.analyze(epic_logs)
        
        return {
            'time_range': {'start': start_time, 'end': end_time},
            'logs': epic_logs,
            'analysis': analysis,
            'alerts': await self._generate_log_based_alerts(analysis)
        }
    
    async def _generate_log_based_alerts(self, analysis):
        """Generate alerts based on log analysis"""
        alerts = []
        
        # Error rate alerts
        if analysis.error_rate > 0.05:  # 5% error rate threshold
            alerts.append({
                'severity': 'high',
                'message': f"High error rate detected: {analysis.error_rate:.2%}",
                'component': 'system',
                'timestamp': datetime.now()
            })
        
        # Performance alerts
        if analysis.avg_response_time > 5000:  # 5 second threshold
            alerts.append({
                'severity': 'medium',
                'message': f"High response time: {analysis.avg_response_time}ms",
                'component': 'performance',
                'timestamp': datetime.now()
            })
        
        return alerts
```

### 3. Metric Collection and Analysis
```python
class MetricsAnalyzer:
    """Advanced metrics analysis and trend detection"""
    
    def __init__(self):
        self.metrics_store = MetricsStore()
        self.trend_analyzer = TrendAnalyzer()
        
    async def analyze_performance_trends(self, time_range: timedelta = timedelta(days=7)):
        """Analyze performance trends across time"""
        metrics_data = await self.metrics_store.get_metrics(
            start_time=datetime.now() - time_range,
            end_time=datetime.now()
        )
        
        trends = {
            'collection_performance': await self._analyze_collection_trends(metrics_data),
            'data_quality_trends': await self._analyze_quality_trends(metrics_data),
            'system_health_trends': await self._analyze_health_trends(metrics_data),
            'error_rate_trends': await self._analyze_error_trends(metrics_data)
        }
        
        # Generate recommendations
        recommendations = await self._generate_optimization_recommendations(trends)
        
        return {
            'trends': trends,
            'recommendations': recommendations,
            'prediction': await self._predict_future_performance(trends)
        }
    
    async def _generate_optimization_recommendations(self, trends):
        """Generate optimization recommendations based on trends"""
        recommendations = []
        
        # Collection performance recommendations
        if trends['collection_performance']['declining']:
            recommendations.append({
                'category': 'performance',
                'priority': 'high',
                'description': 'Collection performance is declining',
                'actions': [
                    'Review API rate limits',
                    'Check proxy performance',
                    'Optimize data processing pipeline'
                ]
            })
        
        # Data quality recommendations
        if trends['data_quality_trends']['score'] < 0.9:
            recommendations.append({
                'category': 'quality',
                'priority': 'medium',
                'description': 'Data quality below target',
                'actions': [
                    'Review LLM processing accuracy',
                    'Update validation rules',
                    'Check source data consistency'
                ]
            })
        
        return recommendations
```

### 4. Alert Management
```python
from enum import Enum
from typing import Callable, Dict, List

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertManager:
    """Intelligent alert management system"""
    
    def __init__(self):
        self.alert_rules = AlertRules()
        self.notification_manager = NotificationManager()
        self.alert_history = AlertHistory()
        
    async def evaluate_alerts(self, metrics: SystemMetrics):
        """Evaluate metrics against alert rules"""
        alerts = []
        
        # System health alerts
        if metrics.health_score < 0.7:
            alerts.append(Alert(
                severity=AlertSeverity.HIGH,
                component='system',
                message=f"System health critical: {metrics.health_score:.2f}",
                metrics={'health_score': metrics.health_score},
                timestamp=datetime.now()
            ))
        
        # Data quality alerts
        if 'collection' in metrics.metrics:
            quality_score = metrics.metrics['collection'].get('data_quality_score', 1.0)
            if quality_score < 0.8:
                alerts.append(Alert(
                    severity=AlertSeverity.MEDIUM,
                    component='collection',
                    message=f"Data quality below threshold: {quality_score:.2f}",
                    metrics={'quality_score': quality_score},
                    timestamp=datetime.now()
                ))
        
        # Process alerts
        for alert in alerts:
            await self._process_alert(alert)
        
        return alerts
    
    async def _process_alert(self, alert: Alert):
        """Process individual alert"""
        # Check for alert suppression
        if await self._should_suppress_alert(alert):
            return
            
        # Store alert
        await self.alert_history.store(alert)
        
        # Send notifications
        await self.notification_manager.send_alert(alert)
        
        # Trigger automated responses if configured
        if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            await self._trigger_automated_response(alert)

@dataclass
class Alert:
    severity: AlertSeverity
    component: str
    message: str
    metrics: Dict[str, float]
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None
```

### 5. Performance Monitoring
```python
class PerformanceMonitor:
    """Comprehensive performance monitoring"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.performance_analyzer = PerformanceAnalyzer()
        
    async def monitor_collection_performance(self):
        """Monitor data collection performance"""
        collection_metrics = {
            'api_response_times': await self._measure_api_response_times(),
            'processing_throughput': await self._measure_processing_throughput(),
            'memory_usage': await self._measure_memory_usage(),
            'error_rates': await self._calculate_error_rates(),
            'proxy_performance': await self._monitor_proxy_performance()
        }
        
        # Analyze performance patterns
        analysis = await self.performance_analyzer.analyze(collection_metrics)
        
        # Generate performance insights
        insights = {
            'bottlenecks': analysis.identified_bottlenecks,
            'optimization_opportunities': analysis.optimization_opportunities,
            'performance_score': analysis.overall_score,
            'trend': analysis.performance_trend
        }
        
        return {
            'metrics': collection_metrics,
            'analysis': analysis,
            'insights': insights,
            'recommendations': await self._generate_performance_recommendations(insights)
        }
    
    async def _generate_performance_recommendations(self, insights):
        """Generate performance optimization recommendations"""
        recommendations = []
        
        for bottleneck in insights['bottlenecks']:
            if bottleneck['component'] == 'api_calls':
                recommendations.append({
                    'type': 'optimization',
                    'priority': 'high',
                    'description': 'API call optimization needed',
                    'actions': [
                        'Implement request caching',
                        'Optimize batch sizes',
                        'Consider API call pooling'
                    ]
                })
        
        return recommendations
```

## Quality Monitoring Integration

### Data Quality Continuous Monitoring
```python
class DataQualityMonitor:
    """Continuous data quality monitoring"""
    
    def __init__(self):
        self.quality_metrics = DataQualityMetrics()
        self.validation_engine = DataValidationEngine()
        
    async def monitor_data_quality(self, properties: List[Property]):
        """Monitor data quality in real-time"""
        quality_report = {
            'timestamp': datetime.now(),
            'sample_size': len(properties),
            'completeness': await self._check_completeness(properties),
            'accuracy': await self._check_accuracy(properties),
            'consistency': await self._check_consistency(properties),
            'timeliness': await self._check_timeliness(properties),
            'validity': await self._check_validity(properties)
        }
        
        # Calculate overall quality score
        quality_report['overall_score'] = (
            quality_report['completeness'] * 0.25 +
            quality_report['accuracy'] * 0.30 +
            quality_report['consistency'] * 0.20 +
            quality_report['timeliness'] * 0.15 +
            quality_report['validity'] * 0.10
        )
        
        # Store quality metrics
        await self.quality_metrics.record_quality_report(quality_report)
        
        return quality_report
```

## Resource-Efficient Monitoring

### Lightweight Monitoring for Budget Constraints
```python
class LightweightMonitor:
    """Resource-efficient monitoring for budget constraints"""
    
    def __init__(self):
        self.sample_rate = 0.1  # Monitor 10% of operations
        self.batch_size = 100
        self.cache_ttl = 300  # 5-minute cache
        
    async def efficient_metric_collection(self):
        """Collect metrics with minimal resource usage"""
        # Use sampling to reduce overhead
        if random.random() > self.sample_rate:
            return None
            
        # Batch metric collection
        metrics = await self._collect_lightweight_metrics()
        
        # Use caching to reduce database calls
        cached_metrics = self._get_cached_metrics()
        if cached_metrics:
            return self._merge_metrics(cached_metrics, metrics)
            
        return metrics
    
    async def _collect_lightweight_metrics(self):
        """Collect only essential metrics"""
        return {
            'timestamp': datetime.now(),
            'system_health': await self._quick_health_check(),
            'error_count': await self._get_error_count(),
            'success_rate': await self._calculate_success_rate(),
            'response_time': await self._measure_avg_response_time()
        }
```

## Success Criteria
- Real-time monitoring with <1 minute alert latency
- System health visibility across all epics
- Performance monitoring with <5% overhead
- Data quality tracking with 90%+ accuracy
- Alert false positive rate <10%
- Dashboard load time <2 seconds
- Monitoring data storage within budget constraints

## Deliverables
1. Real-time monitoring dashboard
2. Distributed tracing implementation
3. Centralized log aggregation
4. Intelligent alert management system
5. Performance monitoring and analysis
6. Data quality continuous monitoring
7. Resource-efficient monitoring for budget constraints

## Resource Requirements
- MongoDB storage: 50MB/month for metrics
- GitHub Actions: 200 minutes/month for monitoring workflows
- External services: Free tier monitoring tools where possible
- Memory overhead: <100MB additional memory usage