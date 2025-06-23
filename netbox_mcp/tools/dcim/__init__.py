"""
DCIM (Data Center Infrastructure Management) Tools

This module contains enterprise-grade tools for managing NetBox DCIM objects including
devices, racks, sites, cables, interfaces, modules, and power infrastructure.
"""

# Import all DCIM tools to make them discoverable by the registry
from . import sites
from . import racks
from . import manufacturers
from . import device_roles
# TODO: Import other DCIM modules as they are migrated