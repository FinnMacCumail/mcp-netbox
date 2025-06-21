"""
NetBox Read/Write MCP Server

A Model Context Protocol server that provides safe, intelligent read/write access
to NetBox instances. Designed with safety-first principles and idempotent operations.

Features:
- Read-only MCP tools for NetBox data exploration
- Write operations with mandatory confirmation and dry-run mode
- Idempotent ensure operations for robust automation
- Integration-ready for Unimus network discovery workflows
"""

__version__ = "0.1.0"
__author__ = "Deployment Team"
__email__ = "info@deployment-team.nl"

# Version information
VERSION = (0, 1, 0)
VERSION_STRING = ".".join(map(str, VERSION))

# Package exports
from .exceptions import NetBoxError, NetBoxConnectionError, NetBoxAuthError
from .config import NetBoxConfig, SafetyConfig, CacheConfig, load_config
from .client import NetBoxClient, ConnectionStatus

__all__ = [
    "__version__",
    "VERSION", 
    "VERSION_STRING",
    "NetBoxError",
    "NetBoxConnectionError", 
    "NetBoxAuthError",
    "NetBoxConfig",
    "SafetyConfig", 
    "CacheConfig",
    "load_config",
    "NetBoxClient",
    "ConnectionStatus",
]