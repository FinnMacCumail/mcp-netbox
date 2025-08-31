#!/usr/bin/env python3
"""
Validation Script for Adaptive Intelligence System

This script tests the original failing queries to validate that the 
LLM-driven adaptive intelligence system now works correctly.
"""

import asyncio
import logging
import json
from datetime import datetime

from netbox_mcp.orchestration.backward_compatibility import BackwardCompatibilityManager, CompatibilityConfig, MigrationPhase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_adaptive_recovery():
    """Test the adaptive intelligence system with original failing queries"""
    
    print("🧪 Testing Adaptive Intelligence System - Original Failing Queries")
    print("="*80)
    
    # Create compatibility manager configured to use intelligent system
    config = CompatibilityConfig(
        migration_phase=MigrationPhase.INTELLIGENT_ONLY,  # Force intelligent system
        feature_flags={
            "use_intelligent_tool_selector": True,
            "use_context_aware_parameters": True,
            "use_langgraph_workflow": True,
            "use_intelligent_fallback": True,
            "enable_a_b_testing": False,
            "enable_performance_monitoring": True,
        }
    )
    
    manager = BackwardCompatibilityManager(config)
    await manager.initialize()
    
    # Original failing queries from the user's examples
    test_queries = [
        {
            "query": "Get rack elevation for rack Comms closet in site DM-Akron",
            "expected_improvements": [
                "Should discover correct site name/slug through EntityDiscoveryAgent",
                "Should adapt parameters with ParameterAdaptationAgent", 
                "Should recover from site validation error"
            ]
        },
        {
            "query": "Show rack inventory for rack 'Rack Comms closet' in site 'DM-Scranton'",
            "expected_improvements": [
                "Should discover correct rack and site identifiers",
                "Should adapt parameters based on discoveries",
                "Should recover from entity naming issues"
            ]
        },
        {
            "query": "Show all virtual machines in cluster DO-AMS3",
            "expected_improvements": [
                "Should select netbox_list_all_virtual_machines (NOT netbox_list_all_devices)",
                "Should classify as Virtualization domain (NOT DCIM)",
                "Should recognize DO-AMS3 as cluster (NOT site)"
            ]
        },
        {
            "query": "Get IP usage statistics for prefix 10.112.128.0/17",
            "expected_improvements": [
                "Should select appropriate IP usage tool",
                "Should extract specific prefix parameter correctly",
                "Should avoid generic prefix listing"
            ]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected = test_case["expected_improvements"]
        
        print(f"\n🔍 Test {i}: {query}")
        print("-" * 60)
        
        try:
            session_id = f"adaptive_test_{i}_{datetime.now().strftime('%H%M%S')}"
            
            # Process with adaptive intelligence system
            result = await manager.process_query(
                query=query,
                session_id=session_id,
                correlation_id=f"validation_test_{i}"
            )
            
            # Analyze results
            success = result.get("success", False)
            system_used = result.get("compatibility_metadata", {}).get("system_used", "unknown")
            response = result.get("response", "No response")
            
            print(f"✅ System Used: {system_used}")
            print(f"✅ Success: {success}")
            print(f"📝 Response Length: {len(response)} characters")
            
            if "tool_results" in result and result["tool_results"]:
                tool_names = [tr.get("tool_name", "unknown") for tr in result["tool_results"]]
                print(f"🔧 Tools Used: {', '.join(tool_names)}")
                
                # Check for VM query improvement
                if "virtual machine" in query.lower() and "netbox_list_all_virtual_machines" in tool_names:
                    print("🎉 IMPROVEMENT: Correctly selected VM tools instead of device tools!")
                elif "virtual machine" in query.lower() and "netbox_list_all_devices" in tool_names:
                    print("⚠️  ISSUE: Still using device tools for VM query")
            
            # Check for recovery indicators
            execution_metrics = result.get("execution_metrics", {})
            if "recovery_attempted" in str(result):
                print("🔄 Recovery mechanisms detected in response")
            
            if "fallback_used" in result.get("compatibility_metadata", {}):
                print("🔀 Fallback system was used")
            
            results.append({
                "query": query,
                "success": success,
                "system_used": system_used,
                "improvements_validated": [],
                "issues_remaining": []
            })
            
            print(f"📊 Expected Improvements:")
            for improvement in expected:
                print(f"   • {improvement}")
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print(f"\n🎯 VALIDATION SUMMARY")
    print("="*80)
    
    successful_tests = sum(1 for r in results if r.get("success", False))
    total_tests = len(results)
    
    print(f"✅ Successful Tests: {successful_tests}/{total_tests}")
    print(f"🧠 Adaptive Intelligence: {'ACTIVE' if any(r.get('system_used') == 'intelligent' for r in results) else 'NOT DETECTED'}")
    
    if successful_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Adaptive Intelligence System Working!")
    else:
        print(f"⚠️  {total_tests - successful_tests} tests still need improvement")
    
    return results

async def main():
    """Main validation function"""
    try:
        results = await test_adaptive_recovery()
        
        # Save results for analysis
        with open("adaptive_validation_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to adaptive_validation_results.json")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())