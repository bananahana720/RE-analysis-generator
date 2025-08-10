# Task 03: Configuration Management - Testing Strategy & Quality Gates

## Testing Philosophy

The configuration management system is critical infrastructure that affects all other components. Our testing strategy emphasizes:
- **Comprehensive Coverage**: >90% code coverage with focus on critical paths
- **Environment Isolation**: Each environment tested independently
- **Security First**: Dedicated security testing for secret management
- **Performance Validation**: Sub-100ms initialization requirement
- **Backward Compatibility**: Ensuring existing code continues to work

## Test Categories

### 1. Unit Tests (Story Coverage: 1, 3, 4)

#### Base Configuration Tests
```python
# tests/foundation/config/test_base_enhanced.py
class TestEnvironmentVariableLoading:
    """Test dual support for environment variables."""
    
    def test_phoenix_prefix_variables(self):
        """Test PHOENIX_ prefixed variables work."""
        # Set: PHOENIX_DATABASE_URI
        # Verify: Accessible via config.get("database.uri")
    
    def test_direct_environment_variables(self):
        """Test direct PRD-specified variables."""
        # Set: MONGODB_URI, LOG_LEVEL, etc.
        # Verify: Properly mapped to config keys
    
    def test_precedence_order(self):
        """Test env vars override config files."""
        # Set both env var and config file value
        # Verify env var takes precedence

class TestValidationMethods:
    """Test new list-based validation."""
    
    def test_validation_returns_list(self):
        """Test validate() returns List[str]."""
        # Create config with errors
        # Verify list of error messages returned
    
    def test_environment_specific_validation(self):
        """Test production requires more fields."""
        # Test development vs production validation
        # Verify different requirements enforced
```

#### Factory Pattern Tests
```python
# tests/foundation/config/test_environment.py
class TestEnvironmentFactory:
    """Test factory pattern implementation."""
    
    def test_create_development_config(self):
        """Test development config creation."""
        # Create via factory
        # Verify correct environment and settings
    
    def test_auto_environment_detection(self):
        """Test ENVIRONMENT variable detection."""
        # Set ENVIRONMENT=testing
        # Verify correct config created
    
    def test_singleton_pattern(self):
        """Test same instance returned."""
        # Call get_config() multiple times
        # Verify same object reference

class TestConfigurationValidator:
    """Test validation across environments."""
    
    def test_validate_all_environments(self):
        """Test all environments validate."""
        # Run validator on all environments
        # Check for configuration issues
```

#### Secret Management Tests
```python
# tests/foundation/config/test_secrets.py
class TestSecretManager:
    """Test secure secret handling."""
    
    def test_secret_loading_with_prefixes(self):
        """Test various prefix patterns."""
        # Test SECRET_, SECURE_, CREDENTIAL_ prefixes
        # Verify correct loading
    
    def test_base64_encryption(self):
        """Test encoding/decoding."""
        # Test b64: prefix handling
        # Verify round-trip encoding
    
    def test_no_plaintext_logging(self):
        """Test secrets not logged."""
        # Load secret and trigger logging
        # Verify secret value not in logs
    
    def test_required_secret_validation(self):
        """Test missing secrets caught."""
        # Remove required secret
        # Verify ConfigurationError raised
```

### 2. Integration Tests (Story Coverage: 5, 6)

#### Multi-Module Integration
```python
# tests/integration/test_config_integration.py
class TestConfigurationIntegration:
    """Test modules work together."""
    
    def test_factory_with_base_provider(self):
        """Test factory uses enhanced provider."""
        # Create config via factory
        # Verify dual env var support works
    
    def test_secret_manager_integration(self):
        """Test secrets integrate with config."""
        # Load config with secrets
        # Verify proper integration
    
    def test_environment_switching(self):
        """Test switching between environments."""
        # Load dev, test, prod configs
        # Verify proper isolation
```

#### End-to-End Configuration Loading
```python
class TestEndToEndConfiguration:
    """Test complete configuration flow."""
    
    def test_development_configuration_load(self):
        """Test full dev config loading."""
        # Set up dev environment
        # Load configuration
        # Verify all settings correct
    
    def test_production_configuration_load(self):
        """Test production config with secrets."""
        # Set up production env vars
        # Load configuration
        # Verify security settings
```

### 3. Security Tests (Story Coverage: 4, 6)

#### Secret Protection Tests
```python
# tests/security/test_config_security.py
class TestSecretSecurity:
    """Test secret protection measures."""
    
    def test_secrets_not_in_exceptions(self):
        """Test secrets not exposed in errors."""
        # Trigger various exceptions
        # Verify no secret values in messages
    
    def test_secrets_not_in_string_repr(self):
        """Test __str__ and __repr__ safe."""
        # Get string representation of config
        # Verify no secrets exposed
    
    def test_log_sanitization(self):
        """Test logging doesn't expose secrets."""
        # Enable debug logging
        # Load secrets
        # Verify logs sanitized
```

### 4. Performance Tests (Story Coverage: 6)

#### Load Time Benchmarks
```python
# tests/performance/test_config_performance.py
class TestConfigurationPerformance:
    """Test performance requirements."""
    
    def test_initialization_speed(self):
        """Test <100ms initialization."""
        # Time configuration loading
        # Verify under 100ms
    
    def test_validation_speed(self):
        """Test <50ms validation."""
        # Time full validation
        # Verify under 50ms
    
    def test_memory_usage(self):
        """Test <10MB memory usage."""
        # Load full configuration
        # Measure memory footprint
```

### 5. Environment-Specific Tests

#### Development Environment
```python
# tests/environments/test_development.py
class TestDevelopmentEnvironment:
    """Test development-specific behavior."""
    
    def test_debug_logging_enabled(self):
        """Test DEBUG level in development."""
    
    def test_relaxed_validation(self):
        """Test less strict validation."""
    
    def test_local_database_config(self):
        """Test local MongoDB settings."""
```

#### Testing Environment
```python
# tests/environments/test_testing.py
class TestTestingEnvironment:
    """Test testing-specific behavior."""
    
    def test_external_services_disabled(self):
        """Test no external API calls."""
    
    def test_mock_llm_configured(self):
        """Test mock LLM for tests."""
    
    def test_strict_validation(self):
        """Test strict validation enabled."""
```

#### Production Environment
```python
# tests/environments/test_production.py
class TestProductionEnvironment:
    """Test production-specific behavior."""
    
    def test_security_requirements(self):
        """Test all security settings required."""
    
    def test_json_logging_format(self):
        """Test structured logging enabled."""
    
    def test_performance_settings(self):
        """Test optimized settings."""
```

## Quality Gates

### Gate 1: Pre-Commit (Local Development)
```yaml
checks:
  - name: "Unit Tests"
    command: "uv run pytest tests/foundation/config/"
    threshold: "100% pass"
    
  - name: "Type Checking"
    command: "uv run mypy src/phoenix_real_estate/foundation/config/"
    threshold: "No errors"
    
  - name: "Linting"
    command: "uv run ruff check src/phoenix_real_estate/foundation/config/"
    threshold: "No violations"
    
  - name: "Security Scan"
    command: "grep -r 'password\\|secret\\|key' --include='*.py'"
    threshold: "No hardcoded secrets"
```

### Gate 2: Pull Request (CI Pipeline)
```yaml
checks:
  - name: "Full Test Suite"
    command: "uv run pytest tests/ -v"
    threshold: "100% pass"
    
  - name: "Code Coverage"
    command: "uv run pytest --cov=phoenix_real_estate.foundation.config --cov-report=term-missing"
    threshold: ">90% coverage"
    
  - name: "Integration Tests"
    command: "uv run pytest tests/integration/ -v"
    threshold: "100% pass"
    
  - name: "Performance Tests"
    command: "uv run pytest tests/performance/ -v"
    threshold: "All benchmarks pass"
```

### Gate 3: Pre-Deployment
```yaml
checks:
  - name: "Environment Validation"
    command: "python -m phoenix_real_estate.foundation.config.environment validate"
    threshold: "All environments valid"
    
  - name: "Security Audit"
    command: "uv run bandit -r src/phoenix_real_estate/foundation/config/"
    threshold: "No high severity issues"
    
  - name: "Dependency Check"
    command: "uv pip check"
    threshold: "No conflicts"
```

### Gate 4: Post-Deployment
```yaml
checks:
  - name: "Configuration Load Test"
    command: "python -c 'from phoenix_real_estate.foundation.config import get_config; get_config()'"
    threshold: "Loads without error"
    
  - name: "Health Check"
    command: "curl http://localhost:8000/health"
    threshold: "200 OK"
    
  - name: "Secret Validation"
    command: "python -m phoenix_real_estate.foundation.config.secrets validate"
    threshold: "All required secrets present"
```

## Test Data Management

### Configuration Test Files
```
tests/fixtures/config/
├── valid/
│   ├── base.yaml
│   ├── development.yaml
│   ├── testing.yaml
│   └── production.yaml
├── invalid/
│   ├── malformed.yaml
│   ├── missing_required.yaml
│   └── type_errors.yaml
└── edge_cases/
    ├── empty.yaml
    ├── deeply_nested.yaml
    └── large_config.yaml
```

### Environment Variable Sets
```python
# tests/fixtures/envvars.py
DEVELOPMENT_ENV = {
    "ENVIRONMENT": "development",
    "MONGODB_URI": "mongodb://localhost:27017/test",
    "LOG_LEVEL": "DEBUG",
}

PRODUCTION_ENV = {
    "ENVIRONMENT": "production",
    "MONGODB_URI": "mongodb+srv://...",
    "SECRET_KEY": "production-secret",
    "WEBSHARE_USERNAME": "prod-user",
    "WEBSHARE_PASSWORD": "prod-pass",
}
```

## Test Execution Strategy

### Local Development Testing
```bash
# Quick unit tests during development
uv run pytest tests/foundation/config/test_base.py -v

# Full module tests before commit
uv run pytest tests/foundation/config/ -v --cov

# Integration tests
uv run pytest tests/integration/test_config_integration.py
```

### CI/CD Pipeline Testing
```yaml
# .github/workflows/test-config.yml
name: Configuration Tests
on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        environment: [development, testing, production]
    steps:
      - name: Run tests
        env:
          ENVIRONMENT: ${{ matrix.environment }}
        run: |
          uv run pytest tests/ -v
          uv run pytest --cov
```

### Performance Testing
```python
# Continuous performance monitoring
import time
import statistics

def benchmark_config_load(iterations=100):
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        config = get_config()
        end = time.perf_counter()
        times.append(end - start)
    
    print(f"Mean: {statistics.mean(times)*1000:.2f}ms")
    print(f"P95: {statistics.quantiles(times, n=20)[18]*1000:.2f}ms")
    assert statistics.mean(times) < 0.1  # <100ms requirement
```

## Continuous Improvement

### Metrics to Track
1. **Test Execution Time**: Keep under 5 minutes for full suite
2. **Code Coverage**: Maintain >90% on new code
3. **Defect Escape Rate**: Track bugs found post-deployment
4. **Performance Regression**: Monitor config load times

### Test Maintenance
1. **Weekly**: Review and update test data
2. **Monthly**: Audit test coverage gaps
3. **Quarterly**: Performance baseline updates
4. **Annually**: Security test scenario review

## Success Criteria

### Immediate Success (Day 1)
- [ ] All unit tests passing
- [ ] >90% code coverage achieved
- [ ] No security vulnerabilities
- [ ] Performance requirements met

### Short-term Success (Week 1)
- [ ] Zero configuration-related bugs
- [ ] Smooth deployment to all environments
- [ ] Positive developer feedback
- [ ] Documentation complete

### Long-term Success (Month 1)
- [ ] No configuration-related incidents
- [ ] Easy onboarding for new developers
- [ ] Extensible for new requirements
- [ ] Performance maintained under load

## Risk Mitigation Through Testing

| Risk | Test Mitigation |
|------|-----------------|
| Secret exposure | Security tests, log scanning |
| Performance degradation | Benchmark tests, continuous monitoring |
| Breaking changes | Backward compatibility tests |
| Environment conflicts | Environment-specific test suites |
| Integration failures | Cross-module integration tests |

This comprehensive testing strategy ensures the configuration management system is robust, secure, and performant across all environments.