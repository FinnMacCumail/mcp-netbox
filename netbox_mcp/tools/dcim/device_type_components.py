#!/usr/bin/env python3
"""
DCIM Device Type Components Management Tools - Read-Only Operations

Note: This module originally contained only write operations for device type component templates.
In read-only mode, component template information can be accessed through device type inspection tools.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

# Read-only access to device type components is available through:
# - netbox_get_device_type_info() in device_types.py
# - netbox_list_all_device_types() in device_types.py
