# Claude Instructions for NetBox MCP Server

## Communication Language Guidelines

- **Human Communication**: Always communicate with the user in Dutch
- **Code & Documentation**: All code, documentation, comments, commit messages, and GitHub-related content must be in English
- **Reason**: This maintains accessibility for the international open-source community while allowing natural communication with the Dutch-speaking project maintainer

## Project Context

This is a NetBox MCP (Model Context Protocol) server - a Python project that provides an interface between Large Language Models and NetBox network documentation and IPAM systems. It's an enterprise-grade read/write server that allows LLMs to interact with NetBox data such as devices, racks, IP addresses, and network infrastructure.

The project is hosted as a public repository on GitHub under the Deployment Team organization.

## Development Guidelines

- Always use English for:
  - Code comments and docstrings
  - README, documentation files
  - Git commit messages
  - GitHub issues/PRs
  - Error messages and logs
  - Configuration examples

- Maintain Dutch for:
  - Direct communication with the user
  - Explanations of what you're doing
  - Questions about requirements

## Key Architecture Components

### Self-Describing Server Architecture
- **Tool Registry System** (`netbox_mcp/registry.py`): Core @mcp_tool decorator with automatic function inspection
- **Dependency Injection** (`netbox_mcp/dependencies.py`): Thread-safe singleton client management
- **Plugin Architecture** (`netbox_mcp/tools/`): Automatic tool discovery with clean module separation
- **Foreign Key Resolution**: Intelligent slug/name to ID conversion for all NetBox relationships
- **Enterprise Safety**: confirm=True, dry-run mode, comprehensive error handling, audit logging

### Production Hardening Features
- **Secrets Management** (`netbox_mcp/secrets.py`): Docker secrets, Kubernetes secrets, environment variables
- **Structured Logging** (`netbox_mcp/logging_config.py`): JSON formatting for ELK Stack compatibility
- **Performance Caching**: TTL-based caching with correlation IDs and performance timing
- **Health Endpoints**: `/health`, `/healthz`, `/readyz` for container orchestration

## Key Files

- `netbox_mcp/server.py`: Main MCP server with FastAPI REST endpoints
- `netbox_mcp/client.py`: Enhanced NetBox REST API client with caching and error handling
- `netbox_mcp/registry.py`: Core tool registry with @mcp_tool decorator
- `netbox_mcp/dependencies.py`: Dependency injection hub resolving circular imports
- `netbox_mcp/config.py`: Configuration management with secrets integration
- `netbox_mcp/tools/`: Plugin architecture with automatic tool discovery
  - `dcim_tools.py`: Data Center Infrastructure Management tools
  - `ipam_tools.py`: IP Address Management tools with high-level automation
  - `tenancy_tools.py`: Multi-tenant resource management tools
  - `system_tools.py`: System health and utility tools
- `main.py`: Application entry point
- `pyproject.toml`: Project configuration and dependencies

## Testing Commands

When making changes, always run linting and type checking if available:
- Check for available commands in the project
- Look for scripts in pyproject.toml
- Ask user for specific test/lint commands if not obvious

## Current Status

**Version: 0.9.0 - Enterprise Automation Platform**

**21 MCP Tools Implemented:**
- **System Tools** (1): Health monitoring
- **IPAM Tools** (11): IP management with high-level automation
- **DCIM Tools** (8): Device and infrastructure management
- **Tenancy Tools** (1): Multi-tenant resource management

**✅ All High-Level Enterprise Tools Complete:**
- `netbox_provision_new_device`: Revolutionary 8-step device provisioning
- `netbox_find_next_available_ip`: Atomic IP reservation with cross-domain integration
- `netbox_get_prefix_utilization`: Comprehensive capacity planning reports
- `netbox_provision_vlan_with_prefix`: Atomic VLAN/prefix coordination
- `netbox_decommission_device`: Safe device decommissioning with risk assessment
- `netbox_create_cable_connection`: Physical cable documentation with cache invalidation
- `netbox_find_duplicate_ips`: Enterprise duplicate IP detection with severity analysis
- `netbox_assign_ip_to_interface`: Cross-domain IPAM/DCIM integration
- `netbox_get_rack_inventory`: Human-readable rack inventory reports
- `netbox_onboard_new_tenant`: Formalized tenant onboarding
- `netbox_assign_resources_to_tenant`: Flexible cross-domain resource assignment
- `netbox_get_tenant_resource_report`: "Single pane of glass" tenant visibility
- `netbox_create_tenant_group`: Hierarchical tenant organization

**Enterprise Features:**
- 100% test success rates for all functions
- Comprehensive safety mechanisms (confirm=True, dry-run mode)
- Foreign key resolution and intelligent validation
- Cache invalidation patterns for data consistency
- Atomic operations with rollback capabilities
- Cross-domain integration (IPAM/DCIM/Tenancy)

## Development Standards

### Function Design Patterns
- Follow enterprise tool patterns with comprehensive parameter validation
- Implement intelligent slug/name to ID conversion for all NetBox relationships
- Use specific error types (ValidationError, ConflictError, NotFoundError)
- Apply cache invalidation pattern for all write operations
- Always implement confirm=False dry-run mode for enterprise safety

### Testing Protocol
- Test against real NetBox 4.2.9 instances with actual data
- Cover dry-run, execution, error handling, parameter validation, conflict detection
- Maintain test infrastructure (sites, devices, interfaces) for consistent testing
- Provide NetBox URLs for manual verification of created objects
- Save detailed JSON reports for each test run with timestamps and results

### Code Quality Standards
- Enterprise safety: comprehensive validation, error handling, audit trails
- Parameter validation with helpful error messages
- Atomic operations with rollback logic for multi-step operations
- Cache consistency through proper invalidation patterns
- Performance optimization with intelligent caching

## Important Resources

- **GitHub Repository**: https://github.com/Deployment-Team/netbox-mcp
- **Wiki Documentation**: Complete usage examples and API reference
- **Docker Hub**: Container images published for production deployment

## Architecture Status

**✅ PRODUCTION READY**: The NetBox MCP server has achieved enterprise-grade status with complete self-describing architecture, production hardening, and 21 sophisticated tools that transform complex multi-step workflows into intelligent single-call operations.

**v0.9.0 Complete**: Enterprise automation platform with revolutionary high-level functions providing "single pane of glass" visibility and atomic operations across all NetBox domains.