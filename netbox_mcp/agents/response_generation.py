"""
Response Generation Agent - Natural language formatting of tool outputs
"""

import json
from typing import Any, Dict, List, Optional

from .base import BaseAgent, QueryContext
from .config import get_config


class ResponseGenerationAgent(BaseAgent):
    """
    Agent responsible for converting structured tool outputs to natural language.
    Uses GPT-4o-mini for efficient response generation.
    """
    
    def __init__(self, agent_id: str = "response_generator"):
        config = get_config().openai
        super().__init__(agent_id, "response_generation", config)
        
        self.model = config.response_model
        self.temperature = config.response_temperature
        
        # Response formatting templates
        self.system_prompt = """You are a helpful NetBox assistant that converts technical data into clear, natural language responses.

Your responsibilities:
1. Convert structured NetBox data into user-friendly explanations
2. Add helpful context and insights
3. Format complex data clearly (use tables, lists, etc.)
4. Suggest relevant follow-up actions
5. Handle error states gracefully with helpful guidance

Guidelines:
- Be concise but informative
- Use appropriate formatting for readability
- Highlight important information
- Provide actionable next steps when relevant
- Explain technical terms when necessary"""
    
    async def initialize(self) -> None:
        """Initialize response generation agent"""
        self.logger.info("Response Generation Agent initialized")
    
    async def cleanup(self) -> None:
        """Clean up agent resources"""
        self.logger.info("Response Generation Agent cleaned up")
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process a response generation request"""
        request_type = content.get("type", "format_response")
        
        if request_type == "format_response":
            return await self.format_response(content)
        elif request_type == "format_error":
            return await self.format_error(content)
        elif request_type == "format_clarification":
            return await self.format_clarification(content)
        elif request_type == "format_progress":
            return await self.format_progress(content)
        else:
            return {"error": f"Unknown request type: {request_type}"}
    
    async def format_response(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format tool results into natural language response"""
        query_context = content.get("context", {})
        tool_results = query_context.get("tool_results", [])
        response_type = content.get("response_type", "standard")
        
        try:
            # Prepare the formatting prompt
            formatting_prompt = self._build_formatting_prompt(
                tool_results, 
                query_context, 
                response_type
            )
            
            # Call OpenAI to format the response
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": formatting_prompt}
                ],
                temperature=self.temperature,
                max_tokens=2048
            )
            
            formatted_response = response.choices[0].message.content
            
            # Add metadata and suggestions
            enhanced_response = await self._enhance_response(
                formatted_response,
                tool_results,
                query_context
            )
            
            return {
                "success": True,
                "response": enhanced_response,
                "metadata": {
                    "tokens_used": response.usage.total_tokens,
                    "model": self.model,
                    "response_type": response_type
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting response: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_response": self._create_fallback_response(tool_results)
            }
    
    async def format_error(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format error messages for users"""
        error_info = content.get("error", {})
        context = content.get("context", {})
        
        error_prompt = f"""Convert this technical error into a helpful user message:

Error Type: {error_info.get('type', 'Unknown')}
Error Message: {error_info.get('message', 'An error occurred')}
Context: {json.dumps(context, indent=2)}

Provide:
1. A clear explanation of what went wrong
2. Why this might have happened
3. Suggested actions the user can take
4. Alternative approaches if available

Keep the tone helpful and non-technical."""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": error_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "error_handled": True
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting error message: {e}")
            return {
                "success": False,
                "response": "An error occurred while processing your request. Please try again or rephrase your query.",
                "error_handled": False
            }
    
    async def format_clarification(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format clarification questions for ambiguous queries"""
        ambiguous_entities = content.get("ambiguous_entities", [])
        possible_values = content.get("possible_values", {})
        original_query = content.get("original_query", "")
        
        clarification_prompt = f"""Generate helpful clarification questions for this ambiguous query:

Original Query: "{original_query}"
Ambiguous Elements: {json.dumps(ambiguous_entities, indent=2)}
Possible Values: {json.dumps(possible_values, indent=2)}

Create natural, friendly clarification questions that:
1. Are easy to understand
2. Provide helpful context
3. Show available options when appropriate
4. Guide the user to provide specific information

Format as a conversational response with numbered questions if multiple clarifications are needed."""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": clarification_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "requires_clarification": True,
                "clarification_metadata": {
                    "entities": ambiguous_entities,
                    "options": possible_values
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting clarification: {e}")
            # Fallback to simple clarification
            questions = []
            for entity in ambiguous_entities:
                if entity in possible_values and possible_values[entity]:
                    options = possible_values[entity][:5]  # Limit to 5 options
                    questions.append(f"Which {entity} did you mean? Options include: {', '.join(options)}")
                else:
                    questions.append(f"Could you please specify which {entity} you're referring to?")
            
            return {
                "success": True,
                "response": "I need some clarification:\n\n" + "\n".join(questions),
                "requires_clarification": True
            }
    
    async def format_progress(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Format progress updates for long-running operations"""
        operation = content.get("operation", "Processing")
        current_step = content.get("current_step", 0)
        total_steps = content.get("total_steps", 0)
        message = content.get("message", "")
        
        progress_percentage = (current_step / total_steps * 100) if total_steps > 0 else 0
        
        progress_response = f"⏳ {operation}: Step {current_step}/{total_steps} ({progress_percentage:.0f}%)"
        if message:
            progress_response += f"\n   {message}"
        
        return {
            "success": True,
            "response": progress_response,
            "is_progress": True,
            "metadata": {
                "operation": operation,
                "progress": progress_percentage,
                "current_step": current_step,
                "total_steps": total_steps
            }
        }
    
    def _build_formatting_prompt(
        self, 
        tool_results: List[Dict[str, Any]],
        query_context: Dict[str, Any],
        response_type: str
    ) -> str:
        """Build the prompt for intelligent NetBox response formatting - Claude Code CLI style with recovery awareness"""
        
        # Extract and intelligently format NetBox data
        extracted_data = self._extract_meaningful_netbox_data(tool_results)
        user_query = query_context.get('user_query', 'N/A')
        
        # Check if recovery was used to get this data
        recovery_info = self._analyze_recovery_context(query_context, tool_results)
        recovery_context = ""
        if recovery_info["recovery_used"]:
            recovery_context = f"""
RECOVERY CONTEXT:
- The system successfully corrected parameters to retrieve this data
- Parameter corrections applied: {recovery_info['corrections_applied']}
- Recovery strategy: {recovery_info['strategy_used']}
- This shows the adaptive intelligence working to fix parameter issues
"""
        
        prompt = f"""Format this NetBox data into a natural language response that matches Claude Code CLI quality:

User Query: "{user_query}"
Response Type: {response_type}
{recovery_context}
Extracted NetBox Data:
{extracted_data}

Raw Tool Results (for context):
{json.dumps(tool_results, indent=2, default=str)}

Create a Claude Code CLI style response that:
1. Directly answers the user's question with specific NetBox data (not generic guidance)
2. Shows key entity information clearly (ID, name, relationships, counts, specific values)
3. Uses concise but informative formatting
4. Focuses on the most relevant data for the query
5. Matches this style: "Device: dmi01-akron-pdu01, ID: 27, Site: ID 2, Rack: ID 1, Position 1.0, Power ports: 1, Power outlets: 8"
6. If recovery was used, briefly acknowledge the parameter correction success
7. ALWAYS provide specific data values, not generic explanations

Be specific and factual, not generic. Show actual NetBox data returned by the tools."""
        
        return prompt
    
    def _analyze_recovery_context(self, query_context: Dict[str, Any], tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze if recovery was used and what corrections were applied"""
        recovery_info = {
            "recovery_used": False,
            "strategy_used": "none",
            "corrections_applied": {},
            "recovery_successful": False
        }
        
        # Check query context for recovery information
        if query_context.get("recovery_attempted"):
            recovery_info["recovery_used"] = True
            recovery_info["strategy_used"] = query_context.get("recovery_strategy", "parameter_correction")
            
        # Check tool results for recovery indicators
        for result in tool_results:
            if isinstance(result, dict):
                # Check if result indicates parameter correction was applied
                if result.get("corrected_parameters"):
                    recovery_info["recovery_used"] = True
                    recovery_info["corrections_applied"].update(result.get("corrected_parameters", {}))
                
                # Check if result has recovery metadata
                if result.get("parameter_correction_applied"):
                    recovery_info["recovery_used"] = True
                    recovery_info["recovery_successful"] = result.get("success", False)
                
                # Check for real API call indicators
                if result.get("real_api_call"):
                    recovery_info["recovery_successful"] = result.get("success", False)
        
        return recovery_info
    
    def _extract_meaningful_netbox_data(self, tool_results: List[Dict[str, Any]]) -> str:
        """Extract meaningful information from NetBox API responses - Claude Code CLI style"""
        
        if not tool_results:
            return "No data available"
        
        extracted_parts = []
        
        for result in tool_results:
            if not isinstance(result, dict) or not result.get("success"):
                continue
                
            tool_name = result.get("tool_name", "unknown")
            result_data = result.get("result")
            
            if not result_data:
                continue
            
            # Extract meaningful data based on tool type
            if "device" in tool_name.lower():
                device_info = self._extract_device_info(result_data, tool_name)
                if device_info:
                    extracted_parts.append(f"Device Data: {device_info}")
                    
            elif "site" in tool_name.lower():
                site_info = self._extract_site_info(result_data, tool_name)
                if site_info:
                    extracted_parts.append(f"Site Data: {site_info}")
                    
            elif "rack" in tool_name.lower():
                if "elevation" in tool_name.lower():
                    rack_info = self._extract_rack_elevation_info(result_data, tool_name)
                    if rack_info:
                        extracted_parts.append(f"Rack Elevation: {rack_info}")
                else:
                    rack_info = self._extract_rack_info(result_data, tool_name)
                    if rack_info:
                        extracted_parts.append(f"Rack Data: {rack_info}")
                    
            elif "virtual_machine" in tool_name.lower() or "vm" in tool_name.lower():
                vm_info = self._extract_vm_info(result_data, tool_name)
                if vm_info:
                    extracted_parts.append(f"VM Data: {vm_info}")
                    
            elif "ip" in tool_name.lower() and ("usage" in tool_name.lower() or "prefix" in tool_name.lower()):
                ip_info = self._extract_ip_info(result_data, tool_name)
                if ip_info:
                    extracted_parts.append(f"IP Data: {ip_info}")
                    
            elif "interface" in tool_name.lower():
                interface_info = self._extract_interface_info(result_data, tool_name)
                if interface_info:
                    extracted_parts.append(f"Interface Data: {interface_info}")
                    
            elif "cable" in tool_name.lower():
                cable_info = self._extract_cable_info(result_data, tool_name)
                if cable_info:
                    extracted_parts.append(f"Cable Data: {cable_info}")
                    
            else:
                # Generic data extraction for unknown types
                generic_info = self._extract_generic_info(result_data, tool_name)
                if generic_info:
                    extracted_parts.append(f"Data ({tool_name}): {generic_info}")
        
        return "\n".join(extracted_parts) if extracted_parts else "No meaningful data extracted"
    
    def _extract_device_info(self, data: Any, tool_name: str) -> str:
        """Extract device information in Claude Code CLI style"""
        try:
            if isinstance(data, dict):
                # Single device
                device = data
                parts = []
                
                if "name" in device:
                    parts.append(f"Name: {device['name']}")
                if "id" in device:
                    parts.append(f"ID: {device['id']}")
                if "device_type" in device and isinstance(device["device_type"], dict):
                    parts.append(f"Type: {device['device_type'].get('display', device['device_type'].get('model', 'N/A'))}")
                if "site" in device and isinstance(device["site"], dict):
                    parts.append(f"Site: {device['site'].get('name', device['site'].get('id', 'N/A'))}")
                if "rack" in device and device["rack"] and isinstance(device["rack"], dict):
                    parts.append(f"Rack: {device['rack'].get('name', device['rack'].get('id', 'N/A'))}")
                if "position" in device and device["position"]:
                    parts.append(f"Position: {device['position']}")
                if "status" in device and isinstance(device["status"], dict):
                    parts.append(f"Status: {device['status'].get('label', device['status'].get('value', 'N/A'))}")
                
                return ", ".join(parts)
                
            elif isinstance(data, list):
                # Multiple devices
                device_summaries = []
                for device in data[:5]:  # Limit to first 5 devices
                    if isinstance(device, dict):
                        name = device.get('name', f"ID-{device.get('id', 'unknown')}")
                        device_type = ""
                        if "device_type" in device and isinstance(device["device_type"], dict):
                            device_type = f" ({device['device_type'].get('display', 'Unknown type')})"
                        device_summaries.append(f"{name}{device_type}")
                
                total_count = len(data) if isinstance(data, list) else 0
                summary = f"Found {total_count} devices"
                if device_summaries:
                    summary += f": {', '.join(device_summaries)}"
                    if total_count > 5:
                        summary += f" + {total_count - 5} more"
                
                return summary
                
        except Exception as e:
            return f"Device data parsing error: {str(e)}"
        
        return "No device information available"
    
    def _extract_site_info(self, data: Any, tool_name: str) -> str:
        """Extract site information"""
        try:
            if isinstance(data, dict):
                parts = []
                if "name" in data:
                    parts.append(f"Name: {data['name']}")
                if "id" in data:
                    parts.append(f"ID: {data['id']}")
                if "status" in data and isinstance(data["status"], dict):
                    parts.append(f"Status: {data['status'].get('label', 'N/A')}")
                if "region" in data and data["region"] and isinstance(data["region"], dict):
                    parts.append(f"Region: {data['region'].get('name', 'N/A')}")
                    
                return ", ".join(parts)
            elif isinstance(data, list):
                return f"Found {len(data)} sites"
                
        except Exception:
            pass
        
        return "Site information not available"
    
    def _extract_rack_info(self, data: Any, tool_name: str) -> str:
        """Extract rack information"""
        try:
            if isinstance(data, dict):
                parts = []
                if "name" in data:
                    parts.append(f"Name: {data['name']}")
                if "id" in data:
                    parts.append(f"ID: {data['id']}")
                if "u_height" in data:
                    parts.append(f"U Height: {data['u_height']}")
                if "site" in data and isinstance(data["site"], dict):
                    parts.append(f"Site: {data['site'].get('name', 'N/A')}")
                    
                return ", ".join(parts)
            elif isinstance(data, list):
                return f"Found {len(data)} racks"
                
        except Exception:
            pass
        
        return "Rack information not available"
    
    def _extract_interface_info(self, data: Any, tool_name: str) -> str:
        """Extract interface information"""
        try:
            if isinstance(data, list):
                interface_summaries = []
                for interface in data[:10]:  # Limit to first 10 interfaces
                    if isinstance(interface, dict):
                        name = interface.get('name', 'Unknown')
                        interface_type = interface.get('type', {})
                        if isinstance(interface_type, dict):
                            type_label = interface_type.get('label', interface_type.get('value', ''))
                        else:
                            type_label = str(interface_type) if interface_type else ''
                        
                        enabled = interface.get('enabled', True)
                        status = "enabled" if enabled else "disabled"
                        
                        summary = f"{name}"
                        if type_label:
                            summary += f" ({type_label})"
                        summary += f" [{status}]"
                        interface_summaries.append(summary)
                
                total_count = len(data)
                result = f"Found {total_count} interfaces"
                if interface_summaries:
                    result += f": {', '.join(interface_summaries)}"
                    if total_count > 10:
                        result += f" + {total_count - 10} more"
                
                return result
            elif isinstance(data, dict):
                # Single interface
                parts = []
                if "name" in data:
                    parts.append(f"Name: {data['name']}")
                if "type" in data and isinstance(data["type"], dict):
                    parts.append(f"Type: {data['type'].get('label', 'N/A')}")
                if "enabled" in data:
                    parts.append(f"Status: {'enabled' if data['enabled'] else 'disabled'}")
                    
                return ", ".join(parts)
                
        except Exception:
            pass
        
        return "Interface information not available"
    
    def _extract_cable_info(self, data: Any, tool_name: str) -> str:
        """Extract cable information"""
        try:
            if isinstance(data, list):
                return f"Found {len(data)} cables"
            elif isinstance(data, dict):
                parts = []
                if "id" in data:
                    parts.append(f"ID: {data['id']}")
                if "label" in data and data["label"]:
                    parts.append(f"Label: {data['label']}")
                if "type" in data and isinstance(data["type"], dict):
                    parts.append(f"Type: {data['type'].get('label', 'N/A')}")
                    
                return ", ".join(parts)
                
        except Exception:
            pass
        
        return "Cable information not available"
    
    def _extract_vm_info(self, data: Any, tool_name: str) -> str:
        """Extract virtual machine information"""
        try:
            if isinstance(data, list):
                vm_summaries = []
                for vm in data[:10]:  # Limit to first 10 VMs
                    if isinstance(vm, dict):
                        name = vm.get('name', 'Unknown')
                        cluster = vm.get('cluster', {})
                        cluster_name = cluster.get('name', 'N/A') if isinstance(cluster, dict) else 'N/A'
                        status = vm.get('status', 'unknown')
                        
                        vm_summaries.append(f"{name} (cluster: {cluster_name}, status: {status})")
                
                total_count = len(data)
                result = f"Found {total_count} virtual machines"
                if vm_summaries:
                    result += f": {', '.join(vm_summaries)}"
                    if total_count > 10:
                        result += f" + {total_count - 10} more"
                
                return result
            elif isinstance(data, dict) and "virtual_machines" in data:
                # Handle wrapped VM data
                return self._extract_vm_info(data["virtual_machines"], tool_name)
            elif isinstance(data, dict):
                # Single VM
                parts = []
                if "name" in data:
                    parts.append(f"Name: {data['name']}")
                if "id" in data:
                    parts.append(f"ID: {data['id']}")
                if "cluster" in data and isinstance(data["cluster"], dict):
                    parts.append(f"Cluster: {data['cluster'].get('name', 'N/A')}")
                if "status" in data:
                    parts.append(f"Status: {data['status']}")
                    
                return ", ".join(parts)
                
        except Exception as e:
            return f"VM data parsing error: {str(e)}"
        
        return "Virtual machine information not available"
    
    def _extract_ip_info(self, data: Any, tool_name: str) -> str:
        """Extract IP address/prefix usage information"""
        try:
            if isinstance(data, dict):
                parts = []
                if "prefix" in data:
                    parts.append(f"Prefix: {data['prefix']}")
                if "total_ips" in data:
                    parts.append(f"Total IPs: {data['total_ips']:,}")
                if "used_ips" in data:
                    parts.append(f"Used: {data['used_ips']:,}")
                if "available_ips" in data:
                    parts.append(f"Available: {data['available_ips']:,}")
                if "utilization" in data:
                    parts.append(f"Utilization: {data['utilization']:.2f}%")
                
                return ", ".join(parts)
            elif isinstance(data, list):
                return f"Found {len(data)} IP entries"
                
        except Exception as e:
            return f"IP data parsing error: {str(e)}"
        
        return "IP information not available"
    
    def _extract_rack_elevation_info(self, data: Any, tool_name: str) -> str:
        """Extract rack elevation information"""
        try:
            if isinstance(data, dict):
                parts = []
                if "rack" in data:
                    parts.append(f"Rack: {data['rack']}")
                if "site" in data:
                    parts.append(f"Site: {data['site']}")
                if "height" in data:
                    parts.append(f"Height: {data['height']}U")
                elif "elevation" in data and isinstance(data["elevation"], list):
                    parts.append(f"Height: {len(data['elevation'])}U")
                
                # Count occupied vs free units
                if "elevation" in data and isinstance(data["elevation"], list):
                    occupied = sum(1 for unit in data["elevation"] if unit.get("device"))
                    free = len(data["elevation"]) - occupied
                    parts.append(f"Occupied: {occupied}U, Free: {free}U")
                
                return ", ".join(parts)
                
        except Exception as e:
            return f"Rack elevation parsing error: {str(e)}"
        
        return "Rack elevation information not available"
    
    def _extract_generic_info(self, data: Any, tool_name: str) -> str:
        """Extract generic information from unknown data types"""
        try:
            if isinstance(data, list):
                return f"Found {len(data)} items"
            elif isinstance(data, dict):
                # Try to find common NetBox fields
                parts = []
                for key in ["name", "id", "display", "label"]:
                    if key in data and data[key]:
                        parts.append(f"{key.title()}: {data[key]}")
                        
                if parts:
                    return ", ".join(parts[:3])  # Limit to 3 most important fields
                else:
                    return f"Data object with {len(data)} properties"
            else:
                return f"Value: {str(data)[:100]}"  # Truncate long values
                
        except Exception:
            pass
        
        return "Generic data not parseable"
    
    async def _enhance_response(
        self,
        formatted_response: str,
        tool_results: List[Dict[str, Any]],
        query_context: Dict[str, Any]
    ) -> str:
        """Enhance response with additional context and suggestions"""
        enhanced = formatted_response
        
        # Add performance notes if there were known limitations handled
        if query_context.get("limitations_handled"):
            enhanced += "\n\n📝 **Note**: Some results may be limited due to system constraints. Use filters for more specific queries."
        
        # Add follow-up suggestions based on response type
        if any(result.get("has_more_data") for result in tool_results if isinstance(result, dict)):
            enhanced += "\n\n💡 **Tip**: More data is available. Try adding filters or being more specific to see detailed results."
        
        return enhanced
    
    def _create_fallback_response(self, tool_results: List[Dict[str, Any]]) -> str:
        """Create a basic fallback response if formatting fails"""
        if not tool_results:
            return "I've completed the operation but couldn't format the results properly. Please try your query again."
        
        # Try to create a simple summary
        response_parts = ["Here's what I found:"]
        
        for i, result in enumerate(tool_results):
            if isinstance(result, dict):
                tool_name = result.get("tool_name", f"Tool {i+1}")
                success = result.get("success", False)
                if success:
                    response_parts.append(f"- {tool_name}: Completed successfully")
                    if "result" in result:
                        result_data = result["result"]
                        if isinstance(result_data, dict) and result_data:
                            response_parts.append(f"  Result: {len(result_data)} properties")
                else:
                    error = result.get("error", "Unknown error")
                    response_parts.append(f"- {tool_name}: Failed - {error}")
        
        return "\n".join(response_parts)