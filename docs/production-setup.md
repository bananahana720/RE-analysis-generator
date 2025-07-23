# Production Environment Setup Guide

This guide explains how to configure and deploy the Phoenix Real Estate Data Collector in a production environment.

## Overview

The production environment uses a combination of configuration files and environment variables to manage settings securely. The system is designed to collect real estate data from multiple sources while maintaining high availability and data quality.

## Configuration Files

### 1. Base Configuration Files

The system uses a hierarchical configuration structure:

- `config/base.yaml` - Default settings for all environments
- `config/production.yaml` - Production-specific overrides
- `config/production-phoenix-mls.yaml` - Phoenix MLS specific settings
- `config/production-deployment.yaml` - Deployment and infrastructure settings

### 2. Secrets Management

**IMPORTANT**: Never commit secrets to version control!

1. Copy the template file:
   ```bash
   cp config/production-secrets.yaml.template config/production-secrets.yaml
   ```

2. Fill in actual production values in `production-secrets.yaml`

3. Add to `.gitignore`:
   ```
   config/production-secrets.yaml
   ```

### 3. Environment Variables

For sensitive data that changes frequently or needs to be injected at runtime:

1. Create `.env.production` (see `.env.sample` for template)
2. Never commit `.env.production` to version control
3. Use a secure secrets management service in production

## Production Setup Steps

### Step 1: Database Setup

1. Create MongoDB Atlas production cluster:
   - Go to [MongoDB Atlas](https://cloud.mongodb.com)
   - Create M10 or higher cluster for production
   - Configure network access (whitelist production IPs)
   - Create database user with appropriate permissions

2. Update connection string in secrets:
   ```yaml
   database:
     mongodb:
       connection_string: "mongodb+srv://prod_user:password@cluster.mongodb.net/phoenix_real_estate"
   ```

### Step 2: Proxy Configuration

1. Set up Webshare.io account:
   - Sign up at [Webshare.io](https://webshare.io)
   - Purchase premium proxy package
   - Get username, password, and API key

2. Configure proxy credentials:
   ```yaml
   proxy:
     webshare:
       username: "your_username"
       password: "your_password"
   ```

### Step 3: API Keys

1. Maricopa County API:
   - Register at [Maricopa County API Portal](https://mcassessor.maricopa.gov/api)
   - Get production API key
   - Update in secrets configuration

2. Particle Space API (when available):
   - Register for API access
   - Configure API key and limits

### Step 4: Monitoring Setup

1. Configure Sentry for error tracking:
   ```yaml
   monitoring:
     sentry:
       dsn: "https://your_key@sentry.io/project"
   ```

2. Set up application monitoring (Datadog/New Relic)

3. Configure log aggregation (CloudWatch/ELK)

### Step 5: Security Configuration

1. Generate strong encryption keys:
   ```bash
   # Generate 32-byte key
   openssl rand -hex 32
   ```

2. Set up SSL certificates:
   - Obtain certificates from CA
   - Configure paths in deployment config

3. Configure firewall rules:
   - Allow only necessary ports
   - Whitelist production IPs

### Step 6: Deployment

1. Install dependencies:
   ```bash
   uv sync --no-dev
   ```

2. Run production checks:
   ```bash
   # Validate configuration
   python -m phoenix_real_estate.validate_config --env production
   
   # Run tests
   uv run pytest
   
   # Check code quality
   make ruff && make pyright
   ```

3. Deploy application:
   ```bash
   # Using systemd
   sudo systemctl start phoenix-collector
   
   # Or using Docker
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Production Checklist

Before going live, ensure:

- [ ] All placeholder values replaced with actual credentials
- [ ] MongoDB Atlas cluster configured and accessible
- [ ] Proxy credentials valid and tested
- [ ] API keys configured and rate limits understood
- [ ] SSL certificates installed
- [ ] Monitoring and alerting configured
- [ ] Backup procedures in place
- [ ] Disaster recovery plan documented
- [ ] Security audit completed
- [ ] Performance testing completed
- [ ] Documentation updated

## Environment-Specific Settings

### Phoenix MLS Configuration

The `config/production-phoenix-mls.yaml` file contains:

- Base URL: `https://www.phoenixmlssearch.com`
- Rate limiting: 60 requests/hour
- Anti-detection settings enabled
- Proxy rotation configured
- CSS selectors for data extraction

### Data Collection Schedule

Production runs on the following schedule:

- Daily full collection: 2 AM Phoenix time
- Incremental updates: Every 6 hours
- Target ZIP codes: 85031, 85033, 85035

### Performance Targets

- Properties per hour: 1000+
- Success rate: >95%
- Response time (p95): <5 seconds
- Proxy health: 2+ healthy proxies minimum

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Collection Metrics**:
   - Properties collected per hour
   - Success/failure rates by source
   - Average response times

2. **System Metrics**:
   - CPU and memory usage
   - Disk I/O
   - Network throughput

3. **Data Quality**:
   - Validation success rate
   - Data completeness scores
   - Duplicate detection rate

### Alert Thresholds

- Error rate > 5%: Warning
- Error rate > 10%: Critical
- Healthy proxies < 2: Critical
- Response time > 10s (p99): Warning

## Troubleshooting

### Common Issues

1. **Proxy Connection Failures**:
   - Check proxy credentials
   - Verify proxy health status
   - Review proxy rotation logs

2. **Rate Limiting**:
   - Check request counters
   - Verify delay settings
   - Review rate limit configuration

3. **Data Quality Issues**:
   - Check CSS selectors
   - Review parser logs
   - Validate against site changes

### Debug Mode

Enable debug logging temporarily:

```bash
LOG_LEVEL=DEBUG python -m phoenix_real_estate.collectors.phoenix_mls
```

## Security Best Practices

1. **Credential Rotation**:
   - Rotate all credentials every 90 days
   - Use automated rotation where possible
   - Document rotation procedures

2. **Access Control**:
   - Limit production access
   - Use MFA for all accounts
   - Audit access regularly

3. **Data Protection**:
   - Encrypt sensitive data at rest
   - Use SSL for all connections
   - Sanitize logs of PII

## Maintenance

### Regular Tasks

- **Daily**: Check collection logs and metrics
- **Weekly**: Review error rates and performance
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Rotate credentials and review access

### Update Procedures

1. Test updates in staging first
2. Schedule maintenance window
3. Create backup before updates
4. Monitor closely after deployment
5. Have rollback plan ready

## Support

For production issues:

1. Check monitoring dashboards
2. Review recent logs
3. Consult troubleshooting guide
4. Contact on-call engineer if critical

Remember: Production data is valuable - always err on the side of caution!