"""
Integration tests for Bridget Auto-Context System - Auto-Initialization

Tests end-to-end auto-initialization behavior and first-call context injection.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from netbox_mcp.registry import execute_tool, reset_context_state
from netbox_mcp.persona import get_context_manager


class TestAutoInitializationIntegration:
    """Test cases for auto-initialization integration with tool execution."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Reset context state
        reset_context_state()
        
        # Mock client
        self.mock_client = Mock()
        self.mock_client.url = "https://demo.netbox.local"
        
        # Mock health check
        mock_status = Mock()
        mock_status.version = "3.5.0"
        mock_status.connected = True
        self.mock_client.health_check.return_value = mock_status
        
        # Mock tool function
        self.mock_tool_func = Mock()
        self.mock_tool_func.return_value = {"success": True, "data": "test_result"}
    
    def teardown_method(self):
        """Clean up after each test."""
        # Reset context state
        reset_context_state()
        
        # Clean environment variables
        env_vars = ['NETBOX_ENVIRONMENT', 'NETBOX_SAFETY_LEVEL', 'NETBOX_AUTO_CONTEXT']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_first_tool_execution_triggers_context_initialization(self, mock_get_tool):
        """Test that first tool execution automatically initializes context."""
        # Mock tool metadata
        mock_get_tool.return_value = {
            "function": self.mock_tool_func,
            "name": "test_tool",
            "category": "test"
        }
        
        # Execute tool for the first time
        result = execute_tool("test_tool", self.mock_client, param1="value1")
        
        # Verify tool was executed
        self.mock_tool_func.assert_called_once_with(client=self.mock_client, param1="value1")
        
        # Verify context was initialized
        context_manager = get_context_manager()
        assert context_manager.is_context_initialized()
        
        # Verify result includes context information
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["data"] == "test_result"
        assert "bridget_context" in result
        assert "🦜" in result["bridget_context"]
        assert "Context Automatisch Gedetecteerd" in result["bridget_context"]
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_second_tool_execution_no_context_injection(self, mock_get_tool):
        """Test that second tool execution doesn't inject context again."""
        # Mock tool metadata
        mock_get_tool.return_value = {
            "function": self.mock_tool_func,
            "name": "test_tool",
            "category": "test"
        }
        
        # Execute tool twice
        result1 = execute_tool("test_tool", self.mock_client, param1="value1")
        result2 = execute_tool("test_tool", self.mock_client, param1="value2")
        
        # First execution should have context
        assert "bridget_context" in result1
        
        # Second execution should not have context
        assert "bridget_context" not in result2
        assert result2 == {"success": True, "data": "test_result"}
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_auto_context_disabled_no_injection(self, mock_get_tool):
        """Test that context injection is disabled when NETBOX_AUTO_CONTEXT=false."""
        os.environ['NETBOX_AUTO_CONTEXT'] = 'false'
        
        # Mock tool metadata
        mock_get_tool.return_value = {
            "function": self.mock_tool_func,
            "name": "test_tool",
            "category": "test"
        }
        
        # Execute tool
        result = execute_tool("test_tool", self.mock_client, param1="value1")
        
        # Verify tool was executed
        self.mock_tool_func.assert_called_once()
        
        # Verify no context was injected
        assert result == {"success": True, "data": "test_result"}
        assert "bridget_context" not in result
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_context_initialization_failure_graceful_degradation(self, mock_get_tool):
        """Test graceful degradation when context initialization fails."""
        # Mock tool metadata
        mock_get_tool.return_value = {
            "function": self.mock_tool_func,
            "name": "test_tool",
            "category": "test"
        }
        
        # Mock client to fail health check
        self.mock_client.health_check.side_effect = Exception("Network error")
        
        # Execute tool
        result = execute_tool("test_tool", self.mock_client, param1="value1")
        
        # Verify tool execution was not blocked
        self.mock_tool_func.assert_called_once_with(client=self.mock_client, param1="value1")
        
        # Result should still be the original tool result (graceful degradation)
        assert result["success"] is True
        assert result["data"] == "test_result"
        
        # Context might still be injected with fallback message
        if "bridget_context" in result:
            assert "Context detectie tijdelijk niet beschikbaar" in result["bridget_context"]
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_context_reset_allows_reinitialization(self, mock_get_tool):
        """Test that context reset allows re-initialization on next tool call."""
        # Mock tool metadata
        mock_get_tool.return_value = {
            "function": self.mock_tool_func,
            "name": "test_tool",
            "category": "test"
        }
        
        # Execute tool first time
        result1 = execute_tool("test_tool", self.mock_client, param1="value1")
        assert "bridget_context" in result1
        
        # Reset context
        reset_context_state()
        
        # Execute tool again - should trigger re-initialization
        result2 = execute_tool("test_tool", self.mock_client, param1="value2")
        assert "bridget_context" in result2
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_string_result_context_injection(self, mock_get_tool):
        """Test context injection with string tool results."""
        # Mock tool function that returns string
        mock_string_tool = Mock()
        mock_string_tool.return_value = "Tool executed successfully"
        
        # Mock tool metadata
        mock_get_tool.return_value = {
            "function": mock_string_tool,
            "name": "string_tool",
            "category": "test"
        }
        
        # Execute tool
        result = execute_tool("string_tool", self.mock_client)
        
        # Verify result is string with context prepended
        assert isinstance(result, str)
        assert "🦜" in result
        assert "Context Automatisch Gedetecteerd" in result
        assert "Tool executed successfully" in result
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_non_dict_non_string_result_unchanged(self, mock_get_tool):
        """Test that non-dict/non-string results are unchanged by context injection."""
        # Mock tool function that returns integer
        mock_int_tool = Mock()
        mock_int_tool.return_value = 42
        
        # Mock tool metadata
        mock_get_tool.return_value = {
            "function": mock_int_tool,
            "name": "int_tool",
            "category": "test"
        }
        
        # Execute tool
        result = execute_tool("int_tool", self.mock_client)
        
        # Verify result is unchanged
        assert result == 42
        assert isinstance(result, int)


class TestEnvironmentSpecificInitialization:
    """Test auto-initialization behavior in different environments."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_context_state()
        
        # Mock health check
        self.mock_status = Mock()
        self.mock_status.version = "3.5.0"
        self.mock_status.connected = True
    
    def teardown_method(self):
        """Clean up after each test."""
        reset_context_state()
        
        # Clean environment variables
        env_vars = ['NETBOX_ENVIRONMENT', 'NETBOX_SAFETY_LEVEL']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_production_environment_initialization(self, mock_get_tool):
        """Test context initialization behavior in production environment."""
        # Mock production client
        mock_client = Mock()
        mock_client.url = "https://netbox.company.com"
        mock_client.health_check.return_value = self.mock_status
        
        # Mock tool
        mock_tool_func = Mock()
        mock_tool_func.return_value = {"success": True}
        mock_get_tool.return_value = {"function": mock_tool_func}
        
        # Execute tool
        result = execute_tool("test_tool", mock_client)
        
        # Verify production-specific context
        assert "bridget_context" in result
        context_message = result["bridget_context"]
        assert "Production" in context_message
        assert "MAXIMUM" in context_message  # Safety level
        assert "🚨" in context_message  # Production warning
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_demo_environment_initialization(self, mock_get_tool):
        """Test context initialization behavior in demo environment."""
        # Mock demo client
        mock_client = Mock()
        mock_client.url = "https://demo.netbox.local"
        mock_client.health_check.return_value = self.mock_status
        
        # Mock tool
        mock_tool_func = Mock()
        mock_tool_func.return_value = {"success": True}
        mock_get_tool.return_value = {"function": mock_tool_func}
        
        # Execute tool
        result = execute_tool("test_tool", mock_client)
        
        # Verify demo-specific context
        assert "bridget_context" in result
        context_message = result["bridget_context"]
        assert "Demo/Development" in context_message
        assert "STANDARD" in context_message  # Safety level
        assert "🧪" in context_message  # Demo guidance
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_cloud_environment_initialization(self, mock_get_tool):
        """Test context initialization behavior in cloud environment."""
        # Mock cloud client
        mock_client = Mock()
        mock_client.url = "https://abc123.cloud.netboxapp.com"
        mock_client.health_check.return_value = self.mock_status
        
        # Mock tool
        mock_tool_func = Mock()
        mock_tool_func.return_value = {"success": True}
        mock_get_tool.return_value = {"function": mock_tool_func}
        
        # Execute tool
        result = execute_tool("test_tool", mock_client)
        
        # Verify cloud-specific context
        assert "bridget_context" in result
        context_message = result["bridget_context"]
        assert "NetBox Cloud" in context_message
        assert "HIGH" in context_message  # Safety level
        assert "☁️" in context_message  # Cloud guidance


class TestConcurrencyAndThreadSafety:
    """Test auto-initialization behavior under concurrent access."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_context_state()
        
        self.mock_client = Mock()
        self.mock_client.url = "https://demo.netbox.local"
        mock_status = Mock()
        mock_status.version = "3.5.0"
        self.mock_client.health_check.return_value = mock_status
    
    def teardown_method(self):
        """Clean up after each test."""
        reset_context_state()
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_concurrent_first_calls_single_initialization(self, mock_get_tool):
        """Test that concurrent first calls result in single context initialization."""
        import threading
        import time
        
        # Mock tool
        mock_tool_func = Mock()
        mock_tool_func.return_value = {"success": True}
        mock_get_tool.return_value = {"function": mock_tool_func}
        
        results = {}
        exceptions = {}
        
        def execute_tool_thread(thread_id):
            try:
                # Add small delay to increase chance of concurrent execution
                time.sleep(0.01)
                result = execute_tool("test_tool", self.mock_client, thread_id=thread_id)
                results[thread_id] = result
            except Exception as e:
                exceptions[thread_id] = e
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=execute_tool_thread, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
        
        # Verify all tools executed successfully
        assert len(results) == 5
        
        # Count how many results have context injection
        context_injections = sum(1 for result in results.values() if "bridget_context" in result)
        
        # Should be exactly one context injection (first call wins)
        assert context_injections == 1, f"Expected 1 context injection, got {context_injections}"
        
        # Verify context manager shows initialized state
        context_manager = get_context_manager()
        assert context_manager.is_context_initialized()


class TestPerformanceImpact:
    """Test performance impact of auto-initialization."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_context_state()
        
        self.mock_client = Mock()
        self.mock_client.url = "https://demo.netbox.local"
        mock_status = Mock()
        mock_status.version = "3.5.0"
        self.mock_client.health_check.return_value = mock_status
    
    def teardown_method(self):
        """Clean up after each test."""
        reset_context_state()
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_first_call_overhead_acceptable(self, mock_get_tool):
        """Test that first call overhead is within acceptable limits."""
        import time
        
        # Mock simple tool
        mock_tool_func = Mock()
        mock_tool_func.return_value = {"success": True}
        mock_get_tool.return_value = {"function": mock_tool_func}
        
        # Measure first call (with context initialization)
        start_time = time.time()
        result1 = execute_tool("test_tool", self.mock_client)
        first_call_time = time.time() - start_time
        
        # Measure second call (without context initialization)
        start_time = time.time()
        result2 = execute_tool("test_tool", self.mock_client)
        second_call_time = time.time() - start_time
        
        # Verify both calls succeeded
        assert result1["success"] is True
        assert result2["success"] is True
        
        # Context initialization should add minimal overhead (< 500ms as per requirements)
        assert first_call_time < 0.5, f"First call took {first_call_time:.3f}s, exceeds 500ms requirement"
        
        # Second call should be faster (no context initialization)
        # Allow some margin due to test environment variability
        assert second_call_time <= first_call_time * 1.1, "Second call should not be significantly slower than first"
    
    @patch('netbox_mcp.registry.get_tool_by_name')
    def test_subsequent_calls_no_overhead(self, mock_get_tool):
        """Test that subsequent calls have no context-related overhead."""
        import time
        
        # Mock simple tool
        mock_tool_func = Mock()
        mock_tool_func.return_value = {"success": True}
        mock_get_tool.return_value = {"function": mock_tool_func}
        
        # Initialize context with first call
        execute_tool("test_tool", self.mock_client)
        
        # Measure multiple subsequent calls
        call_times = []
        for _ in range(10):
            start_time = time.time()
            result = execute_tool("test_tool", self.mock_client)
            call_time = time.time() - start_time
            call_times.append(call_time)
            assert result["success"] is True
        
        # All subsequent calls should be consistently fast
        avg_time = sum(call_times) / len(call_times)
        max_time = max(call_times)
        
        # Subsequent calls should be very fast (< 10ms average)
        assert avg_time < 0.01, f"Average call time {avg_time:.4f}s too high"
        assert max_time < 0.05, f"Max call time {max_time:.4f}s too high"


if __name__ == '__main__':
    pytest.main([__file__])