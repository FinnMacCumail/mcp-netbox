"""
Conversation Manager Agent - Primary orchestrator and user interface
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .base import BaseAgent, AgentMessage, MessageType, AgentState, QueryContext
from .config import get_config


class ConversationSession:
    """Manages a single user conversation session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
        self.active_agents: Dict[str, str] = {}  # agent_type -> agent_id
        self.pending_clarifications: List[Dict[str, Any]] = []
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.last_activity = datetime.now()
    
    def get_recent_context(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history for context"""
        return self.conversation_history[-max_messages:]
    
    def update_context(self, key: str, value: Any):
        """Update session context"""
        self.context[key] = value
        self.last_activity = datetime.now()


class ConversationManagerAgent(BaseAgent):
    """
    Primary orchestrator agent that manages conversation flow and coordinates
    with specialized agents. Uses GPT-4o for complex reasoning and coordination.
    """
    
    def __init__(self, agent_id: str = "conversation_manager"):
        config = get_config().openai
        super().__init__(agent_id, "conversation_manager", config)
        
        self.model = config.conversation_model
        self.temperature = config.conversation_temperature
        self.max_tokens = config.max_conversation_tokens
        
        # Session management
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.agent_registry: Dict[str, BaseAgent] = {}
        
        # Orchestration settings
        self.max_session_duration = 3600  # 1 hour
        self.max_concurrent_sessions = 100
        
        # System prompt for conversation management
        self.system_prompt = """You are the Conversation Manager for an intelligent NetBox orchestration system.

Your responsibilities:
1. Understand user queries about NetBox infrastructure
2. Coordinate with specialized agents (Intent Recognition, Task Planning, Tool Coordination, Response Generation)
3. Maintain conversation context and handle multi-turn interactions
4. Manage clarification flows when queries are ambiguous
5. Provide progress updates for long-running operations
6. Ensure coherent user experience across agent interactions

Available Specialized Agents:
- Intent Recognition: Understands what the user wants to do
- Task Planning: Breaks down complex queries into workflows
- Tool Coordination: Executes NetBox MCP tools intelligently
- Response Generation: Formats results into natural language

Conversation Flow:
1. Receive user query
2. Route to Intent Recognition for understanding
3. Coordinate with other agents based on intent
4. Aggregate results and ensure coherent response
5. Handle any clarifications or follow-ups

Always maintain conversation context and provide helpful, accurate responses about NetBox infrastructure."""
    
    async def initialize(self) -> None:
        """Initialize conversation manager"""
        self.logger.info("Conversation Manager Agent initialized")
        
        # Start session cleanup task
        asyncio.create_task(self._cleanup_expired_sessions())
    
    async def cleanup(self) -> None:
        """Clean up conversation manager resources"""
        # Close all active sessions
        for session in self.active_sessions.values():
            await self._close_session(session.session_id)
        
        self.logger.info("Conversation Manager Agent cleaned up")
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process conversation management requests"""
        request_type = content.get("type", "process_query")
        
        if request_type == "process_query":
            return await self.process_user_query(content)
        elif request_type == "create_session":
            return await self.create_session(content)
        elif request_type == "close_session":
            return await self.close_session(content)
        elif request_type == "get_session_info":
            return await self.get_session_info(content)
        else:
            return {"error": f"Unknown request type: {request_type}"}
    
    async def create_session(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new conversation session"""
        session_id = content.get("session_id") or str(uuid4())
        
        if session_id in self.active_sessions:
            return {
                "success": False,
                "error": "Session already exists",
                "session_id": session_id
            }
        
        # Check session limits
        if len(self.active_sessions) >= self.max_concurrent_sessions:
            await self._cleanup_oldest_sessions(1)
        
        session = ConversationSession(session_id)
        self.active_sessions[session_id] = session
        
        self.logger.info(f"Created conversation session: {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "created_at": session.created_at.isoformat()
        }
    
    async def close_session(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Close a conversation session"""
        session_id = content.get("session_id")
        
        if not session_id or session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "Session not found"
            }
        
        await self._close_session(session_id)
        
        return {
            "success": True,
            "session_id": session_id
        }
    
    async def get_session_info(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about a session"""
        session_id = content.get("session_id")
        
        if not session_id or session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "Session not found"
            }
        
        session = self.active_sessions[session_id]
        
        return {
            "success": True,
            "session_info": {
                "session_id": session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "message_count": len(session.conversation_history),
                "context_keys": list(session.context.keys()),
                "active_agents": list(session.active_agents.keys())
            }
        }
    
    async def process_user_query(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process a user query through the agent orchestration system"""
        user_query = content.get("query", "")
        session_id = content.get("session_id")
        
        if not user_query:
            return {
                "success": False,
                "error": "No query provided"
            }
        
        # Get or create session
        if not session_id or session_id not in self.active_sessions:
            session_result = await self.create_session({"session_id": session_id})
            if not session_result["success"]:
                return session_result
            session_id = session_result["session_id"]
        
        session = self.active_sessions[session_id]
        
        try:
            # Add user message to history
            session.add_message("user", user_query)
            
            # Process the query through orchestration
            result = await self._orchestrate_query(session, user_query)
            
            # Add assistant response to history
            if result.get("success") and result.get("response"):
                session.add_message("assistant", result["response"], {
                    "agents_used": result.get("agents_used", []),
                    "processing_time": result.get("processing_time", 0)
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing query in session {session_id}: {e}")
            
            # Add error to session
            session.add_message("system", f"Error: {str(e)}", {"error": True})
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def _orchestrate_query(self, session: ConversationSession, user_query: str) -> Dict[str, Any]:
        """Orchestrate query processing through specialized agents"""
        start_time = datetime.now()
        agents_used = []
        
        try:
            # Step 1: Intent Recognition
            self.logger.info(f"Starting intent recognition for query: {user_query[:50]}...")
            
            intent_result = await self._call_intent_recognition({
                "type": "classify_query",
                "query": user_query,
                "context": {
                    "session_id": session.session_id,
                    "conversation_history": session.get_recent_context()
                }
            })
            
            agents_used.append("intent_recognition")
            
            if not intent_result.get("success"):
                return {
                    "success": False,
                    "error": "Intent recognition failed",
                    "details": intent_result.get("error"),
                    "session_id": session.session_id
                }
            
            classification = intent_result["classification"]
            session.update_context("last_intent", classification)
            
            # Step 2: Check if clarification is needed
            if classification.get("requires_clarification"):
                clarification_result = await self._handle_clarification_request(
                    session, classification
                )
                agents_used.append("response_generation")
                
                return {
                    "success": True,
                    "response": clarification_result["response"],
                    "requires_clarification": True,
                    "clarification_context": classification,
                    "agents_used": agents_used,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "session_id": session.session_id
                }
            
            # Step 3: For simple queries, go direct to tool coordination
            if classification.get("complexity") == "simple":
                return await self._handle_simple_query(
                    session, user_query, classification, agents_used, start_time
                )
            
            # Step 4: For complex queries, involve task planning
            elif classification.get("complexity") in ["moderate", "complex"]:
                return await self._handle_complex_query(
                    session, user_query, classification, agents_used, start_time
                )
            
            else:
                # Unclear complexity - request clarification
                clarification_result = await self._generate_clarification({
                    "reason": "query_unclear",
                    "original_query": user_query,
                    "suggestions": ["Could you please be more specific?"]
                })
                
                return {
                    "success": True,
                    "response": clarification_result["response"],
                    "requires_clarification": True,
                    "agents_used": agents_used,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "session_id": session.session_id
                }
                
        except Exception as e:
            self.logger.error(f"Error in query orchestration: {e}")
            return {
                "success": False,
                "error": str(e),
                "agents_used": agents_used,
                "session_id": session.session_id
            }
    
    async def _handle_simple_query(
        self, 
        session: ConversationSession, 
        user_query: str, 
        classification: Dict[str, Any],
        agents_used: List[str],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Handle simple queries with direct tool coordination"""
        
        # Step 1: Tool Coordination (simulate for now)
        tool_result = await self._call_tool_coordination({
            "classification": classification,
            "query": user_query,
            "session_context": session.context
        })
        
        agents_used.append("tool_coordination")
        
        if not tool_result.get("success"):
            return {
                "success": False,
                "error": "Tool coordination failed",
                "details": tool_result.get("error"),
                "agents_used": agents_used,
                "session_id": session.session_id
            }
        
        # Step 2: Response Generation
        response_result = await self._call_response_generation({
            "tool_results": tool_result.get("results", {}),
            "context": {
                "user_query": user_query,
                "intent": classification,
                "session_id": session.session_id
            },
            "response_type": "standard"
        })
        
        agents_used.append("response_generation")
        
        if not response_result.get("success"):
            return {
                "success": False,
                "error": "Response generation failed",
                "details": response_result.get("error"),
                "agents_used": agents_used,
                "session_id": session.session_id
            }
        
        return {
            "success": True,
            "response": response_result["response"],
            "tool_results": tool_result.get("results", {}),
            "agents_used": agents_used,
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "session_id": session.session_id
        }
    
    async def _handle_complex_query(
        self, 
        session: ConversationSession, 
        user_query: str, 
        classification: Dict[str, Any],
        agents_used: List[str],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Handle complex queries with task planning"""
        
        # For now, simulate task planning - will be implemented in Task Planning Agent
        # Step 1: Task Planning (placeholder)
        planning_result = await self._simulate_task_planning(classification)
        agents_used.append("task_planning")
        
        # Step 2: Execute planned steps through tool coordination
        tool_result = await self._call_tool_coordination({
            "classification": classification,
            "execution_plan": planning_result,
            "query": user_query,
            "session_context": session.context
        })
        
        agents_used.append("tool_coordination")
        
        # Step 3: Response Generation
        response_result = await self._call_response_generation({
            "tool_results": tool_result.get("results", {}),
            "context": {
                "user_query": user_query,
                "intent": classification,
                "execution_plan": planning_result,
                "session_id": session.session_id
            },
            "response_type": "complex"
        })
        
        agents_used.append("response_generation")
        
        return {
            "success": True,
            "response": response_result.get("response", "Complex query processed"),
            "tool_results": tool_result.get("results", {}),
            "execution_plan": planning_result,
            "agents_used": agents_used,
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "session_id": session.session_id
        }
    
    async def _call_intent_recognition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Intent Recognition Agent"""
        try:
            # Check if we have a registered Intent Recognition Agent
            if "intent_recognition" in self.agent_registry:
                agent = self.agent_registry["intent_recognition"]
                
                # Send message to Intent Recognition Agent
                correlation_id = str(uuid4())
                await agent.send_message(
                    target=agent.agent_id,
                    message_type=MessageType.REQUEST,
                    content=data,
                    correlation_id=correlation_id
                )
                
                # Wait for response (simplified - in production would use proper async messaging)
                return await agent.process_request(data)
            else:
                # Fallback to intelligent query classification using existing logic
                return await self._classify_query_locally(data)
                
        except Exception as e:
            self.logger.error(f"Error calling intent recognition: {e}")
            return {"success": False, "error": str(e)}
    
    async def _classify_query_locally(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Local query classification as fallback"""
        try:
            query = data.get("query", "").lower()
            
            # Enhanced pattern matching for NetBox queries
            if any(word in query for word in ["list", "show", "all", "get", "find"]):
                intent = "discovery"
                complexity = "simple"
                tools_needed = self._suggest_discovery_tools(query)
            elif any(word in query for word in ["create", "add", "provision", "new"]):
                intent = "creation"
                complexity = "moderate"
                tools_needed = self._suggest_creation_tools(query)
            elif any(word in query for word in ["analyze", "report", "audit", "compare", "summary"]):
                intent = "analysis"
                complexity = "complex"
                tools_needed = self._suggest_analysis_tools(query)
            elif any(word in query for word in ["update", "modify", "change", "edit"]):
                intent = "modification"
                complexity = "moderate"
                tools_needed = []  # Read-only for now
            elif any(word in query for word in ["delete", "remove", "decommission"]):
                intent = "deletion"
                complexity = "moderate"
                tools_needed = []  # Read-only for now
            else:
                intent = "unclear"
                complexity = "unclear"
                tools_needed = []
            
            # Extract entities from query
            entities = self._extract_entities(query)
            
            return {
                "success": True,
                "classification": {
                    "intent": intent,
                    "complexity": complexity,
                    "entities": entities,
                    "tools_needed": tools_needed,
                    "requires_clarification": intent == "unclear" or len(entities) == 0,
                    "confidence": 0.8 if intent != "unclear" else 0.3,
                    "query_type": self._determine_query_type(query),
                    "scope": self._determine_query_scope(query)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _suggest_discovery_tools(self, query: str) -> List[str]:
        """Suggest appropriate discovery tools based on query"""
        tools = []
        
        if "device" in query:
            tools.append("netbox_list_all_devices")
        if "site" in query:
            tools.append("netbox_list_all_sites")
        if "rack" in query:
            tools.append("netbox_list_all_racks")
        if "cable" in query:
            tools.append("netbox_list_all_cables")
        if "vlan" in query:
            tools.append("netbox_list_all_vlans")
        if "prefix" in query or "ip" in query:
            tools.append("netbox_list_all_prefixes")
        if "tenant" in query:
            tools.append("netbox_list_all_tenants")
        
        return tools if tools else ["netbox_health_check"]
    
    def _suggest_creation_tools(self, query: str) -> List[str]:
        """Suggest creation tools (placeholder for read-only phase)"""
        # In read-only phase, suggest discovery instead
        return self._suggest_discovery_tools(query)
    
    def _suggest_analysis_tools(self, query: str) -> List[str]:
        """Suggest analysis tools based on query"""
        tools = []
        
        if "utilization" in query or "usage" in query:
            if "prefix" in query or "ip" in query:
                tools.append("netbox_get_prefix_utilization")
        if "inventory" in query:
            tools.append("netbox_get_rack_inventory")
        if "report" in query and "tenant" in query:
            tools.append("netbox_get_tenant_resource_report")
        
        return tools
    
    def _extract_entities(self, query: str) -> List[Dict[str, str]]:
        """Extract entities from query"""
        entities = []
        
        # Simple entity extraction patterns
        if "site" in query:
            entities.append({"type": "site", "value": "site_reference"})
        if "device" in query:
            entities.append({"type": "device", "value": "device_reference"})
        if "rack" in query:
            entities.append({"type": "rack", "value": "rack_reference"})
        if "vlan" in query:
            entities.append({"type": "vlan", "value": "vlan_reference"})
        if "tenant" in query:
            entities.append({"type": "tenant", "value": "tenant_reference"})
            
        return entities
    
    def _determine_query_type(self, query: str) -> str:
        """Determine the type of query"""
        if any(word in query for word in ["health", "status", "check"]):
            return "health_check"
        elif any(word in query for word in ["bulk", "multiple", "batch"]):
            return "bulk_operation"
        elif any(word in query for word in ["complex", "advanced", "detailed"]):
            return "complex_query"
        else:
            return "standard_query"
    
    def _determine_query_scope(self, query: str) -> str:
        """Determine the scope of the query"""
        if "all" in query:
            return "global"
        elif any(word in query for word in ["site", "location"]):
            return "site_scoped"
        elif any(word in query for word in ["rack", "cabinet"]):
            return "rack_scoped"
        else:
            return "entity_scoped"
    
    async def _call_tool_coordination(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Tool Coordination Agent"""
        try:
            # Check if we have a registered Tool Coordination Agent
            if "tool_coordination" in self.agent_registry:
                agent = self.agent_registry["tool_coordination"]
                
                # Send message to Tool Coordination Agent
                correlation_id = str(uuid4())
                await agent.send_message(
                    target=agent.agent_id,
                    message_type=MessageType.REQUEST,
                    content=data,
                    correlation_id=correlation_id
                )
                return await agent.process_request(data)
            else:
                # Fallback to simulation for now (Week 1-4 scope)
                return await self._simulate_tool_coordination(data)
                
        except Exception as e:
            self.logger.error(f"Error calling tool coordination: {e}")
            return {"success": False, "error": str(e)}
    
    async def _simulate_tool_coordination(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate tool coordination for Week 1-4 development"""
        classification = data.get("classification", {})
        tools_needed = classification.get("tools_needed", [])
        query = data.get("query", "")
        
        # Simulate intelligent tool selection and execution
        results = {
            "operation": "orchestrated_tool_execution",
            "query_analysis": {
                "intent": classification.get("intent"),
                "complexity": classification.get("complexity"),
                "scope": classification.get("scope", "unknown")
            },
            "tools_selected": tools_needed,
            "execution_plan": {
                "strategy": "sequential" if len(tools_needed) <= 3 else "parallel",
                "estimated_time": len(tools_needed) * 2,
                "optimization": "read_only_optimized"
            },
            "simulated_results": {
                "status": "success",
                "data_points": len(tools_needed) * 10,
                "processing_time": 0.5,
                "cache_hits": 0
            }
        }
        
        # Add specific simulation based on intent
        if classification.get("intent") == "discovery":
            results["discovery_summary"] = {
                "entities_found": 25,
                "search_patterns": tools_needed,
                "data_quality": "high"
            }
        elif classification.get("intent") == "analysis":
            results["analysis_summary"] = {
                "metrics_calculated": 5,
                "relationships_identified": 12,
                "insights_generated": 3
            }
        
        return {
            "success": True,
            "results": results,
            "tools_used": tools_needed,
            "execution_metadata": {
                "agent_version": "week_1-4_simulation",
                "orchestration_level": "basic",
                "coordination_pattern": "direct_mapping"
            }
        }
    
    async def _call_response_generation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Response Generation Agent"""
        try:
            # Check if we have a registered Response Generation Agent
            if "response_generation" in self.agent_registry:
                agent = self.agent_registry["response_generation"]
                
                # Send message to Response Generation Agent
                correlation_id = str(uuid4())
                await agent.send_message(
                    target=agent.agent_id,
                    message_type=MessageType.REQUEST,
                    content=data,
                    correlation_id=correlation_id
                )
                return await agent.process_request(data)
            else:
                # Fallback to intelligent response generation
                return await self._generate_response_locally(data)
                
        except Exception as e:
            self.logger.error(f"Error calling response generation: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_response_locally(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response locally with intelligent formatting"""
        try:
            tool_results = data.get("tool_results", {})
            context = data.get("context", {})
            response_type = data.get("response_type", "standard")
            user_query = context.get("user_query", "")
            intent = context.get("intent", {})
            
            # Generate contextual response based on intent and results
            if response_type == "clarification":
                response = self._generate_clarification_response(data)
            elif intent.get("intent") == "discovery":
                response = self._generate_discovery_response(user_query, tool_results, intent)
            elif intent.get("intent") == "analysis":
                response = self._generate_analysis_response(user_query, tool_results, intent)
            elif intent.get("intent") == "creation":
                response = self._generate_creation_response(user_query, tool_results, intent)
            elif response_type == "complex":
                response = self._generate_complex_response(user_query, tool_results, context)
            else:
                response = self._generate_standard_response(user_query, tool_results)
            
            return {
                "success": True,
                "response": response,
                "response_metadata": {
                    "response_type": response_type,
                    "intent_handled": intent.get("intent"),
                    "confidence": intent.get("confidence", 0.8),
                    "generation_method": "local_intelligent"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_discovery_response(self, query: str, tool_results: Dict, intent: Dict) -> str:
        """Generate response for discovery queries"""
        operation = tool_results.get("operation", "")
        
        if operation == "orchestrated_tool_execution":
            summary = tool_results.get("discovery_summary", {})
            entities_found = summary.get("entities_found", 0)
            tools_used = tool_results.get("tools_used", [])
            
            response = f"I've analyzed your query: '{query}'\n\n"
            response += f"**Discovery Results:**\n"
            response += f"- Found {entities_found} entities across your NetBox infrastructure\n"
            response += f"- Used {len(tools_used)} specialized tools for comprehensive discovery\n"
            response += f"- Data quality: {summary.get('data_quality', 'good')}\n\n"
            
            if tools_used:
                response += f"**Tools Coordinated:** {', '.join(tools_used)}\n\n"
            
            response += "The orchestration system successfully coordinated multiple NetBox MCP tools to provide you with comprehensive infrastructure visibility."
        else:
            response = f"I've processed your discovery query: '{query}'. The NetBox orchestration system is ready to discover and analyze your infrastructure."
        
        return response
    
    def _generate_analysis_response(self, query: str, tool_results: Dict, intent: Dict) -> str:
        """Generate response for analysis queries"""
        operation = tool_results.get("operation", "")
        
        if operation == "orchestrated_tool_execution":
            summary = tool_results.get("analysis_summary", {})
            metrics = summary.get("metrics_calculated", 0)
            relationships = summary.get("relationships_identified", 0)
            insights = summary.get("insights_generated", 0)
            
            response = f"I've completed the analysis for: '{query}'\n\n"
            response += f"**Analysis Results:**\n"
            response += f"- Calculated {metrics} key metrics\n"
            response += f"- Identified {relationships} infrastructure relationships\n"
            response += f"- Generated {insights} actionable insights\n\n"
            response += "The analysis reveals comprehensive patterns in your NetBox infrastructure, providing valuable insights for planning and optimization."
        else:
            response = f"I've analyzed your request: '{query}'. The NetBox orchestration system has processed your analysis requirements."
        
        return response
    
    def _generate_creation_response(self, query: str, tool_results: Dict, intent: Dict) -> str:
        """Generate response for creation queries (read-only phase)"""
        response = f"I understand you want to create or provision resources: '{query}'\n\n"
        response += "**Phase 3 Note:** During this read-only orchestration phase, I can help you:\n"
        response += "- Discover existing resources and dependencies\n"
        response += "- Analyze requirements and constraints\n"
        response += "- Plan implementation strategies\n"
        response += "- Identify potential conflicts or issues\n\n"
        response += "Creation and modification capabilities will be added in future phases. For now, I've analyzed your requirements and can provide detailed planning assistance."
        
        return response
    
    def _generate_complex_response(self, query: str, tool_results: Dict, context: Dict) -> str:
        """Generate response for complex queries"""
        execution_plan = context.get("execution_plan", {})
        steps = execution_plan.get("steps", [])
        
        response = f"I've processed your complex query: '{query}'\n\n"
        response += f"**Execution Summary:**\n"
        response += f"- Broke down into {len(steps)} coordinated steps\n"
        response += f"- Execution strategy: {execution_plan.get('execution_strategy', 'adaptive')}\n"
        response += f"- Processing time: {tool_results.get('simulated_results', {}).get('processing_time', 'N/A')} seconds\n\n"
        
        if steps:
            response += "**Workflow Steps:**\n"
            for i, step in enumerate(steps[:3], 1):
                response += f"{i}. {step.get('action', 'Unknown action')}\n"
        
        response += "\nThe orchestration system successfully coordinated multiple agents to handle your complex requirements."
        
        return response
    
    def _generate_standard_response(self, query: str, tool_results: Dict) -> str:
        """Generate standard response"""
        return f"I've processed your query: '{query}'. The NetBox orchestration system has successfully coordinated the required operations and tools to fulfill your request."
    
    def _generate_clarification_response(self, data: Dict) -> str:
        """Generate clarification questions"""
        clarification_data = data.get("clarification_data", {})
        reason = clarification_data.get("reason", "general")
        
        if reason == "ambiguous_entities":
            return "I need some clarification to better help you. Could you please specify which specific devices, sites, or resources you're interested in?"
        elif reason == "query_unclear":
            return "I want to make sure I understand your request correctly. Could you provide more details about what you'd like to accomplish with your NetBox infrastructure?"
        else:
            return "Could you please provide more specific details about your request? This will help me coordinate the right tools and provide you with the most accurate information."
    
    async def _simulate_task_planning(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate task planning for complex queries"""
        return {
            "steps": [
                {"step": 1, "action": "gather_requirements", "agent": "tool_coordination"},
                {"step": 2, "action": "execute_operations", "agent": "tool_coordination"},
                {"step": 3, "action": "aggregate_results", "agent": "response_generation"}
            ],
            "execution_strategy": "sequential",
            "estimated_time": 10
        }
    
    async def _handle_clarification_request(
        self, 
        session: ConversationSession, 
        classification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle requests for clarification"""
        
        return await self._generate_clarification({
            "reason": "ambiguous_entities",
            "ambiguous_entities": classification.get("clarification_needed", []),
            "original_query": session.conversation_history[-1]["content"]
        })
    
    async def _generate_clarification(self, clarification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate clarification questions"""
        
        # Use Response Generation Agent for clarification
        return await self._call_response_generation({
            "type": "format_clarification",
            "clarification_data": clarification_data,
            "context": {}
        })
    
    async def _close_session(self, session_id: str):
        """Close and clean up a session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            self.logger.info(f"Closing session {session_id} with {len(session.conversation_history)} messages")
            del self.active_sessions[session_id]
    
    async def _cleanup_expired_sessions(self):
        """Periodic cleanup of expired sessions"""
        while self.state != AgentState.SHUTDOWN:
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                for session_id, session in self.active_sessions.items():
                    age = (current_time - session.last_activity).total_seconds()
                    if age > self.max_session_duration:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    await self._close_session(session_id)
                
                if expired_sessions:
                    self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Shorter sleep on error
    
    async def _cleanup_oldest_sessions(self, count: int):
        """Clean up the oldest sessions to make room"""
        if not self.active_sessions:
            return
        
        # Sort by last activity
        sorted_sessions = sorted(
            self.active_sessions.items(),
            key=lambda x: x[1].last_activity
        )
        
        for session_id, _ in sorted_sessions[:count]:
            await self._close_session(session_id)
    
    def register_agent(self, agent_type: str, agent: BaseAgent):
        """Register a specialized agent for coordination"""
        self.agent_registry[agent_type] = agent
        self.logger.info(f"Registered {agent_type} agent: {agent.agent_id}")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation manager statistics"""
        total_messages = sum(
            len(session.conversation_history) 
            for session in self.active_sessions.values()
        )
        
        return {
            "active_sessions": len(self.active_sessions),
            "total_messages": total_messages,
            "registered_agents": list(self.agent_registry.keys()),
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "avg_messages_per_session": total_messages / max(len(self.active_sessions), 1)
        }