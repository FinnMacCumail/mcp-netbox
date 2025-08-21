#!/usr/bin/env python3
"""
Phase 3 CLI Integration Test Suite

Comprehensive automated testing of the Phase 3 Week 1-4 CLI → Agent → Response flow.
Tests the complete orchestration system end-to-end.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
import sys
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Phase3IntegrationTests:
    """Integration test suite for Phase 3 CLI and Agent System"""
    
    def __init__(self):
        self.conversation_manager = None
        self.session_id = None
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    async def setup(self) -> bool:
        """Set up the test environment"""
        try:
            from netbox_mcp.agents.conversation_manager import ConversationManagerAgent
            from netbox_mcp.agents.intent_recognition import IntentRecognitionAgent
            from netbox_mcp.agents.response_generation import ResponseGenerationAgent
            
            print("🔧 Setting up Phase 3 Integration Test Environment...")
            
            # Initialize agents
            self.conversation_manager = ConversationManagerAgent()
            await self.conversation_manager.initialize()
            
            intent_agent = IntentRecognitionAgent()
            await intent_agent.initialize()
            self.conversation_manager.register_agent("intent_recognition", intent_agent)
            
            response_agent = ResponseGenerationAgent()
            await response_agent.initialize()
            self.conversation_manager.register_agent("response_generation", response_agent)
            
            # Create test session
            session_result = await self.conversation_manager.create_session({})
            self.session_id = session_result["session_id"]
            
            print(f"✅ Test environment ready - Session: {self.session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            logger.exception("Setup error details:")
            return False
    
    async def teardown(self):
        """Clean up test environment"""
        try:
            if self.conversation_manager and self.session_id:
                await self.conversation_manager.close_session({"session_id": self.session_id})
                await self.conversation_manager.cleanup()
            print("🧹 Test environment cleaned up")
        except Exception as e:
            print(f"⚠️  Warning during teardown: {e}")
    
    async def run_test_case(self, test_name: str, query: str, expected_intent: str = None, 
                           expected_success: bool = True, check_agents: List[str] = None) -> bool:
        """Run a single test case"""
        self.total_tests += 1
        test_start = datetime.now()
        
        print(f"\n🧪 Test: {test_name}")
        print(f"   Query: '{query}'")
        
        try:
            result = await self.conversation_manager.process_user_query({
                "query": query,
                "session_id": self.session_id
            })
            
            test_duration = (datetime.now() - test_start).total_seconds()
            
            # Basic success check
            success = result.get("success", False)
            if success != expected_success:
                print(f"   ❌ Expected success={expected_success}, got {success}")
                self.test_results.append({
                    "test": test_name,
                    "passed": False,
                    "error": f"Success mismatch: expected {expected_success}, got {success}",
                    "duration": test_duration
                })
                return False
            
            if not success:
                # Expected failure case
                print(f"   ✅ Expected failure handled correctly")
                self.test_results.append({
                    "test": test_name,
                    "passed": True,
                    "duration": test_duration
                })
                self.passed_tests += 1
                return True
            
            # Check response exists
            response = result.get("response")
            if not response:
                print(f"   ❌ No response generated")
                self.test_results.append({
                    "test": test_name,
                    "passed": False,
                    "error": "No response generated",
                    "duration": test_duration
                })
                return False
            
            # Check agent coordination
            agents_used = result.get("agents_used", [])
            if check_agents:
                missing_agents = [agent for agent in check_agents if agent not in agents_used]
                if missing_agents:
                    print(f"   ❌ Missing expected agents: {missing_agents}")
                    self.test_results.append({
                        "test": test_name,
                        "passed": False,
                        "error": f"Missing agents: {missing_agents}",
                        "duration": test_duration
                    })
                    return False
            
            # Check processing time is reasonable
            processing_time = result.get("processing_time", 0)
            if processing_time > 10:  # 10 second timeout
                print(f"   ⚠️  Slow processing time: {processing_time:.3f}s")
            
            print(f"   ✅ Success ({test_duration:.3f}s)")
            print(f"   🤖 Agents: {', '.join(agents_used)}")
            print(f"   📝 Response: {response[:100]}...")
            
            self.test_results.append({
                "test": test_name,
                "passed": True,
                "agents_used": agents_used,
                "processing_time": processing_time,
                "response_length": len(response),
                "duration": test_duration
            })
            self.passed_tests += 1
            return True
            
        except Exception as e:
            test_duration = (datetime.now() - test_start).total_seconds()
            print(f"   ❌ Exception: {e}")
            self.test_results.append({
                "test": test_name,
                "passed": False,
                "error": str(e),
                "duration": test_duration
            })
            return False
    
    async def test_discovery_queries(self) -> bool:
        """Test discovery-type queries"""
        print(f"\n📋 Testing Discovery Queries")
        print("=" * 50)
        
        tests = [
            ("Device Discovery", "list all devices in the datacenter", ["intent_recognition", "tool_coordination", "response_generation"]),
            ("Site Discovery", "show me all sites", ["intent_recognition", "tool_coordination", "response_generation"]),
            ("Rack Discovery", "find all racks in site-1", ["intent_recognition", "tool_coordination", "response_generation"]),
            ("VLAN Discovery", "list all VLANs", ["intent_recognition", "tool_coordination", "response_generation"]),
            ("Cable Discovery", "show me cable connections", ["intent_recognition", "tool_coordination", "response_generation"])
        ]
        
        results = []
        for test_name, query, expected_agents in tests:
            result = await self.run_test_case(test_name, query, check_agents=expected_agents)
            results.append(result)
        
        passed = sum(results)
        print(f"\n📊 Discovery Tests: {passed}/{len(tests)} passed")
        return passed == len(tests)
    
    async def test_analysis_queries(self) -> bool:
        """Test analysis-type queries"""
        print(f"\n📈 Testing Analysis Queries")
        print("=" * 50)
        
        tests = [
            ("Network Analysis", "analyze network utilization across all sites", ["intent_recognition", "tool_coordination", "response_generation"]),
            ("Inventory Analysis", "generate inventory report for datacenter-1", ["intent_recognition", "tool_coordination", "response_generation"]),
            ("Capacity Analysis", "analyze rack capacity utilization", ["intent_recognition", "tool_coordination", "response_generation"]),
            ("Health Analysis", "check system health status", ["intent_recognition", "tool_coordination", "response_generation"])
        ]
        
        results = []
        for test_name, query, expected_agents in tests:
            result = await self.run_test_case(test_name, query, check_agents=expected_agents)
            results.append(result)
        
        passed = sum(results)
        print(f"\n📊 Analysis Tests: {passed}/{len(tests)} passed")
        return passed == len(tests)
    
    async def test_creation_queries(self) -> bool:
        """Test creation-type queries (read-only phase)"""
        print(f"\n🔧 Testing Creation Queries (Read-Only Phase)")
        print("=" * 50)
        
        tests = [
            ("Device Creation", "create a new device in rack-01", ["intent_recognition", "task_planning", "tool_coordination", "response_generation"]),
            ("Site Creation", "add a new site called datacenter-2", ["intent_recognition", "task_planning", "tool_coordination", "response_generation"]),
            ("Rack Creation", "provision a new rack in site-1", ["intent_recognition", "task_planning", "tool_coordination", "response_generation"]),
            ("VLAN Creation", "create VLAN 100 for guest network", ["intent_recognition", "task_planning", "tool_coordination", "response_generation"])
        ]
        
        results = []
        for test_name, query, expected_agents in tests:
            result = await self.run_test_case(test_name, query, check_agents=expected_agents)
            results.append(result)
        
        passed = sum(results)
        print(f"\n📊 Creation Tests: {passed}/{len(tests)} passed")
        return passed == len(tests)
    
    async def test_clarification_flow(self) -> bool:
        """Test clarification and ambiguous queries"""
        print(f"\n❓ Testing Clarification Flow")
        print("=" * 50)
        
        tests = [
            ("Unclear Query", "help me with stuff", ["intent_recognition", "response_generation"]),
            ("Ambiguous Query", "show me the devices", ["intent_recognition", "response_generation"]),
            ("Vague Request", "I need help", ["intent_recognition", "response_generation"]),
            ("Empty Context", "what about those things?", ["intent_recognition", "response_generation"])
        ]
        
        results = []
        for test_name, query, expected_agents in tests:
            result = await self.run_test_case(test_name, query, check_agents=expected_agents)
            results.append(result)
        
        passed = sum(results)
        print(f"\n📊 Clarification Tests: {passed}/{len(tests)} passed")
        return passed == len(tests)
    
    async def test_multi_turn_conversation(self) -> bool:
        """Test multi-turn conversation capabilities"""
        print(f"\n💬 Testing Multi-Turn Conversation")
        print("=" * 50)
        
        # Simulate a conversation flow
        conversation_steps = [
            ("Initial Query", "show me all sites"),
            ("Follow-up", "what devices are in site-1?"),
            ("Refinement", "show me only the servers"),
            ("Analysis", "analyze their utilization")
        ]
        
        results = []
        for test_name, query in conversation_steps:
            result = await self.run_test_case(f"Conversation: {test_name}", query)
            results.append(result)
        
        # Test session state
        session_info = await self.conversation_manager.get_session_info({"session_id": self.session_id})
        if session_info.get("success"):
            info = session_info["session_info"]
            expected_messages = len(conversation_steps) * 2  # User + assistant messages
            if info["message_count"] >= expected_messages:
                print(f"   ✅ Session state maintained: {info['message_count']} messages")
                results.append(True)
            else:
                print(f"   ❌ Session state issue: {info['message_count']} messages, expected >= {expected_messages}")
                results.append(False)
        else:
            print(f"   ❌ Could not retrieve session info")
            results.append(False)
        
        passed = sum(results)
        print(f"\n📊 Multi-Turn Tests: {passed}/{len(conversation_steps)+1} passed")
        return passed == len(conversation_steps) + 1
    
    async def test_error_handling(self) -> bool:
        """Test error handling capabilities"""
        print(f"\n⚠️  Testing Error Handling")
        print("=" * 50)
        
        tests = [
            ("Empty Query", "", False),  # Expected to fail
            ("Invalid Session", "test query", True)  # Will use current session, should succeed
        ]
        
        results = []
        for test_name, query, expected_success in tests:
            result = await self.run_test_case(test_name, query, expected_success=expected_success)
            results.append(result)
        
        # Test invalid session
        invalid_result = await self.conversation_manager.process_user_query({
            "query": "test query",
            "session_id": "invalid-session-id"
        })
        
        # Should create new session and succeed
        if invalid_result.get("success"):
            print(f"   ✅ Invalid session handled correctly (auto-created new session)")
            results.append(True)
        else:
            print(f"   ❌ Invalid session not handled properly")
            results.append(False)
        
        passed = sum(results)
        print(f"\n📊 Error Handling Tests: {passed}/{len(tests)+1} passed")
        return passed == len(tests) + 1
    
    async def run_performance_test(self) -> bool:
        """Test system performance with concurrent queries"""
        print(f"\n⚡ Testing Performance")
        print("=" * 50)
        
        queries = [
            "list all devices",
            "show all sites", 
            "analyze network utilization",
            "check system health",
            "show rack inventory"
        ]
        
        start_time = datetime.now()
        
        # Run queries sequentially for now (could be parallel in production)
        results = []
        for i, query in enumerate(queries):
            result = await self.run_test_case(f"Performance Test {i+1}", query)
            results.append(result)
        
        total_time = (datetime.now() - start_time).total_seconds()
        avg_time = total_time / len(queries)
        
        print(f"\n📊 Performance Results:")
        print(f"   ⏱️  Total time: {total_time:.3f}s")
        print(f"   📈 Average per query: {avg_time:.3f}s")
        print(f"   🎯 Queries completed: {sum(results)}/{len(queries)}")
        
        # Performance criteria: average < 5 seconds per query
        performance_ok = avg_time < 5.0 and sum(results) == len(queries)
        if performance_ok:
            print(f"   ✅ Performance acceptable")
        else:
            print(f"   ❌ Performance issues detected")
        
        return performance_ok
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        # Calculate average processing time
        processing_times = [result.get("processing_time", 0) for result in self.test_results if result.get("processing_time")]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Calculate average test duration
        durations = [result.get("duration", 0) for result in self.test_results if result.get("duration")]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Count agent usage
        agent_usage = {}
        for result in self.test_results:
            agents = result.get("agents_used", [])
            for agent in agents:
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.total_tests - self.passed_tests,
                "success_rate": success_rate
            },
            "performance": {
                "avg_processing_time": avg_processing_time,
                "avg_test_duration": avg_duration,
                "total_duration": sum(durations)
            },
            "agent_usage": agent_usage,
            "detailed_results": self.test_results
        }
    
    async def run_all_tests(self) -> bool:
        """Run the complete test suite"""
        print("🚀 Starting Phase 3 CLI Integration Test Suite")
        print("=" * 70)
        print(f"📅 Test time: {datetime.now().isoformat()}")
        
        if not await self.setup():
            return False
        
        try:
            # Run all test categories
            test_results = []
            
            test_results.append(await self.test_discovery_queries())
            test_results.append(await self.test_analysis_queries()) 
            test_results.append(await self.test_creation_queries())
            test_results.append(await self.test_clarification_flow())
            test_results.append(await self.test_multi_turn_conversation())
            test_results.append(await self.test_error_handling())
            test_results.append(await self.run_performance_test())
            
            # Generate final report
            all_passed = all(test_results)
            report = self.generate_report()
            
            print(f"\n" + "=" * 70)
            print(f"🎉 Phase 3 Integration Test Suite Complete")
            print(f"=" * 70)
            print(f"📊 Overall Results:")
            print(f"  ✅ Tests passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']}")
            print(f"  📈 Success rate: {report['summary']['success_rate']:.1f}%")
            print(f"  ⏱️  Average processing time: {report['performance']['avg_processing_time']:.3f}s")
            print(f"  🤖 Agent usage: {', '.join([f'{k}({v})' for k, v in report['agent_usage'].items()])}")
            
            if all_passed:
                print(f"\n🎯 ALL TESTS PASSED - Phase 3 Week 1-4 CLI Integration Successful!")
                print(f"   OpenAI Agent Orchestration is fully operational")
            else:
                print(f"\n❌ Some tests failed - Review results above")
                failed_tests = [r for r in self.test_results if not r["passed"]]
                print(f"   Failed tests: {[r['test'] for r in failed_tests]}")
            
            # Save detailed report
            with open("phase3_integration_test_report.json", "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved: phase3_integration_test_report.json")
            
            return all_passed
            
        finally:
            await self.teardown()

async def main():
    """Main test runner"""
    test_suite = Phase3IntegrationTests()
    success = await test_suite.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal test error: {e}")
        logger.exception("Full error details:")
        sys.exit(1)