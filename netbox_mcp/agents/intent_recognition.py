"""
Intent Recognition Agent - Natural language understanding and query classification
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from .base import BaseAgent, QueryContext
from .config import get_config


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"      # Single tool, direct execution
    MODERATE = "moderate"  # 2-3 tools, some coordination
    COMPLEX = "complex"    # Multiple tools, complex orchestration
    UNCLEAR = "unclear"    # Requires clarification


class IntentType(Enum):
    """Types of user intents"""
    DISCOVERY = "discovery"          # List, search, find operations
    RETRIEVAL = "retrieval"          # Get specific information
    ANALYSIS = "analysis"            # Analyze relationships, usage
    CREATION = "creation"            # Create new resources
    MODIFICATION = "modification"    # Update existing resources
    DELETION = "deletion"            # Remove resources
    REPORTING = "reporting"          # Generate reports, summaries
    HEALTH_CHECK = "health_check"    # System status checks
    CLARIFICATION = "clarification"  # Need more information
    UNCLEAR = "unclear"              # Intent cannot be determined


class IntentRecognitionAgent(BaseAgent):
    """
    Agent responsible for understanding user queries and extracting intent.
    Uses GPT-4o-mini with structured outputs for efficient classification.
    """
    
    def __init__(self, agent_id: str = "intent_recognizer"):
        config = get_config().openai
        super().__init__(agent_id, "intent_recognition", config)
        
        self.model = config.intent_model
        self.temperature = config.intent_temperature
        
        # System prompt for intent recognition
        self.system_prompt = """You are an expert at understanding NetBox queries and extracting structured information.

Your task is to analyze user queries and extract:
1. Primary intent (what the user wants to do)
2. Target entities (devices, sites, VLANs, etc.)
3. Filters and constraints
4. Query complexity
5. Required NetBox MCP tools

Entity Types:
- Devices, Sites, Racks, Cables, Interfaces
- VLANs, Prefixes, IP Addresses, VRFs
- Tenants, Contacts, Journal Entries
- Clusters, Virtual Machines
- Power infrastructure (panels, feeds, outlets, ports)
- Manufacturers, Device Types, Modules

Always respond with valid JSON containing these fields:
{
  "intent": "discovery|retrieval|analysis|creation|modification|deletion|reporting|health_check|clarification",
  "complexity": "simple|moderate|complex|unclear",
  "entities": [{"type": "entity_type", "value": "entity_value", "filters": {}}],
  "tools_needed": ["tool_name1", "tool_name2"],
  "requires_clarification": false,
  "clarification_needed": [],
  "confidence": 0.95
}"""
        
        # Known NetBox MCP tool patterns
        self.tool_patterns = {
            "netbox_list_all_sites": ["list sites", "show sites", "all sites"],
            "netbox_list_all_devices": ["list devices", "show devices", "all devices"],
            "netbox_list_all_vlans": ["list vlans", "show vlans", "all vlans"],
            "netbox_get_device_info": ["device info", "device details", "show device"],
            "netbox_get_site_info": ["site info", "site details", "show site"],
            "netbox_list_all_prefixes": ["list prefixes", "show prefixes", "ip ranges"],
            "netbox_list_all_racks": ["list racks", "show racks", "all racks"],
            "netbox_get_rack_inventory": ["rack inventory", "devices in rack"],
            "netbox_health_check": ["health", "status", "system check"],
        }
    
    async def initialize(self) -> None:
        """Initialize intent recognition agent"""
        self.logger.info("Intent Recognition Agent initialized")
    
    async def cleanup(self) -> None:
        """Clean up agent resources"""
        self.logger.info("Intent Recognition Agent cleaned up")
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process an intent recognition request"""
        request_type = content.get("type", "classify_query")
        
        if request_type == "classify_query":
            return await self.classify_query(content)
        elif request_type == "extract_entities":
            return await self.extract_entities(content)
        elif request_type == "suggest_tools":
            return await self.suggest_tools(content)
        else:
            return {"error": f"Unknown request type: {request_type}"}
    
    async def classify_query(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Classify user query and extract structured information"""
        user_query = content.get("query", "")
        context = content.get("context", {})
        
        try:
            # First, try pattern matching for known queries
            pattern_result = self._match_known_patterns(user_query)
            if pattern_result and pattern_result.get("confidence", 0) > 0.9:
                self.logger.info(f"Matched known pattern for query: {user_query}")
                return {
                    "success": True,
                    "classification": pattern_result
                }
            
            # Use OpenAI for complex intent recognition
            classification_prompt = f"""Analyze this NetBox query and extract structured information:

Query: "{user_query}"

Previous context: {json.dumps(context.get('conversation_history', [])[-3:], indent=2) if context.get('conversation_history') else 'None'}

Identify:
1. What the user wants to do (intent)
2. What NetBox objects are involved (entities)
3. Any filters or constraints mentioned
4. Complexity level (simple/moderate/complex)
5. Which NetBox MCP tools would be needed
6. Whether clarification is needed

Remember to respond with valid JSON as specified."""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            classification = json.loads(response.choices[0].message.content)
            
            # Validate and enhance the classification
            classification = self._validate_classification(classification, user_query)
            
            # Add query metadata
            classification["original_query"] = user_query
            classification["tokens_used"] = response.usage.total_tokens
            
            return {
                "success": True,
                "classification": classification
            }
            
        except Exception as e:
            self.logger.error(f"Error classifying query: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_classification": self._create_fallback_classification(user_query)
            }
    
    async def extract_entities(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract specific entities from user query"""
        query = content.get("query", "")
        entity_types = content.get("entity_types", [])
        
        extraction_prompt = f"""Extract these entity types from the query:

Query: "{query}"
Entity Types to Extract: {json.dumps(entity_types)}

For each entity found, provide:
- type: The entity type
- value: The exact value or name
- confidence: How confident you are (0-1)
- context: Any additional context

Respond with JSON:
{{
  "entities": [
    {{"type": "device", "value": "switch-01", "confidence": 0.95, "context": "primary device"}}
  ]
}}"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"}
            )
            
            entities = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "entities": entities.get("entities", [])
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return {
                "success": False,
                "error": str(e),
                "entities": []
            }
    
    async def suggest_tools(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest appropriate NetBox MCP tools for the query"""
        classification = content.get("classification", {})
        
        intent = classification.get("intent")
        entities = classification.get("entities", [])
        complexity = classification.get("complexity")
        
        # Map intent and entities to tools
        suggested_tools = []
        
        if intent == IntentType.DISCOVERY.value:
            for entity in entities:
                entity_type = entity.get("type", "").lower()
                if "device" in entity_type:
                    suggested_tools.append("netbox_list_all_devices")
                elif "site" in entity_type:
                    suggested_tools.append("netbox_list_all_sites")
                elif "vlan" in entity_type:
                    suggested_tools.append("netbox_list_all_vlans")
                elif "rack" in entity_type:
                    suggested_tools.append("netbox_list_all_racks")
                elif "prefix" in entity_type or "ip" in entity_type:
                    suggested_tools.append("netbox_list_all_prefixes")
        
        elif intent == IntentType.RETRIEVAL.value:
            for entity in entities:
                entity_type = entity.get("type", "").lower()
                entity_value = entity.get("value", "")
                if "device" in entity_type and entity_value:
                    suggested_tools.append("netbox_get_device_info")
                elif "site" in entity_type and entity_value:
                    suggested_tools.append("netbox_get_site_info")
                elif "rack" in entity_type and entity_value:
                    suggested_tools.append("netbox_get_rack_inventory")
        
        elif intent == IntentType.HEALTH_CHECK.value:
            suggested_tools.append("netbox_health_check")
        
        # Remove duplicates while preserving order
        suggested_tools = list(dict.fromkeys(suggested_tools))
        
        return {
            "success": True,
            "suggested_tools": suggested_tools,
            "execution_order": self._determine_execution_order(suggested_tools, complexity)
        }
    
    def _match_known_patterns(self, query: str) -> Optional[Dict[str, Any]]:
        """Match query against known patterns for fast classification"""
        query_lower = query.lower()
        
        # Check for direct tool matches
        for tool, patterns in self.tool_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return {
                        "intent": IntentType.DISCOVERY.value if "list" in pattern else IntentType.RETRIEVAL.value,
                        "complexity": QueryComplexity.SIMPLE.value,
                        "entities": self._extract_entities_from_pattern(query, pattern),
                        "tools_needed": [tool],
                        "requires_clarification": False,
                        "confidence": 0.95
                    }
        
        return None
    
    def _extract_entities_from_pattern(self, query: str, pattern: str) -> List[Dict[str, Any]]:
        """Extract entities based on matched pattern"""
        entities = []
        
        # Extract entity type from pattern
        if "device" in pattern:
            entity_type = "device"
        elif "site" in pattern:
            entity_type = "site"
        elif "vlan" in pattern:
            entity_type = "vlan"
        elif "rack" in pattern:
            entity_type = "rack"
        elif "prefix" in pattern:
            entity_type = "prefix"
        else:
            entity_type = "unknown"
        
        # Try to extract specific values from query
        # Look for quoted strings or specific patterns
        quoted = re.findall(r'"([^"]*)"', query)
        if quoted:
            for value in quoted:
                entities.append({
                    "type": entity_type,
                    "value": value,
                    "filters": {}
                })
        else:
            # Generic entity without specific value
            entities.append({
                "type": entity_type,
                "value": None,
                "filters": {}
            })
        
        return entities
    
    def _validate_classification(self, classification: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Validate and enhance classification results"""
        # Ensure required fields exist
        classification.setdefault("intent", IntentType.UNCLEAR.value)
        classification.setdefault("complexity", QueryComplexity.UNCLEAR.value)
        classification.setdefault("entities", [])
        classification.setdefault("tools_needed", [])
        classification.setdefault("requires_clarification", False)
        classification.setdefault("confidence", 0.5)
        
        # Validate intent
        valid_intents = [e.value for e in IntentType]
        if classification["intent"] not in valid_intents:
            classification["intent"] = IntentType.UNCLEAR.value
            classification["requires_clarification"] = True
        
        # Validate complexity
        valid_complexities = [e.value for e in QueryComplexity]
        if classification["complexity"] not in valid_complexities:
            classification["complexity"] = QueryComplexity.UNCLEAR.value
        
        # If no tools identified but intent is clear, suggest tools
        if not classification["tools_needed"] and classification["intent"] != IntentType.UNCLEAR.value:
            classification["tools_needed"] = self._suggest_tools_for_intent(
                classification["intent"],
                classification["entities"]
            )
        
        return classification
    
    def _suggest_tools_for_intent(self, intent: str, entities: List[Dict]) -> List[str]:
        """Suggest tools based on intent and entities"""
        tools = []
        
        if intent == IntentType.DISCOVERY.value:
            tools.extend(["netbox_list_all_sites", "netbox_list_all_devices"])
        elif intent == IntentType.HEALTH_CHECK.value:
            tools.append("netbox_health_check")
        elif intent == IntentType.RETRIEVAL.value and entities:
            for entity in entities:
                if entity.get("type") == "device":
                    tools.append("netbox_get_device_info")
                elif entity.get("type") == "site":
                    tools.append("netbox_get_site_info")
        
        return tools
    
    def _determine_execution_order(self, tools: List[str], complexity: str) -> List[List[str]]:
        """Determine optimal execution order for tools"""
        if complexity == QueryComplexity.SIMPLE.value:
            # Execute all tools in parallel
            return [tools]
        elif complexity == QueryComplexity.MODERATE.value:
            # Some sequential, some parallel
            # Group related tools
            groups = []
            current_group = []
            for tool in tools:
                if "list" in tool:
                    current_group.append(tool)
                else:
                    if current_group:
                        groups.append(current_group)
                        current_group = []
                    groups.append([tool])
            if current_group:
                groups.append(current_group)
            return groups
        else:
            # Complex - mostly sequential
            return [[tool] for tool in tools]
    
    def _create_fallback_classification(self, query: str) -> Dict[str, Any]:
        """Create a basic classification when OpenAI fails"""
        return {
            "intent": IntentType.UNCLEAR.value,
            "complexity": QueryComplexity.UNCLEAR.value,
            "entities": [],
            "tools_needed": [],
            "requires_clarification": True,
            "clarification_needed": ["Could you please rephrase your query?"],
            "confidence": 0.1,
            "original_query": query
        }