#!/usr/bin/env python3
"""
DCIM Module Management Tools

High-level tools for managing NetBox device modules and modular components.
"""

from typing import Dict, List, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


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
        device_id = device["id"]
        
        # Find the module bay
        module_bays = client.dcim.module_bays.filter(device_id=device_id, name=module_bay)
        if not module_bays:
            return {
                "success": False,
                "error": f"Module bay '{module_bay}' not found on device '{device_name}'",
                "error_type": "ModuleBayNotFound"
            }
        bay = module_bays[0]
        bay_id = bay["id"]
        
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
        mod_type_id = mod_type["id"]
        
        if not confirm:
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "module_installation",
                "module": {
                    "device": {"name": device["name"], "id": device_id},
                    "module_type": {"model": mod_type["model"], "id": mod_type_id},
                    "module_bay": {"name": bay["name"], "id": bay_id},
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
                "device": {"name": device["name"], "id": device_id},
                "module_type": {"model": mod_type["model"], "id": mod_type_id},
                "module_bay": {"name": bay["name"], "id": bay_id}
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
        device_id = device["id"]
        
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
                    "device": {"name": device["name"], "id": device_id},
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
            "device": {"name": device["name"], "id": device_id},
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to add power port {power_port_name} to {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }