"""Dataset definitions and configuration management."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from .utils import display_error

console = Console()


class DatasetManager:
    """Manages dataset configurations and provides search/filter functionality."""
    
    def __init__(self):
        self.datasets = {}
        self.categories = {}
        self.download_methods = {}
        self._load_datasets()
    
    def _load_datasets(self):
        """Load dataset configurations from JSON file."""
        # Try to find the datasets.json file
        possible_paths = [
            Path(__file__).parent.parent / "data" / "datasets.json",  # Development
            Path(__file__).parent / "data" / "datasets.json",         # Installed package
            Path("data") / "datasets.json"                            # Current directory
        ]
        
        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        
        if not config_path:
            display_error("Could not find datasets.json configuration file")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.datasets = config.get('datasets', {})
            self.categories = config.get('categories', {})
            self.download_methods = config.get('download_methods', {})
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            display_error(f"Failed to load dataset configuration: {e}")
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """Get a specific dataset by ID."""
        return self.datasets.get(dataset_id.upper())
    
    def list_datasets(self, category: Optional[str] = None, auth_only: bool = False, 
                     no_auth_only: bool = False) -> Dict[str, Dict]:
        """List datasets with optional filtering."""
        filtered = {}
        
        for dataset_id, dataset in self.datasets.items():
            # Category filter
            if category and dataset.get('category', '').lower() != category.lower():
                continue
            
            # Auth filter
            if auth_only and not dataset.get('auth_required', False):
                continue
            if no_auth_only and dataset.get('auth_required', False):
                continue
            
            filtered[dataset_id] = dataset
        
        return filtered
    
    def get_categories(self) -> Dict[str, Dict]:
        """Get all dataset categories."""
        return self.categories
    
    def get_download_methods(self) -> Dict[str, Dict]:
        """Get all download methods."""
        return self.download_methods
    
    def search_datasets(self, query: str) -> Dict[str, Dict]:
        """Search datasets by name, description, or ID."""
        query = query.lower()
        results = {}
        
        for dataset_id, dataset in self.datasets.items():
            # Search in ID, name, and description
            searchable_text = " ".join([
                dataset_id.lower(),
                dataset.get('name', '').lower(),
                dataset.get('description', '').lower()
            ])
            
            if query in searchable_text:
                results[dataset_id] = dataset
        
        return results
    
    def display_datasets_table(self, datasets: Optional[Dict[str, Dict]] = None, 
                              detailed: bool = False):
        """Display datasets in a formatted table."""
        if datasets is None:
            datasets = self.datasets
        
        if not datasets:
            console.print("[yellow]No datasets found matching the criteria.[/yellow]")
            return
        
        table = Table(title="Available Datasets")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("Category", justify="center")
        table.add_column("Size", justify="center")
        table.add_column("Auth", justify="center")
        
        if detailed:
            table.add_column("Description", style="dim")
        
        for dataset_id, dataset in sorted(datasets.items()):
            name = dataset.get('name', 'Unknown')
            category = dataset.get('category', 'unknown').upper()
            size = dataset.get('size', 'Unknown')
            auth_required = dataset.get('auth_required', False)
            description = dataset.get('description', '')
            
            auth_text = "[red]Yes[/red]" if auth_required else "[green]No[/green]"
            
            row = [dataset_id, name, category, size, auth_text]
            if detailed:
                # Truncate description for table display
                desc_short = (description[:50] + "...") if len(description) > 53 else description
                row.append(desc_short)
            
            table.add_row(*row)
        
        console.print(table)
        
        # Display summary
        total = len(datasets)
        auth_required = len([d for d in datasets.values() if d.get('auth_required', False)])
        no_auth = total - auth_required
        
        console.print(f"\n[dim]Total: {total} datasets | "
                     f"No auth required: {no_auth} | "
                     f"Auth required: {auth_required}[/dim]")
    
    def display_categories_table(self):
        """Display available categories in a formatted table."""
        table = Table(title="Dataset Categories")
        table.add_column("Category", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Description")
        table.add_column("Auth Required", justify="center")
        table.add_column("Count", justify="center")
        
        for cat_id, category in self.categories.items():
            name = category.get('name', 'Unknown')
            description = category.get('description', '')
            auth_req = category.get('auth_required', 'varies')
            
            # Count datasets in this category
            count = len([d for d in self.datasets.values() 
                        if d.get('category') == cat_id])
            
            # Format auth requirement
            if auth_req is True:
                auth_text = "[red]Yes[/red]"
            elif auth_req is False:
                auth_text = "[green]No[/green]"
            else:
                auth_text = "[yellow]Varies[/yellow]"
            
            table.add_row(cat_id.upper(), name, description, auth_text, str(count))
        
        console.print(table)
    
    def validate_dataset_id(self, dataset_id: str) -> bool:
        """Validate that a dataset ID exists."""
        return dataset_id.upper() in self.datasets
    
    def get_datasets_by_category(self, category: str) -> Dict[str, Dict]:
        """Get all datasets in a specific category."""
        return {
            dataset_id: dataset 
            for dataset_id, dataset in self.datasets.items()
            if dataset.get('category', '').lower() == category.lower()
        }
    
    def get_datasets_requiring_auth(self) -> Dict[str, Dict]:
        """Get all datasets that require authentication."""
        return {
            dataset_id: dataset 
            for dataset_id, dataset in self.datasets.items()
            if dataset.get('auth_required', False)
        }
    
    def get_datasets_no_auth(self) -> Dict[str, Dict]:
        """Get all datasets that don't require authentication."""
        return {
            dataset_id: dataset 
            for dataset_id, dataset in self.datasets.items()
            if not dataset.get('auth_required', False)
        }
    
    def get_dataset_stats(self) -> Dict:
        """Get statistics about the dataset collection."""
        total = len(self.datasets)
        by_category = {}
        by_auth = {'required': 0, 'not_required': 0}
        by_method = {}
        
        for dataset in self.datasets.values():
            # Category stats
            category = dataset.get('category', 'unknown')
            by_category[category] = by_category.get(category, 0) + 1
            
            # Auth stats
            if dataset.get('auth_required', False):
                by_auth['required'] += 1
            else:
                by_auth['not_required'] += 1
            
            # Method stats
            method = dataset.get('download_method', 'unknown')
            by_method[method] = by_method.get(method, 0) + 1
        
        return {
            'total': total,
            'by_category': by_category,
            'by_auth': by_auth,
            'by_method': by_method
        }


# Global dataset manager instance
dataset_manager = DatasetManager()