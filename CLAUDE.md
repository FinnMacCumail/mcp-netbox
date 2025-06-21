# Claude Instructions for NetBox Read/Write MCP Server

## Communication Language Guidelines

- **Human Communication**: Always communicate with the user in Dutch
- **Code & Documentation**: All code, documentation, comments, commit messages, and GitHub-related content must be in English
- **Reason**: This maintains accessibility for the international open-source community while allowing natural communication with the Dutch-speaking project maintainer

## Project Context

This is a NetBox Read/Write MCP (Model Context Protocol) server - a Python project that provides a conversational interface between Large Language Models and NetBox (Network Documentation and IPAM) systems. This server is designed from the ground up to support both reading and writing operations with robust safety mechanisms.

The primary goal is to provide enterprise-grade NetBox automation capabilities with robust safety mechanisms, idempotent operations, and comprehensive write functionality.

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

## Architecture Consultations

**Gemini Phase 3 Architecture Consultation (June 2025)**
Based on the successful completion of Phase 2, detailed architectural guidance was sought from Gemini for Phase 3 implementation. Key recommendations implemented:

- **Hybrid Ensure Pattern**: Combines hierarchical convenience (`ensure_device(manufacturer="Cisco")`) with direct ID injection for performance (`ensure_device(manufacturer_id=5)`)
- **Selective Field Comparison**: Only compare managed fields, use hash-based diffing for efficiency, store metadata in NetBox custom fields
- **Two-Pass Strategy**: Separate core object creation from relationship establishment to avoid circular dependencies
- **Canonical Data Model**: Pydantic models with consistent tagging and metadata
- **Asynchronous Processing**: Redis + RQ task queue for enterprise-scale bulk operations with progress tracking

These architectural patterns form the foundation for enterprise-grade NetBox automation and integration workflows.

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
- **Basic Write Methods (✅ Implemented)**: 
  - `create_object(type, data, confirm=False)`: Generic object creation with safety
  - `update_object(object_id, data, confirm=False)`: Object updates with validation
  - `delete_object(object_id, confirm=False)`: Safe object deletion
- **Hybrid Ensure Methods (Phase 3 - Planned)**: Gemini-recommended architecture
  - `ensure_manufacturer(name=None, manufacturer_id=None, confirm=False)`: Hybrid pattern
  - `ensure_site(name=None, site_id=None, confirm=False)`: Name-based or ID-based
  - `ensure_device_role(name=None, role_id=None, confirm=False)`: Flexible resolution
  - `ensure_device_type(name, manufacturer_id, confirm=False)`: With dependencies
  - `ensure_device(name, device_type_id, site_id, role_id, confirm=False)`: Complex object
- **State Management (Phase 3 - Planned)**: 
  - Selective field comparison with managed fields concept
  - Hash-based diffing using NetBox custom fields
  - Efficient bulk operation pre-filtering
- **Error Handling**: Translate pynetbox exceptions to consistent NetBoxError exceptions

### server.py
- **Read-Only Tools (8 implemented)**: 
  - `netbox_health_check()`: NetBox system health and connection status
  - `netbox_get_device(name: str, site: str)`: Get device by name and site
  - `netbox_list_devices(filters: dict)`: List devices with filtering
  - `netbox_get_site_by_name(name: str)`: Get site information by name
  - `netbox_find_ip(address: str)`: Find IP address object by address
  - `netbox_get_vlan_by_name(name: str, site: str)`: Get VLAN by name and site
  - `netbox_get_device_interfaces(device_name: str)`: Get all interfaces for device
  - `netbox_get_manufacturers(limit: int)`: Get list of manufacturers

- **Write Tools (10 implemented)**:
  - `netbox_create_manufacturer(name: str, slug: str, description: str, confirm: bool = False)`: Create manufacturer
  - `netbox_create_site(name: str, slug: str, status: str, region: str, description: str, physical_address: str, confirm: bool = False)`: Create site
  - `netbox_create_device_role(name: str, slug: str, color: str, vm_role: bool, description: str, confirm: bool = False)`: Create device role
  - `netbox_update_device_status(device_name: str, status: str, site: str, confirm: bool = False)`: Update device status
  - `netbox_delete_manufacturer(manufacturer_name: str, confirm: bool = False)`: Delete manufacturer
  - `netbox_bulk_ensure_devices(devices_data: List[Dict], confirm: bool = False, dry_run_report: bool = False)`: Two-pass bulk device operations
  - `netbox_start_bulk_async(devices_data: List[Dict], confirm: bool = False, max_devices: int = 1000)`: Asynchronous bulk operations
  - `netbox_get_task_status(task_id: str)`: Monitor async task progress and results
  - `netbox_list_active_tasks()`: List all currently active async tasks
  - `netbox_get_queue_info()`: Queue statistics and system status

- **Future Integration Tools (planned)**:
  - Additional idempotent tools for complex enterprise workflows
  - Idempotent "ensure" methods for complex relationship management

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

### Phase 1: Foundation and Read-Only Core (v0.1) ✅ COMPLETE
- Project structure with pyproject.toml, .gitignore, README.md
- Configuration implementation (config.py) with NETBOX_URL and NETBOX_TOKEN
- NetBox Client (Read-Only) with basic GET operations
- 8 read-only MCP tools implemented and tested
- Docker containerization with health monitoring
- Complete API documentation and testing framework

### Phase 2: Initial Write Capabilities and Safety (v0.2) ✅ COMPLETE
- Enterprise-grade write methods in client (create_object, update_object, delete_object)
- Comprehensive safety mechanisms (confirm parameter, dry-run mode)
- 5 basic write MCP tools with comprehensive safety validation
- Extensive logging and audit trail implementation
- 100% safety test pass rate against live NetBox 4.2.9

### Phase 3: Advanced R/W Operations and Relations (v0.3) ✅ COMPLETE
**Based on Gemini's Phase 3 Architecture Recommendations**:
- **Issue #11**: ✅ Hybrid ensure pattern for core objects (convenience + performance)
- **Issue #12**: ✅ Selective field comparison and hash-based diffing (efficiency + safety)  
- **Issue #13**: ✅ Two-pass strategy for complex relationships (dependency resolution)
- **Issue #15**: ✅ Asynchronous task queue for long-running operations (enterprise scale)

### Phase 4: Enterprise Features and Integration-readiness (v0.4)
- Advanced caching system for performance optimization
- Bulk operation optimization and parallel processing
- Enhanced health checks and monitoring (Prometheus metrics)
- Configuration management for transformation rules
- Advanced search and filter tools

### Phase 5: Production-readiness and Full Integration (v1.0)
- Performance tuning for 1000+ device operations
- Complete test coverage and security hardening
- End-to-end automated device management workflows
- Comprehensive documentation and deployment guides
- Multi-tenant support and advanced security features

## Configuration and Deployment

- **config.py**: Required NETBOX_URL and NETBOX_TOKEN variables, supports YAML/TOML and environment variables
- **Dockerfile**: Multi-stage build with non-root user, optimized image
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

## Implementation Standards

This project follows enterprise MCP server patterns:
- Modular project structure
- Configuration management with environment variables
- Docker containerization approach
- Comprehensive testing methodology
- Clear documentation standards
- Automated CI/CD pipeline setup

**Key Features**:
- Write capabilities with safety mechanisms
- Idempotent operation design
- Confirmation parameters for all mutations
- Complex error handling for write operations
- Enterprise-focused tools for network automation

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
- **v0.3 - Advanced R/W Operations & Relations**: Idempotent operations, complex relationships, enterprise automation
- **v0.4 - Enterprise Features & Integration-readiness**: Caching, advanced tools, health checks
- **v1.0 - Production-readiness & Full Integration**: Performance tuning, full coverage, end-to-end workflows

### Issue Labels System
- **Feature Categories**:
  - `enhancement` - New features and functionality
  - `safety-critical` - Security and safety-related features (high priority)
  - `read-only` - Read-only functionality implementation
  - `read-write` - Write operation functionality (requires safety review)
  - `idempotency` - Idempotent operation design and testing
  - `integration` - Enterprise integration workflows

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
3. **Integration Request Template**: For enterprise workflow features
4. **Bug Report Template**: With write-operation impact assessment
5. **Safety Review Template**: For reviewing safety-critical implementations

### Development Priority Guidelines
1. **Safety-Critical Issues**: Always highest priority - must include confirmation mechanisms
2. **Milestone Blockers**: Issues required for version completion
3. **Integration Features**: Medium priority - focus on enterprise automation workflows
4. **Enhancement Features**: Lower priority - quality of life improvements

**Benefits of GitHub Issues Approach**:
- ✅ **Claude Code Continuity**: All context available in Issues for future sessions
- ✅ **Community Engagement**: Public roadmap and feature discussions
- ✅ **Progress Tracking**: Clear milestone and completion tracking
- ✅ **Safety Focus**: Dedicated labels and templates for safety-critical features
- ✅ **Integration Planning**: Specific workflow for enterprise integration features

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

**📋 PHASE 3 IMPLEMENTATION COMPLETE**
- **Issue #1-5**: Foundation & Read-Only Core ✅ (Complete)
  - Project structure, configuration, NetBox client (read-only)
  - 8 read-only MCP tools implemented and tested
  - Docker containerization with health monitoring
  - Complete API documentation and testing framework

- **Issue #6**: Write Methods in NetBox Client ✅ (Complete)  
  - Comprehensive write operations in NetBox client with enterprise-grade safety
  - create_object(), update_object(), delete_object() methods
  - Mandatory confirmation parameters and dry-run mode functionality
  - Extensive safety testing with 100% pass rate against live NetBox 4.2.9

- **Issue #7**: Basic Write MCP Tools ✅ (Complete)
  - 10 core write MCP tools implemented (6 basic + 4 async)
  - **Basic tools**: netbox_create_manufacturer, netbox_create_site, netbox_create_device_role, netbox_update_device_status, netbox_delete_manufacturer
  - **Bulk tools**: netbox_bulk_ensure_devices (synchronous two-pass operations)
  - **Async tools**: netbox_start_bulk_async, netbox_get_task_status, netbox_list_active_tasks, netbox_get_queue_info
  - All tools implement comprehensive safety mechanisms and input validation
  - Complete test suite with 100% safety validation

**🎯 PHASE 3 COMPLETED FEATURES:**
- **Issue #11**: ✅ Hybrid Ensure Pattern - Production-ready idempotent methods
- **Issue #12**: ✅ Selective Field Comparison - Hash-based diffing with managed fields
- **Issue #13**: ✅ Two-Pass Strategy - Complete bulk operations with NetBoxBulkOrchestrator
- **Issue #15**: ✅ Asynchronous Task Queue - Enterprise-scale async processing with Redis/RQ
- **Enterprise MCP Tools**: Synchronous (netbox_bulk_ensure_devices) + Asynchronous (netbox_start_bulk_async)
- **Test Coverage**: 41 comprehensive unit tests across all Phase 3 components
- **Architecture**: Stateless orchestrator + async task queue with comprehensive monitoring

**🎯 NEXT PHASE: Enterprise Features & Integration-readiness (v0.4)**

**Phase 3 Architecture Achievements (Based on Gemini Guidance)**:
- **Issue #11**: ✅ Implement Hybrid Ensure Pattern for Core Objects
  - Foundation idempotent methods for manufacturers, sites, device roles
  - Hybrid pattern supporting both name-based and ID-based operations
  - Integration with existing safety mechanisms
  - **Status**: Production ready, 17 unit tests + live validation

- **Issue #12**: ✅ Implement Selective Field Comparison and Hash-Based Diffing
  - Advanced state comparison using managed fields concept
  - Hash-based efficiency with NetBox custom fields metadata
  - Prevents overwrites of manually maintained data
  - **Status**: Production ready, 19 comprehensive tests

**Phase 3 Completed Issues**:
- **Issue #11**: ✅ Hybrid Ensure Pattern for Core Objects
  - Foundation idempotent methods for manufacturers, sites, device roles
  - Hybrid pattern supporting both name-based and ID-based operations
  - Integration with existing safety mechanisms
  - **Status**: Production ready, 17 unit tests + live validation

- **Issue #12**: ✅ Selective Field Comparison and Hash-Based Diffing
  - Advanced state comparison using managed fields concept
  - Hash-based efficiency with NetBox custom fields metadata
  - Prevents overwrites of manually maintained data
  - **Status**: Production ready, 19 comprehensive tests

- **Issue #13**: ✅ Two-Pass Strategy for Complex Relationships
  - **Phase 1**: ensure_device_type() with hybrid pattern + batch_id tracking
  - **Phase 2**: NetBoxBulkOrchestrator class for stateless coordination
  - **Phase 3**: ensure_device() method for Pass 2 relationships
  - **Phase 4**: netbox_bulk_ensure_devices MCP tool with pre-flight reporting
  - **Architecture**: Production-ready stateless design with enterprise rollback capabilities
  - **Final Status**: 24 tests passing (100% pass rate), full two-pass strategy implementation
  - **Key Features**: Bulk device operations, data normalization, comprehensive error handling, dry-run reports

**Phase 3 Completed Issues (FINAL)**:
- **Issue #15**: ✅ Asynchronous Task Queue for Long-Running Operations
  - **TaskTracker**: Redis-based progress tracking with real-time updates
  - **AsyncTaskManager**: RQ-based task queueing for enterprise-scale operations
  - **Background workers**: Dedicated processes for bulk device operations
  - **4 Async MCP Tools**: netbox_start_bulk_async, netbox_get_task_status, netbox_list_active_tasks, netbox_get_queue_info
  - **Docker deployment**: Complete async stack with Redis, workers, and monitoring
  - **Architecture**: Graceful fallback when Redis/RQ unavailable, enterprise-grade error handling
  - **Final Status**: 17 comprehensive tests, production-ready async processing

**🎯 PHASE 4 FOCUS: Enterprise Features & Integration-readiness (v0.4)**

**🔒 SAFETY STATUS**: All write operations are production-ready with enterprise-grade safety mechanisms validated against live NetBox instance.

This project represents a significant advancement over read-only MCP servers by providing safe, intelligent write capabilities for NetBox automation and integration workflows.