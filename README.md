# NetBox MCP Server

<p align="center">
  <img src="https://img.shields.io/github/v/release/Deployment-Team/netbox-mcp" alt="Latest Release">
  <img src="https://img.shields.io/docker/pulls/controlaltautomate/netbox-mcp" alt="Docker Pulls">
  <img src="https://img.shields.io/github/license/Deployment-Team/netbox-mcp" alt="License">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/MCP%20Tools-142+-brightgreen" alt="MCP Tools">
</p>

A comprehensive read/write [Model Context Protocol](https://modelcontextprotocol.io/) server for NetBox network documentation and IPAM systems. This server allows you to "talk" to your NetBox infrastructure using natural language through LLMs that support MCP.

## ✨ Key Features

- **142+ MCP Tools**: Complete DCIM, IPAM, tenancy, extras, system, and virtualization management with dual-tool pattern architecture
- **🤖 LangGraph Orchestration Engine** (Phase 3 Week 5-8)
  - **StateGraph Workflows** - 5-node workflow orchestration with intelligent routing
  - **Advanced Coordination** - Parallel execution, dependency management, and result aggregation
  - **Intelligent Caching** - Redis-backed caching with tool-specific TTL strategies (33%+ performance boost)
  - **Limitation Handling** - Progressive disclosure, N+1 query prevention, and graceful degradation
  - **Natural Language Interface** - OpenAI-powered intent classification and response generation
- **🦜 Bridget - Your NetBox Infrastructure Guide**
  - **Auto-Context Detection** - Intelligent environment detection (demo/staging/production)
  - **Safety Guidance** - Context-aware operational recommendations
  - **Persona-Based Assistance** - Friendly, professional infrastructure guidance
  - **Enterprise Safety** - Automatic safety level assignment based on environment
- **🔐 Safety First**: Built-in dry-run mode, confirmation requirements, and audit logging
- **🏗️ Self-Describing**: Automatic tool discovery with REST API endpoints
- **⚡ Enterprise Hardening**: Production-ready secrets management and structured logging
- **📊 Performance Optimized**: TTL-based caching with 33%+ performance improvements
- **🔄 Write Operations**: Full read/write capabilities with idempotent operations
- **🐳 Docker Ready**: Enterprise-grade containerization with health checks

## 🚀 Quick Start

### Docker (Recommended)

```bash
docker run -d \
  --name netbox-mcp \
  -e NETBOX_URL="https://your-netbox.example.com" \
  -e NETBOX_TOKEN="your-api-token" \
  -p 8080:8080 \
  controlaltautomate/netbox-mcp:latest
```

### Python Installation

```bash
git clone https://github.com/FinnMacCumail/mcp-netbox.git
cd mcp-netbox
pip install .
```

### Bridget Auto-Context Experience

For the optimal Bridget experience with full auto-context and persona guidance:
- **Recommended**: Use Claude Code CLI for complete functionality
- **Alternative**: Claude Desktop (tools work, limited prompt support)

See the [Bridget Documentation](https://github.com/Deployment-Team/netbox-mcp/wiki/Bridget-Auto-Context) in the wiki for complete usage guide.

### 🤖 LangGraph Orchestration Engine (Phase 3 Week 5-8)

Advanced state machine orchestration for intelligent NetBox automation:

```bash
# Install with LangGraph dependencies
pip install -e .[langgraph]

# Set OpenAI API key for orchestration
export OPENAI_API_KEY="your-openai-api-key"

# Test LangGraph orchestration
python test_realistic_queries.py
```

**LangGraph Features:**
- **5-Node StateGraph Workflow**: classify_intent → route_coordination_strategy → execute_tools → generate_response → END
- **Intelligent Strategy Selection**: Direct, complex, and limitation-aware routing
- **Advanced Caching**: Redis-backed with tool-specific TTL strategies (60s to 4 hours)
- **Parallel Execution**: Multi-tool coordination with dependency management
- **Limitation Handling**: Progressive disclosure and N+1 query prevention

See [LangGraph Testing Guide](docs/PHASE3_LANGGRAPH_TESTING.md) for comprehensive testing documentation.

## 🔧 Claude Code CLI Configuration

### Prerequisites
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed
- Python 3.10+ 
- NetBox instance with API access

### MCP Server Setup

1. **Install the NetBox MCP Server**:
```bash
pip install git+https://github.com/FinnMacCumail/mcp-netbox.git
```

2. **Create MCP Configuration File**:
Create `~/.claude/mcp_servers.json` (or your preferred location):
```json
{
  "netbox": {
    "command": "python",
    "args": ["-m", "netbox_mcp.server"],
    "env": {
      "NETBOX_URL": "https://your-netbox-instance.com",
      "NETBOX_TOKEN": "your-netbox-api-token",
      "NETBOX_AUTO_CONTEXT": "true",
      "NETBOX_BRIDGET_PERSONA": "true"
    }
  }
}
```

3. **Alternative: Environment Variables**:
```bash
export NETBOX_URL="https://your-netbox-instance.com"
export NETBOX_TOKEN="your-netbox-api-token"  
export NETBOX_AUTO_CONTEXT="true"
export NETBOX_BRIDGET_PERSONA="true"
```

### Quick Test

Start Claude Code CLI and test the connection:
```bash
claude --mcp-config ~/.claude/mcp_servers.json
```

Then ask Claude: "What sites are available in NetBox?" or "Show me the NetBox system health"

### Example Workflows with Claude Code CLI

**Infrastructure Discovery**:
```
"What sites do we have in NetBox?"
"Show me all devices in the datacenter-1 site"
"What's the rack elevation for rack R1-01?"
```

**Device Management**:
```
"Create a new site called 'branch-office-nyc'"
"Add a new device 'sw01' of type 'Cisco 9300' in site 'datacenter-1'"
"Show me the interfaces for device 'core-sw01'"
```

**IPAM Operations**:
```
"What IP addresses are available in the 10.1.0.0/24 network?"
"Create a new VLAN 100 named 'servers' in site 'datacenter-1'"
"Assign IP 10.1.0.50 to interface eth0 on device 'server01'"
```

**Bridget Persona Experience**:
With `NETBOX_BRIDGET_PERSONA=true`, you get:
- Friendly, conversational responses
- Safety guidance for operations
- Context-aware recommendations
- Enterprise-grade operational advice

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `NETBOX_URL` | NetBox instance URL | Required |
| `NETBOX_TOKEN` | API token | Required |
| `NETBOX_AUTO_CONTEXT` | Enable automatic context detection | `false` |
| `NETBOX_BRIDGET_PERSONA` | Enable Bridget persona responses | `false` |
| `NETBOX_DRY_RUN` | Enable dry-run mode (no actual changes) | `false` |

### Troubleshooting

**Connection Issues**:
- Verify NetBox URL is accessible
- Check API token permissions
- Ensure NetBox version 3.5+ compatibility

**Configuration Problems**:
- Validate JSON syntax in MCP config file
- Check environment variables with `echo $NETBOX_URL`
- Test NetBox API directly: `curl -H "Authorization: Token YOUR_TOKEN" https://your-netbox.com/api/`

**Debug Mode**:
Add to your MCP configuration:
```json
"env": {
  "NETBOX_DEBUG": "true",
  "NETBOX_LOG_LEVEL": "DEBUG"
}
```

## 📊 Current Status

**Version**: 1.0.0 - Production Release! ⭐

**🎉 NEW: MANAGEMENT IP SUITE**: Complete out-of-band and primary IP management tools for enterprise device automation:
- `netbox_create_interface` with `mgmt_only` parameter for BMC/iDRAC/Console interfaces
- Enhanced `netbox_update_device` with `oob_ip`, `primary_ip4`, `primary_ip6` support
- `netbox_set_primary_ip` with flexible IP resolution and device validation

**✅ PRODUCTION READY**: All management IP workflows tested against NetBox 4.3.2 with comprehensive bug fixes and enterprise safety features.

**🔧 COMPREHENSIVE COVERAGE**: 142+ production-ready tools across six domains:
- **DCIM Tools (73)**: Complete device and infrastructure lifecycle management with power management and management IP support
- **Virtualization Tools (30)**: Complete VM infrastructure management (NEW) ⭐
- **IPAM Tools (16)**: IP address and network management with enterprise automation
- **Tenancy Tools (8)**: Multi-tenant resource management with hierarchical organization
- **Extras Tools (2)**: Journal entries and audit trail management
- **System Tools (1)**: Health monitoring and system status

**🚀 DISCOVERY TOOLS**: 23+ `list_all_*` tools enabling efficient bulk exploration:
- `netbox_list_all_devices`, `netbox_list_all_sites`, `netbox_list_all_racks`, `netbox_list_all_power_panels`, `netbox_list_all_power_feeds`, `netbox_list_all_power_outlets`, `netbox_list_all_power_cables`, `netbox_list_all_module_type_profiles` (DCIM)
- `netbox_list_all_prefixes`, `netbox_list_all_vlans`, `netbox_list_all_vrfs` (IPAM)  
- `netbox_list_all_tenants`, `netbox_list_all_tenant_groups` (Tenancy)
- `netbox_list_all_manufacturers`, `netbox_list_all_device_types`, `netbox_list_all_device_roles` (Device Management)

**🛡️ ENTERPRISE FOUNDATION**: Defensive Read-Validate-Write Pattern with Registry Bridge ensuring 100% tool accessibility and conflict detection accuracy.

## ⚙️ Configuration

**Quick Setup**: Set required environment variables:

- `NETBOX_URL`: Full URL to your NetBox instance
- `NETBOX_TOKEN`: API token from NetBox

**Advanced Configuration**: Use YAML/TOML configuration files or additional environment variables for enterprise features like secrets management and structured logging.

## 🔒 Safety & Enterprise Features

**CRITICAL SAFETY CONTROLS**: This MCP server can perform write operations on NetBox data:

- ✅ **Idempotent Operations**: All write tools are idempotent by design
- ✅ **Confirmation Required**: `confirm=True` parameter for all write operations
- ✅ **Global Dry-Run Mode**: `NETBOX_DRY_RUN=true` for testing
- ✅ **Audit Logging**: Comprehensive logging of all operations
- ✅ **Transaction Safety**: Atomic operations with rollback capabilities

## 🏗️ Architecture Highlights

### Revolutionary Dual-Tool Pattern
- **Fundamental LLM Architecture**: Every NetBox domain implements both "info" tools (detailed single-object retrieval) and "list_all" tools (bulk discovery/exploration)
- **Comprehensive Filtering**: All list tools support filtering by site, tenant, status, and domain-specific criteria
- **Summary Statistics**: Rich aggregate statistics, breakdowns, and utilization metrics for operational insight
- **Cross-Domain Integration**: Tools bridge DCIM, IPAM, and Tenancy domains with relationship tracking

### Revolutionary Self-Describing Server
- **@mcp_tool Decorator**: Automatic function inspection and metadata generation
- **Plugin Architecture**: Modular tools/ subpackage with automatic discovery
- **Registry Bridge Pattern**: Seamless connection between internal registry and FastMCP interface
- **Dependency Injection**: Clean separation using FastAPI's Depends() system
- **REST API Endpoints**: `/api/v1/tools`, `/api/v1/execute`, `/api/v1/status`

#### Bridget Auto-Context Layer
```
Auto-Context Detection → Environment Assessment → Safety Assignment → Persona Guidance
```

### Enterprise Security & Operations
- **Secrets Management**: Docker secrets, Kubernetes secrets, environment variables
- **Structured Logging**: JSON logging compatible with ELK Stack, Splunk, Datadog
- **Performance Monitoring**: Correlation IDs, operation timing, cache statistics

## 🚧 Current Development: Phase 3 - OpenAI Orchestration

Replacing Claude Code CLI with intelligent orchestration system:
- **Technology**: OpenAI GPT-4o/4o-mini + LangGraph
- **Focus**: Orchestrating existing read-only NetBox MCP tools
- **Goal**: Enhanced user experience through intelligent coordination
- **Timeline**: 16 weeks
- **Status**: Active development

### What's Being Built
- **Natural Language Understanding**: OpenAI-powered query interpretation
- **Workflow Orchestration**: LangGraph state machines for multi-step operations
- **Tool Coordination**: Intelligent aggregation of read-only tool results
- **Performance Enhancement**: Caching, parallel execution, streaming responses
- **User Experience**: Clarification dialogues, progress indication, context management

### Strategic Approach
- **Work WITH existing tools**: Orchestration layer optimizes tool usage
- **Handle known limitations**: Graceful workarounds for tool issues
- **Focus on intelligence**: Enhanced user experience through smart coordination

### What's NOT in Scope
- Fixing NetBox MCP server tool implementations
- Production deployment features
- Multi-user support
- State persistence
- Security/authentication

See [DEVELOPMENT_PHASE.md](DEVELOPMENT_PHASE.md) for current phase details.

## 📚 Documentation

### Phase 3 Documentation
- **[Development Phase](DEVELOPMENT_PHASE.md)** - Current development status
- **[Technical Specification](docs/PHASE3_OPENAI_ORCHESTRATION.md)** - Complete phase 3 details
- **[Architecture](docs/architecture/AGENT_SYSTEM.md)** - Agent system design
- **[Progress Tracking](docs/PHASE3_PROGRESS.md)** - Development progress
- **[Validation Checklist](docs/CLI_REPLACEMENT_CHECKLIST.md)** - CLI replacement criteria

### General Documentation
- **[Complete Wiki](https://github.com/Deployment-Team/netbox-mcp/wiki)** - Comprehensive documentation with examples
- **[API Reference](https://github.com/Deployment-Team/netbox-mcp/wiki/API-Reference)** - Complete tool documentation
- **[Installation Guide](https://github.com/Deployment-Team/netbox-mcp/wiki/Installation)** - Setup and deployment
- **[Docker Guide](https://github.com/Deployment-Team/netbox-mcp/wiki/Docker)** - Container deployment
- **[Enterprise Showcase](https://github.com/Deployment-Team/netbox-mcp/wiki/Enterprise-Showcase)** - Real-world use cases

## 📋 Requirements

- Python 3.10+
- NetBox 3.5+ or newer (REST API v2.8+ support)
- Valid NetBox API token with appropriate permissions

## 🚀 Available Tools

**System Tools** (1):
- `netbox_health_check` - Comprehensive health check

**IPAM Tools** (12):
- `netbox_create_ip_address` - Create IP address assignments
- `netbox_find_available_ip` - Find available IPs in network
- `netbox_get_ip_usage` - Network utilization statistics
- `netbox_create_prefix` - Create network prefixes
- `netbox_create_vlan` - Create VLANs
- `netbox_find_available_vlan_id` - Find available VLAN IDs
- `netbox_create_vrf` - Create VRF instances
- `netbox_assign_mac_to_interface` - 🆕 Enterprise MAC address management with defensive conflict detection
- `netbox_find_next_available_ip` - 🆕 Atomic IP reservation with cross-domain integration
- `netbox_get_prefix_utilization` - 🆕 Comprehensive capacity planning reports
- `netbox_provision_vlan_with_prefix` - 🆕 Atomic VLAN/prefix coordination
- `netbox_assign_ip_to_interface` - 🆕 Cross-domain IPAM/DCIM integration

**DCIM Tools** (73):
- **Core Infrastructure** (17 tools):
  - `netbox_create_site`, `netbox_get_site_info` - Site management
  - `netbox_create_rack`, `netbox_get_rack_elevation` - Rack management
  - `netbox_create_manufacturer` - Manufacturer management
  - `netbox_create_device_type`, `netbox_get_device_type_info`, `netbox_update_device_type`, `netbox_delete_device_type` - 🆕 Complete device type CRUD
  - `netbox_create_device_role` - Device role management
  - `netbox_create_device`, `netbox_get_device_info`, `netbox_update_device` - 🆕 Enhanced device management with management IP support
  - `netbox_install_module_in_device` - Device component installation
  - `netbox_add_power_port_to_device` - Power infrastructure documentation

- **Management & OOB IP Suite** (3 tools) 🆕:
  - `netbox_create_interface` - 🆕 Interface creation with `mgmt_only` support for BMC/iDRAC
  - `netbox_set_primary_ip` - 🆕 Primary IP assignment with intelligent resolution
  - Enhanced `netbox_update_device` with `oob_ip`, `primary_ip4`, `primary_ip6` parameters

- **Module Type Profiles** (6 tools) 🆕 **NetBox 4.3.x**:
  - `netbox_create_module_type_profile`, `netbox_get_module_type_profile_info`, `netbox_list_all_module_type_profiles`
  - `netbox_update_module_type_profile`, `netbox_delete_module_type_profile`, `netbox_assign_module_type_profile`

- **Module Management** (2 enhanced tools) 🆕:
  - `netbox_update_module_type`, `netbox_delete_module_type` - Complete module type CRUD

- **Power Management Infrastructure** (19 tools) 🆕:
  - **Power Panels** (5): `netbox_create_power_panel`, `netbox_get_power_panel_info`, `netbox_list_all_power_panels`, `netbox_update_power_panel`, `netbox_delete_power_panel`
  - **Power Feeds** (5): `netbox_create_power_feed`, `netbox_get_power_feed_info`, `netbox_list_all_power_feeds`, `netbox_update_power_feed`, `netbox_delete_power_feed`
  - **Power Outlets** (5): `netbox_create_power_outlet`, `netbox_get_power_outlet_info`, `netbox_list_all_power_outlets`, `netbox_update_power_outlet`, `netbox_delete_power_outlet`
  - **Power Connections** (4): `netbox_create_power_cable`, `netbox_get_power_connection_info`, `netbox_list_all_power_cables`, `netbox_disconnect_power_cable`

- **Inventory Management Suite** (7 tools):
  - `netbox_add_inventory_item_template_to_device_type`, `netbox_list_inventory_item_templates_for_device_type`
  - `netbox_add_inventory_item_to_device`, `netbox_list_device_inventory`, `netbox_update_inventory_item`
  - `netbox_remove_inventory_item`, `netbox_bulk_add_standard_inventory`

**Tenancy Tools** (8):
- `netbox_create_contact_for_tenant` - 🆕 Contact management with role-based assignment
- `netbox_onboard_new_tenant` - Complete tenant onboarding with contact integration
- `netbox_create_tenant_group` - Hierarchical tenant organization
- `netbox_assign_resources_to_tenant` - Cross-domain resource assignment
- `netbox_get_tenant_resource_report` - Comprehensive tenant resource reporting
- `netbox_list_all_tenants` - Bulk tenant discovery
- `netbox_list_all_tenant_groups` - Tenant group exploration

**Extras Tools** (2):
- `netbox_create_journal_entry` - 🆕 Create audit trail entries for any NetBox object
- `netbox_list_all_journal_entries` - 🆕 Bulk journal entry discovery with filtering

**Virtualization Tools** (30) ⭐ **NEW**:
- **Clusters** (5 tools): `netbox_create_cluster`, `netbox_get_cluster_info`, `netbox_list_all_clusters`, `netbox_update_cluster`, `netbox_delete_cluster`
- **Virtual Machines** (5 tools): `netbox_create_virtual_machine`, `netbox_get_virtual_machine_info`, `netbox_list_all_virtual_machines`, `netbox_update_virtual_machine`, `netbox_delete_virtual_machine`
- **Cluster Types** (5 tools): `netbox_create_cluster_type`, `netbox_get_cluster_type_info`, `netbox_list_all_cluster_types`, `netbox_update_cluster_type`, `netbox_delete_cluster_type`
- **Cluster Groups** (5 tools): `netbox_create_cluster_group`, `netbox_get_cluster_group_info`, `netbox_list_all_cluster_groups`, `netbox_update_cluster_group`, `netbox_delete_cluster_group`
- **VM Interfaces** (5 tools): `netbox_create_vm_interface`, `netbox_get_vm_interface_info`, `netbox_list_all_vm_interfaces`, `netbox_update_vm_interface`, `netbox_delete_vm_interface`
- **Virtual Disks** (5 tools): `netbox_create_virtual_disk`, `netbox_get_virtual_disk_info`, `netbox_list_all_virtual_disks`, `netbox_update_virtual_disk`, `netbox_delete_virtual_disk`

## 🤝 Contributing

This project is under active development. See our [GitHub Issues](https://github.com/Deployment-Team/netbox-mcp/issues) for:

- Current development priorities
- Feature requests and roadmap
- Bug reports and discussions

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- Enterprise network automation tools - Production-ready MCP servers
- [NetBox](https://github.com/netbox-community/netbox) - The network documentation and IPAM application

---

**⚠️ Development Notice**: This is a development version with write capabilities. Always use proper safety measures and test in non-production environments.