#!/usr/bin/env python3
"""
Batch download examples for NeuroDataHub CLI.

This script demonstrates how to download multiple datasets efficiently
and handle various batch processing scenarios.
"""

import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional


class BatchDownloader:
    """Class for managing batch downloads."""
    
    def __init__(self, base_path: str, max_workers: int = 3):
        """Initialize batch downloader.
        
        Args:
            base_path: Base directory for downloads
            max_workers: Maximum concurrent downloads
        """
        self.base_path = Path(base_path)
        self.max_workers = max_workers
        self.downloads = []
        
        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Base download path: {self.base_path}")
    
    def add_dataset(self, dataset_id: str, custom_path: Optional[str] = None, 
                   force: bool = False, dry_run: bool = False):
        """Add a dataset to the download queue.
        
        Args:
            dataset_id: Dataset identifier
            custom_path: Custom download path (optional)
            force: Skip confirmation prompts
            dry_run: Preview only, don't download
        """
        if custom_path:
            download_path = Path(custom_path)
        else:
            download_path = self.base_path / dataset_id
        
        download_info = {
            'dataset_id': dataset_id,
            'path': str(download_path),
            'force': force,
            'dry_run': dry_run
        }
        
        self.downloads.append(download_info)
        print(f"➕ Added {dataset_id} → {download_path}")
    
    def download_single(self, download_info: Dict) -> Dict:
        """Download a single dataset.
        
        Args:
            download_info: Download configuration
            
        Returns:
            Download result dictionary
        """
        dataset_id = download_info['dataset_id']
        path = download_info['path']
        force = download_info['force']
        dry_run = download_info['dry_run']
        
        print(f"🚀 Starting download: {dataset_id}")
        start_time = time.time()
        
        # Build command
        cmd = ['neurodatahub', 'pull', dataset_id, path]
        if force:
            cmd.append('--force')
        if dry_run:
            cmd.append('--dry-run')
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=3600  # 1 hour timeout
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                status = "SUCCESS"
                print(f"✅ {dataset_id} completed in {duration:.1f}s")
            else:
                status = "FAILED"
                print(f"❌ {dataset_id} failed after {duration:.1f}s")
                print(f"   Error: {result.stderr}")
            
            return {
                'dataset_id': dataset_id,
                'path': path,
                'status': status,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {dataset_id} timed out after {duration:.1f}s")
            return {
                'dataset_id': dataset_id,
                'path': path,
                'status': "TIMEOUT",
                'duration': duration,
                'stdout': "",
                'stderr': "Download timed out",
                'returncode': 1
            }
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {dataset_id} error: {e}")
            return {
                'dataset_id': dataset_id,
                'path': path,
                'status': "ERROR",
                'duration': duration,
                'stdout': "",
                'stderr': str(e),
                'returncode': 1
            }
    
    def download_all(self, sequential: bool = False) -> List[Dict]:
        """Download all queued datasets.
        
        Args:
            sequential: Download one at a time instead of parallel
            
        Returns:
            List of download results
        """
        if not self.downloads:
            print("⚠️ No datasets queued for download")
            return []
        
        print(f"\n🎯 Starting batch download of {len(self.downloads)} datasets")
        print(f"   Mode: {'Sequential' if sequential else 'Parallel'}")
        print(f"   Max workers: {1 if sequential else self.max_workers}")
        
        results = []
        
        if sequential:
            # Download one at a time
            for download_info in self.downloads:
                result = self.download_single(download_info)
                results.append(result)
        else:
            # Download in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_dataset = {
                    executor.submit(self.download_single, download_info): download_info['dataset_id']
                    for download_info in self.downloads
                }
                
                for future in concurrent.futures.as_completed(future_to_dataset):
                    result = future.result()
                    results.append(result)
        
        return results
    
    def save_results(self, results: List[Dict], filename: str = "download_results.json"):
        """Save download results to file.
        
        Args:
            results: Download results
            filename: Output filename
        """
        results_file = self.base_path / filename
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Results saved to: {results_file}")
    
    def print_summary(self, results: List[Dict]):
        """Print download summary.
        
        Args:
            results: Download results
        """
        if not results:
            return
        
        successful = len([r for r in results if r['status'] == 'SUCCESS'])
        failed = len([r for r in results if r['status'] == 'FAILED'])
        errors = len([r for r in results if r['status'] == 'ERROR'])
        timeouts = len([r for r in results if r['status'] == 'TIMEOUT'])
        
        total_time = sum(r['duration'] for r in results)
        
        print(f"\n📊 BATCH DOWNLOAD SUMMARY")
        print("="*40)
        print(f"Total datasets: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Timeouts: {timeouts}")
        print(f"Total time: {total_time:.1f}s")
        print(f"Average time: {total_time/len(results):.1f}s")
        
        # Show failed downloads
        failed_downloads = [r for r in results if r['status'] != 'SUCCESS']
        if failed_downloads:
            print(f"\n❌ Failed downloads:")
            for result in failed_downloads:
                print(f"   • {result['dataset_id']}: {result['status']}")
                if result['stderr']:
                    print(f"     Error: {result['stderr'][:100]}...")


def example_small_datasets_batch():
    """Example: Download small datasets for testing."""
    print("\n" + "="*60)
    print("📦 EXAMPLE: Small Datasets Batch Download")
    print("="*60)
    
    downloader = BatchDownloader('/tmp/neurodatahub_small', max_workers=2)
    
    # Add small datasets (using dry-run to avoid actual downloads)
    small_datasets = [
        'IXI',      # ~12GB
        'OASIS1',   # ~8GB  
        'DENSE_F',  # ~50GB
        'DENSE_M'   # ~50GB
    ]
    
    for dataset in small_datasets:
        downloader.add_dataset(dataset, dry_run=True, force=True)
    
    # Download in parallel
    results = downloader.download_all(sequential=False)
    downloader.print_summary(results)
    downloader.save_results(results)


def example_category_batch_download():
    """Example: Download all datasets from a specific category."""
    print("\n" + "="*60)
    print("🏷️ EXAMPLE: Category-based Batch Download")
    print("="*60)
    
    # First, get list of datasets in a category
    try:
        result = subprocess.run(
            ['neurodatahub', '--list', '--category', 'openneuro', '--no-auth-only'],
            capture_output=True, text=True
        )
        
        print("📋 Available OpenNeuro datasets (no auth required):")
        print(result.stdout)
        
        # In a real scenario, you would parse the output to get dataset IDs
        openneuro_datasets = [
            'AOMIC_PIOP1',
            'AOMIC_PIOP2', 
            'Pixar',
            'DENSE_F'
        ]
        
        downloader = BatchDownloader('/tmp/neurodatahub_openneuro', max_workers=2)
        
        for dataset in openneuro_datasets[:2]:  # Limit to 2 for example
            downloader.add_dataset(dataset, dry_run=True)
        
        results = downloader.download_all(sequential=True)  # Sequential for large datasets
        downloader.print_summary(results)
        
    except Exception as e:
        print(f"❌ Error in category batch download: {e}")


def example_priority_batch_download():
    """Example: Download datasets with different priorities."""
    print("\n" + "="*60)
    print("⭐ EXAMPLE: Priority-based Batch Download")
    print("="*60)
    
    # Define datasets with priorities (high priority first)
    datasets_by_priority = {
        'high': ['IXI', 'OASIS1'],        # Small, quick downloads
        'medium': ['HBN'],                 # Medium size
        'low': ['AOMIC_PIOP1']            # Larger datasets
    }
    
    downloader = BatchDownloader('/tmp/neurodatahub_priority', max_workers=1)
    
    # Add datasets in priority order
    for priority in ['high', 'medium', 'low']:
        print(f"\n🎯 Adding {priority} priority datasets:")
        for dataset in datasets_by_priority[priority]:
            downloader.add_dataset(dataset, dry_run=True)
    
    # Download sequentially to maintain priority order
    results = downloader.download_all(sequential=True)
    downloader.print_summary(results)


def example_selective_batch_download():
    """Example: Download datasets based on criteria."""
    print("\n" + "="*60)
    print("🎯 EXAMPLE: Selective Batch Download")
    print("="*60)
    
    # Get dataset information and filter
    datasets_to_check = ['IXI', 'OASIS1', 'HBN', 'CORR', 'DENSE_F']
    selected_datasets = []
    
    for dataset in datasets_to_check:
        try:
            result = subprocess.run(
                ['neurodatahub', 'info', dataset],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                # Simple criteria: select datasets < 100GB and no auth required
                output = result.stdout.lower()
                if 'mb' in output or ('gb' in output and not any(x in output for x in ['tb', '500gb', '800gb'])):
                    if 'no' in output and 'auth' in output:  # Simplified check
                        selected_datasets.append(dataset)
                        print(f"✅ Selected: {dataset}")
                    else:
                        print(f"⏭️ Skipped {dataset}: requires authentication")
                else:
                    print(f"⏭️ Skipped {dataset}: too large")
            else:
                print(f"❌ Could not get info for {dataset}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout getting info for {dataset}")
    
    if selected_datasets:
        downloader = BatchDownloader('/tmp/neurodatahub_selective', max_workers=2)
        
        for dataset in selected_datasets:
            downloader.add_dataset(dataset, dry_run=True, force=True)
        
        results = downloader.download_all()
        downloader.print_summary(results)
    else:
        print("⚠️ No datasets matched selection criteria")


def example_resume_batch_download():
    """Example: Resume interrupted batch downloads."""
    print("\n" + "="*60)
    print("🔄 EXAMPLE: Resume Batch Downloads")
    print("="*60)
    
    # Simulate resuming downloads by checking what's already downloaded
    base_path = Path('/tmp/neurodatahub_resume')
    base_path.mkdir(parents=True, exist_ok=True)
    
    planned_downloads = ['IXI', 'OASIS1', 'DENSE_F', 'HBN']
    
    # Check what's already downloaded (simulate by checking directories)
    already_downloaded = []
    remaining_downloads = []
    
    for dataset in planned_downloads:
        dataset_path = base_path / dataset
        if dataset_path.exists() and any(dataset_path.iterdir()):
            already_downloaded.append(dataset)
            print(f"✅ Already downloaded: {dataset}")
        else:
            remaining_downloads.append(dataset)
            print(f"⏳ Still need: {dataset}")
    
    if remaining_downloads:
        print(f"\n🔄 Resuming download of {len(remaining_downloads)} datasets")
        
        downloader = BatchDownloader(str(base_path), max_workers=2)
        
        for dataset in remaining_downloads:
            downloader.add_dataset(dataset, dry_run=True)
        
        results = downloader.download_all()
        downloader.print_summary(results)
    else:
        print("✅ All downloads already completed!")


def main():
    """Run all batch download examples."""
    print("🧠 NeuroDataHub CLI - Batch Download Examples")
    print("=" * 60)
    print("This script demonstrates batch downloading techniques.")
    print("Note: Using --dry-run to avoid large downloads.")
    
    try:
        # Check if neurodatahub is available
        result = subprocess.run(['neurodatahub', '--version'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ NeuroDataHub CLI not found. Please install it first:")
            print("   pip install neurodatahub-cli")
            sys.exit(1)
        
        print(f"✅ Found NeuroDataHub CLI")
        
        # Run examples
        example_small_datasets_batch()
        example_category_batch_download()
        example_priority_batch_download()
        example_selective_batch_download()
        example_resume_batch_download()
        
        print("\n" + "="*60)
        print("✅ All batch download examples completed!")
        print("="*60)
        print("\n📚 Tips for production use:")
        print("   • Remove --dry-run for actual downloads")
        print("   • Adjust max_workers based on your bandwidth")
        print("   • Monitor disk space during large batch downloads")
        print("   • Use sequential downloads for very large datasets")
        print("   • Set up logging to track long-running batch jobs")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Batch download examples interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running batch download examples: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()