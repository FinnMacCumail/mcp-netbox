#!/usr/bin/env python3
"""
Circuit Provider Management Tools

Enterprise-grade tools for managing NetBox circuit providers including provider creation,
information retrieval, and bulk discovery operations following the dual-tool pattern.
"""

from typing import Dict, List, Any, Optional
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="circuits")
def netbox_create_provider(
    client: NetBoxClient,
    name: str,
    slug: str = None,
    asn: int = None,
    account: str = None,
    portal_url: str = None,
    noc_contact: str = None,
    admin_contact: str = None,
    comments: str = None,
    tags: List[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new circuit provider in NetBox.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        name: Provider name (required)
        slug: URL-friendly slug (auto-generated if not provided)
        asn: Autonomous System Number
        account: Account number with the provider
        portal_url: Provider's customer portal URL
        noc_contact: Network Operations Center contact information
        admin_contact: Administrative contact information
        comments: Additional comments
        tags: List of tags to assign
        confirm: Set to True to execute the creation
        
    Returns:
        Dictionary containing the created provider information or validation results
    """
    if not confirm:
        return {
            "success": False,
            "message": "Dry run - Provider creation requires confirm=True",
            "would_create": {
                "name": name,
                "slug": slug or name.lower().replace(" ", "-").replace("_", "-"),
                "asn": asn,
                "account": account,
                "portal_url": portal_url,
                "noc_contact": noc_contact,
                "admin_contact": admin_contact,
                "comments": comments,
                "tags": tags or []
            }
        }
    
    try:
        # Generate slug if not provided
        if not slug:
            slug = name.lower().replace(" ", "-").replace("_", "-")
        
        # Prepare provider data
        provider_data = {
            "name": name,
            "slug": slug
        }
        
        # Add optional fields if provided
        if asn is not None:
            provider_data["asn"] = asn
        if account:
            provider_data["account"] = account
        if portal_url:
            provider_data["portal_url"] = portal_url
        if noc_contact:
            provider_data["noc_contact"] = noc_contact
        if admin_contact:
            provider_data["admin_contact"] = admin_contact
        if comments:
            provider_data["comments"] = comments
        if tags:
            provider_data["tags"] = tags
        
        # Create the provider
        provider = client.circuits.providers.create(provider_data)
        
        logger.info(f"Successfully created provider: {name} (ID: {provider.id})")
        
        return {
            "success": True,
            "message": f"Successfully created provider: {name}",
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "slug": provider.slug,
                "asn": getattr(provider, 'asn', None),
                "account": getattr(provider, 'account', None),
                "portal_url": getattr(provider, 'portal_url', None),
                "noc_contact": getattr(provider, 'noc_contact', None),
                "admin_contact": getattr(provider, 'admin_contact', None),
                "circuit_count": getattr(provider, 'circuit_count', 0),
                "url": f"{client.base_url}/circuits/providers/{provider.id}/"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to create provider {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="circuits")
def netbox_get_provider_info(
    client: NetBoxClient,
    provider_name: str = None,
    provider_id: int = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific circuit provider.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        provider_name: Name of the provider to retrieve
        provider_id: ID of the provider to retrieve
        
    Returns:
        Dictionary containing detailed provider information
    """
    try:
        if not provider_name and not provider_id:
            return {
                "success": False,
                "error": "Either provider_name or provider_id must be provided"
            }
        
        # Find the provider
        if provider_id:
            provider = client.circuits.providers.get(provider_id)
        else:
            providers = client.circuits.providers.filter(name=provider_name)
            if not providers:
                return {
                    "success": False,
                    "error": f"Provider not found: {provider_name}"
                }
            provider = providers[0]
        
        # Get related circuits
        circuits = client.circuits.circuits.filter(provider_id=provider.id)
        
        return {
            "success": True,
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "slug": provider.slug,
                "asn": getattr(provider, 'asn', None),
                "account": getattr(provider, 'account', None),
                "portal_url": getattr(provider, 'portal_url', None),
                "noc_contact": getattr(provider, 'noc_contact', None),
                "admin_contact": getattr(provider, 'admin_contact', None),
                "comments": getattr(provider, 'comments', None),
                "tags": [tag.name for tag in getattr(provider, 'tags', [])],
                "circuit_count": len(circuits),
                "circuits": [
                    {
                        "id": circuit.id,
                        "cid": circuit.cid,
                        "type": getattr(circuit.type, 'name', 'Unknown') if hasattr(circuit, 'type') and circuit.type else 'Unknown',
                        "status": getattr(circuit.status, 'label', 'Unknown') if hasattr(circuit, 'status') and circuit.status else 'Unknown'
                    }
                    for circuit in circuits[:10]  # Limit to first 10 circuits
                ],
                "created": str(getattr(provider, 'created', 'Unknown')),
                "last_updated": str(getattr(provider, 'last_updated', 'Unknown')),
                "url": f"{client.base_url}/circuits/providers/{provider.id}/"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get provider info: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="circuits")
def netbox_list_all_providers(
    client: NetBoxClient,
    name_filter: str = None,
    asn_filter: int = None,
    has_circuits: bool = None
) -> Dict[str, Any]:
    """
    Get a comprehensive list of all circuit providers with filtering capabilities.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        name_filter: Filter providers by name (partial match)
        asn_filter: Filter providers by ASN
        has_circuits: Filter providers that have/don't have circuits
        
    Returns:
        Dictionary containing list of providers with summary statistics
    """
    try:
        # Build filter parameters
        filter_params = {}
        if name_filter:
            filter_params['name__icontains'] = name_filter
        if asn_filter:
            filter_params['asn'] = asn_filter
        
        # Get all providers
        providers = client.circuits.providers.filter(**filter_params)
        
        # Process providers with defensive dict access
        provider_list = []
        total_circuits = 0
        providers_with_circuits = 0
        asn_stats = {}
        
        for provider in providers:
            # Defensive dictionary access patterns
            provider_dict = provider if isinstance(provider, dict) else provider.__dict__
            
            provider_id = provider_dict.get('id', 'Unknown')
            provider_name = provider_dict.get('name', 'Unknown')
            provider_asn = provider_dict.get('asn', None)
            
            # Get circuit count for this provider
            circuits = client.circuits.circuits.filter(provider_id=provider_id)
            circuit_count = len(circuits)
            
            # Apply has_circuits filter
            if has_circuits is not None:
                if has_circuits and circuit_count == 0:
                    continue
                if not has_circuits and circuit_count > 0:
                    continue
            
            # Track statistics
            total_circuits += circuit_count
            if circuit_count > 0:
                providers_with_circuits += 1
            
            if provider_asn:
                asn_stats[provider_asn] = asn_stats.get(provider_asn, 0) + 1
            
            provider_info = {
                "id": provider_id,
                "name": provider_name,
                "slug": provider_dict.get('slug', 'unknown'),
                "asn": provider_asn,
                "account": provider_dict.get('account', None),
                "circuit_count": circuit_count,
                "portal_url": provider_dict.get('portal_url', None),
                "noc_contact": provider_dict.get('noc_contact', None),
                "admin_contact": provider_dict.get('admin_contact', None),
                "tags": [],  # Simplified for list view
                "url": f"{client.base_url}/circuits/providers/{provider_id}/"
            }
            
            # Safely extract tags if available
            try:
                if hasattr(provider, 'tags') and provider.tags:
                    provider_info["tags"] = [tag.name for tag in provider.tags]
            except:
                pass
            
            provider_list.append(provider_info)
        
        # Sort providers by name
        provider_list.sort(key=lambda x: x["name"])
        
        return {
            "success": True,
            "providers": provider_list,
            "summary": {
                "total_providers": len(provider_list),
                "providers_with_circuits": providers_with_circuits,
                "providers_without_circuits": len(provider_list) - providers_with_circuits,
                "total_circuits": total_circuits,
                "average_circuits_per_provider": round(total_circuits / len(provider_list), 2) if provider_list else 0,
                "unique_asns": len(asn_stats),
                "filter_applied": {
                    "name_filter": name_filter,
                    "asn_filter": asn_filter,
                    "has_circuits": has_circuits
                }
            },
            "asn_distribution": dict(sorted(asn_stats.items())) if asn_stats else {}
        }
        
    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }