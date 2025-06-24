"""
IPAM (IP Address Management) Tools

This module contains enterprise-grade tools for managing NetBox IPAM objects including
IP addresses, prefixes, VLANs, and high-level automation workflows.
"""

# Import all IPAM tools to make them discoverable by the registry
from . import addresses
from . import prefixes  
from . import vlans
from . import enterprise
from . import aggregates
from . import ip_addresses
from . import mac_addresses
from . import rirs
from . import vrfs