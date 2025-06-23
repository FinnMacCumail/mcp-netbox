"""
IPAM (IP Address Management) Tools

This module contains enterprise-grade tools for managing NetBox IPAM objects including
IP addresses, prefixes, VLANs, and high-level automation workflows.
"""

# Import all IPAM tools to make them discoverable by the registry
from . import addresses
from . import prefixes  
from . import vlans
# TODO: Import other IPAM modules as they are migrated