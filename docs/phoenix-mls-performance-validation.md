# Phoenix MLS Scraper Performance Validation

This document describes how to validate the Phoenix MLS scraper's performance against the target of 1000+ properties per hour while maintaining rate limit compliance.

## Overview

The performance validation script (`scripts/validate_phoenix_mls_performance.py`) tests the scraper under realistic conditions and measures:

- **Throughput**: Properties scraped per hour
- **Success Rate**: Percentage of successful scraping attempts  
- **Rate Limit Compliance**: Whether the scraper respects configured rate limits
- **Resource Usage**: CPU and memory consumption
- **Response Times**: Average and percentile latencies
- **Error Patterns**: Types and frequency of errors

## Target Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Throughput | 1000+ properties/hour | Sustained scraping rate |
| Success Rate | >95% | Percentage of successful property scrapes |
| Rate Limit Compliance | 100% | No rate limit violations |
| Average Response Time | <2 seconds | Per-property scraping time |
| CPU Usage | <80% average | Sustainable resource usage |
| Memory Usage | <1GB | Reasonable memory footprint |

## Running the Validation

### Basic Usage

Run a 10-minute validation test:

```bash
python scripts/validate_phoenix_mls_performance.py
```

### Extended Test

Run a full 60-minute validation:

```bash
python scripts/validate_phoenix_mls_performance.py --duration 60
```

### Custom Target

Test against a different throughput target:

```bash
python scripts/validate_phoenix_mls_performance.py --target 1500 --duration 30
```

### Specific Zipcodes

Test with specific Phoenix zipcodes:

```bash
python scripts/validate_phoenix_mls_performance.py --zipcodes 85001 85003 85004 85006
```

### Save Report

Save detailed JSON report:

```bash
python scripts/validate_phoenix_mls_performance.py --duration 60 --output reports/performance-validation.json
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--duration` | 10 | Test duration in minutes |
| `--target` | 1000 | Target properties per hour |
| `--output` | None | Path to save JSON report |
| `--zipcodes` | Phoenix metros | Specific zipcodes to test |

## Understanding the Report

### Summary Section

```
📊 SUMMARY
----------------------------------------
Test Status: ✅ PASSED
Target: 1000 properties/hour
Actual: 1156 properties/hour
Total Properties: 1156
Success Rate: 98.3%
Rate Limit Compliant: Yes
Test Duration: 60.0 minutes
```

- **Test Status**: Overall pass/fail based on meeting the target
- **Actual vs Target**: Comparison of achieved throughput
- **Success Rate**: Percentage of properties successfully scraped
- **Rate Limit Compliant**: Whether rate limits were respected

### Throughput Metrics

```
⚡ THROUGHPUT
----------------------------------------
Properties/Hour: 1156
Properties/Minute: 19.3
Peak Properties/Minute: 25
```

Shows sustained and peak throughput rates.

### Performance Metrics

```
🚀 PERFORMANCE
----------------------------------------
Avg Response Time: 1.234s
P95 Response Time: 2.156s
P99 Response Time: 3.452s
CPU Usage: 45.2% avg, 78.5% max
Memory Usage: 456.7MB avg, 823.4MB max
```

- **Response Times**: How long each property takes to scrape
- **P95/P99**: 95th and 99th percentile response times
- **Resource Usage**: CPU and memory consumption

### Reliability Metrics

```
🛡️ RELIABILITY
----------------------------------------
Total Requests: 1175
Successful: 1156
Failed: 19
Rate Limited: 0

Error Breakdown:
  - TimeoutError: 12
  - ConnectionError: 7
```

Shows error patterns and failure reasons.

### Recommendations

The script provides specific recommendations based on the test results:

```
💡 RECOMMENDATIONS
----------------------------------------
1. Throughput meets target. Consider increasing concurrent operations for better performance.
2. Success rate is 98.3%. Investigate TimeoutError occurrences for improvement.
3. CPU usage peaks at 78.5%. Monitor during extended runs for sustainability.
```

## Performance Optimization Tips

### 1. Increase Concurrency

If throughput is below target, increase concurrent operations:

- Adjust batch size in the scraper
- Use more worker tasks
- Implement connection pooling

### 2. Optimize Parsing

If CPU usage is high:

- Use more efficient HTML parsing (lxml vs BeautifulSoup)
- Cache parsed selectors
- Implement lazy loading for large responses

### 3. Add More Proxies

If rate limiting occurs:

- Add more proxy servers to distribute load
- Implement better proxy rotation
- Use residential proxies for better success rates

### 4. Improve Error Handling

For high failure rates:

- Implement exponential backoff
- Add retry logic for transient errors
- Better timeout configuration

### 5. Memory Optimization

If memory usage is high:

- Stream large responses instead of loading fully
- Implement periodic cleanup
- Limit concurrent operations

## Proxy Configuration

Ensure `config/proxies.yaml` is properly configured:

```yaml
proxy_manager:
  proxies:
    - host: "proxy1.example.com"
      port: 8080
      type: "http"
      username: "user"
      password: "pass"
    - host: "proxy2.example.com"
      port: 8080
      type: "http"
  max_failures: 3
  cooldown_minutes: 5
  health_check_url: "https://httpbin.org/ip"
```

## Monitoring During Tests

The validation script logs progress in real-time:

```
2024-01-20 10:15:23 - INFO - Found 48 properties in 85001 (1.23s)
2024-01-20 10:15:35 - INFO - Scraped 20/20 properties (11.45s, 1.7 props/s)
2024-01-20 10:16:00 - INFO - Current rate: 1134 properties/hour (Target: 1000)
2024-01-20 10:16:30 - INFO - Resources - CPU: 42.3%, Memory: 467.2MB, Properties: 378
```

## Troubleshooting

### Test Fails to Start

1. Check proxy configuration exists
2. Verify network connectivity
3. Ensure all dependencies are installed

### Low Throughput

1. Check for rate limiting in logs
2. Verify proxy health
3. Look for parsing bottlenecks
4. Consider network latency

### High Error Rate

1. Check error breakdown in report
2. Verify target site is accessible
3. Test proxies independently
4. Review anti-detection measures

### Resource Issues

1. Monitor system resources during test
2. Reduce concurrent operations
3. Implement memory cleanup
4. Use resource limits

## Integration with CI/CD

Run performance validation in CI:

```yaml
# .github/workflows/performance-test.yml
name: Performance Validation

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      
      - name: Run performance validation
        run: |
          python scripts/validate_phoenix_mls_performance.py \
            --duration 30 \
            --output reports/performance-${GITHUB_RUN_ID}.json
      
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: reports/performance-*.json
```

## Best Practices

1. **Regular Testing**: Run validation tests regularly to catch performance regressions
2. **Baseline Establishment**: Create performance baselines for comparison
3. **Load Testing**: Test with different load patterns (burst, sustained, ramp-up)
4. **Environment Parity**: Test in production-like environments
5. **Metric Tracking**: Track performance metrics over time
6. **Alert Thresholds**: Set up alerts for performance degradation

## Conclusion

The performance validation script provides comprehensive testing of the Phoenix MLS scraper's ability to meet the 1000+ properties/hour target. Regular validation ensures the scraper maintains its performance characteristics while respecting rate limits and resource constraints.