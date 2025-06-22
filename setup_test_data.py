#!/usr/bin/env python3
"""
Setup Test Data for Device Provisioning Test

This script creates the necessary test infrastructure in NetBox for testing
the high-level device provisioning function.
"""

import sys
import os
import logging

# Add the package directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import load_config
from netbox_mcp.tools.dcim_tools import (
    netbox_create_site, 
    netbox_create_manufacturer,
    netbox_create_device_type,
    netbox_create_device_role,
    netbox_create_rack
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_test_infrastructure():
    """Set up test infrastructure for device provisioning tests."""
    
    try:
        # Load configuration and connect
        config = load_config()
        client = NetBoxClient(config)
        
        status = client.health_check()
        if not status.connected:
            logger.error(f"Failed to connect to NetBox: {status.error}")
            return False
            
        logger.info(f"✅ Connected to NetBox {status.version}")
        
        # 1. Create test site
        logger.info("📍 Creating test site...")
        site_result = netbox_create_site(
            client=client,
            name="MCP Test Site",
            slug="mcp-test-site",
            status="active",
            description="Test site for MCP device provisioning tests",
            confirm=True
        )
        
        if not site_result["success"] and "already exists" not in site_result.get("error", ""):
            logger.error(f"Failed to create test site: {site_result['error']}")
            return False
        logger.info("✅ Test site ready")
        
        # 2. Create test manufacturer
        logger.info("🏭 Creating test manufacturer...")
        mfg_result = netbox_create_manufacturer(
            client=client,
            name="MCP Test Vendor",
            slug="mcp-test-vendor",
            description="Test manufacturer for MCP device provisioning tests",
            confirm=True
        )
        
        if not mfg_result["success"] and "already exists" not in mfg_result.get("error", ""):
            logger.error(f"Failed to create test manufacturer: {mfg_result['error']}")
            return False
        logger.info("✅ Test manufacturer ready")
        
        # 3. Create test device type
        logger.info("🔧 Creating test device type...")
        dt_result = netbox_create_device_type(
            client=client,
            model="MCP Test Switch",
            manufacturer="MCP Test Vendor",
            slug="mcp-test-switch",
            u_height=1,
            description="Test device type for MCP device provisioning tests",
            confirm=True
        )
        
        if not dt_result["success"] and "already exists" not in dt_result.get("error", ""):
            logger.error(f"Failed to create test device type: {dt_result['error']}")
            return False
        logger.info("✅ Test device type ready")
        
        # 4. Create test device role
        logger.info("👔 Creating test device role...")
        role_result = netbox_create_device_role(
            client=client,
            name="MCP Test Switch",
            slug="mcp-test-switch",
            color="2196f3",
            description="Test device role for MCP device provisioning tests",
            confirm=True
        )
        
        if not role_result["success"] and "already exists" not in role_result.get("error", ""):
            logger.error(f"Failed to create test device role: {role_result['error']}")
            return False
        logger.info("✅ Test device role ready")
        
        # 5. Create test rack
        logger.info("🗄️ Creating test rack...")
        rack_result = netbox_create_rack(
            client=client,
            name="MCP Test Rack",
            site="MCP Test Site",
            u_height=42,
            width=19,
            status="active",
            description="Test rack for MCP device provisioning tests",
            confirm=True
        )
        
        if not rack_result["success"] and "already exists" not in rack_result.get("error", ""):
            logger.error(f"Failed to create test rack: {rack_result['error']}")
            return False
        logger.info("✅ Test rack ready")
        
        print("\n" + "="*60)
        print("🎉 TEST INFRASTRUCTURE SETUP COMPLETE")
        print("="*60)
        print("Created test infrastructure:")
        print("  • Site: MCP Test Site")
        print("  • Manufacturer: MCP Test Vendor")
        print("  • Device Type: MCP Test Switch (1U)")
        print("  • Device Role: MCP Test Switch")
        print("  • Rack: MCP Test Rack (42U)")
        print("\nYou can now run the device provisioning test!")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_test_infrastructure()
    sys.exit(0 if success else 1)