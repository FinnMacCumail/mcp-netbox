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