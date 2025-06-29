"""
Unit tests for Bridget Auto-Context System - Context Prompts

Tests prompt integration and MCP prompt functionality for auto-context system.
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from netbox_mcp.prompts.context_prompts import (
    bridget_welcome_and_initialize_prompt,
    bridget_environment_detected_prompt,
    bridget_safety_guidance_prompt
)
from netbox_mcp.persona.bridget_context import ContextState


class TestContextPrompts:
    """Test cases for context-related MCP prompts."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.mock_client = Mock()
        self.mock_client.url = "https://demo.netbox.local"
        
        # Mock health check
        mock_status = Mock()
        mock_status.version = "3.5.0"
        mock_status.connected = True
        self.mock_client.health_check.return_value = mock_status
    
    def teardown_method(self):
        """Clean up after each test."""
        # Reset context manager state
        from netbox_mcp.persona import get_context_manager
        context_manager = get_context_manager()
        context_manager.reset_context()
        
        # Clean environment variables
        env_vars = ['NETBOX_ENVIRONMENT', 'NETBOX_SAFETY_LEVEL', 'NETBOX_AUTO_CONTEXT']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    @patch('netbox_mcp.prompts.context_prompts.get_netbox_client')
    async def test_bridget_welcome_and_initialize_prompt_success(self, mock_get_client):
        """Test successful welcome and initialization prompt."""
        mock_get_client.return_value = self.mock_client
        
        result = await bridget_welcome_and_initialize_prompt()
        
        # Verify result is a string (MCP compatible)
        assert isinstance(result, str)
        
        # Verify Bridget branding
        assert "🦜" in result
        assert "Bridget" in result
        assert "NetBox MCP" in result
        
        # Verify context information
        assert "Context Automatisch Gedetecteerd" in result
        assert "Demo/Development" in result  # Based on demo.netbox.local
        assert "STANDARD" in result  # Safety level for demo
        
        # Verify guidance sections
        assert "Workflow Guidance" in result
        assert "Direct Tool Access" in result
        assert "Aanbevolen Volgende Stappen" in result
    
    @patch('netbox_mcp.prompts.context_prompts.get_netbox_client')
    async def test_bridget_welcome_prompt_production_environment(self, mock_get_client):
        """Test welcome prompt with production environment detection."""
        self.mock_client.url = "https://netbox.company.com"
        mock_get_client.return_value = self.mock_client
        
        result = await bridget_welcome_and_initialize_prompt()
        
        assert isinstance(result, str)
        assert "Production" in result
        assert "MAXIMUM" in result  # Safety level for production
        assert "Start Carefully" in result  # Production-specific guidance
    
    @patch('netbox_mcp.prompts.context_prompts.get_netbox_client')
    async def test_bridget_welcome_prompt_already_initialized(self, mock_get_client):
        """Test welcome prompt when context is already initialized."""
        mock_get_client.return_value = self.mock_client
        
        # Initialize context first
        from netbox_mcp.persona import get_context_manager
        context_manager = get_context_manager()
        context_manager.initialize_context(self.mock_client)
        
        result = await bridget_welcome_and_initialize_prompt()
        
        assert isinstance(result, str)
        assert "Context reeds geïnitialiseerd" in result
    
    @patch('netbox_mcp.prompts.context_prompts.get_netbox_client')
    async def test_bridget_welcome_prompt_error_handling(self, mock_get_client):
        """Test welcome prompt error handling."""
        # Mock client to raise exception
        mock_get_client.side_effect = Exception("Connection failed")
        
        result = await bridget_welcome_and_initialize_prompt()
        
        # Should return fallback message, not raise exception
        assert isinstance(result, str)
        assert "Bridget" in result
        assert "Context" in result
    
    @patch('netbox_mcp.prompts.context_prompts.get_netbox_client')
    async def test_bridget_environment_detected_prompt_success(self, mock_get_client):
        """Test environment detection prompt with initialized context."""
        mock_get_client.return_value = self.mock_client
        
        # Initialize context first
        from netbox_mcp.persona import get_context_manager
        context_manager = get_context_manager()
        context_manager.initialize_context(self.mock_client)
        
        result = await bridget_environment_detected_prompt()
        
        assert isinstance(result, str)
        assert "Environment Detection Report" in result
        assert "DEMO" in result  # Environment type
        assert "STANDARD" in result  # Safety level
        assert "Self-Hosted" in result  # Instance type
        assert "Configuration Details" in result
    
    @patch('netbox_mcp.prompts.context_prompts.get_netbox_client')
    async def test_bridget_environment_detected_prompt_not_initialized(self, mock_get_client):
        """Test environment detection prompt without initialized context."""
        mock_get_client.return_value = self.mock_client
        
        result = await bridget_environment_detected_prompt()
        
        # Should auto-initialize and then provide report
        assert isinstance(result, str)
        assert "Environment Detection Report" in result
    
    async def test_bridget_environment_detected_prompt_no_context(self):
        """Test environment detection prompt when context cannot be initialized."""
        with patch('netbox_mcp.prompts.context_prompts.get_netbox_client') as mock_get_client:
            mock_get_client.side_effect = Exception("No client available")
            
            result = await bridget_environment_detected_prompt()
            
            assert isinstance(result, str)
            assert "Context nog niet geïnitialiseerd" in result
    
    async def test_bridget_safety_guidance_prompt_demo_environment(self):
        """Test safety guidance prompt for demo environment."""
        # Pre-initialize context with demo environment
        from netbox_mcp.persona import get_context_manager
        context_manager = get_context_manager()
        context_state = ContextState(
            environment='demo',
            safety_level='standard',
            instance_type='self-hosted',
            initialization_time=datetime.now()
        )
        context_manager._context_state = context_state
        
        result = await bridget_safety_guidance_prompt()
        
        assert isinstance(result, str)
        assert "Safety Level: STANDARD" in result
        assert "Standard Safety Mode" in result
        assert "Development Best Practices" in result
    
    async def test_bridget_safety_guidance_prompt_production_environment(self):
        """Test safety guidance prompt for production environment."""
        # Pre-initialize context with production environment
        from netbox_mcp.persona import get_context_manager
        context_manager = get_context_manager()
        context_state = ContextState(
            environment='production',
            safety_level='maximum',
            instance_type='self-hosted',
            initialization_time=datetime.now()
        )
        context_manager._context_state = context_state
        
        result = await bridget_safety_guidance_prompt()
        
        assert isinstance(result, str)
        assert "Safety Level: MAXIMUM" in result
        assert "Maximum Safety Mode" in result
        assert "Production Best Practices" in result
        assert "VERPLICHT" in result  # Dry-run mandatory
    
    async def test_bridget_safety_guidance_prompt_not_initialized(self):
        """Test safety guidance prompt without initialized context."""
        result = await bridget_safety_guidance_prompt()
        
        assert isinstance(result, str)
        assert "Context niet geïnitialiseerd" in result
        assert "bridget_welcome_and_initialize" in result


class TestPromptHelperFunctions:
    """Test cases for prompt helper functions."""
    
    def setup_method(self):
        """Set up test environment."""
        from netbox_mcp.persona import get_context_manager
        self.context_manager = get_context_manager()
        self.context_manager.reset_context()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.context_manager.reset_context()
    
    def test_next_steps_recommendations_production(self):
        """Test next steps recommendations for production environment."""
        from netbox_mcp.prompts.context_prompts import _get_next_steps_recommendations
        
        context_state = ContextState(
            environment='production',
            safety_level='maximum',
            instance_type='self-hosted',
            initialization_time=datetime.now()
        )
        
        result = _get_next_steps_recommendations(context_state)
        
        assert "Production Environment - Start Carefully" in result
        assert "dry-run mode" in result
        assert "confirm=False" in result
    
    def test_next_steps_recommendations_demo(self):
        """Test next steps recommendations for demo environment."""
        from netbox_mcp.prompts.context_prompts import _get_next_steps_recommendations
        
        context_state = ContextState(
            environment='demo',
            safety_level='standard',
            instance_type='self-hosted',
            initialization_time=datetime.now()
        )
        
        result = _get_next_steps_recommendations(context_state)
        
        assert "Demo Environment - Experiment Freely" in result
        assert "install_device_in_rack" in result
        assert "Try workflows" in result
    
    def test_detailed_safety_info_levels(self):
        """Test detailed safety information for different levels."""
        from netbox_mcp.prompts.context_prompts import _get_detailed_safety_info
        
        # Test each safety level
        standard_info = _get_detailed_safety_info('standard')
        assert "Standard Safety Mode" in standard_info
        assert "🟢" in standard_info
        
        high_info = _get_detailed_safety_info('high')
        assert "High Safety Mode" in high_info
        assert "🟡" in high_info
        
        maximum_info = _get_detailed_safety_info('maximum')
        assert "Maximum Safety Mode" in maximum_info
        assert "🔴" in maximum_info
        assert "VERPLICHT" in maximum_info
    
    def test_environment_analysis(self):
        """Test environment analysis for different environments."""
        from netbox_mcp.prompts.context_prompts import _get_environment_analysis
        
        # Test each environment type
        demo_analysis = _get_environment_analysis('demo')
        assert "Demo/Development Environment" in demo_analysis
        assert "Veilig voor experimenteren" in demo_analysis
        
        production_analysis = _get_environment_analysis('production')
        assert "Production Environment" in production_analysis
        assert "Kritieke business operations" in production_analysis
        
        cloud_analysis = _get_environment_analysis('cloud')
        assert "NetBox Cloud Instance" in cloud_analysis
        assert "Managed cloud service" in cloud_analysis
    
    def test_check_environment_overrides_with_overrides(self):
        """Test environment override checking with active overrides."""
        from netbox_mcp.prompts.context_prompts import _check_environment_overrides
        
        # Set some overrides
        os.environ['NETBOX_ENVIRONMENT'] = 'staging'
        os.environ['NETBOX_SAFETY_LEVEL'] = 'high'
        
        try:
            result = _check_environment_overrides()
            assert 'NETBOX_ENVIRONMENT' in result
            assert 'NETBOX_SAFETY_LEVEL' in result
        finally:
            # Clean up
            del os.environ['NETBOX_ENVIRONMENT']
            del os.environ['NETBOX_SAFETY_LEVEL']
    
    def test_check_environment_overrides_no_overrides(self):
        """Test environment override checking with no overrides."""
        from netbox_mcp.prompts.context_prompts import _check_environment_overrides
        
        result = _check_environment_overrides()
        assert result == 'None'
    
    def test_calculate_session_duration(self):
        """Test session duration calculation."""
        from netbox_mcp.prompts.context_prompts import _calculate_session_duration
        
        # Test different durations
        now = datetime.now()
        
        # Test seconds
        init_time = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second - 30)
        result = _calculate_session_duration(init_time)
        assert "seconden" in result
        
        # Test minutes
        init_time = datetime(now.year, now.month, now.day, now.hour, now.minute - 5, now.second)
        result = _calculate_session_duration(init_time)
        assert "minuten" in result
    
    def test_safety_rules_production(self):
        """Test critical safety rules for production environment."""
        from netbox_mcp.prompts.context_prompts import _get_critical_safety_rules
        
        result = _get_critical_safety_rules('production', 'maximum')
        
        assert "confirm=True" in result
        assert "dry-run validation" in result
        assert "maintenance windows" in result
        assert "rollback procedures" in result
    
    def test_safety_rules_demo(self):
        """Test critical safety rules for demo environment."""
        from netbox_mcp.prompts.context_prompts import _get_critical_safety_rules
        
        result = _get_critical_safety_rules('demo', 'standard')
        
        # Should contain basic rules but not production-specific ones
        assert "confirm=True" in result
        assert "dependencies" in result
        # Should not contain maintenance window requirements
        assert "maintenance windows" not in result


class TestPromptMCPCompatibility:
    """Test cases for MCP protocol compatibility."""
    
    @patch('netbox_mcp.prompts.context_prompts.get_netbox_client')
    async def test_all_prompts_return_strings(self, mock_get_client):
        """Test that all context prompts return MCP-compatible strings."""
        mock_client = Mock()
        mock_client.url = "https://demo.netbox.local"
        mock_status = Mock()
        mock_status.version = "3.5.0"
        mock_client.health_check.return_value = mock_status
        mock_get_client.return_value = mock_client
        
        # Test all prompt functions
        prompts = [
            bridget_welcome_and_initialize_prompt,
            bridget_environment_detected_prompt,
            bridget_safety_guidance_prompt
        ]
        
        for prompt_func in prompts:
            result = await prompt_func()
            assert isinstance(result, str), f"{prompt_func.__name__} must return string for MCP compatibility"
            assert len(result) > 0, f"{prompt_func.__name__} must return non-empty string"
            assert "🦜" in result, f"{prompt_func.__name__} must include Bridget branding"
    
    async def test_prompt_error_handling_returns_strings(self):
        """Test that prompt error handling returns MCP-compatible strings."""
        with patch('netbox_mcp.prompts.context_prompts.get_netbox_client') as mock_get_client:
            # Force an error
            mock_get_client.side_effect = Exception("Test error")
            
            # All prompts should handle errors gracefully and return strings
            result = await bridget_welcome_and_initialize_prompt()
            assert isinstance(result, str)
            assert "Bridget" in result
    
    def test_no_complex_objects_in_prompt_returns(self):
        """Test that prompts don't return complex objects that break MCP rendering."""
        # This is more of a design validation test
        from netbox_mcp.prompts.context_prompts import (
            _get_fallback_welcome_message
        )
        
        fallback = _get_fallback_welcome_message()
        assert isinstance(fallback, str)
        assert "🦜" in fallback
        assert "NetBox MCP" in fallback


if __name__ == '__main__':
    pytest.main([__file__])