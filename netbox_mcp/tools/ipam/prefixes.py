#!/usr/bin/env python3
"""
IPAM Prefix Management Tools

High-level tools for managing NetBox IP prefixes and network planning.
"""

from typing import Dict, List, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="ipam")
def netbox_create_prefix(
    client: NetBoxClient,
    prefix: str,
    status: str = "active",
    description: Optional[str] = None,
    site: Optional[str] = None,
    vlan: Optional[str] = None,
    tenant: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new IP prefix in NetBox IPAM.
    
    Args:
        client: NetBoxClient instance (injected)
        prefix: Network prefix with CIDR notation (e.g., "192.168.1.0/24")
        status: Prefix status (active, reserved, deprecated, container)
        description: Optional description
        site: Optional site name or slug
        vlan: Optional VLAN name or ID
        tenant: Optional tenant name or slug
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
        
        if description:
            prefix_data["description"] = description
        if site:
            prefix_data["site"] = site
        if vlan:
            prefix_data["vlan"] = vlan
        if tenant:
            prefix_data["tenant"] = tenant
        
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