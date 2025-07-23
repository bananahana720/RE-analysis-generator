# Phoenix Real Estate Data Collector - Claude Development Guide

## CRITICAL PROJECT CONTEXT
- **Purpose**: Automated real estate data collection for Phoenix, AZ (zip codes: 85031, 85033, 85035)
- **Budget**: $25/month maximum (currently ~$1/month with free tiers)
- **Status**: Epic 1 Foundation 95% complete - Maricopa API ready, Phoenix MLS needs selectors
- **Windows Environment**: Always use Windows paths with backslashes

## RULES (violating ANY invalidates your response):
❌ No new files without exhaustive reuse analysis
❌ No rewrites when refactoring is possible
❌ No generic advice - provide specific implementations
❌ No ignoring existing codebase architecture
✅ Extend existing services and components
✅ Consolidate duplicate code
✅ Reference specific file paths with Windows backslashes
✅ Test-driven development is MANDATORY
✅ Clean up after yourself (temp files, unused imports, etc.)

## Environment Setup
- **Package Management**: ALWAYS use uv with pyproject.toml, never pip
- **Python Version**: 3.13.4
- **Node Version**: 20.17.0
- **Database**: MongoDB (local - localhost:27017)
- **Testing**: pytest, tox, ruff, pyright

## Most Used Commands

```bash
# MongoDB (Windows - run as Administrator)
net start MongoDB                                        # Start service
python scripts/testing/test_mongodb_connection.py       # Test & setup database

# Code Quality (run before commits)
uv run ruff check . --fix                               # Lint and auto-fix
uv run pytest tests/                                    # Run tests
make security-check                                     # Check for exposed secrets

# Data Collection Testing
python scripts/test_maricopa_api.py --api-key KEY      # Test Maricopa API
python scripts/testing/discover_phoenix_mls_selectors.py --headless  # Find MLS selectors
```

## Key Architecture Points

- **MongoDB**: Local instance on `localhost:27017`, database: `phoenix_real_estate`
- **Data Sources**: 
  - Maricopa County API (working with 84% success rate)
  - Phoenix MLS (needs selector configuration from live site)
- **Project Structure**:
  - `src/collection/` - Data collectors (Maricopa API, Phoenix MLS scraper)
  - `src/database/` - MongoDB models and connections
  - `src/processing/` - LLM data processing (Epic 2)
  - `src/api/` - FastAPI backend (Epic 3)
  - `config/` - Configuration files (use .example templates)

## Critical Configuration Files

- **`.env`**: Create from `.env.sample` - contains API keys, never commit!
- **`config/proxies.yaml`**: Create from `config/proxies.yaml.example` - proxy credentials
- **`config/selectors/phoenix_mls.yaml`**: CSS selectors for Phoenix MLS (needs update)
- **Security**: Run `make security-check` before commits to scan for exposed secrets

## Common Issues & Solutions

1. **MongoDB Connection Refused**: Run `net start MongoDB` as Administrator
2. **Import Errors**: Use `uv sync` to ensure all dependencies are installed
3. **Maricopa API 403**: Check API key in `.env` file
4. **Phoenix MLS Blocked**: Need proxy service (Webshare.io) and updated selectors
5. **Test Failures**: Check MongoDB is running and `.env` is configured

## Next Steps for Completion

1. **Configure Phoenix MLS Selectors** (2-3 hours)
   - Run `python scripts/testing/discover_phoenix_mls_selectors.py`
   - Update `config/selectors/phoenix_mls.yaml`
   
2. **Set Up Proxy Service** (1 hour)
   - Sign up for Webshare.io ($1/month)
   - Copy `config/proxies.yaml.example` to `config/proxies.yaml`
   - Add credentials to `.env`
   
3. **Begin Data Collection**
   - Run `python src/main.py` for manual test
   - Deploy to GitHub Actions for daily runs

## Code Quality Standards

- **Before ANY commit**: Run `uv run ruff check . --fix` and `make security-check`
- **Test-driven development**: Write tests FIRST, always
- **Type hints**: Required for all functions
- **Exception handling**: Always use `raise ... from` for proper chaining
- **Documentation**: Google-style docstrings mandatory