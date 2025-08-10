# Production Restoration Test Plan

## Overview

**Critical Mission**: Production has been DOWN for 2+ days. This test plan ensures thorough validation of system restoration after secrets configuration.

**Last Updated**: 2025-01-10
**Version**: 1.0
**Status**: CRITICAL - Production Recovery

## Test Execution Summary

### Quick Status Check
- [ ] All secrets configured and verified
- [ ] All external services responding  
- [ ] Data collection workflows operational
- [ ] LLM processing pipeline functional
- [ ] MongoDB connectivity established
- [ ] Notification systems active
- [ ] GitHub Actions workflows passing

---

# Phase 1: Manual Secret Configuration Verification

## 1.1 Pre-Configuration Checklist

### Environment Variables Verification

| Secret | Required Format | Validation Method |
|--------|----------------|-------------------|
| MONGODB_URI | mongodb+srv://... or mongodb://localhost:27017/phoenix_real_estate | Connection test |
| MARICOPA_API_KEY | UUID format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | API call test |
| SECRET_KEY | Min 32 characters | Length validation |
| OLLAMA_HOST | http://localhost:11434 | Health check |
| WEBSHARE_USERNAME | String | Authentication test |
| WEBSHARE_PASSWORD | String | Authentication test |
| TWOCAPTCHA_API_KEY | 32-character hex | Balance check |

## 1.2 Manual Validation Steps

### Step 1: Local Environment Setup
```bash
# Copy environment template
cp .env.sample .env

# Validate format
python scripts/validation/validate_secrets.py validate
```

### Step 2: MongoDB Connection Test
```bash
# Test local MongoDB
python scripts/testing/simple_mongodb_test.py
```

### Step 3: External API Validation
```bash
# Test Maricopa API
python scripts/testing/test_maricopa_api.py
```

### Step 4: LLM Service Validation  
```bash
# Check Ollama service
curl http://localhost:11434/api/version

# Test LLM processing
python scripts/testing/simple_llm_test.py
```

# Phase 2: Automated System Validation

## Component Health Checks
- Database connectivity (<5s)
- External service connectivity 
- Data collection workflows
- LLM processing pipeline

## Integration Test Sequence
1. End-to-End Data Flow
2. Phoenix MLS Workflow
3. Error Recovery Testing

# Phase 3: Performance & Quality Validation

## Performance Benchmarks

| Component | Target |
|-----------|--------|
| MongoDB Connection | <5s |
| Maricopa API | <10s |
| LLM Processing | <30s |
| Phoenix MLS Scraper | <60s |
| End-to-End Workflow | <5min |

# Phase 4: Production Readiness Validation

## Health Endpoints
- /api/health - Application health
- /api/health/database - Database connectivity
- /api/health/services - External services status
- /api/metrics - Performance metrics

# Phase 5: Rollback Procedures

## Rollback Triggers
- Health Check Failure: >5 consecutive failures
- Performance Degradation: >50% response time increase
- Data Quality Issues: <70% processing accuracy
- Security Concerns: Unauthorized access detected

## Rollback Execution Plan
1. **Immediate Actions** (0-15 minutes): Stop, Isolate, Preserve, Communicate
2. **System Restoration** (15-60 minutes): Revert, Restore, Validate, Monitor
3. **Recovery Validation** (60+ minutes): Test, Performance, Data, Documentation

# Success Criteria

## Production Restoration Complete When:

### Core Systems (100% Required)
- [ ] Database connectivity established and stable
- [ ] All external APIs responding within SLA
- [ ] Data collection workflows executing successfully
- [ ] LLM processing pipeline operational
- [ ] Error rates <1% for all components

### Performance Standards (100% Required)  
- [ ] Response times within target ranges
- [ ] Resource usage within limits
- [ ] Data quality metrics >90% accuracy
- [ ] End-to-end workflow completion <5 minutes

### Monitoring & Operations (100% Required)
- [ ] All health endpoints responding correctly
- [ ] Monitoring dashboards showing green status
- [ ] Alert systems functional and tested
- [ ] GitHub Actions workflows passing

### Quality Gates (100% Required)
- [ ] Security validation passed
- [ ] Data integrity confirmed
- [ ] Performance benchmarks met
- [ ] Error handling verified

---

**CRITICAL**: System has been DOWN for 2+ days. Every test failure must be addressed immediately before declaring production restoration successful.
ENDHERE < /dev/null
