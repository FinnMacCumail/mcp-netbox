"""
Comprehensive tests for bulk cable creation functionality.

This module tests the netbox_bulk_create_cable_connections function
that enables enterprise-grade bulk cable operations with rollback support.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from netbox_mcp.tools.dcim.cables import netbox_bulk_create_cable_connections
from netbox_mcp.client import NetBoxClient
from netbox_mcp.exceptions import NetBoxValidationError, NetBoxNotFoundError


class TestBulkCableCreation:
    """Test bulk cable creation functionality."""
    
    def setup_method(self):
        """Setup test client and mock data."""
        self.mock_client = Mock(spec=NetBoxClient)
        
        # Mock successful cable creation response
        self.mock_cable_response = {
            'id': 123,
            'label': 'Test Cable',
            'type': {'value': 'cat6'},
            'color': 'pink',
            'status': {'value': 'connected'},
            'a_terminations': [{'object_id': 101, 'object_type': 'dcim.interface'}],
            'b_terminations': [{'object_id': 201, 'object_type': 'dcim.interface'}]
        }
        
        # Sample cable connections for testing
        self.sample_connections = [
            {
                "device_a_name": "server-01",
                "interface_a_name": "lom1",
                "device_b_name": "switch1.k3",
                "interface_b_name": "Te1/1/1"
            },
            {
                "device_a_name": "server-02",
                "interface_a_name": "lom1",
                "device_b_name": "switch1.k3",
                "interface_b_name": "Te1/1/2"
            },
            {
                "device_a_name": "server-03",
                "interface_a_name": "lom1",
                "device_b_name": "switch1.k3",
                "interface_b_name": "Te1/1/3"
            }
        ]
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_bulk_cable_creation_success(self, mock_create_cable):
        """Test successful bulk cable creation."""
        
        # Mock individual cable creation success
        mock_create_cable.return_value = {
            "success": True,
            "action": "created",
            "cable": self.mock_cable_response
        }
        
        # Execute bulk creation
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            cable_color="pink",
            batch_size=2,
            confirm=True
        )
        
        # Verify success
        assert result["success"] is True
        assert result["action"] == "bulk_created"
        assert result["dry_run"] is False
        
        # Verify batch processing
        batch_results = result["batch_results"]
        assert len(batch_results) == 2  # 3 cables in batches of 2 = 2 batches
        
        # First batch (2 cables)
        assert batch_results[0]["batch_number"] == 1
        assert batch_results[0]["cables_in_batch"] == 2
        assert batch_results[0]["batch_success"] is True
        
        # Second batch (1 cable)
        assert batch_results[1]["batch_number"] == 2
        assert batch_results[1]["cables_in_batch"] == 1
        assert batch_results[1]["batch_success"] is True
        
        # Verify summary
        summary = result["summary"]
        assert summary["total_requested"] == 3
        assert summary["total_successful"] == 3
        assert summary["total_failed"] == 0
        assert summary["success_rate"] == "100.0%"
        
        # Verify individual cable creation was called 3 times
        assert mock_create_cable.call_count == 3
        
        # Verify cable creation parameters
        calls = mock_create_cable.call_args_list
        assert calls[0][1]["cable_type"] == "cat6"
        assert calls[0][1]["cable_color"] == "pink"
        assert calls[0][1]["confirm"] is True
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_bulk_cable_creation_dry_run(self, mock_create_cable):
        """Test bulk cable creation in dry-run mode."""
        
        # Mock dry-run response
        mock_create_cable.return_value = {
            "success": True,
            "action": "dry_run",
            "cable_preview": {
                "device_a_name": "server-01",
                "interface_a_name": "lom1",
                "device_b_name": "switch1.k3",
                "interface_b_name": "Te1/1/1"
            }
        }
        
        # Execute dry run
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            cable_color="pink",
            batch_size=10,
            confirm=False
        )
        
        # Verify dry run
        assert result["success"] is True
        assert result["action"] == "dry_run"
        assert result["dry_run"] is True
        
        # Verify preview
        preview = result["bulk_preview"]
        assert preview["total_cables"] == 3
        assert preview["cable_type"] == "cat6"
        assert preview["cable_color"] == "pink"
        assert preview["batch_size"] == 10
        assert preview["estimated_batches"] == 1
        
        # Verify individual previews
        cable_previews = preview["cable_previews"]
        assert len(cable_previews) == 3
        
        # Verify all calls were made with confirm=False
        calls = mock_create_cable.call_args_list
        for call in calls:
            assert call[1]["confirm"] is False
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_bulk_cable_creation_partial_failure(self, mock_create_cable):
        """Test bulk cable creation with partial failures."""
        
        # Mock mixed success/failure responses
        def mock_cable_side_effect(*args, **kwargs):
            device_a = kwargs.get('device_a_name', '')
            if device_a == 'server-02':
                return {
                    "success": False,
                    "error": "Interface not found",
                    "error_type": "NotFoundError"
                }
            return {
                "success": True,
                "action": "created",
                "cable": self.mock_cable_response
            }
        
        mock_create_cable.side_effect = mock_cable_side_effect
        
        # Execute bulk creation
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            cable_color="pink",
            batch_size=2,
            rollback_on_error=False,  # Don't rollback on individual failures
            confirm=True
        )
        
        # Verify partial success
        assert result["success"] is True  # Overall success despite individual failures
        assert result["action"] == "bulk_created"
        
        # Verify summary
        summary = result["summary"]
        assert summary["total_requested"] == 3
        assert summary["total_successful"] == 2
        assert summary["total_failed"] == 1
        assert summary["success_rate"] == "66.7%"
        
        # Verify failed cables are tracked
        failed_cables = result["failed_cables"]
        assert len(failed_cables) == 1
        assert failed_cables[0]["device_a_name"] == "server-02"
        assert failed_cables[0]["error"] == "Interface not found"
        assert failed_cables[0]["error_type"] == "NotFoundError"
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_bulk_cable_creation_rollback_on_error(self, mock_create_cable):
        """Test bulk cable creation with rollback on error."""
        
        # Mock responses: first succeeds, second fails
        responses = [
            {
                "success": True,
                "action": "created",
                "cable": {'id': 100, 'label': 'Cable 1'}
            },
            {
                "success": False,
                "error": "Critical error",
                "error_type": "ValidationError"
            }
        ]
        
        mock_create_cable.side_effect = responses
        
        # Mock rollback function
        with patch('netbox_mcp.tools.dcim.cables.netbox_disconnect_cable') as mock_disconnect:
            mock_disconnect.return_value = {"success": True}
            
            # Execute bulk creation with rollback enabled
            result = netbox_bulk_create_cable_connections(
                client=self.mock_client,
                cable_connections=self.sample_connections[:2],  # Only 2 cables
                cable_type="cat6",
                rollback_on_error=True,
                confirm=True
            )
            
            # Verify rollback was triggered
            assert result["success"] is False  # Overall failure due to rollback
            assert result["action"] == "rolled_back"
            assert "rollback_performed" in result
            assert result["rollback_performed"] is True
            
            # Verify rollback details
            rollback_info = result["rollback_info"]
            assert rollback_info["cables_rolled_back"] == 1
            assert rollback_info["rollback_successful"] is True
            
            # Verify disconnect was called for the successful cable
            mock_disconnect.assert_called_once_with(
                client=self.mock_client,
                cable_id=100,
                confirm=True
            )
    
    def test_bulk_cable_creation_validation_errors(self):
        """Test validation errors in bulk cable creation."""
        
        # Test empty cable connections
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=[],
            cable_type="cat6",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "No cable connections provided" in result["error"]
        
        # Test invalid cable type
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="invalid_type",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_type" in result["error"]
        
        # Test invalid cable color
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            cable_color="invalid_color",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_color" in result["error"]
        
        # Test invalid batch size
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            batch_size=0,
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "batch_size must be between 1 and 50" in result["error"]
    
    def test_bulk_cable_creation_connection_validation(self):
        """Test individual cable connection validation."""
        
        # Test missing required fields
        invalid_connections = [
            {
                "device_a_name": "server-01",
                # Missing interface_a_name
                "device_b_name": "switch1.k3",
                "interface_b_name": "Te1/1/1"
            }
        ]
        
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=invalid_connections,
            cable_type="cat6",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Missing required field" in result["error"]
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_bulk_cable_creation_progress_tracking(self, mock_create_cable):
        """Test progress tracking during bulk creation."""
        
        # Mock successful responses
        mock_create_cable.return_value = {
            "success": True,
            "action": "created",
            "cable": self.mock_cable_response
        }
        
        # Execute with small batch size to test multiple batches
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            batch_size=1,  # One cable per batch
            confirm=True
        )
        
        # Verify batch tracking
        batch_results = result["batch_results"]
        assert len(batch_results) == 3  # 3 cables, 1 per batch
        
        # Verify each batch has proper tracking
        for i, batch in enumerate(batch_results):
            assert batch["batch_number"] == i + 1
            assert batch["cables_in_batch"] == 1
            assert batch["batch_success"] is True
            assert "execution_time_ms" in batch
            assert batch["execution_time_ms"] >= 0
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_bulk_cable_creation_performance_metrics(self, mock_create_cable):
        """Test performance metrics collection."""
        
        # Mock responses with some delay simulation
        mock_create_cable.return_value = {
            "success": True,
            "action": "created",
            "cable": self.mock_cable_response
        }
        
        # Execute bulk creation
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            batch_size=5,
            confirm=True
        )
        
        # Verify performance metrics
        performance = result["performance_metrics"]
        assert "total_execution_time_ms" in performance
        assert "average_time_per_cable_ms" in performance
        assert "cables_per_second" in performance
        assert performance["total_execution_time_ms"] >= 0
        assert performance["average_time_per_cable_ms"] >= 0
        assert performance["cables_per_second"] > 0
    
    def test_bulk_cable_creation_edge_cases(self):
        """Test edge cases and boundary conditions."""
        
        # Test maximum batch size
        large_connections = [
            {
                "device_a_name": f"server-{i:02d}",
                "interface_a_name": "lom1",
                "device_b_name": "switch1.k3",
                "interface_b_name": f"Te1/1/{i}"
            }
            for i in range(1, 101)  # 100 connections
        ]
        
        with patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection') as mock_create:
            mock_create.return_value = {
                "success": True,
                "action": "created",
                "cable": self.mock_cable_response
            }
            
            result = netbox_bulk_create_cable_connections(
                client=self.mock_client,
                cable_connections=large_connections,
                cable_type="cat6",
                batch_size=50,  # Max batch size
                confirm=True
            )
            
            assert result["success"] is True
            assert result["summary"]["total_requested"] == 100
            assert len(result["batch_results"]) == 2  # 100 cables / 50 batch size
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_bulk_cable_creation_with_labels(self, mock_create_cable):
        """Test bulk cable creation with automatic labeling."""
        
        mock_create_cable.return_value = {
            "success": True,
            "action": "created",
            "cable": self.mock_cable_response
        }
        
        # Execute with label prefix
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=self.sample_connections,
            cable_type="cat6",
            cable_color="pink",
            label_prefix="K3-SW1",
            confirm=True
        )
        
        # Verify label generation
        assert result["success"] is True
        
        # Check that labels were passed to individual cable creation
        calls = mock_create_cable.call_args_list
        for i, call in enumerate(calls):
            expected_label = f"K3-SW1-{i+1:03d}"
            assert call[1]["label"] == expected_label


class TestBulkCableRollback:
    """Test rollback functionality for bulk cable creation."""
    
    def setup_method(self):
        """Setup test client."""
        self.mock_client = Mock(spec=NetBoxClient)
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_disconnect_cable')
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_rollback_success(self, mock_create_cable, mock_disconnect):
        """Test successful rollback of created cables."""
        
        # Setup: first cable succeeds, second fails
        created_cables = [
            {"success": True, "action": "created", "cable": {"id": 100}},
            {"success": False, "error": "Test error", "error_type": "TestError"}
        ]
        
        mock_create_cable.side_effect = created_cables
        mock_disconnect.return_value = {"success": True}
        
        # Execute with rollback enabled
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=[
                {"device_a_name": "server-01", "interface_a_name": "lom1", 
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"},
                {"device_a_name": "server-02", "interface_a_name": "lom1",
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/2"}
            ],
            cable_type="cat6",
            rollback_on_error=True,
            confirm=True
        )
        
        # Verify rollback was performed
        assert result["success"] is False
        assert result["action"] == "rolled_back"
        assert result["rollback_performed"] is True
        
        # Verify disconnect was called for the successful cable
        mock_disconnect.assert_called_once_with(
            client=self.mock_client,
            cable_id=100,
            confirm=True
        )
    
    @patch('netbox_mcp.tools.dcim.cables.netbox_disconnect_cable')
    @patch('netbox_mcp.tools.dcim.cables.netbox_create_cable_connection')
    def test_rollback_failure(self, mock_create_cable, mock_disconnect):
        """Test handling of rollback failures."""
        
        # Setup: cable creation succeeds, rollback fails
        mock_create_cable.side_effect = [
            {"success": True, "action": "created", "cable": {"id": 100}},
            {"success": False, "error": "Test error", "error_type": "TestError"}
        ]
        
        mock_disconnect.return_value = {
            "success": False,
            "error": "Rollback failed",
            "error_type": "RollbackError"
        }
        
        # Execute with rollback enabled
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=[
                {"device_a_name": "server-01", "interface_a_name": "lom1", 
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"},
                {"device_a_name": "server-02", "interface_a_name": "lom1",
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/2"}
            ],
            cable_type="cat6",
            rollback_on_error=True,
            confirm=True
        )
        
        # Verify rollback failure is reported
        assert result["success"] is False
        assert result["rollback_performed"] is True
        assert result["rollback_info"]["rollback_successful"] is False
        assert "rollback_errors" in result["rollback_info"]


class TestBulkCableValidation:
    """Test validation functionality for bulk cable operations."""
    
    def setup_method(self):
        """Setup test client."""
        self.mock_client = Mock(spec=NetBoxClient)
    
    def test_cable_type_validation(self):
        """Test cable type validation."""
        
        valid_types = [
            "cat3", "cat5", "cat5e", "cat6", "cat6a", "cat7", "cat8",
            "dac-active", "dac-passive", "mmf", "smf", "power"
        ]
        
        for cable_type in valid_types:
            result = netbox_bulk_create_cable_connections(
                client=self.mock_client,
                cable_connections=[
                    {"device_a_name": "server-01", "interface_a_name": "lom1",
                     "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"}
                ],
                cable_type=cable_type,
                confirm=False  # Dry run
            )
            
            # Should not fail validation
            assert result["success"] is True or result["error_type"] != "ValidationError"
    
    def test_cable_color_validation(self):
        """Test cable color validation."""
        
        valid_colors = [
            "pink", "red", "blue", "green", "yellow", "orange",
            "purple", "grey", "black", "white", "brown", "cyan",
            "magenta", "lime", "silver", "gold"
        ]
        
        for color in valid_colors:
            result = netbox_bulk_create_cable_connections(
                client=self.mock_client,
                cable_connections=[
                    {"device_a_name": "server-01", "interface_a_name": "lom1",
                     "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"}
                ],
                cable_type="cat6",
                cable_color=color,
                confirm=False  # Dry run
            )
            
            # Should not fail validation
            assert result["success"] is True or result["error_type"] != "ValidationError"
    
    def test_batch_size_validation(self):
        """Test batch size validation."""
        
        # Test minimum batch size
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=[
                {"device_a_name": "server-01", "interface_a_name": "lom1",
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"}
            ],
            cable_type="cat6",
            batch_size=1,  # Minimum
            confirm=False
        )
        
        assert result["success"] is True
        
        # Test maximum batch size
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=[
                {"device_a_name": "server-01", "interface_a_name": "lom1",
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"}
            ],
            cable_type="cat6",
            batch_size=50,  # Maximum
            confirm=False
        )
        
        assert result["success"] is True
        
        # Test invalid batch size (too small)
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=[
                {"device_a_name": "server-01", "interface_a_name": "lom1",
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"}
            ],
            cable_type="cat6",
            batch_size=0,
            confirm=False
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        
        # Test invalid batch size (too large)
        result = netbox_bulk_create_cable_connections(
            client=self.mock_client,
            cable_connections=[
                {"device_a_name": "server-01", "interface_a_name": "lom1",
                 "device_b_name": "switch1.k3", "interface_b_name": "Te1/1/1"}
            ],
            cable_type="cat6",
            batch_size=100,
            confirm=False
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])