# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NeuroDataHub CLI is a command-line tool for downloading 39 neuroimaging datasets from multiple sources (INDI, OpenNeuro, ReproBrainChart, IDA-LONI, etc.) AND distributing 10 brain atlases for network analysis. It handles diverse authentication workflows, supports multiple download backends (AWS CLI, aria2c, DataLad), and provides a rich user experience with progress tracking.

**Key stats:**
- Package name: `neurodatahub-cli`
- Python versions: 3.8+
- Entry point: `neurodatahub.cli:main`
- Current version: 1.0.3 (tracked in `pyproject.toml`)
- Datasets: 39 (87.2% with metadata)
- Brain Atlases: 10 (from BrainGraph R package)

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=neurodatahub --cov-report=html

# Quick unit test run (development)
make quick-test
```

### Code Quality
```bash
# Run all linting checks (flake8, mypy, black, isort)
make lint

# Auto-format code
make format

# Type checking only
make typecheck
mypy neurodatahub

# Security checks
make security
```

### Building and Publishing
```bash
# Build package (runs lint + test + build)
make build

# Validate datasets configuration
make validate-config

# Upload to Test PyPI
make upload-test

# Upload to production PyPI
make upload
```

### Development Setup
```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Or use the Makefile
make install

# Setup pre-commit hooks
make pre-commit-install
```

### CLI Testing
```bash
# Test CLI commands manually
neurodatahub --version
neurodatahub check
neurodatahub --list
neurodatahub info HBN
```

## Architecture

### Core Design Pattern: Manager-Based Architecture

The codebase uses a manager pattern with global singleton instances for different concerns:

1. **DatasetManager** (`neurodatahub/datasets.py`) - Manages dataset metadata and search
   - Loads dataset configurations from `neurodatahub/data/datasets.json`
   - Provides filtering, searching, and display functionality
   - Global instance: `dataset_manager`

2. **DownloadManager** (`neurodatahub/downloader.py`) - Handles dataset downloads
   - Implements downloader classes for different backends (AWS S3, aria2c, DataLad, requests)
   - Each downloader inherits from `BaseDownloader` with `prepare()` and `download()` methods
   - Global instance: `download_manager`

3. **AuthManager** (`neurodatahub/auth.py`) - Manages authentication workflows
   - Implements authenticator classes for different auth types (AWS, manual, Selenium-based)
   - Each authenticator inherits from `BaseAuthenticator`
   - Global instance: `auth_manager`

4. **IDALONIWorkflow** (`neurodatahub/ida_flow.py`) - Special interactive workflow for IDA-LONI datasets
   - Implements checklist-based authentication guidance
   - Handles IP-restricted download links

### Key Architecture Patterns

**Dataset Configuration File Path Resolution:**
The DatasetManager tries multiple paths to find `datasets.json` (development, installed package, current directory):
```python
possible_paths = [
    Path(__file__).parent.parent / "data" / "datasets.json",  # Development
    Path(__file__).parent / "data" / "datasets.json",         # Installed package
    Path("data") / "datasets.json"                            # Current directory
]
```

**Downloader Selection:**
The DownloadManager maps download methods to downloader classes:
```python
self.downloaders = {
    'aws_s3': AwsS3Downloader,
    'aws_credentials': AwsS3Downloader,
    'aria2c': Aria2cDownloader,
    'datalad': DataladDownloader,
}
```

**CLI Command Structure:**
The CLI (`neurodatahub/cli.py`) uses Click with a main group that supports both legacy flags (`--list`, `--pull`) and modern subcommands (`list`, `pull`, `info`, etc.).

### Dataset Configuration Schema

Located in `neurodatahub/data/datasets.json`, each dataset entry includes:
- `name`: Full dataset name
- `category`: indi, openneuro, independent, rbc, or ida
- `description`: Dataset description
- `size`: Approximate size (e.g., "~2TB")
- `auth_required`: Boolean
- `download_method`: aws_s3, aws_credentials, aria2c, datalad, or ida_loni
- `base_command`: The actual download command template
- `website`: Dataset homepage
- `publication`: DOI or publication link (optional)

## Important Implementation Details

### Package Data Inclusion

The `datasets.json` file must be included in the package. This is configured in `pyproject.toml`:
```toml
[tool.setuptools.package-data]
neurodatahub = ["data/*.json"]
```

And the file is located at: `neurodatahub/data/datasets.json` (note: NOT in the root `data/` directory).

### Download Method Implementations

**AWS S3 Downloads:**
- Replace placeholder ` .` in base_command with actual target path
- Support `--no-sign-request` for public datasets
- Check AWS credentials for private datasets

**Aria2c Downloads:**
- Some datasets use special handling (e.g., OASIS with multiple files)
- Check for `base_command == "multiple_aria2c_downloads"` pattern

**DataLad Downloads:**
- Change to target directory before executing commands
- Parse multiple commands from `base_command` (split by ` && `)
- Restore original working directory after completion

### IDA-LONI Workflow

IDA-LONI datasets (ADNI, PPMI, AIBL, MCSA) require a special interactive checklist workflow:
1. Verify IDA-LONI account registration
2. Check Data Use Agreement (DUA) approval
3. Confirm image collection creation
4. Obtain Advanced Downloader link
5. Verify same IP for link generation and download

This workflow is implemented in `neurodatahub/ida_flow.py` and called from `cli.py` when `download_method == 'ida_loni'`.

### Testing Infrastructure

**Test Structure:**
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - End-to-end workflow tests
- `tests/conftest.py` - Shared fixtures and mocks

**Key Test Fixtures:**
- `cli_runner` - Click CLI testing
- `temp_dir` - Temporary directory for file operations
- `mock_datasets_config` - Sample dataset configuration
- `MockDatasetManager` - Complete mock implementation of DatasetManager
- `mock_dependency_check`, `mock_run_command` - Mock external dependencies

### Validation

The project includes a validation module (`neurodatahub/validation.py`) to check datasets.json integrity. Run it with:
```bash
make validate-config
```

## Common Development Workflows

### Adding a New Dataset

1. Edit `neurodatahub/data/datasets.json`
2. Add the dataset entry with all required fields
3. Run validation: `make validate-config`
4. Add tests in `tests/unit/test_datasets.py`
5. Test manually: `neurodatahub info DATASET_ID`

### Adding a New Download Method

1. Create a new downloader class in `neurodatahub/downloader.py`
2. Inherit from `BaseDownloader`
3. Implement `prepare()` (check dependencies) and `download()` methods
4. Register in `DownloadManager.downloaders` dictionary
5. Add tests in `tests/unit/test_downloader.py`

### Adding a New Authentication Method

1. Create authenticator class in `neurodatahub/auth.py`
2. Inherit from `BaseAuthenticator`
3. Implement `authenticate()` and `is_authenticated()` methods
4. Register in `AuthManager.get_authenticator()` method
5. Add tests for the authentication flow

## Dependencies

**Runtime:**
- click (CLI framework)
- requests (HTTP downloads)
- selenium (interactive auth)
- tqdm (progress bars)
- rich (rich console output)
- colorama (cross-platform color)
- pyyaml (config files)

**Development:**
- pytest, pytest-cov (testing)
- black, isort (formatting)
- flake8, mypy (linting)
- pre-commit (git hooks)
- bandit (security)
- build, twine (packaging)

**Optional (performance):**
- psutil, aiohttp, aiofiles

**External tools checked at runtime:**
- `aws` (AWS CLI)
- `aria2c` (fast downloads)
- `datalad` (DataLad datasets)
- `git` (version control, DataLad)
- `firefox` (Selenium auth)

## Error Handling and User Experience

The project emphasizes helpful error messages:
- Missing dependencies show installation commands
- Failed downloads provide troubleshooting guidance
- Dry-run mode shows what would be executed
- Confirmation prompts prevent accidental large downloads

Use utility functions from `neurodatahub/utils.py`:
- `display_error()`, `display_warning()`, `display_info()`, `display_success()`
- `get_confirmation()`, `get_user_input()`
- `check_dependency()`, `run_command()`

## Brain Atlas Management

NeuroDataHub includes 10 curated brain atlases for network analysis:

### Available Atlases

1. **Anatomical** (4): AAL90, Destrieux, Destrieux_SCGM, DK82
2. **Functional** (4): Power264, Dosenbach160, Gordon333, Craddock200
3. **Multimodal** (1): HCP_MMP_Glasser_360
4. **Connectivity-based** (1): Brainnetome

### Atlas CLI Commands

```bash
# List all atlases
neurodatahub atlas list

# Filter by type
neurodatahub atlas list --type functional

# Filter by ROI count
neurodatahub atlas list --min-rois 200 --max-rois 300

# Show detailed information
neurodatahub atlas info HCP_MMP_GLASSER_360

# Download specific atlas
neurodatahub atlas download AAL90 --path ./my_atlases

# Download all atlases
neurodatahub atlas download-all --path ./all_atlases

# Show attribution
neurodatahub atlas attribution

# List atlas types
neurodatahub atlas types
```

### Atlas Data Structure

Atlases are stored in `neurodatahub/data/atlases/` and `data/atlases/`:
- CSV files with MNI coordinates and region metadata
- Columns: name, x.mni, y.mni, z.mni, lobe, hemi, index (+ additional metadata)
- Configuration in `atlases.json`

### Atlas Manager

The `AtlasManager` class (`neurodatahub/atlas.py`) provides:
- `list_atlases()` - Filter atlases by type, ROI count
- `get_atlas()` - Get atlas by ID
- `display_atlases_table()` - Rich table display
- `display_atlas_info()` - Detailed atlas information
- `copy_atlas()` - Copy atlas file to directory
- `copy_all_atlases()` - Copy all atlases

### Adding a New Atlas

1. Add CSV file to `neurodatahub/data/atlases/` and `data/atlases/`
2. Update `atlases.json` with atlas metadata:
   - name, num_rois, atlas_type, parcellation_type
   - description, suitable_for, age_range
   - reference, doi, columns
3. Test with `neurodatahub atlas list` and `info`

### Atlas Attribution

All atlases were obtained using the BrainGraph R package (Watson, 2024):
- Reference: Watson CG (2024). brainGraph: Graph Theory Analysis of Brain MRI Data
- DOI: 10.32614/CRAN.package.brainGraph
- NIfTI images to be added in future releases

## Release Process

1. Update version in `pyproject.toml`
2. Run full test suite: `make ci`
3. Build package: `make build`
4. Upload to PyPI: `make upload`

The package is also being prepared for conda-forge distribution (see `conda-recipe/` directory).
