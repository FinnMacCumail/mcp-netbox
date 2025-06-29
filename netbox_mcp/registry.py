#!/usr/bin/env python3
"""
MCP Tool Registry and Decorator System

Provides the core infrastructure for self-describing MCP tools.
The @mcp_tool decorator automatically inspects and registers functions,
making them discoverable and executable via the dynamic API endpoints.
"""

import inspect
import logging
from functools import wraps
from typing import Dict, List, Any, Callable, Optional, get_type_hints, Union

logger = logging.getLogger(__name__)

# Global tool registry - contains all registered MCP tools
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

# Global prompt registry - contains all registered MCP prompts
PROMPT_REGISTRY: Dict[str, Dict[str, Any]] = {}


def extract_parameter_info(func: Callable) -> List[Dict[str, Any]]:
    """
    Extract detailed parameter information from a function.
    
    Args:
        func: The function to inspect
        
    Returns:
        List of parameter dictionaries with name, type, required, and default info
    """
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)
    parameters = []
    
    for param_name, param in signature.parameters.items():
        # Skip 'self' parameter for methods
        if param_name == 'self':
            continue
            
        param_info = {
            "name": param_name,
            "required": param.default == inspect.Parameter.empty,
            "default": None if param.default == inspect.Parameter.empty else param.default
        }
        
        # Get type information
        if param_name in type_hints:
            param_type = type_hints[param_name]
            # Handle Optional types
            if hasattr(param_type, '__origin__') and param_type.__origin__ is Union:
                # This is likely Optional[T] which is Union[T, None]
                args = param_type.__args__
                if len(args) == 2 and type(None) in args:
                    param_info["type"] = str(args[0] if args[1] is type(None) else args[1])
                    param_info["required"] = False
                else:
                    param_info["type"] = str(param_type)
            else:
                param_info["type"] = str(param_type).replace("typing.", "")
        else:
            # Fallback to annotation if available
            if param.annotation != inspect.Parameter.empty:
                param_info["type"] = str(param.annotation)
            else:
                param_info["type"] = "Any"
        
        parameters.append(param_info)
    
    return parameters


def extract_return_info(func: Callable) -> Dict[str, Any]:
    """
    Extract return type information from a function.
    
    Args:
        func: The function to inspect
        
    Returns:
        Dictionary with return type information
    """
    type_hints = get_type_hints(func)
    
    if 'return' in type_hints:
        return_type = type_hints['return']
        return {
            "type": str(return_type).replace("typing.", ""),
            "description": "Function return value"
        }
    
    # Check for annotation fallback
    signature = inspect.signature(func)
    if signature.return_annotation != inspect.Parameter.empty:
        return {
            "type": str(signature.return_annotation),
            "description": "Function return value"
        }
    
    return {
        "type": "Any",
        "description": "Function return value"
    }


def parse_docstring(docstring: str) -> Dict[str, str]:
    """
    Parse a function's docstring to extract structured information.
    
    Args:
        docstring: The raw docstring
        
    Returns:
        Dictionary with parsed sections (description, args, returns, example)
    """
    if not docstring:
        return {"description": "No description available"}
    
    sections = {
        "description": "",
        "args": "",
        "returns": "",
        "example": ""
    }
    
    lines = docstring.strip().split('\n')
    current_section = "description"
    section_content = []
    
    for line in lines:
        line = line.strip()
        
        # Check for section headers
        if line.lower().startswith(('args:', 'arguments:', 'parameters:')):
            sections[current_section] = '\n'.join(section_content).strip()
            current_section = "args"
            section_content = []
        elif line.lower().startswith(('returns:', 'return:')):
            sections[current_section] = '\n'.join(section_content).strip()
            current_section = "returns"
            section_content = []
        elif line.lower().startswith(('example:', 'examples:')):
            sections[current_section] = '\n'.join(section_content).strip()
            current_section = "example"
            section_content = []
        else:
            section_content.append(line)
    
    # Don't forget the last section
    sections[current_section] = '\n'.join(section_content).strip()
    
    return sections


def mcp_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general"
) -> Callable:
    """
    Decorator to register a function as an MCP tool.
    
    This decorator automatically inspects the function and adds it to the
    global TOOL_REGISTRY with complete metadata for discovery and execution.
    
    Args:
        name: Override the tool name (defaults to function name)
        description: Override the description (defaults to first line of docstring)
        category: Tool category for organization (default: "general")
        
    Returns:
        The decorated function (unchanged functionality)
        
    Example:
        @mcp_tool(category="ipam")
        def netbox_create_ip_address(address: str, confirm: bool = False) -> Dict[str, Any]:
            '''Create a new IP address in NetBox.'''
            # Implementation here
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Determine tool name
        tool_name = name or func.__name__
        
        # Extract function metadata
        docstring_info = parse_docstring(func.__doc__ or "")
        parameters = extract_parameter_info(func)
        return_info = extract_return_info(func)
        
        # Build tool metadata
        tool_metadata = {
            "name": tool_name,
            "function": func,  # Keep reference to actual function
            "category": category,
            "description": description or docstring_info.get("description", f"Execute {tool_name}"),
            "docstring": {
                "full": func.__doc__ or "",
                "parsed": docstring_info
            },
            "parameters": parameters,
            "return_info": return_info,
            "module": func.__module__,
            "source_file": inspect.getfile(func) if hasattr(func, '__code__') else "unknown"
        }
        
        # Register the tool
        TOOL_REGISTRY[tool_name] = tool_metadata
        
        logger.info(f"Registered MCP tool: {tool_name} (category: {category})")
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def mcp_prompt(name: str, description: str) -> Callable:
    """
    Decorator for registering MCP prompts.
    
    Args:
        name: Unique prompt name
        description: Brief description of the prompt's purpose
        
    Returns:
        The decorated function (unchanged functionality)
        
    Example:
        @mcp_prompt(
            name="install_device_in_rack",
            description="Interactive workflow for installing a new device"
        )
        async def install_device_prompt() -> Dict[str, Any]:
            # Implementation here
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Get function signature and docstring
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or "No description available"
        
        # Register the prompt
        PROMPT_REGISTRY[name] = {
            "name": name,
            "description": description,
            "function": func,
            "signature": sig,
            "docstring": doc,
            "module": func.__module__,
            "source_file": inspect.getfile(func) if hasattr(func, '__code__') else "unknown"
        }
        
        logger.info(f"Registered MCP prompt: {name}")
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_tool_registry() -> Dict[str, Dict[str, Any]]:
    """
    Get the complete tool registry.
    
    Returns:
        Dictionary mapping tool names to their metadata
    """
    return TOOL_REGISTRY.copy()


def get_tool_by_name(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific tool by name.
    
    Args:
        tool_name: Name of the tool to retrieve
        
    Returns:
        Tool metadata dictionary or None if not found
    """
    return TOOL_REGISTRY.get(tool_name)


def get_tools_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all tools in a specific category.
    
    Args:
        category: Category to filter by
        
    Returns:
        Dictionary of tools in the specified category
    """
    return {
        name: metadata 
        for name, metadata in TOOL_REGISTRY.items() 
        if metadata.get("category") == category
    }


def get_registry_stats() -> Dict[str, Any]:
    """
    Get statistics about the tool registry.
    
    Returns:
        Dictionary with registry statistics
    """
    categories = {}
    total_tools = len(TOOL_REGISTRY)
    
    for tool_name, metadata in TOOL_REGISTRY.items():
        category = metadata.get("category", "unknown")
        categories[category] = categories.get(category, 0) + 1
    
    return {
        "total_tools": total_tools,
        "categories": categories,
        "tool_names": list(TOOL_REGISTRY.keys())
    }


def serialize_tool_for_api(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Serialize a tool's metadata for API consumption (excludes function reference).
    
    Args:
        tool_name: Name of the tool to serialize
        
    Returns:
        Serialized tool metadata without the function reference
    """
    tool = get_tool_by_name(tool_name)
    if not tool:
        return None
    
    # Create a copy without the function reference
    serialized = tool.copy()
    serialized.pop("function", None)  # Remove function reference for JSON serialization
    
    return serialized


def serialize_registry_for_api() -> List[Dict[str, Any]]:
    """
    Serialize the entire registry for API consumption.
    
    Returns:
        List of tool metadata dictionaries (without function references)
    """
    return [
        serialize_tool_for_api(tool_name) 
        for tool_name in TOOL_REGISTRY.keys()
    ]


def get_prompt_registry() -> Dict[str, Dict[str, Any]]:
    """
    Get the complete prompt registry.
    
    Returns:
        Dictionary mapping prompt names to their metadata
    """
    return PROMPT_REGISTRY.copy()


def get_prompt_by_name(prompt_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific prompt by name.
    
    Args:
        prompt_name: Name of the prompt to retrieve
        
    Returns:
        Prompt metadata dictionary or None if not found
    """
    return PROMPT_REGISTRY.get(prompt_name)


def serialize_prompt_for_api(prompt_name: str) -> Optional[Dict[str, Any]]:
    """
    Serialize a prompt's metadata for API consumption (excludes function reference).
    
    Args:
        prompt_name: Name of the prompt to serialize
        
    Returns:
        Serialized prompt metadata without the function reference
    """
    prompt = get_prompt_by_name(prompt_name)
    if not prompt:
        return None
    
    # Create a copy without the function reference
    serialized = prompt.copy()
    serialized.pop("function", None)  # Remove function reference for JSON serialization
    serialized.pop("signature", None)  # Remove signature object
    
    return serialized


def serialize_prompts_for_api() -> List[Dict[str, Any]]:
    """
    Serialize the entire prompt registry for API consumption.
    
    Returns:
        List of prompt metadata dictionaries (without function references)
    """
    return [
        serialize_prompt_for_api(prompt_name) 
        for prompt_name in PROMPT_REGISTRY.keys()
    ]


def load_tools():
    """
    Load all tools from the tools package.
    
    This function imports the tools package which automatically discovers
    and registers all tools using the @mcp_tool decorator.
    """
    try:
        # Import the tools package - this triggers automatic tool discovery
        from . import tools
        logger.info(f"Tools loaded via package import: {len(TOOL_REGISTRY)} tools registered")
    except ImportError as e:
        logger.warning(f"Failed to import tools package: {e}")
    except Exception as e:
        logger.error(f"Error loading tools: {e}")


def load_prompts():
    """
    Load all prompts from the prompts package.
    
    This function imports the prompts package which automatically discovers
    and registers all prompts using the @mcp_prompt decorator.
    """
    try:
        # Import the prompts package - this triggers automatic prompt discovery
        from . import prompts
        logger.info(f"Prompts loaded via package import: {len(PROMPT_REGISTRY)} prompts registered")
    except ImportError as e:
        logger.warning(f"Failed to import prompts package: {e}")
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")


def execute_tool(tool_name: str, client, **parameters) -> Any:
    """
    Execute a registered tool with dependency injection.
    
    Args:
        tool_name: Name of the tool to execute
        client: NetBoxClient instance to inject
        **parameters: Tool parameters
        
    Returns:
        Tool execution result
        
    Raises:
        ValueError: If tool not found
        Exception: Tool execution errors
    """
    tool_metadata = get_tool_by_name(tool_name)
    if not tool_metadata:
        raise ValueError(f"Tool '{tool_name}' not found in registry")
    
    tool_function = tool_metadata["function"]
    
    # Filter out 'client' parameter from parameters to avoid duplicate argument error
    # The client is injected separately as named parameter
    filtered_parameters = {k: v for k, v in parameters.items() if k != 'client'}
    
    # Inject client as first parameter
    return tool_function(client=client, **filtered_parameters)


async def execute_prompt(prompt_name: str, **arguments) -> Any:
    """
    Execute a registered prompt.
    
    Args:
        prompt_name: Name of the prompt to execute
        **arguments: Prompt arguments (if any)
        
    Returns:
        Prompt execution result
        
    Raises:
        ValueError: If prompt not found
        Exception: Prompt execution errors
    """
    prompt_metadata = get_prompt_by_name(prompt_name)
    if not prompt_metadata:
        raise ValueError(f"Prompt '{prompt_name}' not found in registry")
    
    prompt_function = prompt_metadata["function"]
    
    # Execute the prompt function with provided arguments, handling both sync and async functions
    if inspect.iscoroutinefunction(prompt_function):
        if arguments:
            return await prompt_function(**arguments)
        else:
            return await prompt_function()
    else:
        if arguments:
            return prompt_function(**arguments)
        else:
            return prompt_function()