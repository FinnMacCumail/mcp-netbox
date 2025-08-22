"""
LangGraph StateGraph Orchestration for NetBox Phase 3 Week 5-8

This module implements the core state machine orchestration that replaces
the existing simple agent coordination with sophisticated LangGraph workflows.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..agents.conversation_manager import ConversationManagerAgent
from ..agents.intent_recognition import IntentRecognitionAgent  
from ..agents.response_generation import ResponseGenerationAgent


class NetworkOrchestrationState(TypedDict):
    """
    Comprehensive state for LangGraph NetBox orchestration workflows
    
    This state structure captures all information needed for complex
    multi-tool NetBox operations with graceful limitation handling.
    """
    # Core query information
    user_query: str
    session_id: str
    correlation_id: str
    
    # Intent classification results
    classified_intent: Optional[Dict[str, Any]]
    entities: Optional[Dict[str, List[str]]]
    confidence_score: Optional[float]
    
    # Tool coordination state
    coordination_strategy: Optional[str]  # "direct", "complex", "limitation_aware"
    tool_execution_plan: Optional[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # Limitation handling
    known_limitations: List[str]
    limitation_strategy: Optional[str]  # "progressive", "sampling", "fallback"
    progressive_state: Optional[Dict[str, Any]]
    
    # Response generation
    natural_language_response: Optional[str]
    user_options: Optional[List[str]]
    
    # Workflow control
    next_action: Optional[str]
    workflow_complete: bool
    error_state: Optional[Dict[str, Any]]
    
    # Context and session management
    conversation_context: Optional[Dict[str, Any]]
    performance_metrics: Optional[Dict[str, Any]]


async def classify_user_intent(state: NetworkOrchestrationState) -> NetworkOrchestrationState:
    """
    LangGraph node: Classify user intent using Intent Recognition Agent
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Classifying intent for query: {state['user_query'][:50]}...")
    
    try:
        # Initialize Intent Recognition Agent
        intent_agent = IntentRecognitionAgent()
        await intent_agent.initialize()
        
        # Classify intent with conversation context
        classification_result = await intent_agent.process_request({
            "type": "classify_query",
            "query": state["user_query"],
            "context": state.get("conversation_context", {}),
            "correlation_id": state["correlation_id"]
        })
        
        # Update state with classification results
        if classification_result.get("success"):
            classification = classification_result["classification"]
            state["classified_intent"] = classification
            state["entities"] = classification.get("entities", [])
            state["confidence_score"] = classification.get("confidence", 0.5)
        else:
            # Fallback for failed classification
            state["classified_intent"] = {"intent": "discovery", "complexity": "simple"}
            state["entities"] = []
            state["confidence_score"] = 0.3
        
        # Determine coordination strategy based on intent
        confidence = state["confidence_score"]
        intent_data = state["classified_intent"]
        
        if confidence > 0.8:
            if intent_data.get("complexity") == "simple":
                state["coordination_strategy"] = "direct"
            else:
                state["coordination_strategy"] = "complex"
        else:
            state["coordination_strategy"] = "limitation_aware"
            
        logger.info(f"Intent classified: {state['coordination_strategy']} strategy selected")
        return state
        
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        state["error_state"] = {
            "stage": "intent_classification",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        state["coordination_strategy"] = "limitation_aware"
        return state


async def plan_tool_coordination(state: NetworkOrchestrationState) -> NetworkOrchestrationState:
    """
    LangGraph node: Create execution plan for complex multi-tool operations
    """
    logger = logging.getLogger(__name__)
    logger.info("Planning tool coordination for complex query...")
    
    try:
        # Extract planning context
        intent = state["classified_intent"]
        entities = state["entities"]
        
        # Create execution plan based on intent category
        intent_type = intent.get("intent", "discovery")
        if intent_type in ["discovery", "retrieval"]:
            plan = await create_discovery_plan(entities, state["user_query"])
        elif intent_type == "analysis":
            plan = await create_analysis_plan(entities, state["user_query"])
        elif intent_type == "creation":
            plan = await create_creation_plan(entities, state["user_query"])
        else:
            plan = await create_fallback_plan(entities, state["user_query"])
            
        state["tool_execution_plan"] = plan
        state["known_limitations"] = plan.get("limitations", [])
        
        logger.info(f"Execution plan created with {len(plan['steps'])} steps")
        return state
        
    except Exception as e:
        logger.error(f"Tool coordination planning failed: {e}")
        state["error_state"] = {
            "stage": "tool_planning", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return state


async def execute_coordinated_tools(state: NetworkOrchestrationState) -> NetworkOrchestrationState:
    """
    LangGraph node: Execute NetBox MCP tools according to coordination plan
    """
    logger = logging.getLogger(__name__)
    logger.info("Executing coordinated NetBox MCP tools...")
    
    try:
        plan = state["tool_execution_plan"]
        results = []
        
        # Execute tools according to plan (parallel or sequential)
        for step in plan["steps"]:
            if step["execution_type"] == "parallel":
                # Execute tools in parallel
                step_results = await execute_parallel_tools(step["tools"])
            else:
                # Execute tools sequentially with context passing
                step_results = await execute_sequential_tools(step["tools"], results)
                
            results.extend(step_results)
            
        state["tool_results"] = results
        
        # Check for any tool failures
        failed_tools = [r for r in results if not r.get("success", False)]
        if failed_tools:
            state["known_limitations"].extend([
                f"Tool {tool['name']} failed: {tool['error']}"
                for tool in failed_tools
            ])
            
        logger.info(f"Tool execution completed: {len(results)} tools executed")
        return state
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        state["error_state"] = {
            "stage": "tool_execution",
            "error": str(e), 
            "timestamp": datetime.now().isoformat()
        }
        return state


async def handle_known_limitations(state: NetworkOrchestrationState) -> NetworkOrchestrationState:
    """
    LangGraph node: Provide graceful fallback for queries with known limitations
    """
    logger = logging.getLogger(__name__)
    logger.info("Handling known NetBox MCP tool limitations...")
    
    try:
        limitations = state["known_limitations"]
        
        # Determine limitation handling strategy
        if any("token_overflow" in limit for limit in limitations):
            state["limitation_strategy"] = "progressive"
            state["progressive_state"] = await setup_progressive_disclosure(state)
        elif any("n_plus_one" in limit for limit in limitations):
            state["limitation_strategy"] = "sampling"
            state["progressive_state"] = await setup_intelligent_sampling(state)
        else:
            state["limitation_strategy"] = "fallback"
            state["progressive_state"] = await setup_graceful_fallback(state)
            
        logger.info(f"Limitation strategy: {state['limitation_strategy']}")
        return state
        
    except Exception as e:
        logger.error(f"Limitation handling failed: {e}")
        state["error_state"] = {
            "stage": "limitation_handling",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return state


async def generate_intelligent_response(state: NetworkOrchestrationState) -> NetworkOrchestrationState:
    """
    LangGraph node: Generate natural language response using Response Generation Agent
    """
    logger = logging.getLogger(__name__)
    logger.info("Generating intelligent natural language response...")
    
    try:
        # Initialize Response Generation Agent
        response_agent = ResponseGenerationAgent()
        await response_agent.initialize()
        
        # Prepare response context
        response_context = {
            "original_query": state["user_query"],
            "intent": state["classified_intent"],
            "tool_results": state["tool_results"],
            "limitations": state["known_limitations"],
            "limitation_strategy": state.get("limitation_strategy"),
            "progressive_state": state.get("progressive_state")
        }
        
        # Generate response
        response_result = await response_agent.process_request({
            "type": "format_response",
            "context": response_context,
            "correlation_id": state["correlation_id"]
        })
        
        state["natural_language_response"] = response_result["response"]
        state["user_options"] = response_result.get("user_options", [])
        state["workflow_complete"] = True
        
        logger.info("Natural language response generated successfully")
        return state
        
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        state["error_state"] = {
            "stage": "response_generation",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        state["workflow_complete"] = True  # End workflow even on error
        return state


def route_coordination_strategy(state: NetworkOrchestrationState) -> str:
    """
    LangGraph routing function: Determine next workflow step based on coordination strategy
    """
    strategy = state.get("coordination_strategy", "limitation_aware")
    
    # Return the strategy key, not the node name (LangGraph maps this to target nodes)
    if strategy == "direct":
        return "direct"
    elif strategy == "complex":
        return "complex"
    else:  # limitation_aware
        return "limitation_aware"


def check_workflow_completion(state: NetworkOrchestrationState) -> str:
    """
    LangGraph routing function: Check if workflow is complete
    """
    if state.get("workflow_complete", False):
        return "end"
    elif state.get("error_state"):
        return "generate_response"  # Generate error response
    else:
        return "generate_response"


def create_orchestration_graph() -> StateGraph:
    """
    Create LangGraph StateGraph for NetBox orchestration workflows
    
    This replaces the simple agent coordination from Week 1-4 with
    sophisticated state machine orchestration for Week 5-8.
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating LangGraph orchestration state machine...")
    
    # Initialize StateGraph with NetworkOrchestrationState
    workflow = StateGraph(NetworkOrchestrationState)
    
    # Add orchestration nodes
    workflow.add_node("classify_intent", classify_user_intent)
    workflow.add_node("plan_coordination", plan_tool_coordination)
    workflow.add_node("execute_tools", execute_coordinated_tools)
    workflow.add_node("handle_limitations", handle_known_limitations)
    workflow.add_node("generate_response", generate_intelligent_response)
    
    # Define workflow entry point
    workflow.add_edge(START, "classify_intent")
    
    # Add conditional routing based on coordination strategy
    workflow.add_conditional_edges(
        "classify_intent",
        route_coordination_strategy,
        {
            "direct": "execute_tools",
            "complex": "plan_coordination", 
            "limitation_aware": "handle_limitations"
        }
    )
    
    # Connect planning to execution
    workflow.add_edge("plan_coordination", "execute_tools")
    
    # Connect limitation handling to response generation
    workflow.add_edge("handle_limitations", "generate_response")
    
    # Connect tool execution to response generation
    workflow.add_edge("execute_tools", "generate_response")
    
    # End workflow after response generation
    workflow.add_edge("generate_response", END)
    
    # Compile graph with memory checkpointing
    memory_saver = MemorySaver()
    compiled_graph = workflow.compile(checkpointer=memory_saver)
    
    logger.info("LangGraph orchestration state machine compiled successfully")
    return compiled_graph


# Helper functions for tool coordination planning

async def create_discovery_plan(entities: Dict[str, List[str]], query: str) -> Dict[str, Any]:
    """Create execution plan for discovery queries"""
    return {
        "type": "discovery",
        "steps": [
            {
                "name": "entity_discovery",
                "execution_type": "parallel",
                "tools": [
                    {"name": "netbox_list_all_sites", "params": {}},
                    {"name": "netbox_list_all_devices", "params": {"site_name": entities.get("sites", [None])[0]}}
                ]
            }
        ],
        "limitations": ["potential_token_overflow", "large_result_set"]
    }


async def create_analysis_plan(entities: Dict[str, List[str]], query: str) -> Dict[str, Any]:
    """Create execution plan for analysis queries"""
    return {
        "type": "analysis",
        "steps": [
            {
                "name": "data_collection",
                "execution_type": "sequential",
                "tools": [
                    {"name": "netbox_get_device_info", "params": {"device_name": entities.get("devices", [None])[0]}},
                    {"name": "netbox_get_device_interfaces", "params": {"device_name": entities.get("devices", [None])[0]}}
                ]
            },
            {
                "name": "relationship_analysis", 
                "execution_type": "parallel",
                "tools": [
                    {"name": "netbox_get_device_cables", "params": {"device_name": entities.get("devices", [None])[0]}},
                    {"name": "netbox_list_all_vlans", "params": {"site_name": entities.get("sites", [None])[0]}}
                ]
            }
        ],
        "limitations": ["n_plus_one_queries", "relationship_complexity"]
    }


async def create_creation_plan(entities: Dict[str, List[str]], query: str) -> Dict[str, Any]:
    """Create execution plan for creation/provisioning queries"""
    return {
        "type": "creation",
        "steps": [
            {
                "name": "validation",
                "execution_type": "sequential", 
                "tools": [
                    {"name": "netbox_get_site_info", "params": {"site_name": entities.get("sites", [None])[0]}},
                    {"name": "netbox_list_all_racks", "params": {"site_name": entities.get("sites", [None])[0]}}
                ]
            },
            {
                "name": "provisioning",
                "execution_type": "sequential",
                "tools": [
                    {"name": "netbox_provision_new_device", "params": {"confirm": False}}  # Will be populated with validated data
                ]
            }
        ],
        "limitations": ["validation_dependencies", "creation_confirmation_required"]
    }


async def create_fallback_plan(entities: Dict[str, List[str]], query: str) -> Dict[str, Any]:
    """Create fallback plan for unclassified or ambiguous queries"""
    return {
        "type": "fallback",
        "steps": [
            {
                "name": "general_discovery",
                "execution_type": "parallel",
                "tools": [
                    {"name": "netbox_health_check", "params": {}},
                    {"name": "netbox_list_all_sites", "params": {"limit": 10}}
                ]
            }
        ],
        "limitations": ["ambiguous_intent", "general_exploration_needed"]
    }


async def execute_parallel_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute NetBox MCP tools in parallel"""
    logger = logging.getLogger(__name__)
    
    # Simulate tool execution (Week 5-8 will integrate real NetBox MCP tools)
    results = []
    for tool in tools:
        result = {
            "tool_name": tool["name"],
            "params": tool["params"],
            "success": True,
            "result": f"Simulated result for {tool['name']}",
            "execution_time": 0.5,
            "timestamp": datetime.now().isoformat()
        }
        results.append(result)
        
    logger.info(f"Parallel execution completed: {len(tools)} tools")
    return results


async def execute_sequential_tools(tools: List[Dict[str, Any]], previous_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute NetBox MCP tools sequentially with context passing"""
    logger = logging.getLogger(__name__)
    
    # Simulate sequential tool execution with context
    results = []
    for i, tool in enumerate(tools):
        # Use previous results as context for current tool
        context = previous_results if previous_results else []
        
        result = {
            "tool_name": tool["name"],
            "params": tool["params"],
            "context": f"Used context from {len(context)} previous tools",
            "success": True,
            "result": f"Simulated sequential result for {tool['name']}",
            "execution_time": 0.7,
            "timestamp": datetime.now().isoformat()
        }
        results.append(result)
        
    logger.info(f"Sequential execution completed: {len(tools)} tools")
    return results


async def setup_progressive_disclosure(state: NetworkOrchestrationState) -> Dict[str, Any]:
    """Setup progressive disclosure for token overflow scenarios"""
    return {
        "strategy": "progressive_disclosure",
        "total_estimated_results": 500,
        "current_batch": 1,
        "batch_size": 50,
        "user_options": [
            "Show next 50 results",
            "Apply filters to reduce scope",
            "Switch to summary view"
        ]
    }


async def setup_intelligent_sampling(state: NetworkOrchestrationState) -> Dict[str, Any]:
    """Setup intelligent sampling for N+1 query scenarios"""
    return {
        "strategy": "intelligent_sampling",
        "total_entities": 150,
        "sample_size": 10,
        "user_options": [
            "Process next 10 entities",
            "Filter to specific entities", 
            "Generate summary report"
        ]
    }


async def setup_graceful_fallback(state: NetworkOrchestrationState) -> Dict[str, Any]:
    """Setup graceful fallback for general limitations"""
    return {
        "strategy": "graceful_fallback",
        "alternative_approaches": [
            "Try simplified query",
            "Use different NetBox tools",
            "Request specific entity names"
        ],
        "user_options": [
            "Simplify query scope",
            "Try alternative approach",
            "Get help with query syntax"
        ]
    }