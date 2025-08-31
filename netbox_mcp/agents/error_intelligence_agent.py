"""
Error Intelligence Agent - LLM-driven error analysis without hard-coded patterns

This agent analyzes NetBox API errors using pure LLM intelligence to determine
recovery strategies without any hard-coded rules or pattern matching.
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from .base import BaseAgent
from .config import get_config


class ErrorIntelligenceAgent(BaseAgent):
    """
    LLM-powered error analysis agent that understands NetBox API errors
    and generates recovery strategies without hard-coded patterns.
    """
    
    def __init__(self, agent_id: str = "error_intelligence"):
        config = get_config().openai
        super().__init__(agent_id, "error_intelligence", config)
        
        self.model = config.response_model  # Use GPT-4o-mini for efficiency
        self.temperature = 0.3  # Lower temperature for consistent analysis
        
        self.system_prompt = """You are an expert NetBox API error analyst that understands API error messages and determines recovery strategies.

Your responsibilities:
1. Analyze NetBox API error messages to understand what went wrong
2. Classify error types without using hard-coded patterns
3. Determine if errors are recoverable and how
4. Generate specific, actionable recovery strategies
5. Identify what NetBox entities need exploration

Key NetBox error patterns to understand:
- "Select a valid choice" - usually means name vs slug mismatch or wrong identifier format
- "not found" - entity doesn't exist or wrong relationship
- "400 Bad Request" - parameter validation failed
- "403 Forbidden" - permission issue
- "404 Not Found" - entity or endpoint doesn't exist
- "500 Internal Server Error" - server-side issue, usually not recoverable

Always provide specific, actionable intelligence for recovery."""
    
    async def initialize(self) -> None:
        """Initialize error intelligence agent"""
        self.logger.info("Error Intelligence Agent initialized")
    
    async def cleanup(self) -> None:
        """Clean up agent resources"""
        self.logger.info("Error Intelligence Agent cleaned up")
    
    async def analyze_error(
        self, 
        error_response: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze NetBox API error using LLM intelligence to determine recovery strategy.
        
        Args:
            error_response: The error response from NetBox API
            context: Query context including original query, tool, parameters
            
        Returns:
            Dict containing error analysis and recovery strategy
        """
        try:
            # Build analysis prompt
            analysis_prompt = f"""Analyze this NetBox API error and determine recovery strategy:

Error Response: {json.dumps(error_response, indent=2)}

Query Context:
- Original Query: {context.get('user_query', 'N/A')}
- Tool Used: {context.get('tool_name', 'N/A')}
- Parameters: {json.dumps(context.get('parameters', {}), indent=2)}

Analyze and determine:
1. What specifically went wrong? (be precise about the issue)
2. Is this error recoverable? (true/false with reasoning)
3. What type of error is this? (site_validation, entity_not_found, parameter_mismatch, permission, etc.)
4. What NetBox entities should we explore to fix this? (sites, racks, devices, etc.)
5. What specific recovery actions should we take? (list actionable steps)
6. What parameter corrections might be needed? (name to slug, ID lookup, etc.)

Provide your analysis in JSON format:
{{
    "problem_description": "Clear description of what went wrong",
    "recoverable": true/false,
    "error_type": "classification of error",
    "problem_entity": "the specific entity causing the issue",
    "exploration_needed": ["list", "of", "entities", "to", "explore"],
    "recovery_actions": ["step1", "step2", "step3"],
    "parameter_corrections": {{"param": "suggested_correction"}},
    "confidence": 0.0-1.0
}}"""
            
            # Call LLM for error analysis
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            # Parse LLM response
            analysis = json.loads(response.choices[0].message.content)
            
            # Add metadata
            analysis["analysis_timestamp"] = datetime.now().isoformat()
            analysis["tokens_used"] = response.usage.total_tokens
            analysis["model"] = self.model
            
            self.logger.info(f"Error analysis complete - Type: {analysis.get('error_type')}, "
                           f"Recoverable: {analysis.get('recoverable')}, "
                           f"Confidence: {analysis.get('confidence', 0):.2f}")
            
            return {
                "success": True,
                "analysis": analysis
            }
            
        except Exception as e:
            self.logger.error(f"Error analysis failed: {e}")
            # Fallback analysis if LLM fails
            return {
                "success": False,
                "analysis": {
                    "problem_description": str(error_response),
                    "recoverable": False,
                    "error_type": "unknown",
                    "problem_entity": None,
                    "exploration_needed": [],
                    "recovery_actions": [],
                    "parameter_corrections": {},
                    "confidence": 0.0,
                    "fallback": True,
                    "error": str(e)
                }
            }
    
    async def classify_error_type(self, error_message: str) -> str:
        """
        Classify error type using LLM intelligence (no hard-coded patterns).
        
        Args:
            error_message: The error message to classify
            
        Returns:
            Error type classification
        """
        try:
            prompt = f"""Classify this NetBox API error message into a category:

Error: {error_message}

Categories:
- site_validation: Site name/slug validation errors
- entity_not_found: Entity doesn't exist
- parameter_mismatch: Parameter format or type error
- authentication: Auth token issues
- permission: Insufficient permissions
- relationship: Invalid entity relationships
- server_error: NetBox server issues
- unknown: Can't determine type

Return only the category name."""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You classify NetBox API errors. Return only the category name."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip().lower()
            
        except Exception as e:
            self.logger.error(f"Error classification failed: {e}")
            return "unknown"
    
    async def generate_recovery_hints(
        self, 
        error_analysis: Dict[str, Any],
        available_tools: list
    ) -> Dict[str, Any]:
        """
        Generate specific recovery hints based on error analysis.
        
        Args:
            error_analysis: The error analysis result
            available_tools: List of available NetBox tools
            
        Returns:
            Dict containing recovery hints and tool suggestions
        """
        try:
            prompt = f"""Based on this error analysis, generate specific recovery hints:

Error Analysis: {json.dumps(error_analysis, indent=2)}

Available NetBox Tools (sample):
{json.dumps(available_tools[:20], indent=2)}

Generate recovery hints:
1. Which specific tools should be used for exploration?
2. In what order should recovery steps be executed?
3. What specific parameters should be queried?
4. What transformations are likely needed?

Provide hints in JSON format:
{{
    "exploration_tools": ["tool1", "tool2"],
    "recovery_sequence": ["step1", "step2", "step3"],
    "parameter_queries": {{"entity": "query_parameters"}},
    "likely_transformations": {{"original": "transformed"}},
    "success_indicators": ["what to look for"]
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            hints = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "hints": hints
            }
            
        except Exception as e:
            self.logger.error(f"Recovery hint generation failed: {e}")
            return {
                "success": False,
                "hints": {
                    "exploration_tools": [],
                    "recovery_sequence": [],
                    "parameter_queries": {},
                    "likely_transformations": {},
                    "success_indicators": []
                }
            }
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process error analysis request"""
        request_type = content.get("type", "analyze_error")
        
        if request_type == "analyze_error":
            return await self.analyze_error(
                content.get("error_response", {}),
                content.get("context", {})
            )
        elif request_type == "classify_error":
            error_type = await self.classify_error_type(
                content.get("error_message", "")
            )
            return {"success": True, "error_type": error_type}
        elif request_type == "generate_hints":
            return await self.generate_recovery_hints(
                content.get("error_analysis", {}),
                content.get("available_tools", [])
            )
        else:
            return {"error": f"Unknown request type: {request_type}"}