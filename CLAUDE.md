# Phoenix Real Estate Data Collector - Claude Development Guide

## PROJECT CONTEXT
- **Purpose**: Automated real estate data collection for Phoenix, AZ (zips: 85031, 85033, 85035)
- **Budget**: $25/month maximum (currently ~$2-3/month operational)
- **Status**: 98% operational - **All critical tests passing** ✅ Test suite: 1063+ tests collecting successfully
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
- **Testing**: **1063+ tests collecting successfully**, critical issues resolved
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

## CODE STANDARDS & GOTCHAS
- **Async/await** for all I/O operations, always `async with` for LLM components
- **MongoDB**: Use `is None` not boolean truthiness
- **Error handling**: Custom exceptions with proper chaining
- **Maricopa API**: `AUTHORIZATION` (uppercase) + `user-agent: null`
- **WebShare Auth**: `Authorization: Token {api_key}` format

## QUICK LLM USAGE
```python
from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.orchestration import ProcessingIntegrator

# Batch processing (optimized)
async with ProcessingIntegrator(EnvironmentConfigProvider()) as integrator:
    results = await integrator.process_maricopa_batch(property_list)
```

## RECENT FIXES & LESSONS LEARNED
- **Test Suite Recovery**: Fixed import errors (uvloop, DatabaseClient→DatabaseConnection)
- **Pipeline Bug**: Fixed batch processing duplication (24→10 results)
- **Cache Management**: Resolved memory size limit enforcement
- **Windows Compatibility**: uvloop conditional import for cross-platform support
- **ConfigProvider**: Use EnvironmentConfigProvider (not protocol interface)

## BEFORE COMMITS
1. `uv run ruff check . --fix` && `uv run pytest tests/` - Ensure quality
2. Check for hardcoded credentials, verify .env not committed

## CRITICAL GOTCHAS
- **TDD Guard**: Enabled - test-first development enforced
- **Windows Only**: uvloop disabled, use standard asyncio
- **Import Paths**: Always `phoenix_real_estate`, never `src`
- **Database**: Use `DatabaseConnection` not `DatabaseClient`
- **Config**: Use `EnvironmentConfigProvider()` for instantiation
- **Testing**: 81 linting errors remain (non-critical)