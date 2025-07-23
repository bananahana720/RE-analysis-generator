# Phoenix Real Estate Data Collector - Claude Development Guide

## PROJECT CONTEXT
- **Purpose**: Automated real estate data collection for Phoenix, AZ (zips: 85031, 85033, 85035)
- **Budget**: $25/month maximum (currently ~$1/month with WebShare proxy)
- **Status**: 85% operational - MongoDB running, all APIs configured
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

# Data Collection (main.py not yet implemented)
python scripts/test_maricopa_api.py                # Test Maricopa API
python scripts/testing/test_phoenix_mls_selectors.py # Test MLS scraper

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
1. **`.env`** - API keys required:
   - `MARICOPA_API_KEY` - From mcassessor.maricopa.gov
   - `WEBSHARE_API_KEY`- from webshare.io
   - `CAPTCHA_API_KEY` - 2captcha key ($10 balance)
   
2. **`config/proxies.yaml`** - WebShare proxy list:
   - 10 working proxies configured
   - Username, Password - in `.env`
   - Download URL included for proxy list updates

## CURRENT STATUS (85% OPERATIONAL)

### Working Components (✅)
- MongoDB v8.1.2 running with all collections
- Maricopa API configured (84% success rate)
- WebShare proxy (10 proxies, verified working)
- 2captcha service ($10 balance)
- All code bugs fixed

### Recent Fixes Applied
1. **Config Loading**: BaseConfig uses `getattr()` not `get()`
2. **Database Check**: Changed to `if self._database is None`
3. **API Headers**: `AUTHORIZATION` + `user-agent: null`
4. **Proxy Config**: Updated with working credentials

## CRITICAL IMPLEMENTATION DETAILS
- **BaseConfig**: No `get()` method - use `getattr(config, 'key', default)`
- **Maricopa Headers**: Must use `AUTHORIZATION` (not Authorization) + `user-agent: null`
- **WebShare Auth**: `Authorization: Token {api_key}` format
- **Import Path**: Always use `phoenix_real_estate` not `src`
- **MongoDB Check**: Use `is None` not boolean truthiness

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