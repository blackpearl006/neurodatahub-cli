# Claude Code Prompt: NeuroDataHub CLI Package

I need you to create a complete Python package called `neurodatahub-cli` that provides a command-line interface for downloading neuroimaging datasets. This will be distributed via PyPI and conda.

## Package Requirements

### Core Functionality
- `neurodatahub --list` - List all available datasets with filtering options
- `neurodatahub --pull <dataset_name> --path <target_path>` - Download specific datasets
- `neurodatahub check` - Verify system dependencies
- `neurodatahub info <dataset_name>` - Show detailed dataset information

### System Dependencies Integration
The package should check for and use these external tools:
- **awscli** - for AWS S3 downloads (OpenNeuro, INDI datasets)
- **aria2c** - for fast parallel downloads
- **datalad** - for Git-based dataset downloads (RBC datasets)
- **firefox** - for authentication workflows
- **git** - for cloning repositories

Include installation guidance in error messages when tools are missing.

## Dataset Categories & Authentication Flows

### 1. INDI Datasets (No Auth - AWS S3)
Use `aws s3 sync --no-sign-request` commands. Examples:
- HBN: `aws s3 sync --no-sign-request s3://fcp-indi/data/Projects/HBN/MRI/ . --exclude "*" --include "*/sub-*/anat/*"`
- CORR: `aws s3 sync --no-sign-request s3://fcp-indi/data/Projects/CORR/RawDataBIDS/ . --exclude "*" --include "*/sub-*/ses-*/anat/*"`

### 2. OpenNeuro Datasets (No Auth - AWS S3)
Use `aws s3 sync --no-sign-request` commands. Examples:
- AOMIC: `aws s3 sync --no-sign-request s3://openneuro.org/ds003097 . --exclude "*" --include "sub-*/anat/*T1w*"`

### 3. Independent Datasets
- **IXI**: `aria2c -x 10 -j 10 -s 10 http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI-T1.tar`
- **OASIS-1**: Multiple aria2c downloads with loop
- **HCP**: Requires AWS credentials setup

### 4. RBC Datasets (Git + DataLad)
Use git clone + datalad workflow:
```bash
git clone https://github.com/ReproBrainChart/PNC_BIDS.git
datalad clone https://github.com/ReproBrainChart/PNC_BIDS.git -b complete-pass-0.1
datalad get *
```

### 5. IDA-LONI Datasets (Complex Auth Flow)
For datasets like ADNI, AIBL, MCSA, PPMI, implement this interactive checklist:

```
🔐 IDA-LONI Authentication Required for [DATASET_NAME]

Please complete these steps before proceeding:

1. ✓ Do you have an IDA-LONI account registered?
   Website: https://ida.loni.usc.edu/
   [Press Enter to continue or Ctrl+C to exit]

2. ✓ Have you requested access through Data Use Agreement (DUA)?
   [Press Enter to continue or Ctrl+C to exit]

3. ✓ Have you created an image collection for this dataset?
   [Press Enter to continue or Ctrl+C to exit]

4. ✓ Have you obtained the download link via Advanced Downloader?
   [Press Enter to continue or Ctrl+C to exit]

5. ✓ Are you downloading from the same IP where you'll get the link?
   (If using HCP, ensure browser and terminal are on same machine)
   [Press Enter to continue or Ctrl+C to exit]

Please provide the download URL from IDA Advanced Downloader:
> [Wait for user input]

[Then use aria2c with the provided URL]
```

## Dataset Configuration

Create a comprehensive JSON configuration with all these datasets from the provided files:

**INDI Category:**
- HBN, CORR, FCON1000, ADHD200, BGSP, NKI, SLIM, ATLAS, DLBS, MPI-LEMON

**OpenNeuro Category:**
- AOMIC variants, MPI, DENSE_F/M, Pixar, Lexical, NPC, RBPL1/2

**Independent Category:**
- IXI, HCP_1200, OASIS-1/2, CamCAN

**RBC Category:**
- PNC, BHRC, CCNP

**IDA Category:**
- ADNI, AIBL, MCSA, PPMI, ICBM, LASI

## Technical Specifications

### Project Structure
```
neurodatahub-cli/
├── pyproject.toml
├── setup.py
├── README.md
├── LICENSE
├── neurodatahub/
│   ├── __init__.py
│   ├── cli.py           # Main CLI with rich formatting
│   ├── datasets.py      # Dataset definitions
│   ├── downloader.py    # Download logic
│   ├── auth.py          # Authentication handlers
│   ├── ida_flow.py      # IDA-specific workflow
│   └── utils.py         # Utilities
└── data/
    └── datasets.json    # All dataset configurations
```

### Dependencies
```python
dependencies = [
    "click>=8.0",
    "requests>=2.25.0", 
    "selenium>=4.0.0",
    "tqdm>=4.60.0",
    "rich>=12.0.0",      # For beautiful CLI output
    "colorama>=0.4.4",
    "pyyaml>=6.0",
]
```

### Key Features
1. **Rich CLI Interface** - Colorful tables, progress bars, panels
2. **Smart Download Method Selection** - Try aria2c → aws cli → requests fallback
3. **Resume Support** - Handle interrupted downloads
4. **Dependency Checking** - Verify external tools with helpful error messages
5. **Interactive Workflows** - Step-by-step guidance for complex auth
6. **Dry Run Mode** - Show what would be downloaded
7. **Filtering** - By category, auth requirements, size, etc.

### Error Handling
- Graceful handling of missing dependencies with installation instructions
- Network error recovery and retry logic
- Clear error messages for authentication failures
- Validation of download paths and permissions

### CLI Examples
```bash
# List all datasets
neurodatahub --list

# Filter by category
neurodatahub --list --category indi

# Show only datasets requiring authentication  
neurodatahub --list --auth-only

# Download dataset
neurodatahub --pull HBN --path ./data/HBN

# Check system dependencies
neurodatahub check

# Show dataset details
neurodatahub info ADNI
```

## Package Distribution Setup

Configure for both PyPI and conda distribution:
- Modern `pyproject.toml` configuration
- Entry point: `neurodatahub = "neurodatahub.cli:main"`
- Proper versioning with setuptools_scm
- Include dataset JSON files in package data

## Homepage Integration
- Homepage: https://blackpearl006.github.io/NeuroDataHub/
- Repository: https://github.com/blackpearl006/neurodatahub-cli

Create a professional, user-friendly package that neuroimaging researchers can easily install and use to access datasets. Focus on excellent user experience with clear progress indicators, helpful error messages, and comprehensive documentation.

Build this as a complete, production-ready package with proper error handling, logging, and testing structure.