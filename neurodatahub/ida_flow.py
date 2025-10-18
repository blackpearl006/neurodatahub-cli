"""Interactive workflow for IDA-LONI dataset downloads."""

import time
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .downloader import Aria2cDownloader
from .utils import (
    check_dependency,
    display_error,
    display_info,
    display_success,
    display_warning,
    get_confirmation,
    get_user_input,
    run_command,
    validate_path
)

console = Console()


class IDALONIWorkflow:
    """Interactive workflow for IDA-LONI dataset downloads."""
    
    def __init__(self, dataset: Dict, target_path: str):
        self.dataset = dataset
        self.target_path = target_path
        self.dataset_name = dataset.get('name', 'Unknown Dataset')
        self.ida_url = dataset.get('ida_url', 'https://ida.loni.usc.edu/')
    
    def run_workflow(self, dry_run: bool = False) -> bool:
        """Execute the complete IDA-LONI interactive workflow."""
        if not self._check_prerequisites():
            return False
        
        if not self._display_checklist():
            return False
        
        download_url = self._get_download_url()
        if not download_url:
            return False
        
        return self._execute_download(download_url, dry_run)
    
    def _check_prerequisites(self) -> bool:
        """Check system prerequisites for IDA-LONI downloads."""
        # Check if aria2c is available (preferred for IDA downloads)
        if not check_dependency('aria2c'):
            display_error(
                "aria2c is required for IDA-LONI downloads",
                "Install with: brew install aria2  OR  apt-get install aria2  OR  conda install -c conda-forge aria2"
            )
            return False
        
        # Check if Firefox is available (for authentication guidance)
        if not check_dependency('firefox'):
            display_warning("Firefox not found. You'll need a web browser for IDA-LONI authentication.")
        
        # Validate target path
        if not validate_path(self.target_path):
            return False
        
        return True
    
    def _display_checklist(self) -> bool:
        """Display and walk through the IDA-LONI authentication checklist."""
        checklist_title = f"[AUTH] IDA-LONI Authentication Required for {self.dataset_name}"
        
        checklist_content = f"""
[bold cyan]Please complete these steps before proceeding:[/bold cyan]

[bold]1. [✓] Do you have an IDA-LONI account registered?[/bold]
   Website: {self.ida_url}
   
[bold]2. [✓] Have you requested access through Data Use Agreement (DUA)?[/bold]
   Each dataset requires separate DUA approval
   
[bold]3. [✓] Have you created an image collection for this dataset?[/bold]
   Use the IDA interface to create a collection with your desired images
   
[bold]4. [✓] Have you obtained the download link via Advanced Downloader?[/bold]
   Navigate to: Downloads -> Advanced Download -> Get download link
   
[bold]5. [✓] Are you downloading from the same IP where you got the link?[/bold]
   [yellow](Important: IDA-LONI download links are IP-restricted)[/yellow]

[dim]This workflow will guide you through each step...[/dim]
"""
        
        console.print(Panel(checklist_content, title=checklist_title, border_style="yellow"))
        
        # Step 1: IDA-LONI account
        if not self._check_step_1():
            return False
        
        # Step 2: Data Use Agreement
        if not self._check_step_2():
            return False
        
        # Step 3: Image collection
        if not self._check_step_3():
            return False
        
        # Step 4: Advanced Downloader
        if not self._check_step_4():
            return False
        
        # Step 5: IP address check
        if not self._check_step_5():
            return False
        
        return True
    
    def _check_step_1(self) -> bool:
        """Check IDA-LONI account registration."""
        display_info("Step 1: IDA-LONI Account")
        
        if get_confirmation("Do you have an IDA-LONI account registered?"):
            display_success("[✓] IDA-LONI account confirmed")
            return True
        
        display_info(f"Please register at: {self.ida_url}")
        display_info("Account registration is free but may require institutional affiliation verification.")
        
        if get_confirmation("Have you registered and can log in to IDA-LONI?"):
            display_success("[✓] IDA-LONI account confirmed")
            return True
        
        display_error("IDA-LONI account is required to proceed")
        return False
    
    def _check_step_2(self) -> bool:
        """Check Data Use Agreement status."""
        display_info("Step 2: Data Use Agreement (DUA)")
        
        dua_info = f"""
Each dataset on IDA-LONI requires separate DUA approval:

* {self.dataset_name} requires specific approval
* DUA approval can take several days to weeks
* You must agree to data usage terms and restrictions
* Some datasets require additional documentation
"""
        
        console.print(Panel(dua_info, title="DUA Information", border_style="blue"))
        
        if get_confirmation(f"Have you requested and received DUA approval for {self.dataset_name}?"):
            display_success("[✓] DUA approval confirmed")
            return True
        
        display_info("Please submit DUA request through your IDA-LONI account")
        display_info("Check your email for approval notifications")
        
        if get_confirmation("Have you now received DUA approval?"):
            display_success("[✓] DUA approval confirmed")
            return True
        
        display_error("DUA approval is required to access this dataset")
        return False
    
    def _check_step_3(self) -> bool:
        """Check image collection creation."""
        display_info("ℹ Step 3: Image Collection - CRITICAL SETUP REQUIRED")

        collection_info = """
[bold red]!!!!!! IMPORTANT STEP !!!!![/bold red]
You need to create an image collection in IDA-LONI:

[bold cyan]1. Log in to IDA-LONI[/bold cyan]
[bold cyan]2. Navigate to your approved dataset[/bold cyan]
[bold cyan]3. Go to "Advanced Search"[/bold cyan]

[bold yellow]4. MANDATORY: In "Display in Results" column, CHECK these fields:[/bold yellow]
   [green]☑[/green] Research Group
   [green]☑[/green] Field Strength (Tesla)
   [green]☑[/green] Acquisition Plane
   [green]☑[/green] Acquisition Type
   [green]☑[/green] Modality
   [green]☑[/green] Weighting

   [yellow]NOTE: These fields MUST be displayed to be included in the metadata CSV![/yellow]

[bold cyan]5. Recommended search filters for beginners (T1-weighted structural MRI):[/bold cyan]
   • Modality: MRI
   • Acquisition Plane: SAGITTAL
   • Acquisition Type: 3D
   • Weighting: T1

[bold cyan]6. FOR ADNI SPECIFICALLY - Filter by Image Description to avoid duplicates:[/bold cyan]
   Search for "MPRAGE" OR "MP-RAGE" OR "MP RAGE" (3 variations exist)
   This ensures one scan per subject (MPRAGE has highest subject coverage)

[bold cyan]7. Sanity check for ADNI:[/bold cyan]
   Healthy/CN (Cognitively Normal) + Sagittal + 3D + Age >50
   Should return 2000+ images

[bold cyan]8. Create collection with selected images[/bold cyan]

[bold yellow]9. DOWNLOAD METADATA:[/bold yellow]
   • Check "ALL" checkbox in the right panel
   • Click the "CSV" button under "Collection: [Your Collection Name]"
   • Save this CSV file - you'll need to manually place it in the metadata/ folder
"""

        console.print(Panel(collection_info, title="Collection Setup", border_style="green"))

        if get_confirmation("Have you created an image collection for this dataset?"):
            display_success("[✓] Image collection confirmed")
            return True

        display_info("Please log in to IDA-LONI and create your image collection following the steps above")

        if get_confirmation("Have you now created an image collection?"):
            display_success("[✓] Image collection confirmed")
            return True

        display_error("Image collection is required to generate download links")
        return False
    
    def _check_step_4(self) -> bool:
        """Check Advanced Downloader usage."""
        display_info("Step 4: Advanced Downloader")
        
        downloader_info = """
Generate download link using IDA-LONI Advanced Downloader:

1. In IDA-LONI, go to: Downloads -> Advanced Download
2. Select your created image collection
3. Choose download format (usually DICOM or NIfTI)
4. Click "Get Download Link"
5. Copy the generated download URL

[yellow]Important: The download link is tied to your IP address![/yellow]
"""
        
        console.print(Panel(downloader_info, title="Advanced Downloader", border_style="cyan"))
        
        if get_confirmation("Have you generated a download link using Advanced Downloader?"):
            display_success("[✓] Download link generation confirmed")
            return True
        
        display_info("Please use the Advanced Downloader to generate your link")
        
        if get_confirmation("Have you now generated a download link?"):
            display_success("[✓] Download link generation confirmed")
            return True
        
        display_error("Download link is required to proceed")
        return False
    
    def _check_step_5(self) -> bool:
        """Check IP address consistency."""
        display_info("Step 5: IP Address Check")
        
        ip_info = """
[yellow]Critical: IDA-LONI download links are IP-restricted![/yellow]

* You must download from the same IP address where you generated the link
* If using a different machine/network, the download will fail
* VPNs may cause IP address mismatches
* University networks may have dynamic IPs

[dim]If downloading on a different machine, generate the link on that machine.[/dim]
"""
        
        console.print(Panel(ip_info, title="IP Address Restriction", border_style="red"))
        
        if get_confirmation("Are you downloading from the same IP where you generated the link?"):
            display_success("[✓] IP address consistency confirmed")
            return True
        
        display_warning("IP address mismatch may cause download to fail")
        
        if get_confirmation("Do you want to proceed anyway? (download may fail)"):
            display_warning("[WARNING] Proceeding with potential IP address mismatch")
            return True
        
        display_info("Please generate the download link from this machine/network")
        return False
    
    def _get_download_url(self) -> str:
        """Get the download URL from user input."""
        display_info("Download URL Input")
        
        url_prompt = """
Please provide the download URL from IDA Advanced Downloader:

The URL should look like:
https://ida.loni.usc.edu/download/...

Paste your download URL"""
        
        console.print(Panel(url_prompt, title="Download URL", border_style="green"))
        
        while True:
            download_url = get_user_input("Download URL").strip()
            
            if not download_url:
                display_error("Download URL is required")
                continue
            
            if not download_url.startswith(('http://', 'https://')):
                display_error("Please provide a valid HTTP/HTTPS URL")
                continue
            
            if 'ida.loni.usc.edu' not in download_url.lower():
                if not get_confirmation("This doesn't look like an IDA-LONI URL. Continue anyway?"):
                    continue
            
            # Display URL for confirmation
            console.print(f"[dim]URL: {download_url}[/dim]")
            
            if get_confirmation("Is this URL correct?"):
                return download_url
    
    def _execute_download(self, download_url: str, dry_run: bool = False) -> bool:
        """Execute the download using aria2c."""
        display_info("Starting IDA-LONI download...")
        
        if dry_run:
            display_info(f"[DRY RUN] Would download from: {download_url}")
            display_info(f"[DRY RUN] Target location: {self.target_path}")
            return True
        
        # Create a temporary aria2c-compatible dataset dict
        temp_dataset = {
            'name': self.dataset_name,
            'base_command': f'aria2c -x 16 -j 16 -s 16 "{download_url}"'
        }
        
        # Use Aria2cDownloader
        downloader = Aria2cDownloader(temp_dataset, self.target_path)
        
        if not downloader.prepare():
            return False
        
        display_info("Download may take a long time depending on dataset size...")
        display_info("You can interrupt with Ctrl+C and resume later using aria2c")
        
        success = downloader.download(dry_run=False)
        
        if success:
            self._display_completion_message()
        else:
            self._display_failure_message()
        
        return success
    
    def _display_completion_message(self):
        """Display completion message with next steps."""
        completion_msg = f"""
[bold green][✓] Download completed successfully![/bold green]

[bold]Files downloaded to:[/bold]
📁 {self.target_path}/
   ├── anat/         [cyan](anatomical MRI images)[/cyan]
   └── metadata/     [yellow](place your CSV metadata file here)[/yellow]

[bold]Next steps:[/bold]
1. Verify downloaded files in: {self.target_path}/anat/
2. [yellow]IMPORTANT:[/yellow] Manually place the CSV metadata file you downloaded from IDA-LONI
   into: {self.target_path}/metadata/
3. Check file integrity if checksums were provided
4. Follow dataset-specific processing instructions
5. Review data usage terms from your DUA

[bold]Data Usage Reminder:[/bold]
* Use data only as approved in your DUA
* Cite the dataset properly in publications
* Follow sharing restrictions
* Report any data issues to IDA-LONI

[dim]Thank you for using NeuroDataHub CLI![/dim]
"""

        console.print(Panel(completion_msg, title="Download Complete", border_style="green"))
    
    def _display_failure_message(self):
        """Display failure message with troubleshooting tips."""
        failure_msg = f"""
[bold red][✗] Download failed[/bold red]

[bold]Common issues and solutions:[/bold]

* [yellow]IP address mismatch:[/yellow] Generate download link from this machine
* [yellow]Expired link:[/yellow] Links expire after 24-48 hours, generate a new one
* [yellow]Network issues:[/yellow] Check internet connection and retry
* [yellow]DUA expired:[/yellow] Verify your DUA is still active
* [yellow]Collection issues:[/yellow] Ensure your image collection is valid

[bold]Troubleshooting:[/bold]
1. Try generating a fresh download link
2. Verify you're on the same network
3. Check IDA-LONI system status
4. Contact IDA-LONI support if issues persist

[dim]IDA-LONI Support: ida-support@loni.usc.edu[/dim]
"""
        
        console.print(Panel(failure_msg, title="Download Failed", border_style="red"))


def run_ida_workflow(dataset: Dict, target_path: str, dry_run: bool = False) -> bool:
    """Run the complete IDA-LONI interactive workflow."""
    workflow = IDALONIWorkflow(dataset, target_path)
    return workflow.run_workflow(dry_run)