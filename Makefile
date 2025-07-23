.PHONY: install dev-install test lint format type-check quality benchmark benchmark-quick setup-mongodb test-mongodb validate-mongodb

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
	@uv pip list  < /dev/null |  grep -E "phoenix-real-estate|src" || echo "All clear\!"

benchmark:
	@echo "Running comprehensive configuration benchmarks..."
	uv run python run_benchmarks.py

benchmark-quick:
	@echo "Running quick performance tests..."
	uv run pytest tests/foundation/config/test_performance.py -m benchmark -v

setup-mongodb:
	@echo "Setting up MongoDB Atlas configuration..."
	python scripts/setup_mongodb_atlas.py

test-mongodb:
	@echo "Testing MongoDB Atlas connection..."
	python scripts/test_db_connection.py

validate-mongodb:
	@echo "Running full MongoDB Atlas validation..."
	python scripts/validate_mongodb_atlas.py
