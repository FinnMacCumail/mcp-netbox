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


# TODO: Implement advanced device type management tools:
# - netbox_get_device_type_specifications
# - netbox_update_device_type_properties
# - netbox_get_compatible_device_types
# - netbox_clone_device_type_template