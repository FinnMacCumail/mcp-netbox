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
    
    This tool simplifies documenting physical connections by handling device/interface
    lookups and creating cable objects that link two termination points. Essential
    for cable management and network topology documentation.
    
    Args:
        client: NetBoxClient instance (injected)
        device_a_name: Name of the first device
        interface_a_name: Name of the interface on device A
        device_b_name: Name of the second device  
        interface_b_name: Name of the interface on device B
        cable_type: Type of cable (cat5e, cat6, cat6a, fiber, power, coax, dac)
        cable_status: Cable status (connected, planned, decommissioning)
        cable_length: Length of the cable
        cable_length_unit: Unit for cable length (m, ft, in, cm)
        label: Optional cable label for identification
        description: Optional description of the connection
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Cable connection creation result with termination details
        
    Example:
        netbox_create_cable_connection(
            device_a_name="sw-01",
            interface_a_name="GigabitEthernet0/1",
            device_b_name="sw-02", 
            interface_b_name="GigabitEthernet0/1",
            cable_type="cat6",
            cable_length=3,
            label="SW01-SW02-TRUNK",
            confirm=True
        )
    """
    try:
        if not all([device_a_name, interface_a_name, device_b_name, interface_b_name]):
            return {
                "success": False,
                "error": "device_a_name, interface_a_name, device_b_name, and interface_b_name are required",
                "error_type": "ValidationError"
            }
        
        # Validate cable parameters
        valid_cable_types = ["cat3", "cat5", "cat5e", "cat6", "cat6a", "cat7", "cat8", 
                           "dac-active", "dac-passive", "mrj21-trunk", "coaxial", 
                           "mmf", "mmf-om1", "mmf-om2", "mmf-om3", "mmf-om4", "mmf-om5",
                           "smf", "smf-os1", "smf-os2", "aoc", "power", "usb", "other"]
        
        valid_cable_statuses = ["connected", "planned", "decommissioning"]
        valid_length_units = ["km", "m", "cm", "mi", "ft", "in"]
        
        if cable_type not in valid_cable_types:
            return {
                "success": False,
                "error": f"Invalid cable_type. Must be one of: {valid_cable_types}",
                "error_type": "ValidationError"
            }
        
        if cable_status not in valid_cable_statuses:
            return {
                "success": False,
                "error": f"Invalid cable_status. Must be one of: {valid_cable_statuses}",
                "error_type": "ValidationError"
            }
        
        if cable_length_unit not in valid_length_units:
            return {
                "success": False,
                "error": f"Invalid cable_length_unit. Must be one of: {valid_length_units}",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Creating cable connection: {device_a_name}:{interface_a_name} ↔ {device_b_name}:{interface_b_name}")
        
        # Step 1: Find Device A and Interface A
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
        logger.debug(f"Found device A: {device_a['name']} (ID: {device_a_id})")
        
        logger.debug(f"Looking up interface A: {interface_a_name} on device {device_a['name']}")
        interfaces_a = client.dcim.interfaces.filter(device_id=device_a_id, name=interface_a_name)
        if not interfaces_a:
            return {
                "success": False,
                "error": f"Interface A '{interface_a_name}' not found on device '{device_a['name']}'",
                "error_type": "NotFoundError"
            }
        interface_a = interfaces_a[0]
        interface_a_id = interface_a["id"]
        logger.debug(f"Found interface A: {interface_a['name']} (ID: {interface_a_id})")
        
        # Step 2: Find Device B and Interface B
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
        logger.debug(f"Found device B: {device_b['name']} (ID: {device_b_id})")
        
        logger.debug(f"Looking up interface B: {interface_b_name} on device {device_b['name']}")
        interfaces_b = client.dcim.interfaces.filter(device_id=device_b_id, name=interface_b_name)
        if not interfaces_b:
            return {
                "success": False,
                "error": f"Interface B '{interface_b_name}' not found on device '{device_b['name']}'",
                "error_type": "NotFoundError"
            }
        interface_b = interfaces_b[0]
        interface_b_id = interface_b["id"]
        logger.debug(f"Found interface B: {interface_b['name']} (ID: {interface_b_id})")
        
        # Step 3: Validate interface availability (refresh interface data for accurate cable status)
        logger.debug("Validating interface availability...")
        
        # Refresh interface data to get current cable status (avoid cache issues)
        try:
            fresh_interfaces_a = client.dcim.interfaces.filter(device_id=device_a_id, name=interface_a_name)
            if fresh_interfaces_a:
                fresh_interface_a = fresh_interfaces_a[0]
                if fresh_interface_a.get("cable"):
                    return {
                        "success": False,
                        "error": f"Interface A '{interface_a_name}' on device '{device_a['name']}' is already connected to cable ID {fresh_interface_a['cable']}",
                        "error_type": "ConflictError"
                    }
            
            fresh_interfaces_b = client.dcim.interfaces.filter(device_id=device_b_id, name=interface_b_name)
            if fresh_interfaces_b:
                fresh_interface_b = fresh_interfaces_b[0]
                if fresh_interface_b.get("cable"):
                    return {
                        "success": False,
                        "error": f"Interface B '{interface_b_name}' on device '{device_b['name']}' is already connected to cable ID {fresh_interface_b['cable']}",
                        "error_type": "ConflictError"
                    }
        except Exception as e:
            logger.warning(f"Could not refresh interface data for conflict detection: {e}")
            # Fall back to original interface data
            if interface_a.get("cable"):
                return {
                    "success": False,
                    "error": f"Interface A '{interface_a_name}' on device '{device_a['name']}' is already connected to cable ID {interface_a['cable']}",
                    "error_type": "ConflictError"
                }
            
            if interface_b.get("cable"):
                return {
                    "success": False,
                    "error": f"Interface B '{interface_b_name}' on device '{device_b['name']}' is already connected to cable ID {interface_b['cable']}",
                    "error_type": "ConflictError"
                }
        
        # Check if trying to connect the same interface to itself
        if device_a_id == device_b_id and interface_a_id == interface_b_id:
            return {
                "success": False,
                "error": "Cannot connect an interface to itself",
                "error_type": "ValidationError"
            }
        
        # Step 4: Generate cable data
        cable_data = {
            "a_terminations": [
                {
                    "object_type": "dcim.interface",
                    "object_id": interface_a_id
                }
            ],
            "b_terminations": [
                {
                    "object_type": "dcim.interface", 
                    "object_id": interface_b_id
                }
            ],
            "type": cable_type,
            "status": cable_status
        }
        
        # Add optional fields
        if cable_length is not None:
            cable_data["length"] = cable_length
            cable_data["length_unit"] = cable_length_unit
        
        if label:
            cable_data["label"] = label
        
        if description:
            cable_data["description"] = description
        
        if not confirm:
            # Dry run mode - return what would be created
            logger.info(f"DRY RUN: Would create cable connection")
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "cable",
                "cable_connection": {
                    "termination_a": {
                        "device": device_a["name"],
                        "interface": interface_a["name"],
                        "device_id": device_a_id,
                        "interface_id": interface_a_id
                    },
                    "termination_b": {
                        "device": device_b["name"],
                        "interface": interface_b["name"],
                        "device_id": device_b_id,
                        "interface_id": interface_b_id
                    },
                    "cable_type": cable_type,
                    "cable_status": cable_status,
                    "cable_length": f"{cable_length} {cable_length_unit}" if cable_length else None,
                    "cable_label": label,
                    "dry_run": True
                },
                "dry_run": True
            }
        
        # Step 5: Create the cable
        logger.info(f"Creating cable: {cable_data}")
        try:
            created_cable = client.dcim.cables.create(confirm=True, **cable_data)
            logger.info(f"Cable created successfully with ID: {created_cable['id']}")
            
            # CACHE INVALIDATION: Invalidate interface cache after cable creation
            # This ensures that subsequent queries for interface data return fresh information
            # including the new cable assignment, fixing conflict detection issues
            logger.debug("Invalidating interface cache for connected interfaces...")
            try:
                invalidated_a = client.cache.invalidate_for_object("dcim.interfaces", interface_a_id)
                invalidated_b = client.cache.invalidate_for_object("dcim.interfaces", interface_b_id)
                logger.info(f"Cache invalidated: {invalidated_a + invalidated_b} entries for interfaces {interface_a_id}, {interface_b_id}")
            except Exception as cache_error:
                # Cache invalidation failure should not fail the cable creation
                logger.warning(f"Cache invalidation failed after cable creation: {cache_error}")
            
            return {
                "success": True,
                "action": "created",
                "object_type": "cable",
                "cable": created_cable,
                "connection_details": {
                    "cable_id": created_cable["id"],
                    "cable_type": cable_type,
                    "cable_status": cable_status,
                    "cable_label": label or f"Cable-{created_cable['id']}",
                    "cable_length": f"{cable_length} {cable_length_unit}" if cable_length else "Unspecified",
                    "termination_a": {
                        "device": device_a["name"],
                        "interface": interface_a["name"],
                        "device_id": device_a_id,
                        "interface_id": interface_a_id,
                        "device_url": device_a.get("url", "")
                    },
                    "termination_b": {
                        "device": device_b["name"],
                        "interface": interface_b["name"], 
                        "device_id": device_b_id,
                        "interface_id": interface_b_id,
                        "device_url": device_b.get("url", "")
                    }
                },
                "dry_run": False
            }
            
        except Exception as e:
            logger.error(f"Failed to create cable: {e}")
            return {
                "success": False,
                "error": f"Cable creation failed: {str(e)}",
                "error_type": "CreationError"
            }
        
    except Exception as e:
        logger.error(f"Failed to create cable connection {device_a_name}:{interface_a_name} ↔ {device_b_name}:{interface_b_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ========================================
# DEVICE COMPONENT MANAGEMENT TOOLS
# ========================================

@mcp_tool(category="dcim")
def netbox_install_module_in_device(
    client: NetBoxClient,
    device_name: str,
    module_bay_name: str,
    module_type_model: str,
    serial_number: Optional[str] = None,
    asset_tag: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Install a module in a device bay with comprehensive validation and documentation.
    
    This enterprise-grade module management tool simplifies the complex workflow of
    installing modules (line cards, optics, expansion cards) in device bays, essential
    for accurate infrastructure documentation and capacity management.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the target device
        module_bay_name: Name of the module bay in the device
        module_type_model: Model name of the module type to install
        serial_number: Serial number of the module (optional)
        asset_tag: Asset tag for inventory tracking (optional)
        description: Description of the module installation (optional)
        confirm: Safety confirmation (default: False)
        
    Returns:
        Module installation result with device and bay details
        
    Examples:
        # Install 100G linecard in core router
        netbox_install_module_in_device(
            device_name="core-router-01",
            module_bay_name="Slot 1",
            module_type_model="ASR1000-SIP40",
            serial_number="FXS2124A001",
            asset_tag="LC-001",
            confirm=True
        )
        
        # Install optics module in switch
        netbox_install_module_in_device(
            device_name="dist-sw-01", 
            module_bay_name="QSFP28-1",
            module_type_model="QSFP-100G-SR4",
            description="100G SR4 optics for uplink",
            confirm=True
        )
    """
    try:
        if not confirm:
            return {
                "success": False,
                "error": "Module installation requires confirm=True for safety",
                "error_type": "ValidationError"
            }
        
        if not all([device_name, module_bay_name, module_type_model]):
            return {
                "success": False,
                "error": "device_name, module_bay_name, and module_type_model are required",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Installing module '{module_type_model}' in device '{device_name}' bay '{module_bay_name}'")
        
        # Step 1: Resolve target device
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
        
        # Step 2: Resolve module bay within the device
        logger.debug(f"Looking up module bay '{module_bay_name}' in device {device_obj['name']}")
        module_bays = client.dcim.module_bays.filter(device_id=device_id, name=module_bay_name)
        if not module_bays:
            return {
                "success": False,
                "error": f"Module bay '{module_bay_name}' not found in device '{device_obj['name']}'",
                "error_type": "NotFoundError"
            }
        
        module_bay_obj = module_bays[0]
        module_bay_id = module_bay_obj["id"]
        logger.debug(f"Found module bay: {module_bay_obj['name']} (ID: {module_bay_id})")
        
        # Step 3: Check if bay is already occupied
        if module_bay_obj.get("installed_module"):
            existing_module = module_bay_obj["installed_module"]
            return {
                "success": False,
                "error": f"Module bay '{module_bay_name}' is already occupied by module ID {existing_module}",
                "error_type": "ConflictError"
            }
        
        # Step 4: Resolve module type
        logger.debug(f"Looking up module type: {module_type_model}")
        module_types = client.dcim.module_types.filter(model=module_type_model)
        if not module_types:
            return {
                "success": False,
                "error": f"Module type '{module_type_model}' not found. Check available module types in NetBox.",
                "error_type": "NotFoundError"
            }
        
        module_type_obj = module_types[0]
        module_type_id = module_type_obj["id"]
        logger.debug(f"Found module type: {module_type_obj['model']} (ID: {module_type_id})")
        
        # Step 5: Prepare module data
        module_data = {
            "device": device_id,
            "module_bay": module_bay_id,
            "module_type": module_type_id
        }
        
        # Add optional fields if provided
        if serial_number:
            module_data["serial"] = serial_number
        if asset_tag:
            module_data["asset_tag"] = asset_tag
        if description:
            module_data["description"] = description
        
        logger.debug(f"Module data prepared: {list(module_data.keys())}")
        
        # Step 6: Create and install the module
        logger.info(f"Creating module: {module_type_model}")
        created_module = client.dcim.modules.create(confirm=True, **module_data)
        module_id = created_module["id"]
        
        logger.info(f"✅ Module installed: {module_type_model} (ID: {module_id}) in bay {module_bay_name}")
        
        # Step 7: Apply cache invalidation pattern
        logger.debug("Invalidating cache after module installation...")
        try:
            client.cache.invalidate_pattern("dcim.modules")
            client.cache.invalidate_pattern("dcim.module_bays")
            client.cache.invalidate_for_object("dcim.devices", device_id)
        except Exception as cache_error:
            logger.warning(f"Cache invalidation failed after module installation: {cache_error}")
        
        # Step 8: Build comprehensive response
        result = {
            "success": True,
            "action": "installed",
            "module": {
                "id": module_id,
                "model": module_type_obj["model"],
                "manufacturer": module_type_obj.get("manufacturer", {}).get("name", ""),
                "serial": created_module.get("serial", ""),
                "asset_tag": created_module.get("asset_tag", ""),
                "description": created_module.get("description", ""),
                "url": created_module.get("url", ""),
                "display_url": created_module.get("display_url", "")
            },
            "device": {
                "id": device_id,
                "name": device_obj["name"],
                "device_type": device_obj.get("device_type", {}).get("model", ""),
                "url": device_obj.get("url", "")
            },
            "module_bay": {
                "id": module_bay_id,
                "name": module_bay_obj["name"],
                "position": module_bay_obj.get("position", ""),
                "label": module_bay_obj.get("label", "")
            },
            "installation_details": {
                "device_name": device_obj["name"],
                "bay_name": module_bay_obj["name"],
                "module_type": module_type_obj["model"],
                "manufacturer": module_type_obj.get("manufacturer", {}).get("name", ""),
                "installed_date": created_module.get("created", "")
            },
            "dry_run": False
        }
        
        logger.info(f"✅ Module installation complete: '{module_type_obj['model']}' installed in '{device_obj['name']}:{module_bay_obj['name']}'")
        return result
        
    except Exception as e:
        logger.error(f"Failed to install module in device {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_add_power_port_to_device(
    client: NetBoxClient,
    device_name: str,
    port_name: str,
    port_type: str,
    maximum_draw: Optional[int] = None,
    allocated_draw: Optional[int] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a power port to a device for comprehensive power infrastructure documentation.
    
    This enterprise-grade power management tool ensures complete and accurate documentation
    of power connections, essential for datacenter power planning, capacity management,
    and electrical safety compliance.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the target device
        port_name: Name of the power port (e.g., "PSU-1", "Power Supply 2")
        port_type: Type of power connector (e.g., "iec-60320-c14", "nema-5-15p")
        maximum_draw: Maximum power draw in watts (optional)
        allocated_draw: Allocated power draw in watts (optional)
        description: Description of the power port (optional)
        confirm: Safety confirmation (default: False)
        
    Returns:
        Power port creation result with device and power details
        
    Examples:
        # Add primary power supply to server
        netbox_add_power_port_to_device(
            device_name="db-server-01",
            port_name="PSU-1",
            port_type="iec-60320-c14",
            maximum_draw=800,
            allocated_draw=400,
            description="Primary power supply",
            confirm=True
        )
        
        # Add secondary PSU for redundancy
        netbox_add_power_port_to_device(
            device_name="core-firewall-01",
            port_name="PSU-2",
            port_type="iec-60320-c14",
            maximum_draw=300,
            description="Secondary PSU for redundancy",
            confirm=True
        )
        
        # Add DC power input for telecom equipment
        netbox_add_power_port_to_device(
            device_name="wan-router-01",
            port_name="DC-Input",
            port_type="dc-terminal",
            maximum_draw=150,
            description="-48V DC power input",
            confirm=True
        )
    """
    try:
        if not confirm:
            return {
                "success": False,
                "error": "Power port creation requires confirm=True for safety",
                "error_type": "ValidationError"
            }
        
        if not all([device_name, port_name, port_type]):
            return {
                "success": False,
                "error": "device_name, port_name, and port_type are required",
                "error_type": "ValidationError"
            }
        
        # Validate power port type
        valid_port_types = [
            "iec-60320-c5", "iec-60320-c7", "iec-60320-c13", "iec-60320-c14", "iec-60320-c15", "iec-60320-c19", "iec-60320-c20", "iec-60320-c21",
            "iec-60309-p-n-e-4h", "iec-60309-p-n-e-6h", "iec-60309-p-n-e-9h", "iec-60309-2p-e-4h", "iec-60309-2p-e-6h", "iec-60309-2p-e-9h",
            "iec-60309-3p-e-4h", "iec-60309-3p-e-6h", "iec-60309-3p-e-9h", "iec-60309-3p-n-e-4h", "iec-60309-3p-n-e-6h", "iec-60309-3p-n-e-9h",
            "nema-1-15p", "nema-5-15p", "nema-5-20p", "nema-5-30p", "nema-5-50p", "nema-6-15p", "nema-6-20p", "nema-6-30p", "nema-6-50p",
            "nema-10-30p", "nema-10-50p", "nema-14-20p", "nema-14-30p", "nema-14-50p", "nema-14-60p", "nema-15-15p", "nema-15-20p", "nema-15-30p",
            "nema-15-50p", "nema-15-60p", "nema-l1-15p", "nema-l5-15p", "nema-l5-20p", "nema-l5-30p", "nema-l5-50p", "nema-l6-15p", "nema-l6-20p",
            "nema-l6-30p", "nema-l6-50p", "nema-l10-30p", "nema-l14-20p", "nema-l14-30p", "nema-l15-20p", "nema-l15-30p", "nema-l21-20p", "nema-l21-30p",
            "cs6361c", "cs6365c", "cs8165c", "cs8265c", "cs8365c", "cs8465c", "ita-e", "ita-f", "ita-ef", "ita-g", "ita-h", "ita-i", "ita-j", "ita-k", "ita-l", "ita-m", "ita-n", "ita-o",
            "usb-a", "usb-b", "usb-c", "usb-mini-a", "usb-mini-b", "usb-micro-a", "usb-micro-b", "usb-micro-ab", "usb-3-b", "usb-3-micro-b",
            "dc-terminal", "saf-d-grid", "neutrik-powercon-20a", "neutrik-powercon-32a", "neutrik-powercon-true1", "neutrik-powercon-true1-top",
            "ubiquiti-smartpower", "hardwired", "other"
        ]
        
        if port_type not in valid_port_types:
            return {
                "success": False,
                "error": f"Invalid port_type. Must be one of: {valid_port_types[:10]}... (see NetBox documentation for complete list)",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Adding power port '{port_name}' to device '{device_name}' (type: {port_type})")
        
        # Step 1: Resolve target device
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
        
        # Step 2: Check for existing power port with same name
        logger.debug(f"Checking for existing power port '{port_name}' on device {device_obj['name']}")
        existing_ports = client.dcim.power_ports.filter(device_id=device_id, name=port_name)
        if existing_ports:
            return {
                "success": False,
                "error": f"Power port '{port_name}' already exists on device '{device_obj['name']}'",
                "error_type": "ConflictError"
            }
        
        # Step 3: Prepare power port data
        power_port_data = {
            "device": device_id,
            "name": port_name,
            "type": port_type
        }
        
        # Add optional fields if provided
        if maximum_draw is not None:
            power_port_data["maximum_draw"] = maximum_draw
        if allocated_draw is not None:
            power_port_data["allocated_draw"] = allocated_draw
        if description:
            power_port_data["description"] = description
        
        logger.debug(f"Power port data prepared: {list(power_port_data.keys())}")
        
        # Step 4: Create the power port
        logger.info(f"Creating power port: {port_name}")
        created_port = client.dcim.power_ports.create(confirm=True, **power_port_data)
        port_id = created_port["id"]
        
        logger.info(f"✅ Power port created: {port_name} (ID: {port_id}) on device {device_obj['name']}")
        
        # Step 5: Apply cache invalidation pattern
        logger.debug("Invalidating cache after power port creation...")
        try:
            client.cache.invalidate_pattern("dcim.power_ports")
            client.cache.invalidate_for_object("dcim.devices", device_id)
        except Exception as cache_error:
            logger.warning(f"Cache invalidation failed after power port creation: {cache_error}")
        
        # Step 6: Build comprehensive response
        result = {
            "success": True,
            "action": "created",
            "power_port": {
                "id": port_id,
                "name": created_port["name"],
                "type": created_port["type"],
                "maximum_draw": created_port.get("maximum_draw", 0),
                "allocated_draw": created_port.get("allocated_draw", 0),
                "description": created_port.get("description", ""),
                "url": created_port.get("url", ""),
                "display_url": created_port.get("display_url", "")
            },
            "device": {
                "id": device_id,
                "name": device_obj["name"],
                "device_type": device_obj.get("device_type", {}).get("model", ""),
                "url": device_obj.get("url", "")
            },
            "power_details": {
                "device_name": device_obj["name"],
                "port_name": port_name,
                "port_type": port_type,
                "power_capacity": {
                    "maximum_watts": maximum_draw or 0,
                    "allocated_watts": allocated_draw or 0,
                    "available_watts": (maximum_draw - allocated_draw) if (maximum_draw and allocated_draw) else 0
                },
                "created_date": created_port.get("created", "")
            },
            "dry_run": False
        }
        
        logger.info(f"✅ Power port documentation complete: '{port_name}' ({port_type}) added to '{device_obj['name']}'")
        return result
        
    except Exception as e:
        logger.error(f"Failed to add power port to device {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }