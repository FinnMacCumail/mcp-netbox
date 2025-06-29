# **NetBox MCP - Development Guide**

## **1. Introduction**

Welcome to the development guide for the **NetBox Model Context Protocol (MCP) Server v0.9.9**. This document is the central source of truth for developing new tools and extending the functionality of this enterprise-grade MCP server.

The NetBox MCP provides **specialized tools** that enable Large Language Models to interact intelligently with NetBox network documentation and IPAM systems through a sophisticated dual-tool pattern architecture.

## **2. Current Architecture Overview**

### **2.1 Production Status**

  - **Version**: 0.9.9 - Cable Management Suite Complete
  - **Tool Count**: 47 MCP tools covering all NetBox domains
  - **Architecture**: Hierarchical domain structure with Registry Bridge pattern
  - **Safety**: Enterprise-grade with dry-run mode, confirmation requirements, and audit logging

### **2.2 Core Components**

#### **Registry Bridge Pattern**

```
Internal Tool Registry (@mcp_tool) → Registry Bridge → FastMCP Interface
```

  - **Tool Registry** (`netbox_mcp/registry.py`): Core `@mcp_tool` decorator with automatic function inspection.
  - **Registry Bridge** (`netbox_mcp/server.py`): Dynamic tool export with dependency injection.
  - **Dependency Injection** (`netbox_mcp/dependencies.py`): Thread-safe singleton client management.
  - **Client Layer** (`netbox_mcp/client.py`): Enhanced NetBox API client with caching and safety controls.

#### **Dual-Tool Pattern Implementation**

Every NetBox domain implements both:

1.  **"Info" Tools**: Detailed single-object retrieval (e.g., `netbox_get_device_info`).
2.  **"List All" Tools**: Bulk discovery for exploratory queries (e.g., `netbox_list_all_devices`).

This fundamental LLM architecture ensures both detailed inspection AND bulk exploration capabilities.

## **3. Local Development & Testing Environment**

To contribute to this project, please use the following setup. This ensures consistency and proper testing against the live-test environment.

### **3.1 Directory Structure**

  - **Main Git Repository**: `/Users/elvis/Developer/github/netbox-mcp`
  - **Repository Wiki (Documentation)**: `/Users/elvis/Developer/github/netbox-mcp.wiki`
  - **Live Testing Directory**: `/Developer/live-testing/netbox-mcp`

### **3.2 Live Test Instance (NetBox Cloud)**

The live testing directory is connected to a dedicated NetBox Cloud test instance. Use the following credentials to configure your local environment for testing.

  - **NetBox URL**: `NETBOX_URL=https://zwqg2756.cloud.netboxapp.com`
  - **NetBox API Token**: `NETBOX_TOKEN=809e04182a7e280398de97e524058277994f44a5`

**CRITICAL SECURITY NOTICE:**
Set these values as environment variables in your shell. **DO NOT** commit the `NETBOX_TOKEN` to version control or hardcode it in any file. Ensure your local configuration files (like `.env`) are listed in your global `.gitignore` file.

## **4. Project Structure**

### **4.1 Hierarchical Domain Structure**

```
netbox-mcp/
├── docs/                           # Documentation
├── netbox_mcp/
│   ├── server.py                   # Main MCP server with Registry Bridge
│   ├── registry.py                 # @mcp_tool decorator and tool registry
│   ├── client.py                   # Enhanced NetBox API client
│   ├── dependencies.py             # Dependency injection system
│   └── tools/                      # Hierarchical domain structure
│       ├── dcim/
│       ├── ipam/
│       └── tenancy/
└── tests/                          # Test structure mirrors tools
```

## **5. Development Standards**

### **5.1 The @mcp\_tool Decorator Pattern**

Every tool function must follow this pattern:

```python
@mcp_tool(category="dcim")
def netbox_example_tool(...) -> Dict[str, Any]:
    """
    Tool description for LLM context.

    Args:
        ...
        confirm: Must be True for write operations (safety mechanism).
    ...
    """
```

### **5.2 Defensive Dict/Object Handling Pattern** 

**CRITICAL**: NetBox API responses can be either dictionaries OR objects. ALL tools must handle both formats defensively.

#### **The Universal Pattern**

```python
# CORRECT - Works with both dict and object responses
resource = api_response[0]
resource_id = resource.get('id') if isinstance(resource, dict) else resource.id
resource_name = resource.get('name') if isinstance(resource, dict) else resource.name
```

#### **Common Failure Pattern**

```python
# INCORRECT - Causes AttributeError: 'dict' object has no attribute 'id'
resource = api_response[0]
resource_id = resource.id  # ❌ Fails when NetBox returns dict
```

#### **Write Function Requirements**

ALL write functions must apply this pattern to EVERY NetBox API lookup:

```python
# Device Type Lookup
device_types = client.dcim.device_types.filter(model=device_type_model)
device_type = device_types[0]
device_type_id = device_type.get('id') if isinstance(device_type, dict) else device_type.id
device_type_display = device_type.get('display', device_type_model) if isinstance(device_type, dict) else getattr(device_type, 'display', device_type_model)

# Related Object Lookup (e.g., rear port template)
templates = client.dcim.rear_port_templates.filter(device_type_id=device_type_id, name=template_name)
template_obj = templates[0]
template_id = template_obj.get('id') if isinstance(template_obj, dict) else template_obj.id
template_positions = template_obj.get('positions') if isinstance(template_obj, dict) else template_obj.positions
```

#### **List Tools Defensive Access**

```python
# CORRECT - Defensive pattern for nested attributes
status_obj = device.get("status", {})
if isinstance(status_obj, dict):
    status = status_obj.get("label", "N/A")
else:
    status = str(status_obj) if status_obj else "N/A"
```

**This pattern is MANDATORY for ALL tools that process NetBox API responses.**

### **5.3 Complete Write Function Template**

**Use this template for ALL new write functions to prevent recurring AttributeError bugs:**

```python
@mcp_tool(category="dcim")  
async def netbox_create_example_function(
    client: NetBoxClient,
    required_param: str,
    optional_param: str = "default",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create example function with full defensive pattern.
    
    Args:
        required_param: Required parameter
        optional_param: Optional parameter  
        client: NetBox client (injected)
        confirm: Must be True to execute
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: Resource would be created. Set confirm=True to execute.",
            "would_create": {
                "required_param": required_param,
                "optional_param": optional_param
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not required_param or not required_param.strip():
        raise ValidationError("Required parameter cannot be empty")
    
    # STEP 3: LOOKUP MAIN RESOURCE (with defensive dict/object handling)
    try:
        main_resources = client.dcim.main_resource.filter(name=required_param)
        if not main_resources:
            raise NotFoundError(f"Main resource '{required_param}' not found")
        
        main_resource = main_resources[0]
        # CRITICAL: Apply dict/object handling to ALL NetBox responses
        main_resource_id = main_resource.get('id') if isinstance(main_resource, dict) else main_resource.id
        main_resource_display = main_resource.get('display', required_param) if isinstance(main_resource, dict) else getattr(main_resource, 'display', required_param)
        
    except Exception as e:
        raise NotFoundError(f"Could not find main resource '{required_param}': {e}")
    
    # STEP 4: LOOKUP RELATED RESOURCES (if needed)
    if related_param:
        try:
            related_resources = client.dcim.related_resource.filter(
                main_resource_id=main_resource_id,
                name=related_param
            )
            if not related_resources:
                raise NotFoundError(f"Related resource '{related_param}' not found")
            
            related_resource = related_resources[0]
            # CRITICAL: Apply dict/object handling to related resources too
            related_resource_id = related_resource.get('id') if isinstance(related_resource, dict) else related_resource.id
            related_positions = related_resource.get('positions') if isinstance(related_resource, dict) else related_resource.positions
            
        except Exception as e:
            raise ValidationError(f"Failed to resolve related resource: {e}")
    
    # STEP 5: CONFLICT DETECTION
    try:
        existing_resources = client.dcim.target_resource.filter(
            main_resource_id=main_resource_id,
            name=target_name,
            no_cache=True  # Force live check for accurate conflict detection
        )
        
        if existing_resources:
            existing_resource = existing_resources[0]
            existing_id = existing_resource.get('id') if isinstance(existing_resource, dict) else existing_resource.id
            raise ConflictError(
                resource_type="Target Resource",
                identifier=f"{target_name} for Main Resource {required_param}",
                existing_id=existing_id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing resources: {e}")
    
    # STEP 6: CREATE RESOURCE
    create_payload = {
        "main_resource": main_resource_id,
        "name": target_name,
        "type": resource_type,
        "description": description or ""
    }
    
    # Add related resource ID if applicable
    if related_param:
        create_payload["related_resource"] = related_resource_id
    
    try:
        new_resource = client.dcim.target_resource.create(confirm=confirm, **create_payload)
        resource_id = new_resource.get('id') if isinstance(new_resource, dict) else new_resource.id
        
    except Exception as e:
        raise ValidationError(f"NetBox API error during resource creation: {e}")
    
    # STEP 7: RETURN SUCCESS
    return {
        "success": True,
        "message": f"Resource '{target_name}' successfully created for '{required_param}'.",
        "data": {
            "resource_id": resource_id,
            "resource_name": new_resource.get('name') if isinstance(new_resource, dict) else new_resource.name,
            "main_resource_id": main_resource_id,
            "main_resource_name": required_param
        }
    }
```

### **5.4 Common Bugs and How to Prevent Them**

#### **Bug #1: AttributeError: 'dict' object has no attribute 'id'**

**Cause**: Direct attribute access on NetBox API responses without checking if it's a dict or object.

**Prevention**: ALWAYS use the defensive dict/object pattern for ALL NetBox API responses.

```python
# ❌ WRONG - Will fail randomly
resource = api_responses[0]
resource_id = resource.id

# ✅ CORRECT - Always works  
resource = api_responses[0]
resource_id = resource.get('id') if isinstance(resource, dict) else resource.id
```

#### **Bug #2: Missing Related Resource Handling**

**Cause**: Functions that reference other NetBox objects (like front ports → rear ports) often forget to apply defensive handling to the related object.

**Prevention**: Apply defensive pattern to EVERY NetBox API lookup in the function.

```python
# ❌ WRONG - Only main resource has defensive handling
device_type = device_types[0]
device_type_id = device_type.get('id') if isinstance(device_type, dict) else device_type.id
rear_port = rear_ports[0]
rear_port_id = rear_port.id  # ❌ Missing defensive handling

# ✅ CORRECT - All resources have defensive handling
device_type = device_types[0]  
device_type_id = device_type.get('id') if isinstance(device_type, dict) else device_type.id
rear_port = rear_ports[0]
rear_port_id = rear_port.get('id') if isinstance(rear_port, dict) else rear_port.id
```

#### **Bug #3: Inconsistent Error Handling**

**Cause**: Not following the standard exception handling pattern.

**Prevention**: Use the standard exception handling pattern:

```python
try:
    # NetBox API operation
except ConflictError:
    raise  # Re-raise specific errors
except Exception as e:
    raise ValidationError(f"NetBox API error during operation: {e}")
```

#### **Bug #4: Incorrect NetBox API Update/Delete Patterns**

**Cause**: Using incorrect pynetbox patterns for UPDATE and DELETE operations instead of the established NetBox MCP patterns.

**Critical Discovery**: During inventory management implementation, a critical bug was discovered where the wrong API patterns were used for update/delete operations, causing `NetBoxValidationError: Write operation requires confirm=True`.

**Root Cause Analysis**:
- Used individual record operations: `get()` + `setattr()` + `save()` 
- This pattern is NOT used anywhere else in the NetBox MCP codebase
- All proven working modules use direct ID-based operations with confirm parameter

**Prevention**: ALWAYS follow the established NetBox MCP patterns by checking existing working modules:

```python
# ❌ WRONG - Individual record pattern (not used in NetBox MCP)
inventory_record = client.dcim.inventory_items.get(item_id)
for field, value in update_payload.items():
    setattr(inventory_record, field, value)
updated_item = inventory_record.save()

# ✅ CORRECT - Direct ID-based pattern (used by ALL working modules)
updated_item = client.dcim.inventory_items.update(item_id, confirm=confirm, **update_payload)
```

**Proven Working Patterns** (validated in devices.py, tenancy/resources.py):

```python
# UPDATE operations
client.dcim.devices.update(device_id, confirm=True, **update_data)
client.ipam.ip_addresses.update(ip_id, confirm=True, **update_data)
endpoint.update(resource_id, confirm=True, **update_data)

# DELETE operations
client.dcim.cables.delete(cable_id, confirm=True)
client.dcim.inventory_items.delete(item_id, confirm=confirm)

# CREATE operations (for reference)
client.dcim.inventory_items.create(confirm=confirm, **create_payload)
```

**Validation Process**:
1. **Before implementing**: Check 2-3 similar functions in existing working modules
2. **Pattern matching**: Ensure UPDATE/DELETE operations follow the exact same syntax
3. **Parameter consistency**: Use `confirm=confirm` or `confirm=True` consistently
4. **Testing validation**: If similar functions work, your pattern should work too

**Key Insight**: The NetBox MCP codebase has established patterns that MUST be followed. Never assume pynetbox patterns from documentation - always check working NetBox MCP functions first.

### **5.5 Enterprise Safety Requirements**

All write operations must include a `confirm` parameter and logic to check for conflicts.

## **6. Tool Registration and Discovery**

Tools are automatically discovered and registered via the `@mcp_tool` decorator and the Registry Bridge.

## **7. Testing and Validation**

### **7.1 Codebase Pattern Validation**

**CRITICAL**: Before implementing any UPDATE or DELETE operations, ALWAYS validate against existing working functions to ensure consistent patterns.

#### **Validation Methodology**

**Step 1: Pattern Discovery**
```bash
# Find all files with update/delete/save operations
find netbox_mcp/tools -name "*.py" -exec grep -l "\.update\|\.delete\|\.save" {} \;

# Check specific patterns in proven working modules
grep -A3 -B3 "\.update.*confirm=True" netbox_mcp/tools/dcim/devices.py
grep -A3 -B3 "\.delete.*confirm=True" netbox_mcp/tools/dcim/devices.py
```

**Step 2: Pattern Analysis**
```bash
# Extract actual working patterns
grep -n "\.update(" netbox_mcp/tools/dcim/devices.py
grep -n "\.delete(" netbox_mcp/tools/dcim/devices.py
grep -n "\.create(" netbox_mcp/tools/dcim/inventory.py
```

**Step 3: Pattern Comparison**
- ✅ **CREATE**: `client.endpoint.create(confirm=confirm, **payload)` - CONSISTENT
- ✅ **UPDATE**: `client.endpoint.update(id, confirm=confirm, **payload)` - CONSISTENT  
- ✅ **DELETE**: `client.endpoint.delete(id, confirm=confirm)` - CONSISTENT

#### **Live Validation Example**

From inventory management development:

```python
# DISCOVERED working patterns in devices.py:
client.dcim.devices.update(device_id, confirm=True, **device_update_data)
client.dcim.cables.delete(cable["id"], confirm=True)

# DISCOVERED working patterns in tenancy/resources.py:
endpoint.update(resource_id, confirm=True, **update_data)

# APPLIED to inventory functions:
client.dcim.inventory_items.update(item_id, confirm=confirm, **update_payload)
client.dcim.inventory_items.delete(item_id, confirm=confirm)
```

### **7.2 Testing Protocol**

**IMPORTANT**: NetBox MCP development now uses a **dedicated test team** for comprehensive functional testing. Developers are responsible for **code-level validation only**.

#### **Developer Testing Responsibilities** (Code Level Only)
1. **Pattern Validation**: Confirm your API patterns match 2-3 working functions
2. **Syntax Check**: Verify parameter order and confirm usage consistency  
3. **Similar Function Test**: If similar functions work, yours should too
4. **Tool Registration**: Verify tools load correctly in registry without errors
5. **Basic Import Test**: Ensure no import/syntax errors when loading modules

#### **Test Team Handoff Requirements**

**CRITICAL**: All PRs must include detailed test instructions for the dedicated test team.

**Required Test Documentation Format**:
```markdown
## Test Plan

### **Tool Functions to Test**
- `function_name_1` - Brief description
- `function_name_2` - Brief description

### **Test Scenarios**
1. **Dry Run Validation**: Test confirm=False behavior
2. **Parameter Validation**: Test with invalid/missing parameters
3. **Success Path**: Test normal operation with valid data
4. **Conflict Detection**: Test with existing resources (if applicable)
5. **Error Handling**: Test NetBox API error scenarios

### **Test Data Requirements**
- Device types needed: [list specific requirements]
- Sites needed: [list specific requirements]  
- Other prerequisites: [list any setup requirements]

### **Expected Results**
- Success: [describe expected successful outcomes]
- Errors: [describe expected error conditions and messages]
- Side effects: [describe what should be created/modified/deleted]
```

#### **Developer Testing Scope** (Minimal Code Validation)
- ✅ **Code compiles**: No import or syntax errors
- ✅ **Tool registration**: Functions register correctly in `TOOL_REGISTRY`
- ✅ **Pattern compliance**: Code follows DEVELOPMENT-GUIDE.md patterns
- ❌ **Functional testing**: NOT developer responsibility
- ❌ **NetBox API testing**: Handled by dedicated test team
- ❌ **Integration testing**: Handled by dedicated test team
- ❌ **Error scenario testing**: Handled by dedicated test team

#### **Test Team Integration**

**Workflow**:
1. **Developer**: Implements function with comprehensive test instructions
2. **PR Creation**: Includes detailed test plan for test team
3. **Test Team**: Executes comprehensive functional testing
4. **Feedback Loop**: Test team reports results back to developer if issues found

## **8. Common Patterns and Examples**

Implement the Dual-Tool Pattern for all new domains to ensure both detailed and bulk retrieval capabilities.

## **9. High-Level Development Steps**

This section outlines the general steps for adding new tools. For the mandatory, detailed process including Git workflow and code reviews, see **Section 10**.

1.  **Identify Domain**: Determine which domain your tool belongs to.
2.  **Create Function**: Follow the `@mcp_tool` decorator pattern.
3.  **Implement Logic**: Use defensive programming and enterprise safety patterns.
4.  **Test Locally**: Validate against the NetBox Cloud test instance.
5.  **Document**: Add appropriate docstrings and examples.

-----

## **10. End-to-End Development Workflow (Mandatory)**

**All development and contributions must follow this structured process.** This ensures traceability, code quality, and allows us to leverage automated tools like Gemini Code Assist. The **GitHub CLI (`gh`) is mandatory** for this workflow.

### **Step 1: Issue Creation**

Every new feature, bug fix, or task begins with a GitHub Issue. This is the central hub for discussion and tracking.

  * **How to use:** Create an issue with a clear title, a detailed description of the task, and the appropriate labels.
  * **IMPORTANT - Label Validation:** Always check if labels exist before using them. Create missing labels first.
    ```bash
    # MANDATORY: Check existing labels first
    gh label list
    
    # Create missing labels if needed
    gh label create "new-label" --description "Description" --color "color-hex"
    ```
  * **Label Naming Conventions:** Use consistent naming patterns for better discoverability:
    - **Domain labels**: `dcim`, `ipam`, `tenancy`, `virtualization`, `prompts`
    - **Type labels**: `feature`, `bug`, `enhancement`, `documentation`
    - **Priority labels**: `priority-high`, `priority-medium`, `priority-low`
    - **Complexity labels**: `complexity-high`, `complexity-medium`, `complexity-low`
    - **Status labels**: `on-hold`, `ready-for-review`, `needs-testing`
  * **GitHub CLI Example:**
    ```bash
    # Example for a new feature
    gh issue create --title "Feature: Add Virtual Chassis tools" \
                    --body "Implement 'netbox_get_virtual_chassis_info' and 'netbox_list_all_virtual_chassis' tools within the DCIM domain." \
                    --label "feature,dcim"
    ```

#### **Requesting Help and Advice from Gemini**

If you need advice while planning the implementation, you can ask Gemini directly in the issue.

  * **How to use:** Mention `@gemini-code-assist` in a comment with your specific question.
  * **Example:**
    > @gemini-code-assist I'm working on issue \#52. What is the best way to retrieve the 'master' of a virtual chassis via pynetbox while also listing its members?

### **Step 2: Branching for the Task**

Never work directly on the `main` branch. Link your work to the issue by creating a correctly named branch.

  * **How to use:** Use the `gh` CLI to create a branch that is directly linked to the issue. Use the convention `feature/ISSUE-NR-description` or `fix/ISSUE-NR-description`.
  * **GitHub CLI Example (assuming issue number 52):**
    ```bash
    # This command creates the branch, links it to the issue, and checks it out immediately.
    gh issue develop 52 --name feature/52-virtual-chassis-tools --base main
    ```

### **Step 3: Implementation and Local Testing**

This is the phase where you write the code. Adhere to the coding standards in sections 5, 6, and 8. Test your tool locally against the NetBox Cloud instance and validate its registration.

### **Step 4: Create a Pull Request (PR)**

Once the code is complete and locally tested, open a Pull Request (PR) to propose your changes for the `main` branch.

**The Benefit of the PR Method:** This is the most critical step, as it triggers the **automatic code review by the Gemini Code Assist GitHub App**. Gemini will analyze the PR, provide a summary, identify potential bugs, and suggest improvements to ensure code quality.

  * **How to use:** Create the PR using the `gh` CLI. Ensure a clear title and a description that closes the issue (e.g., `Closes #52`).
  * **GitHub CLI Example:**
    ```bash
    # Create the Pull Request from your feature branch
    gh pr create --title "Feature: Virtual Chassis Tools for DCIM" \
                 --body "Closes #52. This adds the dual-tool pattern implementation for NetBox Virtual Chassis. The tools are 'netbox_get_virtual_chassis_info' and 'netbox_list_all_virtual_chassis'." \
                 --reviewer @username # Request a review from a team member
    ```

### **Step 5: Review, Approval, and Merge**

The PR will now be reviewed by both team members and the **Gemini Code Assist bot**. Incorporate any feedback and wait for approval. Once approved, the PR can be merged.

  * **How to use:** Use the `gh` CLI to merge the PR after approval. Use the `--squash` option to keep the `main` branch history clean.
  * **GitHub CLI Example (assuming PR number 54):**
    ```bash
    # Merge the approved PR and delete the local and remote branch
    gh pr merge 54 --squash --delete-branch
    ```

This structured workflow, powered by the GitHub CLI and enhanced by Gemini Code Assist, ensures that every contribution is transparent, traceable, and maintains the high-quality standard of the NetBox MCP Server.

-----

## **11. Future Development**

### **11.1 Extension Points**

  - **New Domains**: Easy addition of new NetBox domains as they become available.
  - **Enhanced Tools**: Build upon the dual-tool pattern for domain-specific workflows.
  - **Integration Tools**: Create cross-domain operations leveraging multiple NetBox APIs.

### **11.2 Architecture Scalability**

The hierarchical domain structure and Registry Bridge pattern support:

  - **Unlimited Tool Growth**: No architectural limits on tool count.
  - **Domain Expansion**: Easy addition of new NetBox domains.
  - **Enterprise Features**: Built-in safety, caching, and performance optimization.
