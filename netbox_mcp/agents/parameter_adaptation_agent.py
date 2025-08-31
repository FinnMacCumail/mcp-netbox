"""
Parameter Adaptation Agent - LLM-driven parameter transformation without fixed mappings

This agent intelligently transforms parameters based on discoveries and error context
using pure LLM intelligence without any hard-coded transformation rules.
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from .base import BaseAgent
from .config import get_config


class ParameterAdaptationAgent(BaseAgent):
    """
    LLM-driven parameter transformation agent that adapts user parameters
    to correct NetBox API formats based on discovered context.
    """
    
    def __init__(self, agent_id: str = "parameter_adaptation"):
        config = get_config().openai
        super().__init__(agent_id, "parameter_adaptation", config)
        
        self.model = config.response_model  # GPT-4o-mini
        self.temperature = 0.2  # Low temperature for consistent transformations
        
        self.system_prompt = """You are an expert NetBox parameter correction specialist focused on fixing parameter issues that cause query failures.

Your core mission: Transform user parameters using discovered NetBox entity data to ensure successful API calls.

Critical NetBox parameter patterns you MUST handle:
1. **Site Parameter Correction**: User says "DM-Akron" but NetBox needs site slug "dm-akron"
   - Always check discoveries for site name->slug mappings
   - netbox_get_rack_elevation needs site_name="dm-akron" not "DM-Akron"

2. **Rack Parameter Correction**: User says "Comms closet" and NetBox has exact match
   - Use exact rack names from discoveries: rack_name="Comms closet"
   - Preserve exact casing and spacing as discovered

3. **Cluster Parameter Correction**: User says "DO-AMS3" and NetBox has exact match
   - Use exact cluster names: cluster="DO-AMS3"
   - Virtual machine queries need cluster parameter for filtering

4. **Prefix Parameter Correction**: User provides "10.112.128.0/17" and NetBox accepts exact format
   - Use exact prefix format: prefix="10.112.128.0/17"

5. **ID vs Name vs Slug Intelligence**:
   - Use discoveries to determine if tool needs name, slug, or id
   - Sites: usually slug (dm-akron), sometimes name (DM-Akron)
   - Racks: usually name (Comms closet)
   - Clusters: usually name (DO-AMS3)

ALWAYS prioritize discovered entity data over user input formatting. Your goal is 100% successful parameter correction."""
    
    async def initialize(self) -> None:
        """Initialize parameter adaptation agent"""
        self.logger.info("Parameter Adaptation Agent initialized")
    
    async def cleanup(self) -> None:
        """Clean up agent resources"""
        self.logger.info("Parameter Adaptation Agent cleaned up")
    
    async def adapt_parameters(
        self,
        original_params: Dict[str, Any],
        discoveries: Dict[str, Any],
        error_context: Dict[str, Any] = None,
        tool_schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Transform query parameters based on NetBox discoveries using LLM intelligence.
        
        Args:
            original_params: Original parameters that failed
            discoveries: Discovered NetBox entity context
            error_context: Error analysis context
            tool_schema: Schema of the target tool
            
        Returns:
            Dict containing adapted parameters and transformation details
        """
        try:
            # Build adaptation prompt
            adaptation_prompt = f"""CORRECT these NetBox parameters using discovered entity data to ensure API success:

Original Parameters That Failed: {json.dumps(original_params, indent=2)}

NetBox Entity Discoveries: {json.dumps(discoveries, indent=2)}

Error Context: {json.dumps(error_context, indent=2) if error_context else 'No errors'}

Target Tool: {error_context.get('failed_tool', 'unknown') if error_context else 'unknown'}

CRITICAL PARAMETER CORRECTIONS NEEDED:

1. **Site Parameters**: If discoveries show sites like {{"DM-Akron": "dm-akron"}}, use the slug "dm-akron" for site_name
2. **Rack Parameters**: If discoveries show racks like {{"Comms closet": {{"id": 1, "site": "dm-akron"}}}}, use exact name "Comms closet"
3. **Cluster Parameters**: If discoveries show clusters like {{"DO-AMS3": {{"id": 1}}}}, use exact name "DO-AMS3"
4. **Missing Parameters**: Add any missing required parameters using discovery data

EXAMPLES OF CORRECT TRANSFORMATIONS:
- User input "DM-Akron" → site_name: "dm-akron" (use slug from discoveries)
- User input "Comms closet" → rack_name: "Comms closet" (exact match from discoveries)
- User input "DO-AMS3" → cluster: "DO-AMS3" (exact match from discoveries)

Apply these corrections to ensure the failed query will succeed:

Return corrected parameters in JSON format:
{{
    "adapted_parameters": {{"site_name": "dm-akron", "rack_name": "Comms closet"}},
    "transformations_applied": [
        {{"original": "DM-Akron", "transformed": "dm-akron", "reason": "Used site slug from discoveries for site_name parameter"}},
        {{"original": "missing", "transformed": "Comms closet", "reason": "Added required rack_name from discoveries"}}
    ],
    "confidence": 0.95,
    "validation_notes": ["All required parameters now present with correct values"],
    "alternative_parameters": {{}}
}}"""
            
            # Get LLM transformation
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": adaptation_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            adaptation = json.loads(response.choices[0].message.content)
            
            # Add metadata
            adaptation["adaptation_timestamp"] = datetime.now().isoformat()
            adaptation["original_params"] = original_params
            
            self.logger.info(f"Parameter adaptation complete - "
                           f"{len(adaptation.get('transformations_applied', []))} transformations, "
                           f"Confidence: {adaptation.get('confidence', 0):.2f}")
            
            return {
                "success": True,
                "adaptation": adaptation
            }
            
        except Exception as e:
            self.logger.error(f"Parameter adaptation failed: {e}")
            return {
                "success": False,
                "adaptation": {
                    "adapted_parameters": original_params,
                    "transformations_applied": [],
                    "confidence": 0.0,
                    "validation_notes": [f"Adaptation failed: {e}"],
                    "alternative_parameters": {}
                }
            }
    
    async def validate_parameters(
        self,
        parameters: Dict[str, Any],
        tool_schema: Dict[str, Any],
        netbox_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate parameters against tool schema and NetBox context using LLM.
        
        Args:
            parameters: Parameters to validate
            tool_schema: Schema requirements of the tool
            netbox_context: Available NetBox entities and constraints
            
        Returns:
            Dict containing validation results and suggestions
        """
        try:
            prompt = f"""Validate these parameters against NetBox tool requirements:

Parameters: {json.dumps(parameters, indent=2)}

Tool Schema: {json.dumps(tool_schema, indent=2)}

NetBox Context (available entities): {json.dumps(netbox_context, indent=2)}

Validate:
1. Are all required parameters present?
2. Do parameter values exist in NetBox?
3. Are parameter formats correct?
4. Are there any relationship conflicts?
5. What corrections are needed?

Return validation in JSON format:
{{
    "is_valid": true/false,
    "missing_required": ["param1", "param2"],
    "invalid_values": {{"param": "reason"}},
    "format_issues": {{"param": "expected format"}},
    "suggested_corrections": {{"param": "corrected_value"}},
    "validation_confidence": 0.0-1.0
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You validate NetBox API parameters intelligently."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            validation = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Parameter validation - Valid: {validation.get('is_valid')}, "
                           f"Confidence: {validation.get('validation_confidence', 0):.2f}")
            
            return {
                "success": True,
                "validation": validation
            }
            
        except Exception as e:
            self.logger.error(f"Parameter validation failed: {e}")
            return {
                "success": False,
                "validation": {
                    "is_valid": False,
                    "validation_confidence": 0.0,
                    "error": str(e)
                }
            }
    
    async def generate_parameter_alternatives(
        self,
        original_params: Dict[str, Any],
        error_feedback: str
    ) -> Dict[str, Any]:
        """
        Generate alternative parameter sets based on error feedback using LLM.
        
        Args:
            original_params: Parameters that failed
            error_feedback: Error message or feedback
            
        Returns:
            Dict containing alternative parameter suggestions
        """
        try:
            prompt = f"""Generate alternative parameters based on this error feedback:

Failed Parameters: {json.dumps(original_params, indent=2)}

Error Feedback: {error_feedback}

Generate alternatives:
1. What parameter variations might work?
2. What different identifier formats could be tried?
3. What related parameters might be more appropriate?
4. What simplifications could help?

Return alternatives in JSON format:
{{
    "alternatives": [
        {{"params": {{}}, "reasoning": "why this might work", "confidence": 0.0-1.0}}
    ],
    "recommended_alternative": 0,
    "exploration_needed": ["what to explore to find correct params"]
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,  # Slightly higher for creative alternatives
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            alternatives = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Generated {len(alternatives.get('alternatives', []))} parameter alternatives")
            
            return {
                "success": True,
                "alternatives": alternatives
            }
            
        except Exception as e:
            self.logger.error(f"Alternative generation failed: {e}")
            return {
                "success": False,
                "alternatives": {
                    "alternatives": [],
                    "recommended_alternative": -1,
                    "exploration_needed": []
                }
            }
    
    async def merge_parameter_discoveries(
        self,
        original_params: Dict[str, Any],
        discovered_params: Dict[str, Any],
        priority: str = "discovered"
    ) -> Dict[str, Any]:
        """
        Intelligently merge original and discovered parameters using LLM.
        
        Args:
            original_params: User-provided parameters
            discovered_params: Parameters discovered through exploration
            priority: Which parameters take priority
            
        Returns:
            Dict containing merged parameters
        """
        try:
            prompt = f"""Merge these parameter sets intelligently:

Original User Parameters: {json.dumps(original_params, indent=2)}

Discovered Parameters: {json.dumps(discovered_params, indent=2)}

Priority: {priority}

Merge rules:
1. Preserve user intent where possible
2. Use discovered values for corrections
3. Handle conflicts intelligently
4. Maintain parameter relationships
5. Document merge decisions

Return merged parameters in JSON format:
{{
    "merged_parameters": {{"param": "value"}},
    "merge_decisions": [
        {{"param": "...", "chose": "original|discovered", "reason": "..."}}
    ],
    "conflicts_resolved": ["conflict1", "conflict2"],
    "merge_confidence": 0.0-1.0
}}"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You merge NetBox parameters intelligently."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            merge_result = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Parameter merge complete - "
                           f"{len(merge_result.get('conflicts_resolved', []))} conflicts resolved, "
                           f"Confidence: {merge_result.get('merge_confidence', 0):.2f}")
            
            return {
                "success": True,
                "merge": merge_result
            }
            
        except Exception as e:
            self.logger.error(f"Parameter merge failed: {e}")
            return {
                "success": False,
                "merge": {
                    "merged_parameters": original_params,
                    "merge_decisions": [],
                    "conflicts_resolved": [],
                    "merge_confidence": 0.0
                }
            }
    
    async def process_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process parameter adaptation request"""
        request_type = content.get("type", "adapt_parameters")
        
        if request_type == "adapt_parameters":
            return await self.adapt_parameters(
                content.get("original_params", {}),
                content.get("discoveries", {}),
                content.get("error_context", {}),
                content.get("tool_schema", {})
            )
        elif request_type == "validate_parameters":
            return await self.validate_parameters(
                content.get("parameters", {}),
                content.get("tool_schema", {}),
                content.get("netbox_context", {})
            )
        elif request_type == "generate_alternatives":
            return await self.generate_parameter_alternatives(
                content.get("original_params", {}),
                content.get("error_feedback", "")
            )
        elif request_type == "merge_parameters":
            return await self.merge_parameter_discoveries(
                content.get("original_params", {}),
                content.get("discovered_params", {}),
                content.get("priority", "discovered")
            )
        else:
            return {"error": f"Unknown request type: {request_type}"}