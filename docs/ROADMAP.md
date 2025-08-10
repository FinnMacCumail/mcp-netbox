Project Roadmap: NetBox Read/Write MCP Server
This document describes an iterative development plan to build the NetBox R/W MCP Server. The roadmap is divided into phases, where each phase delivers a stable and testable product.

Phase 1: Foundation and Read-Only Core (v0.1)
Goal: A stable, read-only server that lays the foundation for future development.

Project Structure: Setting up the repository with pyproject.toml, .gitignore, README.md, etc.
Configuration: Implementing config.py with support for NETBOX_URL and NETBOX_TOKEN.
NetBox Client (Read-Only): Implementing the netbox_client.py with pynetbox. Focus on GET operations: get_device, list_sites, get_ip_address, get_vlan.
First MCP Tools: Implementing the first set of read-only tools in server.py:
netbox_get_device
netbox_list_devices
netbox_get_site_by_name
Basic Docker Support: Creating a Dockerfile and docker-compose.yml for a working, read-only container.
CI/CD Pipeline: Setting up a GitHub Actions workflow for linting, testing, and building the Docker image.
Phase 2: Initial Write Capabilities and Safety (v0.2)
Goal: Introduce the first, simple write actions with maximum safety.

Write Methods in Client: Extending netbox_client.py with basic create, update, and delete methods.
Safety Mechanisms: Implementing the confirm: bool = False parameter in the write tools and the global dry-run mode.
First Write Tools: Implementing the first, most basic write tools:
netbox_create_site(name: str, slug: str, confirm: bool = False)
netbox_create_manufacturer(name: str, slug: str, confirm: bool = False)
netbox_create_device_role(name: str, slug: str, color: str, confirm: bool = False)
Extended Logging: Implementing detailed logging for all write actions.
Integration Tests: Setting up the first integration tests that validate write actions (in dry-run or against a test instance).
Phase 3: Advanced R/W Operations and Relationships (v0.3)
Goal: Build complex tools that connect objects to each other and lay the foundation for enterprise integration.

Idempotent "Ensure" Logic: Implementing ensure_* methods in the netbox_client.py.
Complex MCP Tools: Implementing tools that create relationships:
netbox_create_device (with connection to site, role, type)
netbox_create_interface_for_device
netbox_assign_ip_to_interface
Data Mapping Logic: Developing a strategy to map enterprise fields (such as device type and vendor) to NetBox objects (DeviceType, Manufacturer).
Core Integration Tool: Implementing enterprise device management tools. This is the most important milestone of this phase.
Phase 4: Enterprise Features and Integration Readiness (v0.4)
Goal: Make the server more robust and prepare it for production use and actual integration.

Caching System: Implementing a caching layer for frequently requested read-only data to improve performance and reduce the load on the NetBox API.
Advanced Search and Filter Tools: Implementing tools that use the powerful filtering capabilities of NetBox, e.g., netbox_find_available_ips_in_prefix.
Improved Health Checks: Extending /readyz to check the NetBox API version and status.
Documentation: Writing the initial Wiki documentation for installation, configuration, and API reference.
Phase 5: Production Readiness and Full Integration (v1.0)
Goal: A stable, well-documented v1.0 release and a working end-to-end enterprise-to-NetBox workflow.

Performance Tuning: Optimizing the client and tools for bulk operations.
Full Test Coverage: Ensuring high test coverage, especially for all write and ensure paths.
End-to-End Workflow: Creating an example script or notebook that shows how enterprise tools and NetBox MCP work together to synchronize a NetBox instance.
Wiki Documentation: Completing the documentation with extensive examples, use cases, and best practices for R/W operations.
Security Hardening: A final review of all security aspects.
Future Ideas (Post-v1.0)
Webhook Support: Listening to NetBox webhooks to trigger actions.
Custom Reports: Tools that generate complex, composite reports from NetBox data.
Service Modeling: Tools for modeling complete network services (e.g., setting up a VPN with all associated objects).
Extended 'Diff' Functionality: A tool that compares a device (discovered by enterprise tools) with its state in NetBox and generates a 'plan' of required changes.
