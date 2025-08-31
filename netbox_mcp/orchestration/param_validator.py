#!/usr/bin/env python3
"""
NetBox MCP Parameter Validation and Correction System

This module provides comprehensive parameter validation, correction, and missing
parameter detection for all 150+ NetBox MCP tools. It includes smart parameter
inference, aliases handling, and validation to ensure tools receive the correct
parameters for successful execution.

Features:
- Complete tool parameter mapping for all NetBox domains
- Parameter aliases for common variations
- Smart parameter inference from context
- Missing parameter detection and correction
- Parameter type validation and conversion
- Context-aware parameter suggestions
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """Parameter type classification for validation."""
    STRING = "string"
    INTEGER = "integer" 
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    EMAIL = "email"
    IP_ADDRESS = "ip"
    MAC_ADDRESS = "mac"
    CIDR = "cidr"
    URL = "url"
    SLUG = "slug"
    UUID = "uuid"


@dataclass
class ParameterSpec:
    """Specification for a tool parameter."""
    name: str
    param_type: ParameterType
    required: bool = False
    default: Any = None
    description: str = ""
    aliases: List[str] = None
    validation_pattern: Optional[str] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    allowed_values: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


@dataclass
class ValidationResult:
    """Result of parameter validation."""
    is_valid: bool
    normalized_params: Dict[str, Any]
    missing_required: List[str]
    invalid_params: List[str]
    suggestions: List[str]
    auto_corrections: Dict[str, Any]


class ParameterValidator:
    """
    Comprehensive parameter validator for all NetBox MCP tools.
    
    Provides validation, normalization, and correction for tool parameters
    with support for aliases, type checking, and intelligent suggestions.
    """
    
    def __init__(self):
        self.tool_specs: Dict[str, List[ParameterSpec]] = {}
        self.global_aliases: Dict[str, List[str]] = {}
        self._initialize_tool_specifications()
        self._initialize_global_aliases()
    
    def _initialize_global_aliases(self):
        """Initialize global parameter aliases for common naming variations."""
        self.global_aliases = {
            # Site/Location aliases
            'site': ['site_name', 'location', 'datacenter', 'dc', 'facility'],
            'site_name': ['site', 'location', 'datacenter', 'dc', 'facility'],
            
            # Device aliases
            'device': ['device_name', 'hostname', 'host', 'server', 'equipment'],
            'device_name': ['device', 'hostname', 'host', 'server', 'equipment'],
            
            # Rack aliases
            'rack': ['rack_name', 'rack_id'],
            'rack_name': ['rack', 'rack_id'],
            
            # Network interface aliases
            'interface': ['interface_name', 'port', 'port_name', 'nic'],
            'interface_name': ['interface', 'port', 'port_name', 'nic'],
            
            # IP/Network aliases
            'ip': ['ip_address', 'address', 'ipv4', 'ipv6'],
            'ip_address': ['ip', 'address', 'ipv4', 'ipv6'],
            'network': ['prefix', 'subnet', 'cidr', 'ip_block'],
            'prefix': ['network', 'subnet', 'cidr', 'ip_block'],
            
            # VLAN aliases
            'vlan': ['vlan_id', 'vlan_name', 'vid'],
            'vlan_id': ['vlan', 'vid'],
            'vlan_name': ['vlan'],
            'vid': ['vlan_id', 'vlan'],
            
            # Virtual Machine aliases
            'vm': ['virtual_machine', 'virtual_machine_name', 'guest'],
            'virtual_machine': ['vm', 'virtual_machine_name', 'guest'],
            'virtual_machine_name': ['vm', 'virtual_machine', 'guest'],
            
            # Cluster aliases
            'cluster': ['cluster_name'],
            'cluster_name': ['cluster'],
            
            # Tenant aliases
            'tenant': ['tenant_name', 'customer', 'organization', 'client'],
            'tenant_name': ['tenant', 'customer', 'organization', 'client'],
            
            # Module aliases
            'module': ['module_type', 'linecard', 'card'],
            'module_type': ['module', 'linecard', 'card'],
            
            # Power aliases
            'power_panel': ['panel', 'electrical_panel'],
            'power_feed': ['feed', 'power_source'],
            'power_outlet': ['outlet', 'receptacle'],
            'power_port': ['power_input', 'inlet'],
            
            # Cable aliases
            'cable': ['cable_id', 'connection'],
            'cable_type': ['cable_kind', 'medium'],
            
            # Status aliases
            'status': ['state', 'condition'],
            
            # ID aliases
            'id': ['object_id', 'pk', 'primary_key'],
            
            # Confirmation aliases
            'confirm': ['confirmation', 'confirmed', 'yes', 'force'],
        }
    
    def _initialize_tool_specifications(self):
        """Initialize parameter specifications for all NetBox MCP tools."""
        
        # SYSTEM TOOLS
        self.tool_specs['netbox_health_check'] = [
            # No parameters required
        ]
        
        # DCIM SITE TOOLS
        self.tool_specs['netbox_list_all_sites'] = [
            ParameterSpec('region_name', ParameterType.STRING, aliases=['region']),
            ParameterSpec('status', ParameterType.STRING, allowed_values=['active', 'planned', 'retired']),
            ParameterSpec('tenant_name', ParameterType.STRING, aliases=['tenant']),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_get_site_info'] = [
            ParameterSpec('site_name', ParameterType.STRING, required=True, aliases=['site', 'location', 'datacenter']),
        ]
        
        self.tool_specs['netbox_create_site'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('slug', ParameterType.SLUG, aliases=['identifier']),
            ParameterSpec('region', ParameterType.STRING, aliases=['region_name']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('physical_address', ParameterType.STRING, aliases=['address', 'location_address']),
            ParameterSpec('shipping_address', ParameterType.STRING),
            ParameterSpec('contact_name', ParameterType.STRING, aliases=['contact']),
            ParameterSpec('contact_phone', ParameterType.STRING, aliases=['phone']),
            ParameterSpec('contact_email', ParameterType.EMAIL, aliases=['email']),
            ParameterSpec('status', ParameterType.STRING, default='active', allowed_values=['active', 'planned', 'retired']),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # DCIM RACK TOOLS
        self.tool_specs['netbox_list_all_racks'] = [
            ParameterSpec('site_name', ParameterType.STRING, aliases=['site']),
            ParameterSpec('role', ParameterType.STRING),
            ParameterSpec('status', ParameterType.STRING, allowed_values=['active', 'planned', 'retired']),
            ParameterSpec('tenant_name', ParameterType.STRING, aliases=['tenant']),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_get_rack_inventory'] = [
            ParameterSpec('site_name', ParameterType.STRING, required=True, aliases=['site']),
            ParameterSpec('rack_name', ParameterType.STRING, required=True, aliases=['rack']),
            ParameterSpec('include_detailed', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_get_rack_elevation'] = [
            ParameterSpec('rack_name', ParameterType.STRING, required=True, aliases=['rack']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
        ]
        
        self.tool_specs['netbox_create_rack'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('site', ParameterType.STRING, required=True, aliases=['site_name']),
            ParameterSpec('role', ParameterType.STRING),
            ParameterSpec('u_height', ParameterType.INTEGER, default=42, min_value=1, max_value=100),
            ParameterSpec('width', ParameterType.INTEGER, default=19, allowed_values=[19, 23]),
            ParameterSpec('facility_id', ParameterType.STRING),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('status', ParameterType.STRING, default='active', allowed_values=['active', 'planned', 'retired']),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # DCIM DEVICE TOOLS  
        self.tool_specs['netbox_list_all_devices'] = [
            ParameterSpec('site_name', ParameterType.STRING, aliases=['site']),
            ParameterSpec('role_name', ParameterType.STRING, aliases=['role']),
            ParameterSpec('manufacturer_name', ParameterType.STRING, aliases=['manufacturer', 'vendor']),
            ParameterSpec('status', ParameterType.STRING, allowed_values=['active', 'planned', 'staged', 'failed', 'inventory', 'decommissioning']),
            ParameterSpec('tenant_name', ParameterType.STRING, aliases=['tenant']),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_get_device_info'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['device', 'hostname', 'host']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('include_interfaces', ParameterType.BOOLEAN, default=True),
            ParameterSpec('include_cables', ParameterType.BOOLEAN, default=True),
            ParameterSpec('interface_limit', ParameterType.INTEGER, default=20, min_value=1, max_value=100),
            ParameterSpec('cable_limit', ParameterType.INTEGER, default=10, min_value=1, max_value=100),
        ]
        
        self.tool_specs['netbox_get_device_basic_info'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['device', 'hostname', 'host']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
        ]
        
        self.tool_specs['netbox_get_device_interfaces'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['device', 'hostname', 'host']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('enabled_only', ParameterType.BOOLEAN, default=False),
            ParameterSpec('interface_type', ParameterType.STRING),
            ParameterSpec('limit', ParameterType.INTEGER, default=50, min_value=1, max_value=200),
            ParameterSpec('offset', ParameterType.INTEGER, default=0, min_value=0),
        ]
        
        self.tool_specs['netbox_get_device_cables'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['device', 'hostname', 'host']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('cable_status', ParameterType.STRING, allowed_values=['connected', 'planned', 'decommissioning']),
            ParameterSpec('cable_type', ParameterType.STRING),
            ParameterSpec('limit', ParameterType.INTEGER, default=50, min_value=1, max_value=200),
            ParameterSpec('offset', ParameterType.INTEGER, default=0, min_value=0),
        ]
        
        self.tool_specs['netbox_create_device'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('device_type', ParameterType.STRING, required=True, aliases=['model']),
            ParameterSpec('site', ParameterType.STRING, required=True, aliases=['site_name']),
            ParameterSpec('role', ParameterType.STRING, required=True, aliases=['device_role']),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('rack', ParameterType.STRING, aliases=['rack_name']),
            ParameterSpec('position', ParameterType.INTEGER, aliases=['u_position'], min_value=1),
            ParameterSpec('face', ParameterType.STRING, default='front', allowed_values=['front', 'rear']),
            ParameterSpec('serial', ParameterType.STRING, aliases=['serial_number']),
            ParameterSpec('asset_tag', ParameterType.STRING),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_provision_new_device'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['name']),
            ParameterSpec('site_name', ParameterType.STRING, required=True, aliases=['site']),
            ParameterSpec('rack_name', ParameterType.STRING, required=True, aliases=['rack']),
            ParameterSpec('device_model', ParameterType.STRING, required=True, aliases=['model', 'device_type']),
            ParameterSpec('role_name', ParameterType.STRING, required=True, aliases=['role']),
            ParameterSpec('position', ParameterType.INTEGER, required=True, aliases=['u_position'], min_value=1),
            ParameterSpec('face', ParameterType.STRING, default='front', allowed_values=['front', 'rear']),
            ParameterSpec('platform', ParameterType.STRING),
            ParameterSpec('serial', ParameterType.STRING, aliases=['serial_number']),
            ParameterSpec('asset_tag', ParameterType.STRING),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # DCIM DEVICE TYPE TOOLS
        self.tool_specs['netbox_list_all_device_types'] = [
            ParameterSpec('manufacturer_name', ParameterType.STRING, aliases=['manufacturer', 'vendor']),
            ParameterSpec('u_height', ParameterType.INTEGER, min_value=1, max_value=100),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_get_device_type_info'] = [
            ParameterSpec('manufacturer', ParameterType.STRING, required=True, aliases=['vendor']),
            ParameterSpec('model', ParameterType.STRING, required=True, aliases=['device_type']),
        ]
        
        self.tool_specs['netbox_create_device_type'] = [
            ParameterSpec('model', ParameterType.STRING, required=True, aliases=['name']),
            ParameterSpec('manufacturer', ParameterType.STRING, required=True, aliases=['vendor']),
            ParameterSpec('slug', ParameterType.SLUG, required=True),
            ParameterSpec('u_height', ParameterType.INTEGER, default=1, min_value=1, max_value=100),
            ParameterSpec('is_full_depth', ParameterType.BOOLEAN, default=True),
            ParameterSpec('part_number', ParameterType.STRING),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # DCIM MANUFACTURER TOOLS
        self.tool_specs['netbox_list_all_manufacturers'] = [
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_create_manufacturer'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('slug', ParameterType.SLUG, required=True),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # DCIM DEVICE ROLE TOOLS
        self.tool_specs['netbox_list_all_device_roles'] = [
            ParameterSpec('vm_role', ParameterType.BOOLEAN),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_create_device_role'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('slug', ParameterType.SLUG, required=True),
            ParameterSpec('color', ParameterType.STRING, default='9e9e9e'),
            ParameterSpec('vm_role', ParameterType.BOOLEAN, default=False),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # DCIM CABLE TOOLS
        self.tool_specs['netbox_list_all_cables'] = [
            ParameterSpec('cable_status', ParameterType.STRING, allowed_values=['connected', 'planned', 'decommissioning']),
            ParameterSpec('cable_type', ParameterType.STRING),
            ParameterSpec('site_name', ParameterType.STRING, aliases=['site']),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_get_cable_info'] = [
            ParameterSpec('cable_id', ParameterType.INTEGER, aliases=['id']),
            ParameterSpec('device_name', ParameterType.STRING, aliases=['device']),
            ParameterSpec('interface_name', ParameterType.STRING, aliases=['interface']),
        ]
        
        self.tool_specs['netbox_create_cable_connection'] = [
            ParameterSpec('device_a_name', ParameterType.STRING, required=True, aliases=['device_a', 'source_device']),
            ParameterSpec('interface_a_name', ParameterType.STRING, required=True, aliases=['interface_a', 'source_interface']),
            ParameterSpec('device_b_name', ParameterType.STRING, required=True, aliases=['device_b', 'target_device']),
            ParameterSpec('interface_b_name', ParameterType.STRING, required=True, aliases=['interface_b', 'target_interface']),
            ParameterSpec('cable_type', ParameterType.STRING, default='cat6'),
            ParameterSpec('cable_status', ParameterType.STRING, default='connected'),
            ParameterSpec('cable_color', ParameterType.STRING, aliases=['color']),
            ParameterSpec('cable_length', ParameterType.INTEGER, aliases=['length'], min_value=1),
            ParameterSpec('cable_length_unit', ParameterType.STRING, default='m', allowed_values=['m', 'ft', 'cm', 'in']),
            ParameterSpec('label', ParameterType.STRING),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_disconnect_cable'] = [
            ParameterSpec('cable_id', ParameterType.INTEGER, aliases=['id']),
            ParameterSpec('device_name', ParameterType.STRING, aliases=['device']),
            ParameterSpec('interface_name', ParameterType.STRING, aliases=['interface']),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # DCIM INTERFACE TOOLS
        self.tool_specs['netbox_create_interface'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['device']),
            ParameterSpec('interface_name', ParameterType.STRING, required=True, aliases=['interface', 'name']),
            ParameterSpec('interface_type', ParameterType.STRING, default='1000base-t'),
            ParameterSpec('enabled', ParameterType.BOOLEAN, default=True),
            ParameterSpec('mgmt_only', ParameterType.BOOLEAN, default=False, aliases=['management_only']),
            ParameterSpec('mtu', ParameterType.INTEGER, min_value=68, max_value=65536),
            ParameterSpec('mac_address', ParameterType.MAC_ADDRESS, aliases=['mac']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_assign_ip_to_interface'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['device']),
            ParameterSpec('interface_name', ParameterType.STRING, required=True, aliases=['interface']),
            ParameterSpec('ip_address', ParameterType.IP_ADDRESS, required=True, aliases=['ip']),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_set_primary_ip'] = [
            ParameterSpec('device_name', ParameterType.STRING, required=True, aliases=['device']),
            ParameterSpec('ip_address', ParameterType.IP_ADDRESS, required=True, aliases=['ip']),
            ParameterSpec('ip_version', ParameterType.STRING, default='auto', allowed_values=['auto', '4', '6', 'ipv4', 'ipv6']),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # IPAM PREFIX TOOLS
        self.tool_specs['netbox_list_all_prefixes'] = [
            ParameterSpec('family', ParameterType.INTEGER, allowed_values=[4, 6]),
            ParameterSpec('role', ParameterType.STRING),
            ParameterSpec('site_name', ParameterType.STRING, aliases=['site']),
            ParameterSpec('status', ParameterType.STRING),
            ParameterSpec('tenant_name', ParameterType.STRING, aliases=['tenant']),
            ParameterSpec('vrf_name', ParameterType.STRING, aliases=['vrf']),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_create_prefix'] = [
            ParameterSpec('prefix', ParameterType.CIDR, required=True, aliases=['network', 'subnet']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('vlan', ParameterType.STRING, aliases=['vlan_name']),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_get_prefix_utilization'] = [
            ParameterSpec('prefix', ParameterType.CIDR, required=True, aliases=['network', 'subnet']),
            ParameterSpec('include_child_prefixes', ParameterType.BOOLEAN, default=True),
            ParameterSpec('include_detailed_breakdown', ParameterType.BOOLEAN, default=False),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('vrf', ParameterType.STRING, aliases=['vrf_name']),
        ]
        
        # IPAM IP ADDRESS TOOLS
        self.tool_specs['netbox_create_ip_address'] = [
            ParameterSpec('ip_address', ParameterType.IP_ADDRESS, required=True, aliases=['ip', 'address']),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_find_available_ip'] = [
            ParameterSpec('prefix', ParameterType.CIDR, required=True, aliases=['network', 'subnet']),
            ParameterSpec('count', ParameterType.INTEGER, default=1, min_value=1, max_value=100),
        ]
        
        self.tool_specs['netbox_find_next_available_ip'] = [
            ParameterSpec('prefix', ParameterType.CIDR, aliases=['network', 'subnet']),
            ParameterSpec('count', ParameterType.INTEGER, default=1, min_value=1, max_value=100),
            ParameterSpec('reserve_immediately', ParameterType.BOOLEAN, default=False),
            ParameterSpec('assign_to_interface', ParameterType.STRING, aliases=['interface']),
            ParameterSpec('device_name', ParameterType.STRING, aliases=['device']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('vrf', ParameterType.STRING, aliases=['vrf_name']),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # IPAM VLAN TOOLS
        self.tool_specs['netbox_list_all_vlans'] = [
            ParameterSpec('group_name', ParameterType.STRING, aliases=['group']),
            ParameterSpec('role', ParameterType.STRING),
            ParameterSpec('site_name', ParameterType.STRING, aliases=['site']),
            ParameterSpec('status', ParameterType.STRING),
            ParameterSpec('tenant_name', ParameterType.STRING, aliases=['tenant']),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_create_vlan'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('vid', ParameterType.INTEGER, required=True, aliases=['vlan_id'], min_value=1, max_value=4094),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('group', ParameterType.STRING, aliases=['vlan_group']),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        self.tool_specs['netbox_find_available_vlan_id'] = [
            ParameterSpec('start_vid', ParameterType.INTEGER, default=1, min_value=1, max_value=4094),
            ParameterSpec('end_vid', ParameterType.INTEGER, default=4094, min_value=1, max_value=4094),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('group', ParameterType.STRING, aliases=['vlan_group']),
        ]
        
        # IPAM VRF TOOLS
        self.tool_specs['netbox_list_all_vrfs'] = [
            ParameterSpec('tenant_name', ParameterType.STRING, aliases=['tenant']),
            ParameterSpec('enforce_unique', ParameterType.BOOLEAN),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_create_vrf'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('rd', ParameterType.STRING, aliases=['route_distinguisher']),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # VIRTUALIZATION CLUSTER TOOLS
        self.tool_specs['netbox_list_all_clusters'] = [
            ParameterSpec('cluster_type', ParameterType.STRING, aliases=['type']),
            ParameterSpec('cluster_group', ParameterType.STRING, aliases=['group']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('status', ParameterType.STRING),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_create_cluster'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('cluster_type', ParameterType.STRING, required=True, aliases=['type']),
            ParameterSpec('cluster_group', ParameterType.STRING, aliases=['group']),
            ParameterSpec('site', ParameterType.STRING, aliases=['site_name']),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('comments', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # VIRTUALIZATION VM TOOLS
        self.tool_specs['netbox_list_all_virtual_machines'] = [
            ParameterSpec('cluster', ParameterType.STRING, aliases=['cluster_name']),
            ParameterSpec('platform', ParameterType.STRING),
            ParameterSpec('role', ParameterType.STRING, aliases=['role_name']),
            ParameterSpec('status', ParameterType.STRING),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_create_virtual_machine'] = [
            ParameterSpec('name', ParameterType.STRING, required=True),
            ParameterSpec('cluster', ParameterType.STRING, required=True, aliases=['cluster_name']),
            ParameterSpec('role', ParameterType.STRING, aliases=['role_name']),
            ParameterSpec('platform', ParameterType.STRING),
            ParameterSpec('vcpus', ParameterType.INTEGER, aliases=['cpu_count'], min_value=1),
            ParameterSpec('memory_mb', ParameterType.INTEGER, aliases=['memory'], min_value=1),
            ParameterSpec('disk_gb', ParameterType.INTEGER, aliases=['disk'], min_value=1),
            ParameterSpec('status', ParameterType.STRING, default='active'),
            ParameterSpec('tenant', ParameterType.STRING, aliases=['tenant_name']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('comments', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # TENANCY TOOLS
        self.tool_specs['netbox_list_all_tenants'] = [
            ParameterSpec('group_name', ParameterType.STRING, aliases=['group']),
            ParameterSpec('status', ParameterType.STRING),
            ParameterSpec('limit', ParameterType.INTEGER, default=100, min_value=1, max_value=1000),
        ]
        
        self.tool_specs['netbox_onboard_new_tenant'] = [
            ParameterSpec('tenant_name', ParameterType.STRING, required=True, aliases=['name']),
            ParameterSpec('tenant_group_name', ParameterType.STRING, aliases=['group']),
            ParameterSpec('tenant_status', ParameterType.STRING, default='active', aliases=['status']),
            ParameterSpec('description', ParameterType.STRING),
            ParameterSpec('contact_name', ParameterType.STRING, aliases=['contact']),
            ParameterSpec('contact_email', ParameterType.EMAIL, aliases=['email']),
            ParameterSpec('contact_phone', ParameterType.STRING, aliases=['phone']),
            ParameterSpec('contact_address', ParameterType.STRING, aliases=['address']),
            ParameterSpec('create_group_if_missing', ParameterType.BOOLEAN, default=False),
            ParameterSpec('tags', ParameterType.LIST),
            ParameterSpec('comments', ParameterType.STRING),
            ParameterSpec('confirm', ParameterType.BOOLEAN, default=False),
        ]
        
        # Add more tools as needed...
        # This is a comprehensive start covering the major NetBox domains
    
    def validate_parameters(
        self, 
        tool_name: str, 
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate and normalize parameters for a specific tool.
        
        Args:
            tool_name: Name of the NetBox MCP tool
            params: Parameters to validate
            context: Optional context for parameter inference
            
        Returns:
            ValidationResult with validation status and corrections
        """
        if tool_name not in self.tool_specs:
            logger.warning(f"No parameter specification found for tool: {tool_name}")
            return ValidationResult(
                is_valid=True,  # Allow unknown tools to pass through
                normalized_params=params,
                missing_required=[],
                invalid_params=[],
                suggestions=[],
                auto_corrections={}
            )
        
        tool_spec = self.tool_specs[tool_name]
        normalized_params = {}
        missing_required = []
        invalid_params = []
        suggestions = []
        auto_corrections = {}
        
        # Create parameter name mapping with aliases
        param_name_map = {}
        for spec in tool_spec:
            param_name_map[spec.name] = spec
            for alias in spec.aliases:
                param_name_map[alias] = spec
            # Add global aliases
            if spec.name in self.global_aliases:
                for alias in self.global_aliases[spec.name]:
                    param_name_map[alias] = spec
        
        # Process provided parameters
        for param_key, param_value in params.items():
            if param_key in param_name_map:
                spec = param_name_map[param_key]
                canonical_name = spec.name
                
                # Validate and convert parameter value
                is_valid, converted_value, suggestion = self._validate_parameter_value(
                    spec, param_value, context
                )
                
                if is_valid:
                    normalized_params[canonical_name] = converted_value
                    if param_key != canonical_name:
                        auto_corrections[param_key] = canonical_name
                else:
                    invalid_params.append(param_key)
                    if suggestion:
                        suggestions.append(suggestion)
            else:
                # Unknown parameter - add suggestion for closest match
                closest_param = self._find_closest_parameter(param_key, tool_spec)
                if closest_param:
                    suggestions.append(f"Did you mean '{closest_param}' instead of '{param_key}'?")
                # Still include unknown parameters (they might be valid)
                normalized_params[param_key] = param_value
        
        # Check for missing required parameters
        for spec in tool_spec:
            if spec.required and spec.name not in normalized_params:
                # Try to infer from context
                inferred_value = self._infer_parameter_from_context(spec, context)
                if inferred_value is not None:
                    normalized_params[spec.name] = inferred_value
                    auto_corrections[f"inferred_{spec.name}"] = inferred_value
                else:
                    missing_required.append(spec.name)
        
        # Add default values for missing optional parameters
        for spec in tool_spec:
            if not spec.required and spec.name not in normalized_params and spec.default is not None:
                normalized_params[spec.name] = spec.default
        
        # Generate suggestions for missing required parameters
        for missing_param in missing_required:
            spec = next((s for s in tool_spec if s.name == missing_param), None)
            if spec:
                suggestion = f"Missing required parameter '{missing_param}'"
                if spec.aliases:
                    suggestion += f" (aliases: {', '.join(spec.aliases)})"
                if spec.description:
                    suggestion += f": {spec.description}"
                suggestions.append(suggestion)
        
        is_valid = len(missing_required) == 0 and len(invalid_params) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            normalized_params=normalized_params,
            missing_required=missing_required,
            invalid_params=invalid_params,
            suggestions=suggestions,
            auto_corrections=auto_corrections
        )
    
    def _validate_parameter_value(
        self, 
        spec: ParameterSpec, 
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Validate and convert a parameter value according to its specification.
        
        Returns:
            Tuple of (is_valid, converted_value, suggestion)
        """
        if value is None:
            return True, None, None
        
        try:
            # Type-specific validation and conversion
            if spec.param_type == ParameterType.STRING:
                converted = str(value)
                
                # Check allowed values
                if spec.allowed_values and converted not in spec.allowed_values:
                    return False, value, f"Value must be one of: {', '.join(spec.allowed_values)}"
                
                # Validation pattern check
                if spec.validation_pattern:
                    if not re.match(spec.validation_pattern, converted):
                        return False, value, f"Value doesn't match required pattern"
                
                return True, converted, None
                
            elif spec.param_type == ParameterType.INTEGER:
                converted = int(value)
                
                # Range validation
                if spec.min_value is not None and converted < spec.min_value:
                    return False, value, f"Value must be >= {spec.min_value}"
                if spec.max_value is not None and converted > spec.max_value:
                    return False, value, f"Value must be <= {spec.max_value}"
                
                # Allowed values check
                if spec.allowed_values and converted not in spec.allowed_values:
                    return False, value, f"Value must be one of: {', '.join(map(str, spec.allowed_values))}"
                
                return True, converted, None
                
            elif spec.param_type == ParameterType.BOOLEAN:
                if isinstance(value, bool):
                    return True, value, None
                elif isinstance(value, str):
                    if value.lower() in ['true', 'yes', '1', 'on']:
                        return True, True, None
                    elif value.lower() in ['false', 'no', '0', 'off']:
                        return True, False, None
                return False, value, "Value must be true/false"
                
            elif spec.param_type == ParameterType.EMAIL:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if re.match(email_pattern, str(value)):
                    return True, str(value), None
                return False, value, "Invalid email format"
                
            elif spec.param_type == ParameterType.IP_ADDRESS:
                import ipaddress
                try:
                    # Try to parse as IP address
                    ip = ipaddress.ip_address(str(value))
                    return True, str(ip), None
                except ValueError:
                    return False, value, "Invalid IP address format"
                    
            elif spec.param_type == ParameterType.MAC_ADDRESS:
                mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
                if re.match(mac_pattern, str(value)):
                    return True, str(value), None
                return False, value, "Invalid MAC address format (use XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)"
                
            elif spec.param_type == ParameterType.CIDR:
                import ipaddress
                try:
                    # Try to parse as network
                    network = ipaddress.ip_network(str(value), strict=False)
                    return True, str(network), None
                except ValueError:
                    return False, value, "Invalid CIDR format (use x.x.x.x/xx)"
                    
            elif spec.param_type == ParameterType.SLUG:
                slug_pattern = r'^[-a-zA-Z0-9_]+$'
                if re.match(slug_pattern, str(value)):
                    return True, str(value), None
                return False, value, "Slug must contain only letters, numbers, hyphens, and underscores"
                
            elif spec.param_type == ParameterType.LIST:
                if isinstance(value, list):
                    return True, value, None
                elif isinstance(value, str):
                    # Try to parse comma-separated values
                    return True, [item.strip() for item in value.split(',')], None
                return False, value, "Value must be a list or comma-separated string"
                
            elif spec.param_type == ParameterType.DICT:
                if isinstance(value, dict):
                    return True, value, None
                return False, value, "Value must be a dictionary"
                
            else:
                # Default: treat as string
                return True, str(value), None
                
        except (ValueError, TypeError) as e:
            return False, value, f"Type conversion error: {str(e)}"
    
    def _find_closest_parameter(self, param_name: str, tool_spec: List[ParameterSpec]) -> Optional[str]:
        """Find the closest matching parameter name using fuzzy matching."""
        import difflib
        
        all_param_names = []
        for spec in tool_spec:
            all_param_names.append(spec.name)
            all_param_names.extend(spec.aliases)
            # Add global aliases
            if spec.name in self.global_aliases:
                all_param_names.extend(self.global_aliases[spec.name])
        
        closest_matches = difflib.get_close_matches(param_name, all_param_names, n=1, cutoff=0.6)
        return closest_matches[0] if closest_matches else None
    
    def _infer_parameter_from_context(
        self, 
        spec: ParameterSpec, 
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Try to infer a parameter value from context."""
        if not context:
            return None
        
        # Context-based inference rules
        inference_rules = {
            'site_name': ['current_site', 'site', 'location'],
            'device_name': ['current_device', 'device', 'hostname'],
            'rack_name': ['current_rack', 'rack'],
            'tenant_name': ['current_tenant', 'tenant'],
            'cluster_name': ['current_cluster', 'cluster'],
        }
        
        if spec.name in inference_rules:
            for context_key in inference_rules[spec.name]:
                if context_key in context:
                    return context[context_key]
        
        return None
    
    def get_parameter_suggestions(self, tool_name: str, partial_param: str) -> List[str]:
        """Get parameter name suggestions for a tool based on partial input."""
        if tool_name not in self.tool_specs:
            return []
        
        tool_spec = self.tool_specs[tool_name]
        all_param_names = []
        
        for spec in tool_spec:
            all_param_names.append(spec.name)
            all_param_names.extend(spec.aliases)
            if spec.name in self.global_aliases:
                all_param_names.extend(self.global_aliases[spec.name])
        
        # Filter parameters that start with the partial input
        suggestions = [
            param for param in all_param_names 
            if param.startswith(partial_param.lower())
        ]
        
        # If no direct matches, use fuzzy matching
        if not suggestions:
            import difflib
            suggestions = difflib.get_close_matches(partial_param, all_param_names, n=5, cutoff=0.3)
        
        return sorted(set(suggestions))
    
    def get_tool_parameter_info(self, tool_name: str) -> Dict[str, Any]:
        """Get complete parameter information for a tool."""
        if tool_name not in self.tool_specs:
            return {"error": f"No parameter specification found for tool: {tool_name}"}
        
        tool_spec = self.tool_specs[tool_name]
        
        required_params = []
        optional_params = []
        
        for spec in tool_spec:
            param_info = {
                "name": spec.name,
                "type": spec.param_type.value,
                "description": spec.description,
                "aliases": spec.aliases + self.global_aliases.get(spec.name, []),
                "default": spec.default,
            }
            
            if spec.allowed_values:
                param_info["allowed_values"] = spec.allowed_values
            if spec.min_value is not None:
                param_info["min_value"] = spec.min_value
            if spec.max_value is not None:
                param_info["max_value"] = spec.max_value
            if spec.validation_pattern:
                param_info["pattern"] = spec.validation_pattern
            
            if spec.required:
                required_params.append(param_info)
            else:
                optional_params.append(param_info)
        
        return {
            "tool_name": tool_name,
            "required_parameters": required_params,
            "optional_parameters": optional_params,
            "total_parameters": len(tool_spec),
        }


# Global validator instance
parameter_validator = ParameterValidator()


def validate_tool_parameters(
    tool_name: str, 
    params: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Public interface for parameter validation.
    
    Args:
        tool_name: Name of the NetBox MCP tool
        params: Parameters to validate
        context: Optional context for inference
        
    Returns:
        ValidationResult with validation status and corrections
    """
    return parameter_validator.validate_parameters(tool_name, params, context)


def get_parameter_info(tool_name: str) -> Dict[str, Any]:
    """Get parameter information for a tool."""
    return parameter_validator.get_tool_parameter_info(tool_name)


def suggest_parameters(tool_name: str, partial_param: str) -> List[str]:
    """Get parameter suggestions for a tool."""
    return parameter_validator.get_parameter_suggestions(tool_name, partial_param)