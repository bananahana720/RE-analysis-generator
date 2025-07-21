# Phoenix Real Estate - Quick Reference

## Environment
- **Path**: `C:/Users/Andrew/.vscode/RE-analysis-generator`
- **Tools**: `uv` (not pip), Python 3.13.4, MongoDB Atlas free tier
- **Commands**: `uv sync --extra dev`, `uv run pytest`, `make ruff`

## Architecture Patterns
- **Structure**: `src/phoenix_real_estate/{foundation,collectors,orchestration,processors}/`
- **Imports**: Drop `src.` prefix → `from phoenix_real_estate.foundation...`
- **Principles**: TDD first, SOLID, Clean Architecture

## Key Technical Patterns

### Pydantic v2
- `@field_validator` with `@classmethod`
- `model_dump()` not `dict()`
- `datetime.now(UTC)` not `datetime.utcnow()`

### MongoDB Atlas
- 10 connection pool limit
- Graceful index creation
- Motor async driver

### Testing
- TDD: Write tests first, then implement
- Fixtures in conftest.py
- `pytest-asyncio` for async tests

## Task Completion Patterns

### Parallelization Success
- **Spawn/Wave**: 60-95% time reduction
- **Sub-agents**: Independent streams, zero conflicts
- **Strategy**: Split by domain (tests, docs, integration)

### Common Gotchas
- **RateLimiter**: `wait_if_needed()` not `acquire()`
- **Playwright**: Timeout in ms, tests expect seconds
- **Config**: `get_typed()` for type safety
- **Async Tests**: ±10% timing tolerance

## Implementation Status
✅ **Complete**: Foundation, Database, Config, Maricopa Client, Phoenix MLS Scraper
🔄 **Next**: Integration testing, selector updates, production deployment