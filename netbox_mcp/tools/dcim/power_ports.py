#!/usr/bin/env python3
"""
DCIM Power Port Management Tools - Read-Only Operations

Enterprise-grade tools for inspecting NetBox power ports and power consumption infrastructure.
Provides read-only access to power port information with comprehensive discovery capabilities.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient
from ...exceptions import NetBoxNotFoundError, NetBoxValidationError

logger = logging.getLogger(__name__)

@mcp_tool(category="dcim")
def netbox_get_power_port_info(
    client: NetBoxClient,
    port_identifier: str,
    device_name: Optional[str] = None,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific power port.
    
    This inspection tool provides comprehensive power port details including
    power specifications, connection status, and related device information.
    
    Args:
        port_identifier: Power port name or ID
        device_name: Device name for port lookup (improves search accuracy)
        site: Site name for device lookup (improves search accuracy)
        client: NetBox client (injected)
        
    Returns:
        Dict containing detailed power port information
        
    Examples:
        # Search by name
        netbox_get_power_port_info("PSU1")
        
        # Search with device context
        netbox_get_power_port_info("PSU1", device_name="server-01")
        
        # Search with full context
        netbox_get_power_port_info("PSU1", device_name="server-01", site="datacenter-1")
    """
    
    # LOOKUP POWER PORT
    try:
        # Try lookup by ID first
        if port_identifier.isdigit():
            port_id = int(port_identifier)
            ports = client.dcim.power_ports.filter(id=port_id)
        else:
            # Search by name with optional device/site context
            filter_params = {"name": port_identifier}
            
            if device_name:
                # Resolve device
                device_filter = {"name": device_name}
                if site:
                    sites = client.dcim.sites.filter(name=site)
                    if sites:
                        site_obj = sites[0]
                        site_id = site_obj.get('id') if isinstance(site_obj, dict) else site_obj.id
                        device_filter["site_id"] = site_id
                
                devices = client.dcim.devices.filter(**device_filter)
                if devices:
                    device_obj = devices[0]
                    device_id = device_obj.get('id') if isinstance(device_obj, dict) else device_obj.id
                    filter_params["device_id"] = device_id
            
            ports = client.dcim.power_ports.filter(**filter_params)
        
        if not ports:
            identifier_desc = f"power port '{port_identifier}'"
            if device_name:
                identifier_desc += f" on device '{device_name}'"
            if site:
                identifier_desc += f" in site '{site}'"
            raise NetBoxNotFoundError(f"Could not find {identifier_desc}")
        
        port = ports[0]
        port_id = port.get('id') if isinstance(port, dict) else port.id
        port_name = port.get('name') if isinstance(port, dict) else port.name
        
    except Exception as e:
        raise NetBoxNotFoundError(f"Failed to find power port: {e}")
    
    # GET CABLE CONNECTION
    cable_info = {}
    try:
        cable_data = port.get('cable') if isinstance(port, dict) else getattr(port, 'cable', None)
        if cable_data:
            cable_info = {
                "id": cable_data.get('id') if isinstance(cable_data, dict) else getattr(cable_data, 'id', None),
                "label": cable_data.get('label') if isinstance(cable_data, dict) else getattr(cable_data, 'label', None),
                "status": cable_data.get('status', {}).get('label') if isinstance(cable_data, dict) else str(getattr(cable_data, 'status', 'N/A')),
                "type": cable_data.get('type', {}).get('label') if isinstance(cable_data, dict) else str(getattr(cable_data, 'type', 'N/A'))
            }
    except Exception as e:
        logger.warning(f"Could not retrieve cable information for port {port_id}: {e}")
    
    # GET DEVICE INFORMATION
    device_info = {}
    try:
        device_data = port.get('device') if isinstance(port, dict) else getattr(port, 'device', None)
        if device_data:
            device_info = {
                "id": device_data.get('id') if isinstance(device_data, dict) else getattr(device_data, 'id', None),
                "name": device_data.get('name') if isinstance(device_data, dict) else getattr(device_data, 'name', None),
                "display": device_data.get('display') if isinstance(device_data, dict) else getattr(device_data, 'display', None),
                "device_type": device_data.get('device_type', {}).get('display') if isinstance(device_data, dict) else str(getattr(device_data, 'device_type', 'N/A'))
            }
    except Exception as e:
        logger.warning(f"Could not retrieve device information for port {port_id}: {e}")
    
    # GET POWER SPECIFICATIONS
    power_specs = {}
    try:
        power_specs = {
            "maximum_draw": port.get('maximum_draw') if isinstance(port, dict) else getattr(port, 'maximum_draw', None),
            "allocated_draw": port.get('allocated_draw') if isinstance(port, dict) else getattr(port, 'allocated_draw', None),
            "type": port.get('type', {}).get('label') if isinstance(port, dict) else str(getattr(port, 'type', 'N/A'))
        }
    except Exception as e:
        logger.warning(f"Could not retrieve power specifications for port {port_id}: {e}")
    
    # RETURN COMPREHENSIVE INFORMATION
    return {
        "success": True,
        "data": {
            "port_id": port_id,
            "name": port_name,
            "device": device_info,
            "power_specifications": power_specs,
            "cable_connection": cable_info if cable_info else None,
            "description": port.get('description') if isinstance(port, dict) else getattr(port, 'description', ''),
            "tags": port.get('tags', []) if isinstance(port, dict) else getattr(port, 'tags', []),
            "mark_connected": port.get('mark_connected') if isinstance(port, dict) else getattr(port, 'mark_connected', False),
            "created": port.get('created') if isinstance(port, dict) else getattr(port, 'created', None),
            "last_updated": port.get('last_updated') if isinstance(port, dict) else getattr(port, 'last_updated', None),
            "url": f"{client.config.url}/dcim/power-ports/{port_id}/"
        }
    }



@mcp_tool(category="dcim")
def netbox_list_all_power_ports(
    client: NetBoxClient,
    device_name: Optional[str] = None,
    site: Optional[str] = None,
    port_type: Optional[str] = None,
    connected: Optional[bool] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    List all power ports with optional filtering.
    
    This bulk discovery tool helps explore and analyze power consumption
    infrastructure across devices and sites.
    
    Args:
        device_name: Filter by device name (optional)
        site: Filter by site name (optional)
        port_type: Filter by port type (optional)
        connected: Filter by connection status (optional)
        limit: Maximum number of ports to return (default: 50)
        client: NetBox client (injected)
        
    Returns:
        Dict containing list of power ports with summary statistics
        
    Examples:
        # List all ports
        netbox_list_all_power_ports()
        
        # Filter by device
        netbox_list_all_power_ports(device_name="server-01")
        
        # Filter by site and connection status
        netbox_list_all_power_ports(site="datacenter-1", connected=True)
    """
    
    filter_params = {}
    
    # RESOLVE SITE FILTER
    if site:
        try:
            sites = client.dcim.sites.filter(name=site)
            if sites:
                site_obj = sites[0]
                site_id = site_obj.get('id') if isinstance(site_obj, dict) else site_obj.id
                filter_params["site_id"] = site_id
            else:
                return {
                    "success": True,
                    "data": {
                        "ports": [],
                        "total_count": 0,
                        "message": f"No ports found - site '{site}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve site filter '{site}': {e}")
    
    # RESOLVE DEVICE FILTER
    if device_name:
        try:
            device_filter = {"name": device_name}
            if "site_id" in filter_params:
                device_filter["site_id"] = filter_params["site_id"]
            
            devices = client.dcim.devices.filter(**device_filter)
            if devices:
                device_obj = devices[0]
                device_id = device_obj.get('id') if isinstance(device_obj, dict) else device_obj.id
                filter_params["device_id"] = device_id
            else:
                return {
                    "success": True,
                    "data": {
                        "ports": [],
                        "total_count": 0,
                        "message": f"No ports found - device '{device_name}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve device filter '{device_name}': {e}")
    
    # ADD OTHER FILTERS
    if port_type:
        filter_params["type"] = port_type
    
    if connected is not None:
        filter_params["cabled"] = connected
    
    # GET POWER PORTS
    try:
        ports = client.dcim.power_ports.filter(**filter_params)
        total_count = len(ports)
        
        # Apply limit
        limited_ports = ports[:limit]
        
        ports_data = []
        power_stats = {"total_draw": 0, "allocated_draw": 0, "connected_count": 0}
        
        for port in limited_ports:
            try:
                # Get basic port info
                port_id = port.get('id') if isinstance(port, dict) else port.id
                port_name = port.get('name') if isinstance(port, dict) else port.name
                
                # Get device info
                device_data = port.get('device') if isinstance(port, dict) else getattr(port, 'device', {})
                device_name = device_data.get('name') if isinstance(device_data, dict) else getattr(device_data, 'name', 'N/A')
                
                # Get site info through device
                site_data = device_data.get('site') if isinstance(device_data, dict) else getattr(device_data, 'site', {})
                site_name = site_data.get('name') if isinstance(site_data, dict) else getattr(site_data, 'name', 'N/A')
                
                # Get power specifications
                max_draw = port.get('maximum_draw') if isinstance(port, dict) else getattr(port, 'maximum_draw', None)
                alloc_draw = port.get('allocated_draw') if isinstance(port, dict) else getattr(port, 'allocated_draw', None)
                
                if max_draw:
                    power_stats["total_draw"] += max_draw
                if alloc_draw:
                    power_stats["allocated_draw"] += alloc_draw
                
                # Check connection status
                cable_data = port.get('cable') if isinstance(port, dict) else getattr(port, 'cable', None)
                is_connected = cable_data is not None
                if is_connected:
                    power_stats["connected_count"] += 1
                
                # Get port type
                type_data = port.get('type') if isinstance(port, dict) else getattr(port, 'type', {})
                port_type_label = type_data.get('label') if isinstance(type_data, dict) else str(type_data)
                
                port_info = {
                    "id": port_id,
                    "name": port_name,
                    "device": device_name,
                    "site": site_name,
                    "type": port_type_label,
                    "power": {
                        "maximum_draw": max_draw,
                        "allocated_draw": alloc_draw
                    },
                    "connected": is_connected,
                    "url": f"{client.config.url}/dcim/power-ports/{port_id}/"
                }
                
                ports_data.append(port_info)
                
            except Exception as e:
                logger.warning(f"Error processing port data: {e}")
                continue
        
        # Build filter description
        filter_description = []
        if device_name:
            filter_description.append(f"device: {device_name}")
        if site:
            filter_description.append(f"site: {site}")
        if port_type:
            filter_description.append(f"type: {port_type}")
        if connected is not None:
            filter_description.append(f"connected: {connected}")
        
        filter_text = f" (filtered by {', '.join(filter_description)})" if filter_description else ""
        
        return {
            "success": True,
            "data": {
                "ports": ports_data,
                "total_count": total_count,
                "returned_count": len(ports_data),
                "limit_applied": limit if total_count > limit else None,
                "filters": filter_text,
                "statistics": {
                    "total_maximum_draw_watts": power_stats["total_draw"],
                    "total_allocated_draw_watts": power_stats["allocated_draw"],
                    "connected_ports": power_stats["connected_count"],
                    "disconnected_ports": len(ports_data) - power_stats["connected_count"],
                    "average_max_draw_per_port": round(power_stats["total_draw"] / len(ports_data), 1) if ports_data and power_stats["total_draw"] > 0 else 0
                }
            }
        }
        
    except Exception as e:
        raise NetBoxValidationError(f"Failed to retrieve power ports: {e}")

