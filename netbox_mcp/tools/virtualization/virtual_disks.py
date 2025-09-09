#!/usr/bin/env python3
"""
Virtual Machine Disk Management Tools

High-level tools for managing NetBox virtual machine disks,
enabling comprehensive VM storage configuration and capacity management.
"""

from typing import Dict, Optional, Any, List
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

@mcp_tool(category="virtualization")
def netbox_get_virtual_disk_info(
    client: NetBoxClient,
    virtual_machine_name: Optional[str] = None,
    disk_name: Optional[str] = None,
    disk_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific virtual disk.
    
    Args:
        client: NetBoxClient instance (injected)
        virtual_machine_name: Virtual machine name (used with disk_name)
        disk_name: Disk name to retrieve
        disk_id: Disk ID to retrieve
        
    Returns:
        Dict containing detailed virtual disk information
        
    Raises:
        ValidationError: If no valid identifier provided
        NotFoundError: If virtual disk not found
    """
    
    if disk_id:
        try:
            virtual_disk = client.virtualization.virtual_disks.get(disk_id)
        except Exception as e:
            raise ValueError(f"Virtual disk with ID {disk_id} not found: {e}")
    elif virtual_machine_name and disk_name:
        try:
            # First find the VM
            virtual_machines = client.virtualization.virtual_machines.filter(name=virtual_machine_name)
            if not virtual_machines:
                raise ValueError(f"Virtual machine '{virtual_machine_name}' not found")
            
            vm = virtual_machines[0]
            vm_id = vm.get('id') if isinstance(vm, dict) else vm.id
            
            # Then find the disk
            disks = client.virtualization.virtual_disks.filter(
                virtual_machine_id=vm_id,
                name=disk_name
            )
            if not disks:
                raise ValueError(f"Virtual disk '{disk_name}' not found on VM '{virtual_machine_name}'")
            
            virtual_disk = disks[0]
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to find virtual disk: {e}")
    else:
        raise ValueError("Either 'disk_id' or both 'virtual_machine_name' and 'disk_name' must be provided")
    
    # Apply defensive dict/object handling
    disk_id = virtual_disk.get('id') if isinstance(virtual_disk, dict) else virtual_disk.id
    disk_name = virtual_disk.get('name') if isinstance(virtual_disk, dict) else virtual_disk.name
    disk_size_mb = virtual_disk.get('size') if isinstance(virtual_disk, dict) else getattr(virtual_disk, 'size', 0)
    disk_size_gb = disk_size_mb / 1024 if disk_size_mb else 0
    disk_description = virtual_disk.get('description') if isinstance(virtual_disk, dict) else getattr(virtual_disk, 'description', None)
    
    # Get virtual machine information - with proper resolution
    vm_obj = virtual_disk.get('virtual_machine') if isinstance(virtual_disk, dict) else getattr(virtual_disk, 'virtual_machine', None)
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
                logger.debug(f"Fetched VM name from API: {vm_name} for ID {vm_id}")
            else:
                vm_name = 'N/A'
                vm_id = 'N/A'
        except Exception as e:
            logger.warning(f"Failed to fetch VM name for ID {vm_id}: {e}")
            vm_name = 'N/A'
            vm_id = vm_id or 'N/A'
    
    return {
        "success": True,
        "message": f"Retrieved virtual disk '{disk_name}'.",
        "data": {
            "disk_id": disk_id,
            "name": disk_name,
            "size_gb": round(disk_size_gb, 2),
            "size_mb": disk_size_mb,
            "description": disk_description,
            "virtual_machine": {
                "id": vm_id,
                "name": vm_name
            },
            "url": virtual_disk.get('url') if isinstance(virtual_disk, dict) else getattr(virtual_disk, 'url', None)
        }
    }

@mcp_tool(category="virtualization")
def netbox_list_all_virtual_disks(
    client: NetBoxClient,
    virtual_machine_name: Optional[str] = None,
    size_gb_min: Optional[int] = None,
    size_gb_max: Optional[int] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get comprehensive list of all virtual disks with filtering capabilities.
    
    This tool provides bulk virtual disk discovery across the virtualization infrastructure,
    enabling efficient storage capacity analysis and disk management.
    
    Args:
        client: NetBoxClient instance (injected)
        virtual_machine_name: Filter by virtual machine name
        size_gb_min: Filter by minimum disk size in GB
        size_gb_max: Filter by maximum disk size in GB
        limit: Maximum number of disks to return (default: 100)
        
    Returns:
        Dict containing summary list of virtual disks with capacity statistics
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
    
    if size_gb_min:
        filter_params["size__gte"] = size_gb_min * 1024  # Convert GB to MB
    
    if size_gb_max:
        filter_params["size__lte"] = size_gb_max * 1024  # Convert GB to MB
    
    try:
        # Get virtual disks with applied filters
        virtual_disks = list(client.virtualization.virtual_disks.filter(**filter_params)[:limit])
        
        # Process disks with defensive dict/object handling
        disks_summary = []
        total_capacity_gb = 0
        size_distribution = {"small": 0, "medium": 0, "large": 0}  # <10GB, 10-100GB, >100GB
        
        for disk in virtual_disks:
            disk_id = disk.get('id') if isinstance(disk, dict) else disk.id
            disk_name = disk.get('name') if isinstance(disk, dict) else disk.name
            disk_size_mb = disk.get('size') if isinstance(disk, dict) else getattr(disk, 'size', 0)
            disk_size_gb = round(disk_size_mb / 1024, 2) if disk_size_mb else 0
            disk_description = disk.get('description') if isinstance(disk, dict) else getattr(disk, 'description', None)
            
            # Accumulate total capacity
            total_capacity_gb += disk_size_gb
            
            # Categorize by size
            if disk_size_gb < 10:
                size_distribution["small"] += 1
            elif disk_size_gb <= 100:
                size_distribution["medium"] += 1
            else:
                size_distribution["large"] += 1
            
            # Get VM information - with proper resolution
            vm_obj = disk.get('virtual_machine') if isinstance(disk, dict) else getattr(disk, 'virtual_machine', None)
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
            
            disks_summary.append({
                "id": disk_id,
                "name": disk_name,
                "size_gb": round(disk_size_gb, 2),
                "size_mb": disk_size_mb,
                "description": disk_description,
                "virtual_machine_name": vm_name
            })
            
    except Exception as e:
        raise ValueError(f"Failed to retrieve virtual disks: {e}")
    
    return {
        "success": True,
        "message": f"Found {len(disks_summary)} virtual disks.",
        "total_disks": len(disks_summary),
        "capacity_statistics": {
            "total_capacity_gb": round(total_capacity_gb, 2),
            "average_disk_size_gb": round(total_capacity_gb / len(disks_summary), 2) if disks_summary else 0,
            "size_distribution": size_distribution
        },
        "applied_filters": {
            "virtual_machine_name": virtual_machine_name,
            "size_gb_min": size_gb_min,
            "size_gb_max": size_gb_max,
            "limit": limit
        },
        "data": disks_summary
    }
