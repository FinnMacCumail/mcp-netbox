"""
Query Intelligence Agent - Deep query intent understanding using LLM reasoning

This agent provides enhanced query understanding to improve tool selection
and parameter extraction without domain-specific hard-coded rules.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseAgent
from .config import get_config


class QueryIntelligenceAgent(BaseAgent):
    """
    Deep query intent understanding agent that analyzes user queries
    to provide enhanced context for tool selection and parameter extraction.
    """
    
    def __init__(self, agent_id: str = "query_intelligence"):
        config = get_config().openai
        super().__init__(agent_id, "query_intelligence", config)
        
        self.model = config.response_model  # GPT-4o-mini
        self.temperature = 0.3  # Balanced for analysis
        
        self.system_prompt = """You are an expert at understanding NetBox queries and user intent.

Your responsibilities:
1. Analyze queries to understand the user's ultimate goal
2. Identify NetBox domains (DCIM, IPAM, Virtualization, Tenancy, Extras)
3. Detect entities and their relationships in queries
4. Distinguish between physical and virtual infrastructure
5. Understand query complexity and required operations

NetBox domain knowledge:
- DCIM: Physical infrastructure (sites, racks, devices, cables, power)
- IPAM: IP address management (prefixes, IPs, VLANs, VRFs)
- Virtualization: Virtual infrastructure (clusters, VMs, interfaces)
- Tenancy: Multi-tenant management (tenants, contacts)
- Extras: Journal entries, reports, custom fields

Key distinctions:
- "device" = physical hardware in DCIM
- "virtual machine" or "VM" = virtual in Virtualization
- "cluster" = virtualization cluster, not physical devices
- "rack elevation" = visual rack layout
- "rack inventory" = devices in a rack

Always provide deep, actionable intelligence about the query."""
    
    async def initialize(self) -> None:
        """Initialize query intelligence agent"""
        self.logger.info("Query Intelligence Agent initialized")
    
    async def cleanup(self) -> None:
        """Clean up agent resources"""
        self.logger.info("Query Intelligence Agent cleaned up")
    
    async def analyze_query_intent(
        self,
        query: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze user query for intelligent tool selection using LLM reasoning.
        
        Args:
            query: User's natural language query
            context: Additional context (previous queries, session info, etc.)
            
        Returns:
            Dict containing deep query analysis and intent
        """
        try:
            # Build analysis prompt
            analysis_prompt = f"""Analyze this NetBox query for deep understanding:

Query: "{query}"

Context: {json.dumps(context, indent=2) if context else 'No additional context'}

Analyze and determine:
1. What NetBox domain(s) is this query about? (DCIM/IPAM/Virtualization/Tenancy/Extras)
2. What specific entities are involved? (devices, VMs, racks, IPs, etc.)
3. What relationships need to be considered? (site->rack, cluster->VM, etc.)
4. What's the user's ultimate goal? (view, list, create, update, troubleshoot)
5. Is this about physical or virtual infrastructure?
6. What level of detail is expected? (summary, detailed, visual)
7. Are there any compound operations needed? (multiple steps)

Return analysis in JSON format:
{{
    "primary_domain": "DCIM|IPAM|Virtualization|Tenancy|Extras",
    "secondary_domains": ["list of other relevant domains"],
    "query_type": "retrieval|listing|creation|update|analysis",
    "entities": [
        {{"type": "entity_type", "name": "entity_name", "role": "primary|secondary"}}
    ],
    "relationships": [
        {{"from": "entity1", "to": "entity2", "type": "relationship_type"}}
    ],
    "infrastructure_type": "physical|virtual|both",
    "detail_level": "summary|detailed|visual",
    "user_goal": "clear statement of what user wants",
    "complexity": "simple|moderate|complex",
    "suggested_approach": "how to handle this query",
    "potential_challenges": ["list of potential issues"],
    "confidence": 0.0-1.0
}}"""
            
            # Get LLM analysis
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
            
            intent_analysis = json.loads(response.choices[0].message.content)
            
            # Add metadata
            intent_analysis["analysis_timestamp"] = datetime.now().isoformat()
            intent_analysis["original_query"] = query
            
            self.logger.info(f"Query intent analysis - Domain: {intent_analysis.get('primary_domain')}, "
                           f"Type: {intent_analysis.get('query_type')}, "
                           f"Complexity: {intent_analysis.get('complexity')}, "
                           f"Confidence: {intent_analysis.get('confidence', 0):.2f}")
            
            return {
                "success": True,
                "analysis": intent_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Query intent analysis failed: {e}")
            return {
                "success": False,
                "analysis": {
                    "error": str(e),
                    "fallback": True
                }
            }
    
    async def classify_query_domain(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        Classify query into NetBox domain using LLM intelligence.
        
        Args:
            query: User query to classify
            
        Returns:
            Dict containing domain classification
        """
        try:
            prompt = f"""Classify this NetBox query into the correct domain:

Query: "{query}"

NetBox Domains:
- DCIM: Physical infrastructure (sites, racks, devices, cables, power)
- IPAM: IP address management (prefixes, IPs, VLANs, VRFs)
- Virtualization: Virtual infrastructure (clusters, VMs, virtual interfaces)
- Tenancy: Multi-tenant management (tenants, tenant groups, contacts)
- Extras: Journal entries, config contexts, reports, tags

Key indicators:
- "device", "rack", "cable", "power" → DCIM
- "IP", "subnet", "VLAN", "prefix" → IPAM
- "VM", "virtual machine", "cluster" → Virtualization
- "tenant" → Tenancy

Return classification in JSON format:
{{
    "primary_domain": "domain_name",
    "confidence": 0.0-1.0,
    "indicators": ["words/phrases that led to this classification"],
    "secondary_domain": "domain_name or null"
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You classify NetBox queries into domains accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            
            classification = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Domain classification: {classification.get('primary_domain')} "
                           f"(confidence: {classification.get('confidence', 0):.2f})")
            
            return {
                "success": True,
                "classification": classification
            }
            
        except Exception as e:
            self.logger.error(f"Domain classification failed: {e}")
            return {
                "success": False,
                "classification": {
                    "primary_domain": "unknown",
                    "confidence": 0.0
                }
            }
    
    async def extract_entities_and_relationships(
        self,
        query: str,
        domain: str = None
    ) -> Dict[str, Any]:
        """
        Extract entities and their relationships from query using LLM.
        
        Args:
            query: User query to analyze
            domain: NetBox domain context
            
        Returns:
            Dict containing extracted entities and relationships
        """
        try:
            prompt = f"""Extract NetBox entities and relationships from this query:

Query: "{query}"
Domain Context: {domain if domain else 'Not specified'}

Identify:
1. All NetBox entities mentioned (even implicitly)
2. Entity names/identifiers
3. Relationships between entities
4. Entity roles (primary target, filter, context)

Common patterns:
- "rack elevation for R01-A15" → rack entity (R01-A15) is primary
- "devices in site X" → site entity (X) is filter, devices are primary
- "VMs in cluster Y" → cluster entity (Y) is context, VMs are primary
- "interfaces on device Z" → device entity (Z) is parent, interfaces are primary

Return extraction in JSON format:
{{
    "entities": [
        {{
            "type": "rack|device|site|vm|cluster|etc",
            "identifier": "name or ID mentioned",
            "role": "primary|filter|context|parent",
            "confidence": 0.0-1.0
        }}
    ],
    "relationships": [
        {{
            "parent": "entity_identifier",
            "child": "entity_identifier",
            "relationship_type": "contains|belongs_to|connected_to"
        }}
    ],
    "implicit_entities": ["entities implied but not explicitly mentioned"]
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            extraction = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Extracted {len(extraction.get('entities', []))} entities, "
                           f"{len(extraction.get('relationships', []))} relationships")
            
            return {
                "success": True,
                "extraction": extraction
            }
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return {
                "success": False,
                "extraction": {
                    "entities": [],
                    "relationships": []
                }
            }
    
    async def suggest_tool_candidates(
        self,
        intent_analysis: Dict[str, Any],
        available_tools: List[str]
    ) -> Dict[str, Any]:
        """
        Suggest candidate tools based on query intent analysis using LLM.
        
        Args:
            intent_analysis: Query intent analysis result
            available_tools: List of available NetBox tools
            
        Returns:
            Dict containing tool suggestions with reasoning
        """
        try:
            prompt = f"""Suggest NetBox tools based on this query analysis:

Query Intent: {json.dumps(intent_analysis, indent=2)}

Sample Available Tools:
{json.dumps(available_tools[:30], indent=2)}

Suggest tools:
1. What's the primary tool for this query?
2. What alternative tools could work?
3. What tools might be needed for parameter discovery?
4. What's the reasoning for each suggestion?

Consider:
- Domain alignment (DCIM tools for physical, Virtualization for VMs)
- Operation type (list_all for listings, get for specific items)
- Entity relationships (may need multiple tools)

Return suggestions in JSON format:
{{
    "primary_tool": {{
        "name": "tool_name",
        "confidence": 0.0-1.0,
        "reasoning": "why this tool"
    }},
    "alternative_tools": [
        {{"name": "tool_name", "confidence": 0.0-1.0, "reasoning": "why"}}
    ],
    "discovery_tools": [
        {{"name": "tool_name", "purpose": "what to discover"}}
    ],
    "tool_sequence": ["ordered list if multiple tools needed"]
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You suggest NetBox tools based on query intent."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            suggestions = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Suggested primary tool: {suggestions.get('primary_tool', {}).get('name')} "
                           f"with {len(suggestions.get('alternative_tools', []))} alternatives")
            
            return {
                "success": True,
                "suggestions": suggestions
            }
            
        except Exception as e:
            self.logger.error(f"Tool suggestion failed: {e}")
            return {
                "success": False,
                "suggestions": {}
            }
    
    async def analyze_query_complexity(
        self,
        query: str,
        intent_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze query complexity to determine execution strategy using LLM.
        
        Args:
            query: User query
            intent_analysis: Previous intent analysis
            
        Returns:
            Dict containing complexity analysis
        """
        try:
            prompt = f"""Analyze the complexity of this NetBox query:

Query: "{query}"

Intent Analysis: {json.dumps(intent_analysis, indent=2) if intent_analysis else 'Not provided'}

Determine:
1. Complexity level (simple/moderate/complex)
2. Number of operations likely needed
3. Potential challenges or ambiguities
4. Recommended execution strategy
5. Estimated execution time

Complexity factors:
- Simple: Single entity, direct lookup
- Moderate: Multiple entities, relationships, or filters
- Complex: Multi-step operations, complex filters, or aggregations

Return analysis in JSON format:
{{
    "complexity_level": "simple|moderate|complex",
    "estimated_operations": 1-10,
    "challenges": ["list of potential issues"],
    "ambiguities": ["unclear aspects"],
    "execution_strategy": "direct|exploratory|multi_step",
    "estimated_seconds": 1-60,
    "requires_recovery": true/false,
    "explanation": "reasoning for complexity assessment"
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You analyze NetBox query complexity accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            complexity = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Query complexity: {complexity.get('complexity_level')}, "
                           f"Estimated operations: {complexity.get('estimated_operations')}")
            
            return {
                "success": True,
                "complexity": complexity
            }
            
        except Exception as e:
            self.logger.error(f"Complexity analysis failed: {e}")
            return {
                "success": False,
                "complexity": {
                    "complexity_level": "unknown",
                    "estimated_operations": 1
                }
            }
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process query intelligence request"""
        request_type = content.get("type", "analyze_intent")
        
        if request_type == "analyze_intent":
            return await self.analyze_query_intent(
                content.get("query", ""),
                content.get("context", {})
            )
        elif request_type == "classify_domain":
            return await self.classify_query_domain(
                content.get("query", "")
            )
        elif request_type == "extract_entities":
            return await self.extract_entities_and_relationships(
                content.get("query", ""),
                content.get("domain")
            )
        elif request_type == "suggest_tools":
            return await self.suggest_tool_candidates(
                content.get("intent_analysis", {}),
                content.get("available_tools", [])
            )
        elif request_type == "analyze_complexity":
            return await self.analyze_query_complexity(
                content.get("query", ""),
                content.get("intent_analysis", {})
            )
        else:
            return {"error": f"Unknown request type: {request_type}"}