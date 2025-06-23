#!/usr/bin/env python3
"""
IPAM VLAN Management Tools

High-level tools for managing NetBox VLANs and VLAN assignments.
"""

from typing import Dict, List, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="ipam")
def netbox_create_vlan(
    client: NetBoxClient,
    name: str,
    vid: int,
    status: str = "active",
    description: Optional[str] = None,
    site: Optional[str] = None,
    group: Optional[str] = None,
    tenant: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new VLAN in NetBox IPAM.
    
    Args:
        client: NetBoxClient instance (injected)
        name: VLAN name
        vid: VLAN ID (1-4094)
        status: VLAN status (active, reserved, deprecated)
        description: Optional description
        site: Optional site name or slug
        group: Optional VLAN group name
        tenant: Optional tenant name or slug
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created VLAN information or error details
        
    Example:
        netbox_create_vlan("Management", 100, status="active", confirm=True)
    """
    try:
        if not name or not vid:
            return {
                "success": False,
                "error": "VLAN name and VID are required",
                "error_type": "ValidationError"
            }
        
        if not (1 <= vid <= 4094):
            return {
                "success": False,
                "error": "VID must be between 1 and 4094",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating VLAN: {name} (VID: {vid})")
        
        # Build VLAN data
        vlan_data = {
            "name": name,
            "vid": vid,
            "status": status
        }
        
        if description:
            vlan_data["description"] = description
        if site:
            vlan_data["site"] = site
        if group:
            vlan_data["group"] = group
        if tenant:
            vlan_data["tenant"] = tenant
        
        # Use dynamic API with safety
        result = client.ipam.vlans.create(confirm=confirm, **vlan_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "vlan",
            "vlan": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create VLAN {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="ipam")
def netbox_find_available_vlan_id(
    client: NetBoxClient,
    site: Optional[str] = None,
    group: Optional[str] = None,
    start_vid: int = 1,
    end_vid: int = 4094
) -> Dict[str, Any]:
    """
    Find available VLAN IDs in a range.
    
    Args:
        client: NetBoxClient instance (injected)
        site: Optional site name or slug to filter VLANs
        group: Optional VLAN group name to filter VLANs
        start_vid: Starting VLAN ID (default: 1)
        end_vid: Ending VLAN ID (default: 4094)
        
    Returns:
        Available VLAN IDs or error details
        
    Example:
        netbox_find_available_vlan_id(site="main-dc", start_vid=100, end_vid=200)
    """
    try:
        if not (1 <= start_vid <= 4094) or not (1 <= end_vid <= 4094):
            return {
                "success": False,
                "error": "VLAN IDs must be between 1 and 4094",
                "error_type": "ValidationError"
            }
        
        if start_vid > end_vid:
            return {
                "success": False,
                "error": "start_vid must be less than or equal to end_vid",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Finding available VLAN IDs between {start_vid} and {end_vid}")
        
        # Build filter
        vlan_filter = {}
        if site:
            vlan_filter["site"] = site
        if group:
            vlan_filter["group"] = group
        
        # Get existing VLANs
        existing_vlans = client.ipam.vlans.filter(**vlan_filter)
        used_vids = {vlan["vid"] for vlan in existing_vlans}
        
        # Find available VIDs
        available_vids = []
        for vid in range(start_vid, end_vid + 1):
            if vid not in used_vids:
                available_vids.append(vid)
        
        return {
            "success": True,
            "available_vids": available_vids,
            "count": len(available_vids),
            "range": {"start": start_vid, "end": end_vid},
            "filter": vlan_filter
        }
        
    except Exception as e:
        logger.error(f"Failed to find available VLAN IDs: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }