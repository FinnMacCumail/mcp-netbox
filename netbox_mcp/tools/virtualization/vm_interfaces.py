#!/usr/bin/env python3
"""
Virtual Machine Interface Management Tools

High-level tools for managing NetBox virtual machine interfaces,
enabling comprehensive VM network connectivity and configuration management.
"""

from typing import Dict, Optional, Any, List
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

@mcp_tool(category="virtualization")
def netbox_get_vm_interface_info(
    client: NetBoxClient,
    virtual_machine_name: Optional[str] = None,
    interface_name: Optional[str] = None,
    interface_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific VM interface.
    
    Args:
        client: NetBoxClient instance (injected)
        virtual_machine_name: Virtual machine name (used with interface_name)
        interface_name: Interface name to retrieve
        interface_id: Interface ID to retrieve
        
    Returns:
        Dict containing detailed VM interface information
        
    Raises:
        ValidationError: If no valid identifier provided
        NotFoundError: If VM interface not found
    """
    
    if interface_id:
        try:
            vm_interface = client.virtualization.interfaces.get(interface_id)
        except Exception as e:
            raise ValueError(f"VM interface with ID {interface_id} not found: {e}")
    elif virtual_machine_name and interface_name:
        try:
            # First find the VM
            virtual_machines = client.virtualization.virtual_machines.filter(name=virtual_machine_name)
            if not virtual_machines:
                raise ValueError(f"Virtual machine '{virtual_machine_name}' not found")
            
            vm = virtual_machines[0]
            vm_id = vm.get('id') if isinstance(vm, dict) else vm.id
            
            # Then find the interface
            interfaces = client.virtualization.interfaces.filter(
                virtual_machine_id=vm_id,
                name=interface_name
            )
            if not interfaces:
                raise ValueError(f"Interface '{interface_name}' not found on VM '{virtual_machine_name}'")
            
            vm_interface = interfaces[0]
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to find VM interface: {e}")
    else:
        raise ValueError("Either 'interface_id' or both 'virtual_machine_name' and 'interface_name' must be provided")
    
    # Apply defensive dict/object handling
    interface_id = vm_interface.get('id') if isinstance(vm_interface, dict) else vm_interface.id
    interface_name = vm_interface.get('name') if isinstance(vm_interface, dict) else vm_interface.name
    interface_type = vm_interface.get('type') if isinstance(vm_interface, dict) else getattr(vm_interface, 'type', None)
    interface_enabled = vm_interface.get('enabled') if isinstance(vm_interface, dict) else getattr(vm_interface, 'enabled', None)
    interface_mtu = vm_interface.get('mtu') if isinstance(vm_interface, dict) else getattr(vm_interface, 'mtu', None)
    interface_mac = vm_interface.get('mac_address') if isinstance(vm_interface, dict) else getattr(vm_interface, 'mac_address', None)
    interface_description = vm_interface.get('description') if isinstance(vm_interface, dict) else getattr(vm_interface, 'description', None)
    
    # Get virtual machine information - with comprehensive debugging
    vm_obj = vm_interface.get('virtual_machine') if isinstance(vm_interface, dict) else getattr(vm_interface, 'virtual_machine', None)
    
    # Debug: Log the entire VM interface object structure first
    logger.debug(f"Full VM interface object keys: {list(vm_interface.keys()) if isinstance(vm_interface, dict) else dir(vm_interface)}")
    logger.debug(f"VM object type: {type(vm_obj)}, content: {vm_obj}")
    
    vm_id = None
    vm_name = 'N/A'
    
    if isinstance(vm_obj, dict):
        vm_id = vm_obj.get('id')
        vm_name = vm_obj.get('name', vm_obj.get('display', 'N/A'))
        logger.debug(f"VM from dict - ID: {vm_id}, Name: {vm_name}, All keys: {list(vm_obj.keys())}")
    elif vm_obj:
        vm_id = getattr(vm_obj, 'id', None)
        vm_name = getattr(vm_obj, 'name', getattr(vm_obj, 'display', None))
        logger.debug(f"VM from object - ID: {vm_id}, Name: {vm_name}, Type: {type(vm_obj)}")
    else:
        logger.warning("VM object is None or empty")
    
    # Always try to fetch VM name directly from API if we have an ID
    if vm_id and str(vm_id).isdigit():
        try:
            logger.debug(f"Attempting direct VM API call for ID: {vm_id}")
            vm_full = client.virtualization.virtual_machines.get(vm_id)
            vm_name_from_api = vm_full.get('name') if isinstance(vm_full, dict) else vm_full.name
            logger.debug(f"SUCCESS: VM name from direct API call: {vm_name_from_api} for ID {vm_id}")
            vm_name = vm_name_from_api  # Always use the direct API result
        except Exception as e:
            logger.error(f"FAILED to fetch VM name for ID {vm_id}: {e}")
            if not vm_name or vm_name == 'N/A':
                vm_name = f"VM-{vm_id}"  # Fallback to VM-ID format
    else:
        logger.warning(f"Cannot fetch VM name - ID is invalid: {vm_id}")
        vm_id = vm_id or 'N/A'
        vm_name = 'N/A'
    
    # Get IP addresses assigned to this interface
    try:
        ip_addresses = list(client.ipam.ip_addresses.filter(assigned_object_id=interface_id))
        ip_count = len(ip_addresses)
        ip_list = []
        for ip in ip_addresses[:5]:  # Show first 5 IPs
            ip_addr = ip.get('address') if isinstance(ip, dict) else getattr(ip, 'address', 'N/A')
            ip_list.append(ip_addr)
    except Exception:
        ip_count = 0
        ip_list = []
    
    return {
        "success": True,
        "message": f"Retrieved VM interface '{interface_name}'.",
        "data": {
            "interface_id": interface_id,
            "name": interface_name,
            "type": interface_type,
            "enabled": interface_enabled,
            "mtu": interface_mtu,
            "mac_address": interface_mac,
            "description": interface_description,
            "virtual_machine": {
                "id": vm_id,
                "name": vm_name
            },
            "ip_addresses": {
                "count": ip_count,
                "addresses": ip_list
            },
            "url": vm_interface.get('url') if isinstance(vm_interface, dict) else getattr(vm_interface, 'url', None)
        }
    }

@mcp_tool(category="virtualization")
def netbox_list_all_vm_interfaces(
    client: NetBoxClient,
    virtual_machine_name: Optional[str] = None,
    interface_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get comprehensive list of all VM interfaces with filtering capabilities.
    
    This tool provides bulk VM interface discovery across the virtualization infrastructure,
    enabling efficient network connectivity analysis and interface management.
    
    Args:
        client: NetBoxClient instance (injected)
        virtual_machine_name: Filter by virtual machine name
        interface_type: Filter by interface type (virtual, bridge, lag, etc.)
        enabled: Filter by enabled status (True/False)
        limit: Maximum number of interfaces to return (default: 100)
        
    Returns:
        Dict containing summary list of VM interfaces with statistics
    """
    
    # Build filter parameters
    filter_params = {}
    
    if virtual_machine_name:
        # First find the VM ID
        try:
            vms = client.virtualization.virtual_machines.filter(name=virtual_machine_name)
            if not vms:
                raise ValueError(f"Virtual machine '{virtual_machine_name}' not found")
            vm = vms[0]
            vm_id = vm.get('id') if isinstance(vm, dict) else vm.id
            filter_params["virtual_machine_id"] = vm_id
        except Exception as e:
            raise ValueError(f"Failed to find virtual machine: {e}")
    
    if interface_type:
        filter_params["type"] = interface_type
    
    if enabled is not None:
        filter_params["enabled"] = enabled
    
    try:
        # Get VM interfaces with applied filters
        vm_interfaces = list(client.virtualization.interfaces.filter(**filter_params)[:limit])
        
        # Process interfaces with defensive dict/object handling
        interfaces_summary = []
        total_enabled = 0
        total_disabled = 0
        type_counts = {}
        
        for interface in vm_interfaces:
            interface_id = interface.get('id') if isinstance(interface, dict) else interface.id
            interface_name = interface.get('name') if isinstance(interface, dict) else interface.name
            interface_type_actual = interface.get('type') if isinstance(interface, dict) else getattr(interface, 'type', 'N/A')
            interface_enabled = interface.get('enabled') if isinstance(interface, dict) else getattr(interface, 'enabled', False)
            interface_mac = interface.get('mac_address') if isinstance(interface, dict) else getattr(interface, 'mac_address', None)
            
            # Count by status
            if interface_enabled:
                total_enabled += 1
            else:
                total_disabled += 1
            
            # Count by type
            type_counts[interface_type_actual] = type_counts.get(interface_type_actual, 0) + 1
            
            # Get VM information - with proper resolution
            vm_obj = interface.get('virtual_machine') if isinstance(interface, dict) else getattr(interface, 'virtual_machine', None)
            if isinstance(vm_obj, dict):
                vm_id = vm_obj.get('id')
                vm_name = vm_obj.get('name', 'N/A')
            else:
                vm_id = getattr(vm_obj, 'id', None) if vm_obj else None
                vm_name = getattr(vm_obj, 'name', None) if vm_obj else None
            
            # If we don't have proper VM name, fetch it directly
            if not vm_name or vm_name == 'N/A' or str(vm_name).isdigit():
                try:
                    if vm_id and vm_id != 'N/A':
                        vm_full = client.virtualization.virtual_machines.get(vm_id)
                        vm_name = vm_full.get('name') if isinstance(vm_full, dict) else vm_full.name
                        logger.debug(f"Fetched VM name from API in list: {vm_name} for ID {vm_id}")
                    else:
                        vm_name = 'N/A'
                except Exception as e:
                    logger.warning(f"Failed to fetch VM name in list for ID {vm_id}: {e}")
                    vm_name = 'N/A'
            
            # Count IP addresses for this interface
            try:
                ip_count = len(list(client.ipam.ip_addresses.filter(assigned_object_id=interface_id)))
            except Exception:
                ip_count = 0
            
            interfaces_summary.append({
                "id": interface_id,
                "name": interface_name,
                "type": interface_type_actual,
                "enabled": interface_enabled,
                "mac_address": interface_mac,
                "virtual_machine_name": vm_name,
                "ip_address_count": ip_count
            })
            
    except Exception as e:
        raise ValueError(f"Failed to retrieve VM interfaces: {e}")
    
    return {
        "success": True,
        "message": f"Found {len(interfaces_summary)} VM interfaces.",
        "total_interfaces": len(interfaces_summary),
        "statistics": {
            "enabled_interfaces": total_enabled,
            "disabled_interfaces": total_disabled,
            "interface_types": type_counts
        },
        "applied_filters": {
            "virtual_machine_name": virtual_machine_name,
            "interface_type": interface_type,
            "enabled": enabled,
            "limit": limit
        },
        "data": interfaces_summary
    }
