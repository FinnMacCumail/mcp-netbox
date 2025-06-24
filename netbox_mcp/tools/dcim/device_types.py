#!/usr/bin/env python3
"""
DCIM Device Type Management Tools

High-level tools for managing NetBox device types with enterprise-grade functionality.
"""

from typing import Dict, List, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_create_device_type(
    client: NetBoxClient,
    model: str,
    manufacturer: str,
    slug: str,
    u_height: int = 1,
    is_full_depth: bool = True,
    part_number: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new device type in NetBox DCIM.
    
    Args:
        client: NetBoxClient instance (injected)
        model: Device model name
        manufacturer: Manufacturer name or slug
        slug: URL-friendly identifier
        u_height: Height in rack units (1-100)
        is_full_depth: Whether device takes full rack depth
        part_number: Manufacturer part number
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created device type information or error details
        
    Example:
        netbox_create_device_type("ISR4331", "cisco", "isr4331", u_height=2, confirm=True)
    """
    try:
        if not model or not manufacturer or not slug:
            return {
                "success": False,
                "error": "Model, manufacturer, and slug are required",
                "error_type": "ValidationError"
            }
        
        if not (1 <= u_height <= 100):
            return {
                "success": False,
                "error": "U-height must be between 1 and 100",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating device type: {model} ({manufacturer})")
        
        # Resolve manufacturer to ID if slug provided
        manufacturer_id = manufacturer
        if isinstance(manufacturer, str) and not manufacturer.isdigit():
            # Try to find manufacturer by slug or name
            manufacturers = client.dcim.manufacturers.filter(slug=manufacturer)
            if not manufacturers:
                manufacturers = client.dcim.manufacturers.filter(name=manufacturer)
            if manufacturers:
                manufacturer_id = manufacturers[0]["id"]
            else:
                return {
                    "success": False,
                    "error": f"Manufacturer '{manufacturer}' not found",
                    "error_type": "ManufacturerNotFound"
                }
        
        # Build device type data
        device_type_data = {
            "model": model,
            "manufacturer": manufacturer_id,
            "slug": slug,
            "u_height": u_height,
            "is_full_depth": is_full_depth
        }
        
        if part_number:
            device_type_data["part_number"] = part_number
        if description:
            device_type_data["description"] = description
        
        # Use dynamic API with safety
        result = client.dcim.device_types.create(confirm=confirm, **device_type_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "device_type",
            "device_type": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create device type {model}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


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
            # Get manufacturer information
            manufacturer_name = "Unknown"
            if device_type.manufacturer:
                if hasattr(device_type.manufacturer, 'name'):
                    manufacturer_name = device_type.manufacturer.name
                else:
                    # If it's an ID, look up the manufacturer
                    try:
                        manufacturer_obj = client.dcim.manufacturers.get(device_type.manufacturer)
                        manufacturer_name = manufacturer_obj.name if hasattr(manufacturer_obj, 'name') else str(device_type.manufacturer)
                    except:
                        manufacturer_name = str(device_type.manufacturer)
            
            # Manufacturer breakdown
            manufacturer_counts[manufacturer_name] = manufacturer_counts.get(manufacturer_name, 0) + 1
            
            # U-height breakdown
            u_height = device_type.u_height if hasattr(device_type, 'u_height') else 1
            u_height_counts[f"{u_height}U"] = u_height_counts.get(f"{u_height}U", 0) + 1
            
            # Get devices using this device type
            devices_of_type = list(client.dcim.devices.filter(device_type_id=device_type.id))
            device_count = len(devices_of_type)
            total_devices += device_count
            if device_count > 0:
                device_types_with_devices += 1
            
            device_type_info = {
                "model": device_type.model,
                "manufacturer": manufacturer_name,
                "slug": device_type.slug,
                "u_height": u_height,
                "is_full_depth": device_type.is_full_depth if hasattr(device_type, 'is_full_depth') else None,
                "part_number": device_type.part_number if hasattr(device_type, 'part_number') else None,
                "description": device_type.description if hasattr(device_type, 'description') else None,
                "device_count": device_count,
                "created": device_type.created if hasattr(device_type, 'created') else None,
                "last_updated": device_type.last_updated if hasattr(device_type, 'last_updated') else None
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


# TODO: Implement advanced device type management tools:
# - netbox_get_device_type_specifications
# - netbox_update_device_type_properties
# - netbox_get_compatible_device_types
# - netbox_clone_device_type_template