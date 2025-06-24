#!/usr/bin/env python3
"""
DCIM Interface and Cable Management Tools

High-level tools for managing NetBox interfaces, cables, and physical connections
with comprehensive enterprise-grade functionality.
"""

from typing import Dict, List, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_assign_ip_to_interface(
    client: NetBoxClient,
    device_name: str,
    interface_name: str,
    ip_address: str,
    status: str = "active",
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Assign an IP address to a device interface with cross-domain IPAM/DCIM integration.
    
    This revolutionary function bridges NetBox's IPAM and DCIM domains by enabling 
    direct IP assignment to device interfaces. Essential for automated network 
    configuration and infrastructure provisioning workflows.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        interface_name: Name of the interface on the device
        ip_address: IP address with CIDR notation (e.g., "10.100.0.1/24")
        status: IP address status (active, reserved, deprecated, dhcp)
        description: Optional description for the IP address
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Cross-domain assignment result with comprehensive status information
        
    Example:
        netbox_assign_ip_to_interface(
            device_name="sw-core-01", 
            interface_name="Vlan100", 
            ip_address="10.100.0.1/24", 
            confirm=True
        )
    """
    try:
        if not all([device_name, interface_name, ip_address]):
            return {
                "success": False,
                "error": "device_name, interface_name, and ip_address are required",
                "error_type": "ValidationError"
            }
        
        # Validate IP address format
        import ipaddress
        try:
            ip_obj = ipaddress.ip_interface(ip_address)
            validated_ip = str(ip_obj)
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid IP address format '{ip_address}': {e}",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Assigning IP {validated_ip} to interface {device_name}:{interface_name}")
        
        # Step 1: Find the device
        logger.debug(f"Looking up device: {device_name}")
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "NotFoundError"
            }
        device = devices[0]
        device_id = device["id"]
        logger.debug(f"Found device: {device['name']} (ID: {device_id})")
        
        # Step 2: Find the interface on the device
        logger.debug(f"Looking up interface: {interface_name} on device {device['name']}")
        interfaces = client.dcim.interfaces.filter(device_id=device_id, name=interface_name)
        if not interfaces:
            return {
                "success": False,
                "error": f"Interface '{interface_name}' not found on device '{device_name}'",
                "error_type": "NotFoundError"
            }
        interface = interfaces[0]
        interface_id = interface["id"]
        logger.debug(f"Found interface: {interface['name']} (ID: {interface_id})")
        
        # Step 3: Check for existing IP assignment conflicts
        logger.debug(f"Checking for IP conflicts: {validated_ip}")
        existing_ips = client.ipam.ip_addresses.filter(address=validated_ip)
        for existing_ip in existing_ips:
            if existing_ip.get("assigned_object_id") and existing_ip.get("assigned_object_type") == "dcim.interface":
                return {
                    "success": False,
                    "error": f"IP address {validated_ip} is already assigned to another interface",
                    "error_type": "ConflictError"
                }
        
        if not confirm:
            # Dry run mode - return what would be assigned without actually assigning
            logger.info(f"DRY RUN: Would assign IP {validated_ip} to interface {device_name}:{interface_name}")
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "ip_assignment",
                "assignment": {
                    "device": {"name": device["name"], "id": device_id},
                    "interface": {"name": interface["name"], "id": interface_id},
                    "ip_address": validated_ip,
                    "status": status,
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Step 4: Create or update IP address with interface assignment
        # NetBox 4.2.9 pattern: Create IP first, then assign to interface
        ip_data = {
            "address": validated_ip,
            "status": status,
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": interface_id
        }
        
        if description:
            ip_data["description"] = description
        
        # Try to create the IP address with assignment
        logger.info(f"Creating IP address {validated_ip} with interface assignment")
        result = client.ipam.ip_addresses.create(confirm=True, **ip_data)
        
        # Invalidate cache for interface and IP data consistency
        try:
            client.cache.invalidate_for_object("dcim.interfaces", interface_id)
            client.cache.invalidate_pattern("ipam.ip_addresses")
        except Exception as cache_error:
            logger.warning(f"Cache invalidation failed: {cache_error}")
        
        return {
            "success": True,
            "action": "assigned",
            "object_type": "ip_assignment",
            "ip_address": result,
            "assignment": {
                "device": {"name": device["name"], "id": device_id},
                "interface": {"name": interface["name"], "id": interface_id},
                "ip_address": validated_ip,
                "status": status
            },
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to assign IP {ip_address} to interface {device_name}:{interface_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# TODO: Implement additional interface management tools:
# - netbox_configure_interface_settings
# - netbox_assign_vlan_to_interface  
# - netbox_monitor_interface_utilization
# - netbox_bulk_interface_operations
# - netbox_get_interface_connections
# 
# NOTE: Cable management tools have been moved to cables.py for better domain separation