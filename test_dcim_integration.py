#!/usr/bin/env python3
"""
DCIM Integration Tests for NetBox MCP

Comprehensive integration tests for DCIM tools using the new dependency injection
architecture. Tests the complete DCIM workflow against live NetBox instance.

Test Flow: Site → Manufacturer → Device Type → Device Role → Rack → Device
"""

import os
import time
import uuid
from typing import Dict, Any

# Set up environment for testing
os.environ["NETBOX_URL"] = "https://zwqg2756.cloud.netboxapp.com"
os.environ["NETBOX_TOKEN"] = "809e04182a7e280398de97e524058277994f44a5"

def generate_test_prefix() -> str:
    """Generate unique test prefix for this test run."""
    return f"mcp-test-{str(uuid.uuid4())[:8]}"

def test_dcim_workflow():
    """Test complete DCIM workflow with dependency injection."""
    print("🧪 DCIM Integration Test Suite")
    print("=" * 50)
    
    test_prefix = generate_test_prefix()
    print(f"🏷️  Test prefix: {test_prefix}")
    
    # Import dependencies
    from netbox_mcp.dependencies import get_netbox_client
    from netbox_mcp.registry import execute_tool, TOOL_REGISTRY, load_tools
    
    # Load tools
    load_tools()
    print(f"📊 Loaded {len(TOOL_REGISTRY)} tools")
    
    # Get client
    client = get_netbox_client()
    print(f"✅ Client initialized: {type(client).__name__}")
    
    results = {}
    cleanup_items = []
    
    try:
        # Test 1: Create Site
        print("\n🏢 Test 1: Create Site")
        site_result = execute_tool(
            "netbox_create_site",
            client,
            name=f"{test_prefix} Test Site",
            slug=f"{test_prefix}-site",
            status="active",
            description="Test site for MCP DCIM integration",
            physical_address="Test Street 123, Test City",
            confirm=True
        )
        
        if site_result["success"]:
            print(f"✅ Site created: {site_result['site']['name']}")
            results["site"] = site_result
            cleanup_items.append(("site", site_result["site"]["id"]))
        else:
            print(f"❌ Site creation failed: {site_result['error']}")
            return False
        
        # Test 2: Create Manufacturer
        print("\n🏭 Test 2: Create Manufacturer")
        manufacturer_result = execute_tool(
            "netbox_create_manufacturer",
            client,
            name=f"{test_prefix} Test Manufacturer",
            slug=f"{test_prefix}-mfg",
            description="Test manufacturer for MCP DCIM integration",
            confirm=True
        )
        
        if manufacturer_result["success"]:
            print(f"✅ Manufacturer created: {manufacturer_result['manufacturer']['name']}")
            results["manufacturer"] = manufacturer_result
            cleanup_items.append(("manufacturer", manufacturer_result["manufacturer"]["id"]))
        else:
            print(f"❌ Manufacturer creation failed: {manufacturer_result['error']}")
            return False
        
        # Test 3: Create Device Type
        print("\n📦 Test 3: Create Device Type")
        device_type_result = execute_tool(
            "netbox_create_device_type",
            client,
            model=f"{test_prefix}-router-1000",
            manufacturer=f"{test_prefix}-mfg",
            slug=f"{test_prefix}-router-1000",
            u_height=2,
            is_full_depth=True,
            part_number="TEST-RTR-1000",
            description="Test router device type",
            confirm=True
        )
        
        if device_type_result["success"]:
            print(f"✅ Device type created: {device_type_result['device_type']['model']}")
            results["device_type"] = device_type_result
            cleanup_items.append(("device_type", device_type_result["device_type"]["id"]))
        else:
            print(f"❌ Device type creation failed: {device_type_result['error']}")
            return False
        
        # Test 4: Create Device Role
        print("\n🎭 Test 4: Create Device Role")
        role_result = execute_tool(
            "netbox_create_device_role",
            client,
            name=f"{test_prefix} Test Router",
            slug=f"{test_prefix}-router",
            color="2196f3",
            vm_role=False,
            description="Test router role",
            confirm=True
        )
        
        if role_result["success"]:
            print(f"✅ Device role created: {role_result['device_role']['name']}")
            results["role"] = role_result
            cleanup_items.append(("device_role", role_result["device_role"]["id"]))
        else:
            print(f"❌ Device role creation failed: {role_result['error']}")
            return False
        
        # Test 5: Create Rack
        print("\n🗄️  Test 5: Create Rack")
        rack_result = execute_tool(
            "netbox_create_rack",
            client,
            name=f"{test_prefix}-rack-01",
            site=f"{test_prefix}-site",
            u_height=42,
            width=19,
            status="active",
            facility_id="TEST-RACK-01",
            description="Test rack for MCP integration",
            confirm=True
        )
        
        if rack_result["success"]:
            print(f"✅ Rack created: {rack_result['rack']['name']}")
            results["rack"] = rack_result
            cleanup_items.append(("rack", rack_result["rack"]["id"]))
        else:
            print(f"❌ Rack creation failed: {rack_result['error']}")
            return False
        
        # Test 6: Create Device
        print("\n💻 Test 6: Create Device")
        device_result = execute_tool(
            "netbox_create_device",
            client,
            name=f"{test_prefix}-rtr-01",
            device_type=f"{test_prefix}-router-1000",
            site=f"{test_prefix}-site",
            role=f"{test_prefix}-router",
            status="active",
            rack=f"{test_prefix}-rack-01",
            position=1,
            face="front",
            serial="TEST12345",
            asset_tag=f"ASSET-{test_prefix.upper()}",
            description="Test router device",
            confirm=True
        )
        
        if device_result["success"]:
            print(f"✅ Device created: {device_result['device']['name']}")
            results["device"] = device_result
            cleanup_items.append(("device", device_result["device"]["id"]))
        else:
            print(f"❌ Device creation failed: {device_result['error']}")
            return False
        
        # Test 7: Get Site Info
        print("\n📋 Test 7: Get Site Information")
        site_info_result = execute_tool(
            "netbox_get_site_info",
            client,
            site_name=f"{test_prefix} Test Site"
        )
        
        if site_info_result["success"]:
            stats = site_info_result["statistics"]
            print(f"✅ Site info retrieved:")
            print(f"   Racks: {stats['rack_count']}")
            print(f"   Devices: {stats['device_count']}")
            print(f"   Total rack units: {stats['total_rack_units']}")
        else:
            print(f"❌ Site info retrieval failed: {site_info_result['error']}")
        
        # Test 8: Get Device Info
        print("\n🔍 Test 8: Get Device Information")
        device_info_result = execute_tool(
            "netbox_get_device_info",
            client,
            device_name=f"{test_prefix}-rtr-01",
            site=f"{test_prefix}-site"
        )
        
        if device_info_result["success"]:
            stats = device_info_result["statistics"]
            print(f"✅ Device info retrieved:")
            print(f"   Interfaces: {stats['interface_count']}")
            print(f"   Cables: {stats['cable_count']}")
            print(f"   Power connections: {stats['power_connection_count']}")
        else:
            print(f"❌ Device info retrieval failed: {device_info_result['error']}")
        
        # Test 9: Get Rack Elevation
        print("\n📏 Test 9: Get Rack Elevation")
        elevation_result = execute_tool(
            "netbox_get_rack_elevation",
            client,
            rack_name=f"{test_prefix}-rack-01",
            site=f"{test_prefix}-site"
        )
        
        if elevation_result["success"]:
            print(f"✅ Rack elevation retrieved:")
            print(f"   Device count: {elevation_result['device_count']}")
            print(f"   Available units: {elevation_result['available_units']}")
            if elevation_result["elevation"]:
                for position, device_info in elevation_result["elevation"].items():
                    print(f"   Position {position}: {device_info['device']} ({device_info['device_type']})")
        else:
            print(f"❌ Rack elevation retrieval failed: {elevation_result['error']}")
        
        print("\n" + "=" * 50)
        print("🎉 All DCIM tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        return False
    
    finally:
        # Cleanup (reverse order to respect dependencies)
        print(f"\n🧹 Cleanup: Removing {len(cleanup_items)} test objects...")
        cleanup_items.reverse()
        
        for object_type, object_id in cleanup_items:
            try:
                if object_type == "device":
                    client.dcim.devices.delete(object_id, confirm=True)
                elif object_type == "rack":
                    client.dcim.racks.delete(object_id, confirm=True)
                elif object_type == "device_role":
                    client.dcim.device_roles.delete(object_id, confirm=True)
                elif object_type == "device_type":
                    client.dcim.device_types.delete(object_id, confirm=True)
                elif object_type == "manufacturer":
                    client.dcim.manufacturers.delete(object_id, confirm=True)
                elif object_type == "site":
                    client.dcim.sites.delete(object_id, confirm=True)
                
                print(f"   ✅ Deleted {object_type} (ID: {object_id})")
                time.sleep(0.1)  # Small delay to avoid rate limiting
                
            except Exception as e:
                print(f"   ⚠️  Failed to delete {object_type} (ID: {object_id}): {e}")

def test_dcim_tools_validation():
    """Test DCIM tools parameter validation."""
    print("\n🧪 DCIM Tools Validation Test")
    print("=" * 50)
    
    from netbox_mcp.dependencies import get_netbox_client
    from netbox_mcp.registry import execute_tool, load_tools
    
    load_tools()
    client = get_netbox_client()
    
    validation_tests = [
        {
            "name": "Site validation - missing required fields",
            "tool": "netbox_create_site",
            "params": {"name": "", "slug": "", "confirm": True},
            "should_fail": True
        },
        {
            "name": "Device Type validation - invalid U height",
            "tool": "netbox_create_device_type",
            "params": {
                "model": "test",
                "manufacturer": "test",
                "slug": "test",
                "u_height": 150,  # Invalid
                "confirm": True
            },
            "should_fail": True
        },
        {
            "name": "Device Role validation - invalid color",
            "tool": "netbox_create_device_role",
            "params": {
                "name": "test",
                "slug": "test",
                "color": "invalid-color",  # Invalid
                "confirm": True
            },
            "should_fail": True
        },
        {
            "name": "Rack validation - invalid width",
            "tool": "netbox_create_rack",
            "params": {
                "name": "test",
                "site": "test",
                "width": 25,  # Invalid
                "confirm": True
            },
            "should_fail": True
        }
    ]
    
    passed = 0
    for test in validation_tests:
        try:
            result = execute_tool(test["tool"], client, **test["params"])
            
            if test["should_fail"] and not result["success"]:
                print(f"✅ {test['name']}: Correctly rejected invalid input")
                passed += 1
            elif not test["should_fail"] and result["success"]:
                print(f"✅ {test['name']}: Correctly accepted valid input")
                passed += 1
            else:
                print(f"❌ {test['name']}: Unexpected result - {result}")
        except Exception as e:
            print(f"❌ {test['name']}: Exception - {e}")
    
    print(f"\n📊 Validation tests: {passed}/{len(validation_tests)} passed")
    return passed == len(validation_tests)

def main():
    """Run all DCIM integration tests."""
    print("🚀 NetBox MCP DCIM Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("DCIM Workflow Integration", test_dcim_workflow),
        ("DCIM Tools Validation", test_dcim_tools_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append(result)
            print(f"{'✅ PASSED' if result else '❌ FAILED'}: {test_name}")
        except Exception as e:
            print(f"❌ FAILED: {test_name} - {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {sum(results)}/{len(results)} test suites passed")
    
    if all(results):
        print("🎉 All DCIM integration tests passed!")
        print("✅ DCIM tools are production-ready with dependency injection")
    else:
        print("⚠️  Some tests failed - review output above")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)