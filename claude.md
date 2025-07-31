# NetBox MCP Server - Claude Context Guide

This document provides comprehensive context about the NetBox MCP Server, enabling Claude to effectively interact with NetBox infrastructure through natural language using the Model Context Protocol.

## 1. Overview – Purpose of the NetBox MCP Server

### Definition & Purpose
The NetBox MCP Server is a **comprehensive read/write Model Context Protocol server for NetBox network documentation and IPAM systems**. It allows you to "talk" to your NetBox infrastructure using natural language through Claude by exposing NetBox operations as AI-accessible tools. In essence, it serves as intelligent middleware that bridges Claude with NetBox, enabling conversational infrastructure management as if you were discussing with a knowledgeable colleague.

*Source: [NetBox MCP Server Overview](https://glama.ai/mcp/servers/@Deployment-Team/netbox-mcp)*

### Context (What is NetBox?)
NetBox is an open-source platform for network documentation and IP address management (IPAM), widely used by network engineers and infrastructure teams for maintaining accurate records of their network infrastructure, devices, and IP allocations.

### Model Context Protocol (MCP)
This server adheres to the **Model Context Protocol standard** - a framework that enables AI applications to connect to tools and data in a secure, standardized way. MCP provides the foundation for Claude to safely perform operations on external systems through well-defined "tools" with proper authentication and safety mechanisms.

*Learn more: [Model Context Protocol](https://modelcontextprotocol.io/)*

### Bridget Persona
**Bridget** is the built-in AI persona and Infrastructure Guide within NetBox MCP. She provides:
- **Automatic environment detection** (demo/staging/production)
- **Context-aware safety recommendations** based on detected environment
- **Friendly, professional guidance** throughout NetBox operations
- **Intelligent welcome messages** with environment-specific tips
- **Consistent persona** that ensures you always know you're interacting with NetBox MCP

Bridget automatically greets users on first interaction and provides ongoing contextual guidance throughout your NetBox management session.

*Source: [Bridget Auto-Context Documentation](https://github.com/Deployment-Team/netbox-mcp/wiki/Bridget-Auto-Context)*

---

## 2. MCP API and Tool Usage

### MCP Tools Concept
The server exposes **140+ MCP "tools"** - each tool functions like a callable operation corresponding to a NetBox action (reading data or making changes). Tools have standardized names (e.g., `netbox_list_all_sites`, `netbox_create_device`) and defined parameters. Claude invokes these tools to perform NetBox operations on your behalf.

### Read vs Write Tools - Dual-Pattern Design
The architecture follows a **revolutionary dual-pattern design** where each resource domain implements:
- **"Info" tools** for detailed retrieval of single items (e.g., `netbox_get_site_info`)
- **"List_all" tools** for bulk listing and exploration (e.g., `netbox_list_all_sites`)

This mimics natural human exploration patterns: first list or search for resources, then drill down into specifics. This consistent pattern across all domains makes the tools intuitive and predictable.

*Source: [Dual-Tool Pattern Architecture](https://glama.ai/mcp/servers/@Deployment-Team/netbox-mcp#:~:text=%23%20Revolutionary%20Dual)*

### Tool Discovery (Self-Describing API)
The server is **self-describing** with REST API endpoints:
- `/api/v1/tools` - Lists all available tools and their metadata
- `/api/v1/execute` - Executes tool operations  
- `/api/v1/status` - Health and status monitoring

Claude automatically queries these endpoints to understand available tools and their parameters, enabling dynamic tool discovery and usage.

### Example Tools by Domain

**DCIM Tools (73 total)**:
- `netbox_list_all_devices` - List all devices with filtering
- `netbox_get_device_info` - Get detailed information about a specific device
- `netbox_create_device` - Add a new device to NetBox
- `netbox_provision_new_device` - Complete device provisioning workflow

**IPAM Tools (16 total)**:
- `netbox_find_next_available_ip` - Find next available IP addresses in a prefix
- `netbox_create_prefix` - Add new network prefixes
- `netbox_assign_ip_to_interface` - Cross-domain IP assignment to device interfaces
- `netbox_get_prefix_utilization` - Comprehensive prefix utilization reports

**Tenancy Tools (8 total)**:
- `netbox_onboard_new_tenant` - Multi-step tenant onboarding automation
- `netbox_list_all_tenants` - Bulk tenant discovery
- `netbox_get_tenant_resource_report` - Comprehensive tenant resource reporting

**Extras Tools (2 total)**:
- `netbox_create_journal_entry` - Add audit log entries to any NetBox object
- `netbox_list_all_journal_entries` - Bulk journal entry discovery

*For complete tool listing, see: [API Reference](https://github.com/Deployment-Team/netbox-mcp/wiki/API-Reference)*

### Write Operations & Safety Mechanisms
Since the server can modify NetBox data, comprehensive safety mechanisms ensure secure operations:

- **Explicit Confirmation**: All write operations require `confirm=true` parameter to execute
- **Global Dry-Run Mode**: `NETBOX_DRY_RUN=true` environment variable prevents real changes
- **Idempotent Operations**: All tools are designed to be safely repeatable
- **Audit Logging**: Comprehensive logging of all operations for compliance

These features ensure Claude won't accidentally modify critical infrastructure data unless explicitly confirmed.

*Source: [Safety & Enterprise Features](https://glama.ai/mcp/servers/@Deployment-Team/netbox-mcp#:~:text=CRITICAL%20SAFETY%20CONTROLS)*

### Authentication
The server uses NetBox API tokens (configured via `NETBOX_TOKEN` environment variable) for all NetBox communication. Authentication is handled transparently - no user intervention required during Claude interactions.

---

## 3. Architecture Highlights

### Hierarchical Module Design
The server organizes functionality into **domain-based modules** (DCIM, IPAM, Virtualization, Tenancy, etc.), each implementing comprehensive tool sets relevant to that domain. This modular architecture ensures scalability and maintainable code organization.

*Source: [Architecture Overview](https://github.com/Deployment-Team/netbox-mcp/wiki#:~:text=code%20organization%20for%20unlimited%20expansion)*

### Revolutionary Dual-Tool Pattern
Every NetBox domain implements the **"Revolutionary Hierarchical Architecture"** with consistent patterns:
- **Info tools** return detailed data for single objects
- **List_all tools** return collections with comprehensive filtering options
- **Cross-domain integration** enables relationship tracking between DCIM, IPAM, and Tenancy

This ensures predictable behavior across all 140+ tools with consistent parameter patterns and response formats.

### MCP Decorators & Discovery
Tools are defined using the **`@mcp_tool` decorator** which automatically:
- Registers tools in the internal registry
- Generates metadata and parameter schemas
- Enables programmatic tool discovery
- Provides type validation and documentation

This self-describing architecture allows Claude to query available tools and understand their parameters dynamically.

### FastAPI & REST Interface
Built on **Python FastAPI**, the server exposes tools via RESTful API endpoints compatible with any MCP-compatible client. The robust foundation ensures enterprise-grade performance and reliability.

### Auto-Context Layer (Bridget)
Bridget's auto-context system follows this pipeline:
**Auto-Context Detection → Environment Assessment → Safety Assignment → Persona Guidance**

On first tool interaction, Bridget:
- Detects environment type (demo/staging/production)
- Assigns appropriate safety level (standard/high/maximum)
- Provides contextual welcome message with environment-specific guidance
- Maintains consistent persona throughout the session

*Source: [Bridget Auto-Context Pipeline](https://glama.ai/mcp/servers/@Deployment-Team/netbox-mcp#:~:text=%23%23%20Bridget%20Auto)*

### Enterprise-Grade Features
**Production-ready capabilities**:
- **Secrets Management**: Environment variables, Docker secrets, Kubernetes secrets support
- **Structured Logging**: JSON logging compatible with ELK Stack, Splunk, Datadog
- **Performance Optimization**: TTL-based caching with **33%+ performance improvements**
- **Transaction Safety**: **Atomic operations with rollback capabilities**
- **Monitoring**: Correlation IDs, operation timing, cache statistics

*Source: [Enterprise Features](https://glama.ai/mcp/servers/@Deployment-Team/netbox-mcp#:~:text=Enterprise%20Hardening)*

### Summary
NetBox MCP Server is a **self-contained, robust service** with 140+ tools covering comprehensive NetBox use-cases via AI interaction. The modular architecture, enterprise safety features, and Bridget's intelligent guidance make it suitable for production infrastructure management through conversational AI.

---

## 4. Example Usage Flows (Prompts & Tool Interaction)

### Example 1: Device Provisioning Workflow
**Scenario**: "User wants to add a new network device to NetBox in a safe manner"

**Step-by-Step Flow**:

1. **Exploration Phase**: 
   - User asks: *"What sites do we have in NetBox?"*
   - Claude calls: `netbox_list_all_sites` to retrieve site listing
   - User selects site: *"Show me details for Datacenter-01"*
   - Claude calls: `netbox_get_site_info site_name="Datacenter-01"` for site verification
   - Optional: `netbox_list_all_racks site_name="Datacenter-01"` for rack availability

2. **Dry-Run Creation** (Following Bridget's Safety Guidance):
   - User requests: *"Add a new switch device (Cisco 2960X, access-switch role) in Datacenter-01"*
   - Claude performs dry-run first: 
     ```
     netbox_create_device name="switch-dc01-01" site="Datacenter-01" 
     device_type="Cisco-2960X" role="access-switch" confirm=false
     ```
   - Bridget provides guidance: *"(Dry run) Here's what would be created. Please review and confirm to proceed."*

3. **Actual Creation**:
   - After user reviews dry-run output and confirms
   - Claude executes: Same parameters with `confirm=true`
   - Bridget acknowledges successful creation and logs the action

4. **Result Confirmation**:
   - Claude reports: *"Device switch-dc01-01 has been created in NetBox under site Datacenter-01"*
   - Provides key details from response (device ID, status, etc.)

**Key Patterns**: Context gathering → dry-run validation → user confirmation → actual execution with Bridget safety guidance

### Example 2: IP Address Management Workflow  
**Scenario**: "User needs to assign an IP address to a device interface, ensuring it's available"

**Step-by-Step Flow**:

1. **Capacity Assessment**:
   - User asks: *"What's the utilization of 10.1.0.0/24 network?"*
   - Claude calls: `netbox_get_prefix_utilization prefix="10.1.0.0/24"`
   - Bridget adds context: *"This prefix is 40% utilized with 153 addresses available"*

2. **IP Discovery**:
   - Claude calls: `netbox_find_next_available_ip prefix="10.1.0.0/24" count=5`
   - Returns next 5 available IPs (e.g., .5, .6, .7, .8, .9)
   - Claude presents options to user

3. **IP Assignment**:
   - User requests: *"Assign the first available IP to interface vlan100 on switch-dc01-01"*
   - Claude executes:
     ```
     netbox_assign_ip_to_interface device_name="switch-dc01-01" 
     interface_name="vlan100" ip_address="10.1.0.5/24" confirm=true
     ```

4. **Result Validation**:
   - Claude confirms successful IP assignment
   - Reports any conflicts or validation errors if they occur

**Key Patterns**: Capacity planning → availability verification → assignment execution with real-time validation

### Example 3: Tenant Onboarding Workflow
**Scenario**: "User wants to onboard a new tenant into NetBox with complete setup"

**Step-by-Step Flow**:

1. **Comprehensive Onboarding**:
   - User requests: *"Onboard new tenant ACME-Corp with full setup"*
   - Claude calls: 
     ```
     netbox_onboard_new_tenant tenant_name="ACME-Corp" 
     description="ACME Corporation Infrastructure" 
     contact_name="John Smith" contact_email="john@acme.com" confirm=true
     ```

2. **Bridget Process Guidance**:
   - Bridget explains: *"Creating tenant ACME-Corp with associated records..."*
   - *"Setting up default contact information and tenant group assignments..."*
   - *"Configuring initial resource allocations..."*

3. **Multi-Step Results**:
   - Tool returns comprehensive results: tenant ID, contact records, group assignments
   - Claude summarizes: *"Successfully onboarded ACME-Corp (ID: 15) with contact John Smith and default configurations"*

**Key Patterns**: Single high-level tool executing complex multi-step workflow with Bridget providing process transparency

*For additional workflow examples, see: [Official Usage Examples](https://github.com/Deployment-Team/netbox-mcp/wiki)*

---

## 5. Integration Steps

### MCP Configuration Setup
Create `.mcp.json` configuration file:
```json
{
  "mcpServers": {
    "netbox": {
      "command": "python",
      "args": ["-m", "netbox_mcp"],
      "env": {
        "NETBOX_URL": "https://your-netbox.example.com",
        "NETBOX_TOKEN": "your-api-token"
      }
    }
  }
}
```

### Environment Variables
**Required**:
- `NETBOX_URL`: Full URL to your NetBox instance
- `NETBOX_TOKEN`: NetBox API token with appropriate permissions

**Optional**:
- `NETBOX_DRY_RUN=true`: Enable global dry-run mode for testing
- `NETBOX_ENVIRONMENT`: Override environment detection (demo/staging/production)
- `NETBOX_SAFETY_LEVEL`: Override safety level (standard/high/maximum)

### Docker Deployment
```bash
docker run -d \
  --name netbox-mcp \
  -e NETBOX_URL="https://your-netbox.example.com" \
  -e NETBOX_TOKEN="your-api-token" \
  -p 8080:8080 \
  controlaltautomate/netbox-mcp:latest
```

### Safety Configuration
- **Development**: Use dry-run mode initially: `NETBOX_DRY_RUN=true`
- **Staging**: Test with confirm=false first, then confirm=true
- **Production**: Bridget automatically enables maximum safety protocols

*For detailed installation instructions, see: [Installation Guide](https://github.com/Deployment-Team/netbox-mcp/wiki/Installation)*

---

## 6. References to Official Documentation

This document provides essential context for Claude's NetBox MCP interaction. For comprehensive information, consult these official resources:

### Complete Documentation
- **[NetBox MCP Wiki](https://github.com/Deployment-Team/netbox-mcp/wiki)** - Complete documentation hub
- **[API Reference](https://github.com/Deployment-Team/netbox-mcp/wiki/API-Reference)** - Complete tool documentation with parameters and examples
- **[Installation Guide](https://github.com/Deployment-Team/netbox-mcp/wiki/Installation)** - Detailed setup and deployment instructions
- **[Docker Guide](https://github.com/Deployment-Team/netbox-mcp/wiki/Docker)** - Container deployment and configuration

### Usage & Examples  
- **[Usage Examples](https://github.com/Deployment-Team/netbox-mcp/wiki)** - Additional workflow examples and patterns
- **[Enterprise Showcase](https://github.com/Deployment-Team/netbox-mcp/wiki/Enterprise-Showcase)** - Real-world use cases and implementations
- **[Bridget Auto-Context Guide](https://github.com/Deployment-Team/netbox-mcp/wiki/Bridget-Auto-Context)** - Complete Bridget persona documentation
- **[Bridget Technical Implementation Guide](https://https://raw.githubusercontent.com/wiki/Deployment-Team/netbox-mcp/Bridget-Technical-Implementation.md)** - Developer and administrator guide to Bridget's Auto-Context System architecture and implementation
- **[Bridget Workflow Examples](https://raw.githubusercontent.com/wiki/Deployment-Team/netbox-mcp/Bridget-Workflow-Examples.md)** - Real-world scenarios demonstrating Bridget's intelligent guidance across different environments

### Community & Support
- **[GitHub Repository](https://github.com/Deployment-Team/netbox-mcp)** - Source code and issue tracking
- **[GitHub Issues](https://github.com/Deployment-Team/netbox-mcp/issues)** - Bug reports, feature requests, and discussions
- **[MCP Server Directory](https://glama.ai/mcp/servers/@Deployment-Team/netbox-mcp)** - Official MCP registry listing

### Technical Specifications
- **Requirements**: Python 3.10+, NetBox 3.5+, valid API token
- **Current Version**: 1.0.0 (Production Release)
- **License**: MIT License

---

*This context guide enables Claude to effectively interact with NetBox infrastructure through the MCP server while following proper safety protocols and leveraging Bridget's intelligent guidance system.*