# 🚨 SECRET MANAGEMENT - QUICK START GUIDE

**CRITICAL**: This guide provides immediate secret management procedures for the Phoenix Real Estate system. For production outages or urgent issues, follow emergency procedures first.

## 🚀 QUICK START (5-10 Minutes)

### Emergency Status Check
- **Production Issues**: See [Emergency Procedures](#emergency-procedures) below
- **CI/CD Failing**: See [GitHub Actions Setup](#github-actions-secret-setup)
- **New Setup**: Continue with [Required Secrets](#required-secrets)

### Required Secrets

**Production Environment (GitHub → Settings → Secrets → Production):**
- `MONGODB_URL` - MongoDB Atlas connection string
- `MARICOPA_API_KEY` - Maricopa County Assessor API key (UUID format)
- `WEBSHARE_API_KEY` - Proxy service for Phoenix MLS (32+ chars)
- `CAPTCHA_API_KEY` - 2captcha service for CAPTCHA solving (32+ chars)

**Test Environment (GitHub → Settings → Secrets → Default):**
- `TEST_MONGODB_PASSWORD` - CI/CD test database password
- `TEST_MARICOPA_API_KEY` - Test API key (UUID format)
- `TEST_WEBSHARE_API_KEY` - Test proxy service key
- `TEST_CAPTCHA_API_KEY` - Test CAPTCHA service key

## ⚡ GitHub Actions Secret Setup

### 1. Access Repository Secrets
1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Select **Production** environment for production secrets
4. Select **Default** for test secrets

### 2. Configure Critical Secrets
```yaml
Production Environment:
  MONGODB_URL: "mongodb+srv://username:password@cluster.mongodb.net/phoenix_real_estate"
  MARICOPA_API_KEY: "12345678-90ab-cdef-1234-567890abcdef"
  WEBSHARE_API_KEY: "abcdef1234567890abcdef1234567890"
  CAPTCHA_API_KEY: "fedcba0987654321fedcba0987654321"

Default Environment:
  TEST_MONGODB_PASSWORD: "test_mongodb_secure_password_123"
  TEST_MARICOPA_API_KEY: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
  TEST_WEBSHARE_API_KEY: "test_webshare_key_1234567890"
  TEST_CAPTCHA_API_KEY: "test_captcha_key_0987654321"
```

### 3. Validation
1. Go to **Actions** tab → **Run workflow** → **"Validate Secrets"**
2. Expected: ✅ All validation checks pass
3. If failing: Check secret names match exactly (case-sensitive)

## 🚨 Emergency Procedures

### Production Outage Response
**Symptoms**: CI/CD failing, data collection stopped, authentication errors

**Immediate Actions (0-15 minutes):**
1. Check GitHub Actions tab for red X marks
2. Look for "secret not found" or "authentication failed" errors
3. Verify all 8 required secrets are configured
4. Run "Validate Secrets" workflow manually
5. Check secret values aren't placeholder text

**If Secrets Missing/Invalid:**
```bash
# Check secret format requirements
MongoDB URL: mongodb+srv://username:password@host/database
Maricopa API Key: UUID format (36 characters with hyphens)
WebShare API Key: Alphanumeric (32+ characters)
Captcha API Key: Alphanumeric (32+ characters)
```

### Secret Compromise Response
**If API keys are exposed or compromised:**

1. **Immediate (0-15 min):**
   - Revoke compromised keys at provider dashboards
   - Generate new keys with same format requirements
   - Update GitHub secrets with new values
   - Test with "Validate Secrets" workflow

2. **Follow-up (15-60 min):**
   - Monitor audit logs for unauthorized access
   - Check for data exfiltration
   - Document timeline of events
   - Rotate related secrets if needed

## 🛡️ Security Best Practices

### Core Security Rules
- ❌ **NEVER** commit secrets to code
- ❌ **NEVER** log secret values
- ❌ **NEVER** use production secrets in test environment
- ✅ **ALWAYS** use environment-specific secrets
- ✅ **ALWAYS** verify secret formats before saving
- ✅ **ALWAYS** rotate secrets every 90 days

### Secret Formats & Validation
```python
# Automatic secret detection patterns
SECRET_*        # SECRET_ prefix
SECURE_*        # SECURE_ prefix
*_PASSWORD      # _PASSWORD suffix
*_KEY           # _KEY suffix
*_TOKEN         # _TOKEN suffix
*_URI / *_URL   # _URI or _URL suffix
```

### Environment Separation
- **Production**: Critical secrets, production environment only
- **Test**: Sandbox credentials, default environment only
- **Development**: Local .env files (never committed)

## 🔄 Secret Rotation Schedule

### Rotation Frequencies
- **Critical** (Database, API keys): 30 days
- **High** (Third-party services): 90 days
- **Medium** (Service tokens): 180 days

### Zero-Downtime Rotation Process
1. **Generate new secret** at provider
2. **Stage new secret** in GitHub (temporary dual-key support)
3. **Test in staging** environment
4. **Deploy to production** and monitor
5. **Remove old secret** after verification

## 📚 Detailed Documentation

For comprehensive information, see:

- **[docs/deployment/SECRET_MANAGEMENT.md](docs/deployment/SECRET_MANAGEMENT.md)** - Complete setup and troubleshooting guide
- **[docs/secrets-management.md](docs/secrets-management.md)** - Security architecture and best practices
- **[docs/security/URGENT_SECRET_UPDATE_REQUIRED.md](docs/security/URGENT_SECRET_UPDATE_REQUIRED.md)** - Legacy secret migration guide

## 🔧 Validation Scripts

```bash
# Validate secret configuration
python scripts/validation/validate_secrets.py --comprehensive

# Test API connectivity  
python scripts/testing/api_credential_setup.py --test-all

# Check MongoDB connection
python scripts/testing/test_mongodb_connection.py

# Full system health check
python scripts/validation/validate_environment.py
```

## 📞 Emergency Contacts

### Missing Secret Values
- **MongoDB Atlas**: MongoDB Atlas dashboard → Database Access
- **Maricopa API**: https://mcassessor.maricopa.gov/api 
- **WebShare**: https://webshare.io account dashboard
- **2captcha**: https://2captcha.com account dashboard

### Critical Escalation
1. Check password managers for stored credentials
2. Contact API providers for account recovery  
3. Review backup documentation in secure storage
4. Contact team lead for emergency credential access

## ✅ Success Checklist

### Configuration Complete
- [ ] All 8 secrets configured with correct names
- [ ] Production secrets in "Production" environment
- [ ] Test secrets in "Default" environment
- [ ] No placeholder values (test-key, etc.)
- [ ] Secret formats validated

### System Operational
- [ ] "Validate Secrets" workflow passes
- [ ] CI/CD pipeline completes successfully
- [ ] Data collection workflows functional
- [ ] Integration tests authenticate successfully
- [ ] No secret-related errors in logs

---

**⚠️ REMEMBER**: This is a quick-start guide for urgent situations. Always refer to detailed documentation for comprehensive procedures and security requirements.

**🔄 NEXT STEPS**: After resolving immediate issues, implement regular secret rotation schedule and monitoring alerts.