#!/usr/bin/env python3
"""
DCIM Interface Mapping Tools

Advanced tools for intelligent interface mapping and bulk cable connection planning.
These tools enable automated discovery and mapping of device interfaces for
structured cabling and bulk infrastructure operations.
"""

from typing import Dict, Optional, Any, List
import logging
import re
from datetime import datetime
from ...registry import mcp_tool
from ...client import NetBoxClient
from ...validation import CableValidator

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_map_rack_to_switch_interfaces(
    client: NetBoxClient,
    rack_name: str,
    switch_name: str,
    interface_filter: str = "lom1",
    switch_interface_pattern: str = "Te1/1/*",
    mapping_algorithm: str = "sequential",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Intelligently map rack device interfaces to switch ports for bulk cable planning.
    
    This enterprise-grade interface mapping tool provides automated discovery and
    intelligent mapping of device interfaces to switch ports, essential for
    structured cabling deployments and bulk infrastructure operations.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Source rack name (e.g., "K3", "R01")
        switch_name: Target switch name (e.g., "switch1.K3", "sw-access-01")
        interface_filter: Interface name pattern to match (e.g., "lom1", "eth*", "GigabitEthernet*")
        switch_interface_pattern: Switch port pattern (e.g., "Te1/1/*", "GigabitEthernet1/0/*")
        mapping_algorithm: Mapping strategy - "sequential", "availability", "position"
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Intelligent mapping proposal with device-interface pairs for bulk cable creation
        
    Example:
        netbox_map_rack_to_switch_interfaces(
            rack_name="K3",
            switch_name="switch1.K3",
            interface_filter="lom1",
            switch_interface_pattern="Te1/1/*",
            mapping_algorithm="sequential",
            confirm=True
        )
    """
    
    def natural_sort_key(interface_name):
        """Create a natural sort key for interface names (e.g., Te1/1/1, Te1/1/2, Te1/1/10)."""
        # Split by numbers and text for natural sorting
        parts = []
        for part in re.split(r'(\d+)', interface_name):
            if part.isdigit():
                parts.append(int(part))
            else:
                parts.append(part)
        return parts
    
    def discover_rack_interfaces(rack_name, interface_pattern):
        """Discover all devices in rack with matching interface pattern - OPTIMIZED VERSION."""
        try:
            # OPTIMIZATION 1: Single API call to get all interfaces in rack with pattern filter
            # This replaces the N+1 query pattern (1 call for devices + N calls for interfaces)
            if interface_pattern == "*":
                # Get all interfaces for devices in rack
                interfaces = client.dcim.interfaces.filter(device__rack__name=rack_name)
            else:
                # Get only matching interfaces - much more efficient!
                interfaces = client.dcim.interfaces.filter(
                    device__rack__name=rack_name,
                    name__icontains=interface_pattern
                )
            
            if not interfaces:
                return [], f"No interfaces found matching '{interface_pattern}' in rack '{rack_name}'"
            
            matching_interfaces = []
            
            for interface in interfaces:
                # Defensive dict/object handling
                interface_name = interface.get('name') if isinstance(interface, dict) else interface.name
                interface_id = interface.get('id') if isinstance(interface, dict) else interface.id
                interface_cable = interface.get('cable') if isinstance(interface, dict) else interface.cable
                
                # Get device info from interface (included in API response)
                device = interface.get('device') if isinstance(interface, dict) else interface.device
                device_name = device.get('name') if isinstance(device, dict) else device.name
                device_id = device.get('id') if isinstance(device, dict) else device.id
                device_position = device.get('position') if isinstance(device, dict) else device.position
                
                # Exact match check for interface pattern
                if interface_pattern == "*" or interface_pattern == interface_name or interface_pattern in interface_name:
                    matching_interfaces.append({
                        "device_name": device_name,
                        "device_id": device_id,
                        "interface_name": interface_name,
                        "interface_id": interface_id,
                        "rack_position": device_position,
                        "available": not bool(interface_cable),
                        "existing_cable_id": interface_cable.get('id') if interface_cable and isinstance(interface_cable, dict) else interface_cable.id if interface_cable else None
                    })
            
            logger.info(f"Found {len(matching_interfaces)} interfaces matching '{interface_pattern}' in rack '{rack_name}'")
            return matching_interfaces, None
            
        except Exception as e:
            logger.error(f"Error discovering rack interfaces: {e}")
            return [], f"Error discovering rack interfaces: {str(e)}"
    
    def discover_switch_ports(switch_name, port_pattern):
        """Discover available switch ports matching pattern - OPTIMIZED VERSION."""
        try:
            # OPTIMIZATION 2: Direct interface query with device filter
            # This replaces the 2-step process (find device, then interfaces)
            
            # Convert pattern to more efficient filter
            if port_pattern.endswith("/*"):
                # Pattern like "Te1/1/*" -> search for "Te1/1/"
                base_pattern = port_pattern.replace("/*", "/")
                interfaces = client.dcim.interfaces.filter(
                    device__name=switch_name,
                    name__istartswith=base_pattern
                )
            else:
                # Exact pattern or wildcard
                if "*" in port_pattern:
                    pattern_base = port_pattern.replace("*", "")
                    interfaces = client.dcim.interfaces.filter(
                        device__name=switch_name,
                        name__icontains=pattern_base
                    )
                else:
                    interfaces = client.dcim.interfaces.filter(
                        device__name=switch_name,
                        name=port_pattern
                    )
            
            if not interfaces:
                return [], f"No interfaces found matching '{port_pattern}' on switch '{switch_name}'"
            
            matching_ports = []
            
            for interface in interfaces:
                interface_name = interface.get('name') if isinstance(interface, dict) else interface.name
                interface_id = interface.get('id') if isinstance(interface, dict) else interface.id
                interface_cable = interface.get('cable') if isinstance(interface, dict) else interface.cable
                
                # Additional regex check for complex patterns
                pattern_regex = port_pattern.replace("*", ".*")
                if re.match(pattern_regex, interface_name):
                    matching_ports.append({
                        "interface_name": interface_name,
                        "interface_id": interface_id,
                        "available": not bool(interface_cable),
                        "existing_cable_id": interface_cable.get('id') if interface_cable and isinstance(interface_cable, dict) else interface_cable.id if interface_cable else None
                    })
            
            logger.info(f"Found {len(matching_ports)} switch ports matching '{port_pattern}' on '{switch_name}'")
            return matching_ports, None
            
        except Exception as e:
            logger.error(f"Error discovering switch ports: {e}")
            return [], f"Error discovering switch ports: {str(e)}"
    
    try:
        # Validate mapping algorithm
        valid_algorithms = ["sequential", "availability", "position"]
        if mapping_algorithm not in valid_algorithms:
            return {
                "success": False,
                "error": f"Invalid mapping_algorithm '{mapping_algorithm}'. Valid algorithms: {valid_algorithms}",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Starting interface mapping: {rack_name} -> {switch_name}, filter: {interface_filter}, pattern: {switch_interface_pattern}")
        
        # Discover rack interfaces
        rack_interfaces, rack_error = discover_rack_interfaces(rack_name, interface_filter)
        if rack_error:
            return {
                "success": False,
                "error": rack_error,
                "error_type": "NotFoundError"
            }
        
        # Discover switch ports
        switch_ports, switch_error = discover_switch_ports(switch_name, switch_interface_pattern)
        if switch_error:
            return {
                "success": False,
                "error": switch_error,
                "error_type": "NotFoundError"
            }
        
        # Filter available interfaces and ports
        available_rack_interfaces = [iface for iface in rack_interfaces if iface["available"]]
        available_switch_ports = [port for port in switch_ports if port["available"]]
        
        # Sort interfaces based on mapping algorithm
        if mapping_algorithm == "sequential":
            # Sort rack interfaces by position, then by name
            available_rack_interfaces.sort(key=lambda x: (x["rack_position"] or 0, x["interface_name"]))
            # Sort switch ports by natural name order
            available_switch_ports.sort(key=lambda x: natural_sort_key(x["interface_name"]))
        elif mapping_algorithm == "availability":
            # Sort by availability (already filtered, so just sort by name)
            available_rack_interfaces.sort(key=lambda x: x["interface_name"])
            available_switch_ports.sort(key=lambda x: natural_sort_key(x["interface_name"]))
        elif mapping_algorithm == "position":
            # Sort rack interfaces by position (lower positions first)
            available_rack_interfaces.sort(key=lambda x: (x["rack_position"] or 999, x["interface_name"]))
            available_switch_ports.sort(key=lambda x: natural_sort_key(x["interface_name"]))
        
        # Check if we have enough switch ports
        if len(available_switch_ports) < len(available_rack_interfaces):
            return {
                "success": False,
                "error": f"Insufficient switch ports: need {len(available_rack_interfaces)}, only {len(available_switch_ports)} available",
                "error_type": "InsufficientResourcesError",
                "available_rack_interfaces": len(available_rack_interfaces),
                "available_switch_ports": len(available_switch_ports)
            }
        
        if not confirm:
            # Dry run mode - return mapping proposal
            logger.info(f"DRY RUN: Would map {len(available_rack_interfaces)} rack interfaces to switch ports")
            
            # Create mapping preview
            mapping_preview = []
            for i, rack_interface in enumerate(available_rack_interfaces):
                if i < len(available_switch_ports):
                    mapping_preview.append({
                        "device_a_name": rack_interface["device_name"],
                        "interface_a_name": rack_interface["interface_name"],
                        "device_b_name": switch_name,
                        "interface_b_name": available_switch_ports[i]["interface_name"],
                        "rack_position": rack_interface["rack_position"]
                    })
            
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "interface_mapping",
                "mapping_proposal": {
                    "total_mappings": len(mapping_preview),
                    "mapping_algorithm": mapping_algorithm,
                    "rack_name": rack_name,
                    "switch_name": switch_name,
                    "interface_filter": interface_filter,
                    "switch_interface_pattern": switch_interface_pattern,
                    "mappings": mapping_preview
                },
                "statistics": {
                    "total_rack_interfaces": len(rack_interfaces),
                    "available_rack_interfaces": len(available_rack_interfaces),
                    "unavailable_rack_interfaces": len(rack_interfaces) - len(available_rack_interfaces),
                    "total_switch_ports": len(switch_ports),
                    "available_switch_ports": len(available_switch_ports),
                    "unavailable_switch_ports": len(switch_ports) - len(available_switch_ports)
                },
                "dry_run": True
            }
        
        # Create the final mapping
        cable_connections = []
        for i, rack_interface in enumerate(available_rack_interfaces):
            if i < len(available_switch_ports):
                cable_connections.append({
                    "device_a_name": rack_interface["device_name"],
                    "interface_a_name": rack_interface["interface_name"],
                    "device_b_name": switch_name,
                    "interface_b_name": available_switch_ports[i]["interface_name"],
                    "rack_position": rack_interface["rack_position"]
                })
        
        return {
            "success": True,
            "action": "mapped",
            "object_type": "interface_mapping",
            "mapping_result": {
                "total_mappings": len(cable_connections),
                "mapping_algorithm": mapping_algorithm,
                "rack_name": rack_name,
                "switch_name": switch_name,
                "interface_filter": interface_filter,
                "switch_interface_pattern": switch_interface_pattern,
                "cable_connections": cable_connections
            },
            "statistics": {
                "total_rack_interfaces": len(rack_interfaces),
                "available_rack_interfaces": len(available_rack_interfaces),
                "unavailable_rack_interfaces": len(rack_interfaces) - len(available_rack_interfaces),
                "total_switch_ports": len(switch_ports),
                "available_switch_ports": len(available_switch_ports),
                "unavailable_switch_ports": len(switch_ports) - len(available_switch_ports),
                "mapping_efficiency": f"{len(cable_connections)/len(available_rack_interfaces)*100:.1f}%" if available_rack_interfaces else "0%"
            },
            "unavailable_interfaces": [
                {
                    "device_name": iface["device_name"],
                    "interface_name": iface["interface_name"],
                    "reason": "Already connected",
                    "existing_cable_id": iface.get("existing_cable_id")
                }
                for iface in rack_interfaces if not iface["available"]
            ],
            "dry_run": False
        }
        
    except Exception as e:
        logger.error(f"Failed to map interfaces: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_generate_bulk_cable_plan(
    client: NetBoxClient,
    rack_name: str,
    switch_name: str,
    interface_filter: str = "lom1",
    switch_interface_pattern: str = "Te1/1/*",
    cable_type: str = "cat6",
    cable_color: Optional[str] = None,
    mapping_algorithm: str = "sequential",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Generate a complete bulk cable connection plan from rack to switch.
    
    This high-level orchestration tool combines interface mapping with cable
    specifications to create a ready-to-execute bulk cable installation plan.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Source rack name (e.g., "K3", "R01")
        switch_name: Target switch name (e.g., "switch1.K3", "sw-access-01")
        interface_filter: Interface name pattern to match (e.g., "lom1", "eth*")
        switch_interface_pattern: Switch port pattern (e.g., "Te1/1/*", "GigabitEthernet1/0/*")
        cable_type: Type of cable (cat5e, cat6, cat6a, cat7, cat8, etc.)
        cable_color: Cable color for all connections (e.g., "pink", "red", "blue")
        mapping_algorithm: Mapping strategy - "sequential", "availability", "position"
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Complete bulk cable installation plan ready for execution
        
    Example:
        netbox_generate_bulk_cable_plan(
            rack_name="K3",
            switch_name="switch1.K3",
            interface_filter="lom1",
            switch_interface_pattern="Te1/1/*",
            cable_type="cat6",
            cable_color="pink",
            mapping_algorithm="sequential",
            confirm=True
        )
    """
    
    try:
        logger.info(f"Generating bulk cable plan: {rack_name} -> {switch_name}")
        
        # First, get the interface mapping
        mapping_result = netbox_map_rack_to_switch_interfaces(
            client=client,
            rack_name=rack_name,
            switch_name=switch_name,
            interface_filter=interface_filter,
            switch_interface_pattern=switch_interface_pattern,
            mapping_algorithm=mapping_algorithm,
            confirm=confirm
        )
        
        if not mapping_result.get("success"):
            return mapping_result
        
        # Extract cable connections from mapping
        if confirm:
            cable_connections = mapping_result["mapping_result"]["cable_connections"]
        else:
            cable_connections = mapping_result["mapping_proposal"]["mappings"]
        
        # Validate cable parameters using shared validator
        try:
            cable_type = CableValidator.validate_type(cable_type)
            cable_color = CableValidator.validate_color(cable_color)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "ValidationError"
            }
        
        # Create the bulk cable plan
        bulk_cable_plan = {
            "plan_type": "bulk_cable_installation",
            "generated_at": datetime.now().isoformat(),
            "source_rack": rack_name,
            "target_switch": switch_name,
            "cable_specifications": {
                "cable_type": cable_type,
                "cable_color": cable_color,
                "cable_status": "connected",
                "mapping_algorithm": mapping_algorithm
            },
            "interface_mapping": mapping_result,
            "cable_connections": cable_connections,
            "execution_plan": {
                "total_cables": len(cable_connections),
                "recommended_batch_size": min(10, len(cable_connections)),
                "estimated_duration_minutes": len(cable_connections) * 2,  # 2 minutes per cable
                "rollback_supported": True
            }
        }
        
        if not confirm:
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "bulk_cable_plan",
                "bulk_cable_plan": bulk_cable_plan,
                "next_step": "Use netbox_bulk_create_cable_connections with the generated cable_connections",
                "dry_run": True
            }
        
        return {
            "success": True,
            "action": "generated",
            "object_type": "bulk_cable_plan",
            "bulk_cable_plan": bulk_cable_plan,
            "ready_for_execution": True,
            "next_step": "Use netbox_bulk_create_cable_connections with the generated cable_connections",
            "dry_run": False
        }
        
    except Exception as e:
        logger.error(f"Failed to generate bulk cable plan: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }