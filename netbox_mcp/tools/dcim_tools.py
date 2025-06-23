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

# netbox_create_manufacturer migrated to dcim/manufacturers.py


# ========================================
# DEVICE TYPE MANAGEMENT TOOLS
# ========================================

# netbox_create_device_type migrated to dcim/device_types.py


# ========================================
# DEVICE ROLE MANAGEMENT TOOLS
# ========================================

# netbox_create_device_role migrated to dcim/device_roles.py


# ========================================
# DEVICE MANAGEMENT TOOLS
# ========================================

# netbox_create_device migrated to dcim/devices.py
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


# netbox_get_device_info migrated to dcim/devices.py


# ========================================
# RACK MANAGEMENT TOOLS
# ========================================
# NOTE: Rack management tools migrated to dcim/racks.py

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

# netbox_provision_new_device migrated to dcim/devices.py


# netbox_assign_ip_to_interface migrated to dcim/interfaces.py


@mcp_tool(category="dcim")
def netbox_get_rack_inventory(
    client: NetBoxClient,
    site_name: str,
    rack_name: str,
    include_detailed: bool = False
) -> Dict[str, Any]:
    """
    Generate a comprehensive, human-readable inventory report for all devices in a specific rack.
    
    This reporting tool transforms raw NetBox data into a clean, organized rack inventory
    that provides essential information for capacity planning and data center documentation.
    
    Args:
        client: NetBoxClient instance (injected)
        site_name: Name of the site containing the rack
        rack_name: Name of the rack to inventory
        include_detailed: Include detailed device information (interfaces, IPs, etc.)
        
    Returns:
        Comprehensive rack inventory with utilization statistics and device details
        
    Example:
        netbox_get_rack_inventory(
            site_name="Main DC",
            rack_name="R-12",
            include_detailed=True
        )
    """
    try:
        if not all([site_name, rack_name]):
            return {
                "success": False,
                "error": "site_name and rack_name are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Generating rack inventory for {site_name}/{rack_name}")
        
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
        rack_height = rack["u_height"]
        logger.debug(f"Found rack: {rack['name']} (ID: {rack_id}, Height: {rack_height}U)")
        
        # Step 3: Get all devices in this rack
        logger.debug(f"Retrieving all devices in rack {rack['name']}")
        devices = client.dcim.devices.filter(rack_id=rack_id)
        logger.debug(f"Found {len(devices)} devices in rack")
        
        # Step 4: Process devices and organize by position
        device_inventory = {}
        occupied_positions = set()
        
        for device in devices:
            position = device.get("position")
            device_type = device.get("device_type")
            
            if position is not None:
                # Get device type details
                device_type_info = None
                if device_type:
                    device_types = client.dcim.device_types.filter(id=device_type)
                    if device_types:
                        device_type_info = device_types[0]
                
                # Calculate device height and occupied positions (ensure integers)
                device_height = 1
                if device_type_info:
                    device_height = int(device_type_info.get("u_height", 1))
                
                # Ensure position is also an integer
                position = int(position)
                
                # Mark all positions occupied by this device
                for u in range(position, position + device_height):
                    occupied_positions.add(u)
                
                # Get role name (handle both ID and object formats)
                role_name = "Unknown"
                role_data = device.get("role")
                if role_data:
                    if isinstance(role_data, dict):
                        role_name = role_data.get("name", "Unknown")
                    else:
                        # If it's an ID, look up the role
                        try:
                            roles = client.dcim.device_roles.filter(id=role_data)
                            if roles:
                                role_name = roles[0].get("name", "Unknown")
                        except Exception as e:
                            logger.warning(f"Could not resolve role ID {role_data}: {e}")
                
                # Get manufacturer name safely
                manufacturer_name = "Unknown"
                if device_type_info:
                    manufacturer_data = device_type_info.get("manufacturer")
                    if isinstance(manufacturer_data, dict):
                        manufacturer_name = manufacturer_data.get("name", "Unknown")
                    elif manufacturer_data:
                        # If it's an ID, look up the manufacturer
                        try:
                            manufacturers = client.dcim.manufacturers.filter(id=manufacturer_data)
                            if manufacturers:
                                manufacturer_name = manufacturers[0].get("name", "Unknown")
                        except Exception as e:
                            logger.warning(f"Could not resolve manufacturer ID {manufacturer_data}: {e}")
                
                # Get IP addresses safely
                primary_ip4 = None
                primary_ip6 = None
                primary_ip4_data = device.get("primary_ip4")
                primary_ip6_data = device.get("primary_ip6")
                
                if primary_ip4_data:
                    if isinstance(primary_ip4_data, dict):
                        primary_ip4 = primary_ip4_data.get("address")
                    else:
                        # If it's an ID, we could look it up, but for now just note it exists
                        primary_ip4 = f"IP ID: {primary_ip4_data}"
                
                if primary_ip6_data:
                    if isinstance(primary_ip6_data, dict):
                        primary_ip6 = primary_ip6_data.get("address")
                    else:
                        primary_ip6 = f"IP ID: {primary_ip6_data}"
                
                # Basic device information
                device_info = {
                    "name": device.get("name", "Unknown"),
                    "position": position,
                    "height": device_height,
                    "device_type": device_type_info.get("model", "Unknown") if device_type_info else "Unknown",
                    "manufacturer": manufacturer_name,
                    "status": device.get("status", "unknown"),
                    "serial": device.get("serial", ""),
                    "asset_tag": device.get("asset_tag", ""),
                    "role": role_name,
                    "primary_ip": None,
                    "primary_ip4": primary_ip4,
                    "primary_ip6": primary_ip6
                }
                
                # Determine primary IP
                if device_info["primary_ip4"]:
                    device_info["primary_ip"] = device_info["primary_ip4"]
                elif device_info["primary_ip6"]:
                    device_info["primary_ip"] = device_info["primary_ip6"]
                
                # Add detailed information if requested
                if include_detailed:
                    device_info["detailed"] = {
                        "description": device.get("description", ""),
                        "platform": device.get("platform", {}).get("name") if device.get("platform") else None,
                        "tenant": device.get("tenant", {}).get("name") if device.get("tenant") else None,
                        "face": device.get("face", "front"),
                        "device_id": device.get("id"),
                        "url": device.get("url", ""),
                        "created": device.get("created", ""),
                        "last_updated": device.get("last_updated", "")
                    }
                    
                    # Get interface count
                    try:
                        interfaces = client.dcim.interfaces.filter(device_id=device["id"])
                        device_info["detailed"]["interface_count"] = len(interfaces)
                    except Exception as e:
                        logger.warning(f"Could not get interface count for device {device['name']}: {e}")
                        device_info["detailed"]["interface_count"] = 0
                
                device_inventory[position] = device_info
        
        # Step 5: Generate position map
        position_map = []
        for u in range(1, rack_height + 1):
            if u in occupied_positions:
                device = device_inventory.get(u)
                position_map.append({
                    "position": u,
                    "status": "occupied",
                    "device": device
                })
            else:
                position_map.append({
                    "position": u,
                    "status": "available",
                    "device": None
                })
        
        # Step 6: Calculate utilization statistics
        total_positions = rack_height
        occupied_count = len(occupied_positions)
        available_count = total_positions - occupied_count
        utilization_percent = (occupied_count / total_positions * 100) if total_positions > 0 else 0
        
        # Step 7: Sort devices by position (ascending - bottom to top)
        devices_by_position = sorted(device_inventory.values(), key=lambda d: d["position"])
        
        # Generate status overview
        status_counts = {}
        for device in devices_by_position:
            status = device.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "success": True,
            "rack_info": {
                "site": site["name"],
                "rack_name": rack["name"],
                "rack_height": rack_height,
                "rack_width": rack.get("width", 19),
                "rack_status": rack.get("status", "unknown"),
                "rack_description": rack.get("description", ""),
                "rack_id": rack_id,
                "rack_url": rack.get("url", "")
            },
            "utilization": {
                "total_positions": total_positions,
                "occupied_positions": occupied_count,
                "available_positions": available_count,
                "utilization_percentage": round(utilization_percent, 1),
                "device_count": len(devices)
            },
            "devices": devices_by_position,
            "position_map": sorted(position_map, key=lambda p: p["position"], reverse=True),  # Top to bottom view
            "summary": {
                "rack_location": f"{site['name']} > {rack['name']}",
                "capacity": f"{occupied_count}/{total_positions}U occupied ({utilization_percent:.1f}%)",
                "device_summary": f"{len(devices)} devices installed" if devices else "Rack is empty",
                "status_overview": status_counts
            },
            "detailed": include_detailed
        }
        
    except Exception as e:
        logger.error(f"Failed to generate rack inventory for {site_name}/{rack_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# netbox_decommission_device migrated to dcim/devices.py


# netbox_create_cable_connection migrated to dcim/interfaces.py


# ========================================
# DEVICE COMPONENT MANAGEMENT TOOLS
# ========================================

# netbox_install_module_in_device migrated to dcim/modules.py


# netbox_add_power_port_to_device migrated to dcim/modules.py