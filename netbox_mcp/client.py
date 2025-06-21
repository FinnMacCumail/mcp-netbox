#!/usr/bin/env python3
"""
NetBox API Client for NetBox MCP Server

Provides a well-tested wrapper around the pynetbox library with comprehensive
error handling, connection management, and read/write operations.

Safety-first design with built-in confirmation mechanisms for write operations.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

import pynetbox
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

from .config import NetBoxConfig
from .exceptions import (
    NetBoxError,
    NetBoxConnectionError,
    NetBoxAuthError,
    NetBoxValidationError,
    NetBoxNotFoundError,
    NetBoxPermissionError,
    NetBoxWriteError,
    NetBoxConfirmationError,
    NetBoxDryRunError
)

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStatus:
    """NetBox connection status information."""
    connected: bool
    version: Optional[str] = None
    python_version: Optional[str] = None
    django_version: Optional[str] = None
    plugins: Optional[Dict[str, str]] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


class NetBoxClient:
    """
    NetBox API client with safety-first design for read/write operations.
    
    Provides a comprehensive wrapper around pynetbox with:
    - Connection validation and health checking
    - Comprehensive error handling and translation
    - Read-only operations for data exploration
    - Write operations with mandatory safety controls
    - Dry-run mode support for testing
    """
    
    def __init__(self, config: NetBoxConfig):
        """
        Initialize NetBox client with configuration.
        
        Args:
            config: NetBox configuration object
        """
        self.config = config
        self._api = None
        self._connection_status = None
        self._last_health_check = 0
        
        logger.info(f"Initializing NetBox client for {config.url}")
        
        # Log safety configuration
        if config.safety.dry_run_mode:
            logger.warning("NetBox client initialized in DRY-RUN mode - no actual writes will be performed")
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize the pynetbox API connection."""
        try:
            self._api = pynetbox.api(
                url=self.config.url,
                token=self.config.token,
                threading=True  # Enable threading for better performance
            )
            
            # Configure session settings
            self._api.http_session.verify = self.config.verify_ssl
            self._api.http_session.timeout = self.config.timeout
            
            # Add custom headers if configured
            if self.config.custom_headers:
                self._api.http_session.headers.update(self.config.custom_headers)
            
            logger.info("NetBox API connection initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize NetBox API connection: {e}"
            logger.error(error_msg)
            raise NetBoxConnectionError(error_msg, {"url": self.config.url})
    
    @property
    def api(self) -> pynetbox.api:
        """Get the pynetbox API instance."""
        if self._api is None:
            self._initialize_connection()
        return self._api
    
    def health_check(self, force: bool = False) -> ConnectionStatus:
        """
        Perform health check against NetBox API.
        
        Args:
            force: Force health check even if recently performed
            
        Returns:
            ConnectionStatus: Current connection status
        """
        # Check if we need to perform health check (cache for 60 seconds)
        current_time = time.time()
        if not force and (current_time - self._last_health_check) < 60:
            if self._connection_status:
                return self._connection_status
        
        logger.debug("Performing NetBox health check")
        start_time = time.time()
        
        try:
            # Test basic connectivity and get status
            status_data = self.api.status()
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Extract version information
            netbox_version = status_data.get('netbox-version')
            python_version = status_data.get('python-version') 
            django_version = status_data.get('django-version')
            plugins = status_data.get('plugins', {})
            
            self._connection_status = ConnectionStatus(
                connected=True,
                version=netbox_version,
                python_version=python_version,
                django_version=django_version, 
                plugins=plugins,
                response_time_ms=response_time
            )
            
            self._last_health_check = current_time
            logger.info(f"Health check successful - NetBox {netbox_version} (response: {response_time:.1f}ms)")
            
            return self._connection_status
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection failed: {e}"
            logger.error(error_msg)
            self._connection_status = ConnectionStatus(connected=False, error=error_msg)
            raise NetBoxConnectionError(error_msg, {"url": self.config.url})
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out after {self.config.timeout}s: {e}"
            logger.error(error_msg)
            self._connection_status = ConnectionStatus(connected=False, error=error_msg)
            raise NetBoxConnectionError(error_msg, {"timeout": self.config.timeout})
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed - invalid API token"
                logger.error(error_msg)
                self._connection_status = ConnectionStatus(connected=False, error=error_msg)
                raise NetBoxAuthError(error_msg, {"status_code": 401})
            elif e.response.status_code == 403:
                error_msg = "Permission denied - insufficient API token permissions"
                logger.error(error_msg)
                self._connection_status = ConnectionStatus(connected=False, error=error_msg)
                raise NetBoxPermissionError(error_msg, {"status_code": 403})
            else:
                error_msg = f"HTTP error {e.response.status_code}: {e}"
                logger.error(error_msg)
                self._connection_status = ConnectionStatus(connected=False, error=error_msg)
                raise NetBoxError(error_msg, {"status_code": e.response.status_code})
                
        except Exception as e:
            error_msg = f"Unexpected error during health check: {e}"
            logger.error(error_msg)
            self._connection_status = ConnectionStatus(connected=False, error=error_msg)
            raise NetBoxError(error_msg)
    
    # READ-ONLY OPERATIONS
    
    def get_device(self, name: str, site: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get device by name and optionally site.
        
        Args:
            name: Device name
            site: Site name (optional for additional filtering)
            
        Returns:
            Device data dictionary or None if not found
        """
        try:
            logger.debug(f"Getting device: {name}" + (f" at site {site}" if site else ""))
            
            # Build filter parameters
            filters = {'name': name}
            if site:
                filters['site'] = site
            
            devices = list(self.api.dcim.devices.filter(**filters))
            
            if not devices:
                logger.debug(f"Device not found: {name}")
                return None
            
            if len(devices) > 1:
                logger.warning(f"Multiple devices found with name {name}, returning first")
            
            device = devices[0]
            
            # Convert to dictionary with comprehensive data
            device_data = {
                'id': device.id,
                'name': device.name,
                'device_type': {
                    'id': device.device_type.id,
                    'name': device.device_type.display,
                    'manufacturer': device.device_type.manufacturer.name if device.device_type.manufacturer else None,
                    'model': device.device_type.model,
                    'slug': device.device_type.slug
                },
                'site': {
                    'id': device.site.id,
                    'name': device.site.name,
                    'slug': device.site.slug
                } if device.site else None,
                'role': {
                    'id': device.role.id,
                    'name': device.role.name,
                    'slug': device.role.slug
                } if device.role else None,
                'status': {
                    'value': device.status.value if device.status else None,
                    'label': device.status.label if device.status else None
                },
                'serial': device.serial,
                'asset_tag': device.asset_tag,
                'primary_ip4': str(device.primary_ip4) if device.primary_ip4 else None,
                'primary_ip6': str(device.primary_ip6) if device.primary_ip6 else None,
                'location': {
                    'id': device.location.id,
                    'name': device.location.name
                } if device.location else None,
                'rack': {
                    'id': device.rack.id,
                    'name': device.rack.name
                } if device.rack else None,
                'position': device.position,
                'description': device.description,
                'comments': device.comments,
                'tags': [tag.name for tag in device.tags] if device.tags else [],
                'custom_fields': device.custom_fields,
                'created': str(device.created) if device.created else None,
                'last_updated': str(device.last_updated) if device.last_updated else None,
                'url': str(device.url) if hasattr(device, 'url') else None
            }
            
            logger.debug(f"Device found: {device.name} (ID: {device.id})")
            return device_data
            
        except Exception as e:
            error_msg = f"Failed to get device {name}: {e}"
            logger.error(error_msg)
            raise NetBoxError(error_msg, {"device_name": name, "site": site})
    
    def list_devices(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List devices with optional filtering.
        
        Args:
            filters: Optional filter parameters (site, role, status, etc.)
            limit: Optional limit on number of results
            
        Returns:
            List of device data dictionaries
        """
        try:
            # Apply default limit from config if not specified
            if limit is None:
                limit = self.config.max_results
            
            logger.debug(f"Listing devices with filters: {filters}, limit: {limit}")
            
            # Get devices with filters
            if filters:
                devices = list(self.api.dcim.devices.filter(**filters))
            else:
                devices = list(self.api.dcim.devices.all())
            
            # Apply limit
            if limit and len(devices) > limit:
                logger.info(f"Limiting results to {limit} devices (found {len(devices)} total)")
                devices = devices[:limit]
            
            # Convert to dictionaries with basic data
            device_list = []
            for device in devices:
                device_data = {
                    'id': device.id,
                    'name': device.name,
                    'device_type': device.device_type.display if device.device_type else None,
                    'site': device.site.name if device.site else None,
                    'role': device.role.name if device.role else None,
                    'status': device.status.label if device.status else None,
                    'primary_ip4': str(device.primary_ip4) if device.primary_ip4 else None,
                    'description': device.description,
                    'last_updated': str(device.last_updated) if device.last_updated else None
                }
                device_list.append(device_data)
            
            logger.info(f"Listed {len(device_list)} devices")
            return device_list
            
        except Exception as e:
            error_msg = f"Failed to list devices: {e}"
            logger.error(error_msg)
            raise NetBoxError(error_msg, {"filters": filters, "limit": limit})
    
    def get_site_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get site by name.
        
        Args:
            name: Site name
            
        Returns:
            Site data dictionary or None if not found
        """
        try:
            logger.debug(f"Getting site: {name}")
            
            sites = list(self.api.dcim.sites.filter(name=name))
            
            if not sites:
                logger.debug(f"Site not found: {name}")
                return None
            
            if len(sites) > 1:
                logger.warning(f"Multiple sites found with name {name}, returning first")
            
            site = sites[0]
            
            site_data = {
                'id': site.id,
                'name': site.name,
                'slug': site.slug,
                'status': {
                    'value': site.status.value if site.status else None,
                    'label': site.status.label if site.status else None
                },
                'region': {
                    'id': site.region.id,
                    'name': site.region.name
                } if site.region else None,
                'group': {
                    'id': site.group.id,
                    'name': site.group.name
                } if site.group else None,
                'tenant': {
                    'id': site.tenant.id,
                    'name': site.tenant.name
                } if site.tenant else None,
                'facility': site.facility,
                'time_zone': str(site.time_zone) if site.time_zone else None,
                'description': site.description,
                'physical_address': site.physical_address,
                'shipping_address': site.shipping_address,
                'latitude': float(site.latitude) if site.latitude else None,
                'longitude': float(site.longitude) if site.longitude else None,
                'comments': site.comments,
                'tags': [tag.name for tag in site.tags] if site.tags else [],
                'custom_fields': site.custom_fields,
                'created': str(site.created) if site.created else None,
                'last_updated': str(site.last_updated) if site.last_updated else None,
                'device_count': getattr(site, 'device_count', None),
                'rack_count': getattr(site, 'rack_count', None),
                'url': str(site.url) if hasattr(site, 'url') else None
            }
            
            logger.debug(f"Site found: {site.name} (ID: {site.id})")
            return site_data
            
        except Exception as e:
            error_msg = f"Failed to get site {name}: {e}"
            logger.error(error_msg)
            raise NetBoxError(error_msg, {"site_name": name})
    
    def get_ip_address(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get IP address object by address.
        
        Args:
            address: IP address (e.g., "192.168.1.1" or "192.168.1.1/24")
            
        Returns:
            IP address data dictionary or None if not found
        """
        try:
            logger.debug(f"Getting IP address: {address}")
            
            ip_addresses = list(self.api.ipam.ip_addresses.filter(address=address))
            
            if not ip_addresses:
                logger.debug(f"IP address not found: {address}")
                return None
            
            if len(ip_addresses) > 1:
                logger.warning(f"Multiple IP addresses found for {address}, returning first")
            
            ip = ip_addresses[0]
            
            ip_data = {
                'id': ip.id,
                'address': str(ip.address),
                'status': {
                    'value': ip.status.value if ip.status else None,
                    'label': ip.status.label if ip.status else None
                },
                'role': {
                    'value': ip.role.value if ip.role else None,
                    'label': ip.role.label if ip.role else None
                } if ip.role else None,
                'tenant': {
                    'id': ip.tenant.id,
                    'name': ip.tenant.name
                } if ip.tenant else None,
                'vrf': {
                    'id': ip.vrf.id,
                    'name': ip.vrf.name
                } if ip.vrf else None,
                'assigned_object': {
                    'id': ip.assigned_object.id,
                    'name': getattr(ip.assigned_object, 'name', str(ip.assigned_object)),
                    'type': ip.assigned_object_type
                } if ip.assigned_object else None,
                'dns_name': ip.dns_name,
                'description': ip.description,
                'comments': ip.comments,
                'tags': [tag.name for tag in ip.tags] if ip.tags else [],
                'custom_fields': ip.custom_fields,
                'created': str(ip.created) if ip.created else None,
                'last_updated': str(ip.last_updated) if ip.last_updated else None,
                'url': str(ip.url) if hasattr(ip, 'url') else None
            }
            
            logger.debug(f"IP address found: {ip.address} (ID: {ip.id})")
            return ip_data
            
        except Exception as e:
            error_msg = f"Failed to get IP address {address}: {e}"
            logger.error(error_msg)
            raise NetBoxError(error_msg, {"ip_address": address})
    
    def get_vlan_by_name(self, name: str, site: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get VLAN by name and optionally site.
        
        Args:
            name: VLAN name
            site: Site name (optional for additional filtering)
            
        Returns:
            VLAN data dictionary or None if not found
        """
        try:
            logger.debug(f"Getting VLAN: {name}" + (f" at site {site}" if site else ""))
            
            # Build filter parameters
            filters = {'name': name}
            if site:
                filters['site'] = site
            
            vlans = list(self.api.ipam.vlans.filter(**filters))
            
            if not vlans:
                logger.debug(f"VLAN not found: {name}")
                return None
            
            if len(vlans) > 1:
                logger.warning(f"Multiple VLANs found with name {name}, returning first")
            
            vlan = vlans[0]
            
            vlan_data = {
                'id': vlan.id,
                'name': vlan.name,
                'vid': vlan.vid,
                'site': {
                    'id': vlan.site.id,
                    'name': vlan.site.name
                } if vlan.site else None,
                'group': {
                    'id': vlan.group.id,
                    'name': vlan.group.name
                } if vlan.group else None,
                'tenant': {
                    'id': vlan.tenant.id,
                    'name': vlan.tenant.name
                } if vlan.tenant else None,
                'status': {
                    'value': vlan.status.value if vlan.status else None,
                    'label': vlan.status.label if vlan.status else None
                },
                'role': {
                    'id': vlan.role.id,
                    'name': vlan.role.name
                } if vlan.role else None,
                'description': vlan.description,
                'comments': vlan.comments,
                'tags': [tag.name for tag in vlan.tags] if vlan.tags else [],
                'custom_fields': vlan.custom_fields,
                'created': str(vlan.created) if vlan.created else None,
                'last_updated': str(vlan.last_updated) if vlan.last_updated else None,
                'url': str(vlan.url) if hasattr(vlan, 'url') else None
            }
            
            logger.debug(f"VLAN found: {vlan.name} (ID: {vlan.id}, VID: {vlan.vid})")
            return vlan_data
            
        except Exception as e:
            error_msg = f"Failed to get VLAN {name}: {e}"
            logger.error(error_msg)
            raise NetBoxError(error_msg, {"vlan_name": name, "site": site})
    
    def get_device_interfaces(self, device_name: str) -> List[Dict[str, Any]]:
        """
        Get all interfaces for a device.
        
        Args:
            device_name: Device name
            
        Returns:
            List of interface data dictionaries
        """
        try:
            logger.debug(f"Getting interfaces for device: {device_name}")
            
            # First get the device to validate it exists
            device_data = self.get_device(device_name)
            if not device_data:
                raise NetBoxNotFoundError(f"Device not found: {device_name}")
            
            device_id = device_data['id']
            
            # Get interfaces for this device
            interfaces = list(self.api.dcim.interfaces.filter(device_id=device_id))
            
            interface_list = []
            for interface in interfaces:
                interface_data = {
                    'id': interface.id,
                    'name': interface.name,
                    'type': {
                        'value': interface.type.value if interface.type else None,
                        'label': interface.type.label if interface.type else None
                    },
                    'enabled': interface.enabled,
                    'device': {
                        'id': interface.device.id,
                        'name': interface.device.name
                    } if interface.device else None,
                    'lag': {
                        'id': interface.lag.id,
                        'name': interface.lag.name
                    } if interface.lag else None,
                    'mtu': interface.mtu,
                    'mac_address': str(interface.mac_address) if interface.mac_address else None,
                    'speed': interface.speed,
                    'duplex': {
                        'value': interface.duplex.value if interface.duplex else None,
                        'label': interface.duplex.label if interface.duplex else None
                    } if interface.duplex else None,
                    'wwn': interface.wwn,
                    'mgmt_only': interface.mgmt_only,
                    'description': interface.description,
                    'mode': {
                        'value': interface.mode.value if interface.mode else None,
                        'label': interface.mode.label if interface.mode else None
                    } if interface.mode else None,
                    'tagged_vlans': [vlan.name for vlan in interface.tagged_vlans] if interface.tagged_vlans else [],
                    'untagged_vlan': {
                        'id': interface.untagged_vlan.id,
                        'name': interface.untagged_vlan.name,
                        'vid': interface.untagged_vlan.vid
                    } if interface.untagged_vlan else None,
                    'ip_addresses': [],  # Will be populated separately if needed
                    'connected_endpoints': [],  # Will be populated separately if needed
                    'tags': [tag.name for tag in interface.tags] if interface.tags else [],
                    'custom_fields': interface.custom_fields,
                    'created': str(interface.created) if interface.created else None,
                    'last_updated': str(interface.last_updated) if interface.last_updated else None,
                    'url': str(interface.url) if hasattr(interface, 'url') else None
                }
                interface_list.append(interface_data)
            
            logger.info(f"Found {len(interface_list)} interfaces for device {device_name}")
            return interface_list
            
        except NetBoxNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to get interfaces for device {device_name}: {e}"
            logger.error(error_msg)
            raise NetBoxError(error_msg, {"device_name": device_name})
    
    def get_manufacturers(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all manufacturers.
        
        Args:
            limit: Optional limit on number of results
            
        Returns:
            List of manufacturer data dictionaries
        """
        try:
            if limit is None:
                limit = self.config.max_results
                
            logger.debug(f"Getting manufacturers (limit: {limit})")
            
            manufacturers = list(self.api.dcim.manufacturers.all())
            
            # Apply limit
            if limit and len(manufacturers) > limit:
                logger.info(f"Limiting results to {limit} manufacturers (found {len(manufacturers)} total)")
                manufacturers = manufacturers[:limit]
            
            manufacturer_list = []
            for mfg in manufacturers:
                mfg_data = {
                    'id': mfg.id,
                    'name': mfg.name,
                    'slug': mfg.slug,
                    'description': mfg.description,
                    'tags': [tag.name for tag in mfg.tags] if mfg.tags else [],
                    'custom_fields': mfg.custom_fields,
                    'devicetype_count': getattr(mfg, 'devicetype_count', None),
                    'created': str(mfg.created) if mfg.created else None,
                    'last_updated': str(mfg.last_updated) if mfg.last_updated else None,
                    'url': str(mfg.url) if hasattr(mfg, 'url') else None
                }
                manufacturer_list.append(mfg_data)
            
            logger.info(f"Retrieved {len(manufacturer_list)} manufacturers")
            return manufacturer_list
            
        except Exception as e:
            error_msg = f"Failed to get manufacturers: {e}"
            logger.error(error_msg)
            raise NetBoxError(error_msg, {"limit": limit})
    
    # =====================================================================
    # WRITE OPERATIONS - SAFETY CRITICAL SECTION
    # =====================================================================
    
    def _check_write_safety(self, operation: str, confirm: bool = False) -> None:
        """
        Verify write operation safety requirements.
        
        Args:
            operation: Name of the write operation
            confirm: Confirmation parameter from caller
            
        Raises:
            NetBoxConfirmationError: If confirm=False
            NetBoxDryRunError: If in dry-run mode (for logging)
        """
        if not confirm:
            error_msg = f"Write operation '{operation}' requires confirm=True for safety"
            logger.error(f"🚨 SAFETY VIOLATION: {error_msg}")
            raise NetBoxConfirmationError(error_msg)
        
        if self.config.safety.dry_run_mode:
            logger.warning(f"🔍 DRY-RUN MODE: Would execute {operation} (no actual changes)")
            # Don't raise error, just log - we'll simulate the operation
    
    def _log_write_operation(self, operation: str, object_type: str, data: Dict[str, Any], 
                           result: Any = None, error: Exception = None) -> None:
        """
        Log write operations for audit trail.
        
        Args:
            operation: Type of operation (create, update, delete)
            object_type: NetBox object type being modified
            data: Data being written or object being modified
            result: Result of the operation (if successful)
            error: Exception if operation failed
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        
        if error:
            logger.error(f"📝 WRITE FAILED [{timestamp}] {operation.upper()} {object_type}: {error}")
            logger.error(f"📝 Data: {data}")
        else:
            logger.info(f"📝 WRITE SUCCESS [{timestamp}] {operation.upper()} {object_type}")
            logger.info(f"📝 Data: {data}")
            if result and hasattr(result, 'id'):
                logger.info(f"📝 Result ID: {result.id}")
    
    def create_object(self, object_type: str, data: Dict[str, Any], confirm: bool = False) -> Dict[str, Any]:
        """
        Create a new object in NetBox with safety mechanisms.
        
        Args:
            object_type: Type of object to create (e.g., 'devices', 'sites', 'manufacturers')
            data: Object data dictionary
            confirm: Safety confirmation (REQUIRED: must be True)
            
        Returns:
            Created object data dictionary
            
        Raises:
            NetBoxConfirmationError: If confirm=False
            NetBoxValidationError: If data validation fails
            NetBoxWriteError: If creation fails
            
        Example:
            device_data = {
                'name': 'switch-01',
                'device_type': 1,
                'site': 1,
                'status': 'active'
            }
            result = client.create_object('devices', device_data, confirm=True)
        """
        operation = f"create_{object_type}"
        
        try:
            # Safety checks
            self._check_write_safety(operation, confirm)
            
            # Validate data
            if not isinstance(data, dict) or len(data) == 0:
                raise NetBoxValidationError("Object data must be a non-empty dictionary")
            
            # Validate endpoint (must be done before dry-run to catch invalid types)
            endpoint = self._get_write_endpoint(object_type)
            
            # Dry-run mode simulation
            if self.config.safety.dry_run_mode:
                logger.info(f"🔍 DRY-RUN: Would create {object_type} with data: {data}")
                simulated_result = {
                    'id': 999999,  # Fake ID for dry-run
                    'dry_run': True,
                    **data
                }
                self._log_write_operation(operation, object_type, data, simulated_result)
                return simulated_result
            
            # Create the object
            logger.info(f"Creating {object_type} object with data: {data}")
            result = endpoint.create(data)
            
            # Convert to dict for consistent return type
            result_dict = self._object_to_dict(result)
            
            # Log successful operation
            self._log_write_operation(operation, object_type, data, result)
            
            logger.info(f"✅ Successfully created {object_type} with ID: {result.id}")
            return result_dict
            
        except (NetBoxConfirmationError, NetBoxValidationError):
            raise
        except Exception as e:
            self._log_write_operation(operation, object_type, data, error=e)
            if "validation" in str(e).lower():
                raise NetBoxValidationError(f"Validation failed for {object_type}: {e}")
            else:
                raise NetBoxWriteError(f"Failed to create {object_type}: {e}")
    
    def update_object(self, object_type: str, object_id: int, data: Dict[str, Any], confirm: bool = False) -> Dict[str, Any]:
        """
        Update an existing object in NetBox with safety mechanisms.
        
        Args:
            object_type: Type of object to update
            object_id: ID of object to update
            data: Updated data dictionary
            confirm: Safety confirmation (REQUIRED: must be True)
            
        Returns:
            Updated object data dictionary
            
        Raises:
            NetBoxConfirmationError: If confirm=False
            NetBoxNotFoundError: If object not found
            NetBoxValidationError: If data validation fails
            NetBoxWriteError: If update fails
        """
        operation = f"update_{object_type}"
        
        try:
            # Safety checks
            self._check_write_safety(operation, confirm)
            
            # Validate data
            if not isinstance(data, dict) or len(data) == 0:
                raise NetBoxValidationError("Update data must be a non-empty dictionary")
            
            # Validate endpoint (must be done before dry-run to catch invalid types)
            endpoint = self._get_write_endpoint(object_type)
            
            # Get the object first to verify it exists
            try:
                existing_obj = endpoint.get(object_id)
                if not existing_obj:
                    raise NetBoxNotFoundError(f"{object_type} with ID {object_id} not found")
            except Exception as e:
                raise NetBoxNotFoundError(f"{object_type} with ID {object_id} not found: {e}")
            
            # Store original data for logging
            original_data = self._object_to_dict(existing_obj)
            
            # Dry-run mode simulation
            if self.config.safety.dry_run_mode:
                logger.info(f"🔍 DRY-RUN: Would update {object_type} ID {object_id} with data: {data}")
                simulated_result = {
                    **original_data,
                    **data,
                    'dry_run': True
                }
                self._log_write_operation(operation, object_type, data, simulated_result)
                return simulated_result
            
            # Update the object
            logger.info(f"Updating {object_type} ID {object_id} with data: {data}")
            
            # Update fields on the object
            for key, value in data.items():
                setattr(existing_obj, key, value)
            
            # Save the changes
            result = existing_obj.save()
            
            # Convert to dict for consistent return type
            result_dict = self._object_to_dict(existing_obj)
            
            # Log successful operation  
            self._log_write_operation(operation, object_type, data, existing_obj)
            
            logger.info(f"✅ Successfully updated {object_type} ID {object_id}")
            return result_dict
            
        except (NetBoxConfirmationError, NetBoxNotFoundError, NetBoxValidationError):
            raise
        except Exception as e:
            self._log_write_operation(operation, object_type, data, error=e)
            if "validation" in str(e).lower():
                raise NetBoxValidationError(f"Validation failed for {object_type}: {e}")
            else:
                raise NetBoxWriteError(f"Failed to update {object_type}: {e}")
    
    def delete_object(self, object_type: str, object_id: int, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete an object from NetBox with safety mechanisms.
        
        Args:
            object_type: Type of object to delete
            object_id: ID of object to delete
            confirm: Safety confirmation (REQUIRED: must be True)
            
        Returns:
            Deletion confirmation dictionary
            
        Raises:
            NetBoxConfirmationError: If confirm=False
            NetBoxNotFoundError: If object not found
            NetBoxWriteError: If deletion fails
        """
        operation = f"delete_{object_type}"
        
        try:
            # Safety checks
            self._check_write_safety(operation, confirm)
            
            # Validate endpoint (must be done before dry-run to catch invalid types)
            endpoint = self._get_write_endpoint(object_type)
            
            # Get the object first to verify it exists and get its data
            try:
                existing_obj = endpoint.get(object_id)
                if not existing_obj:
                    raise NetBoxNotFoundError(f"{object_type} with ID {object_id} not found")
            except Exception as e:
                raise NetBoxNotFoundError(f"{object_type} with ID {object_id} not found: {e}")
            
            # Store object data for logging
            object_data = self._object_to_dict(existing_obj)
            
            # Dry-run mode simulation
            if self.config.safety.dry_run_mode:
                logger.info(f"🔍 DRY-RUN: Would delete {object_type} ID {object_id}")
                simulated_result = {
                    'deleted': True,
                    'dry_run': True,
                    'object_id': object_id,
                    'object_type': object_type,
                    'original_data': object_data
                }
                self._log_write_operation(operation, object_type, object_data, simulated_result)
                return simulated_result
            
            # Delete the object
            logger.info(f"Deleting {object_type} ID {object_id}")
            existing_obj.delete()
            
            result = {
                'deleted': True,
                'object_id': object_id,
                'object_type': object_type,
                'original_data': object_data
            }
            
            # Log successful operation
            self._log_write_operation(operation, object_type, object_data, result)
            
            logger.info(f"✅ Successfully deleted {object_type} ID {object_id}")
            return result
            
        except (NetBoxConfirmationError, NetBoxNotFoundError):
            raise
        except Exception as e:
            self._log_write_operation(operation, object_type, {'object_id': object_id}, error=e)
            raise NetBoxWriteError(f"Failed to delete {object_type}: {e}")
    
    def _get_write_endpoint(self, object_type: str):
        """
        Get the appropriate pynetbox endpoint for write operations.
        
        Args:
            object_type: Type of object (e.g., 'devices', 'sites', 'manufacturers')
            
        Returns:
            pynetbox endpoint object
            
        Raises:
            NetBoxValidationError: If object_type is not supported
        """
        endpoint_mapping = {
            # DCIM endpoints
            'devices': self.api.dcim.devices,
            'sites': self.api.dcim.sites,
            'manufacturers': self.api.dcim.manufacturers,
            'device_types': self.api.dcim.device_types,
            'device_roles': self.api.dcim.device_roles,
            'interfaces': self.api.dcim.interfaces,
            'cables': self.api.dcim.cables,
            'racks': self.api.dcim.racks,
            'locations': self.api.dcim.locations,
            
            # IPAM endpoints
            'ip_addresses': self.api.ipam.ip_addresses,
            'prefixes': self.api.ipam.prefixes,
            'vlans': self.api.ipam.vlans,
            'vlan_groups': self.api.ipam.vlan_groups,
            'vrfs': self.api.ipam.vrfs,
            
            # Extras endpoints
            'tags': self.api.extras.tags,
            'custom_fields': self.api.extras.custom_fields,
        }
        
        if object_type not in endpoint_mapping:
            supported_types = ', '.join(sorted(endpoint_mapping.keys()))
            raise NetBoxValidationError(
                f"Unsupported object type '{object_type}'. "
                f"Supported types: {supported_types}"
            )
        
        return endpoint_mapping[object_type]
    
    def _object_to_dict(self, obj) -> Dict[str, Any]:
        """
        Convert a pynetbox object to a dictionary for consistent return types.
        
        Args:
            obj: pynetbox object
            
        Returns:
            Dictionary representation of the object
        """
        if hasattr(obj, 'serialize'):
            return obj.serialize()
        elif hasattr(obj, '__dict__'):
            # Fallback for objects without serialize method
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    try:
                        # Convert to JSON-serializable types
                        if hasattr(value, 'id'):
                            result[key] = value.id
                        elif hasattr(value, '__dict__'):
                            result[key] = str(value)
                        else:
                            result[key] = value
                    except Exception:
                        result[key] = str(value)
            return result
        else:
            return {'object': str(obj)}


    # === SELECTIVE FIELD COMPARISON AND HASH DIFFING ===
    # Advanced state comparison for efficient ensure operations
    
    # Managed fields configuration - only these fields are compared and updated
    MANAGED_FIELDS = {
        "manufacturers": ["name", "slug", "description"],
        "sites": ["name", "slug", "status", "description", "physical_address", "region"],
        "device_roles": ["name", "slug", "color", "vm_role", "description"]
    }
    
    # Custom fields for metadata tracking
    METADATA_CUSTOM_FIELDS = {
        "managed_hash": "unimus_managed_hash",
        "last_sync": "last_unimus_sync", 
        "source": "management_source"
    }
    
    def _generate_managed_hash(self, data: Dict[str, Any], object_type: str) -> str:
        """
        Generate SHA256 hash from managed field values for efficient comparison.
        
        Args:
            data: Object data dictionary
            object_type: Type of object (manufacturers, sites, device_roles)
            
        Returns:
            SHA256 hash string of managed field values
        """
        import hashlib
        import json
        
        if object_type not in self.MANAGED_FIELDS:
            raise NetBoxValidationError(f"Unknown object type for managed fields: {object_type}")
        
        managed_fields = self.MANAGED_FIELDS[object_type]
        managed_data = {}
        
        # Extract only managed fields, handling None values consistently
        for field in managed_fields:
            value = data.get(field)
            if value is not None:
                managed_data[field] = value
        
        # Sort keys for consistent hashing
        sorted_data = json.dumps(managed_data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode('utf-8')).hexdigest()
    
    def _compare_managed_fields(self, existing_obj: Dict[str, Any], desired_state: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """
        Compare existing object with desired state using selective field comparison.
        
        Args:
            existing_obj: Current object from NetBox
            desired_state: Desired object state
            object_type: Type of object for field selection
            
        Returns:
            Dict with comparison results: needs_update, updated_fields, unchanged_fields
        """
        if object_type not in self.MANAGED_FIELDS:
            raise NetBoxValidationError(f"Unknown object type for managed fields: {object_type}")
        
        managed_fields = self.MANAGED_FIELDS[object_type]
        changes = {
            "updated_fields": [],
            "unchanged_fields": [],
            "needs_update": False
        }
        
        for field in managed_fields:
            current_value = existing_obj.get(field)
            desired_value = desired_state.get(field)
            
            # Handle None values and string comparisons consistently
            if current_value != desired_value:
                changes["updated_fields"].append({
                    "field": field,
                    "current": current_value,
                    "desired": desired_value
                })
                changes["needs_update"] = True
            else:
                changes["unchanged_fields"].append(field)
        
        return changes
    
    def _hash_comparison_check(self, existing_obj: Dict[str, Any], desired_state: Dict[str, Any], object_type: str) -> bool:
        """
        Quick hash comparison to determine if update is needed without detailed field comparison.
        
        Args:
            existing_obj: Current object from NetBox (with custom_fields)
            desired_state: Desired object state
            object_type: Type of object for hash generation
            
        Returns:
            True if hashes match (no update needed), False if update required
        """
        # Get existing hash from custom fields
        existing_custom_fields = existing_obj.get("custom_fields", {})
        existing_hash = existing_custom_fields.get(self.METADATA_CUSTOM_FIELDS["managed_hash"])
        
        # Generate hash for desired state
        desired_hash = self._generate_managed_hash(desired_state, object_type)
        
        # If no existing hash, assume update needed
        if not existing_hash:
            logger.debug(f"No existing hash found for {object_type}, update required")
            return False
        
        # Compare hashes
        hash_match = existing_hash == desired_hash
        logger.debug(f"Hash comparison for {object_type}: existing={existing_hash[:8]}..., desired={desired_hash[:8]}..., match={hash_match}")
        
        return hash_match
    
    def _prepare_metadata_update(self, desired_state: Dict[str, Any], object_type: str, operation: str = "update") -> Dict[str, Any]:
        """
        Prepare custom fields metadata for state tracking.
        
        Args:
            desired_state: Desired object state
            object_type: Type of object for hash generation
            operation: Operation type (create, update)
            
        Returns:
            Dict with custom_fields added for metadata tracking
        """
        from datetime import datetime
        
        # Generate new hash for desired state
        new_hash = self._generate_managed_hash(desired_state, object_type)
        
        # Prepare metadata
        metadata = {
            self.METADATA_CUSTOM_FIELDS["managed_hash"]: new_hash,
            self.METADATA_CUSTOM_FIELDS["last_sync"]: datetime.utcnow().isoformat(),
            self.METADATA_CUSTOM_FIELDS["source"]: "unimus"
        }
        
        # Add metadata to desired state
        updated_state = desired_state.copy()
        updated_state["custom_fields"] = {
            **desired_state.get("custom_fields", {}),
            **metadata
        }
        
        logger.debug(f"Prepared metadata for {object_type} {operation}: hash={new_hash[:8]}...")
        
        return updated_state

    # === HYBRID ENSURE METHODS ===
    # Gemini-recommended architecture combining hierarchical convenience with direct ID injection
    
    def ensure_manufacturer(
        self,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        manufacturer_id: Optional[int] = None,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Ensure a manufacturer exists with idempotent behavior using hybrid pattern.
        
        Supports both hierarchical convenience and direct ID injection for performance:
        - Hierarchical: ensure_manufacturer(name="Cisco Systems", confirm=True)
        - Direct ID: ensure_manufacturer(manufacturer_id=5, confirm=True)
        
        Args:
            name: Manufacturer name (required if manufacturer_id not provided)
            slug: URL slug (auto-generated from name if not provided)
            description: Optional description
            manufacturer_id: Direct manufacturer ID (skips lookup if provided)
            confirm: Safety confirmation (REQUIRED: must be True)
            
        Returns:
            Dict containing manufacturer data and operation details
            
        Raises:
            NetBoxValidationError: Invalid input parameters
            NetBoxConfirmationError: Missing confirm=True
            NetBoxNotFoundError: manufacturer_id provided but doesn't exist
            NetBoxWriteError: API operation failed
        """
        operation = "ENSURE_MANUFACTURER"
        
        try:
            # Safety check - ensure confirmation
            self._check_write_safety(operation, confirm)
            
            # Input validation - either name or manufacturer_id must be provided
            if not name and not manufacturer_id:
                raise NetBoxValidationError("Either 'name' or 'manufacturer_id' parameter is required")
            
            if manufacturer_id and name:
                logger.warning(f"Both manufacturer_id ({manufacturer_id}) and name ('{name}') provided. Using manufacturer_id.")
            
            # Pattern B: Direct ID injection (performance path)
            if manufacturer_id:
                try:
                    existing_obj = self.api.dcim.manufacturers.get(manufacturer_id)
                    if not existing_obj:
                        raise NetBoxNotFoundError(f"Manufacturer with ID {manufacturer_id} not found")
                    
                    result_dict = self._object_to_dict(existing_obj)
                    return {
                        "success": True,
                        "action": "unchanged",
                        "object_type": "manufacturer", 
                        "manufacturer": result_dict,
                        "changes": {
                            "created_fields": [],
                            "updated_fields": [],
                            "unchanged_fields": list(result_dict.keys())
                        },
                        "dry_run": False
                    }
                except Exception as e:
                    if "not found" in str(e).lower():
                        raise NetBoxNotFoundError(f"Manufacturer with ID {manufacturer_id} not found")
                    else:
                        raise NetBoxWriteError(f"Failed to retrieve manufacturer {manufacturer_id}: {e}")
            
            # Pattern A: Hierarchical lookup and create (convenience path)
            if not name or not name.strip():
                raise NetBoxValidationError("Manufacturer name cannot be empty")
            
            name = name.strip()
            
            # Check if manufacturer already exists by name
            try:
                existing_manufacturers = list(self.api.dcim.manufacturers.filter(name=name))
                
                if existing_manufacturers:
                    existing_obj = existing_manufacturers[0]
                    existing_dict = self._object_to_dict(existing_obj)
                    
                    # Build desired state for comparison
                    desired_state = {"name": name}
                    if slug:
                        desired_state["slug"] = slug
                    if description:
                        desired_state["description"] = description
                    
                    # Issue #12: Enhanced selective field comparison with hash diffing
                    # First try quick hash comparison
                    if self._hash_comparison_check(existing_dict, desired_state, "manufacturers"):
                        # Hash matches - no update needed, return unchanged
                        logger.debug(f"Hash match for manufacturer '{name}' - no update needed")
                        return {
                            "success": True,
                            "action": "unchanged",
                            "object_type": "manufacturer",
                            "manufacturer": existing_dict,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [],
                                "unchanged_fields": list(self.MANAGED_FIELDS["manufacturers"])
                            },
                            "dry_run": False
                        }
                    
                    # Hash differs - perform detailed selective field comparison
                    comparison = self._compare_managed_fields(existing_dict, desired_state, "manufacturers")
                    
                    if comparison["needs_update"]:
                        # Prepare update with metadata tracking
                        update_data = self._prepare_metadata_update(desired_state, "manufacturers", "update")
                        
                        logger.info(f"Updating manufacturer '{name}' - managed fields changed: {[f['field'] for f in comparison['updated_fields']]}")
                        result = self.update_object("manufacturers", existing_obj.id, update_data, confirm=True)
                        
                        return {
                            "success": True,
                            "action": "updated",
                            "object_type": "manufacturer",
                            "manufacturer": result,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [f["field"] for f in comparison["updated_fields"]],
                                "unchanged_fields": comparison["unchanged_fields"]
                            },
                            "dry_run": result.get("dry_run", False)
                        }
                    else:
                        # No changes needed - hash mismatch but field comparison shows no changes
                        logger.info(f"Manufacturer '{name}' already exists with desired state")
                        return {
                            "success": True,
                            "action": "unchanged",
                            "object_type": "manufacturer",
                            "manufacturer": existing_dict,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [],
                                "unchanged_fields": comparison["unchanged_fields"]
                            },
                            "dry_run": False
                        }
                
                else:
                    # Create new manufacturer with metadata tracking
                    logger.info(f"Creating new manufacturer '{name}'")
                    create_data = {"name": name}
                    if slug:
                        create_data["slug"] = slug
                    if description:
                        create_data["description"] = description
                    
                    # Add metadata for new objects
                    create_data = self._prepare_metadata_update(create_data, "manufacturers", "create")
                    
                    result = self.create_object("manufacturers", create_data, confirm=True)
                    
                    return {
                        "success": True,
                        "action": "created",
                        "object_type": "manufacturer",
                        "manufacturer": result,
                        "changes": {
                            "created_fields": list(create_data.keys()),
                            "updated_fields": [],
                            "unchanged_fields": []
                        },
                        "dry_run": result.get("dry_run", False)
                    }
                    
            except (NetBoxConfirmationError, NetBoxValidationError, NetBoxNotFoundError):
                raise
            except Exception as e:
                raise NetBoxWriteError(f"Failed to ensure manufacturer '{name}': {e}")
                
        except (NetBoxConfirmationError, NetBoxValidationError, NetBoxNotFoundError, NetBoxWriteError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ensure_manufacturer: {e}")
            raise NetBoxError(f"Unexpected error ensuring manufacturer: {e}")


    def ensure_site(
        self,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        status: str = "active",
        region: Optional[str] = None,
        description: Optional[str] = None,
        physical_address: Optional[str] = None,
        site_id: Optional[int] = None,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Ensure a site exists with idempotent behavior using hybrid pattern.
        
        Supports both hierarchical convenience and direct ID injection for performance:
        - Hierarchical: ensure_site(name="Datacenter Amsterdam", confirm=True)
        - Direct ID: ensure_site(site_id=10, confirm=True)
        
        Args:
            name: Site name (required if site_id not provided)
            slug: URL slug (auto-generated from name if not provided)
            status: Site status (default: "active")
            region: Optional region name
            description: Optional description
            physical_address: Optional physical address
            site_id: Direct site ID (skips lookup if provided)
            confirm: Safety confirmation (REQUIRED: must be True)
            
        Returns:
            Dict containing site data and operation details
        """
        operation = "ENSURE_SITE"
        
        try:
            # Safety check - ensure confirmation
            self._check_write_safety(operation, confirm)
            
            # Input validation
            if not name and not site_id:
                raise NetBoxValidationError("Either 'name' or 'site_id' parameter is required")
            
            if site_id and name:
                logger.warning(f"Both site_id ({site_id}) and name ('{name}') provided. Using site_id.")
            
            # Pattern B: Direct ID injection (performance path)
            if site_id:
                try:
                    existing_obj = self.api.dcim.sites.get(site_id)
                    if not existing_obj:
                        raise NetBoxNotFoundError(f"Site with ID {site_id} not found")
                    
                    result_dict = self._object_to_dict(existing_obj)
                    return {
                        "success": True,
                        "action": "unchanged",
                        "object_type": "site",
                        "site": result_dict,
                        "changes": {
                            "created_fields": [],
                            "updated_fields": [],
                            "unchanged_fields": list(result_dict.keys())
                        },
                        "dry_run": False
                    }
                except Exception as e:
                    if "not found" in str(e).lower():
                        raise NetBoxNotFoundError(f"Site with ID {site_id} not found")
                    else:
                        raise NetBoxWriteError(f"Failed to retrieve site {site_id}: {e}")
            
            # Pattern A: Hierarchical lookup and create (convenience path)
            if not name or not name.strip():
                raise NetBoxValidationError("Site name cannot be empty")
            
            name = name.strip()
            
            # Check if site already exists by name
            try:
                existing_sites = list(self.api.dcim.sites.filter(name=name))
                
                if existing_sites:
                    existing_obj = existing_sites[0]
                    existing_dict = self._object_to_dict(existing_obj)
                    
                    # Build desired state for comparison
                    desired_state = {"name": name, "status": status}
                    if slug:
                        desired_state["slug"] = slug
                    if region:
                        desired_state["region"] = region
                    if description:
                        desired_state["description"] = description
                    if physical_address:
                        desired_state["physical_address"] = physical_address
                    
                    # Issue #12: Enhanced selective field comparison with hash diffing
                    # First try quick hash comparison
                    if self._hash_comparison_check(existing_dict, desired_state, "sites"):
                        # Hash matches - no update needed, return unchanged
                        logger.debug(f"Hash match for site '{name}' - no update needed")
                        return {
                            "success": True,
                            "action": "unchanged",
                            "object_type": "site",
                            "site": existing_dict,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [],
                                "unchanged_fields": list(self.MANAGED_FIELDS["sites"])
                            },
                            "dry_run": False
                        }
                    
                    # Hash differs - perform detailed selective field comparison
                    comparison = self._compare_managed_fields(existing_dict, desired_state, "sites")
                    
                    if comparison["needs_update"]:
                        # Prepare update with metadata tracking
                        update_data = self._prepare_metadata_update(desired_state, "sites", "update")
                        
                        logger.info(f"Updating site '{name}' - managed fields changed: {[f['field'] for f in comparison['updated_fields']]}")
                        result = self.update_object("sites", existing_obj.id, update_data, confirm=True)
                        
                        return {
                            "success": True,
                            "action": "updated",
                            "object_type": "site",
                            "site": result,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [f["field"] for f in comparison["updated_fields"]],
                                "unchanged_fields": comparison["unchanged_fields"]
                            },
                            "dry_run": result.get("dry_run", False)
                        }
                    else:
                        # No changes needed - hash mismatch but field comparison shows no changes
                        logger.info(f"Site '{name}' already exists with desired state")
                        return {
                            "success": True,
                            "action": "unchanged",
                            "object_type": "site",
                            "site": existing_dict,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [],
                                "unchanged_fields": comparison["unchanged_fields"]
                            },
                            "dry_run": False
                        }
                
                else:
                    # Create new site with metadata tracking
                    logger.info(f"Creating new site '{name}'")
                    create_data = {"name": name, "status": status}
                    if slug:
                        create_data["slug"] = slug
                    if region:
                        create_data["region"] = region
                    if description:
                        create_data["description"] = description
                    if physical_address:
                        create_data["physical_address"] = physical_address
                    
                    # Add metadata for new objects
                    create_data = self._prepare_metadata_update(create_data, "sites", "create")
                    
                    result = self.create_object("sites", create_data, confirm=True)
                    
                    return {
                        "success": True,
                        "action": "created",
                        "object_type": "site",
                        "site": result,
                        "changes": {
                            "created_fields": list(create_data.keys()),
                            "updated_fields": [],
                            "unchanged_fields": []
                        },
                        "dry_run": result.get("dry_run", False)
                    }
                    
            except (NetBoxConfirmationError, NetBoxValidationError, NetBoxNotFoundError):
                raise
            except Exception as e:
                raise NetBoxWriteError(f"Failed to ensure site '{name}': {e}")
                
        except (NetBoxConfirmationError, NetBoxValidationError, NetBoxNotFoundError, NetBoxWriteError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ensure_site: {e}")
            raise NetBoxError(f"Unexpected error ensuring site: {e}")


    def ensure_device_role(
        self,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        color: str = "9e9e9e",
        vm_role: bool = False,
        description: Optional[str] = None,
        role_id: Optional[int] = None,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Ensure a device role exists with idempotent behavior using hybrid pattern.
        
        Supports both hierarchical convenience and direct ID injection for performance:
        - Hierarchical: ensure_device_role(name="Access Switch", confirm=True)
        - Direct ID: ensure_device_role(role_id=3, confirm=True)
        
        Args:
            name: Device role name (required if role_id not provided)
            slug: URL slug (auto-generated from name if not provided)
            color: Hex color code (default: gray)
            vm_role: Whether this role applies to virtual machines
            description: Optional description
            role_id: Direct device role ID (skips lookup if provided)
            confirm: Safety confirmation (REQUIRED: must be True)
            
        Returns:
            Dict containing device role data and operation details
        """
        operation = "ENSURE_DEVICE_ROLE"
        
        try:
            # Safety check - ensure confirmation
            self._check_write_safety(operation, confirm)
            
            # Input validation
            if not name and not role_id:
                raise NetBoxValidationError("Either 'name' or 'role_id' parameter is required")
            
            if role_id and name:
                logger.warning(f"Both role_id ({role_id}) and name ('{name}') provided. Using role_id.")
            
            # Pattern B: Direct ID injection (performance path)
            if role_id:
                try:
                    existing_obj = self.api.dcim.device_roles.get(role_id)
                    if not existing_obj:
                        raise NetBoxNotFoundError(f"Device role with ID {role_id} not found")
                    
                    result_dict = self._object_to_dict(existing_obj)
                    return {
                        "success": True,
                        "action": "unchanged",
                        "object_type": "device_role",
                        "device_role": result_dict,
                        "changes": {
                            "created_fields": [],
                            "updated_fields": [],
                            "unchanged_fields": list(result_dict.keys())
                        },
                        "dry_run": False
                    }
                except Exception as e:
                    if "not found" in str(e).lower():
                        raise NetBoxNotFoundError(f"Device role with ID {role_id} not found")
                    else:
                        raise NetBoxWriteError(f"Failed to retrieve device role {role_id}: {e}")
            
            # Pattern A: Hierarchical lookup and create (convenience path)
            if not name or not name.strip():
                raise NetBoxValidationError("Device role name cannot be empty")
            
            name = name.strip()
            
            # Check if device role already exists by name
            try:
                existing_roles = list(self.api.dcim.device_roles.filter(name=name))
                
                if existing_roles:
                    existing_obj = existing_roles[0]
                    existing_dict = self._object_to_dict(existing_obj)
                    
                    # Build desired state for comparison
                    desired_state = {"name": name, "color": color, "vm_role": vm_role}
                    if slug:
                        desired_state["slug"] = slug
                    if description:
                        desired_state["description"] = description
                    
                    # Issue #12: Enhanced selective field comparison with hash diffing
                    # First try quick hash comparison
                    if self._hash_comparison_check(existing_dict, desired_state, "device_roles"):
                        # Hash matches - no update needed, return unchanged
                        logger.debug(f"Hash match for device role '{name}' - no update needed")
                        return {
                            "success": True,
                            "action": "unchanged",
                            "object_type": "device_role",
                            "device_role": existing_dict,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [],
                                "unchanged_fields": list(self.MANAGED_FIELDS["device_roles"])
                            },
                            "dry_run": False
                        }
                    
                    # Hash differs - perform detailed selective field comparison
                    comparison = self._compare_managed_fields(existing_dict, desired_state, "device_roles")
                    
                    if comparison["needs_update"]:
                        # Prepare update with metadata tracking
                        update_data = self._prepare_metadata_update(desired_state, "device_roles", "update")
                        
                        logger.info(f"Updating device role '{name}' - managed fields changed: {[f['field'] for f in comparison['updated_fields']]}")
                        result = self.update_object("device_roles", existing_obj.id, update_data, confirm=True)
                        
                        return {
                            "success": True,
                            "action": "updated",
                            "object_type": "device_role",
                            "device_role": result,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [f["field"] for f in comparison["updated_fields"]],
                                "unchanged_fields": comparison["unchanged_fields"]
                            },
                            "dry_run": result.get("dry_run", False)
                        }
                    else:
                        # No changes needed - hash mismatch but field comparison shows no changes
                        logger.info(f"Device role '{name}' already exists with desired state")
                        return {
                            "success": True,
                            "action": "unchanged",
                            "object_type": "device_role",
                            "device_role": existing_dict,
                            "changes": {
                                "created_fields": [],
                                "updated_fields": [],
                                "unchanged_fields": comparison["unchanged_fields"]
                            },
                            "dry_run": False
                        }
                
                else:
                    # Create new device role with metadata tracking
                    logger.info(f"Creating new device role '{name}'")
                    create_data = {"name": name, "color": color, "vm_role": vm_role}
                    if slug:
                        create_data["slug"] = slug
                    if description:
                        create_data["description"] = description
                    
                    # Add metadata for new objects
                    create_data = self._prepare_metadata_update(create_data, "device_roles", "create")
                    
                    result = self.create_object("device_roles", create_data, confirm=True)
                    
                    return {
                        "success": True,
                        "action": "created",
                        "object_type": "device_role",
                        "device_role": result,
                        "changes": {
                            "created_fields": list(create_data.keys()),
                            "updated_fields": [],
                            "unchanged_fields": []
                        },
                        "dry_run": result.get("dry_run", False)
                    }
                    
            except (NetBoxConfirmationError, NetBoxValidationError, NetBoxNotFoundError):
                raise
            except Exception as e:
                raise NetBoxWriteError(f"Failed to ensure device role '{name}': {e}")
                
        except (NetBoxConfirmationError, NetBoxValidationError, NetBoxNotFoundError, NetBoxWriteError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ensure_device_role: {e}")
            raise NetBoxError(f"Unexpected error ensuring device role: {e}")