"""Integration tests for full workflow scenarios."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from neurodatahub.cli import main
from neurodatahub.datasets import DatasetManager
from neurodatahub.downloader import DownloadManager


class TestFullWorkflow:
    """Test complete workflows from CLI to download."""
    
    @pytest.fixture
    def integration_setup(self, temp_dir):
        """Set up integration test environment."""
        # Create mock datasets.json
        datasets_config = {
            "datasets": {
                "TEST_INDI": {
                    "name": "Test INDI Dataset",
                    "category": "indi",
                    "description": "Test dataset for integration testing",
                    "size": "~10MB",
                    "auth_required": False,
                    "download_method": "aws_s3",
                    "base_command": "aws s3 sync --no-sign-request s3://test-bucket/data/ .",
                    "website": "https://example.com/test-indi"
                },
                "TEST_AUTH": {
                    "name": "Test Auth Dataset",
                    "category": "independent",
                    "description": "Test dataset requiring authentication",
                    "size": "~50MB",
                    "auth_required": True,
                    "download_method": "aws_credentials",
                    "base_command": "aws s3 sync s3://private-bucket/data/ .",
                    "website": "https://example.com/test-auth"
                },
                "TEST_IDA": {
                    "name": "Test IDA Dataset",
                    "category": "ida",
                    "description": "Test IDA-LONI dataset",
                    "size": "~100MB",
                    "auth_required": True,
                    "download_method": "ida_loni",
                    "base_command": "ida_interactive_flow",
                    "website": "https://ida.loni.usc.edu/",
                    "ida_url": "https://ida.loni.usc.edu/login.jsp?project=TEST"
                }
            },
            "categories": {
                "indi": {
                    "name": "Test INDI",
                    "description": "Test INDI category",
                    "auth_required": False,
                    "download_method": "aws_s3"
                },
                "independent": {
                    "name": "Test Independent",
                    "description": "Test independent category",
                    "auth_required": "varies",
                    "download_method": "varies"
                },
                "ida": {
                    "name": "Test IDA",
                    "description": "Test IDA category",
                    "auth_required": True,
                    "download_method": "ida_loni"
                }
            },
            "download_methods": {
                "aws_s3": {
                    "name": "AWS S3",
                    "description": "Test AWS S3 method",
                    "dependencies": ["awscli"]
                },
                "aws_credentials": {
                    "name": "AWS with Credentials",
                    "description": "Test AWS with credentials",
                    "dependencies": ["awscli"]
                },
                "ida_loni": {
                    "name": "IDA-LONI Interactive",
                    "description": "Test IDA interactive method",
                    "dependencies": ["aria2c", "firefox"]
                }
            }
        }
        
        datasets_file = temp_dir / "datasets.json"
        with open(datasets_file, 'w') as f:
            json.dump(datasets_config, f)
        
        return {
            'datasets_file': datasets_file,
            'config': datasets_config,
            'download_dir': temp_dir / "downloads"
        }
    
    def test_list_and_info_workflow(self, integration_setup):
        """Test the workflow of listing datasets and getting info."""
        runner = CliRunner()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'):
            
            # Test listing all datasets
            result = runner.invoke(main, ['--list'])
            assert result.exit_code == 0
            
            # Test listing with category filter
            result = runner.invoke(main, ['--list', '--category', 'indi'])
            assert result.exit_code == 0
            
            # Test getting info about a specific dataset
            result = runner.invoke(main, ['info', 'TEST_INDI'])
            assert result.exit_code == 0
    
    def test_search_workflow(self, integration_setup):
        """Test the search functionality workflow."""
        runner = CliRunner()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'):
            
            # Test search by name
            result = runner.invoke(main, ['search', 'INDI'])
            assert result.exit_code == 0
            
            # Test search by description
            result = runner.invoke(main, ['search', 'integration'])
            assert result.exit_code == 0
    
    def test_check_dependencies_workflow(self, integration_setup):
        """Test the dependency checking workflow."""
        runner = CliRunner()
        
        with patch('neurodatahub.cli.display_info') as mock_info, \
             patch('neurodatahub.utils.get_dependency_status') as mock_status, \
             patch('neurodatahub.utils.console'):
            
            mock_status.return_value = {
                'awscli': True,
                'aria2c': False,
                'datalad': True,
                'git': True,
                'firefox': False
            }
            
            result = runner.invoke(main, ['check'])
            assert result.exit_code == 0
            mock_info.assert_called_with("Checking system dependencies...")
    
    def test_no_auth_download_workflow(self, integration_setup):
        """Test complete download workflow for dataset not requiring auth."""
        runner = CliRunner()
        download_dir = integration_setup['download_dir']
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=True), \
             patch('neurodatahub.downloader.run_command', return_value=(0, "success", "")), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'), \
             patch('neurodatahub.utils.console'), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('time.time', side_effect=[0, 10]):
            
            result = runner.invoke(main, ['pull', 'TEST_INDI', str(download_dir)])
            assert result.exit_code == 0
    
    def test_auth_required_download_workflow(self, integration_setup):
        """Test download workflow for dataset requiring authentication."""
        runner = CliRunner()
        download_dir = integration_setup['download_dir']
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.auth.check_dependency', return_value=True), \
             patch('neurodatahub.auth.run_command', return_value=(0, "configured", "")), \
             patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=True), \
             patch('neurodatahub.downloader.run_command', return_value=(0, "success", "")), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'), \
             patch('neurodatahub.utils.console'), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('time.time', side_effect=[0, 10]):
            
            result = runner.invoke(main, ['pull', 'TEST_AUTH', str(download_dir)])
            assert result.exit_code == 0
    
    def test_ida_download_workflow(self, integration_setup):
        """Test IDA-LONI download workflow."""
        runner = CliRunner()
        download_dir = integration_setup['download_dir']
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.ida_flow.check_dependency', return_value=True), \
             patch('neurodatahub.ida_flow.validate_path', return_value=True), \
             patch('neurodatahub.ida_flow.get_confirmation', return_value=True), \
             patch('neurodatahub.ida_flow.get_user_input', return_value="https://ida.loni.usc.edu/download/test"), \
             patch('neurodatahub.downloader.run_command', return_value=(0, "success", "")), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'), \
             patch('neurodatahub.utils.console'), \
             patch('neurodatahub.ida_flow.console'):
            
            result = runner.invoke(main, ['pull', 'TEST_IDA', str(download_dir)])
            assert result.exit_code == 0
    
    def test_dry_run_workflow(self, integration_setup):
        """Test dry run workflow."""
        runner = CliRunner()
        download_dir = integration_setup['download_dir']
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'), \
             patch('neurodatahub.downloader.display_info'):
            
            result = runner.invoke(main, ['pull', 'TEST_INDI', str(download_dir), '--dry-run'])
            assert result.exit_code == 0
    
    def test_error_recovery_workflow(self, integration_setup):
        """Test error recovery scenarios."""
        runner = CliRunner()
        download_dir = integration_setup['download_dir']
        
        # Test dataset not found
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.cli.display_error') as mock_error:
            
            result = runner.invoke(main, ['pull', 'NONEXISTENT', str(download_dir)])
            mock_error.assert_called_with("Dataset 'NONEXISTENT' not found")
        
        # Test missing dependencies
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=False), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'), \
             patch('neurodatahub.downloader.display_error'):
            
            result = runner.invoke(main, ['pull', 'TEST_INDI', str(download_dir)])
            # Should handle missing dependencies gracefully
    
    def test_interrupted_download_workflow(self, integration_setup):
        """Test handling of interrupted downloads."""
        runner = CliRunner()
        download_dir = integration_setup['download_dir']
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=True), \
             patch('neurodatahub.downloader.run_command', side_effect=KeyboardInterrupt), \
             patch('neurodatahub.cli.get_confirmation', return_value=True), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'):
            
            # Should handle KeyboardInterrupt gracefully
            result = runner.invoke(main, ['pull', 'TEST_INDI', str(download_dir)])


class TestRealDatasetIntegration:
    """Test integration with real dataset configurations."""
    
    def test_load_real_datasets_config(self):
        """Test loading the actual datasets.json file."""
        pytest.skip("Skipping integration test - requires get_config_path function")
    
    def test_real_dataset_validation(self):
        """Test validation of real dataset entries."""
        datasets_file = Path(__file__).parent.parent.parent / "data" / "datasets.json"
        
        if not datasets_file.exists():
            pytest.skip("Real datasets.json not found")
        
        with open(datasets_file) as f:
            config = json.load(f)
        
        required_dataset_fields = ['name', 'category', 'description', 'auth_required', 'download_method']
        
        for dataset_id, dataset in config['datasets'].items():
            # Check required fields
            for field in required_dataset_fields:
                assert field in dataset, f"Dataset {dataset_id} missing field {field}"
            
            # Check valid category
            assert dataset['category'] in config['categories'], \
                f"Dataset {dataset_id} has invalid category {dataset['category']}"
            
            # Check valid download method
            assert dataset['download_method'] in config['download_methods'], \
                f"Dataset {dataset_id} has invalid download method {dataset['download_method']}"
    
    def test_cli_with_real_config(self):
        """Test CLI commands with real configuration."""
        runner = CliRunner()
        datasets_file = Path(__file__).parent.parent.parent / "data" / "datasets.json"
        
        if not datasets_file.exists():
            pytest.skip("Real datasets.json not found")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(datasets_file, *args)), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'):
            
            # Test listing real datasets
            result = runner.invoke(main, ['--list'])
            assert result.exit_code == 0
            
            # Test categories
            result = runner.invoke(main, ['categories'])
            assert result.exit_code == 0
            
            # Test stats
            result = runner.invoke(main, ['stats'])
            assert result.exit_code == 0


class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""
    
    def test_multiple_cli_instances(self, integration_setup):
        """Test multiple CLI instances running concurrently."""
        # This test would ideally use threading or multiprocessing
        # For now, we'll test that the CLI can handle rapid successive calls
        
        runner = CliRunner()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'):
            
            # Rapid successive calls
            results = []
            for _ in range(5):
                result = runner.invoke(main, ['--list'])
                results.append(result.exit_code)
            
            assert all(code == 0 for code in results)
    
    def test_dataset_manager_thread_safety(self, integration_setup):
        """Test dataset manager thread safety."""
        # Create multiple dataset managers simultaneously
        managers = []
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(integration_setup['datasets_file'], *args)):
            
            for _ in range(3):
                manager = DatasetManager()
                managers.append(manager)
            
            # All managers should have loaded the same data
            first_datasets = set(managers[0].datasets.keys())
            for manager in managers[1:]:
                assert set(manager.datasets.keys()) == first_datasets


class TestLargeDatasetHandling:
    """Test handling of large dataset configurations."""
    
    def test_large_dataset_list(self, temp_dir):
        """Test handling of large numbers of datasets."""
        # Create a configuration with many datasets
        large_config = {
            "datasets": {},
            "categories": {"test": {"name": "Test", "description": "Test category", "auth_required": False}},
            "download_methods": {"test": {"name": "Test", "description": "Test method", "dependencies": []}}
        }
        
        # Generate 1000 test datasets
        for i in range(1000):
            large_config["datasets"][f"TEST_{i:03d}"] = {
                "name": f"Test Dataset {i}",
                "category": "test",
                "description": f"Test dataset number {i}",
                "size": f"~{i}MB",
                "auth_required": i % 2 == 0,  # Alternate auth requirements
                "download_method": "test",
                "base_command": f"echo test_{i}",
                "website": f"https://example.com/test_{i}"
            }
        
        datasets_file = temp_dir / "large_datasets.json"
        with open(datasets_file, 'w') as f:
            json.dump(large_config, f)
        
        runner = CliRunner()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=lambda f, *args: open(datasets_file, *args)), \
             patch('neurodatahub.cli.console'), \
             patch('neurodatahub.datasets.console'):
            
            # Test that large dataset list doesn't cause performance issues
            result = runner.invoke(main, ['--list'])
            assert result.exit_code == 0
            
            # Test search with large dataset
            result = runner.invoke(main, ['search', '500'])
            assert result.exit_code == 0
            
            # Test stats with large dataset
            result = runner.invoke(main, ['stats'])
            assert result.exit_code == 0