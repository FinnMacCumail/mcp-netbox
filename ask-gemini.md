# Ask Gemini: Tool Registry Architecture & Circular Import Resolution

## Context

We are implementing Issue #23 from your previous roadmap: "Creëer @mcp_tool decorator en tool registry" as part of the self-describing server architecture for our NetBox MCP. We have successfully created the `@mcp_tool` decorator and tool registry system, but we've encountered a circular import problem that needs architectural guidance.

## Current Implementation Status

### ✅ Successfully Implemented
1. **Tool Registry System** (`netbox_mcp/registry.py`):
   - `@mcp_tool` decorator with automatic function inspection
   - Global `TOOL_REGISTRY` dictionary storing tool metadata
   - Parameter extraction with type hints support
   - Docstring parsing for structured information
   - Serialization functions for API consumption

2. **Registry Features Working**:
   - Function parameter inspection with types and defaults
   - Return type extraction
   - Docstring parsing (description, args, returns, examples)
   - Tool categorization (system, ipam, dcim, etc.)
   - Complete metadata serialization for API endpoints

### ❌ Current Problem: Circular Import

**Error Encountered**:
```
ImportError: cannot import name 'NetBoxClientManager' from partially initialized module 'netbox_mcp.server' 
(most likely due to a circular import)
```

**Root Cause**:
- `ipam_tools_extension.py` imports `NetBoxClientManager` from `netbox_mcp.server`
- `netbox_mcp.server.py` tries to import `ipam_tools_extension` to register tools
- This creates a circular dependency

## Architecture Questions for Gemini

### 1. Module Structure & Dependency Flow

**Current Structure**:
```
netbox_mcp/
├── registry.py          # @mcp_tool decorator + TOOL_REGISTRY
├── server.py            # FastMCP server + NetBoxClientManager + 18 MCP tools
├── client.py            # NetBoxClient (dynamic proxy architecture)
└── config.py            # Configuration management

ipam_tools_extension.py  # Additional IPAM tools (outside package)
```

**Questions**:
- Should we move `NetBoxClientManager` to a separate module (e.g., `client_manager.py`) to break the circular dependency?
- Is it better to keep extension tools inside the package (`netbox_mcp/tools/`) or outside?
- Should we create a dedicated `tools/` subpackage with `__init__.py` for automatic discovery?

### 2. Tool Registration Strategy

**Current Approach**:
```python
# In server.py - trying to import extension tools
try:
    import ipam_tools_extension  # This causes circular import
    logger.info("IPAM tools extension loaded")
except ImportError:
    logger.warning("Extension not available")
```

**Alternative Approaches**:
A. **Lazy Registration**: Import tools only when needed (deferred imports)
B. **Plugin Discovery**: Scan for tools at runtime using `importlib`
C. **Explicit Registration**: Require tools to register themselves explicitly
D. **Factory Pattern**: Use a factory to create and register tools

**Questions**:
- Which registration strategy best fits our self-describing server architecture?
- Should we support automatic discovery of tools in specific directories?
- How can we ensure tools are registered before the API endpoints need them?

### 3. Dependency Injection for NetBoxClientManager

**Current Issue**: Extension tools need access to `NetBoxClientManager` but importing it creates circular dependency.

**Possible Solutions**:
A. **Singleton Access**: Make NetBoxClientManager accessible via a global registry
B. **Dependency Injection**: Pass client to tools at execution time
C. **Service Locator**: Create a service locator pattern
D. **Context Manager**: Use a context manager for tool execution

**Questions**:
- Which pattern provides the cleanest separation of concerns?
- Should tools receive the client instance as a parameter or access it globally?
- Is there a pattern that maintains testability while avoiding circular imports?

### 4. API Endpoint Architecture

**Planned Endpoints** (from your original roadmap):
- `GET /api/v1/tools` - Discovery endpoint (list all tools)
- `POST /api/v1/execute` - Generic execution endpoint
- `GET /api/v1/status` - Health/status endpoint

**Implementation Questions**:
- Should these be FastAPI endpoints or continue with FastMCP architecture?
- How do we integrate tool discovery with the existing MCP protocol?
- Should we maintain backward compatibility with existing FastMCP tools?

### 5. Tool Categories and Organization

**Current Categories**:
- `system` - Health checks, status monitoring
- `ipam` - IP address management tools
- `dcim` - Data center infrastructure tools (planned)
- `general` - Uncategorized tools

**Questions**:
- Is this categorization sufficient for the full NetBox API coverage?
- Should categories match NetBox app structure (dcim, ipam, circuits, etc.)?
- How should we handle cross-category tools (e.g., bulk operations)?

### 6. Error Handling and Safety Integration

**Current Safety Mechanisms** (from existing architecture):
- `confirm=True` requirement for write operations
- Global dry-run mode
- Comprehensive audit logging
- Type-based cache invalidation

**Questions**:
- How should the tool registry integrate with existing safety mechanisms?
- Should safety requirements be part of tool metadata?
- How do we ensure registered tools follow safety patterns?

### 7. Performance and Caching Considerations

**Current Performance Features**:
- TTL-based caching with 33%+ hit ratios
- Thread-safe singleton client manager
- Dynamic proxy architecture for 100% API coverage

**Questions**:
- Should tool metadata be cached or computed on-demand?
- How do we balance tool discovery performance vs. dynamic registration?
- Should tool execution metrics be tracked in the registry?

## Specific Technical Questions

### A. Circular Import Resolution
```python
# Current problematic structure:
# server.py -> imports ipam_tools_extension
# ipam_tools_extension.py -> imports NetBoxClientManager from server

# Proposed solution options:
# Option 1: Move NetBoxClientManager to separate module
# Option 2: Use lazy imports in extension tools
# Option 3: Dependency injection pattern
```

**Which approach do you recommend for maintaining clean architecture?**

### B. Tool Discovery Implementation
```python
# Should we implement automatic tool discovery like this?
def discover_tools():
    import importlib
    import pkgutil
    for _, name, _ in pkgutil.iter_modules(['netbox_mcp/tools']):
        importlib.import_module(f'netbox_mcp.tools.{name}')
```

**Is this approach robust enough for production use?**

### C. Registry Serialization for API
```python
# Current API serialization:
def serialize_registry_for_api() -> List[Dict[str, Any]]:
    return [serialize_tool_for_api(name) for name in TOOL_REGISTRY.keys()]
```

**Should we add filtering, pagination, or caching for large tool registries?**

## Expected Outcomes

After resolving these architectural questions, we should have:

1. **Clean Module Structure**: No circular imports, clear dependency flow
2. **Extensible Tool System**: Easy to add new tools without breaking existing functionality
3. **Self-Describing API**: Complete tool discovery and execution via REST endpoints
4. **Production Ready**: Robust error handling, performance optimization, safety integration

## Priority Ranking

**High Priority (Blocking)**:
1. Circular import resolution - we cannot proceed without this
2. Tool registration strategy - needed for Issue #24 (discovery endpoint)

**Medium Priority (Important)**:
3. API endpoint architecture - affects implementation of Issues #24-26
4. Dependency injection pattern - affects all future tool development

**Lower Priority (Enhancement)**:
5. Tool categorization refinement
6. Performance optimization for tool discovery

## Request for Gemini

Please provide architectural guidance on:
1. **The best approach to resolve the circular import issue**
2. **Recommended module structure for scalable tool management**
3. **Tool registration strategy that supports both automatic discovery and explicit registration**
4. **Dependency injection pattern that maintains clean separation of concerns**

Your guidance will help us implement a robust, scalable foundation for the self-describing server architecture that can support the full NetBox MCP evolution to v1.0.

Thank you for your continued architectural expertise!

---

**Current Implementation Files**:
- `netbox_mcp/registry.py` - Tool registry and decorator system ✅
- `netbox_mcp/server.py` - Main server with circular import issue ❌  
- `ipam_tools_extension.py` - Extension tools causing circular import ❌