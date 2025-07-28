# Phoenix Real Estate Data Collector - Claude Development Guide

## PROJECT CONTEXT
- **Purpose**: Automated real estate data collection for Phoenix, AZ (zips: 85031, 85033, 85035)
- **Budget**: $25/month maximum (currently ~$1/month with WebShare proxy)
- **Status**: 90% operational - LLM processing complete (Task 6)
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
│   └── processing/      # LLM processing (Task 6 COMPLETE)
├── orchestration/       # ProcessingIntegrator, workflow coordination
├── models/              # PropertyDetails, validation models
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

# LLM Processing (NEW)
ollama serve                                        # Start Ollama service
ollama pull llama3.2:latest                        # Download model (2GB)
python scripts/testing/test_property_extractor.py  # Test LLM extraction
python scripts/examples/test_epic_integration.py   # Full pipeline test

# Development Workflow
uv sync                                             # Install dependencies
uv run ruff check . --fix                          # Lint code
uv run pytest tests/collectors/processing/ -v      # Test LLM processing
make security-check                                 # Check for secrets
```

## CONFIGURATION FILES
1. **`.env`** - API keys required:
   - `MARICOPA_API_KEY` - From mcassessor.maricopa.gov
   - `WEBSHARE_API_KEY`- from webshare.io
   - `CAPTCHA_API_KEY` - 2captcha key ($10 balance)
   
2. **`config/proxies.yaml`** - WebShare proxy credentials in `.env`

## CURRENT STATUS (90% OPERATIONAL)

### Working Components (✅)
- MongoDB v8.1.2 running with all collections
- Maricopa API configured (84% success rate)
- WebShare proxy (10 proxies, verified working)
- 2captcha service ($10 balance)
- **LLM Processing**: Ollama with llama3.2:latest (Task 6 complete)
- **83 unit tests** passing for processing module

### LLM Processing Architecture (NEW)
```
Collectors → ProcessingIntegrator → Pipeline → OllamaClient (llama3.2:latest)
```
- **Model**: llama3.2:latest (NOT llama2:7b) - 2GB download
- **Components**: OllamaClient, PropertyDataExtractor, ProcessingValidator
- **Error Handling**: Circuit breakers, dead letter queues, fallback extraction
- **Integration**: ProcessingIntegrator bridges collectors and pipeline

## CRITICAL IMPLEMENTATION DETAILS
- **BaseConfig**: No `get()` method - use `getattr(config, 'key', default)`
- **Maricopa Headers**: Must use `AUTHORIZATION` (not Authorization) + `user-agent: null`
- **WebShare Auth**: `Authorization: Token {api_key}` format
- **Import Path**: Always use `phoenix_real_estate` not `src`
- **MongoDB Check**: Use `is None` not boolean truthiness
- **Ollama Model**: llama3.2:latest (NOT llama2:7b) - critical for extraction
- **Async Context**: Always use `async with` for LLM components
- **Processing Flow**: Raw data → ProcessingIntegrator → Pipeline → Validated data

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

async with ProcessingIntegrator(ConfigProvider()) as integrator:
    result = await integrator.process_property(
        {"html": "<div>property data</div>"}, "phoenix_mls"
    )
```

## BEFORE COMMITS
1. `uv run ruff check . --fix` - Fix linting issues
2. `make security-check` - Scan for exposed secrets
3. `uv run pytest tests/` - Ensure tests pass
4. Review changes for sensitive data