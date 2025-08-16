# Secret Configuration Guide

Complete guide for managing GitHub Secrets in the Phoenix Real Estate project.

## Table of Contents

- [Overview](#overview)
- [Required Secrets](#required-secrets)
- [Environment-Specific Configuration](#environment-specific-configuration)
- [Setup Instructions](#setup-instructions)
- [Validation and Testing](#validation-and-testing)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)
- [Migration Guide](#migration-guide)

## Overview

The Phoenix Real Estate project uses GitHub Secrets to securely store sensitive configuration data including API keys, database connection strings, and service credentials. This guide provides comprehensive instructions for configuring and managing these secrets.

### Secret Management Principles

- **Security First**: All sensitive data must be stored as GitHub Secrets, never in code
- **Environment Separation**: Clear separation between test and production secrets
- **Naming Standards**: Consistent naming conventions for easy maintenance
- **Validation**: Automated validation ensures secrets are correctly configured
- **Documentation**: Clear documentation of secret purposes and formats

## Required Secrets

### Production Environment

| Secret Name | Purpose | Format | Required |
|-------------|---------|---------|----------|
| `MONGODB_URL` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.net/db` | ✅ Critical |
| `MARICOPA_API_KEY` | Maricopa County API access | UUID format | ✅ Critical |
| `WEBSHARE_API_KEY` | WebShare proxy service | Alphanumeric string | ✅ Critical |
| `CAPTCHA_API_KEY` | 2captcha service for CAPTCHA solving | 32-character string | ✅ Critical |

### Test Environment

| Secret Name | Purpose | Format | Required |
|-------------|---------|---------|----------|
| `TEST_MONGODB_PASSWORD` | Test MongoDB password | Simple password | ⚠️ High |
| `TEST_MARICOPA_API_KEY` | Test Maricopa API key | UUID format | ⚠️ High |
| `TEST_WEBSHARE_API_KEY` | Test WebShare API key | Alphanumeric string | ⚠️ High |
| `TEST_CAPTCHA_API_KEY` | Test 2captcha API key | 32-character string | ⚠️ High |

### Optional Configuration

| Secret Name | Purpose | Format | Required |
|-------------|---------|---------|----------|
| `EMAIL_ENABLED` | Enable email notifications | `true` or `false` | ❌ Optional |
| `SLACK_WEBHOOK` | Slack notification webhook | HTTPS URL | ❌ Optional |

### Legacy Secret Names (Deprecated)

⚠️ **These names are deprecated and should be migrated to current standards:**

- `MARICOPA_API` → Use `MARICOPA_API_KEY`
- `WEBSHARE_API` → Use `WEBSHARE_API_KEY`
- `TEST_MARICOPA_API` → Use `TEST_MARICOPA_API_KEY`
- `TEST_WEBSHARE_API` → Use `TEST_WEBSHARE_API_KEY`
- `MONGODB_PASSWORD` → Use `MONGODB_URL` (full connection string)
- `MONGO_URL` → Use `MONGODB_URL`
- `CAPTCHA_KEY` → Use `CAPTCHA_API_KEY`

## Environment-Specific Configuration

### Production Environment

Production secrets are used by:
- Daily data collection workflows
- System monitoring and alerting
- Production deployment pipelines
- Emergency response automation

**Critical Requirements:**
- All production secrets must be configured correctly
- Invalid or missing production secrets will cause system outages
- Production secret validation runs daily at 2 AM UTC
- Automatic alerts are created for critical production secret failures

### Test Environment

Test secrets are used by:
- Development and testing workflows
- Integration testing pipelines
- Feature validation workflows
- Development environment setup

**Configuration Notes:**
- Test secrets can use placeholder values for development
- Test environment failures are non-critical but should be resolved within 24 hours
- Fallback mechanisms allow workflows to continue with limited functionality

## Setup Instructions

### Step 1: Access Repository Settings

1. Navigate to the GitHub repository: `https://github.com/your-username/RE-analysis-generator`
2. Click the **Settings** tab (requires repository admin access)
3. In the left sidebar, click **Secrets and variables** → **Actions**

### Step 2: Configure Production Secrets

#### MongoDB URL (`MONGODB_URL`)

**Purpose**: Production MongoDB Atlas connection string for data storage

**How to Obtain**:
1. Log into MongoDB Atlas dashboard
2. Go to your cluster → Connect → Connect your application
3. Copy the connection string

**Format**: `mongodb+srv://username:password@cluster.mongodb.net/database`

**Example**: `mongodb+srv://phoenixuser:SecurePass123@cluster0.abc123.mongodb.net/phoenix_real_estate`

**Configuration**:
1. Click **New repository secret**
2. Name: `MONGODB_URL`
3. Value: Your complete MongoDB connection string
4. Click **Add secret**

#### Maricopa API Key (`MARICOPA_API_KEY`)

**Purpose**: Access to Maricopa County Assessor's Office API for property data

**How to Obtain**:
1. Contact Maricopa County Assessor's Office
2. Request API access for property data
3. Complete registration process
4. Receive UUID-format API key

**Format**: UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)

**Example**: `a1b2c3d4-e5f6-7890-1234-567890abcdef`

**Configuration**:
1. Click **New repository secret**
2. Name: `MARICOPA_API_KEY`
3. Value: Your UUID-format API key
4. Click **Add secret**

#### WebShare API Key (`WEBSHARE_API_KEY`)

**Purpose**: Proxy service for web scraping to avoid IP blocking

**How to Obtain**:
1. Go to https://www.webshare.io/
2. Create an account
3. Navigate to Dashboard → API
4. Copy your API key

**Format**: Alphanumeric string

**Example**: `abc123def456ghi789jkl012mno345pqr678stu901`

**Configuration**:
1. Click **New repository secret**
2. Name: `WEBSHARE_API_KEY`
3. Value: Your WebShare API key
4. Click **Add secret**

#### 2captcha API Key (`CAPTCHA_API_KEY`)

**Purpose**: CAPTCHA solving service for automated data collection

**How to Obtain**:
1. Go to https://2captcha.com/
2. Create an account and add funds
3. Navigate to Account → API Key
4. Copy your API key

**Format**: 32-character alphanumeric string

**Example**: `a1b2c3d4e5f6789012345678901234567`

**Configuration**:
1. Click **New repository secret**
2. Name: `CAPTCHA_API_KEY`
3. Value: Your 2captcha API key
4. Click **Add secret**

### Step 3: Configure Test Environment Secrets

#### Test MongoDB Password (`TEST_MONGODB_PASSWORD`)

**Purpose**: Password for local test MongoDB instance

**Format**: Simple password (can be basic for testing)

**Example**: `testpassword123`

**Configuration**:
1. Click **New repository secret**
2. Name: `TEST_MONGODB_PASSWORD`
3. Value: Your test MongoDB password
4. Click **Add secret**

#### Test API Keys

Follow similar patterns for test environment:
- `TEST_MARICOPA_API_KEY`: Test version of Maricopa API key
- `TEST_WEBSHARE_API_KEY`: Test version of WebShare API key  
- `TEST_CAPTCHA_API_KEY`: Test version of 2captcha API key

**Note**: Test keys can use placeholder values or actual test accounts from service providers.

### Step 4: Configure Optional Secrets

#### Email Notifications (`EMAIL_ENABLED`)

**Purpose**: Enable/disable email notification system

**Format**: `true` or `false`

**Configuration**:
1. Click **New repository secret**
2. Name: `EMAIL_ENABLED`
3. Value: `true` (to enable) or `false` (to disable)
4. Click **Add secret**

#### Slack Notifications (`SLACK_WEBHOOK`)

**Purpose**: Slack webhook URL for notifications

**How to Obtain**:
1. Create a Slack app in your workspace
2. Enable incoming webhooks
3. Copy the webhook URL

**Format**: HTTPS URL

**Example**: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`

**Configuration**:
1. Click **New repository secret**
2. Name: `SLACK_WEBHOOK`
3. Value: Your Slack webhook URL
4. Click **Add secret**

## Validation and Testing

### Automated Validation

The repository includes automated secret validation that runs:
- **Daily**: At 2 AM UTC via scheduled workflow
- **On-Demand**: Manual trigger via GitHub Actions
- **Integration**: Called by other workflows before critical operations

### Manual Validation

To manually validate your secret configuration:

1. Go to **Actions** tab in the repository
2. Click **Validate Secrets Configuration** workflow
3. Click **Run workflow**
4. Select validation options:
   - **Environment**: `production`, `test`, or `both`
   - **Test Connectivity**: Enable to test service connections
   - **Detailed Output**: Enable for comprehensive diagnostics
5. Click **Run workflow**

### Validation Results

The validation workflow provides:
- ✅ **Success**: All secrets properly configured
- ⚠️ **Warning**: Minor issues or format problems
- ❌ **Critical**: Missing or invalid secrets requiring immediate attention

### Connectivity Testing

When enabled, the validation workflow tests:
- MongoDB Atlas connection
- Maricopa API authentication
- WebShare proxy service access
- 2captcha service availability

## Troubleshooting

### Common Issues and Solutions

#### Issue: MongoDB Connection Failed

**Symptoms**:
- `MongoDB Atlas: Connection failed` in validation logs
- Data collection workflows failing with database errors

**Possible Causes**:
1. Invalid connection string format
2. Incorrect username/password
3. Network connectivity issues
4. MongoDB Atlas whitelist restrictions

**Solutions**:
1. **Verify Format**: Ensure `MONGODB_URL` starts with `mongodb://` or `mongodb+srv://`
2. **Check Credentials**: Verify username and password in MongoDB Atlas
3. **Network Access**: Ensure MongoDB Atlas allows connections from GitHub Actions IPs
4. **Connection String**: Get fresh connection string from MongoDB Atlas dashboard

#### Issue: Maricopa API Authentication Failed

**Symptoms**:
- `Maricopa API: Connection failed or unauthorized` in validation logs
- Data collection returning authentication errors

**Possible Causes**:
1. Invalid API key format
2. Expired or revoked API key
3. API rate limiting
4. Service downtime

**Solutions**:
1. **Verify Format**: Ensure key matches UUID pattern (8-4-4-4-12)
2. **Contact Provider**: Verify API key status with Maricopa County
3. **Rate Limits**: Check API usage and limits
4. **Service Status**: Verify Maricopa API service availability

#### Issue: WebShare Proxy Service Failed

**Symptoms**:
- `WebShare API: Connection failed` in validation logs
- Scraping workflows failing with proxy errors

**Possible Causes**:
1. Invalid API key
2. Insufficient proxy quota
3. Account suspension
4. Service outage

**Solutions**:
1. **Check API Key**: Verify key in WebShare dashboard
2. **Account Status**: Ensure account is active and funded
3. **Quota**: Check remaining proxy quota
4. **Service Health**: Verify WebShare service status

#### Issue: 2captcha Service Failed

**Symptoms**:
- `2captcha API: Connection failed` in validation logs
- CAPTCHA solving failures in scraping workflows

**Possible Causes**:
1. Invalid API key
2. Insufficient account balance
3. Service overload
4. Account restrictions

**Solutions**:
1. **Verify API Key**: Check key in 2captcha account dashboard
2. **Add Funds**: Ensure sufficient account balance
3. **Service Status**: Check 2captcha service status
4. **Account Health**: Verify account is in good standing

### Secret Format Validation

**MongoDB URL Format**:
```
✅ Valid:   mongodb+srv://user:pass@cluster.mongodb.net/database
✅ Valid:   mongodb://user:pass@host:port/database
❌ Invalid: user:pass@cluster.mongodb.net/database (missing protocol)
❌ Invalid: mongodb://cluster.mongodb.net/database (missing credentials)
```

**UUID Format (Maricopa API Key)**:
```
✅ Valid:   a1b2c3d4-e5f6-7890-1234-567890abcdef
❌ Invalid: a1b2c3d4e5f67890123456790abcdef (missing hyphens)
❌ Invalid: a1b2c3d4-e5f6-7890-1234 (too short)
```

### Emergency Recovery

If production services are down due to secret issues:

1. **Immediate Actions**:
   - Fix critical production secrets immediately
   - Run secret validation workflow to verify fixes
   - Monitor data collection workflows for recovery

2. **Validation Steps**:
   - Re-run `Validate Secrets Configuration` workflow
   - Check `Production Data Collection` workflow
   - Monitor `System Monitoring & Budget Tracking`

3. **Communication**:
   - Update any related GitHub issues
   - Notify team of resolution
   - Document lessons learned

## Security Best Practices

### Secret Management Security

1. **Access Control**:
   - Only repository administrators should manage secrets
   - Use principle of least privilege for access
   - Regularly audit secret access permissions

2. **Rotation Policy**:
   - Rotate API keys quarterly or when compromised
   - Update secrets immediately if suspicious activity detected
   - Document rotation procedures and schedules

3. **Monitoring**:
   - Enable automated secret validation
   - Monitor for unauthorized access attempts
   - Set up alerts for secret-related failures

4. **Documentation**:
   - Keep this guide updated with current practices
   - Document any custom secret requirements
   - Maintain changelog of secret modifications

### What NOT to Store as Secrets

❌ **Never store these in secrets**:
- Non-sensitive configuration values
- Public URLs or endpoints
- Default usernames that aren't sensitive
- Documentation or comments
- Empty or placeholder values in production

✅ **Only store sensitive data**:
- API keys and tokens
- Database passwords and connection strings
- Webhook URLs with embedded tokens
- Encryption keys
- Service account credentials

### Secret Naming Conventions

**Standard Patterns**:
- Production secrets: `SERVICE_TYPE` (e.g., `MONGODB_URL`, `MARICOPA_API_KEY`)
- Test secrets: `TEST_SERVICE_TYPE` (e.g., `TEST_MONGODB_PASSWORD`)
- Feature toggles: `FEATURE_ENABLED` (e.g., `EMAIL_ENABLED`)
- Service configs: `SERVICE_CONFIG` (e.g., `SLACK_WEBHOOK`)

**Avoid These Patterns**:
- Inconsistent naming (mix of old and new patterns)
- Ambiguous names that don't indicate purpose
- Generic names like `API_KEY` without service context
- Names with typos or non-standard formatting

## Migration Guide

### Migrating from Legacy Secret Names

If you're using legacy secret names, follow this migration process:

#### Step 1: Audit Current Secrets

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. List all current secrets
3. Identify any legacy names from the deprecated list above

#### Step 2: Add New Standard Secrets

1. Add new secrets with standard names
2. Copy values from legacy secrets
3. **Do not delete legacy secrets yet**

#### Step 3: Test with New Names

1. Run secret validation workflow to test new secrets
2. Run a test data collection workflow
3. Verify all functionality works with new secret names

#### Step 4: Remove Legacy Secrets

1. **Only after confirming new secrets work**
2. Delete legacy secrets one by one
3. Re-run validation after each deletion
4. Monitor for any issues

#### Migration Mapping

| Legacy Name | Current Standard | Action Required |
|-------------|------------------|-----------------|
| `MARICOPA_API` | `MARICOPA_API_KEY` | Copy value, test, remove legacy |
| `WEBSHARE_API` | `WEBSHARE_API_KEY` | Copy value, test, remove legacy |
| `TEST_MARICOPA_API` | `TEST_MARICOPA_API_KEY` | Copy value, test, remove legacy |
| `TEST_WEBSHARE_API` | `TEST_WEBSHARE_API_KEY` | Copy value, test, remove legacy |
| `MONGODB_PASSWORD` | `MONGODB_URL` | Create full connection string |
| `MONGO_URL` | `MONGODB_URL` | Rename and verify format |
| `CAPTCHA_KEY` | `CAPTCHA_API_KEY` | Copy value, test, remove legacy |

### Migration Safety Checklist

- [ ] All new standard secrets added
- [ ] Secret validation workflow passes
- [ ] Test data collection successful
- [ ] Production workflows tested (if safe)
- [ ] Legacy secrets documented before removal
- [ ] Team notified of migration
- [ ] Rollback plan prepared
- [ ] Legacy secrets removed only after verification

## Appendix

### Quick Reference Commands

**Validate Secrets**:
```bash
# Navigate to Actions tab → Validate Secrets Configuration → Run workflow
```

**Test Production Data Collection**:
```bash
# Navigate to Actions tab → Production Data Collection → Run workflow (test mode)
```

**Emergency Secret Recovery**:
```bash
# Navigate to Actions tab → Emergency Response Automation → Run workflow
```

### Support and Contacts

**For Technical Issues**:
- Create GitHub issue with label `secrets` and `support`
- Include validation workflow results
- Provide specific error messages

**For Emergency Production Issues**:
- Create GitHub issue with labels `critical`, `production`, `secrets`
- Run Emergency Response Automation workflow
- Contact repository administrators immediately

**For API Key Issues**:
- MongoDB Atlas: Contact MongoDB support
- Maricopa County: Contact Assessor's Office API team
- WebShare: Contact WebShare support
- 2captcha: Contact 2captcha support

### Related Documentation

- [Production Setup Guide](production-setup.md)
- [Monitoring Documentation](monitoring.md)
- [GitHub Actions Workflows](../.github/workflows/)
- [System Architecture](design/architecture.md)

---

**Last Updated**: December 2024  
**Version**: 2.0  
**Maintainer**: Phoenix Real Estate Development Team