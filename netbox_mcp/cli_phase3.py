#!/usr/bin/env python3
"""
Phase 3 CLI Interface - OpenAI Agent Orchestration Testing

Interactive CLI for testing the Phase 3 Week 1-4 OpenAI Agent Foundation.
Provides natural language interface to the multi-agent orchestration system.
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
        """Initialize the agent system"""
        try:
            from .agents.conversation_manager import ConversationManagerAgent
            from .agents.intent_recognition import IntentRecognitionAgent
            from .agents.response_generation import ResponseGenerationAgent
            
            print("🤖 Initializing Phase 3 OpenAI Agent Orchestration...")
            
            # Initialize Conversation Manager
            self.conversation_manager = ConversationManagerAgent()
            await self.conversation_manager.initialize()
            
            # Initialize and register specialized agents
            intent_agent = IntentRecognitionAgent()
            await intent_agent.initialize()
            self.conversation_manager.register_agent("intent_recognition", intent_agent)
            
            response_agent = ResponseGenerationAgent()
            await response_agent.initialize()
            self.conversation_manager.register_agent("response_generation", response_agent)
            
            # Create a conversation session
            session_result = await self.conversation_manager.create_session({})
            self.session_id = session_result["session_id"]
            
            print(f"✅ Agent system initialized successfully")
            print(f"📱 Session ID: {self.session_id}")
            
            # Display system status
            stats = self.conversation_manager.get_conversation_stats()
            print(f"🤖 Registered agents: {', '.join(stats['registered_agents'])}")
            
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
        if not self.conversation_manager or not self.session_id:
            print("❌ Agent system not initialized")
            return False
        
        print(f"\n🔍 Processing: '{query}'")
        print("⏳ Orchestrating agents...")
        
        start_time = datetime.now()
        
        try:
            result = await self.conversation_manager.process_user_query({
                "query": query,
                "session_id": self.session_id
            })
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if result.get("success"):
                print(f"\n✅ Query processed successfully ({processing_time:.3f}s)")
                
                # Display response
                response = result.get("response", "No response generated")
                print(f"\n💬 Response:")
                print("-" * 60)
                print(response)
                print("-" * 60)
                
                # Display orchestration details
                agents_used = result.get("agents_used", [])
                if agents_used:
                    print(f"\n🤖 Agents coordinated: {', '.join(agents_used)}")
                
                # Display clarification if needed
                if result.get("requires_clarification"):
                    print(f"\n❓ Clarification requested - please provide more details")
                
                # Display any tool results
                tool_results = result.get("tool_results")
                if tool_results and isinstance(tool_results, dict):
                    if tool_results.get("operation") == "orchestrated_tool_execution":
                        execution_plan = tool_results.get("execution_plan", {})
                        print(f"\n📊 Execution Strategy: {execution_plan.get('strategy', 'unknown')}")
                        tools_selected = tool_results.get("tools_selected", [])
                        if tools_selected:
                            print(f"🔧 Tools Selected: {', '.join(tools_selected)}")
                
                return True
            else:
                print(f"\n❌ Query failed: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"\n❌ Error processing query: {e}")
            logger.exception("Full error details:")
            return False
    
    async def run_interactive(self):
        """Run interactive CLI mode"""
        print("\n" + "=" * 70)
        print("🚀 Phase 3 OpenAI Agent Orchestration - Interactive CLI")
        print("=" * 70)
        print("\nWelcome to the Phase 3 testing interface!")
        print("This CLI demonstrates the Week 1-4 OpenAI Agent Foundation.")
        print("\n📖 Example queries to try:")
        print("  • 'list all devices in the datacenter'")
        print("  • 'analyze network utilization across sites'") 
        print("  • 'show me rack inventory for datacenter-1'")
        print("  • 'create a new device in rack-01' (read-only demo)")
        print("  • 'help me understand my infrastructure'")
        print("\n💡 Commands:")
        print("  • 'quit' or 'exit' - Exit the CLI")
        print("  • 'stats' - Show conversation statistics")
        print("  • 'session' - Show session information")
        print("  • 'clear' - Clear screen")
        print("-" * 70)
        
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
                elif user_input.lower() == 'stats':
                    await self.show_stats()
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