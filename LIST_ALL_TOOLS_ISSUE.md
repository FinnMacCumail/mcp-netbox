# [Feature] Implement Standardized 'list_all_*' Tools for All Major NetBox Models

## Issue Summary

The NetBox MCP toolbox currently suffers from a **critical architectural gap**: while we have excellent "info" tools for retrieving detailed information about specific objects (e.g., `netbox_get_device_info`), we lack the corresponding "list_all" tools for bulk discovery and exploration across NetBox domains.

This gap forces LLMs to improvise with inappropriate tools, leading to errors and poor user experience when asked exploratory questions like "What devices do we have?" or "Show me all our sites."

## Problem Statement

### Current State: Info-Only Pattern
- ✅ **"Info" Tools**: 34 tools for detailed single-object retrieval
- ❌ **"List All" Tools**: Minimal bulk discovery capabilities
- **Result**: LLMs attempt to use info tools for list operations, causing errors

### Business Impact
- **Operational Inefficiency**: Manual NetBox UI navigation required for bulk operations
- **Limited Automation**: Complex API calls needed instead of simple tool invocations
- **Enterprise Gaps**: No standardized bulk reporting for compliance, capacity planning, vendor management
- **Integration Barriers**: External systems cannot efficiently discover NetBox objects

## Proposed Solution: Dual-Tool Pattern

Implement a **systematic dual-tool pattern** for all major NetBox models:

1. **`netbox_get_[model]_info`**: Detailed information about specific objects ✅ (exists)
2. **`netbox_list_all_[models]`**: Bulk discovery with filtering ❌ (missing)

## Critical Missing Tools Analysis

### High Priority Implementation

#### **DCIM Domain**
1. **`netbox_list_all_devices`**
   - **Filters**: site, role, status, manufacturer, tenant
   - **Use Cases**: Inventory audits, compliance reporting, bulk operations
   - **Business Value**: Core infrastructure discovery

2. **`netbox_list_all_sites`**
   - **Filters**: region, status, tenant
   - **Use Cases**: Multi-site management, geographic planning
   - **Business Value**: Enterprise site administration

3. **`netbox_list_all_racks`**
   - **Filters**: site, utilization, status
   - **Use Cases**: Capacity planning, data center optimization
   - **Business Value**: Infrastructure capacity management

#### **IPAM Domain**
4. **`netbox_list_all_prefixes`**
   - **Filters**: site, VRF, tenant, utilization
   - **Use Cases**: Network planning, IP space auditing
   - **Business Value**: Network foundation management

5. **`netbox_list_all_vlans`**
   - **Filters**: site, group, usage, conflicts
   - **Use Cases**: VLAN management, conflict detection
   - **Business Value**: Network segmentation oversight

6. **`netbox_list_all_ip_addresses`**
   - **Filters**: prefix, assignment status, device
   - **Use Cases**: IP auditing, assignment tracking, cleanup
   - **Business Value**: IP space management

#### **Tenancy Domain**
7. **`netbox_list_all_tenants`**
   - **Filters**: group, status, resource counts
   - **Use Cases**: Multi-tenant administration, billing, auditing
   - **Business Value**: Enterprise tenant management

### Medium Priority Implementation

8. **`netbox_list_all_manufacturers`** - Vendor analysis and standardization
9. **`netbox_list_all_device_types`** - Hardware standardization and procurement
10. **`netbox_list_all_device_roles`** - Network architecture analysis
11. **`netbox_list_all_vrfs`** - Advanced networking and isolation auditing
12. **`netbox_list_all_tenant_groups`** - Organizational management
13. **`netbox_list_all_contacts`** - Contact management and operational procedures

## Implementation Specification

### Tool Template Pattern

Each `list_all_*` tool should follow this standardized pattern:

```python
@mcp_tool(category="[domain]")
def netbox_list_all_[models](
    client: NetBoxClient,
    limit: int = 100,
    [domain_specific_filters]: str = None,
    site_name: str = None,
    tenant_name: str = None,
    status: str = None
) -> Dict[str, Any]:
    """
    Get summarized list of [models] with optional filtering.
    
    Args:
        client: NetBoxClient instance (injected by dependency system)
        limit: Maximum number of results to return (default: 100)
        [specific filters for the model type]
        site_name: Filter by site name (optional)
        tenant_name: Filter by tenant name (optional)  
        status: Filter by status (optional)
        
    Returns:
        Dictionary containing:
        - count: Total number of objects found
        - [models]: List of summarized object information
        - filters_applied: Dictionary of filters that were applied
        - summary_stats: Optional aggregate statistics
        
    Example:
        netbox_list_all_devices(site_name="datacenter-1", role_name="switch")
        netbox_list_all_prefixes(vrf_name="TENANT-A", utilization_gte=80)
    """
    try:
        # Build filters dictionary
        filters = {}
        if site_name:
            filters['site'] = site_name
        if tenant_name:
            filters['tenant'] = tenant_name
        if status:
            filters['status'] = status
        # Add domain-specific filters...
        
        # Execute filtered query
        objects = client.[domain].[models].filter(**filters)[:limit]
        
        # Return summarized, human-readable format
        result = {
            "count": len(objects),
            "[models]": [
                {
                    "name": obj.name,
                    "status": obj.status.label if hasattr(obj.status, 'label') else str(obj.status),
                    # Include key identifying and status information
                    # Keep response concise but informative
                }
                for obj in objects
            ],
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
            "summary_stats": {
                # Optional: Include aggregate statistics when relevant
                # e.g., utilization percentages, counts by category
            }
        }
        
        logger.info(f"Found {len(result['[models]'])} [models] matching criteria")
        return result
        
    except Exception as e:
        logger.error(f"Error listing [models]: {e}")
        return {
            "count": 0,
            "[models]": [],
            "error": str(e),
            "error_type": type(e).__name__
        }
```

### Design Principles

1. **Consistent Interface**: All tools follow the same parameter and response patterns
2. **Flexible Filtering**: Support for common filters (site, tenant, status) plus domain-specific filters
3. **Human-Readable Output**: Summarized information optimized for LLM consumption
4. **Performance Aware**: Pagination and result limits to handle large datasets
5. **Error Handling**: Comprehensive error handling with structured responses
6. **Logging**: Detailed logging for troubleshooting and audit trails

### Response Format Standardization

All `list_all_*` tools should return:
```json
{
    "count": 42,
    "[objects]": [
        {
            "name": "object-name",
            "status": "active", 
            "site": "datacenter-1",
            "tenant": "customer-a",
            // 3-5 key identifying fields
        }
    ],
    "filters_applied": {
        "site_name": "datacenter-1",
        "status": "active"
    },
    "summary_stats": {
        "total_utilization": "65%",
        "status_breakdown": {"active": 38, "offline": 4}
    }
}
```

## Implementation Plan

### Phase 1: High-Impact Foundation (v0.9.8)
1. `netbox_list_all_devices` - Template implementation
2. `netbox_list_all_sites` - Multi-site management
3. `netbox_list_all_tenants` - Multi-tenant operations
4. `netbox_list_all_prefixes` - Network foundation

### Phase 2: Operational Efficiency (v0.9.9)  
5. `netbox_list_all_racks` - Capacity management
6. `netbox_list_all_vlans` - Network segmentation
7. `netbox_list_all_ip_addresses` - IP space management

### Phase 3: Specialized Operations (v1.0.0)
8. Remaining tools for vendor management, hardware standardization, and advanced networking

## Success Criteria

- [ ] All major NetBox models have corresponding `list_all_*` tools
- [ ] LLMs can successfully answer exploratory questions without errors
- [ ] Consistent filtering and response patterns across all tools
- [ ] Performance optimization for large datasets
- [ ] Comprehensive test coverage for all new tools
- [ ] Documentation update with dual-tool pattern explanation

## Technical Impact

- **Tool Count**: +13 new enterprise tools (increasing from 34 to 47+ tools)
- **Architecture**: Establishes dual-tool pattern as standard practice
- **User Experience**: Eliminates LLM improvisation errors
- **Enterprise Value**: Enables bulk operations, compliance reporting, and system integration
- **Scalability**: Provides foundation for future NetBox domain expansion

This enhancement transforms the NetBox MCP from a detail-focused tool into a comprehensive enterprise platform capable of both granular object management and bulk discovery operations.