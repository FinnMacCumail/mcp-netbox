#!/usr/bin/env python3
"""
Virtualization Cluster Group Management Tools

High-level tools for managing NetBox virtualization cluster groups,
enabling hierarchical organization and management of virtualization clusters.
"""

from typing import Dict, Optional, Any, List
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="virtualization")
def netbox_get_cluster_group_info(
    client: NetBoxClient,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    cluster_group_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific cluster group.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Cluster group name to retrieve
        slug: Cluster group slug to retrieve
        cluster_group_id: Cluster group ID to retrieve
        
    Returns:
        Dict containing detailed cluster group information including cluster count
        
    Raises:
        ValidationError: If no valid identifier provided
        NotFoundError: If cluster group not found
    """
    
    if not any([name, slug, cluster_group_id]):
        raise ValueError("Either 'name', 'slug', or 'cluster_group_id' must be provided")
    
    try:
        if cluster_group_id:
            cluster_group = client.virtualization.cluster_groups.get(cluster_group_id)
        elif name:
            cluster_groups = client.virtualization.cluster_groups.filter(name=name)
            if not cluster_groups:
                raise ValueError(f"Cluster group '{name}' not found")
            cluster_group = cluster_groups[0]
        else:  # slug
            cluster_groups = client.virtualization.cluster_groups.filter(slug=slug)
            if not cluster_groups:
                raise ValueError(f"Cluster group with slug '{slug}' not found")
            cluster_group = cluster_groups[0]
        
        # Apply defensive dict/object handling
        group_id = cluster_group.get('id') if isinstance(cluster_group, dict) else cluster_group.id
        group_name = cluster_group.get('name') if isinstance(cluster_group, dict) else cluster_group.name
        group_slug = cluster_group.get('slug') if isinstance(cluster_group, dict) else cluster_group.slug
        group_description = cluster_group.get('description') if isinstance(cluster_group, dict) else getattr(cluster_group, 'description', None)
        
        # Get cluster count for this group
        cluster_count = len(list(client.virtualization.clusters.filter(group_id=group_id)))
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to retrieve cluster group: {e}")
    
    return {
        "success": True,
        "message": f"Retrieved cluster group '{group_name}'.",
        "data": {
            "id": group_id,
            "name": group_name,
            "slug": group_slug,
            "description": group_description,
            "cluster_count": cluster_count,
            "url": cluster_group.get('url') if isinstance(cluster_group, dict) else getattr(cluster_group, 'url', None)
        }
    }


@mcp_tool(category="virtualization")
def netbox_list_all_cluster_groups(
    client: NetBoxClient,
    name_filter: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get comprehensive list of all cluster groups with filtering capabilities.
    
    This tool provides bulk cluster group discovery across the virtualization infrastructure,
    enabling efficient organizational analysis and hierarchical management.
    
    Args:
        client: NetBoxClient instance (injected)
        name_filter: Filter by cluster group name (partial match)
        limit: Maximum number of cluster groups to return (default: 100)
        
    Returns:
        Dict containing summary list of cluster groups with statistics
    """
    
    # Build filter parameters
    filter_params = {}
    if name_filter:
        filter_params["name__icontains"] = name_filter
    
    try:
        # Get cluster groups with applied filters
        cluster_groups = list(client.virtualization.cluster_groups.filter(**filter_params)[:limit])
        
        # Process cluster groups with defensive dict/object handling
        groups_summary = []
        total_clusters = 0
        
        for cluster_group in cluster_groups:
            group_id = cluster_group.get('id') if isinstance(cluster_group, dict) else cluster_group.id
            group_name = cluster_group.get('name') if isinstance(cluster_group, dict) else cluster_group.name
            group_slug = cluster_group.get('slug') if isinstance(cluster_group, dict) else cluster_group.slug
            group_description = cluster_group.get('description') if isinstance(cluster_group, dict) else getattr(cluster_group, 'description', None)
            
            # Count clusters for this group
            cluster_count = len(list(client.virtualization.clusters.filter(group_id=group_id)))
            total_clusters += cluster_count
            
            groups_summary.append({
                "id": group_id,
                "name": group_name,
                "slug": group_slug,
                "description": group_description,
                "cluster_count": cluster_count
            })
            
    except Exception as e:
        raise ValueError(f"Failed to retrieve cluster groups: {e}")
    
    return {
        "success": True,
        "message": f"Found {len(groups_summary)} cluster groups.",
        "total_cluster_groups": len(groups_summary),
        "total_clusters": total_clusters,
        "applied_filters": {
            "name_filter": name_filter,
            "limit": limit
        },
        "data": groups_summary
    }