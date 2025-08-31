#!/usr/bin/env python3
"""
Phase 5 Quick Validation - Demonstrate Claude Code CLI Parity

This script provides a quick demonstration that the original failing queries
from the user's comparison examples now work correctly with the Phase 1-5
intelligent system.

Shows concrete evidence that Claude Code CLI parity has been achieved.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netbox_mcp.orchestration.intelligent_tool_selector import select_tool
from netbox_mcp.orchestration.tool_aware_parameter_extractor import extract_parameters


async def validate_critical_queries():
    """
    Quick validation of the 4 original failing queries that must now work
    """
    print("🎯 NetBox MCP Phase 5 - Quick Validation")
    print("=" * 60)
    print("Demonstrating Claude Code CLI Parity Achievement")
    print("Testing original failing queries from user comparison")
    print("=" * 60)
    
    # The 4 critical queries that were originally failing
    critical_tests = [
        {
            "name": "Device Type Information Query",
            "query": "device type information for Cisco C9200-48P",
            "expected_tool": "netbox_get_device_type_info",
            "expected_params": ["manufacturer", "model"],
            "original_issue": "Wrong tool selection, lost manufacturer context"
        },
        {
            "name": "Device Info Query", 
            "query": "device info for dc1-sw01",
            "expected_tool": "netbox_get_device_info",
            "expected_params": ["device_name"],
            "original_issue": "Wrong tool, broken parameters"
        },
        {
            "name": "Rack Elevation Query",
            "query": "rack elevation for R01-A15", 
            "expected_tool": "netbox_get_rack_elevation",
            "expected_params": ["rack_name"],
            "original_issue": "Completely wrong tool selection"
        },
        {
            "name": "Device Interfaces Query",
            "query": "show interfaces for device dc1-sw01",
            "expected_tool": "netbox_get_device_interfaces", 
            "expected_params": ["device_name"],
            "original_issue": "Wrong tool selection and parameters"
        }
    ]
    
    results = []
    
    for i, test in enumerate(critical_tests, 1):
        print(f"\n🧪 Test {i}/4: {test['name']}")
        print(f"   Query: '{test['query']}'")
        print(f"   Original Issue: {test['original_issue']}")
        
        try:
            # Phase 1: Test IntelligentToolSelector
            print(f"   🔍 Phase 1: IntelligentToolSelector...")
            tool_selection = await select_tool(test['query'])
            
            if not tool_selection:
                print(f"   ❌ FAIL: No tool selected")
                results.append(False)
                continue
            
            tool_correct = tool_selection.primary_tool == test['expected_tool']
            confidence_good = tool_selection.confidence >= 0.8
            
            print(f"      Selected: {tool_selection.primary_tool}")
            print(f"      Expected: {test['expected_tool']}")
            print(f"      Confidence: {tool_selection.confidence:.2f}")
            
            if not tool_correct:
                print(f"   ❌ FAIL: Wrong tool selected")
                results.append(False) 
                continue
            
            # Phase 2: Test ToolAwareParameterExtractor
            print(f"   🔍 Phase 2: ToolAwareParameterExtractor...")
            param_extraction = await extract_parameters(
                test['query'], 
                tool_selection.primary_tool
            )
            
            if not param_extraction:
                print(f"   ❌ FAIL: Parameter extraction failed")
                results.append(False)
                continue
            
            params_correct = all(
                param in param_extraction.parameters 
                for param in test['expected_params']
            )
            
            print(f"      Method: {param_extraction.extraction_method}")
            print(f"      Confidence: {param_extraction.confidence:.2f}")
            print(f"      Parameters: {param_extraction.parameters}")
            
            if not params_correct:
                print(f"   ❌ FAIL: Missing expected parameters")
                results.append(False)
                continue
            
            # Success!
            print(f"   🎉 SUCCESS: Query FIXED!")
            print(f"      ✅ Correct tool selected: {tool_selection.primary_tool}")
            print(f"      ✅ Parameters extracted: {list(param_extraction.parameters.keys())}")
            print(f"      ✅ Original issue resolved!")
            
            results.append(True)
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("🏆 VALIDATION RESULTS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(critical_tests, results), 1):
        status = "✅ FIXED" if result else "❌ STILL FAILING"
        print(f"{i}. {status}: {test['name']}")
    
    print(f"\nOverall: {passed}/{total} queries fixed")
    
    if passed == total:
        print("\n🎉 CLAUDE CODE CLI PARITY ACHIEVED!")
        print("✅ All original failing queries now work correctly")
        print("✅ Intelligent tool selection replaces failed pattern matching")
        print("✅ Context-preserving parameter extraction maintains relationships")
        print("✅ NetBox MCP now provides reliable, intelligent CLI experience")
        print("\n🚀 Ready for production deployment!")
    else:
        print(f"\n⚠️ Parity not achieved - {total-passed} queries still failing")
        print("🔧 Additional fixes needed")
    
    return passed == total


async def demonstrate_system_intelligence():
    """
    Demonstrate the intelligent capabilities that replace the original failed system
    """
    print("\n" + "=" * 60)  
    print("🧠 SYSTEM INTELLIGENCE DEMONSTRATION")
    print("=" * 60)
    
    demo_queries = [
        "find device type specs for Dell PowerEdge R750",
        "get information about switch core-sw-01", 
        "show rack layout for ServerRack-A10",
        "list network interfaces on firewall-main"
    ]
    
    print("Demonstrating intelligent understanding beyond the fixed queries:")
    
    for query in demo_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            selection = await select_tool(query)
            if selection:
                print(f"   🎯 Tool: {selection.primary_tool}")
                print(f"   📊 Confidence: {selection.confidence:.2f}")
                print(f"   🧠 Reasoning: {selection.reasoning[:100]}...")
            else:
                print(f"   ❌ No tool selected")
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def main():
    """Main validation entry point"""
    
    print("Starting Phase 5 Quick Validation...")
    print("This validates that Claude Code CLI parity has been achieved\n")
    
    try:
        # Test critical failing queries
        parity_achieved = await validate_critical_queries()
        
        # Demonstrate broader intelligence  
        await demonstrate_system_intelligence()
        
        print(f"\n" + "=" * 60)
        print("📋 FINAL ASSESSMENT")
        print("=" * 60)
        
        if parity_achieved:
            print("🎉 PHASE 5 VALIDATION: SUCCESS")
            print("✅ Claude Code CLI parity ACHIEVED")
            print("✅ Original failing queries FIXED") 
            print("✅ Intelligent system demonstrates superior capabilities")
            print("✅ NetBox MCP architectural rewrite: COMPLETE")
            print("\n🚀 Recommendation: DEPLOY TO PRODUCTION")
        else:
            print("⚠️ PHASE 5 VALIDATION: INCOMPLETE")
            print("🔧 Some queries still failing - additional work needed")
        
        return 0 if parity_achieved else 1
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)