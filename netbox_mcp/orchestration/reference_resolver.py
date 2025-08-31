"""
ReferenceResolver for Advanced Pronoun and Entity Reference Resolution
Week 9-12: Real NetBox Integration & Advanced Conversation Management

This module provides sophisticated reference resolution for complex linguistic patterns,
multi-entity references, and NetBox-specific contextual resolution patterns.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from .entity_tracker import EntityTracker, EntityType, TrackedEntity

logger = logging.getLogger(__name__)


class ReferenceType(Enum):
    """Types of entity references that can be resolved"""
    PRONOUN = "pronoun"                    # it, that, this, them
    DEMONSTRATIVE = "demonstrative"        # the device, that server
    POSSESSIVE = "possessive"              # its interface, their connections
    QUANTIFIED = "quantified"              # both devices, all sites
    COMPARATIVE = "comparative"            # the other rack, another site
    SUPERLATIVE = "superlative"            # the main site, primary device
    RELATIONAL = "relational"              # connected device, parent site
    TEMPORAL = "temporal"                  # previous device, last site
    CONTEXTUAL = "contextual"              # current focus, mentioned earlier


@dataclass
class ReferencePattern:
    """Pattern for matching and resolving references"""
    pattern: str                           # Regex pattern to match
    reference_type: ReferenceType          # Type of reference
    priority: int                          # Resolution priority (higher = first)
    context_required: bool = False         # Whether context is required
    multi_entity: bool = False             # Whether it can resolve to multiple entities


class ReferenceResolver:
    """
    Advanced reference resolver for NetBox conversation management.
    
    Handles complex linguistic patterns, multi-entity references, and NetBox-specific
    contextual resolution that goes beyond simple pronoun resolution.
    """
    
    def __init__(self, entity_tracker: EntityTracker):
        self.entity_tracker = entity_tracker
        self.logger = logging.getLogger(__name__)
        
        # Reference resolution patterns ordered by priority
        self.resolution_patterns = self._initialize_resolution_patterns()
        
        # NetBox-specific relationship patterns
        self.relationship_patterns = self._initialize_relationship_patterns()
        
        # Linguistic context tracking
        self.discourse_stack = []              # Stack of recent discourse entities
        self.quantifier_context = {}          # Tracking quantified references
        self.comparison_context = {}          # Tracking comparative references
        
        # Resolution statistics
        self.resolution_stats = {
            "total_attempts": 0,
            "successful_resolutions": 0,
            "multi_entity_resolutions": 0,
            "context_based_resolutions": 0,
            "pattern_match_counts": {},
            "failure_reasons": {}
        }
    
    def resolve_reference(
        self, 
        reference_text: str, 
        conversation_context: Optional[Dict[str, Any]] = None,
        require_validation: bool = False
    ) -> Dict[str, Any]:
        """
        Resolve complex entity references with comprehensive linguistic analysis.
        
        Args:
            reference_text: Text containing the reference to resolve
            conversation_context: Additional conversation context
            require_validation: Whether to validate entities exist in NetBox
            
        Returns:
            Resolution result with entity_ids, confidence, and metadata
        """
        self.resolution_stats["total_attempts"] += 1
        
        try:
            # Normalize reference text
            normalized_ref = self._normalize_reference(reference_text)
            
            # Try each resolution pattern in priority order
            for pattern in self.resolution_patterns:
                match = re.search(pattern.pattern, normalized_ref, re.IGNORECASE)
                if match:
                    # Track pattern usage
                    pattern_name = f"{pattern.reference_type.value}_{pattern.priority}"
                    self.resolution_stats["pattern_match_counts"][pattern_name] = \
                        self.resolution_stats["pattern_match_counts"].get(pattern_name, 0) + 1
                    
                    # Attempt resolution using this pattern
                    result = self._resolve_with_pattern(
                        pattern, match, normalized_ref, conversation_context
                    )
                    
                    if result and result.get("entity_ids"):
                        # Validate entities if required
                        if require_validation:
                            result = self._validate_resolved_entities(result)
                        
                        if result.get("entity_ids"):
                            self.resolution_stats["successful_resolutions"] += 1
                            if len(result["entity_ids"]) > 1:
                                self.resolution_stats["multi_entity_resolutions"] += 1
                            
                            return result
            
            # Fallback to basic EntityTracker resolution
            fallback_result = self._fallback_resolution(normalized_ref, conversation_context)
            if fallback_result:
                return fallback_result
            
            # Resolution failed
            failure_reason = "no_pattern_match"
            self.resolution_stats["failure_reasons"][failure_reason] = \
                self.resolution_stats["failure_reasons"].get(failure_reason, 0) + 1
            
            return {
                "entity_ids": [],
                "confidence": 0.0,
                "reference_type": "unknown",
                "resolution_method": "failed",
                "failure_reason": failure_reason
            }
            
        except Exception as e:
            self.logger.error(f"Error resolving reference '{reference_text}': {e}")
            failure_reason = "resolution_error"
            self.resolution_stats["failure_reasons"][failure_reason] = \
                self.resolution_stats["failure_reasons"].get(failure_reason, 0) + 1
            
            return {
                "entity_ids": [],
                "confidence": 0.0,
                "reference_type": "error",
                "resolution_method": "failed",
                "failure_reason": failure_reason,
                "error": str(e)
            }
    
    def resolve_relational_reference(
        self, 
        base_entity_id: str, 
        relationship_description: str
    ) -> List[str]:
        """
        Resolve references based on NetBox entity relationships.
        
        Args:
            base_entity_id: Starting entity for relationship traversal
            relationship_description: Description of the relationship (e.g., "connected devices")
            
        Returns:
            List of related entity IDs
        """
        try:
            base_entity = self.entity_tracker.get_entity_context(base_entity_id)
            if not base_entity:
                return []
            
            relationship_lower = relationship_description.lower()
            related_entities = []
            
            # Direct relationship lookup
            relationships = base_entity.get("relationships", {})
            
            # NetBox-specific relationship patterns
            if "connected" in relationship_lower:
                # Find connected devices/interfaces
                if "interface" in relationships:
                    related_entities.extend(relationships["interface"])
                if "cable" in relationships:
                    related_entities.extend(relationships["cable"])
            
            elif "same" in relationship_lower and "site" in relationship_lower:
                # Find entities in the same site
                base_site = self._extract_site_from_entity(base_entity_id)
                if base_site:
                    site_entities = self.entity_tracker.get_entities_by_type(EntityType.DEVICE)
                    for entity in site_entities:
                        if self._extract_site_from_entity(entity["entity_id"]) == base_site:
                            related_entities.append(entity["entity_id"])
            
            elif "same" in relationship_lower and "rack" in relationship_lower:
                # Find entities in the same rack
                base_rack = self._extract_rack_from_entity(base_entity_id)
                if base_rack:
                    rack_entities = self.entity_tracker.get_entities_by_type(EntityType.DEVICE)
                    for entity in rack_entities:
                        if self._extract_rack_from_entity(entity["entity_id"]) == base_rack:
                            related_entities.append(entity["entity_id"])
            
            elif "parent" in relationship_lower or "container" in relationship_lower:
                # Find parent/container entities
                if "parent" in relationships:
                    related_entities.extend(relationships["parent"])
            
            elif "child" in relationship_lower or "contained" in relationship_lower:
                # Find child/contained entities
                if "children" in relationships:
                    related_entities.extend(relationships["children"])
            
            return list(set(related_entities))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error resolving relational reference: {e}")
            return []
    
    def resolve_quantified_reference(
        self, 
        quantifier: str, 
        entity_type: Optional[str] = None,
        context_filter: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Resolve quantified references like "all devices", "both sites", "some racks".
        
        Args:
            quantifier: Quantifier word (all, both, some, many, few)
            entity_type: Optional entity type filter
            context_filter: Optional additional filtering context
            
        Returns:
            List of entity IDs matching the quantified reference
        """
        try:
            quantifier_lower = quantifier.lower()
            
            # Get entities to consider
            if entity_type:
                try:
                    entity_type_enum = EntityType(entity_type.lower())
                    candidate_entities = self.entity_tracker.get_entities_by_type(entity_type_enum)
                except ValueError:
                    candidate_entities = []
            else:
                # Get all entities
                candidate_entities = []
                for etype in EntityType:
                    candidate_entities.extend(self.entity_tracker.get_entities_by_type(etype))
            
            # Apply context filtering if provided
            if context_filter:
                candidate_entities = self._apply_context_filter(candidate_entities, context_filter)
            
            # Apply quantifier logic
            if quantifier_lower in ["all", "every", "each"]:
                return [e["entity_id"] for e in candidate_entities]
            
            elif quantifier_lower in ["both", "pair"]:
                # Return exactly 2 if available
                return [e["entity_id"] for e in candidate_entities[:2]]
            
            elif quantifier_lower in ["some", "several", "few"]:
                # Return subset (2-5 entities)
                count = min(len(candidate_entities), max(2, len(candidate_entities) // 2))
                return [e["entity_id"] for e in candidate_entities[:count]]
            
            elif quantifier_lower in ["many", "most"]:
                # Return majority (75% or more)
                count = max(1, int(len(candidate_entities) * 0.75))
                return [e["entity_id"] for e in candidate_entities[:count]]
            
            else:
                # Unknown quantifier, return all
                return [e["entity_id"] for e in candidate_entities]
                
        except Exception as e:
            self.logger.error(f"Error resolving quantified reference: {e}")
            return []
    
    def _initialize_resolution_patterns(self) -> List[ReferencePattern]:
        """Initialize ordered list of reference resolution patterns"""
        return [
            # High priority - specific NetBox patterns
            ReferencePattern(
                pattern=r"the\s+(main|primary|central)\s+(site|datacenter|location)",
                reference_type=ReferenceType.SUPERLATIVE,
                priority=100
            ),
            ReferencePattern(
                pattern=r"(that|the)\s+(same|other)\s+(device|server|switch|router)",
                reference_type=ReferenceType.COMPARATIVE,
                priority=95
            ),
            ReferencePattern(
                pattern=r"(all|both|every)\s+(devices?|sites?|racks?|cables?)",
                reference_type=ReferenceType.QUANTIFIED,
                priority=90,
                multi_entity=True
            ),
            
            # Medium priority - relational patterns
            ReferencePattern(
                pattern=r"(connected|linked|attached)\s+(to\s+)?(it|that|this)",
                reference_type=ReferenceType.RELATIONAL,
                priority=80,
                context_required=True
            ),
            ReferencePattern(
                pattern=r"(its|their)\s+(interface|connection|port)",
                reference_type=ReferenceType.POSSESSIVE,
                priority=75,
                context_required=True
            ),
            ReferencePattern(
                pattern=r"the\s+(previous|last|next|first)\s+(one|device|site)",
                reference_type=ReferenceType.TEMPORAL,
                priority=70
            ),
            
            # Lower priority - basic patterns
            ReferencePattern(
                pattern=r"\b(it|that|this)\b",
                reference_type=ReferenceType.PRONOUN,
                priority=50
            ),
            ReferencePattern(
                pattern=r"the\s+(device|server|site|rack)",
                reference_type=ReferenceType.DEMONSTRATIVE,
                priority=45
            ),
            ReferencePattern(
                pattern=r"\b(them|those)\b",
                reference_type=ReferenceType.PRONOUN,
                priority=40,
                multi_entity=True
            ),
        ]
    
    def _initialize_relationship_patterns(self) -> Dict[str, str]:
        """Initialize NetBox-specific relationship patterns"""
        return {
            "connected_to": r"connected\s+to|linked\s+to|attached\s+to",
            "same_site": r"same\s+(site|location|datacenter)",
            "same_rack": r"same\s+(rack|cabinet|enclosure)",
            "parent_child": r"parent|child|container|contained",
            "power_related": r"powered\s+by|powers|feeds",
            "network_related": r"same\s+(vlan|network|subnet)"
        }
    
    def _normalize_reference(self, reference_text: str) -> str:
        """Normalize reference text for pattern matching"""
        # Convert to lowercase and clean whitespace
        normalized = re.sub(r'\s+', ' ', reference_text.lower().strip())
        
        # Remove common punctuation
        normalized = re.sub(r'[,\.\?\!]', '', normalized)
        
        # Standardize common variations
        replacements = {
            r'\bservers?\b': 'device',
            r'\bswitches?\b': 'device',
            r'\brouters?\b': 'device',
            r'\bdatacenters?\b': 'site',
            r'\blocations?\b': 'site',
            r'\bcabinets?\b': 'rack',
            r'\benclosures?\b': 'rack'
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized
    
    def _resolve_with_pattern(
        self, 
        pattern: ReferencePattern, 
        match: re.Match,
        reference_text: str, 
        context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Resolve reference using a specific pattern"""
        try:
            if pattern.reference_type == ReferenceType.PRONOUN:
                return self._resolve_pronoun_pattern(match, context)
            
            elif pattern.reference_type == ReferenceType.QUANTIFIED:
                return self._resolve_quantified_pattern(match, context)
            
            elif pattern.reference_type == ReferenceType.COMPARATIVE:
                return self._resolve_comparative_pattern(match, context)
            
            elif pattern.reference_type == ReferenceType.SUPERLATIVE:
                return self._resolve_superlative_pattern(match, context)
            
            elif pattern.reference_type == ReferenceType.RELATIONAL:
                return self._resolve_relational_pattern(match, context)
            
            elif pattern.reference_type == ReferenceType.POSSESSIVE:
                return self._resolve_possessive_pattern(match, context)
            
            elif pattern.reference_type == ReferenceType.TEMPORAL:
                return self._resolve_temporal_pattern(match, context)
            
            elif pattern.reference_type == ReferenceType.DEMONSTRATIVE:
                return self._resolve_demonstrative_pattern(match, context)
            
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error resolving with pattern {pattern.reference_type}: {e}")
            return None
    
    def _resolve_pronoun_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve basic pronoun patterns"""
        pronoun = match.group(0).lower()
        
        # Use EntityTracker for basic pronoun resolution
        entity_id = self.entity_tracker.resolve_reference(pronoun)
        
        if entity_id:
            return {
                "entity_ids": [entity_id],
                "confidence": 0.8,
                "reference_type": "pronoun",
                "resolution_method": "entity_tracker_fallback"
            }
        
        return None
    
    def _resolve_quantified_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve quantified patterns like 'all devices'"""
        full_match = match.group(0)
        
        # Extract quantifier and entity type
        quantifier_match = re.search(r'(all|both|every|some|many|few)', full_match)
        entity_match = re.search(r'(devices?|sites?|racks?|cables?|vlans?)', full_match)
        
        if quantifier_match and entity_match:
            quantifier = quantifier_match.group(1)
            entity_type = entity_match.group(1).rstrip('s')  # Remove plural
            
            entity_ids = self.resolve_quantified_reference(quantifier, entity_type, context)
            
            if entity_ids:
                return {
                    "entity_ids": entity_ids,
                    "confidence": 0.9,
                    "reference_type": "quantified",
                    "resolution_method": "quantified_resolution",
                    "quantifier": quantifier,
                    "entity_type": entity_type
                }
        
        return None
    
    def _resolve_superlative_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve superlative patterns like 'the main site'"""
        full_match = match.group(0)
        
        # Extract superlative and entity type
        superlative_match = re.search(r'(main|primary|central|principal)', full_match)
        entity_match = re.search(r'(site|datacenter|location|device|rack)', full_match)
        
        if superlative_match and entity_match:
            entity_type = entity_match.group(1)
            
            # Get entities of this type and find the "main" one
            try:
                entity_type_enum = EntityType(entity_type.lower())
                entities = self.entity_tracker.get_entities_by_type(entity_type_enum)
                
                # Sort by mention count and access count to find "primary" entity
                if entities:
                    primary_entity = max(entities, key=lambda x: (x["mention_count"], x["access_count"]))
                    
                    return {
                        "entity_ids": [primary_entity["entity_id"]],
                        "confidence": 0.85,
                        "reference_type": "superlative",
                        "resolution_method": "primary_entity_selection"
                    }
            except ValueError:
                pass
        
        return None
    
    def _resolve_comparative_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve comparative patterns like 'the other device'"""
        # This is a simplified implementation - could be enhanced with more sophisticated logic
        return None
    
    def _resolve_relational_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve relational patterns like 'connected to it'"""
        # Get the most recent entity as base for relationship
        recent_entities = self.entity_tracker.recent_mentions
        if recent_entities:
            base_entity_id = recent_entities[0]
            related_entities = self.resolve_relational_reference(base_entity_id, match.group(0))
            
            if related_entities:
                return {
                    "entity_ids": related_entities,
                    "confidence": 0.75,
                    "reference_type": "relational",
                    "resolution_method": "relationship_traversal",
                    "base_entity": base_entity_id
                }
        
        return None
    
    def _resolve_possessive_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve possessive patterns like 'its interface'"""
        # Find the owning entity and related component
        recent_entities = self.entity_tracker.recent_mentions
        if recent_entities:
            owner_entity_id = recent_entities[0]
            
            # Extract the possessed component type
            component_match = re.search(r'(interface|connection|port|cable)', match.group(0))
            if component_match:
                component_type = component_match.group(1)
                
                # Find related components
                related_entities = self.resolve_relational_reference(owner_entity_id, component_type)
                
                if related_entities:
                    return {
                        "entity_ids": related_entities,
                        "confidence": 0.8,
                        "reference_type": "possessive",
                        "resolution_method": "possessive_resolution",
                        "owner_entity": owner_entity_id,
                        "component_type": component_type
                    }
        
        return None
    
    def _resolve_temporal_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve temporal patterns like 'the previous device'"""
        # This is a placeholder - could be enhanced with conversation history analysis
        return None
    
    def _resolve_demonstrative_pattern(self, match: re.Match, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve demonstrative patterns like 'the device'"""
        # Extract entity type
        entity_match = re.search(r'(device|server|site|rack|cable)', match.group(0))
        if entity_match:
            entity_type = entity_match.group(1)
            
            # Find most recent entity of this type
            try:
                entity_type_enum = EntityType(entity_type.lower())
                entities = self.entity_tracker.get_entities_by_type(entity_type_enum)
                
                if entities:
                    # Return most recently accessed entity
                    recent_entity = max(entities, key=lambda x: x["last_accessed"])
                    
                    return {
                        "entity_ids": [recent_entity["entity_id"]],
                        "confidence": 0.7,
                        "reference_type": "demonstrative",
                        "resolution_method": "recent_entity_selection"
                    }
            except ValueError:
                pass
        
        return None
    
    def _fallback_resolution(self, reference_text: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Fallback to basic EntityTracker resolution"""
        entity_id = self.entity_tracker.resolve_reference(reference_text)
        
        if entity_id:
            return {
                "entity_ids": [entity_id],
                "confidence": 0.6,
                "reference_type": "fallback",
                "resolution_method": "entity_tracker_fallback"
            }
        
        return None
    
    def _validate_resolved_entities(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that resolved entities exist and are accessible"""
        # This would integrate with the real NetBox API for validation
        # For now, just return the result as-is
        return result
    
    def _apply_context_filter(self, entities: List[Dict[str, Any]], context_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply context-based filtering to entity list"""
        filtered_entities = []
        
        for entity in entities:
            include = True
            
            # Apply filters
            if "site" in context_filter:
                entity_site = self._extract_site_from_entity(entity["entity_id"])
                if entity_site != context_filter["site"]:
                    include = False
            
            if "rack" in context_filter:
                entity_rack = self._extract_rack_from_entity(entity["entity_id"])
                if entity_rack != context_filter["rack"]:
                    include = False
            
            if include:
                filtered_entities.append(entity)
        
        return filtered_entities
    
    def _extract_site_from_entity(self, entity_id: str) -> Optional[str]:
        """Extract site information from entity"""
        entity_context = self.entity_tracker.get_entity_context(entity_id)
        if entity_context:
            attributes = entity_context.get("attributes", {})
            return attributes.get("site")
        return None
    
    def _extract_rack_from_entity(self, entity_id: str) -> Optional[str]:
        """Extract rack information from entity"""
        entity_context = self.entity_tracker.get_entity_context(entity_id)
        if entity_context:
            attributes = entity_context.get("attributes", {})
            return attributes.get("rack")
        return None
    
    def get_resolution_statistics(self) -> Dict[str, Any]:
        """Get comprehensive resolution statistics"""
        total = self.resolution_stats["total_attempts"]
        successful = self.resolution_stats["successful_resolutions"]
        
        return {
            "total_attempts": total,
            "successful_resolutions": successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "multi_entity_resolutions": self.resolution_stats["multi_entity_resolutions"],
            "context_based_resolutions": self.resolution_stats["context_based_resolutions"],
            "pattern_usage": self.resolution_stats["pattern_match_counts"],
            "failure_analysis": self.resolution_stats["failure_reasons"],
            "most_used_patterns": sorted(
                self.resolution_stats["pattern_match_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }