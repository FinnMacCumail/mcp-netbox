#!/usr/bin/env python3
"""
Virtualization Cluster Type Management Tools

High-level tools for managing NetBox virtualization cluster types,
enabling standardized cluster categorization and management.
"""

from typing import Dict, Optional, Any, List
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

@mcp_tool(category="virtualization")
def netbox_get_cluster_type_info(
    client: NetBoxClient,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    cluster_type_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific cluster type.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Cluster type name to retrieve
        slug: Cluster type slug to retrieve
        cluster_type_id: Cluster type ID to retrieve
        
    Returns:
        Dict containing detailed cluster type information
        
    Raises:
        ValidationError: If no valid identifier provided
        NotFoundError: If cluster type not found
    """
    
    if not any([name, slug, cluster_type_id]):
        raise ValueError("Either 'name', 'slug', or 'cluster_type_id' must be provided")
    
    try:
        if cluster_type_id:
            cluster_type = client.virtualization.cluster_types.get(cluster_type_id)
        elif name:
            cluster_types = client.virtualization.cluster_types.filter(name=name)
            if not cluster_types:
                raise ValueError(f"Cluster type '{name}' not found")
            cluster_type = cluster_types[0]
        else:  # slug
            cluster_types = client.virtualization.cluster_types.filter(slug=slug)
            if not cluster_types:
                raise ValueError(f"Cluster type with slug '{slug}' not found")
            cluster_type = cluster_types[0]
        
        # Apply defensive dict/object handling
        cluster_type_id = cluster_type.get('id') if isinstance(cluster_type, dict) else cluster_type.id
        cluster_type_name = cluster_type.get('name') if isinstance(cluster_type, dict) else cluster_type.name
        cluster_type_slug = cluster_type.get('slug') if isinstance(cluster_type, dict) else cluster_type.slug
        cluster_type_description = cluster_type.get('description') if isinstance(cluster_type, dict) else getattr(cluster_type, 'description', None)
        
        # Get cluster count for this type
        cluster_count = len(list(client.virtualization.clusters.filter(type_id=cluster_type_id)))
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to retrieve cluster type: {e}")
    
    return {
        "success": True,
        "message": f"Retrieved cluster type '{cluster_type_name}'.",
        "data": {
            "id": cluster_type_id,
            "name": cluster_type_name,
            "slug": cluster_type_slug,
            "description": cluster_type_description,
            "cluster_count": cluster_count,
            "url": cluster_type.get('url') if isinstance(cluster_type, dict) else getattr(cluster_type, 'url', None)
        }
    }

@mcp_tool(category="virtualization")
def netbox_list_all_cluster_types(
    client: NetBoxClient,
    name_filter: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get comprehensive list of all cluster types with filtering capabilities.
    
    This tool provides bulk cluster type discovery across the virtualization infrastructure,
    enabling efficient platform analysis and cluster categorization.
    
    Args:
        client: NetBoxClient instance (injected)
        name_filter: Filter by cluster type name (partial match)
        limit: Maximum number of cluster types to return (default: 100)
        
    Returns:
        Dict containing summary list of cluster types with statistics
    """
    
    # Build filter parameters
    filter_params = {}
    if name_filter:
        filter_params["name__icontains"] = name_filter
    
    try:
        # Get cluster types with applied filters
        cluster_types = list(client.virtualization.cluster_types.filter(**filter_params)[:limit])
        
        # Process cluster types with defensive dict/object handling
        types_summary = []
        total_clusters = 0
        
        for cluster_type in cluster_types:
            type_id = cluster_type.get('id') if isinstance(cluster_type, dict) else cluster_type.id
            type_name = cluster_type.get('name') if isinstance(cluster_type, dict) else cluster_type.name
            type_slug = cluster_type.get('slug') if isinstance(cluster_type, dict) else cluster_type.slug
            type_description = cluster_type.get('description') if isinstance(cluster_type, dict) else getattr(cluster_type, 'description', None)
            
            # Count clusters for this type
            cluster_count = len(list(client.virtualization.clusters.filter(type_id=type_id)))
            total_clusters += cluster_count
            
            types_summary.append({
                "id": type_id,
                "name": type_name,
                "slug": type_slug,
                "description": type_description,
                "cluster_count": cluster_count
            })
            
    except Exception as e:
        raise ValueError(f"Failed to retrieve cluster types: {e}")
    
    return {
        "success": True,
        "message": f"Found {len(types_summary)} cluster types.",
        "total_cluster_types": len(types_summary),
        "total_clusters": total_clusters,
        "applied_filters": {
            "name_filter": name_filter,
            "limit": limit
        },
        "data": types_summary
    }
