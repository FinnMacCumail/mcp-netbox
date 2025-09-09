#!/usr/bin/env python3
"""
DCIM Module Type Profiles Management Tools - Read-Only Operations

Enterprise-grade tools for inspecting NetBox module type profiles and structured attribute validation.
Provides read-only access to profile definitions with comprehensive discovery capabilities.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient
from ...exceptions import NetBoxNotFoundError, NetBoxValidationError

logger = logging.getLogger(__name__)

@mcp_tool(category="dcim")
def netbox_list_all_module_type_profiles(
    client: NetBoxClient,
    limit: int = 100
) -> Dict[str, Any]:
    """
    List all module type profiles with comprehensive schema analysis.
    
    This discovery tool provides bulk profile exploration with schema statistics
    and field analysis. Essential for profile catalog management and standardized
    module attribute validation across the NetBox infrastructure.
    
    Args:
        client: NetBoxClient instance (injected)
        limit: Maximum number of profiles to return (default: 100)
        
    Returns:
        Comprehensive list of profiles with schema details and statistics
        
    Example:
        netbox_list_all_module_type_profiles()
    """
    
    logger.info(f"Listing Module Type Profiles (limit: {limit})")
    
    try:
        # Fetch all module type profiles
        profiles_raw = list(client.dcim.module_type_profiles.all()[:limit])
        
        # Process profiles with defensive dict/object handling
        profiles = []
        profile_stats = {
            "total_profiles": 0,
            "total_fields": 0,
            "field_types": {},
            "profiles_with_required_fields": 0
        }
        
        for profile in profiles_raw:
            # Apply defensive dict/object handling
            profile_id = profile.get('id') if isinstance(profile, dict) else profile.id
            name = profile.get('name') if isinstance(profile, dict) else profile.name
            description = profile.get('description') if isinstance(profile, dict) else getattr(profile, 'description', '')
            schema = profile.get('schema') if isinstance(profile, dict) else getattr(profile, 'schema', {})
            
            # Analyze schema structure
            field_count = 0
            field_types = {}
            required_fields = []
            
            if isinstance(schema, dict) and "properties" in schema:
                properties = schema["properties"]
                field_count = len(properties)
                
                for field_name, field_def in properties.items():
                    if isinstance(field_def, dict) and "type" in field_def:
                        field_type = field_def["type"]
                        field_types[field_type] = field_types.get(field_type, 0) + 1
                        profile_stats["field_types"][field_type] = profile_stats["field_types"].get(field_type, 0) + 1
                
                required_fields = schema.get("required", [])
                if required_fields:
                    profile_stats["profiles_with_required_fields"] += 1
            
            profile_stats["total_fields"] += field_count
            
            profiles.append({
                "id": profile_id,
                "name": name,
                "description": description,
                "field_count": field_count,
                "field_types": field_types,
                "required_fields": required_fields,
                "required_field_count": len(required_fields)
            })
        
        profile_stats["total_profiles"] = len(profiles)
        
        logger.info(f"Successfully retrieved {len(profiles)} module type profiles")
        
        return {
            "success": True,
            "count": len(profiles),
            "profiles": sorted(profiles, key=lambda x: x["name"]),
            "summary": profile_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to list module type profiles: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }



@mcp_tool(category="dcim")
def netbox_get_module_type_profile_info(
    client: NetBoxClient,
    profile_name: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific module type profile.
    
    This inspection tool provides comprehensive profile details including
    complete schema definition, field specifications, validation rules,
    and usage statistics. Essential for profile verification and module
    type planning with structured attribute validation.
    
    Args:
        client: NetBoxClient instance (injected)
        profile_name: Profile name to inspect
        
    Returns:
        Detailed profile information with schema analysis or error details
        
    Example:
        netbox_get_module_type_profile_info("Memory")
    """
    
    if not profile_name or not profile_name.strip():
        raise ValidationError("Profile name cannot be empty")
    
    logger.info(f"Getting Module Type Profile info for '{profile_name}'")
    
    try:
        # Find profile by name
        profiles = client.dcim.module_type_profiles.filter(name=profile_name)
        if not profiles:
            raise NotFoundError(f"Module Type Profile '{profile_name}' not found")
        
        profile = profiles[0]
        
        # Apply defensive dict/object handling
        profile_id = profile.get('id') if isinstance(profile, dict) else profile.id
        name = profile.get('name') if isinstance(profile, dict) else profile.name
        description = profile.get('description') if isinstance(profile, dict) else getattr(profile, 'description', '')
        schema = profile.get('schema') if isinstance(profile, dict) else getattr(profile, 'schema', {})
        
        # Analyze schema in detail
        schema_analysis = {
            "field_count": 0,
            "required_fields": [],
            "optional_fields": [],
            "field_details": {},
            "validation_rules": {
                "has_enums": False,
                "enum_fields": [],
                "type_distribution": {}
            }
        }
        
        if isinstance(schema, dict) and "properties" in schema:
            properties = schema["properties"]
            required_fields = schema.get("required", [])
            
            schema_analysis["field_count"] = len(properties)
            schema_analysis["required_fields"] = required_fields
            schema_analysis["optional_fields"] = [f for f in properties.keys() if f not in required_fields]
            
            for field_name, field_def in properties.items():
                if isinstance(field_def, dict):
                    field_type = field_def.get("type", "unknown")
                    field_title = field_def.get("title", field_name)
                    field_description = field_def.get("description", "")
                    field_enum = field_def.get("enum", [])
                    
                    # Track type distribution
                    schema_analysis["validation_rules"]["type_distribution"][field_type] = \
                        schema_analysis["validation_rules"]["type_distribution"].get(field_type, 0) + 1
                    
                    # Track enum usage
                    if field_enum:
                        schema_analysis["validation_rules"]["has_enums"] = True
                        schema_analysis["validation_rules"]["enum_fields"].append(field_name)
                    
                    schema_analysis["field_details"][field_name] = {
                        "type": field_type,
                        "title": field_title,
                        "description": field_description,
                        "required": field_name in required_fields,
                        "enum_values": field_enum,
                        "has_enum": bool(field_enum)
                    }
        
        # Count module types using this profile
        module_types_using_profile = list(client.dcim.module_types.filter(profile_id=profile_id))
        usage_count = len(module_types_using_profile)
        
        return {
            "success": True,
            "profile": {
                "id": profile_id,
                "name": name,
                "description": description,
                "schema": schema,
                "schema_analysis": schema_analysis,
                "usage": {
                    "module_types_count": usage_count,
                    "module_types_using": [
                        {
                            "model": mt.get('model') if isinstance(mt, dict) else mt.model,
                            "id": mt.get('id') if isinstance(mt, dict) else mt.id
                        }
                        for mt in module_types_using_profile[:10]  # Show first 10
                    ]
                }
            }
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to get module type profile info for '{profile_name}': {e}")
        raise ValidationError(f"Failed to retrieve profile information: {e}")

