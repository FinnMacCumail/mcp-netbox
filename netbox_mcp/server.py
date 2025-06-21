#!/usr/bin/env python3
"""
NetBox MCP Server

A Model Context Protocol server for safe read/write access to NetBox instances.
Provides tools for querying and managing NetBox data with comprehensive safety controls.

Version: 0.1.0
"""

from mcp.server.fastmcp import FastMCP
from .client import NetBoxClient, ConnectionStatus
from .config import load_config, NetBoxConfig
from .exceptions import (
    NetBoxError,
    NetBoxConnectionError,
    NetBoxAuthError,
    NetBoxNotFoundError,
    NetBoxValidationError
)
import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from functools import partial
from typing import Dict, List, Optional, Any, Union

# Global configuration and client
config: Optional[NetBoxConfig] = None
netbox_client: Optional[NetBoxClient] = None

# Configure logging (will be updated from config)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("NetBox", description="Read/Write MCP server for NetBox network documentation and IPAM")


@mcp.tool()
def netbox_health_check() -> Dict[str, Any]:
    """
    Get NetBox system health status and connection information.

    Returns:
        Health status information containing:
        - connected: True if connected, False otherwise
        - version: NetBox version (e.g., "4.2.9")
        - python_version: Python version of NetBox instance
        - django_version: Django version of NetBox instance
        - response_time_ms: Response time in milliseconds
        - plugins: Installed NetBox plugins
        - error: Error message if connection failed
    """
    try:
        status = netbox_client.health_check()
        return {
            "connected": status.connected,
            "version": status.version,
            "python_version": status.python_version,
            "django_version": status.django_version,
            "response_time_ms": status.response_time_ms,
            "plugins": status.plugins,
            "error": status.error
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


@mcp.tool()
def netbox_get_device(name: str, site: Optional[str] = None) -> Dict[str, Any]:
    """
    Get device information by name and optionally by site.

    Args:
        name: Device name to search for
        site: Optional site name to filter by

    Returns:
        Device information including:
        - Device details (name, type, role, status)
        - Site information
        - IP addresses (primary IPv4/IPv6)
        - Location and rack information
        - Tags and custom fields
        - Timestamps (created, last_updated)

    Example:
        netbox_get_device("switch-01")
        netbox_get_device("switch-01", "datacenter-1")
    """
    try:
        device = netbox_client.get_device(name, site)
        
        if device is None:
            return {
                "found": False,
                "message": f"Device '{name}' not found" + (f" at site '{site}'" if site else "")
            }
        
        return {
            "found": True,
            "device": device
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting device {name}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting device {name}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_list_devices(
    site: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    List devices with optional filtering.

    Args:
        site: Filter by site name (optional)
        role: Filter by device role (optional)
        status: Filter by device status (optional)
        limit: Maximum number of results to return (optional)

    Returns:
        List of devices with basic information:
        - Device name, type, site, role, status
        - Primary IP addresses
        - Last updated timestamp

    Example:
        netbox_list_devices()
        netbox_list_devices(site="datacenter-1", limit=10)
        netbox_list_devices(role="switch", status="active")
    """
    try:
        # Build filters dictionary
        filters = {}
        if site:
            filters['site'] = site
        if role:
            filters['role'] = role
        if status:
            filters['status'] = status
        
        devices = netbox_client.list_devices(filters=filters if filters else None, limit=limit)
        
        return {
            "count": len(devices),
            "devices": devices,
            "filters_applied": filters
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error listing devices: {e}")
        return {
            "count": 0,
            "devices": [],
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error listing devices: {e}")
        return {
            "count": 0,
            "devices": [],
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_site_by_name(name: str) -> Dict[str, Any]:
    """
    Get site information by name.

    Args:
        name: Site name to search for

    Returns:
        Site information including:
        - Site details (name, slug, status, description)
        - Location information (region, physical address)
        - Device and rack counts
        - Tags and custom fields
        - Timestamps (created, last_updated)

    Example:
        netbox_get_site_by_name("datacenter-1")
        netbox_get_site_by_name("branch-office-nyc")
    """
    try:
        site = netbox_client.get_site_by_name(name)
        
        if site is None:
            return {
                "found": False,
                "message": f"Site '{name}' not found"
            }
        
        return {
            "found": True,
            "site": site
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting site {name}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting site {name}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_find_ip(address: str) -> Dict[str, Any]:
    """
    Find IP address object by address.

    Args:
        address: IP address to search for (e.g., "192.168.1.1" or "192.168.1.1/24")

    Returns:
        IP address information including:
        - Address details (address, status, role)
        - Assignment information (device, interface)
        - VRF and tenant information
        - DNS name and description
        - Tags and custom fields

    Example:
        netbox_find_ip("192.168.1.1")
        netbox_find_ip("10.0.0.1/24")
    """
    try:
        ip = netbox_client.get_ip_address(address)
        
        if ip is None:
            return {
                "found": False,
                "message": f"IP address '{address}' not found"
            }
        
        return {
            "found": True,
            "ip_address": ip
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error finding IP {address}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error finding IP {address}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_vlan_by_name(name: str, site: Optional[str] = None) -> Dict[str, Any]:
    """
    Get VLAN information by name and optionally by site.

    Args:
        name: VLAN name to search for
        site: Optional site name to filter by

    Returns:
        VLAN information including:
        - VLAN details (name, VID, status, role)
        - Site and group information
        - Tenant information
        - Description and comments
        - Tags and custom fields

    Example:
        netbox_get_vlan_by_name("VLAN-100")
        netbox_get_vlan_by_name("Management", "datacenter-1")
    """
    try:
        vlan = netbox_client.get_vlan_by_name(name, site)
        
        if vlan is None:
            return {
                "found": False,
                "message": f"VLAN '{name}' not found" + (f" at site '{site}'" if site else "")
            }
        
        return {
            "found": True,
            "vlan": vlan
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting VLAN {name}: {e}")
        return {
            "found": False,
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting VLAN {name}: {e}")
        return {
            "found": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_device_interfaces(device_name: str) -> Dict[str, Any]:
    """
    Get all interfaces for a specific device.

    Args:
        device_name: Name of the device to get interfaces for

    Returns:
        List of interfaces including:
        - Interface details (name, type, enabled status)
        - Network configuration (speed, duplex, MTU)
        - VLAN assignments (tagged/untagged)
        - MAC address and description
        - Connection status

    Example:
        netbox_get_device_interfaces("switch-01")
        netbox_get_device_interfaces("router-core-01")
    """
    try:
        interfaces = netbox_client.get_device_interfaces(device_name)
        
        return {
            "device_name": device_name,
            "interface_count": len(interfaces),
            "interfaces": interfaces
        }
        
    except NetBoxNotFoundError as e:
        logger.error(f"Device not found: {device_name}")
        return {
            "device_name": device_name,
            "interface_count": 0,
            "interfaces": [],
            "error": str(e),
            "error_type": "DeviceNotFound"
        }
    except NetBoxError as e:
        logger.error(f"NetBox error getting interfaces for {device_name}: {e}")
        return {
            "device_name": device_name,
            "interface_count": 0,
            "interfaces": [],
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting interfaces for {device_name}: {e}")
        return {
            "device_name": device_name,
            "interface_count": 0,
            "interfaces": [],
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


@mcp.tool()
def netbox_get_manufacturers(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Get list of manufacturers in NetBox.

    Args:
        limit: Maximum number of results to return (optional)

    Returns:
        List of manufacturers including:
        - Manufacturer details (name, slug, description)
        - Device type count for each manufacturer
        - Tags and custom fields
        - Timestamps (created, last_updated)

    Example:
        netbox_get_manufacturers()
        netbox_get_manufacturers(limit=10)
    """
    try:
        manufacturers = netbox_client.get_manufacturers(limit=limit)
        
        return {
            "count": len(manufacturers),
            "manufacturers": manufacturers
        }
        
    except NetBoxError as e:
        logger.error(f"NetBox error getting manufacturers: {e}")
        return {
            "count": 0,
            "manufacturers": [],
            "error": str(e),
            "error_type": e.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error getting manufacturers: {e}")
        return {
            "count": 0,
            "manufacturers": [],
            "error": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }


# HTTP Health Check Server (similar to unimus-mcp)
class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints."""
    
    def do_GET(self):
        """Handle GET requests for health check endpoints."""
        try:
            if self.path in ['/health', '/healthz']:
                # Basic liveness check
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response = {
                    "status": "OK",
                    "service": "netbox-mcp",
                    "version": "0.1.0"
                }
                self.wfile.write(json.dumps(response).encode())
                
            elif self.path == '/readyz':
                # Readiness check - test NetBox connection
                try:
                    if netbox_client:
                        status = netbox_client.health_check()
                        if status.connected:
                            self.send_response(200)
                            response = {
                                "status": "OK",
                                "netbox_connected": True,
                                "netbox_version": status.version,
                                "response_time_ms": status.response_time_ms
                            }
                        else:
                            self.send_response(503)
                            response = {
                                "status": "Service Unavailable",
                                "netbox_connected": False,
                                "error": status.error
                            }
                    else:
                        self.send_response(503)
                        response = {
                            "status": "Service Unavailable",
                            "netbox_connected": False,
                            "error": "NetBox client not initialized"
                        }
                except Exception as e:
                    self.send_response(503)
                    response = {
                        "status": "Service Unavailable",
                        "netbox_connected": False,
                        "error": str(e)
                    }
                
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response = {"error": "Not Found"}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"Health check handler error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {"error": "Internal Server Error", "details": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"Health check: {format % args}")


def start_health_server(port: int):
    """Start the HTTP health check server in a separate thread."""
    def run_server():
        try:
            server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
            logger.info(f"Health check server started on port {port}")
            logger.info(f"Health endpoints: /health, /healthz (liveness), /readyz (readiness)")
            server.serve_forever()
        except Exception as e:
            logger.error(f"Health check server failed: {e}")
    
    health_thread = threading.Thread(target=run_server, daemon=True)
    health_thread.start()


def initialize_server():
    """Initialize the NetBox MCP server with configuration and client."""
    global config, netbox_client
    
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded successfully")
        
        # Update logging level
        logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
        logger.info(f"Log level set to {config.log_level}")
        
        # Log safety configuration
        if config.safety.dry_run_mode:
            logger.warning("🚨 NetBox MCP running in DRY-RUN mode - no actual writes will be performed")
        
        if not config.safety.enable_write_operations:
            logger.info("🔒 Write operations are DISABLED - server is read-only")
        
        # Initialize NetBox client
        netbox_client = NetBoxClient(config)
        logger.info("NetBox client initialized successfully")
        
        # Test connection
        status = netbox_client.health_check()
        if status.connected:
            logger.info(f"✅ Connected to NetBox {status.version} (response time: {status.response_time_ms:.1f}ms)")
        else:
            logger.error(f"❌ Failed to connect to NetBox: {status.error}")
        
        # Start health check server if enabled
        if config.enable_health_server:
            start_health_server(config.health_check_port)
        
        logger.info("NetBox MCP server initialization complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize NetBox MCP server: {e}")
        raise


def main():
    """Main entry point for the NetBox MCP server."""
    try:
        # Initialize server
        initialize_server()
        
        # Define the MCP server task to run in a thread
        def run_mcp_server():
            try:
                logger.info("Starting NetBox MCP server on a dedicated thread...")
                mcp.run(transport="stdio")
            except Exception as e:
                logger.error(f"MCP server thread encountered an error: {e}", exc_info=True)

        # Start the MCP server in a daemon thread
        mcp_thread = threading.Thread(target=run_mcp_server)
        mcp_thread.daemon = True
        mcp_thread.start()
        
        # Keep the main thread alive to allow daemon threads to run
        logger.info("NetBox MCP server is ready and listening")
        logger.info("Health endpoints: /health, /healthz (liveness), /readyz (readiness)")
        
        try:
            while True:
                time.sleep(3600)  # Sleep for a long time
        except KeyboardInterrupt:
            logger.info("Shutting down NetBox MCP server...")
        
    except Exception as e:
        logger.error(f"NetBox MCP server error: {e}")
        raise


if __name__ == "__main__":
    main()