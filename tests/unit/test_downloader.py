"""Unit tests for downloader module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from neurodatahub.downloader import (
    Aria2cDownloader,
    AwsS3Downloader,
    BaseDownloader,
    DataladDownloader,
    DownloadError,
    DownloadManager,
    RequestsDownloader
)


class TestBaseDownloader:
    """Test BaseDownloader class."""
    
    def test_init(self, sample_dataset, temp_dir):
        """Test BaseDownloader initialization."""
        downloader = BaseDownloader(sample_dataset, str(temp_dir))
        assert downloader.dataset == sample_dataset
        assert downloader.target_path == temp_dir
        assert downloader.dataset_name == sample_dataset['name']
        assert downloader.dataset_size == sample_dataset['size']
    
    def test_prepare_success(self, sample_dataset, temp_dir):
        """Test successful preparation."""
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True):
            downloader = BaseDownloader(sample_dataset, str(temp_dir))
            assert downloader.prepare() is True
    
    def test_prepare_invalid_path(self, sample_dataset, temp_dir):
        """Test preparation with invalid path."""
        with patch('neurodatahub.downloader.validate_path', return_value=False):
            downloader = BaseDownloader(sample_dataset, str(temp_dir))
            assert downloader.prepare() is False
    
    def test_prepare_insufficient_space(self, sample_dataset, temp_dir):
        """Test preparation with insufficient disk space."""
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=False):
            downloader = BaseDownloader(sample_dataset, str(temp_dir))
            assert downloader.prepare() is False
    
    def test_download_not_implemented(self, sample_dataset, temp_dir):
        """Test that download method raises NotImplementedError."""
        downloader = BaseDownloader(sample_dataset, str(temp_dir))
        with pytest.raises(NotImplementedError):
            downloader.download()


class TestAwsS3Downloader:
    """Test AwsS3Downloader class."""
    
    def test_init(self, sample_dataset, temp_dir):
        """Test AwsS3Downloader initialization."""
        downloader = AwsS3Downloader(sample_dataset, str(temp_dir))
        assert downloader.base_command == sample_dataset['base_command']
        assert downloader.requires_credentials is False
    
    def test_init_with_credentials(self, sample_auth_dataset, temp_dir):
        """Test initialization with credentials required."""
        downloader = AwsS3Downloader(sample_auth_dataset, str(temp_dir))
        assert downloader.requires_credentials is True
    
    def test_prepare_success(self, sample_dataset, temp_dir):
        """Test successful preparation."""
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=True):
            downloader = AwsS3Downloader(sample_dataset, str(temp_dir))
            assert downloader.prepare() is True
    
    def test_prepare_missing_aws_cli(self, sample_dataset, temp_dir):
        """Test preparation with missing AWS CLI."""
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=False), \
             patch('neurodatahub.downloader.display_error'):
            downloader = AwsS3Downloader(sample_dataset, str(temp_dir))
            assert downloader.prepare() is False
    
    def test_prepare_missing_credentials(self, sample_auth_dataset, temp_dir):
        """Test preparation with missing AWS credentials."""
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=True), \
             patch('neurodatahub.downloader.run_command', return_value=(1, "", "error")), \
             patch('neurodatahub.downloader.display_error'):
            downloader = AwsS3Downloader(sample_auth_dataset, str(temp_dir))
            assert downloader.prepare() is False
    
    def test_download_success(self, sample_dataset, temp_dir):
        """Test successful download."""
        with patch('neurodatahub.downloader.run_command', return_value=(0, "success", "")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('time.time', side_effect=[0, 10]):  # Mock timing
            downloader = AwsS3Downloader(sample_dataset, str(temp_dir))
            assert downloader.download() is True
    
    def test_download_failure(self, sample_dataset, temp_dir):
        """Test failed download."""
        with patch('neurodatahub.downloader.run_command', return_value=(1, "", "error")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_error'):
            downloader = AwsS3Downloader(sample_dataset, str(temp_dir))
            assert downloader.download() is False
    
    def test_download_dry_run(self, sample_dataset, temp_dir):
        """Test dry run download."""
        with patch('neurodatahub.downloader.display_info'):
            downloader = AwsS3Downloader(sample_dataset, str(temp_dir))
            assert downloader.download(dry_run=True) is True
    
    def test_download_no_command(self, temp_dir):
        """Test download with no base command."""
        dataset_no_cmd = {'name': 'Test', 'base_command': ''}
        with patch('neurodatahub.downloader.display_error'):
            downloader = AwsS3Downloader(dataset_no_cmd, str(temp_dir))
            assert downloader.download() is False


class TestAria2cDownloader:
    """Test Aria2cDownloader class."""
    
    def test_prepare_success(self, sample_dataset, temp_dir):
        """Test successful preparation."""
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=True):
            downloader = Aria2cDownloader(sample_dataset, str(temp_dir))
            assert downloader.prepare() is True
    
    def test_prepare_missing_aria2c(self, sample_dataset, temp_dir):
        """Test preparation with missing aria2c."""
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=False), \
             patch('neurodatahub.downloader.display_error'):
            downloader = Aria2cDownloader(sample_dataset, str(temp_dir))
            assert downloader.prepare() is False
    
    def test_download_single_file(self, temp_dir):
        """Test downloading single file."""
        dataset = {
            'name': 'Test Dataset',
            'base_command': 'aria2c -x 10 http://example.com/file.tar'
        }
        with patch('neurodatahub.downloader.run_command', return_value=(0, "", "")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('time.time', side_effect=[0, 10]):
            downloader = Aria2cDownloader(dataset, str(temp_dir))
            assert downloader.download() is True
    
    def test_download_multiple_files_oasis1(self, temp_dir):
        """Test downloading multiple OASIS-1 files."""
        dataset = {
            'name': 'OASIS1',
            'base_command': 'multiple_aria2c_downloads'
        }
        with patch('neurodatahub.downloader.run_command', return_value=(0, "", "")), \
             patch('neurodatahub.downloader.display_info'):
            downloader = Aria2cDownloader(dataset, str(temp_dir))
            assert downloader.download() is True
    
    def test_download_multiple_files_failure(self, temp_dir):
        """Test failure in multiple file download."""
        dataset = {
            'name': 'OASIS1',
            'base_command': 'multiple_aria2c_downloads'
        }
        with patch('neurodatahub.downloader.run_command', return_value=(1, "", "error")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_error'):
            downloader = Aria2cDownloader(dataset, str(temp_dir))
            assert downloader.download() is False
    
    def test_download_unknown_multiple(self, temp_dir):
        """Test multiple download for unknown dataset."""
        dataset = {
            'name': 'UNKNOWN',
            'base_command': 'multiple_aria2c_downloads'
        }
        with patch('neurodatahub.downloader.display_error'):
            downloader = Aria2cDownloader(dataset, str(temp_dir))
            assert downloader.download() is False


class TestDataladDownloader:
    """Test DataladDownloader class."""
    
    def test_prepare_success(self, temp_dir):
        """Test successful preparation."""
        dataset = {
            'name': 'Test Dataset',
            'repository': 'https://github.com/test/repo.git'
        }
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', return_value=True):
            downloader = DataladDownloader(dataset, str(temp_dir))
            assert downloader.prepare() is True
    
    def test_prepare_missing_dependencies(self, temp_dir):
        """Test preparation with missing dependencies."""
        dataset = {
            'name': 'Test Dataset',
            'repository': 'https://github.com/test/repo.git'
        }
        def mock_check_dep(cmd):
            return cmd not in ['git', 'datalad']
        
        with patch('neurodatahub.downloader.validate_path', return_value=True), \
             patch('neurodatahub.downloader.check_available_space', return_value=True), \
             patch('neurodatahub.downloader.check_dependency', side_effect=mock_check_dep), \
             patch('neurodatahub.downloader.display_error'):
            downloader = DataladDownloader(dataset, str(temp_dir))
            assert downloader.prepare() is False
    
    def test_download_success(self, temp_dir):
        """Test successful download."""
        dataset = {
            'name': 'Test Dataset',
            'repository': 'https://github.com/test/repo.git',
            'base_command': 'git clone https://github.com/test/repo.git && datalad get *'
        }
        original_cwd = os.getcwd()
        
        with patch('neurodatahub.downloader.run_command', return_value=(0, "", "")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('os.getcwd', return_value=original_cwd), \
             patch('os.chdir'):
            downloader = DataladDownloader(dataset, str(temp_dir))
            assert downloader.download() is True
    
    def test_download_no_repository(self, temp_dir):
        """Test download with no repository."""
        dataset = {
            'name': 'Test Dataset',
            'repository': ''
        }
        with patch('neurodatahub.downloader.display_error'):
            downloader = DataladDownloader(dataset, str(temp_dir))
            assert downloader.download() is False
    
    def test_download_command_failure(self, temp_dir):
        """Test download with command failure."""
        dataset = {
            'name': 'Test Dataset',
            'repository': 'https://github.com/test/repo.git',
            'base_command': 'git clone https://github.com/test/repo.git && datalad get *'
        }
        
        with patch('neurodatahub.downloader.run_command', return_value=(1, "", "error")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_error'), \
             patch('os.chdir'):
            downloader = DataladDownloader(dataset, str(temp_dir))
            assert downloader.download() is False
    
    def test_download_exception(self, temp_dir):
        """Test download with exception."""
        dataset = {
            'name': 'Test Dataset',
            'repository': 'https://github.com/test/repo.git',
            'base_command': 'git clone https://github.com/test/repo.git'
        }
        
        with patch('os.chdir') as mock_chdir, \
             patch('neurodatahub.downloader.display_error'):
            # First call (to target_path) fails, second call (back to original) succeeds
            mock_chdir.side_effect = [OSError("Permission denied"), None]
            downloader = DataladDownloader(dataset, str(temp_dir))
            assert downloader.download() is False


class TestRequestsDownloader:
    """Test RequestsDownloader class."""
    
    def test_download_success(self, sample_dataset, temp_dir):
        """Test successful download."""
        url = "http://example.com/test.tar.gz"
        
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content.return_value = [b'test data chunk 1', b'test data chunk 2']
        
        with patch('requests.get', return_value=mock_response), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('tqdm.tqdm') as mock_tqdm:
            
            mock_tqdm.return_value.__enter__.return_value = MagicMock()
            downloader = RequestsDownloader(sample_dataset, str(temp_dir), url)
            assert downloader.download() is True
    
    def test_download_no_content_length(self, sample_dataset, temp_dir):
        """Test download without content-length header."""
        url = "http://example.com/test.tar.gz"
        
        mock_response = MagicMock()
        mock_response.headers = {}  # No content-length
        mock_response.iter_content.return_value = [b'test data']
        
        with patch('requests.get', return_value=mock_response), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'):
            downloader = RequestsDownloader(sample_dataset, str(temp_dir), url)
            assert downloader.download() is True
    
    def test_download_request_exception(self, sample_dataset, temp_dir):
        """Test download with request exception."""
        url = "http://example.com/test.tar.gz"
        
        with patch('requests.get', side_effect=requests.RequestException("Network error")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_error'):
            downloader = RequestsDownloader(sample_dataset, str(temp_dir), url)
            assert downloader.download() is False
    
    def test_download_file_write_error(self, sample_dataset, temp_dir):
        """Test download with file write error."""
        url = "http://example.com/test.tar.gz"
        
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content.return_value = [b'test data']
        
        with patch('requests.get', return_value=mock_response), \
             patch('builtins.open', side_effect=IOError("Write error")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_error'):
            downloader = RequestsDownloader(sample_dataset, str(temp_dir), url)
            assert downloader.download() is False
    
    def test_download_dry_run(self, sample_dataset, temp_dir):
        """Test dry run download."""
        url = "http://example.com/test.tar.gz"
        with patch('neurodatahub.downloader.display_info'):
            downloader = RequestsDownloader(sample_dataset, str(temp_dir), url)
            assert downloader.download(dry_run=True) is True


class TestDownloadManager:
    """Test DownloadManager class."""
    
    def test_get_downloader_aws_s3(self, sample_dataset, temp_dir):
        """Test getting AWS S3 downloader."""
        manager = DownloadManager()
        downloader = manager.get_downloader(sample_dataset, str(temp_dir))
        assert isinstance(downloader, AwsS3Downloader)
    
    def test_get_downloader_aria2c(self, temp_dir):
        """Test getting aria2c downloader."""
        dataset = {'download_method': 'aria2c'}
        manager = DownloadManager()
        downloader = manager.get_downloader(dataset, str(temp_dir))
        assert isinstance(downloader, Aria2cDownloader)
    
    def test_get_downloader_datalad(self, temp_dir):
        """Test getting DataLad downloader."""
        dataset = {'download_method': 'datalad'}
        manager = DownloadManager()
        downloader = manager.get_downloader(dataset, str(temp_dir))
        assert isinstance(downloader, DataladDownloader)
    
    def test_get_downloader_ida_loni(self, temp_dir):
        """Test getting downloader for IDA-LONI dataset."""
        dataset = {'download_method': 'ida_loni'}
        manager = DownloadManager()
        with patch('neurodatahub.downloader.display_error'):
            downloader = manager.get_downloader(dataset, str(temp_dir))
            assert downloader is None
    
    def test_get_downloader_special(self, temp_dir):
        """Test getting downloader for special dataset."""
        dataset = {'download_method': 'special'}
        manager = DownloadManager()
        with patch('neurodatahub.downloader.display_error'):
            downloader = manager.get_downloader(dataset, str(temp_dir))
            assert downloader is None
    
    def test_get_downloader_unknown(self, temp_dir):
        """Test getting downloader for unknown method."""
        dataset = {'download_method': 'unknown'}
        manager = DownloadManager()
        with patch('neurodatahub.downloader.display_warning'):
            downloader = manager.get_downloader(dataset, str(temp_dir))
            assert downloader is None
    
    def test_download_dataset_success(self, sample_dataset, temp_dir):
        """Test successful dataset download."""
        manager = DownloadManager()
        
        mock_downloader = MagicMock()
        mock_downloader.prepare.return_value = True
        mock_downloader.download.return_value = True
        
        with patch.object(manager, 'get_downloader', return_value=mock_downloader):
            result = manager.download_dataset(sample_dataset, str(temp_dir))
            assert result is True
            mock_downloader.prepare.assert_called_once()
            mock_downloader.download.assert_called_once_with(False)
            mock_downloader.cleanup.assert_called_once()
    
    def test_download_dataset_prepare_failure(self, sample_dataset, temp_dir):
        """Test dataset download with prepare failure."""
        manager = DownloadManager()
        
        mock_downloader = MagicMock()
        mock_downloader.prepare.return_value = False
        
        with patch.object(manager, 'get_downloader', return_value=mock_downloader):
            result = manager.download_dataset(sample_dataset, str(temp_dir))
            assert result is False
            mock_downloader.prepare.assert_called_once()
            mock_downloader.download.assert_not_called()
    
    def test_download_dataset_download_failure(self, sample_dataset, temp_dir):
        """Test dataset download with download failure."""
        manager = DownloadManager()
        
        mock_downloader = MagicMock()
        mock_downloader.prepare.return_value = True
        mock_downloader.download.return_value = False
        
        with patch.object(manager, 'get_downloader', return_value=mock_downloader):
            result = manager.download_dataset(sample_dataset, str(temp_dir))
            assert result is False
            mock_downloader.cleanup.assert_called_once()
    
    def test_download_dataset_exception(self, sample_dataset, temp_dir):
        """Test dataset download with exception."""
        manager = DownloadManager()
        
        mock_downloader = MagicMock()
        mock_downloader.prepare.return_value = True
        mock_downloader.download.side_effect = Exception("Download error")
        
        with patch.object(manager, 'get_downloader', return_value=mock_downloader), \
             patch('neurodatahub.downloader.display_error'):
            result = manager.download_dataset(sample_dataset, str(temp_dir))
            assert result is False
            mock_downloader.cleanup.assert_called_once()
    
    def test_download_dataset_no_downloader(self, sample_dataset, temp_dir):
        """Test dataset download with no suitable downloader."""
        manager = DownloadManager()
        
        with patch.object(manager, 'get_downloader', return_value=None), \
             patch.object(manager, '_try_fallback_download', return_value=False):
            result = manager.download_dataset(sample_dataset, str(temp_dir))
            assert result is False
    
    def test_try_fallback_download_with_url(self, temp_dir):
        """Test fallback download with URL in base command."""
        dataset = {
            'name': 'Test',
            'base_command': 'aria2c https://example.com/test.tar.gz'
        }
        manager = DownloadManager()
        
        with patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.RequestsDownloader') as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.download.return_value = True
            mock_downloader_class.return_value = mock_downloader
            
            result = manager._try_fallback_download(dataset, str(temp_dir))
            assert result is True
    
    def test_try_fallback_download_no_url(self, temp_dir):
        """Test fallback download with no URL."""
        dataset = {
            'name': 'Test',
            'base_command': 'some command without url'
        }
        manager = DownloadManager()
        
        with patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_error'):
            result = manager._try_fallback_download(dataset, str(temp_dir))
            assert result is False


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_downloader_with_empty_dataset(self, temp_dir):
        """Test downloader with empty dataset."""
        empty_dataset = {}
        downloader = BaseDownloader(empty_dataset, str(temp_dir))
        assert downloader.dataset_name == 'Unknown Dataset'
        assert downloader.dataset_size == 'Unknown'
    
    def test_aws_downloader_command_with_spaces(self, temp_dir):
        """Test AWS downloader with spaces in target path."""
        dataset = {
            'name': 'Test',
            'base_command': 'aws s3 sync s3://bucket/ .'
        }
        spaced_path = temp_dir / "path with spaces"
        spaced_path.mkdir()
        
        with patch('neurodatahub.downloader.run_command', return_value=(0, "", "")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('time.time', side_effect=[0, 1]):
            downloader = AwsS3Downloader(dataset, str(spaced_path))
            assert downloader.download() is True
    
    def test_aria2c_multiple_download_edge_cases(self, temp_dir):
        """Test aria2c multiple download edge cases."""
        # Test OASIS2 specific case
        dataset_oasis2 = {
            'name': 'OASIS2',
            'base_command': 'multiple_aria2c_downloads'
        }
        
        with patch('neurodatahub.downloader.run_command', return_value=(0, "", "")), \
             patch('neurodatahub.downloader.display_info'):
            downloader = Aria2cDownloader(dataset_oasis2, str(temp_dir))
            assert downloader.download() is True
    
    def test_requests_downloader_filename_extraction(self, sample_dataset, temp_dir):
        """Test filename extraction from URL."""
        # URL without filename
        url_no_filename = "http://example.com/"
        
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b'data']
        
        with patch('requests.get', return_value=mock_response), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'):
            downloader = RequestsDownloader(sample_dataset, str(temp_dir), url_no_filename)
            result = downloader.download()
            assert result is True
    
    def test_dataład_download_with_complex_commands(self, temp_dir):
        """Test DataLad download with complex command sequences."""
        dataset = {
            'name': 'Complex Dataset',
            'repository': 'https://github.com/test/repo.git',
            'base_command': 'git clone repo.git && cd repo && datalad get . && datalad unlock data/*'
        }
        
        # Mock successful execution of all commands
        with patch('neurodatahub.downloader.run_command', return_value=(0, "", "")), \
             patch('neurodatahub.downloader.display_info'), \
             patch('neurodatahub.downloader.display_success'), \
             patch('os.chdir'):
            downloader = DataladDownloader(dataset, str(temp_dir))
            assert downloader.download() is True