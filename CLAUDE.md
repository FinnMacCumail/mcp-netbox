# NetBox MCP Development Instructions

## 🧪 **Testing Structure Update (2025-06-27)**

**IMPORTANT**: NetBox MCP nu heeft een **dedicated test team** voor comprehensive functional testing.

### **Developer Responsibilities** (Code Level Only):
- ✅ **Code compilation**: No import/syntax errors
- ✅ **Tool registration**: Functions register correctly in `TOOL_REGISTRY`  
- ✅ **Pattern compliance**: Code follows DEVELOPMENT-GUIDE.md standards
- ❌ **Functional testing**: Handled by dedicated test team
- ❌ **NetBox API validation**: Handled by dedicated test team

### **Test Team Handoff**:
**CRITICAL**: All PRs must include detailed test instructions following the format in DEVELOPMENT-GUIDE.md Section 7.2.

**Required in every PR**:
- Tool functions to test
- Test scenarios (dry-run, parameters, success path, conflicts, errors)
- Test data requirements 
- Expected results

# Previous Testing Session Progress (Historical)

## Completed Tests ✅
- **Health Check**: NetBox MCP connected, version 4.2.9, ~190ms response time
- **Interface Template**: Successfully added "eth0" (1000base-t, management) to Test Device
- **Power Port Template**: Successfully added "PSU1" (IEC C14) to Test Device  
- **Console Port Template**: Successfully added "console" (RJ-45) to Test Device
- **Rear Port Template**: Successfully added "rear1" (8P8C) to Test Device
- **Console Server Port Template**: Successfully added "console-server" (RJ-45) to Test Device
- **Power Outlet Template**: Successfully added "outlet1" (IEC C13) to Test Device
- **Module Bay Template**: Successfully added "module1" to Test Device
- **Device Bay Template**: Successfully added "bay1" to Test Chassis (after setting subdevice_role to "parent")

## Major Bug Discovery & Fix Applied 🔧
**Issue**: ALL Device Type Component Template Functions failing with: `TypeError: got multiple values for argument 'device_type_model'`

**Root Cause (Identified by Gemini Code Assist)**: Registry Bridge parameter handling issue in `registry.py` where `client` parameter from MCP interface conflicts with injected `client=client` parameter.

**Affected Functions**: 
- `netbox_add_interface_template_to_device_type`
- `netbox_add_front_port_template_to_device_type` 
- `netbox_add_rear_port_template_to_device_type`
- `netbox_add_console_port_template_to_device_type`
- `netbox_add_power_port_template_to_device_type`
- All other device type component template functions (9 total)

**Fix Applied**: Modified `execute_tool()` function in `/Users/elvis/Developer/github/netbox-mcp/netbox_mcp/registry.py` (lines 353-358):
```python
# Filter out 'client' parameter from parameters to avoid duplicate argument error
# The client is injected separately as named parameter
filtered_parameters = {k: v for k, v in parameters.items() if k != 'client'}

# Inject client as first parameter
return tool_function(client=client, **filtered_parameters)
```

**Status**: ✅ **COMPLETED** - Registry Bridge fix implemented and activated.

## 🚀 Inventory Management Suite Component Type Fix (2025-06-27) ✅

**Issue**: Inventory functions using incorrect component_type format causing NetBox ContentType validation errors.

**Root Cause**: Inventory functions were using simple strings like "CPU", "Memory", "Storage" instead of correct NetBox ContentType format (`app_label.model_name`).

**Fix Applied**: Updated `validate_component_type()` function and all inventory functions to use correct NetBox ContentType format:

**Files Modified**:
- `/Users/elvis/Developer/github/netbox-mcp/netbox_mcp/tools/dcim/inventory.py`:
  - ✅ **Component Type Validation**: Updated to return correct ContentType format or None for general inventory
  - ✅ **Template Creation**: `netbox_add_inventory_item_template_to_device_type` uses validated component types
  - ✅ **Device Inventory**: `netbox_add_inventory_item_to_device` uses validated component types  
  - ✅ **Bulk Operations**: `netbox_bulk_add_standard_inventory` validates all preset component types
  - ✅ **Preset Updates**: All 4 inventory presets updated with correct component_type values

**Technical Implementation**:
```python
# Before: Simple strings causing validation errors
"component_type": "CPU"  # ❌ Invalid

# After: Correct NetBox ContentType format or None for general inventory
"component_type": None   # ✅ General inventory (cpu, memory, storage map to None)
"component_type": "dcim.interface"  # ✅ Specific NetBox ContentType
```

**Affected Functions Fixed**:
- `netbox_add_inventory_item_template_to_device_type`
- `netbox_add_inventory_item_to_device`  
- `netbox_bulk_add_standard_inventory`

**Status**: ✅ **COMPLETED** - All inventory functions now use correct component_type validation.

## ⚠️ NetBox Deprecation Notice (2025-06-27)

**CRITICAL**: NetBox v4.3+ Inventory Items Deprecation Discovered

**NetBox Official Warning**:
> "Beginning in NetBox v4.3, the use of inventory items has been deprecated. They are planned for removal in a future NetBox release. Users are strongly encouraged to begin using modules and module types in place of inventory items. Modules provide enhanced functionality and can be configured with user-defined attributes."

**Impact Assessment**:
- **Current Status**: Inventory Management Suite fully functional on NetBox 4.2.9
- **Future Risk**: Functions will become obsolete in future NetBox versions
- **Migration Path**: Transition to Module Management Suite required

**Action Plan**:
1. **Immediate**: Document deprecation status in all inventory tools
2. **Short-term**: Add deprecation warnings to function docstrings  
3. **Long-term**: Implement Module Management Suite as replacement
4. **Migration**: Provide transition tools from inventory items to modules

**Affected Functions** (7 tools):
- `netbox_add_inventory_item_template_to_device_type` → Future: Module Type management
- `netbox_list_inventory_item_templates_for_device_type` → Future: Module Type listing
- `netbox_add_inventory_item_to_device` → Future: Module installation
- `netbox_list_device_inventory` → Future: Device module listing
- `netbox_update_inventory_item` → Future: Module updates
- `netbox_remove_inventory_item` → Future: Module removal
- `netbox_bulk_add_standard_inventory` → Future: Bulk module deployment

## 📊 Current Modules Implementation Status

**ASSESSMENT**: NetBox MCP has minimal module coverage (~20% of inventory functionality)

### ✅ **Currently Implemented** (3 tools):
1. **`netbox_add_module_bay_template_to_device_type`** - Device type module bay templates ✅
2. **`netbox_install_module_in_device`** - Module installation in device bays ✅  
3. **`netbox_add_power_port_to_device`** - Power port management ✅

### ❌ **Critical Missing Tools**:
**Module Types Management**:
- `netbox_create_module_type` ❌
- `netbox_get_module_type_info` ❌
- `netbox_list_all_module_types` ❌

**Module Management** (Dual-Tool Pattern Missing):
- `netbox_list_device_modules` ❌
- `netbox_get_module_info` ❌  
- `netbox_remove_module_from_device` ❌
- `netbox_update_module` ❌

**Module Bay Management**:
- `netbox_list_device_module_bays` ❌
- `netbox_get_module_bay_info` ❌

### 🚨 **Gap Analysis**:
- **Inventory Items**: 7 comprehensive tools (deprecated NetBox v4.3+)
- **Modules**: 3 basic tools (incomplete replacement)
- **Missing**: ~10-12 module tools needed for feature parity

**URGENT RECOMMENDATION**: Implement comprehensive Module Management Suite to replace deprecated inventory functionality before NetBox v4.3+.

## 🚨 **CRITICAL ISSUE DISCOVERED**: Existing Module Code Violates Development Standards

**Problem**: Current `modules.py` (lines 63, 73, 93) uses direct dictionary access instead of required defensive dict/object pattern:

```python
# ❌ WRONG - Current code violates DEVELOPMENT-GUIDE.md
device_id = device["id"]  # Line 63 - Will fail if device is object
bay_id = bay["id"]       # Line 73 - Will fail if bay is object  
mod_type_id = mod_type["id"]  # Line 94 - Will fail if module_type is object
```

**Required Fix** (per DEVELOPMENT-GUIDE.md Bug #1):
```python
# ✅ CORRECT - Must apply defensive pattern
device_id = device.get('id') if isinstance(device, dict) else device.id
bay_id = bay.get('id') if isinstance(bay, dict) else bay.id
mod_type_id = mod_type.get('id') if isinstance(mod_type, dict) else mod_type.id
```

**Action Required**: Fix existing module code before implementing new Module Management Suite to avoid perpetuating bad patterns.

## Device Types Created
1. **Test Device** (Test Device model) - has interface, power, console, rear port, console server, power outlet, module bay templates
2. **Test Chassis** (Test Chassis model) - has device bay template (subdevice_role set to "parent" via UI)
3. **Fresh Test Device** (Fresh Test Device model) - clean device type created for testing the parameter fix

## Gemini Code Assist Documentation
- **Issue Report**: Created detailed analysis in `docs/ask_gemini_mcp_parameter.md`
- **Root Cause**: Gemini identified Registry Bridge parameter conflict in `execute_tool()` function
- **Solution**: Parameter filtering to prevent duplicate `client` parameter passing

## Next Steps After Restart
1. **RESTART CLAUDE CODE** to activate the Registry Bridge fix
2. Test all device type component template functions on "Fresh Test Device" 
3. Verify Front Port Template functionality (original issue from CLAUDE.md)
4. Test systematic fix across all 9 affected functions
5. Update CLAUDE.md with test results and mark issue as resolved

## Files Modified
- `/Users/elvis/Developer/github/netbox-mcp/netbox_mcp/tools/dcim/device_type_components.py` (lines 1097, 1098, 1174) - Dictionary access fix
- `/Users/elvis/Developer/github/netbox-mcp/netbox_mcp/registry.py` (lines 353-358) - Registry Bridge parameter filtering fix
- `/Users/elvis/Developer/github/netbox-mcp/docs/ask_gemini_mcp_parameter.md` - Created detailed issue analysis for Gemini

## Branch Status
- Currently on: `main` branch
- Previous branch: `fix/issue-52-template-typeerror`