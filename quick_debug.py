#!/usr/bin/env python3
"""
Quick debug to find exact error location
"""

from netbox_mcp.client import NetBoxClient
from netbox_mcp.config import NetBoxConfig

def quick_debug():
    NETBOX_URL = "https://zwqg2756.cloud.netboxapp.com"
    NETBOX_TOKEN = "809e04182a7e280398de97e524058277994f44a5"
    
    config = NetBoxConfig(url=NETBOX_URL, token=NETBOX_TOKEN)
    client = NetBoxClient(config)
    
    # Step 1: Get interfaces
    all_interfaces = client.dcim.interfaces.filter(
        device__rack__name="Z1",
        name="BMC"
    )
    print(f"Got {len(all_interfaces)} interfaces")
    
    # Step 2: Extract device IDs
    device_ids = set()
    for interface in all_interfaces:
        device = interface.get('device') if isinstance(interface, dict) else interface.device
        print(f"Interface device: {device} (type: {type(device)})")
        
        if isinstance(device, int):
            device_ids.add(device)
        elif isinstance(device, dict):
            device_ids.add(device.get('id'))
        else:
            device_ids.add(getattr(device, 'id', None))
    
    print(f"Device IDs: {device_ids}")
    
    # Step 3: Batch fetch
    device_ids = {dev_id for dev_id in device_ids if dev_id is not None}
    print(f"Filtered Device IDs: {device_ids}")
    
    devices_batch = client.dcim.devices.filter(id__in=list(device_ids))
    print(f"Batch result: {devices_batch} (type: {type(devices_batch)})")
    print(f"Batch length: {len(devices_batch)}")
    
    # Step 4: Inspect each device and check rack info
    for i, device in enumerate(devices_batch):
        if i < 3:  # Only first 3 for brevity
            print(f"Device {i}: {device.get('name')} (type: {type(device)})")
            rack_id = device.get('rack')
            print(f"  Rack ID: {rack_id} (type: {type(rack_id)})")
            
            # We need to fetch rack info to get name!
            if rack_id:
                print(f"  Need to fetch rack {rack_id} to get name!")
        
    print("🚨 PROBLEM IDENTIFIED: Devices have rack IDs, not rack names!")
    print("   We need to batch-fetch racks too to get rack names for validation")

if __name__ == "__main__":
    quick_debug()