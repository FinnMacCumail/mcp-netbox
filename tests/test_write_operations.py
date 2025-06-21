"""
Tests for NetBox client write operations with safety mechanisms
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import copy

from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import NetBoxConfig, SafetyConfig
from netbox_mcp.exceptions import (
    NetBoxConfirmationError,
    NetBoxValidationError,
    NetBoxWriteError,
    NetBoxNotFoundError,
    NetBoxError
)


@pytest.fixture
def write_config():
    """Create a NetBox configuration for write testing."""
    return NetBoxConfig(
        url="https://netbox.test.com",
        token="test-token-123",
        timeout=30,
        verify_ssl=True,
        safety=SafetyConfig(
            dry_run_mode=False,
            enable_write_operations=True
        )
    )


@pytest.fixture
def dry_run_config():
    """Create a NetBox configuration with dry-run mode enabled."""
    return NetBoxConfig(
        url="https://netbox.test.com",
        token="test-token-123",
        timeout=30,
        verify_ssl=True,
        safety=SafetyConfig(
            dry_run_mode=True,
            enable_write_operations=True
        )
    )


@pytest.fixture
def mock_api():
    """Create a mock pynetbox API."""
    api = Mock()
    api.dcim = Mock()
    api.dcim.manufacturers = Mock()
    api.dcim.devices = Mock()
    api.dcim.sites = Mock()
    api.ipam = Mock()
    api.ipam.ip_addresses = Mock()
    api.extras = Mock()
    api.extras.tags = Mock()
    return api


class TestWriteOperationSafety:
    """Test write operation safety mechanisms."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_create_without_confirm_raises_error(self, mock_pynetbox_api, write_config, mock_api):
        """Test that create operations require confirm=True."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        with pytest.raises(NetBoxConfirmationError, match="requires confirm=True for safety"):
            client.create_object('manufacturers', {'name': 'Test Vendor'})
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_update_without_confirm_raises_error(self, mock_pynetbox_api, write_config, mock_api):
        """Test that update operations require confirm=True."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        with pytest.raises(NetBoxConfirmationError, match="requires confirm=True for safety"):
            client.update_object('manufacturers', 1, {'name': 'Updated Vendor'})
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_delete_without_confirm_raises_error(self, mock_pynetbox_api, write_config, mock_api):
        """Test that delete operations require confirm=True."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        with pytest.raises(NetBoxConfirmationError, match="requires confirm=True for safety"):
            client.delete_object('manufacturers', 1)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_invalid_data_raises_validation_error(self, mock_pynetbox_api, write_config, mock_api):
        """Test that invalid data raises validation errors."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Test empty data
        with pytest.raises(NetBoxValidationError, match="must be a non-empty dictionary"):
            client.create_object('manufacturers', {}, confirm=True)
        
        # Test None data
        with pytest.raises(NetBoxValidationError, match="must be a non-empty dictionary"):
            client.create_object('manufacturers', None, confirm=True)
        
        # Test non-dict data
        with pytest.raises(NetBoxValidationError, match="must be a non-empty dictionary"):
            client.create_object('manufacturers', "invalid", confirm=True)


class TestDryRunMode:
    """Test dry-run mode functionality."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_dry_run_create_simulation(self, mock_pynetbox_api, dry_run_config, mock_api):
        """Test that dry-run mode simulates create operations."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(dry_run_config)
        
        data = {'name': 'Test Vendor', 'slug': 'test-vendor'}
        result = client.create_object('manufacturers', data, confirm=True)
        
        # Should return simulated result
        assert result['dry_run'] is True
        assert result['id'] == 999999  # Fake ID
        assert result['name'] == 'Test Vendor'
        assert result['slug'] == 'test-vendor'
        
        # Should not have called the actual API
        mock_api.dcim.manufacturers.create.assert_not_called()
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_dry_run_update_simulation(self, mock_pynetbox_api, dry_run_config, mock_api):
        """Test that dry-run mode simulates update operations."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(dry_run_config)
        
        # Mock existing object
        existing_obj = Mock()
        existing_obj.id = 1
        existing_obj.name = 'Original Vendor'
        existing_obj.slug = 'original-vendor'
        existing_obj.serialize.return_value = {
            'id': 1,
            'name': 'Original Vendor',
            'slug': 'original-vendor'
        }
        mock_api.dcim.manufacturers.get.return_value = existing_obj
        
        update_data = {'name': 'Updated Vendor'}
        result = client.update_object('manufacturers', 1, update_data, confirm=True)
        
        # Should return simulated result
        assert result['dry_run'] is True
        assert result['id'] == 1
        assert result['name'] == 'Updated Vendor'
        assert result['slug'] == 'original-vendor'  # Unchanged field
        
        # Should not have called save
        existing_obj.save.assert_not_called()
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_dry_run_delete_simulation(self, mock_pynetbox_api, dry_run_config, mock_api):
        """Test that dry-run mode simulates delete operations."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(dry_run_config)
        
        # Mock existing object
        existing_obj = Mock()
        existing_obj.id = 1
        existing_obj.serialize.return_value = {
            'id': 1,
            'name': 'Test Vendor'
        }
        mock_api.dcim.manufacturers.get.return_value = existing_obj
        
        result = client.delete_object('manufacturers', 1, confirm=True)
        
        # Should return simulated result
        assert result['dry_run'] is True
        assert result['deleted'] is True
        assert result['object_id'] == 1
        assert result['object_type'] == 'manufacturers'
        assert result['original_data']['id'] == 1
        
        # Should not have called delete
        existing_obj.delete.assert_not_called()


class TestCreateOperations:
    """Test create operations."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_successful_create(self, mock_pynetbox_api, write_config, mock_api):
        """Test successful object creation."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock successful creation
        created_obj = Mock()
        created_obj.id = 1
        created_obj.name = 'Test Vendor'
        created_obj.serialize.return_value = {
            'id': 1,
            'name': 'Test Vendor',
            'slug': 'test-vendor'
        }
        mock_api.dcim.manufacturers.create.return_value = created_obj
        
        data = {'name': 'Test Vendor', 'slug': 'test-vendor'}
        result = client.create_object('manufacturers', data, confirm=True)
        
        # Should call the API correctly
        mock_api.dcim.manufacturers.create.assert_called_once_with(data)
        
        # Should return the created object data
        assert result['id'] == 1
        assert result['name'] == 'Test Vendor'
        assert 'dry_run' not in result
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_create_with_api_error(self, mock_pynetbox_api, write_config, mock_api):
        """Test create operation with API error."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock API error
        mock_api.dcim.manufacturers.create.side_effect = Exception("API validation error")
        
        data = {'name': 'Test Vendor'}
        with pytest.raises(NetBoxValidationError, match="Validation failed"):
            client.create_object('manufacturers', data, confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_create_unsupported_object_type(self, mock_pynetbox_api, write_config, mock_api):
        """Test create operation with unsupported object type."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        with pytest.raises(NetBoxValidationError, match="Unsupported object type"):
            client.create_object('unsupported_type', {'name': 'test'}, confirm=True)


class TestUpdateOperations:
    """Test update operations."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_successful_update(self, mock_pynetbox_api, write_config, mock_api):
        """Test successful object update."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock existing object
        existing_obj = Mock()
        existing_obj.id = 1
        existing_obj.name = 'Original Vendor'
        existing_obj.save.return_value = True
        existing_obj.serialize.return_value = {
            'id': 1,
            'name': 'Updated Vendor',
            'slug': 'original-vendor'
        }
        mock_api.dcim.manufacturers.get.return_value = existing_obj
        
        update_data = {'name': 'Updated Vendor'}
        result = client.update_object('manufacturers', 1, update_data, confirm=True)
        
        # Should have retrieved and updated the object
        mock_api.dcim.manufacturers.get.assert_called_once_with(1)
        existing_obj.save.assert_called_once()
        
        # Should return updated object data
        assert result['id'] == 1
        assert result['name'] == 'Updated Vendor'
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_update_nonexistent_object(self, mock_pynetbox_api, write_config, mock_api):
        """Test update operation on non-existent object."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock object not found
        mock_api.dcim.manufacturers.get.return_value = None
        
        with pytest.raises(NetBoxNotFoundError, match="not found"):
            client.update_object('manufacturers', 999, {'name': 'Updated'}, confirm=True)


class TestDeleteOperations:
    """Test delete operations."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_successful_delete(self, mock_pynetbox_api, write_config, mock_api):
        """Test successful object deletion."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock existing object
        existing_obj = Mock()
        existing_obj.id = 1
        existing_obj.serialize.return_value = {
            'id': 1,
            'name': 'Test Vendor'
        }
        mock_api.dcim.manufacturers.get.return_value = existing_obj
        
        result = client.delete_object('manufacturers', 1, confirm=True)
        
        # Should have retrieved and deleted the object
        mock_api.dcim.manufacturers.get.assert_called_once_with(1)
        existing_obj.delete.assert_called_once()
        
        # Should return deletion confirmation
        assert result['deleted'] is True
        assert result['object_id'] == 1
        assert result['object_type'] == 'manufacturers'
        assert result['original_data']['id'] == 1
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_delete_nonexistent_object(self, mock_pynetbox_api, write_config, mock_api):
        """Test delete operation on non-existent object."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock object not found
        mock_api.dcim.manufacturers.get.return_value = None
        
        with pytest.raises(NetBoxNotFoundError, match="not found"):
            client.delete_object('manufacturers', 999, confirm=True)


class TestEndpointMapping:
    """Test write endpoint mapping."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_dcim_endpoints(self, mock_pynetbox_api, write_config, mock_api):
        """Test DCIM endpoint mapping."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Test various DCIM endpoints
        dcim_types = ['devices', 'sites', 'manufacturers', 'device_types', 'device_roles']
        
        for object_type in dcim_types:
            endpoint = client._get_write_endpoint(object_type)
            assert endpoint is not None
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ipam_endpoints(self, mock_pynetbox_api, write_config, mock_api):
        """Test IPAM endpoint mapping."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Test various IPAM endpoints
        ipam_types = ['ip_addresses', 'prefixes', 'vlans', 'vlan_groups', 'vrfs']
        
        for object_type in ipam_types:
            endpoint = client._get_write_endpoint(object_type)
            assert endpoint is not None
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_extras_endpoints(self, mock_pynetbox_api, write_config, mock_api):
        """Test extras endpoint mapping."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Test extras endpoints
        extras_types = ['tags', 'custom_fields']
        
        for object_type in extras_types:
            endpoint = client._get_write_endpoint(object_type)
            assert endpoint is not None


class TestObjectSerialization:
    """Test object to dictionary conversion."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_object_with_serialize_method(self, mock_pynetbox_api, write_config, mock_api):
        """Test object conversion with serialize method."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock object with serialize method
        obj = Mock()
        obj.serialize.return_value = {'id': 1, 'name': 'Test'}
        
        result = client._object_to_dict(obj)
        assert result == {'id': 1, 'name': 'Test'}
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_object_without_serialize_method(self, mock_pynetbox_api, write_config, mock_api):
        """Test object conversion without serialize method."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock object without serialize method
        obj = Mock()
        del obj.serialize  # Remove serialize method
        obj.id = 1
        obj.name = 'Test'
        obj._private = 'hidden'  # Should be excluded
        
        result = client._object_to_dict(obj)
        assert 'id' in result
        assert 'name' in result
        assert '_private' not in result


class TestLogging:
    """Test write operation logging."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    @patch('netbox_mcp.client.logger')
    def test_successful_operation_logging(self, mock_logger, mock_pynetbox_api, write_config, mock_api):
        """Test logging of successful write operations."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock successful creation
        created_obj = Mock()
        created_obj.id = 1
        created_obj.serialize.return_value = {'id': 1, 'name': 'Test'}
        mock_api.dcim.manufacturers.create.return_value = created_obj
        
        data = {'name': 'Test Vendor'}
        client.create_object('manufacturers', data, confirm=True)
        
        # Should log the successful operation (checking for partial matches due to timestamps)
        success_calls = [call for call in mock_logger.info.call_args_list 
                        if "WRITE SUCCESS" in str(call) and "CREATE_MANUFACTURERS" in str(call)]
        assert len(success_calls) > 0, "Expected WRITE SUCCESS log message"
        
        data_calls = [call for call in mock_logger.info.call_args_list 
                     if f"📝 Data: {data}" in str(call)]
        assert len(data_calls) > 0, "Expected data log message"
        
        result_calls = [call for call in mock_logger.info.call_args_list 
                       if "📝 Result ID: 1" in str(call)]
        assert len(result_calls) > 0, "Expected result ID log message"
    
    @patch('netbox_mcp.client.pynetbox.api')
    @patch('netbox_mcp.client.logger')
    def test_failed_operation_logging(self, mock_logger, mock_pynetbox_api, write_config, mock_api):
        """Test logging of failed write operations."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(write_config)
        
        # Mock API error
        error = Exception("API error")
        mock_api.dcim.manufacturers.create.side_effect = error
        
        data = {'name': 'Test Vendor'}
        with pytest.raises(NetBoxWriteError):
            client.create_object('manufacturers', data, confirm=True)
        
        # Should log the failed operation (checking for partial matches due to timestamps)
        error_calls = [call for call in mock_logger.error.call_args_list 
                      if "WRITE FAILED" in str(call) and "CREATE_MANUFACTURERS" in str(call) and "API error" in str(call)]
        assert len(error_calls) > 0, "Expected WRITE FAILED log message"
        
        data_calls = [call for call in mock_logger.error.call_args_list 
                     if f"📝 Data: {data}" in str(call)]
        assert len(data_calls) > 0, "Expected data log message"