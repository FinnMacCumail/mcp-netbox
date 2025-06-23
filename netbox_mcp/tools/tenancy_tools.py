#!/usr/bin/env python3
"""
Tenancy Tools for NetBox MCP

Comprehensive tenant management tools following Gemini's dependency 
injection architecture. All tools receive NetBoxClient via dependency injection
rather than importing it directly.

These tools provide high-level tenancy functionality with enterprise safety
mechanisms and comprehensive input validation for multi-tenant environments.
"""

from typing import Dict, List, Optional, Any
import logging
import re
from ..registry import mcp_tool
from ..client import NetBoxClient

logger = logging.getLogger(__name__)


# ========================================
# TENANT MANAGEMENT TOOLS
# ========================================
# NOTE: Tenant onboarding tool migrated to tenancy/tenants.py


# ========================================
# TENANT GROUP MANAGEMENT TOOLS
# ========================================

# NOTE: netbox_create_tenant_group migrated to tenancy/tenants.py


# ========================================
# TENANT RESOURCE ASSIGNMENT TOOLS
# ========================================

# NOTE: netbox_assign_resources_to_tenant migrated to tenancy/resources.py


# ========================================
# TENANT REPORTING TOOLS
# ========================================

# NOTE: netbox_get_tenant_resource_report migrated to tenancy/resources.py


# ========================================
# CONTACT MANAGEMENT TOOLS
# ========================================
# NOTE: Contact management tools migrated to tenancy/contacts.py