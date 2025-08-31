"""
Backward Compatibility System for NetBox MCP Phase 5

This module provides seamless backward compatibility during the migration from 
the original NetBox MCP App CLI to the new Phase 1-4 intelligent system.

Key Features:
1. Feature flag system for gradual migration
2. Compatibility bridge for existing interfaces  
3. A/B testing capability for validation
4. Graceful fallback to legacy system when needed
5. Migration tracking and reporting

Enables zero-downtime migration with rollback capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import os


class MigrationPhase(Enum):
    """Migration phases for gradual rollout"""
    LEGACY_ONLY = "legacy_only"
    MIXED_MODE = "mixed_mode"
    INTELLIGENT_PREFERRED = "intelligent_preferred"
    INTELLIGENT_ONLY = "intelligent_only"


class FeatureFlag(Enum):
    """Feature flags for controlling migration"""
    USE_INTELLIGENT_TOOL_SELECTOR = "use_intelligent_tool_selector"
    USE_CONTEXT_AWARE_PARAMETERS = "use_context_aware_parameters"
    USE_LANGGRAPH_WORKFLOW = "use_langgraph_workflow"
    USE_INTELLIGENT_FALLBACK = "use_intelligent_fallback"
    ENABLE_A_B_TESTING = "enable_a_b_testing"
    ENABLE_PERFORMANCE_MONITORING = "enable_performance_monitoring"


@dataclass
class CompatibilityConfig:
    """Configuration for backward compatibility system"""
    migration_phase: MigrationPhase = MigrationPhase.MIXED_MODE
    feature_flags: Dict[str, bool] = None
    a_b_testing_percentage: float = 50.0  # % of requests using intelligent system
    fallback_timeout_seconds: float = 5.0
    enable_migration_tracking: bool = True
    legacy_tool_mapper_path: Optional[str] = None
    
    def __post_init__(self):
        if self.feature_flags is None:
            # Default feature flags for mixed mode
            self.feature_flags = {
                FeatureFlag.USE_INTELLIGENT_TOOL_SELECTOR.value: True,
                FeatureFlag.USE_CONTEXT_AWARE_PARAMETERS.value: True,
                FeatureFlag.USE_LANGGRAPH_WORKFLOW.value: True,
                FeatureFlag.USE_INTELLIGENT_FALLBACK.value: True,
                FeatureFlag.ENABLE_A_B_TESTING.value: True,
                FeatureFlag.ENABLE_PERFORMANCE_MONITORING.value: True,
            }


@dataclass
class RequestTrackingInfo:
    """Tracking information for migration analysis"""
    request_id: str
    query: str
    system_used: str  # "legacy" or "intelligent"
    success: bool
    response_time: float
    error_message: Optional[str]
    timestamp: datetime
    session_id: str
    user_agent: Optional[str] = None
    

class BackwardCompatibilityManager:
    """
    Manages backward compatibility and migration between legacy and intelligent systems
    """
    
    def __init__(self, config: Optional[CompatibilityConfig] = None):
        self.config = config or CompatibilityConfig()
        self.logger = logging.getLogger(__name__)
        self.tracking_data: List[RequestTrackingInfo] = []
        
        # Initialize legacy system if available
        self._legacy_system = None
        self._intelligent_system = None
        
        self.logger.info(f"Backward compatibility initialized - Phase: {self.config.migration_phase.value}")
    
    async def initialize(self):
        """Initialize both legacy and intelligent systems"""
        try:
            # Initialize intelligent system components
            await self._initialize_intelligent_system()
            
            # Initialize legacy system if needed
            if self._should_support_legacy():
                await self._initialize_legacy_system()
                
            self.logger.info("Backward compatibility system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize compatibility system: {e}")
            raise
    
    async def process_query(
        self,
        query: str,
        session_id: str,
        correlation_id: Optional[str] = None,
        force_system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process query with backward compatibility support
        
        Args:
            query: User's natural language query
            session_id: Session identifier
            correlation_id: Optional correlation ID
            force_system: Force use of "legacy" or "intelligent" system (for testing)
            
        Returns:
            Query result with migration metadata
        """
        request_id = f"compat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(query)}"
        start_time = datetime.now()
        
        try:
            # Determine which system to use
            system_to_use = self._determine_system(query, session_id, force_system)
            
            self.logger.info(f"Processing query with {system_to_use} system: {query[:100]}...")
            
            # Process with selected system
            if system_to_use == "intelligent":
                result = await self._process_with_intelligent_system(
                    query, session_id, correlation_id
                )
            else:
                result = await self._process_with_legacy_system(
                    query, session_id, correlation_id
                )
            
            # Add compatibility metadata
            result["compatibility_metadata"] = {
                "system_used": system_to_use,
                "migration_phase": self.config.migration_phase.value,
                "request_id": request_id,
                "fallback_available": system_to_use == "intelligent" and self._should_support_legacy(),
                "feature_flags_used": self._get_active_feature_flags()
            }
            
            # Track request for migration analysis
            if self.config.enable_migration_tracking:
                await self._track_request(
                    request_id, query, system_to_use, 
                    result.get("success", False),
                    (datetime.now() - start_time).total_seconds(),
                    result.get("error"),
                    session_id
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            
            # Try fallback system if primary failed
            fallback_result = await self._handle_system_failure(
                query, session_id, correlation_id, system_to_use, str(e)
            )
            
            # Track failed request
            if self.config.enable_migration_tracking:
                await self._track_request(
                    request_id, query, "fallback",
                    fallback_result.get("success", False),
                    (datetime.now() - start_time).total_seconds(),
                    str(e), session_id
                )
            
            return fallback_result
    
    def _determine_system(self, query: str, session_id: str, force_system: Optional[str]) -> str:
        """Determine which system to use for processing"""
        
        # Force system if specified (for testing)
        if force_system in ["legacy", "intelligent"]:
            return force_system
        
        # Check migration phase
        if self.config.migration_phase == MigrationPhase.LEGACY_ONLY:
            return "legacy"
        elif self.config.migration_phase == MigrationPhase.INTELLIGENT_ONLY:
            return "intelligent"
        
        # For mixed modes, use feature flags and A/B testing
        if self.config.feature_flags.get(FeatureFlag.ENABLE_A_B_TESTING.value, False):
            # Use session-based hash for consistent A/B assignment
            session_hash = hash(session_id) % 100
            
            if session_hash < self.config.a_b_testing_percentage:
                return "intelligent"
            else:
                return "legacy"
        
        # Default to intelligent if all flags enabled
        if all(self.config.feature_flags.get(flag.value, False) 
               for flag in [FeatureFlag.USE_INTELLIGENT_TOOL_SELECTOR, 
                           FeatureFlag.USE_LANGGRAPH_WORKFLOW]):
            return "intelligent"
        
        return "legacy"
    
    async def _process_with_intelligent_system(
        self,
        query: str,
        session_id: str, 
        correlation_id: Optional[str]
    ) -> Dict[str, Any]:
        """Process query with the intelligent system (Phases 1-4)"""
        
        try:
            # Import NEW adaptive intelligence system with recovery capabilities
            from .adaptive_state_machine import execute_adaptive_workflow
            
            result = await execute_adaptive_workflow(
                user_query=query,
                session_id=session_id,
                correlation_id=correlation_id
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Intelligent system processing failed: {e}")
            raise
    
    async def _process_with_legacy_system(
        self,
        query: str,
        session_id: str,
        correlation_id: Optional[str]
    ) -> Dict[str, Any]:
        """Process query with the legacy system"""
        
        try:
            # Simulate legacy system processing
            # In real implementation, this would call the original tool_mapper.py
            self.logger.warning("Legacy system processing - not fully implemented in this demo")
            
            return {
                "success": True,
                "response": f"Legacy system processed query: {query}",
                "system_used": "legacy",
                "workflow_complete": True,
                "tool_results": [],
                "execution_metrics": {
                    "system": "legacy",
                    "processing_time": 1.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Legacy system processing failed: {e}")
            raise
    
    async def _handle_system_failure(
        self,
        query: str,
        session_id: str,
        correlation_id: Optional[str],
        failed_system: str,
        error: str
    ) -> Dict[str, Any]:
        """Handle system failure with fallback"""
        
        self.logger.warning(f"{failed_system.title()} system failed: {error}")
        
        # Try fallback system if available
        fallback_system = "legacy" if failed_system == "intelligent" else "intelligent"
        
        if ((fallback_system == "legacy" and self._should_support_legacy()) or
            (fallback_system == "intelligent" and self._intelligent_system)):
            
            try:
                self.logger.info(f"Attempting fallback to {fallback_system} system...")
                
                if fallback_system == "intelligent":
                    result = await self._process_with_intelligent_system(
                        query, session_id, correlation_id
                    )
                else:
                    result = await self._process_with_legacy_system(
                        query, session_id, correlation_id
                    )
                
                # Mark as fallback result
                result["compatibility_metadata"] = result.get("compatibility_metadata", {})
                result["compatibility_metadata"]["fallback_used"] = True
                result["compatibility_metadata"]["original_system_failed"] = failed_system
                result["compatibility_metadata"]["fallback_system"] = fallback_system
                
                self.logger.info(f"Fallback to {fallback_system} system succeeded")
                return result
                
            except Exception as fallback_error:
                self.logger.error(f"Fallback to {fallback_system} also failed: {fallback_error}")
        
        # Return error response if all systems fail
        return {
            "success": False,
            "response": f"I'm experiencing technical difficulties processing your query: {query}. Please try again later.",
            "error": f"Both systems failed - Primary: {error}",
            "workflow_complete": True,
            "compatibility_metadata": {
                "system_used": "error_fallback",
                "primary_failure": failed_system,
                "all_systems_failed": True
            }
        }
    
    async def _initialize_intelligent_system(self):
        """Initialize intelligent system components"""
        try:
            # Test imports and initialization
            from .intelligent_tool_selector import IntelligentToolSelector
            from .tool_aware_parameter_extractor import ToolAwareParameterExtractor
            from .state_machine import create_intelligent_orchestration_graph
            
            # Initialize components
            selector = IntelligentToolSelector()
            extractor = ToolAwareParameterExtractor()
            graph = create_intelligent_orchestration_graph()
            
            self._intelligent_system = {
                "selector": selector,
                "extractor": extractor,
                "graph": graph
            }
            
            self.logger.info("Intelligent system components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize intelligent system: {e}")
            raise
    
    async def _initialize_legacy_system(self):
        """Initialize legacy system if needed"""
        try:
            # In real implementation, would initialize original tool_mapper.py
            # For now, just mark as available
            self._legacy_system = {"available": True}
            self.logger.info("Legacy system initialized (simulated)")
            
        except Exception as e:
            self.logger.warning(f"Legacy system initialization failed: {e}")
            # Don't raise - legacy system is optional
    
    def _should_support_legacy(self) -> bool:
        """Check if legacy system support is needed"""
        return self.config.migration_phase in [
            MigrationPhase.MIXED_MODE,
            MigrationPhase.INTELLIGENT_PREFERRED
        ]
    
    def _get_active_feature_flags(self) -> Dict[str, bool]:
        """Get currently active feature flags"""
        return {
            flag: enabled for flag, enabled in self.config.feature_flags.items()
            if enabled
        }
    
    async def _track_request(
        self,
        request_id: str,
        query: str,
        system_used: str,
        success: bool,
        response_time: float,
        error: Optional[str],
        session_id: str
    ):
        """Track request for migration analysis"""
        
        tracking_info = RequestTrackingInfo(
            request_id=request_id,
            query=query,
            system_used=system_used,
            success=success,
            response_time=response_time,
            error_message=error,
            timestamp=datetime.now(),
            session_id=session_id
        )
        
        self.tracking_data.append(tracking_info)
        
        # Persist tracking data periodically
        if len(self.tracking_data) >= 100:
            await self._persist_tracking_data()
    
    async def _persist_tracking_data(self):
        """Persist tracking data for analysis"""
        try:
            tracking_file = f"migration_tracking_{datetime.now().strftime('%Y%m%d')}.json"
            
            # Convert to serializable format
            data = [asdict(info) for info in self.tracking_data]
            
            # Write to file
            with open(tracking_file, 'a') as f:
                for entry in data:
                    entry['timestamp'] = entry['timestamp'].isoformat()
                    f.write(json.dumps(entry) + '\n')
            
            self.logger.info(f"Persisted {len(self.tracking_data)} tracking entries to {tracking_file}")
            self.tracking_data.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to persist tracking data: {e}")
    
    async def generate_migration_report(self) -> Dict[str, Any]:
        """Generate migration analysis report"""
        
        if not self.tracking_data:
            return {"error": "No tracking data available"}
        
        # Analyze tracking data
        total_requests = len(self.tracking_data)
        intelligent_requests = sum(1 for t in self.tracking_data if t.system_used == "intelligent")
        legacy_requests = sum(1 for t in self.tracking_data if t.system_used == "legacy")
        
        intelligent_success = sum(1 for t in self.tracking_data 
                                 if t.system_used == "intelligent" and t.success)
        legacy_success = sum(1 for t in self.tracking_data 
                            if t.system_used == "legacy" and t.success)
        
        intelligent_avg_time = (
            sum(t.response_time for t in self.tracking_data if t.system_used == "intelligent") /
            max(intelligent_requests, 1)
        )
        legacy_avg_time = (
            sum(t.response_time for t in self.tracking_data if t.system_used == "legacy") /
            max(legacy_requests, 1)
        )
        
        return {
            "migration_analysis": {
                "total_requests": total_requests,
                "intelligent_system": {
                    "requests": intelligent_requests,
                    "success_rate": (intelligent_success / max(intelligent_requests, 1)) * 100,
                    "avg_response_time": intelligent_avg_time
                },
                "legacy_system": {
                    "requests": legacy_requests,
                    "success_rate": (legacy_success / max(legacy_requests, 1)) * 100,
                    "avg_response_time": legacy_avg_time
                },
                "recommendation": self._generate_migration_recommendation(
                    intelligent_requests, legacy_requests,
                    intelligent_success, legacy_success,
                    intelligent_avg_time, legacy_avg_time
                )
            },
            "current_config": {
                "migration_phase": self.config.migration_phase.value,
                "feature_flags": self.config.feature_flags,
                "a_b_testing_percentage": self.config.a_b_testing_percentage
            },
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_migration_recommendation(
        self, intel_requests, legacy_requests, intel_success, legacy_success,
        intel_time, legacy_time
    ) -> str:
        """Generate migration recommendation based on analysis"""
        
        intel_success_rate = (intel_success / max(intel_requests, 1)) * 100
        legacy_success_rate = (legacy_success / max(legacy_requests, 1)) * 100
        
        if intel_success_rate > legacy_success_rate + 5 and intel_time < legacy_time + 1.0:
            return "RECOMMEND_INTELLIGENT: Intelligent system shows better performance"
        elif intel_success_rate < legacy_success_rate - 5:
            return "RECOMMEND_LEGACY: Legacy system more reliable, need intelligent system fixes"
        else:
            return "CONTINUE_A_B_TESTING: Performance similar, continue gradual migration"
    
    async def update_migration_phase(self, new_phase: MigrationPhase):
        """Update migration phase"""
        old_phase = self.config.migration_phase
        self.config.migration_phase = new_phase
        
        self.logger.info(f"Migration phase updated: {old_phase.value} -> {new_phase.value}")
        
        # Re-initialize if needed
        if new_phase == MigrationPhase.INTELLIGENT_ONLY and not self._intelligent_system:
            await self._initialize_intelligent_system()
        elif new_phase in [MigrationPhase.MIXED_MODE, MigrationPhase.INTELLIGENT_PREFERRED]:
            if not self._legacy_system:
                await self._initialize_legacy_system()
    
    def update_feature_flag(self, flag: FeatureFlag, enabled: bool):
        """Update individual feature flag"""
        old_value = self.config.feature_flags.get(flag.value, False)
        self.config.feature_flags[flag.value] = enabled
        
        self.logger.info(f"Feature flag updated: {flag.value}: {old_value} -> {enabled}")


# Factory function for easy initialization
async def create_backward_compatibility_manager(
    migration_phase: MigrationPhase = MigrationPhase.MIXED_MODE,
    a_b_testing_percentage: float = 50.0
) -> BackwardCompatibilityManager:
    """
    Create and initialize backward compatibility manager
    
    Args:
        migration_phase: Current migration phase
        a_b_testing_percentage: Percentage of requests using intelligent system
        
    Returns:
        Initialized backward compatibility manager
    """
    
    config = CompatibilityConfig(
        migration_phase=migration_phase,
        a_b_testing_percentage=a_b_testing_percentage
    )
    
    manager = BackwardCompatibilityManager(config)
    await manager.initialize()
    
    return manager


# CLI Integration wrapper for backward compatibility
class CompatibleCLIProcessor:
    """
    CLI processor that provides backward compatibility with existing interfaces
    """
    
    def __init__(self, compatibility_manager: BackwardCompatibilityManager):
        self.compatibility_manager = compatibility_manager
        self.logger = logging.getLogger(__name__)
    
    async def process_cli_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process CLI request with backward compatibility
        
        Maintains compatibility with existing CLI interface while using new system
        """
        try:
            # Extract query and session info from request
            query = request.get("query", request.get("user_input", ""))
            session_id = request.get("session_id", f"cli_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            correlation_id = request.get("correlation_id")
            force_system = request.get("force_system")  # For testing
            
            # Process with compatibility layer
            result = await self.compatibility_manager.process_query(
                query=query,
                session_id=session_id,
                correlation_id=correlation_id,
                force_system=force_system
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"CLI processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I encountered an error processing your request. Please try again.",
                "compatibility_metadata": {
                    "system_used": "error_handler",
                    "error_type": "cli_processing_error"
                }
            }