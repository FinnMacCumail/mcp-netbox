#!/usr/bin/env python3
"""
DCIM Tools for NetBox MCP

Comprehensive Data Center Infrastructure Management tools following Gemini's 
dependency injection architecture. All tools receive NetBoxClient via dependency 
injection and provide high-level DCIM functionality with enterprise safety mechanisms.

These tools cover the core DCIM workflow: Sites → Racks → Devices → Interfaces → Cables
"""

from typing import Dict, List, Optional, Any
import logging
from ..registry import mcp_tool
from ..client import NetBoxClient

logger = logging.getLogger(__name__)


# ========================================
# SITE MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="dcim")
def netbox_create_site(
    client: NetBoxClient,
    name: str,
    slug: str,
    status: str = "active",
    region: Optional[str] = None,
    description: Optional[str] = None,
    physical_address: Optional[str] = None,
    shipping_address: Optional[str] = None,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None,
    contact_email: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new site in NetBox DCIM.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Site name
        slug: URL-friendly identifier
        status: Site status (active, planned, staged, decommissioning, retired)
        region: Optional region name
        description: Optional description
        physical_address: Physical location address
        shipping_address: Shipping address if different
        contact_name: Primary contact name
        contact_phone: Contact phone number
        contact_email: Contact email address
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created site information or error details
        
    Example:
        netbox_create_site("Amsterdam DC", "amsterdam-dc", status="active", confirm=True)
    """
    try:
        if not name or not slug:
            return {
                "success": False,
                "error": "Site name and slug are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating site: {name} (slug: {slug})")
        
        # Build site data
        site_data = {
            "name": name,
            "slug": slug,
            "status": status
        }
        
        if region:
            site_data["region"] = region
        if description:
            site_data["description"] = description
        if physical_address:
            site_data["physical_address"] = physical_address
        if shipping_address:
            site_data["shipping_address"] = shipping_address
        if contact_name:
            site_data["contact_name"] = contact_name
        if contact_phone:
            site_data["contact_phone"] = contact_phone
        if contact_email:
            site_data["contact_email"] = contact_email
        
        # Use dynamic API with safety
        result = client.dcim.sites.create(confirm=confirm, **site_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "site",
            "site": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create site {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_site_info(
    client: NetBoxClient,
    site_name: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific site.
    
    Args:
        client: NetBoxClient instance (injected)
        site_name: Name of the site to retrieve
        
    Returns:
        Site information including racks, devices, and statistics
        
    Example:
        netbox_get_site_info("Amsterdam DC")
    """
    try:
        logger.info(f"Getting site information: {site_name}")
        
        # Find the site
        sites = client.dcim.sites.filter(name=site_name)
        
        if not sites:
            return {
                "success": False,
                "error": f"Site '{site_name}' not found",
                "error_type": "SiteNotFound"
            }
        
        site = sites[0]
        site_id = site["id"]
        
        # Get related objects
        racks = client.dcim.racks.filter(site_id=site_id)
        devices = client.dcim.devices.filter(site_id=site_id)
        
        return {
            "success": True,
            "site": site,
            "statistics": {
                "rack_count": len(racks),
                "device_count": len(devices),
                "total_rack_units": sum(rack.get("u_height", 0) for rack in racks)
            },
            "racks": racks,
            "devices": devices[:10]  # Limit to first 10 devices
        }
        
    except Exception as e:
        logger.error(f"Failed to get site info for {site_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# MANUFACTURER MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="dcim")
def netbox_create_manufacturer(
    client: NetBoxClient,
    name: str,
    slug: str,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new manufacturer in NetBox DCIM.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Manufacturer name
        slug: URL-friendly identifier
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created manufacturer information or error details
        
    Example:
        netbox_create_manufacturer("Cisco Systems", "cisco", confirm=True)
    """
    try:
        if not name or not slug:
            return {
                "success": False,
                "error": "Manufacturer name and slug are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating manufacturer: {name} (slug: {slug})")
        
        # Build manufacturer data
        manufacturer_data = {
            "name": name,
            "slug": slug
        }
        
        if description:
            manufacturer_data["description"] = description
        
        # Use dynamic API with safety
        result = client.dcim.manufacturers.create(confirm=confirm, **manufacturer_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "manufacturer",
            "manufacturer": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create manufacturer {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# DEVICE TYPE MANAGEMENT TOOLS
# ========================================

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


# ========================================
# DEVICE ROLE MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="dcim")
def netbox_create_device_role(
    client: NetBoxClient,
    name: str,
    slug: str,
    color: str = "9e9e9e",
    vm_role: bool = False,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new device role in NetBox DCIM.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Role name
        slug: URL-friendly identifier
        color: Hex color code (without #)
        vm_role: Whether role applies to virtual machines
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created device role information or error details
        
    Example:
        netbox_create_device_role("Router", "router", color="2196f3", confirm=True)
    """
    try:
        if not name or not slug:
            return {
                "success": False,
                "error": "Role name and slug are required",
                "error_type": "ValidationError"
            }
        
        # Validate color format
        if not color.startswith('#'):
            color = color.lstrip('#')
        if len(color) != 6:
            return {
                "success": False,
                "error": "Color must be a 6-character hex code",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating device role: {name} (slug: {slug})")
        
        # Build device role data
        role_data = {
            "name": name,
            "slug": slug,
            "color": color,
            "vm_role": vm_role
        }
        
        if description:
            role_data["description"] = description
        
        # Use dynamic API with safety
        result = client.dcim.device_roles.create(confirm=confirm, **role_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "device_role",
            "device_role": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create device role {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# DEVICE MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="dcim")
def netbox_create_device(
    client: NetBoxClient,
    name: str,
    device_type: str,
    site: str,
    role: str,
    status: str = "active",
    rack: Optional[str] = None,
    position: Optional[int] = None,
    face: str = "front",
    serial: Optional[str] = None,
    asset_tag: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new device in NetBox DCIM.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Device name (hostname)
        device_type: Device type model or slug
        site: Site name or slug
        role: Device role name or slug
        status: Device status (active, planned, staged, failed, inventory, decommissioning, offline)
        rack: Optional rack name
        position: Rack position (bottom U)
        face: Rack face (front, rear)
        serial: Serial number
        asset_tag: Asset tag
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created device information or error details
        
    Example:
        netbox_create_device("rtr-01", "isr4331", "amsterdam-dc", "router", confirm=True)
    """
    try:
        if not name or not device_type or not site or not role:
            return {
                "success": False,
                "error": "Device name, type, site, and role are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating device: {name} ({device_type})")
        
        # Resolve foreign key references
        foreign_keys = {}
        
        # Resolve device_type
        if isinstance(device_type, str) and not device_type.isdigit():
            device_types = client.dcim.device_types.filter(model=device_type)
            if not device_types:
                device_types = client.dcim.device_types.filter(slug=device_type)
            if device_types:
                foreign_keys["device_type"] = device_types[0]["id"]
            else:
                return {
                    "success": False,
                    "error": f"Device type '{device_type}' not found",
                    "error_type": "DeviceTypeNotFound"
                }
        else:
            foreign_keys["device_type"] = device_type
        
        # Resolve site
        if isinstance(site, str) and not site.isdigit():
            sites = client.dcim.sites.filter(slug=site)
            if not sites:
                sites = client.dcim.sites.filter(name=site)
            if sites:
                foreign_keys["site"] = sites[0]["id"]
            else:
                return {
                    "success": False,
                    "error": f"Site '{site}' not found",
                    "error_type": "SiteNotFound"
                }
        else:
            foreign_keys["site"] = site
        
        # Resolve role
        if isinstance(role, str) and not role.isdigit():
            roles = client.dcim.device_roles.filter(slug=role)
            if not roles:
                roles = client.dcim.device_roles.filter(name=role)
            if roles:
                foreign_keys["role"] = roles[0]["id"]
            else:
                return {
                    "success": False,
                    "error": f"Device role '{role}' not found",
                    "error_type": "DeviceRoleNotFound"
                }
        else:
            foreign_keys["role"] = role
        
        # Resolve rack if provided
        if rack:
            if isinstance(rack, str) and not rack.isdigit():
                racks = client.dcim.racks.filter(name=rack, site_id=foreign_keys["site"])
                if racks:
                    foreign_keys["rack"] = racks[0]["id"]
                else:
                    return {
                        "success": False,
                        "error": f"Rack '{rack}' not found in site",
                        "error_type": "RackNotFound"
                    }
            else:
                foreign_keys["rack"] = rack
        
        # Build device data
        device_data = {
            "name": name,
            "device_type": foreign_keys["device_type"],
            "site": foreign_keys["site"],
            "role": foreign_keys["role"],
            "status": status,
            "face": face
        }
        
        if rack:
            device_data["rack"] = foreign_keys.get("rack", rack)
        if position is not None:
            device_data["position"] = position
        if serial:
            device_data["serial"] = serial
        if asset_tag:
            device_data["asset_tag"] = asset_tag
        if description:
            device_data["description"] = description
        
        # Use dynamic API with safety
        result = client.dcim.devices.create(confirm=confirm, **device_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "device",
            "device": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create device {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_device_info(
    client: NetBoxClient,
    device_name: str,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive information about a device.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        site: Optional site name for filtering
        
    Returns:
        Device information including interfaces, connections, and power
        
    Example:
        netbox_get_device_info("rtr-01", site="amsterdam-dc")
    """
    try:
        logger.info(f"Getting device information: {device_name}")
        
        # Build filter
        device_filter = {"name": device_name}
        if site:
            device_filter["site"] = site
        
        # Find the device
        devices = client.dcim.devices.filter(**device_filter)
        
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found" + (f" in site '{site}'" if site else ""),
                "error_type": "DeviceNotFound"
            }
        
        device = devices[0]
        device_id = device["id"]
        
        # Get related information
        interfaces = client.dcim.interfaces.filter(device_id=device_id)
        cables = client.dcim.cables.filter(termination_a_id=device_id)
        # Power connections endpoint doesn't exist in this NetBox version
        power_connections = []
        
        return {
            "success": True,
            "device": device,
            "interfaces": interfaces,
            "cables": cables,
            "power_connections": power_connections,
            "statistics": {
                "interface_count": len(interfaces),
                "cable_count": len(cables),
                "power_connection_count": len(power_connections)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get device info for {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# RACK MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="dcim")
def netbox_create_rack(
    client: NetBoxClient,
    name: str,
    site: str,
    u_height: int = 42,
    width: int = 19,
    status: str = "active",
    role: Optional[str] = None,
    facility_id: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new rack in NetBox DCIM.
    
    Args:
        client: NetBoxClient instance (injected)
        name: Rack name
        site: Site name or slug
        u_height: Height in rack units (1-100)
        width: Width in inches (10, 19, 21, 23)
        status: Rack status (active, planned, reserved, available, deprecated)
        role: Optional rack role
        facility_id: Facility identifier
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Created rack information or error details
        
    Example:
        netbox_create_rack("Rack-A01", "amsterdam-dc", u_height=42, confirm=True)
    """
    try:
        if not name or not site:
            return {
                "success": False,
                "error": "Rack name and site are required",
                "error_type": "ValidationError"
            }
        
        if not (1 <= u_height <= 100):
            return {
                "success": False,
                "error": "U-height must be between 1 and 100",
                "error_type": "ValidationError"
            }
        
        if width not in [10, 19, 21, 23]:
            return {
                "success": False,
                "error": "Width must be 10, 19, 21, or 23 inches",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating rack: {name} at {site}")
        
        # Resolve site reference
        site_id = site
        if isinstance(site, str) and not site.isdigit():
            sites = client.dcim.sites.filter(slug=site)
            if not sites:
                sites = client.dcim.sites.filter(name=site)
            if sites:
                site_id = sites[0]["id"]
            else:
                return {
                    "success": False,
                    "error": f"Site '{site}' not found",
                    "error_type": "SiteNotFound"
                }
        
        # Build rack data
        rack_data = {
            "name": name,
            "site": site_id,
            "u_height": u_height,
            "width": width,
            "status": status
        }
        
        if role:
            rack_data["role"] = role
        if facility_id:
            rack_data["facility_id"] = facility_id
        if description:
            rack_data["description"] = description
        
        # Use dynamic API with safety
        result = client.dcim.racks.create(confirm=confirm, **rack_data)
        
        return {
            "success": True,
            "action": "created",
            "object_type": "rack",
            "rack": result,
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to create rack {name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_get_rack_elevation(
    client: NetBoxClient,
    rack_name: str,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get rack elevation showing device positions.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Name of the rack
        site: Optional site for filtering
        
    Returns:
        Rack elevation with device positions
        
    Example:
        netbox_get_rack_elevation("Rack-A01", site="amsterdam-dc")
    """
    try:
        logger.info(f"Getting rack elevation: {rack_name}")
        
        # Build filter
        rack_filter = {"name": rack_name}
        if site:
            rack_filter["site"] = site
        
        # Find the rack
        racks = client.dcim.racks.filter(**rack_filter)
        
        if not racks:
            return {
                "success": False,
                "error": f"Rack '{rack_name}' not found" + (f" in site '{site}'" if site else ""),
                "error_type": "RackNotFound"
            }
        
        rack = racks[0]
        rack_id = rack["id"]
        
        # Get devices in rack
        devices = client.dcim.devices.filter(rack_id=rack_id)
        
        # Build elevation map
        elevation = {}
        for device in devices:
            position = device.get("position")
            if position:
                # Handle device_type as either dict or int
                device_type_info = device.get("device_type", {})
                if isinstance(device_type_info, dict):
                    device_type_model = device_type_info.get("model", "Unknown")
                    device_u_height = device_type_info.get("u_height", 1)
                else:
                    # device_type is an ID, need to resolve it
                    device_type_model = "Unknown"
                    device_u_height = 1
                
                elevation[position] = {
                    "device": device["name"],
                    "device_type": device_type_model,
                    "u_height": device_u_height,
                    "face": device.get("face", "front")
                }
        
        # Calculate used units properly
        used_units = 0
        for device in devices:
            device_type_info = device.get("device_type", {})
            if isinstance(device_type_info, dict):
                used_units += device_type_info.get("u_height", 1)
            else:
                used_units += 1  # Default to 1U if we can't determine
        
        return {
            "success": True,
            "rack": rack,
            "device_count": len(devices),
            "available_units": rack["u_height"] - used_units,
            "elevation": elevation,
            "devices": devices
        }
        
    except Exception as e:
        logger.error(f"Failed to get rack elevation for {rack_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# HIGH-LEVEL DEVICE PROVISIONING TOOLS
# ========================================

@mcp_tool(category="dcim")
def netbox_provision_new_device(
    client: NetBoxClient,
    device_name: str,
    site_name: str,
    rack_name: str,
    device_model: str,
    role_name: str,
    position: int,
    status: str = "active",
    face: str = "front",
    tenant: Optional[str] = None,
    platform: Optional[str] = None,
    serial: Optional[str] = None,
    asset_tag: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Provision a complete new device in a rack with a single function call.
    
    This high-level function reduces 5-6 potential API calls and complex validations 
    into one single, logical function. Essential for data center provisioning workflows.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name for the new device
        site_name: Name of the site where the rack is located
        rack_name: Name of the rack to place the device in
        device_model: Device model name or slug (will be resolved to device_type)
        role_name: Device role name or slug
        position: Rack position (1-based, from bottom)
        status: Device status (active, offline, planned, staged, failed, inventory, decommissioning)
        face: Rack face (front, rear)
        tenant: Optional tenant name or slug
        platform: Optional platform name or slug
        serial: Optional serial number
        asset_tag: Optional asset tag
        description: Optional description
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Complete device provisioning result with all resolved information
        
    Example:
        netbox_provision_new_device(
            device_name="sw-floor3-001", 
            site_name="Main DC", 
            rack_name="R-12", 
            device_model="C9300-24T", 
            role_name="Access Switch", 
            position=42, 
            confirm=True
        )
    """
    try:
        if not all([device_name, site_name, rack_name, device_model, role_name]):
            return {
                "success": False,
                "error": "device_name, site_name, rack_name, device_model, and role_name are required",
                "error_type": "ValidationError"
            }
        
        if not (1 <= position <= 100):
            return {
                "success": False,
                "error": "Position must be between 1 and 100",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Provisioning device: {device_name} in {site_name}/{rack_name} at position {position}")
        
        # Step 1: Find the site
        logger.debug(f"Looking up site: {site_name}")
        sites = client.dcim.sites.filter(name=site_name)
        if not sites:
            sites = client.dcim.sites.filter(slug=site_name)
        if not sites:
            return {
                "success": False,
                "error": f"Site '{site_name}' not found",
                "error_type": "NotFoundError"
            }
        site = sites[0]
        site_id = site["id"]
        logger.debug(f"Found site: {site['name']} (ID: {site_id})")
        
        # Step 2: Find the rack within that site
        logger.debug(f"Looking up rack: {rack_name} in site {site['name']}")
        racks = client.dcim.racks.filter(site_id=site_id, name=rack_name)
        if not racks:
            return {
                "success": False,
                "error": f"Rack '{rack_name}' not found in site '{site['name']}'",
                "error_type": "NotFoundError"
            }
        rack = racks[0]
        rack_id = rack["id"]
        logger.debug(f"Found rack: {rack['name']} (ID: {rack_id})")
        
        # Step 3: Find the device type
        logger.debug(f"Looking up device type: {device_model}")
        device_types = client.dcim.device_types.filter(model=device_model)
        if not device_types:
            device_types = client.dcim.device_types.filter(slug=device_model)
        if not device_types:
            return {
                "success": False,
                "error": f"Device type '{device_model}' not found",
                "error_type": "NotFoundError"
            }
        device_type = device_types[0]
        device_type_id = device_type["id"]
        logger.debug(f"Found device type: {device_type['model']} (ID: {device_type_id})")
        
        # Step 4: Find the device role
        logger.debug(f"Looking up device role: {role_name}")
        roles = client.dcim.device_roles.filter(name=role_name)
        if not roles:
            roles = client.dcim.device_roles.filter(slug=role_name)
        if not roles:
            return {
                "success": False,
                "error": f"Device role '{role_name}' not found",
                "error_type": "NotFoundError"
            }
        role = roles[0]
        role_id = role["id"]
        logger.debug(f"Found device role: {role['name']} (ID: {role_id})")
        
        # Step 5: Validate rack position availability
        logger.debug(f"Validating position {position} availability in rack {rack['name']}")
        
        # Check if position is within rack height
        if position > rack["u_height"]:
            return {
                "success": False,
                "error": f"Position {position} exceeds rack height of {rack['u_height']}U",
                "error_type": "ValidationError"
            }
        
        # Check if position is already occupied
        existing_devices = client.dcim.devices.filter(rack_id=rack_id, position=position)
        if existing_devices:
            return {
                "success": False,
                "error": f"Position {position} is already occupied by device '{existing_devices[0]['name']}'",
                "error_type": "ConflictError"
            }
        
        # Check if device extends beyond rack height
        device_u_height = int(device_type.get("u_height", 1))
        if position + device_u_height - 1 > rack["u_height"]:
            return {
                "success": False,
                "error": f"Device height ({device_u_height}U) at position {position} would exceed rack height of {rack['u_height']}U",
                "error_type": "ValidationError"
            }
        
        # Check for overlapping devices
        for check_pos in range(position, position + int(device_u_height)):
            overlapping = client.dcim.devices.filter(rack_id=rack_id, position=check_pos)
            if overlapping:
                return {
                    "success": False,
                    "error": f"Device would overlap with existing device '{overlapping[0]['name']}' at position {check_pos}",
                    "error_type": "ConflictError"
                }
        
        # Step 6: Resolve optional foreign keys
        tenant_id = None
        tenant_name = None
        if tenant:
            logger.debug(f"Looking up tenant: {tenant}")
            tenants = client.tenancy.tenants.filter(name=tenant)
            if not tenants:
                tenants = client.tenancy.tenants.filter(slug=tenant)
            if tenants:
                tenant_id = tenants[0]["id"]
                tenant_name = tenants[0]["name"]
                logger.debug(f"Found tenant: {tenant_name} (ID: {tenant_id})")
            else:
                logger.warning(f"Tenant '{tenant}' not found, proceeding without tenant assignment")
        
        platform_id = None
        platform_name = None
        if platform:
            logger.debug(f"Looking up platform: {platform}")
            platforms = client.dcim.platforms.filter(name=platform)
            if not platforms:
                platforms = client.dcim.platforms.filter(slug=platform)
            if platforms:
                platform_id = platforms[0]["id"]
                platform_name = platforms[0]["name"]
                logger.debug(f"Found platform: {platform_name} (ID: {platform_id})")
            else:
                logger.warning(f"Platform '{platform}' not found, proceeding without platform assignment")
        
        # Step 7: Assemble the complete payload
        device_data = {
            "name": device_name,
            "device_type": device_type_id,
            "role": role_id,
            "site": site_id,
            "rack": rack_id,
            "position": position,
            "face": face,
            "status": status
        }
        
        # Add optional fields
        if tenant_id:
            device_data["tenant"] = tenant_id
        if platform_id:
            device_data["platform"] = platform_id
        if serial:
            device_data["serial"] = serial
        if asset_tag:
            device_data["asset_tag"] = asset_tag
        if description:
            device_data["description"] = description
        
        # Step 8: Create the device
        if not confirm:
            # Dry run mode - return what would be created without actually creating
            logger.info(f"DRY RUN: Would create device with data: {device_data}")
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "device",
                "device": {"name": device_name, "dry_run": True, "would_create": device_data},
                "resolved_references": {
                    "site": {"name": site["name"], "id": site_id},
                    "rack": {"name": rack["name"], "id": rack_id, "position": position},
                    "device_type": {"model": device_type["model"], "id": device_type_id, "u_height": device_u_height},
                    "role": {"name": role["name"], "id": role_id},
                    "tenant": {"name": tenant_name, "id": tenant_id} if tenant_id else None,
                    "platform": {"name": platform_name, "id": platform_id} if platform_id else None
                },
                "dry_run": True
            }
        
        logger.info(f"Creating device with data: {device_data}")
        result = client.dcim.devices.create(confirm=confirm, **device_data)
        
        return {
            "success": True,
            "action": "provisioned",
            "object_type": "device",
            "device": result,
            "resolved_references": {
                "site": {"name": site["name"], "id": site_id},
                "rack": {"name": rack["name"], "id": rack_id, "position": position},
                "device_type": {"model": device_type["model"], "id": device_type_id, "u_height": device_u_height},
                "role": {"name": role["name"], "id": role_id},
                "tenant": {"name": tenant_name, "id": tenant_id} if tenant_id else None,
                "platform": {"name": platform_name, "id": platform_id} if platform_id else None
            },
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to provision device {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_assign_ip_to_interface(
    client: NetBoxClient,
    device_name: str,
    interface_name: str,
    ip_address: str,
    status: str = "active",
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Assign an IP address directly to a device interface with a single function call.
    
    This cross-domain function bridges IPAM and DCIM by creating IP addresses and 
    assigning them directly to device interfaces. Essential for interface configuration workflows.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device containing the interface
        interface_name: Name of the interface to assign IP to
        ip_address: IP address with CIDR notation (e.g., "10.0.0.1/24")
        status: IP address status (active, reserved, deprecated, dhcp, slaac)
        description: Optional description for the IP address
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        IP assignment result with device and interface information
        
    Example:
        netbox_assign_ip_to_interface(
            device_name="sw-floor3-001",
            interface_name="Vlan100", 
            ip_address="10.100.0.1/24",
            description="Management IP for Floor 3 switch",
            confirm=True
        )
    """
    try:
        if not all([device_name, interface_name, ip_address]):
            return {
                "success": False,
                "error": "device_name, interface_name, and ip_address are required",
                "error_type": "ValidationError"
            }
        
        # Validate IP address format
        import ipaddress
        try:
            ip_obj = ipaddress.ip_interface(ip_address)
            ip_str = str(ip_obj.ip)
            prefix_length = ip_obj.network.prefixlen
            ip_with_cidr = f"{ip_str}/{prefix_length}"
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid IP address format '{ip_address}': {e}",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Assigning IP {ip_with_cidr} to {device_name}:{interface_name}")
        
        # Step 1: Find the device
        logger.debug(f"Looking up device: {device_name}")
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            return {
                "success": False,
                "error": f"Device '{device_name}' not found",
                "error_type": "NotFoundError"
            }
        device = devices[0]
        device_id = device["id"]
        logger.debug(f"Found device: {device['name']} (ID: {device_id})")
        
        # Step 2: Find the interface within that device
        logger.debug(f"Looking up interface: {interface_name} on device {device['name']}")
        interfaces = client.dcim.interfaces.filter(device_id=device_id, name=interface_name)
        if not interfaces:
            return {
                "success": False,
                "error": f"Interface '{interface_name}' not found on device '{device['name']}'",
                "error_type": "NotFoundError"
            }
        interface = interfaces[0]
        interface_id = interface["id"]
        logger.debug(f"Found interface: {interface['name']} (ID: {interface_id})")
        
        # Step 3: Check for existing IP assignments on this interface
        # Note: We can't filter by assigned_object_type during create, so we'll get all IPs
        # assigned to this interface_id and filter afterwards
        all_assigned_ips = client.ipam.ip_addresses.filter(assigned_object_id=interface_id)
        existing_ips = [ip for ip in all_assigned_ips if ip.get("assigned_object_type") == "dcim.interface"]
        
        # Check for IP conflicts
        conflicting_ips = client.ipam.ip_addresses.filter(address=ip_with_cidr)
        if conflicting_ips:
            conflict_info = conflicting_ips[0]
            assigned_to = "unassigned"
            if conflict_info.get("assigned_object_type") and conflict_info.get("assigned_object_id"):
                assigned_to = f"{conflict_info['assigned_object_type']} ID {conflict_info['assigned_object_id']}"
            
            return {
                "success": False,
                "error": f"IP address {ip_with_cidr} is already assigned to {assigned_to}",
                "error_type": "ConflictError"
            }
        
        if not confirm:
            # Dry run mode
            logger.info(f"DRY RUN: Would assign IP {ip_with_cidr} to interface {interface['name']}")
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "ip_address",
                "ip_assignment": {
                    "ip_address": ip_with_cidr,
                    "device": {"name": device["name"], "id": device_id},
                    "interface": {"name": interface["name"], "id": interface_id},
                    "existing_ips": len(existing_ips),
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Step 4: Create IP address and assign to interface (two-step approach)
        # NetBox create operation doesn't accept assigned_object_type, but update does
        
        # First, create the IP address without assignment
        ip_data_basic = {
            "address": ip_with_cidr,
            "status": status
        }
        
        if description:
            ip_data_basic["description"] = description
        
        logger.info(f"Creating IP address: {ip_data_basic}")
        created_ip = client.ipam.ip_addresses.create(confirm=confirm, **ip_data_basic)
        
        if not confirm:
            # For dry run, we can't do the assignment step, so return the basic creation result
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "ip_address",
                "ip_assignment": {
                    "ip_address": ip_with_cidr,
                    "device": {"name": device["name"], "id": device_id},
                    "interface": {"name": interface["name"], "id": interface_id},
                    "existing_ips": len(existing_ips),
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Step 5: Assign the IP to the interface using update
        assignment_data = {
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": interface_id
        }
        
        logger.info(f"Assigning IP to interface: {assignment_data}")
        result = client.ipam.ip_addresses.update(created_ip["id"], confirm=True, **assignment_data)
        
        return {
            "success": True,
            "action": "assigned",
            "object_type": "ip_address",
            "ip_address": result,
            "assignment_details": {
                "device": {"name": device["name"], "id": device_id},
                "interface": {"name": interface["name"], "id": interface_id, "type": interface.get("type")},
                "ip_with_cidr": ip_with_cidr,
                "status": status,
                "existing_ips_on_interface": len(existing_ips)
            },
            "dry_run": result.get("dry_run", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to assign IP {ip_address} to {device_name}:{interface_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }