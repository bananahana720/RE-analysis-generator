# Rate Limiting Strategies Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Sliding Window Algorithm](#sliding-window-algorithm)
4. [Safety Margin Rationale](#safety-margin-rationale)
5. [Observer Pattern Implementation](#observer-pattern-implementation)
6. [Per-Source Tracking](#per-source-tracking)
7. [Configuration Options](#configuration-options)
8. [Monitoring and Alerting](#monitoring-and-alerting)
9. [Integration Examples](#integration-examples)
10. [Troubleshooting Guide](#troubleshooting-guide)

## Overview

The Phoenix Real Estate Data Collector implements a sophisticated rate limiting system designed to ensure compliance with API limits while maximizing throughput and maintaining system reliability. The rate limiter is built with thread-safety, async/await compatibility, and real-time monitoring capabilities.

### Key Features

- **Sliding Window Algorithm**: Provides accurate rate limiting without the "burst" issues of fixed windows
- **Safety Margins**: Configurable buffers to prevent accidental limit violations
- **Observer Pattern**: Real-time notifications for monitoring and alerting
- **Per-Source Tracking**: Independent rate limits for different API sources
- **Performance Optimized**: <100ms response time for rate limit checks
- **Memory Efficient**: Automatic cleanup of expired request timestamps

## Architecture

### Component Hierarchy

```
RateLimiter
├── Core Algorithm (Sliding Window)
├── Thread Safety (asyncio.Lock)
├── Request Tracking (DefaultDict[str, deque])
├── Observer Management
└── Performance Metrics
```

### Class Structure

```python
class RateLimiter:
    """Thread-safe rate limiter with sliding window algorithm"""
    
    def __init__(
        self,
        requests_per_minute: int = 1000,
        safety_margin: float = 0.10,
        window_duration: int = 60,
    ) -> None:
        # Core configuration
        self.requests_per_minute = requests_per_minute
        self.safety_margin = safety_margin
        self.window_duration = window_duration
        
        # Calculated effective limit
        self.effective_limit = int(requests_per_minute * (1 - safety_margin))
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Per-source tracking
        self._source_requests: DefaultDict[str, deque[float]] = defaultdict(deque)
        
        # Observer pattern
        self._observers: List[RateLimitObserver] = []
```

## Sliding Window Algorithm

The sliding window algorithm provides more accurate rate limiting compared to fixed window approaches by continuously tracking requests within a moving time window.

### How It Works

1. **Request Timestamps**: Each request is recorded with its timestamp
2. **Window Calculation**: Only requests within the last `window_duration` seconds are counted
3. **Continuous Sliding**: The window moves continuously with time, not in fixed intervals
4. **Cleanup**: Old timestamps are automatically removed during checks

### Implementation Details

```python
async def wait_if_needed(self, source: str) -> float:
    """Main rate limiting method"""
    async with self._lock:
        current_time = time.time()
        
        # Remove timestamps older than window_duration
        self._cleanup_old_requests(source)
        
        # Count requests in current window
        current_requests = len(self._source_requests[source])
        
        if current_requests < self.effective_limit:
            # Can make request immediately
            self._source_requests[source].append(current_time)
            return 0.0
        
        # Calculate wait time until oldest request expires
        oldest_request = self._source_requests[source][0]
        wait_time = max(0.0, (oldest_request + self.window_duration) - current_time)
        return wait_time
```

### Advantages Over Fixed Windows

1. **No Burst Issues**: Fixed windows can allow 2x the limit at window boundaries
2. **Smooth Rate Distribution**: Requests are spread evenly over time
3. **More Accurate**: Actual rate limiting matches configured limits closely
4. **Fair Queuing**: First-in-first-out behavior for waiting requests

## Safety Margin Rationale

The safety margin is a critical feature that prevents accidental API limit violations due to various factors.

### Why 600 vs 1000?

The Maricopa API has a published limit of 1000 requests per hour. However, we implement a 10% safety margin (900 effective requests) for several reasons:

1. **Clock Drift**: Server and client clocks may not be perfectly synchronized
2. **Network Latency**: Requests may arrive at the server slightly after being sent
3. **Rate Limit Calculation Differences**: The API server may use a different algorithm
4. **Burst Protection**: Prevents hitting the exact limit during high-activity periods
5. **Error Recovery Buffer**: Leaves room for retry attempts on failed requests

### Safety Margin Calculation

```python
# Example: 1000 requests/hour with 10% safety margin
actual_limit = 1000
safety_margin = 0.10
effective_limit = int(actual_limit * (1 - safety_margin))  # 900
```

### Configurable Margins

Different APIs may require different safety margins:

```python
# Conservative (15% margin) - for strict APIs
limiter = RateLimiter(requests_per_minute=100, safety_margin=0.15)

# Standard (10% margin) - default for most APIs
limiter = RateLimiter(requests_per_minute=100, safety_margin=0.10)

# Aggressive (5% margin) - when you have good clock sync
limiter = RateLimiter(requests_per_minute=100, safety_margin=0.05)
```

## Observer Pattern Implementation

The observer pattern enables real-time monitoring and reactive behavior without tight coupling between components.

### Observer Protocol

```python
class RateLimitObserver(Protocol):
    """Observer protocol for rate limit notifications"""
    
    async def on_request_made(self, source: str, timestamp: datetime) -> None:
        """Called when a request is made"""
        
    async def on_rate_limit_hit(self, source: str, wait_time: float) -> None:
        """Called when rate limit is hit"""
        
    async def on_rate_limit_reset(self, source: str) -> None:
        """Called when rate limit window resets"""
```

### Benefits

1. **Decoupling**: Monitoring logic separated from rate limiting logic
2. **Extensibility**: Easy to add new observers without modifying core code
3. **Real-time Notifications**: Immediate alerts for rate limit events
4. **Multiple Observers**: Support for multiple monitoring systems

### Example Observers

```python
class MetricsObserver:
    """Tracks rate limit metrics for monitoring"""
    
    async def on_rate_limit_hit(self, source: str, wait_time: float):
        # Send metric to monitoring system
        await metrics.increment('rate_limit_hits', tags={'source': source})
        await metrics.gauge('rate_limit_wait_time', wait_time, tags={'source': source})

class LoggingObserver:
    """Logs rate limit events"""
    
    async def on_rate_limit_hit(self, source: str, wait_time: float):
        logger.warning(f"Rate limit hit for {source}, waiting {wait_time:.2f}s")

class AlertingObserver:
    """Sends alerts for critical rate limit events"""
    
    async def on_rate_limit_hit(self, source: str, wait_time: float):
        if wait_time > 60:  # Alert if waiting more than 1 minute
            await alert_manager.send_alert(
                level='warning',
                message=f'Long rate limit wait for {source}: {wait_time}s'
            )
```

## Per-Source Tracking

The rate limiter supports independent tracking for multiple API sources, allowing different services to have their own rate limit windows.

### Implementation

```python
# Each source has its own deque of timestamps
self._source_requests: DefaultDict[str, deque[float]] = defaultdict(deque)

# Usage with different sources
await limiter.wait_if_needed('maricopa_api')
await limiter.wait_if_needed('phoenix_mls')
await limiter.wait_if_needed('zillow_api')
```

### Benefits

1. **Source Isolation**: One source hitting limits doesn't affect others
2. **Different Patterns**: Sources can have different usage patterns
3. **Fair Resource Allocation**: Each source gets its configured share
4. **Easier Debugging**: Can track issues per source

### Source Naming Conventions

```python
# Good source names - specific and descriptive
'maricopa_api'
'phoenix_mls_search'
'zillow_property_details'
'redfin_market_data'

# Avoid generic names
'api'         # Too generic
'external'    # Not specific
'default'     # Unclear purpose
```

## Configuration Options

### Basic Configuration

```python
# Standard configuration
limiter = RateLimiter(
    requests_per_minute=1000,  # Base rate limit
    safety_margin=0.10,        # 10% safety buffer
    window_duration=60         # 60-second sliding window
)
```

### Advanced Configuration

```python
# For APIs with hourly limits
hourly_requests = 1000
requests_per_minute = hourly_requests / 60  # Convert to per-minute

limiter = RateLimiter(
    requests_per_minute=int(requests_per_minute),
    safety_margin=0.10,
    window_duration=3600  # Use hour-long window for accuracy
)
```

### Configuration via Config Files

```yaml
rate_limiting:
  maricopa:
    requests_per_hour: 1000
    safety_margin: 0.10
    window_duration: 3600
  
  phoenix_mls:
    requests_per_hour: 5000
    safety_margin: 0.05
    window_duration: 3600
```

### Dynamic Configuration

```python
class ConfigurableRateLimiter:
    """Rate limiter that can be reconfigured at runtime"""
    
    def __init__(self, config: ConfigProvider):
        self.config = config
        self._create_limiter()
        
    def _create_limiter(self):
        self.limiter = RateLimiter(
            requests_per_minute=self.config.get_int('rate_limit.requests_per_minute'),
            safety_margin=self.config.get_float('rate_limit.safety_margin'),
            window_duration=self.config.get_int('rate_limit.window_duration')
        )
    
    async def reload_config(self):
        """Reload configuration without losing current state"""
        old_limiter = self.limiter
        self._create_limiter()
        # Transfer state if needed
```

## Monitoring and Alerting

### Built-in Metrics

The rate limiter provides comprehensive metrics through the `get_performance_metrics()` method:

```python
metrics = limiter.get_performance_metrics()
# Returns:
{
    'configured_limit': 1000,
    'effective_limit': 900,
    'safety_margin_percent': 10.0,
    'window_duration_seconds': 60,
    'total_active_sources': 3,
    'total_current_requests': 450,
    'observer_count': 2,
    'most_active_source': 'maricopa_api',
    'max_source_requests': 200,
    'max_source_utilization_percent': 22.2,
    'memory_efficient': True,
    'cleanup_working': True
}
```

### Usage Statistics

Get real-time usage for monitoring dashboards:

```python
# Per-source statistics
usage = limiter.get_current_usage('maricopa_api')
# Returns:
{
    'source': 'maricopa_api',
    'current_requests': 850,
    'effective_limit': 900,
    'requests_remaining': 50,
    'utilization_percent': 94.4,
    'is_rate_limited': False,
    'next_available_seconds': 0.0,
    'window_duration': 60
}

# Global statistics
global_usage = limiter.get_current_usage()
# Returns aggregate statistics for all sources
```

### Monitoring Integration

```python
class PrometheusExporter:
    """Export rate limiter metrics to Prometheus"""
    
    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter
        
    async def export_metrics(self):
        metrics = self.limiter.get_performance_metrics()
        
        # Export gauges
        rate_limit_utilization.set(
            metrics['max_source_utilization_percent'],
            labels={'source': metrics['most_active_source']}
        )
        
        active_sources.set(metrics['total_active_sources'])
        total_requests.set(metrics['total_current_requests'])
```

### Alerting Strategies

```python
class RateLimitAlerter:
    """Alert on rate limit conditions"""
    
    def __init__(self, limiter: RateLimiter, alert_threshold: float = 0.8):
        self.limiter = limiter
        self.alert_threshold = alert_threshold
        
    async def check_alerts(self):
        for source in self.limiter._source_requests.keys():
            usage = self.limiter.get_current_usage(source)
            
            utilization = usage['utilization_percent'] / 100.0
            
            if utilization >= self.alert_threshold:
                await self.send_alert(
                    level='warning' if utilization < 0.9 else 'critical',
                    message=f'{source} at {utilization:.1%} capacity',
                    source=source,
                    remaining_requests=usage['requests_remaining']
                )
```

## Integration Examples

### Basic Integration

```python
from phoenix_real_estate.collectors.base.rate_limiter import RateLimiter

class APIClient:
    def __init__(self):
        # Create rate limiter with 1000 req/hour limit
        self.rate_limiter = RateLimiter(
            requests_per_minute=16,  # ~1000/hour
            safety_margin=0.10
        )
    
    async def make_request(self, endpoint: str):
        # Wait if rate limited
        wait_time = await self.rate_limiter.wait_if_needed('api')
        
        if wait_time > 0:
            self.logger.info(f"Rate limited, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        # Make the actual request
        return await self._http_request(endpoint)
```

### Advanced Integration with Retry Logic

```python
class RobustAPIClient:
    def __init__(self):
        self.rate_limiter = RateLimiter(
            requests_per_minute=16,
            safety_margin=0.10
        )
        self.max_retries = 3
    
    async def make_request_with_retry(self, endpoint: str):
        for attempt in range(self.max_retries):
            try:
                # Check rate limit
                wait_time = await self.rate_limiter.wait_if_needed('api')
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                # Make request
                response = await self._http_request(endpoint)
                
                # Check for rate limit response from server
                if response.status == 429:
                    # Server says we're rate limited, be more conservative
                    retry_after = int(response.headers.get('Retry-After', 60))
                    await asyncio.sleep(retry_after)
                    continue
                
                return response
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Integration with Circuit Breaker

```python
class ResilientAPIClient:
    def __init__(self):
        self.rate_limiter = RateLimiter(
            requests_per_minute=16,
            safety_margin=0.10
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
    
    async def make_request(self, endpoint: str):
        # Check circuit breaker first
        if self.circuit_breaker.is_open():
            raise ServiceUnavailableError("Circuit breaker is open")
        
        try:
            # Then check rate limit
            wait_time = await self.rate_limiter.wait_if_needed('api')
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            response = await self._http_request(endpoint)
            self.circuit_breaker.record_success()
            return response
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
```

### Bulk Request Handling

```python
class BulkAPIClient:
    def __init__(self):
        self.rate_limiter = RateLimiter(
            requests_per_minute=16,
            safety_margin=0.10
        )
    
    async def fetch_many(self, ids: List[str]):
        """Fetch multiple items while respecting rate limits"""
        results = []
        
        for batch in self._batch_items(ids, batch_size=10):
            # Process batch with rate limiting
            batch_results = await asyncio.gather(*[
                self._fetch_with_rate_limit(item_id)
                for item_id in batch
            ])
            results.extend(batch_results)
            
            # Check if we should slow down
            usage = self.rate_limiter.get_current_usage('api')
            if usage['utilization_percent'] > 80:
                # Slow down when approaching limit
                await asyncio.sleep(1)
        
        return results
    
    async def _fetch_with_rate_limit(self, item_id: str):
        wait_time = await self.rate_limiter.wait_if_needed('api')
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        return await self._fetch_item(item_id)
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Rate Limit Hit Immediately

**Symptom**: Requests are rate limited even though you haven't made many requests.

**Possible Causes**:
- Previous requests still in the sliding window
- Clock synchronization issues
- Multiple instances sharing the same API key

**Solutions**:
```python
# Check current usage
usage = limiter.get_current_usage('api')
print(f"Current requests in window: {usage['current_requests']}")

# Reset if needed (use with caution)
await limiter.reset_source('api')

# Increase safety margin for clock drift
limiter = RateLimiter(safety_margin=0.15)  # 15% margin
```

#### 2. Memory Usage Growing

**Symptom**: Memory usage increases over time.

**Possible Causes**:
- Cleanup not running properly
- Too many unique sources
- Timestamps not being removed

**Solutions**:
```python
# Check if cleanup is working
metrics = limiter.get_performance_metrics()
assert metrics['cleanup_working'] == True
assert metrics['memory_efficient'] == True

# Manually trigger cleanup
limiter._cleanup_old_requests('source_name')

# Monitor unique sources
print(f"Active sources: {metrics['total_active_sources']}")
```

#### 3. Inconsistent Rate Limiting

**Symptom**: Rate limiting behavior seems inconsistent.

**Possible Causes**:
- Multiple rate limiter instances
- Thread safety issues
- Time synchronization

**Solutions**:
```python
# Ensure single instance
class APIClientSingleton:
    _instance = None
    _rate_limiter = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._rate_limiter = RateLimiter()
        return cls._instance
    
    @property
    def rate_limiter(self):
        return self._rate_limiter

# Use consistent time source
import time
# time.time() is monotonic and consistent
```

#### 4. Observer Exceptions

**Symptom**: Observers throwing exceptions disrupting rate limiting.

**Possible Causes**:
- Observer implementation errors
- Async handling issues

**Solutions**:
```python
# Observers are called with exception handling
# but implement defensive coding:

class SafeObserver:
    async def on_rate_limit_hit(self, source: str, wait_time: float):
        try:
            # Your observer logic
            await self.notify_monitoring(source, wait_time)
        except Exception as e:
            # Log but don't raise
            logger.error(f"Observer error: {e}")
```

### Debugging Tips

#### Enable Debug Logging

```python
import logging

# Enable debug logging for rate limiter
logging.getLogger('phoenix_real_estate.collectors.base.rate_limiter').setLevel(logging.DEBUG)
```

#### Rate Limit Testing

```python
async def test_rate_limits():
    """Test rate limit behavior"""
    limiter = RateLimiter(
        requests_per_minute=10,  # Low limit for testing
        safety_margin=0.10
    )
    
    # Add test observer
    class TestObserver:
        def __init__(self):
            self.events = []
            
        async def on_rate_limit_hit(self, source, wait_time):
            self.events.append(('hit', source, wait_time))
    
    observer = TestObserver()
    limiter.add_observer(observer)
    
    # Make requests until rate limited
    for i in range(15):
        wait_time = await limiter.wait_if_needed('test')
        print(f"Request {i+1}: wait_time={wait_time:.2f}s")
        
        if wait_time > 0:
            print(f"Rate limited! Events: {observer.events}")
            break
```

#### Performance Profiling

```python
import cProfile
import pstats

async def profile_rate_limiter():
    """Profile rate limiter performance"""
    limiter = RateLimiter()
    
    async def make_requests():
        for _ in range(1000):
            await limiter.wait_if_needed('test')
    
    # Profile the operation
    profiler = cProfile.Profile()
    profiler.enable()
    
    await make_requests()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

### Best Practices

1. **Always Use Safety Margins**: Never set safety_margin to 0
2. **Monitor Usage**: Regularly check utilization metrics
3. **Handle Wait Times**: Always respect the returned wait time
4. **Use Observers**: Implement observers for production monitoring
5. **Test Rate Limits**: Test with lower limits before production
6. **Document Sources**: Keep a registry of all source names used
7. **Graceful Degradation**: Have a plan when rate limited

## Conclusion

The rate limiting system in Phoenix Real Estate Data Collector provides a robust, scalable solution for API compliance. By combining the sliding window algorithm with safety margins, observer pattern, and comprehensive monitoring, it ensures reliable operation while maximizing throughput within API constraints.

For additional information or specific integration scenarios, consult the codebase examples in `tests/collectors/base/test_rate_limiter.py` and the Maricopa collector implementation in `src/phoenix_real_estate/collectors/maricopa/`.