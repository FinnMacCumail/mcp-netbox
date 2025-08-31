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
        
        # System prompt for intent recognition - Enhanced for precise entity extraction
        self.system_prompt = """You are an expert NetBox infrastructure analyst specializing in precise entity extraction and query understanding.

Your primary mission: Extract structured information from natural language NetBox queries with maximum precision.

CORE CAPABILITIES:
1. Intent Classification - Determine what the user wants to accomplish
2. Entity Extraction - Identify ALL NetBox objects with exact names/values
3. Relationship Analysis - Understand hierarchical and associative relationships
4. Tool Mapping - Select optimal NetBox MCP tools for execution
5. Complexity Assessment - Determine execution strategy requirements

NETBOX ENTITY TYPES & REAL-WORLD PATTERNS:

DCIM Entities:
- Devices: "dmi01-akron-pdu01", "switch-core-01", "srv-db-primary", "fw-edge-main"
- Sites: "DM-Akron", "NC State University", "JBB Branch 104", "datacenter-east", "hq"
- Racks: "Comms closet", "Rack 1", "Row A Rack 5", "Network Cabinet", "Server-Rack-01"
- Interfaces: "GigabitEthernet0/1/0", "eth0", "ge-0/0/1", "Ethernet1/1", "mgmt0"
- Cables: Physical connections between interfaces, power connections
- Manufacturers: "Cisco", "Dell", "HPE", "Juniper Networks"
- Device Types: Model names like "Catalyst 9300", "PowerEdge R750", "EX4300"
- Device Roles: "switch", "server", "firewall", "router", "pdu", "console-server"
- Modules: Line cards, optics, power supplies in modular equipment

IPAM Entities:
- IP Addresses: "192.168.1.1", "10.0.0.1/32", "2001:db8::1"
- Prefixes: "10.112.128.0/17", "192.168.0.0/24", "172.16.0.0/12"
- VLANs: VLAN IDs (100, 200) or names ("PROD-DMZ", "MGMT-VLAN")
- VRFs: "PROD-VRF", "MGMT", "CUSTOMER-A"

VIRTUALIZATION Entities:
- Clusters: "PROD-VMware", "DEV-Cluster", "Hyper-V-01"
- Virtual Machines: "web-server-01", "db-vm-primary", "test-ubuntu"
- VM Interfaces: Virtual network interfaces

TENANCY Entities:
- Tenants: "Customer-A", "Department-IT", "Project-Alpha"
- Tenant Groups: Organizational hierarchies

POWER Entities:
- Power Panels: Electrical distribution panels
- Power Feeds: Electrical feeds from panels to racks
- Power Outlets: PDU outlets, UPS outputs
- Power Ports: Device power inputs

HIERARCHICAL RELATIONSHIPS:
- "rack X in site Y" - Rack-to-Site relationship
- "device Z in rack A in site B" - Device-to-Rack-to-Site chain
- "interface eth0 on device server-01" - Interface-to-Device
- "VLAN 100 in site headquarters" - VLAN-to-Site association
- "power feed A-1 to rack Row-A-01" - Power distribution chain

OUTPUT FORMAT:
Always respond with valid JSON:
{
  "intent": "discovery|retrieval|analysis|creation|modification|deletion|reporting|health_check|clarification",
  "complexity": "simple|moderate|complex|unclear", 
  "entities": [
    {
      "type": "device|site|rack|interface|vlan|prefix|cluster|tenant|cable|etc",
      "value": "exact_name_or_identifier",
      "context": "additional_context_or_relationship",
      "filters": {"key": "value"},
      "parent_entity": {"type": "parent_type", "value": "parent_value"},
      "confidence": 0.95
    }
  ],
  "tools_needed": ["netbox_tool_name1", "netbox_tool_name2"],
  "requires_clarification": false,
  "clarification_needed": [],
  "confidence": 0.95,
  "relationships": [{"from": "entity1", "to": "entity2", "type": "contains|connects|assigned"}]
}

PRECISION REQUIREMENTS:
- Extract EXACT entity names, preserving hyphens, numbers, spaces
- Identify parent-child relationships (rack in site, device in rack)
- Recognize interface naming conventions across vendors
- Handle both technical names and descriptive names
- Preserve IP address formats and CIDR notation
- Maintain case sensitivity for entity identifiers"""
        
        # Known NetBox MCP tool patterns - Enhanced with comprehensive tool coverage
        self.tool_patterns = {
            # DCIM Discovery & Analysis
            "netbox_list_all_sites": ["list sites", "show sites", "all sites", "sites"],
            "netbox_get_site_info": ["site info", "site details", "show site", "site information"],
            "netbox_list_all_devices": ["list devices", "show devices", "all devices", "devices"],
            "netbox_get_device_info": ["device info", "device details", "show device", "device information"],
            "netbox_get_device_basic_info": ["basic device info", "simple device info", "device overview"],
            "netbox_list_all_racks": ["list racks", "show racks", "all racks", "racks"],
            "netbox_get_rack_inventory": ["rack inventory", "devices in rack", "rack contents"],
            "netbox_get_rack_elevation": ["rack elevation", "rack layout", "rack diagram"],
            
            # Interface & Cable Analysis  
            "netbox_get_device_interfaces": ["device interfaces", "interfaces on device", "device ports"],
            "netbox_get_device_cables": ["device cables", "cables on device", "device connections"],
            "netbox_list_all_cables": ["list cables", "show cables", "all cables", "cables"],
            "netbox_get_cable_info": ["cable info", "cable details", "show cable"],
            
            # IPAM Tools
            "netbox_list_all_vlans": ["list vlans", "show vlans", "all vlans", "vlans"],
            "netbox_list_all_prefixes": ["list prefixes", "show prefixes", "ip ranges", "prefixes", "subnets"],
            "netbox_get_prefix_utilization": ["prefix utilization", "ip usage", "subnet usage"],
            "netbox_list_all_vrfs": ["list vrfs", "show vrfs", "all vrfs", "vrfs"],
            
            # Device Types & Manufacturers
            "netbox_list_all_manufacturers": ["list manufacturers", "show manufacturers", "vendors"],
            "netbox_list_all_device_types": ["list device types", "show models", "device models"],
            "netbox_get_device_type_info": ["device type info", "model info", "device type details"],
            "netbox_list_all_device_roles": ["list device roles", "show roles", "device roles"],
            
            # Module Management
            "netbox_list_all_modules": ["list modules", "show modules", "all modules", "modules"],
            "netbox_list_device_modules": ["device modules", "modules on device"],
            "netbox_get_module_info": ["module info", "module details"],
            "netbox_list_all_module_types": ["list module types", "module models"],
            
            # Tenancy
            "netbox_list_all_tenants": ["list tenants", "show tenants", "tenants", "customers"],
            "netbox_list_all_tenant_groups": ["tenant groups", "customer groups"],
            "netbox_get_tenant_resource_report": ["tenant report", "tenant resources", "customer report"],
            
            # System Health
            "netbox_health_check": ["health", "status", "system check", "health check"],
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
        elif request_type == "extract_entities_simple":
            return await self.extract_entities_simple(content)
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
    
    async def extract_entities_simple(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities using GPT without regex - Production-ready entity extraction
        
        This method provides simple, direct entity extraction optimized for immediate
        tool execution. Handles ALL NetBox entity types with real-world naming patterns.
        
        Args:
            content: Dictionary containing:
                - query: User's natural language query
                - focus_types: Optional list of entity types to focus on
                - include_relationships: Boolean to include hierarchical relationships
        
        Returns:
            Dictionary with extracted entities in simple structure for tool execution
        """
        query = content.get("query", "").strip()
        focus_types = content.get("focus_types", [])
        include_relationships = content.get("include_relationships", True)
        
        if not query:
            return {
                "success": False,
                "error": "Empty query provided",
                "entities": []
            }
        
        # Enhanced extraction prompt for all NetBox entity types
        extraction_prompt = f"""Extract NetBox entities from this query with maximum precision.

Query: "{query}"

EXTRACT THESE ENTITY TYPES:
{self._get_entity_extraction_guide(focus_types)}

CRITICAL EXTRACTION RULES:
1. Preserve EXACT names including hyphens, numbers, spaces, case
2. Identify hierarchical relationships (device in rack, rack in site)
3. Extract interface names with vendor-specific formats
4. Recognize IP addresses and prefixes with CIDR notation
5. Handle descriptive names and technical identifiers
6. Detect quoted strings as literal entity names
7. Identify numeric IDs (VLAN IDs, rack positions, etc.)

REAL-WORLD PATTERNS TO RECOGNIZE:
- Device names: "dmi01-akron-pdu01", "switch-core-01", "srv-web-prod-01"
- Site names: "DM-Akron", "NC State University", "Branch-104", "hq"
- Rack names: "Comms closet", "Rack 1", "Row A Rack 5", "Server-Rack-01"
- Interfaces: "GigabitEthernet0/1/0", "eth0", "ge-0/0/1", "Ethernet1/1", "mgmt0"
- IP/Prefixes: "10.112.128.0/17", "192.168.1.1", "172.16.0.0/12"
- VLANs: "VLAN 100", "PROD-DMZ", "MGMT-VLAN" (ID: 100, name: PROD-DMZ)

OUTPUT FORMAT - Return simple JSON:
{{
  "entities": [
    {{
      "type": "device|site|rack|interface|vlan|prefix|ip|cluster|tenant|cable|manufacturer|device_type|module",
      "value": "exact_entity_name_or_identifier",
      "context": "brief_context_from_query",
      "parent": {{"type": "parent_type", "value": "parent_name"}},
      "confidence": 0.9,
      "extraction_source": "direct_mention|inferred|pattern_match"
    }}
  ],
  "relationships": [
    {{
      "child": "entity_name",
      "parent": "parent_name", 
      "relationship_type": "located_in|connected_to|assigned_to|part_of"
    }}
  ] if include_relationships else [],
  "query_intent": "brief_intent_description",
  "extraction_confidence": 0.95
}}

Examples:
- "Show devices in rack Comms closet" -> device (type: device, value: null), rack (type: rack, value: "Comms closet")
- "Get info for switch-core-01" -> device (type: device, value: "switch-core-01")
- "List VLANs in site DM-Akron" -> vlan (type: vlan, value: null), site (type: site, value: "DM-Akron")
- "Check interface eth0 on srv-web-01" -> interface (type: interface, value: "eth0"), device (type: device, value: "srv-web-01")

Focus on accuracy over completeness. Extract only entities you are confident about."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precision NetBox entity extraction specialist. Extract entities with exact names and preserve all formatting, hyphens, numbers, and case sensitivity."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            extraction_result = json.loads(response.choices[0].message.content)
            
            # Validate and enhance extraction results
            entities = self._validate_extracted_entities(extraction_result.get("entities", []), query)
            relationships = extraction_result.get("relationships", []) if include_relationships else []
            
            # Add extraction metadata
            extraction_metadata = {
                "extraction_method": "gpt_simple",
                "query_intent": extraction_result.get("query_intent", "unknown"),
                "extraction_confidence": extraction_result.get("extraction_confidence", 0.5),
                "tokens_used": response.usage.total_tokens,
                "model_used": self.model
            }
            
            self.logger.info(f"Extracted {len(entities)} entities from query: {query[:100]}...")
            
            return {
                "success": True,
                "entities": entities,
                "relationships": relationships,
                "metadata": extraction_metadata,
                "query": query
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in entity extraction: {e}")
            return {
                "success": False,
                "error": f"Invalid JSON response from model: {str(e)}",
                "entities": [],
                "fallback": self._extract_entities_fallback(query)
            }
            
        except Exception as e:
            self.logger.error(f"Error in simple entity extraction: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "entities": [],
                "fallback": self._extract_entities_fallback(query)
            }
    
    def _get_entity_extraction_guide(self, focus_types: List[str]) -> str:
        """Generate entity extraction guide based on focus types"""
        if focus_types:
            return f"Focus on these entity types: {', '.join(focus_types)}"
        
        return """ALL NetBox entity types:
        
DCIM: devices, sites, racks, interfaces, cables, manufacturers, device_types, device_roles, modules, power_panels, power_feeds, power_outlets, power_ports
IPAM: ip_addresses, prefixes, vlans, vrfs  
VIRTUALIZATION: clusters, virtual_machines, vm_interfaces, virtual_disks
TENANCY: tenants, tenant_groups, contacts
SYSTEM: health_status, journal_entries
POWER: power_panels, power_feeds, power_outlets, power_ports, power_connections"""
    
    def _validate_extracted_entities(self, entities: List[Dict], query: str) -> List[Dict]:
        """Validate and enhance extracted entities"""
        validated_entities = []
        
        for entity in entities:
            # Ensure required fields
            if not entity.get("type") or not isinstance(entity.get("value"), (str, type(None))):
                self.logger.warning(f"Skipping invalid entity: {entity}")
                continue
            
            # Standardize entity type
            entity_type = self._standardize_entity_type(entity["type"])
            
            # Create validated entity
            validated_entity = {
                "type": entity_type,
                "value": entity.get("value"),
                "context": entity.get("context", ""),
                "confidence": min(float(entity.get("confidence", 0.5)), 1.0),
                "extraction_source": entity.get("extraction_source", "unknown")
            }
            
            # Add parent relationship if present
            if entity.get("parent") and isinstance(entity["parent"], dict):
                validated_entity["parent"] = {
                    "type": self._standardize_entity_type(entity["parent"].get("type", "")),
                    "value": entity["parent"].get("value", "")
                }
            
            # Add filters if they can be inferred
            validated_entity["filters"] = self._infer_entity_filters(validated_entity, query)
            
            validated_entities.append(validated_entity)
        
        return validated_entities
    
    def _standardize_entity_type(self, entity_type: str) -> str:
        """Standardize entity type names to NetBox conventions"""
        type_mapping = {
            # Common variations to standard types
            "device": "device",
            "devices": "device", 
            "server": "device",
            "switch": "device",
            "router": "device",
            "firewall": "device",
            
            "site": "site",
            "sites": "site",
            "location": "site",
            "datacenter": "site",
            
            "rack": "rack",
            "racks": "rack",
            "cabinet": "rack",
            
            "interface": "interface",
            "interfaces": "interface",
            "port": "interface",
            "ports": "interface",
            
            "vlan": "vlan",
            "vlans": "vlan",
            
            "prefix": "prefix",
            "prefixes": "prefix",
            "network": "prefix",
            "subnet": "prefix",
            
            "ip": "ip_address",
            "ip_address": "ip_address", 
            "address": "ip_address",
            
            "cluster": "cluster",
            "clusters": "cluster",
            
            "vm": "virtual_machine",
            "virtual_machine": "virtual_machine",
            "virtual_machines": "virtual_machine",
            
            "tenant": "tenant",
            "tenants": "tenant",
            "customer": "tenant",
            
            "cable": "cable",
            "cables": "cable",
            "connection": "cable",
            
            "manufacturer": "manufacturer",
            "manufacturers": "manufacturer",
            "vendor": "manufacturer",
            
            "device_type": "device_type",
            "device_types": "device_type",
            "model": "device_type"
        }
        
        return type_mapping.get(entity_type.lower(), entity_type.lower())
    
    def _infer_entity_filters(self, entity: Dict, query: str) -> Dict[str, Any]:
        """Infer filters for entity based on context and query"""
        filters = {}
        query_lower = query.lower()
        
        # Add common filter patterns
        if entity["type"] == "device":
            if "active" in query_lower:
                filters["status"] = "active"
            elif "inactive" in query_lower:
                filters["status"] = "inactive"
        
        if entity["type"] in ["device", "rack", "vlan", "prefix"]:
            if "site" in query_lower and entity.get("parent", {}).get("type") == "site":
                filters["site"] = entity["parent"]["value"]
        
        return filters
    
    def _extract_entities_fallback(self, query: str) -> List[Dict]:
        """Fallback entity extraction using basic patterns when GPT fails"""
        entities = []
        
        # Basic IP address pattern
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b'
        for match in re.finditer(ip_pattern, query):
            ip_value = match.group()
            entity_type = "prefix" if "/" in ip_value else "ip_address"
            entities.append({
                "type": entity_type,
                "value": ip_value,
                "context": "pattern_match",
                "confidence": 0.8,
                "extraction_source": "fallback_regex"
            })
        
        # Basic quoted string extraction for entity names
        quoted_pattern = r'"([^"]+)"'
        for match in re.finditer(quoted_pattern, query):
            entities.append({
                "type": "unknown",
                "value": match.group(1),
                "context": "quoted_string",
                "confidence": 0.6,
                "extraction_source": "fallback_quote"
            })
        
        return entities
    
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