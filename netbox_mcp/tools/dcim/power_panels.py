#!/usr/bin/env python3
"""
DCIM Power Panels Management Tools

This module provides enterprise-grade tools for managing NetBox power panels
including creation, updates, deletion, and information retrieval.
"""

from typing import Dict, Any, Optional, List
import logging

from netbox_mcp.registry import mcp_tool
from netbox_mcp.client import NetBoxClient
from netbox_mcp.exceptions import NetBoxValidationError, NetBoxNotFoundError, NetBoxConflictError

logger = logging.getLogger(__name__)




@mcp_tool(category="dcim")
def netbox_get_power_panel_info(
    client: NetBoxClient,
    panel_identifier: str,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific power panel.
    
    This inspection tool provides comprehensive power panel details including
    power feeds, usage statistics, and connected equipment.
    
    Args:
        panel_identifier: Power panel name or ID
        site: Site name for panel lookup (improves search accuracy)
        client: NetBox client (injected)
        
    Returns:
        Dict containing detailed power panel information
        
    Examples:
        # Search by name
        netbox_get_power_panel_info("PANEL-A-01")
        
        # Search with site context
        netbox_get_power_panel_info("PANEL-A-01", site="datacenter-1")
    """
    
    # LOOKUP POWER PANEL
    try:
        # Try lookup by ID first
        if panel_identifier.isdigit():
            panel_id = int(panel_identifier)
            panels = client.dcim.power_panels.filter(id=panel_id)
        else:
            # Search by name with optional site context
            filter_params = {"name": panel_identifier}
            if site:
                sites = client.dcim.sites.filter(name=site)
                if sites:
                    site_obj = sites[0]
                    site_id = site_obj.get('id') if isinstance(site_obj, dict) else site_obj.id
                    filter_params["site_id"] = site_id
            
            panels = client.dcim.power_panels.filter(**filter_params)
        
        if not panels:
            identifier_desc = f"power panel '{panel_identifier}'"
            if site:
                identifier_desc += f" in site '{site}'"
            raise NetBoxNotFoundError(f"Could not find {identifier_desc}")
        
        panel = panels[0]
        panel_id = panel.get('id') if isinstance(panel, dict) else panel.id
        panel_name = panel.get('name') if isinstance(panel, dict) else panel.name
        
    except Exception as e:
        raise NetBoxNotFoundError(f"Failed to find power panel: {e}")
    
    # GET POWER FEEDS
    power_feeds = []
    feed_count = 0
    try:
        feeds = client.dcim.power_feeds.filter(power_panel_id=panel_id)
        feed_count = len(feeds)
        
        for feed in feeds[:10]:  # Limit to 10 feeds for performance
            feed_info = {
                "id": feed.get('id') if isinstance(feed, dict) else feed.id,
                "name": feed.get('name') if isinstance(feed, dict) else feed.name,
                "status": feed.get('status', {}).get('label') if isinstance(feed, dict) else str(getattr(feed, 'status', 'N/A')),
                "type": feed.get('type', {}).get('label') if isinstance(feed, dict) else str(getattr(feed, 'type', 'N/A')),
                "supply": feed.get('supply', {}).get('label') if isinstance(feed, dict) else str(getattr(feed, 'supply', 'N/A'))
            }
            power_feeds.append(feed_info)
            
    except Exception as e:
        logger.warning(f"Could not retrieve power feeds for panel {panel_id}: {e}")
    
    # GET RELATED INFORMATION
    site_info = {}
    location_info = {}
    rack_group_info = {}
    
    try:
        # Site information
        site_data = panel.get('site') if isinstance(panel, dict) else getattr(panel, 'site', None)
        if site_data:
            site_info = {
                "id": site_data.get('id') if isinstance(site_data, dict) else getattr(site_data, 'id', None),
                "name": site_data.get('name') if isinstance(site_data, dict) else getattr(site_data, 'name', None),
                "display": site_data.get('display') if isinstance(site_data, dict) else getattr(site_data, 'display', None)
            }
        
        # Location information
        location_data = panel.get('location') if isinstance(panel, dict) else getattr(panel, 'location', None)
        if location_data:
            location_info = {
                "id": location_data.get('id') if isinstance(location_data, dict) else getattr(location_data, 'id', None),
                "name": location_data.get('name') if isinstance(location_data, dict) else getattr(location_data, 'name', None),
                "display": location_data.get('display') if isinstance(location_data, dict) else getattr(location_data, 'display', None)
            }
        
        # Rack group information
        rack_group_data = panel.get('rack_group') if isinstance(panel, dict) else getattr(panel, 'rack_group', None)
        if rack_group_data:
            rack_group_info = {
                "id": rack_group_data.get('id') if isinstance(rack_group_data, dict) else getattr(rack_group_data, 'id', None),
                "name": rack_group_data.get('name') if isinstance(rack_group_data, dict) else getattr(rack_group_data, 'name', None),
                "display": rack_group_data.get('display') if isinstance(rack_group_data, dict) else getattr(rack_group_data, 'display', None)
            }
            
    except Exception as e:
        logger.warning(f"Could not retrieve related information for panel {panel_id}: {e}")
    
    # RETURN COMPREHENSIVE INFORMATION
    return {
        "success": True,
        "data": {
            "panel_id": panel_id,
            "name": panel_name,
            "site": site_info,
            "location": location_info,
            "rack_group": rack_group_info,
            "comments": panel.get('comments') if isinstance(panel, dict) else getattr(panel, 'comments', ''),
            "tags": panel.get('tags', []) if isinstance(panel, dict) else getattr(panel, 'tags', []),
            "power_feeds": {
                "count": feed_count,
                "feeds": power_feeds,
                "showing": f"{len(power_feeds)} of {feed_count}" if feed_count > 10 else f"All {feed_count}"
            },
            "created": panel.get('created') if isinstance(panel, dict) else getattr(panel, 'created', None),
            "last_updated": panel.get('last_updated') if isinstance(panel, dict) else getattr(panel, 'last_updated', None),
            "url": f"{client.config.url}/dcim/power-panels/{panel_id}/"
        }
    }


@mcp_tool(category="dcim")
def netbox_list_all_power_panels(
    client: NetBoxClient,
    site: Optional[str] = None,
    location: Optional[str] = None,
    rack_group: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    List all power panels with optional filtering.
    
    This bulk discovery tool helps explore and analyze power distribution
    infrastructure across sites and locations.
    
    Args:
        site: Filter by site name (optional)
        location: Filter by location name (optional)
        rack_group: Filter by rack group name (optional)
        limit: Maximum number of panels to return (default: 50)
        client: NetBox client (injected)
        
    Returns:
        Dict containing list of power panels with summary statistics
        
    Examples:
        # List all panels
        netbox_list_all_power_panels()
        
        # Filter by site
        netbox_list_all_power_panels(site="datacenter-1")
        
        # Filter by location
        netbox_list_all_power_panels(site="datacenter-1", location="Electrical Room A")
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
                        "panels": [],
                        "total_count": 0,
                        "message": f"No panels found - site '{site}' not found"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve site filter '{site}': {e}")
    
    # RESOLVE LOCATION FILTER
    if location and "site_id" in filter_params:
        try:
            locations = client.dcim.locations.filter(site_id=filter_params["site_id"], name=location)
            if locations:
                location_obj = locations[0]
                location_id = location_obj.get('id') if isinstance(location_obj, dict) else location_obj.id
                filter_params["location_id"] = location_id
            else:
                return {
                    "success": True,
                    "data": {
                        "panels": [],
                        "total_count": 0,
                        "message": f"No panels found - location '{location}' not found in site '{site}'"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve location filter '{location}': {e}")
    
    # RESOLVE RACK GROUP FILTER
    if rack_group and "site_id" in filter_params:
        try:
            rack_groups = client.dcim.rack_groups.filter(site_id=filter_params["site_id"], name=rack_group)
            if rack_groups:
                rack_group_obj = rack_groups[0]
                rack_group_id = rack_group_obj.get('id') if isinstance(rack_group_obj, dict) else rack_group_obj.id
                filter_params["rack_group_id"] = rack_group_id
            else:
                return {
                    "success": True,
                    "data": {
                        "panels": [],
                        "total_count": 0,
                        "message": f"No panels found - rack group '{rack_group}' not found in site '{site}'"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not resolve rack group filter '{rack_group}': {e}")
    
    # GET POWER PANELS
    try:
        panels = client.dcim.power_panels.filter(**filter_params)
        total_count = len(panels)
        
        # Apply limit
        limited_panels = panels[:limit]
        
        panels_data = []
        feed_stats = {"total_feeds": 0, "active_feeds": 0}
        
        for panel in limited_panels:
            try:
                # Get basic panel info
                panel_id = panel.get('id') if isinstance(panel, dict) else panel.id
                panel_name = panel.get('name') if isinstance(panel, dict) else panel.name
                
                # Get site info
                site_data = panel.get('site') if isinstance(panel, dict) else getattr(panel, 'site', {})
                site_name = site_data.get('name') if isinstance(site_data, dict) else getattr(site_data, 'name', 'N/A')
                
                # Get location info
                location_data = panel.get('location') if isinstance(panel, dict) else getattr(panel, 'location', None)
                location_name = location_data.get('name') if location_data and isinstance(location_data, dict) else getattr(location_data, 'name', None) if location_data else None
                
                # Get rack group info
                rack_group_data = panel.get('rack_group') if isinstance(panel, dict) else getattr(panel, 'rack_group', None)
                rack_group_name = rack_group_data.get('name') if rack_group_data and isinstance(rack_group_data, dict) else getattr(rack_group_data, 'name', None) if rack_group_data else None
                
                # Count power feeds
                feeds = client.dcim.power_feeds.filter(power_panel_id=panel_id)
                feed_count = len(feeds)
                feed_stats["total_feeds"] += feed_count
                
                # Count active feeds
                active_count = 0
                for feed in feeds:
                    status_obj = feed.get('status') if isinstance(feed, dict) else getattr(feed, 'status', None)
                    if status_obj:
                        status_value = status_obj.get('value') if isinstance(status_obj, dict) else str(status_obj)
                        if status_value == 'active':
                            active_count += 1
                feed_stats["active_feeds"] += active_count
                
                panel_info = {
                    "id": panel_id,
                    "name": panel_name,
                    "site": site_name,
                    "location": location_name,
                    "rack_group": rack_group_name,
                    "power_feeds": {
                        "total": feed_count,
                        "active": active_count
                    },
                    "url": f"{client.config.url}/dcim/power-panels/{panel_id}/"
                }
                
                panels_data.append(panel_info)
                
            except Exception as e:
                logger.warning(f"Error processing panel data: {e}")
                continue
        
        # Build filter description
        filter_description = []
        if site:
            filter_description.append(f"site: {site}")
        if location:
            filter_description.append(f"location: {location}")
        if rack_group:
            filter_description.append(f"rack group: {rack_group}")
        
        filter_text = f" (filtered by {', '.join(filter_description)})" if filter_description else ""
        
        return {
            "success": True,
            "data": {
                "panels": panels_data,
                "total_count": total_count,
                "returned_count": len(panels_data),
                "limit_applied": limit if total_count > limit else None,
                "filters": filter_text,
                "statistics": {
                    "total_power_feeds": feed_stats["total_feeds"],
                    "active_power_feeds": feed_stats["active_feeds"],
                    "average_feeds_per_panel": round(feed_stats["total_feeds"] / len(panels_data), 1) if panels_data else 0
                }
            }
        }
        
    except Exception as e:
        raise NetBoxValidationError(f"Failed to retrieve power panels: {e}")




