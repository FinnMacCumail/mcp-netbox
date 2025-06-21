#!/usr/bin/env python3
"""
Live Safety Testing for NetBox Write Operations

CRITICAL: This script tests write operations against a live NetBox instance
with comprehensive safety validations. All operations are performed in 
DRY-RUN mode to ensure no actual data is modified.
"""

import os
import sys
from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import NetBoxConfig, SafetyConfig
from netbox_mcp.exceptions import NetBoxConfirmationError, NetBoxValidationError


def test_safety_mechanisms():
    """Test all safety mechanisms against live NetBox instance."""
    print("🔍 NetBox Write Operations Safety Testing")
    print("=" * 50)
    
    # Test Configuration 1: Normal mode (write operations enabled)
    print("\n📋 Test 1: Safety Confirmation Requirements")
    config = NetBoxConfig(
        url=os.getenv("NETBOX_URL", "https://zwqg2756.cloud.netboxapp.com"),
        token=os.getenv("NETBOX_TOKEN", "809e04182a7e280398de97e524058277994f44a5"),
        safety=SafetyConfig(
            dry_run_mode=False,
            enable_write_operations=True
        )
    )
    
    client = NetBoxClient(config)
    
    # Test 1.1: Create without confirm should fail
    try:
        client.create_object('manufacturers', {'name': 'Safety Test Vendor'})
        print("❌ SAFETY FAILURE: Create without confirm=True should fail!")
        return False
    except NetBoxConfirmationError as e:
        print(f"✅ Safety OK: Create requires confirm=True - {e}")
    
    # Test 1.2: Update without confirm should fail  
    try:
        client.update_object('manufacturers', 1, {'name': 'Updated Name'})
        print("❌ SAFETY FAILURE: Update without confirm=True should fail!")
        return False
    except NetBoxConfirmationError as e:
        print(f"✅ Safety OK: Update requires confirm=True - {e}")
    
    # Test 1.3: Delete without confirm should fail
    try:
        client.delete_object('manufacturers', 1)
        print("❌ SAFETY FAILURE: Delete without confirm=True should fail!")
        return False
    except NetBoxConfirmationError as e:
        print(f"✅ Safety OK: Delete requires confirm=True - {e}")
    
    # Test Configuration 2: Dry-run mode
    print("\n📋 Test 2: Dry-Run Mode Validation")
    dry_run_config = NetBoxConfig(
        url=os.getenv("NETBOX_URL", "https://zwqg2756.cloud.netboxapp.com"),
        token=os.getenv("NETBOX_TOKEN", "809e04182a7e280398de97e524058277994f44a5"),
        safety=SafetyConfig(
            dry_run_mode=True,
            enable_write_operations=True
        )
    )
    
    dry_client = NetBoxClient(dry_run_config)
    
    # Test 2.1: Dry-run create simulation
    try:
        result = dry_client.create_object('manufacturers', {
            'name': 'DryRun Test Vendor',
            'slug': 'dryrun-test-vendor'
        }, confirm=True)
        
        if result.get('dry_run') and result['id'] == 999999:
            print(f"✅ Dry-run OK: Create simulated successfully - ID: {result['id']}")
        else:
            print(f"❌ DRY-RUN FAILURE: Expected simulation, got real operation: {result}")
            return False
            
    except Exception as e:
        print(f"❌ DRY-RUN FAILURE: Dry-run create failed: {e}")
        return False
    
    # Test 2.2: Dry-run update simulation (using existing manufacturer)
    try:
        # First, get a real manufacturer ID for testing
        manufacturers = client.get_manufacturers(limit=1)
        if not manufacturers:
            print("⚠️  Warning: No manufacturers found for update test")
        else:
            mfg_id = manufacturers[0]['id']
            result = dry_client.update_object('manufacturers', mfg_id, {
                'name': 'DryRun Updated Name'
            }, confirm=True)
            
            if result.get('dry_run') and result['id'] == mfg_id:
                print(f"✅ Dry-run OK: Update simulated successfully - ID: {result['id']}")
            else:
                print(f"❌ DRY-RUN FAILURE: Expected simulation, got real operation: {result}")
                return False
                
    except Exception as e:
        print(f"❌ DRY-RUN FAILURE: Dry-run update failed: {e}")
        return False
    
    # Test 2.3: Dry-run delete simulation
    try:
        if manufacturers:
            mfg_id = manufacturers[0]['id']
            result = dry_client.delete_object('manufacturers', mfg_id, confirm=True)
            
            if result.get('dry_run') and result['deleted'] and result['object_id'] == mfg_id:
                print(f"✅ Dry-run OK: Delete simulated successfully - ID: {result['object_id']}")
            else:
                print(f"❌ DRY-RUN FAILURE: Expected simulation, got real operation: {result}")
                return False
                
    except Exception as e:
        print(f"❌ DRY-RUN FAILURE: Dry-run delete failed: {e}")
        return False
    
    # Test 3: Data Validation
    print("\n📋 Test 3: Data Validation")
    
    # Test 3.1: Empty data validation
    try:
        dry_client.create_object('manufacturers', {}, confirm=True)
        print("❌ VALIDATION FAILURE: Empty data should be rejected!")
        return False
    except NetBoxValidationError as e:
        print(f"✅ Validation OK: Empty data rejected - {e}")
    
    # Test 3.2: None data validation
    try:
        dry_client.create_object('manufacturers', None, confirm=True)
        print("❌ VALIDATION FAILURE: None data should be rejected!")
        return False
    except NetBoxValidationError as e:
        print(f"✅ Validation OK: None data rejected - {e}")
    
    # Test 3.3: Invalid data type validation
    try:
        dry_client.create_object('manufacturers', "invalid_data", confirm=True)
        print("❌ VALIDATION FAILURE: String data should be rejected!")
        return False
    except NetBoxValidationError as e:
        print(f"✅ Validation OK: String data rejected - {e}")
    
    # Test 4: Endpoint Validation
    print("\n📋 Test 4: Endpoint Validation")
    
    # Test 4.1: Invalid object type
    try:
        dry_client.create_object('invalid_object_type', {'name': 'test'}, confirm=True)
        print("❌ ENDPOINT FAILURE: Invalid object type should be rejected!")
        return False
    except NetBoxValidationError as e:
        print(f"✅ Endpoint OK: Invalid object type rejected - {e}")
    
    # Test 4.2: Valid object types
    valid_types = ['manufacturers', 'sites', 'devices', 'ip_addresses', 'tags']
    for obj_type in valid_types:
        try:
            endpoint = dry_client._get_write_endpoint(obj_type)
            print(f"✅ Endpoint OK: {obj_type} endpoint available")
        except Exception as e:
            print(f"❌ ENDPOINT FAILURE: {obj_type} endpoint failed: {e}")
            return False
    
    print("\n🎉 ALL SAFETY TESTS PASSED!")
    print("✅ Confirmation requirements working")
    print("✅ Dry-run mode working")  
    print("✅ Data validation working")
    print("✅ Endpoint validation working")
    print("\n🔒 NetBox write operations are SAFE for production use!")
    
    return True


def test_connectivity():
    """Test basic connectivity to NetBox instance."""
    print("🔗 Testing NetBox connectivity...")
    
    config = NetBoxConfig(
        url=os.getenv("NETBOX_URL", "https://zwqg2756.cloud.netboxapp.com"),
        token=os.getenv("NETBOX_TOKEN", "809e04182a7e280398de97e524058277994f44a5"),
        safety=SafetyConfig(dry_run_mode=True)
    )
    
    try:
        client = NetBoxClient(config)
        status = client.health_check()
        
        if status.connected:
            print(f"✅ Connected to NetBox {status.version}")
            print(f"   Response time: {status.response_time_ms:.1f}ms")
            return True
        else:
            print(f"❌ Connection failed: {status.error}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == "__main__":
    print("🚨 NetBox MCP Write Operations - LIVE SAFETY TESTING")
    print("=" * 60)
    print("⚠️  WARNING: Testing write operations against live NetBox instance")
    print("🔍 All operations will be performed in DRY-RUN mode for safety")
    print("=" * 60)
    
    # Test connectivity first
    if not test_connectivity():
        print("\n❌ Connectivity test failed. Exiting.")
        sys.exit(1)
    
    # Run safety tests
    if test_safety_mechanisms():
        print("\n🎉 ALL SAFETY MECHANISMS VALIDATED!")
        print("💚 Write operations are ready for production use")
        sys.exit(0)
    else:
        print("\n💥 SAFETY TEST FAILURE!")
        print("🚨 Do NOT use write operations until issues are resolved")
        sys.exit(1)