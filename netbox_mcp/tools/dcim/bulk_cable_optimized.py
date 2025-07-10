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
def netbox_bulk_cable_interfaces_to_switch(
    client: NetBoxClient,
    rack_name: str,
    switch_name: str,
    interface_name: str = "lom1",
    switch_port_pattern: str = "Te1/1/",
    cable_color: Optional[str] = None,
    cable_type: str = "cat6",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Optimized bulk cable creation for specific interfaces to switch ports.
    
    This highly optimized tool handles the common scenario of connecting
    all specified interfaces in a rack to sequential switch ports with
    minimal API calls and maximum efficiency.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Source rack name (e.g., "K3")
        switch_name: Target switch name (e.g., "switch1.K3")
        interface_name: Interface name to connect (e.g., "lom1", "eth0", "mgmt", "ilo", "idrac")
        switch_port_pattern: Switch port pattern (e.g., "Te1/1/", "GigabitEthernet0/0/")
        cable_color: Cable color for all connections (e.g., "pink", "blue")
        cable_type: Type of cable (default: "cat6")
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Bulk operation results with detailed success/failure information
        
    Examples:
        netbox_bulk_cable_interfaces_to_switch(
            rack_name="K3", switch_name="switch1.K3", interface_name="lom1", 
            switch_port_pattern="Te1/1/", cable_color="pink", confirm=True
        )
        netbox_bulk_cable_interfaces_to_switch(
            rack_name="K3", switch_name="switch1.K3", interface_name="eth0", 
            switch_port_pattern="GigabitEthernet0/0/", cable_color="blue", confirm=True
        )
        netbox_bulk_cable_interfaces_to_switch(
            rack_name="K3", switch_name="switch1.K3", interface_name="mgmt", 
            switch_port_pattern="FastEthernet0/", cable_color="yellow", confirm=True
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
        logger.info(f"Starting optimized bulk cable creation: {rack_name} -> {switch_name} (interface: {interface_name})")
        
        # OPTIMIZATION 1: Single API call to get all specified interfaces in rack
        # Note: Don't use cable__isnull=True here as it may be inconsistent
        # Instead, filter manually after retrieval for reliability
        all_rack_interfaces = client.dcim.interfaces.filter(
            device__rack__name=rack_name,
            name=interface_name
        )
        
        # DEFENSIVE VALIDATION: Verify devices are actually in the specified rack
        # This prevents the critical bug where API filters return wrong devices
        # PERFORMANCE OPTIMIZATION: Batch fetch devices to avoid N+1 queries
        
        # Step 1: Extract unique device IDs from interfaces
        device_ids = set()
        for interface in all_rack_interfaces:
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            
            # Extract device ID with proper defensive handling
            device_id = None
            if isinstance(device, int):
                device_id = device  # device is already the ID
            elif isinstance(device, dict):
                device_id = device.get('id')
            else:
                device_id = getattr(device, 'id', None)
            
            if device_id is not None:
                device_ids.add(device_id)
        
        # Remove None values if any
        device_ids = {dev_id for dev_id in device_ids if dev_id is not None}
        
        # Step 2: BATCH FETCH all devices in a single API call
        logger.debug(f"Batch fetching {len(device_ids)} devices to validate rack locations")
        devices_batch = client.dcim.devices.filter(id__in=list(device_ids))
        
        # Step 2.5: Extract unique rack IDs and batch fetch racks
        rack_ids = set()
        for device in devices_batch:
            rack_ref = None
            if isinstance(device, dict):
                rack_ref = device.get('rack')
            else:
                rack_ref = getattr(device, 'rack', None)
            
            # Extract rack ID from rack reference (could be int ID or dict)
            rack_id = None
            if isinstance(rack_ref, int):
                rack_id = rack_ref  # rack is already the ID
            elif isinstance(rack_ref, dict):
                rack_id = rack_ref.get('id')
            elif rack_ref is not None:
                rack_id = getattr(rack_ref, 'id', None)
            
            if rack_id is not None:
                rack_ids.add(rack_id)
        
        # Batch fetch racks to get rack names
        rack_lookup = {}
        if rack_ids:
            logger.debug(f"Batch fetching {len(rack_ids)} racks to get rack names")
            racks_batch = client.dcim.racks.filter(id__in=list(rack_ids))
            for rack in racks_batch:
                if isinstance(rack, dict):
                    rack_id = rack.get('id')
                    rack_name = rack.get('name')
                else:
                    rack_id = getattr(rack, 'id', None)
                    rack_name = getattr(rack, 'name', None)
                if rack_id and rack_name:
                    rack_lookup[rack_id] = rack_name
        
        # Step 3: Create device lookup map for O(1) access
        device_lookup = {}
        for device in devices_batch:
            # Extract device ID properly
            device_id = None
            if isinstance(device, dict):
                device_id = device.get('id')
                if device_id is not None:
                    device_lookup[device_id] = device
            else:
                device_id = getattr(device, 'id', None)
                if device_id is not None:
                    device_lookup[device_id] = device
        
        # Step 4: Process interfaces with batch-fetched device and rack data
        rack_interfaces = []
        skipped_devices = []
        
        for interface in all_rack_interfaces:
            # Get device information with defensive handling
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            
            # Extract device ID for lookup
            if isinstance(device, int):
                device_id = device
            elif isinstance(device, dict):
                device_id = device.get('id')
            else:
                device_id = getattr(device, 'id', None)
            
            # Get device from batch lookup (O(1) operation)
            device_obj = device_lookup.get(device_id)
            if not device_obj:
                logger.warning(f"Device ID {device_id} not found in batch fetch - skipping interface")
                continue
            
            # Extract device name and rack with defensive handling
            if isinstance(device_obj, dict):
                device_name = device_obj.get('name', f'device-{device_id}')
                rack_ref = device_obj.get('rack')
            else:
                device_name = getattr(device_obj, 'name', f'device-{device_id}')
                rack_ref = getattr(device_obj, 'rack', None)
            
            # Extract rack ID from rack reference (could be int ID or dict)
            rack_id = None
            if isinstance(rack_ref, int):
                rack_id = rack_ref
            elif isinstance(rack_ref, dict):
                rack_id = rack_ref.get('id')
            elif rack_ref is not None:
                rack_id = getattr(rack_ref, 'id', None)
            
            actual_rack = rack_lookup.get(rack_id) if rack_id else None
            
            # CRITICAL CHECK: Only include devices that are ACTUALLY in the specified rack
            if actual_rack == rack_name:
                interface_cable = interface.get('cable') if isinstance(interface, dict) else interface.cable
                if not interface_cable:  # Only available interfaces
                    rack_interfaces.append(interface)
                    logger.debug(f"✅ Including {device_name}:{interface_name} (actually in rack {actual_rack})")
                else:
                    logger.debug(f"⚠️  Skipping {device_name}:{interface_name} (already connected)")
            else:
                skipped_devices.append(f"{device_name} (in {actual_rack})")
                logger.warning(f"❌ RACK MISMATCH: {device_name} returned by rack filter but is in '{actual_rack}', not '{rack_name}'")
        
        logger.info(f"Found {len(all_rack_interfaces)} total '{interface_name}' interfaces from rack filter")
        logger.info(f"Validated {len(rack_interfaces)} interfaces actually in rack '{rack_name}'")
        
        if skipped_devices:
            logger.warning(f"Skipped {len(skipped_devices)} devices not in rack '{rack_name}': {', '.join(skipped_devices)}")
        
        if not rack_interfaces:
            return {
                "success": False,
                "error": f"No available '{interface_name}' interfaces found in rack '{rack_name}'",
                "error_type": "NotFoundError"
            }
        
        # OPTIMIZATION 2: Single API call to get all switch ports
        # Note: Don't use cable__isnull=True here as it may be inconsistent
        # Instead, filter manually after retrieval for reliability
        # IMPORTANT: Filter by name pattern manually due to NetBox API issues
        all_device_ports = client.dcim.interfaces.filter(
            device__name=switch_name
        )
        
        # DEFENSIVE VALIDATION: Verify switch device exists and get its actual rack
        switch_device = None
        switch_actual_rack = None
        
        if all_device_ports:
            # Get the device from the first interface to validate switch location
            first_port = all_device_ports[0]
            device = first_port.get('device') if isinstance(first_port, dict) else first_port.device
            
            # Handle device being int ID, dict, or object
            if isinstance(device, int):
                switch_device = client.dcim.devices.get(device)
                switch_actual_rack = switch_device.get('rack', {}).get('name') if isinstance(switch_device, dict) else (switch_device.rack.name if switch_device.rack else None)
            elif isinstance(device, dict):
                switch_device = device
                switch_actual_rack = device.get('rack', {}).get('name') if device.get('rack') else None
            else:
                switch_device = device
                switch_actual_rack = device.rack.name if device.rack else None
                
            logger.info(f"Switch '{switch_name}' is located in rack '{switch_actual_rack}'")
        
        # Filter manually for ports matching the pattern
        all_switch_ports = []
        for port in all_device_ports:
            port_name = port.get('name') if isinstance(port, dict) else port.name
            if port_name and port_name.startswith(switch_port_pattern):
                all_switch_ports.append(port)
        
        # Filter manually for available ports (no cable)
        switch_ports = []
        for port in all_switch_ports:
            port_cable = port.get('cable') if isinstance(port, dict) else port.cable
            if not port_cable:  # Only available ports
                switch_ports.append(port)
        
        logger.info(f"Found {len(all_switch_ports)} total switch ports on '{switch_name}' (rack: {switch_actual_rack})")
        logger.info(f"Filtered to {len(switch_ports)} available ports")
        
        if not switch_ports:
            return {
                "success": False,
                "error": f"No available '{switch_port_pattern}*' ports found on switch '{switch_name}'",
                "error_type": "NotFoundError"
            }
        
        # Sort interfaces and ports for logical mapping
        def safe_sort_key(interface):
            """Safely extract device position and name for sorting."""
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            
            # Handle device being int ID, dict, or object
            if isinstance(device, int):
                # For sorting purposes, use device ID as position and empty string as name
                return (device, '')
            elif isinstance(device, dict):
                return (device.get('position', 0), device.get('name', ''))
            else:
                return (getattr(device, 'position', 0), getattr(device, 'name', ''))
        
        interfaces_sorted = sorted(rack_interfaces, key=safe_sort_key)
        
        switch_ports_sorted = sorted(switch_ports, key=lambda x: natural_sort_key(
            x.get('name') if isinstance(x, dict) else x.name
        ))
        
        # Check if we have enough switch ports
        if len(switch_ports_sorted) < len(interfaces_sorted):
            return {
                "success": False,
                "error": f"Insufficient switch ports: need {len(interfaces_sorted)}, only {len(switch_ports_sorted)} available",
                "error_type": "InsufficientResourcesError",
                "details": {
                    f"{interface_name}_interfaces_found": len(interfaces_sorted),
                    "switch_ports_available": len(switch_ports_sorted)
                }
            }
        
        # Create cable connections list
        cable_connections = []
        for i, rack_interface in enumerate(interfaces_sorted):
            if i < len(switch_ports_sorted):
                # Enhanced defensive dict/object handling for nested device objects
                device = rack_interface.get('device') if isinstance(rack_interface, dict) else rack_interface.device
                
                # Handle device being int ID, dict, or object
                if isinstance(device, int):
                    # Device is just an ID, need to fetch device name
                    device_obj = client.dcim.devices.get(device)
                    device_name = device_obj.get('name') if isinstance(device_obj, dict) else device_obj.name
                elif isinstance(device, dict):
                    device_name = device.get('name', f'device-{device.get("id", "unknown")}')
                else:
                    device_name = getattr(device, 'name', f'device-{getattr(device, "id", "unknown")}')
                
                rack_interface_name = rack_interface.get('name') if isinstance(rack_interface, dict) else rack_interface.name
                rack_interface_id = rack_interface.get('id') if isinstance(rack_interface, dict) else rack_interface.id
                
                switch_port = switch_ports_sorted[i]
                switch_port_name = switch_port.get('name') if isinstance(switch_port, dict) else switch_port.name
                switch_port_id = switch_port.get('id') if isinstance(switch_port, dict) else switch_port.id
                
                # DEBUG: Log the mapping
                logger.info(f"Mapping {i}: {device_name}:{rack_interface_name} (ID:{rack_interface_id}) -> {switch_name}:{switch_port_name} (ID:{switch_port_id})")
                
                # Validation check to prevent same object connection
                if rack_interface_id == switch_port_id:
                    logger.error(f"CRITICAL: Same interface ID detected! rack_id={rack_interface_id}, switch_id={switch_port_id}")
                    continue
                
                cable_connections.append({
                    "device_a_name": device_name,
                    "interface_a_name": rack_interface_name,
                    "device_b_name": switch_name,
                    "interface_b_name": switch_port_name,
                    "rack_interface_id": rack_interface_id,
                    "switch_port_id": switch_port_id
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
                        "object_id": connection["rack_interface_id"]
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
def netbox_count_interfaces_in_rack(
    client: NetBoxClient,
    rack_name: str,
    interface_name: str = "lom1"
) -> Dict[str, Any]:
    """
    Efficiently count specific interfaces in a rack with single API call.
    
    This optimized tool provides fast counting of interfaces by name without
    the overhead of multiple API calls or complex data processing.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Rack name to check (e.g., "K3")
        interface_name: Interface name to count (e.g., "lom1", "eth0", "mgmt", "ilo", "idrac")
        
    Returns:
        Count of specified interfaces with availability status
        
    Examples:
        netbox_count_interfaces_in_rack(rack_name="K3", interface_name="lom1")
        netbox_count_interfaces_in_rack(rack_name="K3", interface_name="eth0")
        netbox_count_interfaces_in_rack(rack_name="K3", interface_name="mgmt")
        netbox_count_interfaces_in_rack(rack_name="K3", interface_name="ilo")
        netbox_count_interfaces_in_rack(rack_name="K3", interface_name="idrac")
    """
    
    try:
        logger.info(f"Counting '{interface_name}' interfaces in rack '{rack_name}'")
        
        # OPTIMIZATION: Single API call to get all specified interfaces in rack
        all_interfaces = client.dcim.interfaces.filter(
            device__rack__name=rack_name,
            name=interface_name
        )
        
        # DEFENSIVE VALIDATION: Verify devices are actually in the specified rack
        # This prevents the critical bug where API filters return wrong devices
        # PERFORMANCE OPTIMIZATION: Batch fetch devices to avoid N+1 queries
        
        # Step 1: Extract unique device IDs from interfaces
        device_ids = set()
        for interface in all_interfaces:
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            if isinstance(device, int):
                device_ids.add(device)
            elif isinstance(device, dict):
                device_ids.add(device.get('id'))
            else:
                device_ids.add(getattr(device, 'id', None))
        
        # Remove None values if any
        device_ids = {dev_id for dev_id in device_ids if dev_id is not None}
        
        # Step 2: BATCH FETCH all devices in a single API call
        logger.debug(f"Batch fetching {len(device_ids)} devices to validate rack locations")
        devices_batch = client.dcim.devices.filter(id__in=list(device_ids))
        
        # Step 2.5: Extract unique rack IDs and batch fetch racks
        rack_ids = set()
        for device in devices_batch:
            rack_ref = None
            if isinstance(device, dict):
                rack_ref = device.get('rack')
            else:
                rack_ref = getattr(device, 'rack', None)
            
            # Extract rack ID from rack reference (could be int ID or dict)
            rack_id = None
            if isinstance(rack_ref, int):
                rack_id = rack_ref  # rack is already the ID
            elif isinstance(rack_ref, dict):
                rack_id = rack_ref.get('id')
            elif rack_ref is not None:
                rack_id = getattr(rack_ref, 'id', None)
            
            if rack_id is not None:
                rack_ids.add(rack_id)
        
        # Batch fetch racks to get rack names
        rack_lookup = {}
        if rack_ids:
            logger.debug(f"Batch fetching {len(rack_ids)} racks to get rack names")
            racks_batch = client.dcim.racks.filter(id__in=list(rack_ids))
            for rack in racks_batch:
                if isinstance(rack, dict):
                    rack_id = rack.get('id')
                    rack_name = rack.get('name')
                else:
                    rack_id = getattr(rack, 'id', None)
                    rack_name = getattr(rack, 'name', None)
                if rack_id and rack_name:
                    rack_lookup[rack_id] = rack_name
        
        # Step 3: Create device lookup map for O(1) access
        device_lookup = {}
        for device in devices_batch:
            # Extract device ID properly
            device_id = None
            if isinstance(device, dict):
                device_id = device.get('id')
                if device_id is not None:
                    device_lookup[device_id] = device
            else:
                device_id = getattr(device, 'id', None)
                if device_id is not None:
                    device_lookup[device_id] = device
        
        # Step 4: Process interfaces with batch-fetched device and rack data
        validated_interfaces = []
        skipped_devices = []
        
        for interface in all_interfaces:
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            
            # Extract device ID for lookup
            if isinstance(device, int):
                device_id = device
            elif isinstance(device, dict):
                device_id = device.get('id')
            else:
                device_id = getattr(device, 'id', None)
            
            # Get device from batch lookup (O(1) operation)
            device_obj = device_lookup.get(device_id)
            if not device_obj:
                logger.warning(f"Device ID {device_id} not found in batch fetch - skipping interface")
                continue
            
            # Extract device name and rack with defensive handling
            if isinstance(device_obj, dict):
                device_name = device_obj.get('name', f'device-{device_id}')
                rack_ref = device_obj.get('rack')
            else:
                device_name = getattr(device_obj, 'name', f'device-{device_id}')
                rack_ref = getattr(device_obj, 'rack', None)
            
            # Extract rack ID from rack reference (could be int ID or dict)
            rack_id = None
            if isinstance(rack_ref, int):
                rack_id = rack_ref
            elif isinstance(rack_ref, dict):
                rack_id = rack_ref.get('id')
            elif rack_ref is not None:
                rack_id = getattr(rack_ref, 'id', None)
            
            actual_rack = rack_lookup.get(rack_id) if rack_id else None
            
            # CRITICAL CHECK: Only include devices that are ACTUALLY in the specified rack
            if actual_rack == rack_name:
                validated_interfaces.append(interface)
                logger.debug(f"✅ Including {device_name}:{interface_name} (actually in rack {actual_rack})")
            else:
                skipped_devices.append(f"{device_name} (in {actual_rack})")
                logger.warning(f"❌ RACK MISMATCH: {device_name} returned by rack filter but is in '{actual_rack}', not '{rack_name}'")
        
        logger.info(f"Found {len(all_interfaces)} total '{interface_name}' interfaces from rack filter")
        logger.info(f"Validated {len(validated_interfaces)} interfaces actually in rack '{rack_name}'")
        
        if skipped_devices:
            logger.warning(f"Skipped {len(skipped_devices)} devices not in rack '{rack_name}': {', '.join(skipped_devices)}")
        
        if not validated_interfaces:
            return {
                "success": True,
                "count": 0,
                "available": 0,
                "unavailable": 0,
                "message": f"No '{interface_name}' interfaces found in rack '{rack_name}' (after validation)",
                "devices": [],
                "validation_info": {
                    "total_from_filter": len(all_interfaces),
                    "validated_in_rack": len(validated_interfaces),
                    "skipped_wrong_rack": len(skipped_devices)
                }
            }
        
        # Process validated results using batch-fetched device data
        available_count = 0
        unavailable_count = 0
        device_list = []
        
        for interface in validated_interfaces:
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            
            # Extract device ID for lookup
            if isinstance(device, int):
                device_id = device
            elif isinstance(device, dict):
                device_id = device.get('id')
            else:
                device_id = getattr(device, 'id', None)
            
            # Get device from batch lookup (O(1) operation) - already fetched above
            device_obj = device_lookup.get(device_id)
            if device_obj:
                device_name = device_obj.get('name') if isinstance(device_obj, dict) else getattr(device_obj, 'name', f'device-{device_id}')
            else:
                device_name = f'device-{device_id}'
            
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
                "interface_name": interface_name,
                "available": is_available,
                "cable_id": cable_id
            })
        
        # Sort devices by name
        device_list.sort(key=lambda x: x["device_name"])
        
        return {
            "success": True,
            "count": len(validated_interfaces),
            "available": available_count,
            "unavailable": unavailable_count,
            "message": f"Found {len(validated_interfaces)} '{interface_name}' interfaces in rack '{rack_name}' ({available_count} available, {unavailable_count} connected)",
            "devices": device_list,
            "validation_info": {
                "total_from_filter": len(all_interfaces),
                "validated_in_rack": len(validated_interfaces),
                "skipped_wrong_rack": len(skipped_devices)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to count '{interface_name}' interfaces: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


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
    
    LEGACY FUNCTION: Use netbox_bulk_cable_interfaces_to_switch() instead for better flexibility.
    This function is kept for backward compatibility.
    
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
    return netbox_bulk_cable_interfaces_to_switch(
        client=client,
        rack_name=rack_name,
        switch_name=switch_name,
        interface_name="lom1",
        switch_port_pattern="Te1/1/",
        cable_color=cable_color,
        cable_type=cable_type,
        confirm=confirm
    )


@mcp_tool(category="dcim")
def netbox_count_lom1_interfaces_in_rack(
    client: NetBoxClient,
    rack_name: str
) -> Dict[str, Any]:
    """
    Efficiently count lom1 interfaces in a rack with single API call.
    
    LEGACY FUNCTION: Use netbox_count_interfaces_in_rack() instead for better flexibility.
    This function is kept for backward compatibility.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Rack name to check (e.g., "K3")
        
    Returns:
        Count of lom1 interfaces with availability status
        
    Example:
        netbox_count_lom1_interfaces_in_rack(rack_name="K3")
    """
    return netbox_count_interfaces_in_rack(client, rack_name, "lom1")


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
        # CRITICAL FIX: Don't use name__istartswith as it matches multiple interface types
        # Instead, get all interfaces and filter manually for exact pattern matching
        all_device_ports = client.dcim.interfaces.filter(
            device__name=switch_name
        )
        
        # Filter manually for exact pattern matching (prevents overcounting)
        matching_ports = []
        for port in all_device_ports:
            port_name = port.get('name') if isinstance(port, dict) else port.name
            if port_name and port_name.startswith(port_pattern):
                matching_ports.append(port)
        
        if not matching_ports:
            return {
                "success": True,
                "total_ports": 0,
                "available": 0,
                "unavailable": 0,
                "message": f"No ports found matching '{port_pattern}' on switch '{switch_name}'",
                "ports": []
            }
        
        # Process results with exact pattern matching
        available_count = 0
        unavailable_count = 0
        port_list = []
        
        for port in matching_ports:
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
            "total_ports": len(matching_ports),
            "available": available_count,
            "unavailable": unavailable_count,
            "message": f"Found {len(matching_ports)} ports matching '{port_pattern}' on '{switch_name}' ({available_count} available, {unavailable_count} connected)",
            "ports": port_list
        }
        
    except Exception as e:
        logger.error(f"Failed to count switch ports: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }