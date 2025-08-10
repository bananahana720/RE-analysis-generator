# Project Directory Structure

## Overview
This document describes the standardized directory structure for the Phoenix Real Estate Data Collection System following Python project best practices.

## Root Directory Structure

```
phoenix-real-estate-data-collection/
├── .github/                    # GitHub Actions workflows and templates
├── .venv/                      # Python virtual environment
├── config/                     # Configuration files
├── data/                       # Data storage and processing
├── docs/                       # Project documentation
├── docker/                     # Docker configurations
├── monitoring/                 # Monitoring and logging
├── scripts/                    # Utility and deployment scripts
├── src/                        # Source code
├── tests/                      # Test files
├── .env.sample                 # Environment template
├── .gitignore                  # Git ignore patterns
├── .pre-commit-config.yaml     # Pre-commit hooks
├── pyrightconfig.json          # TypeScript/Python type checking
├── README.md                   # Main project documentation
└── requirements.txt            # Python dependencies
```

## Directory Descriptions

### `/config/` - Configuration Management
Organized configuration files by purpose and environment:

```
config/
├── deployment/                 # Deployment-specific configurations
├── environments/               # Environment-specific settings
├── monitoring/                 # Monitoring system configurations
├── services/                   # Service-specific configurations
├── templates/                  # Configuration templates
└── base.yaml                   # Base configuration
```

### `/docs/` - Documentation Hub
Comprehensive documentation organized by category:

```
docs/
├── api/                        # API documentation
├── deployment/                 # Deployment guides
├── operations/                 # Operational procedures
├── project-management/         # Project planning and management
├── project-reports/           # Status reports and analysis
├── security/                   # Security documentation
├── troubleshooting/           # Issue resolution guides
└── README.md                   # Documentation index
```

### `/scripts/` - Automation Scripts
Utility scripts organized by function:

```
scripts/
├── database/                   # Database management scripts
├── deploy/                     # Deployment automation
├── setup/                      # Environment setup scripts
├── testing/                    # Testing utilities
├── utilities/                  # General utility scripts
└── validation/                 # Validation and verification
```

### `/src/` - Source Code
Main application code following clean architecture:

```
src/phoenix_real_estate/
├── collectors/                 # Data collection modules
├── foundation/                 # Core infrastructure
├── processors/                 # Data processing modules
└── __init__.py
```

### `/tests/` - Test Suite
Comprehensive test coverage:

```
tests/
├── integration/                # Integration tests
├── unit/                       # Unit tests
└── conftest.py                 # Test configuration
```

## File Organization Principles

### Documentation Files
- **Project Reports**: `docs/project-reports/`
- **Security Documentation**: `docs/security/`
- **Troubleshooting Guides**: `docs/troubleshooting/`
- **API Documentation**: `docs/api/`
- **Deployment Guides**: `docs/deployment/`

### Configuration Files
- **Environment Configs**: `config/environments/`
- **Service Configs**: `config/services/`
- **Deployment Configs**: `config/deployment/`
- **Monitoring Configs**: `config/monitoring/`

### Script Organization
- **Setup Scripts**: `scripts/setup/`
- **Deployment Scripts**: `scripts/deploy/`
- **Testing Scripts**: `scripts/testing/`
- **Utility Scripts**: `scripts/utilities/`
- **Validation Scripts**: `scripts/validation/`

## Naming Conventions

### Files
- **Markdown Files**: `UPPERCASE_WITH_UNDERSCORES.md`
- **Configuration Files**: `lowercase-with-hyphens.yaml`
- **Python Files**: `lowercase_with_underscores.py`
- **Script Files**: `descriptive_action.py`

### Directories
- **Standard Directories**: `lowercase-with-hyphens`
- **Python Packages**: `lowercase_with_underscores`
- **Documentation Categories**: `lowercase-categories`

## Import Path Standards

After reorganization, import paths follow these patterns:

```python
# Source code imports
from src.phoenix_real_estate.collectors import MaricopaCollector
from src.phoenix_real_estate.foundation.config import BaseConfig

# Test imports
from tests.unit.collectors.test_maricopa import TestMaricopaCollector
from tests.integration.test_e2e import TestEndToEnd
```

## Quality Standards

### Directory Structure Quality Gates
- ✅ Logical separation of concerns
- ✅ Consistent naming conventions
- ✅ Clear hierarchical organization
- ✅ Scalable structure for future growth
- ✅ Standard Python project conventions

### File Organization Quality Gates
- ✅ Files in appropriate directories based on function
- ✅ No duplicate or obsolete files
- ✅ Clear file naming that indicates purpose
- ✅ Proper documentation indexing
- ✅ Import paths updated where necessary

## Maintenance

### Regular Cleanup Tasks
1. **Monthly**: Review and clean temporary files
2. **Quarterly**: Validate directory structure compliance
3. **Per Release**: Update documentation index
4. **As Needed**: Reorganize based on project evolution

### Directory Structure Evolution
As the project grows, new directories should be added following these principles:
- **Purpose-Based**: Directories reflect functional purpose
- **Scalable**: Structure can accommodate growth
- **Standard**: Follow Python and industry conventions
- **Documented**: Updates to structure are documented

This structure provides a solid foundation for maintainable, scalable project organization while following industry best practices for Python projects.