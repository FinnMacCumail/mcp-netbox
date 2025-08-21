"""
Response Generation Agent - Natural language formatting of tool outputs
"""

import json
from typing import Any, Dict, List, Optional

from .base import BaseAgent, QueryContext
from .config import get_config


class ResponseGenerationAgent(BaseAgent):
    """
    Agent responsible for converting structured tool outputs to natural language.
    Uses GPT-4o-mini for efficient response generation.
    """
    
    def __init__(self, agent_id: str = "response_generator"):
        config = get_config().openai
        super().__init__(agent_id, "response_generation", config)
        
        self.model = config.response_model
        self.temperature = config.response_temperature
        
        # Response formatting templates
        self.system_prompt = """You are a helpful NetBox assistant that converts technical data into clear, natural language responses.

Your responsibilities:
1. Convert structured NetBox data into user-friendly explanations
2. Add helpful context and insights
3. Format complex data clearly (use tables, lists, etc.)
4. Suggest relevant follow-up actions
5. Handle error states gracefully with helpful guidance

Guidelines:
- Be concise but informative
- Use appropriate formatting for readability
- Highlight important information
- Provide actionable next steps when relevant
- Explain technical terms when necessary"""
    
    async def initialize(self) -> None:
        """Initialize response generation agent"""
        self.logger.info("Response Generation Agent initialized")
    
    async def cleanup(self) -> None:
        """Clean up agent resources"""
        self.logger.info("Response Generation Agent cleaned up")
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process a response generation request"""
        request_type = content.get("type", "format_response")
        
        if request_type == "format_response":
            return await self.format_response(content)
        elif request_type == "format_error":
            return await self.format_error(content)
        elif request_type == "format_clarification":
            return await self.format_clarification(content)
        elif request_type == "format_progress":
            return await self.format_progress(content)
        else:
            return {"error": f"Unknown request type: {request_type}"}
    
    async def format_response(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format tool results into natural language response"""
        tool_results = content.get("tool_results", {})
        query_context = content.get("context", {})
        response_type = content.get("response_type", "standard")
        
        try:
            # Prepare the formatting prompt
            formatting_prompt = self._build_formatting_prompt(
                tool_results, 
                query_context, 
                response_type
            )
            
            # Call OpenAI to format the response
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": formatting_prompt}
                ],
                temperature=self.temperature,
                max_tokens=2048
            )
            
            formatted_response = response.choices[0].message.content
            
            # Add metadata and suggestions
            enhanced_response = await self._enhance_response(
                formatted_response,
                tool_results,
                query_context
            )
            
            return {
                "success": True,
                "response": enhanced_response,
                "metadata": {
                    "tokens_used": response.usage.total_tokens,
                    "model": self.model,
                    "response_type": response_type
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting response: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_response": self._create_fallback_response(tool_results)
            }
    
    async def format_error(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format error messages for users"""
        error_info = content.get("error", {})
        context = content.get("context", {})
        
        error_prompt = f"""Convert this technical error into a helpful user message:

Error Type: {error_info.get('type', 'Unknown')}
Error Message: {error_info.get('message', 'An error occurred')}
Context: {json.dumps(context, indent=2)}

Provide:
1. A clear explanation of what went wrong
2. Why this might have happened
3. Suggested actions the user can take
4. Alternative approaches if available

Keep the tone helpful and non-technical."""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": error_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "error_handled": True
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting error message: {e}")
            return {
                "success": False,
                "response": "An error occurred while processing your request. Please try again or rephrase your query.",
                "error_handled": False
            }
    
    async def format_clarification(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format clarification questions for ambiguous queries"""
        ambiguous_entities = content.get("ambiguous_entities", [])
        possible_values = content.get("possible_values", {})
        original_query = content.get("original_query", "")
        
        clarification_prompt = f"""Generate helpful clarification questions for this ambiguous query:

Original Query: "{original_query}"
Ambiguous Elements: {json.dumps(ambiguous_entities, indent=2)}
Possible Values: {json.dumps(possible_values, indent=2)}

Create natural, friendly clarification questions that:
1. Are easy to understand
2. Provide helpful context
3. Show available options when appropriate
4. Guide the user to provide specific information

Format as a conversational response with numbered questions if multiple clarifications are needed."""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": clarification_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "requires_clarification": True,
                "clarification_metadata": {
                    "entities": ambiguous_entities,
                    "options": possible_values
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting clarification: {e}")
            # Fallback to simple clarification
            questions = []
            for entity in ambiguous_entities:
                if entity in possible_values and possible_values[entity]:
                    options = possible_values[entity][:5]  # Limit to 5 options
                    questions.append(f"Which {entity} did you mean? Options include: {', '.join(options)}")
                else:
                    questions.append(f"Could you please specify which {entity} you're referring to?")
            
            return {
                "success": True,
                "response": "I need some clarification:\n\n" + "\n".join(questions),
                "requires_clarification": True
            }
    
    async def format_progress(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format progress updates for long-running operations"""
        operation = content.get("operation", "Processing")
        current_step = content.get("current_step", 0)
        total_steps = content.get("total_steps", 0)
        message = content.get("message", "")
        
        progress_percentage = (current_step / total_steps * 100) if total_steps > 0 else 0
        
        progress_response = f"⏳ {operation}: Step {current_step}/{total_steps} ({progress_percentage:.0f}%)"
        if message:
            progress_response += f"\n   {message}"
        
        return {
            "success": True,
            "response": progress_response,
            "is_progress": True,
            "metadata": {
                "operation": operation,
                "progress": progress_percentage,
                "current_step": current_step,
                "total_steps": total_steps
            }
        }
    
    def _build_formatting_prompt(
        self, 
        tool_results: Dict[str, Any],
        query_context: Dict[str, Any],
        response_type: str
    ) -> str:
        """Build the prompt for response formatting"""
        prompt = f"""Format this NetBox data into a natural language response:

User Query: "{query_context.get('user_query', 'N/A')}"
Response Type: {response_type}

Tool Results:
{json.dumps(tool_results, indent=2, default=str)}

Create a response that:
1. Directly answers the user's question
2. Highlights the most important information
3. Uses appropriate formatting (lists, emphasis, etc.)
4. Adds helpful context where needed
5. Suggests logical next steps if relevant

Keep the response concise but complete."""
        
        return prompt
    
    async def _enhance_response(
        self,
        formatted_response: str,
        tool_results: Dict[str, Any],
        query_context: Dict[str, Any]
    ) -> str:
        """Enhance response with additional context and suggestions"""
        enhanced = formatted_response
        
        # Add performance notes if there were known limitations handled
        if query_context.get("limitations_handled"):
            enhanced += "\n\n📝 **Note**: Some results may be limited due to system constraints. Use filters for more specific queries."
        
        # Add follow-up suggestions based on response type
        if tool_results.get("has_more_data"):
            enhanced += "\n\n💡 **Tip**: More data is available. Try adding filters or being more specific to see detailed results."
        
        return enhanced
    
    def _create_fallback_response(self, tool_results: Dict[str, Any]) -> str:
        """Create a basic fallback response if formatting fails"""
        if not tool_results:
            return "I've completed the operation but couldn't format the results properly. Please try your query again."
        
        # Try to create a simple summary
        response_parts = ["Here's what I found:"]
        
        for key, value in tool_results.items():
            if isinstance(value, (list, tuple)):
                response_parts.append(f"- {key}: {len(value)} items")
            elif isinstance(value, dict):
                response_parts.append(f"- {key}: {len(value)} properties")
            else:
                response_parts.append(f"- {key}: {value}")
        
        return "\n".join(response_parts)