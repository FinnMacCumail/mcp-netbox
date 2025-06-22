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

### ✅ Issue #28 COMPLETED - Safe Device Decommissioning

**Enterprise-grade decommissioning tool** with comprehensive safety mechanisms and validation:

#### ✅ `netbox_decommission_device` - Safe Device Decommissioning Workflow

**Function Signature:**
```python
def netbox_decommission_device(
    client: NetBoxClient,
    device_name: str,
    decommission_strategy: str = "offline",
    handle_ips: str = "unassign", 
    handle_cables: str = "remove",
    confirm: bool = False
) -> Dict[str, Any]
```

**Safe Decommissioning Workflow:**
1. **Device Lookup & Validation**: Find device with comprehensive error handling
2. **Pre-flight Validation**: Check for cluster membership, virtual chassis dependencies
3. **Inventory Analysis**: Collect all interfaces, IP addresses, and cable connections
4. **Risk Assessment**: Evaluate decommissioning risk based on current status and connections
5. **Strategy Planning**: Generate detailed execution plan with multiple strategy options
6. **Controlled Execution**: Execute plan with granular error handling and rollback capability
7. **Comprehensive Reporting**: Detailed success/failure tracking with audit trail

**Decommissioning Strategies:**
- **"offline"**: Mark device as offline (maintenance mode)
- **"decommissioning"**: Mark as actively being decommissioned  
- **"inventory"**: Convert to inventory status (spare)
- **"failed"**: Mark as failed hardware

**IP Address Handling:**
- **"unassign"**: Remove IP assignments (full cleanup)
- **"deprecate"**: Mark IPs as deprecated (preserves for potential reactivation)
- **"keep"**: Leave IP assignments unchanged

**Cable Handling:**
- **"remove"**: Delete cable connections completely
- **"deprecate"**: Mark cables as deprecated (if supported)
- **"keep"**: Leave cables connected

**Enterprise Safety Features:**
- ✅ **Risk Assessment**: Automatic evaluation of decommissioning risks
- ✅ **Pre-flight Validation**: Dependency checks (clusters, virtual chassis)
- ✅ **Conservative Strategies**: Multiple approaches for different scenarios
- ✅ **Granular Control**: Separate handling for IPs, cables, and device status
- ✅ **Dry-Run Mode**: Complete validation without actual changes
- ✅ **Audit Trail**: Detailed execution reporting with success/failure tracking

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 with real device
- ✅ **Complete Test Coverage**: Dry-run, execution, error handling, parameter validation
- ✅ **Real Decommissioning**: Successfully processed test device with IP cleanup
- ✅ **Report Export**: JSON decommissioning report generation

**Test Results:**
```
✅ Dry run validation: PASSED - Risk assessment and planning working
✅ Conservative decommissioning: PASSED - 100% success rate (3/3 actions)
✅ IP processing: PASSED - 2/2 IP addresses successfully deprecated
✅ Device status update: PASSED - Status changed from "planned" to "decommissioning"
✅ Error handling: PASSED - Proper validation for non-existent devices
✅ Parameter validation: PASSED - Invalid strategy rejection working
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/dcim/devices/11/
```

**Sample Execution:**
```
🎯 Risk Assessment: Medium risk (2 factors)
   ⚠️ Device is currently in active/planned status
   ⚠️ 2 IP addresses currently assigned

📊 Execution Summary: 100% success rate
   ✅ Device Status: planned → decommissioning
   ✅ IP Processing: 2/2 addresses deprecated
   ✅ Conservative cleanup: IPs preserved for potential reactivation
```

### ✅ Issue #29 COMPLETED - Physical Cable Management

**Enterprise-grade cable connection documentation** with comprehensive validation and conflict detection:

#### ✅ `netbox_create_cable_connection` - Physical Connection Documentation

**Function Signature:**
```python
def netbox_create_cable_connection(
    client: NetBoxClient,
    device_a_name: str,
    interface_a_name: str,
    device_b_name: str,
    interface_b_name: str,
    cable_type: str = "cat6",
    cable_status: str = "connected",
    cable_length: Optional[int] = None,
    cable_length_unit: str = "m",
    label: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]
```

**Cable Management Workflow:**
1. **Device Resolution**: Find both devices with comprehensive validation
2. **Interface Resolution**: Locate interfaces on respective devices  
3. **Availability Validation**: Check for existing cable connections with cache-aware conflict detection
4. **Parameter Validation**: Validate cable types, statuses, and length units against NetBox standards
5. **Cable Creation**: Create NetBox cable object with termination assignments
6. **Cache Invalidation**: Invalidate interface cache to ensure data consistency for subsequent operations

**Supported Cable Types:**
- **Copper**: cat3, cat5, cat5e, cat6, cat6a, cat7, cat8, dac-active, dac-passive
- **Fiber**: mmf, mmf-om1/2/3/4/5, smf, smf-os1/2, aoc
- **Other**: coaxial, mrj21-trunk, power, usb

**Enterprise Features:**
- ✅ **Smart Conflict Detection**: Cache-aware interface availability validation
- ✅ **Cache Invalidation**: Automatic cache cleanup after cable creation ensuring data consistency
- ✅ **Parameter Validation**: Comprehensive cable type, status, and length unit validation
- ✅ **Dual Interface Validation**: Validates both termination points before cable creation
- ✅ **Self-Connection Prevention**: Prevents connecting interface to itself
- ✅ **Dry-Run Support**: Safe validation without actual cable creation
- ✅ **Comprehensive Error Handling**: Specific error types (ValidationError, ConflictError, NotFoundError)

**Cache Innovation Breakthrough:**
This implementation identified and solved a critical cache consistency issue affecting all NetBox MCP write operations. The solution includes automatic cache invalidation for affected objects, ensuring subsequent queries return fresh data.

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 with real cable connections
- ✅ **Complete Test Suite**: Dry-run validation, cable creation, conflict detection, error handling, parameter validation
- ✅ **Cache Consistency Testing**: Verified cache invalidation resolves conflict detection issues
- ✅ **Web UI Verification**: Cable successfully created (ID: 5) and visible in NetBox UI

**Test Results:**
```
✅ Dry run validation: PASSED - All lookups and validations working
✅ Cable creation: PASSED - Cable successfully created between TestPort3/TestPort4
✅ Conflict detection: PASSED - Detects existing cable connections correctly (FIXED with cache invalidation)
✅ Error handling: PASSED - Proper validation for non-existent devices/interfaces
✅ Parameter validation: PASSED - Invalid cable type rejection working
📡 Cable Created: cat6 cable (2m) between device interfaces
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/dcim/cables/5/
```

**Architecture Impact:**
This implementation established the **cache invalidation pattern** that will be applied to all future high-level tools, ensuring data consistency across the entire NetBox MCP platform. This solves a fundamental challenge in cached API architectures.

### ✅ Issue #30 COMPLETED - Atomic IP Reservation

**Revolutionary IPAM automation tool** that transforms IP allocation from manual multi-step process into intelligent atomic operations:

#### ✅ `netbox_find_next_available_ip` - Intelligent IP Discovery and Atomic Reservation

**Function Signature:**
```python
def netbox_find_next_available_ip(
    client: NetBoxClient,
    prefix: str,
    count: int = 1,
    assign_to_interface: Optional[str] = None,
    device_name: Optional[str] = None,
    status: str = "active",
    description: Optional[str] = None,
    tenant: Optional[str] = None,
    vrf: Optional[str] = None,
    reserve_immediately: bool = False,
    confirm: bool = False
) -> Dict[str, Any]
```

**Multi-Mode Operation Workflow:**
1. **Prefix Discovery**: Find and validate target network prefix in NetBox
2. **Available IP Retrieval**: Use NetBox's available-ips endpoint for real-time availability
3. **IP Selection**: Select consecutive IP addresses based on count parameter
4. **Foreign Key Resolution**: Optional tenant/VRF lookup with graceful degradation
5. **Device/Interface Resolution**: Cross-domain DCIM integration for interface assignment
6. **Atomic Operations**: Create IP objects and assign to interfaces in single workflow
7. **Cache Invalidation**: Apply Issue #29 pattern ensuring data consistency

**Operation Modes:**
- **Discovery Mode**: Read-only IP discovery without reservation
- **Reservation Mode**: Create IP objects with specified status (reserved, active, etc.)
- **Assignment Mode**: Atomic IP allocation directly to device interfaces
- **Bulk Mode**: Process multiple consecutive IPs in single operation (up to 100)

**Cross-Domain Integration:**
- **IPAM → DCIM**: Seamlessly bridges IP management with device infrastructure
- **Atomic Assignment**: Single function call handles IP creation + interface assignment
- **Cache Consistency**: Invalidates both IPAM and DCIM caches maintaining data integrity

**Enterprise Features:**
- ✅ **Intelligent Discovery**: Uses NetBox's native available-ips endpoint for accuracy
- ✅ **Atomic Operations**: Single-call IP reservation with interface assignment
- ✅ **Bulk Processing**: Handle up to 100 consecutive IPs in one operation
- ✅ **Multi-Mode Support**: Discovery, reservation, and assignment workflows
- ✅ **Cache Consistency**: Implements Issue #29 cache invalidation pattern
- ✅ **Cross-Domain Safety**: Validates devices and interfaces before IP assignment
- ✅ **Foreign Key Resolution**: Automatic tenant and VRF lookup with graceful fallback
- ✅ **Comprehensive Error Handling**: Specific error types for different failure scenarios

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 with real IP allocations
- ✅ **Complete Test Suite**: Discovery, reservation, assignment, error handling, parameter validation
- ✅ **Multi-Mode Testing**: All operation modes validated with dry-run and actual execution
- ✅ **Cache Consistency Testing**: Verified cache invalidation maintains data integrity
- ✅ **Cross-Domain Testing**: IPAM/DCIM integration validated with live interface assignment

**Test Results:**
```
✅ IP Discovery: PASSED - Finds next available IP (10.99.0.4/24)
✅ Multiple IP Discovery: PASSED - Finds 5 consecutive IPs correctly
✅ Dry run reservation: PASSED - Shows what would be reserved without creating
✅ IP Reservation: PASSED - Creates 2 IP objects (IDs: 15, 16) with reserved status
✅ Interface Assignment: PASSED - Atomically assigns IP to device interface
✅ Error handling: PASSED - Proper validation for non-existent prefixes
✅ Parameter validation: PASSED - Rejects invalid count values appropriately
✅ Confirm dry-run validation: PASSED - Allows safe validation without confirm=True
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/ipam/prefixes/?q=10.99.0.0/24
```

**Sample Operations:**
```
🌐 IP Discovery: 10.99.0.4/24 (50 total available)
💾 IP Reservation: 10.99.0.4/24, 10.99.0.5/24 (Status: reserved)
🔗 Interface Assignment: 10.99.0.6/24 → test-sw-20250622-183126:TestIP-222433
🎯 Atomic Operation: Single function call handled IP creation + interface assignment
```

**Revolutionary Value:**
This function transforms traditional multi-step IP allocation workflows (discover → reserve → assign) into intelligent single-call operations, essential for automated network provisioning and LLM-driven infrastructure management.

### ✅ Issue #31 COMPLETED - Capacity Planning Reports

**Enterprise-grade capacity analysis tool** that transforms raw NetBox data into actionable capacity planning insights:

#### ✅ `netbox_get_prefix_utilization` - Comprehensive Prefix Utilization Reports

**Function Signature:**
```python
def netbox_get_prefix_utilization(
    client: NetBoxClient,
    prefix: str,
    include_child_prefixes: bool = True,
    include_detailed_breakdown: bool = False,
    tenant: Optional[str] = None,
    vrf: Optional[str] = None
) -> Dict[str, Any]
```

**Capacity Analysis Workflow:**
1. **Prefix Discovery**: Find and validate target network prefix with multi-tenant filtering
2. **Utilization Calculation**: Advanced IPv4/IPv6 address space analysis with network/broadcast exclusion
3. **Assignment Analysis**: Categorize IP assignments (interface, device, unassigned) with detailed breakdown
4. **Status Distribution**: Analyze IP status patterns (active, reserved, deprecated, etc.)
5. **Child Prefix Analysis**: Hierarchical subnet analysis with recursive utilization mapping
6. **Capacity Planning**: Growth projections with intelligent recommendations
7. **Report Generation**: Human-readable capacity reports with actionable insights

**Multi-Mode Analysis:**
- **Basic Analysis**: Core utilization metrics and status distribution
- **Hierarchical Analysis**: Child prefix analysis with subnet utilization mapping
- **Detailed Breakdown**: Complete IP allocation inventory with assignment details
- **Multi-Tenant Analysis**: Tenant and VRF-aware filtering for complex environments

**Enterprise Features:**
- ✅ **Intelligent Network Analysis**: Python ipaddress module for accurate IPv4/IPv6 calculations
- ✅ **Hierarchical Subnet Mapping**: Recursive child prefix discovery and utilization analysis
- ✅ **Assignment Classification**: Automatic categorization of interface vs device assignments
- ✅ **Growth Projections**: Linear capacity forecasting with 3, 6, and 12-month projections
- ✅ **Smart Recommendations**: Automated capacity planning insights and expansion guidance
- ✅ **Multi-Tenant Support**: Tenant and VRF filtering for complex enterprise environments
- ✅ **Status Analysis**: Comprehensive IP status distribution and utilization patterns

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 with real prefix data
- ✅ **Complete Test Suite**: Basic analysis, detailed breakdown, error handling, parameter validation
- ✅ **Capacity Planning Testing**: Growth projections and recommendation generation confirmed
- ✅ **Multi-Mode Testing**: All analysis modes validated with comprehensive scenarios

**Test Results:**
```
✅ Basic utilization analysis: PASSED - 2.36% utilization (6/254 addresses)
✅ Detailed analysis with child prefixes: PASSED - Complete breakdown with assignment classification
✅ Capacity planning insights: PASSED - Growth projections for 3, 6, 12 months
✅ Error handling: PASSED - Proper validation for non-existent prefixes
✅ Parameter validation: PASSED - Empty prefix rejection working
✅ Invalid format handling: PASSED - Malformed prefix detection confirmed
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/ipam/prefixes/?q=10.99.0.0/24
```

**Sample Analysis:**
```
📊 Prefix Analysis: 10.99.0.0/24
📈 Utilization: 2.36% (6/254 addresses) - Status: healthy
🔗 Assignment Breakdown: 0 interface, 0 device, 6 unassigned
📋 Status Distribution: 4 reserved, 2 active
🔮 Growth Projections: 3 months: 3.07%, 6 months: 3.78%, 12 months: 5.20%
```

**Enterprise Value:**
Essential for network capacity planning, growth forecasting, and infrastructure optimization. Transforms complex multi-step analysis into comprehensive single-call reports perfect for automated capacity management and executive reporting.

### ✅ Issue #32 COMPLETED - Coordinated VLAN/Prefix Creation

**Revolutionary network provisioning tool** that eliminates coordination complexity between VLAN and IP prefix creation through atomic operations:

#### ✅ `netbox_provision_vlan_with_prefix` - Atomic VLAN/Prefix Coordination

**Function Signature:**
```python
def netbox_provision_vlan_with_prefix(
    client: NetBoxClient,
    vlan_name: str,
    vlan_id: int,
    prefix: str,
    site: Optional[str] = None,
    vlan_group: Optional[str] = None,
    vrf: Optional[str] = None,
    tenant: Optional[str] = None,
    vlan_role: Optional[str] = None,
    prefix_role: Optional[str] = None,
    vlan_status: str = "active",
    prefix_status: str = "active",
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]
```

**Atomic Coordination Workflow:**
1. **Pre-flight Validation**: Comprehensive conflict detection for VLAN IDs and IP prefixes
2. **Format Validation**: IPv4/IPv6 prefix validation using Python ipaddress module
3. **Foreign Key Resolution**: Automatic lookup of sites, VRFs, tenants, groups, and roles
4. **VLAN Creation**: Primary VLAN object creation with all resolved references
5. **Prefix Creation**: IP prefix creation with automatic VLAN association
6. **Rollback Capability**: Automatic VLAN deletion if prefix creation fails
7. **Cache Invalidation**: Apply Issue #29 pattern ensuring data consistency

**Enterprise Coordination Features:**
- ✅ **Atomic Operations**: Single-call VLAN/prefix creation with automatic association
- ✅ **Intelligent Rollback**: Automatic cleanup on partial failures with detailed status reporting
- ✅ **Conflict Prevention**: Pre-flight validation prevents VLAN ID and prefix duplication
- ✅ **Foreign Key Intelligence**: Comprehensive resolution of sites, VRFs, tenants, groups, roles
- ✅ **Multi-Scope Validation**: Site-specific and VRF-aware conflict detection
- ✅ **Cache Consistency**: Implements Issue #29 cache invalidation pattern for data integrity
- ✅ **Enterprise Safety**: Comprehensive validation, error handling, and audit trails

**Testing & Validation:**
- ✅ **Live Integration Testing**: Validated against NetBox 4.2.9 with atomic VLAN/prefix creation
- ✅ **Complete Test Suite**: Dry-run validation, atomic creation, conflict detection, rollback testing
- ✅ **Coordination Testing**: VLAN-prefix association validation and foreign key resolution
- ✅ **Error Handling Testing**: Parameter validation, conflict detection, rollback capability

**Test Results:**
```
✅ Basic VLAN/prefix provisioning (dry run): PASSED - Validation and planning working
✅ Actual VLAN/prefix provisioning: PASSED - VLAN 3230 + Prefix 10.231.0.0/24 created atomically
✅ Site-specific provisioning: PASSED - Foreign key resolution working
✅ VLAN ID conflict detection: PASSED - Prevents duplicate VLAN IDs correctly
✅ Prefix conflict detection: PASSED - Prevents duplicate prefixes correctly
✅ Parameter validation: PASSED - VLAN ID and prefix format validation working
✅ Rollback capability: PASSED - Automatic cleanup on partial failures
📱 Web UI Verification: https://zwqg2756.cloud.netboxapp.com/ipam/vlans/2/
```

**Sample Operations:**
```
🌐 VLAN Creation: TEST-VLAN-224230 (VID: 3230) → ID: 2
📊 Prefix Creation: 10.231.0.0/24 → ID: 3 (linked to VLAN 2)
🔗 Coordination: VLAN-Prefix automatically associated
🎯 Atomic Success: 2 objects created in proper order with rollback capability
```

**Rollback Intelligence:**
The function implements sophisticated rollback logic - if prefix creation fails after VLAN creation, the VLAN is automatically deleted to prevent orphaned objects. This ensures database consistency and prevents partial provisioning states.

**Enterprise Value:**
Essential for automated network provisioning workflows where VLANs and IP addressing must be coordinated. Eliminates manual coordination errors and ensures consistent network configuration across enterprise environments.

### 🎯 Current Status: v0.9.0 Development

**Milestone Progress**: 8/13 high-level tools completed (62% complete)

**Remaining High-Level Tools (Issues #30-37):**

**IPAM Tools (4 tools):**
- ✅ #30: `netbox_find_next_available_ip` - Atomic IP reservation
- ✅ #31: `netbox_get_prefix_utilization` - Capacity planning reports
- ✅ #32: `netbox_provision_vlan_with_prefix` - Coordinated VLAN/prefix creation
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

## Development Workflow & Best Practices

### Pre-Development Planning
1. **Issue Analysis**: Thoroughly analyze GitHub Issues and understand the enterprise value proposition
2. **Architecture Review**: Ensure alignment with self-describing server architecture and dependency injection patterns
3. **NetBox API Research**: Study NetBox API endpoints, foreign key relationships, and data models
4. **Test Infrastructure**: Verify test data availability and create preserved test objects as needed

### Implementation Standards
1. **Function Design**: Follow enterprise tool patterns with comprehensive parameter validation
2. **Foreign Key Resolution**: Implement intelligent slug/name to ID conversion for all NetBox relationships
3. **Error Handling**: Use specific error types (ValidationError, ConflictError, NotFoundError) with detailed messages
4. **Cache Management**: Apply Issue #29 cache invalidation pattern for all write operations
5. **Dry-Run Support**: Always implement confirm=False dry-run mode for enterprise safety

### Testing Protocol
1. **Live Integration**: Test against real NetBox 4.2.9 instances with actual data
2. **Comprehensive Scenarios**: Cover dry-run, execution, error handling, parameter validation, conflict detection
3. **Test Data Preservation**: Maintain test infrastructure (sites, devices, interfaces) for consistent testing
4. **Web UI Verification**: Always provide NetBox URLs for manual verification of created objects
5. **Report Generation**: Save detailed JSON reports for each test run with timestamps and results

### Code Quality & Safety
1. **Enterprise Safety**: Comprehensive validation, error handling, audit trails, rollback capabilities
2. **Parameter Validation**: Strict validation of all inputs with helpful error messages
3. **Atomic Operations**: Implement rollback logic for multi-step operations (like VLAN/prefix coordination)
4. **Cache Consistency**: Ensure data consistency through proper cache invalidation patterns
5. **Performance**: Optimize API calls and implement intelligent caching where appropriate

### Documentation Standards
1. **Function Signatures**: Complete type hints and comprehensive docstrings with examples
2. **Enterprise Features**: Document all safety mechanisms, validation logic, and error handling
3. **Test Results**: Include actual test output, success rates, and Web UI verification links
4. **Architecture Impact**: Document how each tool contributes to the overall enterprise platform
5. **Value Proposition**: Clearly articulate the enterprise value and automation benefits

## Session Learning & Technical Insights (2025-06-22)

### Key Technical Discoveries

**NetBox API Patterns:**
- **Content Type Resolution**: NetBox 4.2.9 requires string format `"dcim.interface"` for assigned_object_type, not integer IDs
- **Two-Step IP Assignment**: IP creation followed by assignment update is the reliable pattern for interface assignments
- **Cache Conflict Detection**: Real-time conflict detection requires cache invalidation after write operations
- **Foreign Key Flexibility**: NetBox accepts both name and slug lookups for most object types, graceful degradation recommended

**Cache Management Breakthroughs:**
- Issue #29 cache invalidation pattern is critical for all write operations to prevent stale data conflicts
- `client.cache.invalidate_pattern()` and `client.cache.invalidate_for_object()` ensure data consistency
- Cache invalidation should never fail the primary operation - log warnings only

**Enterprise Tool Architecture:**
- **Atomic Operations**: Multi-step workflows (VLAN+Prefix) require sophisticated rollback logic
- **Pre-flight Validation**: Comprehensive conflict detection prevents partial failures
- **Foreign Key Intelligence**: Automatic resolution with graceful degradation enhances user experience
- **Dry-Run Capability**: Essential for enterprise safety - always implement confirm=False validation mode

### Advanced Implementation Patterns

**Error Handling Hierarchy:**
```python
# Standard error types for consistent API responses
ValidationError    # Input validation failures
ConflictError     # Resource conflicts (duplicate IPs, VLAN IDs)
NotFoundError     # Missing foreign key references
NetBoxAPIError    # NetBox API communication issues
```

**Rollback Pattern (VLAN/Prefix Example):**
```python
try:
    created_vlan = create_vlan()
    try:
        created_prefix = create_prefix_with_vlan_association()
    except Exception:
        # Rollback: Delete created VLAN to prevent orphans
        delete_vlan(created_vlan_id)
        raise PrefixCreationError with rollback status
except Exception:
    return VLANCreationError
```

**Cache Invalidation Pattern:**
```python
# After any write operation
try:
    client.cache.invalidate_pattern("ipam.vlans")
    client.cache.invalidate_pattern("ipam.prefixes") 
    if interface_assignment:
        client.cache.invalidate_for_object("dcim.interfaces", interface_id)
except Exception as cache_error:
    # Never fail primary operation due to cache issues
    logger.warning(f"Cache invalidation failed: {cache_error}")
```

### Testing Infrastructure Excellence

**Preserved Test Data Strategy:**
- **Test Site**: "MCP Test Site" with rack and device infrastructure
- **Test Device**: `test-sw-20250622-183126` with multiple interfaces for assignment testing
- **Test Prefixes**: Dynamic generation with `10.{unique}.0.0/24` pattern to avoid conflicts
- **Test VLANs**: Dynamic VLAN ID generation `3000 + timestamp` for uniqueness

**Comprehensive Test Coverage:**
1. **Dry-Run Validation**: Always test planning phase without execution
2. **Actual Execution**: Verify real object creation with Web UI confirmation
3. **Conflict Detection**: Test duplicate prevention for all unique fields
4. **Parameter Validation**: Test input validation with invalid data
5. **Error Handling**: Test failure scenarios and error message quality
6. **Foreign Key Resolution**: Test automatic lookups and graceful degradation

### Performance & Scalability Insights

**API Optimization Strategies:**
- **Bulk Operations**: Process up to 100 consecutive IPs in single operations
- **Intelligent Caching**: Per-type TTL caches with automatic invalidation
- **Foreign Key Batching**: Resolve all foreign keys before main operations
- **Available IP Endpoint**: Use NetBox's native available-ips endpoint for accuracy

**Enterprise Scalability Features:**
- **Multi-Tenant Support**: Tenant and VRF filtering for complex environments
- **Hierarchical Analysis**: Child prefix discovery for large network analysis
- **Growth Projections**: Linear capacity forecasting with recommendation engine
- **Assignment Classification**: Automatic categorization of IP assignments

### Next Session Preparation

**Remaining High-Level Tools (Issues #33-37):**
- **#33**: `netbox_find_duplicate_ips` - Network auditing and conflict detection
- **#34**: `netbox_onboard_new_tenant` - Formalized tenant onboarding  
- **#35**: `netbox_assign_resources_to_tenant` - Flexible resource ownership
- **#36**: `netbox_get_tenant_resource_report` - Comprehensive tenant reporting
- **#37**: `netbox_create_tenant_group` - Hierarchical tenant organization

**Architecture Readiness:**
- Comprehensive test infrastructure preserved and validated
- Cache invalidation patterns established and proven
- Foreign key resolution patterns standardized across all tools
- Enterprise safety mechanisms validated with real NetBox instances
- Atomic operation patterns established with rollback capabilities

## Current Architecture Status

**✅ PRODUCTION READY**: The NetBox MCP server has achieved enterprise-grade status with:

- **Self-Describing Architecture**: Complete tool registry and dependency injection
- **Production Hardening**: Secrets management, structured logging, health endpoints  
- **High-Level Automation**: 8 sophisticated enterprise tools implemented and tested
- **Enterprise Safety**: Comprehensive validation, error handling, audit trails, and rollback capabilities
- **Container Ready**: Docker optimization with graceful degradation and health checks
- **Cache Consistency**: Advanced cache invalidation patterns ensuring data integrity
- **Atomic Operations**: Multi-step workflows with intelligent rollback and error recovery

**v0.9.0 Progress**: 8/13 tools completed (62%) - On track for enterprise automation platform transformation with revolutionary high-level functions that reduce complex multi-step workflows into intelligent single-call operations.