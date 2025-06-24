# [Core] Implement Registry Bridge to Export All Tools to FastMCP Interface

## Issue Summary
Develop a bridge function that dynamically registers all tools from the internal `TOOL_REGISTRY` with the `FastMCP` instance, including a wrapper for dependency injection. This will make all 34 hierarchical tools available to the MCP client.

## Current Situation
- ✅ 34 tools successfully loaded into internal `TOOL_REGISTRY`
- ✅ Hierarchical domain structure working perfectly
- ❌ Tools NOT accessible via MCP interface due to missing bridge

## Root Cause
Two separate registration systems that don't communicate:
- Internal `@mcp_tool` decorator → `TOOL_REGISTRY` (34 tools)
- FastMCP's `@mcp.tool()` decorator → FastMCP registry (18 old tools)

## Solution Architecture
Implement a Registry Bridge that:
1. Removes all old individual tool definitions from server.py
2. Creates dynamic wrappers for dependency injection (NetBoxClient)
3. Registers all TOOL_REGISTRY tools with FastMCP
4. Preserves tool metadata (name, description, category)

## Implementation Steps
1. Clean old tools from server.py (18 definitions, lines 190-1632)
2. Implement `bridge_tools_to_fastmcp()` function
3. Add wrapper functions for client dependency injection
4. Test all 34 tools are accessible via MCP interface

## Success Criteria
- [ ] All 34 tools accessible via MCP interface
- [ ] Proper dependency injection for NetBoxClient
- [ ] No conflicts between old and new definitions
- [ ] Performance equivalent to current system

## Testing
```python
# This should work after implementation:
result = mcp_client.call_tool("netbox_get_rack_inventory", {"rack_name": "Test Rack"})
assert result["success"] == True
```

## Technical Impact
- **Criticality**: High - blocks access to all enterprise tools
- **Scope**: Core MCP functionality
- **Risk**: Low - existing tools continue working, just become accessible