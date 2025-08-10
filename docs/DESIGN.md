Design Document: NetBox Read/Write MCP Server
1. Vision and Objectives
This document describes the design for a Read/Write Model Context Protocol (MCP) Server for NetBox. The goal is to provide a robust, secure, and conversational interface for reading and mutating data in a NetBox (Cloud) instance.

The primary objective is to serve as a robust building block in a broader automation ecosystem, controlled by an orchestrator. This server provides a pure, agnostic interface for NetBox operations without knowledge of the data source. The server will be designed from the start with both read and write capabilities in mind.

2. Core Principles
Idempotence is Crucial: Every write action (tool) must be idempotent. A tool called twice with the same parameters must produce the same end result as when called once, without errors or unwanted duplicates. Tools like netbox_ensure_device_exists are a perfect example of this.
Safety First: Since this MCP can perform destructive actions, there must be built-in safety mechanisms. This includes a 'dry-run' mode and an explicit confirmation parameter for all write actions.
API-First Approach: The core logic is isolated in a netbox_client.py. This client is a direct, well-tested wrapper around the NetBox REST API and the pynetbox library, forming the foundation of the server.
Atomic Operations: MCP tools should, where possible, perform complete, logical operations. A tool to create a device with interfaces must either succeed completely or fail completely and roll back the state, without leaving a half-configured object behind.
Modular Architecture: The server follows a modular structure:
Configuration (config.py): Separated and hierarchical.
Client (netbox_client.py): Responsible for all API interaction.
Server (server.py): Contains the MCP tool definitions and the HTTP server.
Containerization (Dockerfile): For reproducible deployments.
3. Component Architecture
3.1. netbox_client.py
This client will wrap the pynetbox Python library to simplify and standardize interaction with the NetBox API.

Initialization: Accepts NetBox URL, token, and configuration object.
Read methods: Functions for all required GET operations (get_device, get_ip_address, get_prefix, get_vlan, etc.). These methods must expose the powerful filtering capabilities of the NetBox API.
Write methods:
create_object(type, data): A generic function for creating objects.
update_object(object): Uses the .save() method of pynetbox.
delete_object(object): Uses the .delete() method of pynetbox.
Idempotent "Ensure" Methods: Higher-level functions that contain the core of the R/W logic.
ensure_device(name, device_type, site): Searches for a device. If it exists, returns it. If not, creates it.
ensure_ip_address(address, status): Ensures that an IP address object exists.
assign_ip_to_interface(device, interface_name, ip_address): The most complex logic, which creates relationships.
Error Handling: Translates pynetbox exceptions to clear, consistent NetBoxError exceptions.
3.2. server.py
The core of the MCP server. Contains the tool definitions.

Read-Only Tools (Examples):

netbox_get_device(name: str, site: str)
netbox_list_devices(filters: dict)
netbox_find_ip(address: str)
netbox_get_vlan_by_name(name: str, site: str)
netbox_get_device_interfaces(device_name: str)
Read/Write Tools (Examples):

netbox_create_device(name: str, device_type: str, role: str, site: str, confirm: bool = False)
netbox_update_device_status(device_name: str, status: str, confirm: bool = False)
netbox_assign_ip_to_interface(device_name: str, interface_name: str, ip_address: str, confirm: bool = False)
netbox_delete_device(device_name: str, confirm: bool = False)
Agnostic Data Processing: Tools that accept generic device objects and bring them to the correct state in NetBox. These tools make no assumptions about the data source and expect that data preprocessing has been performed by the orchestrator.
3.3. Write Operation Strategy
This is the most critical part of the design.

Confirmation Parameter: Every tool that mutates or deletes data must have a confirm: bool = False parameter. The tool may not perform a write action unless confirm=True. This is an essential safety measure for use with LLMs.
Dry-Run Mode: A global configuration option (--dry-run flag or NETBOX_DRY_RUN=true env var) that puts the server in a mode where all write actions are logged as if they were executed, but no actual API calls are made.
Detailed Logging: Every write action (create, update, delete) must generate a detailed log entry with information about what was changed, with what data, and what the result was.
Response Format: A successful write action returns the modified or created object. This enables the LLM to verify the successful mutation. For example: {"status": "success", "action": "created", "object": {...netbox_device...}}.
3.4. Configuration and Deployment
config.py: Will have NETBOX_URL and NETBOX_TOKEN as required variables. Supports YAML/TOML and environment variables.
Dockerfile: A multi-stage Dockerfile that results in a small, secure image that runs as a non-root user.
Health Checks: Kubernetes-style health checks (/healthz, /readyz) that validate the reachability of the NetBox API in the readyz probe.
