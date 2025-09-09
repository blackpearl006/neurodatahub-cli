"""Configuration management for NeuroDataHub CLI."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from rich.console import Console

from .exceptions import ConfigurationError
from .logging_config import get_logger

console = Console()
logger = get_logger(__name__)


class Config:
    """Configuration manager for NeuroDataHub CLI."""
    
    DEFAULT_CONFIG = {
        'general': {
            'default_download_path': str(Path.home() / 'neurodatahub_data'),
            'concurrent_downloads': 4,
            'retry_attempts': 3,
            'timeout': 3600,  # 1 hour
            'verify_ssl': True
        },
        'logging': {
            'level': 'INFO',
            'file_logging': True,
            'log_file': None,  # Will use default location
            'debug_mode': False
        },
        'download': {
            'resume_downloads': True,
            'verify_checksums': True,
            'cleanup_on_failure': False,
            'chunk_size': 8192,
            'progress_update_interval': 1.0
        },
        'aws': {
            'max_concurrent_requests': 10,
            'max_bandwidth': None,  # No limit
            'use_accelerate_endpoint': False
        },
        'aria2': {
            'max_connections': 16,
            'split': 16,
            'max_tries': 5,
            'retry_wait': 0
        },
        'ui': {
            'color_output': True,
            'progress_bars': True,
            'confirm_downloads': True,
            'show_file_sizes': True
        }
    }
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default locations.
        """
        self.config_file = config_file or self._get_default_config_file()
        self._config = self.DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _get_default_config_file(self) -> Path:
        """Get the default configuration file path."""
        # Check for config in multiple locations
        config_locations = [
            Path.cwd() / '.neurodatahub.yml',
            Path.cwd() / '.neurodatahub.yaml', 
            Path.home() / '.neurodatahub' / 'config.yml',
            Path.home() / '.neurodatahub' / 'config.yaml',
            Path.home() / '.config' / 'neurodatahub' / 'config.yml',
            Path.home() / '.config' / 'neurodatahub' / 'config.yaml'
        ]
        
        for config_path in config_locations:
            if config_path.exists():
                logger.debug(f"Found config file: {config_path}")
                return config_path
        
        # Return the preferred default location
        default_path = Path.home() / '.neurodatahub' / 'config.yml'
        logger.debug(f"Using default config location: {default_path}")
        return default_path
    
    def _load_config(self):
        """Load configuration from file."""
        if not self.config_file.exists():
            logger.debug(f"Config file does not exist: {self.config_file}")
            self._create_default_config()
            return
        
        try:
            with open(self.config_file, 'r') as f:
                file_config = yaml.safe_load(f) or {}
            
            # Deep merge configuration
            self._merge_config(self._config, file_config)
            logger.info(f"Configuration loaded from: {self.config_file}")
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load config file: {e}")
    
    def _merge_config(self, base: Dict, update: Dict) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _create_default_config(self):
        """Create default configuration file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Created default config file: {self.config_file}")
        except Exception as e:
            logger.warning(f"Could not create config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'general.timeout')."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        # Check for environment variable override
        env_key = f"NEURODATAHUB_{key.upper().replace('.', '_')}"
        env_value = os.environ.get(env_key)
        
        if env_value is not None:
            # Try to convert to appropriate type
            if isinstance(value, bool):
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(value, int):
                try:
                    return int(env_value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {env_key}: {env_value}")
            elif isinstance(value, float):
                try:
                    return float(env_value)
                except ValueError:
                    logger.warning(f"Invalid float value for {env_key}: {env_value}")
            else:
                return env_value
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        logger.debug(f"Config updated: {key} = {value}")
    
    def save(self) -> None:
        """Save current configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Configuration saved to: {self.config_file}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save config file: {e}")
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = self.DEFAULT_CONFIG.copy()
        logger.info("Configuration reset to defaults")
    
    def get_all(self) -> Dict:
        """Get all configuration values."""
        return self._config.copy()
    
    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []
        
        # Validate general settings
        timeout = self.get('general.timeout')
        if not isinstance(timeout, int) or timeout <= 0:
            errors.append("general.timeout must be a positive integer")
        
        concurrent = self.get('general.concurrent_downloads')
        if not isinstance(concurrent, int) or concurrent <= 0 or concurrent > 20:
            errors.append("general.concurrent_downloads must be between 1 and 20")
        
        # Validate logging level
        level = self.get('logging.level')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level not in valid_levels:
            errors.append(f"logging.level must be one of: {valid_levels}")
        
        # Validate download path
        download_path = self.get('general.default_download_path')
        if download_path:
            path_obj = Path(download_path)
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                if not os.access(str(path_obj), os.W_OK):
                    errors.append(f"No write permission for download path: {download_path}")
            except Exception as e:
                errors.append(f"Invalid download path: {e}")
        
        if errors:
            raise ConfigurationError("Configuration validation failed:\n" + "\n".join(errors))
        
        return True
    
    def show_config(self) -> None:
        """Display current configuration."""
        from rich.tree import Tree
        from rich.syntax import Syntax
        
        config_text = yaml.dump(self._config, default_flow_style=False, sort_keys=False)
        syntax = Syntax(config_text, "yaml", theme="monokai", line_numbers=True)
        
        console.print(f"\n[bold]Configuration file:[/bold] {self.config_file}")
        console.print(syntax)
    
    def get_cache_dir(self) -> Path:
        """Get cache directory path."""
        cache_dir = Path.home() / '.neurodatahub' / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def get_log_dir(self) -> Path:
        """Get log directory path."""
        log_dir = Path.home() / '.neurodatahub' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir


# Global configuration instance
_config_instance = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def init_config(config_file: Optional[Path] = None) -> Config:
    """Initialize global configuration."""
    global _config_instance
    _config_instance = Config(config_file)
    return _config_instance