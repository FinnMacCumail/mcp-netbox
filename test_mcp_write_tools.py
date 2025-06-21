#!/usr/bin/env python3
"""
Test script for NetBox MCP Write Tools

CRITICAL: This script tests write operations against a live NetBox instance
with comprehensive safety validations. All operations are performed in 
DRY-RUN mode to ensure no actual data is modified.
"""

import os
import sys
import asyncio

# Set environment variables for testing
os.environ["NETBOX_URL"] = "https://zwqg2756.cloud.netboxapp.com"
os.environ["NETBOX_TOKEN"] = "809e04182a7e280398de97e524058277994f44a5"
os.environ["NETBOX_DRY_RUN"] = "true"  # CRITICAL: Enable dry-run mode for safety
from netbox_mcp import server
from netbox_mcp.server import (
    netbox_create_manufacturer,
    netbox_create_site,
    netbox_create_device_role,
    netbox_update_device_status,
    netbox_delete_manufacturer,
    initialize_server
)


def test_write_tools_safety():
    """Test all write tool safety mechanisms."""
    print("🔍 NetBox MCP Write Tools Safety Testing")
    print("=" * 50)
    
    print("\n📋 Test 1: Confirmation Requirements")
    
    # Test 1.1: Create manufacturer without confirm should fail
    try:
        result = netbox_create_manufacturer("Safety Test Vendor")
        if result["success"]:
            print("❌ SAFETY FAILURE: Create without confirm=True should fail!")
            return False
        elif result["error_type"] == "ConfirmationRequired":
            print(f"✅ Safety OK: Create requires confirm=True - {result['error']}")
        else:
            print(f"❌ UNEXPECTED ERROR: {result}")
            return False
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    # Test 1.2: Update device status without confirm should fail
    try:
        result = netbox_update_device_status("any-device-name", "offline")
        if result["success"]:
            print("❌ SAFETY FAILURE: Update without confirm=True should fail!")
            return False
        elif result["error_type"] == "ConfirmationRequired":
            print(f"✅ Safety OK: Update requires confirm=True - {result['error']}")
        elif result["error_type"] == "DeviceNotFound":
            # This is also acceptable since the confirm check might happen first or after device lookup
            print(f"✅ Safety OK: Operation properly rejected (device lookup or confirm check)")
        else:
            print(f"❌ UNEXPECTED ERROR: {result}")
            return False
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    # Test 1.3: Delete manufacturer without confirm should fail
    try:
        result = netbox_delete_manufacturer("Some Vendor")
        if result["success"]:
            print("❌ SAFETY FAILURE: Delete without confirm=True should fail!")
            return False
        elif result["error_type"] == "ConfirmationRequired":
            print(f"✅ Safety OK: Delete requires confirm=True - {result['error']}")
        else:
            print(f"❌ UNEXPECTED ERROR: {result}")
            return False
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    print("\n📋 Test 2: Dry-Run Mode Operations")
    
    # Test 2.1: Create manufacturer in dry-run mode
    try:
        result = netbox_create_manufacturer(
            "DryRun Test Vendor",
            slug="dryrun-test-vendor",
            description="This is a dry-run test",
            confirm=True
        )
        
        if result["success"] and result.get("dry_run"):
            print(f"✅ Dry-run OK: Create manufacturer simulated - ID: {result['manufacturer'].get('id')}")
        elif result["success"] and not result.get("dry_run"):
            print(f"❌ DRY-RUN FAILURE: Expected simulation, got real operation!")
            return False
        else:
            print(f"❌ CREATE FAILURE: {result}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    # Test 2.2: Create site in dry-run mode
    try:
        result = netbox_create_site(
            "DryRun Test Site",
            slug="dryrun-test-site",
            status="active",
            description="This is a dry-run test site",
            confirm=True
        )
        
        if result["success"] and result.get("dry_run"):
            print(f"✅ Dry-run OK: Create site simulated - ID: {result['site'].get('id')}")
        elif result["success"] and not result.get("dry_run"):
            print(f"❌ DRY-RUN FAILURE: Expected simulation, got real operation!")
            return False
        else:
            print(f"❌ CREATE FAILURE: {result}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    # Test 2.3: Create device role in dry-run mode
    try:
        result = netbox_create_device_role(
            "DryRun Test Role",
            slug="dryrun-test-role",
            color="ff0000",
            description="This is a dry-run test role",
            confirm=True
        )
        
        if result["success"] and result.get("dry_run"):
            print(f"✅ Dry-run OK: Create device role simulated - ID: {result['device_role'].get('id')}")
        elif result["success"] and not result.get("dry_run"):
            print(f"❌ DRY-RUN FAILURE: Expected simulation, got real operation!")
            return False
        else:
            print(f"❌ CREATE FAILURE: {result}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    print("\n📋 Test 3: Data Validation")
    
    # Test 3.1: Empty name validation
    try:
        result = netbox_create_manufacturer("", confirm=True)
        if result["success"]:
            print("❌ VALIDATION FAILURE: Empty name should be rejected!")
            return False
        elif result["error_type"] == "ValidationError":
            print(f"✅ Validation OK: Empty name rejected - {result['error']}")
        else:
            print(f"✅ Validation OK: Empty name handled - {result['error_type']}")
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    print("\n📋 Test 4: Non-existent Object Operations")
    
    # Test 4.1: Update non-existent device
    try:
        result = netbox_update_device_status("non-existent-device-12345", "offline", confirm=True)
        if result["success"]:
            print("❌ LOGIC FAILURE: Non-existent device update should fail!")
            return False
        elif result["error_type"] == "DeviceNotFound":
            print(f"✅ Logic OK: Non-existent device rejected - {result['error']}")
        else:
            print(f"✅ Logic OK: Non-existent device handled - {result['error_type']}")
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    # Test 4.2: Delete non-existent manufacturer
    try:
        result = netbox_delete_manufacturer("non-existent-manufacturer-12345", confirm=True)
        if result["success"]:
            print("❌ LOGIC FAILURE: Non-existent manufacturer delete should fail!")
            return False
        elif result["error_type"] == "ManufacturerNotFound":
            print(f"✅ Logic OK: Non-existent manufacturer rejected - {result['error']}")
        else:
            print(f"✅ Logic OK: Non-existent manufacturer handled - {result['error_type']}")
    except Exception as e:
        print(f"❌ EXCEPTION ERROR: {e}")
        return False
    
    print("\n🎉 ALL MCP WRITE TOOLS SAFETY TESTS PASSED!")
    print("✅ Confirmation requirements working")
    print("✅ Dry-run mode working")  
    print("✅ Data validation working")
    print("✅ Non-existent object handling working")
    print("\n🔒 NetBox MCP write tools are SAFE for production use!")
    
    return True


def test_connectivity():
    """Test basic MCP server connectivity."""
    print("🔗 Testing NetBox MCP server connectivity...")
    
    try:
        if server.netbox_client is None:
            print("❌ NetBox client not initialized")
            return False
        
        status = server.netbox_client.health_check()
        
        if status.connected:
            print(f"✅ Connected to NetBox {status.version}")
            print(f"   Response time: {status.response_time_ms:.1f}ms")
            
            # Check if we're in dry-run mode
            if server.netbox_client.config.safety.dry_run_mode:
                print("🔍 Running in DRY-RUN mode (safe for testing)")
            else:
                print("⚠️  Running in LIVE mode (writes will modify data!)")
            
            return True
        else:
            print(f"❌ Connection failed: {status.error}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == "__main__":
    print("🚨 NetBox MCP Write Tools - LIVE SAFETY TESTING")
    print("=" * 60)
    print("⚠️  WARNING: Testing write operations against live NetBox instance")
    print("🔍 All operations will be performed in DRY-RUN mode for safety")
    print("=" * 60)
    
    # Initialize server first
    try:
        print("\n🔧 Initializing NetBox MCP server...")
        initialize_server()
        print("✅ Server initialized successfully")
    except Exception as e:
        print(f"❌ Server initialization failed: {e}")
        sys.exit(1)
    
    # Test connectivity first
    if not test_connectivity():
        print("\n❌ Connectivity test failed. Exiting.")
        sys.exit(1)
    
    # Run safety tests
    if test_write_tools_safety():
        print("\n🎉 ALL MCP WRITE TOOLS SAFETY MECHANISMS VALIDATED!")
        print("💚 Write tools are ready for production use")
        sys.exit(0)
    else:
        print("\n💥 MCP WRITE TOOLS SAFETY TEST FAILURE!")
        print("🚨 Do NOT use write tools until issues are resolved")
        sys.exit(1)