"""Unit tests for utils module."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from neurodatahub.utils import (
    check_available_space,
    check_dependency,
    display_dataset_info,
    format_size,
    get_confirmation,
    get_dependency_status,
    get_user_input,
    run_command,
    validate_path
)


class TestDependencyChecking:
    """Test dependency checking functionality."""
    
    def test_check_dependency_available(self):
        """Test checking for available dependency."""
        with patch('shutil.which', return_value='/usr/bin/python'):
            assert check_dependency('python') is True
    
    def test_check_dependency_unavailable(self):
        """Test checking for unavailable dependency."""
        with patch('shutil.which', return_value=None):
            assert check_dependency('nonexistent') is False
    
    def test_get_dependency_status_all_available(self):
        """Test getting status when all dependencies are available."""
        with patch('neurodatahub.utils.check_dependency', return_value=True):
            status = get_dependency_status()
            expected_deps = ['awscli', 'aria2c', 'datalad', 'git', 'firefox']
            assert all(status[dep] for dep in expected_deps)
    
    def test_get_dependency_status_some_missing(self):
        """Test getting status when some dependencies are missing."""
        def mock_check(cmd):
            return cmd not in ['aria2c', 'firefox']
        
        with patch('neurodatahub.utils.check_dependency', side_effect=mock_check):
            status = get_dependency_status()
            assert status['awscli'] is True
            assert status['aria2c'] is False
            assert status['firefox'] is False


class TestCommandExecution:
    """Test command execution functionality."""
    
    def test_run_command_success(self):
        """Test successful command execution."""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "success output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            returncode, stdout, stderr = run_command('echo test')
            assert returncode == 0
            assert stdout == "success output"
            assert stderr == ""
    
    def test_run_command_failure(self):
        """Test failed command execution."""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "error message"
            mock_run.return_value = mock_result
            
            returncode, stdout, stderr = run_command('false')
            assert returncode == 1
            assert stderr == "error message"
    
    def test_run_command_exception(self):
        """Test command execution with exception."""
        with patch('subprocess.run', side_effect=FileNotFoundError("Command not found")):
            returncode, stdout, stderr = run_command('nonexistent')
            assert returncode == 1
            assert "Command not found" in stderr


class TestPathValidation:
    """Test path validation functionality."""
    
    def test_validate_path_existing_directory(self, temp_dir):
        """Test validating existing directory."""
        assert validate_path(str(temp_dir)) is True
    
    def test_validate_path_create_missing(self, temp_dir):
        """Test creating missing directory."""
        new_path = temp_dir / "new_dir"
        assert validate_path(str(new_path), create_if_missing=True) is True
        assert new_path.exists()
    
    def test_validate_path_existing_file(self, temp_dir):
        """Test validating path that is a file, not directory."""
        file_path = temp_dir / "test_file.txt"
        file_path.write_text("test")
        
        with patch('neurodatahub.utils.console'):
            assert validate_path(str(file_path)) is False
    
    def test_validate_path_no_permission(self, temp_dir):
        """Test path validation with no write permission."""
        with patch('os.access', return_value=False), \
             patch('neurodatahub.utils.console'):
            assert validate_path(str(temp_dir)) is False
    
    def test_validate_path_creation_permission_error(self, temp_dir):
        """Test path creation with permission error."""
        new_path = temp_dir / "restricted"
        
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")), \
             patch('neurodatahub.utils.console'):
            assert validate_path(str(new_path), create_if_missing=True) is False


class TestUserInteraction:
    """Test user interaction functionality."""
    
    @patch('builtins.input', return_value='y')
    def test_get_confirmation_yes(self, mock_input):
        """Test getting positive user confirmation."""
        assert get_confirmation("Continue?") is True
    
    @patch('builtins.input', return_value='n')
    def test_get_confirmation_no(self, mock_input):
        """Test getting negative user confirmation."""
        assert get_confirmation("Continue?") is False
    
    @patch('builtins.input', return_value='')
    def test_get_confirmation_default_true(self, mock_input):
        """Test getting confirmation with default True."""
        assert get_confirmation("Continue?", default=True) is True
    
    @patch('builtins.input', return_value='')
    def test_get_confirmation_default_false(self, mock_input):
        """Test getting confirmation with default False."""
        assert get_confirmation("Continue?", default=False) is False
    
    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_get_confirmation_keyboard_interrupt(self, mock_input):
        """Test handling keyboard interrupt in confirmation."""
        with patch('neurodatahub.utils.console'):
            assert get_confirmation("Continue?") is False
    
    @patch('builtins.input', return_value='test input')
    def test_get_user_input(self, mock_input):
        """Test getting user input."""
        result = get_user_input("Enter something")
        assert result == "test input"
    
    @patch('builtins.input', return_value='')
    def test_get_user_input_with_default(self, mock_input):
        """Test getting user input with default value."""
        result = get_user_input("Enter something", default="default_value")
        assert result == "default_value"
    
    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_get_user_input_keyboard_interrupt(self, mock_input):
        """Test handling keyboard interrupt in user input."""
        with patch('neurodatahub.utils.console'), \
             pytest.raises(SystemExit):
            get_user_input("Enter something")


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_format_size_with_tilde(self):
        """Test formatting size that already has tilde."""
        assert format_size("~100GB") == "~100GB"
    
    def test_format_size_without_tilde(self):
        """Test formatting size without tilde."""
        assert format_size("100GB") == "~100GB"
    
    def test_format_size_empty(self):
        """Test formatting empty size."""
        assert format_size("") == ""
        assert format_size(None) == None
    
    def test_check_available_space_sufficient(self, temp_dir):
        """Test checking available space when sufficient."""
        with patch('os.statvfs') as mock_statvfs:
            mock_statvfs.return_value = MagicMock()
            mock_statvfs.return_value.f_frsize = 4096
            mock_statvfs.return_value.f_bavail = 1000000  # ~4GB available
            
            assert check_available_space(str(temp_dir), "~1GB") is True
    
    def test_check_available_space_insufficient(self, temp_dir):
        """Test checking available space when insufficient."""
        with patch('os.statvfs') as mock_statvfs, \
             patch('neurodatahub.utils.console'):
            mock_statvfs.return_value = MagicMock()
            mock_statvfs.return_value.f_frsize = 4096
            mock_statvfs.return_value.f_bavail = 100  # ~400KB available
            
            assert check_available_space(str(temp_dir), "~1GB") is False
    
    def test_check_available_space_invalid_size(self, temp_dir):
        """Test checking available space with invalid size."""
        assert check_available_space(str(temp_dir), "invalid") is True
        assert check_available_space(str(temp_dir), "") is True
    
    def test_check_available_space_os_error(self, temp_dir):
        """Test checking available space with OS error."""
        with patch('os.statvfs', side_effect=OSError("Permission denied")):
            assert check_available_space(str(temp_dir), "~1GB") is True


class TestDatasetInfoDisplay:
    """Test dataset information display."""
    
    def test_display_dataset_info_basic(self, sample_dataset):
        """Test displaying basic dataset info."""
        with patch('neurodatahub.utils.console'):
            # Should not raise any exceptions
            display_dataset_info(sample_dataset, detailed=False)
    
    def test_display_dataset_info_detailed(self, sample_dataset):
        """Test displaying detailed dataset info."""
        with patch('neurodatahub.utils.console'):
            # Should not raise any exceptions
            display_dataset_info(sample_dataset, detailed=True)
    
    def test_display_dataset_info_missing_fields(self):
        """Test displaying dataset info with missing fields."""
        minimal_dataset = {"name": "Test"}
        with patch('neurodatahub.utils.console'):
            # Should not raise any exceptions
            display_dataset_info(minimal_dataset, detailed=True)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_run_command_with_cwd(self, temp_dir):
        """Test running command with specific working directory."""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            run_command('pwd', cwd=str(temp_dir))
            mock_run.assert_called_once()
            assert mock_run.call_args[1]['cwd'] == str(temp_dir)
    
    def test_validate_path_with_spaces(self, temp_dir):
        """Test path validation with spaces in path name."""
        spaced_path = temp_dir / "path with spaces"
        assert validate_path(str(spaced_path), create_if_missing=True) is True
        assert spaced_path.exists()
    
    def test_get_confirmation_various_inputs(self):
        """Test confirmation with various input formats."""
        test_cases = [
            ('yes', True),
            ('YES', True),
            ('y', True),
            ('Y', True),
            ('true', True),
            ('1', True),
            ('no', False),
            ('n', False),
            ('false', False),
            ('0', False),
            ('invalid', False),
        ]
        
        for input_val, expected in test_cases:
            with patch('builtins.input', return_value=input_val), \
                 patch('neurodatahub.utils.console'):
                result = get_confirmation("Test?", default=False)
                assert result == expected, f"Input '{input_val}' should return {expected}"