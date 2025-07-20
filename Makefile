.PHONY: install dev-install test lint format type-check quality

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
