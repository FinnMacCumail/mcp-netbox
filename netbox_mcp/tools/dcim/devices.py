#\!/usr/bin/env python3
"""
DCIM Device Lifecycle Management Tools

High-level tools for managing NetBox devices with comprehensive lifecycle management,
including creation, provisioning, decommissioning, and enterprise-grade functionality.
"""

from typing import Dict, List, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


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
def netbox_decommission_device(
    client: NetBoxClient,
    device_name: str,
    decommission_strategy: str = "offline",
    handle_ips: str = "unassign",
    handle_cables: str = "remove",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Safely decommission a device with comprehensive validation and cleanup.
    
    This enterprise-grade decommissioning tool handles the complex workflow of removing
    devices from production while maintaining data integrity and preventing accidental
    deletion of devices with active connections.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device to decommission
        decommission_strategy: Strategy for device status ("offline", "decommissioning", "inventory")
        handle_ips: IP address handling ("unassign", "deprecate", "keep")
        handle_cables: Cable handling ("remove", "deprecate", "keep")
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Comprehensive decommissioning report with all actions performed
        
    Example:
        netbox_decommission_device(
            device_name="old-server-01",
            decommission_strategy="offline",
            handle_ips="deprecate",
            handle_cables="remove",
            confirm=True
        )
    """
    try:
        if not device_name:
            return {
                "success": False,
                "error": "device_name is required",
                "error_type": "ValidationError"
            }
        
        # Validate strategy parameters
        valid_strategies = ["offline", "decommissioning", "inventory", "failed"]
        valid_ip_handling = ["unassign", "deprecate", "keep"]
        valid_cable_handling = ["remove", "deprecate", "keep"]
        
        if decommission_strategy not in valid_strategies:
            return {
                "success": False,
                "error": f"Invalid decommission_strategy. Must be one of: {valid_strategies}",
                "error_type": "ValidationError"
            }
        
        if handle_ips not in valid_ip_handling:
            return {
                "success": False,
                "error": f"Invalid handle_ips. Must be one of: {valid_ip_handling}",
                "error_type": "ValidationError"
            }
        
        if handle_cables not in valid_cable_handling:
            return {
                "success": False,
                "error": f"Invalid handle_cables. Must be one of: {valid_cable_handling}",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Decommissioning device: {device_name} (strategy: {decommission_strategy})")
        
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
        current_status = device.get("status", "unknown")
        logger.debug(f"Found device: {device['name']} (ID: {device_id}, Current Status: {current_status})")
        
        # Step 2: Pre-flight validation and dependency checks
        logger.debug("Performing pre-flight validation...")
        validation_results = {}
        
        # Check for critical dependencies (cluster membership, etc.)
        if device.get("cluster"):
            validation_results["cluster_warning"] = f"Device is member of cluster: {device['cluster'].get('name', 'Unknown')}"
        
        if device.get("virtual_chassis"):
            validation_results["virtual_chassis_warning"] = f"Device is part of virtual chassis: {device['virtual_chassis']}"
        
        # Step 3: Inventory current connections and assignments
        logger.debug("Inventorying current device connections...")
        
        # Get all interfaces
        interfaces = client.dcim.interfaces.filter(device_id=device_id)
        interface_count = len(interfaces)
        
        # Get all IP addresses assigned to this device's interfaces
        device_ips = []
        for interface in interfaces:
            assigned_ips = client.ipam.ip_addresses.filter(assigned_object_id=interface["id"])
            interface_ips = [ip for ip in assigned_ips if ip.get("assigned_object_type") == "dcim.interface"]
            device_ips.extend(interface_ips)
        
        # Get all cables connected to this device
        device_cables = []
        for interface in interfaces:
            if interface.get("cable"):
                try:
                    cables = client.dcim.cables.filter(id=interface["cable"])
                    device_cables.extend(cables)
                except Exception as e:
                    logger.warning(f"Could not retrieve cable {interface['cable']}: {e}")
        
        # Remove duplicate cables
        unique_cables = {cable["id"]: cable for cable in device_cables}.values()
        device_cables = list(unique_cables)
        
        logger.debug(f"Device inventory: {len(device_ips)} IP addresses, {len(device_cables)} cables, {interface_count} interfaces")
        
        # Step 4: Risk assessment
        risk_factors = []
        if current_status in ["active", "planned"]:
            risk_factors.append("Device is currently in active/planned status")
        if device_ips:
            risk_factors.append(f"{len(device_ips)} IP addresses currently assigned")
        if device_cables:
            risk_factors.append(f"{len(device_cables)} cables currently connected")
        if device.get("primary_ip4") or device.get("primary_ip6"):
            risk_factors.append("Device has primary IP addresses configured")
        
        # Generate decommissioning plan
        decommission_plan = {
            "device_status_change": {
                "from": current_status,
                "to": decommission_strategy,
                "action": "Update device status"
            },
            "ip_addresses": {
                "count": len(device_ips),
                "action": handle_ips,
                "details": [{"address": ip["address"], "interface": ip.get("assigned_object_id")} for ip in device_ips]
            },
            "cables": {
                "count": len(device_cables),
                "action": handle_cables,
                "details": [{"cable_id": cable["id"], "label": cable.get("label", "Unlabeled")} for cable in device_cables]
            },
            "interfaces": {
                "count": interface_count,
                "action": "Keep (status will reflect device decommissioning)"
            }
        }
        
        if not confirm:
            # Dry run mode - return the plan without executing
            logger.info(f"DRY RUN: Would decommission device {device_name}")
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "device_decommission",
                "device": {
                    "name": device["name"],
                    "id": device_id,
                    "current_status": current_status,
                    "dry_run": True
                },
                "decommission_plan": decommission_plan,
                "risk_assessment": {
                    "risk_level": "high" if len(risk_factors) > 2 else "medium" if risk_factors else "low",
                    "risk_factors": risk_factors
                },
                "validation_results": validation_results,
                "dry_run": True
            }
        
        # Step 5: Execute decommissioning plan
        execution_results = {}
        
        # 5a: Handle IP addresses
        if device_ips and handle_ips != "keep":
            logger.info(f"Processing {len(device_ips)} IP addresses...")
            ip_results = []
            
            for ip in device_ips:
                try:
                    if handle_ips == "unassign":
                        # Unassign the IP from the interface
                        update_data = {
                            "assigned_object_type": None,
                            "assigned_object_id": None
                        }
                        result = client.ipam.ip_addresses.update(ip["id"], confirm=True, **update_data)
                        ip_results.append({
                            "ip": ip["address"],
                            "action": "unassigned",
                            "status": "success"
                        })
                    elif handle_ips == "deprecate":
                        # Change IP status to deprecated
                        update_data = {"status": "deprecated"}
                        result = client.ipam.ip_addresses.update(ip["id"], confirm=True, **update_data)
                        ip_results.append({
                            "ip": ip["address"],
                            "action": "deprecated",
                            "status": "success"
                        })
                except Exception as e:
                    logger.error(f"Failed to process IP {ip['address']}: {e}")
                    ip_results.append({
                        "ip": ip["address"],
                        "action": f"failed: {e}",
                        "status": "error"
                    })
            
            execution_results["ip_processing"] = {
                "total": len(device_ips),
                "successful": len([r for r in ip_results if r["status"] == "success"]),
                "failed": len([r for r in ip_results if r["status"] == "error"]),
                "details": ip_results
            }
        
        # 5b: Handle cables
        if device_cables and handle_cables != "keep":
            logger.info(f"Processing {len(device_cables)} cables...")
            cable_results = []
            
            for cable in device_cables:
                try:
                    if handle_cables == "remove":
                        # Delete the cable
                        client.dcim.cables.delete(cable["id"], confirm=True)
                        cable_results.append({
                            "cable_id": cable["id"],
                            "label": cable.get("label", "Unlabeled"),
                            "action": "removed",
                            "status": "success"
                        })
                    elif handle_cables == "deprecate":
                        # Update cable status to deprecated (if status field exists)
                        try:
                            update_data = {"status": "deprecated"}
                            result = client.dcim.cables.update(cable["id"], confirm=True, **update_data)
                            cable_results.append({
                                "cable_id": cable["id"],
                                "label": cable.get("label", "Unlabeled"),
                                "action": "deprecated",
                                "status": "success"
                            })
                        except Exception as e:
                            # If deprecation fails, try removal
                            client.dcim.cables.delete(cable["id"], confirm=True)
                            cable_results.append({
                                "cable_id": cable["id"],
                                "label": cable.get("label", "Unlabeled"),
                                "action": "removed (deprecation not supported)",
                                "status": "success"
                            })
                except Exception as e:
                    logger.error(f"Failed to process cable {cable['id']}: {e}")
                    cable_results.append({
                        "cable_id": cable["id"],
                        "label": cable.get("label", "Unlabeled"),
                        "action": f"failed: {e}",
                        "status": "error"
                    })
            
            execution_results["cable_processing"] = {
                "total": len(device_cables),
                "successful": len([r for r in cable_results if r["status"] == "success"]),
                "failed": len([r for r in cable_results if r["status"] == "error"]),
                "details": cable_results
            }
        
        # 5c: Update device status
        logger.info(f"Updating device status to: {decommission_strategy}")
        try:
            device_update_data = {"status": decommission_strategy}
            updated_device = client.dcim.devices.update(device_id, confirm=True, **device_update_data)
            execution_results["device_status"] = {
                "action": "updated",
                "from": current_status,
                "to": decommission_strategy,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Failed to update device status: {e}")
            execution_results["device_status"] = {
                "action": "failed",
                "error": str(e),
                "status": "error"
            }
        
        # Step 6: Generate completion summary
        total_actions = 1  # Device status update
        successful_actions = 1 if execution_results.get("device_status", {}).get("status") == "success" else 0
        
        if "ip_processing" in execution_results:
            total_actions += execution_results["ip_processing"]["total"]
            successful_actions += execution_results["ip_processing"]["successful"]
        
        if "cable_processing" in execution_results:
            total_actions += execution_results["cable_processing"]["total"]
            successful_actions += execution_results["cable_processing"]["successful"]
        
        overall_success = successful_actions == total_actions
        
        return {
            "success": overall_success,
            "action": "decommissioned",
            "object_type": "device",
            "device": {
                "name": device["name"],
                "id": device_id,
                "status_changed": execution_results.get("device_status", {}).get("status") == "success",
                "new_status": decommission_strategy if execution_results.get("device_status", {}).get("status") == "success" else current_status
            },
            "execution_summary": {
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "failed_actions": total_actions - successful_actions,
                "success_rate": f"{(successful_actions/total_actions*100):.1f}%" if total_actions > 0 else "0%"
            },
            "execution_results": execution_results,
            "decommission_strategy": decommission_strategy,
            "cleanup_performed": {
                "ips": handle_ips if device_ips else "none",
                "cables": handle_cables if device_cables else "none"
            },
            "dry_run": False
        }
        
    except Exception as e:
        logger.error(f"Failed to decommission device {device_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }



# TODO: Implement advanced device lifecycle management tools:
# - netbox_configure_device_settings
# - netbox_monitor_device_health
# - netbox_bulk_device_operations  
# - netbox_map_device_dependencies
# - netbox_clone_device_configuration
# - netbox_device_compliance_check
