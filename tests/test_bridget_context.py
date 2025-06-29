"""
Unit tests for Bridget Auto-Context System - Context Manager

Tests environment detection, safety level assignment, and context management functionality.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from netbox_mcp.persona.bridget_context import (
    BridgetContextManager,
    ContextState,
    get_context_manager,
    auto_initialize_bridget_context,
    merge_context_with_result
)


class TestBridgetContextManager:
    """Test cases for BridgetContextManager class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.context_manager = BridgetContextManager()
        self.mock_client = Mock()
        self.mock_client.url = "https://demo.netbox.local"
    
    def teardown_method(self):
        """Clean up after each test."""
        # Reset context manager state
        self.context_manager.reset_context()
        
        # Clear environment variables
        env_vars = ['NETBOX_ENVIRONMENT', 'NETBOX_SAFETY_LEVEL', 'NETBOX_AUTO_CONTEXT']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_detect_environment_demo_patterns(self):
        """Test environment detection for demo/development patterns."""
        test_cases = [
            ("https://demo.netbox.local", "demo"),
            ("http://localhost:8000", "demo"),
            ("https://127.0.0.1:8000", "demo"),
            ("https://netbox.local", "demo"),
            ("https://mydemo.company.com", "demo")
        ]
        
        for url, expected in test_cases:
            self.mock_client.url = url
            result = self.context_manager.detect_environment(self.mock_client)
            assert result == expected, f"URL {url} should detect as {expected}, got {result}"
    
    def test_detect_environment_staging_patterns(self):
        """Test environment detection for staging/test patterns."""
        test_cases = [
            ("https://staging.netbox.company.com", "staging"),
            ("https://test-netbox.company.com", "staging"),
            ("https://dev.netbox.company.com", "staging"),
            ("https://netbox-staging.company.com", "staging")
        ]
        
        for url, expected in test_cases:
            self.mock_client.url = url
            result = self.context_manager.detect_environment(self.mock_client)
            assert result == expected, f"URL {url} should detect as {expected}, got {result}"
    
    def test_detect_environment_cloud_patterns(self):
        """Test environment detection for cloud patterns."""
        test_cases = [
            ("https://abc123.cloud.netboxapp.com", "cloud"),
            ("https://company.cloud.netbox.com", "cloud")
        ]
        
        for url, expected in test_cases:
            self.mock_client.url = url
            result = self.context_manager.detect_environment(self.mock_client)
            assert result == expected, f"URL {url} should detect as {expected}, got {result}"
    
    def test_detect_environment_production_patterns(self):
        """Test environment detection for production patterns."""
        test_cases = [
            ("https://netbox.company.com", "production"),
            ("https://prod.netbox.company.com", "production"),
            ("https://production-netbox.company.com", "production")
        ]
        
        for url, expected in test_cases:
            self.mock_client.url = url
            result = self.context_manager.detect_environment(self.mock_client)
            assert result == expected, f"URL {url} should detect as {expected}, got {result}"
    
    def test_detect_environment_override(self):
        """Test environment detection with environment variable override."""
        os.environ['NETBOX_ENVIRONMENT'] = 'staging'
        
        # Should override URL-based detection
        self.mock_client.url = "https://demo.netbox.local"
        result = self.context_manager.detect_environment(self.mock_client)
        assert result == 'staging'
    
    def test_detect_environment_fallback(self):
        """Test environment detection fallback for unknown URLs."""
        unknown_urls = [
            "https://unknown.example.com",
            "https://weird-netbox-url.com",
            ""
        ]
        
        for url in unknown_urls:
            self.mock_client.url = url
            result = self.context_manager.detect_environment(self.mock_client)
            assert result == 'production', f"Unknown URL {url} should fallback to production"
    
    def test_detect_safety_level_mapping(self):
        """Test safety level mapping for different environments."""
        expected_mapping = {
            'demo': 'standard',
            'staging': 'high',
            'cloud': 'high',
            'production': 'maximum',
            'unknown': 'maximum'
        }
        
        for environment, expected_safety in expected_mapping.items():
            result = self.context_manager.detect_safety_level(environment)
            assert result == expected_safety, f"Environment {environment} should map to {expected_safety}"
    
    def test_detect_safety_level_override(self):
        """Test safety level override via environment variable."""
        os.environ['NETBOX_SAFETY_LEVEL'] = 'high'
        
        # Should override environment-based mapping
        result = self.context_manager.detect_safety_level('demo')
        assert result == 'high'
    
    def test_detect_instance_type(self):
        """Test instance type detection."""
        test_cases = [
            ("https://abc123.cloud.netboxapp.com", "cloud"),
            ("http://localhost:8000", "self-hosted"),
            ("https://192.168.1.100", "self-hosted"),
            ("https://10.0.0.100", "self-hosted"),
            ("https://netbox.company.com", "self-hosted")
        ]
        
        for url, expected in test_cases:
            self.mock_client.url = url
            result = self.context_manager.detect_instance_type(self.mock_client)
            assert result == expected, f"URL {url} should detect instance type as {expected}"
    
    def test_initialize_context_success(self):
        """Test successful context initialization."""
        # Mock health check
        mock_status = Mock()
        mock_status.version = "3.5.0"
        self.mock_client.health_check.return_value = mock_status
        
        # Initialize context
        context_state = self.context_manager.initialize_context(self.mock_client)
        
        # Verify context state
        assert isinstance(context_state, ContextState)
        assert context_state.environment == 'demo'  # Based on demo.netbox.local
        assert context_state.safety_level == 'standard'
        assert context_state.instance_type == 'self-hosted'
        assert context_state.netbox_version == '3.5.0'
        assert context_state.auto_context_enabled is True
        assert isinstance(context_state.initialization_time, datetime)
    
    def test_initialize_context_health_check_failure(self):
        """Test context initialization when health check fails."""
        # Mock health check failure
        self.mock_client.health_check.side_effect = Exception("Connection failed")
        
        # Should still initialize with basic info
        context_state = self.context_manager.initialize_context(self.mock_client)
        
        assert isinstance(context_state, ContextState)
        assert context_state.environment == 'demo'
        assert context_state.netbox_version is None
    
    def test_context_already_initialized(self):
        """Test that context initialization is idempotent."""
        # Initialize once
        context_state1 = self.context_manager.initialize_context(self.mock_client)
        assert self.context_manager.is_context_initialized()
        
        # Try to initialize again
        context_state2 = self.context_manager.initialize_context(self.mock_client)
        
        # Should return the same context state
        assert context_state1.initialization_time == context_state2.initialization_time
    
    def test_generate_context_message(self):
        """Test context message generation."""
        context_state = ContextState(
            environment='demo',
            safety_level='standard',
            instance_type='self-hosted',
            initialization_time=datetime.now(),
            netbox_version='3.5.0'
        )
        
        message = self.context_manager.generate_context_message(context_state)
        
        # Verify message contains expected elements
        assert "🦜" in message
        assert "Bridget" in message
        assert "Demo/Development" in message
        assert "STANDARD" in message
        assert "Self-Hosted" in message
    
    def test_update_user_preferences(self):
        """Test user preferences update."""
        # Initialize context first
        context_state = self.context_manager.initialize_context(self.mock_client)
        
        # Update preferences
        preferences = {"theme": "dark", "language": "nl"}
        self.context_manager.update_user_preferences(preferences)
        
        # Verify preferences updated
        updated_state = self.context_manager.get_context_state()
        assert updated_state.user_preferences == preferences
    
    def test_reset_context(self):
        """Test context reset functionality."""
        # Initialize context
        self.context_manager.initialize_context(self.mock_client)
        assert self.context_manager.is_context_initialized()
        
        # Reset context
        self.context_manager.reset_context()
        assert not self.context_manager.is_context_initialized()
        assert self.context_manager.get_context_state() is None


class TestGlobalFunctions:
    """Test cases for global context functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_client = Mock()
        self.mock_client.url = "https://demo.netbox.local"
        
        # Reset global context manager
        global_manager = get_context_manager()
        global_manager.reset_context()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean environment variables
        if 'NETBOX_AUTO_CONTEXT' in os.environ:
            del os.environ['NETBOX_AUTO_CONTEXT']
        
        # Reset global context
        global_manager = get_context_manager()
        global_manager.reset_context()
    
    def test_get_context_manager_singleton(self):
        """Test that get_context_manager returns singleton instance."""
        manager1 = get_context_manager()
        manager2 = get_context_manager()
        
        assert manager1 is manager2
    
    def test_auto_initialize_bridget_context_success(self):
        """Test successful auto-initialization."""
        # Mock health check
        mock_status = Mock()
        mock_status.version = "3.5.0"
        self.mock_client.health_check.return_value = mock_status
        
        # Auto-initialize
        result = auto_initialize_bridget_context(self.mock_client)
        
        # Should return welcome message
        assert isinstance(result, str)
        assert "🦜" in result
        assert "Bridget" in result
        assert "Context Automatisch Gedetecteerd" in result
    
    def test_auto_initialize_disabled(self):
        """Test auto-initialization when disabled."""
        os.environ['NETBOX_AUTO_CONTEXT'] = 'false'
        
        result = auto_initialize_bridget_context(self.mock_client)
        assert result == ""
    
    def test_auto_initialize_already_initialized(self):
        """Test auto-initialization when already initialized."""
        # Initialize first
        auto_initialize_bridget_context(self.mock_client)
        
        # Try again - should return empty string
        result = auto_initialize_bridget_context(self.mock_client)
        assert result == ""
    
    def test_auto_initialize_error_handling(self):
        """Test auto-initialization error handling."""
        # Mock client to raise exception
        self.mock_client.health_check.side_effect = Exception("Network error")
        
        # Should return fallback message, not raise exception
        result = auto_initialize_bridget_context(self.mock_client)
        assert isinstance(result, str)
        assert "Context detectie tijdelijk niet beschikbaar" in result
    
    def test_merge_context_with_dict_result(self):
        """Test merging context with dictionary result."""
        original_result = {"success": True, "data": "test"}
        context_message = "🦜 Context message"
        
        merged = merge_context_with_result(original_result, context_message)
        
        assert isinstance(merged, dict)
        assert merged["success"] is True
        assert merged["data"] == "test"
        assert merged["bridget_context"] == context_message
    
    def test_merge_context_with_string_result(self):
        """Test merging context with string result."""
        original_result = "Original tool output"
        context_message = "🦜 Context message"
        
        merged = merge_context_with_result(original_result, context_message)
        
        assert isinstance(merged, str)
        assert "🦜 Context message" in merged
        assert "Original tool output" in merged
        assert merged.startswith(context_message)
    
    def test_merge_context_with_other_result_types(self):
        """Test merging context with other result types."""
        original_result = 42
        context_message = "🦜 Context message"
        
        # Should return original result unchanged for non-dict/string types
        merged = merge_context_with_result(original_result, context_message)
        assert merged == original_result
    
    def test_merge_context_empty_message(self):
        """Test merging with empty context message."""
        original_result = {"success": True}
        context_message = ""
        
        merged = merge_context_with_result(original_result, context_message)
        assert merged == original_result


class TestEnvironmentVariableOverrides:
    """Test cases for environment variable override behavior."""
    
    def setup_method(self):
        """Set up test environment."""
        self.context_manager = BridgetContextManager()
        self.mock_client = Mock()
        self.mock_client.url = "https://netbox.company.com"  # Production URL
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean all environment variables
        env_vars = ['NETBOX_ENVIRONMENT', 'NETBOX_SAFETY_LEVEL', 'NETBOX_AUTO_CONTEXT', 'NETBOX_BRIDGET_PERSONA']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        self.context_manager.reset_context()
    
    def test_environment_override_precedence(self):
        """Test that environment variable takes precedence over URL detection."""
        os.environ['NETBOX_ENVIRONMENT'] = 'demo'
        
        # URL suggests production, but override should win
        result = self.context_manager.detect_environment(self.mock_client)
        assert result == 'demo'
    
    def test_safety_level_override_precedence(self):
        """Test that safety level override takes precedence."""
        os.environ['NETBOX_SAFETY_LEVEL'] = 'standard'
        
        # Production environment normally gets maximum safety
        result = self.context_manager.detect_safety_level('production')
        assert result == 'standard'
    
    def test_invalid_environment_override(self):
        """Test handling of invalid environment override values."""
        os.environ['NETBOX_ENVIRONMENT'] = 'invalid_env'
        
        # Should fall back to URL-based detection
        result = self.context_manager.detect_environment(self.mock_client)
        assert result == 'production'  # Based on URL
    
    def test_invalid_safety_level_override(self):
        """Test handling of invalid safety level override values."""
        os.environ['NETBOX_SAFETY_LEVEL'] = 'invalid_level'
        
        # Should fall back to environment-based mapping
        result = self.context_manager.detect_safety_level('production')
        assert result == 'maximum'  # Default for production


if __name__ == '__main__':
    pytest.main([__file__])