"""Authentication handlers for different dataset sources."""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .utils import (
    check_dependency,
    display_error,
    display_info,
    display_success,
    display_warning,
    get_confirmation,
    get_user_input,
    run_command
)

console = Console()


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class BaseAuthenticator:
    """Base class for authentication handlers."""
    
    def __init__(self, dataset: Dict):
        self.dataset = dataset
        self.dataset_name = dataset.get('name', 'Unknown Dataset')
    
    def authenticate(self) -> bool:
        """Perform authentication. Should be implemented by subclasses."""
        raise NotImplementedError
    
    def is_authenticated(self) -> bool:
        """Check if already authenticated. Should be implemented by subclasses."""
        raise NotImplementedError


class AWSCredentialsAuth(BaseAuthenticator):
    """Authentication handler for datasets requiring AWS credentials."""
    
    def authenticate(self) -> bool:
        """Guide user through AWS credentials setup."""
        if self.is_authenticated():
            display_success("AWS credentials already configured")
            return True
        
        display_info("AWS credentials required for this dataset")
        display_info("You need to obtain AWS access keys from the dataset provider")
        
        if not get_confirmation("Do you have AWS access keys for this dataset?"):
            display_info("Please obtain access keys from the dataset provider first")
            return False
        
        display_info("Configuring AWS credentials...")
        display_info("You can also manually run 'aws configure' to set up credentials")
        
        # Try to run aws configure
        try:
            subprocess.run(['aws', 'configure'], check=True)
            return self.is_authenticated()
        except (subprocess.CalledProcessError, FileNotFoundError):
            display_error("Failed to run 'aws configure'. Please set up AWS CLI manually.")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if AWS credentials are configured."""
        if not check_dependency('aws'):
            return False
        
        # Check if credentials are configured
        result = run_command('aws configure list', capture_output=True)
        return result[0] == 0


class NoAuthRequired(BaseAuthenticator):
    """Handler for datasets that don't require authentication."""
    
    def authenticate(self) -> bool:
        return True
    
    def is_authenticated(self) -> bool:
        return True


class ManualAuth(BaseAuthenticator):
    """Handler for datasets requiring manual authentication steps."""
    
    def __init__(self, dataset: Dict, instructions: str = ""):
        super().__init__(dataset)
        self.instructions = instructions
    
    def authenticate(self) -> bool:
        """Display manual authentication instructions."""
        display_info(f"Manual authentication required for {self.dataset_name}")
        
        if self.instructions:
            console.print(self.instructions)
        else:
            website = self.dataset.get('website', '')
            if website:
                display_info(f"Please visit: {website}")
                display_info("Follow the website instructions to gain access to this dataset")
        
        return get_confirmation("Have you completed the authentication steps?")
    
    def is_authenticated(self) -> bool:
        """For manual auth, we assume user knows their authentication status."""
        return get_confirmation(f"Do you have access to {self.dataset_name}?", default=False)


class SeleniumAuth(BaseAuthenticator):
    """Base class for Selenium-based authentication."""
    
    def __init__(self, dataset: Dict):
        super().__init__(dataset)
        self.driver = None
    
    def _setup_driver(self) -> bool:
        """Set up Firefox WebDriver."""
        if not check_dependency('firefox'):
            display_error(
                "Firefox is required for interactive authentication",
                "Please install Firefox from https://www.mozilla.org/firefox/"
            )
            return False
        
        try:
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Don't run headless for interactive auth
            self.driver = webdriver.Firefox(options=options)
            return True
            
        except Exception as e:
            display_error(f"Failed to start Firefox WebDriver: {e}")
            display_info("You may need to install geckodriver: https://github.com/mozilla/geckodriver/releases")
            return False
    
    def _cleanup_driver(self):
        """Clean up WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
    
    def authenticate(self) -> bool:
        """Generic Selenium authentication workflow."""
        if not self._setup_driver():
            return False
        
        try:
            return self._perform_authentication()
        finally:
            self._cleanup_driver()
    
    def _perform_authentication(self) -> bool:
        """Perform the actual authentication. Should be implemented by subclasses."""
        raise NotImplementedError


class HCPAuth(SeleniumAuth):
    """Authentication handler for Human Connectome Project."""
    
    def _perform_authentication(self) -> bool:
        """Guide user through HCP authentication process."""
        display_info("Opening HCP ConnectomeDB in Firefox...")
        display_info("Please log in and navigate to the dataset download section")
        
        try:
            self.driver.get("https://db.humanconnectome.org/")
            
            display_info("Please complete the following steps:")
            display_info("1. Log in to your HCP account")
            display_info("2. Navigate to the dataset you want to download")
            display_info("3. Set up your AWS access keys in your account settings")
            
            # Wait for user to complete authentication
            get_user_input("Press Enter after you have configured your AWS access keys")
            
            return True
            
        except Exception as e:
            display_error(f"Authentication failed: {e}")
            return False


class CamCANAuth(BaseAuthenticator):
    """Authentication handler for CamCAN dataset."""
    
    def authenticate(self) -> bool:
        """Guide user through CamCAN access process."""
        display_info("CamCAN dataset requires special access approval")
        
        instructions = """
To access the CamCAN dataset, you need to:

1. Visit: https://www.cam-can.org/index.php?content=dataset
2. Read and accept the Data Use Agreement
3. Submit an access request with your research proposal
4. Wait for approval from the CamCAN team
5. Follow their specific download instructions

This process typically takes several days to weeks for approval.
"""
        
        console.print(instructions)
        
        return get_confirmation("Have you received approval and download instructions from CamCAN?")
    
    def is_authenticated(self) -> bool:
        return get_confirmation("Do you have approved access to CamCAN dataset?", default=False)


class AuthManager:
    """Manages authentication for different dataset types."""
    
    def __init__(self):
        self.authenticators = {
            'aws_credentials': AWSCredentialsAuth,
            'hcp_special': HCPAuth,
            'camcan_special': CamCANAuth,
            'no_auth': NoAuthRequired,
            'manual': ManualAuth
        }
    
    def get_authenticator(self, dataset: Dict) -> BaseAuthenticator:
        """Get the appropriate authenticator for a dataset."""
        if not dataset.get('auth_required', False):
            return NoAuthRequired(dataset)
        
        download_method = dataset.get('download_method', 'manual')
        dataset_id = dataset.get('id', '').upper()
        
        # Special cases
        if dataset_id == 'HCP_1200' or 'HCP' in dataset_id:
            return HCPAuth(dataset)
        elif dataset_id == 'CAMCAN':
            return CamCANAuth(dataset)
        elif download_method == 'aws_credentials':
            return AWSCredentialsAuth(dataset)
        elif download_method == 'ida_loni':
            # IDA-LONI auth is handled separately in ida_flow.py
            return ManualAuth(dataset, "Please use the IDA-LONI interactive workflow")
        else:
            # Default to manual authentication with website info
            return ManualAuth(dataset)
    
    def authenticate_dataset(self, dataset: Dict) -> bool:
        """Authenticate access to a specific dataset."""
        authenticator = self.get_authenticator(dataset)
        
        try:
            return authenticator.authenticate()
        except Exception as e:
            display_error(f"Authentication failed: {e}")
            return False
    
    def check_authentication_status(self, dataset: Dict) -> bool:
        """Check if a dataset is already authenticated."""
        authenticator = self.get_authenticator(dataset)
        return authenticator.is_authenticated()


# Global authentication manager instance
auth_manager = AuthManager()