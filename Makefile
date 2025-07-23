.PHONY: install dev-install test lint format type-check quality benchmark benchmark-quick setup-mongodb test-mongodb validate-mongodb start-mongodb-win stop-mongodb-win mongodb-status-win security-check

install:
	uv sync

dev-install:
	uv sync --extra dev --extra collection --extra processing

dev_install_win:
	uv sync --extra dev --extra collection --extra processing

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

type-check:
	uv run mypy src/

quality: format lint type-check test

ruff:
	uv run ruff check . --fix
	uv run ruff format .

pyright:
	uv run pyright

quick_pyright:
	uv run pyright --stats

sanity_check:
	@echo "Checking for non-editable installs..."
	@uv pip list | findstr /R "phoenix-real-estate src" || echo "All clear!"

benchmark:
	@echo "Running comprehensive configuration benchmarks..."
	uv run python run_benchmarks.py

benchmark-quick:
	@echo "Running quick performance tests..."
	uv run pytest tests/foundation/config/test_performance.py -m benchmark -v

setup-mongodb:
	@echo "Setting up local MongoDB configuration..."
	python scripts/setup/setup_mongodb_local.py

test-mongodb:
	@echo "Testing local MongoDB connection..."
	python scripts/testing/test_mongodb_connection.py

validate-mongodb:
	@echo "Running full local MongoDB validation..."
	python scripts/testing/validate_mongodb_local.py

# Windows-specific MongoDB service management
start-mongodb-win:
	@echo "Starting MongoDB service on Windows..."
	@net start MongoDB || echo "MongoDB service may already be running or requires Administrator privileges"

stop-mongodb-win:
	@echo "Stopping MongoDB service on Windows..."
	@net stop MongoDB || echo "MongoDB service may not be running or requires Administrator privileges"

mongodb-status-win:
	@echo "Checking MongoDB service status..."
	@sc query MongoDB || echo "MongoDB service not found"

# Security validation for pre-commit
security-check:
	@echo "Running security checks..."
	@echo "Checking for hardcoded credentials..."
	@findstr /S /I "api_key password token secret" src\*.py config\*.yaml config\*.yml || echo "No hardcoded credentials found"
	@echo "Checking for sensitive data in commits..."
	@git diff --cached --name-only | findstr /R "\.env$ \.key$ \.pem$ secrets" && echo "WARNING: Sensitive files detected!" || echo "No sensitive files in staging"
	@echo "Running dependency vulnerability scan..."
	@uv pip audit || echo "Consider running 'uv pip install pip-audit' for vulnerability scanning"
	@echo "Security check complete!"
