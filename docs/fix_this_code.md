# Instructions for Fixing Bugs in Bulk Cable Workflow (Issue #101)

Hello Developer,

Below are the instructions to fix the bugs and issues, as described in GitHub Issue #101, in the file `netbox_mcp/tools/dcim/bulk_cable_optimized.py`.

## 1. Overview of the Problems

The current implementation of the bulk cable workflow has the following critical problems:
- `AttributeError` when retrieving device names.
- The tool for counting available ports may return outdated data.
- The tool is not flexible in choosing a start port for mapping.
- The validation for the `cable_color` parameter is inconsistent and incorrect.
- A syntax error in a regular expression prevents the code from running.

## 2. Required Changes

Make the following changes in `netbox_mcp/tools/dcim/bulk_cable_optimized.py`.

### Fix 1: Correct the `SyntaxError` in the Regular Expression

The most direct error is a `SyntaxError` due to an unclosed string in the validation for `cable_color`.

**Replace this line:**
```python
if not (re.match(r'^[0-9a-fA-F]{6}', cable_color) or cable_color.lower() in VALID_COLORS):
```

**With this corrected line:**
```python
if not (re.match(r'^[0-9a-fA-F]{6}$', cable_color) or cable_color.lower() in VALID_COLORS):
```

### Fix 2: Modify the `netbox_bulk_cable_interfaces_to_switch` Function

This function needs multiple adjustments.

**Replace the entire `netbox_bulk_cable_interfaces_to_switch` function with the improved version below.**

**Main changes in this new version:**
- **New parameter `start_port_number`:** Gives the user control to specify from which port the mapping should start.
- **Corrected `device_name` resolution:** Prevents the `AttributeError` by correctly retrieving the device name, even when only an ID is available.
- **Improved `cable_color` validation:** The validation logic now correctly accepts both color names and hex codes.

```python
@mcp_tool(category="dcim")
def netbox_bulk_cable_interfaces_to_switch(
    client: NetBoxClient,
    rack_name: str,
    switch_name: str,
    interface_name: str = "lom1",
    switch_port_pattern: str = "Te1/1/",
    start_port_number: Optional[int] = 1,
    cable_color: Optional[str] = None,
    cable_type: str = "cat6",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Optimized bulk cable creation for specific interfaces to switch ports.
    
    This highly optimized tool handles the common scenario of connecting
    all specified interfaces in a rack to sequential switch ports with
    minimal API calls and maximum efficiency.
    
    Args:
        client: NetBoxClient instance (injected)
        rack_name: Source rack name (e.g., "K3")
        switch_name: Target switch name (e.g., "switch1.K3")
        interface_name: Interface name to connect (e.g., "lom1", "eth0", "mgmt", "ilo", "idrac")
        switch_port_pattern: Switch port pattern (e.g., "Te1/1/", "GigabitEthernet0/0/")
        start_port_number: Optional port number to start mapping from (e.g., 1, 25)
        cable_color: Cable color name (e.g., "green") or 6-digit hex code (e.g., "00ff00").
        cable_type: Type of cable (default: "cat6")
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Bulk operation results with detailed success/failure information
    """
    
    # FIX: Add validation for cable_color parameter
    VALID_COLORS = [
        "black", "dark-grey", "grey", "light-grey", "white", "red", "orange",
        "yellow", "green", "cyan", "blue", "purple", "pink", "brown"
    ]
    if cable_color:
        import re
        if not (re.match(r'^[0-9a-fA-F]{6}$', cable_color) or cable_color.lower() in VALID_COLORS):
            raise ValidationError(
                f"Invalid cable_color '{cable_color}'. "
                f"Please use a valid color name or a 6-digit hex code. "
                f"Valid names are: {', '.join(VALID_COLORS)}"
            )

    # ... (rest of the function setup, like natural_sort_key)

    # --- Within the `try` block ---

    # ... (logic for retrieving rack_interfaces) ...

    # FIX: Filter switch ports based on the start_port_number
    if start_port_number and start_port_number > 1:
        original_count = len(switch_ports_sorted)
        
        def get_port_num(port_name):
            import re
            numbers = re.findall(r'\d+', port_name)
            return int(numbers[-1]) if numbers else 0

        switch_ports_sorted = [
            p for p in switch_ports_sorted
            if get_port_num((p.get('name') if isinstance(p, dict) else p.name)) >= start_port_number
        ]
        logger.info(f"Filtered switch ports to start from port {start_port_number}. Original: {original_count}, New: {len(switch_ports_sorted)}")

    # ... (logic for checking capacity) ...

    # --- Within the `for` loop for creating `cable_connections` ---
    
    device = rack_interface.device
    # FIX: Correctly handle device name resolution to prevent AttributeError
    device_obj = client.dcim.devices.get(device.id)
    device_name = device_obj.name if device_obj else f"device-id-{device.id}"

    # ... (rest of the loop) ...
```

### Fix 3: Prevent Cache Issues with Port Availability

To ensure that the tool always checks the most current status of the ports, we need to bypass the cache.

**Find the function `netbox_count_switch_ports_available` and modify the API call.**

**Replace this block:**
```python
all_device_ports = client.dcim.interfaces.filter(
    device__name=switch_name
)
```

**With this block, which adds `no_cache=True`:**
```python
all_device_ports = client.dcim.interfaces.filter(
    device__name=switch_name,
    no_cache=True
)
```

---

After implementing these changes, the problems from issue #101 should be resolved. Run the test script `test_scripts/issue_101_validation.py` to verify the fixes.
