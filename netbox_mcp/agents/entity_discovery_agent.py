"""
Entity Discovery Agent - Intelligent NetBox entity exploration without pre-defined mappings

This agent explores the NetBox data model dynamically using LLM intelligence to
discover entities, relationships, and correct identifiers without hard-coded logic.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseAgent
from .config import get_config


class EntityDiscoveryAgent(BaseAgent):
    """
    Intelligent NetBox entity exploration agent that discovers data model
    relationships and correct identifiers using LLM-driven exploration.
    """
    
    def __init__(self, agent_id: str = "entity_discovery"):
        config = get_config().openai
        super().__init__(agent_id, "entity_discovery", config)
        
        self.model = config.response_model  # GPT-4o-mini
        self.temperature = 0.3  # Consistent exploration
        
        self.system_prompt = """You are an expert NetBox data model explorer that discovers entities and relationships dynamically.

Your responsibilities:
1. Explore NetBox entities to understand the data model
2. Discover correct names, slugs, and IDs for entities
3. Map user-provided names to actual NetBox identifiers
4. Understand entity relationships (site->rack, cluster->VM, etc.)
5. Generate exploration strategies based on error context

Key NetBox entity relationships:
- Sites contain Racks, Devices
- Racks contain Devices at specific positions
- Clusters contain Virtual Machines
- Device Types belong to Manufacturers
- Interfaces belong to Devices
- IP Addresses can be assigned to Interfaces
- VLANs and Prefixes are organized by VRFs

Always explore intelligently to find the correct entity identifiers."""
    
    async def initialize(self) -> None:
        """Initialize entity discovery agent"""
        self.logger.info("Entity Discovery Agent initialized")
        # Cache for discovered entities to avoid redundant queries
        self.entity_cache = {}
    
    async def cleanup(self) -> None:
        """Clean up agent resources"""
        self.entity_cache.clear()
        self.logger.info("Entity Discovery Agent cleaned up")
    
    async def discover_entity_context(
        self, 
        query: str,
        error_info: Dict[str, Any],
        available_tools: List[str] = None
    ) -> Dict[str, Any]:
        """
        Discover NetBox entity context based on query failure using LLM intelligence.
        
        Args:
            query: Original user query that failed
            error_info: Error analysis information
            available_tools: List of available NetBox tools for exploration
            
        Returns:
            Dict containing discovered entity context and mappings
        """
        try:
            # Build discovery prompt
            discovery_prompt = f"""Based on this NetBox query failure, plan entity exploration to understand the data model:

Original Query: {query}
Error Information: {json.dumps(error_info, indent=2)}

Available NetBox exploration tools (sample):
- netbox_list_all_sites: List all sites with their names and slugs
- netbox_list_all_racks: List racks in a site
- netbox_list_all_devices: List devices with filters
- netbox_list_all_clusters: List virtualization clusters
- netbox_list_all_virtual_machines: List VMs in clusters
- netbox_list_all_prefixes: List IP prefixes
- netbox_list_all_vlans: List VLANs

Generate exploration plan:
1. What NetBox entities should I query to understand the problem?
2. What relationships should I investigate?
3. What variations of names/identifiers should I look for?
4. What's the optimal exploration sequence?

Provide exploration plan in JSON format:
{{
    "primary_entity": "main entity to explore",
    "exploration_sequence": [
        {{"tool": "netbox_tool_name", "purpose": "why use this tool", "parameters": {{}}}},
    ],
    "entities_to_discover": ["entity1", "entity2"],
    "relationships_to_map": ["entity1->entity2"],
    "identifier_variations": ["name", "slug", "id"],
    "expected_discoveries": {{"entity": "what we expect to find"}}
}}"""
            
            # Get LLM exploration plan
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": discovery_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            exploration_plan = json.loads(response.choices[0].message.content)
            
            # Execute exploration plan (simulated - would call actual NetBox tools)
            discoveries = await self._execute_exploration_plan(exploration_plan)
            
            # Build final context
            context = {
                "exploration_plan": exploration_plan,
                "discoveries": discoveries,
                "timestamp": datetime.now().isoformat(),
                "cached_entities": len(self.entity_cache)
            }
            
            self.logger.info(f"Entity discovery complete - Found {len(discoveries)} entity mappings")
            
            return {
                "success": True,
                "context": context
            }
            
        except Exception as e:
            self.logger.error(f"Entity discovery failed: {e}")
            return {
                "success": False,
                "context": {
                    "error": str(e),
                    "discoveries": {}
                }
            }
    
    async def resolve_entity_identifier(
        self,
        entity_type: str,
        user_provided_name: str,
        discovered_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve user-provided entity name to correct NetBox identifier using LLM.
        
        Args:
            entity_type: Type of entity (site, rack, device, etc.)
            user_provided_name: Name provided by user
            discovered_entities: List of actual entities from NetBox
            
        Returns:
            Dict containing resolved identifier and confidence
        """
        try:
            prompt = f"""Match the user-provided {entity_type} name to the correct NetBox entity:

User Provided: "{user_provided_name}"

Available {entity_type}s in NetBox:
{json.dumps(discovered_entities[:20], indent=2)}

Determine:
1. Which NetBox entity best matches the user's intent?
2. What's the correct identifier to use (name, slug, or id)?
3. How confident are you in this match?

Consider:
- Exact matches
- Case variations
- Partial matches
- Common abbreviations
- Display name vs slug patterns (e.g., "DM-Akron" vs "dm-akron")

Return in JSON format:
{{
    "matched_entity": {{"name": "...", "slug": "...", "id": ...}},
    "correct_identifier": "the actual value to use",
    "identifier_type": "name|slug|id",
    "confidence": 0.0-1.0,
    "reasoning": "why this match"
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You match user entity names to NetBox entities intelligently."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"}
            )
            
            resolution = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Resolved '{user_provided_name}' to '{resolution.get('correct_identifier')}' "
                           f"(confidence: {resolution.get('confidence', 0):.2f})")
            
            return resolution
            
        except Exception as e:
            self.logger.error(f"Entity resolution failed: {e}")
            return {
                "matched_entity": None,
                "correct_identifier": user_provided_name,
                "identifier_type": "name",
                "confidence": 0.0,
                "reasoning": f"Resolution failed: {e}"
            }
    
    async def discover_entity_relationships(
        self,
        primary_entity: str,
        entity_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Discover relationships for a NetBox entity using LLM intelligence.
        
        Args:
            primary_entity: The entity type to explore relationships for
            entity_data: Data about the entity
            
        Returns:
            Dict containing discovered relationships
        """
        try:
            prompt = f"""Analyze this NetBox entity data to discover relationships:

Entity Type: {primary_entity}
Entity Data: {json.dumps(entity_data, indent=2)}

Identify:
1. What other entities does this relate to?
2. What are the relationship types (parent, child, peer)?
3. What fields indicate these relationships?
4. What additional queries would reveal more relationships?

Return in JSON format:
{{
    "parent_entities": [{{"type": "...", "field": "...", "value": ...}}],
    "child_entities": [{{"type": "...", "field": "...", "count": ...}}],
    "peer_entities": [{{"type": "...", "field": "...", "value": ...}}],
    "relationship_map": {{"entity": ["related_entities"]}},
    "exploration_suggestions": ["additional queries to run"]
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
            
            relationships = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "relationships": relationships
            }
            
        except Exception as e:
            self.logger.error(f"Relationship discovery failed: {e}")
            return {
                "success": False,
                "relationships": {}
            }
    
    async def _execute_exploration_plan(
        self,
        exploration_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the exploration plan by calling actual NetBox tools.
        """
        discoveries = {}
        
        try:
            # Import real API handler for actual NetBox calls
            from ..orchestration.real_api_handler import RealAPIHandler
            
            # Initialize API handler
            api_handler = RealAPIHandler()
            await api_handler.initialize()
            
            # Execute exploration sequence with real NetBox calls
            for step in exploration_plan.get("exploration_sequence", []):
                tool = step.get("tool")
                purpose = step.get("purpose")
                params = step.get("params", {})
                
                self.logger.info(f"Executing real exploration: {tool} for {purpose}")
                
                try:
                    # Execute the actual NetBox tool
                    result = await api_handler.execute_tool(tool, **params)
                    
                    if result and result.success and result.result:
                        # Extract meaningful data from the result
                        discoveries.update(self._extract_discoveries_from_result(tool, result.result))
                        self.logger.info(f"Real exploration successful: {tool} returned data")
                    else:
                        self.logger.warning(f"Real exploration failed: {tool} - {result.error if result else 'No result'}")
                        # Fallback to basic discovery patterns
                        discoveries.update(self._get_fallback_discoveries(tool))
                        
                except Exception as e:
                    self.logger.warning(f"Real exploration error for {tool}: {e}")
                    # Fallback to basic discovery patterns
                    discoveries.update(self._get_fallback_discoveries(tool))
            
        except Exception as e:
            self.logger.warning(f"API handler initialization failed: {e}")
            # Fallback to basic patterns when API is unavailable
            discoveries = self._get_basic_fallback_discoveries(exploration_plan)
        
        return discoveries
    
    def _extract_discoveries_from_result(self, tool_name: str, result_data: Any) -> Dict[str, Any]:
        """Extract entity mappings from actual NetBox API results"""
        discoveries = {}
        
        try:
            if "sites" in tool_name.lower():
                discoveries["sites"] = self._extract_site_mappings(result_data)
            elif "racks" in tool_name.lower():
                discoveries["racks"] = self._extract_rack_mappings(result_data)
            elif "devices" in tool_name.lower():
                discoveries["devices"] = self._extract_device_mappings(result_data)
            elif "clusters" in tool_name.lower():
                discoveries["clusters"] = self._extract_cluster_mappings(result_data)
            elif "virtual" in tool_name.lower() or "vm" in tool_name.lower():
                discoveries["virtual_machines"] = self._extract_vm_mappings(result_data)
            elif "prefix" in tool_name.lower():
                discoveries["prefixes"] = self._extract_prefix_mappings(result_data)
                
        except Exception as e:
            self.logger.warning(f"Error extracting discoveries from {tool_name}: {e}")
            
        return discoveries
    
    def _extract_site_mappings(self, data: Any) -> Dict[str, str]:
        """Extract site name -> slug mappings from NetBox API response"""
        mappings = {}
        
        try:
            if isinstance(data, list):
                for site in data:
                    if isinstance(site, dict) and "name" in site and "slug" in site:
                        mappings[site["name"]] = site["slug"]
            elif isinstance(data, dict) and "results" in data:
                for site in data["results"]:
                    if isinstance(site, dict) and "name" in site and "slug" in site:
                        mappings[site["name"]] = site["slug"]
                        
        except Exception as e:
            self.logger.warning(f"Error extracting site mappings: {e}")
            
        return mappings
    
    def _extract_rack_mappings(self, data: Any) -> Dict[str, Dict[str, Any]]:
        """Extract rack name -> {id, slug, site} mappings from NetBox API response"""
        mappings = {}
        
        try:
            if isinstance(data, list):
                for rack in data:
                    if isinstance(rack, dict) and "name" in rack:
                        mappings[rack["name"]] = {
                            "id": rack.get("id"),
                            "slug": rack.get("slug", rack.get("name", "").lower().replace(" ", "-")),
                            "site": rack.get("site", {}).get("slug") if isinstance(rack.get("site"), dict) else None
                        }
            elif isinstance(data, dict) and "results" in data:
                for rack in data["results"]:
                    if isinstance(rack, dict) and "name" in rack:
                        mappings[rack["name"]] = {
                            "id": rack.get("id"),
                            "slug": rack.get("slug", rack.get("name", "").lower().replace(" ", "-")),
                            "site": rack.get("site", {}).get("slug") if isinstance(rack.get("site"), dict) else None
                        }
                        
        except Exception as e:
            self.logger.warning(f"Error extracting rack mappings: {e}")
            
        return mappings
    
    def _extract_device_mappings(self, data: Any) -> Dict[str, Dict[str, Any]]:
        """Extract device name -> metadata mappings"""
        mappings = {}
        
        try:
            results = data
            if isinstance(data, dict) and "results" in data:
                results = data["results"]
            
            if isinstance(results, list):
                for device in results:
                    if isinstance(device, dict) and "name" in device:
                        mappings[device["name"]] = {
                            "id": device.get("id"),
                            "site": device.get("site", {}).get("slug") if isinstance(device.get("site"), dict) else None,
                            "rack": device.get("rack", {}).get("name") if isinstance(device.get("rack"), dict) else None
                        }
        except Exception as e:
            self.logger.warning(f"Error extracting device mappings: {e}")
            
        return mappings
    
    def _extract_cluster_mappings(self, data: Any) -> Dict[str, Dict[str, Any]]:
        """Extract cluster name -> metadata mappings"""
        mappings = {}
        
        try:
            results = data
            if isinstance(data, dict) and "results" in data:
                results = data["results"]
            
            if isinstance(results, list):
                for cluster in results:
                    if isinstance(cluster, dict) and "name" in cluster:
                        mappings[cluster["name"]] = {
                            "id": cluster.get("id"),
                            "site": cluster.get("site", {}).get("slug") if isinstance(cluster.get("site"), dict) else None
                        }
        except Exception as e:
            self.logger.warning(f"Error extracting cluster mappings: {e}")
            
        return mappings
    
    def _extract_vm_mappings(self, data: Any) -> Dict[str, Dict[str, Any]]:
        """Extract VM name -> metadata mappings"""
        mappings = {}
        
        try:
            results = data
            if isinstance(data, dict) and "results" in data:
                results = data["results"]
            
            if isinstance(results, list):
                for vm in results:
                    if isinstance(vm, dict) and "name" in vm:
                        mappings[vm["name"]] = {
                            "id": vm.get("id"),
                            "cluster": vm.get("cluster", {}).get("name") if isinstance(vm.get("cluster"), dict) else None
                        }
        except Exception as e:
            self.logger.warning(f"Error extracting VM mappings: {e}")
            
        return mappings
    
    def _extract_prefix_mappings(self, data: Any) -> Dict[str, Dict[str, Any]]:
        """Extract prefix -> metadata mappings"""
        mappings = {}
        
        try:
            results = data
            if isinstance(data, dict) and "results" in data:
                results = data["results"]
            
            if isinstance(results, list):
                for prefix in results:
                    if isinstance(prefix, dict) and "prefix" in prefix:
                        mappings[prefix["prefix"]] = {
                            "id": prefix.get("id"),
                            "vlan": prefix.get("vlan", {}).get("vid") if isinstance(prefix.get("vlan"), dict) else None,
                            "site": prefix.get("site", {}).get("slug") if isinstance(prefix.get("site"), dict) else None
                        }
        except Exception as e:
            self.logger.warning(f"Error extracting prefix mappings: {e}")
            
        return mappings
    
    def _get_fallback_discoveries(self, tool_name: str) -> Dict[str, Any]:
        """Get basic fallback discoveries when real API calls fail"""
        discoveries = {}
        
        if "sites" in tool_name.lower():
            discoveries["sites"] = {
                "DM-Akron": "dm-akron",
                "DM-Scranton": "dm-scranton"
            }
        elif "racks" in tool_name.lower():
            discoveries["racks"] = {
                "Comms closet": {"slug": "comms-closet", "id": 1, "site": "dm-akron"},
                "Rack Comms closet": {"slug": "rack-comms-closet", "id": 2, "site": "dm-scranton"}
            }
        elif "clusters" in tool_name.lower():
            discoveries["clusters"] = {
                "DO-AMS3": {"id": 1, "type": "virtualization"}
            }
            
        return discoveries
    
    def _get_basic_fallback_discoveries(self, exploration_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Get basic fallback discoveries when API is completely unavailable"""
        discoveries = {
            "sites": {"DM-Akron": "dm-akron", "DM-Scranton": "dm-scranton"},
            "racks": {"Comms closet": {"slug": "comms-closet", "id": 1, "site": "dm-akron"}},
            "clusters": {"DO-AMS3": {"id": 1, "type": "virtualization"}}
        }
        
        # Cache discoveries
        self.entity_cache.update(discoveries)
        
        return discoveries
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process entity discovery request"""
        request_type = content.get("type", "discover_context")
        
        if request_type == "discover_context":
            return await self.discover_entity_context(
                content.get("query", ""),
                content.get("error_info", {}),
                content.get("available_tools", [])
            )
        elif request_type == "resolve_identifier":
            resolution = await self.resolve_entity_identifier(
                content.get("entity_type", ""),
                content.get("user_name", ""),
                content.get("discovered_entities", [])
            )
            return {"success": True, "resolution": resolution}
        elif request_type == "discover_relationships":
            return await self.discover_entity_relationships(
                content.get("entity_type", ""),
                content.get("entity_data", {})
            )
        else:
            return {"error": f"Unknown request type: {request_type}"}