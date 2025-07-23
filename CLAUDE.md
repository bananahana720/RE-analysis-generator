# Phoenix Real Estate Data Collector - Claude Development Guide

## PROJECT CONTEXT
- **Purpose**: Automated real estate data collection for Phoenix, AZ (zips: 85031, 85033, 85035)
- **Budget**: $25/month maximum (currently ~$1/month)
- **Status**: 40% operational - MongoDB not running, needs Maricopa API key
- **Architecture**: 3-tier (Collection → Processing → API) with MongoDB storage
- **Package Name**: `phoenix_real_estate` (not `src`)

## DEVELOPMENT RULES
✅ **ALWAYS** check for existing files/components before creating new ones
✅ Use Windows paths with backslashes
✅ Test-driven development - write tests FIRST
✅ Type hints required for all functions
✅ Google-style docstrings mandatory
❌ No new files without exhaustive reuse analysis
❌ No rewrites when refactoring suffices
❌ No generic advice - provide specific implementations

## ENVIRONMENT & TOOLS
- **Python**: 3.13.4 (managed by uv, NOT pip)
- **Database**: MongoDB v8.1.2 (localhost:27017)
- **Package Manager**: uv with pyproject.toml
- **Testing**: pytest (asyncio mode), ruff, pyright
- **Web Scraping**: Playwright (for Phoenix MLS)

## PROJECT STRUCTURE
```
src/phoenix_real_estate/
├── foundation/          # Core infrastructure (config, db, logging)
├── collectors/          # Data collection (Maricopa API, Phoenix MLS)
├── processors/          # LLM processing (Epic 2 - future)
├── api/                 # FastAPI backend (Epic 3 - future)
├── orchestration/       # Workflow coordination
└── utils/              # Shared utilities

config/                  # YAML configurations
├── proxies.yaml        # WebShare proxy settings
├── selectors/          # CSS selectors for scrapers
└── *.yaml.example      # Template files

scripts/
├── testing/            # Test scripts for services
├── setup/              # Configuration helpers
└── validation/         # System validation

tests/
├── e2e/               # End-to-end tests with Playwright
├── collectors/        # Collector unit tests
└── foundation/        # Infrastructure tests
```

## KEY COMMANDS
```bash
# MongoDB Management (run as Administrator)
net start MongoDB                                    # Start service
net stop MongoDB                                     # Stop service
python scripts/testing/test_mongodb_connection.py   # Test connection

# Service Testing
python scripts/testing/test_webshare_proxy.py      # Test WebShare API
python scripts/testing/test_services_simple.py     # Test all services
python scripts/setup/check_setup_status.py         # System readiness

# Data Collection
python src/main.py --source maricopa --limit 5     # Maricopa test
python src/main.py --source phoenix_mls --limit 1  # Phoenix MLS test

# Development Workflow
uv sync                                             # Install dependencies
uv run ruff check . --fix                          # Lint code
uv run pytest tests/ -v                            # Run tests
make security-check                                 # Check for secrets

# E2E Testing
uv run pytest tests/e2e/test_simple_e2e.py        # Basic E2E tests
python scripts/testing/run_e2e_tests.py --fix     # Full E2E suite
```

## CONFIGURATION FILES
1. **`.env`** - API keys and secrets (create from `.env.sample`)
   - MONGODB_URI, MARICOPA_API_KEY, WEBSHARE credentials
   - CAPTCHA_API_KEY for 2captcha service
   
2. **`config/proxies.yaml`** - Proxy configuration
   - WebShare settings with auth format: `Authorization: Token API_KEY`
   
3. **`config/selectors/phoenix_mls.yaml`** - CSS selectors
   - Needs update from live site using discover script

## CURRENT STATUS & BLOCKERS

### Working Components (✅)
- Project structure and all code
- 2captcha service ($10 balance)
- E2E test infrastructure
- Maricopa collector (needs API key)

### Blocked Components (❌)
1. **MongoDB not running**
   - Fix: `net start MongoDB` (as Administrator)
   
2. **Maricopa API unauthorized**
   - Fix: Get API key from mcassessor.maricopa.gov
   - Add to .env: `MARICOPA_API_KEY=your_key`
   
3. **WebShare proxy untested**
   - Credentials configured but needs validation
   - Run: `python scripts/testing/test_webshare_proxy.py`

## COMMON ISSUES & SOLUTIONS
- **Import errors**: Run `uv sync` to install dependencies
- **MongoDB refused**: Start service as Administrator
- **"No module named src"**: Use `phoenix_real_estate` package name
- **Maricopa 403/500**: Missing or invalid API key
- **WebShare 404**: Use correct API endpoint with Token auth

## CODE STANDARDS
- **Async/await** for all I/O operations
- **Error handling**: Use custom exceptions with proper chaining
- **Logging**: Use structured logging with get_logger()
- **Testing**: Minimum 80% coverage for new code
- **Security**: Never commit secrets, always use .env

## BEFORE COMMITS
1. `uv run ruff check . --fix` - Fix linting issues
2. `make security-check` - Scan for exposed secrets
3. `uv run pytest tests/` - Ensure tests pass
4. Review changes for sensitive data