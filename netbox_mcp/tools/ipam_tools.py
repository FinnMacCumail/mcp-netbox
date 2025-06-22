#!/usr/bin/env python3
"""
IPAM Tools for NetBox MCP

Comprehensive IP Address Management tools following Gemini's dependency 
injection architecture. All tools receive NetBoxClient via dependency injection
rather than importing it directly.

These tools provide high-level IPAM functionality with enterprise safety
mechanisms and comprehensive input validation.
"""

from typing import Dict, List, Optional, Any
import logging
from ..registry import mcp_tool
from ..client import NetBoxClient

logger = logging.getLogger(__name__)


# ========================================
# IP ADDRESS MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="ipam")
def netbox_create_ip_address(
    client: NetBoxClient,
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
        client: NetBoxClient instance (injected by dependency system)
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
    client: NetBoxClient,
    prefix: str,
    count: int = 1
) -> Dict[str, Any]:
    """
    Find available IP addresses within a prefix.
    
    Args:
        client: NetBoxClient instance (injected)
        prefix: Network prefix (e.g., "192.168.1.0/24")
        count: Number of available IPs to find
        
    Returns:
        List of available IP addresses
        
    Example:
        netbox_find_available_ip("192.168.1.0/24", count=5)
    """
    try:
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
    client: NetBoxClient,
    prefix: str
) -> Dict[str, Any]:
    """
    Get IP address usage statistics for a prefix.
    
    Args:
        client: NetBoxClient instance (injected)
        prefix: Network prefix (e.g., "192.168.1.0/24")
        
    Returns:
        Usage statistics including total, used, available IPs
        
    Example:
        netbox_get_ip_usage("192.168.1.0/24")
    """
    try:
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
    client: NetBoxClient,
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
        client: NetBoxClient instance (injected)
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
    client: NetBoxClient,
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
        client: NetBoxClient instance (injected)
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
    client: NetBoxClient,
    site: Optional[str] = None,
    group: Optional[str] = None,
    start_vid: int = 100,
    end_vid: int = 4094
) -> Dict[str, Any]:
    """
    Find available VLAN IDs within a range.
    
    Args:
        client: NetBoxClient instance (injected)
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
# HIGH-LEVEL ENTERPRISE IPAM TOOLS (v0.9.0)
# ========================================

@mcp_tool(category="ipam")
def netbox_find_next_available_ip(
    client: NetBoxClient,
    prefix: str,
    count: int = 1,
    assign_to_interface: Optional[str] = None,
    device_name: Optional[str] = None,
    status: str = "active",
    description: Optional[str] = None,
    tenant: Optional[str] = None,
    vrf: Optional[str] = None,
    reserve_immediately: bool = False,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Find and optionally reserve the next available IP address(es) in a prefix with atomic operation.
    
    This enterprise-grade function combines IP discovery with optional atomic reservation,
    providing essential functionality for automated IP allocation workflows. Supports
    both simple IP discovery and complete interface assignment in a single operation.
    
    Args:
        client: NetBoxClient instance (injected)
        prefix: Network prefix to search (e.g., "192.168.1.0/24")
        count: Number of consecutive IPs to find (default: 1)
        assign_to_interface: Optional interface name for immediate assignment
        device_name: Device name (required if assign_to_interface specified)
        status: IP status if reserving (active, reserved, deprecated, dhcp, slaac)
        description: Optional description for reserved IPs
        tenant: Optional tenant name for IP assignment
        vrf: Optional VRF name for IP assignment
        reserve_immediately: Create IP objects immediately (requires confirm=True)
        confirm: Must be True for any write operations (safety mechanism)
        
    Returns:
        Available IP addresses with optional reservation details
        
    Examples:
        # Find next available IP (read-only)
        netbox_find_next_available_ip(prefix="10.0.1.0/24")
        
        # Find and reserve 3 consecutive IPs
        netbox_find_next_available_ip(
            prefix="10.0.1.0/24", 
            count=3,
            reserve_immediately=True,
            description="Reserved for new servers",
            confirm=True
        )
        
        # Find IP and assign to device interface atomically
        netbox_find_next_available_ip(
            prefix="10.0.1.0/24",
            assign_to_interface="eth0",
            device_name="server-01",
            description="Management IP",
            confirm=True
        )
    """
    try:
        if not prefix:
            return {
                "success": False,
                "error": "prefix is required",
                "error_type": "ValidationError"
            }
        
        if count < 1 or count > 100:
            return {
                "success": False,
                "error": "count must be between 1 and 100",
                "error_type": "ValidationError"
            }
        
        if assign_to_interface and not device_name:
            return {
                "success": False,
                "error": "device_name is required when assign_to_interface is specified",
                "error_type": "ValidationError"
            }
        
        # Note: reserve_immediately with confirm=False is allowed for dry-run validation
        
        logger.info(f"Finding next {count} available IP(s) in prefix: {prefix}")
        
        # Step 1: Find and validate the prefix
        logger.debug(f"Looking up prefix: {prefix}")
        prefixes = client.ipam.prefixes.filter(prefix=prefix)
        
        if not prefixes:
            return {
                "success": False,
                "error": f"Prefix '{prefix}' not found in NetBox",
                "error_type": "NotFoundError"
            }
        
        prefix_obj = prefixes[0]
        prefix_id = prefix_obj["id"]
        logger.debug(f"Found prefix: {prefix_obj['prefix']} (ID: {prefix_id})")
        
        # Step 2: Get available IPs using NetBox's available-ips endpoint
        logger.debug("Retrieving available IPs from NetBox")
        try:
            # Use direct API access for the available-ips endpoint
            available_ips_response = client.api.ipam.prefixes.get(prefix_id).available_ips.list()
            available_ips = [str(ip) for ip in available_ips_response]
        except Exception as e:
            logger.error(f"Failed to get available IPs: {e}")
            return {
                "success": False,
                "error": f"Failed to retrieve available IPs from prefix: {str(e)}",
                "error_type": "NetBoxAPIError"
            }
        
        if not available_ips:
            return {
                "success": False,
                "error": f"No available IP addresses in prefix {prefix}",
                "error_type": "NoAvailableIPs"
            }
        
        if len(available_ips) < count:
            return {
                "success": False,
                "error": f"Only {len(available_ips)} available IPs in prefix, but {count} requested",
                "error_type": "InsufficientIPs"
            }
        
        # Step 3: Select the requested number of consecutive IPs
        selected_ips = available_ips[:count]
        logger.info(f"Selected {len(selected_ips)} available IPs: {selected_ips}")
        
        # If only discovery is requested, return the IPs without reservation
        if not reserve_immediately and not assign_to_interface:
            return {
                "success": True,
                "action": "discovered",
                "prefix": prefix,
                "available_ips": selected_ips,
                "total_available": len(available_ips),
                "dry_run": True
            }
        
        # Step 4: Handle device and interface lookup if assignment is requested
        device_id = None
        interface_id = None
        device_obj = None
        interface_obj = None
        
        if assign_to_interface:
            logger.debug(f"Looking up device: {device_name}")
            devices = client.dcim.devices.filter(name=device_name)
            if not devices:
                return {
                    "success": False,
                    "error": f"Device '{device_name}' not found",
                    "error_type": "NotFoundError"
                }
            
            device_obj = devices[0]
            device_id = device_obj["id"]
            logger.debug(f"Found device: {device_obj['name']} (ID: {device_id})")
            
            logger.debug(f"Looking up interface: {assign_to_interface} on device {device_obj['name']}")
            interfaces = client.dcim.interfaces.filter(device_id=device_id, name=assign_to_interface)
            if not interfaces:
                return {
                    "success": False,
                    "error": f"Interface '{assign_to_interface}' not found on device '{device_obj['name']}'",
                    "error_type": "NotFoundError"
                }
            
            interface_obj = interfaces[0]
            interface_id = interface_obj["id"]
            logger.debug(f"Found interface: {interface_obj['name']} (ID: {interface_id})")
        
        # Step 5: Resolve optional foreign keys
        tenant_id = None
        vrf_id = None
        
        if tenant:
            logger.debug(f"Looking up tenant: {tenant}")
            tenants = client.tenancy.tenants.filter(name=tenant)
            if not tenants:
                tenants = client.tenancy.tenants.filter(slug=tenant)
            if tenants:
                tenant_id = tenants[0]["id"]
                logger.debug(f"Found tenant: {tenants[0]['name']} (ID: {tenant_id})")
            else:
                logger.warning(f"Tenant '{tenant}' not found, proceeding without tenant assignment")
        
        if vrf:
            logger.debug(f"Looking up VRF: {vrf}")
            vrfs = client.ipam.vrfs.filter(name=vrf)
            if vrfs:
                vrf_id = vrfs[0]["id"]
                logger.debug(f"Found VRF: {vrfs[0]['name']} (ID: {vrf_id})")
            else:
                logger.warning(f"VRF '{vrf}' not found, proceeding without VRF assignment")
        
        if not confirm:
            # Dry run mode - show what would be created
            result = {
                "success": True,
                "action": "dry_run",
                "prefix": prefix,
                "selected_ips": selected_ips,
                "total_available": len(available_ips),
                "would_reserve": reserve_immediately,
                "would_assign": bool(assign_to_interface),
                "dry_run": True
            }
            
            if assign_to_interface:
                result["assignment_target"] = {
                    "device": device_obj["name"],
                    "interface": interface_obj["name"],
                    "device_id": device_id,
                    "interface_id": interface_id
                }
            
            return result
        
        # Step 6: Create IP address objects (only if confirm=True and operation requires it)
        if not (reserve_immediately or assign_to_interface):
            # No actual IP creation needed, return discovery results
            return {
                "success": True,
                "action": "discovered",
                "prefix": prefix,
                "available_ips": selected_ips,
                "total_available": len(available_ips),
                "dry_run": False
            }
        
        created_ips = []
        assignment_results = []
        
        for ip_address in selected_ips:
            try:
                # Build IP data
                ip_data = {
                    "address": ip_address,
                    "status": status
                }
                
                if description:
                    ip_data["description"] = description
                if tenant_id:
                    ip_data["tenant"] = tenant_id
                if vrf_id:
                    ip_data["vrf"] = vrf_id
                
                logger.debug(f"Creating IP address: {ip_data}")
                created_ip = client.ipam.ip_addresses.create(confirm=True, **ip_data)
                created_ips.append(created_ip)
                logger.info(f"✅ Created IP address: {ip_address} (ID: {created_ip['id']})")
                
                # Step 7: Assign to interface if requested
                if assign_to_interface:
                    assignment_data = {
                        "assigned_object_type": "dcim.interface",
                        "assigned_object_id": interface_id
                    }
                    
                    logger.debug(f"Assigning IP {ip_address} to interface {interface_obj['name']}")
                    assigned_ip = client.ipam.ip_addresses.update(created_ip["id"], confirm=True, **assignment_data)
                    assignment_results.append({
                        "ip_address": ip_address,
                        "ip_id": created_ip["id"],
                        "assigned_to": f"{device_obj['name']}:{interface_obj['name']}",
                        "assignment_result": assigned_ip
                    })
                    logger.info(f"✅ Assigned IP {ip_address} to {device_obj['name']}:{interface_obj['name']}")
                
            except Exception as e:
                logger.error(f"Failed to create/assign IP {ip_address}: {e}")
                # Continue with other IPs but record the failure
                assignment_results.append({
                    "ip_address": ip_address,
                    "error": str(e),
                    "success": False
                })
        
        # Step 8: Apply cache invalidation pattern from Issue #29
        # Invalidate relevant caches to ensure data consistency
        logger.debug("Invalidating IPAM cache after IP creation...")
        try:
            # Invalidate prefix cache
            client.cache.invalidate_pattern("ipam.prefixes")
            
            # Invalidate interface cache if assignment was performed
            if assign_to_interface and interface_id:
                invalidated = client.cache.invalidate_for_object("dcim.interfaces", interface_id)
                logger.info(f"Cache invalidated: {invalidated} entries for interface {interface_id}")
                
        except Exception as cache_error:
            # Cache invalidation failure should not fail the IP creation
            logger.warning(f"Cache invalidation failed after IP creation: {cache_error}")
        
        # Step 9: Build comprehensive response
        success_count = len([r for r in (assignment_results or created_ips) if isinstance(r, dict) and r.get("success", True)])
        
        result = {
            "success": True,
            "action": "assigned" if assign_to_interface else "reserved",
            "prefix": prefix,
            "requested_count": count,
            "successful_count": success_count,
            "ips_created": len(created_ips),
            "created_ips": created_ips,
            "dry_run": False
        }
        
        if assign_to_interface:
            result["assignment_results"] = assignment_results
            result["device"] = {"name": device_obj["name"], "id": device_id}
            result["interface"] = {"name": interface_obj["name"], "id": interface_id}
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to find/reserve next available IP in {prefix}: {e}")
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
    client: NetBoxClient,
    name: str,
    rd: Optional[str] = None,
    description: Optional[str] = None,
    tenant: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new VRF in NetBox IPAM.
    
    Args:
        client: NetBoxClient instance (injected)
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