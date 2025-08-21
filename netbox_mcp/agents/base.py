"""
Base Agent Framework for Phase 3 Orchestration
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict
from uuid import uuid4

from openai import AsyncOpenAI
from .config import get_config, OpenAIConfig


class AgentState(Enum):
    """Agent lifecycle states"""
    INITIALIZED = "initialized"
    READY = "ready"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class MessageType(Enum):
    """Inter-agent message types"""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    PROGRESS = "progress"
    BROADCAST = "broadcast"


@dataclass
class AgentMessage:
    """Standard message format for inter-agent communication"""
    source: str
    target: str  # Agent ID or "broadcast"
    message_type: MessageType
    content: Dict[str, Any]
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryContext(TypedDict):
    """Shared context for query processing"""
    user_query: str
    session_id: str
    conversation_history: List[Dict[str, str]]
    entities: List[Dict[str, Any]]
    intent: Optional[Dict[str, Any]]
    execution_plan: Optional[Dict[str, Any]]
    tool_results: Optional[Dict[str, Any]]
    final_response: Optional[str]
    requires_clarification: bool
    clarification_questions: List[str]
    error_state: Optional[Dict[str, Any]]


class BaseAgent(ABC):
    """Base class for all orchestration agents"""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        config: Optional[OpenAIConfig] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = AgentState.INITIALIZED
        self.config = config or get_config().openai
        self.logger = logging.getLogger(f"agent.{agent_type}.{agent_id}")
        
        # OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=self.config.api_key,
            organization=self.config.organization,
            base_url=self.config.base_url,
        )
        
        # Message handling
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers = {}
        self.response_callbacks = {}
        
        # Metrics
        self.metrics = {
            "messages_processed": 0,
            "errors_encountered": 0,
            "average_processing_time": 0.0,
            "last_activity": datetime.now(),
        }
    
    async def start(self) -> None:
        """Start the agent and begin processing messages"""
        self.logger.info(f"Starting agent {self.agent_id}")
        self.state = AgentState.READY
        
        # Start message processing loop
        asyncio.create_task(self._process_messages())
        
        # Initialize agent-specific resources
        await self.initialize()
    
    async def stop(self) -> None:
        """Stop the agent gracefully"""
        self.logger.info(f"Stopping agent {self.agent_id}")
        self.state = AgentState.SHUTDOWN
        
        # Clean up agent-specific resources
        await self.cleanup()
    
    async def send_message(
        self,
        target: str,
        message_type: MessageType,
        content: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """Send a message to another agent"""
        message = AgentMessage(
            source=self.agent_id,
            target=target,
            message_type=message_type,
            content=content,
            correlation_id=correlation_id or str(uuid4()),
        )
        
        # In a real implementation, this would use a message bus
        # For now, we'll simulate with direct queue access
        await self._route_message(message)
        
        return message.correlation_id
    
    async def handle_message(self, message: AgentMessage) -> None:
        """Handle an incoming message"""
        await self.message_queue.put(message)
    
    async def _process_messages(self) -> None:
        """Process messages from the queue"""
        while self.state != AgentState.SHUTDOWN:
            try:
                # Get message with timeout to allow checking shutdown state
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                self.state = AgentState.PROCESSING
                self.metrics["messages_processed"] += 1
                
                start_time = datetime.now()
                
                # Process based on message type
                if message.message_type == MessageType.REQUEST:
                    response = await self.process_request(message.content)
                    await self.send_message(
                        target=message.source,
                        message_type=MessageType.RESPONSE,
                        content=response,
                        correlation_id=message.correlation_id
                    )
                elif message.message_type == MessageType.RESPONSE:
                    await self.process_response(message)
                elif message.message_type == MessageType.ERROR:
                    await self.process_error(message)
                elif message.message_type == MessageType.PROGRESS:
                    await self.process_progress(message)
                
                # Update metrics
                processing_time = (datetime.now() - start_time).total_seconds()
                self.metrics["average_processing_time"] = (
                    (self.metrics["average_processing_time"] * 
                     (self.metrics["messages_processed"] - 1) + 
                     processing_time) / 
                    self.metrics["messages_processed"]
                )
                self.metrics["last_activity"] = datetime.now()
                
                self.state = AgentState.READY
                
            except asyncio.TimeoutError:
                # No message available, continue loop
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                self.metrics["errors_encountered"] += 1
                self.state = AgentState.ERROR
                await self.handle_error(e)
    
    async def _route_message(self, message: AgentMessage) -> None:
        """Route message to appropriate agent (placeholder for message bus)"""
        # In a real implementation, this would use a central message bus
        # For now, this is a placeholder
        self.logger.debug(f"Routing message from {message.source} to {message.target}")
    
    async def process_response(self, message: AgentMessage) -> None:
        """Process a response message"""
        if message.correlation_id in self.response_callbacks:
            callback = self.response_callbacks.pop(message.correlation_id)
            await callback(message.content)
    
    async def process_error(self, message: AgentMessage) -> None:
        """Process an error message"""
        self.logger.error(f"Received error from {message.source}: {message.content}")
    
    async def process_progress(self, message: AgentMessage) -> None:
        """Process a progress update"""
        self.logger.info(f"Progress from {message.source}: {message.content}")
    
    async def handle_error(self, error: Exception) -> None:
        """Handle internal errors"""
        self.logger.error(f"Internal error: {error}")
        self.state = AgentState.ERROR
        # Attempt recovery
        await asyncio.sleep(1)
        self.state = AgentState.READY
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "state": self.state.value,
            **self.metrics
        }
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize agent-specific resources"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up agent-specific resources"""
        pass
    
    @abstractmethod
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request and return response"""
        pass