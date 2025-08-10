# Phoenix Real Estate - Quick Reference

## Environment
- **Python**: 3.13.4 (uv package manager, NOT pip)
- **Database**: MongoDB v8.1.2 (localhost:27017)
- **LLM**: Ollama with llama3.2:latest (2GB model)
- **Testing**: pytest (asyncio), ruff, pyright
- **CI/CD**: GitHub Actions

## Architecture Patterns
- **Structure**: refer to `@index.md` file to understand project structure and know ***WHERE*** to work. `index-detailed.md` for more details.
- **Imports**: Drop `src.` prefix → `from phoenix_real_estate.foundation...`
- **Principles**: TDD first, SOLID, Clean Architecture

## DEVELOPMENT RULES
✅ **ALWAYS** check for existing files/components before creating new ones
✅ Use Windows paths with backslashes
✅ Test-driven development - write tests FIRST
✅ Type hints required for all functions
✅ Google-style docstrings mandatory
❌ No new files without exhaustive reuse analysis
❌ No rewrites when refactoring suffices
❌ No generic advice - provide specific implementations

**For Python projects specifically:**
* ZERO warnings from `ruff`, `mypy`, `flake8` (all checks enabled)
* No disabled linter rules without explicit justification
* No use of `Any` types or missing type hints
* No `# noqa` comments unless absolutely necessary with explanation
* Proper exception chaining with `raise ... from`
* Clear return statements - no implicit `None` returns
* Consistent naming following PEP 8 conventions

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
- **Spawn/Wave**: 60-95% time reduction for complex tasks
- **Sub-agents**: 8 parallel streams, zero conflicts, domain-specific expertise
- **Strategy**: Split by domain (tests, docs, integration, monitoring, performance)
- **Phoenix MLS**: 13 tasks completed in parallel → enterprise-ready scraper

### Advanced Implementation Lessons
- **Enterprise Features**: Session persistence + captcha handling + error recovery essential for production
- **Monitoring First**: Prometheus metrics from day 1, not afterthought
- **Test Quality**: 92.8% mutation score > coverage percentage alone
- **Error Patterns**: 21 site-specific patterns prevent 80% of scraping failures
- **Windows Compatibility**: Custom mutation testing needed for `mutmut` alternatives

### Production Readiness Lessons (Task 5)
- **Import Validation Critical**: Always verify `__init__.py` imports match `__all__` declarations
- **Systematic Troubleshooting**: Parallel sub-agent execution for critical issue resolution (5 agents, 4 hrs)
- **Test-Reality Gap**: Claims vs actual test results require independent validation
- **Project Organization**: Professional structure essential - organized root, reports/, tools/ directories
- **Quality Gates**: 8-step validation cycle prevents deployment of broken systems

### Common Gotchas  
- **RateLimiter**: `wait_if_needed()` not `acquire()`
- **Playwright**: Timeout in ms, tests expect seconds  
- **Config**: `get_typed()` for type safety
- **Async Tests**: ±10% timing tolerance
- **Captcha Integration**: 2captcha costs $1-3/1000 solves, budget accordingly
- **Proxy Health**: Monitor with 5min intervals, not request-by-request
- **Module Imports**: Broken `__init__.py` imports block all usage - verify with import tests
- **Code Quality**: Run ruff checks before deployment

## Implementation Status
✅ **Complete**: Foundation, Database, Config, Maricopa Client  
✅ **Production Ready**: Phoenix MLS Scraper (enterprise-grade, validated, organized)
✅ **Stabilized**: Critical issues resolved, database validated, environment confirmed
🔄 **Next**: Live deployment, performance optimization, multi-MLS expansion