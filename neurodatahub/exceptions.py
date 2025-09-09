"""Custom exceptions for neurodatahub-cli."""


class NeuroDataHubError(Exception):
    """Base exception for all neurodatahub errors."""
    pass


class DatasetNotFoundError(NeuroDataHubError):
    """Raised when a requested dataset is not found."""
    
    def __init__(self, dataset_id):
        self.dataset_id = dataset_id
        super().__init__(f"Dataset '{dataset_id}' not found")


class ConfigurationError(NeuroDataHubError):
    """Raised when there's an issue with configuration."""
    pass


class DependencyError(NeuroDataHubError):
    """Raised when a required dependency is missing."""
    
    def __init__(self, dependency, suggestion=None):
        self.dependency = dependency
        self.suggestion = suggestion
        message = f"Required dependency '{dependency}' not found"
        if suggestion:
            message += f". {suggestion}"
        super().__init__(message)


class AuthenticationError(NeuroDataHubError):
    """Raised when authentication fails."""
    pass


class DownloadError(NeuroDataHubError):
    """Raised when a download fails."""
    
    def __init__(self, message, retry_possible=True):
        self.retry_possible = retry_possible
        super().__init__(message)


class ValidationError(NeuroDataHubError):
    """Raised when data validation fails."""
    pass


class NetworkError(NeuroDataHubError):
    """Raised when network operations fail."""
    
    def __init__(self, message, is_temporary=True):
        self.is_temporary = is_temporary
        super().__init__(message)


class DiskSpaceError(NeuroDataHubError):
    """Raised when there's insufficient disk space."""
    
    def __init__(self, required, available):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient disk space. Required: {required}, Available: {available}")


class PermissionError(NeuroDataHubError):
    """Raised when there are permission issues."""
    pass


class InterruptedError(NeuroDataHubError):
    """Raised when an operation is interrupted."""
    
    def __init__(self, message, can_resume=False):
        self.can_resume = can_resume
        super().__init__(message)


class DataIntegrityError(NeuroDataHubError):
    """Raised when data integrity checks fail."""
    pass