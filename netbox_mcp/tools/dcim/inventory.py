#!/usr/bin/env python3
"""
DCIM Inventory Management Tools

⚠️ **DEPRECATION WARNING**: NetBox v4.3+ has deprecated inventory items in favor of modules.
These tools will become obsolete in future NetBox releases. Consider using module 
management tools instead for new implementations.

Enterprise-grade tools for managing NetBox inventory items and inventory item templates.
These tools enable comprehensive tracking of device components, assets, and hierarchical
inventory management for complete device lifecycle documentation.

Key Features:
- Inventory Item Template Management: Define standard inventory for device types
- Device Inventory Management: Track actual inventory items on devices
- Component Tracking: Link inventory to device components
- Asset Management: Serial numbers, asset tags, part numbers
- Hierarchical Inventory: Parent/child relationships for complex assemblies

Common Use Cases:
- Memory Modules: RAM, cache memory, storage controllers
- Expansion Cards: Network cards, storage adapters, compute accelerators
- Rack Components: Power supplies, fans, controllers
- Network Components: Transceivers, line cards, modules
- Custom Components: Any trackable asset or component

Migration Path:
- Inventory Item Templates → Module Types
- Inventory Items → Modules with enhanced functionality and user-defined attributes
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient
from ...exceptions import (
    NetBoxValidationError as ValidationError,
    NetBoxNotFoundError as NotFoundError,
    NetBoxConflictError as ConflictError
)

logger = logging.getLogger(__name__)


def normalize_device_name(device_name: str) -> str:
    """Normalize device name for consistent lookup."""
    return device_name.strip().lower()


@mcp_tool(category="dcim")
def netbox_list_inventory_item_templates_for_device_type(
    client: NetBoxClient,
    device_type_model: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    List all inventory item templates for a specific device type.
    
    This tool provides comprehensive visibility into standardized inventory
    definitions for device types, enabling inventory planning and compliance
    verification across device deployments.
    
    Args:
        client: NetBoxClient instance (injected)
        device_type_model: Device type model name
        limit: Maximum number of templates to return (default: 100)
        
    Returns:
        List of inventory item templates with comprehensive details
        
    Example:
        netbox_list_inventory_item_templates_for_device_type(
            device_type_model="PowerEdge R750"
        )
    """
    
    if not device_type_model or not device_type_model.strip():
        raise ValidationError("Device type model cannot be empty")
    
    logger.info(f"Listing Inventory Item Templates for Device Type '{device_type_model}'")
    
    # STEP 1: LOOKUP DEVICE TYPE
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            device_types = client.dcim.device_types.filter(slug=device_type_model.lower().replace(' ', '-'))
        
        if not device_types:
            raise NotFoundError(f"Device Type '{device_type_model}' not found")
        
        device_type = device_types[0]
        device_type_id = device_type.get('id') if isinstance(device_type, dict) else device_type.id
        device_type_display = device_type.get('display', device_type_model) if isinstance(device_type, dict) else getattr(device_type, 'display', device_type_model)
        
    except Exception as e:
        raise NotFoundError(f"Could not find device type '{device_type_model}': {e}")
    
    # STEP 2: GET INVENTORY ITEM TEMPLATES
    try:
        templates = client.dcim.inventory_item_templates.filter(
            device_type_id=device_type_id,
            limit=limit
        )
        
        if not templates:
            return {
                "success": True,
                "message": f"No inventory item templates found for Device Type '{device_type_model}'.",
                "data": {
                    "device_type_model": device_type_model,
                    "device_type_id": device_type_id,
                    "template_count": 0,
                    "templates": []
                }
            }
        
        # Process templates with defensive handling
        template_list = []
        for template in templates:
            template_data = {
                "id": template.get('id') if isinstance(template, dict) else template.id,
                "name": template.get('name') if isinstance(template, dict) else template.name,
                "component_type": template.get('component_type') if isinstance(template, dict) else getattr(template, 'component_type', None),
                "component_id": template.get('component_id') if isinstance(template, dict) else getattr(template, 'component_id', None),
                "description": template.get('description') if isinstance(template, dict) else getattr(template, 'description', ''),
                "part_id": template.get('part_id') if isinstance(template, dict) else getattr(template, 'part_id', None)
            }
            template_list.append(template_data)
        
        # Sort by name for consistent output
        template_list.sort(key=lambda x: x['name'])
        
        return {
            "success": True,
            "message": f"Found {len(template_list)} inventory item template(s) for Device Type '{device_type_model}'.",
            "data": {
                "device_type_model": device_type_model,
                "device_type_display": device_type_display,
                "device_type_id": device_type_id,
                "template_count": len(template_list),
                "templates": template_list
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving inventory item templates: {e}")
        raise ValidationError(f"Error retrieving inventory item templates for device type '{device_type_model}': {e}")


@mcp_tool(category="dcim")
def netbox_list_device_inventory(
    client: NetBoxClient,
    device_name: str,
    component_type: Optional[str] = None,
    include_hierarchy: bool = True
) -> Dict[str, Any]:
    """
    List all inventory items for a specific device with comprehensive details.
    
    This tool provides complete visibility into device inventory, supporting
    filtering by component type and hierarchical display for complex assemblies.
    Essential for asset management, compliance auditing, and inventory reporting.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Target device name
        component_type: Optional filter by component type
        include_hierarchy: Include parent/child relationship information
        
    Returns:
        Comprehensive inventory listing with hierarchy and asset details
        
    Example:
        netbox_list_device_inventory(
            device_name="srv-web-01",
            component_type="Storage"
        )
    """
    
    if not device_name or not device_name.strip():
        raise ValidationError("Device name cannot be empty")
    
    device_name_normalized = normalize_device_name(device_name)
    logger.info(f"Listing Inventory for Device '{device_name}'")
    
    # STEP 1: LOOKUP DEVICE
    try:
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            # Try case-insensitive search
            all_devices = client.dcim.devices.all()
            devices = [d for d in all_devices if normalize_device_name(
                d.get('name') if isinstance(d, dict) else d.name
            ) == device_name_normalized]
        
        if not devices:
            raise NotFoundError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_display = device.get('display', device_name) if isinstance(device, dict) else getattr(device, 'display', device_name)
        
    except Exception as e:
        raise NotFoundError(f"Could not find device '{device_name}': {e}")
    
    # STEP 2: GET INVENTORY ITEMS
    try:
        filter_params = {"device_id": device_id}
        if component_type:
            filter_params["component_type"] = component_type
        
        inventory_items = client.dcim.inventory_items.filter(**filter_params)
        
        if not inventory_items:
            filter_desc = f" with component type '{component_type}'" if component_type else ""
            return {
                "success": True,
                "message": f"No inventory items found for Device '{device_name}'{filter_desc}.",
                "data": {
                    "device_name": device_name,
                    "device_id": device_id,
                    "inventory_count": 0,
                    "inventory_items": []
                }
            }
        
        # Process inventory items with defensive handling
        item_list = []
        for item in inventory_items:
            # Get manufacturer info if available
            manufacturer_obj = item.get('manufacturer') if isinstance(item, dict) else getattr(item, 'manufacturer', None)
            manufacturer_name = None
            if manufacturer_obj:
                if isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get('name')
                else:
                    manufacturer_name = getattr(manufacturer_obj, 'name', None) if hasattr(manufacturer_obj, 'name') else str(manufacturer_obj)
            
            # Get parent item info if available
            parent_obj = item.get('parent') if isinstance(item, dict) else getattr(item, 'parent', None)
            parent_name = None
            if parent_obj:
                if isinstance(parent_obj, dict):
                    parent_name = parent_obj.get('name')
                else:
                    parent_name = getattr(parent_obj, 'name', None) if hasattr(parent_obj, 'name') else str(parent_obj)
            
            item_data = {
                "id": item.get('id') if isinstance(item, dict) else item.id,
                "name": item.get('name') if isinstance(item, dict) else item.name,
                "component_type": item.get('component_type') if isinstance(item, dict) else getattr(item, 'component_type', None),
                "component_id": item.get('component_id') if isinstance(item, dict) else getattr(item, 'component_id', None),
                "description": item.get('description') if isinstance(item, dict) else getattr(item, 'description', ''),
                "part_id": item.get('part_id') if isinstance(item, dict) else getattr(item, 'part_id', None),
                "serial": item.get('serial') if isinstance(item, dict) else getattr(item, 'serial', None),
                "asset_tag": item.get('asset_tag') if isinstance(item, dict) else getattr(item, 'asset_tag', None),
                "manufacturer": manufacturer_name,
                "parent_item": parent_name if include_hierarchy else None
            }
            item_list.append(item_data)
        
        # Sort by name for consistent output
        item_list.sort(key=lambda x: x['name'])
        
        # Generate summary statistics
        component_types = {}
        manufacturers = {}
        items_with_serial = 0
        
        for item in item_list:
            # Component type stats
            comp_type = item['component_type'] or 'Unknown'
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
            
            # Manufacturer stats
            mfg = item['manufacturer'] or 'Unknown'
            manufacturers[mfg] = manufacturers.get(mfg, 0) + 1
            
            # Serial number tracking
            if item['serial']:
                items_with_serial += 1
        
        return {
            "success": True,
            "message": f"Found {len(item_list)} inventory item(s) for Device '{device_name}'.",
            "data": {
                "device_name": device_name,
                "device_display": device_display,
                "device_id": device_id,
                "inventory_count": len(item_list),
                "inventory_items": item_list,
                "summary": {
                    "component_types": component_types,
                    "manufacturers": manufacturers,
                    "items_with_serial": items_with_serial,
                    "total_items": len(item_list)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving inventory items: {e}")
        raise ValidationError(f"Error retrieving inventory items for device '{device_name}': {e}")


# Read-only inventory tools - write operations removed for DeepAgents context optimization