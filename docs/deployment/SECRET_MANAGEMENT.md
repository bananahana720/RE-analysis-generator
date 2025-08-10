# 🚨 CRITICAL: GitHub Actions Secrets Configuration Guide

**PRODUCTION OUTAGE ALERT**: System has been DOWN since August 8, 2025 due to missing GitHub Actions secrets. This guide provides **IMMEDIATE** setup instructions for production recovery.

## ⚡ IMMEDIATE ACTION REQUIRED

### Current Status: PRODUCTION FAILURE
- ❌ **CI/CD Pipeline**: 100% failure rate
- ❌ **Data Collection**: Not operational  
- ❌ **Integration Tests**: Cannot authenticate to external services
- ❌ **E2E Tests**: Failing due to missing API keys
- ❌ **Monitoring**: Alert systems non-functional

### Root Cause
All repository secrets were removed during security cleanup but never reconfigured in GitHub repository settings.

---

## 🛠️ STEP-BY-STEP SECRET CONFIGURATION

### Step 1: Access GitHub Repository Settings

1. **Navigate to Repository**: `https://github.com/[YOUR_USERNAME]/RE-analysis-generator`
2. **Click Settings Tab** (top navigation, right side)
3. **In left sidebar**: Scroll to "Secrets and variables" section
4. **Click "Actions"**

### Step 2: Configure Production Secrets

Configure these secrets in the **Production environment**:

#### 🔑 MONGODB_URL (CRITICAL)
```
Name: MONGODB_URL
Value: [MongoDB Atlas connection string]
Environment: Production
Description: Production database connection string
Format: mongodb+srv://username:password@cluster.mongodb.net/phoenix_real_estate
```

#### 🔑 MARICOPA_API_KEY (CRITICAL)
```
Name: MARICOPA_API_KEY
Value: [UUID format API key]
Environment: Production
Description: Maricopa County Assessor API key
Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

#### 🔑 WEBSHARE_API_KEY (CRITICAL)
```
Name: WEBSHARE_API_KEY
Value: [WebShare proxy service API key]
Environment: Production
Description: Proxy service for Phoenix MLS scraping
Format: 32+ character alphanumeric string
```

#### 🔑 CAPTCHA_API_KEY (CRITICAL)
```
Name: CAPTCHA_API_KEY
Value: [2captcha service API key]
Environment: Production
Description: CAPTCHA solving service for Phoenix MLS
Format: 32+ character alphanumeric string
```

### Step 3: Configure Test Environment Secrets

Configure these secrets in the **Default environment** (for CI/CD):

#### 🧪 TEST_MONGODB_PASSWORD
```
Name: TEST_MONGODB_PASSWORD
Value: test_mongodb_secure_password_123
Environment: Default (Repository level)
Description: Password for CI/CD test MongoDB instance
Usage: mongodb://admin:${{ secrets.TEST_MONGODB_PASSWORD }}@localhost:27017/
```

#### 🧪 TEST_MARICOPA_API_KEY
```
Name: TEST_MARICOPA_API_KEY
Value: [Test/sandbox Maricopa API key - UUID format]
Environment: Default (Repository level)
Description: Test API key for Maricopa County integration tests
Fallback: TEST_MARICOPA_API (alternative name)
```

#### 🧪 TEST_WEBSHARE_API_KEY
```
Name: TEST_WEBSHARE_API_KEY
Value: [Test/sandbox WebShare API key]
Environment: Default (Repository level)
Description: Test proxy service key for CI/CD tests
Fallback: TEST_WEBSHARE_API (alternative name)
```

#### 🧪 TEST_CAPTCHA_API_KEY
```
Name: TEST_CAPTCHA_API_KEY
Value: [Test/sandbox 2captcha API key]
Environment: Default (Repository level)
Description: Test CAPTCHA service key for E2E tests
```

---

## ✅ IMMEDIATE VALIDATION STEPS

### Step 4: Verify Secret Configuration

#### Manual Workflow Test
1. Go to **Actions** tab in repository
2. Select **"Continuous Integration & Deployment"** workflow
3. Click **"Run workflow"** button
4. Select `main` branch
5. Click **"Run workflow"**
6. **Expected Result**: `validate-secrets` job should **PASS**

#### CLI Verification (if GitHub CLI available)
```bash
# Check if secrets are configured (values not shown for security)
gh secret list

# Expected output should include:
# MONGODB_URL                Production environment
# MARICOPA_API_KEY          Production environment
# WEBSHARE_API_KEY          Production environment
# CAPTCHA_API_KEY           Production environment
# TEST_MONGODB_PASSWORD     Repository level
# TEST_MARICOPA_API_KEY     Repository level
# TEST_WEBSHARE_API_KEY     Repository level
# TEST_CAPTCHA_API_KEY      Repository level
```

### Step 5: Test Secret Access
```bash
# Run dedicated secrets access test
# Navigate to: Actions → "Test Secrets Access" → Run workflow

# This workflow will validate:
# - Secret accessibility from workflows
# - Correct secret format validation
# - Fallback pattern support
# - Environment isolation
```

---

## 🔒 SECRET FORMATS & VALIDATION

### Required Production Secret Formats

| Secret Name | Format | Example Pattern | Critical Level |
|-------------|--------|----------------|----------------|
| `MONGODB_URL` | MongoDB URI | `mongodb+srv://...` | **CRITICAL** |
| `MARICOPA_API_KEY` | UUID | `12345678-90ab-cdef-1234-567890abcdef` | **CRITICAL** |
| `WEBSHARE_API_KEY` | Alphanumeric | `abcdef1234567890...` (32+ chars) | **CRITICAL** |
| `CAPTCHA_API_KEY` | Alphanumeric | `fedcba0987654321...` (32+ chars) | **CRITICAL** |

### Test Environment Secret Formats

| Secret Name | Format | Critical Level |
|-------------|--------|----------------|
| `TEST_MONGODB_PASSWORD` | String | **HIGH** |
| `TEST_MARICOPA_API_KEY` | UUID | **HIGH** |
| `TEST_WEBSHARE_API_KEY` | Alphanumeric | **MEDIUM** |
| `TEST_CAPTCHA_API_KEY` | Alphanumeric | **MEDIUM** |

### Secret Validation Commands
```bash
# Validate secret formats using local script
python scripts/validation/validate_secrets.py --validate-format

# Check for production secret requirements
python scripts/setup/setup_secrets.py validate .env

# Test MongoDB connection
python scripts/testing/test_mongodb_connection.py

# Test API credentials
python scripts/testing/api_credential_setup.py
```

---

## 🛡️ SECURITY REQUIREMENTS

### Environment Separation
- **Production Secrets**: Must be configured in "Production" environment
- **Test Secrets**: Must be configured in "Default" (repository level) environment
- **Never mix**: Production values must NEVER be used in test environment

### Secret Value Guidelines
- ✅ **Use dedicated API keys**: Separate keys for test/production
- ✅ **Strong passwords**: Minimum 12 characters for database passwords
- ✅ **Valid formats**: All API keys must match required patterns
- ❌ **No placeholder values**: Never use "test-key" or default values
- ❌ **No production in test**: Never use production credentials for testing

### Access Control
```yaml
Production Environment:
  - MONGODB_URL: Production environment only
  - MARICOPA_API_KEY: Production environment only  
  - WEBSHARE_API_KEY: Production environment only
  - CAPTCHA_API_KEY: Production environment only

Default Environment:
  - TEST_MONGODB_PASSWORD: All workflows access
  - TEST_MARICOPA_API_KEY: CI/CD workflows only
  - TEST_WEBSHARE_API_KEY: CI/CD workflows only
  - TEST_CAPTCHA_API_KEY: CI/CD workflows only
```

---

## 🚨 EMERGENCY RECOVERY PROCEDURES

### If Secret Configuration Fails

#### Issue 1: Workflow Still Failing After Configuration
```bash
# 1. Check secret names exactly match requirements
# 2. Verify environment assignments (Production vs Default)
# 3. Confirm secret values don't contain placeholder text
# 4. Re-run validation workflow manually
```

#### Issue 2: API Authentication Errors  
```bash
# 1. Test API keys independently:
python scripts/testing/api_integration_diagnostic.py

# 2. Verify API key formats:
python scripts/validation/validate_secrets.py --check-api-keys

# 3. Check API quota/limits at provider
```

#### Issue 3: Database Connection Failures
```bash
# 1. Test MongoDB connection:
python scripts/testing/test_mongodb_connection.py

# 2. Verify MongoDB Atlas network access
# 3. Check database user permissions
# 4. Validate connection string format
```

### Recovery Validation Checklist

- [ ] All 8 required secrets configured (4 production + 4 test)
- [ ] Production secrets in "Production" environment
- [ ] Test secrets in "Default" environment  
- [ ] No placeholder values (test-key, etc.)
- [ ] Secret formats match validation patterns
- [ ] `validate-secrets` workflow job passes
- [ ] At least one full CI/CD pipeline run succeeds
- [ ] Integration tests can access external APIs
- [ ] E2E tests complete without authentication errors

---

## 📊 TROUBLESHOOTING GUIDE

### Common Error Patterns

#### Error: "Missing required secrets"
**Cause**: Secret not configured or wrong environment
**Solution**: 
1. Check secret exists in GitHub Settings → Actions
2. Verify environment assignment (Production vs Default)
3. Ensure exact name matches (case-sensitive)

#### Error: "Invalid API key format"
**Cause**: API key doesn't match expected pattern
**Solution**:
1. Check secret value format against patterns above
2. Remove any trailing spaces or newlines
3. Verify no placeholder text remains

#### Error: "MongoDB connection failed"
**Cause**: Database credentials or connection string invalid
**Solution**:
1. Test connection string format: `mongodb+srv://...`
2. Verify MongoDB Atlas network access whitelist
3. Check database user has required permissions

#### Error: "Workflow timeout" or "Service unavailable"
**Cause**: External API service issues
**Solution**:
1. Check API service status (Maricopa, WebShare, 2captcha)
2. Verify API quotas not exceeded
3. Test with reduced request rates

### Debug Commands
```bash
# Test all secret accessibility
.github/workflows/test-secrets-access.yml

# Validate secret formats locally
python scripts/validation/validate_secrets.py --comprehensive

# Test external service connectivity
python scripts/testing/api_integration_diagnostic.py --all-services

# Database connectivity test  
python scripts/testing/test_db_connection.py

# Full system health check
python scripts/validation/validate_environment.py
```

---

## 🔄 SECRET ROTATION PROCEDURES

### Immediate Rotation (Security Incident)
1. **Revoke compromised secrets** at provider (API dashboard)
2. **Generate new credentials** with same format requirements
3. **Update GitHub secrets** with new values immediately
4. **Test workflows** to confirm functionality restored
5. **Monitor logs** for any remaining authentication failures

### Scheduled Rotation (Every 90 Days)
1. **Plan rotation** during low-traffic period
2. **Generate new credentials** at each provider
3. **Stage new secrets** in GitHub (use "Update" button)
4. **Test in staging** environment first
5. **Apply to production** and monitor
6. **Document rotation** in security log

### Rotation Validation
```bash
# After rotation, validate:
python scripts/validation/validate_secrets.py --post-rotation
python scripts/testing/api_credential_setup.py --test-all
```

---

## 📞 EMERGENCY CONTACTS

### For Missing Secret Values
- **MongoDB Atlas**: Check MongoDB Atlas dashboard → Database Access
- **Maricopa API**: https://mcassessor.maricopa.gov/api (registration required)
- **WebShare Proxy**: https://webshare.io account dashboard
- **2captcha Service**: https://2captcha.com account dashboard

### Critical Escalation
If unable to recover production secrets:
1. **Check password managers** for stored credentials
2. **Contact API providers** for account recovery
3. **Review backup documentation** in secure storage
4. **Contact team lead** for emergency credential access

---

## ✅ POST-CONFIGURATION VALIDATION

### Success Indicators
- ✅ **CI/CD Pipeline**: All jobs pass without secret errors
- ✅ **Integration Tests**: Successfully authenticate to external APIs
- ✅ **E2E Tests**: Complete full test suite without failures
- ✅ **Data Collection**: Workflows can collect and process data
- ✅ **Monitoring**: Error rates return to normal levels

### Performance Restoration Timeline
- **Immediate** (0-5 minutes): Secret configuration complete
- **Short-term** (5-15 minutes): CI/CD pipeline validates and passes
- **Medium-term** (15-60 minutes): Full test suite completes successfully  
- **Full recovery** (1-4 hours): Data collection workflows operational

### Success Validation Commands
```bash
# Comprehensive system test
python scripts/testing/production/production_test.py

# Performance validation
python scripts/testing/test_performance_optimizations.py

# Full E2E system test
python scripts/testing/run_e2e_tests.py
```

---

## 📋 COMPLETION CHECKLIST

### Secret Configuration Status
- [ ] **MONGODB_URL** - Production environment - **CRITICAL**
- [ ] **MARICOPA_API_KEY** - Production environment - **CRITICAL**  
- [ ] **WEBSHARE_API_KEY** - Production environment - **CRITICAL**
- [ ] **CAPTCHA_API_KEY** - Production environment - **CRITICAL**
- [ ] **TEST_MONGODB_PASSWORD** - Default environment - **HIGH**
- [ ] **TEST_MARICOPA_API_KEY** - Default environment - **HIGH**
- [ ] **TEST_WEBSHARE_API_KEY** - Default environment - **MEDIUM**
- [ ] **TEST_CAPTCHA_API_KEY** - Default environment - **MEDIUM**

### Validation Status  
- [ ] Manual workflow run succeeds
- [ ] `validate-secrets` job passes
- [ ] Full CI/CD pipeline completes successfully
- [ ] Integration tests authenticate to external APIs
- [ ] E2E tests complete without secret-related failures
- [ ] No secret-related errors in workflow logs

### Recovery Confirmation
- [ ] Production system operational
- [ ] Data collection workflows functional  
- [ ] Monitoring alerts resolved
- [ ] Performance metrics within normal ranges
- [ ] Documentation updated with rotation schedule

---

**🚨 URGENT REMINDER**: This is a **PRODUCTION OUTAGE** situation. Complete secret configuration **IMMEDIATELY** to restore system functionality. Contact emergency support if unable to locate required secret values.

**📅 Next Steps After Recovery**:
1. Document incident response and lessons learned
2. Implement secret monitoring and expiration alerts
3. Schedule regular secret rotation (90-day cycle)
4. Review and improve secret management procedures