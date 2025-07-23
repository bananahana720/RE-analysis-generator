# Phoenix Real Estate Data Collector - Claude Guide

## PROJECT STATUS
- **Purpose**: Phoenix, AZ real estate data (zips: 85031, 85033, 85035)
- **Ready**: 40% operational - needs MongoDB start + API keys
- **Budget**: $25/mo max (current: ~$1/mo)
- **Package**: phoenix_real_estate (not src)

## CRITICAL RULES
✅ Use existing files/components ALWAYS
✅ Windows paths with backslashes
✅ Test BEFORE implementation
❌ No new files without checking reuse
❌ No ignoring project structure

## QUICK COMMANDS
```bash
# Start MongoDB (Administrator)
net start MongoDB

# Test services
python scripts/testing/test_mongodb_connection.py
python scripts/testing/test_webshare_proxy.py  # New!
python scripts/setup/check_setup_status.py

# Run data collection
python src/main.py --source maricopa --limit 5
```

## KEY FILES & PATHS
- **Config**: `.env` (from .env.sample), `config/proxies.yaml`
- **Main Package**: `src/phoenix_real_estate/`
- **Tests**: `tests/` (pytest with asyncio)
- **Scripts**: `scripts/testing/`, `scripts/setup/`

## CURRENT BLOCKERS & FIXES
1. **MongoDB not running** → `net start MongoDB` (as admin)
2. **Maricopa unauthorized** → Need API key from mcassessor.maricopa.gov
3. **WebShare auth failing** → Use `Authorization: Token YOUR_API_KEY`
4. **2captcha working** → $10 balance ready

## ARCHITECTURE NOTES
- MongoDB: localhost:27017, DB: phoenix_real_estate
- Services: 2captcha (✓), WebShare proxy (configured), Maricopa API (needs key)
- E2E tests created in `tests/e2e/`
- WebShare test script: `scripts/testing/test_webshare_proxy.py`

## BEFORE COMMITS
```bash
uv run ruff check . --fix
make security-check
uv run pytest tests/
```