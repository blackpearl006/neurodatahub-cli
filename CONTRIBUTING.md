# Contributing to NeuroDataHub CLI

Thank you for your interest in contributing to NeuroDataHub CLI! This guide will help you get started.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Git
- (Optional) conda for environment management

### Setup Instructions

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/neurodatahub-cli.git
   cd neurodatahub-cli
   ```

2. **Create Development Environment**
   ```bash
   # Using venv
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Or using conda
   conda create -n neurodatahub python=3.9
   conda activate neurodatahub
   ```

3. **Install in Development Mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify Installation**
   ```bash
   neurodatahub --version
   pytest tests/
   ```

## Development Workflow

### Code Style
We use the following tools to maintain code quality:

```bash
# Format code
black neurodatahub/
isort neurodatahub/

# Check style
flake8 neurodatahub/
mypy neurodatahub/

# Run all checks
make lint  # or manually run the above commands
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=neurodatahub --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run tests with different verbosity
pytest -v  # verbose
pytest -s  # show print statements
```

### Pre-commit Hooks
Install pre-commit hooks to automatically check code before commits:

```bash
pip install pre-commit
pre-commit install
```

## Types of Contributions

### 🐛 Bug Reports
When reporting bugs, please include:
- Python version and OS
- NeuroDataHub CLI version (`neurodatahub --version`)
- Complete error message and traceback
- Steps to reproduce the issue
- Expected vs actual behavior

**Template:**
```markdown
## Bug Description
Brief description of the bug.

## Environment
- OS: 
- Python version: 
- NeuroDataHub CLI version: 
- Dependencies: (output of `neurodatahub check`)

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Error Messages
```
Paste any error messages here
```

## Additional Context
Any other relevant information.
```

### ✨ Feature Requests
For feature requests, please include:
- Clear description of the feature
- Use case and motivation
- Possible implementation approach
- Any alternative solutions considered

### 📚 Documentation Improvements
- Fix typos or unclear explanations
- Add examples or tutorials
- Improve API documentation
- Update installation instructions

### 🔧 Code Contributions

#### Adding New Datasets
To add a new dataset to the collection:

1. **Update datasets.json**
   ```json
   {
     "NEW_DATASET": {
       "name": "Full Dataset Name",
       "category": "indi|openneuro|independent|rbc|ida",
       "description": "Brief description of the dataset",
       "size": "~XXX GB",
       "auth_required": true|false,
       "download_method": "aws_s3|aria2c|datalad|ida_loni",
       "base_command": "command to download",
       "website": "https://dataset-website.com",
       "publication": "https://doi.org/...",
       "additional_fields": "as needed"
     }
   }
   ```

2. **Add tests** in `tests/unit/test_datasets.py`

3. **Update documentation** if needed

#### Adding New Download Methods
1. Create a new downloader class in `neurodatahub/downloader.py`
2. Inherit from `BaseDownloader`
3. Implement required methods:
   ```python
   def prepare(self) -> bool:
       """Check dependencies and validate configuration."""
       
   def download(self, dry_run: bool = False) -> bool:
       """Execute the download."""
   ```

4. Register in `DownloadManager.downloaders`
5. Add comprehensive tests
6. Update documentation

#### Adding New Authentication Methods
1. Create authenticator class in `neurodatahub/auth.py`
2. Inherit from `BaseAuthenticator`
3. Implement required methods
4. Add to `AuthManager.authenticators`
5. Add tests and documentation

## Code Architecture

### Project Structure
```
neurodatahub-cli/
├── neurodatahub/          # Main package
│   ├── __init__.py        # Package initialization
│   ├── cli.py             # Click-based CLI interface
│   ├── datasets.py        # Dataset management
│   ├── downloader.py      # Download implementations
│   ├── auth.py            # Authentication handlers
│   ├── ida_flow.py        # IDA-LONI workflow
│   ├── utils.py           # Utility functions
│   ├── config.py          # Configuration management
│   ├── logging_config.py  # Logging setup
│   └── exceptions.py      # Custom exceptions
├── data/                  # Dataset configurations
│   └── datasets.json      # Dataset metadata
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # Test configuration
├── docs/                  # Documentation
│   ├── examples/          # Usage examples
│   └── tutorials/         # Tutorials
└── scripts/               # Development scripts
```

### Design Principles
1. **Modularity**: Each component has a single responsibility
2. **Extensibility**: Easy to add new datasets, downloaders, authenticators
3. **Error Handling**: Graceful failure with helpful error messages
4. **User Experience**: Clear progress indication and informative output
5. **Testing**: Comprehensive test coverage including edge cases

## Pull Request Process

### Before Submitting
1. **Create an Issue**: Discuss major changes first
2. **Branch Naming**: Use descriptive names like `feature/ida-resume-downloads` or `fix/config-validation`
3. **Commits**: Write clear commit messages following conventional commits
4. **Tests**: Ensure all tests pass and add new tests for your changes
5. **Documentation**: Update docs for user-facing changes

### PR Checklist
- [ ] Tests pass (`pytest`)
- [ ] Code style checks pass (`black`, `isort`, `flake8`, `mypy`)
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated (for notable changes)
- [ ] PR description explains the change and motivation
- [ ] Linked to related issues

### Example PR Template
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Related Issues
Closes #XXX

## Additional Notes
Any additional context or notes for reviewers.
```

## Release Process

### Versioning
We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Release Checklist
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. Tag release after merge
5. GitHub Actions will automatically publish to PyPI

## Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Email**: For security issues or private matters

### Development Questions
- Check existing issues and discussions
- Look at similar implementations in the codebase
- Run tests to understand expected behavior
- Ask specific questions in GitHub Discussions

## Recognition

Contributors will be:
- Listed in the README.md contributors section
- Mentioned in release notes for significant contributions
- Added to the `pyproject.toml` authors list (for major contributors)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code.

### Key Points
- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment
- Report unacceptable behavior

## Development Tips

### Local Testing
```bash
# Test CLI commands without installing
python -m neurodatahub.cli --list

# Test specific functions
python -c "from neurodatahub.datasets import DatasetManager; dm = DatasetManager(); print(len(dm.datasets))"

# Debug with pdb
python -m pdb -c continue -m neurodatahub.cli info HBN
```

### Working with Dependencies
```bash
# Check what tools are available
neurodatahub check

# Mock dependencies in tests
# See tests/conftest.py for examples
```

### Performance Testing
```bash
# Time operations
time neurodatahub --list

# Memory usage
python -m memory_profiler neurodatahub/cli.py --list

# Profile code
python -m cProfile -o profile.stats neurodatahub/cli.py --list
```

Thank you for contributing to NeuroDataHub CLI! 🧠✨