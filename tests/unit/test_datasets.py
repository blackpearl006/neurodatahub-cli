"""Unit tests for datasets module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from neurodatahub.datasets import DatasetManager


class TestDatasetManager:
    """Test DatasetManager class."""
    
    def test_init_loads_datasets(self, mock_datasets_config, temp_dir):
        """Test DatasetManager initialization loads datasets."""
        datasets_file = temp_dir / "datasets.json"
        with open(datasets_file, 'w') as f:
            json.dump(mock_datasets_config, f)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mock_datasets_config))):
            manager = DatasetManager()
            assert len(manager.datasets) == 2
            assert 'TEST1' in manager.datasets
            assert 'TEST2' in manager.datasets
    
    def test_init_file_not_found(self):
        """Test DatasetManager when datasets.json not found."""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('neurodatahub.datasets.display_error') as mock_error:
            manager = DatasetManager()
            assert manager.datasets == {}
            mock_error.assert_called_once()
    
    def test_init_invalid_json(self):
        """Test DatasetManager with invalid JSON."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="invalid json")), \
             patch('neurodatahub.datasets.display_error') as mock_error:
            manager = DatasetManager()
            assert manager.datasets == {}
            mock_error.assert_called_once()
    
    def test_get_dataset_exists(self, mock_dataset_manager, sample_dataset):
        """Test getting existing dataset."""
        manager = mock_dataset_manager({'TEST': sample_dataset})
        result = manager.get_dataset('test')  # Test case insensitive
        assert result == sample_dataset
    
    def test_get_dataset_not_exists(self, mock_dataset_manager):
        """Test getting non-existent dataset."""
        manager = mock_dataset_manager({})
        result = manager.get_dataset('nonexistent')
        assert result is None
    
    def test_list_datasets_no_filter(self, mock_dataset_manager, sample_dataset, sample_auth_dataset):
        """Test listing all datasets without filter."""
        datasets = {'TEST1': sample_dataset, 'TEST2': sample_auth_dataset}
        manager = mock_dataset_manager(datasets)
        result = manager.list_datasets()
        assert len(result) == 2
        assert 'TEST1' in result
        assert 'TEST2' in result
    
    def test_list_datasets_category_filter(self, mock_dataset_manager, sample_dataset):
        """Test listing datasets with category filter."""
        dataset_test = sample_dataset.copy()
        dataset_test['category'] = 'test'
        dataset_other = sample_dataset.copy()
        dataset_other['category'] = 'other'
        
        datasets = {'TEST1': dataset_test, 'TEST2': dataset_other}
        manager = mock_dataset_manager(datasets)
        result = manager.list_datasets(category='test')
        assert len(result) == 1
        assert 'TEST1' in result
    
    def test_list_datasets_auth_filter(self, mock_dataset_manager, sample_dataset, sample_auth_dataset):
        """Test listing datasets with auth filter."""
        datasets = {'TEST1': sample_dataset, 'TEST2': sample_auth_dataset}
        manager = mock_dataset_manager(datasets)
        
        # Test auth_only filter
        result = manager.list_datasets(auth_only=True)
        assert len(result) == 1
        assert 'TEST2' in result
        
        # Test no_auth_only filter
        result = manager.list_datasets(no_auth_only=True)
        assert len(result) == 1
        assert 'TEST1' in result
    
    def test_search_datasets(self, mock_dataset_manager):
        """Test searching datasets."""
        dataset1 = {
            'name': 'Brain Development Dataset',
            'description': 'Study of brain development in children'
        }
        dataset2 = {
            'name': 'Alzheimer Study',
            'description': 'Research on Alzheimer disease progression'
        }
        
        datasets = {'DEV1': dataset1, 'ALZ1': dataset2}
        manager = mock_dataset_manager(datasets)
        
        # Search by name
        result = manager.search_datasets('brain')
        assert len(result) == 1
        assert 'DEV1' in result
        
        # Search by description
        result = manager.search_datasets('alzheimer')
        assert len(result) == 1
        assert 'ALZ1' in result
        
        # Search by ID
        result = manager.search_datasets('dev1')
        assert len(result) == 1
        assert 'DEV1' in result
        
        # No matches
        result = manager.search_datasets('nonexistent')
        assert len(result) == 0
    
    def test_validate_dataset_id(self, mock_dataset_manager, sample_dataset):
        """Test dataset ID validation."""
        manager = mock_dataset_manager({'TEST': sample_dataset})
        assert manager.validate_dataset_id('test') is True
        assert manager.validate_dataset_id('TEST') is True
        assert manager.validate_dataset_id('nonexistent') is False
    
    def test_get_datasets_by_category(self, mock_dataset_manager):
        """Test getting datasets by category."""
        dataset1 = {'category': 'indi'}
        dataset2 = {'category': 'openneuro'}
        dataset3 = {'category': 'indi'}
        
        datasets = {'INDI1': dataset1, 'OPEN1': dataset2, 'INDI2': dataset3}
        manager = mock_dataset_manager(datasets)
        
        result = manager.get_datasets_by_category('indi')
        assert len(result) == 2
        assert 'INDI1' in result
        assert 'INDI2' in result
    
    def test_get_datasets_requiring_auth(self, mock_dataset_manager):
        """Test getting datasets requiring authentication."""
        dataset1 = {'auth_required': False}
        dataset2 = {'auth_required': True}
        dataset3 = {'auth_required': True}
        
        datasets = {'NO_AUTH': dataset1, 'AUTH1': dataset2, 'AUTH2': dataset3}
        manager = mock_dataset_manager(datasets)
        
        result = manager.get_datasets_requiring_auth()
        assert len(result) == 2
        assert 'AUTH1' in result
        assert 'AUTH2' in result
    
    def test_get_datasets_no_auth(self, mock_dataset_manager):
        """Test getting datasets not requiring authentication."""
        dataset1 = {'auth_required': False}
        dataset2 = {'auth_required': True}
        dataset3 = {}  # Missing auth_required should default to False
        
        datasets = {'NO_AUTH1': dataset1, 'AUTH1': dataset2, 'NO_AUTH2': dataset3}
        manager = mock_dataset_manager(datasets)
        
        result = manager.get_datasets_no_auth()
        assert len(result) == 2
        assert 'NO_AUTH1' in result
        assert 'NO_AUTH2' in result
    
    def test_get_dataset_stats(self, mock_dataset_manager):
        """Test getting dataset statistics."""
        datasets = {
            'INDI1': {'category': 'indi', 'auth_required': False, 'download_method': 'aws_s3'},
            'INDI2': {'category': 'indi', 'auth_required': True, 'download_method': 'aws_credentials'},
            'OPEN1': {'category': 'openneuro', 'auth_required': False, 'download_method': 'aws_s3'},
            'IDA1': {'category': 'ida', 'auth_required': True, 'download_method': 'ida_loni'},
        }
        manager = mock_dataset_manager(datasets)
        
        stats = manager.get_dataset_stats()
        
        assert stats['total'] == 4
        assert stats['by_category']['indi'] == 2
        assert stats['by_category']['openneuro'] == 1
        assert stats['by_category']['ida'] == 1
        assert stats['by_auth']['required'] == 2
        assert stats['by_auth']['not_required'] == 2
        assert stats['by_method']['aws_s3'] == 2
        assert stats['by_method']['aws_credentials'] == 1
        assert stats['by_method']['ida_loni'] == 1
    
    def test_display_datasets_table_empty(self, mock_dataset_manager):
        """Test displaying empty datasets table."""
        manager = mock_dataset_manager({})
        with patch('neurodatahub.datasets.console'):
            # Should not raise exceptions
            manager.display_datasets_table({})
    
    def test_display_datasets_table_with_data(self, mock_dataset_manager, sample_dataset):
        """Test displaying datasets table with data."""
        manager = mock_dataset_manager({'TEST': sample_dataset})
        with patch('neurodatahub.datasets.console'):
            # Should not raise exceptions
            manager.display_datasets_table({'TEST': sample_dataset})
            manager.display_datasets_table({'TEST': sample_dataset}, detailed=True)
    
    def test_display_categories_table(self, mock_dataset_manager):
        """Test displaying categories table."""
        manager = mock_dataset_manager({})
        manager.categories = {
            'indi': {
                'name': 'INDI',
                'description': 'INDI datasets',
                'auth_required': False
            }
        }
        manager.datasets = {'INDI1': {'category': 'indi'}}
        
        with patch('neurodatahub.datasets.console'):
            # Should not raise exceptions
            manager.display_categories_table()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_dataset_manager_with_malformed_config(self):
        """Test DatasetManager with malformed configuration."""
        malformed_config = {
            "datasets": "not_a_dict",  # Should be dict
            "categories": None,        # Should be dict
        }
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(malformed_config))):
            manager = DatasetManager()
            # Should handle gracefully
            assert manager.datasets == "not_a_dict"
            assert manager.categories is None
    
    def test_search_with_special_characters(self, mock_dataset_manager):
        """Test search with special characters."""
        dataset = {
            'name': 'Test Dataset (2024)',
            'description': 'Dataset with special chars: @#$%'
        }
        manager = mock_dataset_manager({'SPECIAL': dataset})
        
        # Should handle special characters without errors
        result = manager.search_datasets('(2024)')
        assert len(result) == 1
        
        result = manager.search_datasets('@#$')
        assert len(result) == 1
    
    def test_case_insensitive_operations(self, mock_dataset_manager, sample_dataset):
        """Test case insensitive operations."""
        manager = mock_dataset_manager({'TEST_DATASET': sample_dataset})
        
        # Test case insensitive dataset retrieval
        assert manager.get_dataset('test_dataset') is not None
        assert manager.get_dataset('TEST_DATASET') is not None
        assert manager.get_dataset('Test_Dataset') is not None
    
    def test_list_datasets_with_missing_fields(self, mock_dataset_manager):
        """Test listing datasets with missing fields."""
        incomplete_dataset = {
            'name': 'Incomplete Dataset'
            # Missing category, auth_required, etc.
        }
        manager = mock_dataset_manager({'INCOMPLETE': incomplete_dataset})
        
        # Should handle missing fields gracefully
        result = manager.list_datasets(category='missing')
        assert len(result) == 0
        
        result = manager.list_datasets(auth_only=True)
        assert len(result) == 0
        
        result = manager.list_datasets(no_auth_only=True)
        assert len(result) == 1  # Missing auth_required defaults to False
    
    def test_unicode_handling(self, mock_dataset_manager):
        """Test handling of unicode characters in dataset info."""
        unicode_dataset = {
            'name': 'Données Neuroscientifiques',
            'description': 'Dataset with unicode: αβγ δεζ 中文 русский'
        }
        manager = mock_dataset_manager({'UNICODE': unicode_dataset})
        
        # Should handle unicode without errors
        result = manager.search_datasets('données')
        assert len(result) == 1
        
        result = manager.search_datasets('中文')
        assert len(result) == 1