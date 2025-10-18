"""Atlas management and distribution module."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .utils import display_error, display_info, display_success, display_warning

console = Console()


class AtlasManager:
    """Manages brain atlas distribution and metadata."""

    def __init__(self):
        self.atlases = {}
        self.metadata = {}
        self.atlas_types = {}
        self._load_atlases()

    def _load_atlases(self):
        """Load atlas configurations from JSON file."""
        # Try to find the atlases.json file
        possible_paths = [
            Path(__file__).parent.parent / "data" / "atlases.json",  # Development
            Path(__file__).parent / "data" / "atlases.json",         # Installed package
            Path("data") / "atlases.json"                            # Current directory
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if not config_path:
            display_error("Could not find atlases.json configuration file")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.atlases = config.get('atlases', {})
            self.metadata = config.get('metadata', {})
            self.atlas_types = config.get('atlas_types', {})

        except (json.JSONDecodeError, FileNotFoundError) as e:
            display_error(f"Failed to load atlas configuration: {e}")

    def get_atlas(self, atlas_id: str) -> Optional[Dict]:
        """Get a specific atlas by ID."""
        return self.atlases.get(atlas_id.upper())

    def list_atlases(self, atlas_type: Optional[str] = None,
                    min_rois: Optional[int] = None,
                    max_rois: Optional[int] = None) -> Dict[str, Dict]:
        """List atlases with optional filtering."""
        filtered = {}

        for atlas_id, atlas in self.atlases.items():
            # Type filter
            if atlas_type and atlas.get('atlas_type', '').lower() != atlas_type.lower():
                continue

            # ROI count filters
            num_rois = atlas.get('num_rois', 0)
            if min_rois and num_rois < min_rois:
                continue
            if max_rois and num_rois > max_rois:
                continue

            filtered[atlas_id] = atlas

        return filtered

    def display_atlases_table(self, atlases: Optional[Dict[str, Dict]] = None,
                              detailed: bool = False):
        """Display atlases in a formatted table."""
        if atlases is None:
            atlases = self.atlases

        if not atlases:
            console.print("[yellow]No atlases found matching the criteria.[/yellow]")
            return

        table = Table(title="Available Brain Atlases")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("Type", justify="center")
        table.add_column("ROIs", justify="center")
        table.add_column("Resolution", justify="center")
        table.add_column("Subcortical", justify="center")

        if detailed:
            table.add_column("Best For", style="dim")

        for atlas_id, atlas in sorted(atlases.items()):
            name = atlas.get('short_name', atlas.get('name', 'Unknown'))
            atlas_type = atlas.get('atlas_type', 'unknown')
            num_rois = str(atlas.get('num_rois', '?'))
            parcellation = atlas.get('parcellation_type', 'unknown').capitalize()
            has_subcortical = atlas.get('includes_subcortical', False)

            subcortical_text = "[green]Yes[/green]" if has_subcortical else "[red]No[/red]"

            row = [atlas_id, name, atlas_type, num_rois, parcellation, subcortical_text]

            if detailed:
                suitable_for = atlas.get('suitable_for', [])
                best_for = suitable_for[0] if suitable_for else "General use"
                row.append(best_for)

            table.add_row(*row)

        console.print(table)

        # Display summary
        total = len(atlases)
        by_type = {}
        for atlas in atlases.values():
            atlas_type = atlas.get('atlas_type', 'unknown')
            by_type[atlas_type] = by_type.get(atlas_type, 0) + 1

        summary_parts = [f"Total: {total} atlases"]
        for atype, count in sorted(by_type.items()):
            summary_parts.append(f"{atype}: {count}")

        console.print(f"\n[dim]{' | '.join(summary_parts)}[/dim]")

    def display_atlas_info(self, atlas_id: str):
        """Display detailed information about a specific atlas."""
        atlas = self.get_atlas(atlas_id)

        if not atlas:
            display_error(f"Atlas '{atlas_id}' not found")
            return

        # Build info panel
        info_text = f"""
[bold cyan]{atlas.get('name', 'Unknown')}[/bold cyan]

[bold]Description:[/bold]
{atlas.get('description', 'No description available')}

[bold]Atlas Details:[/bold]
• Type: {atlas.get('atlas_type', 'unknown')}
• Number of ROIs: {atlas.get('num_rois', '?')}
• Resolution: {atlas.get('parcellation_type', 'unknown').capitalize()}
• Includes Subcortical: {'Yes' if atlas.get('includes_subcortical') else 'No'}
• Age Range: {atlas.get('age_range', 'Not specified')}
• Coordinate System: {atlas.get('coordinate_system', 'Not specified')}

[bold]Suitable For:[/bold]
"""

        suitable_for = atlas.get('suitable_for', [])
        for item in suitable_for:
            info_text += f"  • {item}\n"

        if atlas.get('reference'):
            info_text += f"\n[bold]Reference:[/bold] {atlas['reference']}"

        if atlas.get('doi'):
            info_text += f"\n[bold]DOI:[/bold] https://doi.org/{atlas['doi']}"

        if atlas.get('notes'):
            info_text += f"\n\n[bold]Notes:[/bold]\n{atlas['notes']}"

        console.print(Panel(info_text, title=f"Atlas: {atlas_id}", border_style="green"))

    def get_atlas_path(self, atlas_id: str) -> Optional[Path]:
        """Get the file path for an atlas CSV file."""
        atlas = self.get_atlas(atlas_id)

        if not atlas:
            return None

        filename = atlas.get('file')
        if not filename:
            return None

        # Try to find the atlas file
        possible_paths = [
            Path(__file__).parent.parent / "data" / "atlases" / filename,  # Development
            Path(__file__).parent / "data" / "atlases" / filename,         # Installed package
            Path("data") / "atlases" / filename                            # Current directory
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def copy_atlas(self, atlas_id: str, target_dir: str) -> bool:
        """Copy an atlas CSV file to a target directory."""
        atlas = self.get_atlas(atlas_id)

        if not atlas:
            display_error(f"Atlas '{atlas_id}' not found")
            return False

        source_path = self.get_atlas_path(atlas_id)

        if not source_path:
            display_error(f"Atlas file not found for '{atlas_id}'")
            return False

        # Create target directory if it doesn't exist
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Copy file
        dest_file = target_path / atlas['file']

        try:
            shutil.copy2(source_path, dest_file)
            display_success(f"Atlas '{atlas_id}' copied to {dest_file}")
            return True
        except Exception as e:
            display_error(f"Failed to copy atlas: {e}")
            return False

    def copy_all_atlases(self, target_dir: str) -> int:
        """Copy all atlases to a target directory."""
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        success_count = 0

        for atlas_id in self.atlases.keys():
            if self.copy_atlas(atlas_id, target_dir):
                success_count += 1

        return success_count

    def display_attribution(self):
        """Display attribution information for the atlases."""
        attribution_text = f"""
[bold cyan]Brain Atlas Collection[/bold cyan]

[bold]Source:[/bold] {self.metadata.get('source', 'Unknown')}

[bold]Attribution:[/bold]
{self.metadata.get('attribution', 'No attribution available')}

[bold]BrainGraph Reference:[/bold]
{self.metadata.get('brainGraph_reference', 'Not specified')}

[bold]File Format:[/bold] {self.metadata.get('file_format', 'CSV')}
[bold]Coordinate System:[/bold] {self.metadata.get('coordinate_system', 'MNI152')}

[bold]Note:[/bold]
{self.metadata.get('notes', 'No additional notes')}

[dim]Last Updated: {self.metadata.get('last_updated', 'Unknown')}[/dim]
"""

        console.print(Panel(attribution_text, title="Atlas Attribution", border_style="blue"))

    def get_atlas_types_info(self) -> Dict:
        """Get information about different atlas types."""
        return self.atlas_types


# Global atlas manager instance
atlas_manager = AtlasManager()
