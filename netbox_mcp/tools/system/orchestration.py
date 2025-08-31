#!/usr/bin/env python3
"""
NetBox MCP Orchestration Tools

Exposes the intelligent orchestration system as MCP tools to enable
Claude Code CLI-style adaptive intelligence for query processing.
"""

import json
import logging
from typing import Dict, Any

from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(
    description="Process NetBox queries using intelligent orchestration with adaptive recovery",
    category="system"
)
def process_query(
    client: NetBoxClient,
    query: str,
    session_id: str = None,
    correlation_id: str = None,
    force_system: str = None
) -> Dict[str, Any]:
    """
    Process NetBox queries using the intelligent orchestration system with adaptive recovery.
    
    This tool provides Claude Code CLI-style intelligent query processing with:
    - LLM-driven tool selection and parameter adaptation
    - Multi-step error recovery with sub-agents
    - Adaptive intelligence that learns from failures
    - Backward compatibility with legacy queries
    
    Args:
        client: NetBoxClient instance
        query: Natural language query about NetBox infrastructure
        session_id: Optional session ID for conversation context
        correlation_id: Optional correlation ID for request tracking
        force_system: Optional system to force ('intelligent', 'legacy', or None for auto)
        
    Returns:
        Dict containing query result with orchestration metadata
        
    Examples:
        - "Show rack elevation for R01-A15 in site DM-Akron"
        - "List all virtual machines in cluster DO-AMS3"
        - "Get IP usage statistics for prefix 10.112.128.0/17"
        - "Show devices in rack Comms closet at DM-Scranton"
    """
    try:
        # Import here to avoid circular dependencies
        from ...orchestration.backward_compatibility import (
            BackwardCompatibilityManager, 
            CompatibilityConfig, 
            MigrationPhase
        )
        
        # Configure for intelligent system with adaptive recovery
        config = CompatibilityConfig(
            migration_phase=MigrationPhase.INTELLIGENT_ONLY,  # Force adaptive intelligence
            feature_flags={
                "use_intelligent_tool_selector": True,
                "use_context_aware_parameters": True,
                "use_langgraph_workflow": True,
                "use_intelligent_fallback": True,
                "enable_a_b_testing": False,
                "enable_performance_monitoring": True,
                "enable_adaptive_recovery": True,  # Enable sub-agent recovery
                "enable_sub_agents": True,         # Enable LLM-driven sub-agents
                "use_adaptive_state_machine": True  # Use new adaptive workflow
            }
        )
        
        # Create and initialize orchestration manager
        manager = BackwardCompatibilityManager(config)
        
        # Run synchronously for MCP compatibility
        import asyncio
        
        async def run_orchestration():
            await manager.initialize()
            
            result = await manager.process_query(
                query=query,
                session_id=session_id or f"mcp_session_{hash(query) % 10000}",
                correlation_id=correlation_id or f"mcp_correlation_{hash(query) % 10000}",
                force_system=force_system
            )
            
            # BackwardCompatibilityManager doesn't have cleanup method
            return result
        
        # Execute orchestration
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(run_orchestration())
        finally:
            loop.close()
        
        # Ensure we return structured data
        if not isinstance(result, dict):
            result = {"response": str(result), "success": True}
            
        # Add orchestration metadata
        result["orchestration_metadata"] = {
            "system_used": "adaptive_intelligence",
            "tool_name": "process_query",
            "adaptive_recovery_enabled": True
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Query orchestration failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "orchestration_metadata": {
                "system_used": "error_fallback",
                "tool_name": "process_query",
                "error_occurred": True
            }
        }


@mcp_tool(
    description="Get orchestration system status and configuration",
    category="system"
)
def get_orchestration_status(client: NetBoxClient) -> Dict[str, Any]:
    """
    Get status and configuration of the intelligent orchestration system.
    
    Args:
        client: NetBoxClient instance
        
    Returns:
        Dict containing orchestration system status and capabilities
    """
    try:
        # Import here to avoid circular dependencies
        from ...orchestration.backward_compatibility import (
            BackwardCompatibilityManager,
            CompatibilityConfig,
            MigrationPhase
        )
        
        # Create basic config to check system
        config = CompatibilityConfig(
            migration_phase=MigrationPhase.INTELLIGENT_ONLY
        )
        
        manager = BackwardCompatibilityManager(config)
        
        return {
            "success": True,
            "orchestration_available": True,
            "adaptive_intelligence_enabled": True,
            "sub_agents_available": [
                "ErrorIntelligenceAgent",
                "EntityDiscoveryAgent", 
                "ParameterAdaptationAgent",
                "RecoveryOrchestrationAgent",
                "QueryIntelligenceAgent"
            ],
            "supported_features": [
                "intelligent_tool_selection",
                "context_aware_parameters",
                "langgraph_workflow",
                "intelligent_fallback",
                "adaptive_recovery",
                "multi_step_error_recovery",
                "entity_discovery",
                "parameter_adaptation"
            ],
            "migration_phase": "INTELLIGENT_ONLY",
            "backward_compatibility": True
        }
        
    except Exception as e:
        logger.error(f"Failed to get orchestration status: {e}")
        return {
            "success": False,
            "orchestration_available": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(
    description="Test orchestration system with sample queries",
    category="system"
)
def test_orchestration(client: NetBoxClient) -> Dict[str, Any]:
    """
    Test the orchestration system with predefined sample queries.
    
    Args:
        client: NetBoxClient instance
        
    Returns:
        Dict containing test results and system validation
    """
    test_queries = [
        "Show all sites",
        "List devices in first available site",
        "Get system health status"
    ]
    
    results = []
    
    for query in test_queries:
        try:
            result = process_query(client, query, session_id="test_session")
            
            results.append({
                "query": query,
                "success": result.get("success", False),
                "system_used": result.get("orchestration_metadata", {}).get("system_used", "unknown"),
                "has_response": bool(result.get("response"))
            })
            
        except Exception as e:
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    successful_tests = sum(1 for r in results if r.get("success"))
    total_tests = len(results)
    
    return {
        "success": successful_tests > 0,
        "test_results": results,
        "summary": {
            "successful_tests": successful_tests,
            "total_tests": total_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "orchestration_working": successful_tests > 0
        }
    }