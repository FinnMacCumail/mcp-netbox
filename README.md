# NetBox MCP Server

<p align="center">
  <img src="https://img.shields.io/github/v/release/Deployment-Team/netbox-mcp" alt="Latest Release">
  <img src="https://img.shields.io/docker/pulls/controlaltautomate/netbox-mcp" alt="Docker Pulls">
  <img src="https://img.shields.io/github/license/Deployment-Team/netbox-mcp" alt="License">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/MCP%20Tools-78-brightgreen" alt="MCP Tools">
</p>

A comprehensive read/write [Model Context Protocol](https://modelcontextprotocol.io/) server for NetBox network documentation and IPAM systems. Just as our LEGO parrot mascot symbolically mimics human speech, this server allows you to "talk" to your NetBox infrastructure using natural language through LLMs that support MCP.

## ✨ Key Features

- **78 MCP Tools**: Complete DCIM, IPAM, tenancy, extras, and system management with dual-tool pattern architecture
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
git clone https://github.com/Deployment-Team/netbox-mcp.git
cd netbox-mcp
pip install .
```

## 📊 Current Status

**Version**: 0.10.2 - Core Modules Stabilized

**📦 NEW: MODULE MANAGEMENT SUITE**: 11 enterprise-grade module management tools added for comprehensive modular infrastructure lifecycle management, replacing deprecated NetBox inventory items.

**🧹 CONTINUOUS OPTIMIZATION**: Maintained clean codebase architecture with enterprise-grade reliability and performance optimization.

**🔧 STABLE CORE MODULES**: 55 production-ready tools across three domains:
- **DCIM Tools**: Complete device and infrastructure lifecycle management
- **IPAM Tools**: IP address and network management with enterprise automation
- **Tenancy Tools**: Multi-tenant resource management with hierarchical organization

**🚀 DISCOVERY TOOLS**: 11 `list_all_*` tools enabling efficient bulk exploration:
- `netbox_list_all_devices`, `netbox_list_all_sites`, `netbox_list_all_racks` (DCIM)
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

### Enterprise Security & Operations
- **Secrets Management**: Docker secrets, Kubernetes secrets, environment variables
- **Structured Logging**: JSON logging compatible with ELK Stack, Splunk, Datadog
- **Performance Monitoring**: Correlation IDs, operation timing, cache statistics

## 📚 Documentation

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

**DCIM Tools** (17):
- `netbox_create_site` - Create and manage sites
- `netbox_get_site_info` - Retrieve site information
- `netbox_create_rack` - Create equipment racks
- `netbox_get_rack_elevation` - Rack elevation view
- `netbox_create_manufacturer` - Create manufacturers
- `netbox_create_device_type` - Create device types
- `netbox_create_device_role` - Create device roles
- `netbox_create_device` - Create devices
- `netbox_get_device_info` - Retrieve device details
- `netbox_install_module_in_device` - 🆕 Device component installation with validation
- `netbox_add_power_port_to_device` - 🆕 Power infrastructure documentation
- **Inventory Management Suite** (7 tools):
  - `netbox_add_inventory_item_template_to_device_type` - 🆕 Define standard inventory for device types
  - `netbox_list_inventory_item_templates_for_device_type` - 🆕 List device type inventory templates
  - `netbox_add_inventory_item_to_device` - 🆕 Track actual inventory items on devices
  - `netbox_list_device_inventory` - 🆕 Comprehensive device inventory reporting
  - `netbox_update_inventory_item` - 🆕 Update asset information and serial numbers
  - `netbox_remove_inventory_item` - 🆕 Safe inventory item removal with validation
  - `netbox_bulk_add_standard_inventory` - 🆕 Rapid deployment with predefined presets

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