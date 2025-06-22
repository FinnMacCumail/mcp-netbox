#!/usr/bin/env python3
"""
Debug Content Types for IP Assignment

This script investigates NetBox content types to understand the correct
format for IP address assignment to interfaces.
"""

import sys
import os
import logging
from datetime import datetime

# Add the package directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_content_types():
    """Debug NetBox content types for IP assignment."""
    
    try:
        # Load configuration and connect
        config = load_config()
        client = NetBoxClient(config)
        
        status = client.health_check()
        if not status.connected:
            logger.error(f"Failed to connect to NetBox: {status.error}")
            return False
            
        logger.info(f"✅ Connected to NetBox {status.version}")
        
        # 1. List all content types
        print("\n🔍 Investigating Content Types...")
        print("="*60)
        
        # Find interface content type
        interface_cts = client.extras.content_types.filter(
            app_label="dcim", 
            model="interface"
        )
        print(f"Interface content types: {len(interface_cts)}")
        for ct in interface_cts:
            print(f"  - ID: {ct['id']}, App: {ct['app_label']}, Model: {ct['model']}")
        
        # 2. Check existing IP addresses to see how they're assigned
        print("\n🔍 Investigating Existing IP Assignments...")
        print("="*60)
        
        # Get all IP addresses that are assigned to interfaces
        existing_ips = client.ipam.ip_addresses.filter(
            assigned_object_type_id__isnull=False
        )
        
        print(f"Found {len(existing_ips)} assigned IP addresses")
        for ip in existing_ips[:3]:  # Show first 3 examples
            print(f"  IP: {ip['address']}")
            print(f"    assigned_object_type: {ip.get('assigned_object_type')}")
            print(f"    assigned_object_type_id: {ip.get('assigned_object_type_id')}")
            print(f"    assigned_object_id: {ip.get('assigned_object_id')}")
            print(f"    assigned_object: {ip.get('assigned_object')}")
            print("    ---")
        
        # 3. Try to get a specific interface and examine its structure
        print("\n🔍 Investigating Test Interface Structure...")
        print("="*60)
        
        test_devices = client.dcim.devices.filter(name__icontains="test-sw-")
        if test_devices:
            device = test_devices[0]
            print(f"Using test device: {device['name']} (ID: {device['id']})")
            
            interfaces = client.dcim.interfaces.filter(device_id=device["id"], name="Vlan100")
            if interfaces:
                interface = interfaces[0]
                print(f"Found interface: {interface['name']} (ID: {interface['id']})")
                print(f"Interface object_type: {interface.get('object_type')}")
                print(f"Interface url: {interface.get('url')}")
                
                # Try to see what content type NetBox expects
                # Check the schema for IP address creation
                print("\n🔍 Testing IP Address Creation Methods...")
                print("="*60)
                
                # Method 1: Try with content type ID
                if interface_cts:
                    ct_id = interface_cts[0]['id']
                    print(f"Trying with content type ID: {ct_id}")
                    
                    ip_data_1 = {
                        "address": "10.200.1.1/24", 
                        "status": "active",
                        "assigned_object_type": ct_id,
                        "assigned_object_id": interface['id']
                    }
                    print(f"Method 1 payload: {ip_data_1}")
                    
                    try:
                        # Try dry run first
                        result1 = client.ipam.ip_addresses.create(confirm=False, **ip_data_1)
                        print(f"✅ Method 1 (content type ID) DRY RUN: SUCCESS")
                        print(f"   Result: {result1}")
                    except Exception as e:
                        print(f"❌ Method 1 (content type ID) DRY RUN: FAILED - {e}")
                
                # Method 2: Try with string content type
                print(f"\nTrying with string content type...")
                ip_data_2 = {
                    "address": "10.200.2.1/24",
                    "status": "active", 
                    "assigned_object_type": "dcim.interface",
                    "assigned_object_id": interface['id']
                }
                print(f"Method 2 payload: {ip_data_2}")
                
                try:
                    result2 = client.ipam.ip_addresses.create(confirm=False, **ip_data_2)
                    print(f"✅ Method 2 (string content type) DRY RUN: SUCCESS")
                    print(f"   Result: {result2}")
                except Exception as e:
                    print(f"❌ Method 2 (string content type) DRY RUN: FAILED - {e}")
                
                # Method 3: Try with assigned_object field  
                print(f"\nTrying with assigned_object field...")
                ip_data_3 = {
                    "address": "10.200.3.1/24",
                    "status": "active",
                    "assigned_object": interface['id']
                }
                print(f"Method 3 payload: {ip_data_3}")
                
                try:
                    result3 = client.ipam.ip_addresses.create(confirm=False, **ip_data_3)
                    print(f"✅ Method 3 (assigned_object) DRY RUN: SUCCESS")
                    print(f"   Result: {result3}")
                except Exception as e:
                    print(f"❌ Method 3 (assigned_object) DRY RUN: FAILED - {e}")
                
                # Method 4: Look at NetBox API schema
                print(f"\n🔍 Checking NetBox API Schema...")
                try:
                    # Get the OpenAPI schema for IP addresses
                    schema_response = client.nb.http_session.get(f"{client.nb.base_url}/api/schema/")
                    if schema_response.status_code == 200:
                        print("✅ Got API schema successfully")
                        # This would be too verbose, but shows we can access it
                    else:
                        print(f"❌ Failed to get API schema: {schema_response.status_code}")
                except Exception as e:
                    print(f"❌ Schema check failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Debug failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_content_types()
    sys.exit(0 if success else 1)