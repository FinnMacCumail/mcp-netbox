#!/usr/bin/env python3
"""
DCIM Cable Management Tools

High-level tools for managing NetBox cables, cable terminations, 
and physical connectivity documentation with comprehensive enterprise-grade functionality.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)






@mcp_tool(category="dcim")
def netbox_get_cable_info(
    client: NetBoxClient,
    cable_id: Optional[int] = None,
    device_name: Optional[str] = None,
    interface_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific cable.
    
    Args:
        client: NetBoxClient instance (injected)
        cable_id: Specific cable ID to query (optional)
        device_name: Device name to find cable by interface (optional)
        interface_name: Interface name to find cable (required if device_name provided)
        
    Returns:
        Detailed cable information including terminations
        
    Example:
        netbox_get_cable_info(cable_id=123)
        netbox_get_cable_info(device_name="sw-01", interface_name="eth0")
    """
    try:
        cable = None
        
        # Find cable by ID
        if cable_id:
            cables = client.dcim.cables.filter(id=cable_id)
            if not cables:
                return {
                    "success": False,
                    "error": f"Cable ID {cable_id} not found",
                    "error_type": "NotFoundError"
                }
            cable = cables[0]
        
        # Find cable by device interface
        elif device_name and interface_name:
            devices = client.dcim.devices.filter(name=device_name)
            if not devices:
                return {
                    "success": False,
                    "error": f"Device '{device_name}' not found",
                    "error_type": "NotFoundError"
                }
            device = devices[0]
            
            interfaces = client.dcim.interfaces.filter(device_id=device["id"], name=interface_name)
            if not interfaces:
                return {
                    "success": False,
                    "error": f"Interface '{interface_name}' not found on device '{device_name}'",
                    "error_type": "NotFoundError"
                }
            interface = interfaces[0]
            
            if not interface.get("cable"):
                return {
                    "success": False,
                    "error": f"No cable connected to interface '{device_name}:{interface_name}'",
                    "error_type": "NotFoundError"
                }
            
            cable_id = interface["cable"]["id"]
            cables = client.dcim.cables.filter(id=cable_id)
            if cables:
                cable = cables[0]
        
        else:
            return {
                "success": False,
                "error": "Either cable_id or both device_name and interface_name must be provided",
                "error_type": "ValidationError"
            }
        
        if not cable:
            return {
                "success": False,
                "error": "Cable not found",
                "error_type": "NotFoundError"
            }
        
        # Get termination details using defensive dictionary access
        termination_a_info = {}
        termination_b_info = {}
        
        if cable.get("termination_a_type") == "dcim.interface" and cable.get("termination_a_id"):
            interface_a = client.dcim.interfaces.get(cable["termination_a_id"])
            if interface_a:
                device_a = None
                if interface_a.get("device") and interface_a["device"].get("id"):
                    device_a = client.dcim.devices.get(interface_a["device"]["id"])
                
                termination_a_info = {
                    "interface": {
                        "id": interface_a.get("id"),
                        "name": interface_a.get("name", "N/A"),
                        "type": interface_a.get("type", {}).get("label", "N/A") if isinstance(interface_a.get("type"), dict) else str(interface_a.get("type", "N/A"))
                    },
                    "device": {
                        "id": device_a.get("id") if device_a else None,
                        "name": device_a.get("name", "N/A") if device_a else "N/A"
                    } if device_a else {}
                }
        
        if cable.get("termination_b_type") == "dcim.interface" and cable.get("termination_b_id"):
            interface_b = client.dcim.interfaces.get(cable["termination_b_id"])
            if interface_b:
                device_b = None
                if interface_b.get("device") and interface_b["device"].get("id"):
                    device_b = client.dcim.devices.get(interface_b["device"]["id"])
                
                termination_b_info = {
                    "interface": {
                        "id": interface_b.get("id"),
                        "name": interface_b.get("name", "N/A"),
                        "type": interface_b.get("type", {}).get("label", "N/A") if isinstance(interface_b.get("type"), dict) else str(interface_b.get("type", "N/A"))
                    },
                    "device": {
                        "id": device_b.get("id") if device_b else None,
                        "name": device_b.get("name", "N/A") if device_b else "N/A"
                    } if device_b else {}
                }
        
        # Build comprehensive cable information
        cable_info = {
            "id": cable.get("id"),
            "type": cable.get("type", "N/A"),
            "status": cable.get("status", {}).get("label", "N/A") if isinstance(cable.get("status"), dict) else str(cable.get("status", "N/A")),
            "label": cable.get("label", "N/A"),
            "description": cable.get("description", "N/A"),
            "length": cable.get("length"),
            "length_unit": cable.get("length_unit", "N/A") if cable.get("length") else None,
            "terminations": {
                "termination_a": termination_a_info,
                "termination_b": termination_b_info
            },
            "created": cable.get("created"),
            "last_updated": cable.get("last_updated")
        }
        
        return {
            "success": True,
            "cable": cable_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get cable info: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_list_all_cables(
    client: NetBoxClient,
    limit: int = 100,
    site_name: Optional[str] = None,
    cable_type: Optional[str] = None,
    cable_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get summarized list of cables with optional filtering (dual-tool pattern).
    
    Args:
        client: NetBoxClient instance (injected)
        limit: Maximum number of cables to return
        site_name: Filter by site name (optional)
        cable_type: Filter by cable type (optional)
        cable_status: Filter by cable status (optional)
        
    Returns:
        Comprehensive cable list with summary statistics
        
    Example:
        netbox_list_all_cables()
        netbox_list_all_cables(site_name="datacenter-1", cable_type="cat6")
    """
    try:
        # Build filter parameters
        filter_params = {"limit": limit}
        
        # Apply filters if provided
        if cable_type:
            filter_params["type"] = cable_type
        if cable_status:
            filter_params["status"] = cable_status
        
        logger.info(f"Fetching cables with filters: {filter_params}")
        cables = client.dcim.cables.filter(**filter_params)
        
        if not cables:
            return {
                "success": True,
                "cables": [],
                "summary": {
                    "total_count": 0,
                    "message": "No cables found with the specified criteria"
                }
            }
        
        # Process cables with defensive dictionary access
        cable_list = []
        status_counts = {}
        type_counts = {}
        length_stats = {"total_length": 0, "with_length": 0}
        
        for cable in cables:
            # Safe dictionary access for status
            status_obj = cable.get("status", {})
            if isinstance(status_obj, dict):
                status = status_obj.get("label", "N/A")
            else:
                status = str(status_obj) if status_obj else "N/A"
            
            # Count statistics
            status_counts[status] = status_counts.get(status, 0) + 1
            cable_type_val = cable.get("type", "N/A")
            type_counts[cable_type_val] = type_counts.get(cable_type_val, 0) + 1
            
            # Length statistics
            if cable.get("length"):
                length_stats["total_length"] += cable["length"]
                length_stats["with_length"] += 1
            
            # Get termination summary
            termination_summary = "N/A -> N/A"
            if (cable.get("termination_a_type") == "dcim.interface" and 
                cable.get("termination_b_type") == "dcim.interface"):
                # Try to get device names from terminations
                device_a_name = "Device A"
                device_b_name = "Device B"
                
                try:
                    if cable.get("termination_a_id"):
                        interface_a = client.dcim.interfaces.get(cable["termination_a_id"])
                        if interface_a and interface_a.get("device"):
                            device_a = client.dcim.devices.get(interface_a["device"]["id"]) 
                            if device_a:
                                device_a_name = device_a.get("name", "Device A")
                    
                    if cable.get("termination_b_id"):
                        interface_b = client.dcim.interfaces.get(cable["termination_b_id"])
                        if interface_b and interface_b.get("device"):
                            device_b = client.dcim.devices.get(interface_b["device"]["id"])
                            if device_b:
                                device_b_name = device_b.get("name", "Device B")
                    
                    termination_summary = f"{device_a_name} -> {device_b_name}"
                except Exception:
                    # Fallback to generic summary
                    termination_summary = "Interface -> Interface"
            
            cable_info = {
                "id": cable.get("id"),
                "type": cable_type_val,
                "status": status,
                "label": cable.get("label", "N/A"),
                "length": f"{cable.get('length')}{cable.get('length_unit', 'm')}" if cable.get("length") else "Not specified",
                "termination_summary": termination_summary,
                "last_updated": cable.get("last_updated")
            }
            
            cable_list.append(cable_info)
        
        # Generate summary statistics
        summary = {
            "total_count": len(cable_list),
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "length_statistics": {
                "cables_with_length": length_stats["with_length"],
                "total_length": f"{length_stats['total_length']}m" if length_stats["total_length"] > 0 else "Not available",
                "average_length": f"{length_stats['total_length'] / length_stats['with_length']:.1f}m" if length_stats["with_length"] > 0 else "Not available"
            },
            "filters_applied": {
                "site_name": site_name,
                "cable_type": cable_type,
                "cable_status": cable_status,
                "limit": limit
            }
        }
        
        return {
            "success": True,
            "cables": cable_list,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Failed to list cables: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }




# Read-only cable management tools - write operations removed for DeepAgents context optimization