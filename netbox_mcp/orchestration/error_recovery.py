#!/usr/bin/env python3
"""
Comprehensive Error Recovery and Fallback System

This module implements production-ready error recovery mechanisms including:
- Automatic fallback tool execution
- Circuit breaker pattern for failing tools
- Comprehensive error classification
- Smart retry logic with exponential backoff
- Parameter validation and correction
- Graceful degradation strategies

The system ensures users get helpful responses even when primary tools fail.
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict

from ..exceptions import (
    NetBoxError, NetBoxConnectionError, NetBoxAuthError, NetBoxValidationError,
    NetBoxNotFoundError, NetBoxPermissionError, NetBoxWriteError, 
    NetBoxConfirmationError, NetBoxConflictError
)
from .param_validator import validate_tool_parameters, ValidationResult
from .tool_mapper import map_query_to_tool, get_tool_info

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for recovery strategies."""
    NETWORK_ERROR = "network"
    AUTHENTICATION_ERROR = "auth"
    VALIDATION_ERROR = "validation"
    NOT_FOUND_ERROR = "not_found"
    PERMISSION_ERROR = "permission"
    CONFLICT_ERROR = "conflict"
    TIMEOUT_ERROR = "timeout"
    RATE_LIMIT_ERROR = "rate_limit"
    CONFIRMATION_ERROR = "confirmation"
    SYSTEM_ERROR = "system"
    UNKNOWN_ERROR = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    PARAMETER_CORRECTION = "parameter_correction"
    ALTERNATIVE_APPROACH = "alternative"
    GRACEFUL_DEGRADATION = "degradation"
    USER_INTERVENTION = "user_intervention"
    CIRCUIT_BREAK = "circuit_break"


@dataclass
class ErrorClassification:
    """Classification and analysis of an error."""
    error_type: ErrorType
    is_transient: bool
    is_recoverable: bool
    recovery_strategies: List[RecoveryStrategy]
    retry_count: int = 0
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    base_delay: float = 1.0
    confidence_score: float = 1.0
    error_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker for a specific tool."""
    tool_name: str
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half_open
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 2  # successful calls to close circuit


@dataclass
class FallbackExecution:
    """Result of fallback tool execution."""
    original_tool: str
    fallback_tool: str
    success: bool
    result: Any
    execution_time: float
    error: Optional[str] = None
    fallback_reason: str = ""
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.FALLBACK


class ErrorRecoveryEngine:
    """
    Comprehensive error recovery engine with circuit breakers and fallbacks.
    
    Provides intelligent error handling, automatic fallback execution, and
    graceful degradation to ensure users always get helpful responses.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.error_history: Dict[str, List[datetime]] = defaultdict(list)
        self.recovery_stats = {
            "total_errors": 0,
            "recovered_errors": 0,
            "fallback_successes": 0,
            "circuit_breaks": 0,
            "parameter_corrections": 0
        }
        self.logger = logging.getLogger(__name__)
    
    async def execute_with_recovery(
        self,
        tool_name: str,
        params: Dict[str, Any],
        execute_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with comprehensive error recovery.
        
        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            execute_func: Function to execute the tool
            context: Optional execution context
            
        Returns:
            Execution result with recovery information
        """
        self.logger.debug(f"Executing tool '{tool_name}' with recovery")
        
        # Check circuit breaker
        if self._is_circuit_open(tool_name):
            return await self._handle_circuit_open(tool_name, params, context)
        
        # Validate and correct parameters
        validation_result = validate_tool_parameters(tool_name, params, context)
        if not validation_result.is_valid:
            return await self._handle_parameter_validation_error(
                tool_name, params, validation_result, execute_func, context
            )
        
        # Use normalized parameters
        normalized_params = validation_result.normalized_params
        
        # Attempt primary execution
        start_time = time.time()
        try:
            result = await execute_func(tool_name, normalized_params)
            execution_time = time.time() - start_time
            
            # Success - update circuit breaker
            self._record_success(tool_name)
            
            return {
                "tool_name": tool_name,
                "params": normalized_params,
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "recovery_used": False,
                "parameter_corrections": validation_result.auto_corrections
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.recovery_stats["total_errors"] += 1
            
            # Classify error
            error_classification = self._classify_error(e, tool_name)
            self.logger.warning(
                f"Tool '{tool_name}' failed: {error_classification.error_type.value} - {str(e)}"
            )
            
            # Record failure for circuit breaker
            self._record_failure(tool_name)
            
            # Attempt recovery
            recovery_result = await self._attempt_recovery(
                tool_name, normalized_params, e, error_classification, 
                execute_func, context
            )
            
            if recovery_result["success"]:
                self.recovery_stats["recovered_errors"] += 1
                self.logger.info(f"Successfully recovered from error using {recovery_result.get('recovery_strategy')}")
            
            # Preserve parameter corrections from recovery strategies
            existing_corrections = recovery_result.get("parameter_corrections", {})
            validation_corrections = validation_result.auto_corrections
            
            # Merge corrections (recovery strategy corrections take precedence)
            merged_corrections = {**validation_corrections, **existing_corrections}
            
            recovery_result.update({
                "original_error": str(e),
                "error_type": error_classification.error_type.value,
                "execution_time": execution_time,
                "parameter_corrections": merged_corrections
            })
            
            return recovery_result
    
    async def execute_with_fallbacks(
        self,
        tools: List[Dict[str, Any]],
        execute_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tools with automatic fallbacks.
        
        Args:
            tools: List of tool specifications
            execute_func: Function to execute tools
            context: Optional execution context
            
        Returns:
            List of execution results with fallback information
        """
        results = []
        
        for tool_spec in tools:
            # Handle malformed tool definitions gracefully
            if not isinstance(tool_spec, dict):
                results.append({
                    "tool_name": "malformed_tool",
                    "params": {},
                    "success": False,
                    "error": "Tool specification must be a dictionary",
                    "result": {"error": "Tool specification must be a dictionary"},
                    "execution_time": 0.0,
                    "timestamp": datetime.now().isoformat()
                })
                continue
                
            if "name" not in tool_spec:
                results.append({
                    "tool_name": "unnamed_tool",
                    "params": tool_spec.get("params", {}),
                    "success": False,
                    "error": "Tool specification missing required 'name' field",
                    "result": {"error": "Tool specification missing required 'name' field"},
                    "execution_time": 0.0,
                    "timestamp": datetime.now().isoformat()
                })
                continue
                
            tool_name = tool_spec["name"]
            params = tool_spec.get("params", {})
            
            # Execute with recovery
            result = await self.execute_with_recovery(
                tool_name, params, execute_func, context
            )
            
            # If primary execution failed, try fallbacks
            if not result["success"]:
                fallback_result = await self._try_fallback_tools(
                    tool_name, params, execute_func, context
                )
                
                if fallback_result["success"]:
                    result = fallback_result
                    self.recovery_stats["fallback_successes"] += 1
            
            results.append(result)
        
        return results
    
    def _classify_error(self, error: Exception, tool_name: str) -> ErrorClassification:
        """Classify an error and determine recovery strategies."""
        
        # NetBox-specific error classification
        if isinstance(error, NetBoxConnectionError):
            return ErrorClassification(
                error_type=ErrorType.NETWORK_ERROR,
                is_transient=True,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.RETRY,
                    RecoveryStrategy.FALLBACK,
                    RecoveryStrategy.GRACEFUL_DEGRADATION
                ],
                max_retries=3,
                base_delay=2.0,
                error_details={"connection_issue": str(error)}
            )
        
        elif isinstance(error, NetBoxAuthError):
            return ErrorClassification(
                error_type=ErrorType.AUTHENTICATION_ERROR,
                is_transient=False,
                is_recoverable=False,
                recovery_strategies=[
                    RecoveryStrategy.USER_INTERVENTION,
                    RecoveryStrategy.GRACEFUL_DEGRADATION
                ],
                max_retries=0,
                error_details={"auth_issue": str(error)}
            )
        
        elif isinstance(error, NetBoxValidationError):
            return ErrorClassification(
                error_type=ErrorType.VALIDATION_ERROR,
                is_transient=False,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.PARAMETER_CORRECTION,
                    RecoveryStrategy.FALLBACK,
                    RecoveryStrategy.ALTERNATIVE_APPROACH
                ],
                max_retries=1,
                error_details={"validation_issue": str(error)}
            )
        
        elif isinstance(error, NetBoxNotFoundError):
            return ErrorClassification(
                error_type=ErrorType.NOT_FOUND_ERROR,
                is_transient=False,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.FALLBACK,
                    RecoveryStrategy.ALTERNATIVE_APPROACH,
                    RecoveryStrategy.GRACEFUL_DEGRADATION
                ],
                max_retries=0,
                error_details={"not_found": str(error)}
            )
        
        elif isinstance(error, NetBoxPermissionError):
            return ErrorClassification(
                error_type=ErrorType.PERMISSION_ERROR,
                is_transient=False,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.FALLBACK,
                    RecoveryStrategy.GRACEFUL_DEGRADATION,
                    RecoveryStrategy.USER_INTERVENTION
                ],
                max_retries=0,
                error_details={"permission_issue": str(error)}
            )
        
        elif isinstance(error, NetBoxConflictError):
            return ErrorClassification(
                error_type=ErrorType.CONFLICT_ERROR,
                is_transient=False,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.ALTERNATIVE_APPROACH,
                    RecoveryStrategy.FALLBACK,
                    RecoveryStrategy.USER_INTERVENTION
                ],
                max_retries=0,
                error_details={"conflict": str(error)}
            )
        
        elif isinstance(error, NetBoxConfirmationError):
            return ErrorClassification(
                error_type=ErrorType.CONFIRMATION_ERROR,
                is_transient=False,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.PARAMETER_CORRECTION,
                    RecoveryStrategy.USER_INTERVENTION
                ],
                max_retries=0,
                error_details={"confirmation_needed": str(error)}
            )
        
        # General error patterns
        error_str = str(error).lower()
        
        if any(keyword in error_str for keyword in ['confirmation', 'confirm']):
            return ErrorClassification(
                error_type=ErrorType.CONFIRMATION_ERROR,
                is_transient=False,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.PARAMETER_CORRECTION,
                    RecoveryStrategy.USER_INTERVENTION
                ],
                max_retries=0,
                error_details={"confirmation_needed": str(error)}
            )
        
        elif any(keyword in error_str for keyword in ['timeout', 'timed out', 'connection timeout']):
            return ErrorClassification(
                error_type=ErrorType.TIMEOUT_ERROR,
                is_transient=True,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.RETRY,
                    RecoveryStrategy.FALLBACK
                ],
                max_retries=2,
                base_delay=5.0,
                error_details={"timeout": str(error)}
            )
        
        elif any(keyword in error_str for keyword in ['rate limit', 'too many requests', '429']):
            return ErrorClassification(
                error_type=ErrorType.RATE_LIMIT_ERROR,
                is_transient=True,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.RETRY,
                    RecoveryStrategy.FALLBACK
                ],
                max_retries=2,
                base_delay=10.0,
                backoff_multiplier=3.0,
                error_details={"rate_limit": str(error)}
            )
        
        elif any(keyword in error_str for keyword in ['connection', 'network', 'unreachable']):
            return ErrorClassification(
                error_type=ErrorType.NETWORK_ERROR,
                is_transient=True,
                is_recoverable=True,
                recovery_strategies=[
                    RecoveryStrategy.RETRY,
                    RecoveryStrategy.FALLBACK,
                    RecoveryStrategy.GRACEFUL_DEGRADATION
                ],
                max_retries=3,
                error_details={"network_issue": str(error)}
            )
        
        # Default classification
        return ErrorClassification(
            error_type=ErrorType.UNKNOWN_ERROR,
            is_transient=True,
            is_recoverable=True,
            recovery_strategies=[
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FALLBACK,
                RecoveryStrategy.GRACEFUL_DEGRADATION
            ],
            max_retries=2,
            confidence_score=0.5,
            error_details={"unknown": str(error)}
        )
    
    async def _attempt_recovery(
        self,
        tool_name: str,
        params: Dict[str, Any],
        error: Exception,
        classification: ErrorClassification,
        execute_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Attempt to recover from an error using various strategies."""
        
        for strategy in classification.recovery_strategies:
            try:
                if strategy == RecoveryStrategy.RETRY:
                    result = await self._retry_with_backoff(
                        tool_name, params, classification, execute_func
                    )
                    if result["success"]:
                        return result
                
                elif strategy == RecoveryStrategy.FALLBACK:
                    result = await self._try_fallback_tools(
                        tool_name, params, execute_func, context
                    )
                    if result["success"]:
                        return result
                
                elif strategy == RecoveryStrategy.PARAMETER_CORRECTION:
                    result = await self._attempt_parameter_correction(
                        tool_name, params, error, execute_func, context
                    )
                    if result["success"]:
                        return result
                
                elif strategy == RecoveryStrategy.ALTERNATIVE_APPROACH:
                    result = await self._try_alternative_approach(
                        tool_name, params, execute_func, context
                    )
                    if result["success"]:
                        return result
                
                elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                    return await self._graceful_degradation(
                        tool_name, params, error, context
                    )
                
            except Exception as recovery_error:
                self.logger.warning(f"Recovery strategy {strategy} failed: {recovery_error}")
                continue
        
        # All recovery strategies failed
        return {
            "tool_name": tool_name,
            "params": params,
            "success": False,
            "error": str(error),
            "result": {
                "success": False,
                "error": str(error),
                "error_type": classification.error_type.value,
                "recovery_attempted": True,
                "recovery_failed": True
            },
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "failed"
        }
    
    async def _retry_with_backoff(
        self,
        tool_name: str,
        params: Dict[str, Any],
        classification: ErrorClassification,
        execute_func: callable
    ) -> Dict[str, Any]:
        """Retry execution with exponential backoff."""
        
        for attempt in range(classification.max_retries):
            if attempt > 0:
                delay = classification.base_delay * (classification.backoff_multiplier ** (attempt - 1))
                # Add jitter to prevent thundering herd
                jitter = random.uniform(0.1, 0.3) * delay
                total_delay = delay + jitter
                
                self.logger.debug(f"Retrying {tool_name} in {total_delay:.2f} seconds (attempt {attempt + 1})")
                await asyncio.sleep(total_delay)
            
            try:
                start_time = time.time()
                result = await execute_func(tool_name, params)
                execution_time = time.time() - start_time
                
                return {
                    "tool_name": tool_name,
                    "params": params,
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "recovery_used": True,
                    "recovery_strategy": "retry",
                    "retry_attempt": attempt + 1
                }
                
            except Exception as retry_error:
                self.logger.warning(f"Retry attempt {attempt + 1} failed: {retry_error}")
                if attempt == classification.max_retries - 1:
                    # Last attempt failed
                    return {
                        "tool_name": tool_name,
                        "params": params,
                        "success": False,
                        "result": {
                            "success": False,
                            "error": str(retry_error),
                            "retry_attempts": attempt + 1
                        },
                        "timestamp": datetime.now().isoformat(),
                        "recovery_used": True,
                        "recovery_strategy": "retry_failed"
                    }
        
        # This shouldn't be reached but handle it anyway
        return {
            "tool_name": tool_name,
            "params": params,
            "success": False,
            "result": {"success": False, "error": "All retry attempts failed"},
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "retry_failed"
        }
    
    async def _try_fallback_tools(
        self,
        original_tool: str,
        params: Dict[str, Any],
        execute_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Try fallback tools for the original tool."""
        
        # Get fallback tools from tool mapper
        tool_info = get_tool_info(original_tool)
        if not tool_info or not tool_info.fallback_tools:
            return {
                "tool_name": original_tool,
                "params": params,
                "success": False,
                "result": {"success": False, "error": "No fallback tools available"},
                "timestamp": datetime.now().isoformat(),
                "recovery_used": True,
                "recovery_strategy": "no_fallbacks"
            }
        
        # Try each fallback tool
        for fallback_tool in tool_info.fallback_tools:
            if self._is_circuit_open(fallback_tool):
                self.logger.debug(f"Skipping fallback tool {fallback_tool} - circuit is open")
                continue
            
            try:
                # Validate parameters for fallback tool
                validation_result = validate_tool_parameters(fallback_tool, params, context)
                fallback_params = validation_result.normalized_params
                
                self.logger.info(f"Trying fallback tool: {fallback_tool}")
                start_time = time.time()
                result = await execute_func(fallback_tool, fallback_params)
                execution_time = time.time() - start_time
                
                # Success with fallback tool
                self._record_success(fallback_tool)
                
                return {
                    "tool_name": fallback_tool,
                    "original_tool": original_tool,
                    "params": fallback_params,
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "recovery_used": True,
                    "recovery_strategy": "fallback",
                    "fallback_tool_used": fallback_tool,
                    "parameter_corrections": validation_result.auto_corrections
                }
                
            except Exception as fallback_error:
                self.logger.warning(f"Fallback tool {fallback_tool} failed: {fallback_error}")
                self._record_failure(fallback_tool)
                continue
        
        # All fallback tools failed
        return {
            "tool_name": original_tool,
            "params": params,
            "success": False,
            "result": {
                "success": False,
                "error": "All fallback tools failed",
                "fallback_tools_tried": tool_info.fallback_tools
            },
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "fallbacks_failed"
        }
    
    async def _attempt_parameter_correction(
        self,
        tool_name: str,
        params: Dict[str, Any],
        error: Exception,
        execute_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Attempt to correct parameters based on error information."""
        
        corrected_params = params.copy()
        corrections_made = {}
        
        error_str = str(error).lower()
        
        # Common parameter corrections based on error patterns
        if "confirmation" in error_str or "confirm" in error_str:
            corrected_params["confirm"] = True
            corrections_made["confirm"] = "Added confirmation parameter"
        
        if "required" in error_str and "missing" in error_str:
            # Try to infer missing parameters from context
            if context:
                for key, value in context.items():
                    if key.endswith("_name") and key not in corrected_params:
                        corrected_params[key] = value
                        corrections_made[key] = f"Inferred from context: {value}"
        
        # Only attempt execution if we made corrections
        if corrections_made:
            try:
                self.logger.info(f"Attempting parameter correction for {tool_name}: {corrections_made}")
                start_time = time.time()
                result = await execute_func(tool_name, corrected_params)
                execution_time = time.time() - start_time
                
                self.recovery_stats["parameter_corrections"] += 1
                
                return {
                    "tool_name": tool_name,
                    "params": corrected_params,
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "recovery_used": True,
                    "recovery_strategy": "parameter_correction",
                    "parameter_corrections": corrections_made
                }
                
            except Exception as correction_error:
                self.logger.warning(f"Parameter correction failed: {correction_error}")
        
        return {
            "tool_name": tool_name,
            "params": params,
            "success": False,
            "error": "Parameter correction failed",
            "result": {"success": False, "error": "Parameter correction failed"},
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "parameter_correction_failed",
            "parameter_corrections": corrections_made if 'corrections_made' in locals() else {}
        }
    
    async def _try_alternative_approach(
        self,
        tool_name: str,
        params: Dict[str, Any],
        execute_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Try alternative approaches based on tool type and context."""
        
        # For list tools, try get tools if specific entity is mentioned
        if "list_all" in tool_name and context:
            # Extract entity name from context
            entity_name = None
            for key, value in context.items():
                if isinstance(value, str) and len(value) > 0:
                    entity_name = value
                    break
            
            if entity_name:
                # Try corresponding get tool
                get_tool = tool_name.replace("list_all", "get").replace("s_", "_")
                if get_tool != tool_name:
                    try:
                        alternative_params = params.copy()
                        # Add entity name parameter
                        if "site" in get_tool and "site_name" not in alternative_params:
                            alternative_params["site_name"] = entity_name
                        elif "device" in get_tool and "device_name" not in alternative_params:
                            alternative_params["device_name"] = entity_name
                        
                        start_time = time.time()
                        result = await execute_func(get_tool, alternative_params)
                        execution_time = time.time() - start_time
                        
                        return {
                            "tool_name": get_tool,
                            "original_tool": tool_name,
                            "params": alternative_params,
                            "success": True,
                            "result": result,
                            "execution_time": execution_time,
                            "timestamp": datetime.now().isoformat(),
                            "recovery_used": True,
                            "recovery_strategy": "alternative_approach",
                            "alternative_tool_used": get_tool
                        }
                        
                    except Exception as alt_error:
                        self.logger.warning(f"Alternative approach {get_tool} failed: {alt_error}")
        
        return {
            "tool_name": tool_name,
            "params": params,
            "success": False,
            "result": {"success": False, "error": "No alternative approach available"},
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "no_alternative"
        }
    
    async def _graceful_degradation(
        self,
        tool_name: str,
        params: Dict[str, Any],
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Provide graceful degradation with helpful error information."""
        
        # Create helpful error response based on error type and tool
        degraded_response = {
            "success": False,
            "error": str(error),
            "graceful_degradation": True,
            "suggested_actions": []
        }
        
        # Add context-specific suggestions
        if isinstance(error, NetBoxAuthError):
            degraded_response["suggested_actions"].extend([
                "Check NetBox authentication credentials",
                "Verify API token permissions",
                "Contact NetBox administrator"
            ])
        elif isinstance(error, NetBoxNotFoundError):
            degraded_response["suggested_actions"].extend([
                "Verify the requested resource exists",
                "Check spelling and formatting",
                "Use list tools to find available resources"
            ])
        elif isinstance(error, NetBoxValidationError):
            degraded_response["suggested_actions"].extend([
                "Check parameter values and types",
                "Verify required parameters are provided",
                "Review NetBox field requirements"
            ])
        else:
            degraded_response["suggested_actions"].extend([
                "Try again in a few moments",
                "Use alternative tools if available",
                "Contact system administrator if problem persists"
            ])
        
        # Add tool-specific help
        if "list" in tool_name:
            degraded_response["alternative_suggestion"] = "Try specific get tools instead of list tools"
        elif "create" in tool_name:
            degraded_response["alternative_suggestion"] = "Check if resource already exists, or use list tools first"
        
        return {
            "tool_name": tool_name,
            "params": params,
            "success": False,
            "result": degraded_response,
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "graceful_degradation",
            "execution_time": 0.0
        }
    
    async def _handle_circuit_open(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle execution when circuit breaker is open."""
        
        circuit = self.circuit_breakers[tool_name]
        
        return {
            "tool_name": tool_name,
            "params": params,
            "success": False,
            "result": {
                "success": False,
                "error": f"Circuit breaker is open for tool '{tool_name}'",
                "circuit_breaker_active": True,
                "failure_count": circuit.failure_count,
                "next_retry_time": (
                    circuit.last_failure_time + timedelta(seconds=circuit.recovery_timeout)
                ).isoformat() if circuit.last_failure_time else None
            },
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "circuit_breaker",
            "execution_time": 0.0
        }
    
    async def _handle_parameter_validation_error(
        self,
        tool_name: str,
        params: Dict[str, Any],
        validation_result: ValidationResult,
        execute_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle parameter validation errors with correction attempts."""
        
        # Try to execute with normalized parameters even if validation failed
        if validation_result.normalized_params != params:
            try:
                start_time = time.time()
                result = await execute_func(tool_name, validation_result.normalized_params)
                execution_time = time.time() - start_time
                
                return {
                    "tool_name": tool_name,
                    "params": validation_result.normalized_params,
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "recovery_used": True,
                    "recovery_strategy": "parameter_normalization",
                    "parameter_corrections": validation_result.auto_corrections,
                    "validation_warnings": validation_result.suggestions
                }
            except Exception as e:
                self.logger.warning(f"Parameter normalization didn't resolve the issue: {e}")
        
        # Return validation error with suggestions
        return {
            "tool_name": tool_name,
            "params": params,
            "success": False,
            "error": "Parameter validation failed",
            "result": {
                "success": False,
                "error": "Parameter validation failed",
                "validation_errors": {
                    "missing_required": validation_result.missing_required,
                    "invalid_params": validation_result.invalid_params,
                    "suggestions": validation_result.suggestions
                }
            },
            "timestamp": datetime.now().isoformat(),
            "recovery_used": True,
            "recovery_strategy": "parameter_validation_failed",
            "execution_time": 0.0
        }
    
    def _is_circuit_open(self, tool_name: str) -> bool:
        """Check if circuit breaker is open for a tool."""
        if tool_name not in self.circuit_breakers:
            return False
        
        circuit = self.circuit_breakers[tool_name]
        
        if circuit.state == "closed":
            return False
        elif circuit.state == "open":
            # Check if recovery timeout has passed
            if circuit.last_failure_time:
                time_since_failure = datetime.now() - circuit.last_failure_time
                if time_since_failure.total_seconds() >= circuit.recovery_timeout:
                    # Move to half-open state
                    circuit.state = "half_open"
                    self.logger.info(f"Circuit breaker for {tool_name} moved to half-open state")
                    return False
            return True
        elif circuit.state == "half_open":
            return False
        
        return False
    
    def _record_success(self, tool_name: str):
        """Record successful execution for circuit breaker."""
        if tool_name not in self.circuit_breakers:
            return
        
        circuit = self.circuit_breakers[tool_name]
        
        if circuit.state == "half_open":
            circuit.failure_count = max(0, circuit.failure_count - 1)
            if circuit.failure_count == 0:
                circuit.state = "closed"
                self.logger.info(f"Circuit breaker for {tool_name} closed after successful recovery")
        elif circuit.state == "closed":
            circuit.failure_count = max(0, circuit.failure_count - 1)
    
    def _record_failure(self, tool_name: str):
        """Record failed execution for circuit breaker."""
        if tool_name not in self.circuit_breakers:
            self.circuit_breakers[tool_name] = CircuitBreakerState(tool_name=tool_name)
        
        circuit = self.circuit_breakers[tool_name]
        circuit.failure_count += 1
        circuit.last_failure_time = datetime.now()
        
        # Open circuit if threshold exceeded
        if circuit.failure_count >= circuit.failure_threshold and circuit.state != "open":
            circuit.state = "open"
            self.recovery_stats["circuit_breaks"] += 1
            self.logger.warning(f"Circuit breaker opened for {tool_name} after {circuit.failure_count} failures")
        
        # Keep error history
        self.error_history[tool_name].append(datetime.now())
        # Keep only recent errors (last hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.error_history[tool_name] = [
            t for t in self.error_history[tool_name] if t > cutoff_time
        ]
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        return {
            "recovery_stats": self.recovery_stats.copy(),
            "circuit_breaker_status": {
                tool: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for tool, cb in self.circuit_breakers.items()
            },
            "error_history": {
                tool: len(errors) for tool, errors in self.error_history.items()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_circuit_breaker(self, tool_name: str):
        """Manually reset a circuit breaker."""
        if tool_name in self.circuit_breakers:
            circuit = self.circuit_breakers[tool_name]
            circuit.state = "closed"
            circuit.failure_count = 0
            circuit.last_failure_time = None
            self.logger.info(f"Circuit breaker for {tool_name} manually reset")


# Global error recovery engine instance
error_recovery_engine = ErrorRecoveryEngine()


async def execute_with_recovery(
    tool_name: str,
    params: Dict[str, Any],
    execute_func: callable,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Public interface for executing tools with error recovery.
    
    Args:
        tool_name: Name of the tool to execute
        params: Tool parameters
        execute_func: Function to execute the tool
        context: Optional execution context
        
    Returns:
        Execution result with recovery information
    """
    return await error_recovery_engine.execute_with_recovery(
        tool_name, params, execute_func, context
    )


async def execute_batch_with_recovery(
    tools: List[Dict[str, Any]],
    execute_func: callable,
    context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Public interface for executing multiple tools with recovery.
    
    Args:
        tools: List of tool specifications
        execute_func: Function to execute tools
        context: Optional execution context
        
    Returns:
        List of execution results with recovery information
    """
    return await error_recovery_engine.execute_with_fallbacks(
        tools, execute_func, context
    )


def get_recovery_statistics() -> Dict[str, Any]:
    """Get current recovery system statistics."""
    return error_recovery_engine.get_recovery_stats()


def reset_circuit_breaker(tool_name: str):
    """Reset circuit breaker for a specific tool."""
    error_recovery_engine.reset_circuit_breaker(tool_name)