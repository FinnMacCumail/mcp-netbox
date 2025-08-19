# Agent System Architecture

## Overview

The Phase 3 agent system replaces the monolithic Claude Code CLI with a distributed multi-agent architecture powered by OpenAI models and orchestrated through LangGraph state machines.

## Core Agents (Essential for CLI Replacement)

### 1. Conversation Manager Agent (GPT-4o)
**Role**: Primary orchestrator and user interface

**Responsibilities**:
- Maintains conversation context and state
- Routes user queries to appropriate specialized agents
- Handles multi-turn interactions with context preservation
- Manages session lifecycle and agent coordination
- Provides unified response aggregation

**OpenAI Configuration**:
```python
class ConversationManagerAgent:
    model = "gpt-4o"
    temperature = 0.7
    max_tokens = 4096
    
    system_prompt = """
    You are the Conversation Manager for NetBox infrastructure operations.
    Route user queries to specialized agents and coordinate responses.
    Maintain conversation context and provide coherent user experience.
    """
```

### 2. Intent Recognition Agent (GPT-4o-mini)
**Role**: Natural language understanding and query classification

**Responsibilities**:
- Parse and classify user queries using OpenAI structured outputs
- Extract entities (devices, sites, IPs, etc.) from natural language
- Determine query complexity and required tools
- Trigger clarification flows for ambiguous requests
- Route to appropriate execution strategy

**OpenAI Configuration**:
```python
class IntentRecognitionAgent:
    model = "gpt-4o-mini"
    temperature = 0.1
    response_format = {"type": "json_object"}
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "classify_query",
                "description": "Classify user query intent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string"},
                        "entities": {"type": "array"},
                        "complexity": {"type": "string", "enum": ["simple", "complex", "unclear"]},
                        "tools_needed": {"type": "array"}
                    }
                }
            }
        }
    ]
```

### 3. Task Planning Agent (GPT-4o)
**Role**: Complex query decomposition and workflow orchestration

**Responsibilities**:
- Decompose complex multi-step queries into executable workflows
- Generate LangGraph state machines dynamically
- Plan parallel vs sequential execution strategies
- Handle conditional logic and branching scenarios
- Optimize execution paths for performance

**OpenAI + LangGraph Integration**:
```python
class TaskPlanningAgent:
    model = "gpt-4o"
    temperature = 0.3
    
    def create_workflow(self, query_analysis):
        """Generate LangGraph workflow from query analysis"""
        workflow = StateGraph(QueryState)
        
        # Add nodes based on query requirements
        for step in self.decompose_query(query_analysis):
            workflow.add_node(step.name, step.executor)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "start",
            self.route_by_complexity,
            {
                "simple": "direct_execution",
                "complex": "multi_step_execution",
                "clarification_needed": "request_clarification"
            }
        )
        
        return workflow.compile()
```

### 4. Tool Coordination Agent (LangGraph + GPT-4o-mini)
**Role**: Intelligent orchestration of read-only NetBox MCP tools

**Responsibilities**:
- Select appropriate read-only NetBox MCP tools
- Coordinate multiple tool calls for complex queries
- Aggregate and optimize tool results 
- Handle known tool limitations gracefully
- Implement performance optimizations (caching, parallel execution)

**Implementation**:
```python
class ToolCoordinationAgent:
    model = "gpt-4o-mini"
    temperature = 0.1
    
    def __init__(self):
        self.read_only_tools = self.load_read_only_tools()
        self.known_limitations = self.load_known_issues()
        self.cache = PerformanceCache()
        self.result_aggregator = ResultAggregator()
    
    def coordinate_tools(self, query_plan: dict):
        """Orchestrate multiple tool calls with optimization"""
        try:
            # Check cache first
            cached_result = self.cache.get(query_plan)
            if cached_result:
                return cached_result
            
            # Handle known limitations
            if self.has_known_issues(query_plan):
                return self.apply_workaround(query_plan)
            
            # Execute tools (parallel where possible)
            results = self.execute_coordinated(query_plan)
            
            # Aggregate results
            aggregated = self.result_aggregator.combine(results)
            
            # Cache for future use
            self.cache.store(query_plan, aggregated)
            
            return aggregated
            
        except Exception as e:
            return self.handle_coordination_error(query_plan, e)
    
    def apply_workaround(self, query_plan: dict):
        """Apply known workarounds for tool limitations"""
        limitation_type = self.known_limitations.get(query_plan['primary_tool'])
        
        if limitation_type == "pagination_issue":
            return self.handle_pagination_workaround(query_plan)
        elif limitation_type == "n_plus_one_queries":
            return self.handle_n_plus_one_workaround(query_plan)
        elif limitation_type == "performance_issue":
            return self.handle_performance_workaround(query_plan)
        
        # Fallback to standard execution
        return self.execute_coordinated(query_plan)
```

### 5. Response Generation Agent (GPT-4o-mini)
**Role**: Natural language response formatting

**Responsibilities**:
- Convert structured tool outputs to natural language
- Format complex data into user-friendly responses
- Add helpful context and explanations
- Stream progress updates during operations
- Generate clarification questions when needed

**OpenAI Configuration**:
```python
class ResponseGenerationAgent:
    model = "gpt-4o-mini"
    temperature = 0.7
    
    system_prompt = """
    Convert structured NetBox data into natural, helpful responses.
    Add context and explanations that help users understand the results.
    Format complex data clearly and suggest follow-up actions.
    """
    
    def format_response(self, tool_result, user_context):
        """Convert tool result to natural language"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Format this result: {tool_result}"},
            ],
            temperature=self.temperature
        )
        return response.choices[0].message.content
```

## LangGraph Orchestration Architecture

### State Definition
```python
from typing import TypedDict, List, Dict, Any
from langgraph.graph import State

class QueryState(State):
    """Shared state across all agents"""
    # Input
    user_query: str
    conversation_history: List[Dict]
    
    # Processing
    intent: Dict[str, Any]
    execution_plan: Dict[str, Any]
    tool_results: Dict[str, Any]
    
    # Output
    final_response: str
    requires_clarification: bool
    clarification_questions: List[str]
    
    # Metadata
    session_id: str
    timestamp: str
    error_state: Dict[str, Any]
```

### Workflow Patterns

#### Simple Query Flow
```python
def create_simple_workflow():
    workflow = StateGraph(QueryState)
    
    workflow.add_node("parse_intent", intent_recognition_node)
    workflow.add_node("execute_tool", tool_execution_node)
    workflow.add_node("format_response", response_generation_node)
    
    workflow.add_edge("parse_intent", "execute_tool")
    workflow.add_edge("execute_tool", "format_response")
    
    workflow.set_entry_point("parse_intent")
    workflow.set_finish_point("format_response")
    
    return workflow.compile()
```

#### Complex Query Flow (Tool Orchestration)
```python
def create_orchestration_workflow():
    workflow = StateGraph(QueryState)
    
    workflow.add_node("parse_intent", intent_recognition_node)
    workflow.add_node("plan_coordination", task_planning_node)
    workflow.add_node("check_cache", cache_lookup_node)
    workflow.add_node("check_limitations", limitation_detection_node)
    workflow.add_node("apply_workaround", workaround_application_node)
    workflow.add_node("coordinate_tools", tool_coordination_node)
    workflow.add_node("aggregate_results", result_aggregation_node)
    workflow.add_node("format_response", response_generation_node)
    
    # Conditional routing for orchestration optimization
    workflow.add_conditional_edges(
        "check_cache",
        route_by_cache_status,
        {
            "cache_hit": "format_response",
            "cache_miss": "check_limitations"
        }
    )
    
    workflow.add_conditional_edges(
        "check_limitations", 
        route_by_known_issues,
        {
            "has_limitations": "apply_workaround",
            "no_limitations": "coordinate_tools"
        }
    )
    
    workflow.add_edge("apply_workaround", "aggregate_results")
    workflow.add_edge("coordinate_tools", "aggregate_results") 
    workflow.add_edge("aggregate_results", "format_response")
    
    return workflow.compile()
```

## Agent Communication Protocol

### Message Bus
```python
class AgentMessage:
    """Standard message format for inter-agent communication"""
    source: str          # Sending agent ID
    target: str          # Receiving agent ID or "broadcast"
    message_type: str    # request, response, error, progress
    content: Dict[str, Any]  # Message payload
    correlation_id: str  # Track related messages
    timestamp: str       # Message timestamp
    
class MessageBus:
    """Central message routing for agents"""
    def __init__(self):
        self.subscribers = {}
        self.message_history = []
    
    def publish(self, message: AgentMessage):
        """Route message to appropriate agents"""
        if message.target == "broadcast":
            for agent in self.subscribers.values():
                agent.handle_message(message)
        else:
            if message.target in self.subscribers:
                self.subscribers[message.target].handle_message(message)
```

### Error Handling Strategy
```python
class ErrorRecoverySystem:
    """Centralized error handling and recovery"""
    
    def handle_agent_error(self, agent_id: str, error: Exception, context: QueryState):
        """Handle agent failures with graceful degradation"""
        
        # Categorize error
        error_type = self.categorize_error(error)
        
        if error_type == "timeout":
            return self.handle_timeout(agent_id, context)
        elif error_type == "api_error":
            return self.handle_api_error(agent_id, error, context)
        elif error_type == "validation_error":
            return self.handle_validation_error(agent_id, error, context)
        else:
            return self.handle_unknown_error(agent_id, error, context)
    
    def handle_timeout(self, agent_id: str, context: QueryState):
        """Handle agent timeouts"""
        # Provide user feedback
        context.final_response = f"Operation is taking longer than expected. Would you like me to continue or try a different approach?"
        return context
```

## Essential Orchestration Features Implementation

### Known Issue Workaround System
```python
class LimitationHandler:
    """Handle known tool limitations with intelligent workarounds"""
    
    def __init__(self):
        self.known_issues = {
            "netbox_list_all_device_types": "pagination_issue",
            "netbox_list_all_vlans": "n_plus_one_queries", 
            "netbox_get_device_interfaces": "pagination_issue",
            "complex_infrastructure_audit": "performance_issue"
        }
    
    def apply_workaround(self, tool_name: str, query_context: dict):
        """Apply appropriate workaround for known limitations"""
        
        issue_type = self.known_issues.get(tool_name)
        
        if issue_type == "pagination_issue":
            return self.handle_pagination_gracefully(tool_name, query_context)
        elif issue_type == "n_plus_one_queries":
            return self.optimize_multiple_calls(tool_name, query_context)
        elif issue_type == "performance_issue":
            return self.handle_slow_operation(tool_name, query_context)
        
        return self.execute_with_monitoring(tool_name, query_context)
    
    def handle_pagination_gracefully(self, tool_name: str, context: dict):
        """Handle tools with pagination issues"""
        try:
            # Attempt normal execution with timeout
            result = self.execute_with_timeout(tool_name, context, timeout=10)
            return {"success": True, "data": result, "method": "direct"}
        except TimeoutError:
            # Fallback to user-friendly explanation
            return {
                "success": False,
                "error": "pagination_limitation",
                "message": f"The {tool_name} operation is experiencing known pagination issues. This is a tool limitation, not a user error.",
                "suggestion": "Try filtering your query to reduce the data size, or use related tools for more specific information."
            }
```

### Performance Optimization Engine
```python
class PerformanceOptimizer:
    """Optimize tool execution through caching and parallel processing"""
    
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache
        self.parallel_executor = ThreadPoolExecutor(max_workers=5)
    
    def optimize_execution(self, tool_plan: dict):
        """Apply performance optimizations to tool execution plan"""
        
        # Check cache for previous results
        cache_key = self.generate_cache_key(tool_plan)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Identify parallelizable operations
        parallel_ops, sequential_ops = self.classify_operations(tool_plan)
        
        # Execute with optimization
        if parallel_ops:
            parallel_results = self.execute_parallel(parallel_ops)
            sequential_results = self.execute_sequential(sequential_ops)
            combined_result = self.combine_results(parallel_results, sequential_results)
        else:
            combined_result = self.execute_sequential(sequential_ops)
        
        # Cache successful results
        self.cache[cache_key] = combined_result
        return combined_result
```

### Clarification Mechanism
```python
class ClarificationHandler:
    """Handle ambiguous queries with intelligent follow-up questions"""
    
    def __init__(self, response_agent: ResponseGenerationAgent):
        self.response_agent = response_agent
    
    def request_clarification(self, ambiguous_entities: List[str], context: QueryState):
        """Generate intelligent clarification questions"""
        
        questions = []
        for entity in ambiguous_entities:
            if entity == "device" and len(self.possible_devices) > 1:
                questions.append(f"Which device? I found: {', '.join(self.possible_devices[:5])}")
            elif entity == "site" and len(self.possible_sites) > 1:
                questions.append(f"Which site? Available: {', '.join(self.possible_sites)}")
            elif entity == "operation" and self.is_ambiguous_operation(context):
                questions.append(f"Would you like me to show a summary or detailed information?")
        
        context.requires_clarification = True
        context.clarification_questions = questions
        
        return context
```

### Progress Indication with Streaming
```python
class ProgressTracker:
    """Track and stream operation progress to users"""
    
    def __init__(self):
        self.progress_callbacks = []
        self.known_slow_operations = {
            "complex_infrastructure_audit": {"expected_time": 180, "steps": 8},
            "full_device_analysis": {"expected_time": 60, "steps": 5}
        }
    
    def report_progress(self, operation: str, step: int, total_steps: int, message: str):
        """Report progress with enhanced context for known slow operations"""
        
        progress_data = {
            "operation": operation,
            "progress": step / total_steps,
            "step": step,
            "total": total_steps,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add context for known slow operations
        if operation in self.known_slow_operations:
            expected = self.known_slow_operations[operation]
            progress_data["expected_duration"] = expected["expected_time"]
            progress_data["is_known_slow"] = True
            progress_data["optimization_note"] = "This operation has known performance limitations. Results will stream as available."
        
        for callback in self.progress_callbacks:
            callback(progress_data)
```

## Deployment Architecture

### Agent Lifecycle Management
```python
class AgentManager:
    """Manage agent lifecycle and health"""
    
    def __init__(self):
        self.agents = {}
        self.health_checker = HealthChecker()
    
    def start_agent(self, agent_type: str, config: Dict):
        """Start new agent instance"""
        agent = self.create_agent(agent_type, config)
        self.agents[agent.id] = agent
        agent.start()
        return agent.id
    
    def monitor_health(self):
        """Monitor agent health and restart if needed"""
        for agent_id, agent in self.agents.items():
            if not self.health_checker.is_healthy(agent):
                self.restart_agent(agent_id)
```

### Configuration Management
```python
class AgentConfiguration:
    """Centralized agent configuration"""
    
    conversation_manager = {
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
        "timeout": 30
    }
    
    intent_recognition = {
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "timeout": 10
    }
    
    task_planning = {
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_workflow_steps": 20,
        "timeout": 60
    }
```

## Success Metrics

### Performance Targets
- Intent recognition: < 500ms
- Tool execution: < 2s average
- Response generation: < 1s
- End-to-end query: < 3s for complex queries

### Quality Metrics
- Intent classification accuracy: > 95%
- Tool parameter extraction: > 98%
- Result validation: > 99%
- User satisfaction: > 90% positive feedback

### Reliability Metrics
- Agent availability: > 99.9%
- Error recovery: < 5s recovery time
- Message delivery: > 99.99% success rate
- Workflow completion: > 98% success rate

## Strategic Focus: Orchestration Intelligence

This architecture is specifically designed for **orchestration intelligence** rather than tool fixes:

### Core Principles
1. **Work WITH existing tools**: Coordinate and optimize existing NetBox MCP tools as-is
2. **Handle limitations gracefully**: Intelligent workarounds for known tool issues
3. **Enhance user experience**: Progress indication, clarification, and context management
4. **Optimize through coordination**: Caching, parallel execution, result aggregation

### What This Architecture Does NOT Do
- Fix NetBox MCP server tool implementations
- Resolve underlying tool performance issues 
- Modify existing tool pagination or N+1 query problems
- Change tool API contracts or behaviors

### What This Architecture DOES Do
- Provides intelligent coordination of existing tools
- Offers graceful handling of tool limitations with user-friendly explanations
- Implements performance optimizations at the orchestration layer
- Delivers enhanced user experience through conversational intelligence

## Future Considerations

This architecture provides foundation for:
1. Multi-user support through session isolation
2. State persistence through checkpointing
3. Advanced monitoring through metrics collection
4. Security through authentication layers
5. Scaling through agent distribution

The current implementation focuses on intelligent orchestration of existing tools while maintaining extensibility for production features in future phases.