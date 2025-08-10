# Phoenix Real Estate Data Collection System

A comprehensive, automated system for collecting and analyzing Phoenix metropolitan area real estate data. Built with clean architecture principles, this system operates within strict budget constraints ($25/month) while maintaining legal compliance and high data quality standards.

## 📌 Current Status: 98% Operational

✅ **Completed Features:**
- Foundation Infrastructure (Epic 1)
- Data Collection Engine with Maricopa API & Phoenix MLS (Epic 2)
- LLM Processing with Ollama Integration (Task 6)
- GitHub Actions CI/CD Automation (Task 7)
- Budget Compliance System (32% of free tier)
- Security & Compliance Framework

🚀 **Ready for Production:** Add API keys and configure GitHub Secrets to begin automated collection.

## 📋 Quick Reference

### Essential Commands
```bash
# Local Development
uv sync                                    # Install dependencies
uv run pytest tests/ -v                   # Run tests
uv run ruff check . --fix                # Lint code
python scripts/validation/workflow_validator.py      # Validate GitHub Actions

# Services (Windows)
net start MongoDB                         # Start database (Admin)
ollama serve                             # Start LLM service
ollama pull llama3.2:latest              # Download model (2GB)

# GitHub Actions (after setup)
gh workflow run data-collection.yml      # Manual collection run
gh run list                             # View recent runs
```

### Key Files
- `.env` - API keys configuration
- `config/proxies.yaml` - Proxy settings
- `.github/workflows/` - GitHub Actions workflows
- `docs/project-overview/CLAUDE.md` - Development guide for AI assistants

## 🚀 Quick Start

### Prerequisites

- Python 3.13.4+
- Node.js 20.17.0+ (for future UI components)
- MongoDB 8.1.2+ (local or Atlas)
- Ollama with llama3.2:latest model (2GB)
- uv package manager (`pip install uv`)
- GitHub account with Actions enabled

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

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys:
# - MARICOPA_API_KEY (from mcassessor.maricopa.gov)
# - WEBSHARE_API_KEY (from webshare.io)
# - CAPTCHA_API_KEY (from 2captcha.com)
```

4. Set up local services:
```bash
# Start MongoDB (Windows - run as Administrator)
net start MongoDB

# Start Ollama service
ollama serve

# Pull the LLM model (2GB download)
ollama pull llama3.2:latest
```

5. Run quality checks:
```bash
make quality
```

## 🔧 GitHub Actions Setup (Required for Automation)

### Step 1: Enable GitHub Actions

1. Go to your repository on GitHub
2. Click on "Settings" → "Actions" → "General"
3. Select "Allow all actions and reusable workflows"
4. Click "Save"

### Step 2: Configure GitHub Secrets

Navigate to "Settings" → "Secrets and variables" → "Actions" and add these secrets:

#### Required Secrets:
```yaml
# API Keys (same as .env file)
MARICOPA_API_KEY: your_maricopa_api_key
WEBSHARE_API_KEY: your_webshare_api_key  
CAPTCHA_API_KEY: your_2captcha_api_key

# MongoDB Connection
MONGODB_URI: mongodb://localhost:27017/phoenix_real_estate
TEST_MONGODB_PASSWORD: your_test_db_password

# Notifications (optional but recommended)
SLACK_WEBHOOK_URL: your_slack_webhook_url
NOTIFICATION_EMAIL: your_email@example.com
```

### Step 3: Verify Workflows

The repository includes 7 production-ready workflows:

1. **data-collection.yml** - Daily data collection (3 AM Phoenix time)
2. **ci-cd.yml** - Continuous integration and testing
3. **monitoring.yml** - Budget and system monitoring
4. **security.yml** - Security scanning and compliance
5. **deployment.yml** - Production deployment management
6. **maintenance.yml** - System maintenance tasks
7. **test-workflows.yml** - Workflow validation

To verify they're working:
```bash
# Check workflow syntax locally
python scripts/validation/workflow_validator.py

# View in GitHub UI
# Go to "Actions" tab - all workflows should appear
```

### Step 4: Initial Test Run

1. Go to the "Actions" tab in your repository
2. Select "CI/CD Pipeline" workflow
3. Click "Run workflow" → "Run workflow"
4. Monitor the execution (should take ~5-10 minutes)

### Step 5: Monitor Budget Usage

The system is designed to stay within FREE GitHub Actions tier:
- Target: <1000 minutes/month (50% of free 2000 minutes)
- Current usage: ~635 minutes/month (32% of free tier)
- Daily budget: ~21 minutes

Monitor usage at: Settings → Billing → Actions

## 📊 Production Operation Guide

### Daily Automated Schedule

| Time (PST) | Workflow | Duration | Purpose |
|------------|----------|----------|---------|
| 3:00 AM | Data Collection | ~15 min | Collect property data |
| 3:30 AM | LLM Processing | ~20 min | Process with Ollama |
| 4:00 AM | Monitoring | ~5 min | Budget & health check |
| 6:00 AM | Security Scan | ~10 min | Vulnerability check |

### Manual Operations

```bash
# Force data collection run
gh workflow run data-collection.yml

# Check workflow status
gh run list --workflow=data-collection.yml

# View recent logs
gh run view --log

# Download artifacts
gh run download [run-id]
```

### Monitoring Dashboard

Access monitoring data:
1. **GitHub Actions**: Actions tab → workflow runs
2. **Budget Tracking**: Settings → Billing → Actions
3. **Security Alerts**: Security tab → Dependabot
4. **Issue Tracking**: Automated issues for failures

## 📁 Project Structure

The project follows clean architecture principles with clear separation of concerns:

```
├── src/phoenix_real_estate/    # Main application code
│   ├── foundation/             # Core infrastructure (Epic 1)
│   │   ├── config/            # Configuration management
│   │   ├── database/          # Repository pattern implementation
│   │   ├── logging/           # Structured logging
│   │   ├── monitoring/        # Metrics and observability
│   │   └── utils/             # Common utilities
│   ├── collectors/            # Data collection modules (Epic 2)
│   │   ├── base/              # Base collector classes
│   │   ├── maricopa/          # Maricopa County API collector
│   │   └── phoenix_mls/       # Phoenix MLS scraper
│   └── processors/            # Data processing pipeline
├── tests/                     # Test suite
│   ├── collectors/            # Collector tests
│   ├── foundation/            # Foundation layer tests
│   └── integration/           # Integration tests
├── scripts/                   # Utility scripts
│   ├── setup/                 # Environment setup scripts
│   ├── validation/            # Validation and testing scripts
│   └── testing/               # Testing utilities
├── config/                    # Configuration files
│   ├── monitoring/            # Prometheus/Grafana configs
│   └── selectors/             # CSS selectors for scraping
├── docs/                      # Documentation
│   ├── api/                   # API documentation
│   ├── architecture/          # Architecture diagrams
│   └── summaries/             # Implementation summaries
├── reports/                   # Generated reports
│   ├── production/            # Production readiness reports
│   ├── testing/               # Test results and metrics
│   └── validation/            # Validation reports
├── tools/                     # Development tools
│   └── validation/            # Validation utilities
├── examples/                  # Usage examples and demos
├── research/                  # Research and findings
├── PRPs/                      # Project Requirements & Planning
│   ├── epics/                 # Epic-level documentation
│   ├── tasks/                 # Task-specific documentation
│   ├── workflows/             # Implementation workflows
│   └── architecture/          # Architecture decisions
└── logs/                      # Runtime logs (auto-managed)
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
   - For local MongoDB: ensure service is running (`net start MongoDB`)
   - For Atlas: verify connection string in `.env`
   - Check network connectivity and firewall settings
   - Ensure IP whitelist includes your address

4. **Test Failures**:
   - Ensure all environment variables are set
   - Check test database is accessible
   - Verify Ollama service is running
   - Run `make quality` to fix code issues

### GitHub Actions Troubleshooting

1. **Workflow Not Appearing**:
   - Ensure file is in `.github/workflows/` directory
   - Check YAML syntax with `python scripts/validation/workflow_validator.py`
   - Verify GitHub Actions is enabled in repository settings

2. **Workflow Failures**:
   ```yaml
   # Common fixes:
   # - Missing secrets: Add in Settings → Secrets
   # - YAML parsing: Use 'on:' not on: (quotes required)
   # - Permission errors: Check GITHUB_TOKEN permissions
   ```

3. **Budget Exceeded**:
   - Check usage: Settings → Billing → Actions
   - Reduce schedule frequency in workflow files
   - Enable workflow concurrency limits
   - Use `workflow_dispatch` for manual runs only

4. **MongoDB Connection in Actions**:
   - Use GitHub-hosted MongoDB service
   - Or use MongoDB Atlas with IP whitelist for GitHub
   - Ensure TEST_MONGODB_PASSWORD secret is set

5. **Ollama Issues in CI**:
   - Ollama runs in Docker container in CI
   - Model is cached between runs
   - Check container logs if failures occur

### Critical Known Issues

1. **YAML Boolean Conversion**:
   ```yaml
   # WRONG - 'on' converts to boolean True
   on:
     schedule:
   
   # CORRECT - Use quotes
   'on':
     schedule:
   ```

2. **ConfigProvider None Values**:
   - Fixed in latest version
   - Uses sentinel pattern for proper None handling

3. **SSL Verification**:
   - Must be enabled in production (`verify_ssl: true`)
   - Required for WebShare proxy connections

### Getting Help

1. Check existing documentation in `docs/`
2. Review architecture decisions in `PRPs/architecture/adrs/`
3. Examine test files for usage examples
4. Review workflow logs in GitHub Actions tab
5. Submit issues with detailed error logs

## 📚 API Documentation

API documentation is auto-generated and available at:
- Development: `http://localhost:8000/docs`
- Production: See deployment documentation

## 🤝 Contributing

Please see [CONTRIBUTING.md](docs/project-overview/CONTRIBUTING.md) for detailed guidelines on:
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