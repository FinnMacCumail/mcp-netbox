#!/usr/bin/env python3
"""
ToolAwareParameterExtractor - Context-preserving parameter extraction for NetBox MCP

This module replaces the broken entity-first parameter mapping with intelligent
parameter extraction that knows what tool needs the parameters. This solves the
core problem where compound identifiers like "Cisco C9200-48P" lose context.

Key improvements:
- Context-preserving extraction: maintains relationships like manufacturer+model
- Tool schema-aware parsing: knows what parameters each tool expects  
- Compound identifier support: "Cisco C9200-48P" → {manufacturer: "Cisco", model: "C9200-48P"}
- Relationship preservation: "rack R01 in datacenter-01" → both entities with relationship
- Integration with IntelligentToolSelector from Phase 1
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
from dataclasses import dataclass
from enum import Enum

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..agents.config import get_config
from .intelligent_tool_selector import intelligent_tool_selector, ToolSelection

logger = logging.getLogger(__name__)


class ParameterConfidence(Enum):
    """Confidence levels for parameter extraction"""
    HIGH = "high"        # 0.8-1.0: Very confident in parameter values
    MEDIUM = "medium"    # 0.6-0.8: Confident, but may need validation
    LOW = "low"          # 0.4-0.6: Uncertain, should verify with user
    VERY_LOW = "very_low" # 0.0-0.4: Not confident, needs clarification


@dataclass
class ParameterExtractionResult:
    """Result of context-preserving parameter extraction"""
    parameters: Dict[str, Any]
    confidence: float
    confidence_level: ParameterConfidence
    extraction_method: str  # "schema_aware", "pattern_matching", "llm_extraction", "fallback"
    preserved_relationships: List[Dict[str, str]]  # Relationships like site->rack->device
    compound_entities: List[Dict[str, str]]  # Compound identifiers like manufacturer+model
    missing_parameters: List[str]  # Required parameters not found
    suggested_values: Dict[str, List[str]]  # Suggested values for missing parameters
    extraction_reasoning: str  # Why these parameters were extracted


class CompoundIdentifierParser:
    """Parser for compound identifiers like manufacturer+model, site+rack, device+interface"""
    
    # Patterns for compound identifiers (order matters for precedence)
    COMPOUND_PATTERNS = {
        # Device Type: Manufacturer + Model patterns
        "device_type": [
            # "Cisco Catalyst 9300-48P" -> manufacturer: Cisco, model: Catalyst 9300-48P
            r"(?P<manufacturer>cisco|dell|hp|hpe|juniper|arista|fortinet|palo alto|checkpoint)\s+(?P<model>.+?)(?:\s+(?:device|switch|router|firewall|server))?$",
            # "C9300-48P from Cisco" -> manufacturer: Cisco, model: C9300-48P
            r"(?P<model>[a-zA-Z0-9-_+.]+)\s+from\s+(?P<manufacturer>cisco|dell|hp|hpe|juniper|arista|fortinet|palo alto|checkpoint)",
            # "PowerEdge R750" (Dell is implied in context)
            r"(?P<model>powerEdge\s+r\d+|optiplex\s+\d+)",
            # Direct model patterns for common manufacturers
            r"(?P<model>c\d+[a-zA-Z0-9-]+|catalyst\s+\d+[a-zA-Z0-9-]*)",  # Cisco
            r"(?P<model>ex\d+[a-zA-Z0-9-]*|qfx\d+[a-zA-Z0-9-]*|srx\d+[a-zA-Z0-9-]*)",  # Juniper
            r"(?P<model>dl\d+[a-zA-Z0-9-]*|ml\d+[a-zA-Z0-9-]*|bl\d+[a-zA-Z0-9-]*)",  # HP/HPE
        ],
        
        # Site + Rack patterns
        "site_rack": [
            # "rack R01 in site datacenter-01" -> site_name: datacenter-01, rack_name: R01
            r"rack\s+(?P<rack_name>[^\s]+)\s+(?:in|at)\s+site\s+(?P<site_name>[^\s]+)",
            # "R01-A15 in Branch-104" -> site_name: Branch-104, rack_name: R01-A15
            r"(?P<rack_name>[a-zA-Z0-9_-]+)\s+(?:in|at)\s+(?P<site_name>[a-zA-Z0-9_-]+)",
            # "datacenter-01 rack Server-01" -> site_name: datacenter-01, rack_name: Server-01
            r"(?P<site_name>[a-zA-Z0-9_-]+)\s+rack\s+(?P<rack_name>[^\s]+)",
        ],
        
        # Device + Interface patterns  
        "device_interface": [
            # "interface eth0 on device switch-01" -> device_name: switch-01, interface_name: eth0
            r"interface\s+(?P<interface_name>[^\s]+)\s+on\s+device\s+(?P<device_name>[^\s]+)",
            # "switch-01 GigabitEthernet0/1/0" -> device_name: switch-01, interface_name: GigabitEthernet0/1/0
            r"(?P<device_name>[a-zA-Z0-9_-]+)\s+(?P<interface_name>(?:GigabitEthernet|FastEthernet|TenGigE|eth|ge-|xe-|et-)[^\s]+)",
            # "port eth0 on srv-web-01" -> device_name: srv-web-01, interface_name: eth0
            r"port\s+(?P<interface_name>[^\s]+)\s+on\s+(?P<device_name>[^\s]+)",
        ],
        
        # IP + Interface patterns
        "ip_interface": [
            # "IP 192.168.1.1 on interface eth0" -> ip_address: 192.168.1.1, interface_name: eth0  
            r"ip\s+(?P<ip_address>\d+\.\d+\.\d+\.\d+(?:/\d+)?)\s+on\s+interface\s+(?P<interface_name>[^\s]+)",
            # "assign 10.1.1.1 to eth0 on device switch-01"
            r"assign\s+(?P<ip_address>\d+\.\d+\.\d+\.\d+(?:/\d+)?)\s+to\s+(?P<interface_name>[^\s]+)\s+on\s+device\s+(?P<device_name>[^\s]+)",
        ],
        
        # VM + Cluster patterns
        "vm_cluster": [
            # "VM web-server-01 in cluster VMware-Prod" -> virtual_machine_name: web-server-01, cluster: VMware-Prod
            r"vm\s+(?P<virtual_machine_name>[^\s]+)\s+(?:in|on)\s+cluster\s+(?P<cluster>[^\s]+)",
            # "virtual machine db-01 on ESX-Cluster-01" 
            r"virtual\s+machine\s+(?P<virtual_machine_name>[^\s]+)\s+on\s+(?P<cluster>[^\s]+)",
        ]
    }
    
    # Manufacturer name mappings for normalization
    MANUFACTURER_ALIASES = {
        "cisco": ["cisco", "cisco systems"],
        "dell": ["dell", "dell technologies", "dell emc"],
        "hp": ["hp", "hewlett packard", "hewlett-packard"],
        "hpe": ["hpe", "hewlett packard enterprise"],
        "juniper": ["juniper", "juniper networks"],
        "arista": ["arista", "arista networks"],
        "fortinet": ["fortinet"],
        "palo alto": ["palo alto", "palo alto networks", "pan"],
        "checkpoint": ["checkpoint", "check point"],
    }
    
    @classmethod
    def extract_compound_identifiers(cls, query: str, tool_name: str) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
        """
        Extract compound identifiers from query based on tool requirements
        
        Args:
            query: User query string
            tool_name: Target NetBox tool name for context
            
        Returns:
            Tuple of (extracted_parameters, compound_entities_found)
        """
        query_lower = query.lower().strip()
        parameters = {}
        compound_entities = []
        
        # Determine which compound patterns are relevant based on tool
        relevant_patterns = cls._get_relevant_patterns(tool_name)
        
        for pattern_type in relevant_patterns:
            if pattern_type in cls.COMPOUND_PATTERNS:
                for pattern in cls.COMPOUND_PATTERNS[pattern_type]:
                    match = re.search(pattern, query_lower, re.IGNORECASE)
                    if match:
                        matched_params = match.groupdict()
                        
                        # Normalize manufacturer names
                        if "manufacturer" in matched_params:
                            matched_params["manufacturer"] = cls._normalize_manufacturer(matched_params["manufacturer"])
                        
                        # Add to parameters
                        parameters.update(matched_params)
                        
                        # Record compound entity
                        compound_entities.append({
                            "type": pattern_type,
                            "pattern": pattern,
                            "extracted": matched_params
                        })
                        
                        logger.debug(f"Extracted compound identifier: {pattern_type} -> {matched_params}")
                        break  # Use first matching pattern
        
        return parameters, compound_entities
    
    @classmethod  
    def _get_relevant_patterns(cls, tool_name: str) -> List[str]:
        """Get compound patterns relevant to the tool"""
        # Map tools to relevant compound patterns
        tool_patterns = {
            # Device type tools need manufacturer+model
            "netbox_get_device_type_info": ["device_type"],
            "netbox_create_device_type": ["device_type"], 
            "netbox_update_device_type": ["device_type"],
            
            # Rack tools may need site+rack
            "netbox_get_rack_inventory": ["site_rack"],
            "netbox_get_rack_elevation": ["site_rack"],
            "netbox_create_rack": ["site_rack"],
            
            # Interface tools need device+interface
            "netbox_get_device_interfaces": ["device_interface"],
            "netbox_create_interface": ["device_interface"],
            "netbox_assign_ip_to_interface": ["device_interface", "ip_interface"],
            
            # VM tools need vm+cluster
            "netbox_create_virtual_machine": ["vm_cluster"],
            "netbox_get_virtual_machine_info": ["vm_cluster"],
        }
        
        return tool_patterns.get(tool_name, [])
    
    @classmethod
    def _normalize_manufacturer(cls, manufacturer: str) -> str:
        """Normalize manufacturer name to canonical form"""
        manufacturer_lower = manufacturer.lower().strip()
        
        for canonical, aliases in cls.MANUFACTURER_ALIASES.items():
            if manufacturer_lower in aliases:
                return canonical.title()  # Return with proper case
        
        return manufacturer.title()  # Default to title case


class RelationshipPreserver:
    """Preserves hierarchical relationships between entities"""
    
    RELATIONSHIP_PATTERNS = [
        # Site -> Rack -> Device hierarchy
        {
            "pattern": r"device\s+(?P<device>\S+)\s+in\s+rack\s+(?P<rack>\S+)\s+(?:in|at)\s+site\s+(?P<site>\S+)",
            "relationships": [
                {"parent": "site", "child": "rack"},
                {"parent": "rack", "child": "device"}
            ]
        },
        {
            "pattern": r"rack\s+(?P<rack>\S+)\s+in\s+site\s+(?P<site>\S+)",
            "relationships": [
                {"parent": "site", "child": "rack"}
            ]
        },
        {
            "pattern": r"(?P<device>\S+)\s+in\s+(?P<rack>\S+)\s+at\s+(?P<site>\S+)",
            "relationships": [
                {"parent": "site", "child": "rack"},
                {"parent": "rack", "child": "device"}
            ]
        },
        
        # Device -> Interface hierarchy
        {
            "pattern": r"interface\s+(?P<interface>\S+)\s+on\s+device\s+(?P<device>\S+)",
            "relationships": [
                {"parent": "device", "child": "interface"}
            ]
        },
        
        # Cluster -> VM hierarchy
        {
            "pattern": r"(?:vm|virtual machine)\s+(?P<vm>\S+)\s+(?:in|on)\s+cluster\s+(?P<cluster>\S+)",
            "relationships": [
                {"parent": "cluster", "child": "vm"}
            ]
        },
        
        # VLAN -> Prefix relationship
        {
            "pattern": r"(?:vlan|network)\s+(?P<vlan>\S+)\s+with\s+(?:prefix|subnet)\s+(?P<prefix>\S+)",
            "relationships": [
                {"parent": "vlan", "child": "prefix"}
            ]
        }
    ]
    
    @classmethod
    def extract_relationships(cls, query: str) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        """
        Extract entity relationships from query
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (entity_mapping, relationships_found)
        """
        entities = {}
        relationships = []
        
        for pattern_info in cls.RELATIONSHIP_PATTERNS:
            pattern = pattern_info["pattern"]
            match = re.search(pattern, query, re.IGNORECASE)
            
            if match:
                # Extract entities from pattern
                extracted = match.groupdict()
                
                # Map extracted entities to parameter names
                entity_mapping = cls._map_entities_to_parameters(extracted)
                entities.update(entity_mapping)
                
                # Record relationships
                pattern_relationships = pattern_info["relationships"]
                for rel in pattern_relationships:
                    parent_key = rel["parent"]
                    child_key = rel["child"]
                    
                    if parent_key in extracted and child_key in extracted:
                        relationships.append({
                            "parent_type": parent_key,
                            "parent_value": extracted[parent_key],
                            "child_type": child_key,
                            "child_value": extracted[child_key],
                            "relationship": f"{parent_key}_contains_{child_key}"
                        })
                
                logger.debug(f"Extracted relationship: {pattern} -> entities: {entities}, relationships: {relationships}")
                break  # Use first matching pattern
        
        return entities, relationships
    
    @classmethod
    def _map_entities_to_parameters(cls, extracted: Dict[str, str]) -> Dict[str, str]:
        """Map extracted entity names to parameter names"""
        mapping = {
            "site": "site_name",
            "rack": "rack_name", 
            "device": "device_name",
            "interface": "interface_name",
            "vm": "virtual_machine_name",
            "cluster": "cluster_name",
            "vlan": "vlan_name",
            "prefix": "prefix"
        }
        
        result = {}
        for key, value in extracted.items():
            param_name = mapping.get(key, key)
            result[param_name] = value
            
        return result


class ToolAwareParameterExtractor:
    """
    Context-preserving parameter extraction that works with IntelligentToolSelector
    
    This replaces the broken entity-first mapping in state_machine.py with intelligent
    parameter extraction that knows what tool needs the parameters.
    """
    
    def __init__(self):
        """Initialize the tool-aware parameter extractor"""
        self.logger = logger
        
        # Initialize OpenAI client for LLM-based extraction
        try:
            config = get_config()
            self.openai_client = AsyncOpenAI(api_key=config.openai.api_key) if hasattr(config, 'openai') else None
            self.model = getattr(config.openai, 'coordination_model', 'gpt-4o-mini') if hasattr(config, 'openai') else 'gpt-4o-mini'
            self.temperature = getattr(config.openai, 'coordination_temperature', 0.1) if hasattr(config, 'openai') else 0.1
        except Exception as e:
            self.logger.warning(f"OpenAI client not available, using pattern matching only: {e}")
            self.openai_client = None
            self.model = "gpt-4o-mini"
            self.temperature = 0.1
    
    async def extract_parameters(
        self, 
        query: str, 
        tool_name: str, 
        tool_schema: Optional[Dict[str, Any]] = None
    ) -> ParameterExtractionResult:
        """
        Extract parameters from query knowing the target tool requirements.
        
        This is the main method that replaces the broken entity-first mapping.
        
        Args:
            query: User's natural language query
            tool_name: Target NetBox tool name  
            tool_schema: Optional tool schema with parameter definitions
            
        Returns:
            ParameterExtractionResult with extracted parameters and metadata
        """
        if not query or not query.strip():
            return self._create_empty_result("Empty query provided")
        
        query = query.strip()
        
        try:
            # Get tool schema from IntelligentToolSelector if not provided
            if not tool_schema:
                tool_info = intelligent_tool_selector.get_tool_catalog_entry(tool_name)
                if tool_info:
                    tool_schema = {
                        "required_parameters": tool_info.required_parameters,
                        "optional_parameters": tool_info.optional_parameters,
                        "entity_types": tool_info.entity_types
                    }
                else:
                    tool_schema = {"required_parameters": [], "optional_parameters": [], "entity_types": []}
            
            # Try schema-aware extraction first (fastest and most accurate)
            schema_result = await self._schema_aware_extraction(query, tool_name, tool_schema)
            if schema_result and schema_result.confidence >= 0.8:
                self.logger.info(f"Schema-aware extraction succeeded for {tool_name}")
                return schema_result
            
            # Try compound identifier parsing
            compound_result = await self._compound_identifier_extraction(query, tool_name, tool_schema)
            if compound_result and compound_result.confidence >= 0.7:
                self.logger.info(f"Compound identifier extraction succeeded for {tool_name}")
                return compound_result
            
            # Try relationship-preserving extraction
            relationship_result = await self._relationship_preserving_extraction(query, tool_name, tool_schema)
            if relationship_result and relationship_result.confidence >= 0.7:
                self.logger.info(f"Relationship-preserving extraction succeeded for {tool_name}")
                return relationship_result
            
            # Try LLM-based extraction if available
            if self.openai_client:
                llm_result = await self._llm_parameter_extraction(query, tool_name, tool_schema)
                if llm_result:
                    self.logger.info(f"LLM parameter extraction succeeded for {tool_name}")
                    return llm_result
            
            # Use best available result or fallback
            best_result = max(
                filter(None, [schema_result, compound_result, relationship_result]),
                key=lambda x: x.confidence,
                default=None
            )
            
            if best_result:
                return best_result
            
            # Final fallback
            return self._create_fallback_result(query, tool_name, tool_schema)
            
        except Exception as e:
            self.logger.error(f"Error in parameter extraction: {e}", exc_info=True)
            return self._create_error_result(f"Parameter extraction failed: {str(e)}")
    
    async def _schema_aware_extraction(
        self, 
        query: str, 
        tool_name: str, 
        tool_schema: Dict[str, Any]
    ) -> Optional[ParameterExtractionResult]:
        """LLM-powered semantic parameter extraction - Claude Code CLI style"""
        try:
            required_params = tool_schema.get("required_parameters", [])
            optional_params = tool_schema.get("optional_parameters", [])
            
            # Use LLM to semantically understand the query and extract parameters
            extraction_prompt = f"""Extract parameters for NetBox MCP tool '{tool_name}' from this user query.

Query: "{query}"

Tool expects these parameters:
- Required: {required_params}
- Optional: {optional_params}

Use semantic understanding to extract the correct parameter values:

Examples:
- "Get detailed information about device dmi01-akron-pdu01" → {{"device_name": "dmi01-akron-pdu01"}}
- "device type information for Cisco C9200-48P" → {{"manufacturer": "Cisco", "model": "C9200-48P"}}
- "rack elevation for R01-A15" → {{"rack_name": "R01-A15"}}
- "interfaces on device switch-01" → {{"device_name": "switch-01"}}
- "show me VLAN 100" → {{"vid": 100}}
- "site information for datacenter-01" → {{"site_name": "datacenter-01"}}

Key principles:
1. Extract entity names EXACTLY as mentioned in the query
2. Match entity types to correct parameter names for the tool
3. Handle compound identifiers (e.g., "Cisco C9200-48P" → manufacturer + model)
4. Use semantic context, not pattern matching
5. Convert numbers to integers where appropriate (vid, position, etc.)

Respond with JSON only:
{{
  "parameters": {{}},
  "confidence": 0.95,
  "reasoning": "brief explanation of extraction logic"
}}"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a NetBox parameter extraction specialist. Use semantic understanding to extract parameters accurately from user queries. Focus on understanding intent, not pattern matching."
                    },
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=512,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            parameters = result.get("parameters", {})
            confidence = min(result.get("confidence", 0.8), 0.95)
            reasoning = result.get("reasoning", "LLM semantic understanding")
            
            if parameters:
                # Validate and clean extracted parameters
                cleaned_parameters = {}
                for param, value in parameters.items():
                    if param in required_params or param in optional_params:
                        # Convert numeric strings to integers where appropriate
                        if param in ["vid", "vlan_id", "position", "u_height", "port", "rack_position"]:
                            try:
                                cleaned_parameters[param] = int(value) if str(value).isdigit() else value
                            except (ValueError, TypeError):
                                cleaned_parameters[param] = value
                        else:
                            cleaned_parameters[param] = str(value).strip() if value is not None else ""
                
                if cleaned_parameters:
                    self.logger.info(f"LLM semantic extraction succeeded for {tool_name}: {cleaned_parameters}")
                    
                    # Count compound entities (parameters with underscores or multiple words)
                    compound_count = len([p for p in cleaned_parameters.keys() if '_' in p or len(p.split()) > 1])
                    
                    return ParameterExtractionResult(
                        parameters=cleaned_parameters,
                        confidence=confidence,
                        confidence_level=self._get_confidence_level(confidence),
                        extraction_method="llm_semantic",
                        preserved_relationships=[],
                        compound_entities=[p for p in cleaned_parameters.keys() if '_' in p],
                        missing_parameters=[p for p in required_params if p not in cleaned_parameters],
                        suggested_values={},
                        extraction_reasoning=f"LLM semantic understanding: {reasoning}"
                    )
            
            return None
            
        except Exception as e:
            self.logger.warning(f"LLM semantic extraction failed for {tool_name}: {e}")
            # Fallback to simple heuristic extraction if LLM fails
            return await self._simple_heuristic_fallback(query, tool_name, tool_schema)
    
    async def _compound_identifier_extraction(
        self, 
        query: str, 
        tool_name: str, 
        tool_schema: Dict[str, Any]
    ) -> Optional[ParameterExtractionResult]:
        """Extract compound identifiers like manufacturer+model"""
        parameters, compound_entities = CompoundIdentifierParser.extract_compound_identifiers(query, tool_name)
        
        if parameters:
            # Calculate confidence based on how well we matched required parameters
            required_params = tool_schema.get("required_parameters", [])
            required_found = sum(1 for p in required_params if p in parameters)
            total_required = len(required_params) if required_params else 1
            
            confidence = (required_found / total_required) * 0.9  # High confidence for compound matching
            confidence = min(confidence, 0.95)
            
            return ParameterExtractionResult(
                parameters=parameters,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                extraction_method="compound_identifier",
                preserved_relationships=[],
                compound_entities=compound_entities,
                missing_parameters=[p for p in required_params if p not in parameters],
                suggested_values={},
                extraction_reasoning=f"Compound identifier extraction found {len(compound_entities)} compound entities"
            )
        
        return None
    
    async def _relationship_preserving_extraction(
        self, 
        query: str, 
        tool_name: str, 
        tool_schema: Dict[str, Any]
    ) -> Optional[ParameterExtractionResult]:
        """Extract parameters while preserving hierarchical relationships"""
        entities, relationships = RelationshipPreserver.extract_relationships(query)
        
        if entities:
            # Calculate confidence based on relationship completeness
            required_params = tool_schema.get("required_parameters", [])
            required_found = sum(1 for p in required_params if p in entities)
            total_required = len(required_params) if required_params else 1
            
            confidence = (required_found / total_required) * 0.85  # Good confidence for relationship matching
            confidence = min(confidence, 0.90)
            
            return ParameterExtractionResult(
                parameters=entities,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                extraction_method="relationship_preserving",
                preserved_relationships=relationships,
                compound_entities=[],
                missing_parameters=[p for p in required_params if p not in entities],
                suggested_values={},
                extraction_reasoning=f"Relationship-preserving extraction found {len(relationships)} relationships"
            )
        
        return None
    
    async def _llm_parameter_extraction(
        self, 
        query: str, 
        tool_name: str, 
        tool_schema: Dict[str, Any]
    ) -> Optional[ParameterExtractionResult]:
        """Use LLM for intelligent parameter extraction when patterns fail"""
        if not self.openai_client:
            return None
        
        extraction_prompt = f"""Extract parameters for NetBox tool '{tool_name}' from this query:

Query: "{query}"

Tool Schema:
- Required Parameters: {tool_schema.get('required_parameters', [])}  
- Optional Parameters: {tool_schema.get('optional_parameters', [])}
- Entity Types: {tool_schema.get('entity_types', [])}

CRITICAL INSTRUCTIONS:
1. Extract EXACT entity names from the query (preserve case, hyphens, numbers)
2. For compound identifiers like "Cisco C9200-48P":
   - manufacturer: "Cisco"
   - model: "C9200-48P"
3. For hierarchical relationships like "device switch-01 in rack R01 at site HQ":
   - device_name: "switch-01"
   - rack_name: "R01"
   - site_name: "HQ"
4. Don't invent values not in the query
5. Be conservative with confidence (0.0-1.0)

Respond with JSON:
{{
  "parameters": {{"param_name": "exact_value"}},
  "confidence": 0.85,
  "compound_entities": [
    {{"type": "device_type", "manufacturer": "Cisco", "model": "C9200-48P"}}
  ],
  "relationships": [
    {{"parent": "site", "parent_value": "HQ", "child": "rack", "child_value": "R01"}}
  ],
  "reasoning": "Explanation of extraction logic"
}}"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            parameters = result.get("parameters", {})
            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
            
            # Validate parameters against schema
            required_params = tool_schema.get("required_parameters", [])
            missing_params = [p for p in required_params if p not in parameters]
            
            return ParameterExtractionResult(
                parameters=parameters,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                extraction_method="llm_extraction",
                preserved_relationships=result.get("relationships", []),
                compound_entities=result.get("compound_entities", []),
                missing_parameters=missing_params,
                suggested_values={},
                extraction_reasoning=result.get("reasoning", "LLM-based parameter extraction")
            )
            
        except Exception as e:
            self.logger.error(f"LLM parameter extraction failed: {e}")
            return None
    
    async def extract_parameters_for_multiple_tools(
        self, 
        query: str, 
        tool_selections: List[ToolSelection]
    ) -> Dict[str, ParameterExtractionResult]:
        """
        Extract parameters for multiple tools in compound queries
        
        Args:
            query: User's natural language query
            tool_selections: List of tool selections from IntelligentToolSelector
            
        Returns:
            Dict mapping tool names to parameter extraction results
        """
        results = {}
        
        for tool_selection in tool_selections:
            try:
                # Extract parameters for this specific tool
                result = await self.extract_parameters(
                    query, 
                    tool_selection.primary_tool,
                    None  # Let it get schema from tool selector
                )
                
                # Merge any parameters already identified by tool selector
                if tool_selection.parameters:
                    result.parameters.update(tool_selection.parameters)
                    # Recalculate confidence if we added parameters
                    if tool_selection.parameters:
                        result.confidence = min(result.confidence + 0.1, 1.0)
                
                results[tool_selection.primary_tool] = result
                
            except Exception as e:
                self.logger.error(f"Error extracting parameters for {tool_selection.primary_tool}: {e}")
                results[tool_selection.primary_tool] = self._create_error_result(str(e))
        
        return results
    
    def _get_confidence_level(self, confidence: float) -> ParameterConfidence:
        """Convert numeric confidence to enum level"""
        if confidence >= 0.8:
            return ParameterConfidence.HIGH
        elif confidence >= 0.6:
            return ParameterConfidence.MEDIUM
        elif confidence >= 0.4:
            return ParameterConfidence.LOW
        else:
            return ParameterConfidence.VERY_LOW
    
    def _create_empty_result(self, reason: str) -> ParameterExtractionResult:
        """Create an empty extraction result"""
        return ParameterExtractionResult(
            parameters={},
            confidence=0.0,
            confidence_level=ParameterConfidence.VERY_LOW,
            extraction_method="empty",
            preserved_relationships=[],
            compound_entities=[],
            missing_parameters=[],
            suggested_values={},
            extraction_reasoning=reason
        )
    
    async def _simple_heuristic_fallback(
        self, 
        query: str, 
        tool_name: str, 
        tool_schema: Dict[str, Any]
    ) -> Optional[ParameterExtractionResult]:
        """Simple heuristic fallback when LLM extraction fails"""
        parameters = {}
        query_lower = query.lower()
        
        required_params = tool_schema.get("required_parameters", [])
        
        # Simple heuristics for common cases
        for param in required_params:
            if param == "device_name":
                # Look for device name after "device" 
                match = re.search(r"device\s+([a-zA-Z0-9_.-]+)", query_lower)
                if match:
                    parameters[param] = match.group(1)
                # Or at end of query if no "device" keyword found
                elif not parameters.get(param):
                    words = query.split()
                    if len(words) > 0:
                        # Take the last word that looks like a device name
                        for word in reversed(words):
                            if re.match(r"^[a-zA-Z0-9_.-]+$", word) and len(word) > 2:
                                parameters[param] = word
                                break
            
            elif param == "site_name":
                match = re.search(r"site\s+([a-zA-Z0-9_.-]+)", query_lower)
                if match:
                    parameters[param] = match.group(1)
                    
            elif param == "rack_name":
                match = re.search(r"rack\s+([a-zA-Z0-9_.-]+)", query_lower)
                if match:
                    parameters[param] = match.group(1)
        
        if parameters:
            return ParameterExtractionResult(
                parameters=parameters,
                confidence=0.6,  # Lower confidence for heuristic extraction
                confidence_level=self._get_confidence_level(0.6),
                extraction_method="heuristic_fallback",
                preserved_relationships=[],
                compound_entities=[],
                missing_parameters=[p for p in required_params if p not in parameters],
                suggested_values={},
                extraction_reasoning="Simple heuristic fallback when LLM extraction failed"
            )
        
        return None
    
    def _create_error_result(self, error_message: str) -> ParameterExtractionResult:
        """Create an error extraction result"""
        return ParameterExtractionResult(
            parameters={},
            confidence=0.0,
            confidence_level=ParameterConfidence.VERY_LOW,
            extraction_method="error",
            preserved_relationships=[],
            compound_entities=[],
            missing_parameters=[],
            suggested_values={},
            extraction_reasoning=f"Error: {error_message}"
        )
    
    def _create_fallback_result(
        self, 
        query: str, 
        tool_name: str, 
        tool_schema: Dict[str, Any]
    ) -> ParameterExtractionResult:
        """Create a fallback extraction result"""
        # Try simple keyword extraction as final fallback
        parameters = {}
        query_lower = query.lower()
        
        # Look for common entity patterns in the query
        simple_patterns = {
            r'([a-zA-Z0-9_.-]+)': 'potential_entity'
        }
        
        # Extract anything that looks like an entity name
        entities_found = re.findall(r'\b[a-zA-Z0-9_.-]{3,}\b', query)
        if entities_found:
            # Try to map to most likely parameter based on tool
            required_params = tool_schema.get("required_parameters", [])
            if required_params and entities_found:
                # Assign first entity to first required parameter as best guess
                parameters[required_params[0]] = entities_found[0]
        
        confidence = 0.2 if parameters else 0.1
        
        return ParameterExtractionResult(
            parameters=parameters,
            confidence=confidence,
            confidence_level=self._get_confidence_level(confidence),
            extraction_method="fallback",
            preserved_relationships=[],
            compound_entities=[],
            missing_parameters=[p for p in tool_schema.get("required_parameters", []) if p not in parameters],
            suggested_values={},
            extraction_reasoning="Fallback extraction using simple pattern matching"
        )


# Global instance
tool_aware_parameter_extractor = ToolAwareParameterExtractor()


async def extract_parameters(
    query: str, 
    tool_name: str, 
    tool_schema: Optional[Dict[str, Any]] = None
) -> ParameterExtractionResult:
    """
    Public interface for context-preserving parameter extraction.
    
    Args:
        query: User's natural language query
        tool_name: Target NetBox tool name
        tool_schema: Optional tool schema with parameter definitions
        
    Returns:
        ParameterExtractionResult with extracted parameters and metadata
    """
    return await tool_aware_parameter_extractor.extract_parameters(query, tool_name, tool_schema)


async def extract_parameters_for_multiple_tools(
    query: str, 
    tool_selections: List[ToolSelection]
) -> Dict[str, ParameterExtractionResult]:
    """
    Extract parameters for multiple tools in compound queries.
    
    Args:
        query: User's natural language query
        tool_selections: List of tool selections from IntelligentToolSelector
        
    Returns:
        Dict mapping tool names to parameter extraction results
    """
    return await tool_aware_parameter_extractor.extract_parameters_for_multiple_tools(query, tool_selections)