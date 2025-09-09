"""Data validation and integrity checking for NeuroDataHub CLI."""

import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table

from .exceptions import ValidationError, DataIntegrityError
from .logging_config import get_logger

console = Console()
logger = get_logger(__name__)


class DatasetValidator:
    """Validate dataset configurations and metadata."""
    
    REQUIRED_FIELDS = {
        'name', 'category', 'description', 'auth_required', 'download_method'
    }
    
    VALID_CATEGORIES = {
        'indi', 'openneuro', 'independent', 'rbc', 'ida'
    }
    
    VALID_DOWNLOAD_METHODS = {
        'aws_s3', 'aws_credentials', 'aria2c', 'datalad', 'ida_loni', 'special'
    }
    
    SIZE_PATTERN = re.compile(r'~?(\d+(?:\.\d+)?)\s*(MB|GB|TB)', re.IGNORECASE)
    
    def __init__(self):
        """Initialize dataset validator."""
        self.errors = []
        self.warnings = []
    
    def validate_dataset(self, dataset_id: str, dataset_data: Dict) -> bool:
        """Validate a single dataset configuration.
        
        Args:
            dataset_id: Dataset identifier
            dataset_data: Dataset configuration
            
        Returns:
            True if valid, False otherwise
        """
        self.errors = []
        self.warnings = []
        
        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(dataset_data.keys())
        if missing_fields:
            self.errors.append(f"Missing required fields: {missing_fields}")
        
        # Validate individual fields
        self._validate_dataset_id(dataset_id)
        self._validate_name(dataset_data.get('name'))
        self._validate_category(dataset_data.get('category'))
        self._validate_description(dataset_data.get('description'))
        self._validate_size(dataset_data.get('size'))
        self._validate_auth_required(dataset_data.get('auth_required'))
        self._validate_download_method(dataset_data.get('download_method'))
        self._validate_base_command(dataset_data.get('base_command'))
        self._validate_website(dataset_data.get('website'))
        self._validate_publication(dataset_data.get('publication'))
        
        # Cross-field validation
        self._validate_auth_consistency(dataset_data)
        self._validate_command_method_consistency(dataset_data)
        
        return len(self.errors) == 0
    
    def _validate_dataset_id(self, dataset_id: str):
        """Validate dataset ID format."""
        if not dataset_id:
            self.errors.append("Dataset ID cannot be empty")
            return
        
        if not isinstance(dataset_id, str):
            self.errors.append("Dataset ID must be a string")
            return
        
        # Check format - alphanumeric, underscore, hyphen only
        if not re.match(r'^[A-Z0-9_-]+$', dataset_id):
            self.errors.append(f"Dataset ID '{dataset_id}' contains invalid characters")
        
        # Check length
        if len(dataset_id) > 50:
            self.warnings.append(f"Dataset ID '{dataset_id}' is very long ({len(dataset_id)} chars)")
    
    def _validate_name(self, name: Optional[str]):
        """Validate dataset name."""
        if not name:
            self.errors.append("Dataset name is required")
            return
        
        if not isinstance(name, str):
            self.errors.append("Dataset name must be a string")
            return
        
        if len(name.strip()) == 0:
            self.errors.append("Dataset name cannot be empty")
        
        if len(name) > 200:
            self.warnings.append(f"Dataset name is very long ({len(name)} chars)")
    
    def _validate_category(self, category: Optional[str]):
        """Validate dataset category."""
        if not category:
            self.errors.append("Dataset category is required")
            return
        
        if category not in self.VALID_CATEGORIES:
            self.errors.append(f"Invalid category '{category}'. Must be one of: {self.VALID_CATEGORIES}")
    
    def _validate_description(self, description: Optional[str]):
        """Validate dataset description."""
        if not description:
            self.errors.append("Dataset description is required")
            return
        
        if not isinstance(description, str):
            self.errors.append("Dataset description must be a string")
            return
        
        if len(description.strip()) == 0:
            self.errors.append("Dataset description cannot be empty")
        
        if len(description) < 10:
            self.warnings.append("Dataset description is very short")
        
        if len(description) > 1000:
            self.warnings.append(f"Dataset description is very long ({len(description)} chars)")
    
    def _validate_size(self, size: Optional[str]):
        """Validate dataset size format."""
        if not size:
            return  # Size is optional
        
        if not isinstance(size, str):
            self.errors.append("Dataset size must be a string")
            return
        
        # Check format
        if not self.SIZE_PATTERN.match(size):
            self.errors.append(f"Invalid size format '{size}'. Expected format: '~100GB' or '2.5TB'")
            return
        
        # Extract numeric value and unit for reasonableness check
        match = self.SIZE_PATTERN.match(size)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            
            # Convert to GB for comparison
            multipliers = {'MB': 0.001, 'GB': 1, 'TB': 1000}
            size_gb = value * multipliers[unit]
            
            if size_gb < 0.001:  # Less than 1MB
                self.warnings.append(f"Dataset size {size} seems very small")
            elif size_gb > 50000:  # More than 50TB
                self.warnings.append(f"Dataset size {size} seems very large")
    
    def _validate_auth_required(self, auth_required):
        """Validate auth_required field."""
        if auth_required is None:
            self.errors.append("auth_required field is required")
            return
        
        if not isinstance(auth_required, bool):
            self.errors.append("auth_required must be a boolean (true/false)")
    
    def _validate_download_method(self, download_method: Optional[str]):
        """Validate download method."""
        if not download_method:
            self.errors.append("download_method is required")
            return
        
        if download_method not in self.VALID_DOWNLOAD_METHODS:
            self.errors.append(f"Invalid download_method '{download_method}'. Must be one of: {self.VALID_DOWNLOAD_METHODS}")
    
    def _validate_base_command(self, base_command: Optional[str]):
        """Validate base command."""
        if not base_command:
            return  # Optional field
        
        if not isinstance(base_command, str):
            self.errors.append("base_command must be a string")
            return
        
        # Check for potential security issues
        suspicious_patterns = [
            r'\||\;|&&|\$\(.*\)|`.*`',  # Command injection patterns
            r'rm\s+-rf|del\s+/|format\s+',  # Destructive commands
            r'sudo|su\s+',  # Privilege escalation
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, base_command, re.IGNORECASE):
                self.warnings.append(f"base_command contains potentially unsafe pattern: {pattern}")
                break
    
    def _validate_website(self, website: Optional[str]):
        """Validate website URL."""
        if not website:
            return  # Optional field
        
        if not isinstance(website, str):
            self.errors.append("website must be a string")
            return
        
        # Basic URL validation
        try:
            parsed = urlparse(website)
            if not parsed.scheme or not parsed.netloc:
                self.errors.append(f"Invalid website URL: {website}")
            elif parsed.scheme not in ['http', 'https']:
                self.warnings.append(f"Website URL should use https: {website}")
        except Exception:
            self.errors.append(f"Invalid website URL: {website}")
    
    def _validate_publication(self, publication: Optional[str]):
        """Validate publication URL/DOI."""
        if not publication:
            return  # Optional field
        
        if not isinstance(publication, str):
            self.errors.append("publication must be a string")
            return
        
        # Check if it's a DOI or URL
        if publication.startswith('http'):
            self._validate_website(publication)
        elif publication.startswith('10.'):
            # Looks like a DOI
            if not re.match(r'^10\.\d+/.+', publication):
                self.warnings.append(f"Publication DOI format may be invalid: {publication}")
        else:
            self.warnings.append(f"Publication should be a URL or DOI: {publication}")
    
    def _validate_auth_consistency(self, dataset_data: Dict):
        """Validate consistency between auth_required and other fields."""
        auth_required = dataset_data.get('auth_required', False)
        download_method = dataset_data.get('download_method', '')
        
        # Check consistency
        auth_methods = {'aws_credentials', 'ida_loni'}
        no_auth_methods = {'aws_s3', 'aria2c'}
        
        if auth_required and download_method in no_auth_methods:
            self.warnings.append(f"auth_required=true but download_method='{download_method}' typically doesn't require auth")
        
        if not auth_required and download_method in auth_methods:
            self.warnings.append(f"auth_required=false but download_method='{download_method}' typically requires auth")
    
    def _validate_command_method_consistency(self, dataset_data: Dict):
        """Validate consistency between base_command and download_method."""
        download_method = dataset_data.get('download_method', '')
        base_command = dataset_data.get('base_command', '')
        
        if not base_command:
            return
        
        # Check for method-command consistency
        method_patterns = {
            'aws_s3': r'aws\s+s3',
            'aws_credentials': r'aws\s+s3',
            'aria2c': r'aria2c',
            'datalad': r'datalad|git\s+clone',
        }
        
        if download_method in method_patterns:
            expected_pattern = method_patterns[download_method]
            if not re.search(expected_pattern, base_command, re.IGNORECASE):
                self.warnings.append(f"base_command doesn't match download_method '{download_method}'")
    
    def get_validation_report(self) -> str:
        """Get formatted validation report."""
        report_lines = []
        
        if self.errors:
            report_lines.append("❌ ERRORS:")
            for error in self.errors:
                report_lines.append(f"  • {error}")
        
        if self.warnings:
            if report_lines:
                report_lines.append("")
            report_lines.append("⚠️ WARNINGS:")
            for warning in self.warnings:
                report_lines.append(f"  • {warning}")
        
        if not self.errors and not self.warnings:
            report_lines.append("✅ Validation passed")
        
        return "\n".join(report_lines)


class FileIntegrityChecker:
    """Check integrity of downloaded files."""
    
    def __init__(self):
        """Initialize file integrity checker."""
        self.supported_algorithms = {'md5', 'sha1', 'sha256', 'sha512'}
    
    def calculate_checksum(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate checksum for file.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm to use
            
        Returns:
            Hexadecimal checksum string
            
        Raises:
            ValidationError: If algorithm not supported or file not readable
        """
        if algorithm not in self.supported_algorithms:
            raise ValidationError(f"Unsupported hash algorithm: {algorithm}")
        
        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValidationError(f"Path is not a file: {file_path}")
        
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            raise ValidationError(f"Failed to calculate checksum: {e}")
    
    def verify_checksum(self, file_path: Path, expected_checksum: str, 
                       algorithm: str = 'sha256') -> bool:
        """Verify file checksum.
        
        Args:
            file_path: Path to file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm used
            
        Returns:
            True if checksums match
        """
        try:
            actual_checksum = self.calculate_checksum(file_path, algorithm)
            return actual_checksum.lower() == expected_checksum.lower()
        except ValidationError:
            return False
    
    def check_file_format(self, file_path: Path, expected_formats: Optional[Set[str]] = None) -> Dict[str, str]:
        """Check file format and MIME type.
        
        Args:
            file_path: Path to file
            expected_formats: Expected file extensions (optional)
            
        Returns:
            Dictionary with format information
        """
        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        # Get file extension and MIME type
        extension = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Try to detect format from magic bytes
        detected_format = self._detect_format_from_magic(file_path)
        
        result = {
            'extension': extension,
            'mime_type': mime_type,
            'detected_format': detected_format,
            'format_consistent': True
        }
        
        # Check consistency between extension and detected format
        if detected_format and extension:
            format_extensions = {
                'zip': {'.zip'},
                'gzip': {'.gz', '.tar.gz', '.tgz'},
                'tar': {'.tar'},
                'pdf': {'.pdf'},
                'nifti': {'.nii', '.nii.gz'},
                'dicom': {'.dcm', '.ima'},
            }
            
            if detected_format in format_extensions:
                expected_exts = format_extensions[detected_format]
                if not any(file_path.name.endswith(ext) for ext in expected_exts):
                    result['format_consistent'] = False
        
        # Check against expected formats
        if expected_formats:
            if extension not in expected_formats:
                result['format_unexpected'] = True
        
        return result
    
    def _detect_format_from_magic(self, file_path: Path) -> Optional[str]:
        """Detect file format from magic bytes."""
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(16)
            
            # Common magic byte patterns
            magic_patterns = {
                b'PK\x03\x04': 'zip',
                b'PK\x05\x06': 'zip',
                b'PK\x07\x08': 'zip',
                b'\x1f\x8b': 'gzip',
                b'ustar': 'tar',
                b'%PDF': 'pdf',
                b'\x00\x00\x01\x00': 'nifti',
                b'DICM': 'dicom',
            }
            
            for pattern, format_name in magic_patterns.items():
                if magic.startswith(pattern) or pattern in magic:
                    return format_name
            
            return None
            
        except Exception:
            return None
    
    def validate_dataset_structure(self, dataset_path: Path, expected_structure: Optional[Dict] = None) -> Dict:
        """Validate dataset directory structure.
        
        Args:
            dataset_path: Path to dataset directory
            expected_structure: Expected directory structure (optional)
            
        Returns:
            Validation results
        """
        if not dataset_path.exists():
            raise ValidationError(f"Dataset path not found: {dataset_path}")
        
        if not dataset_path.is_dir():
            raise ValidationError(f"Dataset path is not a directory: {dataset_path}")
        
        results = {
            'path': str(dataset_path),
            'total_files': 0,
            'total_size': 0,
            'file_types': {},
            'subdirectories': [],
            'issues': []
        }
        
        # Walk through directory structure
        for root, dirs, files in os.walk(dataset_path):
            root_path = Path(root)
            
            # Count subdirectories
            if root_path != dataset_path:
                rel_path = root_path.relative_to(dataset_path)
                results['subdirectories'].append(str(rel_path))
            
            # Process files
            for file_name in files:
                file_path = root_path / file_name
                
                try:
                    # Get file info
                    stat = file_path.stat()
                    results['total_files'] += 1
                    results['total_size'] += stat.st_size
                    
                    # Count file types
                    extension = file_path.suffix.lower()
                    if extension:
                        results['file_types'][extension] = results['file_types'].get(extension, 0) + 1
                    else:
                        results['file_types']['no_extension'] = results['file_types'].get('no_extension', 0) + 1
                    
                    # Check for common issues
                    if stat.st_size == 0:
                        results['issues'].append(f"Empty file: {file_path.relative_to(dataset_path)}")
                    
                    if not os.access(file_path, os.R_OK):
                        results['issues'].append(f"Unreadable file: {file_path.relative_to(dataset_path)}")
                    
                except Exception as e:
                    results['issues'].append(f"Error accessing {file_name}: {e}")
        
        # Check against expected structure if provided
        if expected_structure:
            self._validate_against_expected_structure(dataset_path, expected_structure, results)
        
        return results
    
    def _validate_against_expected_structure(self, dataset_path: Path, expected: Dict, results: Dict):
        """Validate against expected directory structure."""
        # This is a simplified implementation - in practice, you'd want more sophisticated
        # structure validation based on standards like BIDS
        
        required_files = expected.get('required_files', [])
        for req_file in required_files:
            file_path = dataset_path / req_file
            if not file_path.exists():
                results['issues'].append(f"Required file missing: {req_file}")
        
        required_dirs = expected.get('required_directories', [])
        for req_dir in required_dirs:
            dir_path = dataset_path / req_dir
            if not dir_path.exists() or not dir_path.is_dir():
                results['issues'].append(f"Required directory missing: {req_dir}")


def validate_datasets_config(config_file: Path) -> Tuple[bool, List[str]]:
    """Validate entire datasets configuration file.
    
    Args:
        config_file: Path to datasets.json file
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Failed to read config file: {e}"]
    
    # Check top-level structure
    required_sections = {'datasets', 'categories', 'download_methods'}
    missing_sections = required_sections - set(config.keys())
    if missing_sections:
        issues.append(f"Missing required sections: {missing_sections}")
    
    validator = DatasetValidator()
    
    # Validate each dataset
    datasets = config.get('datasets', {})
    for dataset_id, dataset_data in datasets.items():
        if not validator.validate_dataset(dataset_id, dataset_data):
            issues.extend([f"Dataset {dataset_id}: {error}" for error in validator.errors])
            issues.extend([f"Dataset {dataset_id}: {warning}" for warning in validator.warnings])
    
    # Validate categories
    categories = config.get('categories', {})
    for category_id, category_data in categories.items():
        if category_id not in DatasetValidator.VALID_CATEGORIES:
            issues.append(f"Unknown category: {category_id}")
        
        if not isinstance(category_data, dict):
            issues.append(f"Category {category_id} must be an object")
            continue
        
        required_cat_fields = {'name', 'description'}
        missing_cat_fields = required_cat_fields - set(category_data.keys())
        if missing_cat_fields:
            issues.append(f"Category {category_id} missing fields: {missing_cat_fields}")
    
    # Validate download methods
    methods = config.get('download_methods', {})
    for method_id, method_data in methods.items():
        if method_id not in DatasetValidator.VALID_DOWNLOAD_METHODS:
            issues.append(f"Unknown download method: {method_id}")
        
        if not isinstance(method_data, dict):
            issues.append(f"Download method {method_id} must be an object")
            continue
        
        required_method_fields = {'name', 'description', 'dependencies'}
        missing_method_fields = required_method_fields - set(method_data.keys())
        if missing_method_fields:
            issues.append(f"Download method {method_id} missing fields: {missing_method_fields}")
    
    return len(issues) == 0, issues


def display_validation_results(results: Dict, show_details: bool = True):
    """Display file validation results in a formatted table.
    
    Args:
        results: Validation results from validate_dataset_structure
        show_details: Whether to show detailed information
    """
    console.print(f"\n📂 Dataset Structure Validation: {results['path']}")
    
    # Summary table
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", justify="right")
    
    summary_table.add_row("Total Files", f"{results['total_files']:,}")
    summary_table.add_row("Total Size", f"{results['total_size'] / (1024**3):.2f} GB")
    summary_table.add_row("Subdirectories", str(len(results['subdirectories'])))
    summary_table.add_row("File Types", str(len(results['file_types'])))
    summary_table.add_row("Issues Found", str(len(results['issues'])))
    
    console.print(summary_table)
    
    if show_details:
        # File types table
        if results['file_types']:
            types_table = Table(title="File Types")
            types_table.add_column("Extension", style="cyan")
            types_table.add_column("Count", justify="right")
            
            for ext, count in sorted(results['file_types'].items()):
                types_table.add_row(ext or "no extension", f"{count:,}")
            
            console.print(types_table)
        
        # Issues
        if results['issues']:
            console.print(Panel(
                "\n".join([f"• {issue}" for issue in results['issues']]),
                title="⚠️ Issues Found",
                border_style="red"
            ))
        else:
            console.print(Panel(
                "✅ No issues found",
                title="Validation Status",
                border_style="green"
            ))