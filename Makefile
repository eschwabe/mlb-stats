PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

.DEFAULT_GOAL := help

.PHONY: help venv install test lint format typecheck check

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

venv: ## Create .venv and install the package with dev extras
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install: ## Install the package into the current environment (editable)
	$(PYTHON) -m pip install -e ".[dev]"

test: ## Run the test suite
	$(PY) -m pytest

lint: ## Ruff check
	$(VENV)/bin/ruff check .

format: ## Ruff autofix + format
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

typecheck: ## Mypy (strict) on the package
	$(VENV)/bin/mypy mlb_stats

check: lint typecheck test ## Lint, type-check and test
