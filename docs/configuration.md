# Configuration Management Guide

## Overview

The Phoenix Real Estate Collector uses a comprehensive configuration management system that supports multiple environments, secure credential handling, and flexible configuration sources. This system is built on the Epic 1 foundation layer and provides type-safe configuration access with comprehensive validation.

### Key Features

- **Hierarchical Configuration**: Base → Environment-specific → Environment variables
- **Type-Safe Access**: Built-in type conversion and validation
- **Secret Management**: Secure handling of sensitive values with encryption support
- **Environment Detection**: Automatic environment selection with manual override
- **Validation Framework**: Comprehensive validation with clear error reporting
- **Dot Notation**: Nested configuration access (e.g., `database.host`)

## Quick Start

### Basic Usage

```python
from phoenix_real_estate.foundation.config import get_config

# Get configuration instance
config = get_config()

# Access configuration values
db_uri = config.get_required("database.uri")
log_level = config.get("logging.level", default="INFO")
max_workers = config.get_typed("processing.max_workers", int, default=2)

# Check environment
if config.is_development():
    print("Running in development mode")
```

### Environment Setup

1. Copy `.env.sample` to `.env`:
   ```bash
   cp .env.sample .env
   ```

2. Set the environment:
   ```bash
   export ENVIRONMENT=development  # or production, staging
   ```

3. Configure required values in `.env` or environment variables

## Configuration Hierarchy

Configuration sources are loaded in the following order (later sources override earlier ones):

1. **Base Configuration** (`config/base.yaml`)
   - Default values for all environments
   - Common settings across deployments

2. **Environment-Specific Configuration** (`config/{environment}.yaml`)
   - Environment-specific overrides
   - Examples: `development.yaml`, `production.yaml`, `staging.yaml`

3. **Environment Files** (`.env` files)
   - `.env` - Base environment file
   - `.env.local` - Local overrides (development only)
   - `.env.{environment}` - Environment-specific overrides

4. **Environment Variables**
   - Direct environment variables
   - `PHOENIX_` prefixed variables (highest priority)

### Precedence Example

```yaml
# config/base.yaml
database:
  port: 27017
  name: "phoenix_real_estate"

# config/production.yaml
database:
  name: "phoenix_real_estate_prod"

# Environment variable
export PHOENIX_DATABASE_PORT=27018

# Result: port=27018, name="phoenix_real_estate_prod"
```

## Environment Variables Reference

### Database Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `MONGODB_URI` | MongoDB connection URI | `mongodb://localhost:27017` | Yes* |
| `MONGODB_DATABASE` | Database name | `phoenix_real_estate` | Yes* |
| `MONGODB_MAX_POOL_SIZE` | Connection pool size | `10` | No |
| `DATABASE_HOST` | Database host (if not using URI) | `localhost` | No |
| `DATABASE_PORT` | Database port | `27017` | No |
| `DATABASE_USERNAME` | Database username | `dbuser` | No |
| `DATABASE_PASSWORD` | Database password | `secure_password` | No |

*Either `MONGODB_URI` or `DATABASE_HOST` + `DATABASE_NAME` must be provided

### Logging Configuration

| Variable | Description | Example | Default |
|----------|-------------|---------|-------|
| `LOG_LEVEL` | Logging level | `INFO`, `DEBUG`, `WARNING` | `INFO` |
| `LOG_FORMAT` | Log format | `text`, `json` | `text` |
| `LOGGING_FILE_PATH` | Log file path | `/var/log/app.log` | None |
| `LOGGING_MAX_BYTES` | Max log file size | `10485760` | 10MB |
| `LOGGING_BACKUP_COUNT` | Number of backup files | `5` | 5 |

### Collection Configuration

| Variable | Description | Example | Default |
|----------|-------------|---------|-------|
| `MAX_REQUESTS_PER_HOUR` | Rate limit | `100` | 100 |
| `MIN_REQUEST_DELAY` | Delay between requests (seconds) | `3.6` | 3.6 |
| `TARGET_ZIP_CODES` | Comma-separated ZIP codes | `85031,85033,85035` | See base.yaml |
| `COLLECTION_BATCH_SIZE` | Batch processing size | `10` | 10 |
| `COLLECTION_MAX_WORKERS` | Max concurrent workers | `4` | 4 |

### Proxy Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `PROXY_ENABLED` | Enable proxy usage | `true`, `false` | No |
| `WEBSHARE_USERNAME` | Proxy username | `proxy_user` | If enabled |
| `WEBSHARE_PASSWORD` | Proxy password | `proxy_pass` | If enabled |
| `PROXY_URL` | Proxy URL | `http://proxy.example.com:8080` | If enabled |

### Processing Configuration

| Variable | Description | Example | Default |
|----------|-------------|---------|-------|
| `LLM_MODEL` | LLM model name | `llama3.2:latest` | `llama3.2:latest` |
| `LLM_TIMEOUT` | LLM timeout (seconds) | `30` | 30 |
| `PROCESSING_MAX_WORKERS` | Max processing workers | `2` | 2 |

### Security Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Application secret key | 32+ character string | Production |
| `SECRET_JWT_SECRET_KEY` | JWT signing key | 32+ character string | If using JWT |
| `SECRET_ENCRYPTION_KEY` | Encryption key | 32+ character string | If encrypting |

### API Keys (Secrets)

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_API_KEY_GOOGLE` | Google API key | `AIza...` |
| `SECRET_API_KEY_AZURE` | Azure API key | `key...` |
| `SECRET_API_KEY_OPENAI` | OpenAI API key | `sk-...` |
| `SECRET_MARICOPA_API_KEY` | Maricopa County API key | `api_key_here` |

### Phoenix-Prefixed Variables

All configuration values can be set using `PHOENIX_` prefixed environment variables. These take the highest precedence:

```bash
# Maps to database.host
export PHOENIX_DATABASE_HOST=localhost

# Maps to logging.level
export PHOENIX_LOGGING_LEVEL=DEBUG

# Maps to collection.target_zipcodes (note the 'S')
export PHOENIX_COLLECTION_TARGET_ZIPCODES="85031,85033,85035"

# Nested values use underscores
export PHOENIX_DATABASE_CONNECTION_POOL_SIZE=20
```

## Configuration Access Patterns

### Basic Access

```python
config = get_config()

# Get with default
value = config.get("key.path", default="default_value")

# Get required (raises ConfigurationError if missing)
value = config.get_required("key.path")

# Get with type conversion
port = config.get_typed("database.port", int, default=27017)
enabled = config.get_typed("features.cache_enabled", bool, default=True)
zip_codes = config.get_typed("collection.target_zipcodes", list, default=[])
```

### Helper Methods

```python
# Get complete database configuration
db_config = config.get_database_config()
# Returns: {
#   'uri': 'mongodb://...',
#   'name': 'phoenix_real_estate',
#   'pool_size': 10,
#   ...
# }

# Get logging configuration
log_config = config.get_logging_config()
# Returns: {
#   'level': 'INFO',
#   'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#   'file_path': '/var/log/app.log',
#   ...
# }

# Get collection configuration
collection_config = config.get_collection_config()
# Returns: {
#   'target_zipcodes': ['85031', '85033', '85035'],
#   'schedule': '0 0 * * *',
#   'batch_size': 10,
#   ...
# }
```

### Environment Checks

```python
config = get_config()

if config.is_development():
    # Development-specific logic
    pass

if config.is_testing():
    # Testing-specific logic
    pass

if config.is_production():
    # Production-specific logic
    pass

# Get current environment name
env = config.get_environment()  # "development", "staging", "production"
```

## Type Conversion

The configuration system automatically converts string values to the requested type:

### Boolean Conversion

True values: `true`, `yes`, `y`, `1`, `on`, `enabled`, `enable`, `active`
False values: `false`, `no`, `n`, `0`, `off`, `disabled`, `disable`, `inactive`, `""`

```python
# All of these return True
config.get_typed("debug", bool)  # When DEBUG=true
config.get_typed("debug", bool)  # When DEBUG=yes
config.get_typed("debug", bool)  # When DEBUG=1
```

### List Conversion

Lists can use comma or semicolon separators:

```python
# TARGET_ZIP_CODES="85031,85033,85035"
zip_codes = config.get_typed("collection.target_zipcodes", list)
# Returns: ['85031', '85033', '85035']

# Mixed separators (semicolon takes precedence)
# ITEMS="item1,item2;item3,item4"
items = config.get_typed("items", list)
# Returns: ['item1,item2', 'item3,item4']
```

### Numeric Conversion

```python
# Safe conversion with validation
port = config.get_typed("database.port", int)  # PORT="27017"
timeout = config.get_typed("api.timeout", float)  # TIMEOUT="30.5"
```

## Validation

### Automatic Validation

The configuration system performs automatic validation including:

- Required keys presence
- Type constraints
- Format validation (ZIP codes, URIs, etc.)
- Range validation for numeric values
- Environment-specific requirements

### Manual Validation

```python
config = get_config()

# Get validation errors without raising
errors = config.validate()
if errors:
    for error in errors:
        print(f"Validation error: {error}")

# Validate and raise on errors
try:
    config.validate_and_raise()
except ConfigurationError as e:
    print(f"Configuration invalid: {e}")
```

### Custom Validation Rules

The system validates:

1. **Required Keys**: Different for each environment
2. **Type Validation**: Ensures values can be converted to expected types
3. **Format Validation**: 
   - ZIP codes (5-digit format)
   - Database URIs (proper protocol)
   - Log levels (valid level names)
4. **Range Validation**:
   - Port numbers (1-65535)
   - Positive timeouts
   - Reasonable worker counts
5. **Dependency Validation**:
   - Cache directory when caching enabled
   - Monitoring endpoint when monitoring enabled

## Environment-Specific Configuration

### Development Environment

```yaml
# config/development.yaml
logging:
  level: "DEBUG"
  console_output: true

collection:
  max_requests_per_hour: 50  # Lower for development
  target_zip_codes:
    - "85031"  # Single ZIP for testing

proxy:
  enabled: false  # No proxy in development
```

### Production Environment

```yaml
# config/production.yaml
logging:
  level: "INFO"
  format: "json"
  file_path: "/var/log/phoenix_real_estate/app.log"

collection:
  max_requests_per_hour: 100
  target_zip_codes:
    - "85031"
    - "85033"
    - "85035"

proxy:
  enabled: true
  rotation_enabled: true

security:
  encrypt_sensitive_logs: true
```

## Secret Management Integration

The configuration system integrates with the secret management module:

```python
from phoenix_real_estate.foundation.config import get_config, get_secret

config = get_config()

# Secrets are accessed separately
api_key = get_secret('SECRET_API_KEY_GOOGLE')
db_password = get_secret('CREDENTIAL_DB_PASS')

# Or through configuration if stored there
secret_key = config.get_required('security.secret_key')
```

See [Secret Management Guide](secrets-management.md) for details on handling sensitive values.

## Common Configuration Patterns

### Multi-Environment Setup

```bash
# Development
export ENVIRONMENT=development
export MONGODB_URI=mongodb://localhost:27017
export LOG_LEVEL=DEBUG

# Staging
export ENVIRONMENT=staging
export MONGODB_URI=mongodb://staging.example.com:27017
export LOG_LEVEL=INFO
export PHOENIX_MONITORING_ENABLED=true

# Production
export ENVIRONMENT=production
export MONGODB_URI=mongodb+srv://prod.mongodb.net
export LOG_LEVEL=WARNING
export PHOENIX_SECURITY_ENCRYPT_LOGS=true
```

### Docker Configuration

```dockerfile
# Dockerfile
ENV ENVIRONMENT=production
ENV PHOENIX_DATABASE_NAME=phoenix_real_estate
ENV PHOENIX_LOGGING_FORMAT=json
```

### GitHub Actions Configuration

```yaml
# .github/workflows/collect.yml
env:
  ENVIRONMENT: production
  MONGODB_URI: ${{ secrets.MONGODB_URI }}
  SECRET_API_KEY_GOOGLE: ${{ secrets.GOOGLE_API_KEY }}
```

## Troubleshooting

### Configuration Not Loading

1. **Check environment detection**:
   ```python
   config = get_config()
   print(f"Environment: {config.get_environment()}")
   ```

2. **Verify file locations**:
   - Config directory: `config/`
   - Environment files: `.env`, `.env.{environment}`

3. **Check precedence**:
   ```python
   # See what value is actually loaded
   value = config.get("database.uri")
   print(f"Database URI: {value}")
   ```

### Validation Errors

1. **Run validation to see all errors**:
   ```python
   errors = config.validate()
   for error in errors:
       print(error)
   ```

2. **Common issues**:
   - Missing required environment variables
   - Invalid ZIP code format
   - Port numbers out of range
   - Empty required values

### Type Conversion Errors

1. **Check the raw value**:
   ```python
   raw_value = config.get("key")
   print(f"Raw value: {raw_value!r}")
   ```

2. **Use default values**:
   ```python
   # Safe with default
   port = config.get_typed("database.port", int, default=27017)
   ```

## Migration Guide

### From Environment Variables Only

If migrating from a simple environment variable setup:

1. Create `config/base.yaml` with default values
2. Move environment-specific overrides to `config/{environment}.yaml`
3. Keep secrets and deployment-specific values in environment variables
4. Update code to use configuration object:

```python
# Before
import os
db_host = os.getenv('DB_HOST', 'localhost')

# After
from phoenix_real_estate.foundation.config import get_config
config = get_config()
db_host = config.get('database.host', 'localhost')
```

### From Other Configuration Systems

1. **From ConfigParser/INI files**:
   - Convert INI sections to YAML nested structure
   - Update access patterns to use dot notation

2. **From JSON configuration**:
   - Convert JSON to YAML for better readability
   - Leverage environment variable overrides

3. **From hardcoded values**:
   - Extract to configuration files
   - Use environment detection for different values

## Best Practices

1. **Use Type-Safe Access**: Always use `get_typed()` when you need a specific type
2. **Provide Defaults**: Use sensible defaults for optional configuration
3. **Validate Early**: Run validation at application startup
4. **Environment Isolation**: Keep environment-specific values in appropriate files
5. **Secret Separation**: Never put secrets in configuration files
6. **Document Requirements**: Clearly document required vs optional configuration
7. **Use Helpers**: Leverage built-in helper methods for common configurations

## Advanced Usage

### Custom Configuration Provider

```python
from phoenix_real_estate.foundation.config.base import ConfigProvider

class CustomConfigProvider(ConfigProvider):
    def __init__(self, data: dict):
        self.data = data
    
    def get(self, key: str, default=None):
        # Custom implementation
        pass
    
    # Implement other required methods
```

### Configuration Validation Extension

```python
def validate_custom_rules(config):
    """Add custom validation rules."""
    errors = []
    
    # Custom validation logic
    if config.get('custom.setting') == 'invalid':
        errors.append("custom.setting: Invalid value")
    
    return errors

# Add to validation
errors = config.validate()
errors.extend(validate_custom_rules(config))
```

## Configuration File Examples

See the following files for complete examples:
- [`config/base.yaml`](../config/base.yaml) - Base configuration
- [`config/development.yaml`](../config/development.yaml) - Development overrides
- [`config/production.yaml`](../config/production.yaml) - Production settings
- [`.env.sample`](../.env.sample) - Environment variable template