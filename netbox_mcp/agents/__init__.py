"""
Phase 3: OpenAI + LangGraph Agent System

This module implements the multi-agent orchestration system for intelligent
coordination of existing NetBox MCP tools.
"""

from .base import BaseAgent, AgentMessage, AgentState
from .conversation_manager import ConversationManagerAgent
from .intent_recognition import IntentRecognitionAgent
from .response_generation import ResponseGenerationAgent
from .task_planning import TaskPlanningAgent
from .tool_coordination import ToolCoordinationAgent

__all__ = [
    "BaseAgent",
    "AgentMessage", 
    "AgentState",
    "ConversationManagerAgent",
    "IntentRecognitionAgent",
    "ResponseGenerationAgent",
    "TaskPlanningAgent",
    "ToolCoordinationAgent",
]