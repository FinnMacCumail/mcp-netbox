# Gemini Code Assist - MCP Parameter Handling Issue

## 🚨 Critical Issue: "Multiple Values for Argument" Error

**Date**: 2025-06-26  
**Severity**: High - All Device Type Component Template Functions Affected  
**Status**: Investigation Required  

## Problem Statement

All NetBox MCP device type component template functions are failing with the exact same error:
```
TypeError: netbox_add_[template_type]_to_device_type() got multiple values for argument 'device_type_model'
```

This affects **ALL** device type component template functions, not just specific ones.

## Affected Functions

**All Device Type Component Template Functions Fail:**
- `netbox_add_interface_template_to_device_type`
- `netbox_add_front_port_template_to_device_type`
- `netbox_add_rear_port_template_to_device_type`
- `netbox_add_console_port_template_to_device_type`
- `netbox_add_power_port_template_to_device_type`
- `netbox_add_console_server_port_template_to_device_type`
- `netbox_add_power_outlet_template_to_device_type`
- `netbox_add_device_bay_template_to_device_type`
- `netbox_add_module_bay_template_to_device_type`

**Error Pattern:**
Every function throws: `got multiple values for argument 'device_type_model'`

## Function Signature Analysis

All affected functions follow the same pattern:

```python
@mcp_tool(category="dcim")
def netbox_add_interface_template_to_device_type(
    device_type_model: str,  # ← This parameter is causing issues
    name: str,
    type: str,
    mgmt_only: bool = False,
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
```

## Working vs Non-Working Functions

**Functions That Work:**
- `netbox_health_check()` ✅
- `netbox_create_device_type()` ✅
- `netbox_list_all_device_types()` ✅
- Most other NetBox MCP functions ✅

**Functions That Don't Work:**
- All device type component template functions ❌

## Test Cases Attempted

### Test 1: Fresh Device Type Creation
```python
# This works perfectly
netbox_create_device_type(
    model="Fresh Test Device",
    manufacturer="ACT", 
    slug="fresh-test-device",
    confirm=True
)  # ✅ SUCCESS
```

### Test 2: Interface Template on Fresh Device
```python
# This fails with parameter error
netbox_add_interface_template_to_device_type(
    device_type_model="Fresh Test Device",
    name="eth0",
    type="1000base-t", 
    confirm=True
)  # ❌ TypeError: got multiple values for argument 'device_type_model'
```

### Test 3: Multiple Template Types
All template types fail with identical error pattern, confirming this is systematic.

## Architecture Context

### MCP Tool Registration System
```python
# In netbox_mcp/registry.py
@mcp_tool(category="dcim")
def netbox_add_interface_template_to_device_type(...):
    # Function implementation
```

### Registry Bridge Pattern  
```python
# In netbox_mcp/server.py
def bridge_tools_to_fastmcp():
    for tool_name, tool_metadata in TOOL_REGISTRY.items():
        # Dynamic tool registration with FastMCP
        def create_tool_wrapper(original_func):
            def tool_wrapper(**kwargs):
                client = get_netbox_client()
                # Parameter inspection and filtering
                sig = inspect.signature(original_func)
                call_args = {"client": client}
                for param_name in sig.parameters:
                    if param_name != "client" and param_name in kwargs:
                        call_args[param_name] = kwargs[param_name]
                return original_func(**call_args)
            return tool_wrapper
```

## Questions for Gemini Code Assist

### 1. Parameter Handling Analysis
**Q:** Why would the Registry Bridge pattern cause "multiple values for argument 'device_type_model'" errors specifically for device type component template functions, but not for other NetBox MCP functions?

**Q:** Is there something about the parameter inspection logic in `create_tool_wrapper()` that could cause duplicate parameter passing?

### 2. Function Signature Investigation  
**Q:** All failing functions have `device_type_model: str` as the first parameter. Could this specific parameter name be causing conflicts in the MCP interface?

**Q:** Is there a possibility that `device_type_model` is being passed both as a positional argument and a keyword argument through the MCP bridge?

### 3. MCP Interface Behavior
**Q:** How does the FastMCP interface handle function calls with multiple parameters? Could there be a conflict between parameter parsing and the dependency injection system?

**Q:** Are there any known issues with parameter names that match certain patterns in MCP tool registration?

### 4. Debugging Approach
**Q:** What's the best way to debug the actual parameter passing from the MCP interface to our functions? Can we add logging to see exactly what parameters are being passed?

**Q:** Should we examine the `inspect.signature()` behavior specifically for these failing functions vs working functions?

### 5. Registry Bridge Investigation
**Q:** Could the issue be in how the Registry Bridge creates wrapper functions? Is there a possibility that the `client` parameter injection is conflicting with existing parameters?

**Q:** Is there a way to validate that the parameter inspection logic is correctly filtering parameters before calling the original function?

### 6. Architecture Solutions
**Q:** Would renaming the `device_type_model` parameter to something else (like `device_model` or `model_name`) potentially resolve this issue?

**Q:** Is there a more robust way to handle parameter passing in the Registry Bridge that would prevent this type of conflict?

### 7. Comparison Analysis
**Q:** What specific differences exist between the working functions (like `netbox_create_device_type`) and the failing functions that could explain this behavior?

**Q:** Are there any patterns in the parameter types, positions, or names that could be causing the Registry Bridge to malfunction?

## Technical Environment

- **NetBox Version**: 4.2.9
- **Python Version**: 3.12.3
- **MCP Framework**: FastMCP
- **Architecture**: Registry Bridge Pattern with Dependency Injection
- **Tool Count**: 47 tools (only device type component templates failing)

## Expected Resolution

We need to identify why the Registry Bridge parameter handling is causing duplicate parameter errors specifically for device type component template functions, and implement a fix that allows these enterprise tools to function correctly through the MCP interface.

## Impact Assessment

**High Impact**: This issue prevents users from:
- Creating interface templates for devices
- Setting up front/rear port relationships for patch panels  
- Configuring power port templates for power management
- Establishing console port templates for out-of-band access
- All other device type component template operations

This significantly reduces the value of the NetBox MCP server for infrastructure automation workflows.

## Request for Assistance

@gemini-code-assist Please analyze this systematic parameter handling issue and provide guidance on:

1. **Root Cause Analysis**: What's causing the "multiple values for argument" error specifically for these functions?
2. **Debugging Strategy**: How can we trace the parameter flow from MCP interface to function execution?
3. **Architecture Fix**: What changes to the Registry Bridge pattern would resolve this issue?
4. **Testing Approach**: How can we validate the fix works across all affected functions?

Your expertise in analyzing complex parameter handling issues in Python frameworks would be invaluable for resolving this critical NetBox MCP functionality gap.