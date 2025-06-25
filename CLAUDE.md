# Claude Code Memory & Context Documentation

## 🎯 Project Context: NetBox MCP Server v0.9.8

**Repository**: NetBox Model Context Protocol Server  
**Purpose**: Enterprise-grade MCP server providing 45 tools for NetBox DCIM/IPAM management  
**Architecture**: Dual-tool pattern (info + list_all) with Registry Bridge design  

### 🏗️ Architecture Highlights
- **45 MCP Tools**: Complete DCIM, IPAM, tenancy coverage
- **Dual-Tool Pattern**: Every domain has both detailed retrieval (`info`) and bulk discovery (`list_all`) tools
- **Registry Bridge**: Internal tool registry bridges to FastMCP interface with dependency injection
- **Enterprise Safety**: Dry-run mode, confirmation requirements, audit logging

---

## 🐛 Critical Bug Patterns Discovered & Fixed

### 1. Dictionary Access Pattern Issue (CRITICAL)

**Problem**: NetBox API returns dictionaries, not objects with attributes
```python
# CRASHES with AttributeError
status = site.status.label  
name = device.manufacturer.name
```

**Root Cause**: All 11 `list_all` tools used object attribute access pattern
**Impact**: All bulk discovery tools failing with `AttributeError: "'dict' object has no attribute 'status'"`

**Solution**: Defensive dictionary access pattern applied to ALL tools
```python
# SAFE defensive pattern
status_obj = site.get("status", {})
if isinstance(status_obj, dict):
    status = status_obj.get("label", "N/A")
else:
    status = str(status_obj) if status_obj else "N/A"
```

**Fixed Tools**: All 11 list_all tools converted:
- ✅ `netbox_list_all_sites`, `netbox_list_all_devices`, `netbox_list_all_racks` (high-priority)
- ✅ `netbox_list_all_tenants`, `netbox_list_all_prefixes`, `netbox_list_all_vlans` (high-priority)  
- ✅ `netbox_list_all_manufacturers`, `netbox_list_all_device_types`, `netbox_list_all_device_roles` (medium-priority)
- ✅ `netbox_list_all_vrfs`, `netbox_list_all_tenant_groups` (medium-priority)

### 2. LLM Parameter Passing Patterns (CRITICAL)

**Problem**: LLMs send parameters in unexpected nested formats instead of direct parameters

**Pattern 1 - JSON String in kwargs**:
```json
// LLM sends this:
{"kwargs": "{\"device_name\": \"test-sw-123\"}"}

// Instead of expected:
{"device_name": "test-sw-123"}
```

**Pattern 2 - Query String in kwargs**:
```json
// LLM sends this:
{"kwargs": "name=test-sw-123"}

// Instead of expected:
{"device_name": "test-sw-123"}
```

**Root Cause**: Different LLM clients structure tool calls differently, especially Claude Desktop app

**Solution**: Enhanced `tool_wrapper` in `server.py` with intelligent parsing:
```python
# Multi-format parameter parsing
if len(kwargs) == 1 and 'kwargs' in kwargs and isinstance(kwargs['kwargs'], str):
    kwargs_string = kwargs['kwargs']
    
    # Try JSON first
    try:
        actual_params = json.loads(kwargs_string)
        kwargs = actual_params
    except json.JSONDecodeError:
        # Try query string format
        if '=' in kwargs_string:
            key, value = kwargs_string.split('=', 1)
            # Smart parameter mapping (name -> device_name)
            if key == 'name' and 'device_name' in function_signature:
                key = 'device_name'
            kwargs = {key: value}
```

**Result**: Robust handling of all known LLM parameter passing patterns

---

## 📁 File Structure & Key Locations

### Core Infrastructure
- `netbox_mcp/server.py` - Main MCP server with Registry Bridge pattern
- `netbox_mcp/registry.py` - Internal tool registry and metadata system
- `netbox_mcp/client.py` - NetBox API client with caching and safety controls
- `netbox_mcp/dependencies.py` - Dependency injection system for client management

### Tool Categories (45 tools total)
- `netbox_mcp/tools/dcim/` - Data Center Infrastructure (sites, devices, racks, etc.)
- `netbox_mcp/tools/ipam/` - IP Address Management (prefixes, VLANs, VRFs, etc.)
- `netbox_mcp/tools/tenancy/` - Multi-tenant management (tenants, groups)

### Configuration & Deployment
- `netbox_mcp/config.py` - Configuration management with environment variable support
- `docker/` - Enterprise containerization with health checks
- `/Users/elvis/mcp/netbox-mcp/` - **DEPLOYMENT DIRECTORY** (fresh clones for testing)

---

## 🔧 Development Workflow Learned

### Bug Investigation Process
1. **Screenshot Analysis** - Look for TypeError vs AttributeError patterns
2. **Parameter Structure** - Check if LLM sends nested kwargs vs direct parameters  
3. **API Response Format** - Verify if NetBox returns dicts vs objects
4. **Tool Registry** - Confirm tools are properly bridged to FastMCP

### Fix Implementation Pattern
1. **Identify Pattern** - Dictionary access vs parameter parsing issue
2. **Apply Systematically** - Fix all affected tools with consistent pattern
3. **Test with Fresh Clone** - Always deploy to `/Users/elvis/mcp/netbox-mcp`
4. **Git Workflow** - Commit with detailed messages explaining root cause

### Testing Strategy
- Use specific device names like `test-sw-20250622-183126` for verification
- Test both `info` tools (single object) and `list_all` tools (bulk discovery)
- Verify error messages change from AttributeError to successful responses

---

## 🎛️ User Preferences & Context

**User**: Elvis, experienced developer
**Language**: Dutch/Nederlands preferred for communication
**Location**: Netherlands (timezone considerations)
**Testing Approach**: Methodical, prefers understanding root causes
**Git Workflow**: Likes detailed commit messages with context

### User's Environment
- **Development**: `/Users/elvis/Developer/github/netbox-mcp/`
- **Testing**: `/Users/elvis/mcp/netbox-mcp/` (fresh clones)
- **Platform**: macOS (Darwin 22.6.0)

---

## 🚀 Current Status (v0.9.8)

### ✅ Completed Fixes
- **All 11 list_all tools** converted to defensive dictionary access pattern
- **tool_wrapper enhanced** with multi-format parameter parsing (JSON + query string)
- **Fresh deployment** to testing directory with all fixes
- **Comprehensive error handling** and logging for debugging

### 🎯 Ready for Testing
All known AttributeError and TypeError patterns have been systematically addressed. The server should now handle:
- Different NetBox API response formats (dict vs object)
- Various LLM parameter passing patterns (direct, JSON nested, query string nested)
- Robust parameter name mapping and fallback strategies

### 📝 Future Considerations
- Monitor for new LLM parameter passing patterns
- Consider adding more sophisticated parameter parsing if needed
- Track performance impact of defensive programming patterns
- Document any new error patterns that emerge during testing

---

*Last Updated: 2025-01-24 - NetBox MCP v0.9.8 with comprehensive bug fixes*