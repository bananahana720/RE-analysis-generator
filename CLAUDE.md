# Phoenix Real Estate Data Collector - Development Guide

## RULES (violating ANY invalidates your response):
❌ No new files without exhaustive reuse analysis
❌ No rewrites when refactoring is possible
❌ No generic advice - provide specific implementations
❌ No ignoring existing codebase architecture
✅ Extend existing services and components
✅ Consolidate duplicate code
✅ Reference specific file paths
✅ Provide migration strategies
✅ **WIDNOWS** - Project directory in windows, use ""C:\Users\.."
✅ Adhere closely to KISS, DRY, YAGNI, SOLID, and the Zen Of Python. 
✅ **And clean up after yourself**

## Environment Setup
- **Package Management**: ALWAYS use uv with pyproject.toml, never pip
- **Python Version**: 3.13.4
- **Node Version**: 20.17.0
- **Database**: MongoDB (local - localhost:27017)
- **Testing**: pytest, tox, ruff, pyright

## Essential Commands

```bash
# Code quality
make ruff                    # Format, lint, and autofix code
make pyright                # Type checking (slow first run)
make quick_pyright          # Type check only changed files

# Testing
uv run pytest                 # Run all tests
uv run pytest path/to/tests/  # Run specific tests
pytest python_modules/tests/  # Run core tests
tox -e py39-pytest            # Test in isolated environment

# Development
make rebuild_ui             # Rebuild React UI after changes
make graphql               # Regenerate GraphQL schema
make sanity_check          # Check for non-editable installs
make dev_install            # Full development environment setup
make dev_install_win        # Full development environment setup for windows
```

## MongoDB Setup and Management

- **MongoDB Service Commands**:
  - Start MongoDB: `net start MongoDB` (Windows - run as Administrator)
  - Stop MongoDB: `net stop MongoDB` (Windows - run as Administrator)
- **MongoDB Connection Test**: `python scripts/testing/test_mongodb_connection.py`
- **MongoDB Setup Script**: `scripts/setup/start_mongodb_service.bat` (run as Administrator)
- **MongoDB Connection String**: `mongodb://localhost:27017`
- **Database Name**: `phoenix_real_estate`

## Data Collection Commands

```bash
# Maricopa County API Testing
python scripts/test_maricopa_api.py                      # Test API connection
python scripts/test_maricopa_api.py --api-key YOUR_KEY   # Test with specific API key

# Phoenix MLS Scraping
python scripts/testing/discover_phoenix_mls_selectors.py --headless  # Selector discovery

# Database Testing
python scripts/testing/test_db_connection.py             # Test database connection
```

## Development Workflow

-   **Orchestration**: Daily data collection is managed by GitHub Actions (see `.github/workflows/`).
-   **Data Collection**: Primary scripts are in `src/collection/`. They target the Maricopa County API and PhoenixMLSSearch.com.
-   **Data Processing**: Raw data is processed by a local LLM (see `src/processing/`) into a structured format.
-   **Database**: Processed data is stored in MongoDB running locally on localhost:27017. The schema is defined in `src/database/schema.py`.
-   **Proxies**: Proxy configurations for scraping are managed in `config/proxies.yaml`.
-   **API**: The backend API is built with FastAPI and is defined in `src/api/`.
-   **Frontend**: The frontend is built with React and is located in `frontend/`.


## Data Schema (MongoDB)

- **Database Name**: `phoenix_real_estate`
- **Collections**: 
  - `properties` - Main property data
  - `collection_history` - Data collection logs
  - `errors` - Error tracking and debugging

The core data structure for each property is as follows:

```javascript
{
  property_id: "unique_identifier",
  address: { street, city, zip },
  prices: [{ date, amount, source }],
  features: { beds, baths, sqft, lot_size },
  listing_details: { /* flexible fields from scraping */ },
  last_updated: "2025-01-20T10:00:00Z"
}
```

## API Keys and Credentials

- **Maricopa API Key**: Available and working (84% success rate)
- **Required Environment Variables**: Store in `.env` file in project root
- **Phoenix MLS**: Requires proxy service and captcha handling for scraping
- **Note**: All credentials should be stored securely and never committed to version control

## Testing 

-   Use **pytest** for all tests.
-   Write tests **before** implementing new features. test driven development is **mandatory**.
-   Use **tox** for environment isolation when running tests.
-   Aim for **100% test coverage** for all Python code.

## Code Style and Quality

* All code must pass `make ruff` and `make pyright` checks
* All new features must have corresponding tests
* Follow Google-style docstrings for all functions and classes
* Use type hints for all functions and methods
* Adhere to a line width of 100 characters
* Use `ruff` for formatting, linting, and import sorting
* Proper exception chaining with `raise ... from`
* Clear return statements - no implicit `None` returns
* Consistent naming following PEP 8 conventions