# Technology Stack - Phase 3

## Overview
Technical components powering the OpenAI + LangGraph agentic orchestration system that replaces Claude Code CLI.

---

## OpenAI Components

### GPT-4o (Complex Reasoning)
**Usage**: Complex planning, supervision, and reasoning tasks

```python
# Configuration
MODEL = "gpt-4o"
TEMPERATURE = 0.7
MAX_TOKENS = 4096
TIMEOUT = 30

# Primary Use Cases
- Conversation management and orchestration
- Complex query decomposition and planning
- Multi-step workflow coordination
- High-level decision making
```

**Agents Using GPT-4o**:
- Conversation Manager Agent
- Task Planning Agent

### GPT-4o-mini (Fast Operations)
**Usage**: Fast, frequent operations requiring structured outputs

```python
# Configuration
MODEL = "gpt-4o-mini"  
TEMPERATURE = 0.1
TIMEOUT = 10
RESPONSE_FORMAT = {"type": "json_object"}

# Primary Use Cases
- Intent recognition and classification
- Tool parameter extraction
- Response generation and formatting
- Quick decision points
```

**Agents Using GPT-4o-mini**:
- Intent Recognition Agent
- Tool Execution Agent
- Response Generation Agent

### OpenAI Embeddings API
**Usage**: Semantic search and context retrieval

```python
# Configuration
MODEL = "text-embedding-3-small"
DIMENSIONS = 1536

# Primary Use Cases
- Conversation context search
- Tool similarity matching
- Entity relationship mapping
- Knowledge base queries
```

### OpenAI Function Calling
**Usage**: Structured tool integration

```python
# Example Tool Definition
tools = [
    {
        "type": "function",
        "function": {
            "name": "netbox_get_device_info",
            "description": "Get detailed device information from NetBox",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Name of the device"
                    },
                    "include_interfaces": {
                        "type": "boolean",
                        "description": "Include interface information"
                    }
                },
                "required": ["device_name"]
            }
        }
    }
]

# Usage in agents
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
    tool_choice="auto"
)
```

---

## LangGraph Components

### State Machines
**Usage**: Workflow orchestration and control flow

```python
from langgraph.graph import StateGraph, State

class QueryState(State):
    user_query: str
    intent: dict
    tool_results: dict
    final_response: str

# Workflow Definition
workflow = StateGraph(QueryState)
workflow.add_node("parse_intent", intent_node)
workflow.add_node("execute_tools", tool_node)
workflow.add_node("format_response", response_node)
```

### Conditional Edges
**Usage**: Dynamic routing based on OpenAI decisions

```python
# Conditional Routing Example
workflow.add_conditional_edges(
    "parse_intent",
    route_by_complexity,
    {
        "simple": "execute_tools",
        "complex": "plan_tasks",
        "unclear": "request_clarification"
    }
)

def route_by_complexity(state: QueryState):
    if state.intent.get("complexity") == "simple":
        return "simple"
    elif state.intent.get("requires_clarification"):
        return "unclear"
    else:
        return "complex"
```

### Checkpointing
**Usage**: State persistence and recovery

```python
from langgraph.checkpoint import MemorySaver

# Enable checkpointing
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# Execute with state tracking
result = app.invoke(
    {"user_query": "Show devices"},
    config={"configurable": {"thread_id": "session_123"}}
)
```

### Message Passing
**Usage**: Inter-agent communication

```python
from langgraph.graph import MessageGraph

# Agent Communication
class AgentMessage:
    source: str
    target: str
    content: dict
    correlation_id: str

# Message routing
message_graph = MessageGraph()
message_graph.add_node("conversation_manager", conversation_agent)
message_graph.add_node("intent_recognition", intent_agent)
message_graph.add_edge("conversation_manager", "intent_recognition")
```

### Supervisor Pattern
**Usage**: Hierarchical agent coordination

```python
# Supervisor Configuration
class SupervisorConfig:
    supervisor_agent = "conversation_manager"
    worker_agents = [
        "intent_recognition",
        "tool_execution", 
        "response_generation"
    ]
    coordination_strategy = "sequential"
    error_handling = "graceful_degradation"
```

---

## Integration Components

### Python Core Stack
```python
# Core Dependencies
python = "^3.10"
openai = "^1.12.0"
langgraph = "^0.2.0"
langchain = "^0.3.0"
fastapi = "^0.108.0"
pydantic = "^2.5.0"
asyncio = "built-in"
typing = "built-in"
```

### NetBox MCP Integration (Read-Only Focus)
```python
# Read-Only MCP Tool Registry
from netbox_mcp.tools import (
    # Discovery Tools
    netbox_get_device_info,
    netbox_list_all_devices,
    netbox_list_all_sites,
    netbox_list_all_racks,
    # Analysis Tools
    netbox_get_ip_usage,
    netbox_get_tenant_resource_report,
    # Health Tools
    netbox_health_check,
    # ... read-only tools focused on orchestration
)

# Intelligent Tool Coordination
class MCPToolOrchestrator:
    def __init__(self):
        self.read_only_tools = self.discover_read_only_tools()
        self.known_limitations = self.load_known_issues()
    
    def discover_read_only_tools(self):
        """Auto-discover read-only MCP tools for orchestration"""
        tools = {}
        READ_ONLY_OPERATIONS = ["get_", "list_", "health_", "find_"]
        
        for module in netbox_mcp_modules:
            for func in get_mcp_functions(module):
                # Focus on read-only operations
                if any(op in func.__name__ for op in READ_ONLY_OPERATIONS):
                    tools[func.__name__] = func
        return tools
    
    def load_known_issues(self):
        """Known tool limitations to work around"""
        return {
            "netbox_list_all_device_types": "pagination_issue",
            "netbox_list_all_vlans": "n_plus_one_queries", 
            "netbox_get_device_interfaces": "pagination_issue",
            "complex_infrastructure_audit": "performance_issue"
        }
    
    def to_openai_format(self):
        """Convert to OpenAI function calling format with orchestration metadata"""
        openai_tools = []
        for name, func in self.read_only_tools.items():
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": func.__doc__,
                    "parameters": extract_parameters(func),
                    "orchestration_metadata": {
                        "known_issues": self.known_limitations.get(name),
                        "performance_tier": self.classify_performance(name),
                        "aggregation_capable": self.supports_aggregation(name)
                    }
                }
            })
        return openai_tools
```

### Async Processing
```python
import asyncio
from typing import List, Dict, Any

# Concurrent Operation Handling
class AsyncOrchestrator:
    async def execute_parallel(self, operations: List[Dict]):
        """Execute operations concurrently"""
        tasks = []
        for op in operations:
            task = asyncio.create_task(self.execute_operation(op))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self.process_results(results)
    
    async def execute_sequential(self, operations: List[Dict]):
        """Execute operations in sequence"""
        results = []
        for op in operations:
            result = await self.execute_operation(op)
            results.append(result)
            
            # Pass result to next operation if needed
            if op.get("pass_result_to_next"):
                operations[operations.index(op) + 1]["context"] = result
                
        return results
```

### Error Handling Framework
```python
class ErrorHandlingSystem:
    """Centralized error handling for all components"""
    
    def __init__(self):
        self.error_strategies = {
            "openai_api_error": self.handle_openai_error,
            "tool_execution_error": self.handle_tool_error,
            "langgraph_error": self.handle_workflow_error,
            "timeout_error": self.handle_timeout_error
        }
    
    async def handle_error(self, error: Exception, context: Dict):
        """Route errors to appropriate handlers"""
        error_type = self.classify_error(error)
        handler = self.error_strategies.get(error_type, self.handle_unknown_error)
        return await handler(error, context)
    
    async def handle_openai_error(self, error, context):
        """Handle OpenAI API errors with retry logic"""
        if "rate_limit" in str(error):
            await asyncio.sleep(2 ** context.get("retry_count", 0))
            return {"action": "retry", "delay": True}
        elif "context_length" in str(error):
            return {"action": "truncate_context", "max_tokens": 2000}
        else:
            return {"action": "fallback", "message": "OpenAI service temporarily unavailable"}
```

---

## Monitoring & Observability

### Logging Configuration
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """JSON logging for agent operations"""
    
    def __init__(self, component: str):
        self.component = component
        self.logger = logging.getLogger(component)
        
    def log_agent_action(self, agent: str, action: str, context: Dict):
        """Log agent actions with structured data"""
        self.logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "component": self.component,
            "agent": agent,
            "action": action,
            "context": context,
            "correlation_id": context.get("correlation_id")
        }))
```

### Performance Metrics
```python
import time
from functools import wraps

def measure_performance(func):
    """Decorator to measure agent performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Log performance metrics
            logger.info({
                "function": func.__name__,
                "duration": duration,
                "success": True
            })
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error({
                "function": func.__name__,
                "duration": duration,
                "success": False,
                "error": str(e)
            })
            
            raise
            
    return wrapper
```

---

## Configuration Management

### Environment Configuration
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout: int = 30
    
    # LangGraph Configuration  
    langgraph_checkpoint_backend: str = "memory"
    langgraph_max_steps: int = 100
    
    # NetBox Configuration
    netbox_url: str
    netbox_token: str
    netbox_timeout: int = 30
    
    # Agent Configuration
    conversation_model: str = "gpt-4o"
    intent_model: str = "gpt-4o-mini"
    max_conversation_turns: int = 50
    
    # Performance Configuration
    max_concurrent_operations: int = 10
    default_timeout: int = 60
    retry_attempts: int = 3
    
    class Config:
        env_file = ".env"
        env_prefix = "NETBOX_AGENT_"
```

### Agent Configuration
```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class AgentConfig:
    name: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    system_prompt: str
    tools: List[Dict] = None

# Predefined Configurations
AGENT_CONFIGS = {
    "conversation_manager": AgentConfig(
        name="conversation_manager",
        model="gpt-4o",
        temperature=0.7,
        max_tokens=4096,
        timeout=30,
        system_prompt="You are the Conversation Manager for NetBox operations..."
    ),
    
    "intent_recognition": AgentConfig(
        name="intent_recognition", 
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=1000,
        timeout=10,
        system_prompt="Classify user queries and extract entities..."
    )
}
```

---

## Development Tools

### Testing Framework
```python
import pytest
from unittest.mock import AsyncMock
from langgraph.graph.state import CompiledStateGraph

class AgentTestFramework:
    """Testing utilities for agent system"""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing"""
        client = AsyncMock()
        client.chat.completions.create = AsyncMock()
        return client
    
    @pytest.fixture  
    def mock_workflow(self):
        """Mock LangGraph workflow"""
        workflow = AsyncMock(spec=CompiledStateGraph)
        return workflow
    
    async def test_agent_response(self, agent, input_query, expected_output):
        """Test individual agent responses"""
        result = await agent.process(input_query)
        assert result["success"] == True
        assert expected_output in result["response"]
```

### Development Environment
```python
# Development Dependencies
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.0.0"
isort = "^5.12.0"
mypy = "^1.5.0"
flake8 = "^6.0.0"
pre-commit = "^3.4.0"

# Pre-commit hooks
repos:
  - repo: local
    hooks:
      - id: black
        name: black
        entry: black
        language: python
        types: [python]
      
      - id: isort
        name: isort
        entry: isort
        language: python
        types: [python]
      
      - id: mypy
        name: mypy
        entry: mypy
        language: python
        types: [python]
```

---

## Deployment Architecture

### Container Configuration
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Configure environment
ENV PYTHONPATH=/app
ENV NETBOX_AGENT_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["python", "-m", "netbox_agent.main"]
```

### Service Architecture
```yaml
# docker-compose.yml
version: '3.8'
services:
  netbox-agent:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - NETBOX_URL=${NETBOX_URL}
      - NETBOX_TOKEN=${NETBOX_TOKEN}
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

---

## Summary

This technology stack provides:

1. **OpenAI Integration**: Powerful language models for natural language understanding and coordination
2. **LangGraph Orchestration**: Sophisticated workflow management for multi-step operations
3. **Read-Only Tool Orchestration**: Intelligent coordination of existing NetBox MCP tools
4. **Performance Optimization**: Caching, parallel execution, and known issue workarounds
5. **Error Resilience**: Comprehensive error handling and graceful degradation
6. **Observability**: Structured logging and performance monitoring
7. **User Experience**: Progress indication, clarification, and context management

The stack is designed for intelligent orchestration of existing tools rather than fixing underlying tool issues, focusing on enhanced user experience through coordination intelligence.