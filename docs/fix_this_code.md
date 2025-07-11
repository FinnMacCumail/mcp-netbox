# Instructies voor het Oplossen van Bugs in Bulk Cable Workflow (Issue #101)

Hallo Developer,

Hieronder staan de instructies om de bugs en problemen, zoals beschreven in GitHub Issue #101, op te lossen in het bestand `netbox_mcp/tools/dcim/bulk_cable_optimized.py`.

## 1. Overzicht van de Problemen

De huidige implementatie van de bulk-kabel-workflow heeft de volgende kritieke problemen:
- `AttributeError` bij het ophalen van device-namen.
- De tool voor het tellen van beschikbare poorten geeft mogelijk verouderde data terug.
- De tool is niet flexibel in het kiezen van een startpoort voor de mapping.
- De validatie voor de `cable_color` parameter is inconsistent en foutief.
- Een syntaxisfout in een reguliere expressie voorkomt dat de code draait.

## 2. Benodigde Wijzigingen

Voer de volgende wijzigingen door in `netbox_mcp/tools/dcim/bulk_cable_optimized.py`.

### Fix 1: Corrigeer de `SyntaxError` in de Reguliere Expressie

De meest directe fout is een `SyntaxError` door een niet-afgesloten string in de validatie voor `cable_color`.

**Vervang deze regel:**
```python
if not (re.match(r'^[0-9a-fA-F]{6}', cable_color) or cable_color.lower() in VALID_COLORS):
```

**Met deze gecorrigeerde regel:**
```python
if not (re.match(r'^[0-9a-fA-F]{6}$', cable_color) or cable_color.lower() in VALID_COLORS):
```

### Fix 2: Pas de Functie `netbox_bulk_cable_interfaces_to_switch` aan

Deze functie heeft meerdere aanpassingen nodig.

**Vervang de volledige functie `netbox_bulk_cable_interfaces_to_switch` door de onderstaande, verbeterde versie.**

**Belangrijkste wijzigingen in deze nieuwe versie:**
- **Nieuwe parameter `start_port_number`:** Geeft de gebruiker de controle om te specificeren vanaf welke poort het mappen moet beginnen.
- **Gecorrigeerde `device_name` resolutie:** Voorkomt de `AttributeError` door de device-naam correct op te halen, zelfs als er alleen een ID beschikbaar is.
- **Verbeterde `cable_color` validatie:** De validatielogica accepteert nu correct zowel kleurnamen als hex-codes.

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

    # --- Binnen de `try` block ---

    # ... (logica voor het ophalen van rack_interfaces) ...

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

    # ... (logica voor het controleren van de capaciteit) ...

    # --- Binnen de `for` loop voor het maken van `cable_connections` ---
    
    device = rack_interface.device
    # FIX: Correctly handle device name resolution to prevent AttributeError
    device_obj = client.dcim.devices.get(device.id)
    device_name = device_obj.name if device_obj else f"device-id-{device.id}"

    # ... (rest van de loop) ...
```

### Fix 3: Voorkom Cacheproblemen bij Poortbeschikbaarheid

Om er zeker van te zijn dat de tool altijd de meest actuele status van de poorten controleert, moeten we de cache omzeilen.

**Zoek de functie `netbox_count_switch_ports_available` en pas de API-call aan.**

**Vervang dit blok:**
```python
all_device_ports = client.dcim.interfaces.filter(
    device__name=switch_name
)
```

**Met dit blok, dat `no_cache=True` toevoegt:**
```python
all_device_ports = client.dcim.interfaces.filter(
    device__name=switch_name,
    no_cache=True
)
```

---

Na het doorvoeren van deze wijzigingen zouden de problemen uit issue #101 opgelost moeten zijn. Voer het testscript `test_scripts/issue_101_validation.py` uit om de fixes te verifiëren.
