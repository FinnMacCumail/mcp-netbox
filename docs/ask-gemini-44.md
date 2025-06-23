# Ask Gemini #44: DCIM Tool Migration Strategy

## Context

We are in the middle of **Phase 3: DCIM Tools Migration** as part of the incremental migration strategy from flat files to hierarchical domain structure. The migration follows Gemini's architectural guidance from ask-gemini-43.md.

## Current Status

**Successfully completed:**
- ✅ Phase 1: System tools (1 tool) → `system/health.py`
- ✅ Phase 2: Tenancy tools (2 tools) → `tenancy/contacts.py` + `tenancy/tenants.py`
- ✅ Site tools (2 tools) → `dcim/sites.py` 
- ✅ Rack tools (3 tools) → `dcim/racks.py` (497 lines migrated)

**Current Challenge:**
We have 16 DCIM tools total. We've successfully migrated 5 tools (sites + racks) to new domain modules, but we're encountering complexity with removing the migrated tools from the old `dcim_tools.py` file.

## Technical Details

**Tool Registry Intelligence:**
The tool discovery mechanism has intelligent duplicate handling - it loads the first found tool and skips duplicates automatically. Current test shows:
```
✅ netbox_create_rack loaded from: netbox_mcp.tools.dcim.racks (✅ NEW)
❌ netbox_get_rack_elevation loaded from: netbox_mcp.tools.dcim_tools (❌ OLD) 
❌ netbox_get_rack_inventory loaded from: netbox_mcp.tools.dcim_tools (❌ OLD)
```

**File Complexity:**
- `dcim_tools.py`: 2500+ lines with 16 tools
- Complex interdependencies and precise line boundaries
- Manual editing risks breaking function boundaries

**Remaining DCIM Tools to Migrate (11 tools):**
- **Devices** (7 tools): `netbox_create_manufacturer`, `netbox_create_device_type`, `netbox_create_device_role`, `netbox_create_device`, `netbox_get_device_info`, `netbox_provision_new_device`, `netbox_decommission_device`
- **Interfaces** (1 tool): `netbox_assign_ip_to_interface`  
- **Cables** (1 tool): `netbox_create_cable_connection`
- **Modules** (1 tool): `netbox_install_module_in_device`
- **Power Ports** (1 tool): `netbox_add_power_port_to_device`

## Strategic Questions

### 1. **Tool Registry Approach**
Given that the tool registry has intelligent duplicate handling, should we:
- **Option A:** Simply disable old tools by removing/commenting `@mcp_tool` decorators, keeping code as reference
- **Option B:** Completely remove old tool functions after migration  
- **Option C:** Use a hybrid approach with migration markers

### 2. **Batch Migration Strategy**  
For the remaining 11 DCIM tools, what's the optimal approach:
- **Option A:** Migrate all remaining tools at once to respective domain modules
- **Option B:** Continue incremental migration (devices → interfaces → cables → modules → power)
- **Option C:** Group by complexity/dependencies rather than domain

### 3. **Code Preservation**
During migration, should we:
- **Option A:** Keep migrated tool code in old file as reference (disabled via decorator removal)
- **Option B:** Clean removal with git history as backup
- **Option C:** Add migration breadcrumbs with references to new locations

### 4. **Testing Strategy**
For validating 11 tools migration:
- **Option A:** Test each domain module individually as migrated
- **Option B:** Complete all migrations then test entire DCIM domain
- **Option C:** Automated testing after each tool migration

### 5. **Error Recovery**
If migration issues occur with complex tools:
- **Option A:** Git reset and retry with smaller chunks
- **Option B:** Continue with decorator disabling approach
- **Option C:** Implement temporary aliasing system

## Architecture Impact

**Benefits Achieved:**
- Clean domain separation: `dcim/sites.py` (171 lines), `dcim/racks.py` (497 lines)
- Tool discovery working correctly with hierarchical structure
- No duplicate tool registrations
- Enterprise patterns maintained

**Concerns:**
- Manual file editing complexity with large functions
- Risk of breaking function boundaries in 2500+ line file
- Maintaining tool registry integrity during migration

## Request

Please provide specific guidance on:

1. **Best approach for handling remaining tool removal from dcim_tools.py**
2. **Optimal batching strategy for remaining 11 DCIM tools**  
3. **Safe error recovery if migration editing goes wrong**
4. **Testing protocol for validating each migrated domain module**

The goal is to complete Phase 3 efficiently while maintaining system stability and following enterprise-grade migration practices.

## Expected Response

Please analyze these options and provide a detailed recommendation with:
- Specific step-by-step approach for the remaining migrations
- Risk mitigation strategies for large file editing
- Validation checkpoints for ensuring migration success
- Any architectural considerations we should address

This will help us complete the DCIM migration phase and prepare for Phase 4 (IPAM tools - 12 tools, most complex).