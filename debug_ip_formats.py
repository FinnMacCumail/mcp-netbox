#!/usr/bin/env python3
"""
Debug IP Assignment Formats

This script investigates how existing IP addresses are assigned to interfaces
to understand the correct format.
"""

import sys
import os
import logging

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

def debug_ip_formats():
    """Debug how IP addresses are assigned to interfaces."""
    
    try:
        # Load configuration and connect
        config = load_config()
        client = NetBoxClient(config)
        
        status = client.health_check()
        if not status.connected:
            logger.error(f"Failed to connect to NetBox: {status.error}")
            return False
            
        logger.info(f"✅ Connected to NetBox {status.version}")
        
        print("\n🔍 Investigating IP Address Assignment Formats...")
        print("="*80)
        
        # Get all IP addresses to see how they're structured
        all_ips = client.ipam.ip_addresses.all()
        print(f"Total IP addresses in NetBox: {len(all_ips)}")
        
        # Look for assigned IPs
        assigned_ips = [ip for ip in all_ips if ip.get('assigned_object_id')]
        print(f"Assigned IP addresses: {len(assigned_ips)}")
        
        if assigned_ips:
            print("\n📝 Example assigned IP structures:")
            for i, ip in enumerate(assigned_ips[:3]):  # Show first 3
                print(f"\nExample {i+1}:")
                print(f"  Address: {ip['address']}")
                print(f"  ID: {ip['id']}")
                print(f"  assigned_object_type: {ip.get('assigned_object_type')}")
                print(f"  assigned_object_id: {ip.get('assigned_object_id')}")
                print(f"  assigned_object: {ip.get('assigned_object')}")
                
                # If it has assigned_object, get more details
                if ip.get('assigned_object'):
                    assigned_obj = ip['assigned_object']
                    print(f"  assigned_object details:")
                    print(f"    url: {assigned_obj.get('url', 'N/A')}")
                    print(f"    name: {assigned_obj.get('name', 'N/A')}")
                    print(f"    display: {assigned_obj.get('display', 'N/A')}")
        
        # Try creating an IP with the interface format that works
        print("\n🧪 Testing IP Creation...")
        print("="*80)
        
        # Get our test interface
        test_devices = client.dcim.devices.filter(name__icontains="test-sw-")
        if test_devices:
            device = test_devices[0]
            interfaces = client.dcim.interfaces.filter(device_id=device["id"], name="Vlan100")
            if interfaces:
                interface = interfaces[0]
                print(f"Using interface: {interface['name']} (ID: {interface['id']})")
                print(f"Interface URL: {interface.get('url')}")
                
                # Method: Use the interface URL directly as assigned_object
                test_ip = "10.200.99.1/24"
                ip_data = {
                    "address": test_ip,
                    "status": "active",
                    "assigned_object": interface['id']  # Just the ID, not an object
                }
                
                print(f"\nTesting IP creation with payload: {ip_data}")
                
                try:
                    result = client.ipam.ip_addresses.create(confirm=False, **ip_data)
                    print(f"✅ SUCCESS: {result}")
                except Exception as e:
                    print(f"❌ FAILED: {e}")
                    
                    # Try alternative: use assigned_object_id only
                    print(f"\nTrying alternative approach...")
                    ip_data_alt = {
                        "address": test_ip,
                        "status": "active", 
                        "assigned_object_id": interface['id']
                    }
                    print(f"Alternative payload: {ip_data_alt}")
                    
                    try:
                        result = client.ipam.ip_addresses.create(confirm=False, **ip_data_alt)
                        print(f"✅ ALTERNATIVE SUCCESS: {result}")
                    except Exception as e:
                        print(f"❌ ALTERNATIVE FAILED: {e}")
                        
                        # Check if we can create without assignment, then patch
                        print(f"\nTrying create then assign approach...")
                        ip_data_basic = {
                            "address": test_ip,
                            "status": "active"
                        }
                        print(f"Basic creation payload: {ip_data_basic}")
                        
                        try:
                            basic_result = client.ipam.ip_addresses.create(confirm=False, **ip_data_basic)
                            print(f"✅ BASIC CREATION SUCCESS: {basic_result}")
                        except Exception as e:
                            print(f"❌ BASIC CREATION FAILED: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Debug failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_ip_formats()
    sys.exit(0 if success else 1)