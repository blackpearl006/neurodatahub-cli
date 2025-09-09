"""Logging configuration for NeuroDataHub CLI."""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO", 
    log_file: Optional[Path] = None,
    enable_file_logging: bool = True,
    enable_debug: bool = False
) -> None:
    """Set up logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        enable_file_logging: Whether to enable file logging
        enable_debug: Whether to enable debug mode
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger("neurodatahub")
    logger.setLevel(numeric_level if enable_debug else logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler with Rich formatting
    console = Console(stderr=True)
    console_handler = RichHandler(
        console=console,
        show_path=enable_debug,
        show_time=enable_debug,
        rich_tracebacks=True,
        tracebacks_show_locals=enable_debug
    )
    console_handler.setLevel(numeric_level)
    
    # Format for console
    console_format = "%(message)s"
    if enable_debug:
        console_format = "%(name)s: %(message)s"
    
    console_formatter = logging.Formatter(console_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if enable_file_logging:
        if log_file is None:
            # Default log file location
            log_dir = Path.home() / ".neurodatahub"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "neurodatahub.log"
        
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)  # Always debug level for file
            
            # Detailed format for file
            file_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            file_formatter = logging.Formatter(file_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            logger.debug(f"File logging enabled: {log_file}")
        except (IOError, PermissionError) as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    # Set up loggers for dependencies
    setup_dependency_loggers(enable_debug)
    
    logger.info(f"Logging initialized at level: {level}")


def setup_dependency_loggers(enable_debug: bool = False) -> None:
    """Configure logging for third-party dependencies."""
    # Reduce noise from third-party libraries unless in debug mode
    loggers_to_configure = [
        'requests',
        'urllib3',
        'selenium',
        'boto3',
        'botocore',
        's3transfer'
    ]
    
    level = logging.DEBUG if enable_debug else logging.WARNING
    
    for logger_name in loggers_to_configure:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(f"neurodatahub.{name}")


def enable_debug_mode() -> None:
    """Enable debug mode for all loggers."""
    root_logger = logging.getLogger("neurodatahub")
    root_logger.setLevel(logging.DEBUG)
    
    for handler in root_logger.handlers:
        handler.setLevel(logging.DEBUG)
    
    # Also enable debug for dependency loggers
    setup_dependency_loggers(enable_debug=True)


def log_system_info() -> None:
    """Log system information for debugging."""
    import platform
    import subprocess
    
    logger = get_logger("system")
    
    try:
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Platform: {platform.platform()}")
        logger.debug(f"Architecture: {platform.architecture()}")
        
        # Check available tools
        tools = ['aws', 'aria2c', 'git', 'datalad', 'firefox']
        for tool in tools:
            try:
                result = subprocess.run([tool, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0]
                    logger.debug(f"{tool}: {version}")
                else:
                    logger.debug(f"{tool}: not available")
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                logger.debug(f"{tool}: not available or timeout")
                
    except Exception as e:
        logger.warning(f"Could not gather system info: {e}")


def log_performance_metrics(operation: str, duration: float, **kwargs) -> None:
    """Log performance metrics for operations."""
    logger = get_logger("performance")
    
    metrics = [f"{operation} completed in {duration:.2f}s"]
    for key, value in kwargs.items():
        metrics.append(f"{key}={value}")
    
    logger.info(" | ".join(metrics))


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, operation: str, **kwargs):
        self.operation = operation
        self.kwargs = kwargs
        self.start_time = None
        self.logger = get_logger("performance")
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            if exc_type:
                self.logger.error(f"{self.operation} failed after {duration:.2f}s: {exc_val}")
            else:
                log_performance_metrics(self.operation, duration, **self.kwargs)


def log_download_progress(dataset_name: str, bytes_downloaded: int, total_bytes: int = None) -> None:
    """Log download progress."""
    logger = get_logger("download")
    
    if total_bytes:
        percentage = (bytes_downloaded / total_bytes) * 100
        logger.info(f"{dataset_name}: {bytes_downloaded:,} / {total_bytes:,} bytes ({percentage:.1f}%)")
    else:
        logger.info(f"{dataset_name}: {bytes_downloaded:,} bytes downloaded")


# Import time module for PerformanceTimer
import time