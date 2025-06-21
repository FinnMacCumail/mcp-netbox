"""
Tests for netbox_bulk_ensure_devices MCP tool
"""

import pytest
from unittest.mock import Mock, patch
from netbox_mcp.server import netbox_bulk_ensure_devices


@pytest.fixture
def sample_devices_data():
    """Sample device data for testing."""
    return [
        {
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
        },
        {
            "name": "switch-02", 
            "manufacturer": "Cisco",
            "device_type": "Catalyst 9300",
            "site": "Rotterdam DC",
            "role": "Distribution Switch",
            "model": "C9300-48U",
            "status": "active",
            "platform": "ios"
        }
    ]


class TestNetboxBulkEnsureDevices:
    """Test the netbox_bulk_ensure_devices MCP tool."""
    
    @patch('netbox_mcp.server.netbox_client')
    def test_bulk_devices_validation_empty_list(self, mock_client):
        """Test validation with empty devices list."""
        result = netbox_bulk_ensure_devices([], confirm=True)
        
        assert result["success"] is False
        assert "ValidationError" in result["error_type"]
        assert "non-empty list" in result["error"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_bulk_devices_validation_missing_fields(self, mock_client):
        """Test validation with missing required fields."""
        invalid_device = {
            "name": "switch-01",
            "manufacturer": "Cisco"
            # Missing device_type, site, role
        }
        
        result = netbox_bulk_ensure_devices([invalid_device], confirm=True)
        
        assert result["success"] is False
        assert "ValidationError" in result["error_type"]
        assert "missing required fields" in result["error"]
        assert "device_type" in result["error"]
        assert "site" in result["error"]
        assert "role" in result["error"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_bulk_devices_requires_confirm(self, mock_client, sample_devices_data):
        """Test that bulk operation requires confirm=True."""
        result = netbox_bulk_ensure_devices(sample_devices_data, confirm=False)
        
        assert result["success"] is False
        assert "ConfirmationRequired" in result["error_type"]
        assert "confirm=True" in result["error"]
        assert "dry_run_report=True" in result["help"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_bulk_devices_dry_run_report(self, mock_client, sample_devices_data):
        """Test pre-flight dry run report generation."""
        mock_client.config.safety.dry_run_mode = False
        
        result = netbox_bulk_ensure_devices(
            sample_devices_data, 
            confirm=False, 
            dry_run_report=True
        )
        
        assert result["success"] is True
        assert result["action"] == "pre_flight_report"
        assert "pre_flight_analysis" in result
        
        analysis = result["pre_flight_analysis"]
        assert analysis["devices_to_process"] == 2
        assert analysis["estimated_operations"]["manufacturers"] == 1  # Both Cisco
        assert analysis["estimated_operations"]["sites"] == 2  # Amsterdam, Rotterdam
        assert analysis["estimated_operations"]["device_roles"] == 2  # Access, Distribution
        assert analysis["estimated_operations"]["device_types"] == 1  # Both Catalyst 9300
        assert analysis["estimated_operations"]["devices"] == 2
        assert analysis["dry_run_mode"] is True
    
    @patch('netbox_mcp.server.netbox_client')
    @patch('netbox_mcp.server.NetBoxBulkOrchestrator')
    def test_bulk_devices_successful_execution(self, mock_orchestrator_class, mock_client, sample_devices_data):
        """Test successful bulk device execution."""
        # Setup mocks
        mock_client.config.safety.dry_run_mode = False
        
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.generate_batch_id.return_value = "batch_test_123"
        
        # Mock normalize_device_data
        mock_orchestrator.normalize_device_data.return_value = {
            "core_objects": {"manufacturer": "Cisco"},
            "relationship_objects": {"device": {"name": "switch-01"}}
        }
        
        # Mock pass execution
        pass_1_results = {"manufacturer_id": 1, "site_id": 2, "device_role_id": 3, "device_type_id": 4}
        pass_2_results = {"device_id": 10}
        
        mock_orchestrator.execute_pass_1.return_value = pass_1_results
        mock_orchestrator.execute_pass_2.return_value = pass_2_results
        
        # Mock operation report
        mock_orchestrator.generate_operation_report.return_value = {
            "batch_id": "batch_test_123",
            "operation_summary": {
                "total_objects_processed": 5,
                "total_errors": 0,
                "success_rate": 100.0
            }
        }
        
        result = netbox_bulk_ensure_devices(sample_devices_data, confirm=True)
        
        # Verify orchestrator was initialized
        mock_orchestrator_class.assert_called_once_with(mock_client)
        
        # Verify batch ID generation
        mock_orchestrator.generate_batch_id.assert_called_once()
        
        # Verify each device was processed
        assert mock_orchestrator.normalize_device_data.call_count == 2
        assert mock_orchestrator.execute_pass_1.call_count == 2
        assert mock_orchestrator.execute_pass_2.call_count == 2
        
        # Verify result structure
        assert result["success"] is True
        assert result["action"] == "bulk_device_operation"
        assert result["batch_id"] == "batch_test_123"
        
        summary = result["summary"]
        assert summary["devices_processed"] == 2
        assert summary["devices_successful"] == 2
        assert summary["devices_failed"] == 0
        assert summary["success_rate"] == 100.0
        
        # Verify detailed results
        detailed = result["detailed_results"]
        assert len(detailed["pass_1_results"]) == 2
        assert len(detailed["pass_2_results"]) == 2
        assert len(detailed["errors"]) == 0
        
        # Verify operation report included
        assert "operation_report" in result
    
    @patch('netbox_mcp.server.netbox_client')
    @patch('netbox_mcp.server.NetBoxBulkOrchestrator')
    def test_bulk_devices_partial_failure(self, mock_orchestrator_class, mock_client, sample_devices_data):
        """Test bulk operation with some device failures."""
        # Setup mocks
        mock_client.config.safety.dry_run_mode = False
        
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.generate_batch_id.return_value = "batch_test_456"
        
        # First device succeeds, second fails
        call_count = 0
        def mock_normalize_side_effect(device_data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"core_objects": {}, "relationship_objects": {}}
            else:
                raise Exception("Device processing failed")
        
        mock_orchestrator.normalize_device_data.side_effect = mock_normalize_side_effect
        mock_orchestrator.execute_pass_1.return_value = {"device_type_id": 1}
        mock_orchestrator.execute_pass_2.return_value = {"device_id": 1}
        
        mock_orchestrator.generate_operation_report.return_value = {
            "batch_id": "batch_test_456",
            "operation_summary": {"total_errors": 1}
        }
        
        result = netbox_bulk_ensure_devices(sample_devices_data, confirm=True)
        
        # Should fail overall due to one device failure
        assert result["success"] is False
        
        summary = result["summary"]
        assert summary["devices_processed"] == 1  # Only first device processed
        assert summary["devices_successful"] == 1
        assert summary["devices_failed"] == 1
        assert summary["success_rate"] == 50.0
        
        # Should have error details
        detailed = result["detailed_results"]
        assert len(detailed["errors"]) == 1
        error = detailed["errors"][0]
        assert error["device_name"] == "switch-02"
        assert "Device processing failed" in error["error"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_bulk_devices_orchestrator_import_error(self, mock_client, sample_devices_data):
        """Test handling of orchestrator import errors."""
        # Mock import failure by patching the import
        with patch('netbox_mcp.server.NetBoxBulkOrchestrator', side_effect=ImportError("Module not found")):
            result = netbox_bulk_ensure_devices(sample_devices_data, confirm=True)
            
            assert result["success"] is False
            assert "UnexpectedError" in result["error_type"]
            assert "Bulk operation failed" in result["error"]