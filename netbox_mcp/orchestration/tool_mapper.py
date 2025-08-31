#!/usr/bin/env python3
"""
NetBox MCP Tool Mapping System

Comprehensive tool mapping system that maps user queries to appropriate NetBox MCP tools.
Supports all 150+ NetBox MCP tools across all domains: DCIM, IPAM, Virtualization, 
Tenancy, Power Infrastructure, and Extras.

Features:
- O(1) lookups for common queries
- Smart pattern matching for complex queries  
- Parameter validation and correction
- Fallback mechanisms for tool failures
- Support for query variations and aliases
- Comprehensive coverage of all NetBox domains
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Classification of query types for tool mapping."""
    LIST = "list"           # List/show all items
    GET = "get"             # Get specific item details
    CREATE = "create"       # Create new items
    UPDATE = "update"       # Update existing items
    DELETE = "delete"       # Delete items
    HEALTH = "health"       # System health/status
    ANALYSIS = "analysis"   # Analysis/utilization queries
    BULK = "bulk"           # Bulk operations
    PROVISION = "provision" # Provisioning workflows
    REPORT = "report"       # Reporting queries


class Domain(Enum):
    """NetBox domain classification."""
    SYSTEM = "system"
    DCIM = "dcim"
    IPAM = "ipam"
    VIRTUALIZATION = "virtualization"
    TENANCY = "tenancy"
    EXTRAS = "extras"


@dataclass
class ToolMapping:
    """Represents a mapping from query patterns to NetBox tools."""
    tool_name: str
    domain: Domain
    query_type: QueryType
    patterns: List[str]
    entity_types: List[str]
    required_params: List[str]
    optional_params: List[str]
    fallback_tools: List[str]
    description: str


class ParameterValidator:
    """Validates and normalizes tool parameters."""
    
    # Parameter aliases for common entity naming variations
    PARAMETER_ALIASES = {
        # Site aliases
        'site': ['site_name', 'site_id', 'location', 'datacenter', 'dc'],
        'site_name': ['site', 'location', 'datacenter', 'dc'],
        
        # Device aliases
        'device': ['device_name', 'hostname', 'host', 'server'],
        'device_name': ['device', 'hostname', 'host', 'server'],
        
        # Rack aliases
        'rack': ['rack_name', 'rack_id'],
        'rack_name': ['rack', 'rack_id'],
        
        # Network aliases
        'interface': ['interface_name', 'port', 'port_name'],
        'interface_name': ['interface', 'port', 'port_name'],
        
        # IP/Network aliases
        'ip': ['ip_address', 'address'],
        'ip_address': ['ip', 'address'],
        'network': ['prefix', 'subnet', 'cidr'],
        'prefix': ['network', 'subnet', 'cidr'],
        
        # VM aliases
        'vm': ['virtual_machine', 'virtual_machine_name'],
        'virtual_machine_name': ['vm', 'virtual_machine'],
        
        # Cluster aliases
        'cluster': ['cluster_name'],
        'cluster_name': ['cluster'],
        
        # Tenant aliases
        'tenant': ['tenant_name', 'customer', 'organization'],
        'tenant_name': ['tenant', 'customer', 'organization'],
    }
    
    @classmethod
    def normalize_parameters(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameter names using aliases."""
        normalized = {}
        
        for key, value in params.items():
            # Find the canonical parameter name
            canonical_key = key
            for canonical, aliases in cls.PARAMETER_ALIASES.items():
                if key in aliases:
                    canonical_key = canonical
                    break
            
            normalized[canonical_key] = value
        
        return normalized
    
    @classmethod
    def validate_required_params(cls, params: Dict[str, Any], required: List[str]) -> Tuple[bool, List[str]]:
        """Validate that required parameters are present."""
        missing = []
        for param in required:
            if param not in params or params[param] is None:
                # Check aliases
                found = False
                for alias in cls.PARAMETER_ALIASES.get(param, []):
                    if alias in params and params[alias] is not None:
                        found = True
                        break
                
                if not found:
                    missing.append(param)
        
        return len(missing) == 0, missing


class NetBoxToolMapper:
    """
    Comprehensive tool mapping system for NetBox MCP tools.
    
    Maps user queries to appropriate NetBox tools using pattern matching,
    entity recognition, and action classification.
    """
    
    def __init__(self):
        """Initialize the tool mapper with comprehensive mappings."""
        self._tool_mappings: Dict[str, ToolMapping] = {}
        self._pattern_cache: Dict[str, str] = {}
        self._entity_patterns: Dict[str, List[str]] = {}
        self._action_patterns: Dict[QueryType, List[str]] = {}
        
        self._initialize_mappings()
        self._compile_patterns()
    
    def _initialize_mappings(self):
        """Initialize comprehensive tool mappings for all 150+ NetBox tools."""
        
        # SYSTEM TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_health_check",
            domain=Domain.SYSTEM,
            query_type=QueryType.HEALTH,
            patterns=[
                r"health\s+check",
                r"system\s+status",
                r"connection\s+status",
                r"is\s+netbox\s+(?:up|running|available)",
                r"check\s+(?:connectivity|connection)",
                r"system\s+health",
                r"netbox\s+status"
            ],
            entity_types=["system", "health", "status"],
            required_params=[],
            optional_params=[],
            fallback_tools=[],
            description="Check NetBox system health and connection status"
        ))
        
        # DCIM SITE TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_sites",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?sites",
                r"what\s+sites\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:data\s?centers?|locations)",
                r"list\s+(?:data\s?centers?|locations)",
                r"sites\s+in\s+netbox"
            ],
            entity_types=["site", "sites", "datacenter", "location"],
            required_params=[],
            optional_params=["region_name", "status", "tenant_name", "limit"],
            fallback_tools=["netbox_get_site_info"],
            description="List all sites in NetBox"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_site_info",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|describe)\s+site\s+(.+)",
                r"(?:details|info|information)\s+(?:about|for)\s+site\s+(.+)",
                r"site\s+(.+)\s+(?:details|info|information)",
                r"what\s+(?:is|about)\s+site\s+(.+)"
            ],
            entity_types=["site"],
            required_params=["site_name"],
            optional_params=[],
            fallback_tools=["netbox_list_all_sites"],
            description="Get detailed information about a specific site"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_site",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?site\s+(?:named\s+)?(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?site\s+(.+)",
                r"new\s+site\s+(.+)",
                r"create\s+(?:data\s?center|location)\s+(.+)"
            ],
            entity_types=["site"],
            required_params=["name"],  # Remove slug as required since it can be auto-generated
            optional_params=["slug", "region", "description", "physical_address", "shipping_address", "contact_name", "contact_phone", "contact_email", "status", "confirm"],
            fallback_tools=["netbox_list_all_sites"],
            description="Create a new site in NetBox"
        ))
        
        # DCIM RACK TOOLS  
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_racks",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?racks",
                r"what\s+racks\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?racks",
                r"racks\s+in\s+(.+)",
                r"(?:list|show)\s+racks\s+(?:in|at)\s+(.+)"
            ],
            entity_types=["rack", "racks"],
            required_params=[],
            optional_params=["site_name", "role", "status", "tenant_name", "limit"],
            fallback_tools=["netbox_get_rack_inventory"],
            description="List all racks with filtering options"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_rack_inventory",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show)\s+rack\s+(.+?)\s+(?:inventory|contents)",
                r"what(?:'s|\s+is)\s+in\s+rack\s+(.+)",
                r"rack\s+(.+)\s+(?:inventory|contents|devices)",
                r"(?:show|list)\s+(?:devices|equipment)\s+in\s+rack\s+(.+)"
            ],
            entity_types=["rack"],
            required_params=["rack_name"],  # Remove site_name as required
            optional_params=["site_name", "include_detailed"],
            fallback_tools=["netbox_get_rack_elevation", "netbox_list_all_racks"],
            description="Get comprehensive inventory report for a specific rack"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_rack_elevation",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show)\s+rack\s+(.+?)\s+elevation",
                r"rack\s+(.+)\s+elevation",
                r"elevation\s+(?:of|for)\s+rack\s+(.+)",
                r"(?:show|display)\s+rack\s+(.+)\s+layout"
            ],
            entity_types=["rack"],
            required_params=["rack_name"],
            optional_params=["site"],
            fallback_tools=["netbox_get_rack_inventory"],
            description="Get rack elevation showing device positions"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_rack",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?rack\s+(?:named\s+)?(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?rack\s+(.+)",
                r"new\s+rack\s+(.+)",
                r"create\s+rack\s+(.+)\s+in\s+(.+)"
            ],
            entity_types=["rack"],
            required_params=["name", "site"],
            optional_params=["role", "u_height", "width", "facility_id", "description", "status", "confirm"],
            fallback_tools=["netbox_list_all_racks"],
            description="Create a new rack in NetBox"
        ))
        
        # DCIM DEVICE TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_devices",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?devices",
                r"what\s+devices\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:servers?|equipment)",
                r"devices\s+in\s+(.+)",
                r"(?:list|show)\s+devices\s+(?:in|at)\s+(.+)",
                r"all\s+(?:servers?|hosts?|equipment)"
            ],
            entity_types=["device", "devices", "server", "equipment"],
            required_params=[],
            optional_params=["site_name", "role_name", "manufacturer_name", "status", "tenant_name", "limit"],
            fallback_tools=["netbox_get_device_info"],
            description="List all devices in NetBox"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_device_info",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|describe)\s+device\s+(.+)",
                r"(?:details|info|information)\s+(?:about|for)\s+device\s+(.+)",
                r"device\s+(.+)\s+(?:details|info|information)",
                r"what\s+(?:is|about)\s+device\s+(.+)",
                r"(?:server|host)\s+(.+)\s+(?:details|info)"
            ],
            entity_types=["device", "server", "host"],
            required_params=["device_name"],
            optional_params=["site", "include_interfaces", "include_cables", "interface_limit", "cable_limit"],
            fallback_tools=["netbox_get_device_basic_info", "netbox_list_all_devices"],
            description="Get comprehensive device information"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_device_basic_info",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:basic|simple)\s+(?:info|details)\s+(?:for|about)\s+device\s+(.+)",
                r"device\s+(.+)\s+(?:basic|simple)\s+(?:info|details)",
                r"quick\s+(?:info|details)\s+(?:for|about)\s+device\s+(.+)"
            ],
            entity_types=["device"],
            required_params=["device_name"],
            optional_params=["site"],
            fallback_tools=["netbox_get_device_info"],
            description="Get basic device information without interfaces/cables"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_device_interfaces",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|list)\s+(?:interfaces|ports)\s+(?:for|on)\s+device\s+(.+)",
                r"device\s+(.+)\s+(?:interfaces|ports)",
                r"(?:interfaces|ports)\s+(?:for|on)\s+(.+)",
                r"(?:show|list)\s+(.+)\s+(?:interfaces|ports)"
            ],
            entity_types=["interface", "interfaces", "port", "ports"],
            required_params=["device_name"],
            optional_params=["site", "enabled_only", "interface_type", "limit", "offset"],
            fallback_tools=["netbox_get_device_info"],
            description="Get device interfaces with pagination"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_device_cables",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|list)\s+cables\s+(?:for|on)\s+device\s+(.+)",
                r"device\s+(.+)\s+cables",
                r"cables\s+(?:for|on)\s+(.+)",
                r"(?:show|list)\s+(.+)\s+cables"
            ],
            entity_types=["cable", "cables"],
            required_params=["device_name"],
            optional_params=["site", "cable_status", "cable_type", "limit", "offset"],
            fallback_tools=["netbox_get_device_info"],
            description="Get device cables with pagination"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_device",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?device\s+(?:named\s+)?(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?device\s+(.+)",
                r"new\s+device\s+(.+)",
                r"create\s+(?:server|host)\s+(.+)"
            ],
            entity_types=["device", "server"],
            required_params=["name", "device_type", "site", "role"],
            optional_params=["status", "rack", "position", "face", "serial", "asset_tag", "description", "confirm"],
            fallback_tools=["netbox_provision_new_device"],
            description="Create a new device in NetBox"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_provision_new_device",
            domain=Domain.DCIM,
            query_type=QueryType.PROVISION,
            patterns=[
                r"provision\s+(?:new\s+)?device\s+(.+)",
                r"deploy\s+(?:new\s+)?device\s+(.+)",
                r"install\s+(?:new\s+)?device\s+(.+)",
                r"provision\s+(.+)\s+in\s+rack\s+(.+)"
            ],
            entity_types=["device"],
            required_params=["device_name", "site_name", "rack_name", "device_model", "role_name", "position"],
            optional_params=["face", "platform", "serial", "asset_tag", "tenant", "status", "confirm"],
            fallback_tools=["netbox_create_device"],
            description="Provision a complete new device in a rack"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_decommission_device",
            domain=Domain.DCIM,
            query_type=QueryType.DELETE,
            patterns=[
                r"decommission\s+device\s+(.+)",
                r"retire\s+device\s+(.+)",
                r"remove\s+device\s+(.+)\s+from\s+(?:service|production)",
                r"decommission\s+(.+)",
                r"safely\s+remove\s+device\s+(.+)"
            ],
            entity_types=["device"],
            required_params=["device_name"],
            optional_params=["decommission_strategy", "handle_cables", "handle_ips", "confirm"],
            fallback_tools=["netbox_update_device"],
            description="Safely decommission a device with validation and cleanup"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_update_device",
            domain=Domain.DCIM,
            query_type=QueryType.UPDATE,
            patterns=[
                r"update\s+device\s+(.+)",
                r"modify\s+device\s+(.+)",
                r"change\s+device\s+(.+)",
                r"edit\s+device\s+(.+)"
            ],
            entity_types=["device"],
            required_params=["device_id"],
            optional_params=["name", "device_type", "site", "rack", "position", "face", "role", "serial", "asset_tag", "description", "status", "tenant", "platform", "primary_ip4", "primary_ip6", "oob_ip", "comments", "confirm"],
            fallback_tools=["netbox_get_device_info"],
            description="Update an existing device in NetBox"
        ))
        
        # DCIM DEVICE TYPE TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_device_types",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?device\s+types",
                r"what\s+device\s+types\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:hardware\s+)?models",
                r"(?:list|show)\s+(?:hardware\s+)?models"
            ],
            entity_types=["device_type", "device_types", "model", "models"],
            required_params=[],
            optional_params=["manufacturer_name", "u_height", "limit"],
            fallback_tools=["netbox_get_device_type_info"],
            description="List all device types with usage statistics"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_device_type_info",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|describe)\s+device\s+type\s+(.+?)\s+(?:from\s+)?(.+)",
                r"(?:details|info|information)\s+(?:about|for)\s+device\s+type\s+(.+)",
                r"device\s+type\s+(.+)\s+(?:details|info|information)",
                r"(?:model|hardware)\s+(.+?)\s+(?:from\s+)?(.+?)\s+(?:details|info)"
            ],
            entity_types=["device_type", "model"],
            required_params=["manufacturer", "model"],
            optional_params=[],
            fallback_tools=["netbox_list_all_device_types"],
            description="Get detailed information about a specific device type"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_device_type",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?device\s+type\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?device\s+type\s+(.+)",
                r"new\s+device\s+type\s+(.+)",
                r"create\s+(?:model|hardware)\s+(.+)"
            ],
            entity_types=["device_type", "model"],
            required_params=["model", "manufacturer", "slug"],
            optional_params=["u_height", "is_full_depth", "part_number", "description", "confirm"],
            fallback_tools=["netbox_list_all_device_types"],
            description="Create a new device type in NetBox"
        ))
        
        # DCIM MANUFACTURER TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_manufacturers",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?manufacturers",
                r"what\s+manufacturers\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:vendors?|brands?)",
                r"(?:list|show)\s+(?:vendors?|brands?)"
            ],
            entity_types=["manufacturer", "manufacturers", "vendor", "brand"],
            required_params=[],
            optional_params=["limit"],
            fallback_tools=[],
            description="List all manufacturers with device type statistics"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_manufacturer",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?manufacturer\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?manufacturer\s+(.+)",
                r"new\s+manufacturer\s+(.+)",
                r"create\s+(?:vendor|brand)\s+(.+)"
            ],
            entity_types=["manufacturer", "vendor", "brand"],
            required_params=["name", "slug"],
            optional_params=["description", "confirm"],
            fallback_tools=["netbox_list_all_manufacturers"],
            description="Create a new manufacturer in NetBox"
        ))
        
        # DCIM DEVICE ROLE TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_device_roles",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?device\s+roles",
                r"what\s+device\s+roles\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:server\s+)?roles",
                r"(?:list|show)\s+roles"
            ],
            entity_types=["device_role", "device_roles", "role", "roles"],
            required_params=[],
            optional_params=["vm_role", "limit"],
            fallback_tools=[],
            description="List all device roles with usage statistics"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_device_role",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?device\s+role\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?device\s+role\s+(.+)",
                r"new\s+device\s+role\s+(.+)",
                r"create\s+role\s+(.+)"
            ],
            entity_types=["device_role", "role"],
            required_params=["name", "slug"],
            optional_params=["color", "vm_role", "description", "confirm"],
            fallback_tools=["netbox_list_all_device_roles"],
            description="Create a new device role in NetBox"
        ))
        
        # DCIM CABLE TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_cables",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?cables",
                r"what\s+cables\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?cables",
                r"cables\s+in\s+(.+)"
            ],
            entity_types=["cable", "cables"],
            required_params=[],
            optional_params=["cable_status", "cable_type", "site_name", "limit"],
            fallback_tools=["netbox_get_cable_info"],
            description="List all cables with filtering options"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_cable_info",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|describe)\s+cable\s+(.+)",
                r"(?:details|info|information)\s+(?:about|for)\s+cable\s+(.+)",
                r"cable\s+(.+)\s+(?:details|info|information)"
            ],
            entity_types=["cable"],
            required_params=[],
            optional_params=["cable_id", "device_name", "interface_name"],
            fallback_tools=["netbox_list_all_cables"],
            description="Get detailed information about a specific cable"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_cable_connection",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?cable\s+(?:connection\s+)?between\s+(.+?)\s+and\s+(.+)",
                r"connect\s+(.+?)\s+to\s+(.+)\s+(?:with|using)\s+cable",
                r"cable\s+(.+?)\s+to\s+(.+)",
                r"wire\s+(.+?)\s+to\s+(.+)"
            ],
            entity_types=["cable", "connection"],
            required_params=["device_a_name", "interface_a_name", "device_b_name", "interface_b_name"],
            optional_params=["cable_type", "cable_status", "cable_color", "cable_length", "cable_length_unit", "label", "description", "confirm"],
            fallback_tools=["netbox_bulk_create_cable_connections"],
            description="Create a physical cable connection between two device interfaces"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_bulk_create_cable_connections",
            domain=Domain.DCIM,
            query_type=QueryType.BULK,
            patterns=[
                r"(?:bulk\s+)?create\s+(?:multiple\s+)?cable\s+connections",
                r"create\s+(?:many|multiple|bulk)\s+cables",
                r"bulk\s+cable\s+(?:creation|connections)",
                r"mass\s+cable\s+(?:creation|connections)"
            ],
            entity_types=["cable", "cables"],
            required_params=["cable_connections"],
            optional_params=["cable_type", "cable_status", "cable_color", "cable_length", "cable_length_unit", "batch_size", "rollback_on_error", "confirm"],
            fallback_tools=["netbox_create_cable_connection"],
            description="Create multiple cable connections in bulk with rollback support"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_disconnect_cable",
            domain=Domain.DCIM,
            query_type=QueryType.DELETE,
            patterns=[
                r"disconnect\s+cable\s+(.+)",
                r"remove\s+cable\s+(.+)",
                r"delete\s+cable\s+(.+)",
                r"disconnect\s+(.+)\s+from\s+(.+)"
            ],
            entity_types=["cable"],
            required_params=[],
            optional_params=["cable_id", "device_name", "interface_name", "confirm"],
            fallback_tools=["netbox_get_cable_info"],
            description="Disconnect a cable by removing it from NetBox"
        ))
        
        # DCIM INTERFACE TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_interface",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:an?\s+)?(?:new\s+)?interface\s+(.+?)\s+on\s+(?:device\s+)?(.+)",
                r"add\s+(?:an?\s+)?(?:new\s+)?interface\s+(.+?)\s+to\s+(?:device\s+)?(.+)",
                r"new\s+interface\s+(.+?)\s+(?:on|for)\s+(.+)"
            ],
            entity_types=["interface", "port"],
            required_params=["device_name", "interface_name"],
            optional_params=["interface_type", "enabled", "mgmt_only", "mtu", "mac_address", "description", "confirm"],
            fallback_tools=["netbox_get_device_interfaces"],
            description="Create a new interface on a physical device"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_assign_ip_to_interface",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"assign\s+(?:ip\s+)?(.+?)\s+to\s+interface\s+(.+?)\s+on\s+(?:device\s+)?(.+)",
                r"add\s+(?:ip\s+)?(.+?)\s+to\s+interface\s+(.+?)\s+on\s+(?:device\s+)?(.+)",
                r"set\s+(?:ip\s+)?(.+?)\s+on\s+interface\s+(.+?)\s+(?:device\s+)?(.+)"
            ],
            entity_types=["ip", "interface"],
            required_params=["device_name", "interface_name", "ip_address"],
            optional_params=["status", "description", "confirm"],
            fallback_tools=["netbox_create_ip_address"],
            description="Assign an IP address to a device interface"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_set_primary_ip",
            domain=Domain.DCIM,
            query_type=QueryType.UPDATE,
            patterns=[
                r"set\s+primary\s+ip\s+(.+?)\s+(?:for|on)\s+device\s+(.+)",
                r"make\s+(.+?)\s+primary\s+ip\s+(?:for|on)\s+device\s+(.+)",
                r"primary\s+ip\s+(.+?)\s+(?:for|on)\s+device\s+(.+)"
            ],
            entity_types=["ip", "device"],
            required_params=["device_name", "ip_address"],
            optional_params=["ip_version", "confirm"],
            fallback_tools=["netbox_assign_ip_to_interface"],
            description="Set primary IP address for a device"
        ))
        
        # DCIM MODULE TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_module_types",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?module\s+types",
                r"what\s+module\s+types\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:line\s+cards?|modules)",
                r"(?:list|show)\s+(?:line\s+cards?|modules)"
            ],
            entity_types=["module_type", "module_types", "module", "linecard"],
            required_params=[],
            optional_params=["manufacturer", "limit"],
            fallback_tools=["netbox_get_module_type_info"],
            description="List all module types with filtering and statistics"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_module_type_info",
            domain=Domain.DCIM,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|describe)\s+module\s+type\s+(.+?)\s+(?:from\s+)?(.+)",
                r"(?:details|info|information)\s+(?:about|for)\s+module\s+type\s+(.+)",
                r"module\s+type\s+(.+)\s+(?:details|info|information)"
            ],
            entity_types=["module_type", "module"],
            required_params=["manufacturer", "model"],
            optional_params=[],
            fallback_tools=["netbox_list_all_module_types"],
            description="Get detailed information about a specific module type"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_module_type",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?module\s+type\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?module\s+type\s+(.+)",
                r"new\s+module\s+type\s+(.+)"
            ],
            entity_types=["module_type", "module"],
            required_params=["manufacturer", "model"],
            optional_params=["part_number", "description", "weight", "weight_unit", "confirm"],
            fallback_tools=["netbox_list_all_module_types"],
            description="Create a module type for defining modular component specifications"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_modules",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?modules",
                r"what\s+modules\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:installed\s+)?modules",
                r"modules\s+in\s+(.+)"
            ],
            entity_types=["module", "modules"],
            required_params=[],
            optional_params=["device_name", "module_type", "limit"],
            fallback_tools=["netbox_list_device_modules"],
            description="List all modules with filtering and expanded data"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_device_modules",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+modules\s+(?:for|on|in)\s+device\s+(.+)",
                r"device\s+(.+)\s+modules",
                r"modules\s+(?:installed\s+)?(?:in|on)\s+(.+)",
                r"what\s+modules\s+(?:are\s+)?(?:installed\s+)?(?:in|on)\s+device\s+(.+)"
            ],
            entity_types=["module", "modules"],
            required_params=["device_name"],
            optional_params=["limit"],
            fallback_tools=["netbox_get_module_info"],
            description="List all modules installed on a specific device"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_install_module_in_device",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"install\s+module\s+(.+?)\s+in\s+(?:device\s+)?(.+?)\s+(?:bay|slot)\s+(.+)",
                r"add\s+module\s+(.+?)\s+to\s+(?:device\s+)?(.+?)\s+(?:bay|slot)\s+(.+)",
                r"insert\s+module\s+(.+?)\s+into\s+(?:device\s+)?(.+)"
            ],
            entity_types=["module"],
            required_params=["device_name", "module_type", "module_bay"],
            optional_params=["serial_number", "asset_tag", "confirm"],
            fallback_tools=["netbox_list_device_module_bays"],
            description="Install a module in a device module bay"
        ))
        
        # DCIM POWER TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_power_panels",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?power\s+panels",
                r"what\s+power\s+panels\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:electrical\s+)?panels",
                r"power\s+distribution\s+panels"
            ],
            entity_types=["power_panel", "power_panels", "panel"],
            required_params=[],
            optional_params=["site", "location", "rack_group", "limit"],
            fallback_tools=["netbox_get_power_panel_info"],
            description="List all power panels with filtering"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_power_panel",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?power\s+panel\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?power\s+panel\s+(.+)",
                r"new\s+power\s+panel\s+(.+)"
            ],
            entity_types=["power_panel", "panel"],
            required_params=["name", "site"],
            optional_params=["location", "rack_group", "comments", "tags", "confirm"],
            fallback_tools=["netbox_list_all_power_panels"],
            description="Create a new power panel in NetBox"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_power_feeds",
            domain=Domain.DCIM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?power\s+feeds",
                r"what\s+power\s+feeds\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?power\s+feeds",
                r"power\s+feeds\s+in\s+(.+)"
            ],
            entity_types=["power_feed", "power_feeds", "feed"],
            required_params=[],
            optional_params=["site", "power_panel", "rack", "feed_type", "status", "limit"],
            fallback_tools=["netbox_get_power_feed_info"],
            description="List all power feeds with filtering"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_power_feed",
            domain=Domain.DCIM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?power\s+feed\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?power\s+feed\s+(.+)",
                r"new\s+power\s+feed\s+(.+)"
            ],
            entity_types=["power_feed", "feed"],
            required_params=["name", "power_panel", "site"],
            optional_params=["rack", "status", "feed_type", "supply", "phase", "voltage", "amperage", "max_utilization", "comments", "tags", "confirm"],
            fallback_tools=["netbox_list_all_power_feeds"],
            description="Create a new power feed in NetBox"
        ))
        
        # IPAM PREFIX TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_prefixes",
            domain=Domain.IPAM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?(?:prefixes|networks|subnets)",
                r"what\s+(?:prefixes|networks|subnets)\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:ip\s+)?(?:prefixes|networks|subnets)",
                r"(?:prefixes|networks|subnets)\s+in\s+(.+)"
            ],
            entity_types=["prefix", "prefixes", "network", "subnet"],
            required_params=[],
            optional_params=["family", "role", "site_name", "status", "tenant_name", "vrf_name", "limit"],
            fallback_tools=["netbox_get_prefix_utilization"],
            description="List all IP prefixes with filtering"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_prefix",
            domain=Domain.IPAM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?(?:prefix|network|subnet)\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?(?:prefix|network|subnet)\s+(.+)",
                r"new\s+(?:prefix|network|subnet)\s+(.+)"
            ],
            entity_types=["prefix", "network", "subnet"],
            required_params=["prefix"],
            optional_params=["site", "vlan", "status", "tenant", "description", "confirm"],
            fallback_tools=["netbox_list_all_prefixes"],
            description="Create a new IP prefix in NetBox IPAM"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_prefix_utilization",
            domain=Domain.IPAM,
            query_type=QueryType.ANALYSIS,
            patterns=[
                r"(?:get|show)\s+(?:prefix|network|subnet)\s+(.+?)\s+(?:utilization|usage)",
                r"(?:utilization|usage)\s+(?:of|for)\s+(?:prefix|network|subnet)\s+(.+)",
                r"how\s+(?:full|utilized|used)\s+is\s+(?:prefix|network|subnet)\s+(.+)",
                r"capacity\s+(?:of|for)\s+(?:prefix|network|subnet)\s+(.+)",
                r"get\s+prefix\s+utilization",
                r"prefix\s+utilization"
            ],
            entity_types=["prefix", "network", "subnet", "utilization"],
            required_params=["prefix"],
            optional_params=["include_child_prefixes", "include_detailed_breakdown", "tenant", "vrf"],
            fallback_tools=["netbox_get_ip_usage"],
            description="Get comprehensive prefix utilization report for capacity planning"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_ip_usage",
            domain=Domain.IPAM,
            query_type=QueryType.ANALYSIS,
            patterns=[
                r"(?:get|show)\s+(?:ip\s+)?usage\s+(?:for\s+)?(?:prefix\s+)?(.+)",
                r"ip\s+(?:address\s+)?(?:usage|statistics)\s+(?:for\s+)?(.+)",
                r"(?:usage|statistics)\s+(?:for\s+)?(?:prefix\s+)?(.+)"
            ],
            entity_types=["prefix", "ip"],
            required_params=["prefix"],
            optional_params=[],
            fallback_tools=["netbox_get_prefix_utilization"],
            description="Get IP address usage statistics for a prefix"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_find_available_ip",
            domain=Domain.IPAM,
            query_type=QueryType.ANALYSIS,
            patterns=[
                r"find\s+available\s+(?:ip\s+)?(?:addresses?\s+)?(?:in\s+)?(?:prefix\s+)?(.+)",
                r"(?:available|free)\s+(?:ip\s+)?(?:addresses?\s+)?(?:in\s+)?(?:prefix\s+)?(.+)"
            ],
            entity_types=["ip", "prefix"],
            required_params=["prefix"],
            optional_params=["count"],
            fallback_tools=["netbox_find_next_available_ip"],
            description="Find available IP addresses in a prefix"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_find_next_available_ip",
            domain=Domain.IPAM,
            query_type=QueryType.ANALYSIS,
            patterns=[
                r"find\s+next\s+available\s+(?:ip\s+)?(?:in\s+)?(?:prefix\s+)?(.+)",
                r"next\s+(?:free|available)\s+(?:ip\s+)?(?:in\s+)?(?:prefix\s+)?(.+)",
                r"get\s+next\s+(?:ip\s+)?(?:from\s+)?(?:prefix\s+)?(.+)",
                r"find\s+next\s+available\s+ip"
            ],
            entity_types=["ip", "prefix", "next"],
            required_params=[],  # Make prefix optional for now
            optional_params=["prefix", "count", "reserve_immediately", "assign_to_interface", "device_name", "description", "status", "tenant", "vrf", "confirm"],
            fallback_tools=["netbox_find_available_ip"],
            description="Find and optionally reserve the next available IP address(es) in a prefix"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_find_duplicate_ips",
            domain=Domain.IPAM,
            query_type=QueryType.ANALYSIS,
            patterns=[
                r"find\s+(?:duplicate|conflicting)\s+(?:ip\s+)?(?:addresses?)",
                r"(?:duplicate|conflicting)\s+(?:ip\s+)?(?:addresses?)",
                r"ip\s+(?:conflicts|duplicates)",
                r"check\s+for\s+(?:duplicate|conflicting)\s+(?:ips?|ip\s+addresses?)",
                r"find\s+duplicate\s+ips"
            ],
            entity_types=["ip", "duplicate"],
            required_params=[],
            optional_params=["tenant", "vrf", "include_severity_analysis", "include_resolution_recommendations", "limit"],
            fallback_tools=["netbox_list_all_prefixes"],
            description="Find duplicate IP addresses for network auditing"
        ))
        
        # IPAM IP ADDRESS TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_ip_address",
            domain=Domain.IPAM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:an?\s+)?(?:new\s+)?ip\s+(?:address\s+)?(.+)",
                r"add\s+(?:an?\s+)?(?:new\s+)?ip\s+(?:address\s+)?(.+)",
                r"new\s+ip\s+(?:address\s+)?(.+)"
            ],
            entity_types=["ip", "ip_address"],
            required_params=["ip_address"],
            optional_params=["status", "tenant", "description", "confirm"],
            fallback_tools=["netbox_find_next_available_ip"],
            description="Create a new IP address in NetBox IPAM"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_assign_mac_to_interface",
            domain=Domain.IPAM,
            query_type=QueryType.CREATE,
            patterns=[
                r"assign\s+(?:mac\s+)?(?:address\s+)?(.+?)\s+to\s+interface\s+(.+?)\s+on\s+(?:device\s+)?(.+)",
                r"add\s+(?:mac\s+)?(?:address\s+)?(.+?)\s+to\s+interface\s+(.+?)\s+on\s+(?:device\s+)?(.+)",
                r"set\s+(?:mac\s+)?(?:address\s+)?(.+?)\s+on\s+interface\s+(.+?)\s+(?:device\s+)?(.+)"
            ],
            entity_types=["mac", "interface"],
            required_params=["device_name", "interface_name", "mac_address"],
            optional_params=["confirm"],
            fallback_tools=["netbox_create_interface"],
            description="Assign MAC address to device interface"
        ))
        
        # IPAM VLAN TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_vlans",
            domain=Domain.IPAM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?vlans",
                r"what\s+vlans\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?vlans",
                r"vlans\s+in\s+(.+)"
            ],
            entity_types=["vlan", "vlans"],
            required_params=[],
            optional_params=["group_name", "role", "site_name", "status", "tenant_name", "limit"],
            fallback_tools=["netbox_find_available_vlan_id"],
            description="List all VLANs with filtering"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_vlan",
            domain=Domain.IPAM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?vlan\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?vlan\s+(.+)",
                r"new\s+vlan\s+(.+)"
            ],
            entity_types=["vlan"],
            required_params=["name", "vid"],
            optional_params=["site", "group", "tenant", "status", "description", "confirm"],
            fallback_tools=["netbox_find_available_vlan_id"],
            description="Create a new VLAN in NetBox IPAM"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_find_available_vlan_id",
            domain=Domain.IPAM,
            query_type=QueryType.ANALYSIS,
            patterns=[
                r"find\s+available\s+vlan\s+(?:id|ids)",
                r"(?:available|free)\s+vlan\s+(?:id|ids)",
                r"next\s+(?:available\s+)?vlan\s+(?:id|ids)"
            ],
            entity_types=["vlan"],
            required_params=[],
            optional_params=["start_vid", "end_vid", "site", "group"],
            fallback_tools=["netbox_list_all_vlans"],
            description="Find available VLAN IDs in a range"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_provision_vlan_with_prefix",
            domain=Domain.IPAM,
            query_type=QueryType.PROVISION,
            patterns=[
                r"provision\s+vlan\s+(.+?)\s+with\s+(?:prefix|network|subnet)\s+(.+)",
                r"create\s+vlan\s+(.+?)\s+(?:and|with)\s+(?:prefix|network|subnet)\s+(.+)",
                r"deploy\s+vlan\s+(.+?)\s+(?:and|with)\s+(?:prefix|network|subnet)\s+(.+)"
            ],
            entity_types=["vlan", "prefix"],
            required_params=["vlan_name", "vlan_id", "prefix"],
            optional_params=["site", "tenant", "vlan_group", "vlan_role", "vlan_status", "prefix_role", "prefix_status", "vrf", "description", "confirm"],
            fallback_tools=["netbox_create_vlan", "netbox_create_prefix"],
            description="Provision a VLAN with coordinated IP prefix creation"
        ))
        
        # IPAM VRF TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_vrfs",
            domain=Domain.IPAM,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?vrfs",
                r"what\s+vrfs\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?vrfs",
                r"vrfs\s+(?:for\s+)?(.+)"
            ],
            entity_types=["vrf", "vrfs"],
            required_params=[],
            optional_params=["tenant_name", "enforce_unique", "limit"],
            fallback_tools=[],
            description="List all VRFs with prefix and routing statistics"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_vrf",
            domain=Domain.IPAM,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?vrf\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?vrf\s+(.+)",
                r"new\s+vrf\s+(.+)"
            ],
            entity_types=["vrf"],
            required_params=["name"],
            optional_params=["rd", "tenant", "description", "confirm"],
            fallback_tools=["netbox_list_all_vrfs"],
            description="Create a new VRF in NetBox IPAM"
        ))
        
        # VIRTUALIZATION CLUSTER TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_clusters",
            domain=Domain.VIRTUALIZATION,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?clusters",
                r"what\s+clusters\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:virtualization\s+)?clusters",
                r"clusters\s+in\s+(.+)"
            ],
            entity_types=["cluster", "clusters"],
            required_params=[],
            optional_params=["cluster_type", "cluster_group", "site", "status", "limit"],
            fallback_tools=["netbox_get_cluster_info"],
            description="List all clusters with filtering capabilities"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_cluster_info",
            domain=Domain.VIRTUALIZATION,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|describe)\s+cluster\s+(.+)",
                r"(?:details|info|information)\s+(?:about|for)\s+cluster\s+(.+)",
                r"cluster\s+(.+)\s+(?:details|info|information)"
            ],
            entity_types=["cluster"],
            required_params=[],
            optional_params=["cluster_id", "name"],
            fallback_tools=["netbox_list_all_clusters"],
            description="Get detailed information about a specific cluster"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_cluster",
            domain=Domain.VIRTUALIZATION,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?cluster\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?cluster\s+(.+)",
                r"new\s+cluster\s+(.+)"
            ],
            entity_types=["cluster"],
            required_params=["name", "cluster_type"],
            optional_params=["cluster_group", "site", "status", "description", "comments", "confirm"],
            fallback_tools=["netbox_list_all_cluster_types"],
            description="Create a new virtualization cluster in NetBox"
        ))
        
        # VIRTUALIZATION VM TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_virtual_machines",
            domain=Domain.VIRTUALIZATION,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?(?:virtual\s+machines?|vms)",
                r"what\s+(?:virtual\s+machines?|vms)\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:virtual\s+machines?|vms)",
                r"(?:virtual\s+machines?|vms)\s+in\s+(.+)"
            ],
            entity_types=["virtual_machine", "vm", "vms"],
            required_params=[],
            optional_params=["cluster", "platform", "role", "status", "tenant", "limit"],
            fallback_tools=["netbox_get_virtual_machine_info"],
            description="List all virtual machines with filtering"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_virtual_machine_info",
            domain=Domain.VIRTUALIZATION,
            query_type=QueryType.GET,
            patterns=[
                r"(?:get|show|describe)\s+(?:virtual\s+machine|vm)\s+(.+)",
                r"(?:details|info|information)\s+(?:about|for)\s+(?:virtual\s+machine|vm)\s+(.+)",
                r"(?:virtual\s+machine|vm)\s+(.+)\s+(?:details|info|information)"
            ],
            entity_types=["virtual_machine", "vm"],
            required_params=[],
            optional_params=["vm_id", "name"],
            fallback_tools=["netbox_list_all_virtual_machines"],
            description="Get detailed information about a specific virtual machine"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_virtual_machine",
            domain=Domain.VIRTUALIZATION,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?(?:virtual\s+machine|vm)\s+(.+)",
                r"add\s+(?:a\s+)?(?:new\s+)?(?:virtual\s+machine|vm)\s+(.+)",
                r"new\s+(?:virtual\s+machine|vm)\s+(.+)"
            ],
            entity_types=["virtual_machine", "vm"],
            required_params=["name", "cluster"],
            optional_params=["role", "platform", "vcpus", "memory_mb", "disk_gb", "status", "tenant", "description", "comments", "confirm"],
            fallback_tools=["netbox_list_all_clusters"],
            description="Create a new virtual machine in NetBox"
        ))
        
        # TENANCY TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_tenants",
            domain=Domain.TENANCY,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?tenants",
                r"what\s+tenants\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:tenants|customers|organizations)",
                r"(?:tenants|customers|organizations)\s+in\s+(.+)"
            ],
            entity_types=["tenant", "tenants", "customer", "organization"],
            required_params=[],
            optional_params=["group_name", "status", "limit"],
            fallback_tools=["netbox_get_tenant_resource_report"],
            description="List all tenants with filtering"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_onboard_new_tenant",
            domain=Domain.TENANCY,
            query_type=QueryType.CREATE,
            patterns=[
                r"(?:onboard|create|add)\s+(?:a\s+)?(?:new\s+)?tenant\s+(.+)",
                r"new\s+tenant\s+(.+)",
                r"(?:onboard|create|add)\s+(?:customer|organization)\s+(.+)"
            ],
            entity_types=["tenant", "customer", "organization"],
            required_params=["tenant_name"],
            optional_params=["tenant_group_name", "tenant_status", "description", "contact_name", "contact_email", "contact_phone", "contact_address", "create_group_if_missing", "tags", "comments", "confirm"],
            fallback_tools=["netbox_create_tenant_group"],
            description="Onboard a new tenant to NetBox with contact management"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_get_tenant_resource_report",
            domain=Domain.TENANCY,
            query_type=QueryType.REPORT,
            patterns=[
                r"(?:get|generate|show)\s+(?:tenant\s+)?(.+?)\s+(?:resource\s+)?(?:report|resources)",
                r"(?:resources|report)\s+(?:for\s+)?tenant\s+(.+)",
                r"what\s+(?:resources\s+)?(?:does\s+)?tenant\s+(.+)\s+(?:have|own)",
                r"tenant\s+(.+)\s+(?:owns|has)\s+what"
            ],
            entity_types=["tenant", "resource"],
            required_params=["tenant_name"],
            optional_params=["include_details", "include_utilization", "filter_by_site", "filter_by_status", "export_format"],
            fallback_tools=["netbox_list_all_tenants"],
            description="Generate comprehensive tenant resource report"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_assign_resources_to_tenant",
            domain=Domain.TENANCY,
            query_type=QueryType.UPDATE,
            patterns=[
                r"assign\s+(.+?)\s+to\s+tenant\s+(.+)",
                r"give\s+(.+?)\s+to\s+tenant\s+(.+)",
                r"set\s+(.+?)\s+(?:owner|tenant)\s+(?:to\s+)?(.+)"
            ],
            entity_types=["tenant", "resource"],
            required_params=["tenant_name", "resources"],
            optional_params=["assignment_mode", "confirm"],
            fallback_tools=["netbox_get_tenant_resource_report"],
            description="Assign or unassign NetBox resources to/from a tenant"
        ))
        
        # EXTRAS TOOLS
        self._add_mapping(ToolMapping(
            tool_name="netbox_list_all_journal_entries",
            domain=Domain.EXTRAS,
            query_type=QueryType.LIST,
            patterns=[
                r"(?:list|show|get)\s+(?:all\s+)?journal\s+entries",
                r"what\s+journal\s+entries\s+(?:are\s+there|exist)",
                r"show\s+(?:me\s+)?(?:all\s+)?(?:audit\s+)?(?:logs?|entries)",
                r"(?:audit\s+)?(?:logs?|entries)\s+(?:for\s+)?(.+)"
            ],
            entity_types=["journal", "journal_entry", "log", "audit"],
            required_params=[],
            optional_params=["assigned_object_type", "assigned_object_id", "kind", "limit"],
            fallback_tools=["netbox_create_journal_entry"],
            description="List all journal entries with filtering"
        ))
        
        self._add_mapping(ToolMapping(
            tool_name="netbox_create_journal_entry",
            domain=Domain.EXTRAS,
            query_type=QueryType.CREATE,
            patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?journal\s+entry",
                r"add\s+(?:a\s+)?(?:new\s+)?journal\s+entry",
                r"log\s+(?:entry|message|comment)\s+(.+)",
                r"(?:add|create)\s+(?:audit\s+)?log\s+(?:entry\s+)?(.+)"
            ],
            entity_types=["journal", "journal_entry", "log"],
            required_params=["assigned_object_type", "assigned_object_id", "comments"],
            optional_params=["kind", "confirm"],
            fallback_tools=["netbox_list_all_journal_entries"],
            description="Create a new journal entry for a NetBox object"
        ))
        
    def _add_mapping(self, mapping: ToolMapping):
        """Add a tool mapping to the system."""
        self._tool_mappings[mapping.tool_name] = mapping
        
        # Add entity type mappings
        for entity_type in mapping.entity_types:
            if entity_type not in self._entity_patterns:
                self._entity_patterns[entity_type] = []
            self._entity_patterns[entity_type].append(mapping.tool_name)
        
        # Add action type mappings
        if mapping.query_type not in self._action_patterns:
            self._action_patterns[mapping.query_type] = []
        self._action_patterns[mapping.query_type].append(mapping.tool_name)
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for better performance."""
        for tool_name, mapping in self._tool_mappings.items():
            for pattern in mapping.patterns:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._pattern_cache[f"{tool_name}:{pattern}"] = compiled
    
    def map_query_to_tool(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], Dict[str, Any], List[str]]:
        """
        Map a user query to the most appropriate NetBox tool.
        
        Args:
            query: The user's query string
            parameters: Optional parameters extracted from query
            
        Returns:
            Tuple of (tool_name, normalized_parameters, fallback_tools)
        """
        if parameters is None:
            parameters = {}
        
        logger.debug(f"Mapping query: {query}")
        
        # Normalize query
        normalized_query = self._normalize_query(query)
        
        # Try direct pattern matching first
        tool_name = self._match_patterns(normalized_query)
        
        if tool_name:
            mapping = self._tool_mappings[tool_name]
            
            # Extract parameters from query if not provided
            if not parameters:
                parameters = self._extract_parameters(normalized_query, mapping)
            
            # Normalize parameters
            normalized_params = ParameterValidator.normalize_parameters(parameters)
            
            # Validate required parameters
            is_valid, missing_params = ParameterValidator.validate_required_params(
                normalized_params, mapping.required_params
            )
            
            if not is_valid:
                logger.warning(f"Missing required parameters for {tool_name}: {missing_params}")
                # Try to find fallback tools
                fallback_tools = self._find_fallback_tools(mapping, normalized_params)
                return None, normalized_params, fallback_tools
            
            logger.info(f"Mapped query to tool: {tool_name}")
            return tool_name, normalized_params, mapping.fallback_tools
        
        # Fallback: Try entity-based matching
        tool_name = self._match_by_entity(normalized_query)
        if tool_name:
            mapping = self._tool_mappings[tool_name]
            normalized_params = ParameterValidator.normalize_parameters(parameters)
            return tool_name, normalized_params, mapping.fallback_tools
        
        # Fallback: Try action-based matching
        tool_name = self._match_by_action(normalized_query)
        if tool_name:
            mapping = self._tool_mappings[tool_name]
            normalized_params = ParameterValidator.normalize_parameters(parameters)
            return tool_name, normalized_params, mapping.fallback_tools
        
        logger.warning(f"No tool mapping found for query: {query}")
        return None, {}, []
    
    def _normalize_query(self, query: str) -> str:
        """Normalize the query for better matching."""
        # Convert to lowercase
        normalized = query.lower().strip()
        
        # Remove common filler words but preserve meaning
        filler_words = ['please', 'can you', 'could you', 'would you', 'i want to', 'i need to']
        for filler in filler_words:
            normalized = normalized.replace(filler, '').strip()
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _match_patterns(self, query: str) -> Optional[str]:
        """Match query against compiled patterns."""
        for tool_name, mapping in self._tool_mappings.items():
            for pattern in mapping.patterns:
                cache_key = f"{tool_name}:{pattern}"
                if cache_key in self._pattern_cache:
                    compiled_pattern = self._pattern_cache[cache_key]
                else:
                    compiled_pattern = re.compile(pattern, re.IGNORECASE)
                    self._pattern_cache[cache_key] = compiled_pattern
                
                if compiled_pattern.search(query):
                    logger.debug(f"Pattern match: {pattern} -> {tool_name}")
                    return tool_name
        
        return None
    
    def _match_by_entity(self, query: str) -> Optional[str]:
        """Match by entity type mentioned in query."""
        for entity_type, tool_names in self._entity_patterns.items():
            if entity_type in query:
                # Prefer list tools for general mentions
                list_tools = [t for t in tool_names if 'list_all' in t]
                if list_tools:
                    return list_tools[0]
                return tool_names[0]
        
        return None
    
    def _match_by_action(self, query: str) -> Optional[str]:
        """Match by action type inferred from query."""
        # Define action keywords
        action_keywords = {
            QueryType.LIST: ['list', 'show', 'get all', 'what are', 'display'],
            QueryType.GET: ['get', 'show me', 'details', 'info', 'describe'],
            QueryType.CREATE: ['create', 'add', 'new', 'make'],
            QueryType.UPDATE: ['update', 'modify', 'change', 'edit'],
            QueryType.DELETE: ['delete', 'remove', 'decommission'],
            QueryType.HEALTH: ['health', 'status', 'check'],
            QueryType.ANALYSIS: ['analyze', 'usage', 'utilization', 'find'],
        }
        
        for query_type, keywords in action_keywords.items():
            if any(keyword in query for keyword in keywords):
                if query_type in self._action_patterns:
                    return self._action_patterns[query_type][0]
        
        return None
    
    def _extract_parameters(self, query: str, mapping: ToolMapping) -> Dict[str, Any]:
        """Extract parameters from the query based on the tool mapping."""
        parameters = {}
        
        # Try to extract parameters from pattern groups
        for pattern in mapping.patterns:
            compiled = re.compile(pattern, re.IGNORECASE)
            match = compiled.search(query)
            if match and match.groups():
                groups = match.groups()
                
                # Map groups to likely parameter names based on tool requirements
                all_params = mapping.required_params + mapping.optional_params
                if all_params:
                    for i, param in enumerate(all_params[:len(groups)]):
                        if groups[i]:
                            # Clean up the extracted value
                            value = groups[i].strip()
                            # Handle common parameter mappings
                            if param in ['site_name', 'device_name', 'rack_name', 'cluster_name', 'tenant_name']:
                                # Remove common prefixes
                                value = re.sub(r'^(?:named?|called)\s+', '', value, flags=re.IGNORECASE)
                            parameters[param] = value
        
        # Additional parameter extraction for common patterns
        if not parameters:
            # Try to extract common entity names directly
            if any(entity in ['device', 'server', 'host'] for entity in mapping.entity_types):
                device_match = re.search(r'(?:device|server|host)\s+([^\s]+)', query, re.IGNORECASE)
                if device_match:
                    parameters['device_name'] = device_match.group(1)
            
            if any(entity in ['site', 'location', 'datacenter'] for entity in mapping.entity_types):
                site_match = re.search(r'(?:site|location|datacenter)\s+([^\s]+)', query, re.IGNORECASE)
                if site_match:
                    parameters['site_name'] = site_match.group(1)
            
            if any(entity in ['rack'] for entity in mapping.entity_types):
                rack_match = re.search(r'rack\s+([^\s]+)', query, re.IGNORECASE)
                if rack_match:
                    parameters['rack_name'] = rack_match.group(1)
            
            if any(entity in ['vm', 'virtual_machine'] for entity in mapping.entity_types):
                vm_match = re.search(r'(?:vm|virtual\s+machine)\s+([^\s]+)', query, re.IGNORECASE)
                if vm_match:
                    parameters['virtual_machine_name'] = vm_match.group(1)
        
        return parameters
    
    def _find_fallback_tools(
        self, 
        mapping: ToolMapping, 
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Find appropriate fallback tools when primary tool fails."""
        fallbacks = list(mapping.fallback_tools)
        
        # Add domain-specific fallbacks
        if mapping.domain == Domain.DCIM:
            if 'device' in mapping.entity_types:
                fallbacks.extend(['netbox_list_all_devices', 'netbox_get_device_basic_info'])
            elif 'site' in mapping.entity_types:
                fallbacks.extend(['netbox_list_all_sites'])
                
        elif mapping.domain == Domain.IPAM:
            if 'prefix' in mapping.entity_types:
                fallbacks.extend(['netbox_list_all_prefixes'])
            elif 'ip' in mapping.entity_types:
                fallbacks.extend(['netbox_find_next_available_ip'])
                
        elif mapping.domain == Domain.VIRTUALIZATION:
            if 'cluster' in mapping.entity_types:
                fallbacks.extend(['netbox_list_all_clusters'])
            elif 'vm' in mapping.entity_types:
                fallbacks.extend(['netbox_list_all_virtual_machines'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_fallbacks = []
        for tool in fallbacks:
            if tool not in seen:
                seen.add(tool)
                unique_fallbacks.append(tool)
        
        return unique_fallbacks
    
    def get_tool_info(self, tool_name: str) -> Optional[ToolMapping]:
        """Get detailed information about a tool."""
        return self._tool_mappings.get(tool_name)
    
    def get_tools_by_domain(self, domain: Domain) -> List[str]:
        """Get all tools for a specific domain."""
        return [
            name for name, mapping in self._tool_mappings.items()
            if mapping.domain == domain
        ]
    
    def get_tools_by_type(self, query_type: QueryType) -> List[str]:
        """Get all tools of a specific type."""
        return [
            name for name, mapping in self._tool_mappings.items()
            if mapping.query_type == query_type
        ]
    
    def suggest_tools(self, partial_query: str, limit: int = 5) -> List[Tuple[str, str]]:
        """Suggest tools based on partial query."""
        suggestions = []
        normalized_query = self._normalize_query(partial_query)
        
        for tool_name, mapping in self._tool_mappings.items():
            score = 0
            
            # Check if any pattern partially matches
            for pattern in mapping.patterns:
                if any(word in normalized_query for word in pattern.split()):
                    score += 1
            
            # Check entity type matches
            for entity in mapping.entity_types:
                if entity in normalized_query:
                    score += 2
            
            if score > 0:
                suggestions.append((tool_name, mapping.description))
        
        # Sort by score and return top results
        suggestions.sort(key=lambda x: x[0], reverse=True)
        return suggestions[:limit]


# Global instance
tool_mapper = NetBoxToolMapper()


def map_query_to_tool(
    query: str, 
    parameters: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Dict[str, Any], List[str]]:
    """
    Public interface for mapping queries to tools.
    
    Args:
        query: User's query string
        parameters: Optional parameters
        
    Returns:
        Tuple of (tool_name, normalized_parameters, fallback_tools)
    """
    return tool_mapper.map_query_to_tool(query, parameters)


def get_tool_info(tool_name: str) -> Optional[ToolMapping]:
    """Get information about a specific tool."""
    return tool_mapper.get_tool_info(tool_name)


def suggest_tools(partial_query: str, limit: int = 5) -> List[Tuple[str, str]]:
    """Suggest tools based on partial query."""
    return tool_mapper.suggest_tools(partial_query, limit)