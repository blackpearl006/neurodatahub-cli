# PyPI Upload Guide for neurodatahub-cli

## Overview
The package has been fixed to properly include the `datasets.json` configuration file. All 35 neuroimaging datasets will now be available after installation from PyPI.

## Fixed Issues
- ✅ Moved `datasets.json` to `neurodatahub/data/datasets.json`
- ✅ Updated `pyproject.toml` to use `find_packages`
- ✅ Created `MANIFEST.in` to ensure all necessary files are included
- ✅ Added `__init__.py` to `neurodatahub/data/` directory
- ✅ Tested local installation - all functionality works correctly

## Upload Steps

### 1. Clean and Build Package
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build new distribution
python -m build --wheel --sdist
```

### 2. Verify Package Contents (Optional)
```bash
# Check what's included in the wheel
python -m zipfile -l dist/neurodatahub_cli-*.whl | grep datasets.json
# Should show: neurodatahub/data/datasets.json
```

### 3. Upload to PyPI
```bash
# Upload using your API token
twine upload dist/* --username __token__ --password your_pypi_api_token_here

# Or if you have .pypirc configured:
twine upload dist/*
```

## Post-Upload Verification

### 1. Test Installation in Fresh Environment
```bash
# Create clean virtual environment
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
# or: test_env\Scripts\activate  # Windows

# Install from PyPI
pip install neurodatahub-cli

# Test functionality
neurodatahub --version
neurodatahub --list
neurodatahub info HBN
```

### 2. Expected Results
- `neurodatahub --list` should show all 35 datasets
- No error about "Could not find datasets.json configuration file"
- All CLI commands should work correctly

## Package Structure Now Includes
```
neurodatahub-cli/
├── neurodatahub/
│   ├── __init__.py
│   ├── cli.py
│   ├── datasets.py
│   ├── downloader.py
│   ├── utils.py
│   ├── ... (other modules)
│   └── data/
│       ├── __init__.py
│       └── datasets.json  ← Now properly included!
├── pyproject.toml
├── MANIFEST.in
└── README.md
```

## Configuration Files Updated

### pyproject.toml
- Changed to use `packages = {find = {}}` for automatic package discovery
- Includes `neurodatahub/data/datasets.json` via package-data

### MANIFEST.in
- Ensures all necessary files are included in source distribution
- Includes README, LICENSE, and data files

## Version Information
Current version: `0.0.post5+dirty` (development)
- The version is automatically managed by setuptools_scm
- It will generate a proper version number for PyPI upload

## Troubleshooting

### If Upload Fails
1. Check your PyPI API token is correct
2. Ensure package name is available (may need to use different name)
3. Verify all required fields in pyproject.toml are filled

### If Installation Still Has Issues
1. Check the wheel contents: `python -m zipfile -l dist/*.whl`
2. Verify `neurodatahub/data/datasets.json` is listed
3. Test with a completely fresh Python environment

## Success Indicators
✅ Build completes without errors  
✅ `datasets.json` is included in wheel file  
✅ Local installation test passes  
✅ `neurodatahub --list` shows all datasets  
✅ No "Could not find datasets.json" errors  

The package is now ready for PyPI upload with full functionality preserved!