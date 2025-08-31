"""
NetBox MCP Tool Registry for Read-Only Operations
Week 9-12: Real NetBox Integration & Advanced Conversation Management

This module defines and organizes read-only NetBox MCP tools for safe infrastructure
exploration and analysis. Excludes create/update/delete operations to ensure
production safety during initial real NetBox integration.
"""

import logging
from typing import Dict, List, Set, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of read-only NetBox operations"""
    DISCOVERY = "discovery"
    ANALYSIS = "analysis"
    STATUS = "status"
    HEALTH = "health"


class ToolComplexity(Enum):
    """Tool execution complexity levels for orchestration strategy"""
    SIMPLE = "simple"          # Single API call, fast response
    MODERATE = "moderate"      # Multiple API calls, moderate response time
    COMPLEX = "complex"        # Many API calls, longer response time


class ReadOnlyToolRegistry:
    """
    Registry of read-only NetBox MCP tools organized by category and complexity.
    
    Provides safe tool discovery, validation, and metadata for the LangGraph
    orchestration system to intelligently coordinate real NetBox operations.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._tool_registry = self._initialize_tool_registry()
    
    def _initialize_tool_registry(self) -> Dict[str, Dict[str, Any]]:
        """Initialize comprehensive read-only tool registry"""
        
        return {
            # === DCIM DISCOVERY TOOLS ===
            "netbox_list_all_sites": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all NetBox sites with filtering capabilities",
                "typical_params": ["limit", "region_name", "status", "tenant_name"],
                "returns": "List of sites with basic information",
                "cache_priority": "high",  # Sites change infrequently
                "estimated_response_time": 1.2
            },
            
            "netbox_get_site_info": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.MODERATE,
                "description": "Get detailed information about a specific site",
                "typical_params": ["site_name"],
                "returns": "Detailed site information including racks and devices",
                "cache_priority": "high",
                "estimated_response_time": 2.1
            },
            
            "netbox_list_all_devices": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.MODERATE,
                "description": "List all NetBox devices with filtering",
                "typical_params": ["limit", "site_name", "role_name", "status", "manufacturer_name"],
                "returns": "List of devices with basic information",
                "cache_priority": "medium",
                "estimated_response_time": 2.8,
                "limitation_patterns": ["token_overflow", "large_result_set"]
            },
            
            "netbox_get_device_info": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.MODERATE,
                "description": "Get comprehensive device information",
                "typical_params": ["device_name", "site", "include_interfaces", "include_cables"],
                "returns": "Detailed device information with interfaces and cables",
                "cache_priority": "medium",
                "estimated_response_time": 3.1
            },
            
            "netbox_get_device_basic_info": {
                "category": ToolCategory.STATUS,
                "complexity": ToolComplexity.SIMPLE,
                "description": "Get basic device information only (lightweight)",
                "typical_params": ["device_name", "site"],
                "returns": "Basic device details without related objects",
                "cache_priority": "medium",
                "estimated_response_time": 1.5
            },
            
            "netbox_list_all_racks": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all racks with optional filtering",
                "typical_params": ["limit", "site_name", "role", "status"],
                "returns": "List of racks with utilization information",
                "cache_priority": "high",
                "estimated_response_time": 1.8
            },
            
            "netbox_get_rack_inventory": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.MODERATE,
                "description": "Get comprehensive rack inventory report",
                "typical_params": ["site_name", "rack_name", "include_detailed"],
                "returns": "Detailed rack inventory with device positions",
                "cache_priority": "medium",
                "estimated_response_time": 2.5
            },
            
            "netbox_get_rack_elevation": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.SIMPLE,
                "description": "Get rack elevation showing device positions",
                "typical_params": ["rack_name", "site"],
                "returns": "Visual rack elevation with device placement",
                "cache_priority": "medium",
                "estimated_response_time": 1.7
            },
            
            # === DCIM INTERFACE AND CABLE ANALYSIS ===
            "netbox_get_device_interfaces": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.COMPLEX,
                "description": "Get device interfaces with pagination support",
                "typical_params": ["device_name", "site", "enabled_only", "interface_type", "limit"],
                "returns": "Device interfaces with comprehensive filtering",
                "cache_priority": "low",  # Interface states change frequently
                "estimated_response_time": 4.2,
                "limitation_patterns": ["n_plus_one_queries", "large_result_set"]
            },
            
            "netbox_get_device_cables": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.COMPLEX,
                "description": "Get device cables with pagination support",
                "typical_params": ["device_name", "site", "cable_type", "cable_status", "limit"],
                "returns": "Device cable connections with detailed information",
                "cache_priority": "medium",
                "estimated_response_time": 3.8,
                "limitation_patterns": ["n_plus_one_queries"]
            },
            
            "netbox_list_all_cables": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.MODERATE,
                "description": "List all cables with optional filtering",
                "typical_params": ["limit", "site_name", "cable_type", "cable_status"],
                "returns": "List of cable connections",
                "cache_priority": "medium",
                "estimated_response_time": 2.9,
                "limitation_patterns": ["token_overflow", "large_result_set"]
            },
            
            "netbox_get_cable_info": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.SIMPLE,
                "description": "Get detailed information about a specific cable",
                "typical_params": ["cable_id", "device_name", "interface_name"],
                "returns": "Detailed cable information and connections",
                "cache_priority": "medium",
                "estimated_response_time": 1.6
            },
            
            # === IPAM TOOLS ===
            "netbox_list_all_vlans": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all VLANs with filtering capabilities",
                "typical_params": ["limit", "site_name", "group_name", "status"],
                "returns": "List of VLANs with basic information",
                "cache_priority": "medium",
                "estimated_response_time": 2.1
            },
            
            "netbox_list_all_prefixes": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.MODERATE,
                "description": "List all IP prefixes with optional filtering",
                "typical_params": ["limit", "site_name", "vrf_name", "family", "status"],
                "returns": "List of IP prefixes with utilization data",
                "cache_priority": "medium",
                "estimated_response_time": 2.4,
                "limitation_patterns": ["large_result_set"]
            },
            
            "netbox_get_prefix_utilization": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.MODERATE,
                "description": "Get comprehensive prefix utilization report",
                "typical_params": ["prefix", "include_child_prefixes", "include_detailed_breakdown"],
                "returns": "Detailed prefix utilization analysis",
                "cache_priority": "low",  # Utilization changes frequently
                "estimated_response_time": 3.2
            },
            
            "netbox_list_all_vrfs": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all VRFs with prefix statistics",
                "typical_params": ["limit", "tenant_name", "enforce_unique"],
                "returns": "List of VRFs with routing information",
                "cache_priority": "high",
                "estimated_response_time": 1.4
            },
            
            # === DEVICE TYPE AND MANUFACTURER TOOLS ===
            "netbox_list_all_manufacturers": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all manufacturers with device type statistics",
                "typical_params": ["limit"],
                "returns": "List of manufacturers with usage statistics",
                "cache_priority": "high",  # Manufacturers rarely change
                "estimated_response_time": 1.1
            },
            
            "netbox_list_all_device_types": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all device types with usage statistics",
                "typical_params": ["limit", "manufacturer_name", "u_height"],
                "returns": "List of device types with specifications",
                "cache_priority": "high",
                "estimated_response_time": 1.5
            },
            
            "netbox_get_device_type_info": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.SIMPLE,
                "description": "Get detailed information about a device type",
                "typical_params": ["manufacturer", "model"],
                "returns": "Comprehensive device type details and specifications",
                "cache_priority": "high",
                "estimated_response_time": 1.3
            },
            
            "netbox_list_all_device_roles": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all device roles with usage statistics",
                "typical_params": ["limit", "vm_role"],
                "returns": "List of device roles with categorization",
                "cache_priority": "high",
                "estimated_response_time": 1.0
            },
            
            # === MODULE MANAGEMENT ===
            "netbox_list_all_modules": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.MODERATE,
                "description": "List all modules with comprehensive details",
                "typical_params": ["limit", "device_name", "module_type"],
                "returns": "List of installed modules with specifications",
                "cache_priority": "medium",
                "estimated_response_time": 2.3
            },
            
            "netbox_list_device_modules": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.MODERATE,
                "description": "List all modules installed on a specific device",
                "typical_params": ["device_name", "limit"],
                "returns": "Device-specific module inventory",
                "cache_priority": "medium",
                "estimated_response_time": 2.0
            },
            
            "netbox_get_module_info": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.SIMPLE,
                "description": "Get detailed information about a specific module",
                "typical_params": ["device_name", "module_bay"],
                "returns": "Comprehensive module details and specifications",
                "cache_priority": "medium",
                "estimated_response_time": 1.4
            },
            
            "netbox_list_all_module_types": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all module types with statistics",
                "typical_params": ["limit", "manufacturer"],
                "returns": "List of available module types",
                "cache_priority": "high",
                "estimated_response_time": 1.2
            },
            
            # === SYSTEM AND HEALTH ===
            "netbox_health_check": {
                "category": ToolCategory.HEALTH,
                "complexity": ToolComplexity.SIMPLE,
                "description": "Get NetBox system health status and connection info",
                "typical_params": [],
                "returns": "System health status and API connectivity",
                "cache_priority": "none",  # Never cache health checks
                "estimated_response_time": 0.8
            },
            
            # === TENANCY TOOLS ===
            "netbox_list_all_tenants": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all tenants with filtering",
                "typical_params": ["limit", "group_name", "status"],
                "returns": "List of tenants with resource counts",
                "cache_priority": "medium",
                "estimated_response_time": 1.6
            },
            
            "netbox_list_all_tenant_groups": {
                "category": ToolCategory.DISCOVERY,
                "complexity": ToolComplexity.SIMPLE,
                "description": "List all tenant groups with statistics",
                "typical_params": ["limit", "parent_name"],
                "returns": "List of tenant groups with hierarchical data",
                "cache_priority": "high",
                "estimated_response_time": 1.3
            },
            
            "netbox_get_tenant_resource_report": {
                "category": ToolCategory.ANALYSIS,
                "complexity": ToolComplexity.COMPLEX,
                "description": "Generate comprehensive tenant resource report",
                "typical_params": ["tenant_name", "include_details", "filter_by_site"],
                "returns": "Complete tenant resource ownership analysis",
                "cache_priority": "low",
                "estimated_response_time": 5.1,
                "limitation_patterns": ["large_result_set", "complex_aggregation"]
            },
            
            # === TEST TOOLS (for integration testing) ===
            "netbox_test_tool": {
                "category": ToolCategory.STATUS,
                "complexity": ToolComplexity.SIMPLE,
                "description": "Test tool for integration testing and validation",
                "typical_params": [],
                "returns": "Test result data for validation",
                "cache_priority": "none",
                "estimated_response_time": 0.5
            },
            
            "netbox_test_optimization": {
                "category": ToolCategory.STATUS,
                "complexity": ToolComplexity.MODERATE,
                "description": "Test tool for cache optimization testing",
                "typical_params": [],
                "returns": "Test result data for cache performance validation",
                "cache_priority": "medium",
                "estimated_response_time": 1.0
            }
        }
    
    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get all tools in a specific category"""
        return [
            tool_name for tool_name, metadata in self._tool_registry.items()
            if metadata["category"] == category
        ]
    
    def get_tools_by_complexity(self, complexity: ToolComplexity) -> List[str]:
        """Get all tools with specific complexity level"""
        return [
            tool_name for tool_name, metadata in self._tool_registry.items()
            if metadata["complexity"] == complexity
        ]
    
    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool"""
        return self._tool_registry.get(tool_name)
    
    def is_read_only_tool(self, tool_name: str) -> bool:
        """Verify if a tool is in the read-only registry"""
        return tool_name in self._tool_registry
    
    def get_tools_with_limitations(self) -> Dict[str, List[str]]:
        """Get tools that have known limitation patterns"""
        tools_with_limitations = {}
        
        for tool_name, metadata in self._tool_registry.items():
            limitations = metadata.get("limitation_patterns", [])
            if limitations:
                for limitation in limitations:
                    if limitation not in tools_with_limitations:
                        tools_with_limitations[limitation] = []
                    tools_with_limitations[limitation].append(tool_name)
        
        return tools_with_limitations
    
    def get_fast_tools(self, max_response_time: float = 2.0) -> List[str]:
        """Get tools with fast response times for direct strategy"""
        return [
            tool_name for tool_name, metadata in self._tool_registry.items()
            if metadata.get("estimated_response_time", 0) <= max_response_time
        ]
    
    def get_discovery_workflow_tools(self) -> List[str]:
        """Get recommended tools for general discovery workflows"""
        return [
            "netbox_health_check",
            "netbox_list_all_sites", 
            "netbox_list_all_devices",
            "netbox_list_all_racks",
            "netbox_list_all_vlans"
        ]
    
    def get_analysis_workflow_tools(self, entity_type: str) -> List[str]:
        """Get recommended tools for detailed analysis of specific entities"""
        workflows = {
            "site": [
                "netbox_get_site_info",
                "netbox_list_all_devices",
                "netbox_list_all_racks"
            ],
            "device": [
                "netbox_get_device_info",
                "netbox_get_device_interfaces",
                "netbox_get_device_cables",
                "netbox_list_device_modules"
            ],
            "rack": [
                "netbox_get_rack_inventory",
                "netbox_get_rack_elevation"
            ],
            "network": [
                "netbox_list_all_vlans",
                "netbox_list_all_prefixes",
                "netbox_get_prefix_utilization"
            ]
        }
        
        return workflows.get(entity_type, [])
    
    def get_tool_import_path(self, tool_name: str) -> Optional[str]:
        """Get the import path for a specific tool function"""
        
        # Map tool names to their module locations
        tool_imports = {
            # DCIM tools
            "netbox_list_all_sites": "netbox_mcp.tools.dcim.sites",
            "netbox_get_site_info": "netbox_mcp.tools.dcim.sites",
            "netbox_list_all_devices": "netbox_mcp.tools.dcim.devices",
            "netbox_get_device_info": "netbox_mcp.tools.dcim.devices",
            "netbox_get_device_basic_info": "netbox_mcp.tools.dcim.devices",
            "netbox_list_all_racks": "netbox_mcp.tools.dcim.racks",
            "netbox_get_rack_inventory": "netbox_mcp.tools.dcim.racks",
            "netbox_get_rack_elevation": "netbox_mcp.tools.dcim.racks",
            "netbox_get_device_interfaces": "netbox_mcp.tools.dcim.devices",
            "netbox_get_device_cables": "netbox_mcp.tools.dcim.cables",
            "netbox_list_all_cables": "netbox_mcp.tools.dcim.cables",
            "netbox_get_cable_info": "netbox_mcp.tools.dcim.cables",
            "netbox_list_all_manufacturers": "netbox_mcp.tools.dcim.manufacturers",
            "netbox_list_all_device_types": "netbox_mcp.tools.dcim.device_types",
            "netbox_get_device_type_info": "netbox_mcp.tools.dcim.device_types",
            "netbox_list_all_device_roles": "netbox_mcp.tools.dcim.device_roles",
            "netbox_list_all_modules": "netbox_mcp.tools.dcim.modules",
            "netbox_list_device_modules": "netbox_mcp.tools.dcim.modules",
            "netbox_get_module_info": "netbox_mcp.tools.dcim.modules",
            "netbox_list_all_module_types": "netbox_mcp.tools.dcim.modules",
            
            # IPAM tools
            "netbox_list_all_vlans": "netbox_mcp.tools.ipam.vlans",
            "netbox_list_all_prefixes": "netbox_mcp.tools.ipam.prefixes",
            "netbox_get_prefix_utilization": "netbox_mcp.tools.ipam.prefixes",
            "netbox_list_all_vrfs": "netbox_mcp.tools.ipam.vrfs",
            
            # System tools
            "netbox_health_check": "netbox_mcp.tools.system.health",
            
            # Tenancy tools
            "netbox_list_all_tenants": "netbox_mcp.tools.tenancy.tenants",
            "netbox_list_all_tenant_groups": "netbox_mcp.tools.tenancy.tenant_groups",
            "netbox_get_tenant_resource_report": "netbox_mcp.tools.tenancy.resources",
            
            # Test tools
            "netbox_test_tool": "tests.mocks.test_tools",
            "netbox_test_optimization": "tests.mocks.test_tools"
        }
        
        return tool_imports.get(tool_name)
    
    def validate_tool_request(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a tool request against registry metadata"""
        
        if not self.is_read_only_tool(tool_name):
            return {
                "valid": False,
                "error": f"Tool '{tool_name}' is not in read-only registry",
                "error_type": "UnauthorizedTool"
            }
        
        metadata = self.get_tool_metadata(tool_name)
        typical_params = metadata.get("typical_params", [])
        
        # Validate parameters (basic validation)
        unknown_params = set(params.keys()) - set(typical_params)
        if unknown_params:
            self.logger.warning(f"Unknown parameters for {tool_name}: {unknown_params}")
        
        return {
            "valid": True,
            "metadata": metadata,
            "estimated_response_time": metadata.get("estimated_response_time", 2.0),
            "cache_priority": metadata.get("cache_priority", "medium"),
            "complexity": metadata.get("complexity", ToolComplexity.MODERATE),
            "limitation_patterns": metadata.get("limitation_patterns", [])
        }
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """Get statistics about the tool registry"""
        
        total_tools = len(self._tool_registry)
        
        # Count by category
        category_counts = {}
        for category in ToolCategory:
            category_counts[category.value] = len(self.get_tools_by_category(category))
        
        # Count by complexity
        complexity_counts = {}
        for complexity in ToolComplexity:
            complexity_counts[complexity.value] = len(self.get_tools_by_complexity(complexity))
        
        # Calculate average response time
        response_times = [
            metadata.get("estimated_response_time", 0) 
            for metadata in self._tool_registry.values()
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_tools": total_tools,
            "category_distribution": category_counts,
            "complexity_distribution": complexity_counts,
            "average_response_time": round(avg_response_time, 2),
            "tools_with_limitations": len([
                tool for tool, metadata in self._tool_registry.items()
                if metadata.get("limitation_patterns")
            ]),
            "registry_version": "week-9-12-real-integration"
        }


# Global registry instance
read_only_tool_registry = ReadOnlyToolRegistry()


def get_read_only_tools() -> List[str]:
    """Get list of all read-only tools"""
    return list(read_only_tool_registry._tool_registry.keys())


def is_safe_read_only_tool(tool_name: str) -> bool:
    """Check if a tool is safe for read-only operations"""
    return read_only_tool_registry.is_read_only_tool(tool_name)