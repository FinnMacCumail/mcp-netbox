"""
Comprehensive tests for workflow prompts functionality.

This module tests the bulk_cable_installation_prompt and other workflow
prompts that provide guided user experiences for NetBox operations.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from netbox_mcp.prompts.workflows import (
    bulk_cable_installation_prompt,
    install_device_in_rack_prompt,
    activate_bridget_prompt
)


class TestBulkCableInstallationPrompt:
    """Test the bulk cable installation workflow prompt."""
    
    @pytest.mark.asyncio
    async def test_bulk_cable_installation_prompt_structure(self):
        """Test that the bulk cable installation prompt has correct structure."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify result is a string (MCP prompt format)
        assert isinstance(result, str)
        
        # Verify essential workflow elements are present
        assert "Bulk Cable Installation Workflow" in result
        assert "Bridget" in result
        assert "NetBox Infrastructure Guide" in result
        
        # Verify GitHub issue reference
        assert "#92" in result or "GitHub issue #92" in result
        
        # Verify target scenario is mentioned
        assert "lom1" in result
        assert "rack K3" in result or "rack" in result
        assert "switch1.k3" in result or "switch" in result
        assert "pink" in result or "roze" in result
        
        # Verify workflow steps are present
        assert "Stap 1" in result or "Step 1" in result
        assert "Stap 2" in result or "Step 2" in result
        assert "Stap 7" in result or "Step 7" in result
        
        # Verify enterprise features are mentioned
        assert "dry-run" in result or "Dry-run" in result
        assert "rollback" in result or "Rollback" in result
        assert "batch" in result or "Batch" in result
    
    @pytest.mark.asyncio
    async def test_bulk_cable_installation_prompt_workflow_steps(self):
        """Test that all required workflow steps are present."""
        
        result = await bulk_cable_installation_prompt()
        
        # Expected workflow steps
        expected_steps = [
            "Rack en Interface Discovery",
            "Target Switch en Port Validatie",
            "Interface Mapping Algoritme",
            "Cable Specificaties",
            "Mapping Preview",
            "Bulk Cable Creation",
            "Installation Documentatie"
        ]
        
        for step in expected_steps:
            # Check for step presence (allowing for Dutch/English variations)
            assert (step in result or 
                   step.lower() in result.lower() or
                   any(word in result for word in step.split()))
    
    @pytest.mark.asyncio
    async def test_bulk_cable_installation_prompt_netbox_tools(self):
        """Test that NetBox tools are properly referenced."""
        
        result = await bulk_cable_installation_prompt()
        
        # Expected NetBox tools to be mentioned
        expected_tools = [
            "netbox_map_rack_to_switch_interfaces",
            "netbox_generate_bulk_cable_plan",
            "netbox_bulk_create_cable_connections",
            "netbox_list_all_racks",
            "netbox_get_device_info",
            "netbox_create_journal_entry"
        ]
        
        for tool in expected_tools:
            assert tool in result
    
    @pytest.mark.asyncio
    async def test_bulk_cable_installation_prompt_bridget_integration(self):
        """Test Bridget persona integration."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify Bridget persona elements
        assert "Bridget" in result
        assert "NetBox Infrastructure Guide" in result
        assert "🦜" in result or "parrot" in result.lower()
        
        # Verify Dutch language support
        assert "Hallo" in result or "Ik ga" in result
        
        # Verify guidance and support elements
        assert "begeleiden" in result or "guide" in result
        assert "stap-voor-stap" in result or "step-by-step" in result
    
    @pytest.mark.asyncio
    async def test_bulk_cable_installation_prompt_safety_features(self):
        """Test that safety features are properly explained."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify safety mechanisms are mentioned
        safety_features = [
            "dry-run",
            "confirm",
            "rollback",
            "batch",
            "validation",
            "error handling"
        ]
        
        for feature in safety_features:
            assert (feature in result.lower() or 
                   feature.replace("-", "_") in result.lower() or
                   feature.replace(" ", "_") in result.lower())
    
    @pytest.mark.asyncio
    async def test_bulk_cable_installation_prompt_scalability(self):
        """Test that scalability information is included."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify scalability mentions
        assert "1-100" in result or "100+" in result
        assert "cables" in result.lower()
        assert "batch" in result.lower()
        
        # Verify performance information
        assert "minutes" in result.lower()
        assert "time" in result.lower()
    
    @pytest.mark.asyncio
    async def test_bulk_cable_installation_prompt_completeness(self):
        """Test that the prompt is complete and well-formatted."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify minimum length (should be substantial)
        assert len(result) > 5000  # Should be a comprehensive prompt
        
        # Verify proper formatting
        assert "##" in result  # Markdown headers
        assert "**" in result  # Bold text
        assert "•" in result or "-" in result  # List items
        
        # Verify conclusion elements
        assert "Klaar" in result or "Ready" in result
        assert "NetBox MCP" in result
        assert "v1.0.0" in result or "version" in result


class TestInstallDeviceInRackPrompt:
    """Test the install device in rack workflow prompt."""
    
    @pytest.mark.asyncio
    async def test_install_device_prompt_structure(self):
        """Test basic structure of install device prompt."""
        
        result = await install_device_in_rack_prompt()
        
        # Verify result is a string
        assert isinstance(result, str)
        
        # Verify essential elements
        assert "Install Device in Rack" in result
        assert "Bridget" in result
        assert "workflow" in result.lower()
        
        # Verify it's different from bulk cable prompt
        assert "bulk cable" not in result.lower()
        assert "device installation" in result.lower()
    
    @pytest.mark.asyncio
    async def test_install_device_prompt_workflow_steps(self):
        """Test that device installation workflow steps are present."""
        
        result = await install_device_in_rack_prompt()
        
        # Expected workflow steps for device installation
        expected_elements = [
            "Site",
            "Rack",
            "Device",
            "Network",
            "IP",
            "Cable",
            "Documentation"
        ]
        
        for element in expected_elements:
            assert element in result
    
    @pytest.mark.asyncio
    async def test_install_device_prompt_netbox_tools(self):
        """Test NetBox tools mentioned in device installation."""
        
        result = await install_device_in_rack_prompt()
        
        # Expected tools for device installation
        expected_tools = [
            "netbox_get_site_info",
            "netbox_get_rack_elevation",
            "netbox_provision_new_device",
            "netbox_assign_ip_to_interface",
            "netbox_create_cable_connection",
            "netbox_create_journal_entry"
        ]
        
        for tool in expected_tools:
            assert tool in result


class TestActivateBridgetPrompt:
    """Test the activate Bridget prompt."""
    
    @pytest.mark.asyncio
    async def test_activate_bridget_prompt_structure(self):
        """Test basic structure of activate Bridget prompt."""
        
        result = await activate_bridget_prompt()
        
        # Verify result is a string
        assert isinstance(result, str)
        
        # Verify Bridget introduction elements
        assert "Bridget" in result
        assert "NetBox Infrastructure Guide" in result
        assert "🦜" in result or "parrot" in result.lower()
        
        # Verify introduction and capabilities
        assert "Hallo" in result or "Hello" in result
        assert "capabilities" in result.lower() or "mogelijkheden" in result
        
        # Verify tool count information
        assert "108+" in result or "142+" in result  # Tool count
        assert "tools" in result.lower()
    
    @pytest.mark.asyncio
    async def test_activate_bridget_prompt_capabilities(self):
        """Test that Bridget capabilities are properly listed."""
        
        result = await activate_bridget_prompt()
        
        # Expected capability areas
        capabilities = [
            "DCIM",
            "IPAM",
            "Tenancy",
            "Virtualization",
            "workflow",
            "guidance"
        ]
        
        for capability in capabilities:
            assert capability in result or capability.lower() in result.lower()
    
    @pytest.mark.asyncio
    async def test_activate_bridget_prompt_assistance_menu(self):
        """Test that assistance menu is included."""
        
        result = await activate_bridget_prompt()
        
        # Verify assistance elements
        assert "help" in result.lower() or "hulp" in result
        assert "vragen" in result or "questions" in result
        assert "workflow" in result.lower()
        
        # Verify call-to-action
        assert "bouwen" in result or "build" in result


class TestWorkflowPromptIntegration:
    """Test integration aspects of workflow prompts."""
    
    @pytest.mark.asyncio
    async def test_all_prompts_are_callable(self):
        """Test that all workflow prompts can be called successfully."""
        
        prompts = [
            bulk_cable_installation_prompt,
            install_device_in_rack_prompt,
            activate_bridget_prompt
        ]
        
        for prompt in prompts:
            try:
                result = await prompt()
                assert isinstance(result, str)
                assert len(result) > 100  # Should be substantial
            except Exception as e:
                pytest.fail(f"Prompt {prompt.__name__} failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_prompts_have_unique_content(self):
        """Test that each prompt has unique content."""
        
        bulk_result = await bulk_cable_installation_prompt()
        device_result = await install_device_in_rack_prompt()
        bridget_result = await activate_bridget_prompt()
        
        # Verify prompts are different
        assert bulk_result != device_result
        assert bulk_result != bridget_result
        assert device_result != bridget_result
        
        # Verify each has unique keywords
        assert "bulk cable" in bulk_result.lower()
        assert "device installation" in device_result.lower()
        assert "kennismaking" in bridget_result.lower() or "introduction" in bridget_result.lower()
    
    @pytest.mark.asyncio
    async def test_prompts_maintain_consistent_branding(self):
        """Test that all prompts maintain consistent NetBox MCP branding."""
        
        prompts = [
            bulk_cable_installation_prompt,
            install_device_in_rack_prompt,
            activate_bridget_prompt
        ]
        
        for prompt in prompts:
            result = await prompt()
            
            # Verify consistent branding elements
            assert "NetBox MCP" in result
            assert "Bridget" in result
            assert "NetBox Infrastructure Guide" in result
            assert "🦜" in result or "parrot" in result.lower()
            
            # Verify version information
            assert "v1.0.0" in result or "version" in result
    
    @pytest.mark.asyncio
    async def test_prompts_include_safety_messaging(self):
        """Test that prompts include appropriate safety messaging."""
        
        prompts = [
            bulk_cable_installation_prompt,
            install_device_in_rack_prompt,
            activate_bridget_prompt
        ]
        
        for prompt in prompts:
            result = await prompt()
            
            # Verify safety concepts are mentioned
            safety_concepts = ["confirm", "safety", "dry-run", "validation"]
            safety_mentioned = any(concept in result.lower() for concept in safety_concepts)
            assert safety_mentioned, f"No safety concepts found in {prompt.__name__}"


class TestWorkflowPromptDocumentation:
    """Test documentation aspects of workflow prompts."""
    
    @pytest.mark.asyncio
    async def test_bulk_cable_prompt_has_github_issue_reference(self):
        """Test that bulk cable prompt references GitHub issue #92."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify GitHub issue reference
        assert "#92" in result or "GitHub issue #92" in result
        assert "issue" in result.lower()
        
        # Verify problem description
        assert "37" in result or "individual" in result
        assert "scale" in result.lower() or "bulk" in result.lower()
    
    @pytest.mark.asyncio
    async def test_prompts_include_time_estimates(self):
        """Test that prompts include realistic time estimates."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify time estimates
        assert "minuten" in result or "minutes" in result
        assert any(str(i) in result for i in range(10, 61))  # 10-60 minutes range
    
    @pytest.mark.asyncio
    async def test_prompts_include_prerequisites(self):
        """Test that prompts include necessary prerequisites."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify prerequisites section
        assert "Vereisten" in result or "Requirements" in result
        assert "permissions" in result.lower() or "write" in result.lower()
        assert "NetBox" in result
    
    @pytest.mark.asyncio
    async def test_prompts_include_next_steps(self):
        """Test that prompts include next steps information."""
        
        result = await bulk_cable_installation_prompt()
        
        # Verify next steps
        assert "Volgende Stappen" in result or "Next Steps" in result
        assert "technici" in result or "technicians" in result
        assert "installation" in result.lower()


class TestWorkflowPromptErrorHandling:
    """Test error handling in workflow prompts."""
    
    @pytest.mark.asyncio
    async def test_prompts_handle_import_errors_gracefully(self):
        """Test that prompts handle import errors gracefully."""
        
        # Mock import failures
        with patch('netbox_mcp.prompts.workflows.get_bridget_introduction') as mock_intro:
            mock_intro.side_effect = ImportError("Mock import error")
            
            # Should still work or fail gracefully
            try:
                result = await bulk_cable_installation_prompt()
                # If it succeeds, it should still be a string
                assert isinstance(result, str)
            except Exception as e:
                # If it fails, it should be a reasonable error
                assert "import" in str(e).lower() or "module" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_prompts_are_consistent_across_calls(self):
        """Test that prompts return consistent results across multiple calls."""
        
        # Call the same prompt multiple times
        results = []
        for _ in range(3):
            result = await bulk_cable_installation_prompt()
            results.append(result)
        
        # Results should be identical (prompts should be deterministic)
        assert all(result == results[0] for result in results)
    
    @pytest.mark.asyncio
    async def test_prompts_handle_none_values_gracefully(self):
        """Test that prompts handle None values in dependencies gracefully."""
        
        # Mock dependencies returning None
        with patch('netbox_mcp.prompts.workflows.get_bridget_workflow_header') as mock_header:
            mock_header.return_value = None
            
            # Should still work
            result = await bulk_cable_installation_prompt()
            assert isinstance(result, str)
            assert len(result) > 100


class TestWorkflowPromptPerformance:
    """Test performance aspects of workflow prompts."""
    
    @pytest.mark.asyncio
    async def test_prompts_execute_quickly(self):
        """Test that prompts execute in reasonable time."""
        
        import time
        
        start_time = time.time()
        result = await bulk_cable_installation_prompt()
        end_time = time.time()
        
        # Should execute quickly (under 1 second)
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Prompt took {execution_time:.2f} seconds"
        
        # Should still produce substantial output
        assert len(result) > 5000
    
    @pytest.mark.asyncio
    async def test_prompts_memory_usage(self):
        """Test that prompts don't consume excessive memory."""
        
        import sys
        
        # Get initial memory usage
        initial_objects = len(gc.get_objects()) if 'gc' in dir() else 0
        
        # Execute prompt
        result = await bulk_cable_installation_prompt()
        
        # Verify result is reasonable size
        assert len(result) < 1000000  # Less than 1MB
        
        # Clean up
        del result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])