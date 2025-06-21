#!/usr/bin/env python3
"""
NetBox MCP Server

A Model Context Protocol server for safe read/write access to NetBox instances.
Provides tools for querying and managing NetBox data with comprehensive safety controls.

Version: 0.1.0
"""

from mcp.server.fastmcp import FastMCP
from .client import NetBoxClient, ConnectionStatus, NetBoxBulkOrchestrator
from .config import load_config, NetBoxConfig
from .exceptions import (
    NetBoxError,
    NetBoxConnectionError,
    NetBoxAuthError,
    NetBoxNotFoundError,
    NetBoxValidationError,
    NetBoxWriteError,
    NetBoxConfirmationError,
    NetBoxDryRunError
)
import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from functools import partial
from typing import Dict, List, Optional, Any, Union

# Global configuration and client
config: Optional[NetBoxConfig] = None
netbox_client: Optional[NetBoxClient] = None

# Configure logging (will be updated from config)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("NetBox", description="Read/Write MCP server for NetBox network documentation and IPAM")


@mcp.tool()
def netbox_health_check() -> Dict[str, Any]:
    """
    Get NetBox system health status and connection information.

    Returns:
        Health status information containing:
        - connected: True if connected, False otherwise
        - version: NetBox version (e.g., "4.2.9")
        - python_version: Python version of NetBox instance
        - django_version: Django version of NetBox instance
        - response_time_ms: Response time in milliseconds
        - plugins: Installed NetBox plugins
        - error: Error message if connection failed
    """
    try:
        status = netbox_client.health_check()
        return {
            "connected": status.connected,
            "version": status.version,
            "python_version": status.python_version,
            "django_version": status.django_version,
            "response_time_ms": status.response_time_ms,
            "plugins": status.plugins,
            "error": status.error
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


@mcp.tool()
def netbox_get_device(name: str, site: Optional[str] = None) -> Dict[str, Any]:
    """
    Get device information by name and optionally by site.

    Args:
        name: Device name to search for
        site: Optional site name to filter by

    Returns:
        Device information including:
        - Device details (name, type, role, status)
        - Site information
        - IP addresses (primary IPv4/IPv6)
        - Location and rack information
        - Tags and custom fields
        - Timestamps (created, last_updated)

    Example:
        netbox_get_device("switch-01")
        netbox_get_device("switch-01", "datacenter-1")
    """
    try:
        device = netbox_client.get_device(name, site)
        
        if device is None:
            return {
                "found": False,
                "message": f"Device '{name}' not found" + (f" at site '{site}'" if site else "")
            }
        
        return {
            "found": True,
            "device": device
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting device {name}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting device {name}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_list_devices(
    site: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    List devices with optional filtering.

    Args:
        site: Filter by site name (optional)
        role: Filter by device role (optional)
        status: Filter by device status (optional)
        limit: Maximum number of results to return (optional)

    Returns:
        List of devices with basic information:
        - Device name, type, site, role, status
        - Primary IP addresses
        - Last updated timestamp

    Example:
        netbox_list_devices()
        netbox_list_devices(site="datacenter-1", limit=10)
        netbox_list_devices(role="switch", status="active")
    """
    try:
        # Build filters dictionary
        filters = {}
        if site:
            filters['site'] = site
        if role:
            filters['role'] = role
        if status:
            filters['status'] = status
        
        devices = netbox_client.list_devices(filters=filters if filters else None, limit=limit)
        
        return {
            "count": len(devices),
            "devices": devices,
            "filters_applied": filters
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error listing devices: {e}")
        return {
            "count": 0,
            "devices": [],
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error listing devices: {e}")
        return {
            "count": 0,
            "devices": [],
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_site_by_name(name: str) -> Dict[str, Any]:
    """
    Get site information by name.

    Args:
        name: Site name to search for

    Returns:
        Site information including:
        - Site details (name, slug, status, description)
        - Location information (region, physical address)
        - Device and rack counts
        - Tags and custom fields
        - Timestamps (created, last_updated)

    Example:
        netbox_get_site_by_name("datacenter-1")
        netbox_get_site_by_name("branch-office-nyc")
    """
    try:
        site = netbox_client.get_site_by_name(name)
        
        if site is None:
            return {
                "found": False,
                "message": f"Site '{name}' not found"
            }
        
        return {
            "found": True,
            "site": site
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting site {name}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting site {name}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_find_ip(address: str) -> Dict[str, Any]:
    """
    Find IP address object by address.

    Args:
        address: IP address to search for (e.g., "192.168.1.1" or "192.168.1.1/24")

    Returns:
        IP address information including:
        - Address details (address, status, role)
        - Assignment information (device, interface)
        - VRF and tenant information
        - DNS name and description
        - Tags and custom fields

    Example:
        netbox_find_ip("192.168.1.1")
        netbox_find_ip("10.0.0.1/24")
    """
    try:
        ip = netbox_client.get_ip_address(address)
        
        if ip is None:
            return {
                "found": False,
                "message": f"IP address '{address}' not found"
            }
        
        return {
            "found": True,
            "ip_address": ip
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error finding IP {address}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error finding IP {address}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_vlan_by_name(name: str, site: Optional[str] = None) -> Dict[str, Any]:
    """
    Get VLAN information by name and optionally by site.

    Args:
        name: VLAN name to search for
        site: Optional site name to filter by

    Returns:
        VLAN information including:
        - VLAN details (name, VID, status, role)
        - Site and group information
        - Tenant information
        - Description and comments
        - Tags and custom fields

    Example:
        netbox_get_vlan_by_name("VLAN-100")
        netbox_get_vlan_by_name("Management", "datacenter-1")
    """
    try:
        vlan = netbox_client.get_vlan_by_name(name, site)
        
        if vlan is None:
            return {
                "found": False,
                "message": f"VLAN '{name}' not found" + (f" at site '{site}'" if site else "")
            }
        
        return {
            "found": True,
            "vlan": vlan
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting VLAN {name}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting VLAN {name}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_device_interfaces(device_name: str) -> Dict[str, Any]:
    """
    Get all interfaces for a specific device.

    Args:
        device_name: Name of the device to get interfaces for

    Returns:
        List of interfaces including:
        - Interface details (name, type, enabled status)
        - Network configuration (speed, duplex, MTU)
        - VLAN assignments (tagged/untagged)
        - MAC address and description
        - Connection status

    Example:
        netbox_get_device_interfaces("switch-01")
        netbox_get_device_interfaces("router-core-01")
    """
    try:
        interfaces = netbox_client.get_device_interfaces(device_name)
        
        return {
            "device_name": device_name,
            "interface_count": len(interfaces),
            "interfaces": interfaces
        }
        
    except NetBoxNotFoundError as e:
        logger.error(f"Device not found: {device_name}")
        return {
            "device_name": device_name,
            "interface_count": 0,
            "interfaces": [],
            "error": str(e),
            "error_type": "DeviceNotFound"
        }
    except NetBoxError as e:
        logger.error(f"NetBox error getting interfaces for {device_name}: {e}")
        return {
            "device_name": device_name,
            "interface_count": 0,
            "interfaces": [],
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting interfaces for {device_name}: {e}")
        return {
            "device_name": device_name,
            "interface_count": 0,
            "interfaces": [],
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_manufacturers(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Get list of manufacturers in NetBox.

    Args:
        limit: Maximum number of results to return (optional)

    Returns:
        List of manufacturers including:
        - Manufacturer details (name, slug, description)
        - Device type count for each manufacturer
        - Tags and custom fields
        - Timestamps (created, last_updated)

    Example:
        netbox_get_manufacturers()
        netbox_get_manufacturers(limit=10)
    """
    try:
        manufacturers = netbox_client.get_manufacturers(limit=limit)
        
        return {
            "count": len(manufacturers),
            "manufacturers": manufacturers
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting manufacturers: {e}")
        return {
            "count": 0,
            "manufacturers": [],
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting manufacturers: {e}")
        return {
            "count": 0,
            "manufacturers": [],
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


# === WRITE OPERATIONS MCP TOOLS ===
# All write operations require confirm=True for safety and respect dry-run mode


@mcp.tool()
def netbox_create_manufacturer(
    name: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new manufacturer in NetBox.

    SAFETY: This is a write operation that requires confirm=True for safety.
    All operations respect the global dry-run mode setting.

    Args:
        name: Manufacturer name (required)
        slug: URL slug (auto-generated from name if not provided)
        description: Optional description
        confirm: Must be True to execute the operation (safety mechanism)

    Returns:
        Created manufacturer information or error details

    Example:
        netbox_create_manufacturer("Cisco Systems", confirm=True)
        netbox_create_manufacturer("Dell Technologies", slug="dell", description="Server manufacturer", confirm=True)
    """
    try:
        # Input validation
        if not name or not name.strip():
            raise NetBoxValidationError("Manufacturer name cannot be empty")
        
        # Build manufacturer data
        data = {"name": name.strip()}
        if slug:
            data["slug"] = slug
        if description:
            data["description"] = description
        
        # Execute create operation (includes safety checks)
        result = netbox_client.create_object("manufacturers", data, confirm=confirm)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "manufacturer",
            "manufacturer": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except NetBoxConfirmationError as e:
        logger.warning(f"Create manufacturer failed - confirmation required: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ConfirmationRequired",
            "help": "Add confirm=True parameter to execute this write operation"
        }
    except NetBoxValidationError as e:
        logger.error(f"Create manufacturer validation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }
    except NetBoxWriteError as e:
        logger.error(f"Create manufacturer write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "WriteError"
        }
    except Exception as e:
        logger.error(f"Unexpected error creating manufacturer: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_create_site(
    name: str,
    slug: Optional[str] = None,
    status: str = "active",
    region: Optional[str] = None,
    description: Optional[str] = None,
    physical_address: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new site in NetBox.

    SAFETY: This is a write operation that requires confirm=True for safety.
    All operations respect the global dry-run mode setting.

    Args:
        name: Site name (required)
        slug: URL slug (auto-generated from name if not provided)
        status: Site status (default: "active")
        region: Optional region name
        description: Optional description
        physical_address: Optional physical address
        confirm: Must be True to execute the operation (safety mechanism)

    Returns:
        Created site information or error details

    Example:
        netbox_create_site("Datacenter Amsterdam", confirm=True)
        netbox_create_site("Branch Office NYC", slug="branch-nyc", status="active", confirm=True)
    """
    try:
        # Input validation
        if not name or not name.strip():
            raise NetBoxValidationError("Site name cannot be empty")
        
        # Build site data
        data = {
            "name": name.strip(),
            "status": status
        }
        if slug:
            data["slug"] = slug
        if region:
            data["region"] = region
        if description:
            data["description"] = description
        if physical_address:
            data["physical_address"] = physical_address
        
        # Execute create operation (includes safety checks)
        result = netbox_client.create_object("sites", data, confirm=confirm)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "site",
            "site": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except NetBoxConfirmationError as e:
        logger.warning(f"Create site failed - confirmation required: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ConfirmationRequired",
            "help": "Add confirm=True parameter to execute this write operation"
        }
    except NetBoxValidationError as e:
        logger.error(f"Create site validation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }
    except NetBoxWriteError as e:
        logger.error(f"Create site write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "WriteError"
        }
    except Exception as e:
        logger.error(f"Unexpected error creating site: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_create_device_role(
    name: str,
    slug: Optional[str] = None,
    color: str = "9e9e9e",
    vm_role: bool = False,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new device role in NetBox.

    SAFETY: This is a write operation that requires confirm=True for safety.
    All operations respect the global dry-run mode setting.

    Args:
        name: Device role name (required)
        slug: URL slug (auto-generated from name if not provided)
        color: Hex color code (default: gray)
        vm_role: Whether this role applies to virtual machines
        description: Optional description
        confirm: Must be True to execute the operation (safety mechanism)

    Returns:
        Created device role information or error details

    Example:
        netbox_create_device_role("Core Switch", confirm=True)
        netbox_create_device_role("Hypervisor", color="2196f3", vm_role=True, confirm=True)
    """
    try:
        # Input validation
        if not name or not name.strip():
            raise NetBoxValidationError("Device role name cannot be empty")
        
        # Build device role data
        data = {
            "name": name.strip(),
            "color": color,
            "vm_role": vm_role
        }
        if slug:
            data["slug"] = slug
        if description:
            data["description"] = description
        
        # Execute create operation (includes safety checks)
        result = netbox_client.create_object("device_roles", data, confirm=confirm)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "device_role",
            "device_role": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except NetBoxConfirmationError as e:
        logger.warning(f"Create device role failed - confirmation required: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ConfirmationRequired",
            "help": "Add confirm=True parameter to execute this write operation"
        }
    except NetBoxValidationError as e:
        logger.error(f"Create device role validation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }
    except NetBoxWriteError as e:
        logger.error(f"Create device role write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "WriteError"
        }
    except Exception as e:
        logger.error(f"Unexpected error creating device role: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_update_device_status(
    device_name: str,
    status: str,
    site: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Update the status of a device in NetBox.

    SAFETY: This is a write operation that requires confirm=True for safety.
    All operations respect the global dry-run mode setting.

    Args:
        device_name: Name of the device to update
        status: New status (e.g., "active", "offline", "decommissioning")
        site: Optional site name to help identify the device
        confirm: Must be True to execute the operation (safety mechanism)

    Returns:
        Updated device information or error details

    Example:
        netbox_update_device_status("switch-01", "offline", confirm=True)
        netbox_update_device_status("router-01", "active", site="datacenter-1", confirm=True)
    """
    try:
        # Safety check first - this ensures confirm=True is required regardless of device existence
        if not confirm:
            raise NetBoxConfirmationError("Write operation 'update_device_status' requires confirm=True parameter")
        
        # Then find the device
        device = netbox_client.get_device(device_name, site)
        if not device:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found" + (f" at site '{site}'" if site else ""),
                "error_type": "DeviceNotFound"
            }
        
        # Execute update operation (includes safety checks)
        result = netbox_client.update_object("devices", device["id"], {"status": status}, confirm=confirm)
        
        return {
            "success": True,
            "action": "updated",
            "object_type": "device",
            "device": result,
            "old_status": device.get("status"),
            "new_status": status,
            "dry_run": result.get("dry_run", False)
        }
        
    except NetBoxConfirmationError as e:
        logger.warning(f"Update device status failed - confirmation required: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ConfirmationRequired",
            "help": "Add confirm=True parameter to execute this write operation"
        }
    except NetBoxNotFoundError as e:
        logger.error(f"Update device status failed - device not found: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "DeviceNotFound"
        }
    except NetBoxValidationError as e:
        logger.error(f"Update device status validation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }
    except NetBoxWriteError as e:
        logger.error(f"Update device status write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "WriteError"
        }
    except Exception as e:
        logger.error(f"Unexpected error updating device status: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_delete_manufacturer(
    manufacturer_name: str,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Delete a manufacturer from NetBox.

    SAFETY: This is a destructive write operation that requires confirm=True for safety.
    All operations respect the global dry-run mode setting.

    WARNING: This will fail if the manufacturer is referenced by device types or other objects.

    Args:
        manufacturer_name: Name of the manufacturer to delete
        confirm: Must be True to execute the operation (safety mechanism)

    Returns:
        Deletion result or error details

    Example:
        netbox_delete_manufacturer("Obsolete Vendor", confirm=True)
    """
    try:
        # Safety check first - this ensures confirm=True is required regardless of manufacturer existence
        if not confirm:
            raise NetBoxConfirmationError("Write operation 'delete_manufacturer' requires confirm=True parameter")
        
        # Then find the manufacturer
        manufacturers = netbox_client.get_manufacturers()
        manufacturer = None
        for mfg in manufacturers:
            if mfg["name"].lower() == manufacturer_name.lower():
                manufacturer = mfg
                break
        
        if not manufacturer:
            return {
                "success": False,
                "error": f"Manufacturer '{manufacturer_name}' not found",
                "error_type": "ManufacturerNotFound"
            }
        
        # Execute delete operation (includes safety checks)
        result = netbox_client.delete_object("manufacturers", manufacturer["id"], confirm=confirm)
        
        return {
            "success": True,
            "action": "deleted",
            "object_type": "manufacturer",
            "deleted_manufacturer": result.get("original_data", manufacturer),
            "dry_run": result.get("dry_run", False)
        }
        
    except NetBoxConfirmationError as e:
        logger.warning(f"Delete manufacturer failed - confirmation required: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ConfirmationRequired",
            "help": "Add confirm=True parameter to execute this write operation"
        }
    except NetBoxNotFoundError as e:
        logger.error(f"Delete manufacturer failed - not found: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ManufacturerNotFound"
        }
    except NetBoxWriteError as e:
        logger.error(f"Delete manufacturer write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "WriteError",
            "help": "Manufacturer may be referenced by device types or other objects"
        }
    except Exception as e:
        logger.error(f"Unexpected error deleting manufacturer: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_bulk_ensure_devices(
    devices_data: List[Dict[str, Any]],
    confirm: bool = False,
    dry_run_report: bool = False
) -> Dict[str, Any]:
    """
    Ensure multiple devices and their dependencies using two-pass strategy.
    
    This is the primary tool for bulk device synchronization leveraging the
    NetBoxBulkOrchestrator for enterprise-grade two-pass dependency resolution.
    
    SAFETY: This is a complex write operation that requires confirm=True for safety.
    All operations respect the global dry-run mode setting.
    
    Args:
        devices_data: List of device data dictionaries with nested relationships
        confirm: Must be True to execute operations (safety mechanism)
        dry_run_report: If True, generate pre-flight report without changes
        
    Returns:
        Comprehensive two-pass operation results with statistics
        
    Example device data structure:
        [
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
            }
        ]
    """
    try:
        # Input validation
        if not devices_data or not isinstance(devices_data, list):
            return {
                "success": False,
                "error": "devices_data must be a non-empty list of device dictionaries",
                "error_type": "ValidationError"
            }
        
        # Validate each device has required fields
        required_fields = ["name", "manufacturer", "device_type", "site", "role"]
        for i, device in enumerate(devices_data):
            missing_fields = [field for field in required_fields if not device.get(field)]
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Device {i} missing required fields: {', '.join(missing_fields)}",
                    "error_type": "ValidationError"
                }
        
        # Initialize stateless orchestrator
        orchestrator = NetBoxBulkOrchestrator(netbox_client)
        batch_id = orchestrator.generate_batch_id()
        
        logger.info(f"Starting bulk device operation with batch ID: {batch_id}")
        logger.info(f"Processing {len(devices_data)} devices with two-pass strategy")
        
        # If dry_run_report requested, generate pre-flight analysis
        if dry_run_report:
            logger.info("Generating pre-flight report for bulk device operation")
            
            # Analyze what would be created/updated
            pre_flight_summary = {
                "batch_id": batch_id,
                "devices_to_process": len(devices_data),
                "estimated_operations": {
                    "manufacturers": len(set(d.get("manufacturer") for d in devices_data if d.get("manufacturer"))),
                    "sites": len(set(d.get("site") for d in devices_data if d.get("site"))),
                    "device_roles": len(set(d.get("role") for d in devices_data if d.get("role"))),
                    "device_types": len(set(d.get("device_type") for d in devices_data if d.get("device_type"))),
                    "devices": len(devices_data)
                },
                "dry_run_mode": True,
                "safety_checks": {
                    "confirm_required": not confirm,
                    "global_dry_run": netbox_client.config.safety.dry_run_mode
                }
            }
            
            return {
                "success": True,
                "action": "pre_flight_report",
                "pre_flight_analysis": pre_flight_summary,
                "message": "Pre-flight report generated. Use confirm=True to execute operations."
            }
        
        # Safety check for actual execution
        if not confirm:
            return {
                "success": False,
                "error": "Bulk device operation requires confirm=True parameter for safety",
                "error_type": "ConfirmationRequired",
                "help": "Use dry_run_report=True to analyze operations before execution"
            }
        
        # Process each device through two-pass strategy
        total_results = {
            "batch_id": batch_id,
            "devices_processed": 0,
            "devices_successful": 0,
            "devices_failed": 0,
            "pass_1_results": [],
            "pass_2_results": [],
            "errors": []
        }
        
        for i, device_data in enumerate(devices_data):
            try:
                logger.info(f"Processing device {i+1}/{len(devices_data)}: {device_data.get('name')}")
                
                # Normalize device data for two-pass processing
                normalized_data = orchestrator.normalize_device_data(device_data)
                
                # Execute Pass 1: Core objects
                pass_1_results = orchestrator.execute_pass_1(normalized_data, confirm=confirm)
                total_results["pass_1_results"].append({
                    "device_name": device_data.get("name"),
                    "results": pass_1_results
                })
                
                # Execute Pass 2: Relationships
                pass_2_results = orchestrator.execute_pass_2(normalized_data, pass_1_results, confirm=confirm)
                total_results["pass_2_results"].append({
                    "device_name": device_data.get("name"),
                    "results": pass_2_results
                })
                
                total_results["devices_processed"] += 1
                total_results["devices_successful"] += 1
                
                logger.info(f"Successfully processed device: {device_data.get('name')}")
                
            except Exception as device_error:
                error_details = {
                    "device_index": i,
                    "device_name": device_data.get("name"),
                    "error": str(device_error),
                    "error_type": type(device_error).__name__
                }
                total_results["errors"].append(error_details)
                total_results["devices_failed"] += 1
                
                logger.error(f"Failed to process device {device_data.get('name')}: {device_error}")
        
        # Generate comprehensive operation report
        operation_report = orchestrator.generate_operation_report()
        
        # Determine overall success
        overall_success = total_results["devices_failed"] == 0
        
        logger.info(f"Bulk device operation completed. Success: {overall_success}")
        logger.info(f"Processed: {total_results['devices_processed']}, "
                   f"Successful: {total_results['devices_successful']}, "
                   f"Failed: {total_results['devices_failed']}")
        
        return {
            "success": overall_success,
            "action": "bulk_device_operation",
            "batch_id": batch_id,
            "summary": {
                "devices_processed": total_results["devices_processed"],
                "devices_successful": total_results["devices_successful"],
                "devices_failed": total_results["devices_failed"],
                "success_rate": round(total_results["devices_successful"] / len(devices_data) * 100, 2) if devices_data else 100
            },
            "detailed_results": total_results,
            "operation_report": operation_report,
            "dry_run": netbox_client.config.safety.dry_run_mode
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in bulk device operation: {e}")
        return {
            "success": False,
            "error": f"Bulk operation failed: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_start_bulk_async(
    devices_data: List[Dict[str, Any]],
    confirm: bool = False,
    max_devices: int = 1000
) -> Dict[str, Any]:
    """
    Start asynchronous bulk device operation for large device lists.
    
    For large device collections, this operation runs in the background to prevent
    MCP client timeouts. Use netbox_get_task_status() to monitor progress.
    
    SAFETY: This is a complex async write operation that requires confirm=True.
    All operations respect the global dry-run mode setting.
    
    Args:
        devices_data: List of device data dictionaries with nested relationships
        confirm: Must be True to execute operations (safety mechanism)
        max_devices: Maximum devices allowed in single operation (safety limit)
        
    Returns:
        Task information with task_id for progress tracking
        
    Example:
        # Start async operation
        result = netbox_start_bulk_async([device1, device2, ...], confirm=True)
        task_id = result["task_id"]
        
        # Monitor progress
        status = netbox_get_task_status(task_id)
    """
    try:
        # Import task manager
        from .tasks import get_task_manager
        
        task_manager = get_task_manager()
        if task_manager is None:
            return {
                "success": False,
                "error": "Async task queue not available - Redis/RQ not configured",
                "error_type": "TaskQueueUnavailable",
                "help": "Use netbox_bulk_ensure_devices() for synchronous operation"
            }
        
        # Input validation
        if not devices_data or not isinstance(devices_data, list):
            return {
                "success": False,
                "error": "devices_data must be a non-empty list of device dictionaries",
                "error_type": "ValidationError"
            }
        
        if len(devices_data) > max_devices:
            return {
                "success": False,
                "error": f"Device count ({len(devices_data)}) exceeds maximum ({max_devices})",
                "error_type": "ValidationError",
                "help": f"Split into smaller batches or increase max_devices limit"
            }
        
        # Validate each device has required fields
        required_fields = ["name", "manufacturer", "device_type", "site", "role"]
        for i, device in enumerate(devices_data):
            missing_fields = [field for field in required_fields if not device.get(field)]
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Device {i} missing required fields: {', '.join(missing_fields)}",
                    "error_type": "ValidationError"
                }
        
        # Safety check for actual execution
        if not confirm:
            return {
                "success": False,
                "error": "Async bulk operation requires confirm=True parameter for safety",
                "error_type": "ConfirmationRequired",
                "help": "Use netbox_get_task_status() to monitor progress after starting"
            }
        
        # Prepare task configuration
        task_config = {
            "confirm": confirm,
            "netbox_url": netbox_client.config.url,
            "netbox_token": netbox_client.config.token,
            "timeout": netbox_client.config.timeout,
            "verify_ssl": netbox_client.config.verify_ssl,
            "dry_run_mode": netbox_client.config.safety.dry_run_mode
        }
        
        # Queue the async operation
        task_id = task_manager.queue_bulk_device_operation(
            devices_data, 
            task_config,
            timeout=3600  # 1 hour timeout
        )
        
        # Calculate estimated duration (rough estimate: 2 seconds per device)
        estimated_minutes = max(1, len(devices_data) * 2 // 60)
        
        logger.info(f"Started async bulk operation: {task_id} ({len(devices_data)} devices)")
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued", 
            "device_count": len(devices_data),
            "estimated_duration_minutes": estimated_minutes,
            "monitor_with": "netbox_get_task_status",
            "queue_info": task_manager.get_queue_info()
        }
        
    except Exception as e:
        logger.error(f"Failed to start async bulk operation: {e}")
        return {
            "success": False,
            "error": f"Failed to queue async operation: {str(e)}",
            "error_type": "TaskQueueError"
        }


@mcp.tool()
def netbox_get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status and progress of asynchronous task.
    
    Args:
        task_id: Task identifier returned by netbox_start_bulk_async
        
    Returns:
        Current task status, progress, and results (if completed)
        
    Example:
        status = netbox_get_task_status("bulk_devices_100dev_1234567890_a1b2c3d4")
        
        if status["task_status"]["status"] == "completed":
            results = status["task_status"]["results"]
        elif status["task_status"]["status"] == "running":
            progress = status["task_status"]["progress"]
    """
    try:
        from .tasks import get_task_manager
        
        task_manager = get_task_manager()
        if task_manager is None:
            return {
                "success": False,
                "error": "Async task queue not available - Redis/RQ not configured",
                "error_type": "TaskQueueUnavailable"
            }
        
        # Get task status from tracker
        task_status = task_manager.tracker.get_task_status(task_id)
        
        if task_status["status"] == "not_found":
            return {
                "success": False,
                "error": "Task not found or expired",
                "error_type": "TaskNotFound",
                "help": "Task data expires after 1 hour"
            }
        
        # Enhance status with human-readable information
        if task_status["status"] == "running":
            stage = task_status.get("stage", "unknown")
            progress = task_status.get("progress", 0)
            
            stage_descriptions = {
                "initialization": "Preparing bulk operation and NetBox connection",
                "processing": "Processing devices using two-pass strategy",
                "validation": "Validating results and generating reports"
            }
            
            task_status["stage_description"] = stage_descriptions.get(stage, stage)
            task_status["progress_percentage"] = f"{progress:.1f}%"
            
            # Add current processing info if available
            if "current_device" in task_status:
                task_status["current_status"] = f"Processing: {task_status['current_device']}"
        
        elif task_status["status"] == "completed":
            # Add summary information for completed tasks
            results = task_status.get("results", {})
            summary = results.get("summary", {})
            
            task_status["completion_summary"] = {
                "total_devices": summary.get("total_devices", 0),
                "successful_devices": summary.get("successful_devices", 0),
                "failed_devices": summary.get("failed_devices", 0),
                "success_rate": f"{summary.get('success_rate', 0):.1f}%"
            }
        
        return {
            "success": True,
            "task_status": task_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return {
            "success": False,
            "error": f"Failed to retrieve task status: {str(e)}",
            "error_type": "StatusQueryError"
        }


@mcp.tool()
def netbox_list_active_tasks() -> Dict[str, Any]:
    """
    List all currently active asynchronous tasks.
    
    Returns:
        List of active tasks with their current status and progress
        
    Example:
        active_tasks = netbox_list_active_tasks()
        for task in active_tasks["tasks"]:
            print(f"Task {task['task_id']}: {task['status']} ({task['progress']}%)")
    """
    try:
        from .tasks import get_task_manager
        
        task_manager = get_task_manager()
        if task_manager is None:
            return {
                "success": False,
                "error": "Async task queue not available - Redis/RQ not configured",
                "error_type": "TaskQueueUnavailable"
            }
        
        # Get all active tasks
        active_tasks = task_manager.tracker.list_active_tasks()
        
        # Add summary statistics
        status_counts = {}
        for task in active_tasks:
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        queue_info = task_manager.get_queue_info()
        
        return {
            "success": True,
            "task_count": len(active_tasks),
            "tasks": active_tasks,
            "status_summary": status_counts,
            "queue_info": queue_info
        }
        
    except Exception as e:
        logger.error(f"Failed to list active tasks: {e}")
        return {
            "success": False,
            "error": f"Failed to list tasks: {str(e)}",
            "error_type": "TaskListError"
        }


@mcp.tool()
def netbox_get_queue_info() -> Dict[str, Any]:
    """
    Get information about the async task queue status.
    
    Returns:
        Queue statistics, worker information, and system status
        
    Example:
        queue_info = netbox_get_queue_info()
        print(f"Jobs in queue: {queue_info['queue_info']['job_count']}")
        print(f"Workers active: {queue_info['queue_info']['worker_count']}")
    """
    try:
        from .tasks import get_task_manager
        
        task_manager = get_task_manager()
        if task_manager is None:
            return {
                "success": False,
                "error": "Async task queue not available - Redis/RQ not configured",
                "error_type": "TaskQueueUnavailable",
                "help": "Install Redis and RQ: pip install rq redis"
            }
        
        queue_info = task_manager.get_queue_info()
        
        # Add task tracker statistics
        active_tasks = task_manager.tracker.list_active_tasks()
        task_status_counts = {}
        for task in active_tasks:
            status = task.get("status", "unknown")
            task_status_counts[status] = task_status_counts.get(status, 0) + 1
        
        return {
            "success": True,
            "queue_info": queue_info,
            "task_tracker": {
                "active_tasks": len(active_tasks),
                "status_breakdown": task_status_counts
            },
            "system_status": {
                "redis_available": queue_info["redis_info"]["connected"],
                "rq_available": True
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue info: {e}")
        return {
            "success": False,
            "error": f"Failed to get queue information: {str(e)}",
            "error_type": "QueueInfoError"
        }


# HTTP Health Check Server (similar to unimus-mcp)
class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints."""
    
    def do_GET(self):
        """Handle GET requests for health check endpoints."""
        try:
            if self.path in ['/health', '/healthz']:
                # Basic liveness check
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response = {
                    "status": "OK",
                    "service": "netbox-mcp",
                    "version": "0.1.0"
                }
                self.wfile.write(json.dumps(response).encode())
                
            elif self.path == '/readyz':
                # Readiness check - test NetBox connection
                try:
                    if netbox_client:
                        status = netbox_client.health_check()
                        if status.connected:
                            self.send_response(200)
                            response = {
                                "status": "OK",
                                "netbox_connected": True,
                                "netbox_version": status.version,
                                "response_time_ms": status.response_time_ms
                            }
                        else:
                            self.send_response(503)
                            response = {
                                "status": "Service Unavailable",
                                "netbox_connected": False,
                                "error": status.error
                            }
                    else:
                        self.send_response(503)
                        response = {
                            "status": "Service Unavailable",
                            "netbox_connected": False,
                            "error": "NetBox client not initialized"
                        }
                except Exception as e:
                    self.send_response(503)
                    response = {
                        "status": "Service Unavailable",
                        "netbox_connected": False,
                        "error": str(e)
                    }
                
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response = {"error": "Not Found"}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"Health check handler error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {"error": "Internal Server Error", "details": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"Health check: {format % args}")


def start_health_server(port: int):
    """Start the HTTP health check server in a separate thread."""
    def run_server():
        try:
            server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
            logger.info(f"Health check server started on port {port}")
            logger.info(f"Health endpoints: /health, /healthz (liveness), /readyz (readiness)")
            server.serve_forever()
        except Exception as e:
            logger.error(f"Health check server failed: {e}")
    
    health_thread = threading.Thread(target=run_server, daemon=True)
    health_thread.start()


def initialize_server():
    """Initialize the NetBox MCP server with configuration and client."""
    global config, netbox_client
    
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded successfully")
        
        # Update logging level
        logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
        logger.info(f"Log level set to {config.log_level}")
        
        # Log safety configuration
        if config.safety.dry_run_mode:
            logger.warning("🚨 NetBox MCP running in DRY-RUN mode - no actual writes will be performed")
        
        if not config.safety.enable_write_operations:
            logger.info("🔒 Write operations are DISABLED - server is read-only")
        
        # Initialize NetBox client
        netbox_client = NetBoxClient(config)
        logger.info("NetBox client initialized successfully")
        
        # Test connection
        status = netbox_client.health_check()
        if status.connected:
            logger.info(f"✅ Connected to NetBox {status.version} (response time: {status.response_time_ms:.1f}ms)")
        else:
            logger.error(f"❌ Failed to connect to NetBox: {status.error}")
        
        # Initialize async task manager (optional)
        try:
            from .tasks import initialize_task_manager
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            task_manager = initialize_task_manager(redis_url)
            
            if task_manager:
                logger.info("✅ Async task queue initialized - Redis/RQ available")
                logger.info("Async tools: netbox_start_bulk_async, netbox_get_task_status")
            else:
                logger.info("⚠️  Async task queue not available - using synchronous operations only")
        except Exception as e:
            logger.warning(f"Async task queue initialization failed: {e}")
            logger.info("Falling back to synchronous operations only")
        
        # Start health check server if enabled
        if config.enable_health_server:
            start_health_server(config.health_check_port)
        
        logger.info("NetBox MCP server initialization complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize NetBox MCP server: {e}")
        raise


def main():
    """Main entry point for the NetBox MCP server."""
    try:
        # Initialize server
        initialize_server()
        
        # Define the MCP server task to run in a thread
        def run_mcp_server():
            try:
                logger.info("Starting NetBox MCP server on a dedicated thread...")
                mcp.run(transport="stdio")
            except Exception as e:
                logger.error(f"MCP server thread encountered an error: {e}", exc_info=True)

        # Start the MCP server in a daemon thread
        mcp_thread = threading.Thread(target=run_mcp_server)
        mcp_thread.daemon = True
        mcp_thread.start()
        
        # Keep the main thread alive to allow daemon threads to run
        logger.info("NetBox MCP server is ready and listening")
        logger.info("Health endpoints: /health, /healthz (liveness), /readyz (readiness)")
        
        try:
            while True:
                time.sleep(3600)  # Sleep for a long time
        except KeyboardInterrupt:
            logger.info("Shutting down NetBox MCP server...")
        
    except Exception as e:
        logger.error(f"NetBox MCP server error: {e}")
        raise


if __name__ == "__main__":
    main()