# Production Restoration Test Suite

## Overview

**CRITICAL MISSION**: Production system has been DOWN for 2+ days. This comprehensive test suite validates complete system restoration after secrets configuration.

## Directory Structure

```
docs/testing/production-restoration/
├── README.md                           # This file
├── PRODUCTION_RESTORATION_TEST_PLAN.md # Comprehensive test plan
├── test_plan_main.md                   # Main test documentation
└── EXECUTION_CHECKLIST.md              # Step-by-step execution guide

scripts/testing/production/
├── production_restoration_validator.py  # Main validation script
├── emergency_rollback.py               # Emergency rollback procedures
├── performance_validator.py            # Performance benchmarking
└── run_production_restoration_tests.sh # Complete test suite runner
```

## Quick Start

### 1. Prerequisites
```bash
# Ensure environment is set up
cp .env.sample .env
# Edit .env with actual values

# Install dependencies
uv sync

# Verify basic connectivity
python scripts/validation/validate_secrets.py validate
```

### 2. Run Complete Test Suite
```bash
# Execute full production restoration validation
./scripts/testing/production/run_production_restoration_tests.sh
```

### 3. Individual Test Components
```bash
# Secrets validation only
python scripts/testing/production/production_restoration_validator.py --secrets

# Database connectivity only  
python scripts/testing/production/production_restoration_validator.py --database

# External services only
python scripts/testing/production/production_restoration_validator.py --services

# Performance validation
python scripts/testing/production/performance_validator.py --performance
```

## Test Components

### 🔐 Secrets Configuration Validation
- Validates all required environment variables
- Checks format and validity of credentials
- Verifies GitHub secrets accessibility
- **Critical**: Must pass before proceeding

### 🗄️ Database Connectivity Testing
- Tests MongoDB connection establishment
- Validates read/write operations
- Checks connection pool health
- Measures response times

### 🌐 External Services Validation
- Maricopa API connectivity
- Ollama LLM service availability
- WebShare proxy authentication
- 2captcha service validation

### ⚡ Performance Benchmarking
- Database response times
- API call latencies
- LLM processing speeds
- Data quality metrics

### 🔄 Integration Testing
- End-to-end data flow validation
- Error handling verification
- Recovery mechanism testing
- System stability assessment

## Success Criteria

### ✅ Production Ready When:
1. **All validation tests PASS**
2. **Performance targets met**
3. **Error rates < 1%**
4. **Data quality > 90%**
5. **System stability confirmed**

### ❌ Not Ready When:
1. **Any critical test FAILS**
2. **Performance below targets**
3. **High error rates**
4. **System instability detected**

## Emergency Procedures

### Rollback Execution
```bash
# If tests fail and system is unstable
python scripts/testing/production/emergency_rollback.py --execute

# Validate rollback success
python scripts/testing/production/emergency_rollback.py --validate
```

### Rollback Triggers
- Health check failures (>5 consecutive)
- Performance degradation (>50% slower)
- Data quality issues (<70% accuracy)
- Security concerns detected

## Output and Reporting

### Test Results Location
```
test_results/production_restoration_YYYYMMDD_HHMMSS/
├── secrets_validation.json
├── production_restoration.json
├── performance_validation.json
└── summary.json
```

### Report Format
All test outputs use standardized JSON format:
```json
{
  "validation_timestamp": "2025-01-10T...",
  "overall_status": "PRODUCTION_READY|PRODUCTION_NOT_READY",
  "summary": {
    "total_tests": 6,
    "passed": 6,
    "failed": 0
  },
  "test_results": [...],
  "recommendations": [...]
}
```

## Monitoring and Alerts

### Real-time Monitoring
- System health endpoints
- Performance metrics
- Error rate tracking
- Resource utilization

### Alert Thresholds
- **Critical**: System failures, API timeouts
- **Warning**: Performance degradation, quota limits
- **Info**: Successful operations, status updates

## Troubleshooting

### Common Issues

#### Secrets Not Found
```bash
# Check environment file
ls -la .env

# Validate format
python scripts/validation/validate_secrets.py validate
```

#### Database Connection Failed
```bash
# Test local MongoDB
python scripts/testing/simple_mongodb_test.py

# Check MongoDB service
systemctl status mongod  # Linux
# or check MongoDB Atlas connection string
```

#### External Services Timeout
```bash
# Test individual services
curl -I https://mcassessor.maricopa.gov/api/v1/ping
curl http://localhost:11434/api/version
```

### Getting Help

1. **Check logs**: All test outputs include detailed error messages
2. **Review checklist**: Ensure all prerequisites met
3. **Run individual tests**: Isolate failing components
4. **Execute rollback**: If system becomes unstable

## Important Reminders

🚨 **CRITICAL**: System has been DOWN for 2+ days
⏰ **URGENCY**: Every minute of downtime has business impact
🔧 **SYSTEMATIC**: Follow validation process completely
📊 **EVIDENCE**: All decisions must be data-driven
🛡️ **SAFETY**: Rollback procedures ready if needed

---

**Do not declare production restoration successful until ALL tests pass and system stability is confirmed for at least 1 hour of continuous operation.**
README_END < /dev/null
