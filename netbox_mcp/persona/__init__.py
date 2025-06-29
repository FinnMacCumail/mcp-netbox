"""
NetBox MCP Persona Module

Provides personality and context for interactive workflows through our mascotte Bridget.
Creates clear branding and user guidance for NetBox MCP prompt interactions.
"""

from .bridget import *

__all__ = [
    'get_bridget_introduction',
    'get_bridget_workflow_header', 
    'get_bridget_step_transition',
    'get_bridget_completion_message',
    'BridgetPersona'
]