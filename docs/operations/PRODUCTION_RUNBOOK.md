# Phoenix Real Estate - Production Operations Runbook

**Version**: 1.0.0  
**Last Updated**: August 3, 2025  
**Maintainer**: Operations Team

## Overview

This runbook provides comprehensive operational procedures for the Phoenix Real Estate data collection system in production. It covers daily operations, troubleshooting, maintenance, and emergency response procedures.

## System Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Collection Layer │───▶│ Processing Layer│
│                 │    │                  │    │                 │
│ • Maricopa API  │    │ • Collectors     │    │ • LLM Pipeline  │
│ • Phoenix MLS   │    │ • Rate Limiters  │    │ • Data Validation│
│ • WebShare      │    │ • Proxy Manager  │    │ • Error Handling│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │  Orchestration   │    │ Storage Layer   │
                    │                  │    │                 │
                    │ • Workflow Mgmt  │    │ • MongoDB Atlas │
                    │ • Monitoring     │    │ • Email Reports │
                    │ • Cost Tracking  │    │ • Metrics Store │
                    └──────────────────┘    └─────────────────┘
```

## Daily Operations

### Morning Checklist (9 AM MST)

1. **System Health Check**
   ```bash
   # Check system status
   uv run python scripts/deploy/health_check.py
   
   # Review overnight collection results
   uv run python scripts/deploy/monitoring_dashboard.py
   ```

2. **Budget Compliance Check**
   ```bash
   # Check monthly costs and budget utilization
   uv run python scripts/deploy/cost_optimizer.py
   ```

3. **Service Status Verification**
   - MongoDB Atlas: Check cluster health and connection count
   - Ollama LLM Service: Verify model availability
   - WebShare Proxies: Check proxy health and rotation
   - GitHub Actions: Review workflow execution status

4. **Performance Metrics Review**
   - Collection success rate (target: >95%)
   - Processing throughput (target: 1000+ properties/hour)
   - Error rates (target: <5%)
   - Response times (target: <2s average)

### Evening Checklist (6 PM MST)

1. **Data Collection Summary**
   ```bash
   # Generate daily collection report
   uv run python scripts/validation/validate_enhanced.py --daily-report
   ```

2. **System Optimization**
   ```bash
   # Run batch optimization analysis
   uv run python scripts/deploy/batch_optimizer.py
   ```

3. **Tomorrow's Preparation**
   - Review scheduled collection targets
   - Check proxy rotation schedule
   - Verify budget remaining for next day

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. High Error Rate (>10%)

**Symptoms:**
- Collection success rate drops below 90%
- Increased 429 (rate limit) or 403 (forbidden) responses
- Proxy failures or timeouts

**Diagnosis:**
```bash
# Check error patterns
uv run python -c "
from phoenix_real_estate.foundation.logging import get_logger
import json
from pathlib import Path

# Review recent logs
log_files = list(Path('logs').glob('*.log'))
for log_file in sorted(log_files)[-3:]:
    print(f'\n=== {log_file} ===')
    with open(log_file) as f:
        lines = f.readlines()
        error_lines = [l for l in lines if 'ERROR' in l]
        for line in error_lines[-10:]:
            print(line.strip())
"
```

**Resolution:**
1. **Rate Limiting Issues:**
   ```bash
   # Reduce collection frequency temporarily
   # Edit collection schedule in GitHub Actions
   # Increase delays between requests
   ```

2. **Proxy Issues:**
   ```bash
   # Check proxy health
   uv run python -c "
   from phoenix_real_estate.collectors.common.proxy_manager import ProxyManager
   import asyncio
   
   async def check_proxies():
       proxy_manager = ProxyManager()
       health = await proxy_manager.check_proxy_health()
       print(f'Healthy proxies: {health}')
   
   asyncio.run(check_proxies())
   "
   
   # Rotate to backup proxies if needed
   ```

3. **API Changes:**
   - Check Maricopa County website for structure changes
   - Review Phoenix MLS selectors and update if needed
   - Test with small batch to verify fixes

#### 2. High Cost Usage (>80% of budget)

**Symptoms:**
- Monthly costs approaching $20+ (80% of $25 budget)
- Cost alerts triggered
- High proxy or API usage

**Diagnosis:**
```bash
# Detailed cost analysis
uv run python scripts/deploy/cost_optimizer.py --detailed-analysis
```

**Resolution:**
1. **Immediate Actions:**
   - Pause non-essential collections
   - Reduce batch sizes
   - Switch to free proxies for testing
   - Implement collection quotas

2. **Optimization:**
   ```bash
   # Apply cost optimizations
   uv run python scripts/deploy/cost_optimizer.py --apply-recommendations
   
   # Reduce collection frequency
   # Optimize batch processing
   ```

#### 3. Database Connection Issues

**Symptoms:**
- Connection timeouts
- Authentication failures
- High response times

**Diagnosis:**
```bash
# Test database connectivity
uv run python -c "
from phoenix_real_estate.foundation.database import DatabaseConnection
from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
import asyncio

async def test_db():
    config = EnvironmentConfigProvider()
    db = DatabaseConnection(config)
    try:
        await db.health_check()
        print('Database connection: OK')
    except Exception as e:
        print(f'Database connection failed: {e}')
        
asyncio.run(test_db())
"
```

**Resolution:**
1. Check MongoDB Atlas cluster status
2. Verify network connectivity
3. Check connection string and credentials
4. Review connection pool settings
5. Restart services if needed

#### 4. LLM Processing Failures

**Symptoms:**
- Processing pipeline errors
- Ollama service unavailable
- High processing times

**Diagnosis:**
```bash
# Check Ollama service
curl -X POST http://localhost:11434/api/generate -d '{
  "model": "llama3.2:latest",
  "prompt": "Test",
  "stream": false
}'

# Check processing pipeline
uv run pytest tests/collectors/processing/ -v
```

**Resolution:**
1. **Restart Ollama:**
   ```bash
   # Stop and restart Ollama service
   pkill ollama
   ollama serve &
   
   # Verify model availability
   ollama list
   ```

2. **Processing Pipeline:**
   ```bash
   # Test pipeline components
   uv run python -c "
   from phoenix_real_estate.collectors.processing.pipeline import DataProcessingPipeline
   from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
   import asyncio
   
   async def test_pipeline():
       config = EnvironmentConfigProvider()
       pipeline = DataProcessingPipeline(config)
       # Test with sample data
       
   asyncio.run(test_pipeline())
   "
   ```

## Maintenance Procedures

### Weekly Maintenance (Sundays, 2 AM MST)

1. **System Updates**
   ```bash
   # Update dependencies
   uv sync --upgrade
   
   # Run security scans
   uv run bandit -r src/
   uv run safety check
   ```

2. **Database Maintenance**
   ```bash
   # Database cleanup and optimization
   uv run python scripts/database/cleanup_old_data.py
   
   # Index optimization
   uv run python scripts/database/optimize_indexes.py
   ```

3. **Log Rotation**
   ```bash
   # Archive old logs
   find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
   find logs/ -name "*.log.gz" -mtime +30 -delete
   ```

4. **Performance Analysis**
   ```bash
   # Generate weekly performance report
   uv run python scripts/deploy/performance_baseline.py --weekly-report
   ```

### Monthly Maintenance (First Sunday)

1. **Cost Analysis and Budget Planning**
   ```bash
   # Generate monthly cost report
   uv run python scripts/deploy/cost_optimizer.py --monthly-report
   
   # Plan next month's budget allocation
   ```

2. **Security Review**
   ```bash
   # Rotate API keys (if needed)
   # Review access logs
   # Update security configurations
   ```

3. **Capacity Planning**
   ```bash
   # Analyze growth trends
   # Plan infrastructure scaling
   # Review storage requirements
   ```

## Emergency Response Procedures

### Critical System Failure

1. **Immediate Response**
   - Stop all active collection processes
   - Notify stakeholders
   - Begin troubleshooting

2. **Diagnosis Steps**
   ```bash
   # Quick system check
   uv run python scripts/deploy/health_check.py --emergency
   
   # Check all services
   systemctl status mongodb
   ps aux | grep ollama
   curl -I https://www.phoenixmlssearch.com
   ```

3. **Recovery Actions**
   - Implement emergency fixes
   - Activate backup systems if available
   - Document incident for post-mortem

### Data Loss or Corruption

1. **Immediate Actions**
   - Stop all write operations
   - Assess scope of data loss
   - Activate backup recovery procedures

2. **Recovery Process**
   ```bash
   # Restore from MongoDB Atlas backup
   # Verify data integrity
   # Resume operations gradually
   ```

### Budget Exceeded

1. **Emergency Cost Control**
   - Immediately pause all data collection
   - Switch to free-tier services
   - Implement strict quotas

2. **Assessment and Planning**
   - Analyze cost spike causes
   - Plan budget reallocation
   - Implement additional cost controls

## Performance Baselines and SLAs

### Service Level Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| **Uptime** | 99.5% | <99% | <95% |
| **Success Rate** | >95% | <90% | <80% |
| **Response Time** | <2s avg | >5s avg | >10s avg |
| **Throughput** | 1000+ props/hr | <800 props/hr | <500 props/hr |
| **Error Rate** | <5% | >10% | >20% |
| **Cost Efficiency** | <$0.005/property | >$0.010/property | >$0.020/property |

### Monitoring Thresholds

```yaml
resource_limits:
  cpu_warning: 70%
  cpu_critical: 85%
  memory_warning: 75%
  memory_critical: 90%
  disk_warning: 80%
  disk_critical: 95%
  
cost_limits:
  monthly_warning: $20.00  # 80% of budget
  monthly_critical: $23.75  # 95% of budget
  daily_warning: $0.80
  daily_critical: $1.00
```

## Contact Information

### Escalation Path

1. **Level 1**: Automated monitoring and alerts
2. **Level 2**: Operations team notification
3. **Level 3**: Technical lead involvement
4. **Level 4**: Business stakeholder notification

### Service Contacts

- **MongoDB Atlas**: Support portal + phone
- **WebShare Proxies**: Email support
- **GitHub**: Status page monitoring
- **Email Service**: Provider-specific support

## Change Management

### Production Changes

1. **Pre-Change Requirements**
   - Testing in development environment
   - Rollback plan preparation
   - Stakeholder approval
   - Maintenance window scheduling

2. **Change Process**
   ```bash
   # Pre-change validation
   uv run pytest tests/ --integration
   
   # Deploy changes
   git checkout main
   git pull origin main
   uv sync
   
   # Post-change validation
   uv run python scripts/deploy/validate_pipeline.py
   ```

3. **Post-Change Monitoring**
   - Extended monitoring period (24 hours)
   - Performance comparison with baseline
   - Rollback if issues detected

## Documentation Updates

This runbook should be reviewed and updated:
- **Weekly**: Performance baselines and thresholds
- **Monthly**: Procedures and contact information
- **Quarterly**: Architecture diagrams and escalation paths
- **After incidents**: Lessons learned and procedure improvements

---

**Document Control**  
- **Version**: 1.0.0
- **Approved by**: Technical Lead
- **Next Review Date**: September 3, 2025
- **Change History**: Initial version
