# Add neurodatahub-cli

## Description
This adds a conda-forge recipe for **neurodatahub-cli**, a comprehensive command-line interface for downloading neuroimaging datasets used in neuroscience research.

## Package Information
- **PyPI**: https://pypi.org/project/neurodatahub-cli/
- **Homepage**: https://blackpearl006.github.io/NeuroDataHub/
- **Repository**: https://github.com/blackpearl006/neurodatahub-cli  
- **License**: MIT
- **Version**: 1.0.0

## Features
- **Unified Access**: Provides access to 35+ curated neuroimaging datasets from multiple sources
- **Multiple Data Sources**: Supports INDI, OpenNeuro, IDA-LONI, and independent repositories
- **Rich CLI Interface**: Beautiful progress bars, tables, and user-friendly output using Rich
- **Authentication Support**: Handles various authentication methods including AWS credentials and interactive workflows
- **Download Management**: Resume support, integrity checking, and multiple download backends
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Dataset Sources Supported
- **INDI**: HBN, CORR, ADHD200, FCON1000, NKI, MPI-LEMON, etc.
- **OpenNeuro**: AOMIC variants, MPI, DENSE datasets, Pixar, Lexical, etc.
- **Independent**: IXI, HCP, OASIS, CamCAN
- **RBC**: PNC, BHRC, CCNP  
- **IDA-LONI**: ADNI, AIBL, MCSA, PPMI, ICBM, LASI

## Testing
- ✅ All imports work correctly (`neurodatahub`, `neurodatahub.cli`, etc.)
- ✅ CLI commands execute successfully (`--help`, `--version`, `check`, `--list`)
- ✅ Dataset configuration loads properly (35 datasets accessible)
- ✅ Cross-platform compatibility (noarch: python)
- ✅ Comprehensive test suite included

## Usage Examples
```bash
# List all available datasets
neurodatahub --list

# Check system dependencies  
neurodatahub check

# Get detailed information about a dataset
neurodatahub info HBN

# Download a dataset (dry-run)
neurodatahub pull IXI /path/to/download --dry-run

# Search for specific datasets
neurodatahub search "alzheimer"
```

## Technical Details
- **Build**: noarch python package (cross-platform)
- **Dependencies**: All dependencies available in conda-forge
- **Entry Point**: `neurodatahub = neurodatahub.cli:main`
- **Data Files**: Includes datasets.json configuration (35 datasets)
- **Python Support**: Python ≥3.8

## Quality Assurance
- ✅ Recipe follows conda-forge guidelines
- ✅ License file included in package
- ✅ Dependencies properly specified with versions
- ✅ Entry points configured correctly
- ✅ Test suite covers core functionality
- ✅ Package builds successfully locally
- ✅ SHA256 hash verified from PyPI source

## Benefits for Users
This package will enable researchers to easily access neuroimaging datasets through conda:
```bash
conda install -c conda-forge neurodatahub-cli
```

The tool significantly simplifies the process of obtaining research datasets that typically require complex authentication and download procedures.

## Checklist
- [x] License file included  
- [x] Dependencies properly specified
- [x] Entry points configured
- [x] Test suite covers core functionality  
- [x] Recipe follows conda-forge guidelines
- [x] Cross-platform compatibility ensured
- [x] Package tested locally