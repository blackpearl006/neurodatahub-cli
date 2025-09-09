.PHONY: help install test lint format clean build upload docs

help:
	@echo "NeuroDataHub CLI - Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  install       - Install development dependencies"
	@echo "  setup-dev     - Complete development environment setup"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-fast     - Run tests without slow ones"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          - Run all linting checks"
	@echo "  format        - Auto-format code"
	@echo "  typecheck     - Run type checking"
	@echo "  security      - Run security checks"
	@echo ""
	@echo "Validation:"
	@echo "  validate-config  - Validate datasets configuration"
	@echo "  validate-docs    - Check documentation"
	@echo ""
	@echo "Build & Release:"
	@echo "  clean         - Clean build artifacts"
	@echo "  build         - Build package"
	@echo "  upload-test   - Upload to Test PyPI"
	@echo "  upload        - Upload to PyPI"
	@echo ""
	@echo "Documentation:"
	@echo "  docs          - Build documentation"
	@echo "  docs-serve    - Serve documentation locally"

# Setup
install:
	python -m pip install -e .[dev]

setup-dev:
	python scripts/setup_dev.py

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-coverage:
	pytest --cov=neurodatahub --cov-report=html --cov-report=term-missing

test-fast:
	pytest -m "not slow"

# Code Quality
lint:
	@echo "🔍 Running flake8..."
	flake8 neurodatahub tests scripts
	@echo "🔍 Running mypy..."
	mypy neurodatahub
	@echo "🔍 Checking black formatting..."
	black --check neurodatahub tests scripts
	@echo "🔍 Checking isort..."
	isort --check-only neurodatahub tests scripts
	@echo "✅ All linting checks passed!"

format:
	@echo "🎨 Formatting with black..."
	black neurodatahub tests scripts
	@echo "🎨 Sorting imports with isort..."
	isort neurodatahub tests scripts
	@echo "✅ Code formatted!"

typecheck:
	mypy neurodatahub

security:
	@echo "🔒 Running security checks..."
	python -m pip install bandit
	bandit -r neurodatahub/
	@echo "✅ Security checks passed!"

# Validation
validate-config:
	@echo "🔍 Validating datasets configuration..."
	@python -c "from neurodatahub.validation import validate_datasets_config; from pathlib import Path; valid, issues = validate_datasets_config(Path('data/datasets.json')); print('✅ Config valid' if valid else '❌ Config issues found:'); [print(f'  • {issue}') for issue in issues]; exit(0 if valid else 1)"

validate-docs:
	@echo "📚 Validating documentation..."
	@python -c "import os; missing = [f for f in ['README.md', 'CONTRIBUTING.md', 'docs/QUICK_START.md'] if not os.path.exists(f)]; print('✅ All docs present' if not missing else f'❌ Missing docs: {missing}'); exit(0 if not missing else 1)"

# Build & Release
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "✅ Clean complete!"

build: clean lint test
	@echo "📦 Building package..."
	python -m build
	@echo "✅ Package built successfully!"

upload-test: build
	@echo "📤 Uploading to Test PyPI..."
	python -m twine check dist/*
	python -m twine upload --repository testpypi dist/*
	@echo "✅ Uploaded to Test PyPI!"

upload: build
	@echo "📤 Uploading to PyPI..."
	python -m twine check dist/*
	python -m twine upload dist/*
	@echo "✅ Uploaded to PyPI!"

# Development helpers
check-deps:
	@echo "🔍 Checking for outdated dependencies..."
	python -m pip list --outdated

install-deps:
	@echo "📦 Installing/updating dependencies..."
	python -m pip install --upgrade pip setuptools wheel build twine

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# CLI Testing
test-cli:
	@echo "🧪 Testing CLI commands..."
	neurodatahub --version
	neurodatahub check
	neurodatahub --list | head -20
	@echo "✅ CLI tests passed!"

# Performance testing
benchmark:
	@echo "⚡ Running performance benchmarks..."
	python -m pytest tests/ -m "performance" -v
	@echo "✅ Benchmarks complete!"

# Full CI simulation
ci: clean install lint test validate-config build
	@echo "✅ CI simulation completed successfully!"

# Development workflow
dev-setup: setup-dev pre-commit-install
	@echo "✅ Development environment ready!"

dev-check: lint test validate-config
	@echo "✅ Development checks passed!"

# Quick commands for daily development
quick-test:
	pytest tests/unit/ -x -v

quick-lint:
	black neurodatahub tests --check
	flake8 neurodatahub tests