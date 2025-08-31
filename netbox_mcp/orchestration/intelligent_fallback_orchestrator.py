#!/usr/bin/env python3
"""
Intelligent Fallback Orchestrator - Claude Code CLI Style Fallback Intelligence

This module implements multi-level fallback strategies that work at the correct
abstraction level to achieve Claude Code CLI parity. Instead of complex circuit
breakers for wrong tool selection, it provides intelligent recovery that understands
context and can adapt when primary approaches fail.

Key improvements over existing error_recovery.py:
- Tool Selection Fallback: When primary tool fails, intelligently suggest alternatives
- Parameter Correction Fallback: When parameters are invalid, LLM-correct them  
- Query Interpretation Fallback: When query is ambiguous, seek clarification
- Graceful Degradation: When all fails, provide helpful explanations

Multi-Level Recovery Strategy:
Primary: Direct tool selection with Phase 1 + Phase 2
Fallback 1: Parameter correction with LLM validation
Fallback 2: Alternative tool selection with confidence scoring
Fallback 3: Query clarification with user guidance
Fallback 4: Graceful degradation with explanation
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import traceback

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..agents.config import get_config
from .intelligent_tool_selector import (
    select_tool, ToolSelection, ToolSelectionConfidence, 
    intelligent_tool_selector
)
from .tool_aware_parameter_extractor import (
    extract_parameters, ParameterExtractionResult, ParameterConfidence,
    tool_aware_parameter_extractor
)
from .tool_registry import read_only_tool_registry
from .real_api_handler import execute_real_netbox_tool
from ..exceptions import (
    NetBoxError, NetBoxConnectionError, NetBoxAuthError, NetBoxValidationError,
    NetBoxNotFoundError, NetBoxPermissionError, NetBoxWriteError, 
    NetBoxConfirmationError, NetBoxConflictError
)

logger = logging.getLogger(__name__)


class FallbackLevel(Enum):
    """Fallback levels in order of execution"""
    PRIMARY = "primary"
    PARAMETER_CORRECTION = "parameter_correction"
    ALTERNATIVE_TOOL_SELECTION = "alternative_tool_selection"
    QUERY_CLARIFICATION = "query_clarification"
    GRACEFUL_DEGRADATION = "graceful_degradation"


class FallbackReason(Enum):
    """Reasons for fallback activation"""
    TOOL_SELECTION_FAILED = "tool_selection_failed"
    PARAMETER_EXTRACTION_FAILED = "parameter_extraction_failed"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND_ERROR = "not_found_error"
    AMBIGUOUS_QUERY = "ambiguous_query"
    INSUFFICIENT_CONTEXT = "insufficient_context"


@dataclass
class FallbackContext:
    """Context for fallback execution"""
    user_query: str
    original_tool_selection: Optional[ToolSelection]
    original_parameters: Dict[str, Any]
    error: Optional[Exception]
    error_details: Dict[str, Any]
    attempt_history: List[Dict[str, Any]] = field(default_factory=list)
    confidence_threshold: float = 0.6
    max_fallback_attempts: int = 3
    session_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackResult:
    """Result of fallback execution"""
    success: bool
    fallback_level: FallbackLevel
    fallback_reason: FallbackReason
    tool_name: Optional[str]
    parameters: Dict[str, Any]
    result: Any
    confidence: float
    reasoning: str
    suggestions: List[str]
    execution_time: float
    timestamp: datetime
    alternative_approaches: List[Dict[str, Any]] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)


class ToolSelectionFallback:
    """Intelligent alternative tool selection when primary tools fail"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tool_registry = read_only_tool_registry
    
    async def suggest_alternatives(
        self,
        context: FallbackContext
    ) -> List[Tuple[str, float, str]]:
        """
        Suggest alternative tools based on query intent and error analysis
        
        Returns:
            List of (tool_name, confidence_score, reasoning) tuples
        """
        alternatives = []
        
        # Analyze original failure
        if context.original_tool_selection:
            original_tool = context.original_tool_selection.primary_tool
            
            # Get tool category and suggest alternatives within category
            tool_category = self._get_tool_category(original_tool)
            category_alternatives = self._get_category_alternatives(
                tool_category, original_tool, context.user_query
            )
            alternatives.extend(category_alternatives)
        
        # Semantic similarity alternatives using LLM
        semantic_alternatives = await self._get_semantic_alternatives(context)
        alternatives.extend(semantic_alternatives)
        
        # Error-specific alternatives
        error_alternatives = self._get_error_specific_alternatives(context)
        alternatives.extend(error_alternatives)
        
        # Deduplicate and sort by confidence
        seen_tools = set()
        unique_alternatives = []
        for tool, confidence, reasoning in alternatives:
            if tool not in seen_tools:
                seen_tools.add(tool)
                unique_alternatives.append((tool, confidence, reasoning))
        
        return sorted(unique_alternatives, key=lambda x: x[1], reverse=True)[:5]
    
    def _get_tool_category(self, tool_name: str) -> str:
        """Determine tool category from tool name"""
        if "site" in tool_name:
            return "site_management"
        elif "device" in tool_name:
            return "device_management"
        elif "rack" in tool_name:
            return "rack_management"
        elif "cable" in tool_name:
            return "cable_management"
        elif "vlan" in tool_name or "prefix" in tool_name or "ip" in tool_name:
            return "ipam_management"
        elif "cluster" in tool_name or "virtual" in tool_name:
            return "virtualization_management"
        elif "power" in tool_name:
            return "power_management"
        else:
            return "general"
    
    def _get_category_alternatives(
        self, 
        category: str, 
        original_tool: str, 
        query: str
    ) -> List[Tuple[str, float, str]]:
        """Get alternative tools within the same category"""
        alternatives = []
        
        # Map categories to alternative tools
        category_maps = {
            "device_management": {
                "netbox_get_device_info": [
                    ("netbox_list_all_devices", 0.8, "List all devices instead of specific device"),
                    ("netbox_get_device_basic_info", 0.7, "Get basic device info without interfaces/cables"),
                    ("netbox_provision_new_device", 0.3, "Create new device if it doesn't exist")
                ],
                "netbox_create_device": [
                    ("netbox_provision_new_device", 0.9, "Comprehensive device provisioning"),
                    ("netbox_list_all_devices", 0.6, "Check existing devices first")
                ],
                "netbox_list_all_devices": [
                    ("netbox_get_device_info", 0.8, "Get specific device if name is known"),
                    ("netbox_get_device_basic_info", 0.7, "Get basic device info")
                ]
            },
            "site_management": {
                "netbox_get_site_info": [
                    ("netbox_list_all_sites", 0.8, "List all sites instead of specific site"),
                    ("netbox_create_site", 0.3, "Create site if it doesn't exist")
                ],
                "netbox_list_all_sites": [
                    ("netbox_get_site_info", 0.8, "Get specific site if name is known")
                ]
            }
        }
        
        if category in category_maps and original_tool in category_maps[category]:
            alternatives.extend(category_maps[category][original_tool])
        
        return alternatives
    
    async def _get_semantic_alternatives(
        self, context: FallbackContext
    ) -> List[Tuple[str, float, str]]:
        """Use LLM to find semantically similar tools"""
        if not AsyncOpenAI:
            return []
        
        try:
            config = get_config()
            client = AsyncOpenAI(api_key=config.openai.api_key)
            
            # Get available tools for context
            available_tools = list(self.tool_registry.get_all_tools().keys())[:50]
            
            prompt = f"""
Given the failed query and error, suggest 3 alternative NetBox MCP tools that might work better.

Original Query: {context.user_query}
Failed Tool: {context.original_tool_selection.primary_tool if context.original_tool_selection else 'Unknown'}
Error: {str(context.error) if context.error else 'Unknown error'}

Available Tools (sample): {', '.join(available_tools)}

Suggest 3 alternative tools with confidence scores (0.0-1.0) and reasoning.
Format as JSON: [{{"tool": "tool_name", "confidence": 0.8, "reasoning": "why this tool might work better"}}]
"""
            
            response = await client.chat.completions.create(
                model=config.openai.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content.strip()
            suggestions = json.loads(response_text)
            
            alternatives = []
            for suggestion in suggestions:
                if suggestion["tool"] in available_tools:
                    alternatives.append((
                        suggestion["tool"],
                        suggestion["confidence"],
                        suggestion["reasoning"]
                    ))
            
            return alternatives
            
        except Exception as e:
            self.logger.warning(f"LLM semantic alternatives failed: {e}")
            return []
    
    def _get_error_specific_alternatives(
        self, context: FallbackContext
    ) -> List[Tuple[str, float, str]]:
        """Get alternatives based on specific error types"""
        alternatives = []
        
        if not context.error:
            return alternatives
        
        error_str = str(context.error).lower()
        
        if isinstance(context.error, NetBoxNotFoundError) or "not found" in error_str:
            # For not found errors, suggest list tools
            if context.original_tool_selection:
                original_tool = context.original_tool_selection.primary_tool
                if "get_" in original_tool:
                    list_tool = original_tool.replace("get_", "list_all_")
                    alternatives.append((
                        list_tool, 0.8, 
                        "Use list tool to find available resources"
                    ))
        
        elif isinstance(context.error, NetBoxValidationError) or "validation" in error_str:
            # For validation errors, suggest tools with fewer required parameters
            if "device" in context.user_query.lower():
                alternatives.append((
                    "netbox_list_all_devices", 0.7,
                    "List devices with flexible parameters"
                ))
        
        elif isinstance(context.error, NetBoxPermissionError):
            # For permission errors, suggest read-only alternatives
            if "create" in (context.original_tool_selection.primary_tool if context.original_tool_selection else ""):
                alternatives.append((
                    "netbox_list_all_devices", 0.6,
                    "Use read-only operation to check existing resources"
                ))
        
        return alternatives


class ParameterCorrectionFallback:
    """LLM-powered parameter correction when parameters are invalid"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def correct_parameters(
        self,
        context: FallbackContext,
        tool_name: str
    ) -> Tuple[Dict[str, Any], float, str]:
        """
        Use LLM to intelligently correct parameters based on error details
        
        Returns:
            (corrected_parameters, confidence, reasoning)
        """
        if not AsyncOpenAI:
            return context.original_parameters, 0.0, "LLM not available for parameter correction"
        
        try:
            # Get tool schema for context
            tool_info = self._get_tool_schema(tool_name)
            
            config = get_config()
            client = AsyncOpenAI(api_key=config.openai.api_key)
            
            prompt = f"""
You are a NetBox MCP parameter correction expert. Fix the parameters for this tool call.

Original Query: {context.user_query}
Tool: {tool_name}
Original Parameters: {json.dumps(context.original_parameters, indent=2)}
Error: {str(context.error) if context.error else 'Unknown error'}
Tool Schema: {json.dumps(tool_info, indent=2) if tool_info else 'Schema not available'}

Common corrections:
- Add "confirm": true for create/update operations
- Convert "device-01" to "device_name": "device-01"
- Split compound identifiers like "Cisco C9200-48P" into manufacturer: "Cisco", model: "C9200-48P"
- Add missing required parameters from query context
- Fix parameter naming (e.g., "site" vs "site_name")

Provide corrected parameters as JSON, with confidence (0.0-1.0) and reasoning:
{{"parameters": {{}}, "confidence": 0.8, "reasoning": "explanation of changes made"}}
"""
            
            response = await client.chat.completions.create(
                model=config.openai.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800
            )
            
            response_text = response.choices[0].message.content.strip()
            correction_result = json.loads(response_text)
            
            return (
                correction_result["parameters"],
                correction_result["confidence"],
                correction_result["reasoning"]
            )
            
        except Exception as e:
            self.logger.warning(f"LLM parameter correction failed: {e}")
            # Fallback to basic corrections
            return self._basic_parameter_corrections(context, tool_name)
    
    def _get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool schema from registry"""
        try:
            tools = read_only_tool_registry.get_all_tools()
            if tool_name in tools:
                tool_info = tools[tool_name]
                return {
                    "parameters": getattr(tool_info, 'parameters', {}),
                    "required": getattr(tool_info, 'required_params', []),
                    "description": getattr(tool_info, 'description', '')
                }
        except Exception as e:
            self.logger.warning(f"Could not get tool schema for {tool_name}: {e}")
        return None
    
    def _basic_parameter_corrections(
        self, context: FallbackContext, tool_name: str
    ) -> Tuple[Dict[str, Any], float, str]:
        """Basic parameter corrections without LLM"""
        corrected = context.original_parameters.copy()
        corrections_made = []
        
        # Common corrections
        if context.error and "confirmation" in str(context.error).lower():
            corrected["confirm"] = True
            corrections_made.append("Added confirmation parameter")
        
        if "create" in tool_name or "update" in tool_name:
            if "confirm" not in corrected:
                corrected["confirm"] = True
                corrections_made.append("Added confirm=True for write operation")
        
        # Extract parameters from query if missing
        query_lower = context.user_query.lower()
        if "device" in query_lower and "device_name" not in corrected:
            # Try to extract device name from query
            import re
            device_match = re.search(r'device[:\s]+([a-zA-Z0-9\-_]+)', query_lower)
            if device_match:
                corrected["device_name"] = device_match.group(1)
                corrections_made.append("Extracted device name from query")
        
        if "site" in query_lower and "site_name" not in corrected and "site" not in corrected:
            site_match = re.search(r'site[:\s]+([a-zA-Z0-9\-_]+)', query_lower)
            if site_match:
                corrected["site_name"] = site_match.group(1)
                corrections_made.append("Extracted site name from query")
        
        confidence = 0.6 if corrections_made else 0.1
        reasoning = "; ".join(corrections_made) if corrections_made else "No corrections applied"
        
        return corrected, confidence, reasoning


class QueryClarificationFallback:
    """Handle ambiguous queries by seeking clarification from user"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_clarification_questions(
        self, context: FallbackContext
    ) -> List[str]:
        """Generate intelligent clarification questions"""
        questions = []
        
        # Analyze query ambiguity
        query_lower = context.user_query.lower()
        
        # Generic queries that need specificity
        if query_lower in ["show devices", "list devices", "get devices"]:
            questions.append("Which site would you like to see devices for?")
            questions.append("Are you looking for devices with a specific role (e.g., switch, server)?")
            questions.append("Do you want to filter by device status (active, planned, etc.)?")
        
        elif query_lower in ["show sites", "list sites"]:
            questions.append("Are you looking for sites in a specific region?")
            questions.append("Do you want to filter by site status or tenant?")
        
        elif "device type" in query_lower and not any(word in query_lower for word in ["cisco", "juniper", "model", "manufacturer"]):
            questions.append("Which manufacturer are you interested in (Cisco, Juniper, etc.)?")
            questions.append("Are you looking for a specific device model?")
            questions.append("What type of equipment (switch, router, server)?")
        
        # Error-specific clarifications
        if context.error:
            error_str = str(context.error).lower()
            if "not found" in error_str:
                questions.append("Could you verify the exact name or identifier?")
                questions.append("Would you like me to list available options to choose from?")
        
        # LLM-powered clarification questions
        if AsyncOpenAI and not questions:
            llm_questions = await self._generate_llm_clarification_questions(context)
            questions.extend(llm_questions)
        
        return questions[:3]  # Limit to 3 questions
    
    async def _generate_llm_clarification_questions(
        self, context: FallbackContext
    ) -> List[str]:
        """Use LLM to generate clarification questions"""
        try:
            config = get_config()
            client = AsyncOpenAI(api_key=config.openai.api_key)
            
            prompt = f"""
Generate 3 helpful clarification questions for this ambiguous NetBox query.

Query: {context.user_query}
Error: {str(context.error) if context.error else 'Query too ambiguous'}

The questions should help the user provide more specific information.
Examples:
- "Which site are you interested in?"
- "Are you looking for active or all devices?"
- "What specific information do you need about the device?"

Provide 3 questions as a JSON array: ["question1", "question2", "question3"]
"""
            
            response = await client.chat.completions.create(
                model=config.openai.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            response_text = response.choices[0].message.content.strip()
            questions = json.loads(response_text)
            
            return questions[:3]
            
        except Exception as e:
            self.logger.warning(f"LLM clarification questions failed: {e}")
            return []


class GracefulDegradationHandler:
    """Provide helpful explanations when all fallback strategies fail"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_helpful_explanation(
        self, context: FallbackContext
    ) -> Dict[str, Any]:
        """Generate helpful explanation and suggestions"""
        explanation = {
            "error_summary": self._summarize_error(context),
            "what_went_wrong": self._explain_failure(context),
            "suggested_actions": self._get_suggested_actions(context),
            "alternative_approaches": self._get_alternative_approaches(context),
            "learning_resources": self._get_learning_resources(context)
        }
        
        return explanation
    
    def _summarize_error(self, context: FallbackContext) -> str:
        """Provide a user-friendly error summary"""
        if not context.error:
            return "The requested operation could not be completed"
        
        if isinstance(context.error, NetBoxNotFoundError):
            return "The requested resource was not found in NetBox"
        elif isinstance(context.error, NetBoxValidationError):
            return "The provided parameters did not meet NetBox requirements"
        elif isinstance(context.error, NetBoxAuthError):
            return "Authentication failed - please check your NetBox credentials"
        elif isinstance(context.error, NetBoxPermissionError):
            return "You don't have permission to perform this operation"
        else:
            return f"An unexpected error occurred: {type(context.error).__name__}"
    
    def _explain_failure(self, context: FallbackContext) -> str:
        """Explain why the operation failed"""
        explanations = []
        
        if context.original_tool_selection and context.original_tool_selection.confidence < 0.5:
            explanations.append("The query was ambiguous and the system wasn't confident about the intended operation")
        
        if context.error:
            error_str = str(context.error).lower()
            if "not found" in error_str:
                explanations.append("The specified resource doesn't exist in NetBox")
            elif "validation" in error_str:
                explanations.append("The operation failed NetBox's validation rules")
            elif "permission" in error_str or "auth" in error_str:
                explanations.append("Insufficient permissions or authentication issues")
        
        if not explanations:
            explanations.append("Multiple fallback strategies were attempted but none succeeded")
        
        return ". ".join(explanations)
    
    def _get_suggested_actions(self, context: FallbackContext) -> List[str]:
        """Get actionable suggestions for the user"""
        suggestions = []
        
        # Error-specific suggestions
        if isinstance(context.error, NetBoxNotFoundError):
            suggestions.extend([
                "Use list commands to see available resources (e.g., 'list all devices')",
                "Check the spelling and format of resource names",
                "Verify the resource exists in the correct site or location"
            ])
        elif isinstance(context.error, NetBoxValidationError):
            suggestions.extend([
                "Review the required parameters for this operation",
                "Check that all values are in the correct format",
                "Ensure required relationships exist (e.g., site before rack)"
            ])
        elif isinstance(context.error, NetBoxAuthError):
            suggestions.extend([
                "Verify your NetBox API token is valid",
                "Check that the token has the required permissions",
                "Confirm the NetBox URL is correct"
            ])
        
        # Query-specific suggestions
        if context.user_query:
            query_lower = context.user_query.lower()
            if len(query_lower.split()) < 3:
                suggestions.append("Try providing more specific details in your query")
            if not any(word in query_lower for word in ["site", "device", "rack", "cable"]):
                suggestions.append("Specify what type of NetBox resource you're working with")
        
        # Generic helpful suggestions
        if not suggestions:
            suggestions.extend([
                "Try breaking down complex requests into simpler steps",
                "Use 'list all' commands to explore available resources",
                "Provide more context about what you're trying to accomplish"
            ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _get_alternative_approaches(self, context: FallbackContext) -> List[str]:
        """Suggest alternative approaches"""
        approaches = []
        
        if context.original_tool_selection:
            tool_name = context.original_tool_selection.primary_tool
            
            if "create" in tool_name:
                approaches.append("Check if the resource already exists using a list or get command")
                approaches.append("Try using a provisioning command that handles dependencies automatically")
            elif "get" in tool_name:
                approaches.append("Use a list command to see all available options")
                approaches.append("Try searching with partial names or different identifiers")
            elif "update" in tool_name:
                approaches.append("Verify the resource exists before trying to update it")
                approaches.append("Use get commands to check current values before making changes")
        
        if not approaches:
            approaches.extend([
                "Start with read-only operations to explore the NetBox environment",
                "Use the NetBox web interface to verify resource names and relationships",
                "Try simpler queries to build up to more complex operations"
            ])
        
        return approaches[:3]
    
    def _get_learning_resources(self, context: FallbackContext) -> List[str]:
        """Provide learning resources"""
        return [
            "NetBox documentation: https://docs.netbox.dev/",
            "Use 'help' commands to see available tools and their parameters",
            "Try 'list all' commands to explore what's available in your NetBox instance"
        ]


class IntelligentFallbackOrchestrator:
    """Main fallback coordination that replaces error_recovery.py with intelligent recovery"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tool_selection_fallback = ToolSelectionFallback()
        self.parameter_correction_fallback = ParameterCorrectionFallback()
        self.query_clarification_fallback = QueryClarificationFallback()
        self.graceful_degradation_handler = GracefulDegradationHandler()
        
        # Statistics
        self.fallback_stats = {
            "total_fallback_attempts": 0,
            "successful_fallbacks": 0,
            "fallback_levels_used": {level.value: 0 for level in FallbackLevel},
            "fallback_reasons": {reason.value: 0 for reason in FallbackReason}
        }
    
    async def execute_with_intelligent_fallback(
        self,
        user_query: str,
        tool_selection: Optional[ToolSelection] = None,
        parameters: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None
    ) -> FallbackResult:
        """
        Execute with intelligent multi-level fallback strategy
        
        This replaces the existing error recovery with Claude Code CLI-style intelligence
        """
        start_time = datetime.now()
        self.fallback_stats["total_fallback_attempts"] += 1
        
        # Initialize context
        context = FallbackContext(
            user_query=user_query,
            original_tool_selection=tool_selection,
            original_parameters=parameters or {},
            error=None,
            error_details={},
            session_context=session_context or {}
        )
        
        # Try primary execution first
        primary_result = await self._try_primary_execution(context)
        if primary_result.success:
            self.fallback_stats["successful_fallbacks"] += 1
            return primary_result
        
        # Update context with primary failure
        context.error = primary_result.error if hasattr(primary_result, 'error') else None
        context.attempt_history.append({
            "level": FallbackLevel.PRIMARY.value,
            "success": False,
            "error": str(context.error) if context.error else "Unknown error"
        })
        
        # Execute fallback levels in order
        for fallback_level in [
            FallbackLevel.PARAMETER_CORRECTION,
            FallbackLevel.ALTERNATIVE_TOOL_SELECTION,
            FallbackLevel.QUERY_CLARIFICATION,
            FallbackLevel.GRACEFUL_DEGRADATION
        ]:
            try:
                self.fallback_stats["fallback_levels_used"][fallback_level.value] += 1
                
                fallback_result = await self._execute_fallback_level(
                    fallback_level, context, start_time
                )
                
                if fallback_result.success or fallback_level == FallbackLevel.GRACEFUL_DEGRADATION:
                    if fallback_result.success:
                        self.fallback_stats["successful_fallbacks"] += 1
                    return fallback_result
                
                # Update context for next fallback level
                context.attempt_history.append({
                    "level": fallback_level.value,
                    "success": False,
                    "reasoning": fallback_result.reasoning
                })
                
            except Exception as e:
                self.logger.warning(f"Fallback level {fallback_level.value} failed: {e}")
                continue
        
        # This should not be reached, but handle it anyway
        return await self._create_final_degradation_result(context, start_time)
    
    async def _try_primary_execution(self, context: FallbackContext) -> FallbackResult:
        """Try primary execution with Phase 1 + Phase 2 integration"""
        try:
            # If no tool selection provided, do intelligent tool selection (Phase 1)
            if not context.original_tool_selection:
                tool_selection = await select_tool(context.user_query)
                context.original_tool_selection = tool_selection
            
            # If no parameters provided, do tool-aware parameter extraction (Phase 2)
            if not context.original_parameters and context.original_tool_selection:
                param_result = await extract_parameters(
                    context.user_query, 
                    context.original_tool_selection.primary_tool
                )
                context.original_parameters = param_result.parameters
            
            # Execute the tool
            if context.original_tool_selection and context.original_parameters:
                result = await execute_real_netbox_tool(
                    context.original_tool_selection.primary_tool,
                    context.original_parameters
                )
                
                return FallbackResult(
                    success=True,
                    fallback_level=FallbackLevel.PRIMARY,
                    fallback_reason=FallbackReason.TOOL_SELECTION_FAILED,  # Will be updated if needed
                    tool_name=context.original_tool_selection.primary_tool,
                    parameters=context.original_parameters,
                    result=result,
                    confidence=context.original_tool_selection.confidence,
                    reasoning="Primary execution successful",
                    suggestions=[],
                    execution_time=(datetime.now() - datetime.now()).total_seconds(),
                    timestamp=datetime.now()
                )
            else:
                raise ValueError("No tool selection or parameters available")
                
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_level=FallbackLevel.PRIMARY,
                fallback_reason=self._determine_fallback_reason(e),
                tool_name=context.original_tool_selection.primary_tool if context.original_tool_selection else None,
                parameters=context.original_parameters,
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Primary execution failed: {str(e)}",
                suggestions=[],
                execution_time=0.0,
                timestamp=datetime.now()
            )
    
    async def _execute_fallback_level(
        self, 
        level: FallbackLevel, 
        context: FallbackContext,
        start_time: datetime
    ) -> FallbackResult:
        """Execute specific fallback level"""
        
        if level == FallbackLevel.PARAMETER_CORRECTION:
            return await self._try_parameter_correction(context, start_time)
        
        elif level == FallbackLevel.ALTERNATIVE_TOOL_SELECTION:
            return await self._try_alternative_tool_selection(context, start_time)
        
        elif level == FallbackLevel.QUERY_CLARIFICATION:
            return await self._try_query_clarification(context, start_time)
        
        elif level == FallbackLevel.GRACEFUL_DEGRADATION:
            return await self._try_graceful_degradation(context, start_time)
        
        else:
            raise ValueError(f"Unknown fallback level: {level}")
    
    async def _try_parameter_correction(
        self, context: FallbackContext, start_time: datetime
    ) -> FallbackResult:
        """Try parameter correction fallback"""
        if not context.original_tool_selection:
            return FallbackResult(
                success=False,
                fallback_level=FallbackLevel.PARAMETER_CORRECTION,
                fallback_reason=FallbackReason.PARAMETER_EXTRACTION_FAILED,
                tool_name=None,
                parameters={},
                result={"error": "No tool selection available"},
                confidence=0.0,
                reasoning="Cannot correct parameters without tool selection",
                suggestions=["Provide more specific query"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now()
            )
        
        try:
            # Try parameter correction
            corrected_params, confidence, reasoning = await self.parameter_correction_fallback.correct_parameters(
                context, context.original_tool_selection.primary_tool
            )
            
            if confidence > 0.5:
                # Try execution with corrected parameters
                result = await execute_real_netbox_tool(
                    context.original_tool_selection.primary_tool,
                    corrected_params
                )
                
                return FallbackResult(
                    success=True,
                    fallback_level=FallbackLevel.PARAMETER_CORRECTION,
                    fallback_reason=FallbackReason.PARAMETER_EXTRACTION_FAILED,
                    tool_name=context.original_tool_selection.primary_tool,
                    parameters=corrected_params,
                    result=result,
                    confidence=confidence,
                    reasoning=f"Parameter correction successful: {reasoning}",
                    suggestions=[],
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now()
                )
            else:
                return FallbackResult(
                    success=False,
                    fallback_level=FallbackLevel.PARAMETER_CORRECTION,
                    fallback_reason=FallbackReason.PARAMETER_EXTRACTION_FAILED,
                    tool_name=context.original_tool_selection.primary_tool,
                    parameters=corrected_params,
                    result={"error": "Parameter correction confidence too low"},
                    confidence=confidence,
                    reasoning=f"Parameter correction attempted but confidence too low: {reasoning}",
                    suggestions=["Provide more specific parameters", "Check parameter format"],
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_level=FallbackLevel.PARAMETER_CORRECTION,
                fallback_reason=FallbackReason.PARAMETER_EXTRACTION_FAILED,
                tool_name=context.original_tool_selection.primary_tool if context.original_tool_selection else None,
                parameters=context.original_parameters,
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Parameter correction failed: {str(e)}",
                suggestions=["Check parameter format and requirements"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now()
            )
    
    async def _try_alternative_tool_selection(
        self, context: FallbackContext, start_time: datetime
    ) -> FallbackResult:
        """Try alternative tool selection fallback"""
        try:
            # Get alternative tools
            alternatives = await self.tool_selection_fallback.suggest_alternatives(context)
            
            if not alternatives:
                return FallbackResult(
                    success=False,
                    fallback_level=FallbackLevel.ALTERNATIVE_TOOL_SELECTION,
                    fallback_reason=FallbackReason.TOOL_SELECTION_FAILED,
                    tool_name=None,
                    parameters={},
                    result={"error": "No alternative tools found"},
                    confidence=0.0,
                    reasoning="No alternative tools could be suggested",
                    suggestions=["Try rephrasing your query", "Be more specific about what you want"],
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now()
                )
            
            # Try each alternative
            for tool_name, confidence, reasoning in alternatives:
                try:
                    # Extract parameters for alternative tool
                    param_result = await extract_parameters(context.user_query, tool_name)
                    
                    # Try execution
                    result = await execute_real_netbox_tool(tool_name, param_result.parameters)
                    
                    return FallbackResult(
                        success=True,
                        fallback_level=FallbackLevel.ALTERNATIVE_TOOL_SELECTION,
                        fallback_reason=FallbackReason.TOOL_SELECTION_FAILED,
                        tool_name=tool_name,
                        parameters=param_result.parameters,
                        result=result,
                        confidence=confidence,
                        reasoning=f"Alternative tool successful: {reasoning}",
                        suggestions=[],
                        execution_time=(datetime.now() - start_time).total_seconds(),
                        timestamp=datetime.now(),
                        alternative_approaches=[
                            {"tool": alt_tool, "confidence": alt_conf, "reasoning": alt_reason}
                            for alt_tool, alt_conf, alt_reason in alternatives[1:]
                        ]
                    )
                
                except Exception as e:
                    self.logger.debug(f"Alternative tool {tool_name} failed: {e}")
                    continue
            
            # All alternatives failed
            return FallbackResult(
                success=False,
                fallback_level=FallbackLevel.ALTERNATIVE_TOOL_SELECTION,
                fallback_reason=FallbackReason.TOOL_SELECTION_FAILED,
                tool_name=None,
                parameters={},
                result={"error": "All alternative tools failed"},
                confidence=0.0,
                reasoning="Alternative tools were suggested but all failed execution",
                suggestions=["Try a different approach", "Check your query for accuracy"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                alternative_approaches=[
                    {"tool": alt_tool, "confidence": alt_conf, "reasoning": alt_reason}
                    for alt_tool, alt_conf, alt_reason in alternatives
                ]
            )
        
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_level=FallbackLevel.ALTERNATIVE_TOOL_SELECTION,
                fallback_reason=FallbackReason.TOOL_SELECTION_FAILED,
                tool_name=None,
                parameters={},
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Alternative tool selection failed: {str(e)}",
                suggestions=["Try a simpler query", "Provide more context"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now()
            )
    
    async def _try_query_clarification(
        self, context: FallbackContext, start_time: datetime
    ) -> FallbackResult:
        """Try query clarification fallback"""
        try:
            questions = await self.query_clarification_fallback.generate_clarification_questions(context)
            
            return FallbackResult(
                success=False,  # This is intentionally False - we need user input
                fallback_level=FallbackLevel.QUERY_CLARIFICATION,
                fallback_reason=FallbackReason.AMBIGUOUS_QUERY,
                tool_name=None,
                parameters={},
                result={"clarification_needed": True, "questions": questions},
                confidence=0.0,
                reasoning="Query is too ambiguous - user clarification needed",
                suggestions=["Answer the clarification questions to proceed"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                clarification_questions=questions
            )
        
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_level=FallbackLevel.QUERY_CLARIFICATION,
                fallback_reason=FallbackReason.AMBIGUOUS_QUERY,
                tool_name=None,
                parameters={},
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Query clarification failed: {str(e)}",
                suggestions=["Try providing more specific details in your query"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now()
            )
    
    async def _try_graceful_degradation(
        self, context: FallbackContext, start_time: datetime
    ) -> FallbackResult:
        """Try graceful degradation - always succeeds with helpful explanation"""
        try:
            explanation = await self.graceful_degradation_handler.generate_helpful_explanation(context)
            
            return FallbackResult(
                success=False,  # Graceful degradation is a "successful failure"
                fallback_level=FallbackLevel.GRACEFUL_DEGRADATION,
                fallback_reason=self._determine_primary_fallback_reason(context),
                tool_name=None,
                parameters={},
                result=explanation,
                confidence=0.0,
                reasoning="All fallback strategies exhausted - providing helpful explanation",
                suggestions=explanation.get("suggested_actions", []),
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                alternative_approaches=[
                    {"approach": approach, "description": "Manual alternative"}
                    for approach in explanation.get("alternative_approaches", [])
                ]
            )
        
        except Exception as e:
            # Even graceful degradation failed - provide minimal response
            return FallbackResult(
                success=False,
                fallback_level=FallbackLevel.GRACEFUL_DEGRADATION,
                fallback_reason=FallbackReason.INSUFFICIENT_CONTEXT,
                tool_name=None,
                parameters={},
                result={
                    "error_summary": "The operation could not be completed",
                    "suggested_actions": [
                        "Try breaking down your request into simpler steps",
                        "Use more specific terms in your query",
                        "Check the spelling and format of resource names"
                    ]
                },
                confidence=0.0,
                reasoning="Graceful degradation with minimal response",
                suggestions=["Try a simpler query", "Provide more context"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now()
            )
    
    async def _create_final_degradation_result(
        self, context: FallbackContext, start_time: datetime
    ) -> FallbackResult:
        """Create final degradation result when all fallbacks fail"""
        return FallbackResult(
            success=False,
            fallback_level=FallbackLevel.GRACEFUL_DEGRADATION,
            fallback_reason=FallbackReason.INSUFFICIENT_CONTEXT,
            tool_name=None,
            parameters={},
            result={
                "error_summary": "All fallback strategies have been exhausted",
                "attempted_fallbacks": [attempt["level"] for attempt in context.attempt_history],
                "suggested_actions": [
                    "Try rephrasing your query with more specific details",
                    "Break complex requests into simpler steps",
                    "Use NetBox web interface to verify resource names"
                ]
            },
            confidence=0.0,
            reasoning="Final fallback - all strategies exhausted",
            suggestions=["Try a completely different approach to your query"],
            execution_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now()
        )
    
    def _determine_fallback_reason(self, error: Exception) -> FallbackReason:
        """Determine the primary reason for fallback activation"""
        if isinstance(error, NetBoxNotFoundError):
            return FallbackReason.NOT_FOUND_ERROR
        elif isinstance(error, NetBoxValidationError):
            return FallbackReason.VALIDATION_ERROR
        elif isinstance(error, (NetBoxAuthError, NetBoxPermissionError)):
            return FallbackReason.VALIDATION_ERROR
        else:
            return FallbackReason.TOOL_EXECUTION_FAILED
    
    def _determine_primary_fallback_reason(self, context: FallbackContext) -> FallbackReason:
        """Determine the primary reason from context"""
        if context.error:
            return self._determine_fallback_reason(context.error)
        elif not context.original_tool_selection:
            return FallbackReason.TOOL_SELECTION_FAILED
        elif not context.original_parameters:
            return FallbackReason.PARAMETER_EXTRACTION_FAILED
        else:
            return FallbackReason.INSUFFICIENT_CONTEXT
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get fallback system statistics"""
        return {
            "fallback_stats": self.fallback_stats.copy(),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
intelligent_fallback_orchestrator = IntelligentFallbackOrchestrator()


# Public interface functions
async def execute_with_intelligent_fallback(
    user_query: str,
    tool_selection: Optional[ToolSelection] = None,
    parameters: Optional[Dict[str, Any]] = None,
    session_context: Optional[Dict[str, Any]] = None
) -> FallbackResult:
    """
    Public interface for intelligent fallback execution
    
    This is the main entry point that replaces the existing error recovery
    with Claude Code CLI-style intelligent fallback strategies.
    """
    return await intelligent_fallback_orchestrator.execute_with_intelligent_fallback(
        user_query, tool_selection, parameters, session_context
    )


def get_intelligent_fallback_statistics() -> Dict[str, Any]:
    """Get intelligent fallback system statistics"""
    return intelligent_fallback_orchestrator.get_fallback_statistics()