"""
Tests for selective field comparison and hash-based diffing functionality.
"""

import pytest
import hashlib
import json
from unittest.mock import Mock, patch
from datetime import datetime

from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import NetBoxConfig, SafetyConfig
from netbox_mcp.exceptions import NetBoxValidationError


@pytest.fixture
def test_config():
    """Create a NetBox configuration for testing."""
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
def mock_api():
    """Create a mock pynetbox API."""
    api = Mock()
    api.dcim = Mock()
    api.dcim.manufacturers = Mock()
    api.dcim.sites = Mock()
    api.dcim.device_roles = Mock()
    return api


class TestSelectiveFieldComparison:
    """Test selective field comparison logic."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_generate_managed_hash_basic(self, mock_pynetbox_api, test_config, mock_api):
        """Test basic hash generation for managed fields."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Test data with all managed fields for manufacturers
        test_data = {
            "name": "Cisco Systems",
            "slug": "cisco-systems", 
            "description": "Network equipment manufacturer",
            "extra_field": "should be ignored"
        }
        
        # Generate hash
        hash_result = client._generate_managed_hash(test_data, "manufacturers")
        
        # Verify hash is generated correctly
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA256 hex length
        
        # Verify only managed fields are included
        managed_data = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment manufacturer"
        }
        expected_hash = hashlib.sha256(
            json.dumps(managed_data, sort_keys=True).encode('utf-8')
        ).hexdigest()
        
        assert hash_result == expected_hash
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_generate_managed_hash_partial_fields(self, mock_pynetbox_api, test_config, mock_api):
        """Test hash generation with partial field data."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Test data with only some managed fields
        test_data = {
            "name": "HP Inc",
            "slug": "hp-inc"
            # description is None/missing
        }
        
        hash_result = client._generate_managed_hash(test_data, "manufacturers")
        
        # Should only include non-None values
        managed_data = {
            "name": "HP Inc",
            "slug": "hp-inc"
        }
        expected_hash = hashlib.sha256(
            json.dumps(managed_data, sort_keys=True).encode('utf-8')
        ).hexdigest()
        
        assert hash_result == expected_hash
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_generate_managed_hash_unknown_type(self, mock_pynetbox_api, test_config, mock_api):
        """Test hash generation with unknown object type."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        with pytest.raises(NetBoxValidationError, match="Unknown object type"):
            client._generate_managed_hash({"name": "test"}, "unknown_type")
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_compare_managed_fields_no_changes(self, mock_pynetbox_api, test_config, mock_api):
        """Test field comparison when no changes are needed."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        existing_obj = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment"
        }
        
        desired_state = {
            "name": "Cisco Systems", 
            "slug": "cisco-systems",
            "description": "Network equipment"
        }
        
        result = client._compare_managed_fields(existing_obj, desired_state, "manufacturers")
        
        assert result["needs_update"] is False
        assert len(result["updated_fields"]) == 0
        assert "name" in result["unchanged_fields"]
        assert "slug" in result["unchanged_fields"]
        assert "description" in result["unchanged_fields"]
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_compare_managed_fields_with_changes(self, mock_pynetbox_api, test_config, mock_api):
        """Test field comparison when changes are detected."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        existing_obj = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Old description"
        }
        
        desired_state = {
            "name": "Cisco Systems",
            "slug": "cisco-systems", 
            "description": "New description"
        }
        
        result = client._compare_managed_fields(existing_obj, desired_state, "manufacturers")
        
        assert result["needs_update"] is True
        assert len(result["updated_fields"]) == 1
        assert result["updated_fields"][0]["field"] == "description"
        assert result["updated_fields"][0]["current"] == "Old description"
        assert result["updated_fields"][0]["desired"] == "New description"
        assert "name" in result["unchanged_fields"]
        assert "slug" in result["unchanged_fields"]
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_hash_comparison_check_match(self, mock_pynetbox_api, test_config, mock_api):
        """Test hash comparison when hashes match."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        desired_state = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment"
        }
        
        # Generate expected hash
        expected_hash = client._generate_managed_hash(desired_state, "manufacturers")
        
        existing_obj = {
            "name": "Cisco Systems",
            "slug": "cisco-systems", 
            "description": "Network equipment",
            "custom_fields": {
                "enterprise_managed_hash": expected_hash
            }
        }
        
        result = client._hash_comparison_check(existing_obj, desired_state, "manufacturers")
        
        assert result is True  # Hashes match, no update needed
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_hash_comparison_check_mismatch(self, mock_pynetbox_api, test_config, mock_api):
        """Test hash comparison when hashes don't match."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        desired_state = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "New description"
        }
        
        existing_obj = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Old description", 
            "custom_fields": {
                "enterprise_managed_hash": "old_hash_value"
            }
        }
        
        result = client._hash_comparison_check(existing_obj, desired_state, "manufacturers")
        
        assert result is False  # Hashes differ, update needed
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_hash_comparison_check_no_existing_hash(self, mock_pynetbox_api, test_config, mock_api):
        """Test hash comparison when no existing hash is found."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        desired_state = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment"
        }
        
        existing_obj = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment",
            "custom_fields": {}  # No hash stored
        }
        
        result = client._hash_comparison_check(existing_obj, desired_state, "manufacturers")
        
        assert result is False  # No hash, assume update needed
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_prepare_metadata_update(self, mock_pynetbox_api, test_config, mock_api):
        """Test metadata preparation for updates."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        desired_state = {
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment"
        }
        
        # Mock datetime to make test deterministic
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value.isoformat.return_value = "2025-06-21T10:00:00"
            
            result = client._prepare_metadata_update(desired_state, "manufacturers", "update")
        
        # Verify original data is preserved
        assert result["name"] == "Cisco Systems"
        assert result["slug"] == "cisco-systems"
        assert result["description"] == "Network equipment"
        
        # Verify metadata is added
        custom_fields = result["custom_fields"]
        assert "enterprise_managed_hash" in custom_fields
        assert custom_fields["last_enterprise_sync"] == "2025-06-21T10:00:00"
        assert custom_fields["management_source"] == "enterprise"
        
        # Verify hash is correct
        expected_hash = client._generate_managed_hash(desired_state, "manufacturers")
        assert custom_fields["enterprise_managed_hash"] == expected_hash


class TestManagedFieldsConfiguration:
    """Test managed fields configuration."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_managed_fields_manufacturers(self, mock_pynetbox_api, test_config, mock_api):
        """Test managed fields configuration for manufacturers."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        expected_fields = ["name", "slug", "description"]
        assert client.MANAGED_FIELDS["manufacturers"] == expected_fields
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_managed_fields_sites(self, mock_pynetbox_api, test_config, mock_api):
        """Test managed fields configuration for sites."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        expected_fields = ["name", "slug", "status", "description", "physical_address", "region"]
        assert client.MANAGED_FIELDS["sites"] == expected_fields
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_managed_fields_device_roles(self, mock_pynetbox_api, test_config, mock_api):
        """Test managed fields configuration for device roles."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        expected_fields = ["name", "slug", "color", "vm_role", "description"]
        assert client.MANAGED_FIELDS["device_roles"] == expected_fields
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_metadata_custom_fields_configuration(self, mock_pynetbox_api, test_config, mock_api):
        """Test metadata custom fields configuration."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        expected_fields = {
            "managed_hash": "enterprise_managed_hash",
            "last_sync": "last_enterprise_sync",
            "source": "management_source"
        }
        assert client.METADATA_CUSTOM_FIELDS == expected_fields


class TestHashBasedEnsureIntegration:
    """Test hash-based comparison integration with ensure methods."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_manufacturer_hash_match_no_update(self, mock_pynetbox_api, test_config, mock_api):
        """Test ensure_manufacturer with hash match skips update."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Prepare test data
        desired_state = {
            "name": "Cisco Systems",
            "slug": "cisco-systems", 
            "description": "Network equipment"
        }
        
        # Generate expected hash for the desired state
        expected_hash = client._generate_managed_hash(desired_state, "manufacturers")
        
        # Mock existing manufacturer with matching hash
        existing_mfg_dict = {
            "id": 5,
            "name": "Cisco Systems",
            "slug": "cisco-systems",
            "description": "Network equipment",
            "custom_fields": {
                "enterprise_managed_hash": expected_hash
            }
        }
        
        existing_mfg = Mock()
        existing_mfg.id = 5
        existing_mfg.serialize.return_value = existing_mfg_dict
        mock_api.dcim.manufacturers.filter.return_value = [existing_mfg]
        
        # Mock _object_to_dict to return the expected dict
        with patch.object(client, '_object_to_dict', return_value=existing_mfg_dict):
            # Call ensure_manufacturer
            result = client.ensure_manufacturer(
                name="Cisco Systems", 
                slug="cisco-systems",
                description="Network equipment",
                confirm=True
            )
            
            # Should return unchanged without calling update_object
            assert result["success"] is True
            assert result["action"] == "unchanged"
            assert result["object_type"] == "manufacturer"
            
            # Verify no create or update calls were made
            mock_api.dcim.manufacturers.create.assert_not_called()
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_site_selective_field_comparison(self, mock_pynetbox_api, test_config, mock_api):
        """Test ensure_site with selective field comparison."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Mock existing site with different description but matching other fields
        existing_site = Mock()
        existing_site.id = 10
        existing_site.serialize.return_value = {
            "id": 10,
            "name": "Test Site",
            "slug": "test-site",
            "status": "active",
            "description": "Old description",
            "physical_address": "123 Main St",
            "custom_fields": {
                "enterprise_managed_hash": "old_hash"
            }
        }
        mock_api.dcim.sites.filter.return_value = [existing_site]
        
        # Mock update_object to return updated result
        updated_result = {
            "id": 10,
            "name": "Test Site",
            "slug": "test-site", 
            "status": "active",
            "description": "New description",
            "physical_address": "123 Main St"
        }
        
        with patch.object(client, 'update_object', return_value=updated_result) as mock_update:
            result = client.ensure_site(
                name="Test Site",
                status="active", 
                description="New description",
                physical_address="123 Main St",
                confirm=True
            )
        
        # Should detect change in description and call update
        mock_update.assert_called_once()
        assert result["success"] is True
        assert result["action"] == "updated"
        assert "description" in result["changes"]["updated_fields"]
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_role_with_metadata_creation(self, mock_pynetbox_api, test_config, mock_api):
        """Test ensure_device_role creates new role with metadata."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Mock no existing device roles
        mock_api.dcim.device_roles.filter.return_value = []
        
        # Mock create_object to return created result
        created_result = {
            "id": 15,
            "name": "Core Switch",
            "slug": "core-switch",
            "color": "2196f3",
            "vm_role": False,
            "description": "Core network switch"
        }
        
        with patch.object(client, 'create_object', return_value=created_result) as mock_create:
            # Mock datetime for deterministic testing
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value.isoformat.return_value = "2025-06-21T12:00:00"
                
                result = client.ensure_device_role(
                    name="Core Switch",
                    color="2196f3",
                    description="Core network switch",
                    confirm=True
                )
        
        # Verify create_object was called with metadata
        mock_create.assert_called_once()
        call_args = mock_create.call_args[0]
        created_data = call_args[1]  # Second argument is the data
        
        # Verify metadata was added
        assert "custom_fields" in created_data
        custom_fields = created_data["custom_fields"]
        assert "enterprise_managed_hash" in custom_fields
        assert custom_fields["last_enterprise_sync"] == "2025-06-21T12:00:00"
        assert custom_fields["management_source"] == "enterprise"
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["object_type"] == "device_role"


class TestHashConsistency:
    """Test hash generation consistency and edge cases."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_hash_consistency_across_calls(self, mock_pynetbox_api, test_config, mock_api):
        """Test that hash generation is consistent across multiple calls."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        test_data = {
            "name": "Test Manufacturer",
            "slug": "test-manufacturer",
            "description": "Test description",
            "extra_field": "should be ignored"
        }
        
        # Generate hash multiple times
        hash1 = client._generate_managed_hash(test_data, "manufacturers")
        hash2 = client._generate_managed_hash(test_data, "manufacturers")
        hash3 = client._generate_managed_hash(test_data, "manufacturers")
        
        # All hashes should be identical
        assert hash1 == hash2 == hash3
        assert len(hash1) == 64  # SHA256 hex length
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_hash_different_for_different_data(self, mock_pynetbox_api, test_config, mock_api):
        """Test that different data produces different hashes."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        data1 = {"name": "Cisco", "slug": "cisco", "description": "Network equipment"}
        data2 = {"name": "Cisco", "slug": "cisco", "description": "Different description"}
        
        hash1 = client._generate_managed_hash(data1, "manufacturers")
        hash2 = client._generate_managed_hash(data2, "manufacturers")
        
        # Hashes should be different
        assert hash1 != hash2
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_hash_field_order_independence(self, mock_pynetbox_api, test_config, mock_api):
        """Test that field order doesn't affect hash generation."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Same data in different order
        data1 = {"name": "Cisco", "slug": "cisco", "description": "Network equipment"}
        data2 = {"description": "Network equipment", "name": "Cisco", "slug": "cisco"}
        
        hash1 = client._generate_managed_hash(data1, "manufacturers")
        hash2 = client._generate_managed_hash(data2, "manufacturers")
        
        # Hashes should be identical (JSON sorts keys)
        assert hash1 == hash2