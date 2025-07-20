# Phoenix Real Estate Data Collection System

A comprehensive, automated system for collecting and analyzing Phoenix metropolitan area real estate data. Built with clean architecture principles, this system operates within strict budget constraints ($5/month) while maintaining legal compliance and high data quality standards.

## 🚀 Quick Start

### Prerequisites

- Python 3.13.4+
- Node.js 20.17.0+ (for future UI components)
- MongoDB Atlas account (free tier)
- uv package manager (`pip install uv`)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/phoenix-real-estate.git
cd phoenix-real-estate
```

2. Set up the development environment:
```bash
# For Windows
make dev_install_win

# For Unix/Mac
make dev-install
```

3. Copy the environment template and configure:
```bash
cp .env.example .env
# Edit .env with your configuration values
```

4. Run quality checks:
```bash
make quality
```

## 📁 Project Structure

The project follows clean architecture principles with clear separation of concerns:

```
src/phoenix_real_estate/
├── foundation/          # Core infrastructure (Epic 1)
│   ├── config/         # Configuration management
│   ├── database/       # Repository pattern implementation
│   ├── logging/        # Structured logging system
│   └── utils/          # Shared utilities and exceptions
├── collectors/         # Data collection engines (Epic 2)
├── processors/         # LLM and data processing (Epic 2)
├── orchestration/      # Automation workflows (Epic 3)
└── api/               # API endpoints (future)
```

## 🛠️ Development Workflow

### Essential Commands

```bash
# Code Quality
make ruff              # Format, lint, and autofix code
make pyright          # Type checking
make quick_pyright    # Fast type check (changed files only)

# Testing
uv run pytest         # Run all tests
uv run pytest -xvs    # Run with verbose output and stop on first failure
tox -e py313-pytest   # Test in isolated environment

# Development Tools
make sanity_check     # Check for installation issues
make quality          # Run all quality checks
```

### Development Guidelines

1. **Test-Driven Development**: Write tests BEFORE implementation
2. **Type Safety**: All functions must have type hints
3. **Documentation**: Google-style docstrings for all public APIs
4. **Code Quality**: Must pass `ruff` and `pyright` checks

### Working with the Codebase

1. **Adding New Features**:
   - Create tests first in the appropriate `tests/` directory
   - Implement feature following existing patterns
   - Ensure all quality checks pass
   - Update documentation as needed

2. **Making Changes**:
   - Always check for existing implementations first
   - Prefer extending existing code over creating new files
   - Follow SOLID principles and clean architecture patterns
   - Reference specific file paths in commits

## 🏗️ Architecture Overview

The system implements a 4-epic architecture:

### Epic 1: Foundation Infrastructure
- **Repository Pattern**: Clean data access abstraction
- **Configuration Management**: Environment-based settings
- **Structured Logging**: Comprehensive observability
- **Error Handling**: Consistent exception hierarchy

### Epic 2: Data Collection Engine
- **Maricopa County API**: Official property records
- **PhoenixMLS Scraper**: Market listing data
- **Local LLM Processing**: Privacy-preserving data extraction
- **Proxy Management**: Compliant web scraping

### Epic 3: Automation & Orchestration
- **GitHub Actions**: Daily automated workflows
- **Docker Deployment**: Containerized execution
- **Orchestration Engine**: Coordinated data collection
- **Report Generation**: Daily/weekly analytics

### Epic 4: Quality Assurance
- **Testing Framework**: Comprehensive test coverage
- **Real-time Monitoring**: System health tracking
- **Compliance Validation**: Legal and rate limit adherence
- **Data Quality Metrics**: Accuracy and completeness tracking

## 📊 Data Schema

Properties are stored in MongoDB with the following structure:

```javascript
{
  property_id: "unique_identifier",
  address: {
    street: "123 Main St",
    city: "Phoenix",
    zip: "85001"
  },
  prices: [{
    date: "2025-01-20T10:00:00Z",
    amount: 450000,
    source: "maricopa_county"
  }],
  features: {
    beds: 3,
    baths: 2,
    sqft: 1800,
    lot_size: 7500
  },
  listing_details: {
    // Flexible fields from various sources
  },
  last_updated: "2025-01-20T10:00:00Z"
}
```

## 🔧 Configuration

The system uses hierarchical configuration:

1. **Environment Variables**: Sensitive data (API keys, database URLs)
2. **YAML Files**: Environment-specific settings
3. **Code Defaults**: Fallback values

Key configuration areas:
- Database connection settings
- API rate limits and timeouts
- Proxy configurations
- Target ZIP codes
- LLM processing parameters

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=phoenix_real_estate

# Run specific test file
uv run pytest tests/foundation/test_config.py

# Run integration tests only
uv run pytest tests/integration/
```

### Test Organization

- `tests/foundation/`: Unit tests for core infrastructure
- `tests/integration/`: Cross-component integration tests
- `tests/collectors/`: Data collection tests
- `tests/processors/`: LLM processing tests

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   make sanity_check  # Check for installation issues
   make dev-install   # Reinstall in development mode
   ```

2. **Type Checking Slow**:
   ```bash
   make quick_pyright  # Use incremental type checking
   ```

3. **Database Connection Issues**:
   - Verify MongoDB Atlas connection string in `.env`
   - Check network connectivity
   - Ensure IP whitelist includes your address

4. **Test Failures**:
   - Ensure all environment variables are set
   - Check test database is accessible
   - Run `make quality` to fix code issues

### Getting Help

1. Check existing documentation in `docs/`
2. Review architecture decisions in `PRPs/architecture/adrs/`
3. Examine test files for usage examples
4. Submit issues with detailed error logs

## 📚 API Documentation

API documentation is auto-generated and available at:
- Development: `http://localhost:8000/docs`
- Production: See deployment documentation

## 🤝 Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Development setup
- Code style requirements
- Testing requirements
- Pull request process
- Commit conventions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔒 Security & Compliance

- **Personal Use Only**: System designed for individual use
- **Rate Limiting**: Respects all API rate limits
- **robots.txt Compliance**: Honors website scraping policies
- **Data Privacy**: Local LLM processing, no external data transmission
- **Budget Compliance**: Operates within $5/month constraint

## 🚀 Future Enhancements

- Web-based dashboard for data visualization
- Additional data sources integration
- Advanced analytics and ML predictions
- Mobile application for property tracking
- Real-time alerts for market changes

---

For detailed architecture documentation, see [docs/architecture.md](docs/architecture.md)