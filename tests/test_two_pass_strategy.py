"""
Tests for Issue #13: Two-Pass Strategy for Complex Relationships
"""

import pytest
import hashlib
import json
from unittest.mock import Mock, patch
from datetime import datetime

from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import NetBoxConfig, SafetyConfig
from netbox_mcp.exceptions import (
    NetBoxValidationError,
    NetBoxConfirmationError,
    NetBoxNotFoundError
)


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
    api.dcim.device_types = Mock()
    api.dcim.devices = Mock()
    return api


class TestEnsureDeviceType:
    """Test ensure_device_type method - Pass 1 object creation."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_without_confirm_raises_error(self, mock_pynetbox_api, test_config, mock_api):
        """Test that ensure_device_type requires confirm=True."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        with pytest.raises(NetBoxConfirmationError, match="requires confirm=True for safety"):
            client.ensure_device_type(name="Catalyst 9300", manufacturer_id=1)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_missing_parameters_raises_error(self, mock_pynetbox_api, test_config, mock_api):
        """Test that either name or device_type_id is required."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        with pytest.raises(NetBoxValidationError, match="Either 'name' or 'device_type_id' parameter is required"):
            client.ensure_device_type(manufacturer_id=1, confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_missing_manufacturer_id_raises_error(self, mock_pynetbox_api, test_config, mock_api):
        """Test that manufacturer_id is required for device type operations."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        with pytest.raises(NetBoxValidationError, match="manufacturer_id is required"):
            client.ensure_device_type(name="Catalyst 9300", confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_by_id_existing(self, mock_pynetbox_api, test_config, mock_api):
        """Test ensure_device_type with direct ID injection for existing device type."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Mock existing device type
        existing_dt = Mock()
        existing_dt.id = 10
        existing_dt.serialize.return_value = {
            "id": 10,
            "name": "Catalyst 9300",
            "manufacturer": {"id": 1, "name": "Cisco"},
            "slug": "catalyst-9300"
        }
        mock_api.dcim.device_types.get.return_value = existing_dt
        
        with patch.object(client, '_object_to_dict', return_value=existing_dt.serialize()):
            result = client.ensure_device_type(device_type_id=10, manufacturer_id=1, confirm=True)
        
        # Should retrieve by ID directly
        mock_api.dcim.device_types.get.assert_called_once_with(10)
        
        # Should return unchanged result
        assert result["success"] is True
        assert result["action"] == "unchanged"
        assert result["object_type"] == "device_type"
        assert result["device_type"]["id"] == 10
        assert result["device_type"]["name"] == "Catalyst 9300"
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_by_id_not_found(self, mock_pynetbox_api, test_config, mock_api):
        """Test ensure_device_type with non-existent device type ID."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Mock device type not found
        mock_api.dcim.device_types.get.return_value = None
        
        with pytest.raises(NetBoxNotFoundError, match="Device type with ID 999 not found"):
            client.ensure_device_type(device_type_id=999, manufacturer_id=1, confirm=True)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_create_new(self, mock_pynetbox_api, test_config, mock_api):
        """Test creating new device type when it doesn't exist."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Mock no existing device types
        mock_api.dcim.device_types.filter.return_value = []
        
        # Mock create operation
        created_dt = Mock()
        created_dt.id = 15
        created_dt.serialize.return_value = {
            "id": 15,
            "name": "Catalyst 9400",
            "manufacturer": {"id": 1, "name": "Cisco"},
            "slug": "catalyst-9400",
            "model": "C9400-48U"
        }
        
        with patch.object(client, 'create_object', return_value=created_dt.serialize()) as mock_create:
            result = client.ensure_device_type(
                name="Catalyst 9400",
                manufacturer_id=1,
                model="C9400-48U",
                batch_id="batch_001",
                confirm=True
            )
        
        # Should create new device type
        mock_create.assert_called_once()
        call_args = mock_create.call_args[0]
        created_data = call_args[1]  # Second argument is the data
        
        # Verify core data
        assert created_data["name"] == "Catalyst 9400"
        assert created_data["manufacturer"] == 1
        assert created_data["model"] == "C9400-48U"
        
        # Verify metadata was added
        assert "custom_fields" in created_data
        custom_fields = created_data["custom_fields"]
        assert "batch_id" in custom_fields
        assert custom_fields["batch_id"] == "batch_001"
        assert "enterprise_managed_hash" in custom_fields
        assert "last_enterprise_sync" in custom_fields
        assert "management_source" in custom_fields
        
        # Should return created result
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["object_type"] == "device_type"
        assert result["device_type"]["name"] == "Catalyst 9400"
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_update_existing(self, mock_pynetbox_api, test_config, mock_api):
        """Test updating existing device type when fields differ."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Mock existing device type with different model
        existing_dt_dict = {
            "id": 10,
            "name": "Catalyst 9300",
            "manufacturer": 1,
            "slug": "catalyst-9300",
            "model": "C9300-24U",
            "description": "Old description",
            "custom_fields": {
                "enterprise_managed_hash": "old_hash"
            }
        }
        
        existing_dt = Mock()
        existing_dt.id = 10
        existing_dt.serialize.return_value = existing_dt_dict
        mock_api.dcim.device_types.filter.return_value = [existing_dt]
        
        # Mock update operation
        updated_result = {
            "id": 10,
            "name": "Catalyst 9300",
            "manufacturer": 1,
            "slug": "catalyst-9300",
            "model": "C9300-48U",  # Updated
            "description": "Updated description"  # Updated
        }
        
        with patch.object(client, '_object_to_dict', return_value=existing_dt_dict):
            with patch.object(client, 'update_object', return_value=updated_result) as mock_update:
                result = client.ensure_device_type(
                    name="Catalyst 9300",
                    manufacturer_id=1,
                    model="C9300-48U",  # Different from existing
                    description="Updated description",  # Different from existing
                    confirm=True
                )
        
        # Should update the device type
        mock_update.assert_called_once()
        
        # Should return updated result
        assert result["success"] is True
        assert result["action"] == "updated"
        assert result["object_type"] == "device_type"
        assert "model" in result["changes"]["updated_fields"]
        assert "description" in result["changes"]["updated_fields"]
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_ensure_device_type_unchanged_existing(self, mock_pynetbox_api, test_config, mock_api):
        """Test ensuring device type that already has desired state."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        # Build desired state
        desired_state = {
            "name": "Catalyst 9300",
            "manufacturer": 1,
            "slug": "catalyst-9300",
            "model": "C9300-24U",
            "description": "Core switch"
        }
        
        # Generate expected hash for the desired state
        expected_hash = client._generate_managed_hash(desired_state, "device_types")
        
        # Mock existing device type with matching state and hash
        existing_dt_dict = {
            "id": 10,
            "name": "Catalyst 9300",
            "manufacturer": 1,
            "slug": "catalyst-9300",
            "model": "C9300-24U",
            "description": "Core switch",
            "custom_fields": {
                "enterprise_managed_hash": expected_hash
            }
        }
        
        existing_dt = Mock()
        existing_dt.id = 10
        existing_dt.serialize.return_value = existing_dt_dict
        mock_api.dcim.device_types.filter.return_value = [existing_dt]
        
        with patch.object(client, '_object_to_dict', return_value=existing_dt_dict):
            result = client.ensure_device_type(
                name="Catalyst 9300",
                manufacturer_id=1,
                slug="catalyst-9300",
                model="C9300-24U",
                description="Core switch",
                confirm=True
            )
        
        # Should not call update or create
        mock_api.dcim.device_types.create.assert_not_called()
        
        # Should return unchanged result
        assert result["success"] is True
        assert result["action"] == "unchanged"
        assert result["object_type"] == "device_type"
        assert len(result["changes"]["updated_fields"]) == 0
        assert len(result["changes"]["unchanged_fields"]) > 0


class TestManagedFieldsExtension:
    """Test managed fields configuration for device_types and devices."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_managed_fields_device_types(self, mock_pynetbox_api, test_config, mock_api):
        """Test managed fields configuration for device_types."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        expected_fields = ["name", "slug", "model", "manufacturer", "description"]
        assert client.MANAGED_FIELDS["device_types"] == expected_fields
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_managed_fields_devices(self, mock_pynetbox_api, test_config, mock_api):
        """Test managed fields configuration for devices."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        expected_fields = ["name", "device_type", "site", "role", "platform", "status", "description"]
        assert client.MANAGED_FIELDS["devices"] == expected_fields
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_metadata_custom_fields_batch_id(self, mock_pynetbox_api, test_config, mock_api):
        """Test batch_id custom field configuration."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        expected_batch_field = "batch_id"
        assert client.METADATA_CUSTOM_FIELDS["batch_id"] == expected_batch_field


class TestNetBoxBulkOrchestrator:
    """Test NetBoxBulkOrchestrator class - Two-pass stateless orchestration."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_orchestrator_initialization(self, mock_pynetbox_api, test_config, mock_api):
        """Test orchestrator initialization."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        from netbox_mcp.client import NetBoxBulkOrchestrator
        orchestrator = NetBoxBulkOrchestrator(client)
        
        assert orchestrator.client == client
        assert orchestrator.operation_cache == {}
        assert orchestrator.batch_id is None
        assert "pass_1" in orchestrator.results
        assert "pass_2" in orchestrator.results
        assert "created" in orchestrator.results["pass_1"]
        assert "updated" in orchestrator.results["pass_1"]
        assert "unchanged" in orchestrator.results["pass_1"]
        assert "errors" in orchestrator.results["pass_1"]
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_generate_batch_id(self, mock_pynetbox_api, test_config, mock_api):
        """Test batch ID generation."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        from netbox_mcp.client import NetBoxBulkOrchestrator
        orchestrator = NetBoxBulkOrchestrator(client)
        
        batch_id = orchestrator.generate_batch_id()
        
        assert batch_id.startswith("batch_")
        assert orchestrator.batch_id == batch_id
        assert len(batch_id.split("_")) == 4  # batch_{timestamp}_{uuid}
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_normalize_device_data(self, mock_pynetbox_api, test_config, mock_api):
        """Test device data normalization for two-pass processing."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        from netbox_mcp.client import NetBoxBulkOrchestrator
        orchestrator = NetBoxBulkOrchestrator(client)
        orchestrator.generate_batch_id()
        
        # Input device data
        device_data = {
            "name": "switch-01",
            "manufacturer": "Cisco",
            "device_type": "Catalyst 9300",
            "site": "Amsterdam DC",
            "role": "Access Switch",
            "model": "C9300-24U",
            "status": "active",
            "description": "Core switch for floor 3",
            "platform": "ios",
            "interfaces": [
                {"name": "GigabitEthernet1/0/1", "type": "1000base-t"}
            ],
            "ip_addresses": [
                {"address": "192.168.1.10/24", "interface": "Management1"}
            ]
        }
        
        normalized = orchestrator.normalize_device_data(device_data)
        
        # Verify structure
        assert "core_objects" in normalized
        assert "relationship_objects" in normalized
        assert "metadata" in normalized
        
        # Verify core objects
        core = normalized["core_objects"]
        assert core["manufacturer"] == "Cisco"
        assert core["site"] == "Amsterdam DC"
        assert core["device_role"] == "Access Switch"
        assert core["device_type"]["name"] == "Catalyst 9300"
        assert core["device_type"]["manufacturer"] == "Cisco"
        assert core["device_type"]["model"] == "C9300-24U"
        
        # Verify relationship objects
        rel = normalized["relationship_objects"]
        assert rel["device"]["name"] == "switch-01"
        assert rel["device"]["device_type"] == "Catalyst 9300"
        assert rel["device"]["site"] == "Amsterdam DC"
        assert rel["device"]["role"] == "Access Switch"
        assert rel["device"]["platform"] == "ios"
        assert len(rel["interfaces"]) == 1
        assert len(rel["ip_addresses"]) == 1
        
        # Verify metadata
        meta = normalized["metadata"]
        assert meta["batch_id"] == orchestrator.batch_id
        assert meta["source_system"] == "enterprise"
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_execute_pass_1_successful(self, mock_pynetbox_api, test_config, mock_api):
        """Test successful Pass 1 execution."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        from netbox_mcp.client import NetBoxBulkOrchestrator
        orchestrator = NetBoxBulkOrchestrator(client)
        orchestrator.generate_batch_id()
        
        # Mock ensure methods
        manufacturer_result = {
            "success": True,
            "action": "created",
            "manufacturer": {"id": 1, "name": "Cisco"}
        }
        site_result = {
            "success": True, 
            "action": "unchanged",
            "site": {"id": 2, "name": "Amsterdam DC"}
        }
        role_result = {
            "success": True,
            "action": "created", 
            "device_role": {"id": 3, "name": "Access Switch"}
        }
        device_type_result = {
            "success": True,
            "action": "created",
            "device_type": {"id": 4, "name": "Catalyst 9300"}
        }
        
        with patch.object(client, 'ensure_manufacturer', return_value=manufacturer_result) as mock_manufacturer:
            with patch.object(client, 'ensure_site', return_value=site_result) as mock_site:
                with patch.object(client, 'ensure_device_role', return_value=role_result) as mock_role:
                    with patch.object(client, 'ensure_device_type', return_value=device_type_result) as mock_device_type:
                        
                        normalized_data = {
                            "core_objects": {
                                "manufacturer": "Cisco",
                                "site": "Amsterdam DC",
                                "device_role": "Access Switch",
                                "device_type": {
                                    "name": "Catalyst 9300",
                                    "manufacturer": "Cisco",
                                    "model": "C9300-24U"
                                }
                            }
                        }
                        
                        pass_1_results = orchestrator.execute_pass_1(normalized_data, confirm=True)
        
        # Verify all ensure methods were called
        mock_manufacturer.assert_called_once_with(name="Cisco", batch_id=orchestrator.batch_id, confirm=True)
        mock_site.assert_called_once_with(name="Amsterdam DC", batch_id=orchestrator.batch_id, confirm=True)
        mock_role.assert_called_once_with(name="Access Switch", batch_id=orchestrator.batch_id, confirm=True)
        mock_device_type.assert_called_once_with(
            name="Catalyst 9300",
            manufacturer_id=1,
            model="C9300-24U",
            description=None,
            batch_id=orchestrator.batch_id,
            confirm=True
        )
        
        # Verify pass 1 results
        assert pass_1_results["manufacturer_id"] == 1
        assert pass_1_results["site_id"] == 2
        assert pass_1_results["device_role_id"] == 3
        assert pass_1_results["device_type_id"] == 4
        
        # Verify operation cache
        assert orchestrator.operation_cache["manufacturer:Cisco"] == 1
        assert orchestrator.operation_cache["site:Amsterdam DC"] == 2
        assert orchestrator.operation_cache["device_role:Access Switch"] == 3
        assert orchestrator.operation_cache["device_type:Catalyst 9300"] == 4
        
        # Verify results tracking
        assert len(orchestrator.results["pass_1"]["created"]) == 3  # manufacturer, role, device_type
        assert len(orchestrator.results["pass_1"]["unchanged"]) == 1  # site
        assert len(orchestrator.results["pass_1"]["errors"]) == 0
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_execute_pass_2_successful(self, mock_pynetbox_api, test_config, mock_api):
        """Test successful Pass 2 execution."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        from netbox_mcp.client import NetBoxBulkOrchestrator
        orchestrator = NetBoxBulkOrchestrator(client)
        orchestrator.generate_batch_id()
        
        # Mock ensure_device
        device_result = {
            "success": True,
            "action": "created",
            "device": {"id": 10, "name": "switch-01"}
        }
        
        with patch.object(client, 'ensure_device', return_value=device_result) as mock_device:
            normalized_data = {
                "relationship_objects": {
                    "device": {
                        "name": "switch-01",
                        "device_type": "Catalyst 9300",
                        "site": "Amsterdam DC",
                        "role": "Access Switch",
                        "platform": "ios",
                        "status": "active",
                        "description": "Core switch"
                    }
                }
            }
            
            pass_1_results = {
                "manufacturer_id": 1,
                "site_id": 2,
                "device_role_id": 3,
                "device_type_id": 4
            }
            
            pass_2_results = orchestrator.execute_pass_2(normalized_data, pass_1_results, confirm=True)
        
        # Verify ensure_device was called with Pass 1 IDs
        mock_device.assert_called_once_with(
            name="switch-01",
            device_type_id=4,
            site_id=2,
            role_id=3,
            platform="ios",
            status="active",
            description="Core switch",
            batch_id=orchestrator.batch_id,
            confirm=True
        )
        
        # Verify pass 2 results
        assert pass_2_results["device_id"] == 10
        
        # Verify operation cache
        assert orchestrator.operation_cache["device:switch-01"] == 10
        
        # Verify results tracking
        assert len(orchestrator.results["pass_2"]["created"]) == 1
        assert len(orchestrator.results["pass_2"]["errors"]) == 0
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_generate_operation_report(self, mock_pynetbox_api, test_config, mock_api):
        """Test operation report generation."""
        mock_pynetbox_api.return_value = mock_api
        client = NetBoxClient(test_config)
        
        from netbox_mcp.client import NetBoxBulkOrchestrator
        orchestrator = NetBoxBulkOrchestrator(client)
        orchestrator.generate_batch_id()
        
        # Simulate some results
        orchestrator.results["pass_1"]["created"] = [{"object": "manufacturer"}, {"object": "site"}]
        orchestrator.results["pass_1"]["unchanged"] = [{"object": "device_role"}]
        orchestrator.results["pass_2"]["created"] = [{"object": "device"}]
        orchestrator.operation_cache = {"manufacturer:Cisco": 1, "site:Amsterdam": 2}
        
        report = orchestrator.generate_operation_report()
        
        # Verify report structure
        assert "batch_id" in report
        assert "operation_summary" in report
        assert "pass_1_summary" in report
        assert "pass_2_summary" in report
        assert "detailed_results" in report
        assert "cache_statistics" in report
        
        # Verify operation summary
        summary = report["operation_summary"]
        assert summary["total_objects_processed"] == 4  # 3 pass_1 + 1 pass_2
        assert summary["total_errors"] == 0
        assert summary["success_rate"] == 100.0
        
        # Verify pass summaries
        assert report["pass_1_summary"]["core_objects_processed"] == 3
        assert report["pass_1_summary"]["created"] == 2
        assert report["pass_1_summary"]["unchanged"] == 1
        
        assert report["pass_2_summary"]["relationship_objects_processed"] == 1
        assert report["pass_2_summary"]["created"] == 1
        
        # Verify cache statistics
        cache_stats = report["cache_statistics"]
        assert cache_stats["cached_objects"] == 2
        assert "manufacturer:Cisco" in cache_stats["cache_keys"]