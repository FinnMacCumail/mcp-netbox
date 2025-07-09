#!/usr/bin/env python3
"""
Optimized Bulk Cable Management Tools

Simplified and highly efficient bulk cable creation tools that reduce API calls
and improve performance for mass infrastructure operations.
"""

from typing import Dict, Optional, Any, List
import logging
from datetime import datetime
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_bulk_cable_lom1_to_switch(
    client: NetBoxClient,
    rack_name: str,
    switch_name: str,
    cable_color: Optional[str] = None,
    cable_type: str = "cat6",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Optimized bulk cable creation for lom1 interfaces to switch ports.
    
    This highly optimized tool specifically handles the common scenario of
    connecting all lom1 interfaces in a rack to sequential switch ports
    with minimal API calls and maximum efficiency.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Source rack name (e.g., "K3")
        switch_name: Target switch name (e.g., "switch1.K3")
        cable_color: Cable color for all connections (e.g., "pink", "blue")
        cable_type: Type of cable (default: "cat6")
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Bulk operation results with detailed success/failure information
        
    Example:
        netbox_bulk_cable_lom1_to_switch(
            rack_name="K3",
            switch_name="switch1.K3",
            cable_color="pink",
            confirm=True
        )
    """
    
    def natural_sort_key(interface_name):
        """Create a natural sort key for interface names."""
        import re
        parts = []
        for part in re.split(r'(\d+)', interface_name):
            if part.isdigit():
                parts.append(int(part))
            else:
                parts.append(part)
        return parts
    
    try:
        logger.info(f"Starting optimized bulk cable creation: {rack_name} -> {switch_name}")
        
        # OPTIMIZATION 1: Single API call to get all lom1 interfaces in rack
        lom1_interfaces = client.dcim.interfaces.filter(
            device__rack__name=rack_name,
            name="lom1",
            cable__isnull=True  # Only available interfaces
        )
        
        if not lom1_interfaces:
            return {
                "success": False,
                "error": f"No available lom1 interfaces found in rack '{rack_name}'",
                "error_type": "NotFoundError"
            }
        
        # OPTIMIZATION 2: Single API call to get all available switch ports
        switch_ports = client.dcim.interfaces.filter(
            device__name=switch_name,
            name__istartswith="Te1/1/",  # More specific than regex
            cable__isnull=True  # Only available ports
        )
        
        if not switch_ports:
            return {
                "success": False,
                "error": f"No available Te1/1/* ports found on switch '{switch_name}'",
                "error_type": "NotFoundError"
            }
        
        # Sort interfaces and ports for logical mapping
        lom1_sorted = sorted(lom1_interfaces, key=lambda x: (
            x.get('device', {}).get('position', 0) if isinstance(x, dict) else x.device.position,
            x.get('device', {}).get('name', '') if isinstance(x, dict) else x.device.name
        ))
        
        switch_ports_sorted = sorted(switch_ports, key=lambda x: natural_sort_key(
            x.get('name') if isinstance(x, dict) else x.name
        ))
        
        # Check if we have enough switch ports
        if len(switch_ports_sorted) < len(lom1_sorted):
            return {
                "success": False,
                "error": f"Insufficient switch ports: need {len(lom1_sorted)}, only {len(switch_ports_sorted)} available",
                "error_type": "InsufficientResourcesError",
                "details": {
                    "lom1_interfaces_found": len(lom1_sorted),
                    "switch_ports_available": len(switch_ports_sorted)
                }
            }
        
        # Create cable connections list
        cable_connections = []
        for i, lom1_interface in enumerate(lom1_sorted):
            if i < len(switch_ports_sorted):
                # Defensive dict/object handling
                device = lom1_interface.get('device') if isinstance(lom1_interface, dict) else lom1_interface.device
                device_name = device.get('name') if isinstance(device, dict) else device.name
                lom1_name = lom1_interface.get('name') if isinstance(lom1_interface, dict) else lom1_interface.name
                
                switch_port_name = switch_ports_sorted[i].get('name') if isinstance(switch_ports_sorted[i], dict) else switch_ports_sorted[i].name
                
                cable_connections.append({
                    "device_a_name": device_name,
                    "interface_a_name": lom1_name,
                    "device_b_name": switch_name,
                    "interface_b_name": switch_port_name,
                    "lom1_interface_id": lom1_interface.get('id') if isinstance(lom1_interface, dict) else lom1_interface.id,
                    "switch_port_id": switch_ports_sorted[i].get('id') if isinstance(switch_ports_sorted[i], dict) else switch_ports_sorted[i].id
                })
        
        if not confirm:
            return {
                "success": True,
                "action": "dry_run",
                "object_type": "bulk_cable_plan",
                "plan": {
                    "total_connections": len(cable_connections),
                    "source_rack": rack_name,
                    "target_switch": switch_name,
                    "cable_type": cable_type,
                    "cable_color": cable_color,
                    "connections": cable_connections[:5]  # Show first 5 for preview
                },
                "message": f"Would create {len(cable_connections)} cable connections. Set confirm=True to execute.",
                "dry_run": True
            }
        
        # Execute bulk cable creation
        successful_cables = []
        failed_cables = []
        
        for connection in cable_connections:
            try:
                # OPTIMIZATION 3: Direct API call to create cable using interface IDs
                cable_data = {
                    "a_terminations": [{
                        "object_type": "dcim.interface",
                        "object_id": connection["lom1_interface_id"]
                    }],
                    "b_terminations": [{
                        "object_type": "dcim.interface", 
                        "object_id": connection["switch_port_id"]
                    }],
                    "type": cable_type,
                    "status": "connected"
                }
                
                # Add color if specified
                if cable_color:
                    cable_data["color"] = cable_color
                
                # Add automatic label
                cable_data["label"] = f"{connection['device_a_name']}-{connection['interface_a_name']} -> {connection['device_b_name']}-{connection['interface_b_name']}"
                
                new_cable = client.dcim.cables.create(confirm=True, **cable_data)
                cable_id = new_cable.get('id') if isinstance(new_cable, dict) else new_cable.id
                
                successful_cables.append({
                    "cable_id": cable_id,
                    "connection": connection,
                    "created_at": datetime.now().isoformat()
                })
                
            except Exception as e:
                failed_cables.append({
                    "connection": connection,
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                })
                logger.error(f"Failed to create cable {connection['device_a_name']}-{connection['interface_a_name']} -> {connection['device_b_name']}-{connection['interface_b_name']}: {e}")
        
        success_rate = len(successful_cables) / len(cable_connections) * 100 if cable_connections else 0
        
        return {
            "success": len(successful_cables) > 0,
            "action": "bulk_created",
            "object_type": "bulk_cable_connections",
            "results": {
                "total_attempted": len(cable_connections),
                "successful": len(successful_cables),
                "failed": len(failed_cables),
                "success_rate": f"{success_rate:.1f}%",
                "successful_cables": successful_cables,
                "failed_cables": failed_cables
            },
            "summary": {
                "message": f"Successfully created {len(successful_cables)} out of {len(cable_connections)} cables",
                "source_rack": rack_name,
                "target_switch": switch_name,
                "cable_specifications": {
                    "type": cable_type,
                    "color": cable_color,
                    "status": "connected"
                }
            },
            "dry_run": False
        }
        
    except Exception as e:
        logger.error(f"Bulk cable creation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_count_lom1_interfaces_in_rack(
    client: NetBoxClient,
    rack_name: str
) -> Dict[str, Any]:
    """
    Efficiently count lom1 interfaces in a rack with single API call.
    
    This optimized tool provides fast counting of lom1 interfaces without
    the overhead of multiple API calls or complex data processing.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Rack name to check (e.g., "K3")
        
    Returns:
        Count of lom1 interfaces with availability status
        
    Example:
        netbox_count_lom1_interfaces_in_rack(rack_name="K3")
    """
    
    try:
        logger.info(f"Counting lom1 interfaces in rack '{rack_name}'")
        
        # OPTIMIZATION: Single API call to get all lom1 interfaces in rack
        all_lom1 = client.dcim.interfaces.filter(
            device__rack__name=rack_name,
            name="lom1"
        )
        
        if not all_lom1:
            return {
                "success": True,
                "count": 0,
                "available": 0,
                "unavailable": 0,
                "message": f"No lom1 interfaces found in rack '{rack_name}'",
                "devices": []
            }
        
        # Process results
        available_count = 0
        unavailable_count = 0
        device_list = []
        
        for interface in all_lom1:
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            device_name = device.get('name') if isinstance(device, dict) else device.name
            interface_cable = interface.get('cable') if isinstance(interface, dict) else interface.cable
            
            is_available = not bool(interface_cable)
            
            if is_available:
                available_count += 1
            else:
                unavailable_count += 1
                
            # Safe cable ID extraction
            cable_id = None
            if interface_cable:
                if isinstance(interface_cable, dict):
                    cable_id = interface_cable.get('id')
                elif hasattr(interface_cable, 'id'):
                    cable_id = interface_cable.id
                else:
                    cable_id = interface_cable  # May be just the ID itself
                    
            device_list.append({
                "device_name": device_name,
                "interface_name": "lom1",
                "available": is_available,
                "cable_id": cable_id
            })
        
        # Sort devices by name
        device_list.sort(key=lambda x: x["device_name"])
        
        return {
            "success": True,
            "count": len(all_lom1),
            "available": available_count,
            "unavailable": unavailable_count,
            "message": f"Found {len(all_lom1)} lom1 interfaces in rack '{rack_name}' ({available_count} available, {unavailable_count} connected)",
            "devices": device_list
        }
        
    except Exception as e:
        logger.error(f"Failed to count lom1 interfaces: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="dcim")
def netbox_count_switch_ports_available(
    client: NetBoxClient,
    switch_name: str,
    port_pattern: str = "Te1/1/"
) -> Dict[str, Any]:
    """
    Efficiently count available switch ports with single API call.
    
    This optimized tool provides fast counting of available switch ports
    without the overhead of complex pattern matching or multiple API calls.
    
    Args:
        client: NetBoxClient instance (injected)
        switch_name: Switch name to check (e.g., "switch1.K3")
        port_pattern: Port pattern to match (e.g., "Te1/1/")
        
    Returns:
        Count of available switch ports
        
    Example:
        netbox_count_switch_ports_available(switch_name="switch1.K3")
    """
    
    try:
        logger.info(f"Counting available switch ports on '{switch_name}' matching '{port_pattern}'")
        
        # OPTIMIZATION: Single API call to get all matching ports
        all_ports = client.dcim.interfaces.filter(
            device__name=switch_name,
            name__istartswith=port_pattern
        )
        
        if not all_ports:
            return {
                "success": True,
                "total_ports": 0,
                "available": 0,
                "unavailable": 0,
                "message": f"No ports found matching '{port_pattern}' on switch '{switch_name}'",
                "ports": []
            }
        
        # Process results
        available_count = 0
        unavailable_count = 0
        port_list = []
        
        for port in all_ports:
            port_name = port.get('name') if isinstance(port, dict) else port.name
            port_cable = port.get('cable') if isinstance(port, dict) else port.cable
            
            is_available = not bool(port_cable)
            
            if is_available:
                available_count += 1
            else:
                unavailable_count += 1
                
            # Safe cable ID extraction
            cable_id = None
            if port_cable:
                if isinstance(port_cable, dict):
                    cable_id = port_cable.get('id')
                elif hasattr(port_cable, 'id'):
                    cable_id = port_cable.id
                else:
                    cable_id = port_cable  # May be just the ID itself
                    
            port_list.append({
                "port_name": port_name,
                "available": is_available,
                "cable_id": cable_id
            })
        
        # Sort ports naturally
        def natural_sort_key(port_name):
            import re
            parts = []
            for part in re.split(r'(\d+)', port_name):
                if part.isdigit():
                    parts.append(int(part))
                else:
                    parts.append(part)
            return parts
            
        port_list.sort(key=lambda x: natural_sort_key(x["port_name"]))
        
        return {
            "success": True,
            "total_ports": len(all_ports),
            "available": available_count,
            "unavailable": unavailable_count,
            "message": f"Found {len(all_ports)} ports matching '{port_pattern}' on '{switch_name}' ({available_count} available, {unavailable_count} connected)",
            "ports": port_list
        }
        
    except Exception as e:
        logger.error(f"Failed to count switch ports: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }