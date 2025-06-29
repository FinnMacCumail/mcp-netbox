"""
NetBox MCP Prompts Module

This module contains MCP prompts that provide structured workflows and guidance
for complex NetBox operations. Prompts complement our 108+ tools by providing
intelligent orchestration and user guidance.
"""

from .workflows import *

__all__ = [
    'install_device_in_rack_prompt'
]