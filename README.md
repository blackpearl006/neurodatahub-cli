# NeuroDataHub CLI

<div align="center">
  <img src="https://img.shields.io/pypi/v/neurodatahub-cli" alt="PyPI version">
  <img src="https://img.shields.io/pypi/pyversions/neurodatahub-cli" alt="Python versions">
  <img src="https://img.shields.io/github/license/blackpearl006/neurodatahub-cli" alt="License">
  <img src="https://img.shields.io/pypi/dm/neurodatahub-cli" alt="Downloads">
</div>

A command-line interface for downloading neuroimaging datasets with ease! Access over 30 popular neuroimaging datasets from various sources including INDI, OpenNeuro, ReproBrainChart, and more.

🌐 **Homepage**: https://blackpearl006.github.io/NeuroDataHub/  
📦 **Repository**: https://github.com/blackpearl006/neurodatahub-cli

## Features

- 🗂️ **30+ Datasets**: Access popular neuroimaging datasets from multiple sources
- 🔍 **Smart Search**: Find datasets by name, description, or category
- 🚀 **Multiple Backends**: Supports AWS CLI, aria2c, DataLad, and more
- 🔐 **Authentication Support**: Handles various authentication workflows
- 📊 **Rich UI**: Beautiful tables, progress bars, and interactive prompts
- ⚡ **Resume Support**: Interrupted downloads can be resumed
- 🛡️ **Dependency Checking**: Validates required tools with helpful installation guidance
- 🎯 **Filtering**: Filter datasets by category, authentication requirements, size, etc.

## Quick Start

### Installation

```bash
# Via pip
pip install neurodatahub-cli

# Via conda
conda install -c conda-forge neurodatahub-cli
```

### Basic Usage

```bash
# List all available datasets
neurodatahub --list

# Search for specific datasets
neurodatahub search "brain development"

# Get detailed info about a dataset
neurodatahub info HBN

# Download a dataset
neurodatahub pull HBN --path ./data/HBN

# Check system dependencies
neurodatahub check
```

## Dataset Categories

### INDI Datasets (No Authentication Required)
Access datasets from the International Neuroimaging Data-sharing Initiative:
- **HBN** - Healthy Brain Network (2TB)
- **CORR** - Consortium for Reliability and Reproducibility (500GB)
- **ADHD200** - ADHD diagnosis dataset (200GB)
- **NKI** - Nathan Kline Institute Rockland Sample (800GB)
- And many more...

### OpenNeuro Datasets (No Authentication Required)
Open platform datasets:
- **AOMIC** variants - Amsterdam Open MRI Collection
- **Pixar** - fMRI responses to movie clips
- **MPI** - Max Planck Institute datasets
- **Dense sampling** - High-resolution single subjects

### Independent Datasets
- **IXI** - Imperial College London brain MRI (12GB)
- **OASIS-1/2** - Cross-sectional and longitudinal aging studies
- **HCP** - Human Connectome Project (requires authentication)
- **CamCAN** - Cambridge aging study (requires authentication)

### ReproBrainChart (RBC) Datasets
Git/DataLad-based datasets:
- **PNC** - Philadelphia Neurodevelopmental Cohort
- **BHRC** - Brain Health Registry Cohort  
- **CCNP** - Chinese Color Nest Project

### IDA-LONI Datasets (Interactive Authentication)
Datasets requiring complex authentication workflows:
- **ADNI** - Alzheimer's Disease Neuroimaging Initiative
- **PPMI** - Parkinson's Progression Markers Initiative
- **AIBL** - Australian Imaging Biomarkers study
- **MCSA** - Mayo Clinic Study of Aging

## Installation & Dependencies

### System Dependencies

Different datasets require different tools. The CLI will guide you through installation:

```bash
# AWS CLI (for INDI and OpenNeuro datasets)
pip install awscli
# or
conda install -c conda-forge awscli

# aria2c (for fast parallel downloads)
brew install aria2          # macOS
apt-get install aria2       # Ubuntu/Debian
conda install -c conda-forge aria2

# DataLad (for RBC datasets)
pip install datalad

# Firefox (for interactive authentication)
# Download from https://www.mozilla.org/firefox/
```

### Check Dependencies
```bash
neurodatahub check
```

This will show you which tools are installed and provide installation guidance for missing dependencies.

## Command Reference

### Core Commands

#### List Datasets
```bash
# List all datasets
neurodatahub --list
neurodatahub list

# Filter by category
neurodatahub --list --category indi
neurodatahub list --category openneuro

# Show only datasets requiring authentication
neurodatahub --list --auth-only
neurodatahub list --auth-required

# Show only datasets NOT requiring authentication  
neurodatahub --list --no-auth-only
neurodatahub list --no-auth

# Show detailed information
neurodatahub --list --detailed
```

#### Download Datasets
```bash
# Basic download
neurodatahub --pull HBN --path ./data/HBN
neurodatahub pull HBN ./data/HBN

# Dry run (see what would be downloaded)
neurodatahub pull HBN ./data/HBN --dry-run

# Skip confirmation prompts
neurodatahub pull HBN ./data/HBN --force
```

#### Information Commands
```bash
# Dataset information
neurodatahub info HBN

# Search datasets
neurodatahub search "alzheimer"
neurodatahub search "resting state"

# Show categories
neurodatahub categories

# Show datasets in specific category
neurodatahub categories --category ida

# Show statistics
neurodatahub stats

# Check system dependencies
neurodatahub check

# Show version
neurodatahub version
```

## Authentication Workflows

### No Authentication Required
Most INDI and OpenNeuro datasets can be downloaded immediately:

```bash
neurodatahub pull HBN ./data/HBN
```

### AWS Credentials Required (HCP)
For datasets like HCP that require AWS credentials:

```bash
# The CLI will guide you through AWS setup
neurodatahub pull HCP_1200 ./data/HCP

# Or set up manually:
aws configure
```

### IDA-LONI Interactive Workflow
For complex datasets like ADNI, PPMI, etc., the CLI provides an interactive checklist:

```bash
neurodatahub pull ADNI ./data/ADNI
```

This will walk you through:
1. ✅ IDA-LONI account registration
2. ✅ Data Use Agreement (DUA) approval  
3. ✅ Image collection creation
4. ✅ Advanced Downloader link generation
5. ✅ IP address verification
6. 📥 Automated download execution

## Examples

### Download Multiple Datasets
```bash
# Download several INDI datasets
for dataset in HBN CORR ADHD200; do
  neurodatahub pull $dataset ./data/$dataset
done
```

### Search and Filter Workflow
```bash
# Find brain development datasets
neurodatahub search "development"

# Show only small datasets without authentication
neurodatahub list --no-auth | grep -E "(MB|GB)" | head -5

# List all OpenNeuro datasets
neurodatahub list --category openneuro
```

### Check Before Downloading
```bash
# Preview what will be downloaded
neurodatahub pull HBN ./data/HBN --dry-run

# Check system readiness
neurodatahub check

# Get dataset details
neurodatahub info HBN
```

## Troubleshooting

### Common Issues

**Download Failed - Missing Dependencies**
```bash
# Check what's missing
neurodatahub check

# Install missing tools as suggested
pip install awscli
brew install aria2
```

**Authentication Issues**
```bash
# For AWS datasets, check credentials
aws configure list

# For IDA-LONI datasets, verify:
# - Account registration
# - DUA approval
# - Same IP for link generation and download
```

**Network/Resume Issues**
```bash
# Most downloads can be resumed by re-running the command
neurodatahub pull HBN ./data/HBN

# For aria2c downloads, use native resume:
aria2c --continue=true [URL]
```

### Getting Help

1. **Built-in Help**
   ```bash
   neurodatahub --help
   neurodatahub pull --help
   ```

2. **Check Dependencies**
   ```bash
   neurodatahub check
   ```

3. **Dataset Information**
   ```bash
   neurodatahub info DATASET_ID
   ```

4. **GitHub Issues**: https://github.com/blackpearl006/neurodatahub-cli/issues

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
git clone https://github.com/blackpearl006/neurodatahub-cli.git
cd neurodatahub-cli
pip install -e ".[dev]"
```

### Running Tests
```bash
pytest tests/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Citation

If you use NeuroDataHub CLI in your research, please cite:

```bibtex
@software{neurodatahub_cli,
  title={NeuroDataHub},
  author={Ninad Aithal},
  year={2025},
  url={https://github.com/blackpearl006/neurodatahub-cli},
  version={0.1.0}
}
```

## Acknowledgments

- Thanks to all dataset providers for making their data openly available
- INDI consortium for pioneering open neuroimaging data sharing
- OpenNeuro platform for standardized dataset hosting
- ReproBrainChart project for reproducible brain charting
- IDA-LONI for comprehensive neuroimaging data archives

## Links

- 🌐 **Homepage**: https://blackpearl006.github.io/NeuroDataHub/
- 📦 **PyPI**: https://pypi.org/project/neurodatahub-cli/  
- 📚 **Documentation**: https://blackpearl006.github.io/NeuroDataHub/docs/
- 🐛 **Issues**: https://github.com/blackpearl006/neurodatahub-cli/issues
- 💬 **Discussions**: https://github.com/blackpearl006/neurodatahub-cli/discussions

---

<div align="center">
  <p>Made with ❤️ for the neuroimaging community</p>
</div>