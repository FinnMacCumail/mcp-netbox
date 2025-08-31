"""
Enhanced NetBox MCP Orchestration with Intelligent Fallback System

This module implements Phase 1-4 integration:
- Phase 1: IntelligentToolSelector for semantic tool selection
- Phase 2: ToolAwareParameterExtractor for context-preserving parameters  
- Phase 3: Simplified 3-node LangGraph workflow
- Phase 4: Intelligent fallback orchestrator for Claude Code CLI-style resilience

The intelligent fallback system provides multi-level recovery strategies that
work at the correct abstraction level to achieve maximum resilience and helpfulness.
"""

# Import Phase 3 simplified orchestration components
from .state_machine import (
    IntelligentOrchestrationState, 
    create_intelligent_orchestration_graph,
    create_orchestration_graph,  # backward compatibility
    execute_intelligent_workflow
)

# Import Phase 7 Adaptive Intelligence System with recovery capabilities
from .adaptive_state_machine import (
    AdaptiveOrchestrationState,
    create_adaptive_orchestration_graph,
    execute_adaptive_workflow
)

# Import Phase 4 enhanced orchestration with intelligent fallback
from .enhanced_state_machine import (
    process_query_with_intelligent_fallback,
    EnhancedIntelligentOrchestrator
)

# Import Phase 4 intelligent fallback orchestrator
from .intelligent_fallback_orchestrator import (
    execute_with_intelligent_fallback,
    IntelligentFallbackOrchestrator,
    FallbackLevel,
    FallbackReason,
    FallbackResult,
    get_intelligent_fallback_statistics
)

# Import coordination components
from .coordination import ToolCoordinator, ToolRequest, ToolResult

# Import caching and limitation components (for backward compatibility)
from .cache import OrchestrationCache, CacheWarmer
from .limitations import LimitationHandler, ProgressiveDisclosureManager, IntelligentSampler

# Import Phase 1 & Phase 2 intelligent components
from .intelligent_tool_selector import select_tool, ToolSelection
from .tool_aware_parameter_extractor import extract_parameters, ParameterExtractionResult

__all__ = [
    # Phase 4: Enhanced orchestration with intelligent fallback
    "process_query_with_intelligent_fallback",
    "EnhancedIntelligentOrchestrator",
    "execute_with_intelligent_fallback",
    "IntelligentFallbackOrchestrator",
    "FallbackLevel",
    "FallbackReason", 
    "FallbackResult",
    "get_intelligent_fallback_statistics",
    
    # Phase 7: Adaptive Intelligence System with recovery capabilities  
    "AdaptiveOrchestrationState",
    "create_adaptive_orchestration_graph",
    "execute_adaptive_workflow",
    
    # Phase 3: Core intelligent orchestration (for backward compatibility)
    "IntelligentOrchestrationState",
    "create_intelligent_orchestration_graph", 
    "create_orchestration_graph",
    "execute_intelligent_workflow",
    
    # Phase 1 & Phase 2: Intelligent tool selection and parameter extraction
    "select_tool",
    "ToolSelection",
    "extract_parameters",
    "ParameterExtractionResult",
    
    # Tool coordination
    "ToolCoordinator",
    "ToolRequest", 
    "ToolResult",
    
    # Caching and limitation components (for backward compatibility)
    "OrchestrationCache",
    "CacheWarmer", 
    "LimitationHandler",
    "ProgressiveDisclosureManager",
    "IntelligentSampler"
]