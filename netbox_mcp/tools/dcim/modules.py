#!/usr/bin/env python3
"""
DCIM Module Management Tools - Read-Only Operations

Comprehensive enterprise-grade tools for inspecting NetBox modules, module types, and modular components.
Provides read-only access to modular infrastructure with dual-tool pattern architecture.

Key Features:
- Module Types Discovery: Browse module catalog with specifications
- Module Inspection: View modules installed in device module bays  
- Module Lifecycle: List and inspect modules
- Module Bay Management: Bay inspection and availability tracking
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


# ======================================================================
# UTILITY FUNCTIONS
# ======================================================================

def get_expanded_modules(client: NetBoxClient, **filter_params) -> list:
    """
    Get modules with consistent field expansion for enhanced relational data display.
    
    RESOLVED: pynetbox 7.5.0 supports expand parameters. This utility function
    now provides expanded module data including module_type.model, manufacturer.name,
    and module_bay.name for improved user experience.
    
    Args:
        client: NetBoxClient instance
        **filter_params: Filter parameters for module query
        
    Returns:
        List of modules with expanded relational data
    """
    # Use expand parameters to get full relational data
    return list(client.dcim.modules.filter(expand="module_type,module_bay,device", **filter_params))


# ======================================================================
# MODULE TYPE DISCOVERY TOOLS
# ======================================================================

@mcp_tool(category="dcim")
def netbox_list_all_module_types(
    client: NetBoxClient,
    manufacturer: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    List all module types in NetBox with comprehensive filtering and statistics.
    
    This discovery tool provides bulk module type exploration with filtering capabilities
    and summary statistics. Essential for module catalog management and infrastructure
    planning across modular equipment deployments.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        manufacturer: Filter by manufacturer name (optional)
        limit: Maximum number of results to return (default: 100)
        
    Returns:
        Dictionary containing:
        - count: Total number of module types found
        - module_types: List of summarized module type information
        - filters_applied: Dictionary of filters that were applied
        - summary_stats: Aggregate statistics about the module types
        
    Example:
        netbox_list_all_module_types()
        netbox_list_all_module_types(manufacturer="Cisco")
        netbox_list_all_module_types(limit=25)
    """
    try:
        logger.info(f"Listing module types with filters - manufacturer: {manufacturer}")
        
        # Build filters dictionary - only include non-None values
        filters = {}
        if manufacturer:
            filters['manufacturer'] = manufacturer
        
        # Execute filtered query
        module_types = list(client.dcim.module_types.filter(**filters))
        
        # Apply limit after fetching
        if len(module_types) > limit:
            module_types = module_types[:limit]
        
        # Generate summary statistics
        manufacturer_counts = {}
        total_modules = 0
        module_types_with_instances = 0
        
        # Create human-readable module type list
        type_list = []
        for module_type in module_types:
            # Manufacturer breakdown with defensive dictionary access
            manufacturer_obj = module_type.get("manufacturer", {})
            if isinstance(manufacturer_obj, dict):
                manufacturer_name = manufacturer_obj.get("name", str(manufacturer_obj))
            else:
                manufacturer_name = str(manufacturer_obj) if manufacturer_obj else "Unknown"
            manufacturer_counts[manufacturer_name] = manufacturer_counts.get(manufacturer_name, 0) + 1
            
            # Get instances of this module type
            module_type_id = module_type.get("id")
            module_instances = list(client.dcim.modules.filter(module_type_id=module_type_id))
            instance_count = len(module_instances)
            total_modules += instance_count
            if instance_count > 0:
                module_types_with_instances += 1
            
            type_info = {
                "model": module_type.get("model", "Unknown"),
                "manufacturer": manufacturer_name,
                "part_number": module_type.get("part_number"),
                "description": module_type.get("description"),
                "instance_count": instance_count,
                "weight": module_type.get("weight"),
                "weight_unit": module_type.get("weight_unit"),
                "created": module_type.get("created"),
                "last_updated": module_type.get("last_updated")
            }
            type_list.append(type_info)
        
        # Sort by instance count (most used first)
        type_list.sort(key=lambda t: t['instance_count'], reverse=True)
        
        result = {
            "count": len(type_list),
            "module_types": type_list,
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
            "summary_stats": {
                "total_module_types": len(type_list),
                "manufacturer_breakdown": manufacturer_counts,
                "total_module_instances": total_modules,
                "types_with_instances": module_types_with_instances,
                "types_without_instances": len(type_list) - module_types_with_instances,
                "average_instances_per_type": round(total_modules / len(type_list), 1) if type_list else 0,
                "most_deployed_types": [t["model"] for t in type_list[:5] if t["instance_count"] > 0]
            }
        }
        
        logger.info(f"Found {len(type_list)} module types matching criteria. Total instances: {total_modules}")
        return result
        
    except Exception as e:
        logger.error(f"Error listing module types: {e}")
        return {
            "count": 0,
            "module_types": [],
            "error": str(e),
            "error_type": type(e).__name__,
            "filters_applied": {k: v for k, v in {
                'manufacturer': manufacturer
            }.items() if v is not None}
        }


@mcp_tool(category="dcim")
def netbox_get_module_type_info(
    client: NetBoxClient,
    manufacturer: str,
    model: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific module type.
    
    This inspection tool provides comprehensive module type details including
    specifications, usage statistics, and component templates. Essential for
    module selection, compatibility verification, and hardware planning.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        manufacturer: Name or slug of the manufacturer
        model: Model name of the module type
        
    Returns:
        Dictionary containing detailed module type information
        
    Example:
        netbox_get_module_type_info("Cisco", "SFP-10G-LR")
        netbox_get_module_type_info("Arista", "QSFP-40G-SR4")
    """
    try:
        logger.info(f"Looking up module type: {manufacturer} {model}")
        
        # Step 1: Resolve manufacturer
        logger.debug(f"Resolving manufacturer: {manufacturer}")
        manufacturers = client.dcim.manufacturers.filter(name=manufacturer)
        if not manufacturers:
            manufacturers = client.dcim.manufacturers.filter(slug=manufacturer)
        
        if not manufacturers:
            return {
                "success": False,
                "error": f"Manufacturer '{manufacturer}' not found",
                "error_type": "NotFoundError"
            }
        
        manufacturer_obj = manufacturers[0]
        manufacturer_id = manufacturer_obj["id"]
        logger.debug(f"Found manufacturer: {manufacturer_obj['name']} (ID: {manufacturer_id})")
        
        # Step 2: Find module type
        logger.debug(f"Finding module type: {model}")
        module_types = client.dcim.module_types.filter(
            manufacturer=manufacturer_id,
            model=model
        )
        
        if not module_types:
            return {
                "success": False,
                "error": f"Module type '{model}' not found for manufacturer '{manufacturer_obj['name']}'",
                "error_type": "NotFoundError"
            }
        
        module_type = module_types[0]
        module_type_id = module_type["id"]
        logger.debug(f"Found module type: {module_type['model']} (ID: {module_type_id})")
        
        # Step 3: Get usage statistics
        logger.debug("Collecting module instances and usage statistics...")
        module_instances = list(client.dcim.modules.filter(module_type=module_type_id))
        
        # Analyze deployment patterns
        device_assignments = {}
        status_counts = {}
        bay_assignments = {}
        
        for module in module_instances:
            # Device breakdown
            device_obj = module.get("device", {})
            if isinstance(device_obj, dict):
                device_name = device_obj.get("name", "Unknown")
            else:
                device_name = str(device_obj) if device_obj else "Unknown"
            device_assignments[device_name] = device_assignments.get(device_name, 0) + 1
            
            # Bay breakdown
            bay_obj = module.get("module_bay", {})
            if isinstance(bay_obj, dict):
                bay_name = bay_obj.get("name", "Unknown")
            else:
                bay_name = str(bay_obj) if bay_obj else "Unknown"
            bay_assignments[bay_name] = bay_assignments.get(bay_name, 0) + 1
        
        result = {
            "success": True,
            "module_type": {
                "id": module_type_id,
                "model": module_type.get("model"),
                "manufacturer": {
                    "id": manufacturer_obj["id"],
                    "name": manufacturer_obj["name"],
                    "slug": manufacturer_obj.get("slug")
                },
                "part_number": module_type.get("part_number"),
                "description": module_type.get("description"),
                "weight": module_type.get("weight"),
                "weight_unit": module_type.get("weight_unit"),
                "url": module_type.get("url"),
                "display_url": module_type.get("display_url"),
                "created": module_type.get("created"),
                "last_updated": module_type.get("last_updated")
            },
            "usage_statistics": {
                "total_instances": len(module_instances),
                "device_assignments": device_assignments,
                "bay_assignments": bay_assignments,
                "deployment_summary": {
                    "devices_using_this_type": len(device_assignments),
                    "most_common_device": max(device_assignments.items(), key=lambda x: x[1])[0] if device_assignments else None,
                    "most_common_bay": max(bay_assignments.items(), key=lambda x: x[1])[0] if bay_assignments else None
                }
            },
            "relationships": {
                "manufacturer_url": manufacturer_obj.get("url"),
                "manufacturer_display_url": manufacturer_obj.get("display_url")
            }
        }
        
        logger.info(f"✅ Module type details retrieved: {len(module_instances)} instances found")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get module type info for {manufacturer} {model}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ======================================================================
# MODULE DISCOVERY TOOLS
# ======================================================================

@mcp_tool(category="dcim")
def netbox_list_all_modules(
    client: NetBoxClient,
    device_name: Optional[str] = None,
    module_type: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    List all modules in NetBox with comprehensive filtering and expanded data display.
    
    This discovery tool provides bulk module exploration across the NetBox infrastructure
    with enhanced relational data display including module type models, manufacturer names,
    and module bay names. Essential for module inventory management and planning.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        device_name: Filter by device name (optional)
        module_type: Filter by module type model (optional)
        limit: Maximum number of results to return (default: 100)
        
    Returns:
        Dictionary containing:
        - count: Total number of modules found
        - modules: List of summarized module information with expanded data
        - filters_applied: Dictionary of filters that were applied
        - summary_stats: Aggregate statistics about the modules
        
    Example:
        netbox_list_all_modules()
        netbox_list_all_modules(device_name="core-switch-01")
        netbox_list_all_modules(module_type="SFP-10G-LR")
    """
    try:
        logger.info(f"Listing modules with filters - device: {device_name}, type: {module_type}")
        
        # Build filters dictionary - only include non-None values
        filters = {}
        
        # Resolve device filter if provided
        if device_name:
            logger.debug(f"Resolving device filter: {device_name}")
            devices = client.dcim.devices.filter(name=device_name)
            if devices:
                filters['device'] = devices[0]["id"]
                logger.debug(f"Found device for filter: {devices[0]['name']} (ID: {devices[0]['id']})")
            else:
                logger.warning(f"Device filter '{device_name}' not found, proceeding without device filtering")
        
        # Resolve module type filter if provided
        if module_type:
            logger.debug(f"Resolving module type filter: {module_type}")
            module_types = client.dcim.module_types.filter(model=module_type)
            if module_types:
                filters['module_type'] = module_types[0]["id"]
                logger.debug(f"Found module type for filter: {module_types[0]['model']} (ID: {module_types[0]['id']})")
            else:
                logger.warning(f"Module type filter '{module_type}' not found, proceeding without type filtering")
        
        # Execute filtered query with expanded data
        modules = get_expanded_modules(client, **filters)
        
        # Apply limit after fetching
        if len(modules) > limit:
            modules = modules[:limit]
        
        # Generate summary statistics
        device_counts = {}
        type_counts = {}
        bay_counts = {}
        manufacturer_counts = {}
        
        # Create human-readable module list
        module_list = []
        for module in modules:
            # Device breakdown with expanded data
            device_obj = module.get("device", {})
            if isinstance(device_obj, dict):
                device_name = device_obj.get("name", str(device_obj))
            else:
                device_name = str(device_obj) if device_obj else "Unknown"
            device_counts[device_name] = device_counts.get(device_name, 0) + 1
            
            # Module type breakdown with expanded data
            module_type_obj = module.get("module_type", {})
            if isinstance(module_type_obj, dict):
                type_model = module_type_obj.get("model", str(module_type_obj))
                # Get manufacturer from expanded module type
                manufacturer_obj = module_type_obj.get("manufacturer", {})
                if isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get("name", "Unknown")
                else:
                    manufacturer_name = str(manufacturer_obj) if manufacturer_obj else "Unknown"
            else:
                type_model = str(module_type_obj) if module_type_obj else "Unknown"
                manufacturer_name = "Unknown"
            
            type_counts[type_model] = type_counts.get(type_model, 0) + 1
            manufacturer_counts[manufacturer_name] = manufacturer_counts.get(manufacturer_name, 0) + 1
            
            # Bay breakdown with expanded data
            bay_obj = module.get("module_bay", {})
            if isinstance(bay_obj, dict):
                bay_name = bay_obj.get("name", str(bay_obj))
            else:
                bay_name = str(bay_obj) if bay_obj else "Unknown"
            bay_counts[bay_name] = bay_counts.get(bay_name, 0) + 1
            
            module_info = {
                "id": module.get("id"),
                "device": device_name,
                "module_bay": bay_name,
                "module_type": {
                    "model": type_model,
                    "manufacturer": manufacturer_name
                },
                "serial": module.get("serial"),
                "asset_tag": module.get("asset_tag"),
                "description": module.get("description"),
                "url": module.get("url"),
                "display_url": module.get("display_url")
            }
            module_list.append(module_info)
        
        result = {
            "count": len(module_list),
            "modules": module_list,
            "filters_applied": {k: v for k, v in {
                'device_name': device_name,
                'module_type': module_type
            }.items() if v is not None},
            "summary_stats": {
                "total_modules": len(module_list),
                "device_breakdown": device_counts,
                "type_breakdown": type_counts,
                "manufacturer_breakdown": manufacturer_counts,
                "bay_breakdown": bay_counts,
                "unique_devices": len(device_counts),
                "unique_types": len(type_counts),
                "unique_manufacturers": len(manufacturer_counts),
                "modules_with_serials": len([m for m in module_list if m.get("serial")]),
                "modules_with_asset_tags": len([m for m in module_list if m.get("asset_tag")])
            }
        }
        
        logger.info(f"Found {len(module_list)} modules matching criteria. Device breakdown: {device_counts}")
        return result
        
    except Exception as e:
        logger.error(f"Error listing modules: {e}")
        return {
            "count": 0,
            "modules": [],
            "error": str(e),
            "error_type": type(e).__name__,
            "filters_applied": {k: v for k, v in {
                'device_name': device_name,
                'module_type': module_type
            }.items() if v is not None}
        }


@mcp_tool(category="dcim")
def netbox_list_device_modules(
    client: NetBoxClient,
    device_name: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    List all modules installed on a specific device with comprehensive details.
    
    This discovery tool provides complete module inventory for a device including
    module types, serial numbers, bay assignments, and status information.
    Essential for device asset tracking and module lifecycle management.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        device_name: Name of the device to query
        limit: Maximum number of results to return (default: 100)
        
    Returns:
        Dictionary containing:
        - device: Device information
        - count: Total number of modules found
        - modules: List of detailed module information
        - summary_stats: Module statistics for this device
        
    Example:
        netbox_list_device_modules("core-switch-01")
        netbox_list_device_modules("chassis-01", limit=50)
    """
    try:
        logger.info(f"Listing modules for device: {device_name}")
        
        # Step 1: Resolve device
        logger.debug(f"Looking up device: {device_name}")
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "NotFoundError"
            }
        
        device_obj = devices[0]
        device_id = device_obj["id"]
        logger.debug(f"Found device: {device_obj['name']} (ID: {device_id})")
        
        # Step 2: Get modules for this device with expanded data
        logger.debug("Retrieving modules with expanded relational data...")
        modules = get_expanded_modules(client, device=device_id)
        
        # Apply limit after fetching
        if len(modules) > limit:
            modules = modules[:limit]
        
        # Step 3: Process modules with enhanced data
        module_list = []
        type_counts = {}
        manufacturer_counts = {}
        bay_usage = {}
        modules_with_serials = 0
        modules_with_asset_tags = 0
        
        for module in modules:
            # Module type breakdown with expanded data
            module_type_obj = module.get("module_type", {})
            if isinstance(module_type_obj, dict):
                type_model = module_type_obj.get("model", "Unknown")
                # Get manufacturer from expanded module type
                manufacturer_obj = module_type_obj.get("manufacturer", {})
                if isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get("name", "Unknown")
                else:
                    manufacturer_name = str(manufacturer_obj) if manufacturer_obj else "Unknown"
            else:
                type_model = str(module_type_obj) if module_type_obj else "Unknown"
                manufacturer_name = "Unknown"
            
            type_counts[type_model] = type_counts.get(type_model, 0) + 1
            manufacturer_counts[manufacturer_name] = manufacturer_counts.get(manufacturer_name, 0) + 1
            
            # Bay breakdown with expanded data
            bay_obj = module.get("module_bay", {})
            if isinstance(bay_obj, dict):
                bay_name = bay_obj.get("name", "Unknown")
                bay_position = bay_obj.get("position")
            else:
                bay_name = str(bay_obj) if bay_obj else "Unknown"
                bay_position = None
            bay_usage[bay_name] = bay_usage.get(bay_name, 0) + 1
            
            # Count modules with identifiers
            if module.get("serial"):
                modules_with_serials += 1
            if module.get("asset_tag"):
                modules_with_asset_tags += 1
            
            module_info = {
                "id": module.get("id"),
                "module_bay": {
                    "name": bay_name,
                    "position": bay_position
                },
                "module_type": {
                    "model": type_model,
                    "manufacturer": manufacturer_name,
                    "part_number": module_type_obj.get("part_number") if isinstance(module_type_obj, dict) else None
                },
                "serial": module.get("serial"),
                "asset_tag": module.get("asset_tag"),
                "description": module.get("description"),
                "url": module.get("url"),
                "display_url": module.get("display_url")
            }
            module_list.append(module_info)
        
        # Sort by bay position for logical ordering
        module_list.sort(key=lambda m: (m["module_bay"]["name"], m["module_bay"]["position"] or 0))
        
        result = {
            "success": True,
            "device": {
                "id": device_id,
                "name": device_obj["name"],
                "url": device_obj.get("url"),
                "display_url": device_obj.get("display_url")
            },
            "count": len(module_list),
            "modules": module_list,
            "summary_stats": {
                "total_modules": len(module_list),
                "type_breakdown": type_counts,
                "manufacturer_breakdown": manufacturer_counts,
                "bay_usage": bay_usage,
                "modules_with_serials": modules_with_serials,
                "modules_with_asset_tags": modules_with_asset_tags,
                "unique_types": len(type_counts),
                "unique_manufacturers": len(manufacturer_counts),
                "occupied_bays": len(bay_usage),
                "most_common_type": max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None,
                "most_common_manufacturer": max(manufacturer_counts.items(), key=lambda x: x[1])[0] if manufacturer_counts else None
            }
        }
        
        logger.info(f"✅ Found {len(module_list)} modules installed on device {device_name}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to list modules for device {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_module_info(
    client: NetBoxClient,
    device_name: str,
    module_bay: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific module installed in a device bay.
    
    This inspection tool provides comprehensive module details including type,
    specifications, serial numbers, and installation information. Essential for
    module troubleshooting and asset verification.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        device_name: Name of the device containing the module
        module_bay: Name of the module bay to inspect
        
    Returns:
        Dictionary containing detailed module information
        
    Example:
        netbox_get_module_info("core-switch-01", "slot-1")
        netbox_get_module_info("chassis-01", "line-card-3")
    """
    try:
        logger.info(f"Looking up module in device {device_name}, bay {module_bay}")
        
        # Step 1: Resolve device
        logger.debug(f"Looking up device: {device_name}")
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "NotFoundError"
            }
        
        device_obj = devices[0]
        device_id = device_obj["id"]
        logger.debug(f"Found device: {device_obj['name']} (ID: {device_id})")
        
        # Step 2: Find module bay
        logger.debug(f"Finding module bay: {module_bay}")
        module_bays = client.dcim.module_bays.filter(
            device_id=device_id,
            name=module_bay
        )
        
        if not module_bays:
            return {
                "success": False,
                "error": f"Module bay '{module_bay}' not found on device '{device_name}'",
                "error_type": "NotFoundError"
            }
        
        bay_obj = module_bays[0]
        bay_id = bay_obj["id"]
        logger.debug(f"Found module bay: {bay_obj['name']} (ID: {bay_id})")
        
        # Step 3: Find module in bay with expanded data
        logger.debug("Looking for installed module...")
        modules = get_expanded_modules(client, module_bay=bay_id)
        
        if not modules:
            return {
                "success": False,
                "error": f"No module installed in bay '{module_bay}' on device '{device_name}'",
                "error_type": "NotFoundError"
            }
        
        module_obj = modules[0]
        module_id = module_obj["id"]
        logger.debug(f"Found installed module: ID {module_id}")
        
        # Step 4: Extract comprehensive module information
        # Module type details with expanded data
        module_type_obj = module_obj.get("module_type", {})
        if isinstance(module_type_obj, dict):
            module_type_info = {
                "id": module_type_obj.get("id"),
                "model": module_type_obj.get("model"),
                "part_number": module_type_obj.get("part_number"),
                "description": module_type_obj.get("description"),
                "weight": module_type_obj.get("weight"),
                "weight_unit": module_type_obj.get("weight_unit")
            }
            
            # Manufacturer details from expanded data
            manufacturer_obj = module_type_obj.get("manufacturer", {})
            if isinstance(manufacturer_obj, dict):
                module_type_info["manufacturer"] = {
                    "id": manufacturer_obj.get("id"),
                    "name": manufacturer_obj.get("name"),
                    "slug": manufacturer_obj.get("slug")
                }
            else:
                module_type_info["manufacturer"] = {"name": str(manufacturer_obj) if manufacturer_obj else "Unknown"}
        else:
            module_type_info = {"model": str(module_type_obj) if module_type_obj else "Unknown"}
        
        # Module bay details with expanded data
        bay_info = {
            "id": bay_id,
            "name": bay_obj.get("name"),
            "position": bay_obj.get("position"),
            "description": bay_obj.get("description")
        }
        
        result = {
            "success": True,
            "module": {
                "id": module_id,
                "serial": module_obj.get("serial"),
                "asset_tag": module_obj.get("asset_tag"),
                "description": module_obj.get("description"),
                "url": module_obj.get("url"),
                "display_url": module_obj.get("display_url")
            },
            "module_type": module_type_info,
            "module_bay": bay_info,
            "device": {
                "id": device_id,
                "name": device_obj["name"],
                "url": device_obj.get("url"),
                "display_url": device_obj.get("display_url")
            },
            "installation_details": {
                "bay_position": bay_obj.get("position"),
                "bay_description": bay_obj.get("description")
            }
        }
        
        logger.info(f"✅ Module details retrieved for {device_name}:{module_bay}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get module info for {device_name}:{module_bay}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ======================================================================
# MODULE BAY DISCOVERY TOOLS
# ======================================================================

@mcp_tool(category="dcim")
def netbox_list_device_module_bays(
    client: NetBoxClient,
    device_name: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    List all module bays on a specific device with availability and status information.
    
    This discovery tool provides complete module bay inventory for a device including
    bay names, positions, availability status, and installed modules. Essential for
    module planning and capacity management.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        device_name: Name of the device to query
        limit: Maximum number of results to return (default: 100)
        
    Returns:
        Dictionary containing:
        - device: Device information
        - count: Total number of module bays found
        - module_bays: List of detailed module bay information with availability
        - summary_stats: Bay statistics for this device
        
    Example:
        netbox_list_device_module_bays("core-switch-01")
        netbox_list_device_module_bays("chassis-01", limit=20)
    """
    try:
        logger.info(f"Listing module bays for device: {device_name}")
        
        # Step 1: Resolve device
        logger.debug(f"Looking up device: {device_name}")
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "NotFoundError"
            }
        
        device_obj = devices[0]
        device_id = device_obj["id"]
        logger.debug(f"Found device: {device_obj['name']} (ID: {device_id})")
        
        # Step 2: Get module bays for this device
        logger.debug("Retrieving module bays...")
        module_bays = list(client.dcim.module_bays.filter(device_id=device_id))
        
        # Apply limit after fetching
        if len(module_bays) > limit:
            module_bays = module_bays[:limit]
        
        # Step 3: Get installed modules to determine bay availability
        logger.debug("Checking bay occupancy...")
        installed_modules = get_expanded_modules(client, device=device_id)
        
        # Create mapping of bay ID to installed module
        bay_occupancy = {}
        for module in installed_modules:
            bay_obj = module.get("module_bay", {})
            if isinstance(bay_obj, dict):
                bay_id = bay_obj.get("id")
                if bay_id:
                    bay_occupancy[bay_id] = module
        
        # Step 4: Process module bays with availability information
        bay_list = []
        occupied_bays = 0
        available_bays = 0
        position_usage = {}
        
        for bay in module_bays:
            bay_id = bay.get("id")
            bay_position = bay.get("position")
            
            # Check if bay is occupied
            installed_module = bay_occupancy.get(bay_id)
            is_occupied = installed_module is not None
            
            if is_occupied:
                occupied_bays += 1
                # Get module type information from installed module
                module_type_obj = installed_module.get("module_type", {})
                if isinstance(module_type_obj, dict):
                    installed_module_info = {
                        "model": module_type_obj.get("model"),
                        "serial": installed_module.get("serial"),
                        "asset_tag": installed_module.get("asset_tag")
                    }
                else:
                    installed_module_info = {"model": str(module_type_obj) if module_type_obj else "Unknown"}
            else:
                available_bays += 1
                installed_module_info = None
            
            # Position usage tracking
            if bay_position:
                position_usage[bay_position] = position_usage.get(bay_position, 0) + 1
            
            bay_info = {
                "id": bay_id,
                "name": bay.get("name"),
                "position": bay_position,
                "description": bay.get("description"),
                "is_occupied": is_occupied,
                "installed_module": installed_module_info
            }
            bay_list.append(bay_info)
        
        # Sort by position for logical ordering
        bay_list.sort(key=lambda b: b["position"] or 0)
        
        result = {
            "success": True,
            "device": {
                "id": device_id,
                "name": device_obj["name"],
                "url": device_obj.get("url"),
                "display_url": device_obj.get("display_url")
            },
            "count": len(bay_list),
            "module_bays": bay_list,
            "summary_stats": {
                "total_bays": len(bay_list),
                "occupied_bays": occupied_bays,
                "available_bays": available_bays,
                "occupancy_rate": round((occupied_bays / len(bay_list)) * 100, 1) if bay_list else 0,
                "position_usage": position_usage,
                "next_available_bay": next((bay["name"] for bay in bay_list if not bay["is_occupied"]), None),
                "capacity_status": "Full" if available_bays == 0 else f"{available_bays} slots available"
            }
        }
        
        logger.info(f"✅ Found {len(bay_list)} module bays on device {device_name} ({occupied_bays} occupied, {available_bays} available)")
        return result
        
    except Exception as e:
        logger.error(f"Failed to list module bays for device {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_module_bay_info(
    client: NetBoxClient,
    device_name: str,
    module_bay: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific module bay on a device.
    
    This inspection tool provides comprehensive module bay details including
    specifications, availability status, installed module information, and
    supported module types. Essential for module planning and compatibility verification.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        device_name: Name of the device containing the module bay
        module_bay: Name of the module bay to inspect
        
    Returns:
        Dictionary containing detailed module bay information
        
    Example:
        netbox_get_module_bay_info("core-switch-01", "slot-1")
        netbox_get_module_bay_info("chassis-01", "line-card-3")
    """
    try:
        logger.info(f"Looking up module bay {module_bay} on device {device_name}")
        
        # Step 1: Resolve device
        logger.debug(f"Looking up device: {device_name}")
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "NotFoundError"
            }
        
        device_obj = devices[0]
        device_id = device_obj["id"]
        logger.debug(f"Found device: {device_obj['name']} (ID: {device_id})")
        
        # Step 2: Find module bay
        logger.debug(f"Finding module bay: {module_bay}")
        module_bays = client.dcim.module_bays.filter(
            device_id=device_id,
            name=module_bay
        )
        
        if not module_bays:
            return {
                "success": False,
                "error": f"Module bay '{module_bay}' not found on device '{device_name}'",
                "error_type": "NotFoundError"
            }
        
        bay_obj = module_bays[0]
        bay_id = bay_obj["id"]
        logger.debug(f"Found module bay: {bay_obj['name']} (ID: {bay_id})")
        
        # Step 3: Check for installed module with expanded data
        logger.debug("Checking for installed module...")
        installed_modules = get_expanded_modules(client, module_bay=bay_id)
        
        installed_module_info = None
        if installed_modules:
            module = installed_modules[0]
            
            # Get module type information with expanded data
            module_type_obj = module.get("module_type", {})
            if isinstance(module_type_obj, dict):
                module_type_info = {
                    "id": module_type_obj.get("id"),
                    "model": module_type_obj.get("model"),
                    "part_number": module_type_obj.get("part_number"),
                    "description": module_type_obj.get("description")
                }
                
                # Manufacturer from expanded data
                manufacturer_obj = module_type_obj.get("manufacturer", {})
                if isinstance(manufacturer_obj, dict):
                    module_type_info["manufacturer"] = manufacturer_obj.get("name")
                else:
                    module_type_info["manufacturer"] = str(manufacturer_obj) if manufacturer_obj else "Unknown"
            else:
                module_type_info = {"model": str(module_type_obj) if module_type_obj else "Unknown"}
            
            installed_module_info = {
                "id": module.get("id"),
                "serial": module.get("serial"),
                "asset_tag": module.get("asset_tag"),
                "description": module.get("description"),
                "module_type": module_type_info,
                "url": module.get("url"),
                "display_url": module.get("display_url")
            }
        
        # Step 4: Gather bay specifications and capabilities
        bay_specifications = {
            "position": bay_obj.get("position"),
            "description": bay_obj.get("description")
        }
        
        result = {
            "success": True,
            "module_bay": {
                "id": bay_id,
                "name": bay_obj.get("name"),
                "position": bay_obj.get("position"),
                "description": bay_obj.get("description"),
                "url": bay_obj.get("url"),
                "display_url": bay_obj.get("display_url")
            },
            "device": {
                "id": device_id,
                "name": device_obj["name"],
                "url": device_obj.get("url"),
                "display_url": device_obj.get("display_url")
            },
            "availability": {
                "is_occupied": installed_module_info is not None,
                "status": "Occupied" if installed_module_info else "Available"
            },
            "installed_module": installed_module_info,
            "specifications": bay_specifications
        }
        
        logger.info(f"✅ Module bay details retrieved for {device_name}:{module_bay} ({'Occupied' if installed_module_info else 'Available'})")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get module bay info for {device_name}:{module_bay}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }