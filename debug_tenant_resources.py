#!/usr/bin/env python3
"""
Debug script to check what resources are actually assigned to a tenant
"""

import logging
from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import ConfigurationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_tenant_resources():
    config = ConfigurationManager.load_config()
    client = NetBoxClient(config)
    
    # Check what tenants exist
    tenants = client.tenancy.tenants.filter()
    logger.info(f"Found {len(tenants)} tenants total")
    
    for tenant in tenants[-5:]:  # Check last 5 tenants
        logger.info(f"Tenant: {tenant['name']} (ID: {tenant['id']})")
    
    # Check specifically for our test tenant
    test_tenant = "Multi-Resource-Tenant-20250623_041748"
    tenants = client.tenancy.tenants.filter(name=test_tenant)
    
    if tenants:
        tenant = tenants[0]
        tenant_id = tenant["id"]
        logger.info(f"Found tenant: {tenant['name']} (ID: {tenant_id})")
        
        # Check prefixes manually
        logger.info("Checking all prefixes...")
        all_prefixes = client.ipam.prefixes.filter()
        logger.info(f"Found {len(all_prefixes)} total prefixes")
        
        for prefix in all_prefixes[:5]:  # Show first 5
            tenant_field = prefix.get("tenant")
            logger.info(f"Prefix {prefix.get('prefix')}: tenant={tenant_field}")
            
        # Find prefixes assigned to our tenant
        tenant_prefixes = [p for p in all_prefixes if 
                          (isinstance(p.get("tenant"), dict) and p.get("tenant", {}).get("id") == tenant_id) or
                          (isinstance(p.get("tenant"), int) and p.get("tenant") == tenant_id)]
        
        logger.info(f"Found {len(tenant_prefixes)} prefixes for tenant {tenant_id}")
        for prefix in tenant_prefixes:
            logger.info(f"  - {prefix.get('prefix')} (ID: {prefix.get('id')})")
        
        # Check sites manually
        logger.info("Checking all sites...")
        all_sites = client.dcim.sites.filter()
        logger.info(f"Found {len(all_sites)} total sites")
        
        tenant_sites = [s for s in all_sites if 
                       (isinstance(s.get("tenant"), dict) and s.get("tenant", {}).get("id") == tenant_id) or
                       (isinstance(s.get("tenant"), int) and s.get("tenant") == tenant_id)]
        
        logger.info(f"Found {len(tenant_sites)} sites for tenant {tenant_id}")
        for site in tenant_sites:
            logger.info(f"  - {site.get('name')} (ID: {site.get('id')})")
            
    else:
        logger.error(f"Tenant {test_tenant} not found")

if __name__ == "__main__":
    debug_tenant_resources()