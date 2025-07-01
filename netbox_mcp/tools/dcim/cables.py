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
def netbox_create_cable_connection(
    client: NetBoxClient,
    device_a_name: str,
    interface_a_name: str,
    device_b_name: str,
    interface_b_name: str,
    cable_type: str = "cat6",
    cable_status: str = "connected",
    cable_length: Optional[int] = None,
    cable_length_unit: str = "m",
    label: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a physical cable connection between two device interfaces.
    
    This enterprise-grade cable management tool handles the complete workflow of 
    documenting physical cable connections with comprehensive validation, conflict 
    detection, and cache invalidation to ensure data consistency.
    
    Args:
        client: NetBoxClient instance (injected)
        device_a_name: Name of the first device
        interface_a_name: Name of the interface on device A
        device_b_name: Name of the second device
        interface_b_name: Name of the interface on device B
        cable_type: Type of cable (cat5e, cat6, cat6a, cat7, cat8, mmf, smf, dac-active, dac-passive, coaxial, power)
        cable_status: Cable status (planned, installed, connected, decommissioning)
        cable_length: Optional cable length
        cable_length_unit: Length unit (mm, cm, m, km, in, ft, mi)
        label: Optional cable label
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Cable creation result with comprehensive termination information
        
    Example:
        netbox_create_cable_connection(
            device_a_name="sw-access-01",
            interface_a_name="GigabitEthernet1/0/1",
            device_b_name="sw-core-01", 
            interface_b_name="GigabitEthernet1/1",
            cable_type="cat6",
            cable_length=15,
            confirm=True
        )
    """
    try:
        if not all([device_a_name, interface_a_name, device_b_name, interface_b_name]):
            return {
                "success": False,
                "error": "Both device names and interface names are required",
                "error_type": "ValidationError"
            }
        
        # Prevent self-connection
        if device_a_name == device_b_name and interface_a_name == interface_b_name:
            return {
                "success": False,
                "error": "Cannot connect an interface to itself",
                "error_type": "ValidationError"
            }
        
        # Validate cable type
        valid_cable_types = [
            "cat3", "cat5", "cat5e", "cat6", "cat6a", "cat7", "cat8",
            "dac-active", "dac-passive", "mrj21-trunk", "coaxial", 
            "mmf", "mmf-om1", "mmf-om2", "mmf-om3", "mmf-om4", "mmf-om5",
            "smf", "smf-os1", "smf-os2", "aoc", "power", "usb"
        ]
        
        if cable_type not in valid_cable_types:
            return {
                "success": False,
                "error": f"Invalid cable_type '{cable_type}'. Valid types: {valid_cable_types}",
                "error_type": "ValidationError"
            }
        
        # Validate cable status
        valid_statuses = ["planned", "installed", "connected", "decommissioning"]
        if cable_status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid cable_status '{cable_status}'. Valid statuses: {valid_statuses}",
                "error_type": "ValidationError"
            }
        
        # Validate length unit
        valid_units = ["mm", "cm", "m", "km", "in", "ft", "mi"]
        if cable_length_unit not in valid_units:
            return {
                "success": False,
                "error": f"Invalid cable_length_unit '{cable_length_unit}'. Valid units: {valid_units}",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating cable connection: {device_a_name}:{interface_a_name} <-> {device_b_name}:{interface_b_name}")
        
        # Step 1: Find device A and its interface
        logger.debug(f"Looking up device A: {device_a_name}")
        devices_a = client.dcim.devices.filter(name=device_a_name)
        if not devices_a:
            return {
                "success": False,
                "error": f"Device A '{device_a_name}' not found",
                "error_type": "NotFoundError"
            }
        device_a = devices_a[0]
        device_a_id = device_a["id"]
        
        logger.debug(f"Looking up interface A: {interface_a_name} on device {device_a['name']}")
        interfaces_a = client.dcim.interfaces.filter(device_id=device_a_id, name=interface_a_name)
        if not interfaces_a:
            return {
                "success": False,
                "error": f"Interface A '{interface_a_name}' not found on device '{device_a_name}'",
                "error_type": "NotFoundError"
            }
        interface_a_dict = interfaces_a[0]
        interface_a_id = interface_a_dict["id"]
        
        
        # Step 2: Find device B and its interface
        logger.debug(f"Looking up device B: {device_b_name}")
        devices_b = client.dcim.devices.filter(name=device_b_name)
        if not devices_b:
            return {
                "success": False,
                "error": f"Device B '{device_b_name}' not found",
                "error_type": "NotFoundError"
            }
        device_b = devices_b[0]
        device_b_id = device_b["id"]
        
        logger.debug(f"Looking up interface B: {interface_b_name} on device {device_b['name']}")
        interfaces_b = client.dcim.interfaces.filter(device_id=device_b_id, name=interface_b_name)
        if not interfaces_b:
            return {
                "success": False,
                "error": f"Interface B '{interface_b_name}' not found on device '{device_b_name}'",
                "error_type": "NotFoundError"
            }
        interface_b_dict = interfaces_b[0]
        interface_b_id = interface_b_dict["id"]
        
        
        # Step 3: Check for existing cable connections (conflict detection)
        logger.debug("Checking for existing cable connections...")
        
        # Check interface A
        if interface_a_dict.get("cable"):
            return {
                "success": False,
                "error": f"Interface A '{device_a_name}:{interface_a_name}' already has a cable connection",
                "error_type": "ConflictError"
            }
        
        # Check interface B
        if interface_b_dict.get("cable"):
            return {
                "success": False,
                "error": f"Interface B '{device_b_name}:{interface_b_name}' already has a cable connection",
                "error_type": "ConflictError"
            }
        
        if not confirm:
            # Dry run mode - return what would be created without actually creating
            logger.info(f"DRY RUN: Would create cable connection between {device_a_name}:{interface_a_name} and {device_b_name}:{interface_b_name}")
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "cable",
                "cable": {
                    "termination_a": {"device": device_a["name"], "interface": interface_a_dict["name"]},
                    "termination_b": {"device": device_b["name"], "interface": interface_b_dict["name"]},
                    "type": cable_type,
                    "status": cable_status,
                    "length": cable_length,
                    "length_unit": cable_length_unit,
                    "label": label,
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Step 4: Create the cable with terminations
        # NetBox API expects termination arrays with object_type and object_id
        cable_data = {
            "a_terminations": [{"object_type": "dcim.interface", "object_id": interface_a_id}],
            "b_terminations": [{"object_type": "dcim.interface", "object_id": interface_b_id}],
            "type": cable_type,
            "status": cable_status
        }
        
        if cable_length is not None:
            cable_data["length"] = cable_length
            cable_data["length_unit"] = cable_length_unit
        if label:
            cable_data["label"] = label
        if description:
            cable_data["description"] = description
        
        logger.info(f"Creating cable with termination IDs - A: {interface_a_id}, B: {interface_b_id}")
        logger.debug(f"Full cable payload: {cable_data}")
        result = client.dcim.cables.create(confirm=True, **cable_data)
        
        # Step 5: Cache invalidation for data consistency (Issue #29 pattern)
        try:
            client.cache.invalidate_for_object("dcim.interfaces", interface_a_id)
            client.cache.invalidate_for_object("dcim.interfaces", interface_b_id)
            client.cache.invalidate_pattern("dcim.cables")
        except Exception as cache_error:
            logger.warning(f"Cache invalidation failed: {cache_error}")
        
        return {
            "success": True,
            "action": "created",
            "object_type": "cable",
            "cable": result,
            "terminations": {
                "termination_a": {
                    "device": {"name": device_a["name"], "id": device_a_id},
                    "interface": {"name": interface_a_dict["name"], "id": interface_a_id}
                },
                "termination_b": {
                    "device": {"name": device_b["name"], "id": device_b_id},
                    "interface": {"name": interface_b_dict["name"], "id": interface_b_id}
                }
            },
            "cable_specs": {
                "type": cable_type,
                "status": cable_status,
                "length": f"{cable_length}{cable_length_unit}" if cable_length else None,
                "label": label
            },
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create cable connection: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_disconnect_cable(
    client: NetBoxClient,
    cable_id: Optional[int] = None,
    device_name: Optional[str] = None,
    interface_name: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Disconnect a cable by removing it from NetBox.
    
    Args:
        client: NetBoxClient instance (injected)
        cable_id: Specific cable ID to disconnect (optional)
        device_name: Device name to find cable by interface (optional)
        interface_name: Interface name to find cable (required if device_name provided)
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Cable disconnection result with details
        
    Example:
        netbox_disconnect_cable(cable_id=123, confirm=True)
        netbox_disconnect_cable(device_name="sw-01", interface_name="eth0", confirm=True)
    """
    try:
        if not confirm:
            return {
                "success": False,
                "error": "Confirmation required for cable disconnection",
                "error_type": "ConfirmationError"
            }
        
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
        
        logger.info(f"Disconnecting cable ID: {cable['id']}")
        
        # Delete the cable
        result = client.dcim.cables.delete(cable["id"], confirm=True)
        
        # Cache invalidation for data consistency
        try:
            client.cache.invalidate_pattern("dcim.cables")
            client.cache.invalidate_pattern("dcim.interfaces")
        except Exception as cache_error:
            logger.warning(f"Cache invalidation failed: {cache_error}")
        
        return {
            "success": True,
            "action": "disconnected",
            "object_type": "cable",
            "disconnected_cable": {
                "id": cable["id"],
                "type": cable.get("type", "N/A"),
                "status": cable.get("status", "N/A"),
                "label": cable.get("label", "N/A")
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to disconnect cable: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


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


# TODO: Future cable management tools:
# - netbox_trace_cable_path: Follow cable connections through multiple hops
# - netbox_validate_cable_terminations: Check for proper cable termination patterns
# - netbox_bulk_cable_installation: Mass cable creation for structured cabling
# - netbox_audit_cable_inventory: Generate cable audit reports