# GitHub Repository Secrets Configuration Guide

**CRITICAL**: This document contains instructions for configuring missing repository secrets that are preventing CI/CD pipelines and test workflows from running.

## Current Status Analysis

### Production Environment Secrets ✅
- `MONGODB_URL` - Configured and working
- `MARICOPA_API_KEY` - Configured and working  
- `WEBSHARE_API_KEY` - Configured and working
- `CAPTCHA_API_KEY` - Configured and working

### Test Environment Secrets ❌ MISSING
- `TEST_MONGODB_PASSWORD` - **MISSING** (Critical for CI/CD)
- `TEST_MARICOPA_API_KEY` - **MISSING** (Critical for integration tests)
- `TEST_WEBSHARE_API_KEY` - **MISSING** (Critical for Phoenix MLS tests)
- `TEST_CAPTCHA_API_KEY` - **MISSING** (Critical for E2E tests)

## Impact Assessment

**Current State**: 100% workflow failure rate due to missing test secrets
- CI/CD pipeline: `validate-secrets` job fails immediately
- Integration tests: Cannot authenticate to external services
- E2E tests: Cannot access required test APIs
- Data collection workflows: Cannot validate test credentials

## Repository Secret Configuration Instructions

### Step 1: Access Repository Settings

1. Navigate to the GitHub repository: `https://github.com/[YOUR_USERNAME]/RE-analysis-generator`
2. Click on **Settings** (top navigation bar, right side)
3. In left sidebar, scroll to **Secrets and variables** section
4. Click **Actions**

### Step 2: Configure Test Environment Secrets

**IMPORTANT**: These secrets are for TEST/CI environment only - never use production values.

#### 2.1 Configure TEST_MONGODB_PASSWORD

```bash
Name: TEST_MONGODB_PASSWORD
Value: test_mongodb_secure_password_123
Environment: Default (no environment restriction)
```

**Usage**: Used to create test MongoDB connection: `mongodb://admin:${{ secrets.TEST_MONGODB_PASSWORD }}@localhost:27017/`

#### 2.2 Configure TEST_MARICOPA_API_KEY

```bash
Name: TEST_MARICOPA_API_KEY
Value: [REQUEST FROM ADMIN - UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx]
Environment: Default (no environment restriction)
```

**Usage**: Required for Maricopa County API integration tests
**Format**: Must be valid UUID format for API compatibility
**Fallback**: System also checks for `TEST_MARICOPA_API` if primary is missing

#### 2.3 Configure TEST_WEBSHARE_API_KEY

```bash
Name: TEST_WEBSHARE_API_KEY  
Value: [REQUEST FROM ADMIN - WebShare test API key]
Environment: Default (no environment restriction)
```

**Usage**: Required for Phoenix MLS scraping tests with proxy services
**Fallback**: System also checks for `TEST_WEBSHARE_API` if primary is missing

#### 2.4 Configure TEST_CAPTCHA_API_KEY

```bash
Name: TEST_CAPTCHA_API_KEY
Value: [REQUEST FROM ADMIN - 2captcha test API key]
Environment: Default (no environment restriction)
```

**Usage**: Required for E2E tests that encounter CAPTCHAs during Phoenix MLS scraping

### Step 3: Verification Commands

After configuring secrets, verify they are accessible:

#### 3.1 Manual Workflow Dispatch Test
1. Go to **Actions** tab in repository
2. Select **Continuous Integration & Deployment** workflow
3. Click **Run workflow** 
4. Select `main` branch
5. Click **Run workflow**

**Expected Result**: `validate-secrets` job should pass

#### 3.2 CLI Verification (if you have GitHub CLI)
```bash
# Check if secrets are configured (won't show values)
gh secret list

# Expected output should include:
# TEST_MONGODB_PASSWORD
# TEST_MARICOPA_API_KEY  
# TEST_WEBSHARE_API_KEY
# TEST_CAPTCHA_API_KEY
```

## Secret Environment Assignments

### Default Environment (Most Secrets)
- All `TEST_*` secrets should be in **default** environment
- Accessible to all workflows and environments
- No additional access restrictions needed

### Production Environment (Existing)
- `MONGODB_URL`, `MARICOPA_API_KEY`, `WEBSHARE_API_KEY`, `CAPTCHA_API_KEY`
- Already configured and working
- **DO NOT MODIFY** production secrets

## Naming Convention Standards

### Test Environment Pattern
```
TEST_[SERVICE]_[CREDENTIAL_TYPE]
```

Examples:
- `TEST_MONGODB_PASSWORD` (database auth)
- `TEST_MARICOPA_API_KEY` (API authentication)  
- `TEST_WEBSHARE_API_KEY` (proxy service)
- `TEST_CAPTCHA_API_KEY` (captcha solver)

### Fallback Pattern Support
The validation system supports fallback naming:
- Primary: `TEST_MARICOPA_API_KEY`
- Fallback: `TEST_MARICOPA_API`
- Primary: `TEST_WEBSHARE_API_KEY`
- Fallback: `TEST_WEBSHARE_API`

## Security Best Practices

### Secret Value Guidelines
- **Test secrets**: Use dedicated test/sandbox API keys when available
- **Never use production values**: Test secrets must be separate from production
- **Secure generation**: Generate strong passwords for database credentials
- **Documentation**: Document secret purpose and format requirements

### Access Control
- Test secrets: Default environment (no restrictions)
- Production secrets: Production environment only
- Service accounts: Minimal required permissions

### Secret Rotation
- Test secrets: Rotate when compromised or every 6 months
- Production secrets: Follow existing rotation schedule
- Update procedures: Coordinate with team to prevent service interruption

## Troubleshooting

### Common Issues

#### Issue 1: `validate-secrets` Job Fails
**Symptoms**: Workflow fails with "Missing required secrets" error
**Solution**: Ensure all four test secrets are configured exactly as specified above

#### Issue 2: API Authentication Errors
**Symptoms**: Integration tests fail with 401/403 errors
**Solution**: Verify test API keys are valid and not production keys

#### Issue 3: MongoDB Connection Failures  
**Symptoms**: Tests fail with MongoDB connection errors
**Solution**: Verify `TEST_MONGODB_PASSWORD` matches the expected test database password

### Verification Checklist

- [ ] `TEST_MONGODB_PASSWORD` configured in default environment
- [ ] `TEST_MARICOPA_API_KEY` configured with valid UUID format
- [ ] `TEST_WEBSHARE_API_KEY` configured with valid WebShare test key
- [ ] `TEST_CAPTCHA_API_KEY` configured with valid 2captcha test key
- [ ] All secrets in **default** environment (not production environment)
- [ ] Workflow `validate-secrets` job passes
- [ ] Integration tests can access configured services
- [ ] No production secrets exposed in test environment

## Workflow Integration

### Secret Usage in Workflows

The secrets are used across multiple workflow files:

1. **ci-cd.yml**: Primary CI/CD pipeline
   ```yaml
   env:
     TEST_MONGODB_URL: mongodb://admin:${{ secrets.TEST_MONGODB_PASSWORD }}@localhost:27017/
     TEST_MARICOPA_API_KEY: ${{ secrets.TEST_MARICOPA_API_KEY }}
     TEST_WEBSHARE_API_KEY: ${{ secrets.TEST_WEBSHARE_API_KEY }}
   ```

2. **validate-secrets.yml**: Reusable validation workflow
   ```yaml
   - Test environment secrets validation
   - Fallback pattern support
   - Format validation
   ```

3. **data-collection.yml**: Production data workflows
   ```yaml
   - Uses production secrets only
   - Environment separation enforced
   ```

## Post-Configuration Steps

### 1. Immediate Actions
- [ ] Configure all four missing test secrets
- [ ] Verify secret access with manual workflow run
- [ ] Monitor first automated workflow execution

### 2. Validation Testing
- [ ] Run full CI/CD pipeline
- [ ] Verify integration tests pass
- [ ] Check E2E test execution
- [ ] Validate data collection test workflows

### 3. Ongoing Monitoring
- [ ] Set up secret expiration reminders
- [ ] Document secret ownership and rotation schedule
- [ ] Monitor workflow success rates
- [ ] Plan regular security audits

## Contact Information

For questions about secret values or access issues:
- Repository Administrator: [TO BE FILLED IN]
- API Key Requests: [TO BE FILLED IN]  
- Emergency Access: [TO BE FILLED IN]

---

**⚠️ CRITICAL REMINDER**: Never commit actual secret values to version control. Always use the GitHub Secrets interface for sensitive credentials.