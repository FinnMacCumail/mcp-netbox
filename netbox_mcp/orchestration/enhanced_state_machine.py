#!/usr/bin/env python3
"""
Enhanced 3-Node LangGraph Orchestration with Intelligent Fallback Integration

This module enhances the existing 3-node orchestration by integrating the
IntelligentFallbackOrchestrator from Phase 4, providing Claude Code CLI-style
resilience and helpfulness at every step of the workflow.

Key enhancements:
- Integrates intelligent fallback at each node for maximum resilience
- Maintains the simplified 3-node architecture from Phase 3
- Replaces low-level error recovery with high-level intelligent fallbacks
- Provides Claude Code CLI-style user experience with helpful responses
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
import traceback

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Import Phase 1, 2, 3 components
from .intelligent_tool_selector import select_tool, ToolSelection
from .tool_aware_parameter_extractor import extract_parameters, ParameterExtractionResult
from .coordination import ToolRequest, ToolResult
from .real_api_handler import execute_real_netbox_tool
from ..agents.response_generation import ResponseGenerationAgent

# Import Phase 4 intelligent fallback
from .intelligent_fallback_orchestrator import (
    execute_with_intelligent_fallback, FallbackResult, FallbackLevel
)

logger = logging.getLogger(__name__)


class EnhancedOrchestrationState(TypedDict):
    """Enhanced state with intelligent fallback integration"""
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
    
    # Execution results with fallback integration
    fallback_result: Optional[FallbackResult]
    tool_results: List[ToolResult]
    execution_successful: bool
    execution_errors: List[str]
    
    # Enhanced response handling
    natural_language_response: Optional[str]
    user_options: Optional[List[str]]
    clarification_questions: Optional[List[str]]
    alternative_approaches: Optional[List[Dict[str, Any]]]
    workflow_complete: bool
    
    # Fallback tracking
    fallback_level_used: Optional[str]
    fallback_reasoning: Optional[str]
    fallback_suggestions: Optional[List[str]]
    
    # Performance tracking
    execution_metrics: Optional[Dict[str, Any]]


async def intelligent_tool_selection_with_fallback(
    state: EnhancedOrchestrationState
) -> EnhancedOrchestrationState:
    """
    Enhanced Node 1: Intelligent Tool Selection with Fallback
    
    Integrates Phase 1+2 with Phase 4 fallback intelligence for maximum resilience.
    If primary tool selection fails, intelligent fallbacks kick in automatically.
    """
    logger.info(f"Enhanced intelligent tool selection for query: {state['user_query'][:100]}...")
    
    start_time = datetime.now()
    
    try:
        # Use intelligent fallback orchestrator for tool selection
        # This automatically handles Phase 1 + Phase 2 integration with fallbacks
        fallback_result = await execute_with_intelligent_fallback(
            user_query=state["user_query"],
            session_context={
                "session_id": state["session_id"],
                "correlation_id": state["correlation_id"]
            }
        )
        
        # Update state with fallback results
        state["fallback_result"] = fallback_result
        state["fallback_level_used"] = fallback_result.fallback_level.value
        state["fallback_reasoning"] = fallback_result.reasoning
        state["fallback_suggestions"] = fallback_result.suggestions
        
        if fallback_result.success:
            # Successful execution - extract details for workflow continuation
            state["tool_selection"] = ToolSelection(
                primary_tool=fallback_result.tool_name,
                confidence=fallback_result.confidence,
                confidence_level=_map_confidence_to_level(fallback_result.confidence),
                parameters=fallback_result.parameters,
                reasoning=fallback_result.reasoning,
                alternative_tools=[],
                fallback_tools=[]
            )
            state["final_parameters"] = fallback_result.parameters
            state["execution_successful"] = True
            
            # Convert result to ToolResult format for compatibility
            tool_result = ToolResult(
                tool_name=fallback_result.tool_name,
                success=True,
                result=fallback_result.result,
                execution_time=fallback_result.execution_time,
                timestamp=fallback_result.timestamp
            )
            state["tool_results"] = [tool_result]
            
        else:
            # Execution failed but we have intelligent fallback information
            state["execution_successful"] = False
            state["execution_errors"] = [fallback_result.reasoning]
            
            # Check if we have clarification questions or alternatives
            if fallback_result.clarification_questions:
                state["clarification_questions"] = fallback_result.clarification_questions
            
            if fallback_result.alternative_approaches:
                state["alternative_approaches"] = fallback_result.alternative_approaches
            
            # For graceful degradation, we still consider this a "successful" workflow
            if fallback_result.fallback_level == FallbackLevel.GRACEFUL_DEGRADATION:
                state["workflow_complete"] = True
        
        # Record execution metrics
        end_time = datetime.now()
        state["execution_metrics"] = {
            "tool_selection_time": (end_time - start_time).total_seconds(),
            "fallback_level": fallback_result.fallback_level.value,
            "confidence": fallback_result.confidence,
            "timestamp": end_time.isoformat()
        }
        
        logger.info(f"Tool selection completed with fallback level: {fallback_result.fallback_level.value}")
        
    except Exception as e:
        logger.error(f"Enhanced tool selection failed: {e}")
        logger.debug(f"Full error trace: {traceback.format_exc()}")
        
        # Even our enhanced fallback failed - set minimal error state
        state["execution_successful"] = False
        state["execution_errors"] = [f"Enhanced tool selection failed: {str(e)}"]
        state["fallback_level_used"] = "critical_failure"
        state["fallback_reasoning"] = "System-level failure in enhanced tool selection"
        state["fallback_suggestions"] = [
            "Try a simpler query",
            "Check system connectivity",
            "Contact system administrator"
        ]
        state["workflow_complete"] = True  # Force completion on critical failure
    
    return state


async def smart_execution_with_fallback(
    state: EnhancedOrchestrationState
) -> EnhancedOrchestrationState:
    """
    Enhanced Node 2: Smart Execution with Fallback
    
    If tool selection was successful, this validates and potentially re-executes.
    If tool selection used fallbacks, this handles the results appropriately.
    """
    logger.info("Enhanced smart execution with fallback validation...")
    
    # If we already have a successful result from fallback orchestrator, validate it
    if state["execution_successful"] and state["tool_results"]:
        logger.info("Validating successful fallback execution result")
        
        # The result is already good - just add any additional validation
        primary_result = state["tool_results"][0]
        
        # Check if result needs any post-processing
        if primary_result.success and primary_result.result:
            # Result looks good - proceed to response generation
            logger.info(f"Execution validated successfully for tool: {primary_result.tool_name}")
        else:
            # Something's wrong with the result - mark as failed
            state["execution_successful"] = False
            state["execution_errors"].append("Result validation failed")
    
    elif not state["execution_successful"]:
        # Execution failed but we might have useful fallback information
        logger.info("Execution failed - preparing fallback response information")
        
        # The fallback orchestrator already tried all levels
        # Just ensure we have the right completion flags set
        if state.get("fallback_level_used") in ["query_clarification", "graceful_degradation"]:
            state["workflow_complete"] = True
    
    return state


async def adaptive_response_with_fallback(
    state: EnhancedOrchestrationState
) -> EnhancedOrchestrationState:
    """
    Enhanced Node 3: Adaptive Response with Fallback
    
    Generates intelligent responses based on execution results and fallback information.
    Provides Claude Code CLI-style helpful responses regardless of success or failure.
    """
    logger.info("Generating adaptive response with fallback intelligence...")
    
    try:
        if state["execution_successful"] and state["tool_results"]:
            # Successful execution - generate normal response
            response = await _generate_success_response(state)
        
        elif state.get("clarification_questions"):
            # Query clarification needed - generate clarification response
            response = await _generate_clarification_response(state)
        
        elif state.get("alternative_approaches"):
            # Alternative approaches available - generate suggestion response
            response = await _generate_alternatives_response(state)
        
        else:
            # Graceful degradation - generate helpful explanation response
            response = await _generate_degradation_response(state)
        
        state["natural_language_response"] = response
        state["workflow_complete"] = True
        
        logger.info("Adaptive response generated successfully")
    
    except Exception as e:
        logger.error(f"Adaptive response generation failed: {e}")
        
        # Generate minimal fallback response
        state["natural_language_response"] = _generate_minimal_fallback_response(state)
        state["workflow_complete"] = True
    
    return state


async def _generate_success_response(state: EnhancedOrchestrationState) -> str:
    """Generate response for successful execution"""
    tool_result = state["tool_results"][0]
    fallback_info = ""
    
    # Add fallback information if fallbacks were used
    if state.get("fallback_level_used") and state["fallback_level_used"] != "primary":
        fallback_info = f"\n\n*Note: Used {state['fallback_level_used'].replace('_', ' ')} to complete your request.*"
    
    # Use response generation agent if available
    try:
        response_agent = ResponseGenerationAgent()
        response = await response_agent.generate_response(
            query=state["user_query"],
            results=[tool_result],
            context={
                "fallback_used": state.get("fallback_level_used", "primary"),
                "fallback_reasoning": state.get("fallback_reasoning", "")
            }
        )
        return response + fallback_info
    except Exception as e:
        logger.warning(f"Response agent failed, using simple response: {e}")
        
        # Simple fallback response
        return f"""Here are the results for your query "{state['user_query']}":

{json.dumps(tool_result.result, indent=2) if isinstance(tool_result.result, dict) else str(tool_result.result)}

Tool used: {tool_result.tool_name}
Execution time: {tool_result.execution_time:.2f}s{fallback_info}"""


async def _generate_clarification_response(state: EnhancedOrchestrationState) -> str:
    """Generate response when clarification is needed"""
    questions = state.get("clarification_questions", [])
    
    response = f"""I need some clarification to help you with "{state['user_query']}":

"""
    
    for i, question in enumerate(questions, 1):
        response += f"{i}. {question}\n"
    
    if state.get("fallback_reasoning"):
        response += f"\nReason: {state['fallback_reasoning']}"
    
    if state.get("fallback_suggestions"):
        response += "\n\nAlternatively, you could:\n"
        for suggestion in state["fallback_suggestions"][:3]:
            response += f"• {suggestion}\n"
    
    return response


async def _generate_alternatives_response(state: EnhancedOrchestrationState) -> str:
    """Generate response with alternative approaches"""
    alternatives = state.get("alternative_approaches", [])
    
    response = f"""I couldn't complete "{state['user_query']}" as requested, but here are some alternatives:

"""
    
    for i, alternative in enumerate(alternatives[:3], 1):
        if isinstance(alternative, dict):
            tool_name = alternative.get("tool", alternative.get("approach", "unknown"))
            description = alternative.get("reasoning", alternative.get("description", "No description"))
            response += f"{i}. Use {tool_name}: {description}\n"
    
    if state.get("fallback_suggestions"):
        response += "\nOther suggestions:\n"
        for suggestion in state["fallback_suggestions"][:3]:
            response += f"• {suggestion}\n"
    
    return response


async def _generate_degradation_response(state: EnhancedOrchestrationState) -> str:
    """Generate helpful response for graceful degradation"""
    fallback_result = state.get("fallback_result")
    
    if fallback_result and fallback_result.result and isinstance(fallback_result.result, dict):
        result_data = fallback_result.result
        
        response = f"""I wasn't able to complete "{state['user_query']}" successfully.

"""
        
        if "error_summary" in result_data:
            response += f"**What happened:** {result_data['error_summary']}\n\n"
        
        if "what_went_wrong" in result_data:
            response += f"**Details:** {result_data['what_went_wrong']}\n\n"
        
        if "suggested_actions" in result_data:
            response += "**What you can try:**\n"
            for action in result_data["suggested_actions"][:5]:
                response += f"• {action}\n"
        
        if "alternative_approaches" in result_data:
            response += "\n**Alternative approaches:**\n"
            for approach in result_data["alternative_approaches"][:3]:
                response += f"• {approach}\n"
    
    else:
        # Minimal graceful degradation
        response = f"""I wasn't able to complete "{state['user_query']}" successfully.

**What you can try:**
• Try rephrasing your query with more specific details
• Break complex requests into simpler steps
• Use more specific NetBox resource names

**Need help?** Try asking for "list all" commands to explore what's available.
"""
    
    return response


def _generate_minimal_fallback_response(state: EnhancedOrchestrationState) -> str:
    """Generate absolute minimal response when everything else fails"""
    return f"""I encountered an issue processing "{state['user_query']}".

Please try:
• Rephrasing your query more specifically
• Breaking down complex requests into simpler steps
• Checking resource names and spellings

If the problem persists, please contact your system administrator."""


def _map_confidence_to_level(confidence: float):
    """Map confidence score to confidence level enum"""
    from .intelligent_tool_selector import ToolSelectionConfidence
    
    if confidence >= 0.8:
        return ToolSelectionConfidence.HIGH
    elif confidence >= 0.6:
        return ToolSelectionConfidence.MEDIUM
    elif confidence >= 0.4:
        return ToolSelectionConfidence.LOW
    else:
        return ToolSelectionConfidence.VERY_LOW


class EnhancedIntelligentOrchestrator:
    """Enhanced orchestrator with intelligent fallback integration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Build the enhanced LangGraph workflow
        workflow = StateGraph(EnhancedOrchestrationState)
        
        # Add enhanced nodes with fallback integration
        workflow.add_node("intelligent_tool_selection", intelligent_tool_selection_with_fallback)
        workflow.add_node("smart_execution", smart_execution_with_fallback)
        workflow.add_node("adaptive_response", adaptive_response_with_fallback)
        
        # Define enhanced workflow flow
        workflow.add_edge(START, "intelligent_tool_selection")
        workflow.add_edge("intelligent_tool_selection", "smart_execution")
        workflow.add_edge("smart_execution", "adaptive_response")
        workflow.add_edge("adaptive_response", END)
        
        # Compile with memory for conversation continuity
        memory = MemorySaver()
        self.app = workflow.compile(checkpointer=memory)
        
        self.logger.info("Enhanced orchestrator initialized with intelligent fallback integration")
    
    async def process_user_query(
        self, 
        user_query: str, 
        session_id: str = None,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """
        Process user query with enhanced intelligence and fallback resilience
        
        This is the main entry point that provides Claude Code CLI-style
        resilience and helpfulness regardless of query complexity or errors.
        """
        import uuid
        
        session_id = session_id or str(uuid.uuid4())
        correlation_id = correlation_id or str(uuid.uuid4())
        
        self.logger.info(f"Processing query with enhanced orchestrator: {user_query[:100]}...")
        
        # Initialize enhanced state
        initial_state = EnhancedOrchestrationState(
            user_query=user_query,
            session_id=session_id,
            correlation_id=correlation_id,
            tool_selection=None,
            tool_selection_confidence=None,
            parameter_extraction=None,
            final_parameters=None,
            fallback_result=None,
            tool_results=[],
            execution_successful=False,
            execution_errors=[],
            natural_language_response=None,
            user_options=None,
            clarification_questions=None,
            alternative_approaches=None,
            workflow_complete=False,
            fallback_level_used=None,
            fallback_reasoning=None,
            fallback_suggestions=None,
            execution_metrics=None
        )
        
        try:
            # Execute the enhanced workflow
            config = {
                "configurable": {
                    "thread_id": session_id,
                    "correlation_id": correlation_id
                }
            }
            
            final_state = await self.app.ainvoke(initial_state, config)
            
            # Extract key information for response
            response_data = {
                "success": final_state.get("execution_successful", False),
                "response": final_state.get("natural_language_response", "No response generated"),
                "tool_used": final_state["tool_results"][0].tool_name if final_state.get("tool_results") else None,
                "fallback_level": final_state.get("fallback_level_used", "primary"),
                "fallback_reasoning": final_state.get("fallback_reasoning"),
                "suggestions": final_state.get("fallback_suggestions", []),
                "clarification_questions": final_state.get("clarification_questions", []),
                "alternative_approaches": final_state.get("alternative_approaches", []),
                "execution_time": final_state.get("execution_metrics", {}).get("tool_selection_time", 0),
                "session_id": session_id,
                "correlation_id": correlation_id
            }
            
            self.logger.info(f"Enhanced query processing completed with fallback level: {response_data['fallback_level']}")
            return response_data
        
        except Exception as e:
            self.logger.error(f"Enhanced orchestrator failed: {e}")
            self.logger.debug(f"Full error trace: {traceback.format_exc()}")
            
            # Even the enhanced orchestrator failed - provide minimal response
            return {
                "success": False,
                "response": f"I encountered a system error while processing your query: {str(e)}\n\nPlease try a simpler query or contact your administrator.",
                "tool_used": None,
                "fallback_level": "system_failure",
                "fallback_reasoning": "Critical system failure in enhanced orchestrator",
                "suggestions": ["Try a simpler query", "Check system status", "Contact administrator"],
                "clarification_questions": [],
                "alternative_approaches": [],
                "execution_time": 0,
                "session_id": session_id,
                "correlation_id": correlation_id
            }


# Global enhanced orchestrator instance
enhanced_intelligent_orchestrator = EnhancedIntelligentOrchestrator()


# Public interface
async def process_query_with_intelligent_fallback(
    user_query: str,
    session_id: str = None,
    correlation_id: str = None
) -> Dict[str, Any]:
    """
    Public interface for processing queries with enhanced intelligent fallback
    
    This provides Claude Code CLI-style resilience and helpfulness for any NetBox query.
    """
    return await enhanced_intelligent_orchestrator.process_user_query(
        user_query, session_id, correlation_id
    )