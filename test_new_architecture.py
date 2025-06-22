#!/usr/bin/env python3
"""
Test script for the new self-describing architecture

Tests the circular import resolution, tool registry, and API endpoints.
"""

import os
import json
from pathlib import Path

# Set up environment for testing
os.environ["NETBOX_URL"] = "https://zwqg2756.cloud.netboxapp.com"
os.environ["NETBOX_TOKEN"] = "809e04182a7e280398de97e524058277994f44a5"

def test_circular_import_resolution():
    """Test that circular imports are resolved."""
    print("🧪 Testing circular import resolution...")
    
    try:
        from netbox_mcp.registry import TOOL_REGISTRY, load_tools
        from netbox_mcp.dependencies import get_netbox_client
        print("✅ Imports successful - no circular dependency!")
        
        # Test tool loading
        load_tools()
        print(f"✅ Tools loaded: {len(TOOL_REGISTRY)} tools registered")
        
        return True
    except ImportError as e:
        print(f"❌ Circular import still exists: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

def test_tool_registry():
    """Test the tool registry functionality."""
    print("\n🧪 Testing tool registry...")
    
    try:
        from netbox_mcp.registry import TOOL_REGISTRY, serialize_registry_for_api
        
        # Check if tools are loaded
        if len(TOOL_REGISTRY) == 0:
            print("⚠️  No tools loaded - this might be expected if imports failed")
            return False
        
        # Test serialization
        api_tools = serialize_registry_for_api()
        print(f"✅ Registry serialization works: {len(api_tools)} tools serialized")
        
        # Show some examples
        for tool_name, metadata in list(TOOL_REGISTRY.items())[:3]:
            print(f"  - {tool_name} ({metadata['category']}): {metadata['description'][:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ Tool registry error: {e}")
        return False

def test_dependency_injection():
    """Test the dependency injection system."""
    print("\n🧪 Testing dependency injection...")
    
    try:
        from netbox_mcp.dependencies import get_netbox_client, get_client_status
        
        # Test client creation
        client = get_netbox_client()
        print(f"✅ Client creation successful: {type(client).__name__}")
        
        # Test client status
        status = get_client_status()
        print(f"✅ Client status: initialized={status['initialized']}, ID={status['instance_id']}")
        
        return True
    except Exception as e:
        print(f"❌ Dependency injection error: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints (without actually starting server)."""
    print("\n🧪 Testing API endpoint definitions...")
    
    try:
        from netbox_mcp.server import api_app
        
        # Check that FastAPI app is created
        print(f"✅ FastAPI app created: {api_app.title}")
        
        # Check routes
        routes = [route.path for route in api_app.routes if hasattr(route, 'path')]
        expected_routes = ['/api/v1/tools', '/api/v1/execute', '/api/v1/status']
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route defined: {route}")
            else:
                print(f"❌ Route missing: {route}")
        
        return True
    except Exception as e:
        print(f"❌ API endpoint error: {e}")
        return False

def test_tool_execution():
    """Test tool execution with dependency injection."""
    print("\n🧪 Testing tool execution...")
    
    try:
        from netbox_mcp.registry import execute_tool, TOOL_REGISTRY
        from netbox_mcp.dependencies import get_netbox_client
        
        if len(TOOL_REGISTRY) == 0:
            print("⚠️  No tools to test")
            return False
        
        # Get a system tool to test
        system_tools = [name for name, meta in TOOL_REGISTRY.items() if meta.get('category') == 'system']
        if not system_tools:
            print("⚠️  No system tools found to test")
            return False
        
        tool_name = system_tools[0]
        client = get_netbox_client()
        
        print(f"Testing tool: {tool_name}")
        result = execute_tool(tool_name, client)
        print(f"✅ Tool execution successful: {type(result)}")
        
        return True
    except Exception as e:
        print(f"❌ Tool execution error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 NetBox MCP Architecture Test Suite")
    print("=" * 50)
    
    tests = [
        test_circular_import_resolution,
        test_tool_registry, 
        test_dependency_injection,
        test_api_endpoints,
        test_tool_execution
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print(f"📊 Test Summary: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 All tests passed! New architecture is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the output above.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)