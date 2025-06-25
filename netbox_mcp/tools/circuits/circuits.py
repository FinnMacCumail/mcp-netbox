#!/usr/bin/env python3
"""
Circuit Management Tools

Enterprise-grade tools for managing NetBox circuits including circuit creation,
information retrieval, termination management, and bulk discovery operations
following the dual-tool pattern.
"""

from typing import Dict, List, Any, Optional
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="circuits")
def netbox_create_circuit(
    cid: str,
    provider_name: str,
    circuit_type: str,
    status: str = "active",
    tenant_name: str = None,
    description: str = None,
    install_date: str = None,
    commit_rate_kbps: int = None,
    comments: str = None,
    tags: List[str] = None,
    confirm: bool = False,
    client: Optional[NetBoxClient] = None,
) -> Dict[str, Any]:
    """
    Create a new circuit in NetBox.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        cid: Circuit ID (required)
        provider_name: Name of the circuit provider (required)
        circuit_type: Type of circuit (required)
        status: Circuit status (default: "active")
        tenant_name: Name of the tenant (optional)
        description: Circuit description
        install_date: Installation date (YYYY-MM-DD format)
        commit_rate_kbps: Committed rate in kbps
        comments: Additional comments
        tags: List of tags to assign
        confirm: Set to True to execute the creation
        
    Returns:
        Dictionary containing the created circuit information or validation results
    """
    if not confirm:
        return {
            "success": False,
            "message": "Dry run - Circuit creation requires confirm=True",
            "would_create": {
                "cid": cid,
                "provider_name": provider_name,
                "circuit_type": circuit_type,
                "status": status,
                "tenant_name": tenant_name,
                "description": description,
                "install_date": install_date,
                "commit_rate_kbps": commit_rate_kbps,
                "comments": comments,
                "tags": tags or []
            }
        }
    
    try:
        # Find provider
        providers = client.circuits.providers.filter(name=provider_name)
        if not providers:
            return {
                "success": False,
                "error": f"Provider not found: {provider_name}"
            }
        provider = providers[0]
        
        # Find or create circuit type
        circuit_types = client.circuits.circuit_types.filter(name=circuit_type)
        if not circuit_types:
            # Create the circuit type if it doesn't exist
            circuit_type_data = {
                "name": circuit_type,
                "slug": circuit_type.lower().replace(" ", "-").replace("_", "-")
            }
            circuit_type_obj = client.circuits.circuit_types.create(circuit_type_data)
            logger.info(f"Created new circuit type: {circuit_type}")
        else:
            circuit_type_obj = circuit_types[0]
        
        # Find tenant if specified
        tenant = None
        if tenant_name:
            tenants = client.tenancy.tenants.filter(name=tenant_name)
            if not tenants:
                return {
                    "success": False,
                    "error": f"Tenant not found: {tenant_name}"
                }
            tenant = tenants[0]
        
        # Prepare circuit data
        circuit_data = {
            "cid": cid,
            "provider": provider.id,
            "type": circuit_type_obj.id,
            "status": status
        }
        
        # Add optional fields if provided
        if tenant:
            circuit_data["tenant"] = tenant.id
        if description:
            circuit_data["description"] = description
        if install_date:
            circuit_data["install_date"] = install_date
        if commit_rate_kbps:
            circuit_data["commit_rate"] = commit_rate_kbps
        if comments:
            circuit_data["comments"] = comments
        if tags:
            circuit_data["tags"] = tags
        
        # Create the circuit
        circuit = client.circuits.circuits.create(circuit_data)
        
        logger.info(f"Successfully created circuit: {cid} (ID: {circuit.id})")
        
        return {
            "success": True,
            "message": f"Successfully created circuit: {cid}",
            "circuit": {
                "id": circuit.id,
                "cid": circuit.cid,
                "provider": getattr(circuit.provider, 'name', 'Unknown') if hasattr(circuit, 'provider') and circuit.provider else 'Unknown',
                "type": getattr(circuit.type, 'name', 'Unknown') if hasattr(circuit, 'type') and circuit.type else 'Unknown',
                "status": getattr(circuit.status, 'label', status) if hasattr(circuit, 'status') and circuit.status else status,
                "tenant": getattr(circuit.tenant, 'name', None) if hasattr(circuit, 'tenant') and circuit.tenant else None,
                "description": getattr(circuit, 'description', None),
                "install_date": str(getattr(circuit, 'install_date', None)),
                "commit_rate": getattr(circuit, 'commit_rate', None),
                "url": f"{client.base_url}/circuits/circuits/{circuit.id}/"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to create circuit {cid}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="circuits")
def netbox_get_circuit_info(
    cid: str = None, circuit_id: int = None, client: Optional[NetBoxClient] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific circuit.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        cid: Circuit ID to retrieve
        circuit_id: Numeric ID of the circuit to retrieve
        
    Returns:
        Dictionary containing detailed circuit information
    """
    try:
        if not cid and not circuit_id:
            return {
                "success": False,
                "error": "Either cid or circuit_id must be provided"
            }
        
        # Find the circuit
        if circuit_id:
            circuit = client.circuits.circuits.get(circuit_id)
        else:
            circuits = client.circuits.circuits.filter(cid=cid)
            if not circuits:
                return {
                    "success": False,
                    "error": f"Circuit not found: {cid}"
                }
            circuit = circuits[0]

        if not circuit:
            return {
                "success": False,
                "error": f"Circuit not found: {cid or circuit_id}"
            }
        
        # Get circuit terminations
        terminations = client.circuits.circuit_terminations.filter(circuit_id=circuit.id)
        
        return {
            "success": True,
            "circuit": {
                "id": circuit.id,
                "cid": circuit.cid,
                "provider": {
                    "id": getattr(circuit.provider, 'id', None) if hasattr(circuit, 'provider') and circuit.provider else None,
                    "name": getattr(circuit.provider, 'name', 'Unknown') if hasattr(circuit, 'provider') and circuit.provider else 'Unknown'
                },
                "type": {
                    "id": getattr(circuit.type, 'id', None) if hasattr(circuit, 'type') and circuit.type else None,
                    "name": getattr(circuit.type, 'name', 'Unknown') if hasattr(circuit, 'type') and circuit.type else 'Unknown'
                },
                "status": getattr(circuit.status, 'label', 'Unknown') if hasattr(circuit, 'status') and circuit.status else 'Unknown',
                "tenant": {
                    "id": getattr(circuit.tenant, 'id', None) if hasattr(circuit, 'tenant') and circuit.tenant else None,
                    "name": getattr(circuit.tenant, 'name', None) if hasattr(circuit, 'tenant') and circuit.tenant else None
                } if hasattr(circuit, 'tenant') and circuit.tenant else None,
                "description": getattr(circuit, 'description', None),
                "install_date": str(getattr(circuit, 'install_date', None)),
                "commit_rate": getattr(circuit, 'commit_rate', None),
                "comments": getattr(circuit, 'comments', None),
                "tags": [tag.name for tag in getattr(circuit, 'tags', [])],
                "terminations": [
                    {
                        "id": term.id,
                        "term_side": getattr(term, 'term_side', 'Unknown'),
                        "site": getattr(term.site, 'name', 'Unknown') if hasattr(term, 'site') and term.site else None,
                        "port_speed": getattr(term, 'port_speed', None),
                        "upstream_speed": getattr(term, 'upstream_speed', None),
                        "xconnect_id": getattr(term, 'xconnect_id', None),
                        "description": getattr(term, 'description', None)
                    }
                    for term in terminations
                ],
                "created": str(getattr(circuit, 'created', 'Unknown')),
                "last_updated": str(getattr(circuit, 'last_updated', 'Unknown')),
                "url": f"{client.base_url}/circuits/circuits/{circuit.id}/"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get circuit info: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="circuits")
def netbox_list_all_circuits(
    provider_name: str = None,
    circuit_type: str = None,
    status: str = None,
    tenant_name: str = None,
    site_name: str = None,
    client: Optional[NetBoxClient] = None,
) -> Dict[str, Any]:
    """
    Get a comprehensive list of all circuits with filtering capabilities.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        provider_name: Filter circuits by provider name
        circuit_type: Filter circuits by type
        status: Filter circuits by status
        tenant_name: Filter circuits by tenant
        site_name: Filter circuits by termination site
        
    Returns:
        Dictionary containing list of circuits with summary statistics
    """
    try:
        # Build filter parameters
        filter_params = {}
        
        if provider_name:
            providers = client.circuits.providers.filter(name=provider_name)
            if providers:
                filter_params['provider_id'] = providers[0].id
            else:
                return {
                    "success": False,
                    "error": f"Provider not found: {provider_name}"
                }
        
        if circuit_type:
            types = client.circuits.circuit_types.filter(name=circuit_type)
            if types:
                filter_params['type_id'] = types[0].id
            else:
                return {
                    "success": False,
                    "error": f"Circuit type not found: {circuit_type}"
                }
        
        if status:
            filter_params['status'] = status
        
        if tenant_name:
            tenants = client.tenancy.tenants.filter(name=tenant_name)
            if tenants:
                filter_params['tenant_id'] = tenants[0].id
            else:
                return {
                    "success": False,
                    "error": f"Tenant not found: {tenant_name}"
                }
        
        # Get all circuits
        circuits = client.circuits.circuits.filter(**filter_params)
        
        # Process circuits with defensive dict access
        circuit_list = []
        status_stats = {}
        type_stats = {}
        provider_stats = {}
        tenant_stats = {}
        total_commit_rate = 0
        circuits_with_rate = 0
        
        for circuit in circuits:
            # Defensive dictionary access patterns
            circuit_dict = circuit if isinstance(circuit, dict) else circuit.__dict__
            
            circuit_id = circuit_dict.get('id', 'Unknown')
            circuit_cid = circuit_dict.get('cid', 'Unknown')
            
            # Get provider info
            provider_info = "Unknown"
            if hasattr(circuit, 'provider') and circuit.provider:
                provider_info = getattr(circuit.provider, 'name', 'Unknown')
            
            # Get type info
            type_info = "Unknown"
            if hasattr(circuit, 'type') and circuit.type:
                type_info = getattr(circuit.type, 'name', 'Unknown')
            
            # Get status info
            status_info = "Unknown"
            if hasattr(circuit, 'status') and circuit.status:
                status_info = getattr(circuit.status, 'label', 'Unknown')
            
            # Get tenant info
            tenant_info = None
            if hasattr(circuit, 'tenant') and circuit.tenant:
                tenant_info = getattr(circuit.tenant, 'name', None)
            
            # Get commit rate
            commit_rate = circuit_dict.get('commit_rate', None)
            if commit_rate:
                total_commit_rate += commit_rate
                circuits_with_rate += 1
            
            # Apply site filter if specified
            if site_name:
                terminations = client.circuits.circuit_terminations.filter(circuit_id=circuit_id)
                has_site = False
                for term in terminations:
                    if hasattr(term, 'site') and term.site and getattr(term.site, 'name', '') == site_name:
                        has_site = True
                        break
                if not has_site:
                    continue
            
            # Track statistics
            status_stats[status_info] = status_stats.get(status_info, 0) + 1
            type_stats[type_info] = type_stats.get(type_info, 0) + 1
            provider_stats[provider_info] = provider_stats.get(provider_info, 0) + 1
            if tenant_info:
                tenant_stats[tenant_info] = tenant_stats.get(tenant_info, 0) + 1
            
            circuit_info = {
                "id": circuit_id,
                "cid": circuit_cid,
                "provider": provider_info,
                "type": type_info,
                "status": status_info,
                "tenant": tenant_info,
                "description": circuit_dict.get('description', None),
                "install_date": str(circuit_dict.get('install_date', None)),
                "commit_rate": commit_rate,
                "termination_count": 0,  # Will be populated if needed
                "url": f"{client.base_url}/circuits/circuits/{circuit_id}/"
            }
            
            circuit_list.append(circuit_info)
        
        # Sort circuits by CID
        circuit_list.sort(key=lambda x: x["cid"])
        
        return {
            "success": True,
            "circuits": circuit_list,
            "summary": {
                "total_circuits": len(circuit_list),
                "average_commit_rate": round(total_commit_rate / circuits_with_rate, 2) if circuits_with_rate > 0 else 0,
                "circuits_with_commit_rate": circuits_with_rate,
                "total_commit_rate_mbps": round(total_commit_rate / 1000, 2) if total_commit_rate > 0 else 0,
                "filter_applied": {
                    "provider_name": provider_name,
                    "circuit_type": circuit_type,
                    "status": status,
                    "tenant_name": tenant_name,
                    "site_name": site_name
                }
            },
            "statistics": {
                "by_status": dict(sorted(status_stats.items())),
                "by_type": dict(sorted(type_stats.items())),
                "by_provider": dict(sorted(provider_stats.items())),
                "by_tenant": dict(sorted(tenant_stats.items())) if tenant_stats else {}
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list circuits: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="circuits")
def netbox_create_circuit_termination(
    cid: str,
    term_side: str,
    site_name: str,
    port_speed_kbps: int = None,
    upstream_speed_kbps: int = None,
    xconnect_id: str = None,
    pp_info: str = None,
    description: str = None,
    confirm: bool = False,
    client: Optional[NetBoxClient] = None,
) -> Dict[str, Any]:
    """
    Create a circuit termination for an existing circuit.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        cid: Circuit ID to terminate
        term_side: Termination side ("A" or "Z")
        site_name: Name of the site where circuit terminates
        port_speed_kbps: Port speed in kbps
        upstream_speed_kbps: Upstream speed in kbps
        xconnect_id: Cross-connect ID
        pp_info: Patch panel information
        description: Termination description
        confirm: Set to True to execute the creation
        
    Returns:
        Dictionary containing the created termination information
    """
    if not confirm:
        return {
            "success": False,
            "message": "Dry run - Circuit termination creation requires confirm=True",
            "would_create": {
                "cid": cid,
                "term_side": term_side,
                "site_name": site_name,
                "port_speed_kbps": port_speed_kbps,
                "upstream_speed_kbps": upstream_speed_kbps,
                "xconnect_id": xconnect_id,
                "pp_info": pp_info,
                "description": description
            }
        }
    
    try:
        # Find the circuit
        circuits = client.circuits.circuits.filter(cid=cid)
        if not circuits:
            return {
                "success": False,
                "error": f"Circuit not found: {cid}"
            }
        circuit = circuits[0]
        
        # Find the site
        sites = client.dcim.sites.filter(name=site_name)
        if not sites:
            return {
                "success": False,
                "error": f"Site not found: {site_name}"
            }
        site = sites[0]
        
        # Validate term_side
        if term_side.upper() not in ["A", "Z"]:
            return {
                "success": False,
                "error": "term_side must be 'A' or 'Z'"
            }
        
        # Check if termination already exists
        existing_terms = client.circuits.circuit_terminations.filter(
            circuit_id=circuit.id,
            term_side=term_side.upper()
        )
        if existing_terms:
            return {
                "success": False,
                "error": f"Termination {term_side.upper()} already exists for circuit {cid}"
            }
        
        # Prepare termination data
        termination_data = {
            "circuit": circuit.id,
            "term_side": term_side.upper(),
            "site": site.id
        }
        
        # Add optional fields if provided
        if port_speed_kbps:
            termination_data["port_speed"] = port_speed_kbps
        if upstream_speed_kbps:
            termination_data["upstream_speed"] = upstream_speed_kbps
        if xconnect_id:
            termination_data["xconnect_id"] = xconnect_id
        if pp_info:
            termination_data["pp_info"] = pp_info
        if description:
            termination_data["description"] = description
        
        # Create the termination
        termination = client.circuits.circuit_terminations.create(termination_data)
        
        logger.info(f"Successfully created circuit termination: {cid} side {term_side} (ID: {termination.id})")
        
        return {
            "success": True,
            "message": f"Successfully created circuit termination: {cid} side {term_side}",
            "termination": {
                "id": termination.id,
                "circuit_cid": cid,
                "term_side": termination.term_side,
                "site": getattr(termination.site, 'name', 'Unknown') if hasattr(termination, 'site') and termination.site else 'Unknown',
                "port_speed": getattr(termination, 'port_speed', None),
                "upstream_speed": getattr(termination, 'upstream_speed', None),
                "xconnect_id": getattr(termination, 'xconnect_id', None),
                "pp_info": getattr(termination, 'pp_info', None),
                "description": getattr(termination, 'description', None),
                "url": f"{client.base_url}/circuits/circuit-terminations/{termination.id}/"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to create circuit termination for {cid}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }