#!/usr/bin/env python3
"""
DCIM Power Feed Management Tools - Read-Only Operations

Enterprise-grade tools for inspecting NetBox power feeds and power distribution infrastructure.
Provides read-only access to power feed information with comprehensive discovery capabilities.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient
from ...exceptions import NetBoxNotFoundError, NetBoxValidationError

logger = logging.getLogger(__name__)

@mcp_tool(category="dcim")
def netbox_get_power_feed_info(
    client: NetBoxClient,
    feed_identifier: str,
    power_panel: Optional[str] = None,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific power feed.
    
    This inspection tool provides comprehensive power feed details including
    power consumption, connections, and utilization statistics.
    
    Args:
        feed_identifier: Power feed name or ID
        power_panel: Power panel name for feed lookup (improves search accuracy)
        site: Site name for feed lookup (improves search accuracy)
        client: NetBox client (injected)
        
    Returns:
        Dict containing detailed power feed information
        
    Examples:
        # Search by name
        netbox_get_power_feed_info("FEED-A-01")
        
        # Search with panel context
        netbox_get_power_feed_info("FEED-A-01", power_panel="PANEL-A-01")
        
        # Search with site context
        netbox_get_power_feed_info("FEED-A-01", site="datacenter-1")
    """
    
    # LOOKUP POWER FEED
    try:
        # Try lookup by ID first
        if feed_identifier.isdigit():
            feed_id = int(feed_identifier)
            feeds = client.dcim.power_feeds.filter(id=feed_id)
        else:
            # Search by name with optional context
            filter_params = {"name": feed_identifier}
            
            # Add power panel context if provided
            if power_panel:
                if site:
                    # Find panel in specific site
                    sites = client.dcim.sites.filter(name=site)
                    if sites:
                        site_obj = sites[0]
                        site_id = site_obj.get('id') if isinstance(site_obj, dict) else site_obj.id
                        panels = client.dcim.power_panels.filter(site_id=site_id, name=power_panel)
                        if panels:
                            panel_obj = panels[0]
                            panel_id = panel_obj.get('id') if isinstance(panel_obj, dict) else panel_obj.id
                            filter_params["power_panel_id"] = panel_id
                else:
                    # Find panel by name only
                    panels = client.dcim.power_panels.filter(name=power_panel)
                    if panels:
                        panel_obj = panels[0]
                        panel_id = panel_obj.get('id') if isinstance(panel_obj, dict) else panel_obj.id
                        filter_params["power_panel_id"] = panel_id
            
            feeds = client.dcim.power_feeds.filter(**filter_params)
        
        if not feeds:
            identifier_desc = f"power feed '{feed_identifier}'"
            if power_panel:
                identifier_desc += f" in power panel '{power_panel}'"
            if site:
                identifier_desc += f" in site '{site}'"
            raise NetBoxNotFoundError(f"Could not find {identifier_desc}")
        
        feed = feeds[0]
        feed_id = feed.get('id') if isinstance(feed, dict) else feed.id
        feed_name = feed.get('name') if isinstance(feed, dict) else feed.name
        
    except Exception as e:
        raise NetBoxNotFoundError(f"Failed to find power feed: {e}")
    
    # GET POWER OUTLETS
    power_outlets = []
    outlet_count = 0
    try:
        outlets = client.dcim.power_outlets.filter(power_feed_id=feed_id)
        outlet_count = len(outlets)
        
        for outlet in outlets[:10]:  # Limit to 10 outlets for performance
            outlet_info = {
                "id": outlet.get('id') if isinstance(outlet, dict) else outlet.id,
                "name": outlet.get('name') if isinstance(outlet, dict) else outlet.name,
                "type": outlet.get('type', {}).get('label') if isinstance(outlet, dict) else str(getattr(outlet, 'type', 'N/A')),
                "device": outlet.get('device', {}).get('name') if isinstance(outlet, dict) else getattr(getattr(outlet, 'device', {}), 'name', 'N/A')
            }
            power_outlets.append(outlet_info)
            
    except Exception as e:
        logger.warning(f"Could not retrieve power outlets for feed {feed_id}: {e}")
    
    # GET CABLE CONNECTIONS
    connected_devices = []
    try:
        # Get cables connected to this power feed
        cables = client.dcim.cables.filter(termination_a_type="dcim.powerfeed", termination_a_id=feed_id)
        for cable in cables[:5]:  # Limit to 5 connections
            cable_info = {
                "cable_id": cable.get('id') if isinstance(cable, dict) else cable.id,
                "cable_type": cable.get('type', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'type', 'N/A')),
                "status": cable.get('status', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'status', 'N/A'))
            }
            connected_devices.append(cable_info)
            
        # Also check reverse connections (B-side terminations)
        cables_b = client.dcim.cables.filter(termination_b_type="dcim.powerfeed", termination_b_id=feed_id)
        for cable in cables_b[:5]:
            if len(connected_devices) >= 5:
                break
            cable_info = {
                "cable_id": cable.get('id') if isinstance(cable, dict) else cable.id,
                "cable_type": cable.get('type', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'type', 'N/A')),
                "status": cable.get('status', {}).get('label') if isinstance(cable, dict) else str(getattr(cable, 'status', 'N/A'))
            }
            connected_devices.append(cable_info)
            
    except Exception as e:
        logger.warning(f"Could not retrieve cable connections for feed {feed_id}: {e}")
    
    # GET RELATED INFORMATION
    power_panel_info = {}
    site_info = {}
    rack_info = {}
    
    try:
        # Power panel information
        panel_data = feed.get('power_panel') if isinstance(feed, dict) else getattr(feed, 'power_panel', None)
        if panel_data:
            power_panel_info = {
                "id": panel_data.get('id') if isinstance(panel_data, dict) else getattr(panel_data, 'id', None),
                "name": panel_data.get('name') if isinstance(panel_data, dict) else getattr(panel_data, 'name', None),
                "display": panel_data.get('display') if isinstance(panel_data, dict) else getattr(panel_data, 'display', None)
            }
            
            # Get site from power panel
            if panel_data:
                panel_site_data = panel_data.get('site') if isinstance(panel_data, dict) else getattr(panel_data, 'site', None)
                if panel_site_data:
                    site_info = {
                        "id": panel_site_data.get('id') if isinstance(panel_site_data, dict) else getattr(panel_site_data, 'id', None),
                        "name": panel_site_data.get('name') if isinstance(panel_site_data, dict) else getattr(panel_site_data, 'name', None),
                        "display": panel_site_data.get('display') if isinstance(panel_site_data, dict) else getattr(panel_site_data, 'display', None)
                    }
        
        # Rack information
        rack_data = feed.get('rack') if isinstance(feed, dict) else getattr(feed, 'rack', None)
        if rack_data:
            rack_info = {
                "id": rack_data.get('id') if isinstance(rack_data, dict) else getattr(rack_data, 'id', None),
                "name": rack_data.get('name') if isinstance(rack_data, dict) else getattr(rack_data, 'name', None),
                "display": rack_data.get('display') if isinstance(rack_data, dict) else getattr(rack_data, 'display', None)
            }
            
    except Exception as e:
        logger.warning(f"Could not retrieve related information for feed {feed_id}: {e}")
    
    # GET SPECIFICATIONS
    specifications = {}
    try:
        specifications = {
            "status": feed.get('status', {}).get('label') if isinstance(feed, dict) else str(getattr(feed, 'status', 'N/A')),
            "type": feed.get('type', {}).get('label') if isinstance(feed, dict) else str(getattr(feed, 'type', 'N/A')),
            "supply": feed.get('supply', {}).get('label') if isinstance(feed, dict) else str(getattr(feed, 'supply', 'N/A')),
            "phase": feed.get('phase', {}).get('label') if isinstance(feed, dict) else str(getattr(feed, 'phase', 'N/A')),
            "voltage": feed.get('voltage') if isinstance(feed, dict) else getattr(feed, 'voltage', None),
            "amperage": feed.get('amperage') if isinstance(feed, dict) else getattr(feed, 'amperage', None),
            "max_utilization": feed.get('max_utilization') if isinstance(feed, dict) else getattr(feed, 'max_utilization', None)
        }
    except Exception as e:
        logger.warning(f"Could not retrieve specifications for feed {feed_id}: {e}")
    
    # CALCULATE UTILIZATION METRICS
    utilization_metrics = {}
    try:
        if specifications.get('voltage') and specifications.get('amperage'):
            total_capacity_watts = specifications['voltage'] * specifications['amperage']
            utilization_metrics["total_capacity_watts"] = total_capacity_watts
            utilization_metrics["total_capacity_kw"] = round(total_capacity_watts / 1000, 2)
            
            if specifications.get('max_utilization'):
                safe_capacity_watts = total_capacity_watts * (specifications['max_utilization'] / 100)
                utilization_metrics["safe_capacity_watts"] = round(safe_capacity_watts, 2)
                utilization_metrics["safe_capacity_kw"] = round(safe_capacity_watts / 1000, 2)
    except Exception as e:
        logger.warning(f"Could not calculate utilization metrics: {e}")
    
    # RETURN COMPREHENSIVE INFORMATION
    return {
        "success": True,
        "data": {
            "feed_id": feed_id,
            "name": feed_name,
            "power_panel": power_panel_info,
            "site": site_info,
            "rack": rack_info,
            "specifications": specifications,
            "utilization_metrics": utilization_metrics,
            "power_outlets": {
                "count": outlet_count,
                "outlets": power_outlets,
                "showing": f"{len(power_outlets)} of {outlet_count}" if outlet_count > 10 else f"All {outlet_count}"
            },
            "connections": {
                "count": len(connected_devices),
                "devices": connected_devices
            },
            "comments": feed.get('comments') if isinstance(feed, dict) else getattr(feed, 'comments', ''),
            "tags": feed.get('tags', []) if isinstance(feed, dict) else getattr(feed, 'tags', []),
            "created": feed.get('created') if isinstance(feed, dict) else getattr(feed, 'created', None),
            "last_updated": feed.get('last_updated') if isinstance(feed, dict) else getattr(feed, 'last_updated', None),
            "url": f"{client.config.url}/dcim/power-feeds/{feed_id}/"
        }
    }



@mcp_tool(category="dcim")
def netbox_list_all_power_feeds(
    client: NetBoxClient,
    site: Optional[str] = None,
    power_panel: Optional[str] = None,
    rack: Optional[str] = None,
    status: Optional[str] = None,
    feed_type: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    List all power feeds with optional filtering.
    
    This bulk discovery tool helps explore and analyze power distribution
    infrastructure and capacity planning.
    
    Args:
        site: Filter by site name (optional)
        power_panel: Filter by power panel name (optional)
        rack: Filter by rack name (optional)
        status: Filter by status (planned, active, offline, decommissioning, optional)
        feed_type: Filter by type (primary, redundant, optional)
        limit: Maximum number of feeds to return (default: 50)
        client: NetBox client (injected)
        
    Returns:
        Dict containing list of power feeds with capacity statistics
        
    Examples:
        # List all feeds
        netbox_list_all_power_feeds()
        
        # Filter by site and status
        netbox_list_all_power_feeds(site="datacenter-1", status="active")
        
        # Filter by power panel
        netbox_list_all_power_feeds(power_panel="PANEL-A-01")
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
                        "feeds": [],
                        "total_count": 0,
                        "message": f"No feeds found - site '{site}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve site filter '{site}': {e}")
    
    # RESOLVE POWER PANEL FILTER
    if power_panel:
        try:
            panel_filter = {"name": power_panel}
            if "site_id" in filter_params:
                panel_filter["site_id"] = filter_params["site_id"]
                
            panels = client.dcim.power_panels.filter(**panel_filter)
            if panels:
                panel_obj = panels[0]
                panel_id = panel_obj.get('id') if isinstance(panel_obj, dict) else panel_obj.id
                filter_params["power_panel_id"] = panel_id
            else:
                return {
                    "success": True,
                    "data": {
                        "feeds": [],
                        "total_count": 0,
                        "message": f"No feeds found - power panel '{power_panel}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve power panel filter '{power_panel}': {e}")
    
    # RESOLVE RACK FILTER
    if rack and "site_id" in filter_params:
        try:
            racks = client.dcim.racks.filter(site_id=filter_params["site_id"], name=rack)
            if racks:
                rack_obj = racks[0]
                rack_id = rack_obj.get('id') if isinstance(rack_obj, dict) else rack_obj.id
                filter_params["rack_id"] = rack_id
            else:
                return {
                    "success": True,
                    "data": {
                        "feeds": [],
                        "total_count": 0,
                        "message": f"No feeds found - rack '{rack}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve rack filter '{rack}': {e}")
    
    # ADD STATUS AND TYPE FILTERS
    if status:
        filter_params["status"] = status
    
    if feed_type:
        filter_params["type"] = feed_type
    
    # GET POWER FEEDS
    try:
        feeds = client.dcim.power_feeds.filter(**filter_params)
        total_count = len(feeds)
        
        # Apply limit
        limited_feeds = feeds[:limit]
        
        feeds_data = []
        capacity_stats = {
            "total_voltage": 0,
            "total_amperage": 0,
            "total_capacity_kw": 0,
            "feed_count_by_status": {},
            "feed_count_by_type": {}
        }
        
        for feed in limited_feeds:
            try:
                # Get basic feed info
                feed_id = feed.get('id') if isinstance(feed, dict) else feed.id
                feed_name = feed.get('name') if isinstance(feed, dict) else feed.name
                
                # Get power panel info
                panel_data = feed.get('power_panel') if isinstance(feed, dict) else getattr(feed, 'power_panel', {})
                panel_name = panel_data.get('name') if isinstance(panel_data, dict) else getattr(panel_data, 'name', 'N/A')
                
                # Get site info (from power panel)
                site_name = "N/A"
                if panel_data:
                    panel_site_data = panel_data.get('site') if isinstance(panel_data, dict) else getattr(panel_data, 'site', None)
                    if panel_site_data:
                        site_name = panel_site_data.get('name') if isinstance(panel_site_data, dict) else getattr(panel_site_data, 'name', 'N/A')
                
                # Get rack info
                rack_data = feed.get('rack') if isinstance(feed, dict) else getattr(feed, 'rack', None)
                rack_name = rack_data.get('name') if rack_data and isinstance(rack_data, dict) else getattr(rack_data, 'name', None) if rack_data else None
                
                # Get specifications
                status_obj = feed.get('status') if isinstance(feed, dict) else getattr(feed, 'status', None)
                status_value = status_obj.get('label') if isinstance(status_obj, dict) else str(status_obj) if status_obj else 'N/A'
                
                type_obj = feed.get('type') if isinstance(feed, dict) else getattr(feed, 'type', None)
                type_value = type_obj.get('label') if isinstance(type_obj, dict) else str(type_obj) if type_obj else 'N/A'
                
                supply_obj = feed.get('supply') if isinstance(feed, dict) else getattr(feed, 'supply', None)
                supply_value = supply_obj.get('label') if isinstance(supply_obj, dict) else str(supply_obj) if supply_obj else 'N/A'
                
                phase_obj = feed.get('phase') if isinstance(feed, dict) else getattr(feed, 'phase', None)
                phase_value = phase_obj.get('label') if isinstance(phase_obj, dict) else str(phase_obj) if phase_obj else 'N/A'
                
                voltage = feed.get('voltage') if isinstance(feed, dict) else getattr(feed, 'voltage', None)
                amperage = feed.get('amperage') if isinstance(feed, dict) else getattr(feed, 'amperage', None)
                max_utilization = feed.get('max_utilization') if isinstance(feed, dict) else getattr(feed, 'max_utilization', None)
                
                # Calculate capacity
                capacity_kw = None
                if voltage and amperage:
                    capacity_watts = voltage * amperage
                    capacity_kw = round(capacity_watts / 1000, 2)
                    capacity_stats["total_capacity_kw"] += capacity_kw
                
                if voltage:
                    capacity_stats["total_voltage"] += voltage
                if amperage:
                    capacity_stats["total_amperage"] += amperage
                
                # Count by status and type
                capacity_stats["feed_count_by_status"][status_value] = capacity_stats["feed_count_by_status"].get(status_value, 0) + 1
                capacity_stats["feed_count_by_type"][type_value] = capacity_stats["feed_count_by_type"].get(type_value, 0) + 1
                
                # Count power outlets
                outlet_count = 0
                try:
                    outlets = client.dcim.power_outlets.filter(power_feed_id=feed_id)
                    outlet_count = len(outlets)
                except Exception:
                    pass
                
                feed_info = {
                    "id": feed_id,
                    "name": feed_name,
                    "power_panel": panel_name,
                    "site": site_name,
                    "rack": rack_name,
                    "status": status_value,
                    "type": type_value,
                    "supply": supply_value,
                    "phase": phase_value,
                    "specifications": {
                        "voltage": voltage,
                        "amperage": amperage,
                        "capacity_kw": capacity_kw,
                        "max_utilization": max_utilization
                    },
                    "power_outlets": outlet_count,
                    "url": f"{client.config.url}/dcim/power-feeds/{feed_id}/"
                }
                
                feeds_data.append(feed_info)
                
            except Exception as e:
                logger.warning(f"Error processing feed data: {e}")
                continue
        
        # Calculate averages
        if feeds_data:
            capacity_stats["average_voltage"] = round(capacity_stats["total_voltage"] / len(feeds_data), 1) if capacity_stats["total_voltage"] > 0 else 0
            capacity_stats["average_amperage"] = round(capacity_stats["total_amperage"] / len(feeds_data), 1) if capacity_stats["total_amperage"] > 0 else 0
            capacity_stats["average_capacity_kw"] = round(capacity_stats["total_capacity_kw"] / len(feeds_data), 2) if capacity_stats["total_capacity_kw"] > 0 else 0
        
        # Build filter description
        filter_description = []
        if site:
            filter_description.append(f"site: {site}")
        if power_panel:
            filter_description.append(f"power panel: {power_panel}")
        if rack:
            filter_description.append(f"rack: {rack}")
        if status:
            filter_description.append(f"status: {status}")
        if feed_type:
            filter_description.append(f"type: {feed_type}")
        
        filter_text = f" (filtered by {', '.join(filter_description)})" if filter_description else ""
        
        return {
            "success": True,
            "data": {
                "feeds": feeds_data,
                "total_count": total_count,
                "returned_count": len(feeds_data),
                "limit_applied": limit if total_count > limit else None,
                "filters": filter_text,
                "capacity_statistics": {
                    "total_capacity_kw": round(capacity_stats["total_capacity_kw"], 2),
                    "average_voltage": capacity_stats.get("average_voltage", 0),
                    "average_amperage": capacity_stats.get("average_amperage", 0),
                    "average_capacity_kw": capacity_stats.get("average_capacity_kw", 0),
                    "feed_count_by_status": capacity_stats["feed_count_by_status"],
                    "feed_count_by_type": capacity_stats["feed_count_by_type"]
                }
            }
        }
        
    except Exception as e:
        raise NetBoxValidationError(f"Failed to retrieve power feeds: {e}")

