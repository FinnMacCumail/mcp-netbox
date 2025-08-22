#!/usr/bin/env python3
"""
Phase 3 CLI Interface - LangGraph Orchestration Engine (Week 5-8)

Interactive CLI for testing the advanced LangGraph StateGraph orchestration
with intelligent tool coordination, caching, and limitation handling.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class Phase3CLI:
    """Interactive CLI for Phase 3 Agent Testing"""
    
    def __init__(self):
        self.conversation_manager = None
        self.session_id = None
        self.running = False
        
    async def initialize(self):
        """Initialize the LangGraph orchestration system"""
        try:
            from .orchestration import (
                create_orchestration_graph,
                ToolCoordinator, 
                OrchestrationCache,
                LimitationHandler
            )
            
            print("🚀 Initializing Phase 3 Week 5-8 LangGraph Orchestration Engine...")
            
            # Initialize LangGraph state machine
            self.orchestration_graph = create_orchestration_graph()
            print("✅ LangGraph StateGraph compiled successfully")
            
            # Initialize coordination infrastructure
            self.tool_coordinator = ToolCoordinator(redis_url="redis://localhost:6379")
            await self.tool_coordinator.initialize()
            print("✅ Tool coordination system initialized")
            
            # Initialize intelligent caching
            self.cache_system = OrchestrationCache()
            cache_ready = await self.cache_system.initialize()
            if cache_ready:
                print("✅ Redis-backed intelligent caching enabled")
            else:
                print("⚠️  Caching disabled (Redis unavailable)")
            
            # Initialize limitation handler
            self.limitation_handler = LimitationHandler()
            print("✅ Limitation handling system ready")
            
            # Create orchestration session
            self.session_id = f"langgraph_session_{int(datetime.now().timestamp())}"
            
            print(f"✅ LangGraph orchestration system initialized successfully")
            print(f"📱 Session ID: {self.session_id}")
            
            # Display system capabilities
            print(f"🧠 LangGraph StateGraph: 5-node orchestration workflow")
            print(f"⚡ Advanced Coordination: Parallel execution, intelligent caching, limitation handling")
            print(f"🛠️  NetBox Tools: 142+ MCP tools available for coordination")
            
            return True
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("🔧 Make sure dependencies are installed: uv pip install -e .")
            return False
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            logger.exception("Full error details:")
            return False
    
    async def process_query(self, query: str) -> bool:
        """Process a user query through the agent system"""
        if not hasattr(self, 'orchestration_graph') or not self.session_id:
            print("❌ LangGraph orchestration system not initialized")
            return False
        
        print(f"\n🔍 Processing: '{query}'")
        print("⚡ LangGraph StateGraph orchestration...")
        
        start_time = datetime.now()
        
        try:
            # Create initial state for LangGraph workflow
            from uuid import uuid4
            correlation_id = f"{self.session_id}_{str(uuid4())[:8]}"
            
            initial_state = {
                "user_query": query,
                "session_id": self.session_id,
                "correlation_id": correlation_id,
                "classified_intent": None,
                "entities": None,
                "confidence_score": None,
                "coordination_strategy": None,
                "tool_execution_plan": None,
                "tool_results": [],
                "known_limitations": [],
                "limitation_strategy": None,
                "progressive_state": None,
                "natural_language_response": None,
                "user_options": None,
                "next_action": None,
                "workflow_complete": False,
                "error_state": None,
                "conversation_context": {},
                "performance_metrics": None
            }
            
            # Execute LangGraph workflow
            config = {"configurable": {"thread_id": self.session_id}}
            
            final_state = await self.orchestration_graph.ainvoke(
                initial_state, 
                config=config
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if final_state.get("workflow_complete"):
                print(f"\n✅ LangGraph workflow completed successfully ({processing_time:.3f}s)")
                
                # Display orchestration details
                print(f"\n📊 Orchestration Details:")
                print(f"   🎯 Strategy: {final_state.get('coordination_strategy', 'unknown')}")
                print(f"   🧠 Intent: {final_state.get('classified_intent', {}).get('category', 'unknown')}")
                print(f"   🔧 Tools Executed: {len(final_state.get('tool_results', []))}")
                
                # Display limitations handled
                limitations = final_state.get("known_limitations", [])
                if limitations:
                    print(f"   ⚠️  Limitations Handled: {len(limitations)}")
                    limitation_strategy = final_state.get("limitation_strategy")
                    if limitation_strategy:
                        print(f"   🛡️  Strategy: {limitation_strategy}")
                
                # Display response
                response = final_state.get("natural_language_response", "No response generated")
                print(f"\n💬 Response:")
                print("-" * 60)
                print(response)
                print("-" * 60)
                
                # Display user options if available
                user_options = final_state.get("user_options", [])
                if user_options:
                    print(f"\n🎛️  Available Options:")
                    for i, option in enumerate(user_options, 1):
                        print(f"   {i}. {option}")
                
                return True
            else:
                error_state = final_state.get("error_state")
                if error_state:
                    print(f"\n❌ Workflow failed at {error_state['stage']}: {error_state['error']}")
                else:
                    print(f"\n❌ Workflow incomplete - unknown error")
                return False
                
        except Exception as e:
            print(f"\n❌ Error processing query: {e}")
            logger.exception("Full error details:")
            return False
    
    async def run_interactive(self):
        """Run interactive CLI mode"""
        print("\n" + "=" * 80)
        print("🚀 Phase 3 Week 5-8: LangGraph Orchestration Engine - Interactive CLI")
        print("=" * 80)
        print("\nWelcome to the advanced LangGraph StateGraph orchestration interface!")
        print("This CLI demonstrates sophisticated tool coordination with intelligent limitation handling.")
        print("\n🧠 LangGraph Features:")
        print("  • StateGraph workflows with 5-node orchestration")
        print("  • Intelligent caching with Redis backend")
        print("  • Progressive disclosure for large datasets")
        print("  • Parallel tool execution with dependency management")
        print("  • Graceful handling of 35+ NetBox MCP tool limitations")
        print("\n📖 Example queries to try:")
        print("  • 'list all devices in datacenter-01' (with intelligent caching)")
        print("  • 'analyze network connectivity for rack R01-A15' (parallel coordination)")
        print("  • 'show me all VLANs' (progressive disclosure for large datasets)")
        print("  • 'create a new server rack in site NYC' (complex workflow orchestration)")
        print("  • 'help me understand power distribution' (limitation-aware processing)")
        print("\n💡 Commands:")
        print("  • 'quit' or 'exit' - Exit the CLI")
        print("  • 'cache-stats' - Show intelligent caching statistics") 
        print("  • 'orchestration-stats' - Show LangGraph coordination metrics")
        print("  • 'clear' - Clear screen")
        print("-" * 80)
        
        self.running = True
        
        while self.running:
            try:
                # Get user input
                user_input = input(f"\n🤖 NetBox AI> ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye! Shutting down agent system...")
                    break
                elif user_input.lower() == 'cache-stats':
                    await self.show_cache_stats()
                    continue
                elif user_input.lower() == 'orchestration-stats':
                    await self.show_orchestration_stats()
                    continue
                elif user_input.lower() == 'session':
                    await self.show_session_info()
                    continue
                elif user_input.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                elif user_input.lower() in ['help', '?']:
                    self.show_help()
                    continue
                
                # Process the query
                await self.process_query(user_input)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user. Shutting down...")
                break
            except EOFError:
                print("\n\n👋 Session ended. Shutting down...")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                logger.exception("Full error details:")
    
    async def show_stats(self):
        """Show conversation statistics"""
        if not self.conversation_manager:
            print("❌ Agent system not initialized")
            return
        
        stats = self.conversation_manager.get_conversation_stats()
        print(f"\n📊 Conversation Statistics:")
        print(f"  📱 Active sessions: {stats['active_sessions']}")
        print(f"  💬 Total messages: {stats['total_messages']}")
        print(f"  🤖 Registered agents: {', '.join(stats['registered_agents']) if stats['registered_agents'] else 'None'}")
        print(f"  📈 Max concurrent sessions: {stats['max_concurrent_sessions']}")
        print(f"  📊 Avg messages/session: {stats['avg_messages_per_session']:.2f}")
    
    async def show_session_info(self):
        """Show current session information"""
        if not self.conversation_manager or not self.session_id:
            print("❌ No active session")
            return
        
        session_result = await self.conversation_manager.get_session_info({
            "session_id": self.session_id
        })
        
        if session_result.get("success"):
            info = session_result["session_info"]
            print(f"\n📱 Session Information:")
            print(f"  🆔 Session ID: {info['session_id']}")
            print(f"  🕐 Created: {info['created_at']}")
            print(f"  ⏰ Last activity: {info['last_activity']}")
            print(f"  💬 Messages: {info['message_count']}")
            print(f"  🔑 Context keys: {', '.join(info['context_keys']) if info['context_keys'] else 'None'}")
            print(f"  🤖 Active agents: {', '.join(info['active_agents']) if info['active_agents'] else 'None'}")
        else:
            print(f"❌ Failed to get session info: {session_result.get('error')}")
    
    def show_help(self):
        """Show help information"""
        print(f"\n📚 Phase 3 Agent Orchestration Help:")
        print(f"\n🎯 What This Demonstrates:")
        print(f"  • Natural language query processing")
        print(f"  • Multi-agent coordination and orchestration")
        print(f"  • Intelligent intent recognition and classification")
        print(f"  • Context-aware response generation")
        print(f"  • Session management and conversation tracking")
        print(f"\n🤖 Agent System:")
        print(f"  • Conversation Manager: Primary orchestrator")
        print(f"  • Intent Recognition: Query understanding")
        print(f"  • Response Generation: Natural language formatting")
        print(f"  • Tool Coordination: NetBox MCP tool orchestration (simulated)")
        print(f"\n🔧 Current Phase Scope:")
        print(f"  • Week 1-4: OpenAI Agent Foundation")
        print(f"  • Read-only orchestration with simulation")
        print(f"  • Multi-turn conversation support")
        print(f"  • Clarification and error handling")
    
    async def show_cache_stats(self):
        """Show intelligent caching statistics"""
        if not hasattr(self, 'cache_system'):
            print("❌ Cache system not initialized")
            return
        
        try:
            stats = await self.cache_system.get_cache_statistics()
            print(f\"\n📊 Intelligent Caching Statistics:\")
            print(f\"  🎯 Hit Rate: {stats['hit_rate']:.1f}%\")
            print(f\"  📈 Total Requests: {stats['total_requests']}\")
            print(f\"  ✅ Cache Hits: {stats['cache_hits']}\")
            print(f\"  ❌ Cache Misses: {stats['cache_misses']}\")
            print(f\"  💾 Cache Sets: {stats['cache_sets']}\")
            print(f\"  🗑️  Invalidations: {stats['invalidations']}\")
            
            performance = stats.get('performance_impact', {})
            if performance:
                print(f\"\n⚡ Performance Impact:\")
                print(f\"  💰 API Calls Saved: {performance['estimated_api_calls_saved']}\")
                print(f\"  ⏱️  Time Saved: {performance['estimated_time_saved_seconds']:.1f}s\")
                print(f\"  📊 Efficiency: {performance['cache_efficiency']}\")
        except Exception as e:
            print(f\"❌ Error retrieving cache stats: {e}\")
    
    async def show_orchestration_stats(self):
        \"\"\"Show LangGraph coordination statistics\"\"\"
        if not hasattr(self, 'tool_coordinator'):
            print(\"❌ Tool coordinator not initialized\")
            return
        
        try:
            stats = self.tool_coordinator.get_execution_statistics()
            print(f\"\n📊 LangGraph Orchestration Statistics:\")
            print(f\"  🔧 Total Tool Requests: {stats['total_requests']}\")
            print(f\"  ✅ Success Rate: {stats['success_rate']:.1f}%\")
            print(f\"  💾 Cache Hit Rate: {stats['cache_hit_rate']:.1f}%\")
            print(f\"  ⚡ Parallel Executions: {stats['parallel_executions']}\")
            
            performance = stats.get('performance_summary', {})
            if performance:
                print(f\"\n⚡ Performance Summary:\")
                print(f\"  📊 Avg Cache Hit Rate: {performance['avg_cache_hit_rate']}\")
                print(f\"  🚀 Parallel Speedup: {performance['parallel_execution_speedup']}\")
                print(f\"  🛡️  Error Recovery Rate: {performance['error_recovery_rate']}\")
        except Exception as e:
            print(f\"❌ Error retrieving orchestration stats: {e}\")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.conversation_manager and self.session_id:
            try:
                await self.conversation_manager.close_session({"session_id": self.session_id})
                await self.conversation_manager.cleanup()
                print("✅ Agent system shut down successfully")
            except Exception as e:
                print(f"⚠️  Warning during cleanup: {e}")

async def run_batch_test():
    """Run a batch of test queries"""
    cli = Phase3CLI()
    
    if not await cli.initialize():
        return False
    
    test_queries = [
        "list all devices in the datacenter",
        "analyze network utilization across all sites", 
        "show me rack inventory for site-1",
        "create a new device in rack-01",
        "help me understand my infrastructure",
        "what is the current health status?"
    ]
    
    print(f"\n🧪 Running batch test with {len(test_queries)} queries...")
    print("=" * 70)
    
    success_count = 0
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}/{len(test_queries)}")
        if await cli.process_query(query):
            success_count += 1
    
    print(f"\n📊 Batch Test Results:")
    print(f"  ✅ Successful: {success_count}/{len(test_queries)}")
    print(f"  📈 Success rate: {(success_count/len(test_queries)*100):.1f}%")
    
    await cli.cleanup()
    return success_count == len(test_queries)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 3 OpenAI Agent Orchestration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  netbox-mcp-phase3 --interactive    # Start interactive CLI
  netbox-mcp-phase3 --batch-test     # Run automated test queries
  netbox-mcp-phase3 --query "list all devices"  # Single query
        """
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive CLI mode (default)"
    )
    
    parser.add_argument(
        "--batch-test", "-b",
        action="store_true", 
        help="Run batch test with predefined queries"
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Process a single query and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async def main_async():
        """Async main function"""
        cli = Phase3CLI()
        
        try:
            if not await cli.initialize():
                return 1
            
            if args.batch_test:
                success = await run_batch_test()
                return 0 if success else 1
            elif args.query:
                success = await cli.process_query(args.query)
                await cli.cleanup()
                return 0 if success else 1
            else:
                # Default to interactive mode
                await cli.run_interactive()
                await cli.cleanup()
                return 0
                
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            logger.exception("Full error details:")
            return 1
    
    # Run the async main function
    try:
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()