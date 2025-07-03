# **NetBox MCP - Development Guide**

## **1. Introduction**

Welcome to the development guide for the **NetBox Model Context Protocol (MCP) Server v1.0.0**. This document is the central source of truth for developing new tools and extending the functionality of this enterprise-grade MCP server.

The NetBox MCP provides **specialized tools** that enable Large Language Models to interact intelligently with NetBox network documentation and IPAM systems through a sophisticated dual-tool pattern architecture.

## **2. Current Architecture Overview**

### **2.1 Production Status**

  - **Version**: 1.0.0 - Production Release Complete
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

#### **Bug #5: Cable Termination API Format Errors (Issue #78)**

**Problem**: Cable creation fails with "Must define A and B terminations when creating a new cable" error.

**Root Cause**: NetBox API expects specific termination array format, not individual type/id fields that might seem intuitive.

**Critical Discovery**: Through NetBox API schema validation (`docs/netbox-api-schema.yaml`), the correct format uses GenericObjectRequest arrays.

```python
# ❌ INCORRECT - Will fail with termination error  
cable_data = {
    "termination_a_type": "dcim.interface",
    "termination_a_id": interface_a_id,
    "termination_b_type": "dcim.interface", 
    "termination_b_id": interface_b_id,
    "type": cable_type,
    "status": cable_status
}

# ✅ CORRECT - Uses GenericObjectRequest format
cable_data = {
    "a_terminations": [{"object_type": "dcim.interface", "object_id": interface_a_id}],
    "b_terminations": [{"object_type": "dcim.interface", "object_id": interface_b_id}],
    "type": cable_type,
    "status": cable_status
}
```

**Prevention Pattern**: Always validate against NetBox API schema for relationship fields:

```bash
# Validate cable creation format
grep -n -A 30 "CableRequest:" docs/netbox-api-schema.yaml
# Look for termination field requirements
```

**Key Pattern**: Relationship fields often require GenericObjectRequest format: `[{"object_type": "app.model", "object_id": <id>}]`

#### **Bug #6: Client Property Access Errors**

**Problem**: `client.base_url` causes AttributeError in URL generation.

**Root Cause**: NetBox client wrapper doesn't expose `base_url` directly.

```python
# ❌ INCORRECT - AttributeError
netbox_url = f"{client.base_url}/dcim/device-types/{device_type_id}/"

# ✅ CORRECT - Use config.url
netbox_url = f"{client.config.url}/dcim/device-types/{device_type_id}/"
```

**Prevention**: Always use `client.config.*` for configuration access, never assume direct property exposure.

### **5.5 NetBox API Debugging Techniques**

When encountering NetBox API errors, use these systematic debugging approaches:

#### **Debug Logging Pattern**

Always add comprehensive logging to understand API interactions:

```python
# Enable debug logging to see exact payload sent to NetBox
logger.debug(f"Creating cable with payload: {cable_data}")
result = client.dcim.cables.create(confirm=True, **cable_data)
logger.debug(f"NetBox API response: {result}")
```

#### **Schema Validation Workflow**

Before implementing new API integrations:

```bash
# 1. Find object schema in NetBox API documentation
grep -n -A 30 "ObjectRequest:" docs/netbox-api-schema.yaml

# 2. Check for GenericObjectRequest patterns (common for relationships)
grep -n -A 10 "GenericObjectRequest:" docs/netbox-api-schema.yaml

# 3. Validate field requirements and formats
grep -n -A 20 "required:" docs/netbox-api-schema.yaml
```

#### **Error Pattern Recognition**

Common NetBox API error patterns and solutions:

- **"Must define A and B terminations"** → Use GenericObjectRequest arrays
- **"AttributeError: ... has no application named 'base_url'"** → Use `client.config.url`
- **"Write operation requires confirm=True"** → Check MCP pattern consistency
- **"Field does not exist"** → Validate against schema (VM interfaces don't have 'type')

### **5.6 Enterprise Safety Requirements**

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

## **11. MCP Prompts Development - Lessons Learned**

**Status**: Production Ready (PR #72 merged) - First MCP Prompt implementation with Bridget persona system

The NetBox MCP Prompts feature represents a major architectural evolution, adding intelligent workflow orchestration and user guidance on top of our 112+ tools foundation. This section documents critical lessons learned during implementation.

### **11.1 The MCP Prompt Architecture**

#### **Prompt vs Tools Distinction**

**MCP Tools**: Atomic operations that perform specific NetBox API calls
**MCP Prompts**: Intelligent workflow orchestrators that guide users through multi-step processes

```python
# Tools do this:
@mcp_tool(category="dcim")
def netbox_create_device(...) -> Dict[str, Any]:
    # Single API operation
    return client.dcim.devices.create(...)

# Prompts do this:
@mcp_prompt(name="install_device_in_rack", description="...")
async def install_device_in_rack_prompt() -> str:
    # Workflow guidance that orchestrates multiple tools
    return "Step-by-step workflow instructions..."
```

#### **Registry Bridge Extension**

The existing Registry Bridge pattern was successfully extended to support prompts:

```python
# Registry supports both tools and prompts
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}
PROMPT_REGISTRY: Dict[str, Dict[str, Any]] = {}  # NEW

# Bridge functions for both
bridge_tools_to_fastmcp()
bridge_prompts_to_fastmcp()  # NEW
```

### **11.2 Critical MCP Client Compatibility Lessons**

#### **Lesson #1: MCP Rendering Limitations**

**Problem Discovered**: MCP clients cannot render complex JSON objects returned by prompts.

**Original Implementation** (FAILED):
```python
@mcp_prompt(...)
async def example_prompt() -> Dict[str, Any]:
    return {
        "persona_active": True,
        "workflow_steps": [...],
        "nested_objects": {...}
    }
```

**Error**: `MCP error 0: Error rendering prompt: Could not convert prompt result to message`

**Solution** (SUCCESS):
```python
@mcp_prompt(...)
async def example_prompt() -> str:
    return """🦜 **Formatted Message String**
    
    All content as markdown-formatted string
    that MCP clients can render directly."""
```

**Critical Rule**: **MCP prompts MUST return simple strings, never complex JSON objects.**

#### **Lesson #2: Async Function Handling in Registry**

**Problem**: The `execute_prompt` function wasn't properly handling async prompt functions.

**Solution**: Enhanced registry with proper async detection:
```python
async def execute_prompt(prompt_name: str, **arguments) -> Any:
    prompt_function = prompt_metadata["function"]
    
    # Handle both sync and async functions
    if inspect.iscoroutinefunction(prompt_function):
        return await prompt_function(**arguments)
    else:
        return prompt_function(**arguments)
```

### **11.3 Persona System Implementation**

#### **The Bridget Persona Architecture**

**Challenge**: Test team feedback indicated users couldn't identify they were using NetBox MCP.

**Solution**: Implemented comprehensive persona system with:

1. **BridgetPersona Class** (`netbox_mcp/persona/bridget.py`)
   - Standardized introduction methods
   - Dutch localization for consistent user experience
   - Clear NetBox MCP branding throughout interactions

2. **Persona Integration Pattern**:
```python
# Every workflow prompt includes Bridget
bridget_intro = BridgetPersona.get_introduction(
    workflow_name="Install Device in Rack",
    user_context="Device installation workflow"
)

# Consistent branding in output
workflow_message = f"""🦜 **Bridget's {workflow_name} Workflow**

*Hallo! Bridget hier, jouw NetBox Infrastructure Guide!*

[Workflow content with clear NetBox MCP branding]

---
*Bridget - NetBox Infrastructure Guide | NetBox MCP v0.11.0+ | 🦜 LEGO Parrot Mascotte*"""
```

#### **Persona System Benefits**

- **Clear System Identification**: Users always know they're using NetBox MCP
- **Consistent Experience**: Same persona across all workflows
- **Localization Support**: Dutch language for local user base
- **Expert Guidance**: Bridget provides context and explanations for each step

### **11.4 Prompt Development Template**

Based on successful implementation, use this template for new prompts:

```python
@mcp_prompt(
    name="prompt_name",
    description="Brief description for MCP client discovery"
)
async def prompt_function() -> str:  # MUST return str, not Dict
    """
    Detailed docstring explaining the prompt's purpose.
    """
    
    # 1. Include Bridget persona introduction
    bridget_intro = BridgetPersona.get_introduction(
        workflow_name="Your Workflow Name",
        user_context="Context for this specific workflow"
    )
    
    # 2. Build comprehensive workflow guidance
    workflow_content = {
        # Structure your workflow data
    }
    
    # 3. CRITICAL: Format as simple string for MCP compatibility
    formatted_message = f"""🦜 **Bridget's {workflow_name} Workflow**

*Hallo! Bridget hier, jouw NetBox Infrastructure Guide!*

{workflow_guidance_content}

---
*Bridget - NetBox Infrastructure Guide | NetBox MCP v0.11.0+ | 🦜 LEGO Parrot Mascotte*"""
    
    return formatted_message  # Simple string - MCP compatible
```

### **11.5 Testing Methodology for Prompts**

#### **MCP Client Testing Requirements**

**Developer Testing** (Code Level):
1. **Import Test**: Verify prompt loads without errors
2. **Registration Test**: Confirm prompt appears in PROMPT_REGISTRY
3. **Return Type Test**: Ensure prompt returns string, not complex object
4. **Syntax Validation**: Check for proper async/sync handling

**Test Team Testing** (Functional):
1. **MCP Client Rendering**: Verify prompt displays correctly in MCP clients
2. **Persona Consistency**: Confirm Bridget branding appears throughout
3. **Workflow Usability**: Test user experience with guided workflows
4. **Content Accuracy**: Validate technical accuracy of workflow instructions

#### **Test Documentation Template**

```markdown
## Prompt Test Plan

### **Prompts to Test**
- `prompt_name` - Brief description of prompt functionality

### **MCP Client Compatibility Tests**
1. **Rendering Test**: Prompt displays as formatted text (not error)
2. **Persona Test**: Bridget introduction and branding visible
3. **Content Test**: All workflow steps readable and actionable
4. **Trigger Test**: Prompt activates with expected trigger phrase

### **Expected Results**
- Prompt renders as formatted markdown text
- Bridget persona consistently present
- Clear NetBox MCP branding throughout
- User guidance actionable and technically accurate
```

### **11.6 Architecture Integration Points**

#### **Server Integration**

Prompts integrate seamlessly with existing server architecture:

```python
# FastAPI endpoints automatically created
@api_app.get("/api/v1/prompts")  # Discovery endpoint
@api_app.post("/api/v1/prompts/execute")  # Execution endpoint

# FastMCP integration via bridge
bridge_prompts_to_fastmcp()  # Automatic registration
```

#### **Registry Integration**

Prompts use the same decorator pattern as tools:

```python
# Same pattern, different registry
@mcp_tool(category="dcim")      # -> TOOL_REGISTRY
@mcp_prompt(name="prompt_name") # -> PROMPT_REGISTRY
```

### **11.7 Key Success Factors**

1. **MCP Client Compatibility**: Always return simple strings from prompts
2. **Persona Consistency**: Use BridgetPersona class for standardized branding
3. **Comprehensive Testing**: Test both code-level and MCP client rendering
4. **User Experience Focus**: Solve real user problems (system identification)
5. **Architecture Reuse**: Leverage existing Registry Bridge pattern

### **11.8 Future Prompt Development**

**Recommended Next Prompts**:
- Device decommissioning workflow
- Network capacity planning workflow  
- Troubleshooting assistant workflow
- Infrastructure health check workflow

**Pattern Validation**: Always check existing working prompts before implementing new ones.

-----

## **12. Bridget Auto-Context System - Lessons Learned**

**Status**: Production Ready (PR #74 merged) - Complete auto-context system with intelligent environment detection

The Bridget Auto-Context System represents a revolutionary advancement in MCP server user experience, providing zero-configuration intelligent persona-based assistance that automatically adapts to user environments. This section documents critical architectural and implementation lessons learned.

### **12.1 The Auto-Context Architecture Revolution**

#### **Thread-Safe Singleton Pattern**

**Critical Discovery**: Auto-context management requires bulletproof thread safety for enterprise environments.

**Implementation Pattern**:
```python
class BridgetContextManager:
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-checked locking
                    cls._instance = cls()
        return cls._instance
```

**Lesson**: Always use double-checked locking pattern for singleton initialization in multi-threaded MCP environments.

#### **Environment Detection Engine**

**Breakthrough Pattern**: URL-based environment detection with override capabilities.

```python
def detect_environment_from_url(self, netbox_url: str) -> Tuple[str, str, str]:
    """Auto-detect environment from URL patterns with fallback to production."""
    
    patterns = {
        'demo': ['demo.netbox.', 'netbox-demo.', 'localhost'],
        'staging': ['staging.netbox.', 'test.netbox.', '.staging.'],
        'cloud': ['.cloud.netboxapp.com', 'cloud.netbox.'],
        # Default to production for unknown patterns (safety-first)
    }
```

**Key Insight**: Default to most restrictive safety level (production/maximum) for unknown environments.

### **12.2 Registry Integration Patterns**

#### **Seamless Auto-Injection**

**Challenge**: Inject context without modifying 112+ existing tool functions.

**Solution**: Enhanced registry `execute_tool()` with first-call detection:

```python
async def execute_tool(tool_name: str, **arguments) -> Any:
    # Normal tool execution
    result = await _execute_tool_core(tool_name, **arguments)
    
    # Auto-context injection (first call only)
    if context_manager.should_inject_context():
        bridget_context = await _generate_bridget_context()
        if isinstance(result, dict):
            result['bridget_context'] = bridget_context
        else:
            result = {'tool_result': result, 'bridget_context': bridget_context}
        context_manager.mark_context_injected()
    
    return result
```

**Lesson**: Enhance existing patterns rather than rebuilding - maintains backward compatibility.

#### **Performance-First Design**

**Requirement**: Auto-context overhead < 500ms for enterprise acceptance.

**Implementation**:
- **Lazy Initialization**: Context only created when needed
- **Single Injection**: Context injected once per session only
- **Lightweight State**: Minimal memory footprint (< 1MB)
- **Graceful Degradation**: Context failures don't break tool execution

**Measured Results**: 45-120ms initialization overhead in production.

### **12.3 MCP Client Compatibility Lessons**

#### **Critical MCP Limitation Discovery**

**Problem**: MCP clients cannot render complex JSON objects from prompts.

**Failed Approach**:
```python
@mcp_prompt(...)
async def context_prompt() -> Dict[str, Any]:
    return {"status": "initialized", "guidance": {...}}  # ❌ FAILS
```

**Error**: `MCP error 0: Error rendering prompt: Could not convert prompt result to message`

**Solution**:
```python
@mcp_prompt(...)
async def context_prompt() -> str:  # ✅ WORKS
    return f"""🦜 **Bridget's Guidance**
    
    Environment: {environment}
    Safety Level: {safety_level}
    """
```

**Critical Rule**: **MCP prompts MUST return simple strings, never complex objects.**

#### **Async Function Registry Handling**

**Discovery**: Registry must properly detect and handle async prompt functions.

```python
async def execute_prompt(prompt_name: str, **arguments) -> Any:
    prompt_function = prompt_metadata["function"]
    
    # Critical: Handle both sync and async functions
    if inspect.iscoroutinefunction(prompt_function):
        return await prompt_function(**arguments)
    else:
        return prompt_function(**arguments)
```

### **12.4 User Experience Revolution**

#### **Zero-Configuration Philosophy** 

**Design Principle**: Users should get intelligent guidance without any setup.

**Implementation**:
- **Automatic Environment Detection**: No manual configuration required
- **Smart Defaults**: Conservative safety levels for unknown environments  
- **Graceful Fallback**: System works even if detection fails
- **Override Capability**: Advanced users can customize via environment variables

**Result**: Perfect balance of automation and control.

#### **Persona Consistency Pattern**

**Challenge**: Maintain consistent Bridget persona across all interactions.

**Solution**: Centralized persona management with standardized messaging:

```python
class BridgetPersona:
    @staticmethod
    def get_introduction(workflow_name: str, user_context: str) -> str:
        return f"""🦜 **Bridget's {workflow_name}**
        
        *Hallo! Bridget hier, jouw NetBox Infrastructure Guide!*
        
        {context_specific_guidance}
        
        ---
        *Bridget - NetBox Infrastructure Guide | NetBox MCP v0.11.0+ | 🦜 LEGO Parrot Mascotte*"""
```

**Lesson**: Centralize persona messaging to ensure consistency across all touchpoints.

### **12.5 Enterprise Safety Architecture**

#### **Environment-Based Safety Assignment**

**Innovation**: Automatic safety level assignment based on environment detection.

```python
safety_mapping = {
    'demo': 'standard',     # Encourages experimentation
    'staging': 'high',      # Enhanced validation
    'production': 'maximum', # Comprehensive protection
    'cloud': 'high',        # Cloud best practices
    'unknown': 'maximum'    # Conservative fallback
}
```

**Key Insight**: Safety levels should match operational reality of each environment.

#### **Context-Aware Guidance**

**Revolutionary Approach**: Guidance adapts to detected environment automatically.

**Production Environment**:
```
🚨 ALTIJD eerst dry-run mode gebruiken!
Dubbele bevestiging VERPLICHT voor alle wijzigingen
```

**Demo Environment**:
```
🧪 Experimenteren en testen is aangemoedigd!
Dry-run mode aanbevolen maar niet verplicht
```

**Result**: Users get appropriate guidance without manual configuration.

### **12.6 Development Patterns for Auto-Context**

#### **Context State Management**

**Pattern**: Immutable context state with defensive programming:

```python
@dataclass
class ContextState:
    environment: str
    safety_level: str
    instance_type: str
    context_initialized: bool
    initialization_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Safe serialization for API responses."""
        return asdict(self)
```

**Lesson**: Use immutable dataclasses for context state to prevent accidental modification.

#### **Error Handling Philosophy**

**Principle**: Context system failures should never break tool functionality.

```python
try:
    context_manager.initialize_context()
    bridget_context = generate_bridget_context()
except Exception as e:
    logger.warning(f"Context initialization failed: {e}")
    # Continue without context - tools still work
    bridget_context = None
```

**Result**: Bulletproof reliability with graceful degradation.

### **12.7 Testing Auto-Context Systems**

#### **Multi-Environment Testing Pattern**

**Challenge**: Test environment detection across all URL patterns.

```python
@pytest.mark.parametrize("url,expected_env,expected_safety", [
    ("https://demo.netbox.local", "demo", "standard"),
    ("https://staging.netbox.company.com", "staging", "high"),
    ("https://netbox.company.com", "production", "maximum"),
    ("https://company.cloud.netboxapp.com", "cloud", "high"),
])
def test_environment_detection(url, expected_env, expected_safety):
    env, safety, _ = context_manager.detect_environment_from_url(url)
    assert env == expected_env
    assert safety == expected_safety
```

#### **Thread Safety Validation**

**Critical Test**: Singleton behavior under concurrent access:

```python
def test_thread_safe_singleton():
    def create_instance():
        return BridgetContextManager.get_instance()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_instance) for _ in range(10)]
        instances = [f.result() for f in futures]
    
    # All instances must be the same object
    assert all(instance is instances[0] for instance in instances)
```

### **12.8 Architecture Integration Success**

#### **Backward Compatibility Achievement**

**Success**: 100% backward compatibility maintained with existing tools.

- ✅ All 112+ tools work unchanged
- ✅ Existing tool signatures preserved  
- ✅ No breaking changes in API responses
- ✅ Optional context enhancement only

#### **Performance Metrics**

**Measured Performance**:
- **Initialization**: 45-120ms (well under 500ms requirement)
- **Memory Usage**: < 1MB context state
- **Subsequent Calls**: Zero performance impact
- **Thread Safety**: No contention under load

### **12.9 Future Auto-Context Development**

#### **Extensibility Points**

**Architecture Support**:
- **Custom Environment Patterns**: User-configurable detection rules
- **Multi-Language Personas**: Beyond Dutch localization
- **Plugin Contexts**: Third-party context providers
- **Advanced Safety Profiles**: Granular safety rules per tool

#### **Planned Enhancements**

**Roadmap**:
- **Context Analytics**: Usage metrics and optimization insights
- **Integration Webhooks**: External system notifications
- **Custom Personas**: Alternative persona implementations
- **Environment Adapters**: Non-URL-based detection methods

### **12.10 Key Success Factors**

1. **Zero-Configuration Philosophy**: Automatic detection with manual overrides
2. **Thread-Safe Implementation**: Enterprise-grade concurrency handling
3. **MCP Client Compatibility**: String-only prompt returns for universal support
4. **Graceful Degradation**: Context failures don't break functionality
5. **Performance First**: Sub-500ms overhead requirement met
6. **Backward Compatibility**: 100% compatibility with existing tools maintained

**Critical Takeaway**: Auto-context systems must enhance user experience without compromising reliability or performance.

-----

## **13. Future Development**

### **13.1 Extension Points**

  - **New Domains**: Easy addition of new NetBox domains as they become available.
  - **Enhanced Tools**: Build upon the dual-tool pattern for domain-specific workflows.
  - **Integration Tools**: Create cross-domain operations leveraging multiple NetBox APIs.
  - **Advanced Prompts**: Build upon the Bridget persona system for complex multi-domain workflows.

### **13.2 Architecture Scalability**

The hierarchical domain structure and Registry Bridge pattern support:

  - **Unlimited Tool Growth**: No architectural limits on tool count.
  - **Domain Expansion**: Easy addition of new NetBox domains.
  - **Enterprise Features**: Built-in safety, caching, and performance optimization.
  - **Prompt Orchestration**: Intelligent workflow guidance on top of atomic tools.
