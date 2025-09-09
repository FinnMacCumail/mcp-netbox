#!/usr/bin/env python3
"""
DCIM Interface Management Tools

High-level tools for managing NetBox interfaces with enterprise-grade functionality.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


# Read-only interface tools - write operations removed for DeepAgents context optimization
# Original file contained only write operations (netbox_assign_ip_to_interface, netbox_create_interface)