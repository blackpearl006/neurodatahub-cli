"""Progress tracking and resume functionality for NeuroDataHub CLI."""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime

from rich.console import Console
from rich.progress import (
    Progress,
    TaskID,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    SpinnerColumn,
    TextColumn
)

from .config import get_config
from .logging_config import get_logger
from .exceptions import ValidationError

console = Console()
logger = get_logger(__name__)


@dataclass
class DownloadProgress:
    """Track progress for a single download."""
    dataset_id: str
    total_size: Optional[int] = None
    downloaded_size: int = 0
    status: str = "pending"  # pending, downloading, completed, failed, paused
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    resume_info: Optional[Dict[str, Any]] = None
    checksum: Optional[str] = None
    files_info: Optional[List[Dict]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DownloadProgress':
        """Create from dictionary."""
        return cls(**data)
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage."""
        if self.total_size and self.total_size > 0:
            return min((self.downloaded_size / self.total_size) * 100, 100.0)
        return 0.0
    
    @property
    def is_completed(self) -> bool:
        """Check if download is completed."""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if download failed."""
        return self.status == "failed"
    
    @property
    def can_resume(self) -> bool:
        """Check if download can be resumed."""
        return self.status in ["paused", "failed"] and self.downloaded_size > 0
    
    @property
    def duration(self) -> Optional[float]:
        """Get download duration in seconds."""
        if self.start_time:
            end = self.end_time or time.time()
            return end - self.start_time
        return None
    
    @property
    def average_speed(self) -> Optional[float]:
        """Get average download speed in bytes per second."""
        duration = self.duration
        if duration and duration > 0 and self.downloaded_size > 0:
            return self.downloaded_size / duration
        return None


class ProgressTracker:
    """Manage progress tracking for multiple downloads."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize progress tracker.
        
        Args:
            storage_path: Path to store progress files
        """
        config = get_config()
        if storage_path is None:
            storage_path = config.get_cache_dir() / "progress"
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._progress_data: Dict[str, DownloadProgress] = {}
        self._active_downloads: Dict[str, TaskID] = {}
        
        # Load existing progress
        self._load_progress()
        
        logger.debug(f"Progress tracker initialized: {self.storage_path}")
    
    def _get_progress_file(self, dataset_id: str) -> Path:
        """Get progress file path for dataset."""
        safe_name = "".join(c for c in dataset_id if c.isalnum() or c in "._-")
        return self.storage_path / f"{safe_name}.json"
    
    def _load_progress(self):
        """Load progress from storage."""
        for progress_file in self.storage_path.glob("*.json"):
            try:
                with open(progress_file, 'r') as f:
                    data = json.load(f)
                
                progress = DownloadProgress.from_dict(data)
                self._progress_data[progress.dataset_id] = progress
                
                logger.debug(f"Loaded progress for {progress.dataset_id}")
                
            except Exception as e:
                logger.warning(f"Failed to load progress from {progress_file}: {e}")
    
    def _save_progress(self, dataset_id: str):
        """Save progress for specific dataset."""
        if dataset_id not in self._progress_data:
            return
        
        progress_file = self._get_progress_file(dataset_id)
        progress = self._progress_data[dataset_id]
        
        try:
            with open(progress_file, 'w') as f:
                json.dump(progress.to_dict(), f, indent=2)
            
            logger.debug(f"Saved progress for {dataset_id}")
            
        except Exception as e:
            logger.error(f"Failed to save progress for {dataset_id}: {e}")
    
    def start_download(self, dataset_id: str, total_size: Optional[int] = None,
                      resume_info: Optional[Dict] = None) -> DownloadProgress:
        """Start tracking a new download.
        
        Args:
            dataset_id: Dataset identifier
            total_size: Total download size in bytes
            resume_info: Information needed to resume download
            
        Returns:
            DownloadProgress object
        """
        # Check if we have existing progress
        if dataset_id in self._progress_data:
            existing = self._progress_data[dataset_id]
            
            if existing.is_completed:
                logger.info(f"Download {dataset_id} already completed")
                return existing
            
            elif existing.can_resume:
                logger.info(f"Resuming download {dataset_id} from {existing.progress_percentage:.1f}%")
                existing.status = "downloading"
                existing.start_time = time.time()  # Reset start time for current session
                self._save_progress(dataset_id)
                return existing
        
        # Create new progress tracker
        progress = DownloadProgress(
            dataset_id=dataset_id,
            total_size=total_size,
            status="downloading",
            start_time=time.time(),
            resume_info=resume_info
        )
        
        self._progress_data[dataset_id] = progress
        self._save_progress(dataset_id)
        
        logger.info(f"Started tracking download: {dataset_id}")
        return progress
    
    def update_progress(self, dataset_id: str, downloaded_size: int,
                       total_size: Optional[int] = None):
        """Update download progress.
        
        Args:
            dataset_id: Dataset identifier
            downloaded_size: Bytes downloaded so far
            total_size: Total size (if newly available)
        """
        if dataset_id not in self._progress_data:
            logger.warning(f"No progress tracker for {dataset_id}")
            return
        
        progress = self._progress_data[dataset_id]
        progress.downloaded_size = downloaded_size
        
        if total_size is not None:
            progress.total_size = total_size
        
        # Save progress periodically (every 1% or every 10MB, whichever is smaller)
        save_threshold = 10 * 1024 * 1024  # 10MB
        if progress.total_size:
            save_threshold = min(save_threshold, progress.total_size // 100)
        
        if (progress.downloaded_size % save_threshold) < 1024:  # Approximate check
            self._save_progress(dataset_id)
    
    def complete_download(self, dataset_id: str, checksum: Optional[str] = None):
        """Mark download as completed.
        
        Args:
            dataset_id: Dataset identifier
            checksum: Optional checksum for verification
        """
        if dataset_id not in self._progress_data:
            logger.warning(f"No progress tracker for {dataset_id}")
            return
        
        progress = self._progress_data[dataset_id]
        progress.status = "completed"
        progress.end_time = time.time()
        progress.checksum = checksum
        
        if progress.total_size:
            progress.downloaded_size = progress.total_size
        
        self._save_progress(dataset_id)
        
        duration = progress.duration
        speed = progress.average_speed
        
        logger.info(f"Completed download: {dataset_id}")
        if duration:
            logger.info(f"  Duration: {duration:.1f}s")
        if speed:
            logger.info(f"  Average speed: {speed / (1024*1024):.1f} MB/s")
    
    def fail_download(self, dataset_id: str, error_message: str):
        """Mark download as failed.
        
        Args:
            dataset_id: Dataset identifier
            error_message: Error description
        """
        if dataset_id not in self._progress_data:
            logger.warning(f"No progress tracker for {dataset_id}")
            return
        
        progress = self._progress_data[dataset_id]
        progress.status = "failed"
        progress.end_time = time.time()
        progress.error_message = error_message
        
        self._save_progress(dataset_id)
        
        logger.error(f"Failed download: {dataset_id} - {error_message}")
    
    def pause_download(self, dataset_id: str):
        """Pause download tracking.
        
        Args:
            dataset_id: Dataset identifier
        """
        if dataset_id not in self._progress_data:
            return
        
        progress = self._progress_data[dataset_id]
        progress.status = "paused"
        progress.end_time = time.time()
        
        self._save_progress(dataset_id)
        
        logger.info(f"Paused download: {dataset_id}")
    
    def get_progress(self, dataset_id: str) -> Optional[DownloadProgress]:
        """Get progress for specific dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            DownloadProgress object or None
        """
        return self._progress_data.get(dataset_id)
    
    def list_downloads(self, status_filter: Optional[str] = None) -> List[DownloadProgress]:
        """List all tracked downloads.
        
        Args:
            status_filter: Filter by status (pending, downloading, completed, failed, paused)
            
        Returns:
            List of DownloadProgress objects
        """
        downloads = list(self._progress_data.values())
        
        if status_filter:
            downloads = [d for d in downloads if d.status == status_filter]
        
        return sorted(downloads, key=lambda x: x.start_time or 0, reverse=True)
    
    def cleanup_completed(self, older_than_days: int = 30):
        """Clean up old completed downloads.
        
        Args:
            older_than_days: Remove completed downloads older than this many days
        """
        cutoff_time = time.time() - (older_than_days * 24 * 3600)
        to_remove = []
        
        for dataset_id, progress in self._progress_data.items():
            if (progress.is_completed and 
                progress.end_time and 
                progress.end_time < cutoff_time):
                
                to_remove.append(dataset_id)
        
        for dataset_id in to_remove:
            self._remove_progress(dataset_id)
            logger.debug(f"Cleaned up old progress: {dataset_id}")
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old progress records")
    
    def _remove_progress(self, dataset_id: str):
        """Remove progress tracking for dataset."""
        if dataset_id in self._progress_data:
            del self._progress_data[dataset_id]
        
        progress_file = self._get_progress_file(dataset_id)
        if progress_file.exists():
            progress_file.unlink()
    
    def show_progress_summary(self):
        """Display progress summary."""
        downloads = self.list_downloads()
        
        if not downloads:
            console.print("📊 No download history found")
            return
        
        from rich.table import Table
        
        table = Table(title="Download Progress Summary")
        table.add_column("Dataset", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Progress", justify="center")
        table.add_column("Size", justify="right")
        table.add_column("Speed", justify="right")
        table.add_column("Started", style="dim")
        
        for progress in downloads[:20]:  # Show last 20
            # Status with color
            status_colors = {
                "completed": "green",
                "downloading": "blue", 
                "failed": "red",
                "paused": "yellow",
                "pending": "dim"
            }
            status_color = status_colors.get(progress.status, "white")
            status_text = f"[{status_color}]{progress.status.upper()}[/{status_color}]"
            
            # Progress bar
            if progress.total_size:
                progress_text = f"{progress.progress_percentage:.1f}%"
            else:
                progress_text = f"{progress.downloaded_size:,} bytes"
            
            # Size
            if progress.total_size:
                size_text = f"{progress.total_size / (1024**3):.1f} GB"
            else:
                size_text = "Unknown"
            
            # Speed
            speed = progress.average_speed
            if speed:
                speed_text = f"{speed / (1024**2):.1f} MB/s"
            else:
                speed_text = "-"
            
            # Start time
            if progress.start_time:
                start_text = datetime.fromtimestamp(progress.start_time).strftime("%Y-%m-%d %H:%M")
            else:
                start_text = "-"
            
            table.add_row(
                progress.dataset_id,
                status_text,
                progress_text,
                size_text,
                speed_text,
                start_text
            )
        
        console.print(table)
        
        # Summary stats
        total_downloads = len(downloads)
        completed = len([d for d in downloads if d.is_completed])
        failed = len([d for d in downloads if d.is_failed])
        in_progress = len([d for d in downloads if d.status == "downloading"])
        
        console.print(f"\n📈 Summary: {total_downloads} total, {completed} completed, "
                     f"{failed} failed, {in_progress} in progress")


class RichProgressManager:
    """Enhanced progress display using Rich."""
    
    def __init__(self):
        """Initialize Rich progress manager."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True
        )
        self._tasks: Dict[str, TaskID] = {}
    
    def __enter__(self):
        """Enter context manager."""
        self.progress.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.progress.__exit__(exc_type, exc_val, exc_tb)
    
    def add_download(self, dataset_id: str, total_size: Optional[int] = None) -> TaskID:
        """Add a download to progress display.
        
        Args:
            dataset_id: Dataset identifier
            total_size: Total download size in bytes
            
        Returns:
            Task ID for updating progress
        """
        task_id = self.progress.add_task(
            f"Downloading {dataset_id}",
            total=total_size,
            start=False
        )
        
        self._tasks[dataset_id] = task_id
        return task_id
    
    def update_download(self, dataset_id: str, completed: int):
        """Update download progress.
        
        Args:
            dataset_id: Dataset identifier
            completed: Bytes completed
        """
        if dataset_id in self._tasks:
            task_id = self._tasks[dataset_id]
            self.progress.update(task_id, completed=completed)
    
    def complete_download(self, dataset_id: str):
        """Mark download as completed.
        
        Args:
            dataset_id: Dataset identifier
        """
        if dataset_id in self._tasks:
            task_id = self._tasks[dataset_id]
            self.progress.update(task_id, description=f"✅ {dataset_id} completed")
    
    def fail_download(self, dataset_id: str, error: str):
        """Mark download as failed.
        
        Args:
            dataset_id: Dataset identifier
            error: Error message
        """
        if dataset_id in self._tasks:
            task_id = self._tasks[dataset_id]
            self.progress.update(task_id, description=f"❌ {dataset_id} failed: {error}")


def calculate_checksum(file_path: Path, algorithm: str = "sha256") -> str:
    """Calculate checksum for file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)
        
    Returns:
        Hexadecimal checksum string
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def verify_download_integrity(file_path: Path, expected_checksum: str, 
                            algorithm: str = "sha256") -> bool:
    """Verify download integrity using checksum.
    
    Args:
        file_path: Path to downloaded file
        expected_checksum: Expected checksum
        algorithm: Hash algorithm
        
    Returns:
        True if checksums match
    """
    try:
        actual_checksum = calculate_checksum(file_path, algorithm)
        return actual_checksum.lower() == expected_checksum.lower()
    except Exception as e:
        logger.error(f"Failed to verify checksum for {file_path}: {e}")
        return False


# Global progress tracker instance
_progress_tracker = None


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker instance."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker