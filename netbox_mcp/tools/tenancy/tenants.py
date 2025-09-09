#!/usr/bin/env python3
"""
Tenancy Management Tools

High-level tools for managing NetBox tenants, tenant groups,
resource assignments and tenant reporting with enterprise-grade functionality.
"""

from typing import Dict, List, Optional, Any
import logging
import re
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

@mcp_tool(category="tenancy")
def netbox_list_all_tenants(
    client: NetBoxClient,
    limit: int = 100,
    group_name: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get summarized list of tenants with optional filtering.
    
    This tool provides bulk tenant discovery across the NetBox multi-tenant 
    infrastructure, enabling efficient tenant administration, billing operations,
    and resource management. Essential for enterprise multi-tenant environments.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        limit: Maximum number of results to return (default: 100)
        group_name: Filter by tenant group name (optional)
        status: Filter by tenant status (active, provisioning, suspended, etc.)
        
    Returns:
        Dictionary containing:
        - count: Total number of tenants found
        - tenants: List of summarized tenant information
        - filters_applied: Dictionary of filters that were applied
        - summary_stats: Aggregate statistics about the tenants
        
    Example:
        netbox_list_all_tenants(status="active", group_name="customers")
        netbox_list_all_tenants(limit=50)
    """
    try:
        logger.info(f"Listing tenants with filters - group: {group_name}, status: {status}")
        
        # Build filters dictionary - only include non-None values
        filters = {}
        if group_name:
            filters['group'] = group_name
        if status:
            filters['status'] = status
        
        # Execute filtered query with limit
        tenants = list(client.tenancy.tenants.filter(**filters))
        
        # Apply limit after fetching
        if len(tenants) > limit:
            tenants = tenants[:limit]
        
        # Generate summary statistics
        status_counts = {}
        group_counts = {}
        
        # Collect resource statistics for each tenant
        total_devices = 0
        total_sites = 0
        total_prefixes = 0
        
        for tenant in tenants:
            # Status breakdown with defensive dictionary access
            status_obj = tenant.get("status", {})
            if isinstance(status_obj, dict):
                status = status_obj.get("label", "N/A")
            else:
                status = str(status_obj) if status_obj else "N/A"
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Group breakdown with defensive dictionary access
            group_obj = tenant.get("group")
            if group_obj:
                if isinstance(group_obj, dict):
                    group_name = group_obj.get("name", str(group_obj))
                else:
                    group_name = str(group_obj)
                group_counts[group_name] = group_counts.get(group_name, 0) + 1
            
            # Get basic resource counts for this tenant (efficient queries)
            tenant_id = tenant.get("id")
            tenant_devices = list(client.dcim.devices.filter(tenant_id=tenant_id))
            tenant_sites = list(client.dcim.sites.filter(tenant_id=tenant_id))
            tenant_prefixes = list(client.ipam.prefixes.filter(tenant_id=tenant_id))
            
            total_devices += len(tenant_devices)
            total_sites += len(tenant_sites)
            total_prefixes += len(tenant_prefixes)
        
        # Create human-readable tenant list
        tenant_list = []
        for tenant in tenants:
            # Get resource counts for this specific tenant
            tenant_id = tenant.get("id")
            tenant_devices = list(client.dcim.devices.filter(tenant_id=tenant_id))
            tenant_sites = list(client.dcim.sites.filter(tenant_id=tenant_id))
            tenant_prefixes = list(client.ipam.prefixes.filter(tenant_id=tenant_id))
            tenant_vlans = list(client.ipam.vlans.filter(tenant_id=tenant_id))
            
            # Defensive dictionary access for status
            status_obj = tenant.get("status", {})
            if isinstance(status_obj, dict):
                status = status_obj.get("label", "N/A")
            else:
                status = str(status_obj) if status_obj else "N/A"
            
            # Defensive dictionary access for group
            group_obj = tenant.get("group")
            group_name = None
            if group_obj:
                if isinstance(group_obj, dict):
                    group_name = group_obj.get("name")
                else:
                    group_name = str(group_obj)
            
            tenant_info = {
                "name": tenant.get("name", "Unknown"),
                "slug": tenant.get("slug", ""),
                "status": status,
                "group": group_name,
                "description": tenant.get("description"),
                "comments": tenant.get("comments"),
                "resource_counts": {
                    "devices": len(tenant_devices),
                    "sites": len(tenant_sites),
                    "prefixes": len(tenant_prefixes),
                    "vlans": len(tenant_vlans)
                },
                "total_resources": len(tenant_devices) + len(tenant_sites) + len(tenant_prefixes) + len(tenant_vlans),
                "created": tenant.get("created"),
                "last_updated": tenant.get("last_updated")
            }
            tenant_list.append(tenant_info)
        
        result = {
            "count": len(tenant_list),
            "tenants": tenant_list,
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
            "summary_stats": {
                "total_tenants": len(tenant_list),
                "status_breakdown": status_counts,
                "group_breakdown": group_counts,
                "total_devices_across_tenants": total_devices,
                "total_sites_across_tenants": total_sites,
                "total_prefixes_across_tenants": total_prefixes,
                "tenants_with_resources": len([t for t in tenant_list if t['total_resources'] > 0]),
                "tenants_with_groups": len([t for t in tenant_list if t['group']]),
                "average_resources_per_tenant": total_devices + total_sites + total_prefixes / len(tenant_list) if tenant_list else 0
            }
        }
        
        logger.info(f"Found {len(tenant_list)} tenants matching criteria. Status breakdown: {status_counts}")
        return result
        
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        return {
            "count": 0,
            "tenants": [],
            "error": str(e),
            "error_type": type(e).__name__,
            "filters_applied": {k: v for k, v in {
                'group_name': group_name,
                'status': status
            }.items() if v is not None}
        }
