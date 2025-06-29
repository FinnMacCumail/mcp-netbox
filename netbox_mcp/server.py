#!/usr/bin/env python3
"""
NetBox MCP Server

A Model Context Protocol server for safe read/write access to NetBox instances.
Provides tools for querying and managing NetBox data with comprehensive safety controls.

Version: 0.9.7 - Hierarchical Architecture with Registry Bridge
"""

from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from .client import NetBoxClient
from .config import load_config
from .registry import (
    TOOL_REGISTRY, PROMPT_REGISTRY, 
    load_tools, load_prompts, 
    serialize_registry_for_api, serialize_prompts_for_api,
    execute_tool, execute_prompt
)
from .dependencies import NetBoxClientManager, get_netbox_client  # Use new dependency system
import logging
import os
import threading
import time
import inspect
from functools import wraps
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from typing import Dict, List, Optional, Any

# Configure logging (will be updated from config)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === REGISTRY BRIDGE IMPLEMENTATION ===

# Step 1: Load all tools and prompts into our internal registries
load_tools()
load_prompts()
logger.info(f"Internal tool registry initialized with {len(TOOL_REGISTRY)} tools")
logger.info(f"Internal prompt registry initialized with {len(PROMPT_REGISTRY)} prompts")

# Step 2: Initialize FastMCP server (empty at first)
mcp = FastMCP(
    "NetBox Model-Context Protocol",
    description="A powerful, tool-based interface to manage and orchestrate a NetBox instance."
)

# Step 3: The Registry Bridge function
def bridge_tools_to_fastmcp():
    """
    Dynamically registers all tools from our internal TOOL_REGISTRY
    with the FastMCP instance, creating wrappers for dependency injection.
    """
    bridged_count = 0
    for tool_name, tool_metadata in TOOL_REGISTRY.items():
        try:
            original_func = tool_metadata["function"]
            description = tool_metadata.get("description", f"Executes the {tool_name} tool.")
            category = tool_metadata.get("category", "General")

            # Create a 'wrapper' that injects the client with EXACT function signature (Gemini's Fix)
            def create_tool_wrapper(original_func):
                """
                Creëert een wrapper voor een tool die de exacte signatuur van de originele functie nabootst,
                terwijl de NetBox client automatisch wordt geïnjecteerd en argument-duplicaten voorkomt.
                """
                sig = inspect.signature(original_func)
                wrapper_params = [p for p in sig.parameters.values() if p.name != 'client']

                @wraps(original_func)
                def tool_wrapper(*args, **kwargs):
                    try:
                        # ----- VEILIGE ARGUMENT-AFHANDELING -----
                        # 1. Maak een lijst van de verwachte parameternamen (zonder 'client')
                        param_names = [p.name for p in wrapper_params]

                        # 2. Maak een dictionary van de positionele argumenten (*args)
                        final_kwargs = dict(zip(param_names, args))

                        # 3. Update met de keyword-argumenten (**kwargs).
                        #    Dit overschrijft eventuele duplicaten en is de kern van de fix.
                        final_kwargs.update(kwargs)
                        # ----------------------------------------

                        client = get_netbox_client()

                        # Roep de originele functie aan met de schone, ontdubbelde argumenten.
                        return original_func(client, **final_kwargs)

                    except Exception as e:
                        logger.error(f"Execution of tool '{tool_name}' failed: {e}", exc_info=True)
                        return {"success": False, "error": str(e), "error_type": type(e).__name__}

                new_sig = sig.replace(parameters=wrapper_params)
                tool_wrapper.__signature__ = new_sig
                return tool_wrapper

            # Register the 'wrapper' with FastMCP with the correct metadata
            wrapped_tool = create_tool_wrapper(original_func)
            mcp.tool(name=tool_name, description=description)(wrapped_tool)

            bridged_count += 1
            logger.debug(f"Bridged tool: {tool_name} (category: {category})")

        except Exception as e:
            logger.error(f"Failed to bridge tool '{tool_name}' to FastMCP: {e}", exc_info=True)

    logger.info(f"Successfully bridged {bridged_count}/{len(TOOL_REGISTRY)} tools to the FastMCP interface")

# Step 4: Execute the bridge function at server startup
bridge_tools_to_fastmcp()

# Step 5: Bridge prompts to FastMCP
def bridge_prompts_to_fastmcp():
    """
    Bridge internal prompt registry to FastMCP interface.
    
    This function creates FastMCP-compatible prompt handlers for each
    prompt in our internal PROMPT_REGISTRY and registers them with the FastMCP server.
    """
    bridged_count = 0
    
    for prompt_name, prompt_metadata in PROMPT_REGISTRY.items():
        try:
            original_func = prompt_metadata["function"]
            description = prompt_metadata["description"]
            
            logger.debug(f"Bridging prompt: {prompt_name}")
            
            def create_prompt_wrapper(func, name):
                """Create a wrapper function that FastMCP can call"""
                async def prompt_wrapper(**kwargs):
                    try:
                        logger.debug(f"Executing prompt '{name}' with args: {kwargs}")
                        
                        # Execute the prompt function
                        if inspect.iscoroutinefunction(func):
                            result = await func(**kwargs)
                        else:
                            result = func(**kwargs)
                        
                        logger.debug(f"Prompt '{name}' executed successfully")
                        return result
                    
                    except Exception as e:
                        logger.error(f"Execution of prompt '{name}' failed: {e}", exc_info=True)
                        return {"success": False, "error": str(e), "error_type": type(e).__name__}
                
                return prompt_wrapper
            
            # Register the wrapper with FastMCP
            wrapped_prompt = create_prompt_wrapper(original_func, prompt_name)
            mcp.prompt(name=prompt_name, description=description)(wrapped_prompt)
            
            bridged_count += 1
            logger.debug(f"Bridged prompt: {prompt_name}")
            
        except Exception as e:
            logger.error(f"Failed to bridge prompt '{prompt_name}' to FastMCP: {e}", exc_info=True)
    
    logger.info(f"Successfully bridged {bridged_count}/{len(PROMPT_REGISTRY)} prompts to the FastMCP interface")

# Step 6: Execute the prompt bridge function at server startup
bridge_prompts_to_fastmcp()

# === FASTAPI SELF-DESCRIBING ENDPOINTS ===

# Initialize FastAPI server for self-describing endpoints
api_app = FastAPI(
    title="NetBox MCP API",
    description="Self-describing REST API for NetBox Management & Control Plane",
    version="0.9.7"
)

# Pydantic models for API requests
class ExecutionRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = {}

class ToolFilter(BaseModel):
    category: Optional[str] = None
    name_pattern: Optional[str] = None

@api_app.get("/api/v1/tools", response_model=List[Dict[str, Any]])
async def get_tools(
    category: Optional[str] = None,
    name_pattern: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Discovery endpoint: List all available MCP tools.

    Query Parameters:
        category: Filter tools by category (system, ipam, dcim, etc.)
        name_pattern: Filter tools by name pattern (partial match)

    Returns:
        List of tool metadata with parameters, descriptions, and categories
    """
    try:
        tools = serialize_registry_for_api()

        # Apply filters
        if category:
            tools = [tool for tool in tools if tool.get("category") == category]

        if name_pattern:
            tools = [tool for tool in tools if name_pattern.lower() in tool.get("name", "").lower()]

        logger.info(f"Tools discovery request: {len(tools)} tools returned (category={category}, pattern={name_pattern})")
        return tools

    except Exception as e:
        logger.error(f"Error in tools discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@api_app.post("/api/v1/execute")
async def execute_mcp_tool(
    request: ExecutionRequest,
    client: NetBoxClient = Depends(get_netbox_client)
) -> Dict[str, Any]:
    """
    Generic execution endpoint: Execute any registered MCP tool.

    Request Body:
        tool_name: Name of the tool to execute
        parameters: Dictionary of tool parameters

    Returns:
        Tool execution result
    """
    try:
        logger.info(f"Executing tool: {request.tool_name} with parameters: {request.parameters}")

        # Execute tool with dependency injection
        result = execute_tool(request.tool_name, client, **request.parameters)

        return {
            "success": True,
            "tool_name": request.tool_name,
            "result": result
        }

    except ValueError as e:
        # Tool not found
        logger.warning(f"Tool not found: {request.tool_name}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Tool execution failed for {request.tool_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


# === PROMPT ENDPOINTS ===

class PromptRequest(BaseModel):
    prompt_name: str
    arguments: Dict[str, Any] = {}

@api_app.get("/api/v1/prompts", response_model=List[Dict[str, Any]])
async def get_prompts() -> List[Dict[str, Any]]:
    """
    Discovery endpoint: List all available MCP prompts.

    Returns:
        List of prompt metadata with descriptions and usage information
    """
    try:
        prompts = serialize_prompts_for_api()
        logger.info(f"Prompts discovery request: {len(prompts)} prompts returned")
        return prompts

    except Exception as e:
        logger.error(f"Error in prompts discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@api_app.post("/api/v1/prompts/execute")
async def execute_mcp_prompt(request: PromptRequest) -> Dict[str, Any]:
    """
    Generic prompt execution endpoint: Execute any registered MCP prompt.

    Request Body:
        prompt_name: Name of the prompt to execute
        arguments: Dictionary of prompt arguments (optional)

    Returns:
        Prompt execution result
    """
    try:
        logger.info(f"Executing prompt: {request.prompt_name} with arguments: {request.arguments}")

        # Execute prompt
        result = await execute_prompt(request.prompt_name, **request.arguments)

        return {
            "success": True,
            "prompt_name": request.prompt_name,
            "result": result
        }

    except ValueError as e:
        # Prompt not found
        logger.warning(f"Prompt not found: {request.prompt_name}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Prompt execution failed for {request.prompt_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Prompt execution failed: {str(e)}")


# === CONTEXT MANAGEMENT ENDPOINTS ===

@api_app.get("/api/v1/context/status")
async def get_context_status(
    client: NetBoxClient = Depends(get_netbox_client)
) -> Dict[str, Any]:
    """
    Get current auto-context status and configuration.
    
    Returns:
        Context status including environment detection and safety level
    """
    try:
        from .persona import get_context_manager
        
        context_manager = get_context_manager()
        context_state = context_manager.get_context_state()
        
        if context_state:
            return {
                "context_initialized": True,
                "environment": context_state.environment,
                "safety_level": context_state.safety_level,
                "instance_type": context_state.instance_type,
                "initialization_time": context_state.initialization_time.isoformat(),
                "netbox_url": context_state.netbox_url,
                "netbox_version": context_state.netbox_version,
                "auto_context_enabled": context_state.auto_context_enabled,
                "user_preferences": context_state.user_preferences
            }
        else:
            return {
                "context_initialized": False,
                "auto_context_enabled": os.getenv('NETBOX_AUTO_CONTEXT', 'true').lower() == 'true',
                "environment_override": os.getenv('NETBOX_ENVIRONMENT'),
                "safety_level_override": os.getenv('NETBOX_SAFETY_LEVEL')
            }
            
    except Exception as e:
        logger.error(f"Error getting context status: {e}")
        raise HTTPException(status_code=500, detail=f"Context status error: {str(e)}")


@api_app.post("/api/v1/context/initialize")
async def initialize_context(
    client: NetBoxClient = Depends(get_netbox_client)
) -> Dict[str, Any]:
    """
    Manually initialize Bridget auto-context system.
    
    Returns:
        Context initialization result
    """
    try:
        from .persona import get_context_manager
        
        context_manager = get_context_manager()
        
        # Reset context if already initialized
        if context_manager.is_context_initialized():
            context_manager.reset_context()
        
        # Initialize context
        context_state = context_manager.initialize_context(client)
        context_message = context_manager.generate_context_message(context_state)
        
        return {
            "success": True,
            "message": "Context initialized successfully",
            "context": {
                "environment": context_state.environment,
                "safety_level": context_state.safety_level,
                "instance_type": context_state.instance_type,
                "initialization_time": context_state.initialization_time.isoformat()
            },
            "bridget_message": context_message
        }
        
    except Exception as e:
        logger.error(f"Error initializing context: {e}")
        raise HTTPException(status_code=500, detail=f"Context initialization failed: {str(e)}")


@api_app.post("/api/v1/context/reset")
async def reset_context() -> Dict[str, Any]:
    """
    Reset the auto-context system state.
    
    Returns:
        Reset operation result
    """
    try:
        from .registry import reset_context_state
        
        reset_context_state()
        
        return {
            "success": True,
            "message": "Context state reset successfully"
        }
        
    except Exception as e:
        logger.error(f"Error resetting context: {e}")
        raise HTTPException(status_code=500, detail=f"Context reset failed: {str(e)}")


@api_app.get("/api/v1/status")
async def get_system_status(
    client: NetBoxClient = Depends(get_netbox_client)
) -> Dict[str, Any]:
    """
    Health/Status endpoint: Get MCP system status and NetBox connectivity.

    Returns:
        System status including NetBox connection, tool registry stats, and performance metrics
    """
    try:
        # Get NetBox health status
        netbox_status = client.health_check()

        # Get tool registry statistics
        from .registry import get_registry_stats
        registry_stats = get_registry_stats()

        # Get client status
        from .dependencies import get_client_status
        client_status = get_client_status()

        return {
            "service": "NetBox MCP",
            "version": "0.9.7",
            "status": "healthy" if netbox_status.connected else "degraded",
            "netbox": {
                "connected": netbox_status.connected,
                "version": netbox_status.version,
                "python_version": netbox_status.python_version,
                "django_version": netbox_status.django_version,
                "response_time_ms": netbox_status.response_time_ms,
                "plugins": netbox_status.plugins
            },
            "tool_registry": registry_stats,
            "client": client_status,
            "cache_stats": netbox_status.cache_stats if hasattr(netbox_status, 'cache_stats') else None
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "service": "NetBox MCP",
            "version": "0.9.7",
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

# === HTTP HEALTH CHECK SERVER ===

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints."""

    def do_GET(self):
        """Handle GET requests for health check endpoints."""
        try:
            if self.path in ['/health', '/healthz']:
                # Basic liveness check
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()

                response = {
                    "status": "OK",
                    "service": "netbox-mcp",
                    "version": "0.9.7"
                }
                self.wfile.write(json.dumps(response).encode())

            elif self.path == '/readyz':
                # Readiness check - test NetBox connection
                try:
                    status = NetBoxClientManager.get_client().health_check()
                    if status.connected:
                        self.send_response(200)
                        response = {
                            "status": "OK",
                            "netbox_connected": True,
                            "netbox_version": status.version,
                            "response_time_ms": status.response_time_ms
                        }
                    else:
                        self.send_response(503)
                        response = {
                            "status": "Service Unavailable",
                            "netbox_connected": False,
                            "error": status.error
                        }
                except Exception as e:
                    self.send_response(503)
                    response = {
                        "status": "Service Unavailable",
                        "netbox_connected": False,
                        "error": str(e)
                    }

                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()

                response = {"error": "Not Found"}
                self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Health check handler error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {"error": "Internal Server Error", "details": str(e)}
            self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"Health check: {format % args}")


def start_health_server(port: int):
    """Start the HTTP health check server in a separate thread."""
    def run_server():
        try:
            server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
            logger.info(f"Health check server started on port {port}")
            logger.info(f"Health endpoints: /health, /healthz (liveness), /readyz (readiness)")
            server.serve_forever()
        except Exception as e:
            logger.error(f"Health check server failed: {e}")

    health_thread = threading.Thread(target=run_server, daemon=True)
    health_thread.start()


def initialize_server():
    """Initialize the NetBox MCP server with configuration and client."""
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded successfully")

        # Update logging level
        logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
        logger.info(f"Log level set to {config.log_level}")

        # Log safety configuration
        if config.safety.dry_run_mode:
            logger.warning("🚨 NetBox MCP running in DRY-RUN mode - no actual writes will be performed")

        if not config.safety.enable_write_operations:
            logger.info("🔒 Write operations are DISABLED - server is read-only")

        # Initialize NetBox client using Gemini's singleton pattern
        NetBoxClientManager.initialize(config)
        logger.info("NetBox client initialized successfully via singleton manager")

        # Test connection (graceful degradation if NetBox is unavailable)
        client = NetBoxClientManager.get_client()
        try:
            status = client.health_check()
            if status.connected:
                logger.info(f"✅ Connected to NetBox {status.version} (response time: {status.response_time_ms:.1f}ms)")
            else:
                logger.warning(f"⚠️ NetBox connection degraded: {status.error}")
        except Exception as e:
            logger.warning(f"⚠️ NetBox connection failed during startup, running in degraded mode: {e}")
            # Continue startup - health server should still start for liveness probes

        # Async task system removed - using synchronous operations only
        logger.info("NetBox MCP server using synchronous operations")

        # Start health check server if enabled
        if config.enable_health_server:
            start_health_server(config.health_check_port)

        logger.info("NetBox MCP server initialization complete")

    except Exception as e:
        logger.error(f"Failed to initialize NetBox MCP server: {e}")
        raise


def main():
    """Main entry point for the NetBox MCP server."""
    try:
        # Initialize server
        initialize_server()

        # Define the MCP server task to run in a thread
        def run_mcp_server():
            try:
                logger.info("Starting NetBox MCP server on a dedicated thread...")
                mcp.run(transport="stdio")
            except Exception as e:
                logger.error(f"MCP server thread encountered an error: {e}", exc_info=True)

        # Start the MCP server in a daemon thread
        mcp_thread = threading.Thread(target=run_mcp_server)
        mcp_thread.daemon = True
        mcp_thread.start()

        # Keep the main thread alive to allow daemon threads to run
        logger.info("NetBox MCP server is ready and listening")
        logger.info("Health endpoints: /health, /healthz (liveness), /readyz (readiness)")

        try:
            while True:
                time.sleep(3600)  # Sleep for a long time
        except KeyboardInterrupt:
            logger.info("Shutting down NetBox MCP server...")

    except Exception as e:
        logger.error(f"NetBox MCP server error: {e}")
        raise


if __name__ == "__main__":
    main()
