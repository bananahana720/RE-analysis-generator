# RA-2 Research Findings: Workflow Architecture for Real Estate Data Collection

## Executive Summary
After extensive research into workflow orchestration for real estate data collection, I recommend Dagster as the primary orchestration tool, combined with Celery for distributed task execution. This architecture provides the scalability, reliability, and monitoring capabilities essential for recurring data collection across multiple zip codes.

## Workflow Orchestration Tools Comparison

### Dagster (Recommended)
- **Architecture**: Asset-based, data-aware orchestration
- **Pros**: 
  - Built-in data lineage tracking
  - Excellent for data pipelines
  - Modern Python-first design
  - Strong typing and testing support
- **Cons**: Newer tool, smaller community
- **Cost**: Open source with cloud options

### Apache Airflow
- **Architecture**: Task-based DAGs
- **Pros**: 
  - Mature, large community
  - Extensive plugin ecosystem
  - Battle-tested at scale
- **Cons**: 
  - Complex infrastructure requirements
  - Steep learning curve
  - Task-oriented (not data-oriented)

### Prefect
- **Architecture**: Flow-based with dynamic workflows
- **Pros**: 
  - Cloud-native design
  - Good error handling
  - Pythonic API
- **Cons**: 
  - Less suitable for fixed schedules
  - Newer ecosystem

### Temporal
- **Architecture**: Workflow as code
- **Pros**: 
  - Excellent for long-running workflows
  - Strong consistency guarantees
- **Cons**: 
  - Overkill for data pipelines
  - More complex setup

## Scheduling Patterns

### Recommended Approach: Hybrid Scheduling
```python
# Example scheduling configuration
scheduling_config = {
    "base_schedule": "0 2 * * *",  # 2 AM daily
    "zip_distribution": {
        "strategy": "round_robin",
        "batch_size": 10,
        "interval_minutes": 5
    },
    "peak_avoidance": {
        "blackout_hours": [9, 10, 11, 17, 18, 19],
        "weekend_boost": 1.5
    }
}
```

### Key Patterns:
1. **Time-based with jitter**: Prevent thundering herd
2. **Off-peak execution**: 2-6 AM for minimal server load
3. **Zip code batching**: Process 10-20 zips per batch
4. **Smart distribution**: Spread requests across time

### Cloud Schedulers:
- **GitHub Actions**: Free tier, simple setup
- **Cloud Functions**: Serverless, auto-scaling
- **AWS EventBridge**: Enterprise-grade reliability

## Error Handling Strategies

### Exponential Backoff Implementation
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def fetch_property_data(property_id):
    # Implementation with jitter
    jitter = random.uniform(0, 0.1)
    time.sleep(jitter)
    return api_call(property_id)
```

### Error Taxonomy:
1. **Transient Errors** (retry immediately)
   - Network timeouts
   - 503 Service Unavailable
   - Connection resets

2. **Rate Limit Errors** (backoff required)
   - 429 Too Many Requests
   - Custom rate limit headers

3. **Data Errors** (skip and log)
   - 404 Not Found
   - Malformed responses

4. **Fatal Errors** (circuit breaker)
   - 401 Unauthorized
   - Account suspended

### Circuit Breaker Pattern
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
```

## Rate Limiting Approaches

### Sliding Window Algorithm (Recommended)
```python
class SlidingWindowRateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
    
    def allow_request(self):
        now = time.time()
        # Remove old requests
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
```

### Multi-Layer Rate Limiting:
1. **Application Layer**: Request frequency control
2. **IP Rotation**: Distribute across multiple IPs
3. **Header Rotation**: Vary user agents
4. **Request Timing**: Add human-like delays

### Adaptive Throttling:
- Monitor response times
- Detect server stress signals
- Automatically adjust request rate
- Implement "good citizen" protocols

## Distributed Processing Architecture

### Recommended Stack
```yaml
architecture:
  orchestrator: Dagster
  task_queue: Celery
  message_broker: Redis
  result_backend: PostgreSQL
  monitoring: Prometheus + Grafana
```

### Celery Configuration
```python
# celery_config.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'postgresql://user:pass@localhost/celery'

task_routes = {
    'scrape.*': {'queue': 'scraping'},
    'process.*': {'queue': 'processing'},
    'store.*': {'queue': 'storage'}
}

task_annotations = {
    'scrape.fetch_property': {'rate_limit': '10/m'},
    'scrape.fetch_listings': {'rate_limit': '5/m'}
}
```

### Scaling Patterns:

1. **Horizontal Scaling**
   - Add workers dynamically based on queue depth
   - Geographic distribution for better latency
   - Auto-scaling rules based on metrics

2. **Priority Queues**
   ```python
   task_priorities = {
       'high_value_zips': 10,
       'regular_zips': 5,
       'backfill': 1
   }
   ```

3. **Batch Processing**
   - Group similar requests
   - Bulk database operations
   - Efficient resource utilization

4. **Worker Specialization**
   - Dedicated workers for API calls
   - Separate workers for data processing
   - Storage-optimized workers

## Monitoring and Observability

### Key Metrics:
1. **Throughput Metrics**
   - Properties processed/hour
   - API calls/minute
   - Success/failure rates

2. **Performance Metrics**
   - Task execution time
   - Queue depths
   - Worker utilization

3. **Business Metrics**
   - Coverage by zip code
   - Data freshness
   - Cost per property

### Alerting Rules:
- Queue depth > 1000 tasks
- Error rate > 5%
- API response time > 2s
- Worker memory > 80%

## Real-World Implementation Example

### Architecture Diagram:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Dagster   │────▶│    Redis    │────▶│   Celery    │
│ Orchestrator│     │   Broker    │     │   Workers   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                         │
       ▼                                         ▼
┌─────────────┐                         ┌─────────────┐
│ PostgreSQL  │◀────────────────────────│ Data APIs   │
│   Storage   │                         │   Sources   │
└─────────────┘                         └─────────────┘
```

### Deployment Strategy:
1. **Development**: Docker Compose setup
2. **Staging**: Kubernetes with 3-5 workers
3. **Production**: 
   - Kubernetes with auto-scaling
   - Multi-region deployment
   - Disaster recovery plan

## Cost Optimization

### Resource Efficiency:
1. **Smart Scheduling**: Process during off-peak hours
2. **Caching**: Redis for frequently accessed data
3. **Batch Operations**: Reduce API calls
4. **Worker Pooling**: Reuse connections

### Estimated Costs:
- **Small Scale** (10K properties/day): $200-300/month
- **Medium Scale** (100K properties/day): $800-1200/month
- **Large Scale** (1M+ properties/day): $3000-5000/month

## Conclusion

The combination of Dagster for orchestration and Celery for distributed task execution provides a robust, scalable foundation for real estate data collection. Key success factors include implementing proper rate limiting, comprehensive error handling, and geographic distribution of workers. This architecture can scale from processing hundreds to millions of properties daily while maintaining reliability and cost efficiency.