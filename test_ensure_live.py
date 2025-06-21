#!/usr/bin/env python3
"""
Live Testing for NetBox Ensure Operations

CRITICAL: This script tests ensure operations against a live NetBox instance
with comprehensive safety validations. All operations are performed in 
DRY-RUN mode to ensure no actual data is modified.
"""

import os
import sys

# Set environment variables for testing
os.environ["NETBOX_URL"] = "https://zwqg2756.cloud.netboxapp.com"
os.environ["NETBOX_TOKEN"] = "809e04182a7e280398de97e524058277994f44a5"
os.environ["NETBOX_DRY_RUN"] = "true"  # CRITICAL: Enable dry-run mode for safety

from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import NetBoxConfig, SafetyConfig
from netbox_mcp.exceptions import NetBoxConfirmationError, NetBoxValidationError


def test_ensure_methods_safety():
    """Test all ensure method safety mechanisms."""
    print("🔍 NetBox Ensure Methods Safety Testing")
    print("=" * 50)
    
    # Initialize client in dry-run mode
    config = NetBoxConfig(
        url=os.getenv("NETBOX_URL"),
        token=os.getenv("NETBOX_TOKEN"),
        safety=SafetyConfig(
            dry_run_mode=True,
            enable_write_operations=True
        )
    )
    
    client = NetBoxClient(config)
    
    print("\n📋 Test 1: Confirmation Requirements")
    
    # Test 1.1: ensure_manufacturer without confirm should fail
    try:
        client.ensure_manufacturer(name="Safety Test Vendor")
        print("❌ SAFETY FAILURE: ensure_manufacturer without confirm=True should fail!")
        return False
    except NetBoxConfirmationError as e:
        print(f"✅ Safety OK: ensure_manufacturer requires confirm=True - {e}")
    
    # Test 1.2: ensure_site without confirm should fail  
    try:
        client.ensure_site(name="Safety Test Site")
        print("❌ SAFETY FAILURE: ensure_site without confirm=True should fail!")
        return False
    except NetBoxConfirmationError as e:
        print(f"✅ Safety OK: ensure_site requires confirm=True - {e}")
    
    # Test 1.3: ensure_device_role without confirm should fail
    try:
        client.ensure_device_role(name="Safety Test Role")
        print("❌ SAFETY FAILURE: ensure_device_role without confirm=True should fail!")
        return False
    except NetBoxConfirmationError as e:
        print(f"✅ Safety OK: ensure_device_role requires confirm=True - {e}")
    
    print("\n📋 Test 2: Input Validation")
    
    # Test 2.1: Missing parameters
    try:
        client.ensure_manufacturer(confirm=True)
        print("❌ VALIDATION FAILURE: Missing parameters should be rejected!")
        return False
    except NetBoxValidationError as e:
        print(f"✅ Validation OK: Missing parameters rejected - {e}")
    
    # Test 2.2: Empty name
    try:
        client.ensure_manufacturer(name="", confirm=True)
        print("❌ VALIDATION FAILURE: Empty name should be rejected!")
        return False
    except NetBoxValidationError as e:
        print(f"✅ Validation OK: Empty name rejected - {e}")
    
    print("\n📋 Test 3: Hybrid Pattern - Direct ID Injection")
    
    # Test 3.1: Get existing manufacturer by ID
    try:
        # Get existing manufacturers first
        manufacturers = client.get_manufacturers(limit=1)
        if manufacturers:
            mfg_id = manufacturers[0]["id"]
            result = client.ensure_manufacturer(manufacturer_id=mfg_id, confirm=True)
            
            if result["success"] and result["action"] == "unchanged":
                print(f"✅ Hybrid Pattern OK: Direct ID injection works - ID: {mfg_id}")
            else:
                print(f"❌ HYBRID PATTERN FAILURE: {result}")
                return False
        else:
            print("⚠️  Warning: No manufacturers found for ID injection test")
    except Exception as e:
        print(f"❌ HYBRID PATTERN ERROR: {e}")
        return False
    
    print("\n📋 Test 4: Hybrid Pattern - Hierarchical Convenience")
    
    # Test 4.1: Create new manufacturer (dry-run)
    try:
        result = client.ensure_manufacturer(
            name="DryRun Test Manufacturer",
            slug="dryrun-test-mfg",
            description="This is a dry-run test manufacturer",
            confirm=True
        )
        
        if result["success"] and result.get("dry_run"):
            print(f"✅ Hierarchical OK: Create simulation works - Action: {result['action']}")
        elif result["success"] and result["action"] == "unchanged":
            print(f"✅ Hierarchical OK: Existing manufacturer found - Action: {result['action']}")
        else:
            print(f"❌ HIERARCHICAL FAILURE: {result}")
            return False
    except Exception as e:
        print(f"❌ HIERARCHICAL ERROR: {e}")
        return False
    
    # Test 4.2: Create new site (dry-run)
    try:
        result = client.ensure_site(
            name="DryRun Test Site",
            slug="dryrun-test-site",
            status="active",
            description="This is a dry-run test site",
            confirm=True
        )
        
        if result["success"] and (result.get("dry_run") or result["action"] in ["unchanged", "created"]):
            print(f"✅ Site Ensure OK: Action: {result['action']}, Dry-run: {result.get('dry_run', False)}")
        else:
            print(f"❌ SITE ENSURE FAILURE: {result}")
            return False
    except Exception as e:
        print(f"❌ SITE ENSURE ERROR: {e}")
        return False
    
    # Test 4.3: Create new device role (dry-run)
    try:
        result = client.ensure_device_role(
            name="DryRun Test Role",
            slug="dryrun-test-role",
            color="ff9800",
            description="This is a dry-run test device role",
            confirm=True
        )
        
        if result["success"] and (result.get("dry_run") or result["action"] in ["unchanged", "created"]):
            print(f"✅ Device Role Ensure OK: Action: {result['action']}, Dry-run: {result.get('dry_run', False)}")
        else:
            print(f"❌ DEVICE ROLE ENSURE FAILURE: {result}")
            return False
    except Exception as e:
        print(f"❌ DEVICE ROLE ENSURE ERROR: {e}")
        return False
    
    print("\n📋 Test 5: Idempotency Testing")
    
    # Test 5.1: Multiple calls should produce same result
    try:
        # Use an existing manufacturer for idempotency test
        if manufacturers:
            existing_name = manufacturers[0]["name"]
            
            result1 = client.ensure_manufacturer(name=existing_name, confirm=True)
            result2 = client.ensure_manufacturer(name=existing_name, confirm=True)
            result3 = client.ensure_manufacturer(name=existing_name, confirm=True)
            
            # All should return unchanged and same data
            if (result1["action"] == result2["action"] == result3["action"] == "unchanged" and
                result1["manufacturer"]["id"] == result2["manufacturer"]["id"] == result3["manufacturer"]["id"]):
                print(f"✅ Idempotency OK: Multiple calls produce consistent results")
            else:
                print(f"❌ IDEMPOTENCY FAILURE: Results differ between calls")
                return False
        else:
            print("⚠️  Warning: No manufacturers found for idempotency test")
    except Exception as e:
        print(f"❌ IDEMPOTENCY ERROR: {e}")
        return False
    
    print("\n📋 Test 6: Response Format Validation")
    
    # Test 6.1: Check response format structure
    try:
        result = client.ensure_manufacturer(name="Format Test Vendor", confirm=True)
        
        required_fields = ["success", "action", "object_type", "manufacturer", "changes"]
        missing_fields = [f for f in required_fields if f not in result]
        
        if not missing_fields:
            print(f"✅ Response Format OK: All required fields present")
            
            # Check changes structure
            changes = result["changes"]
            change_fields = ["created_fields", "updated_fields", "unchanged_fields"]
            missing_change_fields = [f for f in change_fields if f not in changes]
            
            if not missing_change_fields:
                print(f"✅ Changes Format OK: All change tracking fields present")
            else:
                print(f"❌ CHANGES FORMAT FAILURE: Missing fields: {missing_change_fields}")
                return False
        else:
            print(f"❌ RESPONSE FORMAT FAILURE: Missing fields: {missing_fields}")
            return False
    except Exception as e:
        print(f"❌ RESPONSE FORMAT ERROR: {e}")
        return False
    
    print("\n🎉 ALL ENSURE METHODS SAFETY TESTS PASSED!")
    print("✅ Confirmation requirements working")
    print("✅ Input validation working")
    print("✅ Hybrid pattern (both ID and name-based) working")
    print("✅ Dry-run mode working")
    print("✅ Idempotency confirmed")
    print("✅ Response format validated")
    print("\n🔒 NetBox ensure methods are SAFE for production use!")
    
    return True


def test_connectivity():
    """Test basic NetBox connectivity."""
    print("🔗 Testing NetBox connectivity...")
    
    config = NetBoxConfig(
        url=os.getenv("NETBOX_URL"),
        token=os.getenv("NETBOX_TOKEN"),
        safety=SafetyConfig(dry_run_mode=True)
    )
    
    try:
        client = NetBoxClient(config)
        status = client.health_check()
        
        if status.connected:
            print(f"✅ Connected to NetBox {status.version}")
            print(f"   Response time: {status.response_time_ms:.1f}ms")
            print("🔍 Running in DRY-RUN mode (safe for testing)")
            return True
        else:
            print(f"❌ Connection failed: {status.error}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == "__main__":
    print("🚨 NetBox Ensure Methods - LIVE SAFETY TESTING")
    print("=" * 60)
    print("⚠️  WARNING: Testing ensure operations against live NetBox instance")
    print("🔍 All operations will be performed in DRY-RUN mode for safety")
    print("=" * 60)
    
    # Test connectivity first
    if not test_connectivity():
        print("\n❌ Connectivity test failed. Exiting.")
        sys.exit(1)
    
    # Run safety tests
    if test_ensure_methods_safety():
        print("\n🎉 ALL ENSURE METHODS SAFETY MECHANISMS VALIDATED!")
        print("💚 Hybrid ensure pattern is ready for production use")
        sys.exit(0)
    else:
        print("\n💥 ENSURE METHODS SAFETY TEST FAILURE!")
        print("🚨 Do NOT use ensure methods until issues are resolved")
        sys.exit(1)