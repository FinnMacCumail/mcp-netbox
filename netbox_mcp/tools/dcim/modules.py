#!/usr/bin/env python3
"""
DCIM Module Management Tools

Comprehensive enterprise-grade tools for managing NetBox modules, module types, and modular components.
Provides full lifecycle management for modular infrastructure with dual-tool pattern architecture.

Key Features:
- Module Types Management: Define module catalog with specifications
- Module Installation: Install modules into device module bays  
- Module Lifecycle: List, inspect, update, and remove modules
- Module Bay Management: Bay inspection and availability tracking
- Enterprise Safety: Comprehensive validation, conflict detection, and dry-run capabilities
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


# ======================================================================
# UTILITY FUNCTIONS
# ======================================================================

def get_expanded_modules(client: NetBoxClient, **filter_params) -> list:
    """
    TEMPORARILY DISABLED: Get modules with consistent field expansion.
    
    NOTE: Expand parameters are not supported by pynetbox library.
    This utility function is disabled until architectural decision is made
    about implementing direct REST API calls for expand functionality.
    
    See GitHub issue for expand parameter analysis and future implementation.
    
    Args:
        client: NetBoxClient instance
        **filter_params: Filter parameters for module query
        
    Returns:
        List of modules (without expansion - same as normal filter)
    """
    # Temporarily fallback to normal filter without expand
    return list(client.dcim.modules.filter(**filter_params))


def get_expanded_module_types(client: NetBoxClient, **filter_params) -> list:
    """
    TEMPORARILY DISABLED: Get module types with consistent manufacturer expansion.
    
    NOTE: Expand parameters are not supported by pynetbox library.
    This utility function is disabled until architectural decision is made.
    
    Args:
        client: NetBoxClient instance
        **filter_params: Filter parameters for module type query
        
    Returns:
        List of module types (without expansion - same as normal filter)
    """
    # Temporarily fallback to normal filter without expand
    return list(client.dcim.module_types.filter(**filter_params))


# ======================================================================
# MODULE TYPES MANAGEMENT
# ======================================================================

@mcp_tool(category="dcim")
def netbox_create_module_type(
    client: NetBoxClient,
    manufacturer: str,
    model: str,
    part_number: Optional[str] = None,
    description: Optional[str] = None,
    weight: Optional[float] = None,
    weight_unit: str = "g",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a module type in NetBox for defining modular component specifications.
    
    This enterprise-grade function enables module catalog management by defining
    standard module types that can be installed in device module bays.
    Essential for modular infrastructure standardization and inventory planning.
    
    Args:
        client: NetBoxClient instance (injected)
        manufacturer: Manufacturer name (e.g., "Cisco", "Dell", "HPE")
        model: Module model name (e.g., "SFP-10G-LR", "X710-DA2")
        part_number: Optional manufacturer part number
        description: Detailed description of the module
        weight: Physical weight of the module
        weight_unit: Weight unit (g, kg, lb, oz)
        confirm: Must be True to execute (enterprise safety)
        
    Returns:
        Success status with module type details or error information
        
    Example:
        netbox_create_module_type(
            manufacturer="Cisco",
            model="SFP-10G-LR",
            part_number="SFP-10G-LR=",
            description="10GBASE-LR SFP+ Module",
            weight=20.0,
            weight_unit="g",
            confirm=True
        )
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: Module Type would be created. Set confirm=True to execute.",
            "would_create": {
                "manufacturer": manufacturer,
                "model": model,
                "part_number": part_number,
                "description": description,
                "weight": weight,
                "weight_unit": weight_unit
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not manufacturer or not manufacturer.strip():
        raise ValidationError("Manufacturer cannot be empty")
    
    if not model or not model.strip():
        raise ValidationError("Model cannot be empty")
    
    if weight is not None and weight < 0:
        raise ValidationError("Weight cannot be negative")
    
    valid_weight_units = ["g", "kg", "lb", "oz"]
    if weight_unit not in valid_weight_units:
        raise ValidationError(f"Weight unit must be one of: {', '.join(valid_weight_units)}")
    
    logger.info(f"Creating Module Type '{model}' by '{manufacturer}'")
    
    # STEP 3: LOOKUP MANUFACTURER (with defensive dict/object handling)
    try:
        manufacturers = client.dcim.manufacturers.filter(name=manufacturer)
        if not manufacturers:
            # Try by slug as fallback
            manufacturers = client.dcim.manufacturers.filter(slug=manufacturer.lower().replace(' ', '-'))
        
        if not manufacturers:
            logger.error(f"Manufacturer '{manufacturer}' not found")
            raise NotFoundError(f"Manufacturer '{manufacturer}' not found. Create the manufacturer first.")
        
        manufacturer_obj = manufacturers[0]
        # CRITICAL: Apply defensive dict/object handling to ALL NetBox responses
        manufacturer_id = manufacturer_obj.get('id') if isinstance(manufacturer_obj, dict) else manufacturer_obj.id
        manufacturer_display = manufacturer_obj.get('display', manufacturer) if isinstance(manufacturer_obj, dict) else getattr(manufacturer_obj, 'display', manufacturer)
        logger.info(f"Found Manufacturer: {manufacturer_display} (ID: {manufacturer_id})")
        
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error looking up manufacturer '{manufacturer}': {e}")
        raise ValidationError(f"Failed to resolve manufacturer '{manufacturer}': {e}")
    
    # STEP 4: CONFLICT DETECTION - Check for existing module type
    logger.info(f"Checking for existing Module Type '{model}' by '{manufacturer}'")
    try:
        existing_module_types = client.dcim.module_types.filter(
            manufacturer_id=manufacturer_id,
            model=model,
            no_cache=True  # Force live check for accurate conflict detection
        )
        
        if existing_module_types:
            existing_module_type = existing_module_types[0]
            existing_id = existing_module_type.get('id') if isinstance(existing_module_type, dict) else existing_module_type.id
            logger.warning(f"Module Type conflict detected: '{model}' already exists for manufacturer '{manufacturer}' (ID: {existing_id})")
            raise ConflictError(
                resource_type="Module Type",
                identifier=f"{model} by {manufacturer}",
                existing_id=existing_id
            )
            
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing module types: {e}")
    
    # STEP 5: CREATE MODULE TYPE
    create_payload = {
        "manufacturer": manufacturer_id,
        "model": model,
        "description": description or ""
    }
    
    # Add optional fields
    if part_number:
        create_payload["part_number"] = part_number
    if weight is not None:
        create_payload["weight"] = weight
        create_payload["weight_unit"] = weight_unit
    
    logger.info(f"Creating Module Type with payload: {create_payload}")
    
    try:
        new_module_type = client.dcim.module_types.create(confirm=confirm, **create_payload)
        
        # Handle both dict and object responses
        module_type_id = new_module_type.get('id') if isinstance(new_module_type, dict) else new_module_type.id
        module_type_model = new_module_type.get('model') if isinstance(new_module_type, dict) else new_module_type.model
        
        logger.info(f"Successfully created Module Type '{module_type_model}' (ID: {module_type_id})")
        
    except Exception as e:
        logger.error(f"NetBox API error during module type creation: {e}")
        raise ValidationError(f"NetBox API error during module type creation: {e}")
    
    # STEP 6: RETURN SUCCESS
    return {
        "success": True,
        "message": f"Module Type '{model}' successfully created for manufacturer '{manufacturer}'.",
        "data": {
            "module_type_id": module_type_id,
            "model": module_type_model,
            "manufacturer": manufacturer,
            "manufacturer_id": manufacturer_id,
            "part_number": create_payload.get("part_number"),
            "weight": create_payload.get("weight"),
            "weight_unit": create_payload.get("weight_unit"),
            "description": create_payload.get("description")
        }
    }


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
        client: NetBoxClient instance (injected)
        manufacturer: Optional filter by manufacturer name
        limit: Maximum number of module types to return (default: 100)
        
    Returns:
        Comprehensive list of module types with statistics and details
        
    Example:
        netbox_list_all_module_types(manufacturer="Cisco")
    """
    
    logger.info(f"Listing Module Types (manufacturer filter: {manufacturer}, limit: {limit})")
    
    try:
        # Build filter parameters
        filter_params = {}
        if manufacturer:
            # Resolve manufacturer to ID for filtering
            manufacturers = client.dcim.manufacturers.filter(name=manufacturer)
            if not manufacturers:
                manufacturers = client.dcim.manufacturers.filter(slug=manufacturer.lower().replace(' ', '-'))
            if manufacturers:
                manufacturer_obj = manufacturers[0]
                manufacturer_id = manufacturer_obj.get('id') if isinstance(manufacturer_obj, dict) else manufacturer_obj.id
                filter_params['manufacturer_id'] = manufacturer_id
            else:
                logger.warning(f"Manufacturer '{manufacturer}' not found, returning empty results")
                return {
                    "success": True,
                    "count": 0,
                    "module_types": [],
                    "summary": {
                        "total_module_types": 0,
                        "manufacturers": {},
                        "filter_applied": {"manufacturer": manufacturer}
                    }
                }
        
        # Fetch module types with filtering and expand manufacturer relationship
        if filter_params:
            module_types_raw = list(client.dcim.module_types.filter(**filter_params)[:limit])
        else:
            module_types_raw = list(client.dcim.module_types.filter()[:limit])
        
        # Process module types with defensive dict/object handling
        module_types = []
        manufacturer_counts = {}
        
        for module_type in module_types_raw:
            # Apply defensive dict/object handling
            module_type_id = module_type.get('id') if isinstance(module_type, dict) else module_type.id
            model = module_type.get('model') if isinstance(module_type, dict) else module_type.model
            description = module_type.get('description') if isinstance(module_type, dict) else getattr(module_type, 'description', '')
            part_number = module_type.get('part_number') if isinstance(module_type, dict) else getattr(module_type, 'part_number', None)
            weight = module_type.get('weight') if isinstance(module_type, dict) else getattr(module_type, 'weight', None)
            weight_unit = module_type.get('weight_unit') if isinstance(module_type, dict) else getattr(module_type, 'weight_unit', None)
            
            # Handle manufacturer object
            manufacturer_obj = module_type.get('manufacturer') if isinstance(module_type, dict) else getattr(module_type, 'manufacturer', None)
            if manufacturer_obj:
                if isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get('name', 'Unknown')
                    manufacturer_id = manufacturer_obj.get('id')
                else:
                    manufacturer_name = getattr(manufacturer_obj, 'name', 'Unknown')
                    manufacturer_id = getattr(manufacturer_obj, 'id', None)
            else:
                manufacturer_name = 'Unknown'
                manufacturer_id = None
            
            # Count manufacturers
            manufacturer_counts[manufacturer_name] = manufacturer_counts.get(manufacturer_name, 0) + 1
            
            module_types.append({
                "id": module_type_id,
                "model": model,
                "manufacturer": {
                    "name": manufacturer_name,
                    "id": manufacturer_id
                },
                "part_number": part_number,
                "description": description,
                "weight": weight,
                "weight_unit": weight_unit
            })
        
        # Generate summary statistics
        summary = {
            "total_module_types": len(module_types),
            "manufacturers": manufacturer_counts,
            "filter_applied": {}
        }
        
        if manufacturer:
            summary["filter_applied"]["manufacturer"] = manufacturer
        
        logger.info(f"Successfully retrieved {len(module_types)} module types")
        
        return {
            "success": True,
            "count": len(module_types),
            "module_types": sorted(module_types, key=lambda x: (x["manufacturer"]["name"], x["model"])),
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Failed to list module types: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
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
    specifications, relationships, and metadata. Essential for module planning
    and compatibility verification in modular infrastructure deployments.
    
    Args:
        client: NetBoxClient instance (injected)
        manufacturer: Manufacturer name
        model: Module model name
        
    Returns:
        Detailed module type information or error details
        
    Example:
        netbox_get_module_type_info("Cisco", "SFP-10G-LR")
    """
    
    if not manufacturer or not manufacturer.strip():
        raise ValidationError("Manufacturer cannot be empty")
    
    if not model or not model.strip():
        raise ValidationError("Model cannot be empty")
    
    logger.info(f"Getting Module Type info for '{model}' by '{manufacturer}'")
    
    try:
        # Find manufacturer first
        manufacturers = client.dcim.manufacturers.filter(name=manufacturer)
        if not manufacturers:
            manufacturers = client.dcim.manufacturers.filter(slug=manufacturer.lower().replace(' ', '-'))
        
        if not manufacturers:
            raise NotFoundError(f"Manufacturer '{manufacturer}' not found")
        
        manufacturer_obj = manufacturers[0]
        manufacturer_id = manufacturer_obj.get('id') if isinstance(manufacturer_obj, dict) else manufacturer_obj.id
        manufacturer_name = manufacturer_obj.get('name') if isinstance(manufacturer_obj, dict) else manufacturer_obj.name
        
        # Find module type
        module_types = client.dcim.module_types.filter(manufacturer_id=manufacturer_id, model=model)
        if not module_types:
            raise NotFoundError(f"Module Type '{model}' by '{manufacturer}' not found")
        
        module_type = module_types[0]
        
        # Apply defensive dict/object handling
        module_type_id = module_type.get('id') if isinstance(module_type, dict) else module_type.id
        model_name = module_type.get('model') if isinstance(module_type, dict) else module_type.model
        description = module_type.get('description') if isinstance(module_type, dict) else getattr(module_type, 'description', '')
        part_number = module_type.get('part_number') if isinstance(module_type, dict) else getattr(module_type, 'part_number', None)
        weight = module_type.get('weight') if isinstance(module_type, dict) else getattr(module_type, 'weight', None)
        weight_unit = module_type.get('weight_unit') if isinstance(module_type, dict) else getattr(module_type, 'weight_unit', None)
        
        # Count installed modules of this type
        installed_modules = list(client.dcim.modules.filter(module_type_id=module_type_id))
        
        return {
            "success": True,
            "module_type": {
                "id": module_type_id,
                "model": model_name,
                "manufacturer": {
                    "name": manufacturer_name,
                    "id": manufacturer_id
                },
                "part_number": part_number,
                "description": description,
                "weight": weight,
                "weight_unit": weight_unit,
                "installed_count": len(installed_modules)
            }
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to get module type info for '{model}' by '{manufacturer}': {e}")
        raise ValidationError(f"Failed to retrieve module type information: {e}")


# ======================================================================
# MODULE MANAGEMENT (DEVICE LEVEL)
# ======================================================================

@mcp_tool(category="dcim")
def netbox_install_module_in_device(
    client: NetBoxClient,
    device_name: str,
    module_type: str,
    module_bay: str,
    serial_number: Optional[str] = None,
    asset_tag: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Install a module in a device module bay.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        module_type: Type/model of the module
        module_bay: Name of the module bay
        serial_number: Optional serial number
        asset_tag: Optional asset tag
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Module installation result
        
    Example:
        netbox_install_module_in_device("rtr-01", "SFP-10G-LR", "slot-1", confirm=True)
    """
    try:
        if not all([device_name, module_type, module_bay]):
            return {
                "success": False,
                "error": "device_name, module_type, and module_bay are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Installing module {module_type} in device {device_name} bay {module_bay}")
        
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "DeviceNotFound"
            }
        device = devices[0]
        # Apply defensive dict/object handling (DEVELOPMENT-GUIDE.md Bug #1)
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Find the module bay
        module_bays = client.dcim.module_bays.filter(device_id=device_id, name=module_bay)
        if not module_bays:
            return {
                "success": False,
                "error": f"Module bay '{module_bay}' not found on device '{device_name}'",
                "error_type": "ModuleBayNotFound"
            }
        bay = module_bays[0]
        # Apply defensive dict/object handling (DEVELOPMENT-GUIDE.md Bug #1)
        bay_id = bay.get('id') if isinstance(bay, dict) else bay.id
        bay_name_actual = bay.get('name') if isinstance(bay, dict) else bay.name
        
        # Check if bay is already occupied
        existing_modules = client.dcim.modules.filter(module_bay_id=bay_id)
        if existing_modules:
            return {
                "success": False,
                "error": f"Module bay '{module_bay}' is already occupied",
                "error_type": "ModuleBayOccupied"
            }
        
        # Find module type
        module_types = client.dcim.module_types.filter(model=module_type)
        if not module_types:
            return {
                "success": False,
                "error": f"Module type '{module_type}' not found",
                "error_type": "ModuleTypeNotFound"
            }
        mod_type = module_types[0]
        # Apply defensive dict/object handling (DEVELOPMENT-GUIDE.md Bug #1)
        mod_type_id = mod_type.get('id') if isinstance(mod_type, dict) else mod_type.id
        mod_type_model = mod_type.get('model') if isinstance(mod_type, dict) else mod_type.model
        
        if not confirm:
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "module_installation",
                "module": {
                    "device": {"name": device_name_actual, "id": device_id},
                    "module_type": {"model": mod_type_model, "id": mod_type_id},
                    "module_bay": {"name": bay_name_actual, "id": bay_id},
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Create the module
        module_data = {
            "device": device_id,
            "module_bay": bay_id,
            "module_type": mod_type_id
        }
        
        if serial_number:
            module_data["serial"] = serial_number
        if asset_tag:
            module_data["asset_tag"] = asset_tag
        
        result = client.dcim.modules.create(confirm=True, **module_data)
        
        return {
            "success": True,
            "action": "installed",
            "object_type": "module",
            "module": result,
            "installation": {
                "device": {"name": device_name_actual, "id": device_id},
                "module_type": {"model": mod_type_model, "id": mod_type_id},
                "module_bay": {"name": bay_name_actual, "id": bay_id}
            },
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to install module {module_type} in {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_add_power_port_to_device(
    client: NetBoxClient,
    device_name: str,
    power_port_name: str,
    power_port_type: str = "iec-60320-c14",
    maximum_draw: Optional[int] = None,
    allocated_draw: Optional[int] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a power port to a device for power infrastructure documentation.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        power_port_name: Name of the power port
        power_port_type: Type of power connector (iec-60320-c14, iec-60320-c20, etc.)
        maximum_draw: Maximum power draw in watts
        allocated_draw: Allocated power draw in watts
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Power port creation result
        
    Example:
        netbox_add_power_port_to_device("server-01", "PSU1", "iec-60320-c14", maximum_draw=750, confirm=True)
    """
    try:
        if not device_name or not power_port_name:
            return {
                "success": False,
                "error": "device_name and power_port_name are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Adding power port {power_port_name} to device {device_name}")
        
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "DeviceNotFound"
            }
        device = devices[0]
        # Apply defensive dict/object handling (DEVELOPMENT-GUIDE.md Bug #1)
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Check for existing power port with same name
        existing_ports = client.dcim.power_ports.filter(device_id=device_id, name=power_port_name)
        if existing_ports:
            return {
                "success": False,
                "error": f"Power port '{power_port_name}' already exists on device '{device_name}'",
                "error_type": "PowerPortExists"
            }
        
        if not confirm:
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "power_port",
                "power_port": {
                    "device": {"name": device_name_actual, "id": device_id},
                    "name": power_port_name,
                    "type": power_port_type,
                    "maximum_draw": maximum_draw,
                    "allocated_draw": allocated_draw,
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Create power port
        port_data = {
            "device": device_id,
            "name": power_port_name,
            "type": power_port_type
        }
        
        if maximum_draw is not None:
            port_data["maximum_draw"] = maximum_draw
        if allocated_draw is not None:
            port_data["allocated_draw"] = allocated_draw
        if description:
            port_data["description"] = description
        
        result = client.dcim.power_ports.create(confirm=True, **port_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "power_port",
            "power_port": result,
            "device": {"name": device_name_actual, "id": device_id},
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to add power port {power_port_name} to {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
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
        client: NetBoxClient instance (injected)
        device_name: Target device name
        limit: Maximum number of modules to return (default: 100)
        
    Returns:
        Comprehensive list of device modules with details and statistics
        
    Example:
        netbox_list_device_modules("rtr-core-01")
    """
    
    if not device_name or not device_name.strip():
        raise ValidationError("Device name cannot be empty")
    
    logger.info(f"Listing modules for device '{device_name}'")
    
    try:
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            # Try case-insensitive search
            all_devices = client.dcim.devices.all()
            devices = [d for d in all_devices if (
                d.get('name') if isinstance(d, dict) else d.name
            ).lower() == device_name.lower()]
        
        if not devices:
            raise NotFoundError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Get all modules for this device with expanded relationships
        modules_raw = list(client.dcim.modules.filter(device_id=device_id)[:limit])
        
        # Process modules with defensive dict/object handling
        modules = []
        module_type_counts = {}
        bay_usage = {}
        
        for module in modules_raw:
            # Apply defensive dict/object handling
            module_id = module.get('id') if isinstance(module, dict) else module.id
            serial = module.get('serial') if isinstance(module, dict) else getattr(module, 'serial', None)
            asset_tag = module.get('asset_tag') if isinstance(module, dict) else getattr(module, 'asset_tag', None)
            status = module.get('status') if isinstance(module, dict) else getattr(module, 'status', None)
            
            # Handle module type object
            module_type_obj = module.get('module_type') if isinstance(module, dict) else getattr(module, 'module_type', None)
            if module_type_obj:
                if isinstance(module_type_obj, dict):
                    module_type_model = module_type_obj.get('model', 'Unknown')
                    module_type_id = module_type_obj.get('id')
                    manufacturer_obj = module_type_obj.get('manufacturer', {})
                    if isinstance(manufacturer_obj, dict):
                        manufacturer_name = manufacturer_obj.get('name', 'Unknown')
                    else:
                        manufacturer_name = getattr(manufacturer_obj, 'name', 'Unknown')
                else:
                    module_type_model = getattr(module_type_obj, 'model', 'Unknown')
                    module_type_id = getattr(module_type_obj, 'id', None)
                    manufacturer_obj = getattr(module_type_obj, 'manufacturer', None)
                    manufacturer_name = getattr(manufacturer_obj, 'name', 'Unknown') if manufacturer_obj else 'Unknown'
            else:
                module_type_model = 'Unknown'
                module_type_id = None
                manufacturer_name = 'Unknown'
            
            # Handle module bay object
            module_bay_obj = module.get('module_bay') if isinstance(module, dict) else getattr(module, 'module_bay', None)
            if module_bay_obj:
                if isinstance(module_bay_obj, dict):
                    bay_name = module_bay_obj.get('name', 'Unknown')
                    bay_id = module_bay_obj.get('id')
                else:
                    bay_name = getattr(module_bay_obj, 'name', 'Unknown')
                    bay_id = getattr(module_bay_obj, 'id', None)
            else:
                bay_name = 'Unknown'
                bay_id = None
            
            # Count module types
            module_type_counts[module_type_model] = module_type_counts.get(module_type_model, 0) + 1
            
            # Track bay usage
            if bay_name != 'Unknown':
                bay_usage[bay_name] = 'occupied'
            
            # Handle status
            if status:
                if isinstance(status, dict):
                    status_label = status.get('label', 'Unknown')
                else:
                    status_label = str(status)
            else:
                status_label = 'Unknown'
            
            modules.append({
                "id": module_id,
                "module_type": {
                    "model": module_type_model,
                    "id": module_type_id,
                    "manufacturer": manufacturer_name
                },
                "module_bay": {
                    "name": bay_name,
                    "id": bay_id
                },
                "serial": serial,
                "asset_tag": asset_tag,
                "status": status_label
            })
        
        # Calculate accurate bay utilization
        all_bays = list(client.dcim.module_bays.filter(device_id=device_id))
        total_bays = len(all_bays)
        # Count actual installed modules (each module occupies one bay)
        occupied_bays = len(modules)  # modules list contains actual installed modules
        available_bays = total_bays - occupied_bays
        
        # Generate summary statistics
        summary = {
            "device": {
                "name": device_name_actual,
                "id": device_id
            },
            "total_modules": len(modules),
            "module_types": module_type_counts,
            "bay_utilization": {
                "total_bays": total_bays,
                "occupied_bays": occupied_bays,
                "available_bays": available_bays,
                "utilization_percent": round((occupied_bays / total_bays * 100) if total_bays > 0 else 0, 1)
            }
        }
        
        logger.info(f"Successfully retrieved {len(modules)} modules for device '{device_name}'")
        
        return {
            "success": True,
            "count": len(modules),
            "modules": sorted(modules, key=lambda x: x["module_bay"]["name"]),
            "summary": summary
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to list modules for device '{device_name}': {e}")
        raise ValidationError(f"Failed to retrieve device modules: {e}")


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
        client: NetBoxClient instance (injected)
        device_name: Target device name
        module_bay: Module bay name where module is installed
        
    Returns:
        Detailed module information or error details
        
    Example:
        netbox_get_module_info("rtr-core-01", "slot-1")
    """
    
    if not device_name or not device_name.strip():
        raise ValidationError("Device name cannot be empty")
    
    if not module_bay or not module_bay.strip():
        raise ValidationError("Module bay name cannot be empty")
    
    logger.info(f"Getting module info for bay '{module_bay}' on device '{device_name}'")
    
    try:
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            raise NotFoundError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Find the module bay
        module_bays = client.dcim.module_bays.filter(device_id=device_id, name=module_bay)
        if not module_bays:
            raise NotFoundError(f"Module bay '{module_bay}' not found on device '{device_name}'")
        
        bay = module_bays[0]
        bay_id = bay.get('id') if isinstance(bay, dict) else bay.id
        
        # Find module in the bay
        modules = client.dcim.modules.filter(module_bay_id=bay_id)
        if not modules:
            raise NotFoundError(f"No module installed in bay '{module_bay}' on device '{device_name}'")
        
        module = modules[0]
        
        # Apply defensive dict/object handling
        module_id = module.get('id') if isinstance(module, dict) else module.id
        serial = module.get('serial') if isinstance(module, dict) else getattr(module, 'serial', None)
        asset_tag = module.get('asset_tag') if isinstance(module, dict) else getattr(module, 'asset_tag', None)
        description = module.get('description') if isinstance(module, dict) else getattr(module, 'description', '')
        status = module.get('status') if isinstance(module, dict) else getattr(module, 'status', None)
        
        # Handle module type with comprehensive details
        module_type_obj = module.get('module_type') if isinstance(module, dict) else getattr(module, 'module_type', None)
        if module_type_obj:
            if isinstance(module_type_obj, dict):
                module_type_id = module_type_obj.get('id')
                module_type_model = module_type_obj.get('model', 'Unknown')
                part_number = module_type_obj.get('part_number')
                weight = module_type_obj.get('weight')
                weight_unit = module_type_obj.get('weight_unit')
                type_description = module_type_obj.get('description', '')
                
                manufacturer_obj = module_type_obj.get('manufacturer', {})
                if isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get('name', 'Unknown')
                    manufacturer_id = manufacturer_obj.get('id')
                else:
                    manufacturer_name = getattr(manufacturer_obj, 'name', 'Unknown')
                    manufacturer_id = getattr(manufacturer_obj, 'id', None)
            else:
                module_type_id = getattr(module_type_obj, 'id', None)
                module_type_model = getattr(module_type_obj, 'model', 'Unknown')
                part_number = getattr(module_type_obj, 'part_number', None)
                weight = getattr(module_type_obj, 'weight', None)
                weight_unit = getattr(module_type_obj, 'weight_unit', None)
                type_description = getattr(module_type_obj, 'description', '')
                
                manufacturer_obj = getattr(module_type_obj, 'manufacturer', None)
                manufacturer_name = getattr(manufacturer_obj, 'name', 'Unknown') if manufacturer_obj else 'Unknown'
                manufacturer_id = getattr(manufacturer_obj, 'id', None) if manufacturer_obj else None
        else:
            module_type_id = None
            module_type_model = 'Unknown'
            part_number = None
            weight = None
            weight_unit = None
            type_description = ''
            manufacturer_name = 'Unknown'
            manufacturer_id = None
        
        # Handle status
        if status:
            if isinstance(status, dict):
                status_label = status.get('label', 'Unknown')
                status_value = status.get('value', 'unknown')
            else:
                status_label = str(status)
                status_value = 'unknown'
        else:
            status_label = 'Unknown'
            status_value = 'unknown'
        
        return {
            "success": True,
            "module": {
                "id": module_id,
                "device": {
                    "name": device_name_actual,
                    "id": device_id
                },
                "module_bay": {
                    "name": module_bay,
                    "id": bay_id
                },
                "module_type": {
                    "id": module_type_id,
                    "model": module_type_model,
                    "manufacturer": {
                        "name": manufacturer_name,
                        "id": manufacturer_id
                    },
                    "part_number": part_number,
                    "description": type_description,
                    "weight": weight,
                    "weight_unit": weight_unit
                },
                "serial": serial,
                "asset_tag": asset_tag,
                "description": description,
                "status": {
                    "label": status_label,
                    "value": status_value
                }
            }
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to get module info for bay '{module_bay}' on device '{device_name}': {e}")
        raise ValidationError(f"Failed to retrieve module information: {e}")


@mcp_tool(category="dcim")
def netbox_update_module(
    client: NetBoxClient,
    device_name: str,
    module_bay: str,
    serial: Optional[str] = None,
    asset_tag: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Update module information for asset tracking and documentation.
    
    This enterprise-grade function enables module asset updates including
    serial numbers, asset tags, and descriptions. Uses established NetBox MCP
    update patterns with defensive error handling.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Target device name
        module_bay: Module bay name where module is installed
        serial: Updated serial number
        asset_tag: Updated asset tag
        description: Updated description
        confirm: Must be True to execute (enterprise safety)
        
    Returns:
        Success status with updated module details or error information
        
    Example:
        netbox_update_module(
            device_name="rtr-core-01",
            module_bay="slot-1",
            serial="SFP8F3D92A1",
            asset_tag="AST-001234",
            description="Updated 10G SFP+ module",
            confirm=True
        )
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: Module would be updated. Set confirm=True to execute.",
            "would_update": {
                "device_name": device_name,
                "module_bay": module_bay,
                "serial": serial,
                "asset_tag": asset_tag,
                "description": description
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not device_name or not device_name.strip():
        raise ValidationError("Device name cannot be empty")
    
    if not module_bay or not module_bay.strip():
        raise ValidationError("Module bay name cannot be empty")
    
    if not any([serial, asset_tag, description]):
        raise ValidationError("At least one field (serial, asset_tag, description) must be provided for update")
    
    logger.info(f"Updating module in bay '{module_bay}' on device '{device_name}'")
    
    try:
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            raise NotFoundError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Find the module bay
        module_bays = client.dcim.module_bays.filter(device_id=device_id, name=module_bay)
        if not module_bays:
            raise NotFoundError(f"Module bay '{module_bay}' not found on device '{device_name}'")
        
        bay = module_bays[0]
        bay_id = bay.get('id') if isinstance(bay, dict) else bay.id
        
        # Find module in the bay
        modules = client.dcim.modules.filter(module_bay_id=bay_id)
        if not modules:
            raise NotFoundError(f"No module installed in bay '{module_bay}' on device '{device_name}'")
        
        module = modules[0]
        module_id = module.get('id') if isinstance(module, dict) else module.id
        
        # Build update payload
        update_payload = {}
        if serial is not None:
            update_payload["serial"] = serial
        if asset_tag is not None:
            update_payload["asset_tag"] = asset_tag
        if description is not None:
            update_payload["description"] = description
        
        logger.info(f"Updating module {module_id} with payload: {update_payload}")
        
        # Use proven NetBox MCP update pattern (DEVELOPMENT-GUIDE.md Bug #4)
        updated_module = client.dcim.modules.update(module_id, confirm=confirm, **update_payload)
        
        # Handle both dict and object responses
        updated_serial = updated_module.get('serial') if isinstance(updated_module, dict) else getattr(updated_module, 'serial', None)
        updated_asset_tag = updated_module.get('asset_tag') if isinstance(updated_module, dict) else getattr(updated_module, 'asset_tag', None)
        updated_description = updated_module.get('description') if isinstance(updated_module, dict) else getattr(updated_module, 'description', '')
        
        logger.info(f"Successfully updated module in bay '{module_bay}' on device '{device_name}'")
        
        return {
            "success": True,
            "message": f"Module in bay '{module_bay}' on device '{device_name}' successfully updated.",
            "data": {
                "module_id": module_id,
                "device": {
                    "name": device_name_actual,
                    "id": device_id
                },
                "module_bay": {
                    "name": module_bay,
                    "id": bay_id
                },
                "updated_fields": {
                    "serial": updated_serial,
                    "asset_tag": updated_asset_tag,
                    "description": updated_description
                }
            }
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to update module in bay '{module_bay}' on device '{device_name}': {e}")
        raise ValidationError(f"NetBox API error during module update: {e}")


@mcp_tool(category="dcim")
def netbox_remove_module_from_device(
    client: NetBoxClient,
    device_name: str,
    module_bay: str,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Remove a module from a device bay with enterprise safety validation.
    
    This enterprise-grade function enables safe module removal with comprehensive
    validation and conflict detection. Uses established NetBox MCP delete patterns
    with defensive error handling.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Target device name
        module_bay: Module bay name where module is installed
        confirm: Must be True to execute (enterprise safety)
        
    Returns:
        Success status with removal details or error information
        
    Example:
        netbox_remove_module_from_device(
            device_name="rtr-core-01",
            module_bay="slot-1",
            confirm=True
        )
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: Module would be removed. Set confirm=True to execute.",
            "would_remove": {
                "device_name": device_name,
                "module_bay": module_bay
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not device_name or not device_name.strip():
        raise ValidationError("Device name cannot be empty")
    
    if not module_bay or not module_bay.strip():
        raise ValidationError("Module bay name cannot be empty")
    
    logger.info(f"Removing module from bay '{module_bay}' on device '{device_name}'")
    
    try:
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            raise NotFoundError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Find the module bay
        module_bays = client.dcim.module_bays.filter(device_id=device_id, name=module_bay)
        if not module_bays:
            raise NotFoundError(f"Module bay '{module_bay}' not found on device '{device_name}'")
        
        bay = module_bays[0]
        bay_id = bay.get('id') if isinstance(bay, dict) else bay.id
        
        # Find module in the bay
        modules = client.dcim.modules.filter(module_bay_id=bay_id)
        if not modules:
            raise NotFoundError(f"No module installed in bay '{module_bay}' on device '{device_name}'")
        
        module = modules[0]
        module_id = module.get('id') if isinstance(module, dict) else module.id
        
        # Get module details before deletion
        module_serial = module.get('serial') if isinstance(module, dict) else getattr(module, 'serial', None)
        module_asset_tag = module.get('asset_tag') if isinstance(module, dict) else getattr(module, 'asset_tag', None)
        
        module_type_obj = module.get('module_type') if isinstance(module, dict) else getattr(module, 'module_type', None)
        if module_type_obj:
            if isinstance(module_type_obj, dict):
                module_type_model = module_type_obj.get('model', 'Unknown')
            else:
                module_type_model = getattr(module_type_obj, 'model', 'Unknown')
        else:
            module_type_model = 'Unknown'
        
        logger.info(f"Removing module {module_id} (type: {module_type_model}) from bay '{module_bay}'")
        
        # Use proven NetBox MCP delete pattern (DEVELOPMENT-GUIDE.md Bug #4)
        client.dcim.modules.delete(module_id, confirm=confirm)
        
        logger.info(f"Successfully removed module from bay '{module_bay}' on device '{device_name}'")
        
        return {
            "success": True,
            "message": f"Module successfully removed from bay '{module_bay}' on device '{device_name}'.",
            "data": {
                "removed_module": {
                    "id": module_id,
                    "type": module_type_model,
                    "serial": module_serial,
                    "asset_tag": module_asset_tag
                },
                "device": {
                    "name": device_name_actual,
                    "id": device_id
                },
                "module_bay": {
                    "name": module_bay,
                    "id": bay_id,
                    "status": "available"
                }
            }
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to remove module from bay '{module_bay}' on device '{device_name}': {e}")
        raise ValidationError(f"NetBox API error during module removal: {e}")


# ======================================================================
# MODULE BAY MANAGEMENT
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
        client: NetBoxClient instance (injected)
        device_name: Target device name
        limit: Maximum number of module bays to return (default: 100)
        
    Returns:
        Comprehensive list of device module bays with status and statistics
        
    Example:
        netbox_list_device_module_bays("rtr-core-01")
    """
    
    if not device_name or not device_name.strip():
        raise ValidationError("Device name cannot be empty")
    
    logger.info(f"Listing module bays for device '{device_name}'")
    
    try:
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            # Try case-insensitive search
            all_devices = client.dcim.devices.all()
            devices = [d for d in all_devices if (
                d.get('name') if isinstance(d, dict) else d.name
            ).lower() == device_name.lower()]
        
        if not devices:
            raise NotFoundError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Get all module bays for this device
        module_bays_raw = list(client.dcim.module_bays.filter(device_id=device_id)[:limit])
        
        # Get all installed modules to determine bay occupancy
        installed_modules = list(client.dcim.modules.filter(device_id=device_id))
        bay_occupancy = {}
        for module in installed_modules:
            module_bay_obj = module.get('module_bay') if isinstance(module, dict) else getattr(module, 'module_bay', None)
            if module_bay_obj:
                bay_id = module_bay_obj.get('id') if isinstance(module_bay_obj, dict) else getattr(module_bay_obj, 'id', None)
                if bay_id:
                    # Get module type info
                    module_type_obj = module.get('module_type') if isinstance(module, dict) else getattr(module, 'module_type', None)
                    if module_type_obj:
                        if isinstance(module_type_obj, dict):
                            module_type_model = module_type_obj.get('model', 'Unknown')
                        else:
                            module_type_model = getattr(module_type_obj, 'model', 'Unknown')
                    else:
                        module_type_model = 'Unknown'
                    
                    bay_occupancy[bay_id] = {
                        "module_id": module.get('id') if isinstance(module, dict) else module.id,
                        "module_type": module_type_model,
                        "serial": module.get('serial') if isinstance(module, dict) else getattr(module, 'serial', None)
                    }
        
        # Process module bays with defensive dict/object handling
        module_bays = []
        bay_status_counts = {"available": 0, "occupied": 0}
        
        for bay in module_bays_raw:
            # Apply defensive dict/object handling
            bay_id = bay.get('id') if isinstance(bay, dict) else bay.id
            bay_name = bay.get('name') if isinstance(bay, dict) else bay.name
            bay_label = bay.get('label') if isinstance(bay, dict) else getattr(bay, 'label', '')
            bay_position = bay.get('position') if isinstance(bay, dict) else getattr(bay, 'position', None)
            bay_description = bay.get('description') if isinstance(bay, dict) else getattr(bay, 'description', '')
            
            # Determine bay status and installed module
            if bay_id in bay_occupancy:
                bay_status = "occupied"
                installed_module = bay_occupancy[bay_id]
                bay_status_counts["occupied"] += 1
            else:
                bay_status = "available"
                installed_module = None
                bay_status_counts["available"] += 1
            
            module_bays.append({
                "id": bay_id,
                "name": bay_name,
                "label": bay_label,
                "position": bay_position,
                "description": bay_description,
                "status": bay_status,
                "installed_module": installed_module
            })
        
        # Generate summary statistics
        total_bays = len(module_bays)
        utilization_percent = round((bay_status_counts["occupied"] / total_bays * 100) if total_bays > 0 else 0, 1)
        
        summary = {
            "device": {
                "name": device_name_actual,
                "id": device_id
            },
            "total_bays": total_bays,
            "bay_status": bay_status_counts,
            "utilization": {
                "percent": utilization_percent,
                "available_bays": bay_status_counts["available"],
                "occupied_bays": bay_status_counts["occupied"]
            }
        }
        
        logger.info(f"Successfully retrieved {total_bays} module bays for device '{device_name}' ({utilization_percent}% utilized)")
        
        return {
            "success": True,
            "count": total_bays,
            "module_bays": sorted(module_bays, key=lambda x: x["name"]),
            "summary": summary
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to list module bays for device '{device_name}': {e}")
        raise ValidationError(f"Failed to retrieve device module bays: {e}")


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
        client: NetBoxClient instance (injected)
        device_name: Target device name
        module_bay: Module bay name to inspect
        
    Returns:
        Detailed module bay information or error details
        
    Example:
        netbox_get_module_bay_info("rtr-core-01", "slot-1")
    """
    
    if not device_name or not device_name.strip():
        raise ValidationError("Device name cannot be empty")
    
    if not module_bay or not module_bay.strip():
        raise ValidationError("Module bay name cannot be empty")
    
    logger.info(f"Getting module bay info for bay '{module_bay}' on device '{device_name}'")
    
    try:
        # Find the device
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            raise NotFoundError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_name_actual = device.get('name') if isinstance(device, dict) else device.name
        
        # Find the module bay
        module_bays = client.dcim.module_bays.filter(device_id=device_id, name=module_bay)
        if not module_bays:
            raise NotFoundError(f"Module bay '{module_bay}' not found on device '{device_name}'")
        
        bay = module_bays[0]
        
        # Apply defensive dict/object handling
        bay_id = bay.get('id') if isinstance(bay, dict) else bay.id
        bay_name = bay.get('name') if isinstance(bay, dict) else bay.name
        bay_label = bay.get('label') if isinstance(bay, dict) else getattr(bay, 'label', '')
        bay_position = bay.get('position') if isinstance(bay, dict) else getattr(bay, 'position', None)
        bay_description = bay.get('description') if isinstance(bay, dict) else getattr(bay, 'description', '')
        
        # Check for installed module
        modules = client.dcim.modules.filter(module_bay_id=bay_id)
        
        if modules:
            # Bay is occupied
            module = modules[0]
            module_id = module.get('id') if isinstance(module, dict) else module.id
            module_serial = module.get('serial') if isinstance(module, dict) else getattr(module, 'serial', None)
            module_asset_tag = module.get('asset_tag') if isinstance(module, dict) else getattr(module, 'asset_tag', None)
            module_description = module.get('description') if isinstance(module, dict) else getattr(module, 'description', '')
            module_status = module.get('status') if isinstance(module, dict) else getattr(module, 'status', None)
            
            # Handle module type
            module_type_obj = module.get('module_type') if isinstance(module, dict) else getattr(module, 'module_type', None)
            if module_type_obj:
                if isinstance(module_type_obj, dict):
                    module_type_id = module_type_obj.get('id')
                    module_type_model = module_type_obj.get('model', 'Unknown')
                    part_number = module_type_obj.get('part_number')
                    
                    manufacturer_obj = module_type_obj.get('manufacturer', {})
                    if isinstance(manufacturer_obj, dict):
                        manufacturer_name = manufacturer_obj.get('name', 'Unknown')
                    else:
                        manufacturer_name = getattr(manufacturer_obj, 'name', 'Unknown')
                else:
                    module_type_id = getattr(module_type_obj, 'id', None)
                    module_type_model = getattr(module_type_obj, 'model', 'Unknown')
                    part_number = getattr(module_type_obj, 'part_number', None)
                    
                    manufacturer_obj = getattr(module_type_obj, 'manufacturer', None)
                    manufacturer_name = getattr(manufacturer_obj, 'name', 'Unknown') if manufacturer_obj else 'Unknown'
            else:
                module_type_id = None
                module_type_model = 'Unknown'
                part_number = None
                manufacturer_name = 'Unknown'
            
            # Handle status
            if module_status:
                if isinstance(module_status, dict):
                    status_label = module_status.get('label', 'Unknown')
                else:
                    status_label = str(module_status)
            else:
                status_label = 'Unknown'
            
            installed_module = {
                "id": module_id,
                "module_type": {
                    "id": module_type_id,
                    "model": module_type_model,
                    "manufacturer": manufacturer_name,
                    "part_number": part_number
                },
                "serial": module_serial,
                "asset_tag": module_asset_tag,
                "description": module_description,
                "status": status_label
            }
            bay_status = "occupied"
        else:
            # Bay is available
            installed_module = None
            bay_status = "available"
        
        return {
            "success": True,
            "module_bay": {
                "id": bay_id,
                "name": bay_name,
                "label": bay_label,
                "position": bay_position,
                "description": bay_description,
                "device": {
                    "name": device_name_actual,
                    "id": device_id
                },
                "status": bay_status,
                "installed_module": installed_module
            }
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to get module bay info for bay '{module_bay}' on device '{device_name}': {e}")
        raise ValidationError(f"Failed to retrieve module bay information: {e}")