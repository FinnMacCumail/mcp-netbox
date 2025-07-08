"""
Comprehensive tests for cable color parameter support.

This module tests the enhanced netbox_create_cable_connection function
with cable_color parameter support for colored cable documentation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from netbox_mcp.tools.dcim.cables import netbox_create_cable_connection
from netbox_mcp.client import NetBoxClient
from netbox_mcp.exceptions import NetBoxValidationError


class TestCableColorSupport:
    """Test cable color parameter support in cable creation."""
    
    def setup_method(self):
        """Setup test client and mock data."""
        self.mock_client = Mock(spec=NetBoxClient)
        
        # Create mock dcim namespace
        self.mock_client.dcim = Mock()
        self.mock_client.dcim.devices = Mock()
        self.mock_client.dcim.interfaces = Mock()
        self.mock_client.dcim.cables = Mock()
        
        # Create mock cache
        self.mock_client.cache = Mock()
        self.mock_client.cache.invalidate_for_object = Mock()
        self.mock_client.cache.invalidate_pattern = Mock()
        
        # Mock device and interface data
        self.mock_device_a = {
            'id': 1, 'name': 'server-01',
            'device_type': {'model': 'PowerEdge R740'}
        }
        
        self.mock_device_b = {
            'id': 2, 'name': 'switch1.k3',
            'device_type': {'model': 'Catalyst 9300'}
        }
        
        self.mock_interface_a = {
            'id': 101, 'name': 'lom1', 'device': 1,
            'cable': None, 'type': {'value': '1000base-t'}
        }
        
        self.mock_interface_b = {
            'id': 201, 'name': 'Te1/1/1', 'device': 2,
            'cable': None, 'type': {'value': '10gbase-x-sfpp'}
        }
        
        # Mock successful cable creation response
        self.mock_cable_response = {
            'id': 123,
            'label': 'Pink Cable',
            'type': {'value': 'cat6'},
            'color': 'pink',
            'status': {'value': 'connected'},
            'length': 5,
            'length_unit': {'value': 'm'},
            'a_terminations': [{'object_id': 101, 'object_type': 'dcim.interface'}],
            'b_terminations': [{'object_id': 201, 'object_type': 'dcim.interface'}]
        }
        
        # Setup common mock behavior
        self.setup_common_mocks()
    
    def setup_common_mocks(self):
        """Setup common mock behavior for most tests."""
        
        # Mock device lookups
        def mock_device_filter(name):
            if name == 'server-01':
                return [self.mock_device_a]
            elif name == 'switch1.k3':
                return [self.mock_device_b]
            return []
        
        self.mock_client.dcim.devices.filter.side_effect = mock_device_filter
        
        # Mock interface lookups
        def mock_interface_filter(device_id, name):
            if device_id == 1 and name == 'lom1':
                return [self.mock_interface_a]
            elif device_id == 2 and name == 'Te1/1/1':
                return [self.mock_interface_b]
            return []
        
        self.mock_client.dcim.interfaces.filter.side_effect = mock_interface_filter
        
        # Mock cable creation
        self.mock_client.dcim.cables.create.return_value = self.mock_cable_response
    
    def test_cable_creation_with_pink_color(self):
        """Test cable creation with pink color."""
        
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="pink",
            confirm=True
        )
        
        # Verify success
        assert result["success"] is True
        assert result["action"] == "created"
        
        # Verify cable creation was called with color
        call_args = self.mock_client.dcim.cables.create.call_args
        create_kwargs = call_args[1]  # Keyword arguments
        assert create_kwargs["color"] == "pink"
        assert create_kwargs["type"] == "cat6"
        
        # Verify response includes color
        cable_info = result["cable"]
        assert cable_info["color"] == "pink"
    
    def test_cable_creation_with_all_supported_colors(self):
        """Test cable creation with all supported colors."""
        
        supported_colors = [
            "pink", "red", "blue", "green", "yellow", "orange",
            "purple", "grey", "black", "white", "brown", "cyan",
            "magenta", "lime", "silver", "gold"
        ]
        
        for color in supported_colors:
            # Reset mock for each color test
            self.mock_client.reset_mock()
            self.setup_common_mocks()
            
            # Update mock response for this color
            self.mock_cable_response['color'] = color
            self.mock_client.dcim.cables.create.return_value = self.mock_cable_response
            
            result = netbox_create_cable_connection(
                client=self.mock_client,
                device_a_name="server-01",
                interface_a_name="lom1",
                device_b_name="switch1.k3",
                interface_b_name="Te1/1/1",
                cable_type="cat6",
                cable_color=color,
                confirm=True
            )
            
            # Verify success for this color
            assert result["success"] is True, f"Failed for color: {color}"
            assert result["action"] == "created"
            
            # Verify color was passed to NetBox
            call_args = self.mock_client.dcim.cables.create.call_args
            create_kwargs = call_args[1]  # Keyword arguments
            assert create_kwargs["color"] == color
    
    def test_cable_creation_without_color(self):
        """Test cable creation without color parameter."""
        
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            # No cable_color parameter
            confirm=True
        )
        
        # Verify success
        assert result["success"] is True
        assert result["action"] == "created"
        
        # Verify no color was passed to NetBox
        call_args = self.mock_client.dcim.cables.create.call_args
        create_kwargs = call_args[1]  # Keyword arguments
        assert "color" not in create_kwargs
    
    def test_cable_creation_with_none_color(self):
        """Test cable creation with None color parameter."""
        
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color=None,
            confirm=True
        )
        
        # Verify success
        assert result["success"] is True
        assert result["action"] == "created"
        
        # Verify no color was passed to NetBox
        call_args = self.mock_client.dcim.cables.create.call_args
        create_kwargs = call_args[1]  # Keyword arguments
        assert "color" not in create_kwargs
    
    def test_cable_creation_with_invalid_color(self):
        """Test cable creation with invalid color."""
        
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="invalid_color",
            confirm=True
        )
        
        # Verify validation error
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_color" in result["error"]
        assert "invalid_color" in result["error"]
        
        # Verify valid colors are listed in error
        assert "pink" in result["error"]
        assert "red" in result["error"]
        assert "blue" in result["error"]
    
    def test_cable_creation_with_case_insensitive_color(self):
        """Test cable creation with case-insensitive color matching."""
        
        test_cases = [
            ("PINK", "pink"),
            ("Red", "red"),
            ("BLUE", "blue"),
            ("Green", "green"),
            ("yElLoW", "yellow")
        ]
        
        for input_color, expected_color in test_cases:
            # Reset mock for each test
            self.mock_client.reset_mock()
            self.setup_common_mocks()
            
            # Update mock response
            self.mock_cable_response['color'] = expected_color
            self.mock_client.dcim.cables.create.return_value = self.mock_cable_response
            
            result = netbox_create_cable_connection(
                client=self.mock_client,
                device_a_name="server-01",
                interface_a_name="lom1",
                device_b_name="switch1.k3",
                interface_b_name="Te1/1/1",
                cable_type="cat6",
                cable_color=input_color,
                confirm=True
            )
            
            # Verify success
            assert result["success"] is True, f"Failed for input color: {input_color}"
            
            # Verify color was normalized to lowercase
            call_args = self.mock_client.dcim.cables.create.call_args
            create_kwargs = call_args[1]  # Keyword arguments
            assert create_kwargs["color"] == expected_color
    
    def test_cable_creation_dry_run_with_color(self):
        """Test cable creation dry run with color parameter."""
        
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="pink",
            confirm=False  # Dry run
        )
        
        # Verify dry run success
        assert result["success"] is True
        assert result["action"] == "dry_run"
        assert result["dry_run"] is True
        
        # Verify cable preview includes color
        cable_preview = result["cable"]
        assert cable_preview["color"] == "pink"
        assert cable_preview["type"] == "cat6"
        
        # Verify no actual cable was created
        assert not self.mock_client.dcim.cables.create.called
    
    def test_cable_creation_with_color_and_other_params(self):
        """Test cable creation with color combined with other parameters."""
        
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6a",
            cable_color="orange",
            cable_length=10,
            cable_length_unit="m",
            label="Orange Uplink Cable",
            description="Server to switch uplink",
            confirm=True
        )
        
        # Verify success
        assert result["success"] is True
        assert result["action"] == "created"
        
        # Verify all parameters were passed correctly
        call_args = self.mock_client.dcim.cables.create.call_args
        create_kwargs = call_args[1]  # Keyword arguments
        assert create_kwargs["type"] == "cat6a"
        assert create_kwargs["color"] == "orange"
        assert create_kwargs["length"] == 10
        assert create_kwargs["length_unit"] == "m"
        assert create_kwargs["label"] == "Orange Uplink Cable"
        assert create_kwargs["description"] == "Server to switch uplink"
    
    def test_cable_color_validation_edge_cases(self):
        """Test edge cases for cable color validation."""
        
        # Test empty string
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_color" in result["error"]
        
        # Test whitespace only
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="   ",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_color" in result["error"]
        
        # Test numeric color
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="123",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_color" in result["error"]
    
    def test_cable_color_with_special_characters(self):
        """Test cable color handling with special characters."""
        
        # Test color with hyphens (should be invalid)
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="dark-blue",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_color" in result["error"]
        
        # Test color with underscores (should be invalid)
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="light_green",
            confirm=True
        )
        
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid cable_color" in result["error"]


class TestCableColorIntegration:
    """Test cable color integration with existing cable functionality."""
    
    def setup_method(self):
        """Setup test client."""
        self.mock_client = Mock(spec=NetBoxClient)
        
        # Create mock dcim namespace
        self.mock_client.dcim = Mock()
        self.mock_client.dcim.devices = Mock()
        self.mock_client.dcim.interfaces = Mock()
        self.mock_client.dcim.cables = Mock()
        
        # Create mock cache
        self.mock_client.cache = Mock()
        self.mock_client.cache.invalidate_for_object = Mock()
        self.mock_client.cache.invalidate_pattern = Mock()
    
    def test_cable_color_validation_function(self):
        """Test the cable color validation function directly."""
        
        # This tests the internal validation logic
        # Since we can't easily access the internal function, we test via the main function
        
        valid_colors = [
            "pink", "red", "blue", "green", "yellow", "orange",
            "purple", "grey", "black", "white", "brown", "cyan",
            "magenta", "lime", "silver", "gold"
        ]
        
        # Test that all valid colors pass validation
        for color in valid_colors:
            # Use a minimal mock setup
            self.mock_client.dcim.devices.filter.return_value = []
            
            result = netbox_create_cable_connection(
                client=self.mock_client,
                device_a_name="test-device-a",
                interface_a_name="test-interface-a",
                device_b_name="test-device-b",
                interface_b_name="test-interface-b",
                cable_type="cat6",
                cable_color=color,
                confirm=True
            )
            
            # Should fail due to device not found, not color validation
            assert result["success"] is False
            assert result["error_type"] != "ValidationError" or "Invalid cable_color" not in result["error"]
    
    def test_cable_color_with_different_cable_types(self):
        """Test cable color with different cable types."""
        
        cable_types = ["cat6", "cat6a", "cat7", "mmf", "smf", "dac-active"]
        colors = ["pink", "blue", "green", "red"]
        
        for cable_type in cable_types:
            for color in colors:
                # Mock devices not found to test validation only
                self.mock_client.dcim.devices.filter.return_value = []
                
                result = netbox_create_cable_connection(
                    client=self.mock_client,
                    device_a_name="test-device-a",
                    interface_a_name="test-interface-a",
                    device_b_name="test-device-b",
                    interface_b_name="test-interface-b",
                    cable_type=cable_type,
                    cable_color=color,
                    confirm=True
                )
                
                # Should fail due to device not found, not due to color/type validation
                assert result["success"] is False
                assert result["error_type"] != "ValidationError" or (
                    "Invalid cable_color" not in result["error"] and
                    "Invalid cable_type" not in result["error"]
                )
    
    @patch('netbox_mcp.tools.dcim.cables.logger')
    def test_cable_color_logging(self, mock_logger):
        """Test that cable color is properly logged."""
        
        # Setup successful cable creation
        self.mock_client.dcim.devices.filter.side_effect = [
            [{'id': 1, 'name': 'server-01'}],
            [{'id': 2, 'name': 'switch1.k3'}]
        ]
        
        self.mock_client.dcim.interfaces.filter.return_value = [
            {'id': 101, 'name': 'lom1', 'cable': None}
        ]
        
        self.mock_client.dcim.cables.create.return_value = {
            'id': 123, 'color': 'pink', 'type': {'value': 'cat6'}
        }
        
        # Execute with color
        result = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="server-01",
            interface_a_name="lom1",
            device_b_name="switch1.k3",
            interface_b_name="Te1/1/1",
            cable_type="cat6",
            cable_color="pink",
            confirm=True
        )
        
        # Verify logging was called (we can't easily check the exact message)
        assert mock_logger.info.called or mock_logger.debug.called
    
    def test_cable_color_parameter_order(self):
        """Test that cable_color parameter position doesn't affect functionality."""
        
        # Test with color parameter in different positions
        # This mainly tests that the parameter is properly defined in function signature
        
        # Mock minimal setup
        self.mock_client.dcim.devices.filter.return_value = []
        
        # These should all produce the same validation error (device not found)
        # regardless of parameter order
        
        result1 = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="test-device-a",
            interface_a_name="test-interface-a",
            device_b_name="test-device-b",
            interface_b_name="test-interface-b",
            cable_color="pink",  # Early position
            cable_type="cat6",
            confirm=True
        )
        
        result2 = netbox_create_cable_connection(
            client=self.mock_client,
            device_a_name="test-device-a",
            interface_a_name="test-interface-a",
            device_b_name="test-device-b",
            interface_b_name="test-interface-b",
            cable_type="cat6",
            cable_color="pink",  # Later position
            confirm=True
        )
        
        # Both should fail the same way (device not found)
        assert result1["success"] is False
        assert result2["success"] is False
        assert result1["error_type"] == result2["error_type"]


class TestCableColorDocumentation:
    """Test cable color documentation and help information."""
    
    def test_cable_color_error_message_completeness(self):
        """Test that color validation error includes all supported colors."""
        
        mock_client = Mock(spec=NetBoxClient)
        
        result = netbox_create_cable_connection(
            client=mock_client,
            device_a_name="test-device-a",
            interface_a_name="test-interface-a",
            device_b_name="test-device-b",
            interface_b_name="test-interface-b",
            cable_type="cat6",
            cable_color="invalid_color",
            confirm=True
        )
        
        # Verify error message includes all supported colors
        assert result["success"] is False
        assert "Invalid cable_color" in result["error"]
        
        expected_colors = [
            "pink", "red", "blue", "green", "yellow", "orange",
            "purple", "grey", "black", "white", "brown", "cyan",
            "magenta", "lime", "silver", "gold"
        ]
        
        for color in expected_colors:
            assert color in result["error"]
    
    def test_cable_color_function_signature(self):
        """Test that cable_color parameter is properly defined in function signature."""
        
        import inspect
        from netbox_mcp.tools.dcim.cables import netbox_create_cable_connection
        
        # Get function signature
        sig = inspect.signature(netbox_create_cable_connection)
        
        # Verify cable_color parameter exists
        assert "cable_color" in sig.parameters
        
        # Verify it's optional (has default value)
        cable_color_param = sig.parameters["cable_color"]
        assert cable_color_param.default is None
        
        # Verify it's typed as Optional[str]
        assert "Optional" in str(cable_color_param.annotation) or cable_color_param.annotation is str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])