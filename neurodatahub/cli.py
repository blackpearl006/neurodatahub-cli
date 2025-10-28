"""Main CLI interface for NeuroDataHub."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .atlas import atlas_manager
from .auth import auth_manager
from .datasets import dataset_manager
from .downloader import download_manager
from .feedback import maybe_prompt_feedback
from .ida_flow import run_ida_workflow
from .state import get_state_manager
from .telemetry import record_download_event
from .utils import (
    display_dataset_info,
    display_dependency_status,
    display_error,
    display_info,
    display_success,
    display_welcome,
    get_confirmation,
)

console = Console()


def _prompt_telemetry_consent() -> None:
    """Prompt user for telemetry consent on first successful download."""
    state_manager = get_state_manager()

    # Check if we already asked
    if state_manager.was_telemetry_consent_asked():
        return

    # Show consent prompt
    consent_notice = """
[bold cyan]NeuroDataHub Telemetry[/bold cyan]

We collect anonymized usage data to improve NeuroDataHub:
• Dataset download success/failure counts
• OS platform, CLI version, Python version

[green]NOT collected:[/green]
• No personal information (usernames, emails, file paths, hostnames)
• No IP addresses are stored
• No persistent user identifiers

Would you like to help us improve by sharing anonymous usage data?
    """
    console.print(Panel(consent_notice, title="Privacy Notice", border_style="cyan"))

    try:
        from rich.prompt import Confirm

        consent = Confirm.ask("Enable telemetry?", default=True)
        state_manager.set_telemetry_consent(consent)

        if consent:
            display_success(
                "Telemetry enabled. Thank you for helping improve NeuroDataHub!"
            )
        else:
            display_info(
                "Telemetry disabled. You can change this in ~/.neurodatahub/state.json"
            )

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Skipping telemetry setup[/yellow]")
        state_manager.set_telemetry_consent(False)


@click.group(invoke_without_command=True)
@click.option(
    "--list", "list_datasets", is_flag=True, help="List all available datasets"
)
@click.option("--pull", "dataset_id", help="Download a specific dataset by ID")
@click.option("--path", "target_path", help="Target path for dataset download")
@click.option(
    "--note", help="Optional note/description for download event (use with --pull)"
)
@click.option("--category", help="Filter datasets by category (use with --list)")
@click.option(
    "--auth-only",
    is_flag=True,
    help="Show only datasets requiring authentication (use with --list)",
)
@click.option(
    "--no-auth-only",
    is_flag=True,
    help="Show only datasets not requiring authentication (use with --list)",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed dataset information (use with --list)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually downloading",
)
@click.option(
    "--feedback",
    "show_feedback",
    is_flag=True,
    help="Provide feedback about NeuroDataHub",
)
@click.version_option(version=__version__, prog_name="neurodatahub")
@click.pass_context
def main(
    ctx,
    list_datasets,
    dataset_id,
    target_path,
    note,
    category,
    auth_only,
    no_auth_only,
    detailed,
    dry_run,
    show_feedback,
):
    """NeuroDataHub CLI - Download neuroimaging datasets with ease!"""

    # Handle --feedback option
    if show_feedback:
        maybe_prompt_feedback(force=True)
        return

    # If no command and no options, show welcome
    if ctx.invoked_subcommand is None and not any(
        [list_datasets, dataset_id, target_path]
    ):
        display_welcome()
        return

    # Handle --list option
    if list_datasets:
        if auth_only and no_auth_only:
            display_error("Cannot use both --auth-only and --no-auth-only")
            return

        datasets = dataset_manager.list_datasets(
            category=category, auth_only=auth_only, no_auth_only=no_auth_only
        )
        dataset_manager.display_datasets_table(datasets, detailed=detailed)
        return

    # Handle --pull option
    if dataset_id:
        if not target_path:
            display_error("--path is required when using --pull")
            return

        dataset = dataset_manager.get_dataset(dataset_id)
        if not dataset:
            display_error(f"Dataset '{dataset_id}' not found")
            display_info("Use 'neurodatahub --list' to see available datasets")
            return

        # Show dataset info
        display_dataset_info(dataset, detailed=True)

        if not dry_run and not get_confirmation(
            f"Download {dataset.get('name')} to {target_path}?"
        ):
            display_info("Download cancelled")
            return

        # Handle IDA-LONI datasets specially
        if dataset.get("download_method") == "ida_loni":
            success = run_ida_workflow(dataset, target_path, dry_run)
        else:
            # Check authentication if required
            if dataset.get("auth_required", False):
                if not auth_manager.authenticate_dataset(dataset):
                    display_error("Authentication failed")
                    return

            # Download the dataset
            success = download_manager.download_dataset(dataset, target_path, dry_run)

        if success:
            if not dry_run:
                display_success(f"Successfully downloaded {dataset.get('name')}")

                # Check if this is the first successful download
                state_manager = get_state_manager()
                is_first_success = state_manager.get_successful_runs() == 0

                # Prompt for telemetry consent on first successful download
                if is_first_success:
                    _prompt_telemetry_consent()

                # Record telemetry event
                record_download_event(
                    dataset_name=dataset_id,
                    succeeded=True,
                    metadata_received=True,
                    resume_attempts=0,
                    note=note,
                )

                # Maybe prompt for feedback
                maybe_prompt_feedback()
        else:
            if not dry_run:
                # Record failed download
                record_download_event(
                    dataset_name=dataset_id,
                    succeeded=False,
                    metadata_received=False,
                    resume_attempts=0,
                    note=note,
                )
            display_error("Download failed")
            sys.exit(1)


@main.command()
def check():
    """Check system dependencies and configuration."""
    display_info("Checking system dependencies...")
    display_dependency_status()


@main.command()
@click.argument("dataset_id")
def info(dataset_id):
    """Show detailed information about a specific dataset."""
    dataset = dataset_manager.get_dataset(dataset_id)

    if not dataset:
        display_error(f"Dataset '{dataset_id}' not found")
        display_info("Use 'neurodatahub --list' to see available datasets")
        return

    display_dataset_info(dataset, detailed=True)

    # Show additional technical information
    console.print("\n[bold]Technical Details:[/bold]")
    console.print(f"Download method: {dataset.get('download_method', 'unknown')}")
    console.print(f"Base command: {dataset.get('base_command', 'N/A')}")

    if dataset.get("openneuro_id"):
        console.print(f"OpenNeuro ID: {dataset['openneuro_id']}")

    if dataset.get("repository"):
        console.print(f"Repository: {dataset['repository']}")


@main.command()
@click.option("--category", help="Show only datasets from this category")
def categories(category):
    """List dataset categories or show datasets in a specific category."""
    if category:
        datasets = dataset_manager.get_datasets_by_category(category)
        if not datasets:
            display_error(f"No datasets found in category '{category}'")
            return

        console.print(f"[bold]Datasets in category '{category.upper()}':[/bold]")
        dataset_manager.display_datasets_table(datasets)
    else:
        dataset_manager.display_categories_table()


@main.command()
@click.argument("query")
def search(query):
    """Search datasets by name, description, or ID."""
    results = dataset_manager.search_datasets(query)

    if not results:
        display_info(f"No datasets found matching '{query}'")
        return

    console.print(f"[bold]Search results for '{query}':[/bold]")
    dataset_manager.display_datasets_table(results, detailed=True)


@main.command()
def stats():
    """Show statistics about the dataset collection."""
    stats = dataset_manager.get_dataset_stats()

    console.print("[bold]NeuroDataHub Dataset Statistics[/bold]\n")

    console.print(f"[cyan]Total datasets:[/cyan] {stats['total']}")

    console.print(f"\n[cyan]By authentication requirement:[/cyan]")
    console.print(f"  No authentication required: {stats['by_auth']['not_required']}")
    console.print(f"  Authentication required: {stats['by_auth']['required']}")

    console.print(f"\n[cyan]By category:[/cyan]")
    for category, count in sorted(stats["by_category"].items()):
        console.print(f"  {category.upper()}: {count}")

    console.print(f"\n[cyan]By download method:[/cyan]")
    for method, count in sorted(stats["by_method"].items()):
        console.print(f"  {method}: {count}")


@main.command()
@click.option("--category", help="List only datasets from this category")
@click.option(
    "--auth-required", is_flag=True, help="List only datasets requiring authentication"
)
@click.option(
    "--no-auth", is_flag=True, help="List only datasets not requiring authentication"
)
def list(category, auth_required, no_auth):
    """List all available datasets with filtering options."""
    if auth_required and no_auth:
        display_error("Cannot use both --auth-required and --no-auth")
        return

    datasets = dataset_manager.list_datasets(
        category=category, auth_only=auth_required, no_auth_only=no_auth
    )
    dataset_manager.display_datasets_table(datasets)


@main.command()
@click.argument("dataset_id")
@click.argument("target_path")
@click.option("--note", help="Optional note/description for download event")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without downloading"
)
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
def pull(dataset_id, target_path, note, dry_run, force):
    """Download a specific dataset."""
    dataset = dataset_manager.get_dataset(dataset_id)

    if not dataset:
        display_error(f"Dataset '{dataset_id}' not found")
        display_info("Use 'neurodatahub list' to see available datasets")
        return

    # Show dataset info
    display_dataset_info(dataset, detailed=True)

    if not force and not dry_run:
        if not get_confirmation(f"Download {dataset.get('name')} to {target_path}?"):
            display_info("Download cancelled")
            return

    # Handle IDA-LONI datasets specially
    if dataset.get("download_method") == "ida_loni":
        success = run_ida_workflow(dataset, target_path, dry_run)
    else:
        # Check authentication if required
        if dataset.get("auth_required", False):
            if not auth_manager.authenticate_dataset(dataset):
                display_error("Authentication failed")
                return

        # Download the dataset
        success = download_manager.download_dataset(dataset, target_path, dry_run)

    if success:
        if not dry_run:
            display_success(f"Successfully downloaded {dataset.get('name')}")

            # Check if this is the first successful download
            state_manager = get_state_manager()
            is_first_success = state_manager.get_successful_runs() == 0

            # Prompt for telemetry consent on first successful download
            if is_first_success:
                _prompt_telemetry_consent()

            # Record telemetry event
            record_download_event(
                dataset_name=dataset_id,
                succeeded=True,
                metadata_received=True,
                resume_attempts=0,
                note=note,
            )

            # Maybe prompt for feedback
            maybe_prompt_feedback()
    else:
        if not dry_run:
            # Record failed download
            record_download_event(
                dataset_name=dataset_id,
                succeeded=False,
                metadata_received=False,
                resume_attempts=0,
                note=note,
            )
        display_error("Download failed")
        sys.exit(1)


@main.command()
def version():
    """Show version information."""
    console.print(f"NeuroDataHub CLI version {__version__}")
    console.print("Homepage: https://blackpearl006.github.io/NeuroDataHub/")
    console.print("Repository: https://github.com/blackpearl006/neurodatahub-cli")


@main.command()
def feedback():
    """Provide feedback about NeuroDataHub."""
    maybe_prompt_feedback(force=True)


@main.group()
def atlas():
    """Manage and download brain atlases."""
    pass


@atlas.command("list")
@click.option(
    "--type",
    "atlas_type",
    help="Filter by atlas type (anatomical, functional, multimodal, connectivity-based)",
)
@click.option("--min-rois", type=int, help="Minimum number of ROIs")
@click.option("--max-rois", type=int, help="Maximum number of ROIs")
@click.option("--detailed", is_flag=True, help="Show detailed information")
def atlas_list(atlas_type, min_rois, max_rois, detailed):
    """List all available brain atlases."""
    atlases = atlas_manager.list_atlases(
        atlas_type=atlas_type, min_rois=min_rois, max_rois=max_rois
    )
    atlas_manager.display_atlases_table(atlases, detailed=detailed)


@atlas.command("info")
@click.argument("atlas_id")
def atlas_info(atlas_id):
    """Show detailed information about a specific atlas."""
    atlas_manager.display_atlas_info(atlas_id)


@atlas.command("download")
@click.argument("atlas_id")
@click.option(
    "--path", default=".", help="Target directory (default: current directory)"
)
def atlas_download(atlas_id, path):
    """Download a specific atlas CSV file."""
    success = atlas_manager.copy_atlas(atlas_id, path)
    if not success:
        sys.exit(1)


@atlas.command("download-all")
@click.option(
    "--path", default=".", help="Target directory (default: current directory)"
)
def atlas_download_all(path):
    """Download all atlas CSV files."""
    display_info(f"Downloading all atlases to {path}...")
    count = atlas_manager.copy_all_atlases(path)
    display_success(f"Successfully downloaded {count} atlases")


@atlas.command("attribution")
def atlas_attribution():
    """Show attribution information for the atlas collection."""
    atlas_manager.display_attribution()


@atlas.command("types")
def atlas_types():
    """Show information about different atlas types."""
    types_info = atlas_manager.get_atlas_types_info()

    if not types_info:
        display_info("No atlas type information available")
        return

    console.print("[bold cyan]Brain Atlas Types[/bold cyan]\n")

    for type_name, type_data in types_info.items():
        console.print(f"[bold]{type_name.upper()}[/bold]")
        console.print(f"  Description: {type_data.get('description', 'N/A')}")
        examples = type_data.get("examples", [])
        if examples:
            console.print(f"  Examples: {', '.join(examples)}")
        console.print()


if __name__ == "__main__":
    main()
