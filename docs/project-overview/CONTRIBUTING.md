# Contributing to Phoenix Real Estate Data Collection System

Thank you for your interest in contributing to the Phoenix Real Estate Data Collection System! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Commit Message Conventions](#commit-message-conventions)
- [Documentation Standards](#documentation-standards)

## 📜 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Accept responsibility and apologize for mistakes
- Prioritize the project's best interests

### Unacceptable Behavior

- Harassment, discrimination, or offensive language
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that could be considered inappropriate

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

1. Python 3.13.4+ installed
2. uv package manager (`pip install uv`)
3. Git configured with your identity
4. A MongoDB Atlas account (free tier)
5. Basic understanding of clean architecture principles

### First Steps

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/yourusername/phoenix-real-estate.git
   cd phoenix-real-estate
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/original/phoenix-real-estate.git
   ```
4. Create a new branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 💻 Development Setup

### Environment Setup

1. **Install dependencies**:
   ```bash
   # Windows
   make dev_install_win
   
   # Unix/Mac
   make dev-install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Set up pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

4. **Verify installation**:
   ```bash
   make sanity_check
   make quality
   ```

### Development Tools

- **VS Code**: Recommended IDE with Python and Pylance extensions
- **PyCharm**: Alternative IDE with excellent Python support
- **Git hooks**: Automatically run quality checks before commits

### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml"
  ]
}
```

## 📝 Code Style Guidelines

### Core Principles

1. **KISS** (Keep It Simple, Stupid)
2. **DRY** (Don't Repeat Yourself)
3. **YAGNI** (You Aren't Gonna Need It)
4. **SOLID** principles
5. **Zen of Python** (`import this`)

### Python Style Guide

#### Formatting

- Line length: 100 characters maximum
- Use `ruff` for automatic formatting:
  ```bash
  make ruff
  ```

#### Naming Conventions

```python
# Classes: PascalCase
class PropertyRepository:
    pass

# Functions and variables: snake_case
def get_property_by_id(property_id: str) -> Property:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3

# Private methods: leading underscore
def _validate_input(data: dict) -> bool:
    pass
```

#### Type Hints

All functions must have complete type hints:

```python
from typing import List, Optional, Dict, Any

def process_properties(
    properties: List[Property],
    filters: Optional[Dict[str, Any]] = None
) -> List[ProcessedProperty]:
    """Process and filter property data.
    
    Args:
        properties: List of Property objects to process
        filters: Optional dictionary of filter criteria
        
    Returns:
        List of ProcessedProperty objects
        
    Raises:
        ValidationError: If property data is invalid
    """
    pass
```

#### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
class PropertyCollector:
    """Collects property data from various sources.
    
    This class implements the DataCollector interface and provides
    methods for retrieving property information from external APIs
    and websites.
    
    Attributes:
        config: Configuration provider instance
        repository: Property repository for data storage
        logger: Structured logger instance
    """
    
    def collect_properties(
        self,
        zip_codes: List[str],
        start_date: datetime
    ) -> List[Property]:
        """Collect properties for specified ZIP codes.
        
        Args:
            zip_codes: List of ZIP codes to search
            start_date: Start date for property search
            
        Returns:
            List of collected Property objects
            
        Raises:
            CollectionError: If data collection fails
            RateLimitError: If API rate limit is exceeded
            
        Example:
            >>> collector = PropertyCollector(config, repository)
            >>> properties = collector.collect_properties(
            ...     ["85001", "85002"],
            ...     datetime.now() - timedelta(days=7)
            ... )
        """
        pass
```

### File Organization

1. **Imports**: Group and order imports using `ruff`
2. **Module docstring**: Describe the module's purpose
3. **Constants**: Define at module level
4. **Classes**: Group related functionality
5. **Functions**: After classes, utilities at the end

Example structure:

```python
"""Property data collection module.

This module provides classes and functions for collecting
property data from various external sources.
"""

from datetime import datetime
from typing import List, Optional

from phoenix_real_estate.foundation import (
    ConfigProvider,
    PropertyRepository,
    get_logger,
)
from phoenix_real_estate.foundation.exceptions import CollectionError

# Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Classes
class PropertyCollector:
    """Main collector implementation."""
    pass

# Utility functions
def validate_zip_code(zip_code: str) -> bool:
    """Validate ZIP code format."""
    pass
```

## 🧪 Testing Requirements

### Test-Driven Development

**MANDATORY**: Write tests BEFORE implementing features.

1. Create failing test
2. Implement minimal code to pass
3. Refactor while keeping tests green
4. Ensure 100% test coverage for new code

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

from phoenix_real_estate.collectors import PropertyCollector
from phoenix_real_estate.foundation.exceptions import CollectionError


class TestPropertyCollector:
    """Test cases for PropertyCollector class."""
    
    @pytest.fixture
    def collector(self, mock_config, mock_repository):
        """Create PropertyCollector instance for testing."""
        return PropertyCollector(mock_config, mock_repository)
    
    def test_collect_properties_success(self, collector):
        """Test successful property collection."""
        # Arrange
        zip_codes = ["85001"]
        expected_count = 10
        
        # Act
        properties = collector.collect_properties(zip_codes)
        
        # Assert
        assert len(properties) == expected_count
        assert all(p.zip_code in zip_codes for p in properties)
    
    def test_collect_properties_rate_limit(self, collector):
        """Test rate limit handling during collection."""
        # Arrange
        collector._api_client.get.side_effect = RateLimitError()
        
        # Act & Assert
        with pytest.raises(CollectionError) as exc_info:
            collector.collect_properties(["85001"])
        
        assert "rate limit" in str(exc_info.value).lower()
```

### Testing Guidelines

1. **Test file naming**: `test_<module_name>.py`
2. **Test class naming**: `Test<ClassName>`
3. **Test method naming**: `test_<method>_<scenario>`
4. **Use fixtures**: Share setup code via pytest fixtures
5. **Mock external dependencies**: Never make real API calls
6. **Test edge cases**: Empty inputs, None values, exceptions
7. **Integration tests**: Separate directory for cross-component tests

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=phoenix_real_estate --cov-report=html

# Run specific test file
uv run pytest tests/collectors/test_property_collector.py

# Run tests matching pattern
uv run pytest -k "test_collect"

# Run with verbose output
uv run pytest -xvs
```

## 🔄 Pull Request Process

### Before Creating a PR

1. **Update from upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run quality checks**:
   ```bash
   make quality
   ```

3. **Ensure tests pass**:
   ```bash
   uv run pytest
   ```

4. **Update documentation** if needed

### Creating the PR

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub** with:
   - Clear, descriptive title
   - Link to related issue (if any)
   - Description of changes
   - Screenshots (if UI changes)
   - Test coverage report

3. **PR Description Template**:
   ```markdown
   ## Description
   Brief description of what this PR does.
   
   ## Related Issue
   Fixes #123
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Checklist
   - [ ] Tests pass locally
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] No new warnings
   ```

### Code Review Process

1. **Automated checks**: Must pass all CI/CD checks
2. **Peer review**: At least one approval required
3. **Address feedback**: Respond to all comments
4. **Update branch**: Keep up-to-date with main
5. **Squash commits**: Clean history before merge

### After Merge

1. Delete your feature branch
2. Update your local main branch
3. Celebrate your contribution! 🎉

## 🐛 Issue Reporting

### Before Creating an Issue

1. Search existing issues
2. Check documentation
3. Verify it's reproducible

### Creating an Issue

Use appropriate issue template:

#### Bug Report Template

```markdown
**Describe the bug**
Clear description of the issue.

**To Reproduce**
Steps to reproduce:
1. Configure '...'
2. Run command '...'
3. See error

**Expected behavior**
What should happen instead.

**Screenshots**
If applicable.

**Environment:**
- OS: [e.g., Windows 11]
- Python version: [e.g., 3.13.4]
- Project version: [e.g., 0.1.0]

**Additional context**
Any other relevant information.
```

#### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Additional context**
Any other information or screenshots.
```

## 📝 Commit Message Conventions

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **test**: Test additions or modifications
- **chore**: Maintenance tasks
- **build**: Build system changes
- **ci**: CI/CD changes

### Examples

```bash
# Feature
feat(collectors): add retry logic for API requests

Implement exponential backoff retry strategy for handling
temporary API failures. Maximum of 3 retries with delays
of 1, 2, and 4 seconds.

Closes #45

# Bug fix
fix(database): correct property ID generation

Property IDs were not unique when multiple collectors
ran simultaneously. Added timestamp and random suffix
to ensure uniqueness.

Fixes #67

# Documentation
docs(api): update configuration examples

Add examples for proxy configuration and rate limiting
settings. Include troubleshooting section for common
connection issues.

# Refactoring
refactor(foundation): extract validation logic

Move property validation logic from repository to
dedicated validator class following single responsibility
principle.
```

## 📚 Documentation Standards

### Code Documentation

1. **Module docstrings**: Describe purpose and contents
2. **Class docstrings**: Explain responsibility and usage
3. **Function docstrings**: Document parameters, returns, and exceptions
4. **Inline comments**: Explain "why" not "what"
5. **Type hints**: Always include for clarity

### Project Documentation

1. **README.md**: Keep updated with major changes
2. **Architecture docs**: Update for significant design changes
3. **API docs**: Auto-generated from docstrings
4. **Examples**: Provide working code examples
5. **Troubleshooting**: Document common issues and solutions

### Documentation Checklist

- [ ] All public APIs documented
- [ ] Examples provided for complex features
- [ ] Installation instructions tested
- [ ] Configuration options explained
- [ ] Error messages helpful and actionable

## 🎯 Areas for Contribution

### Current Priorities

1. **Testing**: Increase test coverage
2. **Documentation**: Improve examples and guides
3. **Performance**: Optimize data collection
4. **Features**: See GitHub issues labeled "good first issue"
5. **Bug fixes**: Check issues labeled "bug"

### Future Enhancements

- Web dashboard development
- Additional data source integrations
- Machine learning predictions
- Mobile application
- API rate limit optimizations

## 🤝 Getting Help

### Resources

1. **Documentation**: Check `docs/` directory
2. **Architecture**: Review `PRPs/architecture/`
3. **Examples**: See test files for usage patterns
4. **Issues**: Search closed issues for solutions

### Communication

- **GitHub Issues**: For bugs and features
- **Pull Requests**: For code discussions
- **Discussions**: For general questions

## 🏆 Recognition

Contributors are recognized in:
- Project README.md
- Release notes
- Special thanks section

Thank you for contributing to the Phoenix Real Estate Data Collection System! Your efforts help make this project better for everyone.