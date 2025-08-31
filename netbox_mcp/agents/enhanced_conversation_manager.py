#!/usr/bin/env python3
"""
Enhanced Conversation Manager with Intelligent Fallback Integration

This module enhances the existing conversation manager by integrating the
IntelligentFallbackOrchestrator from Phase 4, providing Claude Code CLI-style
user experience with comprehensive fallback strategies and helpful responses.

Key enhancements:
- Integrates intelligent fallback orchestrator for maximum resilience
- Maintains conversation context for better fallback decisions
- Provides Claude Code CLI-style helpful responses regardless of failure
- Handles clarification questions and alternative suggestions seamlessly
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    from .base import BaseAgent, AgentMessage, MessageType, AgentState, QueryContext
    from .config import get_config
    from ..orchestration.entity_tracker import EntityTracker, EntityType, TrackedEntity
except ImportError:
    # Handle import errors gracefully
    BaseAgent = object
    AgentMessage = dict
    MessageType = object
    AgentState = object
    QueryContext = dict
    EntityTracker = object
    EntityType = object
    TrackedEntity = object

# Import Phase 4 intelligent fallback
from ..orchestration.enhanced_state_machine import process_query_with_intelligent_fallback
from ..orchestration.intelligent_fallback_orchestrator import (
    get_intelligent_fallback_statistics, FallbackLevel
)

logger = logging.getLogger(__name__)


class EnhancedConversationSession:
    """Enhanced conversation session with intelligent fallback integration"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
        self.active_agents: Dict[str, str] = {}
        self.pending_clarifications: List[Dict[str, Any]] = []
        
        # Enhanced entity tracking
        try:
            self.entity_tracker = EntityTracker(session_id)
        except:
            self.entity_tracker = None
            
        self.conversation_topic: Optional[str] = None
        
        # Intelligent fallback tracking
        self.fallback_history: List[Dict[str, Any]] = []
        self.clarification_context: Dict[str, Any] = {}
        self.alternative_suggestions: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {}
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history with enhanced metadata"""
        message_data = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Add fallback information to metadata if available
        if metadata and "fallback_info" in metadata:
            fallback_info = metadata["fallback_info"]
            self.fallback_history.append({
                "timestamp": datetime.now().isoformat(),
                "fallback_level": fallback_info.get("fallback_level", "unknown"),
                "reasoning": fallback_info.get("reasoning", ""),
                "success": fallback_info.get("success", False)
            })
        
        self.conversation_history.append(message_data)
        self.last_activity = datetime.now()
    
    def get_recent_context(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history for enhanced context"""
        return self.conversation_history[-max_messages:]
    
    def get_fallback_context(self) -> Dict[str, Any]:
        """Get fallback-specific context for better decision making"""
        return {
            "recent_fallbacks": self.fallback_history[-5:],  # Last 5 fallbacks
            "clarification_context": self.clarification_context,
            "user_preferences": self.user_preferences,
            "conversation_topic": self.conversation_topic,
            "session_context": self.context
        }
    
    def update_clarification_context(self, clarification_data: Dict[str, Any]):
        """Update context based on clarification responses"""
        self.clarification_context.update(clarification_data)
        self.last_activity = datetime.now()
    
    def add_alternative_suggestion(self, suggestion: Dict[str, Any]):
        """Add alternative suggestion to session"""
        self.alternative_suggestions.append({
            **suggestion,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
    
    def update_user_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences based on interaction patterns"""
        self.user_preferences.update(preferences)
        self.last_activity = datetime.now()


class EnhancedConversationManager(BaseAgent if BaseAgent != object else object):
    """Enhanced conversation manager with intelligent fallback integration"""
    
    def __init__(self):
        # Initialize BaseAgent if it exists and needs parameters
        if BaseAgent != object:
            try:
                super().__init__(agent_id="enhanced-conversation-manager", agent_type="conversation")
            except TypeError:
                # BaseAgent might not need parameters or might be different
                pass
        
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, EnhancedConversationSession] = {}
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "fallback_queries": 0,
            "clarification_queries": 0,
            "degradation_queries": 0
        }
    
    # Implement abstract methods if BaseAgent is actually abstract
    async def initialize(self):
        """Initialize the enhanced conversation manager"""
        pass
    
    async def cleanup(self):
        """Cleanup the enhanced conversation manager"""
        pass
    
    async def process_request(self, request: Any) -> Any:
        """Process a generic request - delegates to process_user_query"""
        if isinstance(request, dict) and "query" in request:
            return await self.process_user_query(
                request["query"],
                request.get("session_id"),
                request.get("user_context")
            )
        elif isinstance(request, str):
            return await self.process_user_query(request)
        else:
            raise ValueError(f"Unsupported request type: {type(request)}")
    
    async def process_user_query(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user query with intelligent fallback integration
        
        This is the main entry point that provides Claude Code CLI-style
        resilience and helpfulness for any user query.
        """
        # Initialize session
        if not session_id:
            session_id = str(uuid4())
        
        session = self._get_or_create_session(session_id)
        correlation_id = str(uuid4())
        
        self.logger.info(f"Processing query with enhanced fallback: {query[:100]}...")
        self.stats["total_queries"] += 1
        
        # Add user query to conversation history
        session.add_message("user", query, {"correlation_id": correlation_id})
        
        try:
            # Get enhanced fallback context
            fallback_context = session.get_fallback_context()
            
            # Process query with intelligent fallback orchestrator
            result = await process_query_with_intelligent_fallback(
                user_query=query,
                session_id=session_id,
                correlation_id=correlation_id
            )
            
            # Update statistics based on result
            self._update_statistics(result)
            
            # Process the result based on fallback level
            enhanced_response = await self._enhance_response_based_on_fallback(
                result, session, query
            )
            
            # Add assistant response to conversation history
            session.add_message(
                "assistant", 
                enhanced_response["response"],
                {
                    "correlation_id": correlation_id,
                    "fallback_info": {
                        "fallback_level": result.get("fallback_level", "primary"),
                        "reasoning": result.get("fallback_reasoning", ""),
                        "success": result.get("success", False)
                    }
                }
            )
            
            # Update session context based on result
            await self._update_session_context(session, result)
            
            return enhanced_response
        
        except Exception as e:
            self.logger.error(f"Enhanced conversation manager failed: {e}")
            
            # Generate minimal fallback response
            fallback_response = self._generate_critical_fallback_response(query, str(e))
            session.add_message("assistant", fallback_response["response"])
            
            return fallback_response
    
    def _get_or_create_session(self, session_id: str) -> EnhancedConversationSession:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = EnhancedConversationSession(session_id)
        return self.sessions[session_id]
    
    def _update_statistics(self, result: Dict[str, Any]):
        """Update conversation manager statistics"""
        if result.get("success"):
            self.stats["successful_queries"] += 1
        
        fallback_level = result.get("fallback_level", "primary")
        
        if fallback_level != "primary":
            self.stats["fallback_queries"] += 1
        
        if fallback_level == "query_clarification":
            self.stats["clarification_queries"] += 1
        
        if fallback_level == "graceful_degradation":
            self.stats["degradation_queries"] += 1
    
    async def _enhance_response_based_on_fallback(
        self, 
        result: Dict[str, Any], 
        session: EnhancedConversationSession,
        original_query: str
    ) -> Dict[str, Any]:
        """Enhance response based on fallback level and context"""
        
        fallback_level = result.get("fallback_level", "primary")
        base_response = result.get("response", "No response available")
        
        enhanced_response = {
            "response": base_response,
            "success": result.get("success", False),
            "fallback_level": fallback_level,
            "metadata": {
                "tool_used": result.get("tool_used"),
                "execution_time": result.get("execution_time", 0),
                "session_id": session.session_id,
                "conversation_context": self._extract_conversation_context(session)
            }
        }
        
        # Enhance based on specific fallback levels
        if fallback_level == "query_clarification":
            enhanced_response = await self._enhance_clarification_response(
                enhanced_response, result, session
            )
        
        elif fallback_level == "alternative_tool_selection":
            enhanced_response = await self._enhance_alternatives_response(
                enhanced_response, result, session
            )
        
        elif fallback_level == "graceful_degradation":
            enhanced_response = await self._enhance_degradation_response(
                enhanced_response, result, session
            )
        
        elif fallback_level == "parameter_correction":
            enhanced_response = await self._enhance_correction_response(
                enhanced_response, result, session
            )
        
        # Add general enhancements
        enhanced_response = self._add_contextual_enhancements(enhanced_response, session)
        
        return enhanced_response
    
    async def _enhance_clarification_response(
        self, 
        response: Dict[str, Any], 
        result: Dict[str, Any],
        session: EnhancedConversationSession
    ) -> Dict[str, Any]:
        """Enhance response when clarification is needed"""
        
        clarification_questions = result.get("clarification_questions", [])
        
        if clarification_questions:
            # Store clarification context for next interaction
            session.clarification_context.update({
                "pending_questions": clarification_questions,
                "original_query": session.conversation_history[-1]["content"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Enhance response with conversation-aware clarification
            enhanced_text = response["response"]
            
            # Add helpful context based on conversation history
            if len(session.conversation_history) > 2:
                enhanced_text += "\n\n*Based on our conversation, you might also want to consider:*\n"
                suggestions = self._generate_conversation_aware_suggestions(session)
                for suggestion in suggestions[:2]:
                    enhanced_text += f"• {suggestion}\n"
            
            response["response"] = enhanced_text
            response["metadata"]["clarification_questions"] = clarification_questions
            response["metadata"]["requires_user_input"] = True
        
        return response
    
    async def _enhance_alternatives_response(
        self, 
        response: Dict[str, Any], 
        result: Dict[str, Any],
        session: EnhancedConversationSession
    ) -> Dict[str, Any]:
        """Enhance response when alternative approaches are suggested"""
        
        alternatives = result.get("alternative_approaches", [])
        
        if alternatives:
            # Store alternatives for potential follow-up
            for alternative in alternatives:
                session.add_alternative_suggestion(alternative)
            
            # Enhance response with session-aware alternatives
            enhanced_text = response["response"]
            enhanced_text += "\n\n*You can also try:*\n"
            enhanced_text += "• Type 'help' to see all available commands\n"
            enhanced_text += "• Ask 'what can I do with [resource type]?' for specific guidance\n"
            
            response["response"] = enhanced_text
            response["metadata"]["alternative_approaches"] = alternatives
        
        return response
    
    async def _enhance_degradation_response(
        self, 
        response: Dict[str, Any], 
        result: Dict[str, Any],
        session: EnhancedConversationSession
    ) -> Dict[str, Any]:
        """Enhance response for graceful degradation"""
        
        # Add conversation-specific learning suggestions
        enhanced_text = response["response"]
        
        # Add session-specific helpful information
        if session.fallback_history:
            recent_successes = [
                fb for fb in session.fallback_history[-10:] 
                if fb.get("success", False)
            ]
            
            if recent_successes:
                enhanced_text += "\n\n*Note: Earlier in our conversation, these approaches worked well:*\n"
                for success in recent_successes[-2:]:
                    enhanced_text += f"• Used {success.get('fallback_level', 'unknown method')}\n"
        
        # Add progressive assistance
        enhanced_text += "\n\n**Progressive assistance available:**\n"
        enhanced_text += "• Start with 'list all [resource type]' commands\n"
        enhanced_text += "• Try 'help me with [specific task]' for guided assistance\n"
        enhanced_text += "• Use 'show example for [operation]' to see working examples\n"
        
        response["response"] = enhanced_text
        response["metadata"]["degradation_level"] = "enhanced_with_context"
        
        return response
    
    async def _enhance_correction_response(
        self, 
        response: Dict[str, Any], 
        result: Dict[str, Any],
        session: EnhancedConversationSession
    ) -> Dict[str, Any]:
        """Enhance response when parameter correction was used"""
        
        # Add explanation of what was corrected
        enhanced_text = response["response"]
        enhanced_text += f"\n\n*Note: I automatically corrected some parameters to complete your request.*"
        
        if result.get("fallback_reasoning"):
            enhanced_text += f" {result['fallback_reasoning']}"
        
        response["response"] = enhanced_text
        response["metadata"]["auto_correction_used"] = True
        
        return response
    
    def _add_contextual_enhancements(
        self, 
        response: Dict[str, Any], 
        session: EnhancedConversationSession
    ) -> Dict[str, Any]:
        """Add general contextual enhancements to any response"""
        
        # Add conversation continuation hints
        if response.get("success") and session.conversation_topic:
            enhanced_text = response["response"]
            enhanced_text += f"\n\n*You can continue working with {session.conversation_topic} or ask about something else.*"
            response["response"] = enhanced_text
        
        # Add session metadata
        response["metadata"].update({
            "session_duration": (datetime.now() - session.created_at).total_seconds(),
            "conversation_length": len(session.conversation_history),
            "fallback_count": len(session.fallback_history)
        })
        
        return response
    
    def _generate_conversation_aware_suggestions(
        self, session: EnhancedConversationSession
    ) -> List[str]:
        """Generate suggestions based on conversation history"""
        suggestions = []
        
        # Analyze recent conversation for patterns
        recent_messages = session.get_recent_context(5)
        
        # Look for repeated resource types
        resource_types = []
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            if "device" in content:
                resource_types.append("device")
            elif "site" in content:
                resource_types.append("site")
            elif "rack" in content:
                resource_types.append("rack")
        
        if resource_types:
            most_common = max(set(resource_types), key=resource_types.count)
            suggestions.append(f"List all {most_common}s to see what's available")
            suggestions.append(f"Get detailed information about a specific {most_common}")
        
        # Add general helpful suggestions
        suggestions.extend([
            "Try using exact names from your NetBox instance",
            "Break complex requests into simpler steps",
            "Ask for examples of working commands"
        ])
        
        return suggestions[:3]
    
    def _extract_conversation_context(self, session: EnhancedConversationSession) -> Dict[str, Any]:
        """Extract relevant conversation context"""
        return {
            "topic": session.conversation_topic,
            "recent_resources": self._extract_recent_resources(session),
            "session_length": len(session.conversation_history),
            "fallback_patterns": self._analyze_fallback_patterns(session)
        }
    
    def _extract_recent_resources(self, session: EnhancedConversationSession) -> List[str]:
        """Extract resource types mentioned recently"""
        resources = set()
        recent_messages = session.get_recent_context(5)
        
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            for resource in ["device", "site", "rack", "cable", "vlan", "prefix"]:
                if resource in content:
                    resources.add(resource)
        
        return list(resources)
    
    def _analyze_fallback_patterns(self, session: EnhancedConversationSession) -> Dict[str, Any]:
        """Analyze patterns in fallback usage"""
        if not session.fallback_history:
            return {}
        
        recent_fallbacks = session.fallback_history[-5:]
        
        return {
            "most_common_fallback": max(
                [fb.get("fallback_level", "unknown") for fb in recent_fallbacks],
                key=recent_fallbacks.count,
                default="none"
            ),
            "success_rate": sum(1 for fb in recent_fallbacks if fb.get("success", False)) / len(recent_fallbacks),
            "needs_clarification": any(
                fb.get("fallback_level") == "query_clarification" 
                for fb in recent_fallbacks
            )
        }
    
    def _generate_critical_fallback_response(self, query: str, error: str) -> Dict[str, Any]:
        """Generate response when even the enhanced system fails"""
        return {
            "response": f"""I encountered a system error while processing your request "{query}".

**Error:** {error}

**What you can try:**
• Wait a moment and try again
• Try a simpler version of your request
• Check if all resource names are spelled correctly
• Contact your system administrator if the problem persists

**Alternative approaches:**
• Use the NetBox web interface to verify resource names
• Try breaking complex requests into individual steps
• Start with basic 'list all' commands to explore available resources""",
            "success": False,
            "fallback_level": "critical_system_failure",
            "metadata": {
                "error": error,
                "critical_failure": True
            }
        }
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a conversation session"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "conversation_length": len(session.conversation_history),
            "fallback_history": session.fallback_history,
            "conversation_topic": session.conversation_topic,
            "pending_clarifications": session.pending_clarifications,
            "alternative_suggestions": session.alternative_suggestions[-5:],  # Last 5
            "context_summary": self._extract_conversation_context(session)
        }
    
    async def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get enhanced conversation manager statistics"""
        fallback_stats = get_intelligent_fallback_statistics()
        
        return {
            "conversation_stats": self.stats.copy(),
            "active_sessions": len(self.sessions),
            "fallback_system_stats": fallback_stats,
            "session_summaries": [
                {
                    "session_id": session.session_id,
                    "conversation_length": len(session.conversation_history),
                    "fallback_count": len(session.fallback_history),
                    "last_activity": session.last_activity.isoformat()
                }
                for session in list(self.sessions.values())[-10:]  # Last 10 sessions
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    async def clear_session(self, session_id: str) -> bool:
        """Clear a conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


# Global enhanced conversation manager instance
enhanced_conversation_manager = EnhancedConversationManager()


# Public interface functions
async def process_user_query_with_fallback(
    query: str,
    session_id: Optional[str] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Public interface for processing user queries with intelligent fallback
    
    This provides the main entry point for Claude Code CLI-style user interaction
    with comprehensive fallback strategies and helpful responses.
    """
    return await enhanced_conversation_manager.process_user_query(
        query, session_id, user_context
    )


async def get_session_information(session_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a conversation session"""
    return await enhanced_conversation_manager.get_session_info(session_id)


async def get_enhanced_conversation_statistics() -> Dict[str, Any]:
    """Get comprehensive conversation and fallback statistics"""
    return await enhanced_conversation_manager.get_conversation_statistics()