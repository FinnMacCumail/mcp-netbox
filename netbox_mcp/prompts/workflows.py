"""
NetBox MCP Workflow Prompts

Interactive prompts that guide users through complex NetBox workflows
by orchestrating multiple tools and providing contextual guidance.
"""

from typing import Dict, Any, List, Optional
from ..registry import mcp_prompt


@mcp_prompt(
    name="install_device_in_rack",
    description="Interactive workflow for installing a new device in a datacenter rack"
)
async def install_device_in_rack_prompt() -> Dict[str, Any]:
    """
    Interactive Device Installation Workflow
    
    This prompt guides you through the complete process of installing a new device
    in a datacenter rack, including:
    
    1. Pre-installation validation (rack capacity, power, space)
    2. Resource allocation (IP addresses, rack position)
    3. NetBox configuration (device creation, connections)
    4. Documentation generation (installation checklist, labels)
    
    The workflow will ask for your input step by step and call the appropriate
    NetBox tools automatically.
    
    Required Information:
    - Site name where the device will be installed
    - Rack identifier within the site
    - Device type/model to be installed
    - Network requirements (VLAN preference, IP requirements)
    - Installation preferences (position preference, power requirements)
    
    This prompt will orchestrate the following NetBox tools:
    - netbox_list_all_sites (validate site exists)
    - netbox_get_rack_elevation (check available space)
    - netbox_list_all_device_types (validate device type)
    - netbox_find_next_available_ip (allocate IP address)
    - netbox_provision_new_device (create device in NetBox)
    - netbox_create_cable_connection (document connections)
    - netbox_create_journal_entry (add installation notes)
    
    Expected Workflow:
    1. Site and rack validation
    2. Device type verification
    3. Space and power capacity check
    4. IP address allocation
    5. Device provisioning
    6. Cable documentation
    7. Generate installation checklist
    
    Returns:
        Interactive workflow that collects user input and executes NetBox operations
    """
    
    workflow_steps = {
        "workflow_name": "Install Device in Rack",
        "description": "Complete device installation workflow with pre-checks and documentation",
        "steps": [
            {
                "step": 1,
                "title": "Site and Rack Validation",
                "description": "Verify the target site and rack exist and have capacity",
                "user_inputs_required": [
                    {
                        "name": "site_name",
                        "type": "string",
                        "required": True,
                        "description": "Name of the datacenter site (e.g., 'datacenter-1', 'NYC-DC01')"
                    },
                    {
                        "name": "rack_name", 
                        "type": "string",
                        "required": True,
                        "description": "Rack identifier within the site (e.g., 'R01', 'Rack-A-01')"
                    }
                ],
                "tools_to_execute": [
                    "netbox_get_site_info",
                    "netbox_get_rack_elevation",
                    "netbox_get_rack_inventory"
                ],
                "validation_checks": [
                    "Site exists and is active",
                    "Rack exists in specified site", 
                    "Rack has available U space",
                    "Power capacity available"
                ]
            },
            {
                "step": 2,
                "title": "Device Type and Role Selection",
                "description": "Specify the device to be installed and its intended role",
                "user_inputs_required": [
                    {
                        "name": "device_model",
                        "type": "string", 
                        "required": True,
                        "description": "Device model/type (e.g., 'Cisco Catalyst 9300', 'Dell PowerEdge R740')"
                    },
                    {
                        "name": "device_name",
                        "type": "string",
                        "required": True,
                        "description": "Unique device name (e.g., 'sw-floor1-01', 'srv-db-prod-01')"
                    },
                    {
                        "name": "device_role",
                        "type": "string",
                        "required": True,
                        "description": "Device role (e.g., 'switch', 'server', 'firewall')"
                    },
                    {
                        "name": "position_preference",
                        "type": "string",
                        "required": False,
                        "description": "Preferred rack position: 'top', 'bottom', 'middle', or specific U number",
                        "default": "bottom"
                    }
                ],
                "tools_to_execute": [
                    "netbox_list_all_device_types",
                    "netbox_list_all_device_roles"
                ],
                "validation_checks": [
                    "Device type exists in NetBox",
                    "Device role exists in NetBox",
                    "Device name is unique",
                    "Requested position is available"
                ]
            },
            {
                "step": 3,
                "title": "Network Configuration Planning",
                "description": "Allocate IP addresses and plan network connectivity",
                "user_inputs_required": [
                    {
                        "name": "management_vlan",
                        "type": "string",
                        "required": False,
                        "description": "VLAN for management interface (leave empty for auto-selection)"
                    },
                    {
                        "name": "ip_requirements",
                        "type": "integer",
                        "required": False, 
                        "description": "Number of IP addresses needed",
                        "default": 1
                    },
                    {
                        "name": "network_connections",
                        "type": "array",
                        "required": False,
                        "description": "List of network connections to document (e.g., ['uplink to sw-core-01', 'management to oob-switch'])"
                    }
                ],
                "tools_to_execute": [
                    "netbox_list_all_vlans",
                    "netbox_find_next_available_ip",
                    "netbox_list_all_prefixes"
                ],
                "validation_checks": [
                    "Management VLAN exists (if specified)",
                    "IP addresses available in selected networks",
                    "Network connectivity plan is feasible"
                ]
            },
            {
                "step": 4,
                "title": "Device Provisioning",
                "description": "Create the device in NetBox with all configurations",
                "tools_to_execute": [
                    "netbox_provision_new_device",
                    "netbox_assign_ip_to_interface"
                ],
                "automated": True,
                "description_detail": "This step automatically creates the device with all specified parameters"
            },
            {
                "step": 5,
                "title": "Cable Documentation",
                "description": "Document physical connections and cable management",
                "user_inputs_required": [
                    {
                        "name": "cable_connections",
                        "type": "array",
                        "required": False,
                        "description": "Cable connections to document (format: 'local_interface:remote_device:remote_interface')"
                    }
                ],
                "tools_to_execute": [
                    "netbox_create_cable_connection"
                ]
            },
            {
                "step": 6,
                "title": "Installation Documentation",
                "description": "Generate installation checklist and audit trail",
                "tools_to_execute": [
                    "netbox_create_journal_entry"
                ],
                "automated": True,
                "deliverables": [
                    "Installation checklist for technicians",
                    "Network configuration summary", 
                    "Cable labeling schedule",
                    "Audit trail entry"
                ]
            }
        ],
        "completion_criteria": [
            "Device successfully created in NetBox",
            "IP addresses allocated and assigned",
            "Physical position reserved in rack",
            "Cable connections documented",
            "Installation documentation generated",
            "Journal entry created for audit trail"
        ],
        "rollback_instructions": "If installation fails, use netbox_decommission_device to clean up partially created resources",
        "next_steps": [
            "Physical installation by datacenter technicians",
            "Network configuration deployment", 
            "Device commissioning and testing",
            "Update device status to 'active' after successful installation"
        ]
    }
    
    return {
        "success": True,
        "prompt_type": "interactive_workflow",
        "workflow": workflow_steps,
        "estimated_duration": "15-30 minutes",
        "complexity": "intermediate",
        "prerequisites": [
            "Site and rack must exist in NetBox",
            "Device type must be defined in NetBox", 
            "IP address space must be available",
            "User must have NetBox write permissions"
        ]
    }