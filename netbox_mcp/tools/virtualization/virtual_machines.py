#!/usr/bin/env python3
"""
Virtual Machine Management Tools

High-level tools for managing NetBox virtual machines with comprehensive
VM lifecycle management, resource allocation, and provisioning automation.
"""

from typing import Dict, Optional, Any, List
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

@mcp_tool(category="virtualization")
def netbox_get_virtual_machine_info(
    client: NetBoxClient,
    name: Optional[str] = None,
    vm_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific virtual machine.
    
    Args:
        client: NetBoxClient instance (injected)
        name: VM name to retrieve
        vm_id: VM ID to retrieve
        
    Returns:
        Dict containing detailed VM information including interfaces and resources
        
    Raises:
        ValidationError: If no valid identifier provided
        NotFoundError: If VM not found
    """
    
    if not any([name, vm_id]):
        raise ValueError("Either 'name' or 'vm_id' must be provided")
    
    try:
        if vm_id:
            vm = client.virtualization.virtual_machines.get(vm_id)
        else:  # name
            vms = client.virtualization.virtual_machines.filter(name=name)
            if not vms:
                raise ValueError(f"Virtual machine '{name}' not found")
            vm = vms[0]
        
        # Apply defensive dict/object handling
        vm_id = vm.get('id') if isinstance(vm, dict) else vm.id
        vm_name = vm.get('name') if isinstance(vm, dict) else vm.name
        vm_status = vm.get('status') if isinstance(vm, dict) else getattr(vm, 'status', None)
        vm_vcpus = vm.get('vcpus') if isinstance(vm, dict) else getattr(vm, 'vcpus', None)
        vm_memory = vm.get('memory') if isinstance(vm, dict) else getattr(vm, 'memory', None)
        vm_disk = vm.get('disk') if isinstance(vm, dict) else getattr(vm, 'disk', None)
        vm_description = vm.get('description') if isinstance(vm, dict) else getattr(vm, 'description', None)
        vm_comments = vm.get('comments') if isinstance(vm, dict) else getattr(vm, 'comments', None)
        
        # Get cluster information
        cluster_obj = vm.get('cluster') if isinstance(vm, dict) else getattr(vm, 'cluster', None)
        if isinstance(cluster_obj, dict):
            cluster_name = cluster_obj.get('name', 'N/A')
            cluster_id = cluster_obj.get('id', 'N/A')
        else:
            cluster_name = str(cluster_obj) if cluster_obj else 'N/A'
            cluster_id = getattr(cluster_obj, 'id', 'N/A') if cluster_obj else 'N/A'
        
        # Get role information
        role_obj = vm.get('role') if isinstance(vm, dict) else getattr(vm, 'role', None)
        if isinstance(role_obj, dict):
            role_name = role_obj.get('name', 'N/A')
        else:
            role_name = str(role_obj) if role_obj else 'N/A'
        
        # Get tenant information
        tenant_obj = vm.get('tenant') if isinstance(vm, dict) else getattr(vm, 'tenant', None)
        if isinstance(tenant_obj, dict):
            tenant_name = tenant_obj.get('name', 'N/A')
        else:
            tenant_name = str(tenant_obj) if tenant_obj else 'N/A'
        
        # Get platform information
        platform_obj = vm.get('platform') if isinstance(vm, dict) else getattr(vm, 'platform', None)
        if isinstance(platform_obj, dict):
            platform_name = platform_obj.get('name', 'N/A')
        else:
            platform_name = str(platform_obj) if platform_obj else 'N/A'
        
        # Get interfaces for this VM
        try:
            vm_interfaces = list(client.virtualization.interfaces.filter(virtual_machine_id=vm_id))
            interface_count = len(vm_interfaces)
            
            interfaces_summary = []
            for interface in vm_interfaces[:5]:  # Show first 5
                iface_name = interface.get('name') if isinstance(interface, dict) else getattr(interface, 'name', 'N/A')
                iface_enabled = interface.get('enabled') if isinstance(interface, dict) else getattr(interface, 'enabled', False)
                iface_mac = interface.get('mac_address') if isinstance(interface, dict) else getattr(interface, 'mac_address', None)
                
                interfaces_summary.append({
                    "name": iface_name,
                    "enabled": iface_enabled,
                    "mac_address": iface_mac
                })
                
        except Exception:
            interface_count = 0
            interfaces_summary = []
        
        # Get virtual disks for this VM
        try:
            vm_disks = list(client.virtualization.virtual_disks.filter(virtual_machine_id=vm_id))
            disk_count = len(vm_disks)
            total_disk_gb = 0
            
            for disk in vm_disks:
                disk_size_mb = disk.get('size', 0) if isinstance(disk, dict) else getattr(disk, 'size', 0)
                total_disk_gb += round(disk_size_mb / 1024, 2) if disk_size_mb else 0
                
        except Exception:
            disk_count = 0
            total_disk_gb = 0
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to retrieve virtual machine: {e}")
    
    return {
        "success": True,
        "message": f"Retrieved virtual machine '{vm_name}'.",
        "data": {
            "vm_id": vm_id,
            "name": vm_name,
            "status": vm_status,
            "cluster": {
                "id": cluster_id,
                "name": cluster_name
            },
            "resources": {
                "vcpus": vm_vcpus,
                "memory_mb": vm_memory,
                "memory_gb": round(vm_memory / 1024, 2) if vm_memory else None,
                "disk_gb": round(vm_disk / 1024, 2) if vm_disk else None,
                "total_virtual_disks_gb": round(total_disk_gb, 2)
            },
            "role": role_name,
            "tenant": tenant_name,
            "platform": platform_name,
            "description": vm_description,
            "comments": vm_comments,
            "interfaces": {
                "count": interface_count,
                "summary": interfaces_summary
            },
            "virtual_disks": {
                "count": disk_count,
                "total_gb": round(total_disk_gb, 2)
            },
            "url": vm.get('url') if isinstance(vm, dict) else getattr(vm, 'url', None)
        }
    }

@mcp_tool(category="virtualization")
def netbox_list_all_virtual_machines(
    client: NetBoxClient,
    cluster: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    tenant: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get comprehensive list of all virtual machines with filtering capabilities.
    
    This tool provides bulk VM discovery across the virtualization infrastructure,
    enabling efficient resource management and capacity planning.
    
    Args:
        client: NetBoxClient instance (injected)
        cluster: Filter by cluster name
        status: Filter by status (active, offline, planned, etc.)
        role: Filter by role name
        tenant: Filter by tenant name
        platform: Filter by platform name
        limit: Maximum number of VMs to return (default: 100)
        
    Returns:
        Dict containing summary list of VMs with resource statistics
    """
    
    # Build filter parameters
    filter_params = {}
    
    if cluster:
        try:
            clusters = client.virtualization.clusters.filter(name=cluster)
            if not clusters:
                raise ValueError(f"Cluster '{cluster}' not found")
            cluster_obj = clusters[0]
            cluster_id = cluster_obj.get('id') if isinstance(cluster_obj, dict) else cluster_obj.id
            filter_params["cluster_id"] = cluster_id
        except Exception as e:
            raise ValueError(f"Failed to find cluster: {e}")
    
    if status:
        filter_params["status"] = status
    
    if role:
        try:
            roles = client.dcim.device_roles.filter(name=role)
            if not roles:
                raise ValueError(f"Role '{role}' not found")
            role_obj = roles[0]
            role_id = role_obj.get('id') if isinstance(role_obj, dict) else role_obj.id
            filter_params["role_id"] = role_id
        except Exception as e:
            raise ValueError(f"Failed to find role: {e}")
    
    if tenant:
        try:
            tenants = client.tenancy.tenants.filter(name=tenant)
            if not tenants:
                raise ValueError(f"Tenant '{tenant}' not found")
            tenant_obj = tenants[0]
            tenant_id = tenant_obj.get('id') if isinstance(tenant_obj, dict) else tenant_obj.id
            filter_params["tenant_id"] = tenant_id
        except Exception as e:
            raise ValueError(f"Failed to find tenant: {e}")
    
    if platform:
        try:
            platforms = client.dcim.platforms.filter(name=platform)
            if not platforms:
                raise ValueError(f"Platform '{platform}' not found")
            platform_obj = platforms[0]
            platform_id = platform_obj.get('id') if isinstance(platform_obj, dict) else platform_obj.id
            filter_params["platform_id"] = platform_id
        except Exception as e:
            raise ValueError(f"Failed to find platform: {e}")
    
    try:
        # Get VMs with applied filters
        virtual_machines = list(client.virtualization.virtual_machines.filter(**filter_params)[:limit])
        
        # Process VMs with defensive dict/object handling
        vms_summary = []
        total_vcpus = 0
        total_memory_gb = 0
        total_disk_gb = 0
        status_counts = {}
        cluster_counts = {}
        
        for vm in virtual_machines:
            vm_id = vm.get('id') if isinstance(vm, dict) else vm.id
            vm_name = vm.get('name') if isinstance(vm, dict) else vm.name
            vm_status = vm.get('status') if isinstance(vm, dict) else getattr(vm, 'status', None)
            vm_vcpus = vm.get('vcpus') if isinstance(vm, dict) else getattr(vm, 'vcpus', 0)
            vm_memory = vm.get('memory') if isinstance(vm, dict) else getattr(vm, 'memory', 0)
            vm_disk = vm.get('disk') if isinstance(vm, dict) else getattr(vm, 'disk', 0)
            
            # Count by status
            if isinstance(vm_status, dict):
                status_value = vm_status.get('value', 'unknown')
            else:
                status_value = str(vm_status) if vm_status else 'unknown'
            status_counts[status_value] = status_counts.get(status_value, 0) + 1
            
            # Get cluster, role, tenant, platform names
            cluster_obj = vm.get('cluster') if isinstance(vm, dict) else getattr(vm, 'cluster', None)
            if isinstance(cluster_obj, dict):
                cluster_name = cluster_obj.get('name', 'N/A')
            else:
                cluster_name = str(cluster_obj) if cluster_obj else 'N/A'
            
            # Count by cluster
            cluster_counts[cluster_name] = cluster_counts.get(cluster_name, 0) + 1
            
            role_obj = vm.get('role') if isinstance(vm, dict) else getattr(vm, 'role', None)
            if isinstance(role_obj, dict):
                role_name = role_obj.get('name', 'N/A')
            else:
                role_name = str(role_obj) if role_obj else 'N/A'
            
            tenant_obj = vm.get('tenant') if isinstance(vm, dict) else getattr(vm, 'tenant', None)
            if isinstance(tenant_obj, dict):
                tenant_name = tenant_obj.get('name', 'N/A')
            else:
                tenant_name = str(tenant_obj) if tenant_obj else 'N/A'
            
            platform_obj = vm.get('platform') if isinstance(vm, dict) else getattr(vm, 'platform', None)
            if isinstance(platform_obj, dict):
                platform_name = platform_obj.get('name', 'N/A')
            else:
                platform_name = str(platform_obj) if platform_obj else 'N/A'
            
            # Accumulate resource totals
            total_vcpus += vm_vcpus or 0
            total_memory_gb += round(vm_memory / 1024, 2) if vm_memory else 0
            total_disk_gb += round(vm_disk / 1024, 2) if vm_disk else 0
            
            vms_summary.append({
                "id": vm_id,
                "name": vm_name,
                "status": status_value,
                "cluster": cluster_name,
                "role": role_name,
                "tenant": tenant_name,
                "platform": platform_name,
                "resources": {
                    "vcpus": vm_vcpus,
                    "memory_mb": vm_memory,
                    "memory_gb": round(vm_memory / 1024, 2) if vm_memory else 0,
                    "disk_gb": round(vm_disk / 1024, 2) if vm_disk else 0
                }
            })
            
    except Exception as e:
        raise ValueError(f"Failed to retrieve virtual machines: {e}")
    
    return {
        "success": True,
        "message": f"Found {len(vms_summary)} virtual machines.",
        "total_vms": len(vms_summary),
        "resource_totals": {
            "total_vcpus": total_vcpus,
            "total_memory_gb": round(total_memory_gb, 2),
            "total_disk_gb": round(total_disk_gb, 2),
            "average_vcpus": round(total_vcpus / len(vms_summary), 1) if vms_summary else 0,
            "average_memory_gb": round(total_memory_gb / len(vms_summary), 2) if vms_summary else 0,
            "average_disk_gb": round(total_disk_gb / len(vms_summary), 2) if vms_summary else 0
        },
        "distribution": {
            "status_counts": status_counts,
            "cluster_counts": cluster_counts
        },
        "applied_filters": {
            "cluster": cluster,
            "status": status,
            "role": role,
            "tenant": tenant,
            "platform": platform,
            "limit": limit
        },
        "data": vms_summary
    }
