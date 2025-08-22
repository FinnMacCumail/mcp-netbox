"""
Known Limitation Handling for NetBox MCP Tool Coordination

This module implements graceful handling of the 35+ documented NetBox MCP
tool limitations through progressive disclosure, intelligent sampling,
and user-friendly fallback strategies.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .coordination import ToolRequest, ToolResult


class LimitationType(Enum):
    """Categories of NetBox MCP tool limitations"""
    TOKEN_OVERFLOW = "token_overflow"
    N_PLUS_ONE_QUERIES = "n_plus_one_queries"
    API_RATE_LIMITS = "api_rate_limits"
    LARGE_RESULT_SET = "large_result_set"
    RELATIONSHIP_COMPLEXITY = "relationship_complexity"
    PAGINATION_ISSUES = "pagination_issues"
    TIMEOUT_PRONE = "timeout_prone"


@dataclass
class LimitationContext:
    """Context information for limitation handling"""
    limitation_type: LimitationType
    affected_tools: List[str]
    estimated_impact: str
    user_query: str
    entities: Dict[str, List[str]]
    original_plan: Dict[str, Any]


class LimitationHandler:
    """
    Sophisticated limitation handling with progressive disclosure and
    intelligent fallback strategies for NetBox MCP tool constraints
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Known limitation patterns for NetBox MCP tools
        self.limitation_patterns = {
            # Token overflow limitations
            LimitationType.TOKEN_OVERFLOW: {
                "tools": [
                    "netbox_list_all_devices",
                    "netbox_list_all_vlans",
                    "netbox_list_all_cables",
                    "netbox_list_all_ip_addresses"
                ],
                "threshold_params": {
                    "netbox_list_all_devices": {"limit": 50},
                    "netbox_list_all_vlans": {"limit": 100},
                    "netbox_list_all_cables": {"limit": 30},
                    "netbox_list_all_ip_addresses": {"limit": 200}
                }
            },
            
            # N+1 query issues
            LimitationType.N_PLUS_ONE_QUERIES: {
                "tools": [
                    "netbox_get_device_interfaces",
                    "netbox_get_device_cables", 
                    "netbox_list_device_modules",
                    "netbox_list_device_inventory"
                ],
                "batch_limits": {
                    "netbox_get_device_interfaces": 10,
                    "netbox_get_device_cables": 5,
                    "netbox_list_device_modules": 15,
                    "netbox_list_device_inventory": 8
                }
            },
            
            # Large result set handling
            LimitationType.LARGE_RESULT_SET: {
                "tools": [
                    "netbox_list_all_prefixes",
                    "netbox_list_all_journal_entries", 
                    "netbox_list_all_power_cables"
                ],
                "progressive_limits": {
                    "initial_batch": 25,
                    "subsequent_batch": 50,
                    "max_total": 500
                }
            }
        }
    
    async def detect_limitations(self, tool_requests: List[ToolRequest], query_context: Dict[str, Any]) -> List[LimitationContext]:
        """Detect potential limitations in planned tool execution"""
        limitations = []
        
        for request in tool_requests:
            detected_limitations = await self._analyze_tool_limitations(request, query_context)
            limitations.extend(detected_limitations)
        
        self.logger.info(f"Detected {len(limitations)} potential limitations")
        return limitations
    
    async def handle_limitation(self, limitation_context: LimitationContext) -> Dict[str, Any]:
        """Handle specific limitation with appropriate strategy"""
        limitation_type = limitation_context.limitation_type
        
        if limitation_type == LimitationType.TOKEN_OVERFLOW:
            return await self._handle_token_overflow(limitation_context)
        elif limitation_type == LimitationType.N_PLUS_ONE_QUERIES:
            return await self._handle_n_plus_one_queries(limitation_context)
        elif limitation_type == LimitationType.LARGE_RESULT_SET:
            return await self._handle_large_result_set(limitation_context)
        else:
            return await self._handle_general_limitation(limitation_context)
    
    async def _handle_token_overflow(self, context: LimitationContext) -> Dict[str, Any]:
        """Handle token overflow with progressive disclosure"""
        self.logger.info("Implementing progressive disclosure for token overflow")
        
        # Get appropriate limit for the tool
        tool_limits = self.limitation_patterns[LimitationType.TOKEN_OVERFLOW]["threshold_params"]
        primary_tool = context.affected_tools[0]
        limit = tool_limits.get(primary_tool, {"limit": 50})["limit"]
        
        return {
            "strategy": "progressive_disclosure",
            "approach": "batched_retrieval",
            "initial_limit": limit,
            "total_estimated": "500+",
            "user_guidance": f"""
I've detected this query might return a large dataset that could cause token overflow.

**Progressive Disclosure Strategy**:
- Showing first {limit} results initially
- You can request additional batches as needed
- Apply filters to reduce scope if desired

**Your Options**:
1. **Show Results**: Display first {limit} entries
2. **Apply Filters**: Narrow down the search scope  
3. **Summary View**: Get high-level statistics instead

Which approach would you prefer?
            """.strip(),
            "user_options": [
                f"Show first {limit} results",
                "Apply additional filters", 
                "Switch to summary view",
                "Explain limitation details"
            ]
        }
    
    async def _handle_n_plus_one_queries(self, context: LimitationContext) -> Dict[str, Any]:
        """Handle N+1 queries with intelligent sampling"""
        self.logger.info("Implementing intelligent sampling for N+1 query limitation")
        
        # Get batch limit for the tool
        batch_limits = self.limitation_patterns[LimitationType.N_PLUS_ONE_QUERIES]["batch_limits"]
        primary_tool = context.affected_tools[0]
        batch_limit = batch_limits.get(primary_tool, 10)
        
        return {
            "strategy": "intelligent_sampling",
            "approach": "representative_sampling",
            "sample_size": batch_limit,
            "total_entities": "100+",
            "user_guidance": f"""
This query involves examining many related entities, which could trigger excessive API calls.

**Intelligent Sampling Strategy**:
- Processing representative sample of {batch_limit} entities
- Providing insights based on sample analysis
- Option to process additional entities as needed

**Your Options**:
1. **View Sample**: See analysis of {batch_limit} representative entities
2. **Process More**: Examine additional entity batches
3. **Full Analysis**: Process all entities (may take longer)
4. **Filter Entities**: Specify which entities to focus on

Which approach would you like?
            """.strip(),
            "user_options": [
                f"Analyze sample of {batch_limit} entities",
                "Process next batch of entities",
                "Specify entities to focus on",
                "Full analysis (may be slow)"
            ]
        }
    
    async def _handle_large_result_set(self, context: LimitationContext) -> Dict[str, Any]:
        """Handle large result sets with progressive loading"""
        self.logger.info("Implementing progressive loading for large result set")
        
        progressive_config = self.limitation_patterns[LimitationType.LARGE_RESULT_SET]["progressive_limits"]
        
        return {
            "strategy": "progressive_loading",
            "approach": "chunked_retrieval",
            "initial_batch": progressive_config["initial_batch"],
            "user_guidance": f"""
This query could return a very large dataset. I'll use progressive loading to manage the results.

**Progressive Loading Strategy**:
- Starting with {progressive_config['initial_batch']} most relevant results
- Additional results available on request
- Summary statistics provided upfront

**Your Options**:
1. **View Initial Results**: See first {progressive_config['initial_batch']} entries
2. **Load More**: Get additional batches of results
3. **Summary Only**: Just show statistics and counts
4. **Apply Filters**: Reduce the result scope

What would be most helpful?
            """.strip(),
            "user_options": [
                f"Show first {progressive_config['initial_batch']} results",
                "Load next batch",
                "Show summary statistics only",
                "Apply filters to reduce scope"
            ]
        }
    
    async def _handle_general_limitation(self, context: LimitationContext) -> Dict[str, Any]:
        """Handle general or unspecified limitations"""
        self.logger.info("Implementing general limitation fallback")
        
        return {
            "strategy": "graceful_fallback",
            "approach": "alternative_methods",
            "user_guidance": f"""
I've identified some limitations with the requested NetBox operation.

**Alternative Approaches Available**:
- Simplified query with reduced scope
- Alternative NetBox tools for similar information
- Manual guidance for specific entity names

**Your Options**:
1. **Simplify Query**: Use a more focused search approach
2. **Try Alternative**: Use different NetBox tools for similar data
3. **Get Guidance**: Learn how to structure the query differently
4. **Manual Input**: Provide specific NetBox entity names

Which approach would you prefer?
            """.strip(),
            "user_options": [
                "Simplify the query scope",
                "Try alternative tools",
                "Get query guidance", 
                "Provide specific entity names"
            ]
        }
    
    async def _analyze_tool_limitations(self, tool_request: ToolRequest, query_context: Dict[str, Any]) -> List[LimitationContext]:
        """Analyze individual tool request for potential limitations"""
        limitations = []
        
        # Check for token overflow risk
        if tool_request.tool_name in self.limitation_patterns[LimitationType.TOKEN_OVERFLOW]["tools"]:
            if not tool_request.params.get("limit") or tool_request.params.get("limit", 0) > 100:
                limitations.append(LimitationContext(
                    limitation_type=LimitationType.TOKEN_OVERFLOW,
                    affected_tools=[tool_request.tool_name],
                    estimated_impact="high",
                    user_query=query_context.get("user_query", ""),
                    entities=query_context.get("entities", {}),
                    original_plan={}
                ))
        
        # Check for N+1 query risk
        if tool_request.tool_name in self.limitation_patterns[LimitationType.N_PLUS_ONE_QUERIES]["tools"]:
            entity_count = len(query_context.get("entities", {}).get("devices", []))
            if entity_count > 10:
                limitations.append(LimitationContext(
                    limitation_type=LimitationType.N_PLUS_ONE_QUERIES,
                    affected_tools=[tool_request.tool_name],
                    estimated_impact="medium",
                    user_query=query_context.get("user_query", ""),
                    entities=query_context.get("entities", {}),
                    original_plan={}
                ))
        
        # Check for large result set risk
        if tool_request.tool_name in self.limitation_patterns[LimitationType.LARGE_RESULT_SET]["tools"]:
            if not tool_request.params.get("limit"):
                limitations.append(LimitationContext(
                    limitation_type=LimitationType.LARGE_RESULT_SET,
                    affected_tools=[tool_request.tool_name],
                    estimated_impact="medium",
                    user_query=query_context.get("user_query", ""),
                    entities=query_context.get("entities", {}),
                    original_plan={}
                ))
        
        return limitations
    
    async def create_limitation_summary(self, limitations: List[LimitationContext]) -> Dict[str, Any]:
        """Create summary of detected limitations for user communication"""
        if not limitations:
            return {"has_limitations": False}
        
        limitation_summary = {
            "has_limitations": True,
            "total_limitations": len(limitations),
            "limitation_types": list(set(l.limitation_type.value for l in limitations)),
            "affected_tools": list(set(tool for l in limitations for tool in l.affected_tools)),
            "recommended_strategy": self._recommend_strategy(limitations),
            "user_message": self._generate_user_message(limitations)
        }
        
        return limitation_summary
    
    def _recommend_strategy(self, limitations: List[LimitationContext]) -> str:
        """Recommend overall strategy based on detected limitations"""
        limitation_types = [l.limitation_type for l in limitations]
        
        if LimitationType.TOKEN_OVERFLOW in limitation_types:
            return "progressive_disclosure"
        elif LimitationType.N_PLUS_ONE_QUERIES in limitation_types:
            return "intelligent_sampling"
        elif LimitationType.LARGE_RESULT_SET in limitation_types:
            return "progressive_loading"
        else:
            return "graceful_fallback"
    
    def _generate_user_message(self, limitations: List[LimitationContext]) -> str:
        """Generate user-friendly message explaining limitations"""
        limitation_types = list(set(l.limitation_type.value for l in limitations))
        
        if len(limitation_types) == 1:
            limitation_type = limitation_types[0]
            return f"""
I've detected that this query may encounter {limitation_type.replace('_', ' ')} limitations.

I'll use an optimized approach to get you the information you need while working
around these NetBox MCP tool constraints. You'll have full control over how
much detail to retrieve and can request additional information as needed.
            """.strip()
        else:
            return f"""
I've detected multiple potential limitations with this query:
- {', '.join(limitation_types)}

I'll coordinate the tools intelligently to work around these constraints and
provide you with the best possible results. You'll have options to adjust
the scope and detail level as we go.
            """.strip()


class ProgressiveDisclosureManager:
    """
    Manage progressive disclosure workflows for large dataset queries
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_sessions = {}
    
    async def create_progressive_session(self, 
                                       query: str, 
                                       tool_request: ToolRequest,
                                       estimated_total: int) -> Dict[str, Any]:
        """Create new progressive disclosure session"""
        session_id = f"progressive_{int(datetime.now().timestamp())}"
        
        # Determine optimal batch size based on tool and estimated total
        batch_size = self._calculate_optimal_batch_size(tool_request.tool_name, estimated_total)
        
        session = {
            "session_id": session_id,
            "query": query,
            "tool_request": tool_request,
            "estimated_total": estimated_total,
            "batch_size": batch_size,
            "current_offset": 0,
            "retrieved_count": 0,
            "batches_completed": 0,
            "created_at": datetime.now(),
            "results": []
        }
        
        self.active_sessions[session_id] = session
        
        self.logger.info(f"Created progressive session {session_id} with batch size {batch_size}")
        return session
    
    async def get_next_batch(self, session_id: str) -> Dict[str, Any]:
        """Retrieve next batch of results for progressive session"""
        if session_id not in self.active_sessions:
            return {"error": "Progressive session not found"}
        
        session = self.active_sessions[session_id]
        
        # Update tool request with current offset and limit
        batch_request = ToolRequest(
            tool_name=session["tool_request"].tool_name,
            params={
                **session["tool_request"].params,
                "limit": session["batch_size"],
                "offset": session["current_offset"]
            }
        )
        
        # Execute batch request (simulation for Week 5-8)
        batch_result = await self._execute_batch_request(batch_request)
        
        # Update session state
        session["current_offset"] += session["batch_size"]
        session["retrieved_count"] += len(batch_result.get("results", []))
        session["batches_completed"] += 1
        session["results"].append(batch_result)
        
        # Determine if more batches available
        has_more = session["retrieved_count"] < session["estimated_total"]
        
        return {
            "session_id": session_id,
            "batch_results": batch_result,
            "progress": {
                "retrieved": session["retrieved_count"],
                "total_estimated": session["estimated_total"],
                "completion_percentage": min(100, (session["retrieved_count"] / session["estimated_total"]) * 100),
                "batches_completed": session["batches_completed"]
            },
            "has_more_results": has_more,
            "user_options": [
                "Get next batch",
                "Apply filters",
                "View summary", 
                "Export current results"
            ] if has_more else [
                "View summary",
                "Export all results",
                "Start new query"
            ]
        }
    
    async def _execute_batch_request(self, batch_request: ToolRequest) -> Dict[str, Any]:
        """Execute batch request (simulation for Week 5-8)"""
        # Simulate batch execution
        await asyncio.sleep(0.4)
        
        batch_size = batch_request.params.get("limit", 25)
        offset = batch_request.params.get("offset", 0)
        
        return {
            "tool_name": batch_request.tool_name,
            "batch_info": {
                "limit": batch_size,
                "offset": offset,
                "returned_count": min(batch_size, 50)  # Simulate actual results
            },
            "results": [
                {
                    "id": offset + i,
                    "name": f"simulated_entity_{offset + i}",
                    "type": "simulation",
                    "status": "active"
                }
                for i in range(min(batch_size, 50))
            ],
            "execution_time": 0.4,
            "success": True
        }
    
    def _calculate_optimal_batch_size(self, tool_name: str, estimated_total: int) -> int:
        """Calculate optimal batch size based on tool characteristics and dataset size"""
        # Base batch sizes by tool type
        base_sizes = {
            "netbox_list_all_devices": 25,
            "netbox_list_all_vlans": 50,
            "netbox_list_all_cables": 20,
            "netbox_list_all_ip_addresses": 100,
            "default": 30
        }
        
        base_size = base_sizes.get(tool_name, base_sizes["default"])
        
        # Adjust based on estimated total
        if estimated_total < 100:
            return min(base_size, estimated_total)
        elif estimated_total < 500:
            return base_size
        else:
            return int(base_size * 1.5)  # Larger batches for very large datasets


class IntelligentSampler:
    """
    Intelligent sampling for relationship-heavy queries to prevent N+1 issues
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def create_sampling_strategy(self, 
                                     entities: List[str], 
                                     relationship_tool: str,
                                     query_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create intelligent sampling strategy for entity relationships"""
        
        total_entities = len(entities)
        
        # Determine sample size based on relationship complexity
        if relationship_tool in ["netbox_get_device_interfaces", "netbox_get_device_cables"]:
            sample_size = min(8, max(3, total_entities // 10))  # 10% sample, min 3, max 8
        else:
            sample_size = min(10, max(5, total_entities // 8))   # 12.5% sample, min 5, max 10
        
        # Select representative sample
        sample_entities = await self._select_representative_sample(entities, sample_size, query_context)
        
        return {
            "strategy": "intelligent_sampling",
            "total_entities": total_entities,
            "sample_size": sample_size,
            "sample_entities": sample_entities,
            "remaining_entities": [e for e in entities if e not in sample_entities],
            "sampling_method": "representative_diversity",
            "user_guidance": f"""
To avoid excessive API calls, I'll analyze a representative sample of {sample_size} entities
from the total {total_entities} available. This provides insights while respecting
NetBox API limits.

**Sampling Approach**:
- Representative selection across different entity types
- Focus on entities most likely to provide valuable insights
- Option to examine additional entities based on sample findings

**Your Options**:
1. **View Sample Analysis**: See detailed analysis of selected entities
2. **Examine Specific Entities**: Choose which entities to analyze
3. **Process All** (Slower): Analyze all {total_entities} entities
4. **Adjust Sample**: Change the sample size or selection criteria

Which approach would you prefer?
            """.strip(),
            "user_options": [
                f"Analyze {sample_size} representative entities",
                "Choose specific entities to analyze",
                f"Process all {total_entities} entities",
                "Adjust sampling criteria"
            ]
        }
    
    async def _select_representative_sample(self, entities: List[str], sample_size: int, context: Dict[str, Any]) -> List[str]:
        """Select representative sample from entity list"""
        # For Week 5-8, use simple selection strategy
        # Future versions could use ML-based representativeness scoring
        
        if len(entities) <= sample_size:
            return entities
        
        # Distribute sample across the entity list for diversity
        step = len(entities) // sample_size
        selected = []
        
        for i in range(sample_size):
            index = i * step
            if index < len(entities):
                selected.append(entities[index])
        
        return selected