"""Utility functions for NeuroDataHub CLI."""

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .exceptions import (
    DependencyError,
    DiskSpaceError,
    NetworkError,
    PermissionError as NDHPermissionError,
    ValidationError
)

console = Console()
logger = logging.getLogger(__name__)


def check_dependency(command: str) -> bool:
    """Check if a system dependency is available."""
    return shutil.which(command) is not None


def get_dependency_status() -> Dict[str, bool]:
    """Check the status of all system dependencies."""
    dependencies = {
        "awscli": "aws",
        "aria2c": "aria2c",
        "datalad": "datalad",
        "git": "git",
        "firefox": "firefox"
    }
    
    status = {}
    for name, command in dependencies.items():
        status[name] = check_dependency(command)
    
    return status


def display_dependency_status():
    """Display a formatted table of dependency status."""
    status = get_dependency_status()
    
    table = Table(title="System Dependencies Status")
    table.add_column("Dependency", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Installation Guide", style="dim")
    
    installation_guides = {
        "awscli": "pip install awscli  OR  conda install -c conda-forge awscli",
        "aria2c": "brew install aria2  OR  apt-get install aria2  OR  conda install -c conda-forge aria2",
        "datalad": "pip install datalad  OR  conda install -c conda-forge datalad",
        "git": "https://git-scm.com/downloads",
        "firefox": "https://www.mozilla.org/firefox/"
    }
    
    for dep, is_available in status.items():
        status_text = "[green]✓ Available[/green]" if is_available else "[red]✗ Missing[/red]"
        guide = installation_guides.get(dep, "See official documentation")
        table.add_row(dep, status_text, guide)
    
    console.print(table)
    
    missing_deps = [dep for dep, available in status.items() if not available]
    if missing_deps:
        console.print(Panel(
            f"[yellow]Warning:[/yellow] Some dependencies are missing: {', '.join(missing_deps)}\n"
            "Some datasets may not be downloadable without these tools.",
            title="Missing Dependencies"
        ))


def run_command(command: str, cwd: Optional[str] = None, capture_output: bool = False, 
                timeout: Optional[int] = None, retries: int = 0) -> Tuple[int, str, str]:
    """Run a shell command with enhanced error handling and retry logic."""
    last_exception = None
    
    for attempt in range(retries + 1):
        try:
            logger.debug(f"Running command (attempt {attempt + 1}): {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=False,
                timeout=timeout
            )
            
            if result.returncode == 0 or attempt == retries:
                return result.returncode, result.stdout or "", result.stderr or ""
            else:
                logger.warning(f"Command failed on attempt {attempt + 1}, retrying...")
                time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds
                
        except subprocess.TimeoutExpired as e:
            last_exception = e
            logger.warning(f"Command timed out on attempt {attempt + 1}")
            if attempt < retries:
                time.sleep(min(2 ** attempt, 10))
            else:
                return 1, "", f"Command timed out after {timeout} seconds"
                
        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error running command: {e}")
            if attempt < retries:
                time.sleep(min(2 ** attempt, 10))
            else:
                return 1, "", str(e)
    
    return 1, "", str(last_exception) if last_exception else "Command failed"


def validate_path(path: str, create_if_missing: bool = True) -> bool:
    """Validate and optionally create a download path."""
    path_obj = Path(path)
    
    if path_obj.exists():
        if not path_obj.is_dir():
            console.print(f"[red]Error:[/red] Path exists but is not a directory: {path}")
            return False
        if not os.access(path, os.W_OK):
            console.print(f"[red]Error:[/red] No write permission for path: {path}")
            return False
        return True
    
    if create_if_missing:
        try:
            path_obj.mkdir(parents=True, exist_ok=True)
            return True
        except PermissionError:
            console.print(f"[red]Error:[/red] Permission denied creating directory: {path}")
            return False
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to create directory {path}: {e}")
            return False
    
    return False


def format_size(size_str: str) -> str:
    """Format size string for display."""
    if not size_str or size_str.startswith("~"):
        return size_str
    return f"~{size_str}"


def get_confirmation(message: str, default: bool = True) -> bool:
    """Get user confirmation with yes/no prompt."""
    default_str = "Y/n" if default else "y/N"
    try:
        response = input(f"{message} [{default_str}]: ").strip().lower()
        if not response:
            return default
        return response in ['y', 'yes', 'true', '1']
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return False


def display_dataset_info(dataset: Dict, detailed: bool = False):
    """Display information about a dataset."""
    name = dataset.get('name', 'Unknown')
    description = dataset.get('description', 'No description available')
    size = dataset.get('size', 'Unknown')
    category = dataset.get('category', 'unknown')
    auth_required = dataset.get('auth_required', False)
    website = dataset.get('website', '')
    
    auth_text = "[red]Yes[/red]" if auth_required else "[green]No[/green]"
    
    if detailed:
        table = Table(title=f"Dataset Information: {name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        
        table.add_row("Name", name)
        table.add_row("Description", description)
        table.add_row("Category", category.upper())
        table.add_row("Size", format_size(size))
        table.add_row("Authentication Required", auth_text)
        if website:
            table.add_row("Website", website)
        if dataset.get('publication'):
            table.add_row("Publication", dataset['publication'])
        if dataset.get('openneuro_id'):
            table.add_row("OpenNeuro ID", dataset['openneuro_id'])
        if dataset.get('repository'):
            table.add_row("Repository", dataset['repository'])
        
        console.print(table)
    else:
        console.print(f"[bold]{name}[/bold] ({category.upper()})")
        console.print(f"  {description}")
        console.print(f"  Size: {format_size(size)} | Auth: {auth_text}")
        if website:
            console.print(f"  Website: {website}")


def check_available_space(path: str, required_size: str) -> bool:
    """Check if there's enough available disk space."""
    if not required_size or not required_size.replace('~', '').replace('GB', '').replace('TB', '').strip():
        return True
    
    try:
        # Convert size to bytes (rough estimation)
        size_str = required_size.replace('~', '').strip()
        if 'TB' in size_str:
            required_bytes = float(size_str.replace('TB', '')) * 1024 * 1024 * 1024 * 1024
        elif 'GB' in size_str:
            required_bytes = float(size_str.replace('GB', '')) * 1024 * 1024 * 1024
        else:
            return True
        
        # Check available space
        statvfs = os.statvfs(path)
        available_bytes = statvfs.f_frsize * statvfs.f_bavail
        
        if available_bytes < required_bytes:
            available_gb = available_bytes / (1024 * 1024 * 1024)
            required_gb = required_bytes / (1024 * 1024 * 1024)
            console.print(f"[yellow]Warning:[/yellow] Insufficient disk space. "
                         f"Available: {available_gb:.1f}GB, Required: {required_gb:.1f}GB")
            return False
        
        return True
    except (ValueError, OSError):
        # If we can't determine space, assume it's okay
        return True


def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default value."""
    try:
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            return response if response else default
        else:
            return input(f"{prompt}: ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(1)


def display_welcome():
    """Display welcome message."""
    welcome_text = """
[bold blue]NeuroDataHub CLI[/bold blue] - Download neuroimaging datasets with ease!

This tool helps you download various neuroimaging datasets from different sources:
• INDI datasets (no authentication required)
• OpenNeuro datasets (no authentication required)  
• Independent datasets (some require authentication)
• ReproBrainChart datasets (requires git/datalad)
• IDA-LONI datasets (requires interactive authentication)

Use [bold]neurodatahub --help[/bold] to see all available commands.
Use [bold]neurodatahub check[/bold] to verify your system dependencies.
"""
    console.print(Panel(welcome_text, title="Welcome", border_style="blue"))


def display_error(message: str, suggestion: str = ""):
    """Display an error message with optional suggestion."""
    error_text = f"[red]Error:[/red] {message}"
    if suggestion:
        error_text += f"\n[yellow]Suggestion:[/yellow] {suggestion}"
    console.print(Panel(error_text, title="Error", border_style="red"))


def display_success(message: str):
    """Display a success message."""
    console.print(f"[green]✓[/green] {message}")


def display_info(message: str):
    """Display an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def display_warning(message: str):
    """Display a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")