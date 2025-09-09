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


