"""
Adaptive State Machine with Sub-Agent Integration - Phase 7 Implementation

This module implements the enhanced adaptive workflow that integrates all
intelligent sub-agents for LLM-driven recovery without hard-coded logic.

The workflow includes:
1. Enhanced query understanding with Query Intelligence Agent
2. Adaptive execution with multi-step recovery using all sub-agents
3. Recovery-aware response generation with explanations
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import traceback

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Import existing intelligent components
from .intelligent_tool_selector import select_tool, ToolSelection
from .tool_aware_parameter_extractor import extract_parameters, ParameterExtractionResult
from .coordination import ToolRequest, ToolResult
from .real_api_handler import execute_real_netbox_tool

# Import new intelligent sub-agents
from ..agents.error_intelligence_agent import ErrorIntelligenceAgent
from ..agents.entity_discovery_agent import EntityDiscoveryAgent
from ..agents.parameter_adaptation_agent import ParameterAdaptationAgent
from ..agents.recovery_orchestration_agent import RecoveryOrchestrationAgent
from ..agents.query_intelligence_agent import QueryIntelligenceAgent
from ..agents.response_generation import ResponseGenerationAgent

# Import base state from existing state machine
from .state_machine import IntelligentOrchestrationState


class AdaptiveOrchestrationState(IntelligentOrchestrationState):
    """
    Extended state for adaptive orchestration with recovery intelligence.
    
    Adds fields for tracking recovery attempts and multi-agent collaboration.
    """
    # Query intelligence analysis
    query_intent_analysis: Optional[Dict[str, Any]]
    
    # Recovery tracking
    recovery_attempted: bool
    recovery_plan: Optional[Dict[str, Any]]
    recovery_execution_log: Optional[List[Dict[str, Any]]]
    recovery_successful: bool
    
    # Entity discovery and adaptation
    discovered_entities: Optional[Dict[str, Any]]
    adapted_parameters: Optional[Dict[str, Any]]
    
    # Multi-agent collaboration
    agent_interactions: List[Dict[str, Any]]


async def enhanced_intelligent_tool_selection(state: AdaptiveOrchestrationState) -> AdaptiveOrchestrationState:
    """
    Enhanced tool selection with Query Intelligence Agent integration.
    
    Provides deeper query understanding before tool selection.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Enhanced tool selection with query intelligence for: {state['user_query'][:100]}...")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Deep query analysis with Query Intelligence Agent
        query_agent = QueryIntelligenceAgent()
        await query_agent.initialize()
        
        query_analysis_result = await query_agent.analyze_query_intent(
            state["user_query"],
            {"session_id": state["session_id"]}
        )
        
        if query_analysis_result["success"]:
            state["query_intent_analysis"] = query_analysis_result["analysis"]
            logger.info(f"Query intelligence - Domain: {query_analysis_result['analysis'].get('primary_domain')}, "
                       f"Complexity: {query_analysis_result['analysis'].get('complexity')}")
        
        # Step 2: Use existing Phase 1 IntelligentToolSelector with enhanced context
        tool_selection = await select_tool(state["user_query"])
        
        if not tool_selection or not tool_selection.primary_tool:
            logger.error("Enhanced tool selection failed to select a tool")
            state["error_state"] = {
                "stage": "enhanced_tool_selection",
                "error": "No suitable tool found",
                "timestamp": datetime.now().isoformat()
            }
            return state
        
        logger.info(f"Selected tool: {tool_selection.primary_tool} (confidence: {tool_selection.confidence:.2f})")
        state["tool_selection"] = tool_selection
        
        # Step 3: Use Phase 2 ToolAwareParameterExtractor
        parameter_result = await extract_parameters(
            state["user_query"],
            tool_selection.primary_tool
        )
        
        if not parameter_result:
            logger.error("Parameter extraction failed")
            state["error_state"] = {
                "stage": "parameter_extraction",
                "error": "Parameter extraction failed",
                "timestamp": datetime.now().isoformat()
            }
            return state
        
        state["parameter_extraction"] = parameter_result
        state["final_parameters"] = {**tool_selection.parameters, **parameter_result.parameters}
        
        # Track agent interaction
        if not state.get("agent_interactions"):
            state["agent_interactions"] = []
        
        state["agent_interactions"].append({
            "agent": "QueryIntelligenceAgent",
            "action": "analyze_query_intent",
            "timestamp": datetime.now().isoformat(),
            "result": "success" if query_analysis_result["success"] else "failed"
        })
        
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Enhanced tool selection completed in {execution_time:.2f}s")
        
        return state
        
    except Exception as e:
        logger.error(f"Enhanced tool selection failed: {e}", exc_info=True)
        state["error_state"] = {
            "stage": "enhanced_tool_selection",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        return state


async def adaptive_execution_with_recovery(state: AdaptiveOrchestrationState) -> AdaptiveOrchestrationState:
    """
    Adaptive execution with intelligent multi-step recovery using sub-agents.
    
    This is the core of Phase 7 - integrates all sub-agents for recovery.
    """
    logger = logging.getLogger(__name__)
    logger.info("Adaptive execution with intelligent recovery...")
    
    start_time = datetime.now()
    
    try:
        # Check prerequisites
        if not state.get("tool_selection") or not state.get("final_parameters"):
            logger.error("Missing tool selection or parameters")
            state["execution_successful"] = False
            return state
        
        tool_selection = state["tool_selection"]
        parameters = state["final_parameters"]
        
        # Initial execution attempt
        logger.info(f"Attempting primary execution: {tool_selection.primary_tool} with {parameters}")
        
        tool_request = ToolRequest(
            tool_name=tool_selection.primary_tool,
            params=parameters,
            priority=1,
            max_retries=2
        )
        
        initial_result = await _execute_with_recovery_aware_retry(tool_request)
        
        if initial_result.success:
            # Success on first try
            logger.info("Primary execution succeeded without recovery")
            state["tool_results"] = [initial_result]
            state["execution_successful"] = True
            state["recovery_attempted"] = False
            return state
        
        # Primary execution failed - initiate intelligent recovery
        logger.info("Primary execution failed, initiating intelligent recovery...")
        
        # Initialize sub-agents for recovery
        error_agent = ErrorIntelligenceAgent()
        discovery_agent = EntityDiscoveryAgent()
        adaptation_agent = ParameterAdaptationAgent()
        recovery_agent = RecoveryOrchestrationAgent()
        
        await error_agent.initialize()
        await discovery_agent.initialize()
        await adaptation_agent.initialize()
        await recovery_agent.initialize()
        
        # Step 1: Analyze error with Error Intelligence Agent
        error_analysis_result = await error_agent.analyze_error(
            {"error": initial_result.error, "result": initial_result.result},
            {
                "user_query": state["user_query"],
                "tool_name": tool_selection.primary_tool,
                "parameters": parameters
            }
        )
        
        if not error_analysis_result["success"] or not error_analysis_result["analysis"]["recoverable"]:
            logger.warning("Error deemed non-recoverable by Error Intelligence Agent")
            state["tool_results"] = [initial_result]
            state["execution_successful"] = False
            state["recovery_attempted"] = True
            state["recovery_successful"] = False
            state["execution_errors"] = [initial_result.error or "Execution failed"]
            return state
        
        error_analysis = error_analysis_result["analysis"]
        logger.info(f"Error analysis - Type: {error_analysis['error_type']}, "
                   f"Recoverable: {error_analysis['recoverable']}")
        
        # Step 2: Discover entity context with Entity Discovery Agent
        discovery_result = await discovery_agent.discover_entity_context(
            state["user_query"],
            error_analysis,
            _get_available_netbox_tools()
        )
        
        discovered_entities = discovery_result["context"]["discoveries"] if discovery_result["success"] else {}
        state["discovered_entities"] = discovered_entities
        
        logger.info(f"Entity discovery found {len(discovered_entities)} entity mappings")
        
        # Step 3: Adapt parameters with Parameter Adaptation Agent
        adaptation_result = await adaptation_agent.adapt_parameters(
            parameters,
            discovered_entities,
            error_analysis,
            _get_tool_schema(tool_selection.primary_tool)
        )
        
        if adaptation_result["success"]:
            adapted_params = adaptation_result["adaptation"]["adapted_parameters"]
            state["adapted_parameters"] = adapted_params
            logger.info(f"Parameters adapted: {len(adaptation_result['adaptation']['transformations_applied'])} transformations")
        else:
            adapted_params = parameters
        
        # Step 4: Plan and execute recovery with Recovery Orchestration Agent
        recovery_plan_result = await recovery_agent.plan_recovery(
            error_analysis,
            {"discoveries": discovered_entities},
            _get_available_netbox_tools()
        )
        
        if not recovery_plan_result["success"]:
            logger.error("Recovery plan generation failed")
            state["tool_results"] = [initial_result]
            state["execution_successful"] = False
            state["recovery_attempted"] = True
            state["recovery_successful"] = False
            return state
        
        recovery_plan = recovery_plan_result["plan"]
        state["recovery_plan"] = recovery_plan
        
        logger.info(f"Recovery plan created - Strategy: {recovery_plan['strategy_type']}, "
                   f"Steps: {len(recovery_plan['recovery_steps'])}")
        
        # Execute recovery plan
        recovery_execution = await recovery_agent.execute_recovery_plan(
            recovery_plan,
            {
                "adapted_parameters": adapted_params,
                "original_tool": tool_selection.primary_tool,
                "discovered_entities": discovered_entities
            }
        )
        
        state["recovery_execution_log"] = recovery_execution.get("execution_log", [])
        state["recovery_successful"] = recovery_execution["success"]
        
        if recovery_execution["success"]:
            logger.info("Recovery successful!")
            # Create successful tool result from recovery
            recovery_result = ToolResult(
                tool_name=tool_selection.primary_tool,
                params=adapted_params,
                success=True,
                result=recovery_execution.get("final_result"),
                execution_time=(datetime.now() - start_time).total_seconds(),
                error=None,
                cached=False
            )
            state["tool_results"] = [recovery_result]
            state["execution_successful"] = True
        else:
            logger.warning("Recovery failed after all attempts")
            state["tool_results"] = [initial_result]
            state["execution_successful"] = False
            state["execution_errors"] = [
                initial_result.error or "Primary execution failed",
                "Recovery attempts unsuccessful"
            ]
        
        state["recovery_attempted"] = True
        
        # Track agent interactions
        state["agent_interactions"].extend([
            {"agent": "ErrorIntelligenceAgent", "action": "analyze_error", "timestamp": datetime.now().isoformat()},
            {"agent": "EntityDiscoveryAgent", "action": "discover_entities", "timestamp": datetime.now().isoformat()},
            {"agent": "ParameterAdaptationAgent", "action": "adapt_parameters", "timestamp": datetime.now().isoformat()},
            {"agent": "RecoveryOrchestrationAgent", "action": "execute_recovery", "timestamp": datetime.now().isoformat()}
        ])
        
        # Clean up agents
        await error_agent.cleanup()
        await discovery_agent.cleanup()
        await adaptation_agent.cleanup()
        await recovery_agent.cleanup()
        
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Adaptive execution completed in {execution_time:.2f}s - "
                   f"Success: {state['execution_successful']}, Recovery: {state.get('recovery_attempted', False)}")
        
        return state
        
    except Exception as e:
        logger.error(f"Adaptive execution failed: {e}", exc_info=True)
        state["error_state"] = {
            "stage": "adaptive_execution",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        state["execution_successful"] = False
        state["execution_errors"] = [str(e)]
        return state


async def recovery_aware_response(state: AdaptiveOrchestrationState) -> AdaptiveOrchestrationState:
    """
    Generate response that explains recovery process and results.
    
    Enhanced response generation that provides transparency about recovery attempts.
    """
    logger = logging.getLogger(__name__)
    logger.info("Generating recovery-aware response...")
    
    start_time = datetime.now()
    
    try:
        # Prepare response context with recovery details
        execution_successful = state.get("execution_successful", False)
        recovery_attempted = state.get("recovery_attempted", False)
        recovery_successful = state.get("recovery_successful", False)
        tool_results = state.get("tool_results", [])
        
        # Initialize Response Generation Agent
        response_agent = ResponseGenerationAgent()
        await response_agent.initialize()
        
        # Build enhanced response context
        response_context = {
            "original_query": state["user_query"],
            "execution_successful": execution_successful,
            "tool_results": [_serialize_tool_result(r) for r in tool_results],
            "recovery_attempted": recovery_attempted,
            "recovery_successful": recovery_successful
        }
        
        # Add recovery details if recovery was attempted
        if recovery_attempted:
            response_context["recovery_details"] = {
                "recovery_plan": state.get("recovery_plan"),
                "recovery_log": state.get("recovery_execution_log", []),
                "discovered_entities": state.get("discovered_entities"),
                "adapted_parameters": state.get("adapted_parameters"),
                "recovery_summary": _generate_recovery_summary(state)
            }
        
        # Add query intelligence insights
        if state.get("query_intent_analysis"):
            response_context["query_intelligence"] = state["query_intent_analysis"]
        
        # Generate intelligent response
        response_result = await response_agent.process_request({
            "type": "format_response",
            "context": response_context,
            "response_type": "recovery_aware" if recovery_attempted else "standard",
            "correlation_id": state["correlation_id"]
        })
        
        if response_result and response_result.get("success"):
            # Enhance response with recovery explanation if needed
            response_text = response_result["response"]
            
            if recovery_attempted:
                recovery_explanation = _create_recovery_explanation(state)
                response_text = f"{response_text}\n\n{recovery_explanation}"
            
            state["natural_language_response"] = response_text
            state["user_options"] = _generate_adaptive_user_options(state)
            response_generated = True
            logger.info("Recovery-aware response generated successfully")
        else:
            # Fallback response
            state["natural_language_response"] = _create_adaptive_fallback_response(state)
            state["user_options"] = ["Try a simpler query", "Check NetBox status", "Contact support"]
            response_generated = False
        
        state["workflow_complete"] = True
        
        # Update performance metrics
        response_time = (datetime.now() - start_time).total_seconds()
        if state.get("execution_metrics"):
            state["execution_metrics"]["response_generation_time"] = response_time
            state["execution_metrics"]["recovery_attempted"] = recovery_attempted
            state["execution_metrics"]["recovery_successful"] = recovery_successful
        
        logger.info(f"Recovery-aware response completed in {response_time:.2f}s")
        
        return state
        
    except Exception as e:
        logger.error(f"Recovery-aware response generation failed: {e}", exc_info=True)
        
        # Emergency fallback
        state["natural_language_response"] = (
            f"I encountered an issue processing your query. "
            f"{'Recovery was attempted but unsuccessful. ' if state.get('recovery_attempted') else ''}"
            "Please try rephrasing your query or contact support."
        )
        state["user_options"] = ["Try again", "Get help"]
        state["workflow_complete"] = True
        
        return state


# Helper functions

async def _execute_with_recovery_aware_retry(tool_request: ToolRequest) -> ToolResult:
    """Execute tool with recovery-aware retry logic"""
    logger = logging.getLogger(__name__)
    
    for attempt in range(tool_request.max_retries + 1):
        try:
            result = await execute_real_netbox_tool(tool_request)
            
            if result.success:
                return result
            else:
                logger.warning(f"Tool {tool_request.tool_name} failed on attempt {attempt + 1}: {result.error}")
                
                if attempt < tool_request.max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                
        except Exception as e:
            logger.error(f"Exception executing {tool_request.tool_name}: {e}")
            
            if attempt == tool_request.max_retries:
                return ToolResult(
                    tool_name=tool_request.tool_name,
                    params=tool_request.params,
                    success=False,
                    result=None,
                    execution_time=0.0,
                    error=str(e),
                    cached=False
                )
            
            await asyncio.sleep(0.5 * (attempt + 1))
    
    return ToolResult(
        tool_name=tool_request.tool_name,
        params=tool_request.params,
        success=False,
        result=None,
        execution_time=0.0,
        error="All retry attempts failed",
        cached=False
    )


def _get_available_netbox_tools() -> List[str]:
    """Get list of available NetBox tools"""
    # This would be populated from tool registry in production
    return [
        "netbox_list_all_sites",
        "netbox_list_all_racks",
        "netbox_get_rack_elevation",
        "netbox_get_rack_inventory",
        "netbox_list_all_devices",
        "netbox_get_device_info",
        "netbox_get_device_interfaces",
        "netbox_list_all_clusters",
        "netbox_list_all_virtual_machines",
        "netbox_get_ip_usage",
        "netbox_list_all_prefixes"
    ]


def _get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """Get schema for a specific tool"""
    # Simplified schema - in production would come from tool registry
    schemas = {
        "netbox_get_rack_elevation": {
            "required_parameters": ["rack_name"],
            "optional_parameters": ["site"]
        },
        "netbox_get_rack_inventory": {
            "required_parameters": ["site_name", "rack_name"],
            "optional_parameters": ["include_detailed"]
        },
        "netbox_get_device_info": {
            "required_parameters": ["device_name"],
            "optional_parameters": ["site"]
        }
    }
    return schemas.get(tool_name, {})


def _serialize_tool_result(tool_result: ToolResult) -> Dict[str, Any]:
    """Serialize ToolResult for response context"""
    return {
        "tool_name": tool_result.tool_name,
        "params": tool_result.params,
        "success": tool_result.success,
        "result": tool_result.result,
        "execution_time": tool_result.execution_time,
        "error": tool_result.error,
        "cached": tool_result.cached
    }


def _generate_recovery_summary(state: AdaptiveOrchestrationState) -> str:
    """Generate a summary of recovery attempts"""
    if not state.get("recovery_attempted"):
        return "No recovery attempted"
    
    summary_parts = []
    
    if state.get("discovered_entities"):
        summary_parts.append(f"Discovered {len(state['discovered_entities'])} entity mappings")
    
    if state.get("adapted_parameters"):
        summary_parts.append("Parameters were adapted based on discoveries")
    
    if state.get("recovery_execution_log"):
        log = state["recovery_execution_log"]
        successful_steps = sum(1 for step in log if step.get("success"))
        summary_parts.append(f"Executed {len(log)} recovery steps ({successful_steps} successful)")
    
    if state.get("recovery_successful"):
        summary_parts.append("Recovery was successful")
    else:
        summary_parts.append("Recovery was attempted but unsuccessful")
    
    return " | ".join(summary_parts)


def _create_recovery_explanation(state: AdaptiveOrchestrationState) -> str:
    """Create user-friendly explanation of recovery process"""
    if not state.get("recovery_attempted"):
        return ""
    
    explanation_parts = ["🔄 Recovery Process:"]
    
    if state.get("discovered_entities"):
        explanation_parts.append("• Explored NetBox to understand entity relationships")
    
    if state.get("adapted_parameters"):
        explanation_parts.append("• Corrected parameters based on discoveries")
    
    if state.get("recovery_plan"):
        plan = state["recovery_plan"]
        explanation_parts.append(f"• Executed {plan.get('strategy_type', 'adaptive')} recovery strategy")
    
    if state.get("recovery_successful"):
        explanation_parts.append("• ✅ Recovery successful - retrieved requested data")
    else:
        explanation_parts.append("• ⚠️ Recovery attempted but some issues remain")
    
    return "\n".join(explanation_parts)


def _create_adaptive_fallback_response(state: AdaptiveOrchestrationState) -> str:
    """Create adaptive fallback response based on state"""
    if state.get("recovery_attempted"):
        if state.get("recovery_successful"):
            return "Recovery was successful. The requested information has been retrieved."
        else:
            return ("I attempted to recover from the initial error by exploring NetBox and adapting parameters, "
                   "but was unable to complete the request. The issue may require manual intervention.")
    else:
        return "I encountered an issue processing your request. Please verify the entity names and try again."


def _generate_adaptive_user_options(state: AdaptiveOrchestrationState) -> List[str]:
    """Generate context-aware user options"""
    options = []
    
    if state.get("execution_successful"):
        options = [
            "Ask a follow-up question",
            "Get more details",
            "Explore related resources"
        ]
    elif state.get("recovery_attempted"):
        options = [
            "Try with different entity names",
            "List available entities first",
            "Simplify the query"
        ]
    else:
        options = [
            "Check entity names",
            "List available options",
            "Try a simpler query"
        ]
    
    return options


def create_adaptive_orchestration_graph() -> StateGraph:
    """
    Create the enhanced adaptive orchestration graph with sub-agent integration.
    
    This is the Phase 7 workflow with intelligent recovery capabilities.
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating adaptive orchestration state machine with sub-agents...")
    
    # Initialize StateGraph with AdaptiveOrchestrationState
    workflow = StateGraph(AdaptiveOrchestrationState)
    
    # Add the enhanced nodes
    workflow.add_node("enhanced_tool_selection", enhanced_intelligent_tool_selection)
    workflow.add_node("adaptive_execution", adaptive_execution_with_recovery)
    workflow.add_node("recovery_aware_response", recovery_aware_response)
    
    # Define the workflow
    workflow.add_edge(START, "enhanced_tool_selection")
    workflow.add_edge("enhanced_tool_selection", "adaptive_execution")
    workflow.add_edge("adaptive_execution", "recovery_aware_response")
    workflow.add_edge("recovery_aware_response", END)
    
    # Compile with memory checkpointing
    memory_saver = MemorySaver()
    compiled_graph = workflow.compile(checkpointer=memory_saver)
    
    logger.info("Adaptive orchestration state machine compiled successfully")
    return compiled_graph


# Public interface

async def execute_adaptive_workflow(
    user_query: str,
    session_id: str,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute the adaptive workflow with intelligent recovery capabilities.
    
    This is the main entry point for Phase 7 adaptive orchestration.
    """
    logger = logging.getLogger(__name__)
    
    if not correlation_id:
        correlation_id = f"adaptive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Executing adaptive workflow for query: {user_query[:100]}...")
    
    try:
        # Create the adaptive orchestration graph
        workflow_graph = create_adaptive_orchestration_graph()
        
        # Create initial state
        initial_state: AdaptiveOrchestrationState = {
            # Base state fields
            "user_query": user_query,
            "session_id": session_id,
            "correlation_id": correlation_id,
            "tool_selection": None,
            "tool_selection_confidence": None,
            "parameter_extraction": None,
            "final_parameters": None,
            "tool_results": [],
            "execution_successful": False,
            "execution_errors": [],
            "natural_language_response": None,
            "user_options": None,
            "workflow_complete": False,
            "error_state": None,
            "execution_metrics": None,
            
            # Adaptive state fields
            "query_intent_analysis": None,
            "recovery_attempted": False,
            "recovery_plan": None,
            "recovery_execution_log": None,
            "recovery_successful": False,
            "discovered_entities": None,
            "adapted_parameters": None,
            "agent_interactions": []
        }
        
        # Execute workflow
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": correlation_id
            }
        }
        
        workflow_result = await workflow_graph.ainvoke(initial_state, config=config)
        
        # Extract results
        result = {
            "success": workflow_result.get("execution_successful", False),
            "response": workflow_result.get("natural_language_response", "No response generated"),
            "user_options": workflow_result.get("user_options", []),
            "execution_metrics": workflow_result.get("execution_metrics", {}),
            "tool_results": [_serialize_tool_result(r) for r in workflow_result.get("tool_results", [])],
            "workflow_complete": workflow_result.get("workflow_complete", False),
            "recovery_attempted": workflow_result.get("recovery_attempted", False),
            "recovery_successful": workflow_result.get("recovery_successful", False),
            "agent_interactions": workflow_result.get("agent_interactions", []),
            "error_state": workflow_result.get("error_state"),
            "session_id": session_id,
            "correlation_id": correlation_id
        }
        
        logger.info(f"Adaptive workflow completed - Success: {result['success']}, "
                   f"Recovery: {result['recovery_attempted']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Adaptive workflow execution failed: {e}", exc_info=True)
        
        return {
            "success": False,
            "response": f"Workflow execution failed: {str(e)}",
            "user_options": ["Try a simpler query", "Check system status"],
            "execution_metrics": {"error": True, "error_message": str(e)},
            "tool_results": [],
            "workflow_complete": True,
            "recovery_attempted": False,
            "recovery_successful": False,
            "agent_interactions": [],
            "error_state": {
                "stage": "workflow_execution",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            "session_id": session_id,
            "correlation_id": correlation_id
        }