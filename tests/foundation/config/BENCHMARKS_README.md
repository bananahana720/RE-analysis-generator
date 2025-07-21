# Configuration System Performance Benchmarks

This directory contains comprehensive performance benchmarks for the Phoenix Real Estate configuration system.

## Overview

The benchmarking suite measures performance across 10 key areas:

1. **Configuration Load Time** - Cold/warm cache performance across environments
2. **Validation Performance** - Simple vs complex configuration validation
3. **Concurrent Access** - Thread scalability and throughput
4. **Memory Usage** - Startup, sustained, and peak memory patterns
5. **Secret Access** - Direct, encrypted, and validated secret retrieval
6. **Environment Processing** - Performance with varying environment variable counts
7. **YAML Parsing** - Small vs large configuration file parsing
8. **Cache Efficiency** - Hit rates and invalidation overhead
9. **Thread Contention** - Lock contention and scaling efficiency
10. **Optimization Analysis** - Actionable recommendations based on results

## Running Benchmarks

### Method 1: Direct Execution
```bash
python run_benchmarks.py
```

### Method 2: As a Module
```bash
python -m tests.foundation.config.benchmarks
```

### Method 3: With pytest (specific benchmarks)
```bash
# Run all benchmarks
pytest tests/foundation/config/benchmarks.py -v

# Run only performance benchmarks
pytest tests/foundation/config/test_performance.py -m benchmark -v
```

## Output

The benchmarks generate three types of output:

1. **Console Output** - Real-time results with ASCII dashboard
2. **JSON Report** - Detailed metrics in `benchmark_results/benchmark_report_TIMESTAMP.json`
3. **Markdown Report** - Human-readable report in `benchmark_results/benchmark_report_TIMESTAMP.md`

## Performance Targets

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cold Start | < 100ms | TBD | TBD |
| Warm Cache | < 100μs | TBD | TBD |
| Validation (simple) | < 50ms | TBD | TBD |
| Concurrent (64 threads) | > 100k ops/s | TBD | TBD |
| Memory per Config | < 100KB | TBD | TBD |
| Cache Hit Rate | > 99% | TBD | TBD |

## Key Metrics Explained

### Percentiles
- **Mean**: Average across all measurements
- **Median (P50)**: Middle value when sorted
- **P95**: 95% of operations complete within this time
- **P99**: 99% of operations complete within this time
- **Max**: Worst-case scenario

### Efficiency Metrics
- **Cache Hit Rate**: Percentage of requests served from cache
- **Thread Efficiency**: Actual throughput vs ideal linear scaling
- **Memory Overhead**: Extra memory beyond raw data storage

## Optimization Recommendations

The benchmark suite automatically generates optimization recommendations based on:

- Performance bottlenecks (response times exceeding targets)
- Inefficient resource usage (memory, CPU)
- Poor scaling characteristics
- Cache inefficiencies

Recommendations are prioritized as:
- **HIGH**: Critical performance issues requiring immediate attention
- **MEDIUM**: Significant improvements possible
- **LOW**: Nice-to-have optimizations

## Interpreting Results

### Good Performance Indicators
- ✅ Cold start < 100ms
- ✅ Warm cache < 100μs
- ✅ Linear or near-linear scaling with threads
- ✅ Low memory overhead (< 2x data size)
- ✅ High cache hit rates (> 95%)

### Warning Signs
- ⚠️ Cold start > 200ms
- ⚠️ High P99 latencies (> 10x median)
- ⚠️ Poor thread scaling (< 50% efficiency)
- ⚠️ Memory leaks or excessive usage
- ⚠️ Low cache hit rates (< 80%)

## Continuous Monitoring

For production systems, consider:

1. Running benchmarks in CI/CD pipeline
2. Setting up performance regression alerts
3. Tracking metrics over time
4. A/B testing optimization changes
5. Profiling before major releases

## Related Files

- `test_performance.py` - pytest-based performance tests
- `benchmarks.py` - Comprehensive benchmark suite
- `benchmark_results/` - Output directory for reports