#!/usr/bin/env python3
"""Development environment setup script for NeuroDataHub CLI."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True, shell=False):
    """Run a command and handle errors."""
    print(f"🔧 Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, check=check)
        else:
            result = subprocess.run(cmd, check=check)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0] if isinstance(cmd, list) else cmd}")
        return False


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print("✅ Python version OK")
    return True


def setup_git_hooks():
    """Set up git pre-commit hooks."""
    print("\n🪝 Setting up git hooks...")
    
    # Check if we're in a git repository
    if not Path('.git').exists():
        print("⚠️ Not in a git repository, skipping git hooks")
        return True
    
    # Install pre-commit
    if not run_command([sys.executable, '-m', 'pip', 'install', 'pre-commit']):
        print("❌ Failed to install pre-commit")
        return False
    
    # Install hooks
    if not run_command(['pre-commit', 'install']):
        print("❌ Failed to install pre-commit hooks")
        return False
    
    print("✅ Git hooks installed")
    return True


def install_dependencies():
    """Install development dependencies."""
    print("\n📦 Installing dependencies...")
    
    # Install package in development mode with dev dependencies
    if not run_command([sys.executable, '-m', 'pip', 'install', '-e', '.[dev]']):
        print("❌ Failed to install package dependencies")
        return False
    
    print("✅ Dependencies installed")
    return True


def create_config_files():
    """Create development configuration files."""
    print("\n⚙️ Creating configuration files...")
    
    # Create .pre-commit-config.yaml if it doesn't exist
    precommit_config = Path('.pre-commit-config.yaml')
    if not precommit_config.exists():
        config_content = """
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3
        args: [--line-length=88]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mypy-mirror
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
        args: [--ignore-missing-imports]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements
""".strip()
        
        with open(precommit_config, 'w') as f:
            f.write(config_content)
        print(f"   Created {precommit_config}")
    
    # Create pytest.ini if it doesn't exist
    pytest_config = Path('pytest.ini')
    if not pytest_config.exists():
        config_content = """
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --cov=neurodatahub
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
""".strip()
        
        with open(pytest_config, 'w') as f:
            f.write(config_content)
        print(f"   Created {pytest_config}")
    
    # Create Makefile for common tasks
    makefile = Path('Makefile')
    if not makefile.exists():
        content = """
.PHONY: help install test lint format clean build upload

help:
	@echo "Available targets:"
	@echo "  install  - Install development dependencies"
	@echo "  test     - Run tests"
	@echo "  lint     - Run linting checks"
	@echo "  format   - Format code"
	@echo "  clean    - Clean build artifacts"
	@echo "  build    - Build package"
	@echo "  upload   - Upload to PyPI (use upload-test for test PyPI)"

install:
	python -m pip install -e .[dev]

test:
	pytest

test-coverage:
	pytest --cov=neurodatahub --cov-report=html

lint:
	flake8 neurodatahub tests
	mypy neurodatahub
	black --check neurodatahub tests
	isort --check-only neurodatahub tests

format:
	black neurodatahub tests
	isort neurodatahub tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

build: clean
	python -m build

upload-test: build
	python -m twine upload --repository testpypi dist/*

upload: build
	python -m twine upload dist/*

validate-config:
	python -c "from neurodatahub.validation import validate_datasets_config; from pathlib import Path; valid, issues = validate_datasets_config(Path('data/datasets.json')); print('✅ Config valid' if valid else '❌ Config issues:'); [print(f'  {issue}') for issue in issues]"
""".strip()
        
        with open(makefile, 'w') as f:
            f.write(content)
        print(f"   Created {makefile}")
    
    print("✅ Configuration files created")
    return True


def run_initial_tests():
    """Run initial test suite to verify setup."""
    print("\n🧪 Running initial tests...")
    
    # Run a basic test to see if everything is working
    if not run_command([sys.executable, '-m', 'pytest', '--version']):
        print("❌ pytest not available")
        return False
    
    # Run quick syntax check
    if not run_command([sys.executable, '-c', 'import neurodatahub; print("Import OK")']):
        print("❌ Package import failed")
        return False
    
    # Run basic validation
    if Path('data/datasets.json').exists():
        validation_cmd = """
from neurodatahub.validation import validate_datasets_config
from pathlib import Path
valid, issues = validate_datasets_config(Path('data/datasets.json'))
print('✅ Config validation passed' if valid else f'❌ Config validation failed: {len(issues)} issues')
"""
        if not run_command([sys.executable, '-c', validation_cmd]):
            print("⚠️ Config validation had issues")
    
    print("✅ Initial tests passed")
    return True


def display_next_steps():
    """Display next steps for development."""
    print("\n" + "="*60)
    print("🎉 Development Environment Setup Complete!")
    print("="*60)
    print("\n📋 Next steps:")
    print("   1. Activate your virtual environment (if using one)")
    print("   2. Run tests: pytest")
    print("   3. Check code style: make lint")
    print("   4. Format code: make format")
    print("   5. Validate datasets config: make validate-config")
    print("\n🔧 Development commands:")
    print("   • make help        - Show all available commands")
    print("   • make test        - Run test suite")
    print("   • make lint        - Check code style")
    print("   • make format      - Auto-format code")
    print("   • pre-commit run --all-files  - Run all pre-commit hooks")
    print("\n📚 Useful files:")
    print("   • Makefile         - Common development tasks")
    print("   • pytest.ini       - Test configuration")
    print("   • .pre-commit-config.yaml  - Code quality hooks")
    print("\n🐛 If you encounter issues:")
    print("   • Check that you're using Python 3.8+")
    print("   • Make sure all dependencies installed: pip install -e .[dev]")
    print("   • Run tests to verify setup: pytest tests/")
    print("\n✨ Happy coding!")


def main():
    """Main setup function."""
    print("🚀 NeuroDataHub CLI Development Environment Setup")
    print("="*60)
    
    # Change to script directory
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    print(f"📁 Working directory: {script_dir.absolute()}")
    
    success = True
    
    # Check Python version
    success &= check_python_version()
    
    # Install dependencies
    success &= install_dependencies()
    
    # Create configuration files
    success &= create_config_files()
    
    # Setup git hooks
    success &= setup_git_hooks()
    
    # Run initial tests
    success &= run_initial_tests()
    
    if success:
        display_next_steps()
        sys.exit(0)
    else:
        print("\n❌ Setup encountered errors. Please fix the issues above and try again.")
        sys.exit(1)


if __name__ == '__main__':
    main()