#!/usr/bin/env python3
"""
NetBox MCP Tools Package

This package contains all MCP tool implementations organized by category.
Tools are automatically discovered and registered using the @mcp_tool decorator.

The package structure follows NetBox's application organization:
- system_tools.py - System health and monitoring tools  
- ipam_tools.py - IP Address Management tools
- dcim_tools.py - Data Center Infrastructure Management tools
- bulk_tools.py - Bulk operations and orchestration tools

Tools are loaded automatically when this package is imported.
"""

import importlib
import pkgutil
import logging
from typing import List

logger = logging.getLogger(__name__)

def load_all_tools() -> List[str]:
    """
    Automatically discover and load all tool modules in this package.
    
    This function scans the tools/ directory for Python modules and imports
    them, which triggers the @mcp_tool decorator registration.
    Supports both flat files and domain subdirectories.
    
    Returns:
        List[str]: Names of successfully loaded tool modules
    """
    loaded_modules = []
    
    # Get the path of this package
    package_path = __path__
    
    try:
        # Iterate through all modules in this package
        for finder, module_name, ispkg in pkgutil.iter_modules(package_path, prefix=__name__ + '.'):
            try:
                if ispkg:
                    # This is a subdirectory (domain package) - import it to trigger __init__.py
                    importlib.import_module(module_name)
                    loaded_modules.append(module_name)
                    logger.info(f"Successfully loaded domain package: {module_name}")
                    
                    # Also load all modules within the domain package
                    domain_package = importlib.import_module(module_name)
                    if hasattr(domain_package, '__path__'):
                        for domain_finder, domain_module_name, domain_ispkg in pkgutil.iter_modules(
                            domain_package.__path__, prefix=module_name + '.'
                        ):
                            if not domain_ispkg and not domain_module_name.endswith('.__init__'):
                                try:
                                    importlib.import_module(domain_module_name)
                                    loaded_modules.append(domain_module_name)
                                    logger.info(f"Successfully loaded domain module: {domain_module_name}")
                                except Exception as e:
                                    logger.error(f"Failed to load domain module {domain_module_name}: {e}")
                                    
                elif not module_name.endswith('.__init__'):
                    # This is a flat module file - import it directly
                    importlib.import_module(module_name)
                    loaded_modules.append(module_name)
                    logger.info(f"Successfully loaded flat module: {module_name}")
                    
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")
                # Continue loading other modules even if one fails
    
    except Exception as e:
        logger.error(f"Error during tool discovery: {e}")
    
    logger.info(f"Tool discovery complete: {len(loaded_modules)} modules loaded")
    return loaded_modules

# Automatically load all tools when this package is imported
_loaded_tools = load_all_tools()

# Export the load function for explicit use if needed
__all__ = ['load_all_tools']