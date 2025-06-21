# Claude Instructions for NetBox Read/Write MCP Server

## Communication Language Guidelines

- **Human Communication**: Always communicate with the user in Dutch
- **Code & Documentation**: All code, documentation, comments, commit messages, and GitHub-related content must be in English
- **Reason**: This maintains accessibility for the international open-source community while allowing natural communication with the Dutch-speaking project maintainer

## Project Context

This is a NetBox Read/Write MCP (Model Context Protocol) server - a Python project that provides a conversational interface between Large Language Models and NetBox (Network Documentation and IPAM) systems. Unlike the read-only Unimus MCP, this server is designed from the ground up to support both reading and writing operations with robust safety mechanisms.

The primary goal is to create an automated workflow where network data discovered by Unimus can be used to build and maintain a NetBox instance through intelligent, idempotent operations.

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

## Core Design principles

**CRITICAL SAFETY FIRST**: This MCP server can perform destructive operations on NetBox data. All write operations must implement:

1. **Idempotency is Crucial**: Every write action (tool) must be idempotent. A tool called twice with the same parameters must produce the same end result as calling it once, without errors or unwanted duplicates.

2. **Safety First**: Built-in safety mechanisms including:
   - `confirm: bool = False` parameter for all write operations
   - Global dry-run mode (--dry-run flag or NETBOX_DRY_RUN=true env var)
   - Detailed logging of all mutations

3. **API-First Approach**: Core logic isolated in `netbox_client.py` - a well-tested wrapper around the NetBox REST API and pynetbox library.

4. **Atomic Operations**: MCP tools should perform complete, logical operations. Either fully succeed or fully fail and rollback state.

## Architecture Components

### netbox_client.py
- **Initialization**: Accepts NetBox URL, token, and configuration object
- **Read Methods**: Functions for all required GET operations with NetBox API filter capabilities
- **Write Methods**: 
  - `create_object(type, data)`: Generic object creation
  - `update_object(object)`: Uses pynetbox .save() method
  - `delete_object(object)`: Uses pynetbox .delete() method
- **Idempotent "Ensure" Methods**: Higher-level functions containing core R/W logic
  - `ensure_device(name, device_type, site)`: Find device or create if doesn't exist
  - `ensure_ip_address(address, status)`: Ensure IP address object exists
  - `assign_ip_to_interface(device, interface_name, ip_address)`: Complex relationship logic
- **Error Handling**: Translate pynetbox exceptions to consistent NetBoxError exceptions

### server.py
- **Read-Only Tools**: 
  - `netbox_get_device(name: str, site: str)`
  - `netbox_list_devices(filters: dict)`
  - `netbox_find_ip(address: str)`
  - `netbox_get_vlan_by_name(name: str, site: str)`
  - `netbox_get_device_interfaces(device_name: str)`

- **Read/Write Tools**:
  - `netbox_create_device(name: str, device_type: str, role: str, site: str, confirm: bool = False)`
  - `netbox_update_device_status(device_name: str, status: str, confirm: bool = False)`
  - `netbox_assign_ip_to_interface(device_name: str, interface_name: str, ip_address: str, confirm: bool = False)`
  - `netbox_delete_device(device_name: str, confirm: bool = False)`

- **Key Integration Tool**:
  - `netbox_ensure_device_from_unimus(unimus_device_data: dict, confirm: bool = False)`: Accepts Unimus device data and translates to proper NetBox state

### Write Operation Strategy

**CRITICAL SAFETY REQUIREMENTS**:

1. **Confirmation Parameter**: Every mutation tool must have `confirm: bool = False`. No write action unless `confirm=True`.

2. **Dry-Run Mode**: Global configuration option that logs write actions as if executed but makes no actual API calls.

3. **Detailed Logging**: Every write action must generate detailed log entries with change information and results.

4. **Response Format**: Successful write actions return the modified/created object for LLM verification:
   ```json
   {
     "status": "success", 
     "action": "created", 
     "object": {...netbox_device...}
   }
   ```

## Development Roadmap

### Phase 1: Foundation and Read-Only Core (v0.1)
- Project structure with pyproject.toml, .gitignore, README.md
- Configuration implementation (config.py) with NETBOX_URL and NETBOX_TOKEN
- NetBox Client (Read-Only) with basic GET operations
- First read-only MCP tools
- Basic Docker support
- CI/CD pipeline setup

### Phase 2: Initial Write Capabilities and Safety (v0.2)
- Write methods in client
- Safety mechanisms (confirm parameter, dry-run mode)
- First basic write tools (site, manufacturer, device role creation)
- Extensive logging implementation
- Integration tests

### Phase 3: Advanced R/W Operations and Relations (v0.3)
- Idempotent "Ensure" logic implementation
- Complex tools that create relationships
- Data mapping logic for Unimus-to-NetBox translation
- Core integration tool: `netbox_ensure_device_from_unimus`

### Phase 4: Enterprise Features and Integration-readiness (v0.4)
- Caching system for performance
- Advanced search and filter tools
- Enhanced health checks
- Documentation

### Phase 5: Production-readiness and Full Integration (v1.0)
- Performance tuning for bulk operations
- Full test coverage
- End-to-end Unimus-to-NetBox workflow
- Complete documentation
- Security hardening

## Configuration and Deployment

- **config.py**: Required NETBOX_URL and NETBOX_TOKEN variables, supports YAML/TOML and environment variables
- **Dockerfile**: Multi-stage build similar to Unimus MCP, non-root user, optimized image
- **Health Checks**: Kubernetes-style endpoints (/healthz, /readyz) validating NetBox API connectivity

## Testing Commands

When making changes, always run linting and type checking if available:
- Check for available commands in the project
- Look for scripts in pyproject.toml
- Ask user for specific test/lint commands if not obvious

## Key Files Structure (Planned)

- `server.py`: Main MCP server implementation
- `netbox_client.py`: NetBox REST API client library  
- `config.py`: Configuration management with YAML/TOML support
- `README.md`: Main project documentation
- `DESIGN.md`: Detailed design document
- `ROADMAP.md`: Development phases and milestones
- `pyproject.toml`: Project configuration and dependencies
- `Dockerfile`: Container configuration
- `docker-compose.yml`: Development environment setup

## Reference Implementation

The Unimus MCP server serves as a reference for:
- Project structure and modularity
- Configuration management patterns
- Docker containerization approach
- Testing methodology
- Documentation standards
- CI/CD pipeline setup

**Key Differences from Unimus MCP**:
- Write capabilities with safety mechanisms
- Idempotent operation design
- Confirmation parameters for all mutations
- More complex error handling for write operations
- Integration-focused tools for Unimus data processing

## Development Workflow

**IMPORTANT**: All development is tracked through GitHub Issues. DESIGN.md and ROADMAP.md content has been fully migrated to Issues for better tracking and Claude Code session continuity.

1. **Before implementing new features**: Check GitHub Issues and Milestones for current priorities
2. **Issue Management**: Use GitHub Issues for all feature requests, bugs, and roadmap tracking
3. **API integration**: Use NetBox REST API documentation and pynetbox library patterns
4. **Safety first**: Always implement confirmation and dry-run mechanisms
5. **Testing**: Test against real NetBox instances with proper safety measures
6. **Documentation**: Update relevant documentation when adding features
7. **Community**: All community interaction through GitHub Issues

## GitHub Issues Structure

**Project Management Strategy**: Complete migration from DESIGN.md/ROADMAP.md to GitHub Issues for optimal Claude Code session continuity and community engagement.

### Milestones (Version-based)
- **v0.1 - Foundation & Read-Only Core**: Project structure, config, basic read operations
- **v0.2 - Initial Write Capabilities & Safety**: Write methods, safety mechanisms, basic write tools
- **v0.3 - Advanced R/W Operations & Relations**: Idempotent operations, complex relationships, Unimus integration
- **v0.4 - Enterprise Features & Integration-readiness**: Caching, advanced tools, health checks
- **v1.0 - Production-readiness & Full Integration**: Performance tuning, full coverage, end-to-end workflows

### Issue Labels System
- **Feature Categories**:
  - `enhancement` - New features and functionality
  - `safety-critical` - Security and safety-related features (high priority)
  - `read-only` - Read-only functionality implementation
  - `read-write` - Write operation functionality (requires safety review)
  - `idempotency` - Idempotent operation design and testing
  - `integration` - Unimus-NetBox integration workflows

- **Development Categories**:
  - `documentation` - Documentation updates and improvements
  - `testing` - Test implementation and coverage
  - `configuration` - Configuration and deployment features
  - `performance` - Performance optimization and caching
  - `docker` - Container and deployment features

- **Priority & Complexity**:
  - `priority-high` - Critical features for milestone completion
  - `priority-medium` - Important but not blocking
  - `priority-low` - Nice-to-have features
  - `complexity-high` - Complex implementation requiring careful design
  - `complexity-medium` - Standard implementation complexity
  - `complexity-low` - Simple, straightforward implementation

### Issue Templates
1. **Feature Request Template**: For new functionality with safety checklist
2. **Write Operation Template**: Special template for write-capable features with idempotency requirements
3. **Integration Request Template**: For Unimus-NetBox workflow features
4. **Bug Report Template**: With write-operation impact assessment
5. **Safety Review Template**: For reviewing safety-critical implementations

### Development Priority Guidelines
1. **Safety-Critical Issues**: Always highest priority - must include confirmation mechanisms
2. **Milestone Blockers**: Issues required for version completion
3. **Integration Features**: Medium priority - focus on Unimus-NetBox workflows
4. **Enhancement Features**: Lower priority - quality of life improvements

**Benefits of GitHub Issues Approach**:
- ✅ **Claude Code Continuity**: All context available in Issues for future sessions
- ✅ **Community Engagement**: Public roadmap and feature discussions
- ✅ **Progress Tracking**: Clear milestone and completion tracking
- ✅ **Safety Focus**: Dedicated labels and templates for safety-critical features
- ✅ **Integration Planning**: Specific workflow for Unimus-NetBox integration features

## Development Instance Configuration

**NetBox Cloud Instance (Development)**
- **URL**: https://zwqg2756.cloud.netboxapp.com
- **API Token**: 809e04182a7e280398de97e524058277994f44a5
- **Configuration**: Stored in `.env` file (excluded from git via .gitignore)
- **Purpose**: Development and testing of NetBox MCP server functionality

**Environment Files**:
- `.env.example`: Template configuration file (committed to git)
- `.env`: Actual development credentials (git-ignored for security)
- Configuration loaded via environment variables with NETBOX_URL and NETBOX_TOKEN

**Security Notice**: The `.env` file containing actual credentials is excluded from git tracking. The development instance credentials are provided here for Claude's reference during development work.

## API Documentation and Testing

**✅ API Connectivity Verified (2025-06-21)**
- Full read/write access confirmed
- Authentication working properly
- Response times excellent (sub-second)

**NetBox Instance Details**:
- **Version**: NetBox 4.2.9 (latest stable)
- **Python**: 3.12.3, Django 5.1.8
- **Available Data**: 16 sites, 2 devices, 7 manufacturers
- **Test Location**: "2514JL-14" (Den Haag address)

**API Documentation Resources**:

1. **OpenAPI Schema (COMPLETE)** ✅
   - **Local File**: `netbox-api-schema.yaml` (4.3MB, downloaded 2025-06-21)
   - **Source URL**: `https://zwqg2756.cloud.netboxapp.com/api/schema/`
   - **Format**: OpenAPI 3.0.3 specification
   - **Content**: All endpoints, parameters, request/response schemas
   - **Usage**: Import in IDE/Postman for development reference

2. **Browsable API Interface** ✅
   - **Base URL**: `https://zwqg2756.cloud.netboxapp.com/api/dcim/` (with auth)
   - **Format**: Django REST Framework HTML interface
   - **Features**: Interactive API browser per endpoint
   - **Usage**: Manual testing and endpoint exploration

**Key API Endpoints for Development**:
- `/api/dcim/devices/` - Device management (CRUD operations)
- `/api/dcim/sites/` - Site management
- `/api/dcim/manufacturers/` - Manufacturer management  
- `/api/dcim/device-types/` - Device type management
- `/api/dcim/device-roles/` - Device role management
- `/api/status/` - Instance status and version info

**API Testing Results**:
- ✅ READ operations: All endpoints accessible
- ✅ WRITE operations: POST/DELETE confirmed working
- ✅ Test object lifecycle: Successfully created and deleted manufacturer
- ✅ Error handling: Proper HTTP status codes and JSON responses
- ✅ Performance: Excellent response times for all operations

**Development Resources**:
- Complete API schema available offline for reference
- All pynetbox library operations can be tested against live instance
- Sufficient test data available for comprehensive development
- Full write permissions available for testing safety mechanisms

## Current Project Status

**📋 PROJECT INITIATION PHASE**
- Design document completed ✅
- Roadmap defined ✅  
- CLAUDE.md instructions created ✅
- Environment configuration and .gitignore setup ✅
- Development NetBox instance configured ✅
- Ready to begin Phase 1 implementation

This project represents a significant advancement over read-only MCP servers by providing safe, intelligent write capabilities for NetBox automation and integration workflows.