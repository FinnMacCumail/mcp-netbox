#!/usr/bin/env python3
"""
DCIM Power Outlet Management Tools - Read-Only Operations

Enterprise-grade tools for inspecting NetBox power outlets and power distribution equipment.
Provides read-only access to power infrastructure with comprehensive discovery capabilities.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient
from ...exceptions import NetBoxNotFoundError, NetBoxValidationError

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_get_power_outlet_info(
    client: NetBoxClient,
    outlet_identifier: str,
    device_name: Optional[str] = None,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific power outlet.
    
    This inspection tool provides comprehensive power outlet details including
    device assignment, power feed connections, and cable information.
    
    Args:
        outlet_identifier: Power outlet name or ID
        device_name: Device name for outlet lookup (improves search accuracy)
        site: Site name for outlet lookup (improves search accuracy)
        client: NetBox client (injected)
        
    Returns:
        Dict containing detailed power outlet information
        
    Examples:
        # Search by name
        netbox_get_power_outlet_info("PDU-A-01")
        
        # Search with device context
        netbox_get_power_outlet_info("PDU-A-01", device_name="PDU-RACK-A-01")
        
        # Search with site context
        netbox_get_power_outlet_info("PDU-A-01", site="datacenter-1")
    """
    
    # LOOKUP POWER OUTLET
    try:
        # Try lookup by ID first
        if outlet_identifier.isdigit():
            outlet_id = int(outlet_identifier)
            outlets = client.dcim.power_outlets.filter(id=outlet_id)
        else:
            # Search by name with optional context
            filter_params = {"name": outlet_identifier}
            
            # Add device context if provided
            if device_name:
                if site:
                    # Find device in specific site
                    sites = client.dcim.sites.filter(name=site)
                    if sites:
                        site_obj = sites[0]
                        site_id = site_obj.get('id') if isinstance(site_obj, dict) else site_obj.id
                        devices = client.dcim.devices.filter(site_id=site_id, name=device_name)
                        if devices:
                            device_obj = devices[0]
                            device_id = device_obj.get('id') if isinstance(device_obj, dict) else device_obj.id
                            filter_params["device_id"] = device_id
                else:
                    # Find device by name only
                    devices = client.dcim.devices.filter(name=device_name)
                    if devices:
                        device_obj = devices[0]
                        device_id = device_obj.get('id') if isinstance(device_obj, dict) else device_obj.id
                        filter_params["device_id"] = device_id
            elif site:
                # Filter by site only
                sites = client.dcim.sites.filter(name=site)
                if sites:
                    site_obj = sites[0]
                    site_id = site_obj.get('id') if isinstance(site_obj, dict) else site_obj.id
                    filter_params["site_id"] = site_id
            
            outlets = client.dcim.power_outlets.filter(**filter_params)
        
        if not outlets:
            identifier_desc = f"power outlet '{outlet_identifier}'"
            if device_name:
                identifier_desc += f" on device '{device_name}'"
            if site:
                identifier_desc += f" in site '{site}'"
            raise NetBoxNotFoundError(f"Could not find {identifier_desc}")
        
        outlet = outlets[0]
        outlet_id = outlet.get('id') if isinstance(outlet, dict) else outlet.id
        outlet_name = outlet.get('name') if isinstance(outlet, dict) else outlet.name
        
    except Exception as e:
        raise NetBoxNotFoundError(f"Failed to find power outlet: {e}")
    
    # GET CABLE CONNECTIONS
    cable_connections = []
    try:
        # Check A-side terminations
        cables_a = client.dcim.cables.filter(termination_a_type="dcim.poweroutlet", termination_a_id=outlet_id)
        for cable in cables_a:
            cable_info = {
                "cable_id": cable.get('id') if isinstance(cable, dict) else cable.id,
                "cable_type": cable.get('type', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'type', 'N/A')),
                "status": cable.get('status', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'status', 'N/A')),
                "termination_side": "A"
            }
            
            # Get B-side termination info
            b_terminations = cable.get('b_terminations', []) if isinstance(cable, dict) else getattr(cable, 'b_terminations', [])
            if b_terminations:
                b_term = b_terminations[0]
                cable_info["connected_to"] = {
                    "type": b_term.get('object_type') if isinstance(b_term, dict) else getattr(b_term, 'object_type', 'N/A'),
                    "name": b_term.get('object', {}).get('name') if isinstance(b_term, dict) else getattr(getattr(b_term, 'object', {}), 'name', 'N/A')
                }
            
            cable_connections.append(cable_info)
        
        # Check B-side terminations
        cables_b = client.dcim.cables.filter(termination_b_type="dcim.poweroutlet", termination_b_id=outlet_id)
        for cable in cables_b:
            cable_info = {
                "cable_id": cable.get('id') if isinstance(cable, dict) else cable.id,
                "cable_type": cable.get('type', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'type', 'N/A')),
                "status": cable.get('status', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'status', 'N/A')),
                "termination_side": "B"
            }
            
            # Get A-side termination info
            a_terminations = cable.get('a_terminations', []) if isinstance(cable, dict) else getattr(cable, 'a_terminations', [])
            if a_terminations:
                a_term = a_terminations[0]
                cable_info["connected_to"] = {
                    "type": a_term.get('object_type') if isinstance(a_term, dict) else getattr(a_term, 'object_type', 'N/A'),
                    "name": a_term.get('object', {}).get('name') if isinstance(a_term, dict) else getattr(getattr(a_term, 'object', {}), 'name', 'N/A')
                }
            
            cable_connections.append(cable_info)
            
    except Exception as e:
        logger.warning(f"Could not retrieve cable connections for outlet {outlet_id}: {e}")
    
    # GET RELATED INFORMATION
    device_info = {}
    site_info = {}
    power_feed_info = {}
    
    try:
        # Device information
        device_data = outlet.get('device') if isinstance(outlet, dict) else getattr(outlet, 'device', None)
        if device_data:
            device_info = {
                "id": device_data.get('id') if isinstance(device_data, dict) else getattr(device_data, 'id', None),
                "name": device_data.get('name') if isinstance(device_data, dict) else getattr(device_data, 'name', None),
                "display": device_data.get('display') if isinstance(device_data, dict) else getattr(device_data, 'display', None)
            }
            
            # Get site from device
            if device_data:
                device_site_data = device_data.get('site') if isinstance(device_data, dict) else getattr(device_data, 'site', None)
                if device_site_data:
                    site_info = {
                        "id": device_site_data.get('id') if isinstance(device_site_data, dict) else getattr(device_site_data, 'id', None),
                        "name": device_site_data.get('name') if isinstance(device_site_data, dict) else getattr(device_site_data, 'name', None),
                        "display": device_site_data.get('display') if isinstance(device_site_data, dict) else getattr(device_site_data, 'display', None)
                    }
        
        # Power feed information
        feed_data = outlet.get('power_feed') if isinstance(outlet, dict) else getattr(outlet, 'power_feed', None)
        if feed_data:
            power_feed_info = {
                "id": feed_data.get('id') if isinstance(feed_data, dict) else getattr(feed_data, 'id', None),
                "name": feed_data.get('name') if isinstance(feed_data, dict) else getattr(feed_data, 'name', None),
                "display": feed_data.get('display') if isinstance(feed_data, dict) else getattr(feed_data, 'display', None)
            }
            
    except Exception as e:
        logger.warning(f"Could not retrieve related information for outlet {outlet_id}: {e}")
    
    # GET SPECIFICATIONS
    specifications = {}
    try:
        specifications = {
            "type": outlet.get('type', {}).get('label') if isinstance(outlet, dict) else str(getattr(outlet, 'type', 'N/A')),
            "feed_leg": outlet.get('feed_leg', {}).get('label') if isinstance(outlet, dict) else str(getattr(outlet, 'feed_leg', None)),
            "mark_connected": outlet.get('mark_connected') if isinstance(outlet, dict) else getattr(outlet, 'mark_connected', False),
            "description": outlet.get('description') if isinstance(outlet, dict) else getattr(outlet, 'description', '')
        }
    except Exception as e:
        logger.warning(f"Could not retrieve specifications for outlet {outlet_id}: {e}")
    
    # RETURN COMPREHENSIVE INFORMATION
    return {
        "success": True,
        "data": {
            "outlet_id": outlet_id,
            "name": outlet_name,
            "device": device_info,
            "site": site_info,
            "power_feed": power_feed_info,
            "specifications": specifications,
            "cable_connections": {
                "count": len(cable_connections),
                "connections": cable_connections
            },
            "tags": outlet.get('tags', []) if isinstance(outlet, dict) else getattr(outlet, 'tags', []),
            "created": outlet.get('created') if isinstance(outlet, dict) else getattr(outlet, 'created', None),
            "last_updated": outlet.get('last_updated') if isinstance(outlet, dict) else getattr(outlet, 'last_updated', None),
            "url": f"{client.config.url}/dcim/power-outlets/{outlet_id}/"
        }
    }


@mcp_tool(category="dcim")
def netbox_list_all_power_outlets(
    client: NetBoxClient,
    site: Optional[str] = None,
    device_name: Optional[str] = None,
    power_feed: Optional[str] = None,
    outlet_type: Optional[str] = None,
    connected_only: bool = False,
    limit: int = 50
) -> Dict[str, Any]:
    """
    List all power outlets with optional filtering.
    
    This bulk discovery tool helps explore and analyze power outlet
    distribution and connectivity across devices and sites.
    
    Args:
        site: Filter by site name (optional)
        device_name: Filter by device name (optional)
        power_feed: Filter by power feed name (optional)
        outlet_type: Filter by outlet type (optional)
        connected_only: Show only outlets with cable connections (optional)
        limit: Maximum number of outlets to return (default: 50)
        client: NetBox client (injected)
        
    Returns:
        Dict containing list of power outlets with connectivity statistics
        
    Examples:
        # List all outlets
        netbox_list_all_power_outlets()
        
        # Filter by site and device
        netbox_list_all_power_outlets(site="datacenter-1", device_name="PDU-RACK-A-01")
        
        # Show only connected outlets
        netbox_list_all_power_outlets(connected_only=True)
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
                        "outlets": [],
                        "total_count": 0,
                        "message": f"No outlets found - site '{site}' not found"
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
                        "outlets": [],
                        "total_count": 0,
                        "message": f"No outlets found - device '{device_name}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve device filter '{device_name}': {e}")
    
    # RESOLVE POWER FEED FILTER
    if power_feed:
        try:
            # Find power feed across all power panels (or in specific site if provided)
            feed_found = False
            if "site_id" in filter_params:
                panels = client.dcim.power_panels.filter(site_id=filter_params["site_id"])
            else:
                panels = client.dcim.power_panels.all()
            
            for panel in panels:
                panel_id = panel.get('id') if isinstance(panel, dict) else panel.id
                feeds = client.dcim.power_feeds.filter(power_panel_id=panel_id, name=power_feed)
                if feeds:
                    feed_obj = feeds[0]
                    feed_id = feed_obj.get('id') if isinstance(feed_obj, dict) else feed_obj.id
                    filter_params["power_feed_id"] = feed_id
                    feed_found = True
                    break
            
            if not feed_found:
                return {
                    "success": True,
                    "data": {
                        "outlets": [],
                        "total_count": 0,
                        "message": f"No outlets found - power feed '{power_feed}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve power feed filter '{power_feed}': {e}")
    
    # ADD TYPE FILTER
    if outlet_type:
        filter_params["type"] = outlet_type
    
    # GET POWER OUTLETS
    try:
        outlets = client.dcim.power_outlets.filter(**filter_params)
        
        # Filter connected outlets if requested
        if connected_only:
            connected_outlets = []
            for outlet in outlets:
                outlet_id = outlet.get('id') if isinstance(outlet, dict) else outlet.id
                
                # Check for cable connections
                cables_a = client.dcim.cables.filter(termination_a_type="dcim.poweroutlet", termination_a_id=outlet_id)
                cables_b = client.dcim.cables.filter(termination_b_type="dcim.poweroutlet", termination_b_id=outlet_id)
                
                if cables_a or cables_b:
                    connected_outlets.append(outlet)
            
            outlets = connected_outlets
        
        total_count = len(outlets)
        
        # Apply limit
        limited_outlets = outlets[:limit]
        
        outlets_data = []
        connection_stats = {
            "total_outlets": total_count,
            "connected_outlets": 0,
            "outlet_count_by_type": {},
            "outlet_count_by_device": {}
        }
        
        for outlet in limited_outlets:
            try:
                # Get basic outlet info
                outlet_id = outlet.get('id') if isinstance(outlet, dict) else outlet.id
                outlet_name = outlet.get('name') if isinstance(outlet, dict) else outlet.name
                
                # Get device info
                device_data = outlet.get('device') if isinstance(outlet, dict) else getattr(outlet, 'device', {})
                device_name = device_data.get('name') if isinstance(device_data, dict) else getattr(device_data, 'name', 'N/A')
                
                # Get site info (from device)
                site_name = "N/A"
                if device_data:
                    device_site_data = device_data.get('site') if isinstance(device_data, dict) else getattr(device_data, 'site', None)
                    if device_site_data:
                        site_name = device_site_data.get('name') if isinstance(device_site_data, dict) else getattr(device_site_data, 'name', 'N/A')
                
                # Get power feed info
                feed_data = outlet.get('power_feed') if isinstance(outlet, dict) else getattr(outlet, 'power_feed', None)
                feed_name = feed_data.get('name') if feed_data and isinstance(feed_data, dict) else getattr(feed_data, 'name', None) if feed_data else None
                
                # Get specifications
                type_obj = outlet.get('type') if isinstance(outlet, dict) else getattr(outlet, 'type', None)
                type_value = type_obj.get('label') if isinstance(type_obj, dict) else str(type_obj) if type_obj else 'N/A'
                
                feed_leg_obj = outlet.get('feed_leg') if isinstance(outlet, dict) else getattr(outlet, 'feed_leg', None)
                feed_leg_value = feed_leg_obj.get('label') if isinstance(feed_leg_obj, dict) else str(feed_leg_obj) if feed_leg_obj else None
                
                mark_connected = outlet.get('mark_connected') if isinstance(outlet, dict) else getattr(outlet, 'mark_connected', False)
                
                # Check for actual cable connections
                cables_a = client.dcim.cables.filter(termination_a_type="dcim.poweroutlet", termination_a_id=outlet_id)
                cables_b = client.dcim.cables.filter(termination_b_type="dcim.poweroutlet", termination_b_id=outlet_id)
                cable_count = len(cables_a) + len(cables_b)
                
                if cable_count > 0:
                    connection_stats["connected_outlets"] += 1
                
                # Update statistics
                connection_stats["outlet_count_by_type"][type_value] = connection_stats["outlet_count_by_type"].get(type_value, 0) + 1
                connection_stats["outlet_count_by_device"][device_name] = connection_stats["outlet_count_by_device"].get(device_name, 0) + 1
                
                outlet_info = {
                    "id": outlet_id,
                    "name": outlet_name,
                    "device": device_name,
                    "site": site_name,
                    "power_feed": feed_name,
                    "specifications": {
                        "type": type_value,
                        "feed_leg": feed_leg_value,
                        "mark_connected": mark_connected
                    },
                    "cable_connections": cable_count,
                    "url": f"{client.config.url}/dcim/power-outlets/{outlet_id}/"
                }
                
                outlets_data.append(outlet_info)
                
            except Exception as e:
                logger.warning(f"Error processing outlet data: {e}")
                continue
        
        # Calculate connection percentage
        connection_percentage = round((connection_stats["connected_outlets"] / connection_stats["total_outlets"]) * 100, 1) if connection_stats["total_outlets"] > 0 else 0
        
        # Build filter description
        filter_description = []
        if site:
            filter_description.append(f"site: {site}")
        if device_name:
            filter_description.append(f"device: {device_name}")
        if power_feed:
            filter_description.append(f"power feed: {power_feed}")
        if outlet_type:
            filter_description.append(f"type: {outlet_type}")
        if connected_only:
            filter_description.append("connected only")
        
        filter_text = f" (filtered by {', '.join(filter_description)})" if filter_description else ""
        
        return {
            "success": True,
            "data": {
                "outlets": outlets_data,
                "total_count": total_count,
                "returned_count": len(outlets_data),
                "limit_applied": limit if total_count > limit else None,
                "filters": filter_text,
                "connection_statistics": {
                    "total_outlets": connection_stats["total_outlets"],
                    "connected_outlets": connection_stats["connected_outlets"],
                    "connection_percentage": connection_percentage,
                    "outlet_count_by_type": connection_stats["outlet_count_by_type"],
                    "outlet_count_by_device": connection_stats["outlet_count_by_device"]
                }
            }
        }
        
    except Exception as e:
        raise NetBoxValidationError(f"Failed to retrieve power outlets: {e}")