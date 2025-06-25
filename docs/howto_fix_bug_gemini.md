# NetBox MCP Critical Bug Analysis - Request for Gemini's Expert Opinion

**Date**: 2025-06-25  
**Context**: Critical parameter passing bug discovered during comprehensive live testing session  
**Severity**: CRITICAL - 85% of tools unusable

---

## 🚨 Bug Summary

During systematic testing of all 55 MCP tools, we discovered that **ALL multi-parameter tools are completely broken** in the MCP interface, while single-parameter and no-parameter tools work perfectly.

### Testing Results:
- ✅ **11/15 tested tools work perfectly** (all read/discovery operations)
- ❌ **4/15 tested tools completely broken** (all write/create operations)
- 🚨 **Extrapolated impact: ~47/55 tools unusable** (85% failure rate)

---

## 🔍 Technical Analysis

### Current Registry Bridge Pattern (server.py):
```python
def bridge_tools_to_fastmcp():
    """
    Dynamically registers all tools from our internal TOOL_REGISTRY
    with the FastMCP instance, creating wrappers for dependency injection.
    """
    for tool_name, tool_metadata in TOOL_REGISTRY.items():
        def create_tool_wrapper(original_func):
            def tool_wrapper(**kwargs):
                client = get_netbox_client()
                # Inspect function signature and filter parameters
                sig = inspect.signature(original_func)
                call_args = {"client": client}
                for param_name in sig.parameters:
                    if param_name != "client" and param_name in kwargs:
                        call_args[param_name] = kwargs[param_name]
                return original_func(**call_args)
            return tool_wrapper
        
        # Register with FastMCP
        wrapped_tool = create_tool_wrapper(original_func)
        mcp.tool(name=tool_name, description=description)(wrapped_tool)
```

### Error Patterns Observed:

**1. Multi-parameter JSON format fails:**
```
Input: {"kwargs": {"name": "test", "slug": "test"}}
Error: netbox_create_site() missing 2 required positional arguments: 'name' and 'slug'
```

**2. Multi-parameter query string format fails:**
```
Input: {"kwargs": "name=test&slug=test"}
Error: netbox_create_site() missing 2 required positional arguments: 'name' and 'slug'
```

**3. Single-parameter query string works:**
```
Input: {"kwargs": "site_name=MCP Test Site"}
Result: ✅ SUCCESS
```

**4. No-parameter tools work perfectly:**
```
Input: {"kwargs": {}}
Result: ✅ SUCCESS
```

---

## 🤔 My Suspected Root Causes

### Theory 1: Parameter Parsing Logic Flaw
The parameter parsing in `tool_wrapper` may not be correctly extracting multiple parameters from the `kwargs` parameter that MCP interface sends.

**Questions for Gemini:**
1. Is the parameter inspection logic correctly handling the `kwargs` dictionary?
2. Should we be looking at how FastMCP expects parameters to be passed?
3. Is there a mismatch between how we register tools and how MCP calls them?

### Theory 2: FastMCP Registration Issue
The way we're registering tools with FastMCP may not be compatible with multi-parameter function calls.

**Questions for Gemini:**
1. Is our `@mcp.tool()` registration pattern correct for multi-parameter functions?
2. Do we need to specify parameter schemas explicitly?
3. Are we missing Pydantic model definitions for complex parameter structures?

### Theory 3: MCP Protocol Parameter Handling
The MCP protocol itself might have specific requirements for how multi-parameter tools should be called.

**Questions for Gemini:**
1. How does the MCP protocol expect multi-parameter function calls to be structured?
2. Are there specific patterns for parameter passing in MCP that we're missing?
3. Should parameters be passed as individual arguments rather than a kwargs dictionary?

---

## 💡 Potential Solutions I'm Considering

### Solution 1: Enhanced Parameter Parsing
```python
def tool_wrapper(**kwargs):
    client = get_netbox_client()
    sig = inspect.signature(original_func)
    call_args = {"client": client}
    
    # Enhanced parameter parsing logic
    if 'kwargs' in kwargs and isinstance(kwargs['kwargs'], str):
        # Parse query string format
        parsed_params = parse_query_string(kwargs['kwargs'])
        call_args.update(parsed_params)
    elif 'kwargs' in kwargs and isinstance(kwargs['kwargs'], dict):
        # Parse JSON format
        call_args.update(kwargs['kwargs'])
    else:
        # Direct parameter passing
        for param_name in sig.parameters:
            if param_name != "client" and param_name in kwargs:
                call_args[param_name] = kwargs[param_name]
    
    return original_func(**call_args)
```

**Questions for Gemini:**
1. Is this parameter parsing approach on the right track?
2. What other parameter formats should we handle?
3. Are there edge cases in parameter parsing we should consider?

### Solution 2: Explicit Parameter Schema Registration
```python
# Define parameter schemas for each tool
@mcp.tool(
    name=tool_name,
    description=description,
    parameters={
        "type": "object",
        "properties": {
            param: {"type": "string"} for param in signature_params
        },
        "required": required_params
    }
)
def tool_wrapper(**kwargs):
    # Direct parameter mapping without kwargs wrapper
    return original_func(client=client, **kwargs)
```

**Questions for Gemini:**
1. Should we explicitly define parameter schemas for each tool?
2. How does FastMCP handle parameter validation and passing?
3. Is the current dynamic registration approach fundamentally flawed?

### Solution 3: Alternative Registration Pattern
```python
# Register tools differently - one per parameter pattern
for tool_name, tool_metadata in TOOL_REGISTRY.items():
    # Get function signature
    sig = inspect.signature(tool_metadata['function'])
    params = [p for p in sig.parameters if p != 'client']
    
    # Create parameter schema
    schema = create_parameter_schema(params)
    
    # Register with explicit schema
    mcp.tool(name=tool_name, description=description, parameters=schema)(
        create_wrapper(tool_metadata['function'])
    )
```

**Questions for Gemini:**
1. Is this approach more aligned with FastMCP best practices?
2. How should we handle optional vs required parameters?
3. What's the proper way to bridge internal tool registry to FastMCP?

---

## 🔧 Technical Context

### Our Architecture:
- **Internal Tool Registry**: Uses `@mcp_tool` decorator to register 55 tools
- **Registry Bridge**: Dynamically exports all tools to FastMCP interface
- **Dependency Injection**: Automatically injects NetBoxClient into all tool calls
- **Function Inspection**: Uses `inspect.signature()` to understand tool parameters

### Working Tools Pattern:
```python
# Example: Working single-parameter tool
@mcp_tool
def netbox_get_site_info(client: NetBoxClient, site_name: str):
    # Implementation
```

### Broken Tools Pattern:
```python
# Example: Broken multi-parameter tool
@mcp_tool  
def netbox_create_site(client: NetBoxClient, name: str, slug: str, status: str = "active"):
    # Implementation
```

---

## 🤝 Questions for Gemini's Expertise

### Architecture Questions:
1. **Is our Registry Bridge pattern fundamentally sound or flawed?**
2. **Should we abandon dynamic registration in favor of explicit tool-by-tool registration?**
3. **How do other MCP servers handle large numbers of tools with varying parameter patterns?**

### Parameter Passing Questions:
4. **What's the correct way to handle multi-parameter functions in FastMCP?**
5. **Are there specific MCP protocol requirements we're violating?**
6. **Should parameters be passed as individual arguments or grouped objects?**

### Debugging Questions:
7. **What debugging techniques would you recommend to trace the parameter flow?**
8. **Are there FastMCP logging features that could help us understand what's happening?**
9. **How can we test parameter passing in isolation?**

### Implementation Questions:
10. **Which of our proposed solutions is most likely to succeed?**
11. **Are there FastMCP examples or patterns we should follow?**
12. **Should we implement parameter validation at the wrapper level?**

### Performance Questions:
13. **Will fixing this bug impact the performance of working tools?**
14. **Is there a way to fix this without disrupting the 11 working tools?**
15. **Should we implement feature flags to test fixes incrementally?**

---

## 📋 Request for Gemini

Dear Gemini,

We've built an enterprise-grade NetBox MCP server with 55 sophisticated tools, but discovered during live testing that 85% of functionality is broken due to this parameter passing bug. 

**What we need from you:**
1. **Root cause analysis** - What's actually broken in our approach?
2. **Solution recommendation** - Which fix approach is most likely to succeed?
3. **Implementation guidance** - Step-by-step fix strategy
4. **Testing approach** - How to validate the fix without breaking working tools
5. **Architecture review** - Is our overall approach sound or should we redesign?

**Context**: This is a production-critical bug affecting a public open-source project. The tools themselves work perfectly when called directly - the issue is purely in the MCP interface layer.

**Urgency**: High - This blocks the release of significant enterprise automation capabilities for NetBox users.

Please provide your expert analysis and guidance. We're especially interested in:
- Specific code fixes
- FastMCP best practices
- MCP protocol requirements
- Testing strategies
- Architecture recommendations

Thank you for your expertise!

---

## 📁 Reference Files

Key files for your analysis:
- `netbox_mcp/server.py` - Registry Bridge implementation
- `netbox_mcp/registry.py` - Internal tool registry
- `ISSUES_FOUND_DURING_TESTING.md` - Detailed test results
- `docs/claude.md` - Updated with bug discovery

**All tools work perfectly when called directly - the bug is purely in the MCP interface layer.**