#!/usr/bin/env python3
"""
IPAM-Specific MCP Tools Extension

Additional MCP tools specifically designed for comprehensive IPAM management.
These tools can be added to server.py or used as reference for IPAM operations.
"""

from typing import Dict, List, Optional, Any
from netbox_mcp.server import NetBoxClientManager
from netbox_mcp.registry import mcp_tool
import logging

logger = logging.getLogger(__name__)


# ========================================
# IP ADDRESS MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="ipam")
def netbox_create_ip_address(
    address: str,
    status: str = "active",
    description: Optional[str] = None,
    vrf: Optional[str] = None,
    tenant: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new IP address in NetBox IPAM.
    
    Args:
        address: IP address with prefix (e.g., "192.168.1.10/24")
        status: IP address status (active, reserved, deprecated, dhcp)
        description: Optional description
        vrf: Optional VRF name
        tenant: Optional tenant name
        confirm: Must be True to execute (safety mechanism)
    
    Returns:
        Created IP address information or error details
        
    Example:
        netbox_create_ip_address("192.168.1.10/24", status="active", confirm=True)
    """
    try:
        if not address:
            return {
                "success": False,
                "error": "IP address is required",
                "error_type": "ValidationError"
            }
        
        client = NetBoxClientManager.get_client()
        logger.info(f"Creating IP address: {address}")
        
        # Build IP data
        ip_data = {
            "address": address,
            "status": status
        }
        
        if description:
            ip_data["description"] = description
        if vrf:
            ip_data["vrf"] = vrf
        if tenant:
            ip_data["tenant"] = tenant
        
        # Use dynamic API with safety
        result = client.ipam.ip_addresses.create(confirm=confirm, **ip_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "ip_address",
            "ip_address": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create IP address {address}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="ipam")
def netbox_find_available_ip(
    prefix: str,
    count: int = 1
) -> Dict[str, Any]:
    """
    Find available IP addresses within a prefix.
    
    Args:
        prefix: Network prefix (e.g., "192.168.1.0/24")
        count: Number of available IPs to find
        
    Returns:
        List of available IP addresses
        
    Example:
        netbox_find_available_ip("192.168.1.0/24", count=5)
    """
    try:
        client = NetBoxClientManager.get_client()
        logger.info(f"Finding {count} available IPs in prefix: {prefix}")
        
        # Find the prefix object first
        prefixes = client.ipam.prefixes.filter(prefix=prefix)
        
        if not prefixes:
            return {
                "success": False,
                "error": f"Prefix '{prefix}' not found",
                "error_type": "PrefixNotFound"
            }
        
        prefix_obj = prefixes[0]
        prefix_id = prefix_obj["id"]
        
        # Use NetBox's available-ips endpoint
        # This requires direct API call as it's a special endpoint
        available_ips = client.api.ipam.prefixes.get(prefix_id).available_ips.list()
        
        # Limit results
        if count and len(available_ips) > count:
            available_ips = available_ips[:count]
        
        return {
            "success": True,
            "prefix": prefix,
            "available_count": len(available_ips),
            "available_ips": [str(ip) for ip in available_ips]
        }
        
    except Exception as e:
        logger.error(f"Failed to find available IPs in {prefix}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="ipam")
def netbox_get_ip_usage(
    prefix: str
) -> Dict[str, Any]:
    """
    Get IP address usage statistics for a prefix.
    
    Args:
        prefix: Network prefix (e.g., "192.168.1.0/24")
        
    Returns:
        Usage statistics including total, used, available IPs
        
    Example:
        netbox_get_ip_usage("192.168.1.0/24")
    """
    try:
        client = NetBoxClientManager.get_client()
        logger.info(f"Getting IP usage for prefix: {prefix}")
        
        # Find the prefix
        prefixes = client.ipam.prefixes.filter(prefix=prefix)
        
        if not prefixes:
            return {
                "success": False,
                "error": f"Prefix '{prefix}' not found",
                "error_type": "PrefixNotFound"
            }
        
        prefix_obj = prefixes[0]
        
        # Calculate usage
        prefix_size = prefix_obj.get("_depth", 0)  # Number of host bits
        total_hosts = 2 ** (32 - int(prefix.split('/')[1])) - 2  # Exclude network and broadcast
        
        # Get used IPs in this prefix
        used_ips = client.ipam.ip_addresses.filter(parent=prefix)
        used_count = len(used_ips)
        available_count = total_hosts - used_count
        usage_percent = (used_count / total_hosts * 100) if total_hosts > 0 else 0
        
        return {
            "success": True,
            "prefix": prefix,
            "total_addresses": total_hosts,
            "used_addresses": used_count,
            "available_addresses": available_count,
            "usage_percentage": round(usage_percent, 2),
            "prefix_details": prefix_obj
        }
        
    except Exception as e:
        logger.error(f"Failed to get IP usage for {prefix}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# PREFIX MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="ipam")
def netbox_create_prefix(
    prefix: str,
    status: str = "active",
    role: Optional[str] = None,
    vrf: Optional[str] = None,
    site: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new IP prefix in NetBox IPAM.
    
    Args:
        prefix: Network prefix (e.g., "192.168.1.0/24")
        status: Prefix status (active, reserved, deprecated)
        role: Optional prefix role
        vrf: Optional VRF name
        site: Optional site name
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created prefix information or error details
        
    Example:
        netbox_create_prefix("192.168.1.0/24", status="active", confirm=True)
    """
    try:
        if not prefix:
            return {
                "success": False,
                "error": "Prefix is required",
                "error_type": "ValidationError"
            }
        
        client = NetBoxClientManager.get_client()
        logger.info(f"Creating prefix: {prefix}")
        
        # Build prefix data
        prefix_data = {
            "prefix": prefix,
            "status": status
        }
        
        if role:
            prefix_data["role"] = role
        if vrf:
            prefix_data["vrf"] = vrf
        if site:
            prefix_data["site"] = site
        if description:
            prefix_data["description"] = description
        
        # Use dynamic API with safety
        result = client.ipam.prefixes.create(confirm=confirm, **prefix_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "prefix",
            "prefix": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create prefix {prefix}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# VLAN MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="ipam")
def netbox_create_vlan(
    name: str,
    vid: int,
    site: Optional[str] = None,
    group: Optional[str] = None,
    status: str = "active",
    role: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new VLAN in NetBox IPAM.
    
    Args:
        name: VLAN name
        vid: VLAN ID (1-4094)
        site: Optional site name
        group: Optional VLAN group
        status: VLAN status (active, reserved, deprecated)
        role: Optional VLAN role
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created VLAN information or error details
        
    Example:
        netbox_create_vlan("Management", vid=100, site="datacenter-1", confirm=True)
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
        
        client = NetBoxClientManager.get_client()
        logger.info(f"Creating VLAN: {name} (VID: {vid})")
        
        # Build VLAN data
        vlan_data = {
            "name": name,
            "vid": vid,
            "status": status
        }
        
        if site:
            vlan_data["site"] = site
        if group:
            vlan_data["group"] = group
        if role:
            vlan_data["role"] = role
        if description:
            vlan_data["description"] = description
        
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
    site: Optional[str] = None,
    group: Optional[str] = None,
    start_vid: int = 100,
    end_vid: int = 4094
) -> Dict[str, Any]:
    """
    Find available VLAN IDs within a range.
    
    Args:
        site: Optional site to search within
        group: Optional VLAN group to search within  
        start_vid: Start of VID range (default: 100)
        end_vid: End of VID range (default: 4094)
        
    Returns:
        List of available VLAN IDs
        
    Example:
        netbox_find_available_vlan_id(site="datacenter-1", start_vid=100, end_vid=200)
    """
    try:
        client = NetBoxClientManager.get_client()
        logger.info(f"Finding available VLAN IDs from {start_vid} to {end_vid}")
        
        # Build filter
        filters = {}
        if site:
            filters["site"] = site
        if group:
            filters["group"] = group
        
        # Get existing VLANs
        existing_vlans = client.ipam.vlans.filter(**filters)
        used_vids = set(vlan.get("vid") for vlan in existing_vlans if vlan.get("vid"))
        
        # Find available VIDs
        available_vids = []
        for vid in range(start_vid, end_vid + 1):
            if vid not in used_vids:
                available_vids.append(vid)
        
        return {
            "success": True,
            "range": f"{start_vid}-{end_vid}",
            "site": site,
            "group": group,
            "total_in_range": end_vid - start_vid + 1,
            "used_count": len([vid for vid in used_vids if start_vid <= vid <= end_vid]),
            "available_count": len(available_vids),
            "available_vids": available_vids[:50]  # Limit to first 50
        }
        
    except Exception as e:
        logger.error(f"Failed to find available VLAN IDs: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# VRF MANAGEMENT TOOLS  
# ========================================

@mcp_tool(category="ipam")
def netbox_create_vrf(
    name: str,
    rd: Optional[str] = None,
    description: Optional[str] = None,
    tenant: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new VRF in NetBox IPAM.
    
    Args:
        name: VRF name
        rd: Route distinguisher (optional)
        description: Optional description
        tenant: Optional tenant name
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created VRF information or error details
        
    Example:
        netbox_create_vrf("MGMT-VRF", rd="65000:100", confirm=True)
    """
    try:
        if not name:
            return {
                "success": False,
                "error": "VRF name is required",
                "error_type": "ValidationError"
            }
        
        client = NetBoxClientManager.get_client()
        logger.info(f"Creating VRF: {name}")
        
        # Build VRF data
        vrf_data = {"name": name}
        
        if rd:
            vrf_data["rd"] = rd
        if description:
            vrf_data["description"] = description
        if tenant:
            vrf_data["tenant"] = tenant
        
        # Use dynamic API with safety
        result = client.ipam.vrfs.create(confirm=confirm, **vrf_data)
        
        return {
            "success": True,
            "action": "created", 
            "object_type": "vrf",
            "vrf": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create VRF {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


if __name__ == "__main__":
    print("🌐 IPAM Tools Extension for NetBox MCP")
    print("=" * 40)
    print("These tools provide comprehensive IPAM functionality:")
    print("• IP Address Management (create, find available, usage stats)")
    print("• Prefix Management (create, organize)")
    print("• VLAN Management (create, find available VIDs)")
    print("• VRF Management (create, configure)")
    print("• All tools include enterprise safety mechanisms")
    print("• Ready to integrate into server.py as MCP tools")