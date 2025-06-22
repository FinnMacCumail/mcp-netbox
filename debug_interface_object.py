#!/usr/bin/env python3
"""
Debug Interface Object Structure

Check what fields are available in the interface object to find content_type.
"""

import sys
import os
import logging
import json

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

def debug_interface_object():
    """Debug the interface object structure."""
    
    try:
        config = load_config()
        client = NetBoxClient(config)
        
        # Get test interface
        test_devices = client.dcim.devices.filter(name__icontains="test-sw-")
        if not test_devices:
            print("❌ No test devices found")
            return False
            
        device = test_devices[0]
        interfaces = client.dcim.interfaces.filter(device_id=device["id"], name="Vlan100")
        if not interfaces:
            print("❌ No test interface found")
            return False
            
        interface = interfaces[0]
        print(f"Found interface: {interface['name']} (ID: {interface['id']})")
        
        print(f"\n🔍 Interface Object Structure:")
        print("="*80)
        
        # Print all keys in the interface object
        print(f"Available keys: {list(interface.keys())}")
        
        # Print the full interface object structure
        print(f"\nFull interface object:")
        for key, value in interface.items():
            print(f"  {key}: {value} (type: {type(value).__name__})")
        
        # Check if content_type exists
        content_type = interface.get("content_type")
        print(f"\nContent type check:")
        print(f"  interface.get('content_type'): {content_type}")
        
        # Check for object_type
        object_type = interface.get("object_type")
        print(f"  interface.get('object_type'): {object_type}")
        
        # Check for _content_type
        _content_type = interface.get("_content_type")
        print(f"  interface.get('_content_type'): {_content_type}")
        
        # Try to see if there's a url that gives us clues
        url = interface.get("url")
        print(f"  interface.get('url'): {url}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_interface_object()
    sys.exit(0 if success else 1)