# ADR-004: Configuration Management Strategy

## Status
**ACCEPTED** - Implemented in Epic 1 Foundation Infrastructure

## Context
The Phoenix Real Estate Data Collection System requires a comprehensive configuration management strategy that supports multiple environments (development, testing, production), secure secret handling, and seamless integration across all four epics. The system must:

- Support environment-specific configurations (dev, test, prod)
- Securely manage sensitive data (API keys, database credentials, proxy settings)
- Provide compile-time validation of required configuration keys
- Enable easy configuration changes without code modifications
- Integrate with Epic 2's data collection parameters
- Support Epic 3's orchestration and deployment needs
- Allow Epic 4's quality monitoring configuration

Several configuration management approaches were considered:

### Option 1: Environment Variables Only
- All configuration through environment variables
- Simple and widely supported
- Difficult to manage complex nested configurations
- No built-in validation or type safety

### Option 2: Configuration Files + Environment Overrides
- YAML/JSON files for default values
- Environment variables override file settings
- Structured configuration with validation
- Clear separation of sensitive vs non-sensitive data

### Option 3: External Configuration Service
- Centralized configuration management (AWS Parameter Store, etc.)
- Advanced features like encryption and audit trails
- Additional cost and complexity
- Vendor lock-in concerns

## Decision
**We will implement Configuration Files + Environment Overrides** with a layered configuration system built into Epic 1's foundation.

### Architecture Decision
```
Environment Variables (highest priority)
    ↓
Environment-Specific Files (config/production.yaml)
    ↓  
Base Configuration (config/base.yaml)
    ↓
Default Values (in ConfigProvider code)
```

### Key Implementation
```python
# Epic 1: Foundation configuration system
class ConfigProvider:
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self._config = self._load_configuration()
    
    def _load_configuration(self) -> Dict[str, Any]:
        # Load base configuration
        config = self._load_yaml_file("config/base.yaml")
        
        # Override with environment-specific settings
        env_file = f"config/{self.environment.value}.yaml"
        if os.path.exists(env_file):
            env_config = self._load_yaml_file(env_file)
            config = self._deep_merge(config, env_config)
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        # Validate required keys
        self._validate_required_config(config)
        
        return config
    
    def get_required(self, key: str) -> Any:
        """Get required configuration value, raise error if missing"""
        if key not in self._config:
            raise ConfigurationError(f"Required configuration key missing: {key}")
        return self._config[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get optional configuration value with default"""
        return self._config.get(key, default)
```

## Consequences

### Positive Consequences
1. **Environment Flexibility**: Easy switching between dev/test/prod configurations
2. **Security**: Sensitive data managed through environment variables only
3. **Validation**: Compile-time validation of required configuration keys
4. **Maintainability**: Clear separation of configuration from code
5. **Type Safety**: Full type hints and validation for configuration values
6. **Testability**: Mock configurations for unit testing
7. **Documentation**: Self-documenting through configuration schema

### Negative Consequences
1. **Complexity**: More complex than simple environment variables
2. **File Management**: Multiple configuration files to maintain
3. **Merge Logic**: Complex deep-merge logic for configuration layers
4. **Debugging**: Configuration resolution can be complex to debug

### Configuration Structure
```yaml
# config/base.yaml - Default values and structure
database:
  connection_timeout_seconds: 30
  max_connections: 10
  retry_attempts: 3

logging:
  level: "INFO"
  format: "json"
  
collection:
  target_zip_codes: "85001,85002,85003"
  min_request_delay_seconds: 3.6
  max_concurrent_requests: 2

automation:
  daily_schedule: "0 10 * * *"  # 3 AM Phoenix time
  workflow_timeout_minutes: 120
  orchestration_mode: "sequential"

quality:
  monitoring_enabled: true
  alert_thresholds:
    error_rate: 0.05
    response_time_ms: 5000
```

```yaml
# config/production.yaml - Production overrides
logging:
  level: "WARNING"
  
collection:
  max_concurrent_requests: 1  # More conservative in production
  
automation:
  orchestration_mode: "sequential"  # Safer for production
```

### Environment Variable Mapping
```bash
# Sensitive data only in environment variables
export MONGODB_CONNECTION_STRING="mongodb+srv://user:pass@cluster.mongodb.net/db"
export MARICOPA_API_KEY="your-api-key-here"
export WEBSHARE_USERNAME="proxy-username"
export WEBSHARE_PASSWORD="proxy-password"

# Override any configuration value
export COLLECTION__TARGET_ZIP_CODES="85001,85002"  # __ means nested
export AUTOMATION__ORCHESTRATION_MODE="parallel"
export LOGGING__LEVEL="DEBUG"
```

## Impact on Each Epic

### Epic 1: Foundation Infrastructure
**Implementation Responsibility:**
- Define ConfigProvider interface and implementation
- Handle configuration file loading and environment variable overrides
- Provide validation and error handling for missing required keys
- Support type conversion and default value management

**Integration Pattern:**
```python
# Epic 1 provides configuration to all other epics
config = ConfigProvider(environment=Environment.PRODUCTION)
database_url = config.get_required("MONGODB_CONNECTION_STRING")
log_level = config.get("LOGGING__LEVEL", "INFO")
```

### Epic 2: Data Collection Engine
**Configuration Usage:**
- API endpoints and authentication keys
- Rate limiting and timing parameters
- Proxy configuration and rotation settings
- LLM model selection and processing parameters

**Integration Pattern:**
```python
class CollectionConfig:
    def __init__(self, config: ConfigProvider):
        self.config = config
    
    @property
    def maricopa_api_key(self) -> str:
        return self.config.get_required("MARICOPA_API_KEY")
    
    @property
    def target_zip_codes(self) -> List[str]:
        zip_codes_str = self.config.get_required("COLLECTION__TARGET_ZIP_CODES")
        return [z.strip() for z in zip_codes_str.split(",")]
```

### Epic 3: Automation & Orchestration
**Configuration Usage:**
- Workflow scheduling and execution parameters
- Orchestration strategy selection
- Deployment environment configuration
- Docker and GitHub Actions settings

**Integration Pattern:**
```python
class AutomationConfig:
    def __init__(self, config: ConfigProvider):
        self.config = config
    
    @property
    def orchestration_mode(self) -> OrchestrationMode:
        mode_str = self.config.get("AUTOMATION__ORCHESTRATION_MODE", "sequential")
        return OrchestrationMode(mode_str)
    
    @property
    def daily_schedule_time(self) -> str:
        return self.config.get("AUTOMATION__DAILY_SCHEDULE", "0 10 * * *")
```

### Epic 4: Quality Assurance
**Configuration Usage:**
- Monitoring thresholds and alert settings
- Test execution parameters
- Compliance validation rules
- Performance benchmarking configuration

**Integration Pattern:**
```python
class QualityConfig:
    def __init__(self, config: ConfigProvider):
        self.config = config
    
    @property
    def error_rate_threshold(self) -> float:
        return self.config.get("QUALITY__ALERT_THRESHOLDS__ERROR_RATE", 0.05)
    
    @property
    def monitoring_enabled(self) -> bool:
        return self.config.get("QUALITY__MONITORING_ENABLED", True)
```

## Security Considerations

### Sensitive Data Management
1. **Never in Files**: API keys, passwords, connection strings only in environment variables
2. **GitHub Secrets**: Production secrets managed through GitHub Actions secrets
3. **Local Development**: `.env` files for local development (git-ignored)
4. **Logging Security**: Configuration logging never includes sensitive values

### Configuration Validation
```python
class ConfigurationValidator:
    @staticmethod
    def validate_required_keys(config: Dict[str, Any]) -> None:
        required_keys = [
            "MONGODB_CONNECTION_STRING",
            "MARICOPA_API_KEY", 
            "COLLECTION__TARGET_ZIP_CODES"
        ]
        
        missing_keys = [key for key in required_keys if not config.get(key)]
        if missing_keys:
            raise ConfigurationError(f"Missing required configuration: {missing_keys}")
    
    @staticmethod
    def validate_format(config: Dict[str, Any]) -> None:
        # Validate ZIP code format
        zip_codes = config.get("COLLECTION__TARGET_ZIP_CODES", "")
        if not re.match(r"^(\d{5})(,\d{5})*$", zip_codes):
            raise ConfigurationError("Invalid ZIP code format")
```

## Environment-Specific Deployment

### Development Environment
```yaml
# config/development.yaml
logging:
  level: "DEBUG"
  format: "human"

collection:
  min_request_delay_seconds: 1.0  # Faster for development
  
database:
  connection_timeout_seconds: 10  # Shorter for quick feedback
```

### Testing Environment
```yaml
# config/testing.yaml
database:
  # Use test database
  database_name: "phoenix_real_estate_test"
  
collection:
  target_zip_codes: "85001"  # Single ZIP for testing
  
automation:
  workflow_timeout_minutes: 30  # Shorter for tests
```

### Production Environment
```yaml
# config/production.yaml
logging:
  level: "WARNING"
  format: "json"

collection:
  min_request_delay_seconds: 5.0  # More conservative
  max_concurrent_requests: 1
  
automation:
  orchestration_mode: "sequential"  # Safer approach
```

## Configuration Schema Documentation
```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class DatabaseConfig:
    connection_string: str  # From MONGODB_CONNECTION_STRING env var
    connection_timeout_seconds: int = 30
    max_connections: int = 10
    retry_attempts: int = 3

@dataclass
class CollectionConfig:
    target_zip_codes: List[str]  # From COLLECTION__TARGET_ZIP_CODES
    maricopa_api_key: str  # From MARICOPA_API_KEY env var
    min_request_delay_seconds: float = 3.6
    max_concurrent_requests: int = 2
    llm_model: str = "llama3.2:latest"

@dataclass
class SystemConfig:
    database: DatabaseConfig
    collection: CollectionConfig
    automation: AutomationConfig
    quality: QualityConfig
```

## Testing Strategy

### Configuration Testing
```python
class TestConfigurationManagement:
    def test_required_config_validation(self):
        # Test that missing required keys raise errors
        with pytest.raises(ConfigurationError):
            config = ConfigProvider()
            config.get_required("MISSING_KEY")
    
    def test_environment_overrides(self):
        # Test that environment variables override file values
        os.environ["TEST_KEY"] = "env_value"
        config = ConfigProvider()
        assert config.get("TEST_KEY") == "env_value"
    
    def test_nested_config_access(self):
        # Test nested configuration access
        config = ConfigProvider()
        value = config.get("COLLECTION__TARGET_ZIP_CODES")
        assert isinstance(value, str)
```

### Mock Configuration for Testing
```python
class MockConfigProvider(ConfigProvider):
    def __init__(self, test_config: Dict[str, Any]):
        self._config = test_config
    
    def get_required(self, key: str) -> Any:
        if key not in self._config:
            raise ConfigurationError(f"Test config missing key: {key}")
        return self._config[key]
```

## Migration and Deployment

### Configuration Deployment Process
1. **Development**: Use `config/development.yaml` + local `.env` file
2. **Testing**: Use `config/testing.yaml` + test environment variables
3. **Production**: Use `config/production.yaml` + GitHub Actions secrets

### Version Control Strategy
- Configuration files (YAML) are committed to repository
- Environment variable templates documented in README
- Sensitive data never committed to repository
- Configuration schema changes versioned with code

## Validation Criteria
- [ ] Configuration loading works in all environments (dev/test/prod)
- [ ] Required configuration keys are validated at startup
- [ ] Environment variables properly override file-based configuration
- [ ] Sensitive data is never logged or committed to repository
- [ ] All epics successfully integrate with ConfigProvider
- [ ] Configuration changes deploy without code changes
- [ ] Mock configurations enable comprehensive testing
- [ ] Configuration documentation is complete and accurate

## References
- Epic 1: Foundation Infrastructure specification
- Epic 2: Data Collection Engine configuration requirements
- Epic 3: Automation & Orchestration deployment needs
- Epic 4: Quality Assurance monitoring configuration
- Phoenix Real Estate system security requirements

---
**Author**: Integration Architect  
**Date**: 2025-01-20  
**Review**: Architecture Review Board, Security Team  
**Next Review**: After Epic 1 implementation completion