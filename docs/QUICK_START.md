# NeuroDataHub CLI - Quick Start Guide

Welcome to NeuroDataHub CLI! This guide will help you get up and running quickly.

## Installation

### Via pip (Recommended)
```bash
pip install neurodatahub-cli
```

### Via conda
```bash
conda install -c conda-forge neurodatahub-cli
```

### From source (Development)
```bash
git clone https://github.com/blackpearl006/neurodatahub-cli.git
cd neurodatahub-cli
pip install -e ".[dev]"
```

## First Steps

### 1. Check System Dependencies
Before downloading datasets, check what tools are available:

```bash
neurodatahub check
```

This will show you which dependencies are installed and provide installation guidance for missing ones.

### 2. Browse Available Datasets
See what datasets are available:

```bash
# List all datasets
neurodatahub --list

# List with detailed information
neurodatahub --list --detailed

# Filter by category
neurodatahub --list --category indi

# Show only datasets not requiring authentication
neurodatahub --list --no-auth-only
```

### 3. Get Dataset Information
Learn about a specific dataset:

```bash
neurodatahub info HBN
```

### 4. Download Your First Dataset
Let's download a small dataset that doesn't require authentication:

```bash
# Create a directory for your data
mkdir ~/neurodatahub_data

# Download the IXI dataset (small, ~12GB)
neurodatahub pull IXI ~/neurodatahub_data/IXI

# Or use the alternative syntax
neurodatahub --pull IXI --path ~/neurodatahub_data/IXI
```

### 5. Search for Datasets
Find datasets by keywords:

```bash
# Search for brain development datasets
neurodatahub search "development"

# Search for Alzheimer's datasets
neurodatahub search "alzheimer"
```

## Common Workflows

### Download Multiple Datasets
```bash
# Download several INDI datasets (no authentication required)
for dataset in HBN CORR ADHD200; do
    neurodatahub pull $dataset ~/neurodatahub_data/$dataset
done
```

### Preview Downloads (Dry Run)
Check what would be downloaded without actually downloading:

```bash
neurodatahub pull HBN ~/neurodatahub_data/HBN --dry-run
```

### Force Download (Skip Confirmations)
```bash
neurodatahub pull IXI ~/neurodatahub_data/IXI --force
```

## Dataset Categories

### 🔓 No Authentication Required

**INDI Datasets** - Ready to download immediately:
- `HBN` - Healthy Brain Network (2TB)
- `CORR` - Reliability and Reproducibility (500GB)
- `ADHD200` - ADHD diagnosis dataset (200GB)
- `NKI` - Nathan Kline Institute (800GB)

**OpenNeuro Datasets**:
- `AOMIC_PIOP1` - Amsterdam Open MRI Collection (180GB)
- `Pixar` - Movie watching fMRI (120GB)

**Independent Datasets**:
- `IXI` - Imperial College London (12GB) - **Good for testing**
- `OASIS1` - Aging study (8GB) - **Good for testing**

### 🔐 Authentication Required

**AWS Credentials Required**:
- `HCP_1200` - Human Connectome Project (15TB)

**Interactive Authentication (IDA-LONI)**:
- `ADNI` - Alzheimer's Disease study (5TB)
- `PPMI` - Parkinson's study (3TB)

## Configuration

Create a configuration file for personalized settings:

```bash
# The CLI will create a default config file at:
# ~/.neurodatahub/config.yml

# View current configuration
neurodatahub config show

# Edit common settings
neurodatahub config set general.default_download_path ~/my_data
neurodatahub config set download.verify_checksums true
```

## Troubleshooting

### Missing Dependencies
```bash
# Install AWS CLI
pip install awscli

# Install aria2 (fast downloader)
brew install aria2  # macOS
apt install aria2   # Ubuntu/Debian

# Install DataLad (for Git-based datasets)
pip install datalad
```

### Download Failures
```bash
# Check system status
neurodatahub check

# Try with debug logging
neurodatahub --debug pull DATASET_ID ~/path

# Resume interrupted downloads (most tools support this)
neurodatahub pull DATASET_ID ~/path  # Re-run the same command
```

### Authentication Issues
```bash
# For AWS datasets, configure credentials
aws configure

# For IDA-LONI datasets, the CLI will guide you through the process
neurodatahub pull ADNI ~/data/ADNI  # Follow interactive prompts
```

## Getting Help

```bash
# General help
neurodatahub --help

# Command-specific help
neurodatahub pull --help
neurodatahub info --help

# Show version
neurodatahub --version
```

## What's Next?

- Check out the [User Guide](USER_GUIDE.md) for detailed information
- Browse [examples](examples/) for specific use cases
- Read about [authentication workflows](AUTHENTICATION.md)
- Learn about [configuration options](CONFIGURATION.md)

## Quick Reference

| Command | Description |
|---------|-------------|
| `neurodatahub check` | Check system dependencies |
| `neurodatahub --list` | List all available datasets |
| `neurodatahub info DATASET` | Show dataset information |
| `neurodatahub pull DATASET PATH` | Download a dataset |
| `neurodatahub search QUERY` | Search datasets |
| `neurodatahub categories` | Show dataset categories |
| `neurodatahub stats` | Show statistics |

Happy downloading! 🧠✨