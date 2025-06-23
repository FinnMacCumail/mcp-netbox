#!/usr/bin/env python3
"""
DCIM Device Role Management Tools

High-level tools for managing NetBox device roles with enterprise-grade functionality.
"""

from typing import Dict, List, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_create_device_role(
    client: NetBoxClient,
    name: str,
    slug: str,
    color: str = "9e9e9e",
    vm_role: bool = False,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new device role in NetBox DCIM.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Role name
        slug: URL-friendly identifier
        color: Hex color code (without #)
        vm_role: Whether role applies to virtual machines
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created device role information or error details
        
    Example:
        netbox_create_device_role("Router", "router", color="2196f3", confirm=True)
    """
    try:
        if not name or not slug:
            return {
                "success": False,
                "error": "Role name and slug are required",
                "error_type": "ValidationError"
            }
        
        # Validate color format
        if not color.startswith('#'):
            color = color.lstrip('#')
        if len(color) != 6:
            return {
                "success": False,
                "error": "Color must be a 6-character hex code",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating device role: {name} (slug: {slug})")
        
        # Build device role data
        role_data = {
            "name": name,
            "slug": slug,
            "color": color,
            "vm_role": vm_role
        }
        
        if description:
            role_data["description"] = description
        
        # Use dynamic API with safety
        result = client.dcim.device_roles.create(confirm=confirm, **role_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "device_role",
            "device_role": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create device role {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# TODO: Implement advanced device role management tools:
# - netbox_get_device_role_usage
# - netbox_update_device_role_properties
# - netbox_get_role_based_device_inventory
# - netbox_migrate_devices_between_roles