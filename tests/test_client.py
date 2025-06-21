"""
Tests for NetBox client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import ConnectionError, Timeout, HTTPError

from netbox_mcp.client import NetBoxClient, ConnectionStatus
from netbox_mcp.config import NetBoxConfig, SafetyConfig
from netbox_mcp.exceptions import (
    NetBoxConnectionError,
    NetBoxAuthError,
    NetBoxPermissionError,
    NetBoxError,
    NetBoxNotFoundError
)


@pytest.fixture
def mock_config():
    """Create a mock NetBox configuration."""
    return NetBoxConfig(
        url="https://netbox.test.com",
        token="test-token-123",
        timeout=30,
        verify_ssl=True,
        safety=SafetyConfig()
    )


@pytest.fixture 
def mock_api():
    """Create a mock pynetbox API."""
    api = Mock()
    api.http_session = Mock()
    api.http_session.headers = {}
    return api


class TestNetBoxClient:
    """Test NetBox client initialization and basic functionality."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_client_initialization(self, mock_pynetbox_api, mock_config, mock_api):
        """Test client initialization with valid config."""
        mock_pynetbox_api.return_value = mock_api
        
        client = NetBoxClient(mock_config)
        
        assert client.config == mock_config
        mock_pynetbox_api.assert_called_once_with(
            url="https://netbox.test.com",
            token="test-token-123",
            threading=True
        )
        assert mock_api.http_session.verify is True
        assert mock_api.http_session.timeout == 30
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_client_initialization_with_custom_headers(self, mock_pynetbox_api, mock_config, mock_api):
        """Test client initialization with custom headers."""
        mock_pynetbox_api.return_value = mock_api
        mock_config.custom_headers = {"X-Custom": "test-value"}
        
        # Mock headers as Mock object with update method
        mock_headers = Mock()
        mock_api.http_session.headers = mock_headers
        
        client = NetBoxClient(mock_config)
        
        mock_headers.update.assert_called_once_with({"X-Custom": "test-value"})
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_client_initialization_failure(self, mock_pynetbox_api, mock_config):
        """Test client initialization failure."""
        mock_pynetbox_api.side_effect = Exception("Connection failed")
        
        with pytest.raises(NetBoxConnectionError, match="Failed to initialize NetBox API connection"):
            NetBoxClient(mock_config)


class TestHealthCheck:
    """Test health check functionality."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_health_check_success(self, mock_pynetbox_api, mock_config, mock_api):
        """Test successful health check."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.status.return_value = {
            'netbox-version': '4.2.9',
            'python-version': '3.12.3',
            'django-version': '5.1.8',
            'plugins': {'test-plugin': '1.0.0'}
        }
        
        client = NetBoxClient(mock_config)
        status = client.health_check()
        
        assert status.connected is True
        assert status.version == '4.2.9'
        assert status.python_version == '3.12.3'
        assert status.django_version == '5.1.8'
        assert status.plugins == {'test-plugin': '1.0.0'}
        assert status.response_time_ms is not None
        assert status.response_time_ms > 0
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_health_check_connection_error(self, mock_pynetbox_api, mock_config, mock_api):
        """Test health check with connection error."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.status.side_effect = ConnectionError("Connection failed")
        
        client = NetBoxClient(mock_config)
        
        with pytest.raises(NetBoxConnectionError, match="Connection failed"):
            client.health_check()
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_health_check_timeout(self, mock_pynetbox_api, mock_config, mock_api):
        """Test health check with timeout."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.status.side_effect = Timeout("Request timed out")
        
        client = NetBoxClient(mock_config)
        
        with pytest.raises(NetBoxConnectionError, match="Request timed out"):
            client.health_check()
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_health_check_auth_error(self, mock_pynetbox_api, mock_config, mock_api):
        """Test health check with authentication error."""
        mock_pynetbox_api.return_value = mock_api
        
        # Create mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 401
        http_error = HTTPError(response=mock_response)
        mock_api.status.side_effect = http_error
        
        client = NetBoxClient(mock_config)
        
        with pytest.raises(NetBoxAuthError, match="Authentication failed"):
            client.health_check()
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_health_check_permission_error(self, mock_pynetbox_api, mock_config, mock_api):
        """Test health check with permission error."""
        mock_pynetbox_api.return_value = mock_api
        
        # Create mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 403
        http_error = HTTPError(response=mock_response)
        mock_api.status.side_effect = http_error
        
        client = NetBoxClient(mock_config)
        
        with pytest.raises(NetBoxPermissionError, match="Permission denied"):
            client.health_check()


class TestDeviceOperations:
    """Test device-related operations."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_device_success(self, mock_pynetbox_api, mock_config, mock_api):
        """Test successful device retrieval."""
        mock_pynetbox_api.return_value = mock_api
        
        # Mock device object
        mock_device = Mock()
        mock_device.id = 1
        mock_device.name = "test-device"
        mock_device.device_type.id = 10
        mock_device.device_type.display = "test-type"
        mock_device.device_type.manufacturer.name = "test-manufacturer"
        mock_device.device_type.model = "test-model"
        mock_device.device_type.slug = "test-type"
        mock_device.site.id = 5
        mock_device.site.name = "test-site"
        mock_device.site.slug = "test-site"
        mock_device.role.id = 3
        mock_device.role.name = "test-role"
        mock_device.role.slug = "test-role"
        mock_device.status.value = "active"
        mock_device.status.label = "Active"
        mock_device.serial = "12345"
        mock_device.asset_tag = "AT001"
        mock_device.primary_ip4 = None
        mock_device.primary_ip6 = None
        mock_device.location = None
        mock_device.rack = None
        mock_device.position = None
        mock_device.description = "Test device"
        mock_device.comments = ""
        mock_device.tags = []
        mock_device.custom_fields = {}
        mock_device.created = "2023-01-01T00:00:00Z"
        mock_device.last_updated = "2023-01-02T00:00:00Z"
        
        mock_api.dcim.devices.filter.return_value = [mock_device]
        
        client = NetBoxClient(mock_config)
        device = client.get_device("test-device")
        
        assert device is not None
        assert device['id'] == 1
        assert device['name'] == "test-device"
        assert device['device_type']['name'] == "test-type"
        assert device['site']['name'] == "test-site"
        assert device['role']['name'] == "test-role"
        
        mock_api.dcim.devices.filter.assert_called_once_with(name="test-device")
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_device_with_site(self, mock_pynetbox_api, mock_config, mock_api):
        """Test device retrieval with site filter."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.dcim.devices.filter.return_value = []
        
        client = NetBoxClient(mock_config)
        device = client.get_device("test-device", site="test-site")
        
        mock_api.dcim.devices.filter.assert_called_once_with(name="test-device", site="test-site")
        assert device is None
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_device_not_found(self, mock_pynetbox_api, mock_config, mock_api):
        """Test device not found."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.dcim.devices.filter.return_value = []
        
        client = NetBoxClient(mock_config)
        device = client.get_device("nonexistent-device")
        
        assert device is None
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_device_error(self, mock_pynetbox_api, mock_config, mock_api):
        """Test device retrieval error."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.dcim.devices.filter.side_effect = Exception("API error")
        
        client = NetBoxClient(mock_config)
        
        with pytest.raises(NetBoxError, match="Failed to get device"):
            client.get_device("test-device")
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_list_devices_success(self, mock_pynetbox_api, mock_config, mock_api):
        """Test successful device listing."""
        mock_pynetbox_api.return_value = mock_api
        
        # Mock device objects
        mock_device1 = Mock()
        mock_device1.id = 1
        mock_device1.name = "device1"
        mock_device1.device_type.display = "type1"
        mock_device1.site.name = "site1"
        mock_device1.role.name = "role1"
        mock_device1.status.label = "Active"
        mock_device1.primary_ip4 = None
        mock_device1.description = "Device 1"
        mock_device1.last_updated = "2023-01-01T00:00:00Z"
        
        mock_device2 = Mock()
        mock_device2.id = 2
        mock_device2.name = "device2"
        mock_device2.device_type.display = "type2"
        mock_device2.site.name = "site2"
        mock_device2.role.name = "role2"
        mock_device2.status.label = "Active"
        mock_device2.primary_ip4 = None
        mock_device2.description = "Device 2"
        mock_device2.last_updated = "2023-01-02T00:00:00Z"
        
        mock_api.dcim.devices.all.return_value = [mock_device1, mock_device2]
        
        client = NetBoxClient(mock_config)
        devices = client.list_devices()
        
        assert len(devices) == 2
        assert devices[0]['name'] == "device1"
        assert devices[1]['name'] == "device2"
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_list_devices_with_filters(self, mock_pynetbox_api, mock_config, mock_api):
        """Test device listing with filters."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.dcim.devices.filter.return_value = []
        
        client = NetBoxClient(mock_config)
        devices = client.list_devices(filters={'site': 'test-site'})
        
        mock_api.dcim.devices.filter.assert_called_once_with(site='test-site')
        assert devices == []
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_list_devices_with_limit(self, mock_pynetbox_api, mock_config, mock_api):
        """Test device listing with limit."""
        mock_pynetbox_api.return_value = mock_api
        
        # Create more devices than the limit
        mock_devices = []
        for i in range(5):
            mock_device = Mock()
            mock_device.id = i
            mock_device.name = f"device{i}"
            mock_device.device_type.display = f"type{i}"
            mock_device.site.name = f"site{i}"
            mock_device.role.name = f"role{i}"
            mock_device.status.label = "Active"
            mock_device.primary_ip4 = None
            mock_device.description = f"Device {i}"
            mock_device.last_updated = "2023-01-01T00:00:00Z"
            mock_devices.append(mock_device)
        
        mock_api.dcim.devices.all.return_value = mock_devices
        
        client = NetBoxClient(mock_config)
        devices = client.list_devices(limit=3)
        
        assert len(devices) == 3
        assert devices[0]['name'] == "device0"
        assert devices[2]['name'] == "device2"


class TestSiteOperations:
    """Test site-related operations."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_site_success(self, mock_pynetbox_api, mock_config, mock_api):
        """Test successful site retrieval."""
        mock_pynetbox_api.return_value = mock_api
        
        # Mock site object
        mock_site = Mock()
        mock_site.id = 1
        mock_site.name = "test-site"
        mock_site.slug = "test-site"
        mock_site.status.value = "active"
        mock_site.status.label = "Active"
        mock_site.region = None
        mock_site.group = None
        mock_site.tenant = None
        mock_site.facility = ""
        mock_site.time_zone = None
        mock_site.description = "Test site"
        mock_site.physical_address = "123 Test St"
        mock_site.shipping_address = ""
        mock_site.latitude = None
        mock_site.longitude = None
        mock_site.comments = ""
        mock_site.tags = []
        mock_site.custom_fields = {}
        mock_site.created = "2023-01-01T00:00:00Z"
        mock_site.last_updated = "2023-01-02T00:00:00Z"
        mock_site.device_count = 5
        mock_site.rack_count = 2
        
        mock_api.dcim.sites.filter.return_value = [mock_site]
        
        client = NetBoxClient(mock_config)
        site = client.get_site_by_name("test-site")
        
        assert site is not None
        assert site['id'] == 1
        assert site['name'] == "test-site"
        assert site['slug'] == "test-site"
        assert site['device_count'] == 5
        
        mock_api.dcim.sites.filter.assert_called_once_with(name="test-site")
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_site_not_found(self, mock_pynetbox_api, mock_config, mock_api):
        """Test site not found."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.dcim.sites.filter.return_value = []
        
        client = NetBoxClient(mock_config)
        site = client.get_site_by_name("nonexistent-site")
        
        assert site is None


class TestInterfaceOperations:
    """Test interface-related operations."""
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_device_interfaces_success(self, mock_pynetbox_api, mock_config, mock_api):
        """Test successful device interface retrieval."""
        mock_pynetbox_api.return_value = mock_api
        
        # Mock device
        mock_device = Mock()
        mock_device.id = 1
        mock_device.name = "test-device"
        mock_device.device_type.id = 10
        mock_device.device_type.display = "test-type"
        mock_device.device_type.manufacturer.name = "test-manufacturer"
        mock_device.device_type.model = "test-model"
        mock_device.device_type.slug = "test-type"
        mock_device.site.id = 5
        mock_device.site.name = "test-site"
        mock_device.site.slug = "test-site"
        mock_device.role.id = 3
        mock_device.role.name = "test-role"
        mock_device.role.slug = "test-role"
        mock_device.status.value = "active"
        mock_device.status.label = "Active"
        mock_device.serial = "12345"
        mock_device.asset_tag = "AT001"
        mock_device.primary_ip4 = None
        mock_device.primary_ip6 = None
        mock_device.location = None
        mock_device.rack = None
        mock_device.position = None
        mock_device.description = "Test device"
        mock_device.comments = ""
        mock_device.tags = []
        mock_device.custom_fields = {}
        mock_device.created = "2023-01-01T00:00:00Z"
        mock_device.last_updated = "2023-01-02T00:00:00Z"
        
        # Mock interface
        mock_interface = Mock()
        mock_interface.id = 1
        mock_interface.name = "eth0"
        mock_interface.type.value = "1000base-t"
        mock_interface.type.label = "1000BASE-T (1GE)"
        mock_interface.enabled = True
        mock_interface.device.id = 1
        mock_interface.device.name = "test-device"
        mock_interface.lag = None
        mock_interface.mtu = 1500
        mock_interface.mac_address = None
        mock_interface.speed = 1000000
        mock_interface.duplex = None
        mock_interface.wwn = None
        mock_interface.mgmt_only = False
        mock_interface.description = "Management interface"
        mock_interface.mode = None
        mock_interface.tagged_vlans = []
        mock_interface.untagged_vlan = None
        mock_interface.tags = []
        mock_interface.custom_fields = {}
        mock_interface.created = "2023-01-01T00:00:00Z"
        mock_interface.last_updated = "2023-01-02T00:00:00Z"
        
        mock_api.dcim.devices.filter.return_value = [mock_device]
        mock_api.dcim.interfaces.filter.return_value = [mock_interface]
        
        client = NetBoxClient(mock_config)
        interfaces = client.get_device_interfaces("test-device")
        
        assert len(interfaces) == 1
        assert interfaces[0]['name'] == "eth0"
        assert interfaces[0]['type']['value'] == "1000base-t"
        assert interfaces[0]['enabled'] is True
        
        mock_api.dcim.interfaces.filter.assert_called_once_with(device_id=1)
    
    @patch('netbox_mcp.client.pynetbox.api')
    def test_get_device_interfaces_device_not_found(self, mock_pynetbox_api, mock_config, mock_api):
        """Test interface retrieval for non-existent device."""
        mock_pynetbox_api.return_value = mock_api
        mock_api.dcim.devices.filter.return_value = []
        
        client = NetBoxClient(mock_config)
        
        with pytest.raises(NetBoxNotFoundError, match="Device not found"):
            client.get_device_interfaces("nonexistent-device")