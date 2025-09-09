#!/usr/bin/env python3
"""
NetBox Extras Journal Entry Management Tools

High-level tools for managing NetBox journal entries with enterprise-grade functionality.
Journal entries provide audit trails and activity logging for NetBox objects.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)




@mcp_tool(category="extras")
def netbox_list_all_journal_entries(
    client: NetBoxClient,
    assigned_object_type: Optional[str] = None,
    assigned_object_id: Optional[int] = None,
    kind: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get a summarized list of journal entries with optional filtering.
    
    This tool provides bulk journal entry discovery across the NetBox infrastructure,
    enabling efficient activity monitoring, audit trail analysis, and operational
    history tracking. Essential for compliance auditing and change management.
    
    Args:
        client: NetBoxClient instance (injected)
        assigned_object_type: Filter by object content type (e.g., "dcim.device")
        assigned_object_id: Filter by specific object ID
        kind: Filter by journal entry kind (info, success, warning, danger)
        limit: Maximum number of entries to return (default: 100)
    
    Returns:
        Dict containing summary list of journal entries with filtering metadata
    """
    
    # Build filter parameters
    filter_params = {}
    
    if assigned_object_type:
        filter_params["assigned_object_type"] = assigned_object_type
        
    if assigned_object_id:
        filter_params["assigned_object_id"] = assigned_object_id
        
    if kind:
        valid_kinds = ["info", "success", "warning", "danger"]
        if kind not in valid_kinds:
            raise ValueError(f"kind must be one of {valid_kinds}")
        filter_params["kind"] = kind
    
    try:
        # Get journal entries with applied filters
        journal_entries = list(client.extras.journal_entries.filter(**filter_params)[:limit])
        
        # Process entries with defensive dict/object handling
        entries_summary = []
        for entry in journal_entries:
            entry_id = entry.get('id') if isinstance(entry, dict) else entry.id
            entry_kind = entry.get('kind') if isinstance(entry, dict) else entry.kind
            entry_comments = entry.get('comments') if isinstance(entry, dict) else entry.comments
            entry_created = entry.get('created') if isinstance(entry, dict) else getattr(entry, 'created', None)
            
            # Handle assigned object information
            assigned_object = entry.get('assigned_object') if isinstance(entry, dict) else getattr(entry, 'assigned_object', None)
            assigned_object_type = entry.get('assigned_object_type') if isinstance(entry, dict) else getattr(entry, 'assigned_object_type', None)
            
            # Extract object type name safely
            if isinstance(assigned_object_type, dict):
                object_type_name = assigned_object_type.get('model', 'N/A')
            else:
                object_type_name = str(assigned_object_type) if assigned_object_type else 'N/A'
            
            # Extract assigned object display name safely
            if isinstance(assigned_object, dict):
                object_display = assigned_object.get('display', f"ID {entry.get('assigned_object_id', 'N/A')}")
            else:
                object_display = str(assigned_object) if assigned_object else f"ID {entry.get('assigned_object_id') if isinstance(entry, dict) else getattr(entry, 'assigned_object_id', 'N/A')}"
            
            entries_summary.append({
                "id": entry_id,
                "kind": entry_kind,
                "assigned_object_type": object_type_name,
                "assigned_object": object_display,
                "comments_preview": (entry_comments[:100] + "...") if entry_comments and len(entry_comments) > 100 else entry_comments,
                "created": str(entry_created) if entry_created else None
            })
            
    except Exception as e:
        raise ValueError(f"Failed to retrieve journal entries: {e}")
    
    return {
        "success": True,
        "message": f"Found {len(entries_summary)} journal entries.",
        "total_entries": len(entries_summary),
        "applied_filters": {
            "assigned_object_type": assigned_object_type,
            "assigned_object_id": assigned_object_id,
            "kind": kind,
            "limit": limit
        },
        "data": entries_summary
    }