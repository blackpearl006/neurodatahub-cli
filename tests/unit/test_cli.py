"""Unit tests for CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from neurodatahub.cli import main


class TestMainCommand:
    """Test main CLI command functionality."""
    
    def test_main_no_args_shows_welcome(self, cli_runner):
        """Test main command without arguments shows welcome message."""
        with patch('neurodatahub.cli.display_welcome') as mock_welcome:
            result = cli_runner.invoke(main, [])
            assert result.exit_code == 0
            mock_welcome.assert_called_once()
    
    def test_list_all_datasets(self, cli_runner):
        """Test listing all datasets."""
        with patch('neurodatahub.cli.dataset_manager') as mock_manager:
            mock_manager.list_datasets.return_value = {'TEST': {'name': 'Test Dataset'}}
            mock_manager.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['--list'])
            assert result.exit_code == 0
            mock_manager.list_datasets.assert_called_once_with(
                category=None, auth_only=False, no_auth_only=False
            )
            mock_manager.display_datasets_table.assert_called_once()
    
    def test_list_with_category_filter(self, cli_runner):
        """Test listing datasets with category filter."""
        with patch('neurodatahub.cli.dataset_manager') as mock_manager:
            mock_manager.list_datasets.return_value = {}
            mock_manager.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['--list', '--category', 'indi'])
            assert result.exit_code == 0
            mock_manager.list_datasets.assert_called_once_with(
                category='indi', auth_only=False, no_auth_only=False
            )
    
    def test_list_auth_only(self, cli_runner):
        """Test listing only datasets requiring authentication."""
        with patch('neurodatahub.cli.dataset_manager') as mock_manager:
            mock_manager.list_datasets.return_value = {}
            mock_manager.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['--list', '--auth-only'])
            assert result.exit_code == 0
            mock_manager.list_datasets.assert_called_once_with(
                category=None, auth_only=True, no_auth_only=False
            )
    
    def test_list_no_auth_only(self, cli_runner):
        """Test listing only datasets not requiring authentication."""
        with patch('neurodatahub.cli.dataset_manager') as mock_manager:
            mock_manager.list_datasets.return_value = {}
            mock_manager.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['--list', '--no-auth-only'])
            assert result.exit_code == 0
            mock_manager.list_datasets.assert_called_once_with(
                category=None, auth_only=False, no_auth_only=True
            )
    
    def test_list_both_auth_flags_error(self, cli_runner):
        """Test error when both auth flags are used."""
        with patch('neurodatahub.cli.display_error') as mock_error:
            result = cli_runner.invoke(main, ['--list', '--auth-only', '--no-auth-only'])
            mock_error.assert_called_once_with("Cannot use both --auth-only and --no-auth-only")
    
    def test_pull_dataset_success(self, cli_runner, sample_dataset):
        """Test successful dataset pull."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.download_manager') as mock_dl, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.display_success'):
            
            mock_dm.get_dataset.return_value = sample_dataset
            mock_dl.download_dataset.return_value = True
            
            result = cli_runner.invoke(main, ['--pull', 'HBN', '--path', '/tmp/test'])
            assert result.exit_code == 0
            mock_dm.get_dataset.assert_called_once_with('HBN')
            mock_dl.download_dataset.assert_called_once()
    
    def test_pull_dataset_not_found(self, cli_runner):
        """Test pulling non-existent dataset."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.display_error') as mock_error, \
             patch('neurodatahub.cli.display_info') as mock_info:
            
            mock_dm.get_dataset.return_value = None
            
            result = cli_runner.invoke(main, ['--pull', 'NONEXISTENT', '--path', '/tmp/test'])
            mock_error.assert_called_once_with("Dataset 'NONEXISTENT' not found")
            mock_info.assert_called_once_with("Use 'neurodatahub --list' to see available datasets")
    
    def test_pull_without_path_error(self, cli_runner):
        """Test pull command without path argument."""
        with patch('neurodatahub.cli.display_error') as mock_error:
            result = cli_runner.invoke(main, ['--pull', 'HBN'])
            mock_error.assert_called_once_with("--path is required when using --pull")
    
    def test_pull_user_cancellation(self, cli_runner, sample_dataset):
        """Test user cancelling download."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=False), \
             patch('neurodatahub.cli.display_info') as mock_info:
            
            mock_dm.get_dataset.return_value = sample_dataset
            
            result = cli_runner.invoke(main, ['--pull', 'HBN', '--path', '/tmp/test'])
            mock_info.assert_called_once_with("Download cancelled")
    
    def test_pull_ida_dataset(self, cli_runner, sample_ida_dataset):
        """Test pulling IDA-LONI dataset."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.run_ida_workflow') as mock_ida, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.display_success'):
            
            mock_dm.get_dataset.return_value = sample_ida_dataset
            mock_ida.return_value = True
            
            result = cli_runner.invoke(main, ['--pull', 'ADNI', '--path', '/tmp/test'])
            assert result.exit_code == 0
            mock_ida.assert_called_once()
    
    def test_pull_auth_required_dataset(self, cli_runner, sample_auth_dataset):
        """Test pulling dataset requiring authentication."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.auth_manager') as mock_auth, \
             patch('neurodatahub.cli.download_manager') as mock_dl, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.display_success'):
            
            mock_dm.get_dataset.return_value = sample_auth_dataset
            mock_auth.authenticate_dataset.return_value = True
            mock_dl.download_dataset.return_value = True
            
            result = cli_runner.invoke(main, ['--pull', 'AUTH_DATASET', '--path', '/tmp/test'])
            assert result.exit_code == 0
            mock_auth.authenticate_dataset.assert_called_once()
    
    def test_pull_auth_failure(self, cli_runner, sample_auth_dataset):
        """Test pulling dataset with authentication failure."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.auth_manager') as mock_auth, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.display_error') as mock_error:
            
            mock_dm.get_dataset.return_value = sample_auth_dataset
            mock_auth.authenticate_dataset.return_value = False
            
            result = cli_runner.invoke(main, ['--pull', 'AUTH_DATASET', '--path', '/tmp/test'])
            mock_error.assert_called_once_with("Authentication failed")
    
    def test_pull_download_failure(self, cli_runner, sample_dataset):
        """Test pull with download failure."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.download_manager') as mock_dl, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.display_error') as mock_error:
            
            mock_dm.get_dataset.return_value = sample_dataset
            mock_dl.download_dataset.return_value = False
            
            result = cli_runner.invoke(main, ['--pull', 'HBN', '--path', '/tmp/test'])
            assert result.exit_code == 1
            mock_error.assert_called_once_with("Download failed")
    
    def test_dry_run_download(self, cli_runner, sample_dataset):
        """Test dry run download."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.download_manager') as mock_dl, \
             patch('neurodatahub.cli.display_dataset_info'):
            
            mock_dm.get_dataset.return_value = sample_dataset
            mock_dl.download_dataset.return_value = True
            
            result = cli_runner.invoke(main, ['--pull', 'HBN', '--path', '/tmp/test', '--dry-run'])
            assert result.exit_code == 0
            # Dry run should not call get_confirmation
            mock_dl.download_dataset.assert_called_once_with(sample_dataset, '/tmp/test', True)


class TestSubcommands:
    """Test CLI subcommands."""
    
    def test_check_command(self, cli_runner):
        """Test check command."""
        with patch('neurodatahub.cli.display_info') as mock_info, \
             patch('neurodatahub.cli.display_dependency_status') as mock_status:
            result = cli_runner.invoke(main, ['check'])
            assert result.exit_code == 0
            mock_info.assert_called_once_with("Checking system dependencies...")
            mock_status.assert_called_once()
    
    def test_info_command_success(self, cli_runner, sample_dataset):
        """Test info command with existing dataset."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.display_dataset_info') as mock_info, \
             patch('neurodatahub.cli.console'):
            
            mock_dm.get_dataset.return_value = sample_dataset
            
            result = cli_runner.invoke(main, ['info', 'HBN'])
            assert result.exit_code == 0
            mock_dm.get_dataset.assert_called_once_with('HBN')
            mock_info.assert_called_once()
    
    def test_info_command_not_found(self, cli_runner):
        """Test info command with non-existent dataset."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.display_error') as mock_error, \
             patch('neurodatahub.cli.display_info') as mock_info:
            
            mock_dm.get_dataset.return_value = None
            
            result = cli_runner.invoke(main, ['info', 'NONEXISTENT'])
            mock_error.assert_called_once_with("Dataset 'NONEXISTENT' not found")
            mock_info.assert_called_once_with("Use 'neurodatahub --list' to see available datasets")
    
    def test_categories_command_list_all(self, cli_runner):
        """Test categories command listing all categories."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm:
            mock_dm.display_categories_table.return_value = None
            
            result = cli_runner.invoke(main, ['categories'])
            assert result.exit_code == 0
            mock_dm.display_categories_table.assert_called_once()
    
    def test_categories_command_specific_category(self, cli_runner):
        """Test categories command with specific category."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.console'):
            
            mock_dm.get_datasets_by_category.return_value = {'TEST': {'name': 'Test'}}
            mock_dm.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['categories', '--category', 'indi'])
            assert result.exit_code == 0
            mock_dm.get_datasets_by_category.assert_called_once_with('indi')
            mock_dm.display_datasets_table.assert_called_once()
    
    def test_categories_command_empty_category(self, cli_runner):
        """Test categories command with empty category."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.display_error') as mock_error:
            
            mock_dm.get_datasets_by_category.return_value = {}
            
            result = cli_runner.invoke(main, ['categories', '--category', 'empty'])
            mock_error.assert_called_once_with("No datasets found in category 'empty'")
    
    def test_search_command_success(self, cli_runner):
        """Test successful search command."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.console'):
            
            mock_dm.search_datasets.return_value = {'TEST': {'name': 'Test Dataset'}}
            mock_dm.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['search', 'brain'])
            assert result.exit_code == 0
            mock_dm.search_datasets.assert_called_once_with('brain')
            mock_dm.display_datasets_table.assert_called_once()
    
    def test_search_command_no_results(self, cli_runner):
        """Test search command with no results."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.display_info') as mock_info:
            
            mock_dm.search_datasets.return_value = {}
            
            result = cli_runner.invoke(main, ['search', 'nonexistent'])
            assert result.exit_code == 0
            mock_info.assert_called_once_with("No datasets found matching 'nonexistent'")
    
    def test_stats_command(self, cli_runner):
        """Test stats command."""
        mock_stats = {
            'total': 10,
            'by_auth': {'required': 3, 'not_required': 7},
            'by_category': {'indi': 5, 'openneuro': 3, 'ida': 2},
            'by_method': {'aws_s3': 6, 'aria2c': 2, 'ida_loni': 2}
        }
        
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.console'):
            
            mock_dm.get_dataset_stats.return_value = mock_stats
            
            result = cli_runner.invoke(main, ['stats'])
            assert result.exit_code == 0
            mock_dm.get_dataset_stats.assert_called_once()
    
    def test_list_command(self, cli_runner):
        """Test list subcommand."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm:
            mock_dm.list_datasets.return_value = {}
            mock_dm.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['list'])
            assert result.exit_code == 0
            mock_dm.list_datasets.assert_called_once()
            mock_dm.display_datasets_table.assert_called_once()
    
    def test_list_command_with_filters(self, cli_runner):
        """Test list command with filters."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm:
            mock_dm.list_datasets.return_value = {}
            mock_dm.display_datasets_table.return_value = None
            
            result = cli_runner.invoke(main, ['list', '--category', 'indi', '--auth-required'])
            assert result.exit_code == 0
            mock_dm.list_datasets.assert_called_once_with(
                category='indi', auth_only=True, no_auth_only=False
            )
    
    def test_list_command_conflicting_flags(self, cli_runner):
        """Test list command with conflicting auth flags."""
        with patch('neurodatahub.cli.display_error') as mock_error:
            result = cli_runner.invoke(main, ['list', '--auth-required', '--no-auth'])
            mock_error.assert_called_once_with("Cannot use both --auth-required and --no-auth")
    
    def test_pull_command_success(self, cli_runner, sample_dataset):
        """Test pull subcommand success."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.download_manager') as mock_dl, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.display_success'):
            
            mock_dm.get_dataset.return_value = sample_dataset
            mock_dl.download_dataset.return_value = True
            
            result = cli_runner.invoke(main, ['pull', 'HBN', '/tmp/test'])
            assert result.exit_code == 0
    
    def test_pull_command_force_flag(self, cli_runner, sample_dataset):
        """Test pull subcommand with force flag."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.download_manager') as mock_dl, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.display_success'):
            
            mock_dm.get_dataset.return_value = sample_dataset
            mock_dl.download_dataset.return_value = True
            
            result = cli_runner.invoke(main, ['pull', 'HBN', '/tmp/test', '--force'])
            assert result.exit_code == 0
            # Should not call get_confirmation when force flag is used
    
    def test_pull_command_not_found(self, cli_runner):
        """Test pull subcommand with non-existent dataset."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.display_error') as mock_error, \
             patch('neurodatahub.cli.display_info') as mock_info:
            
            mock_dm.get_dataset.return_value = None
            
            result = cli_runner.invoke(main, ['pull', 'NONEXISTENT', '/tmp/test'])
            mock_error.assert_called_once_with("Dataset 'NONEXISTENT' not found")
            mock_info.assert_called_once_with("Use 'neurodatahub list' to see available datasets")
    
    def test_version_command(self, cli_runner):
        """Test version command."""
        with patch('neurodatahub.cli.console') as mock_console:
            result = cli_runner.invoke(main, ['version'])
            assert result.exit_code == 0
            assert mock_console.print.call_count >= 3  # Should print version, homepage, and repository


class TestErrorHandling:
    """Test error handling in CLI."""
    
    def test_dataset_manager_exception(self, cli_runner):
        """Test handling of dataset manager exceptions."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm:
            mock_dm.get_dataset.side_effect = Exception("Database error")
            
            with patch('neurodatahub.cli.display_error'):
                result = cli_runner.invoke(main, ['info', 'HBN'])
                # Should handle exception gracefully, not crash
    
    def test_download_manager_exception(self, cli_runner, sample_dataset):
        """Test handling of download manager exceptions."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.download_manager') as mock_dl, \
             patch('neurodatahub.cli.display_dataset_info'), \
             patch('neurodatahub.cli.get_confirmation', return_value=True):
            
            mock_dm.get_dataset.return_value = sample_dataset
            mock_dl.download_dataset.side_effect = Exception("Network error")
            
            with patch('neurodatahub.cli.display_error'):
                result = cli_runner.invoke(main, ['--pull', 'HBN', '--path', '/tmp/test'])
                # Should handle exception gracefully
    
    def test_keyboard_interrupt(self, cli_runner, sample_dataset):
        """Test handling of keyboard interrupt."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm, \
             patch('neurodatahub.cli.get_confirmation', side_effect=KeyboardInterrupt):
            
            mock_dm.get_dataset.return_value = sample_dataset
            
            result = cli_runner.invoke(main, ['--pull', 'HBN', '--path', '/tmp/test'])
            # Should handle KeyboardInterrupt gracefully


class TestCommandLineEdgeCases:
    """Test edge cases in command line parsing."""
    
    def test_empty_arguments(self, cli_runner):
        """Test with empty arguments."""
        result = cli_runner.invoke(main, [])
        assert result.exit_code == 0
    
    def test_invalid_flags(self, cli_runner):
        """Test with invalid flags."""
        result = cli_runner.invoke(main, ['--invalid-flag'])
        assert result.exit_code != 0  # Should fail with invalid option
    
    def test_mixed_commands(self, cli_runner):
        """Test mixing incompatible commands."""
        # This should work - click handles option precedence
        result = cli_runner.invoke(main, ['--list', 'check'])
        # Behavior depends on click's handling
    
    def test_special_characters_in_args(self, cli_runner):
        """Test special characters in arguments."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm:
            mock_dm.search_datasets.return_value = {}
            
            result = cli_runner.invoke(main, ['search', 'test@#$%'])
            assert result.exit_code == 0
    
    def test_unicode_in_args(self, cli_runner):
        """Test unicode characters in arguments."""
        with patch('neurodatahub.cli.dataset_manager') as mock_dm:
            mock_dm.search_datasets.return_value = {}
            
            result = cli_runner.invoke(main, ['search', 'тест'])
            assert result.exit_code == 0
    
    def test_very_long_arguments(self, cli_runner):
        """Test with very long arguments."""
        long_string = 'a' * 1000
        with patch('neurodatahub.cli.dataset_manager') as mock_dm:
            mock_dm.search_datasets.return_value = {}
            
            result = cli_runner.invoke(main, ['search', long_string])
            assert result.exit_code == 0