"""
Virtualization Management Tools

This module contains enterprise-grade tools for managing NetBox virtualization objects including
virtual machines, clusters, cluster types, and virtualization platforms.
"""

# Import all virtualization tools to make them discoverable by the registry
from . import clusters
from . import virtual_machines