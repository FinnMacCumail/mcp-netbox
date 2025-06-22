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
The NetBox MCP follows Gemini AI's architectural recommendations:

- **Tool Registry System** (`netbox_mcp/registry.py`): Core @mcp_tool decorator with automatic function inspection
- **Dependency Injection** (`netbox_mcp/dependencies.py`): Thread-safe singleton client management resolving circular imports
- **Plugin Architecture** (`netbox_mcp/tools/`): Automatic tool discovery with clean module separation
- **Foreign Key Resolution**: Intelligent slug/name to ID conversion for all NetBox relationships
- **Enterprise Safety**: confirm=True, dry-run mode, comprehensive error handling, audit logging

### Production Hardening Features
- **Secrets Management** (`netbox_mcp/secrets.py`): Docker secrets, Kubernetes secrets, environment variables
- **Structured Logging** (`netbox_mcp/logging_config.py`): JSON formatting for ELK Stack compatibility
- **Performance Caching**: TTL-based caching with correlation IDs and performance timing
- **Health Endpoints**: `/health`, `/healthz`, `/readyz` for container orchestration
- **Graceful Degradation**: Server continues in degraded mode when NetBox unavailable

## Key Files

- `netbox_mcp/server.py`: Main MCP server with FastAPI REST endpoints
- `netbox_mcp/client.py`: Enhanced NetBox REST API client with caching and error handling
- `netbox_mcp/registry.py`: Core tool registry with @mcp_tool decorator
- `netbox_mcp/dependencies.py`: Dependency injection hub resolving circular imports
- `netbox_mcp/config.py`: Configuration management with secrets integration
- `netbox_mcp/tools/`: Plugin architecture with automatic tool discovery
  - `dcim_tools.py`: Data Center Infrastructure Management tools
  - `ipam_tools.py`: IP Address Management tools  
  - `system_tools.py`: System health and utility tools
- `main.py`: Application entry point
- `pyproject.toml`: Project configuration and dependencies

## Testing Commands

When making changes, always run linting and type checking if available:
- Check for available commands in the project
- Look for scripts in pyproject.toml
- Ask user for specific test/lint commands if not obvious

## Version Information

**Current version: 0.3.0 (Production Hardening Complete)**

## Recent Work Completed

### ✅ Epic 1 - Self-Describing Server Architecture (COMPLETED)

**Issues #23-26 RESOLVED** following Gemini AI's architectural guidance:

1. **Tool Registry System** (`registry.py`): COMPLETED ✅
   - @mcp_tool decorator with automatic function inspection
   - Global TOOL_REGISTRY with complete metadata storage  
   - Functions: `mcp_tool()`, `load_tools()`, `execute_tool()`, `serialize_registry_for_api()`

2. **Dependency Injection Pattern** (`dependencies.py`): COMPLETED ✅
   - Thread-safe singleton client management
   - Resolves circular import issues between server.py and client modules
   - Functions: `get_netbox_client()`, `get_netbox_config()`, `NetBoxClientManager`

3. **Plugin Architecture** (`tools/`): COMPLETED ✅ 
   - Automatic tool discovery using pkgutil
   - Clean module separation with `load_all_tools()` function
   - Support for multiple tool categories (DCIM, IPAM, System)

4. **FastAPI Integration**: COMPLETED ✅
   - Three REST endpoints: `GET /api/v1/tools`, `POST /api/v1/execute`, `GET /api/v1/status`
   - Self-describing API alongside FastMCP protocol
   - Complete tool metadata exposure for external integration

**Architecture Benefits Achieved:**
- ✅ Circular imports completely resolved
- ✅ 100% test pass rate for architectural validation  
- ✅ Clean plugin architecture supporting automatic discovery
- ✅ Enterprise-grade dependency injection pattern
- ✅ Self-describing server capabilities

### ✅ Epic 2 - DCIM Coverage (COMPLETED)

**Comprehensive DCIM tools implemented** with enterprise safety mechanisms:

**Infrastructure Tools (4 tools):**
- `netbox_create_site`: Complete site provisioning with region support
- `netbox_get_site_info`: Site information retrieval with utilization stats
- `netbox_create_rack`: Rack provisioning with site integration 
- `netbox_get_rack_elevation`: Rack inventory with device positioning

**Device Catalog Tools (3 tools):**
- `netbox_create_manufacturer`: Vendor management
- `netbox_create_device_type`: Device model definitions with specifications
- `netbox_create_device_role`: Role-based device categorization

**Device Lifecycle Tools (2 tools):**
- `netbox_create_device`: Device provisioning with foreign key resolution
- `netbox_get_device_info`: Device information with connection details

**Key Features:**
- ✅ Foreign key resolution (slug/name to ID conversion)
- ✅ Enterprise safety mechanisms (confirm=True, dry-run mode)
- ✅ Comprehensive error handling with detailed logging
- ✅ 100% integration test coverage with live NetBox 4.2.9

### ✅ Epic 3 - Production Hardening (COMPLETED)

**Issue #30-31 IMPLEMENTED** with enterprise-grade features:

1. **Centralized Configuration & Secrets Management** (`secrets.py`): COMPLETED ✅
   - SecretsManager supporting Docker secrets (/run/secrets/*)
   - Kubernetes secrets (/var/secrets/*) with priority-based loading
   - Environment variable integration with NETBOX_* prefix
   - Secret masking for safe logging and audit compliance

2. **Structured Logging System** (`logging_config.py`): COMPLETED ✅
   - StructuredFormatter with JSON output for ELK Stack compatibility
   - NetBoxOperationLogger with specialized NetBox operation context
   - Correlation ID management for distributed request tracing
   - Operation timing context managers for performance monitoring
   - 12 comprehensive metadata fields for enterprise log aggregation

**Production Features:**
- ✅ Docker secrets and Kubernetes secrets support
- ✅ Structured JSON logging for enterprise log management
- ✅ Correlation IDs for request tracing
- ✅ Performance timing and operation context
- ✅ Configuration validation with secrets integration

### 🎉 NEW: High-Level Enterprise Tools (v0.9.0 Development)

**Issue #25 COMPLETED** - First high-level enterprise tool implemented:

#### ✅ `netbox_provision_new_device` - Complete Device Provisioning

**Revolutionary high-level function** that reduces 5-6 API calls into one logical operation:

**Function Signature:**
```python
def netbox_provision_new_device(
    client: NetBoxClient,
    device_name: str,
    site_name: str, 
    rack_name: str,
    device_model: str,
    role_name: str,
    position: int,
    status: str = "active",
    face: str = "front", 
    tenant: Optional[str] = None,
    platform: Optional[str] = None,
    serial: Optional[str] = None,
    asset_tag: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]
```

**8-Step Internal Workflow:**
1. **Site Lookup**: Find site by name/slug with validation
2. **Rack Lookup**: Find rack within site with validation  
3. **Device Type Resolution**: Resolve device model to device_type ID
4. **Role Resolution**: Resolve role name to device_role ID
5. **Position Validation**: Check rack height, position availability, device overlap
6. **Foreign Key Resolution**: Optional tenant/platform lookup
7. **Payload Assembly**: Complete device data with all resolved IDs
8. **Device Creation**: Atomic device creation with full audit trail

**Enterprise Features:**
- ✅ **Comprehensive Validation**: Position conflicts, rack height, device overlap
- ✅ **Foreign Key Resolution**: Automatic slug/name to ID conversion
- ✅ **Dry-Run Support**: Safe validation without actual creation  
- ✅ **Enterprise Safety**: Position conflict detection, overlap validation
- ✅ **Detailed Logging**: Complete audit trail with correlation IDs
- ✅ **Error Handling**: Specific error types (ValidationError, ConflictError, NotFoundError)

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 instance
- ✅ **Test Infrastructure**: Complete test data setup with `setup_test_data.py`
- ✅ **Comprehensive Testing**: Dry-run validation, device creation, conflict detection
- ✅ **Web UI Verification**: Device successfully created (ID: 11) and visible in NetBox UI
- ✅ **Test Data Preservation**: Setup scripts and dependencies maintained for future testing

**Test Results:**
```
✅ Dry run validation: PASSED - All lookups and validations working
✅ Device creation: PASSED - Device successfully created (ID: 11)  
✅ Conflict detection: PASSED - Detects occupied rack positions correctly
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/dcim/devices/11/
```

**Value Proposition:**
This is the ultimate high-level function for data center provisioning workflows. It transforms complex multi-step device provisioning into a single, safe, validated operation perfect for LLM automation.

### ✅ Issue #26 COMPLETED - Cross-Domain IP Assignment

**Revolutionary IPAM/DCIM integration** that bridges network configuration and infrastructure management:

#### ✅ `netbox_assign_ip_to_interface` - Cross-Domain IPAM/DCIM Integration

**Function Signature:**
```python
def netbox_assign_ip_to_interface(
    client: NetBoxClient,
    device_name: str,
    interface_name: str,
    ip_address: str,  # e.g., "10.100.0.1/24"
    status: str = "active",
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]
```

**Cross-Domain Workflow:**
1. **Device Resolution**: Find device by name with validation
2. **Interface Resolution**: Find interface within device context
3. **IP Validation**: Validate IP format using Python ipaddress module
4. **Conflict Detection**: Check for existing IP assignments and conflicts
5. **Two-Step Assignment**: Create IP address, then assign to interface (NetBox 4.2.9 pattern)
6. **Assignment Verification**: Confirm successful IP-to-interface binding

**Key Technical Innovation:**
- **Two-Step API Pattern**: Discovered NetBox 4.2.9 requires IP creation first, then update with assignment
- **Content Type Resolution**: Uses `"dcim.interface"` string format for `assigned_object_type`
- **Smart Conflict Detection**: Filters assigned IPs client-side when API filtering fails
- **IP Format Validation**: Robust IP address and CIDR validation with Python ipaddress module

**Enterprise Features:**
- ✅ **Cross-Domain Integration**: Seamlessly bridges IPAM and DCIM domains
- ✅ **IP Conflict Detection**: Prevents duplicate IP assignments
- ✅ **Interface Validation**: Ensures interface exists before assignment
- ✅ **Format Validation**: Validates IP address format and CIDR notation
- ✅ **Dry-Run Support**: Safe validation without actual assignment
- ✅ **Comprehensive Error Handling**: ValidationError, ConflictError, NotFoundError

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 instance
- ✅ **Complete Test Suite**: Dry-run validation, IP assignment, conflict detection, format validation
- ✅ **Web UI Verification**: IP successfully assigned (ID: 11) and visible in NetBox UI
- ✅ **Two-Step Verification**: Confirmed both IP creation and interface assignment work correctly

**Test Results:**
```
✅ Dry run validation: PASSED - All lookups and validations working
✅ IP assignment: PASSED - IP 10.100.184.1/24 successfully assigned to interface Vlan100
✅ Conflict detection: PASSED - Detects existing IP assignments correctly
✅ Format validation: PASSED - Rejects invalid IP formats appropriately
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/ipam/ip-addresses/11/
```

### ✅ Issue #27 COMPLETED - Rack Inventory Reporting

**Comprehensive rack reporting tool** that transforms raw NetBox data into human-readable inventory reports:

#### ✅ `netbox_get_rack_inventory` - Human-Readable Rack Inventory Reports

**Function Signature:**
```python
def netbox_get_rack_inventory(
    client: NetBoxClient,
    site_name: str,
    rack_name: str,
    include_detailed: bool = False
) -> Dict[str, Any]
```

**Rack Analysis Workflow:**
1. **Site & Rack Resolution**: Find rack within specified site with validation
2. **Device Collection**: Retrieve all devices assigned to the rack
3. **Data Transformation**: Process device information with foreign key resolution
4. **Position Mapping**: Generate complete rack elevation map (occupied vs available)
5. **Utilization Analysis**: Calculate capacity statistics and device distribution
6. **Report Generation**: Create human-readable summary with detailed device information

**Key Features:**
- ✅ **Complete Rack Visualization**: Position map showing occupied and available rack units
- ✅ **Utilization Statistics**: Capacity percentages, device counts, availability metrics
- ✅ **Device Details**: Model, manufacturer, role, status, IP addresses, serial numbers
- ✅ **Foreign Key Resolution**: Automatic lookup of device types, roles, manufacturers
- ✅ **Flexible Detail Levels**: Basic summary or comprehensive detailed reporting
- ✅ **Status Analysis**: Device status overview and distribution statistics

**Report Structure:**
- **Rack Information**: Site, rack specs, dimensions, status
- **Utilization Metrics**: Total/occupied/available positions, utilization percentage
- **Device Inventory**: Sorted by position with complete device details
- **Position Map**: Visual rack elevation (top-to-bottom view)
- **Summary**: Human-readable capacity and status overview

**Enterprise Features:**
- ✅ **Robust Data Handling**: Handles both object and ID references from NetBox API
- ✅ **Error Handling**: Graceful handling of missing data and lookup failures
- ✅ **Performance Optimized**: Efficient API calls with intelligent caching
- ✅ **Export Capability**: JSON report export for external processing

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 with real rack data
- ✅ **Complete Test Coverage**: Basic inventory, detailed reporting, error handling
- ✅ **Real Data Verification**: Successfully processed test rack with device inventory
- ✅ **Export Validation**: JSON report generation and file export confirmed

**Test Results:**
```
✅ Basic inventory: PASSED - Generated clean rack overview
✅ Detailed inventory: PASSED - Complete device details with interface counts
✅ Error handling: PASSED - Proper validation for non-existent racks
✅ Utilization analysis: 1/42U occupied (2.4%) with accurate position mapping
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/api/dcim/racks/18/
```

**Sample Output:**
```
📍 Rack Information: MCP Test Site > MCP Test Rack (42U, 19")
📊 Utilization: 1/42U occupied (2.4%), 1 device installed
🖥️ Device at Position 10U: test-sw-20250622-183126
   Model: MCP Test Vendor MCP Test Switch
   Role: MCP Test Switch, Status: planned
```

### 🎯 Current Status: v0.9.0 Development

**Milestone Progress**: 3/13 high-level tools completed (23% complete)

**Remaining High-Level Tools (Issues #28-37):**

**DCIM Tools (2 remaining):**
- #28: `netbox_decommission_device` - Safe device decommissioning workflow
- #29: `netbox_create_cable_connection` - Physical connection documentation

**IPAM Tools (4 tools):**
- #30: `netbox_find_next_available_ip` - Atomic IP reservation
- #31: `netbox_get_prefix_utilization` - Capacity planning reports
- #32: `netbox_provision_vlan_with_prefix` - Coordinated VLAN/prefix creation
- #33: `netbox_find_duplicate_ips` - Network auditing and conflict detection

**Tenancy Tools (4 tools):**
- #34: `netbox_onboard_new_tenant` - Formalized tenant onboarding
- #35: `netbox_assign_resources_to_tenant` - Flexible resource ownership
- #36: `netbox_get_tenant_resource_report` - Comprehensive tenant reporting  
- #37: `netbox_create_tenant_group` - Hierarchical tenant organization

**Target**: v0.9.0 will transform NetBox MCP from a basic API wrapper into a true enterprise automation platform with 13 sophisticated high-level tools.

## Important Resources

- **GitHub Repository**: https://github.com/Deployment-Team/netbox-mcp
- **Issues & Roadmap**: Use GitHub Issues for feature requests and v0.9.0 milestone tracking
- **Milestones**: Development organized by version milestones
- **Docker Hub**: Container images published for production deployment

## Development Workflow

1. **Before implementing new features**: Check the roadmap GitHub Issues and Milestones
2. **API changes**: Always follow NetBox API best practices and foreign key resolution patterns
3. **Testing**: Test against real NetBox instances with preserved test infrastructure  
4. **Documentation**: Update relevant documentation when adding features
5. **Community**: Engage with the community through GitHub Issues for feedback

## Current Architecture Status

**✅ PRODUCTION READY**: The NetBox MCP server has achieved enterprise-grade status with:

- **Self-Describing Architecture**: Complete tool registry and dependency injection
- **Production Hardening**: Secrets management, structured logging, health endpoints
- **High-Level Automation**: First enterprise tool (`netbox_provision_new_device`) implemented and tested
- **Enterprise Safety**: Comprehensive validation, error handling, and audit trails
- **Container Ready**: Docker optimization with graceful degradation and health checks

The foundation is established for rapid development of the remaining 12 high-level tools in v0.9.0, transforming NetBox MCP into the ultimate enterprise automation platform for network infrastructure management.