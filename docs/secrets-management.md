# Secrets Management Guide

## Overview

The Phoenix Real Estate system implements a comprehensive secrets management framework designed to protect sensitive configuration data including API keys, database credentials, and third-party service tokens. This document outlines security best practices, operational procedures, and compliance guidelines for managing secrets throughout the application lifecycle.

⚠️ **Security Notice**: Improper secret management is one of the most common causes of security breaches. Follow these guidelines carefully to maintain system security.

## Security Architecture

### Core Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Secrets accessible only when necessary
3. **Separation of Concerns**: Secrets isolated from application code
4. **Audit Trail**: All secret access logged and monitored
5. **Zero Trust**: Verify all secret access attempts

### Secret Categories

| Category | Examples | Storage Method | Rotation Frequency |
|----------|----------|----------------|-------------------|
| Critical | Database credentials, API master keys | Encrypted + HSM | 30 days |
| High | Third-party API keys, OAuth secrets | Encrypted | 90 days |
| Medium | Service tokens, webhook URLs | Base64 encoded | 180 days |
| Low | Feature flags, non-sensitive config | Plain text | As needed |

## Secret Storage Methods

### Environment Variables

**Best Practices:**
- Never commit `.env` files to version control
- Use `.env.example` for documentation only
- Implement strict file permissions (600)
- Separate environments completely

```bash
# File permissions check
chmod 600 .env
ls -la .env  # Should show -rw-------
```

### Automatic Secret Detection

The system automatically identifies secrets based on naming conventions:

```python
# Automatically detected as secrets
SECRET_API_KEY = "..."       # SECRET_ prefix
SECURE_TOKEN = "..."         # SECURE_ prefix  
CREDENTIAL_PASSWORD = "..."  # CREDENTIAL_ prefix
DATABASE_PASSWORD = "..."    # _PASSWORD suffix
MONGODB_URI = "..."         # _URI suffix
API_KEY = "..."             # _KEY suffix
AUTH_TOKEN = "..."          # _TOKEN suffix
```

⚠️ **Warning**: These patterns trigger automatic security handling. Use them intentionally.

### Base64 Encoding

For non-critical secrets requiring obfuscation:

```python
# Automatic decoding with b64: prefix
WEBHOOK_URL = "b64:aHR0cHM6Ly9hcGkuZXhhbXBsZS5jb20vd2ViaG9vaw=="

# Manual encoding for storage
import base64
encoded = base64.b64encode(secret.encode()).decode()
stored_value = f"b64:{encoded}"
```

⚠️ **Security Note**: Base64 is NOT encryption. Use only for obfuscation, not security.

### Encryption Features

For high-security environments:

```python
# config/secrets.py
encryption_config = {
    "enabled": True,
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2",
    "iterations": 100000,
    "key_storage": "HSM"  # Hardware Security Module
}
```

## Secret Rotation Procedures

### Zero-Downtime Rotation

1. **Preparation Phase**
   ```bash
   # Generate new secret
   NEW_SECRET=$(openssl rand -base64 32)
   
   # Test new secret in staging
   export API_KEY_NEW=$NEW_SECRET
   ```

2. **Dual-Key Phase**
   ```python
   # Application supports both keys temporarily
   api_keys = [
       os.getenv("API_KEY"),      # Current
       os.getenv("API_KEY_NEW")   # New
   ]
   ```

3. **Migration Phase**
   ```bash
   # Update all services to use new key
   # Monitor for errors
   # Verify all systems functioning
   ```

4. **Cleanup Phase**
   ```bash
   # Remove old key after verification
   unset API_KEY
   export API_KEY=$API_KEY_NEW
   ```

### Automated Rotation

```yaml
# .github/workflows/rotate-secrets.yml
name: Rotate Secrets
on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly
  workflow_dispatch:     # Manual trigger

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - name: Rotate Database Password
        run: |
          # Rotation script with rollback capability
          ./scripts/rotate-secret.sh DATABASE_PASSWORD
```

## Audit Logging and Monitoring

### Access Logging

```python
# Every secret access is logged
logger.info(
    "Secret accessed",
    extra={
        "secret_name": "API_KEY",
        "accessed_by": user_id,
        "timestamp": datetime.utcnow(),
        "ip_address": request.remote_addr,
        "purpose": "API request to third-party service"
    }
)
```

### Monitoring Alerts

Configure alerts for:
- Unusual access patterns
- Failed authentication attempts
- Secret access from new IP addresses
- Bulk secret retrieval
- Access outside business hours

### Audit Trail Requirements

```python
# Audit log structure
{
    "event_type": "secret_access",
    "secret_id": "hash_of_secret_name",
    "user": "system_or_user_id",
    "timestamp": "2025-01-20T10:00:00Z",
    "ip_address": "192.168.1.1",
    "user_agent": "application/1.0",
    "result": "success|failure",
    "metadata": {
        "purpose": "scheduled_task",
        "service": "data_collector"
    }
}
```

## Compliance Guidelines

### PCI DSS Requirements

For systems handling payment card data:
- Encrypt all stored secrets (Requirement 3.4)
- Implement key management procedures (Requirement 3.5)
- Restrict access by business need-to-know (Requirement 7)
- Track and monitor all access (Requirement 10)

### GDPR Considerations

For systems processing personal data:
- Document all secrets that access personal data
- Implement data minimization for secret scope
- Ensure right to erasure includes secret rotation
- Maintain processing records for audit

### SOC 2 Controls

- **CC6.1**: Logical and physical access controls
- **CC6.7**: Restrict access to secrets
- **CC7.2**: Monitor system components
- **CC7.3**: Evaluate security events

## Common Security Pitfalls

### ❌ Never Do This

```python
# NEVER hardcode secrets
API_KEY = "sk-1234567890abcdef"  # WRONG!

# NEVER log secrets
logger.info(f"Using API key: {api_key}")  # WRONG!

# NEVER commit secrets
git add .env  # WRONG!

# NEVER share secrets in plain text
email.send("Here's the password: " + password)  # WRONG!

# NEVER use weak encryption
encoded = base64.b64encode(secret)  # NOT SECURE!
```

### ✅ Always Do This

```python
# Load from environment
api_key = os.getenv("API_KEY")

# Mask in logs
logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:]}")

# Use gitignore
echo ".env" >> .gitignore

# Share via secure channels
# Use password managers, encrypted email, or secure vaults

# Use proper encryption
from cryptography.fernet import Fernet
encrypted = fernet.encrypt(secret.encode())
```

## Emergency Procedures

### Secret Compromise Response

1. **Immediate Actions** (0-15 minutes)
   ```bash
   # Revoke compromised secret
   ./scripts/emergency-revoke.sh SECRET_NAME
   
   # Generate new secret
   ./scripts/generate-secret.sh SECRET_NAME
   
   # Deploy new secret to production
   ./scripts/deploy-secret.sh SECRET_NAME --emergency
   ```

2. **Investigation** (15-60 minutes)
   - Review audit logs for unauthorized access
   - Identify scope of potential exposure
   - Check for data exfiltration
   - Document timeline of events

3. **Remediation** (1-24 hours)
   - Rotate all related secrets
   - Update security monitoring rules
   - Patch any vulnerabilities
   - Notify affected parties if required

### Disaster Recovery

```bash
# Backup secret recovery
./scripts/recover-secrets.sh --from-backup --date 2025-01-19

# Verify all secrets functional
./scripts/verify-secrets.sh --comprehensive

# Generate recovery report
./scripts/generate-recovery-report.sh
```

## Secret Management Checklist

### Development
- [ ] No secrets in source code
- [ ] .env file not in version control
- [ ] .env.example documents all required secrets
- [ ] Local development uses separate secrets
- [ ] Secret access logged during development

### Deployment
- [ ] Production secrets stored securely
- [ ] Secrets injected at runtime only
- [ ] No secrets in container images
- [ ] Deployment logs sanitized
- [ ] Secret rotation tested

### Operations
- [ ] Regular rotation schedule configured
- [ ] Monitoring alerts configured
- [ ] Audit logs reviewed regularly
- [ ] Emergency procedures documented
- [ ] Team trained on procedures

## Testing Secret Management

```python
# tests/test_secrets.py
def test_secret_masking():
    """Ensure secrets are masked in logs"""
    secret = "sk-1234567890abcdef"
    masked = mask_secret(secret)
    assert masked == "sk-12...cdef"
    assert len(masked) < len(secret)

def test_secret_rotation():
    """Test zero-downtime rotation"""
    old_secret = "old-secret-value"
    new_secret = "new-secret-value"
    
    # Should accept both during rotation
    assert authenticate(old_secret) == True
    assert authenticate(new_secret) == True
    
    # After rotation complete
    complete_rotation()
    assert authenticate(old_secret) == False
    assert authenticate(new_secret) == True

def test_audit_logging():
    """Verify audit trail creation"""
    access_secret("TEST_SECRET")
    
    logs = get_audit_logs()
    assert logs[-1]["event_type"] == "secret_access"
    assert logs[-1]["secret_id"] == hash("TEST_SECRET")
```

## Additional Resources

- [OWASP Secret Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NIST Key Management Guidelines](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)
- [Cloud Provider Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)

---

⚠️ **Remember**: Security is not a feature, it's a requirement. Treat every secret as if a breach would end your business - because it might.