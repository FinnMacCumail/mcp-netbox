# NetBox MCP - Development Guide

## 1. Introduction

Welcome to the development guide for the **NetBox Model Context Protocol (MCP) Server v0.9.8**. This document is the central source of truth for developing new tools and extending the functionality of this enterprise-grade MCP server.

The NetBox MCP provides **45 specialized tools** that enable Large Language Models to interact intelligently with NetBox network documentation and IPAM systems through a sophisticated dual-tool pattern architecture.

## 2. Current Architecture Overview

### 2.1 Production Status
- **Version**: 0.9.8 - Dual-Tool Pattern Architecture Complete
- **Tool Count**: 45 MCP tools covering all NetBox domains
- **Architecture**: Hierarchical domain structure with Registry Bridge pattern
- **Safety**: Enterprise-grade with dry-run mode, confirmation requirements, audit logging

### 2.2 Core Components

#### Registry Bridge Pattern
```
Internal Tool Registry (@mcp_tool) → Registry Bridge → FastMCP Interface
```

- **Tool Registry** (`netbox_mcp/registry.py`): Core `@mcp_tool` decorator with automatic function inspection
- **Registry Bridge** (`netbox_mcp/server.py`): Dynamic tool export with dependency injection
- **Dependency Injection** (`netbox_mcp/dependencies.py`): Thread-safe singleton client management
- **Client Layer** (`netbox_mcp/client.py`): Enhanced NetBox API client with caching and safety controls

#### Dual-Tool Pattern Implementation
Every NetBox domain implements both:
1. **"Info" Tools**: Detailed single-object retrieval (e.g., `netbox_get_device_info`)
2. **"List All" Tools**: Bulk discovery for exploratory queries (e.g., `netbox_list_all_devices`)

This fundamental LLM architecture ensures both detailed inspection AND bulk exploration capabilities.

## 3. Project Structure

### 3.1 Hierarchical Domain Structure
```
netbox-mcp/
├── docs/                           # Documentation including this guide
├── netbox_mcp/
│   ├── server.py                   # Main MCP server with Registry Bridge
│   ├── registry.py                 # @mcp_tool decorator and tool registry
│   ├── client.py                   # Enhanced NetBox API client
│   ├── dependencies.py             # Dependency injection system
│   ├── config.py                   # Configuration management
│   └── tools/                      # Hierarchical domain structure
│       ├── __init__.py             # Automatic tool discovery
│       ├── system/                 # System monitoring tools
│       │   └── health.py           # Health check tools
│       ├── dcim/                   # Data Center Infrastructure
│       │   ├── sites.py            # Site management (2 tools)
│       │   ├── racks.py            # Rack management (3 tools)
│       │   ├── devices.py          # Device lifecycle (4 tools)
│       │   ├── manufacturers.py    # Manufacturer management (2 tools)
│       │   ├── device_types.py     # Device type management (2 tools)
│       │   ├── device_roles.py     # Device role management (2 tools)
│       │   └── interfaces.py       # Interface & cable management (2 tools)
│       ├── ipam/                   # IP Address Management
│       │   ├── prefixes.py         # Prefix management (2 tools)
│       │   ├── vlans.py            # VLAN management (3 tools)
│       │   ├── vrfs.py             # VRF management (2 tools)
│       │   └── ip_addresses.py     # IP address tools (7 tools)
│       └── tenancy/                # Multi-tenant management
│           ├── tenants.py          # Tenant lifecycle (3 tools)
│           └── tenant_groups.py    # Tenant group management (2 tools)
└── tests/                          # Test structure mirrors tools
```

### 3.2 Tool Distribution by Domain
- **System Tools** (1): Health monitoring
- **DCIM Tools** (22): Complete device lifecycle with dual-tool pattern
- **IPAM Tools** (15): IP and network management with comprehensive discovery
- **Tenancy Tools** (7): Multi-tenant resource management

## 4. Development Standards

### 4.1 The @mcp_tool Decorator Pattern

Every tool function must follow this pattern:

```python
from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

@mcp_tool(category="dcim")
def netbox_example_tool(
    client: NetBoxClient,
    required_param: str,
    optional_param: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Tool description for LLM context.
    
    Args:
        client: NetBoxClient instance (injected automatically)
        required_param: Description of required parameter
        optional_param: Description of optional parameter
        confirm: Must be True for write operations (safety mechanism)
        
    Returns:
        Structured result dictionary
        
    Example:
        netbox_example_tool("param_value", confirm=True)
    """
    try:
        if not required_param:
            return {
                "success": False,
                "error": "Required parameter is missing",
                "error_type": "ValidationError"
            }
        
        logger.info(f"Executing example tool with param: {required_param}")
        
        # Implementation logic here
        
        return {
            "success": True,
            "action": "completed",
            "result": "operation_result"
        }
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
```

### 4.2 Defensive Dictionary Access Pattern

**Critical**: All `list_all` tools must use defensive dictionary access since NetBox API returns dictionaries, not objects:

```python
# WRONG - Will cause AttributeError
status = device.status.label

# CORRECT - Defensive pattern
status_obj = device.get("status", {})
if isinstance(status_obj, dict):
    status = status_obj.get("label", "N/A")
else:
    status = str(status_obj) if status_obj else "N/A"
```

This pattern is **mandatory** for all tools that process NetBox API responses.

### 4.3 Enterprise Safety Requirements

#### Write Operation Safety
All write operations must include:
```python
# 1. Confirmation requirement
if not confirm:
    return {
        "success": False,
        "error": "Confirmation required for write operations",
        "error_type": "ConfirmationError"
    }

# 2. Conflict detection with cache bypass
existing = client.api.objects.filter(name=name, no_cache=True)
if existing:
    return {
        "success": False,
        "error": f"Object '{name}' already exists",
        "error_type": "ConflictError"
    }
```

#### Error Handling Standards
```python
try:
    # Operation logic
    result = client.api.operation()
    
    return {
        "success": True,
        "action": "created",
        "object_type": "device",
        "result": result
    }
    
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return {
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__
    }
```

## 5. Tool Registration and Discovery

### 5.1 Automatic Registration
Tools are automatically discovered and registered through:

1. **Domain Module Import**: Add tool to appropriate domain file
2. **Decorator Registration**: `@mcp_tool` automatically registers with internal registry
3. **Registry Bridge**: `bridge_tools_to_fastmcp()` exports all tools to MCP interface
4. **Dependency Injection**: Client automatically injected via wrapper functions

### 5.2 Making Tools Discoverable

Add new tools to the appropriate domain file and ensure they're properly imported:

```python
# In tools/dcim/devices.py
@mcp_tool(category="dcim")
def netbox_new_device_tool(client: NetBoxClient, ...):
    # Tool implementation
    pass

# Domain __init__.py is not required - automatic discovery handles imports
```

## 6. Testing and Validation

### 6.1 Tool Registry Validation
Test tool registration:
```python
python -c "
from netbox_mcp.registry import TOOL_REGISTRY
print(f'Total tools: {len(TOOL_REGISTRY)}')
for name, meta in TOOL_REGISTRY.items():
    print(f'  {name}: {meta[\"category\"]}')
"
```

### 6.2 Development Testing
1. **Local Development**: Test against your NetBox instance
2. **Registry Validation**: Verify tool appears in registry
3. **MCP Interface Testing**: Test via Claude Code or MCP client
4. **Error Handling**: Test failure scenarios and validation

### 6.3 Parameter Parsing Robustness
The enhanced `tool_wrapper` handles multiple LLM parameter passing patterns:
- Direct parameters: `{"device_name": "value"}`
- JSON nested: `{"kwargs": "{\"device_name\": \"value\"}"}`
- Query string nested: `{"kwargs": "device_name=value"}`

## 7. Common Patterns and Examples

### 7.1 Dual-Tool Pattern Implementation

**Info Tool** (detailed retrieval):
```python
@mcp_tool(category="dcim")
def netbox_get_device_info(
    client: NetBoxClient,
    device_name: str,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed information about ONE specific device by name."""
    # Implementation for single device lookup
```

**List All Tool** (bulk discovery):
```python
@mcp_tool(category="dcim") 
def netbox_list_all_devices(
    client: NetBoxClient,
    limit: int = 100,
    site_name: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Get summarized list of devices with optional filtering."""
    # Implementation for bulk device discovery with filtering
```

### 7.2 Cross-Domain Integration
```python
# Example: Device provisioning with IP assignment
@mcp_tool(category="dcim")
def netbox_provision_device_with_ip(
    client: NetBoxClient,
    device_name: str,
    device_type: str,
    site: str,
    ip_address: str,
    confirm: bool = False
) -> Dict[str, Any]:
    """Enterprise tool combining DCIM device creation with IPAM IP assignment."""
    # Multi-domain operation with atomic rollback capabilities
```

## 8. Migration and Architecture Notes

### 8.1 Hierarchical Architecture Status
- **Complete**: System, DCIM, IPAM, and Tenancy domains fully migrated
- **Tool Count**: All 45 tools accessible via MCP interface
- **Registry Bridge**: Fully operational with dependency injection
- **Legacy Code**: All flat files removed, clean hierarchical structure

### 8.2 Recent Architecture Fixes
- **v0.9.6**: Tool loading conflict resolution - removed legacy flat files
- **v0.9.7**: Registry Bridge implementation - connected internal registry to MCP interface
- **v0.9.8**: Enhanced parameter parsing - robust LLM parameter handling

## 9. Development Workflow

### 9.1 Adding New Tools
1. **Identify Domain**: Determine which domain your tool belongs to
2. **Create Function**: Follow the `@mcp_tool` decorator pattern
3. **Implement Logic**: Use defensive programming and enterprise safety patterns
4. **Test Locally**: Validate tool registration and functionality
5. **Document**: Add appropriate docstrings and examples

### 9.2 Deployment and Testing
- **Development Directory**: `/Users/elvis/Developer/github/netbox-mcp/`
- **Testing Directory**: `/Users/elvis/mcp/netbox-mcp/` (fresh clones for testing)
- **Git Workflow**: Commit with detailed messages explaining functionality

## 10. Future Development

### 10.1 Extension Points
- **New Domains**: Easy addition of new NetBox domains as they become available
- **Enhanced Tools**: Build upon dual-tool pattern for domain-specific workflows
- **Integration Tools**: Cross-domain operations leveraging multiple NetBox APIs

### 10.2 Architecture Scalability
The hierarchical domain structure and Registry Bridge pattern support:
- **Unlimited Tool Growth**: No architectural limits on tool count
- **Domain Expansion**: Easy addition of new NetBox domains
- **Enterprise Features**: Built-in safety, caching, and performance optimization

---

This guide represents the current state of the **enterprise-grade NetBox MCP Server v0.9.8** with comprehensive dual-tool pattern architecture and hierarchical domain organization. All development should follow these established patterns to maintain the high standards of quality, safety, and scalability that define this platform.