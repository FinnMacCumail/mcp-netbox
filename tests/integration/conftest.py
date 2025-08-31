"""
Pytest configuration for Week 9-12 Real NetBox Integration Tests

This module provides shared fixtures and configuration for comprehensive
integration testing of the real NetBox MCP integration.
"""

import asyncio
import pytest
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Import test dependencies
import redis.asyncio as aioredis
from unittest.mock import MagicMock, patch

# Import project modules for fixtures
from netbox_mcp.orchestration.real_api_handler import RealAPIHandler
from netbox_mcp.orchestration.cache import OrchestrationCache


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_available():
    """Check if Redis is available for cache testing"""
    try:
        redis_client = aioredis.from_url("redis://localhost:6379")
        await redis_client.ping()
        await redis_client.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="function")
async def clean_redis():
    """Clean Redis test data before each test"""
    try:
        redis_client = aioredis.from_url("redis://localhost:6379")
        await redis_client.flushdb()  # Clear test database
        await redis_client.close()
    except Exception:
        pass  # Redis not available, skip cleanup


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        "redis_url": "redis://localhost:6379",
        "test_namespace": "netbox_mcp_test",
        "test_timeout": 30,
        "mock_netbox_url": "http://localhost:8000",
        "test_session_id": "test_session_integration",
        "netbox_url": "http://localhost:8000",
        "timeout": 30,
        "verify_ssl": False,
        "max_retries": 3,
        "default_page_size": 50,
        "max_results": 1000,
        "netbox": {
            "url": "http://localhost:8000",
            "token": "test_token_123",
            "timeout": 30,
            "verify_ssl": False
        }
    }


@pytest.fixture
async def api_handler(test_config):
    """Provide a configured RealAPIHandler for testing"""
    with patch('netbox_mcp.orchestration.real_api_handler.get_config') as mock_get_config:
        mock_get_config.return_value = test_config
        
        handler = RealAPIHandler(test_config)
        
        # Create a proper mock client that passes all checks
        class MockNetBoxClient:
            def __bool__(self):
                return True
            def __nonzero__(self):  # Python 2 compatibility
                return True
        
        mock_client = MockNetBoxClient()
        
        # Set the client directly and ensure it stays set
        handler._netbox_client = mock_client
        
        # Mock the initialization completely to avoid any actual NetBox connection
        async def mock_initialize():
            handler._netbox_client = mock_client
            handler.logger.info("Mock NetBox API handler initialized")
        
        handler.initialize = mock_initialize
        await handler.initialize()
        
        # Ensure client is set after initialization
        handler._netbox_client = mock_client
        
        yield handler


@pytest.fixture
async def orchestration_cache(redis_available, test_config):
    """Provide an OrchestrationCache for testing"""
    if redis_available:
        # Use real Redis if available
        cache = OrchestrationCache(redis_url=test_config["redis_url"])
    else:
        # Use memory cache as fallback
        with patch('netbox_mcp.orchestration.cache.aioredis') as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis not available")
            cache = OrchestrationCache()
    
    yield cache
    
    # Cleanup
    try:
        if hasattr(cache, '_redis_client') and cache._redis_client:
            await cache._redis_client.close()
    except:
        pass


@pytest.fixture
def sample_netbox_responses():
    """Provide sample NetBox API responses for testing"""
    return {
        "netbox_health_check": {
            "success": True,
            "result": {
                "status": "healthy",
                "version": "3.5.0",
                "timestamp": datetime.now().isoformat()
            },
            "message": "NetBox health check successful"
        },
        
        "netbox_list_all_sites": {
            "success": True,
            "result": {
                "sites": [
                    {
                        "id": 1,
                        "name": "datacenter-1",
                        "slug": "datacenter-1",
                        "status": "active",
                        "region": "us-east",
                        "description": "Primary datacenter"
                    },
                    {
                        "id": 2,
                        "name": "datacenter-2", 
                        "slug": "datacenter-2",
                        "status": "active",
                        "region": "us-west",
                        "description": "Secondary datacenter"
                    }
                ],
                "total": 2
            },
            "message": "Retrieved 2 sites successfully"
        },
        
        "netbox_list_all_devices": {
            "success": True,
            "result": {
                "devices": [
                    {
                        "id": 1,
                        "name": "server-001",
                        "site": "datacenter-1",
                        "device_type": "Dell PowerEdge R740",
                        "role": "server",
                        "status": "active",
                        "position": 10,
                        "rack": "rack-a1"
                    },
                    {
                        "id": 2,
                        "name": "switch-001",
                        "site": "datacenter-1", 
                        "device_type": "Cisco Nexus 9300",
                        "role": "switch",
                        "status": "active",
                        "position": 1,
                        "rack": "rack-a1"
                    }
                ],
                "total": 2
            },
            "message": "Retrieved 2 devices successfully"
        },
        
        "netbox_get_device_info": {
            "success": True,
            "result": {
                "device": {
                    "id": 1,
                    "name": "server-001",
                    "site": "datacenter-1",
                    "device_type": {
                        "model": "PowerEdge R740",
                        "manufacturer": "Dell"
                    },
                    "role": "server",
                    "status": "active",
                    "position": 10,
                    "rack": "rack-a1",
                    "serial": "ABC123456",
                    "asset_tag": "ASSET-001",
                    "interfaces_count": 4,
                    "cables_count": 2
                }
            },
            "message": "Retrieved device info successfully"
        },
        
        "netbox_get_device_interfaces": {
            "success": True,
            "result": {
                "interfaces": [
                    {
                        "id": 1,
                        "name": "eth0",
                        "type": "1000base-t",
                        "enabled": True,
                        "mtu": 1500,
                        "mac_address": "00:11:22:33:44:55",
                        "description": "Management interface"
                    },
                    {
                        "id": 2,
                        "name": "eth1",
                        "type": "10gbase-sr",
                        "enabled": True,
                        "mtu": 9000,
                        "mac_address": "00:11:22:33:44:56",
                        "description": "Data interface"
                    }
                ],
                "total": 2
            },
            "message": "Retrieved 2 interfaces successfully"
        },
        
        "netbox_list_all_device_types": {
            "success": True,
            "result": {
                "device_types": [
                    {
                        "id": 1,
                        "model": "PowerEdge R740",
                        "manufacturer": "Dell",
                        "u_height": 2,
                        "is_full_depth": True,
                        "part_number": "R740"
                    },
                    {
                        "id": 2,
                        "model": "Nexus 9300",
                        "manufacturer": "Cisco",
                        "u_height": 1,
                        "is_full_depth": True,
                        "part_number": "N9K-9300"
                    }
                ],
                "total": 2
            },
            "message": "Retrieved 2 device types successfully"
        }
    }


@pytest.fixture
def mock_tool_execution_times():
    """Provide realistic tool execution times for performance testing"""
    return {
        "netbox_health_check": 0.3,
        "netbox_list_all_sites": 0.8,
        "netbox_list_all_devices": 1.2,
        "netbox_get_device_info": 0.6,
        "netbox_get_device_interfaces": 1.0,
        "netbox_list_all_device_types": 1.1,
        "netbox_list_all_racks": 0.9,
        "netbox_get_rack_inventory": 1.8,
        "netbox_list_all_vlans": 0.7,
        "netbox_list_all_cables": 1.5
    }


@pytest.fixture 
def performance_test_thresholds():
    """Provide performance test thresholds"""
    return {
        "max_execution_time": 10.0,  # seconds
        "min_cache_hit_rate": 0.7,   # 70%
        "max_error_rate": 0.1,       # 10%
        "max_parallel_speedup": 5.0, # 5x improvement
        "min_success_rate": 0.95     # 95%
    }


@pytest.fixture
def entity_test_data():
    """Provide test data for entity tracking"""
    return {
        "sites": [
            {"name": "datacenter-1", "type": "site", "status": "active"},
            {"name": "datacenter-2", "type": "site", "status": "active"}
        ],
        "devices": [
            {"name": "server-001", "type": "device", "site": "datacenter-1"},
            {"name": "server-002", "type": "device", "site": "datacenter-1"},
            {"name": "switch-001", "type": "device", "site": "datacenter-1"}
        ],
        "racks": [
            {"name": "rack-a1", "type": "rack", "site": "datacenter-1"},
            {"name": "rack-a2", "type": "rack", "site": "datacenter-1"}
        ],
        "relationships": [
            {"source": "server-001", "target": "datacenter-1", "type": "located_in"},
            {"source": "server-001", "target": "rack-a1", "type": "installed_in"},
            {"source": "rack-a1", "target": "datacenter-1", "type": "located_in"}
        ]
    }


@pytest.fixture
def reference_resolution_test_cases():
    """Provide test cases for reference resolution"""
    return [
        # Pronoun tests
        {"input": "it", "expected_type": "pronoun", "context": "recent_device"},
        {"input": "that", "expected_type": "pronoun", "context": "recent_entity"},
        {"input": "them", "expected_type": "pronoun", "context": "multiple_entities"},
        
        # Quantified tests
        {"input": "all devices", "expected_type": "quantified", "entity_type": "device"},
        {"input": "both sites", "expected_type": "quantified", "entity_type": "site"},
        {"input": "every rack", "expected_type": "quantified", "entity_type": "rack"},
        
        # Demonstrative tests
        {"input": "the device", "expected_type": "demonstrative", "entity_type": "device"},
        {"input": "the site", "expected_type": "demonstrative", "entity_type": "site"},
        
        # Superlative tests
        {"input": "the main site", "expected_type": "superlative", "entity_type": "site"},
        {"input": "the primary device", "expected_type": "superlative", "entity_type": "device"},
        
        # Relational tests
        {"input": "connected devices", "expected_type": "relational", "relationship": "connected_to"},
        {"input": "same site devices", "expected_type": "relational", "relationship": "same_site"}
    ]


# Test markers for categorizing tests
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "redis_required: marks tests that require Redis"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Mark performance tests
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
            
        # Mark Redis tests
        if "cache" in item.name.lower() or "redis" in item.name.lower():
            item.add_marker(pytest.mark.redis_required)
            
        # Mark slow tests
        if any(keyword in item.name.lower() for keyword in ["end_to_end", "workflow", "complex"]):
            item.add_marker(pytest.mark.slow)