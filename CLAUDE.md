# Phoenix Real Estate Data Collector - Claude Development Guide

## PROJECT CONTEXT
- **Purpose**: Automated real estate data collection for Phoenix, AZ (zips: 85031, 85033, 85035)
- **Budget**: $25/month maximum (currently ~$2-3/month operational)
- **Status**: 98% operational - LLM processing + CI/CD complete (Tasks 6 & 7 ✅)
- **Architecture**: 3-tier (Collection → LLM Processing → Storage) with MongoDB v8.1.2
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
- **LLM**: Ollama with llama3.2:latest (2GB model)
- **Package Manager**: uv with pyproject.toml
- **Testing**: pytest (asyncio mode), ruff, pyright
- **CI/CD**: GitHub Actions (7 workflows implemented)

## PROJECT STRUCTURE
```
src/phoenix_real_estate/
├── foundation/          # Core infrastructure (config, db, logging)
├── collectors/          # Data collection + LLM processing (Task 6 ✅)
├── orchestration/       # ProcessingIntegrator, workflow coordination
└── models/              # PropertyDetails, validation models

config/*.yaml            # Configurations (proxies, selectors)
scripts/                 # Testing, setup, validation helpers
tests/                   # Unit, integration, e2e tests
```

## KEY COMMANDS
```bash
# Essential Services
net start MongoDB                                    # Start database (Admin)
ollama serve                                        # Start LLM service
ollama pull llama3.2:latest                        # Download model (2GB)

# Development Workflow
uv sync                                             # Install dependencies
uv run pytest tests/collectors/processing/ -v      # Test LLM processing
uv run ruff check . --fix                          # Lint + fix code
```

## CONFIGURATION FILES
1. **`.env`** - API keys required:
   - `MARICOPA_API_KEY` - From mcassessor.maricopa.gov
   - `WEBSHARE_API_KEY`- from webshare.io
   - `CAPTCHA_API_KEY` - 2captcha key ($10 balance)
   
2. **`config/proxies.yaml`** - WebShare proxy credentials in `.env`

## CURRENT STATUS (98% OPERATIONAL)

### Working Components (✅)
- **Infrastructure**: MongoDB v8.1.2, Ollama LLM, GitHub Actions CI/CD
- **APIs**: Maricopa (84% success), WebShare proxies, 2captcha
- **Testing**: >95% pass rate, comprehensive coverage
- **Security**: Zero hardcoded credentials, SSL enabled, .env configured

### Key Architectures
```
# LLM Processing Pipeline
Collectors → ProcessingIntegrator → DataProcessingPipeline → OllamaClient → MongoDB

# GitHub Actions Workflows
data-collection.yml → Daily automated collection (3 AM Phoenix)
ci-cd.yml          → Test suite with security scanning
monitoring.yml     → Budget tracking ($25/month limit)
```

## CRITICAL IMPLEMENTATION DETAILS

### Configuration
- **ConfigProvider**: Fixed get_typed() for boolean/None handling
- **YAML Reserved Words**: 'on', 'off', 'yes', 'no' auto-convert to booleans
- **Environment Variables**: Use sentinel objects to distinguish None vs missing

### API Integration
- **Maricopa Headers**: `AUTHORIZATION` (uppercase) + `user-agent: null`
- **WebShare Auth**: `Authorization: Token {api_key}` format
- **Import Path**: Always `phoenix_real_estate` not `src`

### Best Practices
- **MongoDB**: Use `is None` not boolean truthiness
- **Async Context**: Always `async with` for LLM components
- **Cache Keys**: Use CacheManager._generate_cache_key()

## CODE STANDARDS
- **Async/await** for all I/O operations
- **Error handling**: Use custom exceptions with proper chaining
- **Logging**: Use structured logging with get_logger()
- **Testing**: Minimum 80% coverage for new code
- **Security**: Never commit secrets, always use .env

## QUICK LLM USAGE
```python
from phoenix_real_estate.foundation import ConfigProvider
from phoenix_real_estate.orchestration import ProcessingIntegrator

# Single property processing
async with ProcessingIntegrator(ConfigProvider()) as integrator:
    result = await integrator.process_property(
        {"html": "<div>property data</div>"}, "phoenix_mls"
    )

# Batch processing (optimized)
async with ProcessingIntegrator(ConfigProvider()) as integrator:
    results = await integrator.process_maricopa_batch(property_list)
```

## RECENT FIXES & LESSONS LEARNED
- **ConfigProvider.get_typed()**: Fixed None handling with sentinel pattern
- **GitHub Actions YAML**: 'on:' converts to boolean True (YAML quirk)
- **CI/CD Security**: Replaced 23 hardcoded credentials with env vars
- **Service Layer Tests**: Added 47 tests for 100% coverage
- **SSL Verification**: Must be enabled in production (verify_ssl: true)

## BEFORE COMMITS
1. `uv run ruff check . --fix` - Fix linting issues
2. `uv run pytest tests/` - Ensure tests pass (>95% expected)
3. Check for hardcoded credentials (especially in workflows)
4. Verify .env not being committed

## NEXT STEPS
1. Add real API keys to .env file
2. Configure GitHub Secrets for CI/CD
3. Enable GitHub Actions in repo settings
4. Monitor initial production runs