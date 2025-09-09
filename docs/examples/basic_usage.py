#!/usr/bin/env python3
"""
Basic usage examples for NeuroDataHub CLI.

This script demonstrates how to use the NeuroDataHub CLI programmatically
and provides examples of common workflows.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command and print output."""
    print(f"🔧 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(f"📄 Output:\n{result.stdout}")
    
    if result.stderr:
        print(f"⚠️ Errors:\n{result.stderr}")
    
    if check and result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        sys.exit(1)
    
    return result


def example_check_dependencies():
    """Example: Check system dependencies."""
    print("\n" + "="*60)
    print("📋 EXAMPLE: Check System Dependencies")
    print("="*60)
    
    # Check what tools are available
    run_command(['neurodatahub', 'check'])


def example_list_datasets():
    """Example: List and filter datasets."""
    print("\n" + "="*60)
    print("📋 EXAMPLE: List and Filter Datasets")
    print("="*60)
    
    # List all datasets
    print("\n🔹 All datasets:")
    run_command(['neurodatahub', '--list'])
    
    # List datasets by category
    print("\n🔹 INDI datasets only:")
    run_command(['neurodatahub', '--list', '--category', 'indi'])
    
    # List datasets not requiring authentication
    print("\n🔹 No authentication required:")
    run_command(['neurodatahub', '--list', '--no-auth-only'])


def example_search_datasets():
    """Example: Search for datasets."""
    print("\n" + "="*60)
    print("🔍 EXAMPLE: Search Datasets")
    print("="*60)
    
    # Search by keyword
    searches = ['brain', 'alzheimer', 'development', 'resting']
    
    for query in searches:
        print(f"\n🔹 Searching for '{query}':")
        run_command(['neurodatahub', 'search', query])


def example_dataset_info():
    """Example: Get detailed dataset information."""
    print("\n" + "="*60)
    print("📊 EXAMPLE: Dataset Information")
    print("="*60)
    
    # Get info about different types of datasets
    datasets = ['HBN', 'IXI', 'ADNI']
    
    for dataset in datasets:
        print(f"\n🔹 Information about {dataset}:")
        run_command(['neurodatahub', 'info', dataset])


def example_dry_run_download():
    """Example: Preview downloads with dry run."""
    print("\n" + "="*60)
    print("🏃 EXAMPLE: Dry Run Downloads")
    print("="*60)
    
    # Preview what would be downloaded
    datasets = ['IXI', 'OASIS1']
    
    for dataset in datasets:
        print(f"\n🔹 Dry run for {dataset}:")
        run_command(['neurodatahub', 'pull', dataset, f'/tmp/{dataset}', '--dry-run'])


def example_categories_and_stats():
    """Example: Show categories and statistics."""
    print("\n" + "="*60)
    print("📈 EXAMPLE: Categories and Statistics")
    print("="*60)
    
    # Show all categories
    print("\n🔹 Dataset categories:")
    run_command(['neurodatahub', 'categories'])
    
    # Show statistics
    print("\n🔹 Dataset statistics:")
    run_command(['neurodatahub', 'stats'])


def example_download_workflow():
    """Example: Complete download workflow."""
    print("\n" + "="*60)
    print("⬇️ EXAMPLE: Download Workflow")
    print("="*60)
    
    # Create a temporary download directory
    download_dir = Path('/tmp/neurodatahub_examples')
    download_dir.mkdir(exist_ok=True)
    
    print(f"📁 Created download directory: {download_dir}")
    
    # Example 1: Download a small dataset
    dataset = 'IXI'
    dataset_path = download_dir / dataset
    
    print(f"\n🔹 Would download {dataset} to {dataset_path}")
    print("   (Using dry-run to avoid large downloads in this example)")
    
    run_command(['neurodatahub', 'pull', dataset, str(dataset_path), '--dry-run'])
    
    # Example 2: Show what would happen with force flag
    print(f"\n🔹 Forced download (dry-run) of {dataset}:")
    run_command(['neurodatahub', 'pull', dataset, str(dataset_path), '--dry-run', '--force'])


def example_error_handling():
    """Example: Error handling scenarios."""
    print("\n" + "="*60)
    print("🛠️ EXAMPLE: Error Handling")
    print("="*60)
    
    # Try to get info about non-existent dataset
    print("\n🔹 Non-existent dataset:")
    run_command(['neurodatahub', 'info', 'NONEXISTENT'], check=False)
    
    # Try to download to invalid path
    print("\n🔹 Invalid download path:")
    run_command(['neurodatahub', 'pull', 'IXI', '/root/no_permission', '--dry-run'], check=False)


def main():
    """Run all examples."""
    print("🧠 NeuroDataHub CLI - Basic Usage Examples")
    print("=" * 60)
    print("This script demonstrates common usage patterns.")
    print("Note: Downloads use --dry-run to avoid large transfers.")
    
    try:
        # Check if neurodatahub is available
        result = subprocess.run(['neurodatahub', '--version'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ NeuroDataHub CLI not found. Please install it first:")
            print("   pip install neurodatahub-cli")
            sys.exit(1)
        
        print(f"✅ Found NeuroDataHub CLI: {result.stdout.strip()}")
        
        # Run examples
        example_check_dependencies()
        example_list_datasets()
        example_search_datasets()
        example_dataset_info()
        example_categories_and_stats()
        example_dry_run_download()
        example_download_workflow()
        example_error_handling()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("="*60)
        print("\n📚 Next steps:")
        print("   • Try downloading a small dataset like IXI")
        print("   • Read the User Guide for advanced features")
        print("   • Check out authentication examples for protected datasets")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Examples interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()