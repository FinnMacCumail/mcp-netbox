#!/usr/bin/env python3
"""
Demo: Self-Describing NetBox MCP API

Demonstrates the new REST API endpoints for tool discovery and execution.
Shows how the MCP server can now describe its own capabilities to LLMs.
"""

import os
import json
import requests
from netbox_mcp.registry import TOOL_REGISTRY, serialize_registry_for_api

# Mock the REST API responses since we're not running a full server
def demo_api_responses():
    """Demonstrate what the API responses would look like."""
    
    print("🌐 NetBox MCP Self-Describing API Demo")
    print("=" * 50)
    
    # Load tools to populate registry
    from netbox_mcp.registry import load_tools
    load_tools()
    
    print(f"📊 Tool Registry Statistics:")
    print(f"   Total tools registered: {len(TOOL_REGISTRY)}")
    
    categories = {}
    for tool_name, metadata in TOOL_REGISTRY.items():
        category = metadata.get('category', 'unknown')
        categories[category] = categories.get(category, 0) + 1
    
    for category, count in categories.items():
        print(f"   {category}: {count} tools")
    
    print("\n" + "=" * 50)
    print("🔍 GET /api/v1/tools (Tool Discovery)")
    print("=" * 50)
    
    # Simulate API response for tool discovery
    tools_response = serialize_registry_for_api()
    
    print(f"Response: {len(tools_response)} tools available\n")
    
    # Show a sample tool
    for tool in tools_response[:2]:
        print(f"🛠️  Tool: {tool['name']}")
        print(f"   Category: {tool.get('category', 'N/A')}")
        print(f"   Description: {tool.get('description', 'N/A')[:80]}...")
        print(f"   Parameters: {len(tool.get('parameters', []))} parameters")
        
        # Show first few parameters
        for param in tool.get('parameters', [])[:3]:
            required = "required" if param.get('required') else "optional"
            print(f"     - {param['name']} ({param.get('type', 'any')}) - {required}")
        
        if len(tool.get('parameters', [])) > 3:
            print(f"     ... and {len(tool.get('parameters', [])) - 3} more parameters")
        print()
    
    print("=" * 50)
    print("🚀 POST /api/v1/execute (Tool Execution)")
    print("=" * 50)
    
    # Show sample execution request
    sample_request = {
        "tool_name": "netbox_health_check",
        "parameters": {}
    }
    
    print("Sample Request Body:")
    print(json.dumps(sample_request, indent=2))
    
    print("\nSample Response:")
    sample_response = {
        "success": True,
        "tool_name": "netbox_health_check",
        "result": {
            "connected": True,
            "version": "4.2.9",
            "python_version": "3.12.3",
            "django_version": "5.1.8",
            "response_time_ms": 177.4
        }
    }
    print(json.dumps(sample_response, indent=2))
    
    print("\n" + "=" * 50)
    print("📊 GET /api/v1/status (System Status)")
    print("=" * 50)
    
    sample_status = {
        "service": "NetBox MCP",
        "version": "0.6.0",
        "status": "healthy",
        "netbox": {
            "connected": True,
            "version": "4.2.9",
            "response_time_ms": 177.4
        },
        "tool_registry": {
            "total_tools": len(TOOL_REGISTRY),
            "categories": categories,
            "tool_names": list(TOOL_REGISTRY.keys())
        },
        "client": {
            "initialized": True,
            "instance_id": 4364318992
        }
    }
    
    print("Sample Response:")
    print(json.dumps(sample_status, indent=2))
    
    print("\n" + "=" * 50)
    print("🎯 API Usage Examples")
    print("=" * 50)
    
    print("# Discover all IPAM tools")
    print("GET /api/v1/tools?category=ipam")
    print()
    
    print("# Find tools for IP address management")  
    print("GET /api/v1/tools?name_pattern=ip_address")
    print()
    
    print("# Execute a tool via REST API")
    print("POST /api/v1/execute")
    print("Content-Type: application/json")
    print()
    print(json.dumps({
        "tool_name": "netbox_create_ip_address",
        "parameters": {
            "address": "192.168.1.10/24",
            "status": "active",
            "description": "Test IP via REST API",
            "confirm": True
        }
    }, indent=2))
    
    print("\n" + "=" * 50)
    print("🚀 Benefits of Self-Describing Architecture")
    print("=" * 50)
    
    benefits = [
        "🤖 LLMs can discover available tools automatically",
        "📖 Complete parameter documentation with types",
        "🔍 Category-based filtering for relevant tools",
        "🔧 Generic execution endpoint for any tool",
        "📊 System health monitoring and diagnostics",
        "🔌 Plugin architecture for easy extensibility",
        "⚡ Dependency injection for clean architecture",
        "🔒 Enterprise safety mechanisms maintained"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")
    
    print(f"\n🎉 NetBox MCP is now a fully self-describing, intelligent API!")

if __name__ == "__main__":
    demo_api_responses()