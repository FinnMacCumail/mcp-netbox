"""
Tests for NetBox MCP server
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from netbox_mcp.server import (
    netbox_health_check,
    netbox_get_device,
    netbox_list_devices,
    netbox_get_site_by_name,
    netbox_find_ip,
    netbox_get_vlan_by_name,
    netbox_get_device_interfaces,
    netbox_get_manufacturers,
    initialize_server,
    HealthCheckHandler
)
from netbox_mcp.client import ConnectionStatus
from netbox_mcp.config import NetBoxConfig, SafetyConfig
from netbox_mcp.exceptions import NetBoxError, NetBoxNotFoundError


@pytest.fixture
def mock_netbox_client():
    """Create a mock NetBox client."""
    client = Mock()
    
    # Mock health check
    status = ConnectionStatus(
        connected=True,
        version="4.2.9",
        python_version="3.12.3",
        django_version="5.1.8",
        plugins={"test-plugin": "1.0.0"},
        response_time_ms=100.0
    )
    client.health_check.return_value = status
    
    return client


class TestMCPTools:
    """Test MCP tool functions."""
    
    @patch('netbox_mcp.server.netbox_client')
    def test_health_check_success(self, mock_client, mock_netbox_client):
        """Test successful health check."""
        mock_client = mock_netbox_client
        
        result = netbox_health_check()
        
        assert result["connected"] is True
        assert result["version"] == "4.2.9"
        assert result["python_version"] == "3.12.3"
        assert result["django_version"] == "5.1.8"
        assert result["response_time_ms"] == 100.0
        assert result["plugins"] == {"test-plugin": "1.0.0"}
        assert "error" not in result
    
    @patch('netbox_mcp.server.netbox_client')
    def test_health_check_failure(self, mock_client):
        """Test health check failure."""
        mock_client.health_check.side_effect = Exception("Connection failed")
        
        result = netbox_health_check()
        
        assert result["connected"] is False
        assert "error" in result
        assert "Connection failed" in result["error"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_device_found(self, mock_client):
        """Test successful device retrieval."""
        mock_device = {
            "id": 1,
            "name": "test-device",
            "device_type": {"name": "test-type"},
            "site": {"name": "test-site"}
        }
        mock_client.get_device.return_value = mock_device
        
        result = netbox_get_device("test-device")
        
        assert result["found"] is True
        assert result["device"] == mock_device
        mock_client.get_device.assert_called_once_with("test-device", None)
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_device_with_site(self, mock_client):
        """Test device retrieval with site filter."""
        mock_client.get_device.return_value = None
        
        result = netbox_get_device("test-device", "test-site")
        
        assert result["found"] is False
        assert "not found" in result["message"]
        mock_client.get_device.assert_called_once_with("test-device", "test-site")
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_device_not_found(self, mock_client):
        """Test device not found."""
        mock_client.get_device.return_value = None
        
        result = netbox_get_device("nonexistent")
        
        assert result["found"] is False
        assert "not found" in result["message"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_device_error(self, mock_client):
        """Test device retrieval error."""
        mock_client.get_device.side_effect = NetBoxError("API error")
        
        result = netbox_get_device("test-device")
        
        assert result["found"] is False
        assert result["error"] == "API error"
        assert result["error_type"] == "NetBoxError"
    
    @patch('netbox_mcp.server.netbox_client')
    def test_list_devices_success(self, mock_client):
        """Test successful device listing."""
        mock_devices = [
            {"id": 1, "name": "device1", "device_type": "type1"},
            {"id": 2, "name": "device2", "device_type": "type2"}
        ]
        mock_client.list_devices.return_value = mock_devices
        
        result = netbox_list_devices()
        
        assert result["count"] == 2
        assert result["devices"] == mock_devices
        assert result["filters_applied"] == {}
        mock_client.list_devices.assert_called_once_with(filters=None, limit=None)
    
    @patch('netbox_mcp.server.netbox_client')
    def test_list_devices_with_filters(self, mock_client):
        """Test device listing with filters."""
        mock_client.list_devices.return_value = []
        
        result = netbox_list_devices(site="test-site", role="switch", limit=10)
        
        assert result["count"] == 0
        assert result["filters_applied"] == {"site": "test-site", "role": "switch"}
        mock_client.list_devices.assert_called_once_with(
            filters={"site": "test-site", "role": "switch"}, 
            limit=10
        )
    
    @patch('netbox_mcp.server.netbox_client')
    def test_list_devices_error(self, mock_client):
        """Test device listing error."""
        mock_client.list_devices.side_effect = NetBoxError("API error")
        
        result = netbox_list_devices()
        
        assert result["count"] == 0
        assert result["devices"] == []
        assert result["error"] == "API error"
        assert result["error_type"] == "NetBoxError"
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_site_found(self, mock_client):
        """Test successful site retrieval."""
        mock_site = {
            "id": 1,
            "name": "test-site",
            "device_count": 5
        }
        mock_client.get_site_by_name.return_value = mock_site
        
        result = netbox_get_site_by_name("test-site")
        
        assert result["found"] is True
        assert result["site"] == mock_site
        mock_client.get_site_by_name.assert_called_once_with("test-site")
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_site_not_found(self, mock_client):
        """Test site not found."""
        mock_client.get_site_by_name.return_value = None
        
        result = netbox_get_site_by_name("nonexistent")
        
        assert result["found"] is False
        assert "not found" in result["message"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_find_ip_found(self, mock_client):
        """Test successful IP address search."""
        mock_ip = {
            "id": 1,
            "address": "192.168.1.1/24",
            "status": {"label": "Active"}
        }
        mock_client.get_ip_address.return_value = mock_ip
        
        result = netbox_find_ip("192.168.1.1")
        
        assert result["found"] is True
        assert result["ip_address"] == mock_ip
        mock_client.get_ip_address.assert_called_once_with("192.168.1.1")
    
    @patch('netbox_mcp.server.netbox_client')
    def test_find_ip_not_found(self, mock_client):
        """Test IP address not found."""
        mock_client.get_ip_address.return_value = None
        
        result = netbox_find_ip("10.0.0.1")
        
        assert result["found"] is False
        assert "not found" in result["message"]
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_vlan_found(self, mock_client):
        """Test successful VLAN retrieval."""
        mock_vlan = {
            "id": 1,
            "name": "Management",
            "vid": 100
        }
        mock_client.get_vlan_by_name.return_value = mock_vlan
        
        result = netbox_get_vlan_by_name("Management")
        
        assert result["found"] is True
        assert result["vlan"] == mock_vlan
        mock_client.get_vlan_by_name.assert_called_once_with("Management", None)
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_vlan_with_site(self, mock_client):
        """Test VLAN retrieval with site filter."""
        mock_client.get_vlan_by_name.return_value = None
        
        result = netbox_get_vlan_by_name("VLAN-100", "datacenter")
        
        assert result["found"] is False
        mock_client.get_vlan_by_name.assert_called_once_with("VLAN-100", "datacenter")
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_device_interfaces_success(self, mock_client):
        """Test successful interface retrieval."""
        mock_interfaces = [
            {"id": 1, "name": "eth0", "type": {"label": "1000BASE-T"}},
            {"id": 2, "name": "eth1", "type": {"label": "1000BASE-T"}}
        ]
        mock_client.get_device_interfaces.return_value = mock_interfaces
        
        result = netbox_get_device_interfaces("test-device")
        
        assert result["device_name"] == "test-device"
        assert result["interface_count"] == 2
        assert result["interfaces"] == mock_interfaces
        mock_client.get_device_interfaces.assert_called_once_with("test-device")
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_device_interfaces_device_not_found(self, mock_client):
        """Test interface retrieval for non-existent device."""
        mock_client.get_device_interfaces.side_effect = NetBoxNotFoundError("Device not found")
        
        result = netbox_get_device_interfaces("nonexistent")
        
        assert result["device_name"] == "nonexistent"
        assert result["interface_count"] == 0
        assert result["interfaces"] == []
        assert result["error_type"] == "DeviceNotFound"
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_manufacturers_success(self, mock_client):
        """Test successful manufacturer retrieval."""
        mock_manufacturers = [
            {"id": 1, "name": "Cisco", "slug": "cisco"},
            {"id": 2, "name": "Juniper", "slug": "juniper"}
        ]
        mock_client.get_manufacturers.return_value = mock_manufacturers
        
        result = netbox_get_manufacturers()
        
        assert result["count"] == 2
        assert result["manufacturers"] == mock_manufacturers
        mock_client.get_manufacturers.assert_called_once_with(limit=None)
    
    @patch('netbox_mcp.server.netbox_client')
    def test_get_manufacturers_with_limit(self, mock_client):
        """Test manufacturer retrieval with limit."""
        mock_client.get_manufacturers.return_value = []
        
        result = netbox_get_manufacturers(limit=5)
        
        mock_client.get_manufacturers.assert_called_once_with(limit=5)


class TestHealthCheckHandler:
    """Test HTTP health check handler."""
    
    def test_health_endpoint(self):
        """Test /health endpoint."""
        handler = HealthCheckHandler(Mock(), ('127.0.0.1', 8080), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.path = '/health'
        
        handler.do_GET()
        
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_with('Content-Type', 'application/json')
        handler.end_headers.assert_called_once()
        
        # Check response content
        written_data = handler.wfile.write.call_args[0][0]
        response = json.loads(written_data.decode())
        assert response["status"] == "OK"
        assert response["service"] == "netbox-mcp"
        assert response["version"] == "0.1.0"
    
    def test_healthz_endpoint(self):
        """Test /healthz endpoint."""
        handler = HealthCheckHandler(Mock(), ('127.0.0.1', 8080), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.path = '/healthz'
        
        handler.do_GET()
        
        handler.send_response.assert_called_once_with(200)
        
        # Check response content
        written_data = handler.wfile.write.call_args[0][0]
        response = json.loads(written_data.decode())
        assert response["status"] == "OK"
    
    @patch('netbox_mcp.server.netbox_client')
    def test_readyz_endpoint_connected(self, mock_client):
        """Test /readyz endpoint when NetBox is connected."""
        # Mock successful health check
        status = ConnectionStatus(
            connected=True,
            version="4.2.9",
            response_time_ms=100.0
        )
        mock_client.health_check.return_value = status
        
        handler = HealthCheckHandler(Mock(), ('127.0.0.1', 8080), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.path = '/readyz'
        
        handler.do_GET()
        
        handler.send_response.assert_called_once_with(200)
        
        # Check response content
        written_data = handler.wfile.write.call_args[0][0]
        response = json.loads(written_data.decode())
        assert response["status"] == "OK"
        assert response["netbox_connected"] is True
        assert response["netbox_version"] == "4.2.9"
    
    @patch('netbox_mcp.server.netbox_client')
    def test_readyz_endpoint_disconnected(self, mock_client):
        """Test /readyz endpoint when NetBox is disconnected."""
        # Mock failed health check
        status = ConnectionStatus(
            connected=False,
            error="Connection failed"
        )
        mock_client.health_check.return_value = status
        
        handler = HealthCheckHandler(Mock(), ('127.0.0.1', 8080), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.path = '/readyz'
        
        handler.do_GET()
        
        handler.send_response.assert_called_once_with(503)
        
        # Check response content
        written_data = handler.wfile.write.call_args[0][0]
        response = json.loads(written_data.decode())
        assert response["status"] == "Service Unavailable"
        assert response["netbox_connected"] is False
        assert "error" in response
    
    def test_not_found_endpoint(self):
        """Test 404 for unknown endpoints."""
        handler = HealthCheckHandler(Mock(), ('127.0.0.1', 8080), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.path = '/unknown'
        
        handler.do_GET()
        
        handler.send_response.assert_called_once_with(404)
        
        # Check response content
        written_data = handler.wfile.write.call_args[0][0]
        response = json.loads(written_data.decode())
        assert response["error"] == "Not Found"


class TestServerInitialization:
    """Test server initialization."""
    
    @patch('netbox_mcp.server.load_config')
    @patch('netbox_mcp.server.NetBoxClient')
    @patch('netbox_mcp.server.start_health_server')
    def test_initialize_server_success(self, mock_start_health, mock_client_class, mock_load_config):
        """Test successful server initialization."""
        # Mock configuration
        mock_config = NetBoxConfig(
            url="https://netbox.test.com",
            token="test-token",
            log_level="INFO",
            enable_health_server=True,
            health_check_port=8080,
            safety=SafetyConfig()
        )
        mock_load_config.return_value = mock_config
        
        # Mock client
        mock_client = Mock()
        status = ConnectionStatus(connected=True, version="4.2.9", response_time_ms=100.0)
        mock_client.health_check.return_value = status
        mock_client_class.return_value = mock_client
        
        # Initialize server
        initialize_server()
        
        # Verify calls
        mock_load_config.assert_called_once()
        mock_client_class.assert_called_once_with(mock_config)
        mock_client.health_check.assert_called_once()
        mock_start_health.assert_called_once_with(8080)
    
    @patch('netbox_mcp.server.load_config')
    def test_initialize_server_config_failure(self, mock_load_config):
        """Test server initialization failure due to config error."""
        mock_load_config.side_effect = Exception("Config error")
        
        with pytest.raises(Exception, match="Config error"):
            initialize_server()