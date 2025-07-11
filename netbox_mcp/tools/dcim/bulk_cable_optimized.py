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


def is_port_available(pynetbox_interface_object):
    """
    Bepaalt of een poort beschikbaar is voor een nieuwe kabel.
    Een poort wordt als beschikbaar beschouwd als er geen kabel aan is gekoppeld.
    
    GEMINI FIX: Robust port availability check based on cable presence.
    A port is only available if cable is None.
    
    Args:
        pynetbox_interface_object: NetBox interface object (dict or pynetbox object)
        
    Returns:
        bool: True if port is available, False if occupied
    """
    # Handle both dict and object responses defensively
    if isinstance(pynetbox_interface_object, dict):
        cable = pynetbox_interface_object.get('cable')
    else:
        cable = pynetbox_interface_object.cable
    
    # A port is available ONLY if cable is None (no cable object attached)
    return cable is None


def get_resource_details(resource, client, device_lookup=None):
    """
    Haalt details op van een resource, ongeacht of het een dict, object of int (ID) is.
    Maakt gebruik van een pre-fetched lookup tabel voor performance.
    
    GEMINI FIX: Enhanced defensive handling for int/dict/object responses.
    
    Args:
        resource: Resource object (int ID, dict, or pynetbox object)
        client: NetBox client for fallback API calls
        device_lookup: Pre-fetched lookup dict for performance optimization
        
    Returns:
        tuple: (resource_id, resource_name)
    """
    if isinstance(resource, int):
        # We hebben alleen een ID. Zoek het op in de batch-fetched lookup.
        if device_lookup and resource in device_lookup:
            res_obj = device_lookup[resource]
            return res_obj.id, res_obj.name
        else:
            # Fallback naar een directe API call (minder performant, maar robuust)
            logger.warning(f"Fallback API call for resource ID {resource} - consider adding to batch lookup")
            try:
                res_obj = client.dcim.devices.get(resource)
                return (res_obj.id, res_obj.name) if res_obj else (resource, "Unknown")
            except Exception as e:
                logger.error(f"Failed to fetch resource {resource}: {e}")
                return resource, "Unknown"
    
    elif isinstance(resource, dict):
        # Het is een dictionary
        return resource.get('id'), resource.get('name')
        
    else:
        # Het is een pynetbox object
        return resource.id, resource.name


def bulk_create_cables_resilient(cable_plan: List[dict], client) -> dict:
    """
    Voert een bulk kabelcreatie uit en vangt fouten per kabel af.
    
    GEMINI FIX: Implements graceful partial success for bulk operations.
    Returns detailed success/error breakdown instead of failing completely.
    
    Args:
        cable_plan: List of cable data dictionaries
        client: NetBox client for API calls
        
    Returns:
        Dict with success and error results
    """
    success_results = []
    error_results = []
    
    for i, cable_data in enumerate(cable_plan):
        try:
            # Create cable with confirm=True for actual creation
            new_cable = client.dcim.cables.create(**cable_data)
            success_results.append({
                "index": i,
                "data": cable_data,
                "cable_id": new_cable.id,
                "result": f"Kabel #{new_cable.id} succesvol aangemaakt."
            })
            logger.info(f"Cable {i+1}/{len(cable_plan)} created successfully: #{new_cable.id}")
            
        except Exception as e:
            error_results.append({
                "index": i,
                "data": cable_data,
                "error": str(e)
            })
            logger.warning(f"Cable {i+1}/{len(cable_plan)} failed: {e}")
            
    return {
        "success": success_results,
        "errors": error_results,
        "total_attempted": len(cable_plan),
        "total_success": len(success_results),
        "total_errors": len(error_results),
        "success_rate": f"{len(success_results)}/{len(cable_plan)} ({(len(success_results) / len(cable_plan) * 100) if len(cable_plan) > 0 else 0.0:.1f}%)"
    }


@mcp_tool(category="dcim")
def netbox_bulk_cable_with_fallback(
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
    Resilient bulk cable creation with graceful fallback mechanisms.
    
    GEMINI FIX: Enhanced workflow with multiple fallback strategies.
    Attempts optimized tools first, falls back to simpler approaches on failure.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Source rack name (e.g., "L5", "K3")
        switch_name: Target switch name (e.g., "IDRAC L05")
        interface_name: Interface pattern to match (e.g., "idrac", "lom1")
        switch_port_pattern: Switch port prefix (e.g., "POORT", "Te1/1/")
        cable_color: Cable color (e.g., "green", "cat6 blue")
        cable_type: Cable type specification (default: "cat6")
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Comprehensive result with fallback information
    """
    
    logger.info(f"Starting resilient bulk cable workflow: {rack_name} -> {switch_name}")
    
    # Strategy 1: Try optimized bulk cable tool
    try:
        logger.info("Strategy 1: Attempting netbox_bulk_cable_interfaces_to_switch")
        result = netbox_bulk_cable_interfaces_to_switch(
            client=client,
            rack_name=rack_name,
            switch_name=switch_name,
            interface_name=interface_name,
            switch_port_pattern=switch_port_pattern,
            cable_color=cable_color,
            cable_type=cable_type,
            confirm=confirm
        )
        
        if result.get("success"):
            result["strategy_used"] = "optimized_bulk_tool"
            return result
        else:
            logger.warning(f"Strategy 1 failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.warning(f"Strategy 1 failed with exception: {e}")
    
    # Strategy 2: Try simplified manual workflow
    try:
        logger.info("Strategy 2: Attempting simplified manual workflow")
        
        # Get interface count
        interface_count_result = netbox_count_interfaces_in_rack(
            client=client,
            rack_name=rack_name,
            interface_name=interface_name
        )
        
        if not interface_count_result.get("success"):
            raise Exception(f"Interface counting failed: {interface_count_result.get('error')}")
            
        interface_count = interface_count_result["total_interfaces"]
        
        # Get available ports
        port_count_result = netbox_count_switch_ports_available(
            client=client,
            switch_name=switch_name,
            port_pattern=switch_port_pattern
        )
        
        if not port_count_result.get("success"):
            raise Exception(f"Port counting failed: {port_count_result.get('error')}")
            
        available_ports = port_count_result["available"]
        
        if interface_count > available_ports:
            return {
                "success": False,
                "error": "insufficient_capacity",
                "message": f"Insufficient ports: need {interface_count}, available {available_ports}",
                "strategy_used": "manual_workflow_capacity_check",
                "fallback_suggestion": "Review port mapping or use different port range"
            }
        
        # At this point we have validated capacity, suggest manual mapping
        return {
            "success": True,
            "strategy_used": "manual_workflow_suggestion",
            "action": "workflow_guidance",
            "capacity_check": {
                "interfaces_found": interface_count,
                "ports_available": available_ports,
                "capacity_sufficient": True
            },
            "recommended_next_steps": {
                "message": "Capacity validated. Use manual mapping for reliable connection.",
                "workflow": [
                    f"1. Create manual mapping list with {interface_count} connections",
                    f"2. Use {switch_port_pattern}1 through {switch_port_pattern}{interface_count} for ports",
                    f"3. Execute with netbox_bulk_create_cable_connections",
                    f"4. Monitor with resilient error handling"
                ]
            }
        }
        
    except Exception as e:
        logger.warning(f"Strategy 2 failed: {e}")
    
    # Strategy 3: Return comprehensive fallback guidance
    return {
        "success": False,
        "error": "all_strategies_failed",
        "strategy_used": "fallback_guidance",
        "message": "All automated strategies failed. Manual intervention required.",
        "fallback_options": {
            "option_1": {
                "name": "Manual Interface Discovery",
                "tools": ["netbox_list_all_devices(site_name='your_site')", 
                         f"netbox_get_device_interfaces(device_name='device_name')"],
                "description": "Manually discover interfaces and create mapping list"
            },
            "option_2": {
                "name": "Direct Cable Creation",
                "tools": ["netbox_create_cable_connection"],
                "description": "Create cables one by one with explicit device/interface names"
            },
            "option_3": {
                "name": "Review Port Availability",
                "tools": [f"netbox_get_device_interfaces(device_name='{switch_name}')"],
                "description": "Manually verify switch port availability and conflicts"
            }
        }
    }


@mcp_tool(category="dcim")
def netbox_bulk_cable_interfaces_to_switch(
    client: NetBoxClient,
    rack_name: str,
    switch_name: str,
    interface_name: str = "lom1",
    switch_port_pattern: str = "Te1/1/",
    start_port_number: Optional[int] = 1,
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
        start_port_number: Optional port number to start mapping from (e.g., 1, 25)
        cable_color: Cable color name (e.g., "green") or 6-digit hex code (e.g., "00ff00").
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
            rack_name="L5", switch_name="IDRAC L05", interface_name="idrac", 
            switch_port_pattern="POORT ", start_port_number=1, cable_color="green", confirm=True
        )
    """
    
    # GEMINI FIX: Add validation for cable_color parameter
    VALID_COLORS = [
        "black", "dark-grey", "grey", "light-grey", "white", "red", "orange",
        "yellow", "green", "cyan", "blue", "purple", "pink", "brown"
    ]
    if cable_color:
        import re
        if not (re.match(r'^[0-9a-fA-F]{6}$', cable_color) or cable_color.lower() in VALID_COLORS):
            raise ValueError(
                f"Invalid cable_color '{cable_color}'. "
                f"Please use a valid color name or a 6-digit hex code. "
                f"Valid names are: {', '.join(VALID_COLORS)}"
            )

    # Safety check
    if not confirm:
        return {
            "success": False,
            "error": "confirmation_required",
            "message": "This operation requires confirm=True to execute"
        }
    
    try:
        logger.info(f"Bulk cabling {interface_name} interfaces in rack {rack_name} to switch {switch_name}")
        
        # OPTIMIZATION: Single API call to get all specified interfaces in rack
        all_interfaces = client.dcim.interfaces.filter(
            device__rack__name=rack_name,
            name=interface_name
        )
        
        # DEFENSIVE VALIDATION: Verify devices are actually in the specified rack
        # This prevents the critical bug where API filters return wrong devices
        device_ids = set()
        for interface in all_interfaces:
            device = interface.device
            # FIX: Correctly handle device name resolution to prevent AttributeError
            if isinstance(device, int):
                device_obj = client.dcim.devices.get(device)
                device_id = device_obj.id if device_obj else device
            elif isinstance(device, dict):
                device_id = device.get('id')
            else:
                device_id = device.id
            device_ids.add(device_id)
        
        # Batch fetch devices for performance
        device_lookup = {}
        if device_ids:
            devices = client.dcim.devices.filter(id__in=list(device_ids))
            device_lookup = {d.id: d for d in devices}
        
        # Filter interfaces to only those in the correct rack
        rack_interfaces = []
        for interface in all_interfaces:
            device = interface.device
            device_id, device_name = get_resource_details(device, client, device_lookup)
            
            # Verify device is in correct rack
            device_obj = device_lookup.get(device_id)
            if device_obj and hasattr(device_obj, 'rack') and device_obj.rack:
                rack_name_actual = device_obj.rack.name if hasattr(device_obj.rack, 'name') else str(device_obj.rack)
                if rack_name_actual == rack_name:
                    rack_interfaces.append(interface)
        
        if not rack_interfaces:
            return {
                "success": False,
                "error": "no_interfaces_found",
                "message": f"No '{interface_name}' interfaces found in rack '{rack_name}'"
            }
        
        # Get switch ports with real-time data
        NO_CACHE = True
        switch_ports = client.dcim.interfaces.filter(
            device__name=switch_name,
            no_cache=NO_CACHE
        )
        
        # Filter ports by pattern and availability
        available_ports = []
        for port in switch_ports:
            port_name = port.get('name') if isinstance(port, dict) else port.name
            if port_name and port_name.startswith(switch_port_pattern):
                if is_port_available(port):
                    available_ports.append(port)
        
        # Sort ports naturally
        def natural_sort_key(port):
            import re
            port_name = port.get('name') if isinstance(port, dict) else port.name
            numbers = re.findall(r'\d+', port_name)
            return int(numbers[-1]) if numbers else 0
        
        available_ports.sort(key=natural_sort_key)
        
        # Filter by start_port_number if specified
        if start_port_number and start_port_number > 1:
            def get_port_num(port):
                import re
                port_name = port.get('name') if isinstance(port, dict) else port.name
                numbers = re.findall(r'\d+', port_name)
                return int(numbers[-1]) if numbers else 0
            
            available_ports = [
                p for p in available_ports
                if get_port_num(p) >= start_port_number
            ]
        
        # Check capacity
        if len(rack_interfaces) > len(available_ports):
            return {
                "success": False,
                "error": "insufficient_capacity",
                "message": f"Need {len(rack_interfaces)} ports, only {len(available_ports)} available"
            }
        
        # Create cable connections
        cable_connections = []
        for i, rack_interface in enumerate(rack_interfaces[:len(available_ports)]):
            switch_port = available_ports[i]
            
            device = rack_interface.device
            # OPTIMIZED: Use pre-fetched device lookup to avoid N+1 queries
            device_id = device.id if hasattr(device, 'id') else device
            device_obj = device_lookup.get(device_id)
            device_name = device_obj.name if device_obj else f"device-id-{device_id}"
            
            switch_port_name = switch_port.get('name') if isinstance(switch_port, dict) else switch_port.name
            interface_name_actual = rack_interface.get('name') if isinstance(rack_interface, dict) else rack_interface.name
            
            cable_data = {
                "device_a_name": device_name,
                "interface_a_name": interface_name_actual,
                "device_b_name": switch_name,
                "interface_b_name": switch_port_name,
                "cable_type": cable_type
            }
            
            if cable_color:
                cable_data["cable_color"] = cable_color
            
            cable_connections.append(cable_data)
        
        # Execute bulk cable creation
        result = bulk_create_cables_resilient(cable_connections, client)
        
        return {
            "success": True,
            "strategy_used": "optimized_bulk_creation",
            "interfaces_processed": len(rack_interfaces),
            "cables_created": len(result.get('success_results', [])),
            "cables_failed": len(result.get('error_results', [])),
            "detailed_results": result
        }
        
    except Exception as e:
        logger.error(f"Bulk cable creation failed: {e}")
        return {
            "success": False,
            "error": "execution_failed",
            "message": str(e)
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
        
        # GEMINI FIX: Use real-time data to prevent stale port availability
        NO_CACHE = True
        all_device_ports = client.dcim.interfaces.filter(
            device__name=switch_name,
            no_cache=NO_CACHE
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
            
            # GEMINI FIX: Use new robust port availability utility function
            is_available = is_port_available(port)
            
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


@mcp_tool(category="dcim")
def netbox_bulk_cable_lom1_to_switch_optimized(
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
    GEMINI OPTIMIZED: Highly optimized bulk cable creation avoiding N+1 queries.
    
    This function has been optimized to eliminate redundant API calls and
    improve performance for large-scale bulk cable operations.
    """
    
    # Constants for better readability
    NO_CACHE = True
    
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
        all_rack_interfaces = client.dcim.interfaces.filter(
            device__rack__name=rack_name,
            name=interface_name
        )
        
        # DEFENSIVE VALIDATION: Verify devices are actually in the specified rack
        device_ids = set()
        for interface in all_rack_interfaces:
            device = interface.get('device') if isinstance(interface, dict) else interface.device
            device_id = device.get('id') if isinstance(device, dict) else getattr(device, 'id', None)
            if device_id:
                device_ids.add(device_id)
        
        devices_batch = client.dcim.devices.filter(id__in=list(device_ids))
        
        rack_ids = {dev.get('rack', {}).get('id') if isinstance(dev, dict) else getattr(dev.rack, 'id', None) for dev in devices_batch}
        rack_ids = {rid for rid in rack_ids if rid}
        racks_batch = client.dcim.racks.filter(id__in=list(rack_ids))
        rack_lookup = {r.id: r.name for r in racks_batch}
        
        device_lookup = {d.id: d for d in devices_batch}
        
        rack_interfaces = []
        skipped_devices = []
        
        for interface in all_rack_interfaces:
            device_ref = interface.get('device') if isinstance(interface, dict) else interface.device
            device_id = device_ref.get('id') if isinstance(device_ref, dict) else getattr(device_ref, 'id', None)
            device_obj = device_lookup.get(device_id)
            
            if not device_obj:
                continue
            
            rack_ref = device_obj.get('rack') if isinstance(device_obj, dict) else device_obj.rack
            rack_id = rack_ref.get('id') if isinstance(rack_ref, dict) else getattr(rack_ref, 'id', None)
            actual_rack = rack_lookup.get(rack_id)
            
            if actual_rack == rack_name:
                if not (interface.get('cable') if isinstance(interface, dict) else interface.cable):
                    rack_interfaces.append(interface)
            else:
                device_name = device_obj.get('name') if isinstance(device_obj, dict) else device_obj.name
                skipped_devices.append(f"{device_name} (in {actual_rack})")

        if not rack_interfaces:
            return {"success": False, "error": f"No available '{interface_name}' interfaces found in rack '{rack_name}'", "error_type": "NotFoundError"}
        
        # Use real-time data to prevent stale cache issues
        NO_CACHE = True
        all_device_ports = client.dcim.interfaces.filter(
            device__name=switch_name,
            no_cache=NO_CACHE
        )
        
        switch_ports = [
            port for port in all_device_ports
            if (port.get('name') if isinstance(port, dict) else port.name).startswith(switch_port_pattern) and not (port.get('cable') if isinstance(port, dict) else port.cable)
        ]

        if not switch_ports:
            return {"success": False, "error": f"No available '{switch_port_pattern}*' ports found on switch '{switch_name}'", "error_type": "NotFoundError"}
        
        interfaces_sorted = sorted(rack_interfaces, key=lambda i: (i.device.position, i.device.name))
        switch_ports_sorted = sorted(switch_ports, key=lambda x: natural_sort_key(x.get('name') if isinstance(x, dict) else x.name))

        # GEMINI FIX: Filter ports based on the start_port_number
        if start_port_number and start_port_number > 1:
            original_count = len(switch_ports_sorted)
            
            def get_port_num(port_name):
                import re
                numbers = re.findall(r'\d+', port_name)
                return int(numbers[-1]) if numbers else 0

            switch_ports_sorted = [
                p for p in switch_ports_sorted
                if get_port_num((p.get('name') if isinstance(p, dict) else p.name)) >= start_port_number
            ]
            logger.info(f"Filtered switch ports to start from port {start_port_number}. Original: {original_count}, New: {len(switch_ports_sorted)}")

        if len(switch_ports_sorted) < len(interfaces_sorted):
            return {"success": False, "error": f"Insufficient switch ports: need {len(interfaces_sorted)}, only {len(switch_ports_sorted)} available", "error_type": "InsufficientResourcesError"}
        
        cable_connections = []
        for i, rack_interface in enumerate(interfaces_sorted):
            if i < len(switch_ports_sorted):
                device = rack_interface.device
                # GEMINI FIX: Correctly handle device name resolution after .get()
                device_obj = client.dcim.devices.get(device.id)
                device_name = device_obj.name if device_obj else f"device-id-{device.id}"

                switch_port = switch_ports_sorted[i]
                
                cable_connections.append({
                    "device_a_name": device_name,
                    "interface_a_name": rack_interface.name,
                    "device_b_name": switch_name,
                    "interface_b_name": switch_port.name,
                    "rack_interface_id": rack_interface.id,
                    "switch_port_id": switch_port.id
                })
        
        if not confirm:
            return {"success": True, "action": "dry_run", "plan": {"total_connections": len(cable_connections), "connections": cable_connections[:5]}}
        
        successful_cables, failed_cables = [], []
        for conn in cable_connections:
            try:
                cable_data = {
                    "a_terminations": [{"object_type": "dcim.interface", "object_id": conn["rack_interface_id"]}],
                    "b_terminations": [{"object_type": "dcim.interface", "object_id": conn["switch_port_id"]}],
                    "type": cable_type, "status": "connected",
                    "label": f"{conn['device_a_name']}-{conn['interface_a_name']} -> {conn['device_b_name']}-{conn['interface_b_name']}"
                }
                if cable_color:
                    cable_data["color"] = cable_color.lower()
                
                new_cable = client.dcim.cables.create(confirm=True, **cable_data)
                successful_cables.append({"cable_id": new_cable.id, "connection": conn})
            except Exception as e:
                failed_cables.append({"connection": conn, "error": str(e)})
        
        return {
            "success": len(successful_cables) > 0,
            "results": {
                "total_attempted": len(cable_connections),
                "successful": len(successful_cables),
                "failed": len(failed_cables),
                "successful_cables": successful_cables,
                "failed_cables": failed_cables
            }
        }
        
    except Exception as e:
        logger.error(f"Bulk cable creation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


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
        
        # GEMINI FIX: Use real-time data to prevent stale port availability
        NO_CACHE = True
        all_device_ports = client.dcim.interfaces.filter(
            device__name=switch_name,
            no_cache=NO_CACHE
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
            
            # GEMINI FIX: Use new robust port availability utility function
            is_available = is_port_available(port)
            
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