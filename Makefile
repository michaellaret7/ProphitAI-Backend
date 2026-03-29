.PHONY: sync dev test lint format typecheck clean

sync:
	uv sync --no-editable

dev:
	uv run uvicorn prophitai_api.app:app --reload --reload-dir packages --reload-dir projects --reload-dir infra --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
