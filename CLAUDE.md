# Phoenix Real Estate Data Collector - Claude Development Guide

## PROJECT CONTEXT
- **Purpose**: Automated real estate data collection for Phoenix, AZ (zips: 85031, 85033, 85035)
- **Budget**: $25/month maximum (currently ~$2-3/month operational)
- **Status**: 95% operational - LLM processing production-ready (Task 6 COMPLETE)
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
- **Web Scraping**: Playwright (for Phoenix MLS)

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

## CURRENT STATUS (95% OPERATIONAL)

### Working Components (✅)
- MongoDB v8.1.2, Maricopa API (84% success), WebShare proxy (10), 2captcha ($10)
- **LLM Processing**: Production-ready with caching, monitoring, performance optimization
- **All tests passing** (critical issues from quality assessment resolved)

### LLM Processing Architecture (PRODUCTION-READY)
```
Collectors → ProcessingIntegrator → DataProcessingPipeline → OllamaClient → MongoDB
```
- **Model**: llama3.2:latest (2GB) - High accuracy, fast processing
- **Components**: OllamaClient, PropertyDataExtractor, ProcessingValidator, CacheManager
- **Features**: Caching, monitoring, batch processing, circuit breakers, error recovery

## CRITICAL IMPLEMENTATION DETAILS
- **Config**: Use `config.get()` and `config.get_typed()` (NOT config.settings.FIELD)
- **Maricopa Headers**: Must use `AUTHORIZATION` (not Authorization) + `user-agent: null`
- **WebShare Auth**: `Authorization: Token {api_key}` format
- **Import Path**: Always use `phoenix_real_estate` not `src`
- **MongoDB Check**: Use `is None` not boolean truthiness
- **Ollama Model**: llama3.2:latest (NOT llama2:7b) - critical for extraction
- **Async Context**: Always use `async with` for LLM components
- **Cache Keys**: Use CacheManager._generate_cache_key() for consistent caching

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

## COMMON ISSUES
- **Config errors**: Use `config.get()` not `config.settings.FIELD`
- **Import errors**: Check missing imports (OllamaClient, etc.)
- **Cache/Ollama**: Verify service running and key generation

## BEFORE COMMITS
1. `uv run ruff check . --fix` - Fix linting issues
2. `make security-check` - Scan for exposed secrets
3. `uv run pytest tests/` - Ensure tests pass
4. Review changes for sensitive data