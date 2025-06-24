Of course. You've made an important clarification about the project's identity. Redefining "MCP" as a "Model-Context Protocol" is a powerful concept that better reflects the project's purpose as an intelligent bridge between a Large Language Model (LLM) and a system of record like NetBox.

Here is the updated Development Guide, rewritten entirely in English and incorporating this new, more accurate definition.

-----

### **NetBox MCP - Development Guide**

#### **1. Introduction**

Welcome to the development guide for the NetBox Model-Context Protocol (MCP). This document is the central source of truth for developing new tools and extending the functionality of the MCP.

The goal of this guide is to ensure that every contribution upholds the project's high standards of quality, maintainability, and architectural integrity. Adherence to these guidelines is mandatory for all development work.

#### **2. Core Architectural Principles**

The MCP is built on three fundamental principles that define its purpose and design:

1.  **Model-Context Protocol:** The MCP is not just an API wrapper; it's a specialized protocol implementation designed for LLMs. It exposes complex backend systems (like NetBox) as a structured set of "tools" that an LLM can dynamically discover and execute. It provides the **context** (through well-defined tools) for the **model** (the LLM) to operate effectively.
2.  **High-Level Abstraction:** We hide the complexity of the underlying NetBox API. Tools must accept simple, human-understandable parameters (like names) and handle the internal logic (looking up IDs, composing complex API requests) transparently.
3.  **Modular & Scalable Structure:** Functionality is strictly separated by domain and model, mirroring the structure of NetBox itself. This ensures the codebase remains clean, organized, and scalable.

#### **3. Project Structure Overview**

The repository follows a strict, domain-driven structure:

```
netbox-mcp/
├── docs/                     # All documentation, including this guide.
├── netbox_mcp/
│   ├── client.py             # The dynamic NetBox API client.
│   ├── registry.py           # The @mcp_tool decorator and tool registry.
│   └── tools/                # THE CORE: All high-level tools.
│       ├── __init__.py         # Central loading point for all tools.
│       ├── dcim/               # Tools for the DCIM domain.
│       │   ├── __init__.py
│       │   └── devices.py
│       └── ipam/               # Tools for the IPAM domain.
│           ├── __init__.py
│           └── prefixes.py
└── tests/                    # All tests, mirroring the tools structure.
    └── tools/
        └── dcim/
            └── test_devices.py
```

#### **4. The Mandatory Development Workflow**

Every task, from a minor bugfix to a new feature, must follow this process:

1.  **Create a GitHub Issue:** Before writing any code, create a detailed GitHub Issue. This describes the "what" and "why" of the task.
2.  **Implement in a Separate Branch:** Create a new Git branch for your work, named in reference to the issue number (e.g., `feature/issue-45-vlan-tools`).
3.  **Write or Update Tests:** All new functionality must be accompanied by tests. For a bugfix, first write a test that reproduces the bug, then validate that the test passes after your fix.
4.  **Ensure 100% Test Success:** Before opening a Pull Request, the **entire** test suite must pass locally with 100% success.
5.  **Ask for Help (If Needed):** If you get stuck, have doubts about the approach, or have architectural questions, stop implementation. Create a new file in the `/docs` directory named `ask-gemini-<github-issue-number>.md`. Detail your problem or question and wait for advice before proceeding.

#### **5. Guide: Creating a New High-Level Tool**

Follow these steps to add a new tool to the MCP.

##### **Step 1: Find the Right Location**

Determine which domain and model your tool belongs to.

  * A tool to manage VLANs? → `tools/ipam/vlans.py`
  * A tool for a NetBox plugin named "my-plugin"? → `tools/plugins/my_plugin/main.py`

##### **Step 2: Write the Function Template**

Every tool function follows a consistent pattern:

```python
# In e.g., tools/ipam/vlans.py
from netbox_mcp.registry import mcp_tool
from netbox_mcp.client import NetBoxClient
from netbox_mcp.exceptions import McpError
import logging

logger = logging.getLogger(__name__)

@mcp_tool
def create_vlan(
    vlan_id: int,
    name: str,
    site_name: str,
    client: NetBoxClient,
    confirm: bool = False
) -> dict:
    """
    Creates a new VLAN and assigns it to a specific site.
    """
    # Logic goes here
```

**Key Elements:**

  * The `@mcp_tool` decorator is mandatory.
  * The function must have clear type hints.
  * The `client: NetBoxClient` parameter is required for API interaction.
  * Every "write" tool **must** include a `confirm: bool = False` parameter for safety.

##### **Step 3: Implement the Logic (The "Read-Validate-Write-Invalidate" Pattern)**

This pattern is the core of every reliable write tool.

```python
    # Inside the create_vlan function:
    if not confirm:
        raise McpError("Confirmation is required to create a VLAN.")

    # 1. DEFENSIVE READ: Check for conflicts WITHOUT cache
    existing_vlan = client.ipam.vlans.get(vid=vlan_id, site=site_name, no_cache=True)
    if existing_vlan:
        raise McpError(f"Conflict: VLAN {vlan_id} already exists in site '{site_name}'.")

    # 2. VALIDATE: Look up dependencies
    site = client.dcim.sites.get(name=site_name)
    if not site:
        raise McpError(f"Site '{site_name}' not found.")

    # 3. WRITE: Execute the action
    try:
        new_vlan = client.ipam.vlans.create(
            vid=vlan_id,
            name=name,
            site=site.id
        )
    except Exception as e:
        raise McpError(f"Failed to create VLAN in NetBox: {e}")

    # 4. INVALIDATE: (Not strictly needed for 'create', but essential for 'update')
    # Example for an update: client.cache.invalidate_for_objects(updated_vlan)

    return {
        "status": "success",
        "message": f"VLAN {new_vlan.vid} ({new_vlan.name}) created successfully.",
        "data": new_vlan.serialize()
    }
```

##### **Step 4: Register the Tool**

Make the new tool visible to the MCP by importing it into its domain's `__init__.py` file.

  * **File:** `tools/ipam/__init__.py`
  * **Action:** Add the import line.
    ```python
    # In tools/ipam/__init__.py
    from .vlans import create_vlan
    # ... other ipam imports
    ```

#### **6. Testing Your Tool**

  * Mirror the file location in the `tests/` directory (e.g., `tests/tools/ipam/test_vlans.py`).
  * Write tests for both the "happy path" (everything works as expected) and failure scenarios (e.g., what happens if a conflicting VLAN already exists?).
  * Use `pytest` fixtures to manage test data (e.g., creating and cleaning up a temporary `site`). This guarantees test isolation.

-----

This guide establishes the foundation for the continued growth of the NetBox MCP. By following these principles and workflows, we ensure the platform remains clean, stable, and a pleasure to work on.
