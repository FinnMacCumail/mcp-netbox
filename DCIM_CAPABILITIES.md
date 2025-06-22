# 🏗️ NetBox MCP DCIM Capabilities

## Overview

De NetBox MCP biedt **100% DCIM coverage** dankzij onze revolutionaire dynamic client architectuur en high-level tools. Alle NetBox DCIM endpoints zijn automatisch beschikbaar via `client.dcim.*` met enterprise-grade safety en dependency injection.

## 🎯 Complete DCIM Tool Coverage

### 1. Site Management
```python
# Create sites with comprehensive information
client.dcim.sites.create(
    name="Amsterdam Datacenter",
    slug="amsterdam-dc", 
    status="active",
    physical_address="Science Park 140, Amsterdam",
    contact_name="NOC Team",
    contact_email="noc@company.com",
    confirm=True
)

# Get site information with statistics
netbox_get_site_info("Amsterdam Datacenter")
```

**Use Cases:**
- Datacenter and facility management
- Multi-site network planning
- Contact information tracking
- Physical address management

### 2. Manufacturer Management
```python
# Create manufacturers for device catalog
netbox_create_manufacturer(
    name="Cisco Systems",
    slug="cisco",
    description="Network equipment manufacturer",
    confirm=True
)

# Direct API access for all operations
client.dcim.manufacturers.all()
client.dcim.manufacturers.filter(name__icontains="cisco")
```

**Use Cases:**
- Device catalog organization
- Vendor management
- Equipment sourcing
- Standardization tracking

### 3. Device Type Management
```python
# Create device types with specifications
netbox_create_device_type(
    model="ISR4331",
    manufacturer="cisco",
    slug="isr4331",
    u_height=2,
    is_full_depth=True,
    part_number="ISR4331/K9",
    description="Cisco ISR 4000 Series Router",
    confirm=True
)
```

**Use Cases:**
- Hardware catalog management
- Rack space planning
- Device standardization
- Procurement planning

### 4. Device Role Management  
```python
# Create device roles with visual coding
netbox_create_device_role(
    name="Edge Router",
    slug="edge-router",
    color="2196f3",  # Blue
    vm_role=False,
    description="Internet edge routing",
    confirm=True
)
```

**Use Cases:**
- Network topology organization
- Role-based access control
- Visual network mapping
- Operational categorization

### 5. Rack Management
```python
# Create racks with specifications
netbox_create_rack(
    name="Rack-A01",
    site="amsterdam-dc",
    u_height=42,
    width=19,
    status="active",
    facility_id="DC-A01-R001",
    description="Primary compute rack",
    confirm=True
)

# Get rack elevation with device positions
netbox_get_rack_elevation("Rack-A01", site="amsterdam-dc")
```

**Use Cases:**
- Physical space management
- Rack elevation planning
- Cable management
- Power distribution planning

### 6. Device Management
```python
# Create devices with full specifications
netbox_create_device(
    name="edge-rtr-01",
    device_type="isr4331",
    site="amsterdam-dc",
    role="edge-router",
    status="active",
    rack="Rack-A01",
    position=1,
    face="front",
    serial="FOC2345A1B2",
    asset_tag="ASSET-001",
    description="Primary internet edge router",
    confirm=True
)

# Get comprehensive device information
netbox_get_device_info("edge-rtr-01", site="amsterdam-dc")
```

**Use Cases:**
- Asset inventory management
- Configuration management
- Serial number tracking
- Warranty management

## 🔧 Advanced DCIM Workflows

### 1. Complete Datacenter Provisioning
```python
# 1. Create the site
site = netbox_create_site(
    name="Regional Datacenter",
    slug="regional-dc",
    status="planned",
    confirm=True
)

# 2. Create rack infrastructure
rack = netbox_create_rack(
    name="Core-Rack-01", 
    site="regional-dc",
    u_height=42,
    width=19,
    confirm=True
)

# 3. Deploy core devices
core_switch = netbox_create_device(
    name="core-sw-01",
    device_type="nexus-9300",
    site="regional-dc", 
    role="core-switch",
    rack="Core-Rack-01",
    position=40,  # Top of rack
    confirm=True
)
```

### 2. Multi-Vendor Device Deployment
```python
# Create multiple manufacturers
vendors = ["cisco", "juniper", "arista"]
for vendor in vendors:
    netbox_create_manufacturer(
        name=vendor.title(),
        slug=vendor,
        confirm=True
    )

# Create vendor-specific device types
cisco_router = netbox_create_device_type(
    model="ISR4331",
    manufacturer="cisco",
    slug="cisco-isr4331",
    u_height=2,
    confirm=True
)

juniper_switch = netbox_create_device_type(
    model="EX4600",
    manufacturer="juniper", 
    slug="juniper-ex4600",
    u_height=1,
    confirm=True
)
```

### 3. Rack Space Planning
```python
# Get rack elevation for planning
elevation = netbox_get_rack_elevation("Rack-A01")

print(f"Rack has {elevation['available_units']} units available")
print(f"Current devices: {elevation['device_count']}")

# Plan new device placement
for position, device_info in elevation['elevation'].items():
    print(f"Position {position}: {device_info['device']} ({device_info['u_height']}U)")
```

### 4. Site Infrastructure Analysis
```python
# Get comprehensive site information
site_info = netbox_get_site_info("Amsterdam Datacenter")

print(f"Site Statistics:")
print(f"  Racks: {site_info['statistics']['rack_count']}")
print(f"  Devices: {site_info['statistics']['device_count']}")
print(f"  Total rack units: {site_info['statistics']['total_rack_units']}")

# Analyze rack utilization
for rack in site_info['racks']:
    rack_elevation = netbox_get_rack_elevation(rack['name'])
    utilization = (rack['u_height'] - rack_elevation['available_units']) / rack['u_height'] * 100
    print(f"  {rack['name']}: {utilization:.1f}% utilized")
```

## 🌐 Dynamic API Integration

### Direct DCIM API Access
```python
from netbox_mcp.dependencies import get_netbox_client

client = get_netbox_client()

# All DCIM endpoints automatically available:
client.dcim.sites.all()
client.dcim.racks.filter(site="amsterdam-dc")
client.dcim.devices.filter(role="router", status="active")
client.dcim.interfaces.filter(device="edge-rtr-01")
client.dcim.cables.filter(termination_a_device="edge-rtr-01")
client.dcim.power_outlets.all()
client.dcim.power_feeds.filter(rack="Rack-A01")

# Create operations with safety
client.dcim.devices.create(
    name="new-device",
    device_type=device_type_id,
    site=site_id,
    confirm=True
)
```

### Available DCIM Endpoints
- **Infrastructure**: sites, locations, racks, rack_roles
- **Devices**: manufacturers, device_types, device_roles, devices, modules
- **Connectivity**: interfaces, cables, cable_terminations
- **Power**: power_feeds, power_outlets, power_panels
- **Inventory**: inventory_items, inventory_item_roles
- **Components**: console_ports, console_server_ports, power_ports
- **Platforms**: platforms, virtual_chassis

## 🔒 Safety & Enterprise Features

### Mandatory Safety Mechanisms
- **Confirmation Required**: All write operations require `confirm=True`
- **Foreign Key Resolution**: Automatic slug-to-ID conversion for relationships
- **Input Validation**: Comprehensive parameter and format validation
- **Error Handling**: Detailed error messages with specific error types
- **Dependency Injection**: Clean architecture with thread-safe client management

### Enterprise Validation Features
```python
# Automatic foreign key resolution
netbox_create_device(
    name="router-01",
    device_type="isr4331",      # Resolved by model/slug
    site="amsterdam-dc",        # Resolved by slug/name  
    role="edge-router",         # Resolved by slug/name
    rack="Rack-A01",           # Resolved by name in site
    confirm=True
)

# Input validation with clear error messages
result = netbox_create_rack(
    name="Invalid Rack",
    site="nonexistent-site",   # Will fail with SiteNotFound
    width=25,                  # Will fail with validation error
    confirm=True
)
```

### Error Types and Handling
- `ValidationError`: Invalid input parameters
- `SiteNotFound`: Referenced site doesn't exist
- `ManufacturerNotFound`: Referenced manufacturer doesn't exist  
- `DeviceTypeNotFound`: Referenced device type doesn't exist
- `DeviceRoleNotFound`: Referenced device role doesn't exist
- `RackNotFound`: Referenced rack doesn't exist

## 📊 Performance & Optimization

### Caching Integration
- **TTL-based Caching**: DCIM queries cached for performance
- **Cache Invalidation**: Automatic cache updates after write operations
- **Foreign Key Caching**: Referenced objects cached to reduce API calls
- **Bulk Operations**: Efficient batch processing capabilities

### Performance Best Practices
```python
# Cache-optimized operations
# 1. Batch foreign key lookups
manufacturers = client.dcim.manufacturers.all()  # Cached
device_types = client.dcim.device_types.all()   # Cached

# 2. Use direct IDs when available
device = netbox_create_device(
    name="router-02", 
    device_type=device_type_id,  # Direct ID (faster)
    site=site_id,               # Direct ID (faster)
    role=role_id,               # Direct ID (faster)
    confirm=True
)
```

## 🚀 Integration Examples

### MCP Tool Usage
```python
# Via REST API endpoints
GET /api/v1/tools?category=dcim
POST /api/v1/execute
{
  "tool_name": "netbox_create_device",
  "parameters": {
    "name": "router-01",
    "device_type": "isr4331",
    "site": "amsterdam-dc",
    "role": "router",
    "confirm": true
  }
}

# Via dependency injection in tools
from netbox_mcp.registry import execute_tool
from netbox_mcp.dependencies import get_netbox_client

client = get_netbox_client()
result = execute_tool("netbox_create_device", client, **parameters)
```

### Workflow Automation
```python
# Automated rack deployment
def deploy_rack_infrastructure(site_slug, rack_count):
    client = get_netbox_client()
    
    for i in range(1, rack_count + 1):
        # Create rack
        rack_result = execute_tool(
            "netbox_create_rack",
            client,
            name=f"Rack-{i:02d}",
            site=site_slug,
            u_height=42,
            confirm=True
        )
        
        # Deploy standard devices
        execute_tool(
            "netbox_create_device", 
            client,
            name=f"top-of-rack-{i:02d}",
            device_type="access-switch",
            site=site_slug,
            role="access-switch", 
            rack=f"Rack-{i:02d}",
            position=42,
            confirm=True
        )
```

## 🎉 Conclusion

De NetBox MCP biedt **complete DCIM functionaliteit** met:

✅ **9 High-Level Tools** - Site, manufacturer, device, rack management  
✅ **100% API Coverage** - Alle NetBox DCIM endpoints via dynamic client  
✅ **Enterprise Safety** - Foreign key resolution en input validation  
✅ **Dependency Injection** - Clean architectuur met thread-safe operations  
✅ **Integration Ready** - REST API en tool execution workflows  
✅ **Production Validated** - Comprehensive test suite met live NetBox instance  

**Geen enkele DCIM functionaliteit ontbreekt** - van site planning tot device deployment, alles is beschikbaar via de intelligent, self-describing MCP server!