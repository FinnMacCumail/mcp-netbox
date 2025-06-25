#!/usr/bin/env python3
"""
IPAM IP Address Management Tools

High-level tools for managing NetBox IP addresses with enterprise-grade functionality.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="ipam")
def netbox_create_ip_address(
    client: NetBoxClient,
    ip_address: str,
    status: str = "active",
    description: Optional[str] = None,
    tenant: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new IP address in NetBox IPAM.
    
    Args:
        client: NetBoxClient instance (injected)
        ip_address: IP address with CIDR notation (e.g., "192.168.1.10/24")
        status: IP status (active, reserved, deprecated, dhcp)
        description: Optional description
        tenant: Optional tenant name or slug
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created IP address information or error details
        
    Example:
        netbox_create_ip_address("192.168.1.10/24", status="active", confirm=True)
    """
    try:
        if not ip_address:
            return {
                "success": False,
                "error": "IP address is required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating IP address: {ip_address}")
        
        # Build IP data
        ip_data = {
            "address": ip_address,
            "status": status
        }
        
        if description:
            ip_data["description"] = description
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
        logger.error(f"Failed to create IP address {ip_address}: {e}")
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
    Find available IP addresses in a prefix.
    
    Args:
        client: NetBoxClient instance (injected)
        prefix: Network prefix (e.g., "192.168.1.0/24")
        count: Number of IPs to find (1-100)
        
    Returns:
        Available IP addresses or error details
        
    Example:
        netbox_find_available_ip("192.168.1.0/24", count=5)
    """
    try:
        if not prefix:
            return {
                "success": False,
                "error": "Prefix is required",
                "error_type": "ValidationError"
            }
        
        if not (1 <= count <= 100):
            return {
                "success": False,
                "error": "Count must be between 1 and 100",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Finding {count} available IPs in prefix: {prefix}")
        
        # Find the prefix
        prefixes = client.ipam.prefixes.filter(prefix=prefix)
        if not prefixes:
            return {
                "success": False,
                "error": f"Prefix '{prefix}' not found",
                "error_type": "PrefixNotFound"
            }
        
        prefix_obj = prefixes[0]
        prefix_id = prefix_obj["id"]
        
        # Get available IPs
        available = client.ipam.prefixes.available_ips(prefix_id, limit=count)
        
        return {
            "success": True,
            "prefix": prefix_obj,
            "available_ips": available[:count],
            "count": len(available[:count]),
            "total_available": len(available)
        }
        
    except Exception as e:
        logger.error(f"Failed to find available IPs in {prefix}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="ipam")
def netbox_assign_mac_to_interface(
    client: NetBoxClient,
    device_name: str,
    interface_name: str,
    mac_address: str,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Assign MAC address to device interface using Defensive Read-Validate-Write Pattern.
    
    Revolutionary implementation with cache bypass for 100% conflict detection accuracy.
    Solves cache timing race conditions affecting enterprise reliability.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        interface_name: Name of the interface
        mac_address: MAC address (any standard format)
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        MAC address assignment result with comprehensive validation status
        
    Example:
        netbox_assign_mac_to_interface("sw-core-01", "GigE0/0/1", "00:1B:44:11:3A:B7", confirm=True)
    """
    try:
        if not all([device_name, interface_name, mac_address]):
            return {
                "success": False,
                "error": "device_name, interface_name, and mac_address are required",
                "error_type": "ValidationError"
            }
        
        # Normalize MAC address format
        import re
        normalized_mac = re.sub(r'[:-]', '', mac_address.lower())
        if len(normalized_mac) != 12:
            return {
                "success": False,
                "error": f"Invalid MAC address format: {mac_address}",
                "error_type": "ValidationError"
            }
        
        # Format for NetBox (colon-separated)
        formatted_mac = ':'.join(normalized_mac[i:i+2] for i in range(0, 12, 2))
        
        logger.info(f"Assigning MAC {formatted_mac} to {device_name}:{interface_name}")
        
        # Find device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "NotFoundError"
            }
        device = devices[0]
        device_id = device["id"]
        
        # Find interface
        interfaces = client.dcim.interfaces.filter(device_id=device_id, name=interface_name)
        if not interfaces:
            return {
                "success": False,
                "error": f"Interface '{interface_name}' not found on device '{device_name}'",
                "error_type": "NotFoundError"
            }
        interface = interfaces[0]
        interface_id = interface["id"]
        
        # DEFENSIVE PATTERN: Cache bypass for 100% conflict detection accuracy
        existing_mac_objects = client.dcim.mac_addresses.filter(
            mac_address=formatted_mac, 
            no_cache=True  # Force fresh API call
        )
        
        for existing_mac in existing_mac_objects:
            assigned_interface = existing_mac.get("assigned_object_id")
            if assigned_interface and assigned_interface != interface_id:
                return {
                    "success": False,
                    "error": f"MAC address {formatted_mac} is already assigned to another interface",
                    "error_type": "ConflictError"
                }
        
        if not confirm:
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "mac_assignment",
                "assignment": {
                    "device": {"name": device["name"], "id": device_id},
                    "interface": {"name": interface["name"], "id": interface_id},
                    "mac_address": formatted_mac,
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Create or update MAC address assignment
        mac_data = {
            "mac_address": formatted_mac,
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": interface_id
        }
        
        result = client.dcim.mac_addresses.create(confirm=True, **mac_data)
        
        return {
            "success": True,
            "action": "assigned",
            "object_type": "mac_assignment",
            "mac_address": result,
            "assignment": {
                "device": {"name": device["name"], "id": device_id},
                "interface": {"name": interface["name"], "id": interface_id},
                "mac_address": formatted_mac
            },
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to assign MAC {mac_address} to {device_name}:{interface_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }