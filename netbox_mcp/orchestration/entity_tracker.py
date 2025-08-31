"""
EntityTracker for NetBox Entity Management Across Conversation Turns
Week 9-12: Real NetBox Integration & Advanced Conversation Management

This module provides sophisticated NetBox entity tracking, relationship management,
and context persistence for multi-turn conversations with intelligent reference resolution.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """NetBox entity types for tracking"""
    SITE = "site"
    DEVICE = "device"
    RACK = "rack"
    INTERFACE = "interface"
    CABLE = "cable"
    VLAN = "vlan"
    PREFIX = "prefix"
    VRF = "vrf"
    TENANT = "tenant"
    MODULE = "module"
    DEVICE_TYPE = "device_type"
    MANUFACTURER = "manufacturer"
    POWER_FEED = "power_feed"
    POWER_OUTLET = "power_outlet"
    CLUSTER = "cluster"
    VIRTUAL_MACHINE = "virtual_machine"


class EntityStatus(Enum):
    """Entity tracking status"""
    DISCOVERED = "discovered"          # Entity mentioned but not validated
    VALIDATED = "validated"            # Entity confirmed to exist in NetBox
    ACCESSED = "accessed"              # Entity data retrieved from NetBox
    MODIFIED = "modified"              # Entity data changed during conversation
    ERROR = "error"                    # Entity access or validation failed


@dataclass
class TrackedEntity:
    """Comprehensive NetBox entity tracking information"""
    entity_id: str                                    # Unique identifier
    entity_type: EntityType                           # NetBox entity type
    name: str                                         # Primary entity name
    status: EntityStatus                              # Current tracking status
    
    # Discovery and tracking metadata
    first_mentioned: datetime                         # When first mentioned
    last_accessed: datetime                           # Last interaction time
    mention_count: int = 0                           # Total mentions in conversation
    access_count: int = 0                            # NetBox API access count
    
    # Entity attributes and relationships
    attributes: Dict[str, Any] = field(default_factory=dict)  # Entity properties
    relationships: Dict[str, List[str]] = field(default_factory=dict)  # Related entities
    aliases: List[str] = field(default_factory=list)         # Alternative names/references
    
    # Conversation context
    context_tags: Set[str] = field(default_factory=set)      # Contextual tags
    conversation_role: Optional[str] = None                   # Role in current conversation
    
    # NetBox integration data
    netbox_data: Optional[Dict[str, Any]] = None             # Cached NetBox data
    data_freshness: Optional[datetime] = None                # When data was fetched
    validation_attempts: int = 0                             # Validation retry count
    
    def __post_init__(self):
        """Initialize derived fields"""
        if self.name not in self.aliases:
            self.aliases.append(self.name)
        
        # Set conversation role based on entity type
        if not self.conversation_role:
            self.conversation_role = self._determine_default_role()
    
    def _determine_default_role(self) -> str:
        """Determine default conversation role for entity type"""
        role_mapping = {
            EntityType.SITE: "location_context",
            EntityType.DEVICE: "infrastructure_focus",
            EntityType.RACK: "physical_context",
            EntityType.INTERFACE: "connectivity_focus",
            EntityType.CABLE: "connection_focus",
            EntityType.VLAN: "network_context",
            EntityType.PREFIX: "ip_context",
            EntityType.TENANT: "ownership_context"
        }
        return role_mapping.get(self.entity_type, "general_reference")
    
    def update_access(self, netbox_data: Optional[Dict[str, Any]] = None):
        """Update entity access tracking"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        
        if netbox_data:
            self.netbox_data = netbox_data
            self.data_freshness = datetime.now()
            self.status = EntityStatus.ACCESSED
    
    def add_relationship(self, relationship_type: str, related_entity_id: str):
        """Add relationship to another tracked entity"""
        if relationship_type not in self.relationships:
            self.relationships[relationship_type] = []
        
        if related_entity_id not in self.relationships[relationship_type]:
            self.relationships[relationship_type].append(related_entity_id)
    
    def is_data_fresh(self, max_age_minutes: int = 15) -> bool:
        """Check if cached NetBox data is still fresh"""
        if not self.data_freshness:
            return False
        
        age = datetime.now() - self.data_freshness
        return age.total_seconds() < (max_age_minutes * 60)


class EntityTracker:
    """
    Advanced NetBox entity tracker for conversation management.
    
    Provides sophisticated entity tracking, relationship management, and intelligent
    reference resolution for multi-turn conversations about NetBox infrastructure.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logging.getLogger(__name__)
        
        # Entity storage and indexing
        self.tracked_entities: Dict[str, TrackedEntity] = {}
        self.entity_name_index: Dict[str, str] = {}      # name -> entity_id
        self.alias_index: Dict[str, str] = {}            # alias -> entity_id
        self.type_index: Dict[EntityType, List[str]] = {}  # type -> [entity_ids]
        
        # Reference resolution context
        self.recent_mentions: List[str] = []             # Recently mentioned entity_ids
        self.context_stack: List[str] = []               # Contextual entity stack
        self.conversation_focus: Optional[str] = None    # Primary focus entity
        
        # Relationship mapping
        self.entity_relationships: Dict[str, Set[str]] = {}  # entity_id -> {related_ids}
        
        # Advanced reference resolver (lazy-loaded to avoid circular imports)
        self._reference_resolver = None
        
        # Performance tracking
        self.tracking_stats = {
            "entities_tracked": 0,
            "validation_attempts": 0,
            "successful_resolutions": 0,
            "failed_resolutions": 0,
            "relationship_discoveries": 0
        }
    
    def track_entity(
        self, 
        entity_type: EntityType, 
        entity_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        context_tags: Optional[Set[str]] = None
    ) -> str:
        """
        Track a NetBox entity mentioned in conversation.
        
        Args:
            entity_type: Type of NetBox entity
            entity_name: Name or identifier of the entity
            attributes: Additional entity attributes
            context_tags: Contextual tags for this mention
            
        Returns:
            Unique entity_id for tracking
        """
        entity_id = self._generate_entity_id(entity_type, entity_name)
        
        if entity_id in self.tracked_entities:
            # Update existing entity
            entity = self.tracked_entities[entity_id]
            entity.mention_count += 1
            entity.last_accessed = datetime.now()
            
            if attributes:
                entity.attributes.update(attributes)
            if context_tags:
                entity.context_tags.update(context_tags)
        else:
            # Create new tracked entity
            entity = TrackedEntity(
                entity_id=entity_id,
                entity_type=entity_type,
                name=entity_name,
                status=EntityStatus.DISCOVERED,
                first_mentioned=datetime.now(),
                last_accessed=datetime.now(),
                mention_count=1,
                attributes=attributes or {},
                context_tags=context_tags or set()
            )
            
            self.tracked_entities[entity_id] = entity
            self._index_entity(entity)
            self.tracking_stats["entities_tracked"] += 1
        
        # Update mention tracking
        self._update_mention_context(entity_id)
        
        self.logger.info(f"Tracked entity: {entity_id} (mentions: {entity.mention_count})")
        return entity_id
    
    @property
    def reference_resolver(self):
        """Lazy-load the reference resolver to avoid circular imports"""
        if self._reference_resolver is None:
            from .reference_resolver import ReferenceResolver
            self._reference_resolver = ReferenceResolver(self)
        return self._reference_resolver
    
    def resolve_reference(self, reference: str, context_hint: Optional[str] = None, _recursion_depth: int = 0) -> Optional[str]:
        """
        Resolve entity references including pronouns, partial names, and contextual references.
        
        Args:
            reference: Reference text to resolve
            context_hint: Optional context hint for resolution
            _recursion_depth: Internal recursion protection
            
        Returns:
            entity_id if resolved, None otherwise
        """
        # Prevent infinite recursion
        if _recursion_depth > 3:
            self.logger.warning(f"Recursion limit reached resolving '{reference}'")
            return None
            
        reference_lower = reference.lower().strip()
        
        try:
            # Handle ordinal references like "the first site", "the second device"
            if "first" in reference_lower and self.tracked_entities:
                matching_entities = [eid for eid, entity in self.tracked_entities.items() 
                                   if any(word in reference_lower for word in entity.entity_type.value.lower().split())]
                if matching_entities:
                    return matching_entities[0]  # Return first matching entity
            
            if "second" in reference_lower and self.tracked_entities:
                matching_entities = [eid for eid, entity in self.tracked_entities.items() 
                                   if any(word in reference_lower for word in entity.entity_type.value.lower().split())]
                if len(matching_entities) > 1:
                    return matching_entities[1]  # Return second matching entity
            # Direct name/alias lookup (fast path)
            if reference_lower in self.alias_index:
                entity_id = self.alias_index[reference_lower]
                self.tracking_stats["successful_resolutions"] += 1
                return entity_id
            
            # Exact name lookup  
            if reference_lower in self.entity_name_index:
                entity_id = self.entity_name_index[reference_lower]
                self.tracking_stats["successful_resolutions"] += 1
                return entity_id
            
            # Use advanced ReferenceResolver for complex patterns (with recursion protection)
            if _recursion_depth < 2:  # Limit recursive calls
                advanced_result = self.reference_resolver.resolve_reference(
                    reference_text=reference,
                    conversation_context={"context_hint": context_hint} if context_hint else None
                )
            else:
                advanced_result = None
            
            if advanced_result and advanced_result.get("entity_ids"):
                # Return first entity_id from advanced resolution
                entity_id = advanced_result["entity_ids"][0]
                self.tracking_stats["successful_resolutions"] += 1
                return entity_id
            
            # Fallback to basic resolution methods
            # Pronoun resolution
            pronouns = ["it", "that", "this", "them", "those"]
            if reference_lower in pronouns:
                resolved_id = self._resolve_pronoun(reference_lower, context_hint)
                if resolved_id:
                    self.tracking_stats["successful_resolutions"] += 1
                    return resolved_id
            
            # Partial name matching
            partial_match = self._resolve_partial_name(reference_lower)
            if partial_match:
                self.tracking_stats["successful_resolutions"] += 1
                return partial_match
            
            # Contextual resolution using conversation focus
            contextual_match = self._resolve_contextual_reference(reference_lower, context_hint)
            if contextual_match:
                self.tracking_stats["successful_resolutions"] += 1
                return contextual_match
            
            self.tracking_stats["failed_resolutions"] += 1
            return None
            
        except Exception as e:
            self.logger.error(f"Error resolving reference '{reference}': {e}")
            self.tracking_stats["failed_resolutions"] += 1
            return None
    
    def add_entity_relationship(self, entity_id: str, related_entity_id: str, relationship_type: str):
        """Add relationship between two tracked entities"""
        if entity_id in self.tracked_entities and related_entity_id in self.tracked_entities:
            # Add bidirectional relationship
            entity = self.tracked_entities[entity_id]
            related_entity = self.tracked_entities[related_entity_id]
            
            entity.add_relationship(relationship_type, related_entity_id)
            related_entity.add_relationship(f"inverse_{relationship_type}", entity_id)
            
            # Update relationship index
            if entity_id not in self.entity_relationships:
                self.entity_relationships[entity_id] = set()
            if related_entity_id not in self.entity_relationships:
                self.entity_relationships[related_entity_id] = set()
            
            self.entity_relationships[entity_id].add(related_entity_id)
            self.entity_relationships[related_entity_id].add(entity_id)
            
            self.tracking_stats["relationship_discoveries"] += 1
            self.logger.info(f"Added relationship: {entity_id} --{relationship_type}--> {related_entity_id}")
    
    def get_entity_context(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive context for an entity"""
        if entity_id not in self.tracked_entities:
            return None
        
        entity = self.tracked_entities[entity_id]
        related_entities = []
        
        # Get related entity information
        if entity_id in self.entity_relationships:
            for related_id in self.entity_relationships[entity_id]:
                if related_id in self.tracked_entities:
                    related_entity = self.tracked_entities[related_id]
                    related_entities.append({
                        "id": related_id,
                        "type": related_entity.entity_type.value,
                        "name": related_entity.name
                    })
        
        return {
            "entity_id": entity_id,
            "type": entity.entity_type.value,
            "name": entity.name,
            "status": entity.status.value,
            "mention_count": entity.mention_count,
            "access_count": entity.access_count,
            "first_mentioned": entity.first_mentioned.isoformat(),
            "last_accessed": entity.last_accessed.isoformat(),
            "attributes": entity.attributes,
            "relationships": entity.relationships,
            "aliases": entity.aliases,
            "context_tags": list(entity.context_tags),
            "conversation_role": entity.conversation_role,
            "related_entities": related_entities,
            "data_freshness": entity.data_freshness.isoformat() if entity.data_freshness else None,
            "is_data_fresh": entity.is_data_fresh()
        }
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Dict[str, Any]]:
        """Get all tracked entities of a specific type"""
        entities = []
        
        for entity_id, entity in self.tracked_entities.items():
            if entity.entity_type == entity_type:
                entities.append(self.get_entity_context(entity_id))
        
        # Sort by mention count and recency
        entities.sort(key=lambda x: (x["mention_count"], x["last_accessed"]), reverse=True)
        return entities
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of tracked entities and conversation context"""
        entity_type_counts = {}
        total_mentions = 0
        
        for entity in self.tracked_entities.values():
            entity_type = entity.entity_type.value
            if entity_type not in entity_type_counts:
                entity_type_counts[entity_type] = 0
            entity_type_counts[entity_type] += 1
            total_mentions += entity.mention_count
        
        return {
            "session_id": self.session_id,
            "total_entities": len(self.tracked_entities),
            "entity_type_distribution": entity_type_counts,
            "total_mentions": total_mentions,
            "conversation_focus": self.conversation_focus,
            "recent_entities": self.recent_mentions[:5],
            "tracking_stats": self.tracking_stats,
            "relationship_count": len(self.entity_relationships)
        }
    
    def update_conversation_focus(self, entity_id: str):
        """Update the primary conversation focus entity"""
        if entity_id in self.tracked_entities:
            self.conversation_focus = entity_id
            self.tracked_entities[entity_id].conversation_role = "primary_focus"
            self.logger.info(f"Updated conversation focus to: {entity_id}")
    
    def validate_entity_with_netbox(self, entity_id: str, netbox_data: Dict[str, Any]) -> bool:
        """Validate and update entity with NetBox data"""
        if entity_id not in self.tracked_entities:
            return False
        
        entity = self.tracked_entities[entity_id]
        entity.validation_attempts += 1
        
        try:
            if netbox_data.get("success", False):
                entity.update_access(netbox_data)
                entity.status = EntityStatus.VALIDATED
                self.logger.info(f"Entity validated: {entity_id}")
                return True
            else:
                entity.status = EntityStatus.ERROR
                self.logger.warning(f"Entity validation failed: {entity_id}")
                return False
                
        except Exception as e:
            entity.status = EntityStatus.ERROR
            self.logger.error(f"Error validating entity {entity_id}: {e}")
            return False
    
    def _generate_entity_id(self, entity_type: EntityType, entity_name: str) -> str:
        """Generate unique entity identifier"""
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', entity_name.lower())
        return f"{entity_type.value}:{clean_name}"
    
    def _index_entity(self, entity: TrackedEntity):
        """Add entity to search indexes"""
        # Name index
        self.entity_name_index[entity.name.lower()] = entity.entity_id
        
        # Alias index
        for alias in entity.aliases:
            self.alias_index[alias.lower()] = entity.entity_id
        
        # Type index
        if entity.entity_type not in self.type_index:
            self.type_index[entity.entity_type] = []
        
        if entity.entity_id not in self.type_index[entity.entity_type]:
            self.type_index[entity.entity_type].append(entity.entity_id)
    
    def _update_mention_context(self, entity_id: str):
        """Update mention context for reference resolution"""
        # Remove from current position if present
        if entity_id in self.recent_mentions:
            self.recent_mentions.remove(entity_id)
        
        # Add to front of recent mentions
        self.recent_mentions.insert(0, entity_id)
        
        # Keep only last 10 mentions
        self.recent_mentions = self.recent_mentions[:10]
        
        # Update context stack for pronoun resolution
        if entity_id not in self.context_stack:
            self.context_stack.append(entity_id)
            self.context_stack = self.context_stack[-5:]  # Keep last 5 for context
    
    def _resolve_pronoun(self, pronoun: str, context_hint: Optional[str] = None) -> Optional[str]:
        """Resolve pronouns to specific entities"""
        if not self.recent_mentions:
            return None
        
        # Simple pronoun resolution - use most recent mention
        if pronoun in ["it", "that", "this"]:
            return self.recent_mentions[0]
        
        # Plural pronouns
        elif pronoun in ["them", "those"]:
            # Return the most recent entity that could be plural (e.g., devices, sites)
            for entity_id in self.recent_mentions:
                entity = self.tracked_entities[entity_id]
                if entity.entity_type in [EntityType.DEVICE, EntityType.SITE, EntityType.RACK]:
                    return entity_id
        
        return None
    
    def _resolve_partial_name(self, partial_name: str) -> Optional[str]:
        """Resolve partial entity names"""
        best_match = None
        best_score = 0
        
        for entity_id, entity in self.tracked_entities.items():
            # Check entity name
            if partial_name in entity.name.lower():
                score = len(partial_name) / len(entity.name)
                if score > best_score:
                    best_score = score
                    best_match = entity_id
            
            # Check aliases
            for alias in entity.aliases:
                if partial_name in alias.lower():
                    score = len(partial_name) / len(alias)
                    if score > best_score:
                        best_score = score
                        best_match = entity_id
        
        # Return match if confidence is high enough
        return best_match if best_score > 0.3 else None
    
    def _resolve_contextual_reference(self, reference: str, context_hint: Optional[str] = None) -> Optional[str]:
        """Resolve references using conversation context"""
        # Use conversation focus as fallback
        if self.conversation_focus:
            focus_entity = self.tracked_entities[self.conversation_focus]
            if any(word in reference for word in ["main", "primary", "current", "focus"]):
                return self.conversation_focus
        
        # Use context hint if provided
        if context_hint:
            for entity_id, entity in self.tracked_entities.items():
                if (context_hint.lower() in entity.name.lower() or 
                    any(tag in context_hint.lower() for tag in entity.context_tags)):
                    return entity_id
        
        return None
    
    def add_entity_alias(self, entity_id: str, alias: str):
        """Add an alias to an existing entity"""
        if entity_id in self.tracked_entities:
            entity = self.tracked_entities[entity_id]
            if alias not in entity.aliases:
                entity.aliases.append(alias)
                self.alias_index[alias.lower()] = entity_id
                self.logger.info(f"Added alias '{alias}' to entity {entity_id}")
    
    def cleanup_stale_entities(self, max_age_hours: int = 24):
        """Remove entities that haven't been mentioned recently"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        stale_entities = []
        
        for entity_id, entity in self.tracked_entities.items():
            if entity.last_accessed < cutoff_time and entity.mention_count < 2:
                stale_entities.append(entity_id)
        
        for entity_id in stale_entities:
            self._remove_entity(entity_id)
        
        if stale_entities:
            self.logger.info(f"Cleaned up {len(stale_entities)} stale entities")
    
    def _remove_entity(self, entity_id: str):
        """Remove entity from all indexes"""
        if entity_id in self.tracked_entities:
            entity = self.tracked_entities[entity_id]
            
            # Remove from indexes
            self.entity_name_index.pop(entity.name.lower(), None)
            for alias in entity.aliases:
                self.alias_index.pop(alias.lower(), None)
            
            if entity.entity_type in self.type_index:
                if entity_id in self.type_index[entity.entity_type]:
                    self.type_index[entity.entity_type].remove(entity_id)
            
            # Remove from context
            if entity_id in self.recent_mentions:
                self.recent_mentions.remove(entity_id)
            if entity_id in self.context_stack:
                self.context_stack.remove(entity_id)
            
            # Remove relationships
            if entity_id in self.entity_relationships:
                related_ids = self.entity_relationships[entity_id].copy()
                for related_id in related_ids:
                    if related_id in self.entity_relationships:
                        self.entity_relationships[related_id].discard(entity_id)
                del self.entity_relationships[entity_id]
            
            del self.tracked_entities[entity_id]