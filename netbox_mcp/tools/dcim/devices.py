#\!/usr/bin/env python3
"""
DCIM Device Lifecycle Management Tools

High-level tools for managing NetBox devices with comprehensive lifecycle management,
including creation, provisioning, decommissioning, and enterprise-grade functionality.
"""

from typing import Dict, Optional, Any
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
                        except Exception:
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



@mcp_tool(category="dcim")
def netbox_list_all_devices(
    client: NetBoxClient,
    limit: int = 100,
    site_name: Optional[str] = None,
    role_name: Optional[str] = None,
    tenant_name: Optional[str] = None,
    status: Optional[str] = None,
    manufacturer_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a summarized list of all devices in NetBox.

    This function is the correct choice for open, exploratory questions like
    "what devices are there?" or "show all servers in datacenter-1". Use 
    'netbox_get_device' for detailed information about one specific device.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        limit: Maximum number of results to return (default: 100)
        site_name: Filter by site name (optional)
        role_name: Filter by device role name (optional)
        tenant_name: Filter by tenant name (optional)
        status: Filter by device status (active, offline, planned, etc.)
        manufacturer_name: Filter by manufacturer name (optional)
        
    Returns:
        Dictionary containing:
        - count: Total number of devices found
        - devices: List of summarized device information
        - filters_applied: Dictionary of filters that were applied
        - summary_stats: Aggregate statistics about the devices
        
    Example:
        netbox_list_all_devices(site_name="datacenter-1", role_name="switch")
        netbox_list_all_devices(status="active", manufacturer_name="Cisco")
        netbox_list_all_devices(tenant_name="customer-a", limit=50)
    """
    try:
        logger.info(f"Listing devices with filters - site: {site_name}, role: {role_name}, tenant: {tenant_name}, status: {status}, manufacturer: {manufacturer_name}")
        
        # Build filters dictionary - only include non-None values
        filters = {}
        if site_name:
            filters['site'] = site_name
        if role_name:
            filters['role'] = role_name
        if tenant_name:
            filters['tenant'] = tenant_name
        if status:
            filters['status'] = status
        if manufacturer_name:
            # For manufacturer filtering, we need to filter by device_type__manufacturer
            filters['device_type__manufacturer'] = manufacturer_name
        
        # Execute filtered query with limit
        devices = list(client.dcim.devices.filter(**filters))
        
        # Apply limit after fetching (since pynetbox limit behavior can be inconsistent)
        if len(devices) > limit:
            devices = devices[:limit]
        
        # Generate summary statistics
        status_counts = {}
        role_counts = {}
        site_counts = {}
        manufacturer_counts = {}
        
        for device in devices:
            # Status breakdown with defensive checks for dictionary access
            status_obj = device.get("status", {})
            if isinstance(status_obj, dict):
                status = status_obj.get("label", "N/A")
            else:
                status = str(status_obj) if status_obj else "N/A"
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Role breakdown with defensive checks for dictionary access
            role_obj = device.get("role")
            if role_obj:
                if isinstance(role_obj, dict):
                    role_name = role_obj.get("name", str(role_obj))
                else:
                    role_name = str(role_obj)
                role_counts[role_name] = role_counts.get(role_name, 0) + 1
            
            # Site breakdown with defensive checks for dictionary access
            site_obj = device.get("site")
            if site_obj:
                if isinstance(site_obj, dict):
                    site_name = site_obj.get("name", str(site_obj))
                else:
                    site_name = str(site_obj)
                site_counts[site_name] = site_counts.get(site_name, 0) + 1
            
            # Manufacturer breakdown with defensive checks for dictionary access
            device_type_obj = device.get("device_type")
            if device_type_obj and isinstance(device_type_obj, dict):
                manufacturer_obj = device_type_obj.get("manufacturer")
                if manufacturer_obj:
                    if isinstance(manufacturer_obj, dict):
                        mfg_name = manufacturer_obj.get("name", str(manufacturer_obj))
                    else:
                        mfg_name = str(manufacturer_obj)
                    manufacturer_counts[mfg_name] = manufacturer_counts.get(mfg_name, 0) + 1
        
        # Create human-readable device list
        device_list = []
        for device in devices:
            # DEFENSIVE CHECK: Handle dictionary access for all device attributes
            status_obj = device.get("status", {})
            if isinstance(status_obj, dict):
                status = status_obj.get("label", "N/A")
            else:
                status = str(status_obj) if status_obj else "N/A"
            
            site_obj = device.get("site")
            site_name = None
            if site_obj and isinstance(site_obj, dict):
                site_name = site_obj.get("name")
            elif site_obj:
                site_name = str(site_obj)
            
            role_obj = device.get("role")
            role_name = None
            if role_obj and isinstance(role_obj, dict):
                role_name = role_obj.get("name")
            elif role_obj:
                role_name = str(role_obj)
            
            device_type_obj = device.get("device_type")
            device_type_model = None
            manufacturer_name = None
            if device_type_obj and isinstance(device_type_obj, dict):
                device_type_model = device_type_obj.get("model")
                manufacturer_obj = device_type_obj.get("manufacturer")
                if manufacturer_obj and isinstance(manufacturer_obj, dict):
                    manufacturer_name = manufacturer_obj.get("name")
                elif manufacturer_obj:
                    manufacturer_name = str(manufacturer_obj)
            
            # Handle IP addresses
            primary_ip4_obj = device.get("primary_ip4")
            primary_ip6_obj = device.get("primary_ip6")
            primary_ip = None
            if primary_ip4_obj:
                if isinstance(primary_ip4_obj, dict):
                    primary_ip = primary_ip4_obj.get("address")
                else:
                    primary_ip = str(primary_ip4_obj)
            elif primary_ip6_obj:
                if isinstance(primary_ip6_obj, dict):
                    primary_ip = primary_ip6_obj.get("address")
                else:
                    primary_ip = str(primary_ip6_obj)
            
            rack_obj = device.get("rack")
            rack_name = None
            if rack_obj and isinstance(rack_obj, dict):
                rack_name = rack_obj.get("name")
            elif rack_obj:
                rack_name = str(rack_obj)
            
            tenant_obj = device.get("tenant")
            tenant_name = None
            if tenant_obj and isinstance(tenant_obj, dict):
                tenant_name = tenant_obj.get("name")
            elif tenant_obj:
                tenant_name = str(tenant_obj)
            
            device_info = {
                "name": device.get("name", "Unknown"),
                "status": status,
                "site": site_name,
                "role": role_name,
                "device_type": device_type_model,
                "manufacturer": manufacturer_name,
                "primary_ip": primary_ip,
                "rack": rack_name,
                "position": device.get("position"),
                "tenant": tenant_name
            }
            device_list.append(device_info)
        
        result = {
            "count": len(device_list),
            "devices": device_list,
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
            "summary_stats": {
                "total_devices": len(device_list),
                "status_breakdown": status_counts,
                "role_breakdown": role_counts,
                "site_breakdown": site_counts,
                "manufacturer_breakdown": manufacturer_counts,
                "devices_with_ip": len([d for d in device_list if d['primary_ip']]),
                "devices_in_racks": len([d for d in device_list if d['rack']])
            }
        }
        
        logger.info(f"Found {len(device_list)} devices matching criteria. Status breakdown: {status_counts}")
        return result
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        return {
            "count": 0,
            "devices": [],
            "error": str(e),
            "error_type": type(e).__name__,
            "filters_applied": {k: v for k, v in {
                'site_name': site_name,
                'role_name': role_name, 
                'tenant_name': tenant_name,
                'status': status,
                'manufacturer_name': manufacturer_name
            }.items() if v is not None}
        }


@mcp_tool(category="dcim")
def netbox_update_device(
    client: NetBoxClient,
    device_id: int,
    name: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    site: Optional[str] = None,
    rack: Optional[str] = None,
    position: Optional[int] = None,
    face: Optional[str] = None,
    device_type: Optional[str] = None,
    platform: Optional[str] = None,
    tenant: Optional[str] = None,
    serial: Optional[str] = None,
    asset_tag: Optional[str] = None,
    description: Optional[str] = None,
    comments: Optional[str] = None,
    oob_ip: Optional[str] = None,
    primary_ip4: Optional[str] = None,
    primary_ip6: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Update an existing device in NetBox DCIM.
    
    This function enables comprehensive device property updates with enterprise-grade
    safety mechanisms and intelligent foreign key resolution for relationship fields.
    
    Args:
        client: NetBoxClient instance (injected)
        device_id: Device ID to update
        name: Device name (hostname)
        status: Device status (active, planned, staged, failed, inventory, decommissioning, offline)
        role: Device role name or slug
        site: Site name or slug  
        rack: Rack name (will be resolved within the device's site)
        position: Rack position (bottom U)
        face: Rack face (front, rear)
        device_type: Device type model or slug
        platform: Platform name or slug
        tenant: Tenant name or slug
        serial: Serial number
        asset_tag: Asset tag
        description: Device description
        comments: Device comments
        oob_ip: Out-of-band management IP (e.g., BMC/iDRAC IP with CIDR notation)
        primary_ip4: Primary IPv4 address (must be assigned to device interface)
        primary_ip6: Primary IPv6 address (must be assigned to device interface)
        confirm: Must be True to execute (safety mechanism)
    
    Returns:
        Dict containing the updated device data and operation status
        
    Examples:
        # Update device status and description
        result = netbox_update_device(
            device_id=123,
            status="planned",
            description="Updated via NetBox MCP",
            confirm=True
        )
        
        # Move device to different rack
        result = netbox_update_device(
            device_id=456,
            rack="R01-A23",
            position=42,
            face="front",
            confirm=True
        )
        
        # Change device role and platform
        result = netbox_update_device(
            device_id=789,
            role="server",
            platform="Linux",
            confirm=True
        )
        
        # Set device OOB IP for BMC/iDRAC management
        result = netbox_update_device(
            device_id=456,
            oob_ip="192.168.100.10/24",
            description="Server with iDRAC configured",
            confirm=True
        )
        
        # Set primary IP addresses for device
        result = netbox_update_device(
            device_id=62,
            primary_ip4="82.94.240.130/24",
            primary_ip6="2001:888:2000:1450::82:94:240:130/64",
            confirm=True
        )
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        update_fields = {}
        if name: update_fields["name"] = name
        if status: update_fields["status"] = status
        if role: update_fields["role"] = role
        if site: update_fields["site"] = site
        if rack: update_fields["rack"] = rack
        if position is not None: update_fields["position"] = position
        if face: update_fields["face"] = face
        if device_type: update_fields["device_type"] = device_type
        if platform: update_fields["platform"] = platform
        if tenant: update_fields["tenant"] = tenant
        if serial: update_fields["serial"] = serial
        if asset_tag: update_fields["asset_tag"] = asset_tag
        if description is not None: update_fields["description"] = description
        if comments is not None: update_fields["comments"] = comments
        if oob_ip: update_fields["oob_ip"] = oob_ip
        if primary_ip4: update_fields["primary_ip4"] = primary_ip4
        if primary_ip6: update_fields["primary_ip6"] = primary_ip6
        
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: Device would be updated. Set confirm=True to execute.",
            "would_update": {
                "device_id": device_id,
                "fields": update_fields
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not device_id or device_id <= 0:
        raise ValueError("device_id must be a positive integer")
    
    # Check that at least one field is provided for update
    update_fields = [name, status, role, site, rack, position, face, device_type, platform, 
                    tenant, serial, asset_tag, description, comments, oob_ip, primary_ip4, primary_ip6]
    if not any(field is not None for field in update_fields):
        raise ValueError("At least one field must be provided for update")
    
    # STEP 3: VERIFY DEVICE EXISTS
    try:
        existing_device = client.dcim.devices.get(device_id)
        if not existing_device:
            raise ValueError(f"Device with ID {device_id} not found")
        
        # Apply defensive dict/object handling
        device_name = existing_device.get('name') if isinstance(existing_device, dict) else existing_device.name
        device_site = existing_device.get('site') if isinstance(existing_device, dict) else existing_device.site
        
        # Extract site ID for rack resolution
        if isinstance(device_site, dict):
            current_site_id = device_site.get('id')
            current_site_name = device_site.get('name', 'Unknown')
        else:
            current_site_id = getattr(device_site, 'id', None)
            current_site_name = getattr(device_site, 'name', 'Unknown')
            
    except Exception as e:
        raise ValueError(f"Could not retrieve device {device_id}: {e}")
    
    # STEP 4: BUILD UPDATE PAYLOAD WITH FOREIGN KEY RESOLUTION
    update_payload = {}
    
    # Basic string fields
    if name is not None:
        if name and not name.strip():
            raise ValueError("name cannot be empty")
        update_payload["name"] = name
    
    if status:
        valid_statuses = ["active", "planned", "staged", "failed", "inventory", "decommissioning", "offline"]
        if status not in valid_statuses:
            raise ValueError(f"status must be one of: {', '.join(valid_statuses)}")
        update_payload["status"] = status
    
    if serial is not None:
        update_payload["serial"] = serial
        
    if asset_tag is not None:
        update_payload["asset_tag"] = asset_tag
        
    if description is not None:
        update_payload["description"] = f"[NetBox-MCP] {description}" if description else ""
        
    if comments is not None:
        update_payload["comments"] = f"[NetBox-MCP] {comments}" if comments else ""
    
    if face:
        if face not in ["front", "rear"]:
            raise ValueError("face must be 'front' or 'rear'")
        update_payload["face"] = face
    
    if position is not None:
        if position < 1:
            raise ValueError("position must be 1 or greater")
        update_payload["position"] = position
    
    # Foreign key resolution for relationship fields
    if role:
        try:
            roles = client.dcim.device_roles.filter(name=role)
            if not roles:
                roles = client.dcim.device_roles.filter(slug=role)
            if not roles:
                raise ValueError(f"Device role '{role}' not found")
            role_obj = roles[0]
            role_id = role_obj.get('id') if isinstance(role_obj, dict) else role_obj.id
            update_payload["role"] = role_id
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not find device role '{role}': {e}")
    
    if site:
        try:
            sites = client.dcim.sites.filter(name=site)
            if not sites:
                sites = client.dcim.sites.filter(slug=site)
            if not sites:
                raise ValueError(f"Site '{site}' not found")
            site_obj = sites[0]
            site_id = site_obj.get('id') if isinstance(site_obj, dict) else site_obj.id
            update_payload["site"] = site_id
            # Update current_site_id for rack resolution
            current_site_id = site_id
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not find site '{site}': {e}")
    
    if device_type:
        try:
            device_types = client.dcim.device_types.filter(model=device_type)
            if not device_types:
                device_types = client.dcim.device_types.filter(slug=device_type)
            if not device_types:
                raise ValueError(f"Device type '{device_type}' not found")
            dt_obj = device_types[0]
            dt_id = dt_obj.get('id') if isinstance(dt_obj, dict) else dt_obj.id
            update_payload["device_type"] = dt_id
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not find device type '{device_type}': {e}")
    
    if platform:
        try:
            platforms = client.dcim.platforms.filter(name=platform)
            if not platforms:
                platforms = client.dcim.platforms.filter(slug=platform)
            if not platforms:
                raise ValueError(f"Platform '{platform}' not found")
            platform_obj = platforms[0]
            platform_id = platform_obj.get('id') if isinstance(platform_obj, dict) else platform_obj.id
            update_payload["platform"] = platform_id
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not find platform '{platform}': {e}")
    
    if tenant:
        try:
            tenants = client.tenancy.tenants.filter(name=tenant)
            if not tenants:
                tenants = client.tenancy.tenants.filter(slug=tenant)
            if not tenants:
                raise ValueError(f"Tenant '{tenant}' not found")
            tenant_obj = tenants[0]
            tenant_id = tenant_obj.get('id') if isinstance(tenant_obj, dict) else tenant_obj.id
            update_payload["tenant"] = tenant_id
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not find tenant '{tenant}': {e}")
    
    if rack:
        try:
            # Rack resolution requires site context
            if not current_site_id:
                raise ValueError("Cannot resolve rack without a valid site context")
            
            racks = client.dcim.racks.filter(name=rack, site_id=current_site_id)
            if not racks:
                raise ValueError(f"Rack '{rack}' not found in site '{current_site_name}'")
            rack_obj = racks[0]
            rack_id = rack_obj.get('id') if isinstance(rack_obj, dict) else rack_obj.id
            update_payload["rack"] = rack_id
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not find rack '{rack}': {e}")
    
    # OOB IP resolution for device-level management IP
    if oob_ip:
        try:
            # Validate IP address format
            import ipaddress
            try:
                ip_obj = ipaddress.ip_interface(oob_ip)
                validated_oob_ip = str(ip_obj)
            except ValueError as e:
                raise ValueError(f"Invalid OOB IP address format '{oob_ip}': {e}")
            
            # Look for existing IP address with comprehensive search
            existing_ips = client.ipam.ip_addresses.filter(address=validated_oob_ip)
            if existing_ips:
                # Use existing IP address
                ip_obj = existing_ips[0]
                oob_ip_id = ip_obj.get('id') if isinstance(ip_obj, dict) else ip_obj.id
                
                # Apply defensive dict/object handling for assigned_object_type check
                assigned_object_type = ip_obj.get('assigned_object_type') if isinstance(ip_obj, dict) else getattr(ip_obj, 'assigned_object_type', None)
                
                # Check if IP is already assigned to an interface (OOB should be device-level only)
                if assigned_object_type == 'dcim.interface':
                    logger.warning(f"OOB IP {validated_oob_ip} is currently assigned to an interface, proceeding to use for device OOB field anyway")
                
                logger.debug(f"Using existing OOB IP address: {validated_oob_ip} (ID: {oob_ip_id})")
                update_payload["oob_ip"] = oob_ip_id
            else:
                # Try alternative search without full CIDR (in case of format mismatch)
                ip_without_cidr = validated_oob_ip.split('/')[0]
                alternative_ips = client.ipam.ip_addresses.filter(address__net_contains=ip_without_cidr)
                
                if alternative_ips:
                    # Found IP with different CIDR notation
                    ip_obj = alternative_ips[0]
                    oob_ip_id = ip_obj.get('id') if isinstance(ip_obj, dict) else ip_obj.id
                    existing_address = ip_obj.get('address') if isinstance(ip_obj, dict) else getattr(ip_obj, 'address', None)
                    
                    logger.info(f"Found existing IP {existing_address} for OOB request {validated_oob_ip}, using existing IP")
                    update_payload["oob_ip"] = oob_ip_id
                else:
                    # Only create new IP if absolutely not found
                    ip_data = {
                        "address": validated_oob_ip,
                        "status": "active",
                        "description": f"[NetBox-MCP] OOB IP for device {device_name}"
                    }
                    
                    logger.debug(f"Creating new OOB IP address: {validated_oob_ip}")
                    try:
                        new_ip = client.ipam.ip_addresses.create(confirm=True, **ip_data)
                        oob_ip_id = new_ip.get('id') if isinstance(new_ip, dict) else new_ip.id
                        update_payload["oob_ip"] = oob_ip_id
                    except Exception as create_error:
                        # If creation fails due to duplicate, try one more search
                        if "Duplicate IP address" in str(create_error):
                            logger.warning(f"Duplicate IP detected during creation, retrying search for {validated_oob_ip}")
                            retry_ips = client.ipam.ip_addresses.filter(address=validated_oob_ip)
                            if retry_ips:
                                ip_obj = retry_ips[0]
                                oob_ip_id = ip_obj.get('id') if isinstance(ip_obj, dict) else ip_obj.id
                                update_payload["oob_ip"] = oob_ip_id
                                logger.info(f"Successfully found existing OOB IP on retry: {validated_oob_ip} (ID: {oob_ip_id})")
                            else:
                                raise create_error
                        else:
                            raise create_error
                
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not resolve OOB IP '{oob_ip}': {e}")
    
    # Primary IP resolution for primary_ip4 and primary_ip6
    if primary_ip4:
        try:
            # Use the same robust IP search logic as netbox_set_primary_ip
            import ipaddress
            try:
                ip_obj = ipaddress.ip_interface(primary_ip4)
                validated_primary_ip4 = str(ip_obj)
            except ValueError as e:
                raise ValueError(f"Invalid primary IPv4 address format '{primary_ip4}': {e}")
            
            # Search for existing IP with flexible search
            existing_ips = client.ipam.ip_addresses.filter(address=validated_primary_ip4)
            if not existing_ips:
                ip_base = validated_primary_ip4.split('/')[0]
                for search_ip in [f"{ip_base}/24", f"{ip_base}/32", f"{ip_base}/16"]:
                    existing_ips = client.ipam.ip_addresses.filter(address=search_ip)
                    if existing_ips:
                        validated_primary_ip4 = search_ip
                        break
            
            if not existing_ips:
                raise ValueError(f"Primary IPv4 address {primary_ip4} not found in NetBox. Ensure IP is assigned to device interface first.")
            
            ip_address_obj = existing_ips[0]
            primary_ip4_id = ip_address_obj.get('id') if isinstance(ip_address_obj, dict) else ip_address_obj.id
            
            # Verify IP is assigned to this device's interface
            assigned_object_type = ip_address_obj.get('assigned_object_type') if isinstance(ip_address_obj, dict) else getattr(ip_address_obj, 'assigned_object_type', None)
            assigned_object_id = ip_address_obj.get('assigned_object_id') if isinstance(ip_address_obj, dict) else getattr(ip_address_obj, 'assigned_object_id', None)
            
            if assigned_object_type == "dcim.interface" and assigned_object_id:
                interface = client.dcim.interfaces.get(assigned_object_id)
                interface_device_id = None
                
                if isinstance(interface, dict):
                    interface_device = interface.get('device')
                    if isinstance(interface_device, int):
                        interface_device_id = interface_device
                    elif isinstance(interface_device, dict):
                        interface_device_id = interface_device.get('id')
                else:
                    interface_device = getattr(interface, 'device', None)
                    if isinstance(interface_device, int):
                        interface_device_id = interface_device
                    else:
                        interface_device_id = getattr(interface_device, 'id', None) if interface_device else None
                
                if interface_device_id != device_id:
                    raise ValueError(f"Primary IPv4 address {validated_primary_ip4} is not assigned to device {device_name}")
            
            update_payload["primary_ip4"] = primary_ip4_id
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not resolve primary IPv4 '{primary_ip4}': {e}")
    
    if primary_ip6:
        try:
            # Same logic for IPv6
            import ipaddress
            try:
                ip_obj = ipaddress.ip_interface(primary_ip6)
                validated_primary_ip6 = str(ip_obj)
            except ValueError as e:
                raise ValueError(f"Invalid primary IPv6 address format '{primary_ip6}': {e}")
            
            # Search for existing IP
            existing_ips = client.ipam.ip_addresses.filter(address=validated_primary_ip6)
            if not existing_ips:
                ip_base = validated_primary_ip6.split('/')[0]
                for search_ip in [f"{ip_base}/64", f"{ip_base}/128", f"{ip_base}/48"]:
                    existing_ips = client.ipam.ip_addresses.filter(address=search_ip)
                    if existing_ips:
                        validated_primary_ip6 = search_ip
                        break
            
            if not existing_ips:
                raise ValueError(f"Primary IPv6 address {primary_ip6} not found in NetBox. Ensure IP is assigned to device interface first.")
            
            ip_address_obj = existing_ips[0]
            primary_ip6_id = ip_address_obj.get('id') if isinstance(ip_address_obj, dict) else ip_address_obj.id
            
            # Verify IP is assigned to this device's interface (same logic as IPv4)
            assigned_object_type = ip_address_obj.get('assigned_object_type') if isinstance(ip_address_obj, dict) else getattr(ip_address_obj, 'assigned_object_type', None)
            assigned_object_id = ip_address_obj.get('assigned_object_id') if isinstance(ip_address_obj, dict) else getattr(ip_address_obj, 'assigned_object_id', None)
            
            if assigned_object_type == "dcim.interface" and assigned_object_id:
                interface = client.dcim.interfaces.get(assigned_object_id)
                interface_device_id = None
                
                if isinstance(interface, dict):
                    interface_device = interface.get('device')
                    if isinstance(interface_device, int):
                        interface_device_id = interface_device
                    elif isinstance(interface_device, dict):
                        interface_device_id = interface_device.get('id')
                else:
                    interface_device = getattr(interface, 'device', None)
                    if isinstance(interface_device, int):
                        interface_device_id = interface_device
                    else:
                        interface_device_id = getattr(interface_device, 'id', None) if interface_device else None
                
                if interface_device_id != device_id:
                    raise ValueError(f"Primary IPv6 address {validated_primary_ip6} is not assigned to device {device_name}")
            
            update_payload["primary_ip6"] = primary_ip6_id
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not resolve primary IPv6 '{primary_ip6}': {e}")
    
    # STEP 5: CONFLICT DETECTION FOR RACK POSITION
    if rack and position is not None:
        try:
            # Check if the position is already occupied by another device
            rack_id = update_payload.get("rack")
            if rack_id:
                existing_devices = client.dcim.devices.filter(
                    rack_id=rack_id, 
                    position=position,
                    no_cache=True  # Force live check
                )
                
                for existing in existing_devices:
                    existing_id = existing.get('id') if isinstance(existing, dict) else existing.id
                    if existing_id != device_id:  # Different device occupying the position
                        existing_name = existing.get('name') if isinstance(existing, dict) else existing.name
                        raise ValueError(f"Position {position} in rack is already occupied by device '{existing_name}' (ID: {existing_id})")
                        
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Could not check rack position conflicts: {e}")
    
    # STEP 6: UPDATE DEVICE
    try:
        updated_device = client.dcim.devices.update(device_id, confirm=confirm, **update_payload)
        
        # Apply defensive dict/object handling to response
        device_id_updated = updated_device.get('id') if isinstance(updated_device, dict) else updated_device.id
        device_name_updated = updated_device.get('name') if isinstance(updated_device, dict) else updated_device.name
        device_status_updated = updated_device.get('status') if isinstance(updated_device, dict) else getattr(updated_device, 'status', None)
        
        # Handle status object/dict
        if isinstance(device_status_updated, dict):
            status_label = device_status_updated.get('label', device_status_updated.get('value', 'Unknown'))
        else:
            status_label = str(device_status_updated) if device_status_updated else 'Unknown'
        
    except Exception as e:
        raise ValueError(f"NetBox API error during device update: {e}")
    
    # STEP 7: RETURN SUCCESS
    return {
        "success": True,
        "message": f"Device ID {device_id} successfully updated.",
        "data": {
            "device_id": device_id_updated,
            "name": device_name_updated,
            "status": status_label,
            "serial": updated_device.get('serial') if isinstance(updated_device, dict) else getattr(updated_device, 'serial', None),
            "asset_tag": updated_device.get('asset_tag') if isinstance(updated_device, dict) else getattr(updated_device, 'asset_tag', None),
            "description": updated_device.get('description') if isinstance(updated_device, dict) else getattr(updated_device, 'description', None)
        }
    }


@mcp_tool(category="dcim")
def netbox_set_primary_ip(
    client: NetBoxClient,
    device_name: str,
    ip_address: str,
    ip_version: str = "auto",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Set primary IP address for a device in NetBox DCIM.
    
    This tool sets the primary IPv4 or IPv6 address for a device by updating the 
    device's primary_ip4 or primary_ip6 field. The IP address must already be 
    assigned to an interface on the device.
    
    Args:
        client: NetBoxClient instance (injected)
        device_name: Name of the device
        ip_address: IP address with CIDR notation (e.g., "10.0.1.100/24")
        ip_version: IP version selection ("auto", "ipv4", "ipv6")
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Dict containing the primary IP assignment result and device information
        
    Examples:
        # Auto-detect IP version
        netbox_set_primary_ip("server-01", "10.0.1.100/24", confirm=True)
        
        # Force IPv4 assignment
        netbox_set_primary_ip("server-01", "10.0.1.100/24", "ipv4", confirm=True)
        
        # IPv6 primary assignment
        netbox_set_primary_ip("server-01", "2001:db8::1/64", "ipv6", confirm=True)
        
        # Management IP as primary
        netbox_set_primary_ip("switch-01", "192.168.100.20/24", confirm=True)
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: Primary IP would be set. Set confirm=True to execute.",
            "would_update": {
                "device": device_name,
                "ip_address": ip_address,
                "ip_version": ip_version
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not device_name or not device_name.strip():
        raise ValueError("device_name cannot be empty")
    
    if not ip_address or not ip_address.strip():
        raise ValueError("ip_address cannot be empty")
    
    if ip_version not in ["auto", "ipv4", "ipv6"]:
        raise ValueError("ip_version must be 'auto', 'ipv4', or 'ipv6'")
    
    # STEP 3: VALIDATE IP ADDRESS FORMAT AND DETERMINE VERSION
    try:
        import ipaddress
        ip_obj = ipaddress.ip_interface(ip_address)
        validated_ip = str(ip_obj)
        
        # Determine IP version
        if ip_version == "auto":
            detected_version = "ipv4" if ip_obj.version == 4 else "ipv6"
        elif ip_version == "ipv4" and ip_obj.version != 4:
            raise ValueError(f"IP address {ip_address} is not IPv4 but ip_version is set to 'ipv4'")
        elif ip_version == "ipv6" and ip_obj.version != 6:
            raise ValueError(f"IP address {ip_address} is not IPv6 but ip_version is set to 'ipv6'")
        else:
            detected_version = ip_version
            
    except ValueError as e:
        if "cannot be empty" in str(e) or "must be" in str(e):
            raise  # Re-raise our parameter validation errors
        else:
            raise ValueError(f"Invalid IP address format '{ip_address}': {e}")
    
    # STEP 4: LOOKUP DEVICE
    try:
        devices = client.dcim.devices.filter(name=device_name)
        if not devices:
            raise ValueError(f"Device '{device_name}' not found")
        
        device = devices[0]
        device_id = device.get('id') if isinstance(device, dict) else device.id
        device_display = device.get('display', device_name) if isinstance(device, dict) else getattr(device, 'display', device_name)
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not find device '{device_name}': {e}")
    
    # STEP 5: FIND IP ADDRESS OBJECT WITH FLEXIBLE SEARCH
    try:
        existing_ips = client.ipam.ip_addresses.filter(address=validated_ip)
        
        if not existing_ips:
            # If exact match failed, try alternative search methods
            ip_base = validated_ip.split('/')[0]  # Get IP without subnet
            
            # Try searching for IP with common subnet masks
            alternative_searches = []
            if '/' not in ip_address:  # Original input had no subnet
                # Try common subnets for the IP
                alternative_searches = [f"{ip_base}/24", f"{ip_base}/32", f"{ip_base}/16"]
            else:
                # Try without subnet or with alternative subnets
                alternative_searches = [ip_base, f"{ip_base}/24", f"{ip_base}/32"]
            
            for search_ip in alternative_searches:
                existing_ips = client.ipam.ip_addresses.filter(address=search_ip)
                if existing_ips:
                    logger.info(f"Found IP address {search_ip} for search term {ip_address}")
                    validated_ip = search_ip  # Update validated_ip to match what we found
                    break
            
            if not existing_ips:
                # Final attempt: search by IP address alone (network contains search)
                try:
                    existing_ips = client.ipam.ip_addresses.filter(address__net_contains=ip_base)
                    if existing_ips:
                        found_ip = existing_ips[0]
                        found_address = found_ip.get('address') if isinstance(found_ip, dict) else getattr(found_ip, 'address', None)
                        logger.info(f"Found IP address {found_address} using network search for {ip_base}")
                        validated_ip = found_address
                except Exception as search_error:
                    logger.debug(f"Network search failed: {search_error}")
        
        if not existing_ips:
            # Provide helpful error message
            search_terms_tried = [validated_ip] + alternative_searches if 'alternative_searches' in locals() else [validated_ip]
            raise ValueError(f"IP address not found in NetBox. Tried: {', '.join(search_terms_tried)}. Ensure IP is assigned to device interface first.")
        
        ip_address_obj = existing_ips[0]
        ip_id = ip_address_obj.get('id') if isinstance(ip_address_obj, dict) else ip_address_obj.id
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not find IP address '{validated_ip}': {e}")
    
    # STEP 6: VERIFY IP IS ASSIGNED TO DEVICE INTERFACE
    try:
        # Check if IP is assigned to an interface
        assigned_object_type = ip_address_obj.get('assigned_object_type') if isinstance(ip_address_obj, dict) else getattr(ip_address_obj, 'assigned_object_type', None)
        assigned_object_id = ip_address_obj.get('assigned_object_id') if isinstance(ip_address_obj, dict) else getattr(ip_address_obj, 'assigned_object_id', None)
        
        if assigned_object_type != "dcim.interface" or not assigned_object_id:
            raise ValueError(f"IP address {validated_ip} is not assigned to any interface")
        
        # Get the interface and verify it belongs to our device
        interface = client.dcim.interfaces.get(assigned_object_id)
        
        # Apply comprehensive defensive handling for interface → device resolution
        interface_name = 'Unknown'
        interface_device_id = None
        interface_device_name = 'Unknown'
        
        if isinstance(interface, dict):
            interface_name = interface.get('name', 'Unknown')
            interface_device = interface.get('device')
            
            if isinstance(interface_device, dict):
                # Device is a nested object with id and name
                interface_device_id = interface_device.get('id')
                interface_device_name = interface_device.get('name', 'Unknown')
            elif isinstance(interface_device, int):
                # Device is just an ID, need to fetch the device object
                interface_device_id = interface_device
                try:
                    device_obj = client.dcim.devices.get(interface_device_id)
                    interface_device_name = device_obj.get('name') if isinstance(device_obj, dict) else device_obj.name
                except Exception as e:
                    logger.warning(f"Could not fetch device name for ID {interface_device_id}: {e}")
                    interface_device_name = f"Device-{interface_device_id}"
            elif interface_device is not None:
                # Device is some other object type
                interface_device_id = getattr(interface_device, 'id', None)
                interface_device_name = getattr(interface_device, 'name', 'Unknown')
        else:
            # Handle as object
            interface_name = getattr(interface, 'name', 'Unknown')
            interface_device = getattr(interface, 'device', None)
            
            if interface_device:
                if isinstance(interface_device, int):
                    # Device is just an ID
                    interface_device_id = interface_device
                    try:
                        device_obj = client.dcim.devices.get(interface_device_id)
                        interface_device_name = device_obj.get('name') if isinstance(device_obj, dict) else device_obj.name
                    except Exception as e:
                        logger.warning(f"Could not fetch device name for ID {interface_device_id}: {e}")
                        interface_device_name = f"Device-{interface_device_id}"
                else:
                    # Device is an object
                    interface_device_id = getattr(interface_device, 'id', None)
                    interface_device_name = getattr(interface_device, 'name', 'Unknown')
        
        if interface_device_id != device_id:
            raise ValueError(f"IP address {validated_ip} is assigned to device '{interface_device_name}', not '{device_name}'")
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not verify IP assignment: {e}")
    
    # STEP 7: UPDATE DEVICE PRIMARY IP
    primary_field = "primary_ip4" if detected_version == "ipv4" else "primary_ip6"
    
    try:
        update_payload = {primary_field: ip_id}
        
        updated_device = client.dcim.devices.update(device_id, confirm=confirm, **update_payload)
        
        # Apply defensive dict/object handling to response
        device_id_updated = updated_device.get('id') if isinstance(updated_device, dict) else updated_device.id
        device_name_updated = updated_device.get('name') if isinstance(updated_device, dict) else updated_device.name
        
    except Exception as e:
        raise ValueError(f"NetBox API error during primary IP update: {e}")
    
    # STEP 8: RETURN SUCCESS
    return {
        "success": True,
        "message": f"Primary {detected_version.upper()} address successfully set for device '{device_name}'.",
        "data": {
            "device_id": device_id_updated,
            "device_name": device_name_updated,
            "primary_ip": {
                "address": validated_ip,
                "version": detected_version,
                "field": primary_field,
                "ip_id": ip_id
            },
            "assignment": {
                "interface_name": interface_name,
                "interface_id": assigned_object_id
            }
        }
    }


# TODO: Implement advanced device lifecycle management tools:
# - netbox_configure_device_settings
# - netbox_monitor_device_health
# - netbox_bulk_device_operations  
# - netbox_map_device_dependencies
# - netbox_clone_device_configuration
# - netbox_device_compliance_check
