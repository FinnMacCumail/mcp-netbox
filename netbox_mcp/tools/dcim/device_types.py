#!/usr/bin/env python3
"""
DCIM Device Type Management Tools

High-level tools for managing NetBox device types with enterprise-grade functionality.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_list_all_device_types(
    client: NetBoxClient,
    limit: int = 100,
    manufacturer_name: Optional[str] = None,
    u_height: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get summarized list of device types with usage statistics.
    
    This tool provides bulk device type discovery across the NetBox DCIM infrastructure,
    enabling efficient device catalog management, procurement planning, and hardware
    standardization. Essential for device lifecycle management and hardware planning.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        limit: Maximum number of results to return (default: 100)
        manufacturer_name: Filter by manufacturer name (optional)
        u_height: Filter by rack unit height (optional)
        
    Returns:
        Dictionary containing:
        - count: Total number of device types found
        - device_types: List of summarized device type information
        - filters_applied: Dictionary of filters that were applied
        - summary_stats: Aggregate statistics about the device types
        
    Example:
        netbox_list_all_device_types()
        netbox_list_all_device_types(manufacturer_name="cisco", u_height=1)
        netbox_list_all_device_types(limit=50)
    """
    try:
        logger.info(f"Listing device types with filters - manufacturer: {manufacturer_name}, u_height: {u_height}")
        
        # Build filters dictionary - only include non-None values
        filters = {}
        if manufacturer_name:
            filters['manufacturer'] = manufacturer_name
        if u_height is not None:
            filters['u_height'] = u_height
        
        # Execute filtered query with limit
        device_types = list(client.dcim.device_types.filter(**filters))
        
        # Apply limit after fetching
        if len(device_types) > limit:
            device_types = device_types[:limit]
        
        # Generate summary statistics
        manufacturer_counts = {}
        u_height_counts = {}
        total_devices = 0
        device_types_with_devices = 0
        
        # Create human-readable device type list
        device_type_list = []
        for device_type in device_types:
            # Get manufacturer information with defensive dictionary access
            manufacturer_name = "Unknown"
            manufacturer_obj = device_type.get("manufacturer")
            if manufacturer_obj:
                if isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get("name", "Unknown")
                else:
                    # If it's an ID, look up the manufacturer
                    try:
                        manufacturer_detail = client.dcim.manufacturers.get(manufacturer_obj)
                        if isinstance(manufacturer_detail, dict):
                            manufacturer_name = manufacturer_detail.get("name", str(manufacturer_obj))
                        else:
                            manufacturer_name = str(manufacturer_obj)
                    except:
                        manufacturer_name = str(manufacturer_obj)
            
            # Manufacturer breakdown
            manufacturer_counts[manufacturer_name] = manufacturer_counts.get(manufacturer_name, 0) + 1
            
            # U-height breakdown with defensive dictionary access
            u_height = device_type.get("u_height", 1)
            u_height_counts[f"{u_height}U"] = u_height_counts.get(f"{u_height}U", 0) + 1
            
            # Get devices using this device type
            device_type_id = device_type.get("id")
            devices_of_type = list(client.dcim.devices.filter(device_type_id=device_type_id))
            device_count = len(devices_of_type)
            total_devices += device_count
            if device_count > 0:
                device_types_with_devices += 1
            
            device_type_info = {
                "model": device_type.get("model", "Unknown"),
                "manufacturer": manufacturer_name,
                "slug": device_type.get("slug", ""),
                "u_height": u_height,
                "is_full_depth": device_type.get("is_full_depth"),
                "part_number": device_type.get("part_number"),
                "description": device_type.get("description"),
                "device_count": device_count,
                "created": device_type.get("created"),
                "last_updated": device_type.get("last_updated")
            }
            device_type_list.append(device_type_info)
        
        # Sort by device count (most used device types first)
        device_type_list.sort(key=lambda dt: dt['device_count'], reverse=True)
        
        result = {
            "count": len(device_type_list),
            "device_types": device_type_list,
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
            "summary_stats": {
                "total_device_types": len(device_type_list),
                "manufacturer_breakdown": manufacturer_counts,
                "u_height_breakdown": u_height_counts,
                "total_devices_using_types": total_devices,
                "device_types_in_use": device_types_with_devices,
                "device_types_unused": len(device_type_list) - device_types_with_devices,
                "average_devices_per_type": round(total_devices / len(device_type_list), 1) if device_type_list else 0,
                "most_used_types": [dt["model"] for dt in device_type_list[:5] if dt["device_count"] > 0],
                "rack_space_breakdown": {
                    "1U_types": len([dt for dt in device_type_list if dt["u_height"] == 1]),
                    "2U_types": len([dt for dt in device_type_list if dt["u_height"] == 2]),
                    "large_types": len([dt for dt in device_type_list if dt["u_height"] > 2])
                }
            }
        }
        
        logger.info(f"Found {len(device_type_list)} device types matching criteria. Total devices using types: {total_devices}")
        return result
        
    except Exception as e:
        logger.error(f"Error listing device types: {e}")
        return {
            "count": 0,
            "device_types": [],
            "error": str(e),
            "error_type": type(e).__name__,
            "filters_applied": {k: v for k, v in {
                'manufacturer_name': manufacturer_name,
                'u_height': u_height
            }.items() if v is not None}
        }


@mcp_tool(category="dcim")
def netbox_get_device_type_info(
    client: NetBoxClient,
    manufacturer: str,
    model: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific device type.
    
    This inspection tool provides comprehensive device type details including
    specifications, usage statistics, and component templates. Essential for
    device selection, compatibility verification, and hardware planning.
    
    Args:
        client: NetBoxClient instance (injected)
        manufacturer: Manufacturer name
        model: Device model name
        
    Returns:
        Detailed device type information or error details
        
    Example:
        netbox_get_device_type_info("Cisco", "ISR4331")
    """
    try:
        if not manufacturer or not model:
            return {
                "success": False,
                "error": "Manufacturer and model are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Getting device type info for {model} by {manufacturer}")
        
        # Resolve manufacturer to ID
        manufacturers = client.dcim.manufacturers.filter(name=manufacturer)
        if not manufacturers:
            manufacturers = client.dcim.manufacturers.filter(slug=manufacturer)
        if not manufacturers:
            return {
                "success": False,
                "error": f"Manufacturer '{manufacturer}' not found",
                "error_type": "ManufacturerNotFound"
            }
        
        manufacturer_obj = manufacturers[0]
        manufacturer_id = manufacturer_obj.get('id') if isinstance(manufacturer_obj, dict) else manufacturer_obj.id
        manufacturer_name = manufacturer_obj.get('name') if isinstance(manufacturer_obj, dict) else manufacturer_obj.name
        
        # Find device type
        device_types = client.dcim.device_types.filter(manufacturer_id=manufacturer_id, model=model)
        if not device_types:
            return {
                "success": False,
                "error": f"Device type '{model}' by '{manufacturer}' not found",
                "error_type": "DeviceTypeNotFound"
            }
        
        device_type = device_types[0]
        
        # Apply defensive dict/object handling
        device_type_id = device_type.get('id') if isinstance(device_type, dict) else device_type.id
        device_model = device_type.get('model') if isinstance(device_type, dict) else device_type.model
        u_height = device_type.get('u_height') if isinstance(device_type, dict) else device_type.u_height
        is_full_depth = device_type.get('is_full_depth') if isinstance(device_type, dict) else device_type.is_full_depth
        part_number = device_type.get('part_number') if isinstance(device_type, dict) else getattr(device_type, 'part_number', None)
        description = device_type.get('description') if isinstance(device_type, dict) else getattr(device_type, 'description', '')
        slug = device_type.get('slug') if isinstance(device_type, dict) else device_type.slug
        
        # Count devices using this device type
        devices_using_type = list(client.dcim.devices.filter(device_type_id=device_type_id))
        device_count = len(devices_using_type)
        
        # Get component templates count
        interface_templates = list(client.dcim.interface_templates.filter(device_type_id=device_type_id))
        power_port_templates = list(client.dcim.power_port_templates.filter(device_type_id=device_type_id))
        console_port_templates = list(client.dcim.console_port_templates.filter(device_type_id=device_type_id))
        console_server_port_templates = list(client.dcim.console_server_port_templates.filter(device_type_id=device_type_id))
        power_outlet_templates = list(client.dcim.power_outlet_templates.filter(device_type_id=device_type_id))
        front_port_templates = list(client.dcim.front_port_templates.filter(device_type_id=device_type_id))
        rear_port_templates = list(client.dcim.rear_port_templates.filter(device_type_id=device_type_id))
        device_bay_templates = list(client.dcim.device_bay_templates.filter(device_type_id=device_type_id))
        module_bay_templates = list(client.dcim.module_bay_templates.filter(device_type_id=device_type_id))
        
        component_summary = {
            "interface_templates": len(interface_templates),
            "power_port_templates": len(power_port_templates),
            "console_port_templates": len(console_port_templates),
            "console_server_port_templates": len(console_server_port_templates),
            "power_outlet_templates": len(power_outlet_templates),
            "front_port_templates": len(front_port_templates),
            "rear_port_templates": len(rear_port_templates),
            "device_bay_templates": len(device_bay_templates),
            "module_bay_templates": len(module_bay_templates),
            "total_templates": (
                len(interface_templates) + len(power_port_templates) + 
                len(console_port_templates) + len(console_server_port_templates) +
                len(power_outlet_templates) + len(front_port_templates) +
                len(rear_port_templates) + len(device_bay_templates) +
                len(module_bay_templates)
            )
        }
        
        return {
            "success": True,
            "device_type": {
                "id": device_type_id,
                "model": device_model,
                "manufacturer": {
                    "name": manufacturer_name,
                    "id": manufacturer_id
                },
                "slug": slug,
                "u_height": u_height,
                "is_full_depth": is_full_depth,
                "part_number": part_number,
                "description": description,
                "device_count": device_count,
                "component_templates": component_summary
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get device type info for {model} by {manufacturer}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# Read-only device type tools - write operations removed for DeepAgents context optimization