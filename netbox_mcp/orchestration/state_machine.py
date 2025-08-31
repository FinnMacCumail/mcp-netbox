"""
Simplified 3-Node LangGraph Orchestration for NetBox MCP Phase 3

This module implements a simplified intelligent workflow that replaces the complex
5-node orchestration with 3 intelligent nodes that embed intelligence at each step:
1. intelligent_tool_selection - Integrates Phase 1 IntelligentToolSelector + Phase 2 ToolAwareParameterExtractor
2. smart_execution - Intelligent execution with built-in error handling
3. adaptive_response - LLM-generated response with natural fallback logic

Key improvements:
- Embeds intelligence in each node instead of scattered across multiple nodes
- Integrates Phase 1 and Phase 2 components seamlessly
- Simplifies state management to essential workflow data only
- Eliminates rigid routing functions and over-engineering
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
import traceback

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Import Phase 1 and Phase 2 intelligent components
from .intelligent_tool_selector import select_tool, ToolSelection
from .tool_aware_parameter_extractor import extract_parameters, ParameterExtractionResult
from .coordination import ToolRequest, ToolResult
from .real_api_handler import execute_real_netbox_tool
from ..agents.response_generation import ResponseGenerationAgent


class IntelligentOrchestrationState(TypedDict):
    """
    Simplified state for intelligent 3-node workflow
    
    Focuses on essential workflow data instead of complex coordination metadata.
    """
    # Core workflow data
    user_query: str
    session_id: str
    correlation_id: str
    
    # Tool selection results (Phase 1 integration)
    tool_selection: Optional[ToolSelection]
    tool_selection_confidence: Optional[float]
    
    # Parameter extraction results (Phase 2 integration)
    parameter_extraction: Optional[ParameterExtractionResult]
    final_parameters: Optional[Dict[str, Any]]
    
    # Execution results
    tool_results: List[ToolResult]
    execution_successful: bool
    execution_errors: List[str]
    
    # Response and completion
    natural_language_response: Optional[str]
    user_options: Optional[List[str]]
    workflow_complete: bool
    
    # Simple error tracking
    error_state: Optional[Dict[str, Any]]
    
    # Performance tracking
    execution_metrics: Optional[Dict[str, Any]]


async def intelligent_tool_selection(state: IntelligentOrchestrationState) -> IntelligentOrchestrationState:
    """
    Node 1: Intelligent Tool Selection
    
    Integrates Phase 1 IntelligentToolSelector and Phase 2 ToolAwareParameterExtractor
    to select the optimal NetBox tool and extract context-preserving parameters.
    
    Embeds intelligence that was previously scattered across classification and planning.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Intelligent tool selection for query: {state['user_query'][:100]}...")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Use Phase 1 IntelligentToolSelector
        logger.info("Using Phase 1 IntelligentToolSelector for semantic tool selection...")
        tool_selection = await select_tool(state["user_query"])
        
        if not tool_selection or not tool_selection.primary_tool:
            logger.error("IntelligentToolSelector failed to select a tool")
            state["error_state"] = {
                "stage": "tool_selection",
                "error": "No suitable tool found for query",
                "timestamp": datetime.now().isoformat()
            }
            return state
        
        logger.info(f"Selected tool: {tool_selection.primary_tool} (confidence: {tool_selection.confidence:.2f})")
        state["tool_selection"] = tool_selection
        state["tool_selection_confidence"] = tool_selection.confidence
        
        # Step 2: Use Phase 2 ToolAwareParameterExtractor for context-preserving parameters
        logger.info("Using Phase 2 ToolAwareParameterExtractor for context-preserving parameter extraction...")
        parameter_result = await extract_parameters(
            state["user_query"], 
            tool_selection.primary_tool
        )
        
        if not parameter_result:
            logger.error("ToolAwareParameterExtractor failed")
            state["error_state"] = {
                "stage": "parameter_extraction",
                "error": "Parameter extraction failed",
                "timestamp": datetime.now().isoformat()
            }
            return state
        
        logger.info(f"Parameter extraction: method={parameter_result.extraction_method}, "
                   f"confidence={parameter_result.confidence:.2f}, "
                   f"compound_entities={len(parameter_result.compound_entities)}")
        
        state["parameter_extraction"] = parameter_result
        
        # Step 3: Merge parameters from both components intelligently
        final_parameters = {}
        # Tool selector parameters first (from LLM intelligence)
        final_parameters.update(tool_selection.parameters)
        # Parameter extractor parameters override (more detailed context-aware extraction)  
        final_parameters.update(parameter_result.parameters)
        
        state["final_parameters"] = final_parameters
        
        # Calculate combined confidence
        combined_confidence = (tool_selection.confidence * 0.6 + parameter_result.confidence * 0.4)
        state["tool_selection_confidence"] = combined_confidence
        
        # Record performance metrics
        execution_time = (datetime.now() - start_time).total_seconds()
        state["execution_metrics"] = {
            "tool_selection_time": execution_time,
            "tool_selected": tool_selection.primary_tool,
            "tool_confidence": tool_selection.confidence,
            "parameter_confidence": parameter_result.confidence,
            "combined_confidence": combined_confidence,
            "compound_entities_found": len(parameter_result.compound_entities),
            "relationships_preserved": len(parameter_result.preserved_relationships),
            "execution_strategy": tool_selection.execution_strategy
        }
        
        logger.info(f"Intelligent tool selection completed in {execution_time:.2f}s - "
                   f"Tool: {tool_selection.primary_tool}, "
                   f"Combined confidence: {combined_confidence:.2f}")
        
        return state
        
    except Exception as e:
        logger.error(f"Intelligent tool selection failed: {e}", exc_info=True)
        state["error_state"] = {
            "stage": "intelligent_tool_selection",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        return state


async def smart_execution(state: IntelligentOrchestrationState) -> IntelligentOrchestrationState:
    """
    Node 2: Smart Execution
    
    Intelligent execution with built-in error handling, automatic retries,
    and fallback logic. Embeds execution intelligence that was previously
    scattered across multiple coordination components.
    """
    logger = logging.getLogger(__name__)
    logger.info("Smart execution of selected NetBox tool...")
    
    start_time = datetime.now()
    
    try:
        # Check if we have tool selection from previous node
        if not state.get("tool_selection") or not state.get("final_parameters"):
            logger.error("Missing tool selection or parameters from previous node")
            state["error_state"] = {
                "stage": "smart_execution",
                "error": "Tool selection or parameters missing",
                "timestamp": datetime.now().isoformat()
            }
            state["execution_successful"] = False
            return state
        
        tool_selection = state["tool_selection"]
        parameters = state["final_parameters"]
        
        logger.info(f"Executing tool: {tool_selection.primary_tool} with parameters: {parameters}")
        
        # Create tool request for execution
        tool_request = ToolRequest(
            tool_name=tool_selection.primary_tool,
            params=parameters,
            priority=1,
            max_retries=3
        )
        
        # Execute with intelligent error handling
        tool_result = await _execute_with_smart_retry(tool_request, tool_selection)
        
        # Store results
        state["tool_results"] = [tool_result]
        state["execution_successful"] = tool_result.success
        
        if not tool_result.success:
            state["execution_errors"] = [tool_result.error or "Execution failed"]
            
            # Try fallback tools if primary failed and we have fallbacks
            if tool_selection.fallback_tools and len(tool_selection.fallback_tools) > 0:
                logger.info(f"Primary tool failed, trying fallback: {tool_selection.fallback_tools[0]}")
                
                fallback_request = ToolRequest(
                    tool_name=tool_selection.fallback_tools[0],
                    params=parameters,
                    priority=1,
                    max_retries=2
                )
                
                fallback_result = await _execute_with_smart_retry(fallback_request, tool_selection)
                state["tool_results"].append(fallback_result)
                
                if fallback_result.success:
                    state["execution_successful"] = True
                    logger.info("Fallback tool execution succeeded")
                else:
                    state["execution_errors"].append(fallback_result.error or "Fallback execution failed")
        else:
            state["execution_errors"] = []
            logger.info(f"Tool execution succeeded in {tool_result.execution_time:.2f}s")
        
        # Update performance metrics
        execution_time = (datetime.now() - start_time).total_seconds()
        if state["execution_metrics"]:
            state["execution_metrics"].update({
                "execution_time": execution_time,
                "tools_executed": len(state["tool_results"]),
                "execution_successful": state["execution_successful"],
                "primary_tool_success": state["tool_results"][0].success if state["tool_results"] else False,
                "fallback_used": len(state["tool_results"]) > 1
            })
        
        logger.info(f"Smart execution completed in {execution_time:.2f}s - Success: {state['execution_successful']}")
        
        return state
        
    except Exception as e:
        logger.error(f"Smart execution failed: {e}", exc_info=True)
        state["error_state"] = {
            "stage": "smart_execution",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        state["execution_successful"] = False
        state["execution_errors"] = [str(e)]
        return state


async def _execute_with_smart_retry(tool_request: ToolRequest, tool_selection: ToolSelection) -> ToolResult:
    """
    Execute tool with intelligent retry logic and error handling
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(tool_request.max_retries + 1):
        try:
            # Execute the tool using real API handler
            result = await execute_real_netbox_tool(tool_request)
            
            if result.success:
                logger.debug(f"Tool {tool_request.tool_name} succeeded on attempt {attempt + 1}")
                return result
            else:
                logger.warning(f"Tool {tool_request.tool_name} failed on attempt {attempt + 1}: {result.error}")
                
                # If this isn't the last attempt, wait briefly before retry
                if attempt < tool_request.max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                
        except Exception as e:
            logger.error(f"Exception executing {tool_request.tool_name} on attempt {attempt + 1}: {e}")
            
            if attempt == tool_request.max_retries:
                # Last attempt failed, return error result
                return ToolResult(
                    tool_name=tool_request.tool_name,
                    params=tool_request.params,
                    success=False,
                    result=None,
                    execution_time=0.0,
                    error=str(e),
                    cached=False
                )
            
            # Wait before retry
            await asyncio.sleep(0.5 * (attempt + 1))
    
    # If we get here, all attempts failed
    return ToolResult(
        tool_name=tool_request.tool_name,
        params=tool_request.params,
        success=False,
        result=None,
        execution_time=0.0,
        error="All retry attempts failed",
        cached=False
    )


async def adaptive_response(state: IntelligentOrchestrationState) -> IntelligentOrchestrationState:
    """
    Node 3: Adaptive Response
    
    LLM-generated response with natural fallback logic and intelligent
    context adaptation based on execution results and user needs.
    
    Embeds response intelligence that adapts to success/failure scenarios.
    """
    logger = logging.getLogger(__name__)
    logger.info("Generating adaptive natural language response...")
    
    start_time = datetime.now()
    
    try:
        # Analyze execution results to determine response strategy
        execution_successful = state.get("execution_successful", False)
        tool_results = state.get("tool_results", [])
        execution_errors = state.get("execution_errors", [])
        
        # Try intelligent response generation first
        response_generated = False
        
        try:
            # Initialize Response Generation Agent
            response_agent = ResponseGenerationAgent()
            await response_agent.initialize()
            
            # Prepare intelligent response context
            response_context = {
                "original_query": state["user_query"],
                "execution_successful": execution_successful,
                "tool_results": [_serialize_tool_result(r) for r in tool_results],
                "execution_errors": execution_errors,
                "tool_selection": _serialize_tool_selection(state.get("tool_selection")),
                "parameter_extraction": _serialize_parameter_extraction(state.get("parameter_extraction")),
                "execution_metrics": state.get("execution_metrics", {}),
                "session_context": {
                    "session_id": state["session_id"],
                    "correlation_id": state["correlation_id"]
                }
            }
            
            # Generate intelligent response using the correct request type
            response_result = await response_agent.process_request({
                "type": "format_response",
                "context": response_context,
                "response_type": "intelligent",
                "correlation_id": state["correlation_id"]
            })
            
            if response_result and response_result.get("success"):
                state["natural_language_response"] = response_result["response"]
                state["user_options"] = response_result.get("user_options", [])
                response_generated = True
                logger.info("Intelligent response generation succeeded")
            
        except Exception as e:
            logger.warning(f"Intelligent response generation failed, falling back: {e}")
        
        # Fallback to adaptive template-based response if LLM fails
        if not response_generated:
            logger.info("Using adaptive template-based response fallback")
            
            if execution_successful and tool_results:
                # Success response with results
                successful_result = next((r for r in tool_results if r.success), None)
                if successful_result:
                    state["natural_language_response"] = _create_success_response(
                        state["user_query"],
                        successful_result,
                        state.get("tool_selection"),
                        state.get("execution_metrics", {})
                    )
                else:
                    state["natural_language_response"] = "I found some results, but there were issues processing them completely."
            else:
                # Error response with helpful guidance
                state["natural_language_response"] = _create_error_response(
                    state["user_query"],
                    execution_errors,
                    state.get("tool_selection"),
                    state.get("execution_metrics", {})
                )
            
            # Provide user options based on context
            state["user_options"] = _generate_user_options(
                state["user_query"],
                execution_successful,
                state.get("tool_selection")
            )
        
        # Mark workflow as complete
        state["workflow_complete"] = True
        
        # Update final performance metrics
        response_time = (datetime.now() - start_time).total_seconds()
        if state["execution_metrics"]:
            state["execution_metrics"]["response_generation_time"] = response_time
            state["execution_metrics"]["total_workflow_time"] = (
                state["execution_metrics"].get("tool_selection_time", 0) +
                state["execution_metrics"].get("execution_time", 0) +
                response_time
            )
        
        logger.info(f"Adaptive response completed in {response_time:.2f}s - "
                   f"Response length: {len(state['natural_language_response'])}")
        
        return state
        
    except Exception as e:
        logger.error(f"Adaptive response generation failed: {e}", exc_info=True)
        
        # Emergency fallback response
        state["natural_language_response"] = (
            f"I encountered an issue processing your query: '{state['user_query']}'. "
            "Please try rephrasing your question or ask for help with NetBox operations."
        )
        state["user_options"] = [
            "Try a simpler query",
            "Ask for NetBox help", 
            "Check system status"
        ]
        state["workflow_complete"] = True
        
        state["error_state"] = {
            "stage": "adaptive_response",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        
        return state


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


def _serialize_tool_selection(tool_selection: Optional[ToolSelection]) -> Optional[Dict[str, Any]]:
    """Serialize ToolSelection for response context"""
    if not tool_selection:
        return None
    
    return {
        "primary_tool": tool_selection.primary_tool,
        "confidence": tool_selection.confidence,
        "confidence_level": tool_selection.confidence_level.value,
        "reasoning": tool_selection.reasoning,
        "fallback_tools": tool_selection.fallback_tools,
        "execution_strategy": tool_selection.execution_strategy
    }


def _serialize_parameter_extraction(param_extraction: Optional[ParameterExtractionResult]) -> Optional[Dict[str, Any]]:
    """Serialize ParameterExtractionResult for response context"""
    if not param_extraction:
        return None
    
    return {
        "parameters": param_extraction.parameters,
        "confidence": param_extraction.confidence,
        "extraction_method": param_extraction.extraction_method,
        "compound_entities": param_extraction.compound_entities,
        "preserved_relationships": param_extraction.preserved_relationships,
        "extraction_reasoning": param_extraction.extraction_reasoning
    }


def _create_success_response(query: str, result: ToolResult, tool_selection: Optional[ToolSelection], metrics: Dict[str, Any]) -> str:
    """Create a success response template"""
    tool_name = result.tool_name.replace("netbox_", "").replace("_", " ").title()
    execution_time = result.execution_time
    
    if isinstance(result.result, dict):
        # Try to extract meaningful summary from result
        if "devices" in result.result:
            count = len(result.result["devices"])
            return f"Found {count} devices using {tool_name} in {execution_time:.1f}s. The results include detailed device information with configurations and status."
        elif "sites" in result.result:
            count = len(result.result["sites"])
            return f"Found {count} sites using {tool_name} in {execution_time:.1f}s. The results show site locations, configurations, and associated resources."
        elif "racks" in result.result:
            count = len(result.result["racks"])
            return f"Found {count} racks using {tool_name} in {execution_time:.1f}s. The results display rack information and utilization details."
    
    return f"Successfully executed {tool_name} in {execution_time:.1f}s. The query returned detailed NetBox information as requested."


def _create_error_response(query: str, errors: List[str], tool_selection: Optional[ToolSelection], metrics: Dict[str, Any]) -> str:
    """Create an error response with helpful guidance"""
    if not errors:
        return "I encountered an unexpected issue while processing your request."
    
    primary_error = errors[0]
    
    # Provide specific guidance based on error type
    if "authentication" in primary_error.lower() or "auth" in primary_error.lower():
        return "I'm having trouble authenticating with NetBox. Please check the NetBox connection configuration and ensure the API token is valid."
    elif "not found" in primary_error.lower() or "404" in primary_error:
        return f"The requested resource wasn't found in NetBox. Please verify the entity names in your query: '{query}' and ensure they exist in NetBox."
    elif "connection" in primary_error.lower() or "timeout" in primary_error.lower():
        return "I'm unable to connect to NetBox right now. Please check that NetBox is running and accessible."
    elif "permission" in primary_error.lower():
        return "I don't have sufficient permissions to complete this request. Please check the NetBox API token permissions."
    else:
        return f"I encountered an issue while processing your request: {primary_error}. Please try rephrasing your query or contact support if the issue persists."


def _generate_user_options(query: str, execution_successful: bool, tool_selection: Optional[ToolSelection]) -> List[str]:
    """Generate contextual user options based on execution results"""
    options = []
    
    if execution_successful:
        options = [
            "Ask a follow-up question",
            "Get more detailed information",
            "Explore related resources"
        ]
    else:
        options = [
            "Try a simpler version of this query",
            "Check NetBox system status",
            "Get help with query syntax"
        ]
        
        # Add specific suggestions based on tool selection
        if tool_selection and tool_selection.fallback_tools:
            options.append("Try an alternative approach")
    
    return options


def create_intelligent_orchestration_graph() -> StateGraph:
    """
    Create simplified 3-node LangGraph StateGraph for intelligent NetBox orchestration
    
    This replaces the complex 5-node workflow with intelligent nodes that embed
    intelligence at each step instead of scattered across multiple components.
    
    Workflow:
    1. intelligent_tool_selection → 2. smart_execution → 3. adaptive_response
    
    No complex routing needed - simple linear flow with embedded intelligence.
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating simplified intelligent orchestration state machine...")
    
    # Initialize StateGraph with simplified IntelligentOrchestrationState
    workflow = StateGraph(IntelligentOrchestrationState)
    
    # Add the 3 intelligent nodes
    workflow.add_node("intelligent_tool_selection", intelligent_tool_selection)
    workflow.add_node("smart_execution", smart_execution)
    workflow.add_node("adaptive_response", adaptive_response)
    
    # Simple linear workflow - no complex routing needed
    workflow.add_edge(START, "intelligent_tool_selection")
    workflow.add_edge("intelligent_tool_selection", "smart_execution")
    workflow.add_edge("smart_execution", "adaptive_response")
    workflow.add_edge("adaptive_response", END)
    
    # Compile graph with memory checkpointing
    memory_saver = MemorySaver()
    compiled_graph = workflow.compile(checkpointer=memory_saver)
    
    logger.info("Simplified intelligent orchestration state machine compiled successfully")
    return compiled_graph


# Maintain backward compatibility with existing code
def create_orchestration_graph() -> StateGraph:
    """
    Backward compatibility wrapper for the new intelligent orchestration graph
    """
    return create_intelligent_orchestration_graph()


# Public interface for creating and executing intelligent workflows

async def execute_intelligent_workflow(
    user_query: str,
    session_id: str,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Public interface to execute a complete intelligent workflow for a user query.
    
    This is the main entry point that replaces the complex orchestration coordinator.
    
    Args:
        user_query: User's natural language query
        session_id: Session identifier for context
        correlation_id: Optional correlation ID for tracking
        
    Returns:
        Dict containing workflow results and response
    """
    logger = logging.getLogger(__name__)
    
    if not correlation_id:
        correlation_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Executing intelligent workflow for query: {user_query[:100]}...")
    
    try:
        # Create the intelligent orchestration graph
        workflow_graph = create_intelligent_orchestration_graph()
        
        # Create initial state
        initial_state: IntelligentOrchestrationState = {
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
            "execution_metrics": None
        }
        
        # Execute the workflow with proper configuration
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": correlation_id
            }
        }
        workflow_result = await workflow_graph.ainvoke(initial_state, config=config)
        
        # Extract results for return
        result = {
            "success": workflow_result.get("execution_successful", False),
            "response": workflow_result.get("natural_language_response", "No response generated"),
            "user_options": workflow_result.get("user_options", []),
            "execution_metrics": workflow_result.get("execution_metrics", {}),
            "tool_results": [_serialize_tool_result(r) for r in workflow_result.get("tool_results", [])],
            "workflow_complete": workflow_result.get("workflow_complete", False),
            "error_state": workflow_result.get("error_state"),
            "session_id": session_id,
            "correlation_id": correlation_id
        }
        
        logger.info(f"Intelligent workflow completed - Success: {result['success']}")
        return result
        
    except Exception as e:
        logger.error(f"Intelligent workflow execution failed: {e}", exc_info=True)
        
        return {
            "success": False,
            "response": f"I encountered an error processing your query: {str(e)}. Please try again or contact support.",
            "user_options": ["Try a simpler query", "Check system status", "Contact support"],
            "execution_metrics": {"error": True, "error_message": str(e)},
            "tool_results": [],
            "workflow_complete": True,
            "error_state": {
                "stage": "workflow_execution",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            "session_id": session_id,
            "correlation_id": correlation_id
        }


# End of simplified 3-node intelligent workflow implementation

# The new 3-node workflow (intelligent_tool_selection → smart_execution → adaptive_response)
# replaces all the complex coordination logic above with embedded intelligence at each step.