.PHONY: help venv install install-dev lint format typecheck test test-fast build clean cache-clean

PYTHON ?= python
VENV ?= .venv

help:
	@echo "Common targets:"
	@echo "  make venv         Create virtualenv"
	@echo "  make install      Install runtime deps"
	@echo "  make install-dev  Install dev deps"
	@echo "  make lint         Run ruff lint"
	@echo "  make format       Run ruff format"
	@echo "  make typecheck    Run mypy"
	@echo "  make test         Run pytest"
	@echo "  make build        Build executable with PyInstaller"
	@echo "  make clean        Remove build outputs"
	@echo "  make cache-clean  Remove cache artifacts"

venv:
	$(PYTHON) -m venv $(VENV)

install:
	$(VENV)/bin/pip install -r requirements.txt

install-dev:
	$(VENV)/bin/pip install -e ".[dev]"

lint:
	$(VENV)/bin/ruff check .

format:
	$(VENV)/bin/ruff format .

typecheck:
	$(VENV)/bin/mypy src

test:
	$(VENV)/bin/pytest

build:
	$(VENV)/bin/pyinstaller --onefile --name Translator run_translator.py

clean:
	rm -rf build dist __pycache__ .pytest_cache .ruff_cache

cache-clean:
	rm -rf translation_cache.db translation_cache
