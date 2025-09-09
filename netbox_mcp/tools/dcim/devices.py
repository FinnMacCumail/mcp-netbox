#\!/usr/bin/env python3
"""
DCIM Device Lifecycle Management Tools

High-level tools for managing NetBox devices with comprehensive lifecycle management,
including creation, provisioning, decommissioning, and enterprise-grade functionality.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)



@mcp_tool(category="dcim")
def netbox_get_device_info(
    client: NetBoxClient,
    device_name: str,
    site: Optional[str] = None,
    interface_limit: int = 20,
    cable_limit: int = 10,
    include_interfaces: bool = True,
    include_cables: bool = True
) -> Dict[str, Any]:
    """
    Get comprehensive information about a device with pagination support.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        site: Optional site name for filtering
        interface_limit: Maximum number of interfaces to return (default: 20)
        cable_limit: Maximum number of cables to return (default: 10)
        include_interfaces: Include interface information (default: True)
        include_cables: Include cable information (default: True)
        
    Returns:
        Device information including limited interfaces and connections
        
    Example:
        netbox_get_device_info("rtr-01", site="amsterdam-dc")
        netbox_get_device_info("switch-01", interface_limit=50, cable_limit=20)
        netbox_get_device_info("server-01", include_cables=False)
        
    Note:
        For devices with many interfaces/cables, use the specialized tools:
        - netbox_get_device_basic_info (device only)
        - netbox_get_device_interfaces (interfaces with pagination)
        - netbox_get_device_cables (cables with pagination)
    """
    try:
        logger.info(f"Getting device information: {device_name}")
        
        # Build filter
        device_filter = {"name": device_name}
        if site:
            device_filter["site"] = site
        
        # Find the device
        devices = client.dcim.devices.filter(**device_filter)
        
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found" + (f" in site '{site}'" if site else ""),
                "error_type": "DeviceNotFound"
            }
        
        device = devices[0]
        device_id = device["id"]
        
        # Get related information with pagination
        result_data = {
            "success": True,
            "device": device
        }
        
        # Get interfaces with API-side pagination if requested
        if include_interfaces:
            # Use API-side counting for efficiency
            total_interfaces = client.dcim.interfaces.count(device_id=device_id)
            # Use API-side pagination with limit parameter
            interfaces = list(client.dcim.interfaces.filter(device_id=device_id, limit=interface_limit))
            result_data["interfaces"] = interfaces
            result_data["interface_pagination"] = {
                "total_count": total_interfaces,
                "returned_count": len(interfaces),
                "limit": interface_limit,
                "truncated": total_interfaces > interface_limit
            }
        else:
            result_data["interfaces"] = []
            result_data["interface_pagination"] = {
                "total_count": 0,
                "returned_count": 0,
                "limit": interface_limit,
                "truncated": False
            }
        
        # Get cables with API-side pagination if requested
        if include_cables:
            # Use API-side counting for efficiency
            total_cables = client.dcim.cables.count(termination_a_id=device_id)
            # Use API-side pagination with limit parameter
            cables = list(client.dcim.cables.filter(termination_a_id=device_id, limit=cable_limit))
            result_data["cables"] = cables
            result_data["cable_pagination"] = {
                "total_count": total_cables,
                "returned_count": len(cables),
                "limit": cable_limit,
                "truncated": total_cables > cable_limit
            }
        else:
            result_data["cables"] = []
            result_data["cable_pagination"] = {
                "total_count": 0,
                "returned_count": 0,
                "limit": cable_limit,
                "truncated": False
            }
        
        # Power connections endpoint doesn't exist in this NetBox version
        result_data["power_connections"] = []
        
        # Statistics
        result_data["statistics"] = {
            "interface_count": result_data["interface_pagination"]["total_count"],
            "cable_count": result_data["cable_pagination"]["total_count"],
            "power_connection_count": 0,
            "interface_returned": result_data["interface_pagination"]["returned_count"],
            "cable_returned": result_data["cable_pagination"]["returned_count"]
        }
        
        return result_data
        
    except Exception as e:
        logger.error(f"Failed to get device info for {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_device_basic_info(
    client: NetBoxClient,
    device_name: str,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get basic device information only (no interfaces or cables).
    
    This lightweight tool returns only device details without related objects,
    making it ideal for quick device lookups that respect token limits.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        site: Optional site name for filtering
        
    Returns:
        Basic device information without interfaces or cables
        
    Example:
        netbox_get_device_basic_info("rtr-01", site="amsterdam-dc")
        netbox_get_device_basic_info("switch-01")
    """
    try:
        logger.info(f"Getting basic device information: {device_name}")
        
        # Build filter
        device_filter = {"name": device_name}
        if site:
            device_filter["site"] = site
        
        # Find the device
        devices = client.dcim.devices.filter(**device_filter)
        
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found" + (f" in site '{site}'" if site else ""),
                "error_type": "DeviceNotFound"
            }
        
        device = devices[0]
        device_id = device["id"]
        
        # Get counts only (no actual data)
        interface_count = len(list(client.dcim.interfaces.filter(device_id=device_id)))
        cable_count = len(list(client.dcim.cables.filter(termination_a_id=device_id)))
        
        return {
            "success": True,
            "device": device,
            "statistics": {
                "interface_count": interface_count,
                "cable_count": cable_count,
                "power_connection_count": 0
            },
            "note": "Use netbox_get_device_interfaces or netbox_get_device_cables for detailed related data"
        }
        
    except Exception as e:
        logger.error(f"Failed to get basic device info for {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_device_interfaces(
    client: NetBoxClient,
    device_name: str,
    site: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    interface_type: Optional[str] = None,
    enabled_only: bool = False
) -> Dict[str, Any]:
    """
    Get device interfaces with pagination support.
    
    This specialized tool returns device interfaces with comprehensive filtering
    and pagination, ideal for devices with many interfaces.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        site: Optional site name for filtering
        limit: Maximum number of interfaces to return (default: 50)
        offset: Starting position for pagination (default: 0)
        interface_type: Filter by interface type (optional)
        enabled_only: Only return enabled interfaces (default: False)
        
    Returns:
        Device interfaces with pagination information
        
    Example:
        netbox_get_device_interfaces("switch-01")
        netbox_get_device_interfaces("switch-01", limit=20, offset=40)
        netbox_get_device_interfaces("server-01", enabled_only=True)
    """
    try:
        logger.info(f"Getting device interfaces: {device_name}")
        
        # Build device filter
        device_filter = {"name": device_name}
        if site:
            device_filter["site"] = site
        
        # Find the device
        devices = client.dcim.devices.filter(**device_filter)
        
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found" + (f" in site '{site}'" if site else ""),
                "error_type": "DeviceNotFound"
            }
        
        device = devices[0]
        device_id = device["id"]
        
        # Build interface filter
        interface_filter = {"device_id": device_id}
        if interface_type:
            interface_filter["type"] = interface_type
        if enabled_only:
            interface_filter["enabled"] = True
        
        # Use API-side counting and pagination for efficiency
        total_count = client.dcim.interfaces.count(**interface_filter)
        
        # Apply API-side pagination with limit and offset
        interfaces = list(client.dcim.interfaces.filter(
            **interface_filter,
            limit=limit,
            offset=offset
        ))
        
        end_index = offset + len(interfaces)
        
        return {
            "success": True,
            "device": {
                "id": device["id"],
                "name": device["name"],
                "display": device.get("display", device["name"])
            },
            "interfaces": interfaces,
            "pagination": {
                "total_count": total_count,
                "returned_count": len(interfaces),
                "limit": limit,
                "offset": offset,
                "has_next": end_index < total_count,
                "has_previous": offset > 0,
                "next_offset": end_index if end_index < total_count else None,
                "previous_offset": max(0, offset - limit) if offset > 0 else None
            },
            "filters_applied": {
                "interface_type": interface_type,
                "enabled_only": enabled_only
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get device interfaces for {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_device_cables(
    client: NetBoxClient,
    device_name: str,
    site: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    cable_status: Optional[str] = None,
    cable_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get device cables with pagination support.
    
    This specialized tool returns device cables with comprehensive filtering
    and pagination, ideal for devices with many cable connections.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        site: Optional site name for filtering
        limit: Maximum number of cables to return (default: 50)
        offset: Starting position for pagination (default: 0)
        cable_status: Filter by cable status (optional)
        cable_type: Filter by cable type (optional)
        
    Returns:
        Device cables with pagination information
        
    Example:
        netbox_get_device_cables("switch-01")
        netbox_get_device_cables("switch-01", limit=20, offset=20)
        netbox_get_device_cables("server-01", cable_status="connected")
    """
    try:
        logger.info(f"Getting device cables: {device_name}")
        
        # Build device filter
        device_filter = {"name": device_name}
        if site:
            device_filter["site"] = site
        
        # Find the device
        devices = client.dcim.devices.filter(**device_filter)
        
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found" + (f" in site '{site}'" if site else ""),
                "error_type": "DeviceNotFound"
            }
        
        device = devices[0]
        device_id = device["id"]
        
        # Build cable filter - cables where this device is termination A
        cable_filter = {"termination_a_id": device_id}
        if cable_status:
            cable_filter["status"] = cable_status
        if cable_type:
            cable_filter["type"] = cable_type
        
        # Use API-side counting and pagination for efficiency
        total_count = client.dcim.cables.count(**cable_filter)
        
        # Apply API-side pagination with limit and offset
        cables = list(client.dcim.cables.filter(
            **cable_filter,
            limit=limit,
            offset=offset
        ))
        
        end_index = offset + len(cables)
        
        return {
            "success": True,
            "device": {
                "id": device["id"],
                "name": device["name"],
                "display": device.get("display", device["name"])
            },
            "cables": cables,
            "pagination": {
                "total_count": total_count,
                "returned_count": len(cables),
                "limit": limit,
                "offset": offset,
                "has_next": end_index < total_count,
                "has_previous": offset > 0,
                "next_offset": end_index if end_index < total_count else None,
                "previous_offset": max(0, offset - limit) if offset > 0 else None
            },
            "filters_applied": {
                "cable_status": cable_status,
                "cable_type": cable_type
            },
            "note": "Only shows cables where this device is termination A. Use netbox_list_all_cables for comprehensive cable search."
        }
        
    except Exception as e:
        logger.error(f"Failed to get device cables for {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }




@mcp_tool(category="dcim")
def netbox_list_all_devices(
    client: NetBoxClient,
    limit: int = 100,
    site_name: Optional[str] = None,
    role_name: Optional[str] = None,
    tenant_name: Optional[str] = None,
    status: Optional[str] = None,
    manufacturer_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a summarized list of all devices in NetBox.

    This function is the correct choice for open, exploratory questions like
    "what devices are there?" or "show all servers in datacenter-1". Use 
    'netbox_get_device' for detailed information about one specific device.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        limit: Maximum number of results to return (default: 100)
        site_name: Filter by site name (optional)
        role_name: Filter by device role name (optional)
        tenant_name: Filter by tenant name (optional)
        status: Filter by device status (active, offline, planned, etc.)
        manufacturer_name: Filter by manufacturer name (optional)
        
    Returns:
        Dictionary containing:
        - count: Total number of devices found
        - devices: List of summarized device information
        - filters_applied: Dictionary of filters that were applied
        - summary_stats: Aggregate statistics about the devices
        
    Example:
        netbox_list_all_devices(site_name="datacenter-1", role_name="switch")
        netbox_list_all_devices(status="active", manufacturer_name="Cisco")
        netbox_list_all_devices(tenant_name="customer-a", limit=50)
    """
    try:
        logger.info(f"Listing devices with filters - site: {site_name}, role: {role_name}, tenant: {tenant_name}, status: {status}, manufacturer: {manufacturer_name}")
        
        # Build filters dictionary - only include non-None values
        filters = {}
        if site_name:
            filters['site'] = site_name
        if role_name:
            filters['role'] = role_name
        if tenant_name:
            filters['tenant'] = tenant_name
        if status:
            filters['status'] = status
        if manufacturer_name:
            # For manufacturer filtering, we need to filter by device_type__manufacturer
            filters['device_type__manufacturer'] = manufacturer_name
        
        # Execute filtered query with limit
        devices = list(client.dcim.devices.filter(**filters))
        
        # Apply limit after fetching (since pynetbox limit behavior can be inconsistent)
        if len(devices) > limit:
            devices = devices[:limit]
        
        # Generate summary statistics
        status_counts = {}
        role_counts = {}
        site_counts = {}
        manufacturer_counts = {}
        
        for device in devices:
            # Status breakdown with defensive checks for dictionary access
            status_obj = device.get("status", {})
            if isinstance(status_obj, dict):
                status = status_obj.get("label", "N/A")
            else:
                status = str(status_obj) if status_obj else "N/A"
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Role breakdown with defensive checks for dictionary access
            role_obj = device.get("role")
            if role_obj:
                if isinstance(role_obj, dict):
                    role_name = role_obj.get("name", str(role_obj))
                else:
                    role_name = str(role_obj)
                role_counts[role_name] = role_counts.get(role_name, 0) + 1
            
            # Site breakdown with defensive checks for dictionary access
            site_obj = device.get("site")
            if site_obj:
                if isinstance(site_obj, dict):
                    site_name = site_obj.get("name", str(site_obj))
                else:
                    site_name = str(site_obj)
                site_counts[site_name] = site_counts.get(site_name, 0) + 1
            
            # Manufacturer breakdown with defensive checks for dictionary access
            device_type_obj = device.get("device_type")
            if device_type_obj and isinstance(device_type_obj, dict):
                manufacturer_obj = device_type_obj.get("manufacturer")
                if manufacturer_obj:
                    if isinstance(manufacturer_obj, dict):
                        mfg_name = manufacturer_obj.get("name", str(manufacturer_obj))
                    else:
                        mfg_name = str(manufacturer_obj)
                    manufacturer_counts[mfg_name] = manufacturer_counts.get(mfg_name, 0) + 1
        
        # Create human-readable device list
        device_list = []
        for device in devices:
            # DEFENSIVE CHECK: Handle dictionary access for all device attributes
            status_obj = device.get("status", {})
            if isinstance(status_obj, dict):
                status = status_obj.get("label", "N/A")
            else:
                status = str(status_obj) if status_obj else "N/A"
            
            site_obj = device.get("site")
            site_name = None
            if site_obj and isinstance(site_obj, dict):
                site_name = site_obj.get("name")
            elif site_obj:
                site_name = str(site_obj)
            
            role_obj = device.get("role")
            role_name = None
            if role_obj and isinstance(role_obj, dict):
                role_name = role_obj.get("name")
            elif role_obj:
                role_name = str(role_obj)
            
            device_type_obj = device.get("device_type")
            device_type_model = None
            manufacturer_name = None
            if device_type_obj and isinstance(device_type_obj, dict):
                device_type_model = device_type_obj.get("model")
                manufacturer_obj = device_type_obj.get("manufacturer")
                if manufacturer_obj and isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get("name")
                elif manufacturer_obj:
                    manufacturer_name = str(manufacturer_obj)
            
            # Handle IP addresses
            primary_ip4_obj = device.get("primary_ip4")
            primary_ip6_obj = device.get("primary_ip6")
            primary_ip = None
            if primary_ip4_obj:
                if isinstance(primary_ip4_obj, dict):
                    primary_ip = primary_ip4_obj.get("address")
                else:
                    primary_ip = str(primary_ip4_obj)
            elif primary_ip6_obj:
                if isinstance(primary_ip6_obj, dict):
                    primary_ip = primary_ip6_obj.get("address")
                else:
                    primary_ip = str(primary_ip6_obj)
            
            rack_obj = device.get("rack")
            rack_name = None
            if rack_obj and isinstance(rack_obj, dict):
                rack_name = rack_obj.get("name")
            elif rack_obj:
                rack_name = str(rack_obj)
            
            tenant_obj = device.get("tenant")
            tenant_name = None
            if tenant_obj and isinstance(tenant_obj, dict):
                tenant_name = tenant_obj.get("name")
            elif tenant_obj:
                tenant_name = str(tenant_obj)
            
            device_info = {
                "name": device.get("name", "Unknown"),
                "status": status,
                "site": site_name,
                "role": role_name,
                "device_type": device_type_model,
                "manufacturer": manufacturer_name,
                "primary_ip": primary_ip,
                "rack": rack_name,
                "position": device.get("position"),
                "tenant": tenant_name
            }
            device_list.append(device_info)
        
        result = {
            "count": len(device_list),
            "devices": device_list,
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
            "summary_stats": {
                "total_devices": len(device_list),
                "status_breakdown": status_counts,
                "role_breakdown": role_counts,
                "site_breakdown": site_counts,
                "manufacturer_breakdown": manufacturer_counts,
                "devices_with_ip": len([d for d in device_list if d['primary_ip']]),
                "devices_in_racks": len([d for d in device_list if d['rack']])
            }
        }
        
        logger.info(f"Found {len(device_list)} devices matching criteria. Status breakdown: {status_counts}")
        return result
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        return {
            "count": 0,
            "devices": [],
            "error": str(e),
            "error_type": type(e).__name__,
            "filters_applied": {k: v for k, v in {
                'site_name': site_name,
                'role_name': role_name, 
                'tenant_name': tenant_name,
                'status': status,
                'manufacturer_name': manufacturer_name
            }.items() if v is not None}
        }






