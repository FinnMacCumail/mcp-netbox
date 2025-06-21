"""
Tests for NetBox client ensure operations with hybrid pattern
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
def ensure_config():
    """Create a NetBox configuration for ensure testing."""
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
    api.dcim.sites = Mock()
    api.dcim.device_roles = Mock()
    return api


class TestEnsureManufacturer:
    """Test ensure_manufacturer hybrid pattern functionality."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_without_confirm_raises_error(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test that ensure operations require confirm=True."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        with pytest.raises(NetBoxConfirmationError, match="requires confirm=True for safety"):
            client.ensure_manufacturer(name="Cisco Systems")
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_missing_parameters_raises_error(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test that either name or manufacturer_id is required."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        with pytest.raises(NetBoxValidationError, match="Either 'name' or 'manufacturer_id' parameter is required"):
            client.ensure_manufacturer(confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_empty_name_raises_error(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test that empty name raises validation error."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        with pytest.raises(NetBoxValidationError, match="Either 'name' or 'manufacturer_id' parameter is required"):
            client.ensure_manufacturer(name="", confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_by_id_existing(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test ensure_manufacturer with direct ID injection for existing manufacturer."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock existing manufacturer
        existing_mfg = Mock()
        existing_mfg.id = 5
        existing_mfg.name = "Cisco Systems"
        existing_mfg.serialize.return_value = {
            "id": 5,
            "name": "Cisco Systems",
            "slug": "cisco-systems"
        }
        mock_api.dcim.manufacturers.get.return_value = existing_mfg
        
        result = client.ensure_manufacturer(manufacturer_id=5, confirm=True)
        
        # Should retrieve by ID directly
        mock_api.dcim.manufacturers.get.assert_called_once_with(5)
        
        # Should return unchanged result
        assert result["success"] is True
        assert result["action"] == "unchanged"
        assert result["object_type"] == "manufacturer"
        assert result["manufacturer"]["id"] == 5
        assert result["manufacturer"]["name"] == "Cisco Systems"
        assert len(result["changes"]["updated_fields"]) == 0
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_by_id_not_found(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test ensure_manufacturer with non-existent manufacturer ID."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock manufacturer not found
        mock_api.dcim.manufacturers.get.return_value = None
        
        with pytest.raises(NetBoxNotFoundError, match="Manufacturer with ID 999 not found"):
            client.ensure_manufacturer(manufacturer_id=999, confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_create_new(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test creating new manufacturer when it doesn't exist."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock no existing manufacturers
        mock_api.dcim.manufacturers.filter.return_value = []
        
        # Mock create operation
        created_mfg = Mock()
        created_mfg.id = 10
        created_mfg.serialize.return_value = {
            "id": 10,
            "name": "New Vendor",
            "slug": "new-vendor"
        }
        mock_api.dcim.manufacturers.create.return_value = created_mfg
        
        result = client.ensure_manufacturer(name="New Vendor", confirm=True)
        
        # Should check for existing first
        mock_api.dcim.manufacturers.filter.assert_called_once_with(name="New Vendor")
        
        # Should create new manufacturer
        mock_api.dcim.manufacturers.create.assert_called_once_with({"name": "New Vendor"})
        
        # Should return created result
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["object_type"] == "manufacturer"
        assert result["manufacturer"]["id"] == 10
        assert result["manufacturer"]["name"] == "New Vendor"
        assert "name" in result["changes"]["created_fields"]
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_update_existing(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test updating existing manufacturer when fields differ."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock existing manufacturer with different description
        existing_mfg = Mock()
        existing_mfg.id = 5
        existing_mfg.serialize.return_value = {
            "id": 5,
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Old description"
        }
        mock_api.dcim.manufacturers.filter.return_value = [existing_mfg]
        
        # Mock update operation
        updated_mfg = Mock()
        updated_mfg.serialize.return_value = {
            "id": 5,
            "name": "Cisco Systems", 
            "slug": "cisco-systems",
            "description": "Updated description"
        }
        mock_api.dcim.manufacturers.get.return_value = existing_mfg
        existing_mfg.save.return_value = True
        
        # Mock the update_object call to return updated data
        with patch.object(client, 'update_object', return_value=updated_mfg.serialize()) as mock_update:
            result = client.ensure_manufacturer(
                name="Cisco Systems", 
                description="Updated description", 
                confirm=True
            )
        
        # Should update the manufacturer
        mock_update.assert_called_once_with(
            "manufacturers", 
            5, 
            {"name": "Cisco Systems", "description": "Updated description"}, 
            confirm=True
        )
        
        # Should return updated result
        assert result["success"] is True
        assert result["action"] == "updated"
        assert result["object_type"] == "manufacturer"
        assert "description" in result["changes"]["updated_fields"]
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_unchanged_existing(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test ensuring manufacturer that already has desired state."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock existing manufacturer with matching state
        existing_mfg = Mock()
        existing_mfg.id = 5
        existing_mfg.serialize.return_value = {
            "id": 5,
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment"
        }
        mock_api.dcim.manufacturers.filter.return_value = [existing_mfg]
        
        result = client.ensure_manufacturer(
            name="Cisco Systems",
            description="Network equipment",
            confirm=True
        )
        
        # Should not call update or create
        mock_api.dcim.manufacturers.create.assert_not_called()
        
        # Should return unchanged result
        assert result["success"] is True
        assert result["action"] == "unchanged"
        assert result["object_type"] == "manufacturer"
        assert len(result["changes"]["updated_fields"]) == 0
        assert len(result["changes"]["unchanged_fields"]) > 0


class TestEnsureSite:
    """Test ensure_site hybrid pattern functionality."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_site_create_new(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test creating new site."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock no existing sites
        mock_api.dcim.sites.filter.return_value = []
        
        # Mock create operation
        created_site = Mock()
        created_site.id = 20
        created_site.serialize.return_value = {
            "id": 20,
            "name": "Datacenter Amsterdam",
            "slug": "datacenter-amsterdam",
            "status": "active"
        }
        mock_api.dcim.sites.create.return_value = created_site
        
        result = client.ensure_site(name="Datacenter Amsterdam", confirm=True)
        
        # Should create new site
        mock_api.dcim.sites.create.assert_called_once_with({
            "name": "Datacenter Amsterdam",
            "status": "active"
        })
        
        # Should return created result
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["object_type"] == "site"
        assert result["site"]["name"] == "Datacenter Amsterdam"
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_site_by_id_existing(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test ensure_site with direct ID injection."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock existing site
        existing_site = Mock()
        existing_site.id = 15
        existing_site.serialize.return_value = {
            "id": 15,
            "name": "Existing Site",
            "status": "active"
        }
        mock_api.dcim.sites.get.return_value = existing_site
        
        result = client.ensure_site(site_id=15, confirm=True)
        
        # Should retrieve by ID directly
        mock_api.dcim.sites.get.assert_called_once_with(15)
        
        # Should return unchanged result
        assert result["success"] is True
        assert result["action"] == "unchanged"
        assert result["object_type"] == "site"
        assert result["site"]["id"] == 15


class TestEnsureDeviceRole:
    """Test ensure_device_role hybrid pattern functionality."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_role_create_new(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test creating new device role."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock no existing device roles
        mock_api.dcim.device_roles.filter.return_value = []
        
        # Mock create operation
        created_role = Mock()
        created_role.id = 8
        created_role.serialize.return_value = {
            "id": 8,
            "name": "Access Switch",
            "slug": "access-switch",
            "color": "2196f3",
            "vm_role": False
        }
        mock_api.dcim.device_roles.create.return_value = created_role
        
        result = client.ensure_device_role(
            name="Access Switch",
            color="2196f3",
            confirm=True
        )
        
        # Should create new device role
        mock_api.dcim.device_roles.create.assert_called_once_with({
            "name": "Access Switch",
            "color": "2196f3",
            "vm_role": False
        })
        
        # Should return created result
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["object_type"] == "device_role"
        assert result["device_role"]["name"] == "Access Switch"
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_role_validation_error(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test validation errors in ensure_device_role."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Test missing parameters
        with pytest.raises(NetBoxValidationError, match="Either 'name' or 'role_id' parameter is required"):
            client.ensure_device_role(confirm=True)
        
        # Test empty name
        with pytest.raises(NetBoxValidationError, match="Either 'name' or 'role_id' parameter is required"):
            client.ensure_device_role(name="", confirm=True)


class TestEnsureIdempotency:
    """Test idempotency behavior of ensure methods."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_idempotency(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test that calling ensure_manufacturer multiple times produces same result."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock existing manufacturer
        existing_mfg = Mock()
        existing_mfg.id = 5
        existing_mfg.serialize.return_value = {
            "id": 5,
            "name": "Cisco Systems",
            "slug": "cisco-systems"
        }
        mock_api.dcim.manufacturers.filter.return_value = [existing_mfg]
        
        # Call ensure multiple times
        result1 = client.ensure_manufacturer(name="Cisco Systems", confirm=True)
        result2 = client.ensure_manufacturer(name="Cisco Systems", confirm=True)
        result3 = client.ensure_manufacturer(name="Cisco Systems", confirm=True)
        
        # All results should be identical
        assert result1 == result2 == result3
        assert all(r["action"] == "unchanged" for r in [result1, result2, result3])
        assert all(r["manufacturer"]["id"] == 5 for r in [result1, result2, result3])
        
        # Should not call create (only filter for lookup)
        mock_api.dcim.manufacturers.create.assert_not_called()


class TestEnsureDryRunMode:
    """Test ensure operations in dry-run mode."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_dry_run_create(self, mock_pynetbox_api, dry_run_config, mock_api):
        """Test ensure_manufacturer in dry-run mode for creation."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(dry_run_config)
        
        # Mock no existing manufacturers
        mock_api.dcim.manufacturers.filter.return_value = []
        
        # Mock the create_object method to return dry-run result
        with patch.object(client, 'create_object', return_value={
            "id": 999999,
            "name": "New Vendor",
            "dry_run": True
        }) as mock_create:
            result = client.ensure_manufacturer(name="New Vendor", confirm=True)
        
        # Should call create_object in dry-run mode
        mock_create.assert_called_once_with("manufacturers", {"name": "New Vendor"}, confirm=True)
        
        # Should return dry-run result
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["dry_run"] is True
        assert result["manufacturer"]["id"] == 999999
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_site_dry_run_unchanged(self, mock_pynetbox_api, dry_run_config, mock_api):
        """Test ensure_site in dry-run mode for unchanged object."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(dry_run_config)
        
        # Mock existing site with matching state
        existing_site = Mock()
        existing_site.id = 10
        existing_site.serialize.return_value = {
            "id": 10,
            "name": "Test Site",
            "status": "active"
        }
        mock_api.dcim.sites.filter.return_value = [existing_site]
        
        result = client.ensure_site(name="Test Site", status="active", confirm=True)
        
        # Should return unchanged result (no dry-run needed for unchanged)
        assert result["success"] is True
        assert result["action"] == "unchanged"
        assert result["dry_run"] is False  # No write operation performed


class TestEnsureErrorHandling:
    """Test error handling in ensure operations."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_api_error(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test handling of API errors during ensure operations."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock API error during filter
        mock_api.dcim.manufacturers.filter.side_effect = Exception("API connection failed")
        
        with pytest.raises(NetBoxWriteError, match="Failed to ensure manufacturer"):
            client.ensure_manufacturer(name="Test Vendor", confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_site_unexpected_error(self, mock_pynetbox_api, ensure_config, mock_api):
        """Test handling of unexpected errors."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(ensure_config)
        
        # Mock unexpected error
        mock_api.dcim.sites.filter.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(NetBoxWriteError, match="Failed to ensure site"):
            client.ensure_site(name="Test Site", confirm=True)